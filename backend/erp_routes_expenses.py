"""Expense CRUD + monthly summary + CSV export + receipt photo upload."""
import csv
import io
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_models_expense import (
    EXPENSE_CATEGORIES,
    PAYMENT_METHODS,
    STATUSES,
    Expense,
    ExpenseIn,
)

RECEIPTS_DIR = Path(os.environ.get("EXPENSE_RECEIPTS_DIR", "/app/backend/receipts"))
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_RECEIPT_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"}
ALLOWED_RECEIPT_MIME = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif",
    "application/pdf",
}
MAX_RECEIPT_BYTES = 8 * 1024 * 1024  # 8 MB


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.get("/expenses/meta")
    async def expense_meta(_: dict = Depends(auth_dep)):
        """Return categories + payment methods + statuses for the frontend."""
        return {
            "categories": EXPENSE_CATEGORIES,
            "payment_methods": PAYMENT_METHODS,
            "statuses": STATUSES,
        }

    @router.get("/expenses")
    async def list_expenses(
        category: Optional[str] = None,
        status: Optional[str] = None,
        month: Optional[str] = None,  # "YYYY-MM"
        supplier_id: Optional[str] = None,
        _: dict = Depends(auth_dep),
    ):
        query: dict = {}
        if category:
            query["category"] = category
        if status:
            query["status"] = status
        if supplier_id:
            query["supplier_id"] = supplier_id
        if month and len(month) == 7:
            query["date"] = {"$gte": f"{month}-01", "$lt": f"{month}-32"}
        cur = db.erp_expenses.find(query, {"_id": 0}).sort("date", -1).limit(1000)
        return [d async for d in cur]

    @router.post("/expenses", status_code=201, response_model=Expense)
    async def create_expense(data: ExpenseIn, _: dict = Depends(auth_dep)):
        exp = Expense(**data.model_dump())
        await db.erp_expenses.insert_one(exp.model_dump())
        return exp

    @router.put("/expenses/{expense_id}", response_model=Expense)
    async def update_expense(expense_id: str, data: ExpenseIn, _: dict = Depends(auth_dep)):
        update = data.model_dump()
        update["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = await db.erp_expenses.update_one({"id": expense_id}, {"$set": update})
        if res.matched_count == 0:
            raise HTTPException(404, "Dépense introuvable")
        doc = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        return Expense(**doc)

    @router.delete("/expenses/{expense_id}")
    async def delete_expense(expense_id: str, _: dict = Depends(auth_dep)):
        # Delete receipt file too
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if exp and exp.get("receipt_filename"):
            fp = RECEIPTS_DIR / exp["receipt_filename"]
            if fp.exists():
                try:
                    fp.unlink()
                except Exception:
                    pass
        res = await db.erp_expenses.delete_one({"id": expense_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Dépense introuvable")
        return {"deleted": expense_id}

    @router.get("/expenses/summary")
    async def expenses_summary(
        month: Optional[str] = Query(default=None),
        _: dict = Depends(auth_dep),
    ):
        """Return totals + by-category breakdown for a given month (default: current)."""
        if not month:
            month = datetime.now(timezone.utc).strftime("%Y-%m")
        cur = db.erp_expenses.find(
            {"date": {"$gte": f"{month}-01", "$lt": f"{month}-32"}},
            {"_id": 0},
        )
        rows = [d async for d in cur]
        total = sum(float(r.get("total", 0)) for r in rows)
        subtotal = sum(float(r.get("subtotal", 0)) for r in rows)
        tps = sum(float(r.get("tps", 0)) for r in rows)
        tvq = sum(float(r.get("tvq", 0)) for r in rows)
        by_cat: dict[str, float] = {}
        for r in rows:
            c = r.get("category", "Autre")
            by_cat[c] = by_cat.get(c, 0.0) + float(r.get("total", 0))
        by_category = sorted(
            [{"category": k, "total": round(v, 2)} for k, v in by_cat.items()],
            key=lambda x: -x["total"],
        )
        return {
            "month": month,
            "count": len(rows),
            "subtotal": round(subtotal, 2),
            "tps": round(tps, 2),
            "tvq": round(tvq, 2),
            "total": round(total, 2),
            "by_category": by_category,
        }

    @router.post("/expenses/{expense_id}/receipt", status_code=201)
    async def upload_receipt(
        expense_id: str,
        file: UploadFile = File(...),
        _: dict = Depends(auth_dep),
    ):
        """Upload a receipt photo (or PDF) for an expense.

        Replaces any existing receipt. Returns the new filename.
        """
        # Validate
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_RECEIPT_EXTS:
            raise HTTPException(400, f"Format non supporté. Formats acceptés : {', '.join(sorted(ALLOWED_RECEIPT_EXTS))}")
        if file.content_type and file.content_type not in ALLOWED_RECEIPT_MIME:
            # Some browsers send `application/octet-stream`; only block if it's a known bad type
            if file.content_type.startswith("text/") or "script" in file.content_type:
                raise HTTPException(400, "Type de fichier non autorisé")

        # Check the expense exists
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if not exp:
            raise HTTPException(404, "Dépense introuvable")

        # Read with size cap
        contents = await file.read(MAX_RECEIPT_BYTES + 1)
        if len(contents) > MAX_RECEIPT_BYTES:
            raise HTTPException(413, f"Fichier trop volumineux (max {MAX_RECEIPT_BYTES // 1024 // 1024} MB)")

        # Remove previous file if any
        if exp.get("receipt_filename"):
            old = RECEIPTS_DIR / exp["receipt_filename"]
            if old.exists():
                try:
                    old.unlink()
                except Exception:
                    pass

        # Save with a fresh UUID name to avoid collisions
        fname = f"{expense_id}_{uuid.uuid4().hex[:8]}{ext}"
        out_path = RECEIPTS_DIR / fname
        out_path.write_bytes(contents)

        await db.erp_expenses.update_one(
            {"id": expense_id},
            {"$set": {"receipt_filename": fname, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"receipt_filename": fname, "size": len(contents)}

    @router.get("/expenses/{expense_id}/receipt")
    async def download_receipt(expense_id: str, _: dict = Depends(auth_dep)):
        """Stream the receipt file. Authenticated only."""
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if not exp or not exp.get("receipt_filename"):
            raise HTTPException(404, "Aucun reçu pour cette dépense")
        fp = RECEIPTS_DIR / exp["receipt_filename"]
        if not fp.exists():
            raise HTTPException(404, "Fichier introuvable")
        # Pick mime by extension
        mime_by_ext = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".webp": "image/webp", ".heic": "image/heic", ".heif": "image/heif",
            ".pdf": "application/pdf",
        }
        mime = mime_by_ext.get(fp.suffix.lower(), "application/octet-stream")
        return FileResponse(fp, media_type=mime, filename=fp.name)

    @router.delete("/expenses/{expense_id}/receipt")
    async def delete_receipt(expense_id: str, _: dict = Depends(auth_dep)):
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if not exp:
            raise HTTPException(404, "Dépense introuvable")
        fname = exp.get("receipt_filename")
        if fname:
            fp = RECEIPTS_DIR / fname
            if fp.exists():
                try:
                    fp.unlink()
                except Exception:
                    pass
        await db.erp_expenses.update_one(
            {"id": expense_id},
            {"$set": {"receipt_filename": None, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"deleted": True}

    @router.get("/expenses/export.csv")
    async def export_csv(
        month: Optional[str] = None,
        _: dict = Depends(auth_dep),
    ):
        """Export expenses as CSV for accountant. UTF-8 with BOM for Excel."""
        query: dict = {}
        if month and len(month) == 7:
            query["date"] = {"$gte": f"{month}-01", "$lt": f"{month}-32"}
        cur = db.erp_expenses.find(query, {"_id": 0}).sort("date", 1)
        rows = [d async for d in cur]

        buf = io.StringIO()
        buf.write("\ufeff")  # BOM so Excel detects UTF-8
        writer = csv.writer(buf)
        writer.writerow([
            "Date", "Fournisseur", "Description", "Catégorie",
            "Sous-total", "TPS", "TVQ", "Total",
            "Mode paiement", "Statut", "Réf. facture", "Reçu", "Notes",
        ])
        for r in rows:
            writer.writerow([
                r.get("date", ""),
                r.get("supplier_name", ""),
                r.get("description", ""),
                r.get("category", ""),
                f"{float(r.get('subtotal', 0)):.2f}",
                f"{float(r.get('tps', 0)):.2f}",
                f"{float(r.get('tvq', 0)):.2f}",
                f"{float(r.get('total', 0)):.2f}",
                r.get("payment_method", ""),
                r.get("status", ""),
                r.get("invoice_ref", ""),
                "Oui" if r.get("receipt_filename") else "",
                (r.get("notes") or "").replace("\n", " "),
            ])
        buf.seek(0)
        fn_month = month or "all"
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="depenses-{fn_month}.csv"'},
        )
