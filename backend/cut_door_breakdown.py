"""Door breakdown — turn a single 'door panel' item into its frame pieces
+ glazing moulures (parclose) + hardware positions.

⚠ IMPORTANT — INPUT SEMANTICS:
  The two dimensions passed in are the **finished door-leaf (battant fini)**
  dimensions, i.e. the actual cut length of the rails (= leaf_width) and the
  actual cut length of the stiles (= leaf_height). NOT the rough opening.

  This matches what AT Fabrication writes on shop drawings ("porte 723.1 × 2114.5")
  and what the OCR returns in panel.width_mm × panel.length_mm.

Production models (rails / stiles widths confirmed by Portech, 2026-05):
  - AT1000  : non-insulated, 2¼" (55.5 mm) rails + stiles, 6mm or 25mm glass
  - AT2000  : non-insulated, asymmetric — tête 3⅞" (98.425), base 6⅞" (174.625),
              jambage charnière 3½" (88.9), jambage serrure 3⅝" (92.075)
  - ATi1000 : insulated (thermal break), 2¼" sections, 25mm glass only
  - ATi2000 : insulated, asymmetric (same as AT2000), 25mm glass only
  - AT1000-base-AT2000 (hybrid) : AT1000 top + stiles, AT2000 base 6⅞"

Parclose (moulure) for 1/4" carré vitrage : face profile = 13.48 mm.
Mitred at corners → horizontal moulures span the FULL leaf width
                  → vertical moulures = leaf_height - top_rail - base - 2 × face
"""
from dataclasses import dataclass
from typing import List, Optional
from uuid import uuid4

# ===========================================================================
# Per-series profile geometry
# ===========================================================================

# ----- Top rail height (mm) -----
# AT1000/ATi1000: 2¼" (ATT1005)
# AT2000/ATi2000: 3⅞" (uses the AT1000 base profile = part "AT1000")
TOP_RAIL_HEIGHT_MM = {
    "AT1000": 55.5,
    "AT2000": 98.425,   # 3⅞" — same physical profile as AT1000 base ("AT1000")
    "ATI1000": 55.5,
    "ATI2000": 98.425,
    "AT1000-BASE-AT2000": 55.5,
}

# ----- Bottom rail height (mm) -----
# AT1000/ATi1000: 3⅞" (part "AT1000")  ← CORRECTED 2026-05 from 2¼" to 3⅞"
# AT2000/ATi2000: 6⅞" (part "AT2000")
BASE_RAIL_HEIGHT_MM = {
    "AT1000": 98.425,   # 3⅞" — part "AT1000"
    "AT2000": 174.625,  # 6⅞" — part "AT2000"
    "ATI1000": 98.425,
    "ATI2000": 174.625,
    "AT1000-BASE-AT2000": 174.625,  # hybrid: AT2000 base on AT1000 body
}

# ----- Hinge-side stile width (mm) — "jambage charnière" -----
HINGE_STILE_WIDTH_MM = {
    "AT1000": 50.8,     # 2" — part AT1025
    "AT2000": 88.9,     # 3½" — part AT2025
    "ATI1000": 50.8,
    "ATI2000": 88.9,
    "AT1000-BASE-AT2000": 50.8,
}

# ----- Lock-side stile width (mm) — "jambage serrure" -----
LOCK_STILE_WIDTH_MM = {
    "AT1000": 53.975,   # 2⅛" — part AT1020
    "AT2000": 92.075,   # 3⅝" — part AT2020
    "ATI1000": 53.975,
    "ATI2000": 92.075,
    "AT1000-BASE-AT2000": 53.975,
}

# ----- AT Fabrication part numbers per profile slot per series -----
# Codes verified against the official Hydro Extrusion DXF (Jun 2026).
# Same physical extrusion can be reused across series — e.g. the AT2000 head
# is the same extrusion as the AT1000 base (both 3⅞"), so both reference
# part_number "ATB1000" (Hydro MH80476).
PART_NUMBERS = {
    "AT1000":      {"top": "ATT1005", "base": "ATB1000", "hinge": "ATV1010", "lock": "ATV1015"},
    "AT2000":      {"top": "ATB1000", "base": "ATB2000", "hinge": "ATV2010", "lock": "ATV2015"},
    "ATI1000":     {"top": "ATT1005", "base": "ATB1000", "hinge": "ATV1010", "lock": "ATV1015",
                     "clad_v": "ATCV1030", "clad_h": "ATCHA1035"},
    "ATI2000":     {"top": "ATB1000", "base": "ATB2000", "hinge": "ATV2010", "lock": "ATV2015",
                     "clad_v": "ATCV2030", "clad_h": "ATCHA1035"},
    "AT1000-BASE-AT2000": {"top": "ATT1005", "base": "ATB2000", "hinge": "ATV1010", "lock": "ATV1015"},
}

# ----- Parclose (moulure) face width per glass type -----
# Both moulures can be used on ANY door series — the choice depends entirely
# on the GLASS the customer ordered:
#   • Verre simple 6 mm     → moulure CARRÉE 13.48 (AT1045) — comble la rainure
#   • Thermos 25.4 mm        → moulure PLATE  14.3  (AT1050) — le thermos remplit la rainure
PARCLOSE_FACE_BY_GLASS_MM = {
    6.0:  {"face": 13.48, "shape": "carrée", "part_number": "AT1045",
           "label_suffix": "carrée AT1045 (verre simple 6 mm)"},
    25.4: {"face": 14.3,  "shape": "plate", "part_number": "AT1050",
           "label_suffix": "plate AT1050 (thermos 25.4 mm)"},
}
MOULURE_FACE_WIDTH_MM = 13.48  # Legacy default kept for back-compat in tests.

# Lousse (tolérance de coupe) retranché de la LARGEUR du vitrage seulement :
# le verre/thermos est coupé 2 mm plus étroit par porte (portes simples ET
# chaque battant des paires). Doit rester identique à GLASS_WIDTH_LOUSSE_MM
# dans erp_pdf_production.py (plans de production).
GLASS_WIDTH_LOUSSE_MM = 2.0

# Cladding piece (ATi insulated only) — clad pieces are 5.7 mm shorter on each
# axis than the leaf itself (per official AT DXF).
CLADDING_OFFSET_MM = 5.7

# ===========================================================================
# Hardware position rules (mm from BOTTOM of door leaf)
# ===========================================================================
DEFAULT_CYL_HEIGHT_MM = 1016.0       # 40"
DEFAULT_STRIKE_OFFSET_MM = 19.05     # 3/4" lower than cylinder on jamb
DEFAULT_HANDLE_HEIGHT_MM = 876.3     # 34½"
HINGE_BOTTOM_UNDERCUT_MM = 6.35      # 1/4" cut at bottom of continuous hinge


@dataclass
class DoorBreakdown:
    items: List[dict]
    hardware: List[dict]
    notes: List[str]


def _normalize_series(raw: str) -> str:
    """Map any user-supplied series string to a canonical key in the spec tables."""
    s = (raw or "").upper().replace(" ", "").replace("_", "")
    # Hybrid first (must check BEFORE plain AT1000/AT2000 matches)
    if ("AT1000" in s.replace("-", "") and "AT2000" in s.replace("-", "")) \
            or "BASEAT2000" in s.replace("-", ""):
        return "AT1000-BASE-AT2000"
    s = s.replace("-", "")
    if "ATI2000" in s:
        return "ATI2000"
    if "ATI1000" in s:
        return "ATI1000"
    if "AT2000" in s:
        return "AT2000"
    return "AT1000"


def decompose_at_door(
    leaf_width_mm: float,
    leaf_height_mm: float,
    series: str = "AT1000",
    glass_thickness_mm: float = 6.0,
    material: str = "Aluminium anodisé bronze",
    label_prefix: str = "Porte",
    qty: int = 1,
    hardware_rules: Optional[dict] = None,
) -> DoorBreakdown:
    """Decompose a finished door leaf into its cut pieces.

    Args:
        leaf_width_mm:  Finished width of the leaf = length of each rail (mm).
        leaf_height_mm: Finished height of the leaf = length of each stile (mm).

    Formulas (validated by Portech 2026-05):
        rail_cut    = leaf_width_mm                            (×2: top + bottom)
        stile_cut   = leaf_height_mm                           (×2: hinge + lock)
        moulure_V   = leaf_height − top_rail − base − 2 × moulure_face   (×4)
        moulure_H   = leaf_width                               (×4, mitred 45°)
        vitrage     = (rail_cut − stiles_widths) × (stile_cut − rails_heights)

    Example (AT2000, leaf 723.1 × 2114.5, 6mm glass) :
        rail_cut  = 723.10
        stile_cut = 2114.50
        moulure_V = 2114.5 − 98.425 − 174.625 − 26.96 = 1814.49
        moulure_H = 723.10
    """
    notes: list[str] = []
    series_key = _normalize_series(series)

    top_rail = TOP_RAIL_HEIGHT_MM[series_key]
    base_rail = BASE_RAIL_HEIGHT_MM[series_key]
    hinge_stile = HINGE_STILE_WIDTH_MM[series_key]
    lock_stile = LOCK_STILE_WIDTH_MM[series_key]

    # Parclose face width depends on the glass thickness :
    #   • verre 6 mm           → moulure carrée 13.48 mm (comble la rainure de 25.4 mm)
    #   • verre 25.4 mm thermos → moulure plate 14.3 mm (le thermos remplit lui-même la rainure)
    parclose_spec = PARCLOSE_FACE_BY_GLASS_MM.get(
        round(glass_thickness_mm, 1),
        {"face": MOULURE_FACE_WIDTH_MM, "shape": "carrée",
         "label_suffix": f"carrée vitrage {glass_thickness_mm:.1f}mm"},
    )
    moulure_face = parclose_spec["face"]
    moulure_shape = parclose_spec["shape"]
    parclose_label_suffix = parclose_spec["label_suffix"]
    parclose_part_number = parclose_spec.get("part_number")
    parts = PART_NUMBERS[series_key]

    # ----- Cut lengths -----
    rail_cut = leaf_width_mm
    stile_cut = leaf_height_mm
    moulure_v = stile_cut - top_rail - base_rail - 2 * moulure_face
    moulure_h = leaf_width_mm  # mitred 45° → spans full leaf width

    # Largeur RÉELLE du vitrage = largeur battant − 2 montants − 2 parcloses V
    # − lousse (2 mm). Le lousse s'applique UNIQUEMENT en largeur, par porte /
    # par battant (decompose est appelé une fois par battant sur les paires).
    glass_width_mm = moulure_h - hinge_stile - lock_stile - 2 * moulure_face - GLASS_WIDTH_LOUSSE_MM

    is_insulated = series_key.startswith("ATI")
    is_hybrid = series_key == "AT1000-BASE-AT2000"
    is_at2000_family = series_key in ("AT2000", "ATI2000")

    # ----- Profile labels (top vs bottom can differ on hybrid) -----
    if is_at2000_family:
        profile_top = f'{series_key} — tête 3⅞" (98.4 mm)'
        profile_bottom = f'{series_key} — base 6⅞" (174.6 mm)'
        profile_stile_hinge = f'{series_key} — jambage charnière 3½" (88.9 mm)'
        profile_stile_lock = f'{series_key} — jambage serrure 3⅝" (92.1 mm)'
    elif is_hybrid:
        profile_top = f'{series_key} — tête 2¼" (55.5 mm)'
        profile_bottom = f'{series_key} — base 6⅞" (substitution AT2000)'
        profile_stile_hinge = f'{series_key} — jambage 2¼"'
        profile_stile_lock = f'{series_key} — jambage 2¼"'
    else:  # AT1000 / ATi1000
        profile_top = f'{series_key} — tube 2¼" (55.5 mm)'
        profile_bottom = profile_top
        profile_stile_hinge = profile_top
        profile_stile_lock = profile_top

    items = [
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Traverse haute (tête)",
            "profile": profile_top, "material": material,
            "part_number": parts["top"], "manufacturer": "AT Fabrication",
            "length_mm": round(rail_cut, 2), "qty": qty, "source": "computed",
            "notes": f"Largeur battant {leaf_width_mm:.1f} mm. Pièce {parts['top']}.",
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Traverse basse (base)",
            "profile": profile_bottom, "material": material,
            "part_number": parts["base"], "manufacturer": "AT Fabrication",
            "length_mm": round(rail_cut, 2), "qty": qty, "source": "computed",
            "notes": (
                f"Base {base_rail:.1f} mm — pièce {parts['base']}."
                if is_hybrid or is_at2000_family else
                f"Base 3⅞\" ({base_rail:.1f} mm) — pièce {parts['base']} "
                "(même extrusion que la tête AT2000)."
            ),
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Montant côté charnière",
            "profile": profile_stile_hinge, "material": material,
            "part_number": parts["hinge"], "manufacturer": "AT Fabrication",
            "length_mm": round(stile_cut, 2), "qty": qty, "source": "computed",
            "notes": (
                f"Hauteur battant {leaf_height_mm:.1f} mm. Largeur montant {hinge_stile} mm. "
                f"Pièce {parts['hinge']}."
            ),
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Montant côté serrure",
            "profile": profile_stile_lock, "material": material,
            "part_number": parts["lock"], "manufacturer": "AT Fabrication",
            "length_mm": round(stile_cut, 2), "qty": qty, "source": "computed",
            "notes": f"Largeur montant {lock_stile} mm. Pièce {parts['lock']}.",
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Parclose verticale ({parclose_label_suffix})",
            "profile": f"{series_key} — parclose {moulure_shape} {moulure_face} mm",
            "material": material,
            "part_number": parclose_part_number, "manufacturer": "AT Fabrication",
            "length_mm": round(moulure_v, 2),
            "qty": 4 * qty, "source": "computed",
            "notes": (
                f"4 par porte. Pièce {parclose_part_number or '—'}. Calc : "
                f"{leaf_height_mm:.1f} − {top_rail} (tête) − "
                f"{base_rail} (base) − 2 × {moulure_face} = {moulure_v:.2f} mm. "
                f"Moulure {moulure_shape} pour verre {glass_thickness_mm:.1f}mm. Coupes mitrées 45°."
            ),
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Parclose horizontale ({parclose_label_suffix})",
            "profile": f"{series_key} — parclose {moulure_shape} {moulure_face} mm",
            "material": material,
            "part_number": parclose_part_number, "manufacturer": "AT Fabrication",
            "length_mm": round(moulure_h, 2),
            "qty": 4 * qty, "source": "computed",
            "notes": (
                f"4 par porte. Pièce {parclose_part_number or '—'}. "
                f"Calc : moulure_H = largeur battant = {leaf_width_mm:.1f} mm "
                f"(mitré 45° → s'étend sur toute la largeur). Moulure {moulure_shape} "
                f"({moulure_face} mm) pour verre {glass_thickness_mm:.1f}mm."
            ),
        },
        {
            "id": str(uuid4()), "item_type": "glass",
            "label": f"{label_prefix} — Vitrage",
            "material": f"Verre {'thermos' if glass_thickness_mm >= 12 else 'trempé'} {glass_thickness_mm:.1f}mm",
            "length_mm": round(moulure_v, 2),
            "width_mm": round(glass_width_mm, 2),
            "thickness_mm": glass_thickness_mm,
            "qty": qty, "source": "computed",
            "notes": (
                "Largeur vitrage = largeur battant − 2 montants − 2 parcloses "
                f"verticales − lousse {GLASS_WIDTH_LOUSSE_MM:.0f} mm (tolérance de coupe)."
            ),
        },
    ]

    # ----- ATi cladding (revêtement extérieur posé sur la porte isolée) -----
    if is_insulated:
        cladding_v = stile_cut - CLADDING_OFFSET_MM
        cladding_h = rail_cut - CLADDING_OFFSET_MM
        items.extend([
            {
                "id": str(uuid4()), "item_type": "frame",
                "label": f"{label_prefix} — Cladding vertical (revêtement)",
                "profile": f"{series_key} — cladding vertical",
                "material": material,
                "part_number": parts.get("clad_v"), "manufacturer": "AT Fabrication",
                "length_mm": round(cladding_v, 2),
                "qty": 2 * qty, "source": "computed",
                "notes": (
                    f"Pièce {parts.get('clad_v')}. Calc : stile {stile_cut:.1f} − "
                    f"{CLADDING_OFFSET_MM} = {cladding_v:.1f}. 2 par porte (extérieur + intérieur)."
                ),
            },
            {
                "id": str(uuid4()), "item_type": "frame",
                "label": f"{label_prefix} — Cladding horizontal (revêtement)",
                "profile": f"{series_key} — cladding horizontal",
                "material": material,
                "part_number": parts.get("clad_h"), "manufacturer": "AT Fabrication",
                "length_mm": round(cladding_h, 2),
                "qty": 2 * qty, "source": "computed",
                "notes": (
                    f"Pièce {parts.get('clad_h')}. Calc : rail {rail_cut:.1f} − "
                    f"{CLADDING_OFFSET_MM} = {cladding_h:.1f}."
                ),
            },
        ])

    # ----- Hardware positions (from bottom of door leaf) -----
    rules = hardware_rules or {}
    cyl_h = rules.get("cylinder_height_mm", DEFAULT_CYL_HEIGHT_MM)
    strike_off = rules.get("strike_offset_mm", DEFAULT_STRIKE_OFFSET_MM)
    handle_h = rules.get("handle_height_mm", DEFAULT_HANDLE_HEIGHT_MM)
    hardware = [
        {
            "id": str(uuid4()), "item_type": "hole",
            "label": "Perçage cylindre / serrure MS",
            "length_mm": 0, "qty": qty,
            "position_y": round(cyl_h, 1),
            "notes": f"Centré à {cyl_h:.0f} mm du bas, montant côté serrure.",
            "source": "computed",
        },
        {
            "id": str(uuid4()), "item_type": "hole",
            "label": "Machinage gâche (cadre)",
            "length_mm": 0, "qty": qty,
            "position_y": round(cyl_h + strike_off, 1),
            "notes": f"3/4\" plus bas que le cylindre — à {cyl_h + strike_off:.0f} mm sur montant vertical du cadre.",
            "source": "computed",
        },
        {
            "id": str(uuid4()), "item_type": "hole",
            "label": "Poignée / paddle / push bar",
            "length_mm": 0, "qty": qty,
            "position_y": round(handle_h, 1),
            "notes": f"Centré à {handle_h:.0f} mm du bas (34½\").",
            "source": "computed",
        },
        {
            "id": str(uuid4()), "item_type": "hardware",
            "label": "Charnière continue — installation",
            "length_mm": round(stile_cut - HINGE_BOTTOM_UNDERCUT_MM, 2),
            "qty": qty,
            "notes": "Flush sommet, coupée à 1/4\" du bas (dégagement seuil).",
            "source": "computed",
        },
    ]

    summary_parts = [
        f"Porte {series_key} (battant {leaf_width_mm:.1f}×{leaf_height_mm:.1f} mm, "
        f"verre {glass_thickness_mm:.1f}mm{' — isolée avec cladding' if is_insulated else ''})",
        f"2 rails {rail_cut:.1f} + 2 montants {stile_cut:.1f}",
        f"4 parcloses V {moulure_v:.1f} + 4 parcloses H {moulure_h:.1f}",
        "1 vitrage",
    ]
    if is_insulated:
        summary_parts.append(
            f"+ 2 cladding V {stile_cut - CLADDING_OFFSET_MM:.0f} + 2 cladding H {rail_cut - CLADDING_OFFSET_MM:.0f}"
        )
    notes.append(" — ".join(summary_parts))
    return DoorBreakdown(items=items, hardware=hardware, notes=notes)
