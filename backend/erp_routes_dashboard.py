"""Dashboard KPIs + monthly revenue + top customers + outstanding invoices."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_helpers import parse_date_safe


def _kpis(invoices: list, *, now: datetime, first_day_month: datetime) -> dict:
    total_invoiced = sum(float(i.get("total", 0)) for i in invoices)
    total_paid = sum(float(i.get("total", 0)) for i in invoices if i.get("status") == "payée")
    total_outstanding = sum(
        float(i.get("total", 0))
        for i in invoices
        if i.get("status") in ("envoyée", "brouillon")
    )
    revenue_this_month = 0.0
    for i in invoices:
        d = parse_date_safe(i.get("date"))
        if d and d >= first_day_month and i.get("status") == "payée":
            revenue_this_month += float(i.get("total", 0))
    return {
        "invoiced_total": round(total_invoiced, 2),
        "paid_total": round(total_paid, 2),
        "outstanding_total": round(total_outstanding, 2),
        "revenue_this_month": round(revenue_this_month, 2),
        "invoices_count": len(invoices),
    }


def _monthly_revenue(invoices: list, *, first_day_month: datetime) -> list[dict]:
    months = []
    for offset in range(5, -1, -1):
        month_start = (first_day_month - timedelta(days=offset * 30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        total = 0.0
        for i in invoices:
            d = parse_date_safe(i.get("date"))
            if d and month_start <= d < month_end and i.get("status") == "payée":
                total += float(i.get("total", 0))
        months.append({
            "month": month_start.strftime("%Y-%m"),
            "label": month_start.strftime("%b %Y"),
            "total": round(total, 2),
        })
    return months


def _top_customers(invoices: list, limit: int = 5) -> list[dict]:
    top: dict[str, float] = {}
    for i in invoices:
        cust = (i.get("customer_snapshot") or {}).get("name") or "—"
        top[cust] = top.get(cust, 0.0) + float(i.get("total", 0))
    return sorted(
        [{"name": k, "total": round(v, 2)} for k, v in top.items()],
        key=lambda x: -x["total"],
    )[:limit]


def _outstanding_invoices(invoices: list, limit: int = 8) -> list[dict]:
    outstanding = [
        {
            "id": i.get("id"),
            "number": i.get("number"),
            "customer": (i.get("customer_snapshot") or {}).get("name"),
            "date": i.get("date"),
            "due_date": i.get("due_date"),
            "total": i.get("total"),
            "status": i.get("status"),
        }
        for i in invoices
        if i.get("status") in ("envoyée", "brouillon")
    ]
    outstanding.sort(key=lambda x: x.get("date") or "", reverse=True)
    return outstanding[:limit]


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.get("/dashboard")
    async def erp_dashboard(_: dict = Depends(auth_dep)):
        invoices = await db.erp_invoices.find({}, {"_id": 0}).to_list(length=None)

        now = datetime.now(timezone.utc)
        first_day_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        kpi = _kpis(invoices, now=now, first_day_month=first_day_month)
        kpi["customers_count"] = await db.erp_parties.count_documents({"kind": "customer"})
        kpi["suppliers_count"] = await db.erp_parties.count_documents({"kind": "supplier"})
        kpi["products_count"] = await db.erp_products.count_documents({})
        kpi["po_count"] = await db.erp_purchase_orders.count_documents({})
        kpi["bol_count"] = await db.erp_bills_of_lading.count_documents({})

        return {
            "kpi": kpi,
            "monthly_revenue": _monthly_revenue(invoices, first_day_month=first_day_month),
            "top_customers": _top_customers(invoices),
            "outstanding_invoices": _outstanding_invoices(invoices),
        }
