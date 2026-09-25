"""Rapport kilométrique — journal des déplacements + PDF pro (par trajet ou relevé).

Sans taxes (indemnité tout inclus, style Revenu Québec). Taux par défaut 0,73 $/km
(ARC / Revenu Québec 2026), modifiable à chaque trajet.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from erp_helpers import make_next_number_fn, compute_totals
from erp_models import Invoice, LineItem
from erp_pdf import (render_mileage_annual_pdf, render_mileage_statement_pdf,
                     render_mileage_trip_pdf)

DEFAULT_RATE = 0.73  # ARC / Revenu Québec 2026 — 5 000 premiers km


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _distance(data: "MileageIn") -> float:
    """Km direct, ou calculé depuis l'odomètre si fourni."""
    if data.odometer_start is not None and data.odometer_end is not None:
        return round(max(0.0, float(data.odometer_end) - float(data.odometer_start)), 1)
    return round(float(data.distance_km or 0), 1)


class MileageIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    purpose: Optional[str] = None
    odometer_start: Optional[float] = None
    odometer_end: Optional[float] = None
    distance_km: float = 0.0
    rate: float = DEFAULT_RATE
    vehicle: Optional[str] = None
    job_id: Optional[str] = None
    job_number: Optional[str] = None
    notes: Optional[str] = None


class Mileage(MileageIn):
    id: str
    ref: str
    amount: float = 0.0
    invoiced_id: Optional[str] = None
    invoiced_number: Optional[int] = None
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    _next = make_next_number_fn(db)

    async def _client_snapshot(client_id: Optional[str], fallback_name: Optional[str]) -> dict:
        if client_id:
            p = await db.erp_parties.find_one({"id": client_id}, {"_id": 0})
            if p:
                return p
        return {"name": fallback_name} if fallback_name else {}

    @router.get("/mileage/meta")
    async def mileage_meta(_: dict = Depends(auth_dep)):
        return {"default_rate": DEFAULT_RATE}

    @router.get("/mileage")
    async def list_mileage(
        month: Optional[str] = None,
        client_id: Optional[str] = None,
        _: dict = Depends(auth_dep),
    ):
        query: dict = {}
        if client_id:
            query["client_id"] = client_id
        if month and len(month) == 7:
            query["date"] = {"$gte": f"{month}-01", "$lt": f"{month}-32"}
        cur = db.erp_mileage.find(query, {"_id": 0}).sort("date", -1).limit(1000)
        return [d async for d in cur]

    @router.get("/mileage/summary")
    async def mileage_summary(month: Optional[str] = None, _: dict = Depends(auth_dep)):
        if not month:
            month = datetime.now(timezone.utc).strftime("%Y-%m")
        cur = db.erp_mileage.find(
            {"date": {"$gte": f"{month}-01", "$lt": f"{month}-32"}}, {"_id": 0})
        rows = [d async for d in cur]
        total_km = sum(float(r.get("distance_km", 0)) for r in rows)
        total_amount = sum(float(r.get("amount", 0)) for r in rows)
        by = {}
        for r in rows:
            name = r.get("client_name") or "—"
            b = by.setdefault(name, {"client": name, "km": 0.0, "amount": 0.0})
            b["km"] += float(r.get("distance_km", 0))
            b["amount"] += float(r.get("amount", 0))
        by_client = sorted(
            [{"client": v["client"], "km": round(v["km"], 1), "amount": round(v["amount"], 2)}
             for v in by.values()],
            key=lambda x: -x["amount"],
        )
        return {
            "month": month,
            "count": len(rows),
            "total_km": round(total_km, 1),
            "total_amount": round(total_amount, 2),
            "by_client": by_client,
        }

    @router.post("/mileage", status_code=201, response_model=Mileage)
    async def create_mileage(data: MileageIn, _: dict = Depends(auth_dep)):
        n = await _next("mileage")
        km = _distance(data)
        entry = Mileage(
            id=uuid.uuid4().hex,
            ref=f"KM-{n:04d}",
            **{**data.model_dump(), "distance_km": km},
            amount=round(km * float(data.rate or DEFAULT_RATE), 2),
        )
        await db.erp_mileage.insert_one(entry.model_dump())
        return entry

    @router.put("/mileage/{mileage_id}", response_model=Mileage)
    async def update_mileage(mileage_id: str, data: MileageIn, _: dict = Depends(auth_dep)):
        existing = await db.erp_mileage.find_one({"id": mileage_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Trajet introuvable")
        km = _distance(data)
        update = {
            **data.model_dump(),
            "distance_km": km,
            "amount": round(km * float(data.rate or DEFAULT_RATE), 2),
            "updated_at": _now(),
        }
        await db.erp_mileage.update_one({"id": mileage_id}, {"$set": update})
        doc = await db.erp_mileage.find_one({"id": mileage_id}, {"_id": 0})
        return Mileage(**doc)

    @router.delete("/mileage/{mileage_id}")
    async def delete_mileage(mileage_id: str, _: dict = Depends(auth_dep)):
        res = await db.erp_mileage.delete_one({"id": mileage_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Trajet introuvable")
        return {"deleted": mileage_id}

    async def _annual_data(year: int) -> dict:
        cur = db.erp_mileage.find(
            {"date": {"$gte": f"{year}-01-01", "$lt": f"{year + 1}-01-01"}}, {"_id": 0})
        rows = [d async for d in cur]
        months = []
        from erp_pdf import _MONTHS_FR
        for i in range(12):
            mk = f"{year}-{i + 1:02d}"
            mrows = [r for r in rows if str(r.get("date", "")).startswith(mk)]
            months.append({
                "month": mk, "label": _MONTHS_FR[i],
                "count": len(mrows),
                "km": round(sum(float(r.get("distance_km", 0)) for r in mrows), 1),
                "amount": round(sum(float(r.get("amount", 0)) for r in mrows), 2),
            })
        by = {}
        for r in rows:
            name = r.get("client_name") or "—"
            b = by.setdefault(name, {"client": name, "km": 0.0, "amount": 0.0})
            b["km"] += float(r.get("distance_km", 0))
            b["amount"] += float(r.get("amount", 0))
        by_client = sorted(
            [{"client": v["client"], "km": round(v["km"], 1), "amount": round(v["amount"], 2)}
             for v in by.values()], key=lambda x: -x["amount"])
        totals = {
            "count": len(rows),
            "total_km": round(sum(float(r.get("distance_km", 0)) for r in rows), 1),
            "total_amount": round(sum(float(r.get("amount", 0)) for r in rows), 2),
        }
        return {"year": year, "by_month": months, "by_client": by_client, "totals": totals}

    @router.get("/mileage/annual")
    async def mileage_annual(year: Optional[int] = None, _: dict = Depends(auth_dep)):
        if not year:
            year = datetime.now(timezone.utc).year
        return await _annual_data(year)

    @router.get("/mileage/annual.pdf")
    async def mileage_annual_pdf(year: Optional[int] = None, _: dict = Depends(auth_dep)):
        if not year:
            year = datetime.now(timezone.utc).year
        data = await _annual_data(year)
        pdf = await asyncio.to_thread(
            render_mileage_annual_pdf, year, data["by_month"], data["by_client"], data["totals"])
        return Response(
            content=pdf, media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="rapport-km-annuel-{year}.pdf"'},
        )

    @router.get("/mileage/{mileage_id}/report.pdf")
    async def mileage_trip_pdf(mileage_id: str, _: dict = Depends(auth_dep)):
        entry = await db.erp_mileage.find_one({"id": mileage_id}, {"_id": 0})
        if not entry:
            raise HTTPException(404, "Trajet introuvable")
        client = await _client_snapshot(entry.get("client_id"), entry.get("client_name"))
        pdf = await asyncio.to_thread(render_mileage_trip_pdf, entry, client)
        return Response(
            content=pdf, media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{entry.get("ref", "rapport")}.pdf"'},
        )

    @router.get("/mileage/report.pdf")
    async def mileage_statement_pdf(
        month: Optional[str] = Query(default=None),
        client_id: Optional[str] = Query(default=None),
        _: dict = Depends(auth_dep),
    ):
        if not month:
            month = datetime.now(timezone.utc).strftime("%Y-%m")
        query: dict = {"date": {"$gte": f"{month}-01", "$lt": f"{month}-32"}}
        if client_id:
            query["client_id"] = client_id
        cur = db.erp_mileage.find(query, {"_id": 0}).sort("date", 1)
        entries = [d async for d in cur]
        client = None
        if client_id:
            client = await _client_snapshot(client_id, entries[0].get("client_name") if entries else None)
        pdf = await asyncio.to_thread(
            render_mileage_statement_pdf, entries, period_label=month, client=client)
        return Response(
            content=pdf, media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="releve-km-{month}.pdf"'},
        )

    @router.post("/mileage/invoice", status_code=201)
    async def mileage_to_invoice(
        month: Optional[str] = Query(default=None),
        client_id: str = Query(...),
        _: dict = Depends(auth_dep),
    ):
        """Transforme les trajets NON facturés d'un client (pour le mois) en
        une facture brouillon (1 ligne résumée, avec TPS/TVQ). Marque les
        trajets comme facturés."""
        if not month:
            month = datetime.now(timezone.utc).strftime("%Y-%m")
        party = await db.erp_parties.find_one({"id": client_id}, {"_id": 0})
        if not party:
            raise HTTPException(404, "Client introuvable")
        query = {
            "client_id": client_id,
            "date": {"$gte": f"{month}-01", "$lt": f"{month}-32"},
            "invoiced_id": {"$in": [None]},
        }
        cur = db.erp_mileage.find(query, {"_id": 0}).sort("date", 1)
        trips = [d async for d in cur]
        if not trips:
            raise HTTPException(400, "Aucun trajet non facturé pour ce client ce mois-ci.")
        total_km = round(sum(float(t.get("distance_km") or 0) for t in trips), 1)
        total_amount = round(sum(float(t.get("amount") or 0) for t in trips), 2)
        km_str = f"{total_km:.1f}".replace(".", ",")
        desc = f"Frais de déplacement — {km_str} km ({month}, {len(trips)} trajet(s))"
        items = [LineItem(description=desc, quantity=1, unit_price=total_amount, total=total_amount)]
        subtotal, tps, tvq, total = compute_totals(items, True)
        number = await _next("invoice")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        inv = Invoice(
            number=number,
            customer_id=client_id,
            customer_snapshot=party,
            date=today,
            items=items,
            subtotal=subtotal, tps=tps, tvq=tvq, total=total,
            taxable=True,
            status="brouillon",
            notes=f"Facture générée automatiquement à partir du relevé kilométrique de {month}.",
        )
        await db.erp_invoices.insert_one(inv.model_dump())
        await db.erp_mileage.update_many(
            {"id": {"$in": [t["id"] for t in trips]}},
            {"$set": {"invoiced_id": inv.id, "invoiced_number": number,
                      "updated_at": _now()}},
        )
        return {"invoice_id": inv.id, "number": number, "trips": len(trips),
                "subtotal": subtotal, "total": total}
