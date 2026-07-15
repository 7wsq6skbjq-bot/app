"""Parse a *filled* Portech AT order form PDF (interactive AcroForm) into
an `ATDoorOrder` payload — no OCR / no LLM cost.

Clients (glaziers) download our blank AT order form (produced by
`render_client_at_order_form_pdf`), fill the fields directly in
Adobe/Preview, save and email it back. This module reads those
AcroForm values via `pypdf` and produces the same JSON payload as
the Gemini OCR parser — so the ATOrdersPanel can pre-fill the form
identically.
"""
from __future__ import annotations

import io
import re
from typing import Any

from pypdf import PdfReader


# ─── Value helpers ──────────────────────────────────────────────────────────
_TRUE = {"/Yes", "Yes", "On", "/On", "True", "true", "1", "X", "x"}


def _cbox(fields: dict[str, dict], name: str) -> bool:
    """Return True if the checkbox 'name' is ticked, False otherwise."""
    f = fields.get(name)
    if not f:
        return False
    v = f.get("/V") or f.get("value")
    if v is None:
        return False
    if isinstance(v, str):
        return v in _TRUE or v.strip().lower() not in ("off", "/off", "no", "false", "", "0")
    return bool(v)


def _tx(fields: dict[str, dict], name: str) -> str:
    """Return the text-field value or empty string."""
    f = fields.get(name)
    if not f:
        return ""
    v = f.get("/V") or f.get("value") or ""
    return str(v).strip()


def _first_tx(fields: dict[str, dict], prefix: str) -> str:
    """Return the value of the first text-field whose name starts with `prefix`.

    Our blank form suffixes numeric fields with `_N` counters (e.g. `client_1`,
    `po_number_2`), so we resolve by prefix.
    """
    matches = [k for k in fields if k.startswith(prefix + "_") or k == prefix]
    if not matches:
        return ""
    matches.sort(key=lambda k: int(k.rsplit("_", 1)[-1]) if k.rsplit("_", 1)[-1].isdigit() else 0)
    return _tx(fields, matches[0])


# Free text "L x H" dimension parser — returns (w_in, h_in) or None.
_DIM_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:po|pouces|in|\")?\s*[x\u00d7X]\s*(\d+(?:[.,]\d+)?)"
)


def _parse_dim_inches(text: str) -> tuple[float, float] | None:
    if not text:
        return None
    m = _DIM_RE.search(text)
    if not m:
        return None
    try:
        w = float(m.group(1).replace(",", "."))
        h = float(m.group(2).replace(",", "."))
    except ValueError:
        return None
    # If the numbers are clearly in mm (>200), convert to inches.
    if max(w, h) > 200:
        w = round(w / 25.4, 3)
        h = round(h / 25.4, 3)
    return (w, h)


# ─── Main mapper ────────────────────────────────────────────────────────────
def parse_portech_at_form(pdf_bytes: bytes) -> dict[str, Any]:
    """Read our blank Portech AT order form (filled by the client) and
    return a dict suitable for `ATDoorOrder(**data)`.

    Raises `ValueError` if the PDF has no AcroForm or is not our template.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    fields = reader.get_fields() or {}
    if not fields:
        raise ValueError(
            "Ce PDF ne contient aucun champ interactif. Assure-toi que le "
            "client remplit bien la version Portech du formulaire (celle "
            "envoyée depuis l'ERP).",
        )

    # ─── Meta ─────────────────────────────────────────────
    client       = _first_tx(fields, "client")
    contact      = _first_tx(fields, "contact")
    phone        = _first_tx(fields, "phone")
    order_number = _first_tx(fields, "po_number")
    project_name = _first_tx(fields, "project")
    order_date   = _first_tx(fields, "date")
    required_dt  = _first_tx(fields, "date_needed")
    # `email` field currently not persisted in ATDoorOrder — appended to notes.
    email        = _first_tx(fields, "email")

    # ─── Series ───────────────────────────────────────────
    series = "AT1000"
    for k, model_val in (
        ("model_at1000", "AT1000"),
        ("model_ati1000", "ATi1000"),
        ("model_at2000", "AT2000"),
        ("model_ati2000", "ATi2000"),
    ):
        if _cbox(fields, k):
            series = model_val
            break

    # ─── Dimensions ───────────────────────────────────────
    is_standard = _cbox(fields, "dim_standard_36x84")
    dim_custom  = _first_tx(fields, "dim_custom")
    if is_standard:
        w_in, h_in = 36.0, 84.0
    else:
        parsed = _parse_dim_inches(dim_custom)
        w_in, h_in = parsed if parsed else (36.0, 84.0)

    # ─── Finishes ─────────────────────────────────────────
    FIN = [
        "Anodisé clair", "Noir", "Bronze", "Dark Bronze",
        "Champagne", "Mill finish",
    ]
    finish_exterior = next(
        (FIN[i] for i in range(6) if _cbox(fields, f"finish_ext_{i}")),
        None,
    )
    finish_interior = next(
        (FIN[i] for i in range(6) if _cbox(fields, f"finish_int_{i}")),
        None,
    )
    color_code_exterior = _first_tx(fields, "finish_ext_code")
    color_code_interior = _first_tx(fields, "finish_int_code")

    # ─── Swings (GE/DE/PE/GI/DI/PI) → one door line per direction ──────────
    swings = [
        ("swing_ge", "GE"), ("swing_de", "DE"), ("swing_pe", "PE"),
        ("swing_gi", "GI"), ("swing_di", "DI"), ("swing_pi", "PI"),
    ]
    doors: list[dict[str, Any]] = []
    for fname, hand in swings:
        if _cbox(fields, fname):
            qty_raw = _tx(fields, fname + "_qty")
            try:
                qty = max(1, int(re.sub(r"\D", "", qty_raw) or "1"))
            except ValueError:
                qty = 1
            doors.append({
                "tag": None,
                "series": series,
                "width_in": w_in, "height_in": h_in,
                "qty": qty, "hand": hand,
                "glazing": "unknown",
                "hardware": {},   # filled just below (copied on every door)
                "notes": None,
            })
    if not doors:
        doors.append({
            "tag": None, "series": series,
            "width_in": w_in, "height_in": h_in,
            "qty": 1, "hand": "unknown",
            "glazing": "unknown", "hardware": {}, "notes": None,
        })

    # ─── Hardware ────────────────────────────────────────
    hw: dict[str, Any] = {}
    # Hinges
    hw["hinge_4_5x4"]        = _cbox(fields, "hinge_std")
    hw["hinge_continuous"]   = _cbox(fields, "hinge_cont")
    hw["hinge_continuous_hd"] = _cbox(fields, "hinge_cont_hd")
    # Hinge qty per porte (radio-like via 4 checkboxes)
    hw["hinge_4_5x4_qty"] = None
    for i in (1, 2, 3, 4):
        if _cbox(fields, f"hinge_qty_{i}"):
            hw["hinge_4_5x4_qty"] = i
            break

    # Handles/pulls — handle_0..7 mapping (order defined in the PDF)
    handle_map = {
        0: "pull_9_back_to_back", 1: "pull_9_exterior", 2: "pull_9_interior",
        3: "pull_12_back_to_back", 4: "pull_12_exterior",
        5: "pull_12_interior",     6: "push_bar_tubular",
        # 7: "supply_install" (not persisted on Hardware model)
    }
    for i, k in handle_map.items():
        hw[k] = _cbox(fields, f"handle_{i}")

    # Locks — lock_main_0..7
    lock_map = {
        0: "lock_sm_1850_ar", 1: "cylinder_exterior",
        2: None,                                # "Barillet intérieur" — not on Hardware
        3: "cylinder_interior_manual",
        4: None,                                # "Projection courte (MR)"
        5: "lock_4510_ar",
        6: "cylinder_exterior",                 # 4510 alternate cyl (OR)
        7: "lock_4590_ar",
    }
    for i, k in lock_map.items():
        if k is None:
            continue
        if _cbox(fields, f"lock_main_{i}"):
            hw[k] = True

    # Panic bars — panic_0..5
    hw["panic_8400_ar"] = _cbox(fields, "panic_0")
    hw["panic_8600_ar"] = _cbox(fields, "panic_1")
    if _cbox(fields, "panic_2") or _cbox(fields, "panic_3"):
        hw["cylinder_exterior"] = True
    if _cbox(fields, "panic_5"):
        hw["cylinder_interior_manual"] = True

    # Strikes & protectors
    hw["strike_standard"]    = _cbox(fields, "strike_0")
    hw["strike_electric"]    = _cbox(fields, "strike_1")
    hw["contact_recessed"]   = _cbox(fields, "strike_2")
    hw["bolt_protector"]     = _cbox(fields, "strike_3")
    hw["cylinder_protector"] = _cbox(fields, "strike_4")

    # Others (astragal / flush bolts / sweep / mouldings)
    hw["astragal"]        = _cbox(fields, "other_0")
    hw["flush_bolts"]     = _cbox(fields, "other_1")
    hw["door_sweep"]      = _cbox(fields, "other_2")
    hw["moulding_thermo"] = _cbox(fields, "other_3")
    hw["moulding_simple"] = _cbox(fields, "other_4")
    # Glazing hint from moulding checkbox
    if hw["moulding_thermo"]:
        for d in doors:
            d["glazing"] = "thermos"
    elif hw["moulding_simple"]:
        for d in doors:
            d["glazing"] = "simple"

    # Sill / threshold
    hw["sill_supplied"]      = _cbox(fields, "thr_supply")
    hw["sill_space_standard"] = _cbox(fields, "thr_space_yes")
    hw["sill_space_none"]    = _cbox(fields, "thr_space_no")
    thr_type = _first_tx(fields, "thr_type")
    if _cbox(fields, "thr_iso"):
        hw["sill_type_insulated"] = thr_type or "Précisé"
    if _cbox(fields, "thr_non_iso"):
        hw["sill_type_non_insulated"] = thr_type or "Précisé"

    # Attach identical hardware spec to every door
    for d in doors:
        d["hardware"] = dict(hw)

    # ─── Notes ───────────────────────────────────────────
    notes_txt = _first_tx(fields, "notes") or ""
    if email:
        notes_txt = (notes_txt + f"\nCourriel client : {email}").strip()

    return {
        "client":        client or None,
        "contact":       contact or None,
        "phone":         phone or None,
        "order_number":  order_number or None,
        "project_name":  project_name or None,
        "order_date":    order_date or None,
        "required_date": required_dt or None,
        "finish_exterior":     finish_exterior,
        "finish_interior":     finish_interior,
        "color_code_exterior": color_code_exterior or None,
        "color_code_interior": color_code_interior or None,
        "doors": doors,
        "notes": notes_txt or None,
    }
