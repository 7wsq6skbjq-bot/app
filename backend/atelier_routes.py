"""Aluminum bar inventory + cut-confirmation flow + labels PDF.

Three closely-related features that share the same data domain:

1. **alu_inventory**: a stock of unused bars + saved chutes (off-cuts), grouped
   by `profile_key` (typically the part_number or 'Manufacturer SYSTEM Profile').
   Each row: { id, profile_key, label, bar_length_mm, qty_available, is_chute,
              parent_cut_list_id?, created_at }.

2. **Cut confirmation flow**: a cut list can have status 'draft' (default)
   or 'cut'. When the user clicks "Confirmer coupes effectuées", we:
     - flip cut_status to 'cut' + record cuts_confirmed_at
     - DEDUCT the bars consumed by the optimizer plan from inventory
     - ADD remaining chutes (≥ 600 mm — smaller is scrap) back into inventory
     - lock the list (no more item edits via the UI)

3. **Labels PDF**: a printable sheet of Avery-5160-style adhesive labels —
   one label per cut piece, with the cut list number, qty, length, profile,
   project name. Pasted on each cut bar during assembly to prevent mix-ups.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm

logger = logging.getLogger("portech.atelier")

# Chutes shorter than this are considered scrap, not re-usable inventory.
MIN_USEFUL_CHUTE_MM = 600.0


# ===========================================================================
# Pydantic models
# ===========================================================================
class InventoryRowIn(BaseModel):
    profile_key: str = Field(..., min_length=1, max_length=120)
    label: str | None = None
    bar_length_mm: float = Field(..., gt=0)
    qty_available: int = Field(..., ge=0)
    is_chute: bool = False
    restock_threshold: int | None = Field(default=None, ge=0)


class InventoryAdjust(BaseModel):
    delta: int  # positive = add, negative = remove


# ===========================================================================
# Helpers
# ===========================================================================
def _ts() -> datetime:
    return datetime.now(timezone.utc)


async def _stock_collection(db):
    """Return the inventory MongoDB collection."""
    return db.alu_inventory


def _profile_key_for_item(item: dict) -> str:
    """Build a stable inventory key from a cut item — same logic as the
    optimizer's group key.
    Priority: part_number → profile + material → label."""
    pn = (item.get("part_number") or "").strip().lstrip("#").strip()
    if pn:
        manuf = (item.get("manufacturer") or "").strip()
        return f"{manuf} #{pn}".strip()
    profile = (item.get("profile") or "").strip()
    if profile:
        material = (item.get("material") or "").strip()
        return f"{profile} | {material}" if material else profile
    return (item.get("label") or "Inconnu")[:120]


# ===========================================================================
# Public router builder (mounted by server.py)
# ===========================================================================
def build_atelier_router(*, auth_dep, get_db) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["atelier"])

    # ─── Inventory CRUD ────────────────────────────────────────────────────
    @router.get("/alu-inventory")
    async def list_inventory(_: dict = Depends(auth_dep),
                              db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _stock_collection(db)
        rows = await coll.find({}, {"_id": 0}).sort("profile_key", 1).to_list(2000)
        # Group: full bars vs chutes for clarity
        full = [r for r in rows if not r.get("is_chute")]
        chutes = [r for r in rows if r.get("is_chute")]
        return {"bars": full, "chutes": chutes, "total_rows": len(rows)}

    @router.post("/alu-inventory", status_code=201)
    async def add_inventory(payload: InventoryRowIn,
                             _: dict = Depends(auth_dep),
                             db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _stock_collection(db)
        # Merge with existing identical row (same key + bar length + chute flag)
        existing = await coll.find_one({
            "profile_key": payload.profile_key,
            "bar_length_mm": payload.bar_length_mm,
            "is_chute": payload.is_chute,
        }, {"_id": 0})
        if existing:
            await coll.update_one(
                {"id": existing["id"]},
                {"$inc": {"qty_available": payload.qty_available},
                 "$set": {"updated_at": _ts(),
                          "restock_threshold": payload.restock_threshold or existing.get("restock_threshold")}},
            )
            return await coll.find_one({"id": existing["id"]}, {"_id": 0})
        doc = {
            "id": str(uuid.uuid4()),
            **payload.model_dump(),
            "created_at": _ts(),
            "updated_at": _ts(),
        }
        await coll.insert_one(doc)
        return {k: v for k, v in doc.items() if k != "_id"}

    @router.patch("/alu-inventory/{row_id}")
    async def adjust_inventory(row_id: str, payload: InventoryAdjust,
                                _: dict = Depends(auth_dep),
                                db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _stock_collection(db)
        row = await coll.find_one({"id": row_id}, {"_id": 0})
        if not row:
            raise HTTPException(404, "Ligne d'inventaire introuvable.")
        new_qty = max(0, int(row.get("qty_available", 0)) + payload.delta)
        await coll.update_one({"id": row_id},
                               {"$set": {"qty_available": new_qty, "updated_at": _ts()}})
        return await coll.find_one({"id": row_id}, {"_id": 0})

    @router.delete("/alu-inventory/{row_id}", status_code=204)
    async def delete_inventory(row_id: str,
                                _: dict = Depends(auth_dep),
                                db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _stock_collection(db)
        r = await coll.delete_one({"id": row_id})
        if r.deleted_count == 0:
            raise HTTPException(404, "Ligne d'inventaire introuvable.")
        return Response(status_code=204)

    # ─── Cut confirmation ──────────────────────────────────────────────────
    @router.post("/cuts/{cut_id}/confirm")
    async def confirm_cut(cut_id: str,
                           _: dict = Depends(auth_dep),
                           db: AsyncIOMotorDatabase = Depends(get_db)):
        """Mark the cut list as physically cut. Deduct bars used + add reusable
        chutes (≥ 600 mm) back to the inventory."""
        cl = await db.cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not cl:
            raise HTTPException(404, "Liste de coupe introuvable.")
        if cl.get("cut_status") == "cut":
            raise HTTPException(409, "Cette liste est déjà confirmée comme coupée.")
        opt = cl.get("last_optimization") or {}
        groups = opt.get("groups") or []
        if not groups:
            raise HTTPException(400, "Lancez l'optimisation des coupes avant de confirmer.")

        coll = await _stock_collection(db)
        bars_deducted = 0
        chutes_added = 0
        reports: list[dict] = []
        for grp in groups:
            profile_key = grp.get("profile") or "Inconnu"
            material = grp.get("material") or "—"
            plan = grp.get("plan") or {}
            bars_count = int(plan.get("bars_count") or 0)
            bar_length = float(plan.get("stock_length_mm") or 0)
            # Try to find matching stock row (same key + length, NOT a chute).
            row = await coll.find_one({
                "profile_key": profile_key,
                "bar_length_mm": bar_length,
                "is_chute": False,
            })
            if row:
                new_qty = max(0, int(row.get("qty_available", 0)) - bars_count)
                await coll.update_one({"id": row["id"]},
                                       {"$set": {"qty_available": new_qty, "updated_at": _ts()}})
                bars_deducted += bars_count
                reports.append({"profile_key": profile_key, "deducted": bars_count, "remaining": new_qty})
            else:
                reports.append({"profile_key": profile_key, "deducted": 0,
                                "warning": f"Stock non trouvé pour barre {bar_length:.0f} mm (déduction ignorée)."})

            # Add reusable chutes from each bar's leftover.
            for bar in plan.get("bars") or []:
                leftover = float(bar.get("waste_mm") or 0)
                if leftover < MIN_USEFUL_CHUTE_MM:
                    continue
                # Round leftover to nearest 10mm to limit DB row explosion
                chute_len = round(leftover / 10) * 10
                if chute_len < MIN_USEFUL_CHUTE_MM:
                    continue
                existing = await coll.find_one({
                    "profile_key": profile_key,
                    "bar_length_mm": chute_len,
                    "is_chute": True,
                })
                if existing:
                    await coll.update_one({"id": existing["id"]},
                                           {"$inc": {"qty_available": 1},
                                            "$set": {"updated_at": _ts()}})
                else:
                    await coll.insert_one({
                        "id": str(uuid.uuid4()),
                        "profile_key": profile_key,
                        "label": f"Chute {chute_len:.0f} mm — {material}",
                        "bar_length_mm": chute_len,
                        "qty_available": 1,
                        "is_chute": True,
                        "parent_cut_list_id": cut_id,
                        "created_at": _ts(),
                        "updated_at": _ts(),
                    })
                chutes_added += 1

        # Lock the cut list
        await db.cut_lists.update_one(
            {"id": cut_id},
            {"$set": {
                "cut_status": "cut",
                "cuts_confirmed_at": _ts(),
                "updated_at": _ts(),
            }},
        )
        return {
            "ok": True,
            "bars_deducted": bars_deducted,
            "chutes_added": chutes_added,
            "details": reports,
            "message": f"Liste confirmée : {bars_deducted} barre(s) déduite(s) du stock, "
                       f"{chutes_added} chute(s) ≥ {MIN_USEFUL_CHUTE_MM:.0f} mm sauvegardée(s).",
        }

    @router.post("/cuts/{cut_id}/unconfirm")
    async def unconfirm_cut(cut_id: str,
                             _: dict = Depends(auth_dep),
                             db: AsyncIOMotorDatabase = Depends(get_db)):
        """Mark the cut list as DRAFT again (rollback the lock — does NOT
        re-credit deducted bars or remove created chutes; user can adjust
        inventory manually if needed)."""
        cl = await db.cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not cl:
            raise HTTPException(404, "Liste de coupe introuvable.")
        await db.cut_lists.update_one(
            {"id": cut_id},
            {"$set": {"cut_status": "draft", "updated_at": _ts()},
             "$unset": {"cuts_confirmed_at": ""}},
        )
        return {"ok": True}

    # ─── Labels PDF ────────────────────────────────────────────────────────
    @router.get("/cuts/{cut_id}/labels.pdf")
    async def labels_pdf(cut_id: str,
                          _: dict = Depends(auth_dep),
                          db: AsyncIOMotorDatabase = Depends(get_db)):
        cl = await db.cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not cl:
            raise HTTPException(404, "Liste de coupe introuvable.")
        pdf = _render_labels_pdf(cl)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="etiquettes-{cut_id[:8]}.pdf"'},
        )

    return router


# ===========================================================================
# Labels PDF rendering (Avery 5160-ish, 3 cols × 10 rows = 30 / page)
# ===========================================================================
def _render_labels_pdf(cut_list: dict) -> bytes:
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    page_w, page_h = LETTER

    # Avery 5160: 1" × 2-5/8" labels, 3 cols × 10 rows, 0.5" top/bottom margin
    cols = 3
    rows = 10
    margin_x = 5 * mm
    margin_y = 13 * mm
    label_w = (page_w - 2 * margin_x) / cols
    label_h = (page_h - 2 * margin_y) / rows

    project = cut_list.get("name") or cut_list.get("project_ref") or "Projet"
    cut_number = cut_list.get("number") or cut_list.get("id", "")[:8]

    # One label per QTY per frame/glass item (workshop wants 1 sticker / piece)
    labels: list[dict] = []
    for it in cut_list.get("items") or []:
        if it.get("item_type") not in ("frame", "glass", "panel"):
            continue
        qty = int(it.get("qty") or 1)
        for n in range(qty):
            labels.append({
                "project": project,
                "cut_number": cut_number,
                "label": it.get("label") or "",
                "length_mm": it.get("length_mm") or 0,
                "width_mm": it.get("width_mm"),
                "profile": it.get("profile") or it.get("part_number") or "",
                "n_of": f"{n + 1}/{qty}",
            })

    if not labels:
        c.setFont("Helvetica", 14)
        c.drawCentredString(page_w / 2, page_h / 2, "Aucune piece a etiqueter.")
        c.showPage()
        c.save()
        return buf.getvalue()

    idx = 0
    while idx < len(labels):
        for row in range(rows):
            for col in range(cols):
                if idx >= len(labels):
                    break
                lab = labels[idx]
                idx += 1
                x = margin_x + col * label_w
                y = page_h - margin_y - (row + 1) * label_h
                # Border (light, helps cutting)
                c.setStrokeColor(colors.HexColor("#dddddd"))
                c.setLineWidth(0.3)
                c.rect(x + 1, y + 1, label_w - 2, label_h - 2)
                # Content
                c.setFillColor(colors.black)
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x + 5, y + label_h - 14, _ascii(lab["project"])[:32])
                c.setFont("Helvetica", 7)
                c.setFillColor(colors.HexColor("#4b5d7a"))
                c.drawString(x + 5, y + label_h - 24, f"Liste: {_ascii(lab['cut_number'])}  |  {lab['n_of']}")
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 8)
                c.drawString(x + 5, y + label_h - 36, _ascii(lab["label"])[:38])
                c.setFont("Courier", 7)
                c.drawString(x + 5, y + label_h - 46, _ascii(lab["profile"])[:38])
                c.setFont("Helvetica-Bold", 13)
                length_txt = f"{lab['length_mm']:.0f} mm"
                if lab.get("width_mm"):
                    length_txt = f"{lab['length_mm']:.0f} x {lab['width_mm']:.0f} mm"
                c.drawString(x + 5, y + 6, length_txt)
        c.showPage()
    c.save()
    return buf.getvalue()


_ASCII_REPLACE = {
    "¼": ".25", "½": ".5", "¾": ".75",
    "⅛": ".125", "⅜": ".375", "⅝": ".625", "⅞": ".875",
    "—": "-", "–": "-", "•": "*",
    "«": "\"", "»": "\"", "²": "2", "³": "3", "×": "x",
    "é": "e", "è": "e", "ê": "e", "à": "a", "â": "a", "ô": "o", "î": "i", "ç": "c", "ï": "i", "û": "u",
    "É": "E", "È": "E", "Ê": "E", "À": "A", "Ô": "O", "Ç": "C",
}


def _ascii(s) -> str:
    if not s:
        return ""
    out = []
    for ch in str(s):
        out.append(_ASCII_REPLACE.get(ch, ch))
    s2 = "".join(out)
    return "".join(c if ord(c) < 128 else "?" for c in s2)
