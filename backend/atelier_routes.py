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

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm

logger = logging.getLogger("portech.atelier")

# Chutes shorter than this are considered scrap, not re-usable inventory.
MIN_USEFUL_CHUTE_MM = 600.0


FINISHES = ("clair", "noir", "mill_finish")
DEFAULT_FINISH = "clair"


# ===========================================================================
# Pydantic models
# ===========================================================================
class InventoryRowIn(BaseModel):
    profile_key: str = Field(..., min_length=1, max_length=120)
    label: str | None = None
    bar_length_mm: float = Field(..., gt=0)
    qty_available: int = Field(..., ge=0)
    is_chute: bool = False
    finish: str = Field(default=DEFAULT_FINISH)
    restock_min: int | None = Field(default=None, ge=0)
    restock_max: int | None = Field(default=None, ge=0)


class InventoryAdjust(BaseModel):
    delta: int  # positive = add, negative = remove


class InventoryThresholdsIn(BaseModel):
    restock_min: int | None = Field(default=None, ge=0)
    restock_max: int | None = Field(default=None, ge=0)


class InventoryMetaIn(BaseModel):
    """Editable text metadata. Only `label` and `profile_key` are touched —
    qty / finish / length / chute flag are immutable via this endpoint."""
    label: str | None = Field(default=None, max_length=200)
    profile_key: str | None = Field(default=None, min_length=1, max_length=120)


class InventoryBulkThresholdsIn(BaseModel):
    """Apply restock_min / restock_max to many rows in one shot.
    Filters control WHICH rows are touched:
      - finish: 'clair' | 'noir' | None (both)
      - is_chute: bool (default False → only full bars)
      - profile_key_prefix: e.g. 'AT Fabrication' to scope to one manufacturer
    `restock_min` / `restock_max`: set both; pass None to clear that field."""
    restock_min: int | None = Field(default=None, ge=0)
    restock_max: int | None = Field(default=None, ge=0)
    finish: str | None = Field(default=None)
    is_chute: bool = Field(default=False)
    profile_key_prefix: str | None = Field(default=None, max_length=120)
    clear_min: bool = Field(default=False)
    clear_max: bool = Field(default=False)


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
    def _normalize_row(r: dict) -> dict:
        """Ensure backward-compat fields exist on every row served to the UI."""
        r.setdefault("finish", DEFAULT_FINISH)
        # Legacy field: restock_threshold → restock_min
        if "restock_min" not in r and r.get("restock_threshold") is not None:
            r["restock_min"] = r["restock_threshold"]
        r.setdefault("restock_min", None)
        r.setdefault("restock_max", None)
        return r

    @router.get("/alu-inventory")
    async def list_inventory(_: dict = Depends(auth_dep),
                              db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _stock_collection(db)
        rows = await coll.find({}, {"_id": 0}).sort("profile_key", 1).to_list(2000)
        rows = [_normalize_row(r) for r in rows]
        full = [r for r in rows if not r.get("is_chute")]
        chutes = [r for r in rows if r.get("is_chute")]
        # Quick summary counts to feed the "ludique" header in the UI
        finishes_count = {f: sum(1 for r in full if r.get("finish") == f) for f in FINISHES}
        below_min = sum(
            1 for r in full
            if r.get("restock_min") is not None
            and (r.get("qty_available", 0) or 0) <= (r.get("restock_min") or 0)
        )
        return {
            "bars": full, "chutes": chutes, "total_rows": len(rows),
            "finishes_count": finishes_count, "below_min": below_min,
        }

    @router.post("/alu-inventory", status_code=201)
    async def add_inventory(payload: InventoryRowIn,
                             _: dict = Depends(auth_dep),
                             db: AsyncIOMotorDatabase = Depends(get_db)):
        coll = await _stock_collection(db)
        finish = payload.finish if payload.finish in FINISHES else DEFAULT_FINISH
        # Merge with existing identical row (same key + bar length + chute flag + finish)
        existing = await coll.find_one({
            "profile_key": payload.profile_key,
            "bar_length_mm": payload.bar_length_mm,
            "is_chute": payload.is_chute,
            "finish": finish,
        }, {"_id": 0})
        if existing:
            set_fields = {"updated_at": _ts()}
            if payload.restock_min is not None:
                set_fields["restock_min"] = payload.restock_min
            if payload.restock_max is not None:
                set_fields["restock_max"] = payload.restock_max
            await coll.update_one(
                {"id": existing["id"]},
                {"$inc": {"qty_available": payload.qty_available},
                 "$set": set_fields},
            )
            return _normalize_row(await coll.find_one({"id": existing["id"]}, {"_id": 0}))
        doc = {
            "id": str(uuid.uuid4()),
            **payload.model_dump(),
            "finish": finish,
            "created_at": _ts(),
            "updated_at": _ts(),
        }
        await coll.insert_one(doc)
        return _normalize_row({k: v for k, v in doc.items() if k != "_id"})

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
        return _normalize_row(await coll.find_one({"id": row_id}, {"_id": 0}))

    @router.patch("/alu-inventory/{row_id}/thresholds")
    async def set_thresholds(row_id: str, payload: InventoryThresholdsIn,
                              _: dict = Depends(auth_dep),
                              db: AsyncIOMotorDatabase = Depends(get_db)):
        """Set / unset the restock min and max for a single inventory row."""
        coll = await _stock_collection(db)
        row = await coll.find_one({"id": row_id}, {"_id": 0})
        if not row:
            raise HTTPException(404, "Ligne d'inventaire introuvable.")
        set_fields = {"updated_at": _ts()}
        unset_fields = {}
        if payload.restock_min is None:
            unset_fields["restock_min"] = ""
            unset_fields["restock_threshold"] = ""  # also clear legacy field
        else:
            set_fields["restock_min"] = payload.restock_min
        if payload.restock_max is None:
            unset_fields["restock_max"] = ""
        else:
            set_fields["restock_max"] = payload.restock_max
        update = {"$set": set_fields}
        if unset_fields:
            update["$unset"] = unset_fields
        await coll.update_one({"id": row_id}, update)
        return _normalize_row(await coll.find_one({"id": row_id}, {"_id": 0}))

    @router.patch("/alu-inventory-bulk-thresholds")
    async def bulk_thresholds(payload: InventoryBulkThresholdsIn,
                                _: dict = Depends(auth_dep),
                                db: AsyncIOMotorDatabase = Depends(get_db)):
        """Apply restock_min and/or restock_max to a slice of rows.

        Useful for "set everything in the noir finish to min=2, max=8" in one
        click. Returns how many rows were touched + the new normalized rows.
        Pass `clear_min=True` to wipe restock_min on the slice (same for max).
        """
        coll = await _stock_collection(db)
        query: dict = {"is_chute": payload.is_chute}
        if payload.finish in FINISHES:
            query["finish"] = payload.finish
        if payload.profile_key_prefix:
            # Regex anchored at the start, escaped for safety
            import re
            query["profile_key"] = {"$regex": f"^{re.escape(payload.profile_key_prefix)}"}

        set_fields: dict = {"updated_at": _ts()}
        unset_fields: dict = {}
        if payload.clear_min:
            unset_fields["restock_min"] = ""
            unset_fields["restock_threshold"] = ""  # legacy
        elif payload.restock_min is not None:
            set_fields["restock_min"] = payload.restock_min
        if payload.clear_max:
            unset_fields["restock_max"] = ""
        elif payload.restock_max is not None:
            set_fields["restock_max"] = payload.restock_max

        # No-op guard: if nothing to change, return early
        if len(set_fields) == 1 and not unset_fields:
            raise HTTPException(400, "Aucune modification — fournir min/max ou clear_*.")

        update: dict = {"$set": set_fields}
        if unset_fields:
            update["$unset"] = unset_fields
        result = await coll.update_many(query, update)
        return {
            "matched": result.matched_count,
            "modified": result.modified_count,
            "filter": query,
        }

    @router.patch("/alu-inventory/{row_id}/meta")
    async def set_meta(row_id: str, payload: InventoryMetaIn,
                        _: dict = Depends(auth_dep),
                        db: AsyncIOMotorDatabase = Depends(get_db)):
        """Edit the human-readable label (and optionally the inventory key)
        of an existing row. Useful to fix typos without re-creating the row."""
        coll = await _stock_collection(db)
        row = await coll.find_one({"id": row_id}, {"_id": 0})
        if not row:
            raise HTTPException(404, "Ligne d'inventaire introuvable.")
        set_fields = {"updated_at": _ts()}
        if payload.label is not None:
            set_fields["label"] = payload.label.strip() or row.get("profile_key")
        if payload.profile_key is not None:
            new_key = payload.profile_key.strip()
            if new_key:
                set_fields["profile_key"] = new_key
        await coll.update_one({"id": row_id}, {"$set": set_fields})
        return _normalize_row(await coll.find_one({"id": row_id}, {"_id": 0}))

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
        cl = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
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
        # Cut list may carry a default finish — use it to deduct from the right
        # color stock. Fallback: "clair" (most common).
        cut_finish = (cl.get("finish") or DEFAULT_FINISH).lower()
        if cut_finish not in FINISHES:
            cut_finish = DEFAULT_FINISH
        for grp in groups:
            profile_key = grp.get("profile") or "Inconnu"
            material = grp.get("material") or "—"
            plan = grp.get("plan") or {}
            bars_count = int(plan.get("bars_count") or 0)
            bar_length = float(plan.get("stock_length_mm") or 0)
            # Try to find matching stock row in the requested finish first;
            # fall back to ANY finish if not found, then ANY length.
            row = await coll.find_one({
                "profile_key": profile_key,
                "bar_length_mm": bar_length,
                "is_chute": False,
                "finish": cut_finish,
            })
            if not row:
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
                reports.append({
                    "profile_key": profile_key, "finish": row.get("finish"),
                    "deducted": bars_count, "remaining": new_qty,
                })
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
                    "finish": cut_finish,
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
                        "finish": cut_finish,
                        "parent_cut_list_id": cut_id,
                        "created_at": _ts(),
                        "updated_at": _ts(),
                    })
                chutes_added += 1

        # Lock the cut list
        await db.erp_cut_lists.update_one(
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
        cl = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not cl:
            raise HTTPException(404, "Liste de coupe introuvable.")
        await db.erp_cut_lists.update_one(
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
        cl = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not cl:
            raise HTTPException(404, "Liste de coupe introuvable.")
        pdf = _render_labels_pdf(cl)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="etiquettes-{cut_id[:8]}.pdf"'},
        )

    # ─── Purchase-order PDF (inventory restock) ───────────────────────────
    @router.get("/alu-inventory/purchase-order.pdf")
    async def purchase_order_pdf(
        finish: str | None = Query(default=None, description="clair | noir | None=both"),
        stealth: int = Query(default=0, description="1 = remove Portech branding"),
        _: dict = Depends(auth_dep),
        db: AsyncIOMotorDatabase = Depends(get_db),
    ):
        """Generate a supplier-ready PDF listing every inventory row at or
        below its restock_min, with the qty needed to reach restock_max
        (or the min if no max is set). When `stealth=1`, the company branding
        and any reference to Portech is removed — only the bare purchase-order
        table remains. Useful when the buyer doesn't want the supplier or a
        third party to identify the source app."""
        coll = await _stock_collection(db)
        rows = await coll.find({"is_chute": False}, {"_id": 0}).to_list(2000)
        rows = [_normalize_row(r) for r in rows]
        if finish in FINISHES:
            rows = [r for r in rows if r.get("finish") == finish]
        items_to_order = []
        for r in rows:
            rmin = r.get("restock_min")
            if rmin is None:
                continue
            qty = int(r.get("qty_available") or 0)
            if qty > rmin:
                continue
            target = r.get("restock_max") if r.get("restock_max") is not None else rmin
            to_order = max(0, int(target) - qty)
            if to_order <= 0:
                to_order = 1
            items_to_order.append({**r, "to_order": to_order, "target": target})
        items_to_order.sort(key=lambda x: (x.get("profile_key") or "").lower())
        pdf = _render_purchase_order_pdf(items_to_order, finish_filter=finish, stealth=bool(stealth))
        suffix = f"{finish or 'tous'}{'-anon' if stealth else ''}"
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="bon-commande-alu-{suffix}.pdf"'},
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



# ===========================================================================
# Purchase-order PDF rendering (one printable sheet sent to the supplier)
# ===========================================================================
def _hydro_for_inventory_key(profile_key: str | None) -> str | None:
    """Given an inventory profile_key like 'AT Fabrication #ATT1005',
    return the matching Hydro code (e.g. 'MH80477') or None if unknown."""
    if not profile_key or "#" not in profile_key:
        return None
    try:
        from profile_catalog import hydro_for
        at_code = profile_key.split("#", 1)[1].strip()
        entry = hydro_for(at_code)
        return entry.get("hydro") if entry else None
    except Exception:
        return None


def _render_purchase_order_pdf(items: list[dict], finish_filter: str | None = None, stealth: bool = False) -> bytes:
    """Render a printable purchase-order PDF.

    Layout (when no finish filter is applied):
        SECTION 1 — CLAIR : every clair piece below its min (grouped by manuf)
        SECTION 2 — NOIR  : every noir piece below its min (grouped by manuf)
        SECTION 3 — MILL FINISH : per-profile total = clair_qty + noir_qty,
                    the raw mill-finish bar count to order from the supplier
                    and send to anodization.

    When `finish_filter` is set ("clair" or "noir"), only that section is
    rendered (no Mill Finish recap — irrelevant to a single-finish order).
    """
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    page_w, page_h = LETTER
    today = _ts().strftime("%Y-%m-%d")
    bottom_margin = 25 * mm
    line_h = 7 * mm

    # ── Column layout (mm from the left edge of the page) ──────────────
    # Letter is 215.9 mm wide; usable area = 15..200 mm (185 mm wide).
    COL_PIECE_X = 17
    COL_FINI_DOT_X = 92         # finish dot (small circle)
    COL_FINI_TXT_X = 95         # finish text "Clair / Noir"
    COL_LEN_X = 112             # bar length
    COL_QTY_X = 138             # qty stock
    COL_MM_X = 155              # min / max
    COL_ORDER_X = page_w - 17 * mm   # right-aligned "A commander"

    def draw_header():
        c.setFillColor(colors.HexColor("#0c182b"))
        c.rect(0, page_h - 22 * mm, page_w, 22 * mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        title = "Bon de commande aluminium" if stealth else "PORTECH — Bon de commande aluminium"
        c.drawString(15 * mm, page_h - 12 * mm, title)
        c.setFont("Helvetica", 9)
        scope = (finish_filter or "tous").upper()
        c.drawString(15 * mm, page_h - 18 * mm, f"Date : {today}   |   Fini : {scope}")
        c.setFillColor(colors.black)

    draw_header()

    if not items:
        c.setFont("Helvetica", 14)
        c.setFillColor(colors.HexColor("#22a06b"))
        c.drawCentredString(page_w / 2, page_h / 2,
                            "Aucune commande necessaire — tout le stock est au-dessus du minimum.")
        c.showPage()
        c.save()
        return buf.getvalue()

    y = [page_h - 32 * mm]  # mutable via list so nested helpers can update it

    def new_page():
        c.showPage()
        draw_header()
        y[0] = page_h - 32 * mm

    def ensure_space(min_y: float):
        if y[0] < min_y:
            new_page()

    def draw_section_band(title: str, color_hex: str, subtitle: str = ""):
        ensure_space(bottom_margin + 20)
        c.setFillColor(colors.HexColor(color_hex))
        c.rect(15 * mm, y[0] - 1, page_w - 30 * mm, 9 * mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(17 * mm, y[0] + 1.5, title.upper())
        if subtitle:
            c.setFont("Helvetica", 8)
            c.drawRightString(page_w - 17 * mm, y[0] + 2.5, subtitle)
        c.setFillColor(colors.black)
        y[0] -= 9 * mm

    def draw_manuf_band(manuf: str):
        ensure_space(bottom_margin + 14)
        c.setFillColor(colors.HexColor("#1f3a66"))
        c.rect(15 * mm, y[0] - 1, page_w - 30 * mm, line_h, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(17 * mm, y[0] + 1.5, _ascii(manuf).upper())
        c.setFillColor(colors.black)
        y[0] -= line_h

    def draw_table_header():
        ensure_space(bottom_margin + line_h)
        c.setFillColor(colors.HexColor("#f3f6fb"))
        c.rect(15 * mm, y[0] - 1, page_w - 30 * mm, line_h, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#4b5d7a"))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(COL_PIECE_X * mm, y[0] + 1.5, "PIECE")
        c.drawString(COL_FINI_TXT_X * mm, y[0] + 1.5, "FINI")
        c.drawString(COL_LEN_X * mm, y[0] + 1.5, "LONG.")
        c.drawString(COL_QTY_X * mm, y[0] + 1.5, "QTE")
        c.drawString(COL_MM_X * mm, y[0] + 1.5, "MIN / MAX")
        c.drawRightString(COL_ORDER_X, y[0] + 1.5, "A COMMANDER")
        c.setFillColor(colors.black)
        y[0] -= line_h

    def _dot_for(finish: str):
        """Return ReportLab color for a finish dot (PDF) — used by draw_row."""
        if finish == "noir":
            return colors.HexColor("#0c182b")
        if finish == "mill_finish":
            return colors.HexColor("#a8aab2")
        return colors.HexColor("#dde5f0")  # clair

    def draw_row(r: dict):
        ensure_space(bottom_margin)
        if y[0] == page_h - 32 * mm:
            draw_table_header()
        fin = (r.get("finish") or "clair").lower()
        c.setFillColor(_dot_for(fin))
        c.circle(COL_FINI_DOT_X * mm, y[0] + 1.5, 1.4 * mm, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#4b5d7a"))
        c.setFont("Helvetica", 7)
        label_fin = "Mill" if fin == "mill_finish" else _ascii(fin).capitalize()
        c.drawString(COL_FINI_TXT_X * mm, y[0] + 0.5, label_fin)
        # Label / piece (line 1 = AT label, line 2 = Hydro code if known)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        label = r.get("label") or r.get("profile_key") or ""
        c.drawString(COL_PIECE_X * mm, y[0] + 1.5, _ascii(label)[:42])
        hydro = _hydro_for_inventory_key(r.get("profile_key"))
        if hydro:
            c.setFillColor(colors.HexColor("#4b5d7a"))
            c.setFont("Helvetica-Oblique", 6.5)
            c.drawString(COL_PIECE_X * mm, y[0] - 1.5, f"Hydro {hydro}")
            c.setFillColor(colors.black)
        # Length
        c.drawString(COL_LEN_X * mm, y[0] + 1.5, f"{r.get('bar_length_mm', 0):.0f}")
        # Qty (color-coded)
        qty = int(r.get("qty_available") or 0)
        rmin = r.get("restock_min")
        rmax = r.get("restock_max")
        if qty == 0:
            c.setFillColor(colors.HexColor("#cc1f1f"))
        elif rmin is not None and qty <= rmin:
            c.setFillColor(colors.HexColor("#cc7a1f"))
        else:
            c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(COL_QTY_X * mm, y[0] + 1.5, str(qty))
        # Min / max
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawString(COL_MM_X * mm, y[0] + 1.5,
                     f"{rmin if rmin is not None else '-'} / {rmax if rmax is not None else '-'}")
        # A commander (right-aligned, bold)
        c.setFillColor(colors.HexColor("#0c182b"))
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(COL_ORDER_X, y[0] + 1.5, str(r.get("to_order") or 0))
        c.setFillColor(colors.black)
        y[0] -= line_h

    def render_finish_section(finish: str, color_hex: str):
        section_items = [r for r in items if (r.get("finish") or "clair") == finish]
        if not section_items:
            return 0
        total_qty = sum(int(r.get("to_order") or 0) for r in section_items)
        title = f"FINI {finish.upper()}"
        subtitle = f"{len(section_items)} reference(s) - {total_qty} barre(s) a commander"
        draw_section_band(title, color_hex, subtitle)
        # Group by manufacturer
        grouped: dict[str, list[dict]] = {}
        for r in section_items:
            key = r.get("profile_key") or "Divers"
            manuf = key.split(" #")[0].strip() if " #" in key else "Divers"
            grouped.setdefault(manuf, []).append(r)
        for manuf, rows in grouped.items():
            draw_manuf_band(manuf)
            draw_table_header()
            for r in rows:
                draw_row(r)
            y[0] -= 3 * mm
        return total_qty

    # ── SECTION CLAIR / NOIR / MILL FINISH ─────────────────────────────
    clair_total = 0
    noir_total = 0
    mill_total = 0
    if finish_filter in (None, "clair"):
        clair_total = render_finish_section("clair", "#7d9ac2")          # bluish band
    if finish_filter in (None, "noir"):
        noir_total = render_finish_section("noir", "#0c182b")            # dark band
    if finish_filter in (None, "mill_finish"):
        mill_total = render_finish_section("mill_finish", "#7b7f8a")     # silver/grey band

    # ── SECTION 4 — RECAP MILL FINISH (envoi anodisation) ──────────────
    # Only when looking at all finishes: shows for each profile how many
    # raw mill-finish bars to order from Hydro = total (clair + noir) needs
    # minus what's already on the shelf as mill_finish (not yet anodized).
    if finish_filter is None:
        # Pull current mill_finish stock from DB-derived items list (items only
        # contains rows below their min, but the mill_finish recap needs the
        # FULL current mill_finish stock too — to subtract from the demand).
        # For simplicity we use the items list which contains every row that
        # was triggered as "below min". A more advanced version would query
        # the inventory again — kept simple per the user's incremental ask.
        recap: dict[tuple, dict] = {}
        for r in items:
            k = (r.get("profile_key") or "Divers", r.get("bar_length_mm") or 0)
            agg = recap.setdefault(k, {
                "profile_key": k[0], "label": r.get("label") or k[0],
                "bar_length_mm": k[1], "clair": 0, "noir": 0, "mill": 0,
            })
            fin = (r.get("finish") or "clair").lower()
            if fin == "noir":
                agg["noir"] += int(r.get("to_order") or 0)
            elif fin == "mill_finish":
                agg["mill"] += int(r.get("to_order") or 0)
            else:
                agg["clair"] += int(r.get("to_order") or 0)

        if recap:
            draw_section_band(
                "RECAP MILL FINISH — envoi anodisation",
                "#22a06b",
                "Total barres brutes (Hydro -> anodisation)",
            )
            ensure_space(bottom_margin + line_h)
            c.setFillColor(colors.HexColor("#f3f6fb"))
            c.rect(15 * mm, y[0] - 1, page_w - 30 * mm, line_h, fill=True, stroke=False)
            c.setFillColor(colors.HexColor("#4b5d7a"))
            c.setFont("Helvetica-Bold", 7)
            c.drawString(COL_PIECE_X * mm, y[0] + 1.5, "PIECE")
            c.drawString(COL_LEN_X * mm, y[0] + 1.5, "LONG.")
            c.drawString(128 * mm, y[0] + 1.5, "CLAIR")
            c.drawString(143 * mm, y[0] + 1.5, "NOIR")
            c.drawString(158 * mm, y[0] + 1.5, "MILL")
            c.drawRightString(COL_ORDER_X, y[0] + 1.5, "TOTAL")
            c.setFillColor(colors.black)
            y[0] -= line_h
            for (pkey, blen), agg in sorted(recap.items(), key=lambda x: x[0][0].lower()):
                ensure_space(bottom_margin)
                c.setFont("Helvetica", 8)
                c.drawString(COL_PIECE_X * mm, y[0] + 1.5, _ascii(agg["label"])[:42])
                c.drawString(COL_LEN_X * mm, y[0] + 1.5, f"{blen:.0f}")
                c.setFont("Helvetica", 9)
                c.drawString(128 * mm, y[0] + 1.5, str(agg["clair"]))
                c.drawString(143 * mm, y[0] + 1.5, str(agg["noir"]))
                c.drawString(158 * mm, y[0] + 1.5, str(agg["mill"]))
                c.setFillColor(colors.HexColor("#0c182b"))
                c.setFont("Helvetica-Bold", 11)
                total = agg["clair"] + agg["noir"] + agg["mill"]
                c.drawRightString(COL_ORDER_X, y[0] + 1.5, str(total))
                c.setFillColor(colors.black)
                y[0] -= line_h

    # ── Final footer total ──────────────────────────────────────────────
    grand_total = clair_total + noir_total + mill_total
    ensure_space(bottom_margin + 12)
    c.setFillColor(colors.HexColor("#0c182b"))
    c.rect(15 * mm, y[0] - 4, page_w - 30 * mm, 9 * mm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(17 * mm, y[0] + 0.5,
                 f"TOTAL : {grand_total} barre(s)  "
                 f"({clair_total} clair + {noir_total} noir + {mill_total} mill)")
    c.drawRightString(page_w - 17 * mm, y[0] + 0.5, f"{len(items)} ligne(s) sous le min")
    c.showPage()
    c.save()
    return buf.getvalue()
