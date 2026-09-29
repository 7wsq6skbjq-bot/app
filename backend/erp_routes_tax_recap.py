"""Récapitulatif trimestriel TPS/TVQ — à remettre au comptable.

Regroupe, pour un trimestre civil (T1 jan-mar, T2 avr-juin, T3 juil-sep,
T4 oct-déc) :
  * TAXES PERÇUES  : factures émises (statut envoyée + payée) datées dans la période
  * CRÉDITS DE TAXE : taxes payées sur les dépenses enregistrées dans la période
  * NET à remettre  : perçu − payé (par TPS et TVQ)

Endpoints (sous /api/admin) :
  GET  /tax-recap?year=&quarter=  -> JSON résumé + années disponibles
  GET  /tax-recap/pdf?year=&quarter=  -> PDF brandé (aperçu inline)
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_pdf import render_tax_recap_pdf

COLLECTED_STATUSES = ("envoyée", "payée")
_MONTH_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]
_QUARTER_MONTHS = {1: "janvier à mars", 2: "avril à juin",
                   3: "juillet à septembre", 4: "octobre à décembre"}


def _quarter_bounds(year: int, quarter: int) -> tuple[str, str, str]:
    """Return (start_iso_inclusive, end_iso_inclusive, end_exclusive_iso)."""
    m0 = (quarter - 1) * 3 + 1          # 1,4,7,10
    start = f"{year:04d}-{m0:02d}-01"
    if quarter == 4:
        end_excl = f"{year + 1:04d}-01-01"
    else:
        end_excl = f"{year:04d}-{m0 + 3:02d}-01"
    # last day = end_excl minus 1 day (string display only)
    from datetime import date, timedelta
    ex = date.fromisoformat(end_excl)
    last = ex - timedelta(days=1)
    return start, last.isoformat(), end_excl


def _date_fr(iso: str) -> str:
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d")
        return f"{d.day} {_MONTH_FR[d.month - 1]} {d.year}"
    except Exception:
        return iso


async def _compute(db, year: int, quarter: int) -> dict:
    start, end_incl, end_excl = _quarter_bounds(year, quarter)

    inv_cur = db.erp_invoices.find(
        {"status": {"$in": list(COLLECTED_STATUSES)},
         "date": {"$gte": start, "$lt": end_excl}},
        {"_id": 0, "subtotal": 1, "tps": 1, "tvq": 1, "total": 1})
    col = {"subtotal": 0.0, "tps": 0.0, "tvq": 0.0, "total": 0.0, "count": 0}
    async for r in inv_cur:
        col["subtotal"] += float(r.get("subtotal") or 0)
        col["tps"] += float(r.get("tps") or 0)
        col["tvq"] += float(r.get("tvq") or 0)
        col["total"] += float(r.get("total") or 0)
        col["count"] += 1

    exp_cur = db.erp_expenses.find(
        {"date": {"$gte": start, "$lt": end_excl}},
        {"_id": 0, "subtotal": 1, "tps": 1, "tvq": 1, "total": 1})
    paid = {"subtotal": 0.0, "tps": 0.0, "tvq": 0.0, "total": 0.0, "count": 0}
    async for r in exp_cur:
        paid["subtotal"] += float(r.get("subtotal") or 0)
        paid["tps"] += float(r.get("tps") or 0)
        paid["tvq"] += float(r.get("tvq") or 0)
        paid["total"] += float(r.get("total") or 0)
        paid["count"] += 1

    for blk in (col, paid):
        for k in ("subtotal", "tps", "tvq", "total"):
            blk[k] = round(blk[k], 2)

    net = {
        "tps": round(col["tps"] - paid["tps"], 2),
        "tvq": round(col["tvq"] - paid["tvq"], 2),
    }
    net["total"] = round(net["tps"] + net["tvq"], 2)

    return {
        "year": year, "quarter": quarter,
        "period_label": f"T{quarter} {year} ({_QUARTER_MONTHS[quarter]})",
        "start": start, "end": end_incl,
        "start_fr": _date_fr(start), "end_fr": _date_fr(end_incl),
        "collected": col, "paid": paid, "net": net,
    }


async def _available_years(db) -> list[int]:
    years: set[int] = set()
    for coll in (db.erp_invoices, db.erp_expenses):
        for d in await coll.distinct("date"):
            if isinstance(d, str) and len(d) >= 4 and d[:4].isdigit():
                years.add(int(d[:4]))
    now_year = datetime.now(timezone.utc).year
    years.add(now_year)
    return sorted(years, reverse=True)


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    def _now_quarter() -> tuple[int, int]:
        n = datetime.now(timezone.utc)
        return n.year, (n.month - 1) // 3 + 1

    @router.get("/tax-recap")
    async def tax_recap(year: int | None = None, quarter: int | None = None,
                        _: dict = Depends(auth_dep)):
        y, q = _now_quarter()
        year = year or y
        quarter = quarter or q
        if quarter < 1 or quarter > 4:
            raise HTTPException(400, "Trimestre invalide (1-4).")
        data = await _compute(db, year, quarter)
        data["available_years"] = await _available_years(db)
        return data

    @router.get("/tax-recap/pdf")
    async def tax_recap_pdf(year: int | None = None, quarter: int | None = None,
                            _: dict = Depends(auth_dep)):
        y, q = _now_quarter()
        year = year or y
        quarter = quarter or q
        if quarter < 1 or quarter > 4:
            raise HTTPException(400, "Trimestre invalide (1-4).")
        data = await _compute(db, year, quarter)
        pdf = await asyncio.to_thread(render_tax_recap_pdf, data)
        fname = f"recap-tps-tvq-T{quarter}-{year}.pdf"
        return Response(content=pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{fname}"'})
