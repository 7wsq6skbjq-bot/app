"""Bill-of-Lading CRUD + CSV export + PDF download + send-email routes."""
import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_helpers import csv_response, send_pdf_email
from erp_models import BillOfLading, BillOfLadingIn, EmailSendRequest, Party
from erp_pdf import render_bol_pdf


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep, next_number) -> None:
    @router.get("/bills-of-lading", response_model=List[BillOfLading])
    async def list_bols(_: dict = Depends(auth_dep)):
        cur = db.erp_bills_of_lading.find({}, {"_id": 0}).sort("number", -1)
        return [BillOfLading(**d) async for d in cur]

    @router.post("/bills-of-lading", response_model=BillOfLading, status_code=201)
    async def create_bol(data: BillOfLadingIn, _: dict = Depends(auth_dep)):
        number = await next_number("bill_of_lading")
        bol = BillOfLading(
            number=number,
            shipper_snapshot=Party(**data.shipper_snapshot.model_dump()),
            consignee_snapshot=Party(**data.consignee_snapshot.model_dump()),
            carrier=data.carrier,
            date=data.date,
            expected_delivery=data.expected_delivery,
            items=data.items,
            total_weight_kg=data.total_weight_kg,
            special_instructions=data.special_instructions,
            status=data.status,
        )
        await db.erp_bills_of_lading.insert_one(bol.model_dump())
        return bol

    @router.get("/bills-of-lading/{bol_id}", response_model=BillOfLading)
    async def get_bol(bol_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Connaissement introuvable")
        return BillOfLading(**doc)

    @router.put("/bills-of-lading/{bol_id}", response_model=BillOfLading)
    async def update_bol(bol_id: str, data: BillOfLadingIn, _: dict = Depends(auth_dep)):
        existing = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Connaissement introuvable")
        update_fields = {
            "shipper_snapshot": Party(**data.shipper_snapshot.model_dump()).model_dump(),
            "consignee_snapshot": Party(**data.consignee_snapshot.model_dump()).model_dump(),
            "carrier": data.carrier,
            "date": data.date,
            "expected_delivery": data.expected_delivery,
            "items": [it.model_dump() for it in data.items],
            "total_weight_kg": data.total_weight_kg,
            "special_instructions": data.special_instructions,
            "status": data.status,
        }
        await db.erp_bills_of_lading.update_one({"id": bol_id}, {"$set": update_fields})
        doc = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        return BillOfLading(**doc)

    @router.delete("/bills-of-lading/{bol_id}")
    async def delete_bol(bol_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_bills_of_lading.delete_one({"id": bol_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Connaissement introuvable")
        return {"deleted": bol_id}

    @router.get("/exports/bills-of-lading.csv")
    async def export_bols(_: dict = Depends(auth_dep)):
        rows_db = await db.erp_bills_of_lading.find({}, {"_id": 0}).sort("number", -1).to_list(length=None)
        rows = []
        for b in rows_db:
            sh = b.get("shipper_snapshot") or {}
            cn = b.get("consignee_snapshot") or {}
            rows.append({
                "Numéro": f"CONN-{int(b.get('number', 0)):04d}",
                "Date": b.get("date"),
                "Livraison attendue": b.get("expected_delivery") or "",
                "Expéditeur": sh.get("name") or "",
                "Destinataire": cn.get("name") or "",
                "Transporteur": b.get("carrier") or "",
                "Poids total (kg)": b.get("total_weight_kg") or "",
                "Statut": b.get("status") or "",
            })
        return csv_response(rows, "connaissements-portech.csv")

    @router.get("/bills-of-lading/{bol_id}/pdf")
    async def download_bol_pdf(bol_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Connaissement introuvable")
        pdf_bytes = await asyncio.to_thread(render_bol_pdf, doc)
        filename = f"CONN-{int(doc['number']):04d}.pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.post("/bills-of-lading/{bol_id}/send-email")
    async def send_bol_email(bol_id: str, payload: EmailSendRequest, _: dict = Depends(auth_dep)):
        doc = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Connaissement introuvable")
        pdf_bytes = await asyncio.to_thread(render_bol_pdf, doc)
        number = f"CONN-{int(doc['number']):04d}"
        consignee = (doc.get("consignee_snapshot") or {}).get("name") or ""
        subject = payload.subject or f"Portech — Connaissement {number}"
        message_html = payload.message or (
            f"<p>Bonjour {consignee},</p>"
            f"<p>Vous trouverez en pièce jointe le connaissement <b>{number}</b> "
            "couvrant l'expédition à venir.</p>"
            "<p>Cordialement,<br/>Portech</p>"
        )
        await send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes, filename=f"{number}.pdf",
        )
        if doc.get("status") == "brouillon":
            await db.erp_bills_of_lading.update_one(
                {"id": bol_id}, {"$set": {"status": "expédié"}},
            )
        return {"sent": True, "to": payload.to_email}
