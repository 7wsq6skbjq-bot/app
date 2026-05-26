"""Expense CRUD + monthly summary + CSV export for accountant."""
import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_helpers import parse_date_safe
from erp_models_expense import (
    EXPENSE_CATEGORIES,
    PAYMENT_METHODS,
    STATUSES,
    Expense,
    ExpenseIn,
)


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
            "Mode paiement", "Statut", "Réf. facture", "Notes",
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
                (r.get("notes") or "").replace("\n", " "),
            ])
        buf.seek(0)
        fn_month = month or "all"
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="depenses-{fn_month}.csv"'},
        )
