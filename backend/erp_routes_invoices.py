"""Invoice CRUD + CSV export + PDF download + send-email routes."""
import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_helpers import compute_totals, csv_response, send_pdf_email
from erp_models import EmailSendRequest, Invoice, InvoiceIn, Party
from erp_pdf import render_invoice_pdf


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep, next_number) -> None:
    @router.get("/invoices", response_model=List[Invoice])
    async def list_invoices(_: dict = Depends(auth_dep)):
        cur = db.erp_invoices.find({}, {"_id": 0}).sort("number", -1)
        return [Invoice(**d) async for d in cur]

    @router.post("/invoices", response_model=Invoice, status_code=201)
    async def create_invoice(data: InvoiceIn, _: dict = Depends(auth_dep)):
        number = await next_number("invoice")
        subtotal, tps, tvq, total = compute_totals(data.items, data.taxable)
        inv = Invoice(
            number=number,
            customer_id=data.customer_id,
            customer_snapshot=Party(**data.customer_snapshot.model_dump()),
            date=data.date,
            due_date=data.due_date,
            items=data.items,
            subtotal=subtotal, tps=tps, tvq=tvq, total=total,
            taxable=data.taxable, notes=data.notes, status=data.status,
        )
        await db.erp_invoices.insert_one(inv.model_dump())
        return inv

    @router.get("/invoices/{invoice_id}", response_model=Invoice)
    async def get_invoice(invoice_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        return Invoice(**doc)

    @router.put("/invoices/{invoice_id}", response_model=Invoice)
    async def update_invoice(invoice_id: str, data: InvoiceIn, _: dict = Depends(auth_dep)):
        existing = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Facture introuvable")
        subtotal, tps, tvq, total = compute_totals(data.items, data.taxable)
        update_fields = {
            "customer_id": data.customer_id,
            "customer_snapshot": Party(**data.customer_snapshot.model_dump()).model_dump(),
            "date": data.date,
            "due_date": data.due_date,
            "items": [it.model_dump() for it in data.items],
            "subtotal": subtotal, "tps": tps, "tvq": tvq, "total": total,
            "taxable": data.taxable, "notes": data.notes, "status": data.status,
        }
        await db.erp_invoices.update_one({"id": invoice_id}, {"$set": update_fields})
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        return Invoice(**doc)

    @router.delete("/invoices/{invoice_id}")
    async def delete_invoice(invoice_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_invoices.delete_one({"id": invoice_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Facture introuvable")
        return {"deleted": invoice_id}

    @router.get("/exports/invoices.csv")
    async def export_invoices(_: dict = Depends(auth_dep)):
        invoices = await db.erp_invoices.find({}, {"_id": 0}).sort("number", -1).to_list(length=None)
        rows = []
        for i in invoices:
            cs = i.get("customer_snapshot") or {}
            rows.append({
                "Numéro": f"FAC-{int(i.get('number', 0)):04d}",
                "Date": i.get("date"),
                "Échéance": i.get("due_date") or "",
                "Client": cs.get("name") or "",
                "Ville": cs.get("city") or "",
                "Courriel": cs.get("email") or "",
                "Sous-total": f"{i.get('subtotal', 0):.2f}",
                "TPS": f"{i.get('tps', 0):.2f}",
                "TVQ": f"{i.get('tvq', 0):.2f}",
                "Total": f"{i.get('total', 0):.2f}",
                "Statut": i.get("status") or "",
                "Notes": (i.get("notes") or "").replace("\n", " "),
            })
        return csv_response(rows, "factures-portech.csv")

    @router.get("/invoices/{invoice_id}/pdf")
    async def download_invoice_pdf(invoice_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        pdf_bytes = await asyncio.to_thread(render_invoice_pdf, doc)
        filename = f"FAC-{int(doc['number']):04d}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.post("/invoices/{invoice_id}/send-email")
    async def send_invoice_email(invoice_id: str, payload: EmailSendRequest, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        pdf_bytes = await asyncio.to_thread(render_invoice_pdf, doc)
        number = f"FAC-{int(doc['number']):04d}"
        cust = (doc.get("customer_snapshot") or {}).get("name") or ""
        subject = payload.subject or f"Portech — Facture {number}"
        message_html = payload.message or (
            f"<p>Bonjour {cust},</p>"
            f"<p>Vous trouverez en pièce jointe votre facture <b>{number}</b> "
            f"d'un total de <b>{doc.get('total', 0):.2f} $ CAD</b>.</p>"
            "<p>Modalités : paiement net 30 jours.<br/>"
            "Pour toute question, répondez simplement à ce courriel.</p>"
            "<p>Cordialement,<br/>Portech</p>"
        )
        await send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes, filename=f"{number}.pdf",
        )
        if doc.get("status") == "brouillon":
            await db.erp_invoices.update_one(
                {"id": invoice_id}, {"$set": {"status": "envoyée"}},
            )
        return {"sent": True, "to": payload.to_email}
