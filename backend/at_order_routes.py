"""AT Fabrication order ingestion + shop-drawing PDF generation.

Pipeline:
  1. User uploads the AT Fabrication "FORMULAIRE POUR COMMANDE DE PORTE" PDF.
  2. We send it to Gemini Vision (via emergentintegrations) with a strict JSON
     schema → returns a parsed `ATDoorOrder` model.
  3. User reviews / edits the data in the UI.
  4. User saves it (POST /at-orders) and / or downloads a 3-page shop drawing.

Phase 1 scope (per user decision): AT1000 / ATi1000 / AT2000 / ATi2000 doors
ONLY. No curtain walls, no flush glaze, no architectural surrounds.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal

from emergentintegrations.llm.chat import FileContentWithMimeType, LlmChat, UserMessage
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from at_order_pdf import render_shop_drawing_pdf
from cut_door_breakdown import decompose_at_door
from cut_models import CutList, CutItem

logger = logging.getLogger("portech.at_orders")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
OCR_MODEL = os.environ.get("EXPENSE_OCR_MODEL", "gemini-3-flash-preview")
UPLOAD_DIR = Path("/tmp/at_orders_upload")
UPLOAD_DIR.mkdir(exist_ok=True)


# ===========================================================================
# Pydantic schema — what we extract / persist for each order
# ===========================================================================
SeriesT = Literal["AT1000", "ATi1000", "AT2000", "ATi2000"]
GlazingT = Literal["thermos", "simple", "none", "unknown"]
HandT = Literal["GE", "DE", "PE", "GI", "DI", "PI", "unknown"]  # gauche/droite/paire ext/int


class Hardware(BaseModel):
    """Checkboxes from the form, ATTACHED TO A SPECIFIC DOOR (one Hardware
    instance per DoorLine since v2 — was global previously). When the form is
    parsed, the OCR fills the hardware on the first door; the admin can then
    spread / customize hardware per door in the UI."""
    # Hinges
    hinge_4_5x4: bool = False
    hinge_4_5x4_qty: int | None = None              # 2 / 3 / 4
    hinge_continuous: bool = False
    hinge_continuous_hd: bool = False
    # Handles / pulls (9" and 12")
    pull_9_back_to_back: bool = False
    pull_9_exterior: bool = False
    pull_9_interior: bool = False
    pull_12_back_to_back: bool = False
    pull_12_exterior: bool = False
    pull_12_interior: bool = False
    push_bar_tubular: bool = False
    # Locks
    lock_4510_ar: bool = False
    lock_4590_ar: bool = False
    lock_sm_1850_ar: bool = False
    panic_8400_ar: bool = False
    panic_8600_ar: bool = False
    cylinder_exterior: bool = False
    cylinder_interior_manual: bool = False
    cylinder_protector: bool = False
    bolt_protector: bool = False
    strike_standard: bool = False
    strike_electric: bool = False
    contact_recessed: bool = False
    # Other
    astragal: bool = False
    flush_bolts: bool = False
    door_sweep: bool = False
    moulding_thermo: bool = False                    # AT1050 plate 14.3
    moulding_simple: bool = False                    # AT1045 carrée 13.48
    # Sill
    sill_supplied: bool = False
    sill_type_insulated: str | None = None
    sill_type_non_insulated: str | None = None
    sill_space_standard: bool = False
    sill_space_none: bool = False


class DoorLine(BaseModel):
    """One physical door / leaf in the order. Most orders contain 1-4 lines.
    Each door carries its OWN hardware spec so the shop can tell at a glance
    which hardware goes on which door (was a single global hardware before)."""
    tag: str | None = None                          # e.g. "P-100"
    series: SeriesT = "AT1000"
    width_in: float = Field(..., gt=0, description="Largeur du battant en pouces")
    height_in: float = Field(..., gt=0, description="Hauteur du battant en pouces")
    qty: int = Field(default=1, ge=1)
    hand: HandT = "unknown"
    glazing: GlazingT = "unknown"                   # thermos / simple
    hardware: Hardware = Field(default_factory=Hardware)
    notes: str | None = None


class ATDoorOrder(BaseModel):
    """Top-level order. Saved as one document in db.at_door_orders."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    # Client / project
    client: str | None = None
    contact: str | None = None
    phone: str | None = None
    order_number: str | None = None                  # ex: BAJ001463
    project_name: str | None = None                  # ex: A26P1079
    order_date: str | None = None                    # ISO yyyy-mm-dd
    required_date: str | None = None
    # Finishes
    finish_exterior: str | None = None
    finish_interior: str | None = None
    color_code_exterior: str | None = None
    color_code_interior: str | None = None
    # Doors (each one carries its own hardware spec)
    doors: list[DoorLine] = Field(default_factory=list)
    # Legacy: top-level hardware persisted by v1 orders. Kept optional so we
    # can read v1 orders, but new orders should put hardware on each DoorLine.
    hardware: Hardware | None = None
    # Free text
    notes: str | None = None
    # Audit
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ===========================================================================
# Gemini OCR system prompt
# ===========================================================================
OCR_SYSTEM = (
    "Tu es un OCR spécialisé sur le formulaire 'FORMULAIRE POUR COMMANDE DE "
    "PORTE (VERSION 1)' d'AT Fabrication. Tu extrais TOUS les champs et tu "
    "renvoies UN SEUL OBJET JSON conforme au schéma fourni. AUCUN texte hors JSON.\n"
    "\n"
    "Règles d'extraction :\n"
    "1. Le formulaire contient des CASES À COCHER. Tu dois reconnaître si une "
    "case est cochée (✓, x, ●) ou vide. Renvoie un boolean true/false.\n"
    "2. Les dimensions des portes sont en POUCES (ex: 36\" X 84\"). Renvoie "
    "width_in et height_in en pouces décimaux (36, 84, 35.5).\n"
    "3. La SÉRIE de porte vient des cases 'PORTE NON-ISOLÉE SÉRIE AT1000', "
    "'PORTE ISOLÉE SÉRIE ATi1000', 'PORTE NON-ISOLÉE SÉRIE AT2000', "
    "'PORTE ISOLÉE SÉRIE ATi2000'. Renvoie EXACTEMENT 'AT1000' / 'ATi1000' / "
    "'AT2000' / 'ATi2000'.\n"
    "4. Le sens d'ouverture est codé GE (gauche ext.), DE (droite ext.), "
    "PE (paire ext.), GI / DI / PI (intérieur). Renvoie le code exact.\n"
    "5. Le type de verre se déduit des cases 'MOULURE THERMO' (=thermos) ou "
    "'MOULURE VITRAGE SIMPLE' (=simple). Si aucune cochée → unknown.\n"
    "6. Si une porte a plusieurs TAGs séparés par '/' (ex: 'P-100/P-100.G'), "
    "crée une seule ligne `doors` avec le tag combiné.\n"
    "7. La QUINCAILLERIE doit être attachée à chaque porte. Si le formulaire "
    "n'indique qu'une seule colonne de cases à cocher pour TOUTES les portes, "
    "DUPLIQUE la même quincaillerie pour chaque ligne `doors`. Si le "
    "formulaire a une colonne par TAG, attribue la quincaillerie spécifique "
    "à la bonne porte.\n"
    "8. AJOUTE les poignées 12\" si tu vois 'POIGNÉE 12' ou similaire.\n"
)

OCR_USER = (
    "Voici le bon de commande AT Fabrication. Extrait toutes les informations.\n"
    "\n"
    "Schéma JSON attendu :\n"
    "{\n"
    '  "client": str|null, "contact": str|null, "phone": str|null,\n'
    '  "order_number": str|null, "project_name": str|null,\n'
    '  "order_date": str|null, "required_date": str|null,\n'
    '  "finish_exterior": str|null, "finish_interior": str|null,\n'
    '  "color_code_exterior": str|null, "color_code_interior": str|null,\n'
    '  "doors": [\n'
    '    {"tag": str|null, "series": "AT1000"|"ATi1000"|"AT2000"|"ATi2000",\n'
    '     "width_in": float, "height_in": float, "qty": int,\n'
    '     "hand": "GE"|"DE"|"PE"|"GI"|"DI"|"PI"|"unknown",\n'
    '     "glazing": "thermos"|"simple"|"unknown",\n'
    '     "hardware": { all hardware fields below, attached to THIS door },\n'
    '     "notes": str|null}\n'
    "  ],\n"
    '  "notes": str|null\n'
    "}\n"
    "\n"
    "Champs hardware (booleans sauf indication) :\n"
    "  hinge_4_5x4, hinge_4_5x4_qty (int), hinge_continuous, hinge_continuous_hd,\n"
    "  pull_9_back_to_back, pull_9_exterior, pull_9_interior,\n"
    "  pull_12_back_to_back, pull_12_exterior, pull_12_interior, push_bar_tubular,\n"
    "  lock_4510_ar, lock_4590_ar, lock_sm_1850_ar, panic_8400_ar, panic_8600_ar,\n"
    "  cylinder_exterior, cylinder_interior_manual, cylinder_protector, bolt_protector,\n"
    "  strike_standard, strike_electric, contact_recessed,\n"
    "  astragal, flush_bolts, door_sweep, moulding_thermo, moulding_simple,\n"
    "  sill_supplied, sill_type_insulated (str), sill_type_non_insulated (str),\n"
    "  sill_space_standard, sill_space_none\n"
    "\n"
    "AUCUN texte hors du JSON. Pas de ```json. Pas d'explication."
)


def _strip_json_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _migrate_v1_hardware(data: dict) -> dict:
    """If hardware was provided at the top level (v1) but not on each door,
    copy it to every door. If a door already has its own hardware, keep it."""
    top_hw = data.get("hardware") or None
    doors = data.get("doors") or []
    if not top_hw or not doors:
        return data
    for d in doors:
        if not d.get("hardware"):
            d["hardware"] = dict(top_hw)
    return data


async def _ocr_at_order(file_path: Path, mime: str) -> dict:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "EMERGENT_LLM_KEY non configurée — OCR indisponible.")
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"at-order-{uuid.uuid4().hex[:8]}",
        system_message=OCR_SYSTEM,
    ).with_model("gemini", OCR_MODEL)
    msg = UserMessage(
        text=OCR_USER,
        file_contents=[FileContentWithMimeType(file_path=str(file_path), mime_type=mime)],
    )
    raw = await chat.send_message(msg)
    raw_text = raw if isinstance(raw, str) else str(raw)
    try:
        return json.loads(_strip_json_fence(raw_text))
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw_text)
        if not m:
            raise HTTPException(502, "Réponse OCR invalide (JSON non parseable).")
        return json.loads(m.group(0))


# ===========================================================================
# Router
# ===========================================================================
def build_at_order_router(*, auth_dep, get_db) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["at-orders"])

    async def _coll(db: AsyncIOMotorDatabase):
        return db.at_door_orders

    def _ts() -> datetime:
        return datetime.now(timezone.utc)

    @router.post("/at-orders/parse", status_code=200)
    async def parse_pdf(file: UploadFile = File(...),
                         _: dict = Depends(auth_dep)):
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, "Un PDF est requis.")
        # Persist the upload locally so Gemini Vision can read it.
        upload_id = uuid.uuid4().hex[:12]
        path = UPLOAD_DIR / f"{upload_id}.pdf"
        contents = await file.read()
        if len(contents) > 12 * 1024 * 1024:
            raise HTTPException(413, "PDF trop volumineux (>12 Mo).")
        path.write_bytes(contents)
        try:
            data = await _ocr_at_order(path, "application/pdf")
            data = _migrate_v1_hardware(data)
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        # Validate via Pydantic — fills defaults, coerces types, removes junk.
        try:
            order = ATDoorOrder(**data)
        except Exception as e:
            logger.warning("ATDoorOrder validation failed: %s", e)
            raise HTTPException(502, f"OCR retournait des données invalides : {e}")
        return order.model_dump(mode="json")

    @router.post("/at-orders", status_code=201)
    async def save_order(order: ATDoorOrder,
                          _: dict = Depends(auth_dep),
                          db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _coll(db)
        order.updated_at = _ts()
        doc = order.model_dump(mode="json")
        await coll.insert_one(doc)
        return {k: v for k, v in doc.items() if k != "_id"}

    @router.get("/at-orders")
    async def list_orders(_: dict = Depends(auth_dep),
                           db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _coll(db)
        rows = await coll.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"orders": rows}

    @router.get("/at-orders/{order_id}")
    async def get_order(order_id: str,
                         _: dict = Depends(auth_dep),
                         db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _coll(db)
        row = await coll.find_one({"id": order_id}, {"_id": 0})
        if not row:
            raise HTTPException(404, "Commande introuvable.")
        return row

    @router.patch("/at-orders/{order_id}")
    async def update_order(order_id: str, order: ATDoorOrder,
                            _: dict = Depends(auth_dep),
                            db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _coll(db)
        order.id = order_id
        order.updated_at = _ts()
        result = await coll.update_one({"id": order_id},
                                        {"$set": order.model_dump(mode="json")})
        if not result.matched_count:
            raise HTTPException(404, "Commande introuvable.")
        return await coll.find_one({"id": order_id}, {"_id": 0})

    @router.delete("/at-orders/{order_id}", status_code=204)
    async def delete_order(order_id: str,
                            _: dict = Depends(auth_dep),
                            db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _coll(db)
        await coll.delete_one({"id": order_id})
        return Response(status_code=204)

    @router.post("/at-orders/shop-drawing.pdf")
    async def shop_drawing_from_payload(order: ATDoorOrder,
                                         _: dict = Depends(auth_dep)):
        """Stateless: generate a PDF from the posted order WITHOUT saving."""
        pdf = render_shop_drawing_pdf(order.model_dump(mode="json"))
        suffix = (order.order_number or order.id or "atorder")[:32]
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="plan-atelier-{suffix}.pdf"'},
        )

    @router.get("/at-orders/{order_id}/shop-drawing.pdf")
    async def shop_drawing_from_saved(order_id: str,
                                       _: dict = Depends(auth_dep),
                                       db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _coll(db)
        row = await coll.find_one({"id": order_id}, {"_id": 0})
        if not row:
            raise HTTPException(404, "Commande introuvable.")
        pdf = render_shop_drawing_pdf(row)
        suffix = (row.get("order_number") or order_id)[:32]
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="plan-atelier-{suffix}.pdf"'},
        )

    @router.post("/at-orders/to-cut-list", status_code=201)
    async def at_order_to_cut_list(order: ATDoorOrder,
                                    _: dict = Depends(auth_dep),
                                    db: AsyncIOMotorDatabase = Depends(get_db)):
        """Convert an AT order (posted, not necessarily saved) into a new
        ERP Cut List. Each door is decomposed into its frame pieces (head,
        base, hinge stile, lock stile, parclose V/H) using the same
        deterministic logic as the Cut List ERP module.

        Returns the newly created cut_list { id, name, items_count } so the
        frontend can either redirect the user or show a confirmation toast."""
        if not order.doors:
            raise HTTPException(400, "Aucune porte dans la commande — impossible de créer une liste de coupe.")

        all_items: list[CutItem] = []
        notes_lines: list[str] = []
        material = "Aluminium AT Fabrication"
        if order.finish_exterior:
            material += f" — fini ext. {order.finish_exterior}"

        for idx, d in enumerate(order.doors, start=1):
            leaf_w_in = d.width_in
            leaf_h_in = d.height_in
            # AT order width/height are the rough opening dimensions in inches.
            # Convert to leaf finish dimensions (apply standard offsets per series).
            # We use the SAME offsets baked in profile_catalog SYSTEMS — but for
            # simplicity we apply the same formula here.
            from profile_catalog import SYSTEMS  # local import to avoid cycle
            sys_def = next((s for s in SYSTEMS if s.get("system") == d.series), None)
            offsets = (sys_def or {}).get("offsets_mm") or {"width": 115.10, "height": 22.20}

            rough_w_mm = leaf_w_in * 25.4
            rough_h_mm = leaf_h_in * 25.4
            leaf_w_mm = rough_w_mm - offsets["width"]
            leaf_h_mm = rough_h_mm - offsets["height"]

            glass_mm = 25.4 if d.glazing == "thermos" else 6.0
            label_prefix = f"{d.tag or f'D{idx}'} — {d.series}"

            bd = decompose_at_door(
                leaf_width_mm=leaf_w_mm,
                leaf_height_mm=leaf_h_mm,
                series=d.series,
                glass_thickness_mm=glass_mm,
                material=material,
                label_prefix=label_prefix,
                qty=d.qty,
            )
            # Mark every line as coming from this AT order
            for raw in bd.items:
                raw["source"] = "at_order"
                all_items.append(CutItem(**raw))
            if bd.notes:
                notes_lines.append(f"[{label_prefix}] " + " · ".join(bd.notes))

        # Build the cut list
        name = f"Plan d'atelier AT — {order.order_number or order.project_name or 'sans-num'}"
        notes_lines.insert(0,
            f"Source : Commande AT Fabrication {order.order_number or ''} "
            f"— Projet {order.project_name or ''} — Client {order.client or ''}".strip())
        cut = CutList(
            name=name,
            project_ref=order.project_name,
            customer_name=order.client,
            items=all_items,
            source_filename=f"at-order-{order.order_number or order.id}",
            source_type="at_order",
            notes="\n".join(notes_lines),
        )
        await db.erp_cut_lists.insert_one(cut.model_dump())
        return {
            "id": cut.id,
            "name": cut.name,
            "items_count": len(cut.items),
        }

    return router
