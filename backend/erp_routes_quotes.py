"""Quote (soumission / devis) CRUD + PDF download + email + convert-to-invoice.

Mirrors the invoice pipeline (same shape, same helpers) but:
  * Uses `valid_until` instead of `due_date`
  * Statuses : brouillon / envoyée / acceptée / refusée / expirée / annulée
  * No overdue math, no reminder scheduler — a quote is a proposal, not a
    debt. When Cédrick marks it "acceptée" he can one-click convert into
    an invoice via `POST /admin/quotes/{id}/convert-to-invoice`.
"""
import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from erp_helpers import compute_totals, csv_response, send_pdf_email
from erp_models import EmailSendRequest, Invoice, Party, Quote, QuoteIn
from erp_pdf import render_invoice_pdf, render_quote_pdf
from adams_rite_drawings import load_index, merge_drawing_pages


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep, next_number) -> None:
    @router.get("/quotes", response_model=List[Quote])
    async def list_quotes(_: dict = Depends(auth_dep)):
        cur = db.erp_quotes.find({}, {"_id": 0}).sort("number", -1)
        return [Quote(**d) async for d in cur]

    @router.post("/quotes", response_model=Quote, status_code=201)
    async def create_quote(data: QuoteIn, _: dict = Depends(auth_dep)):
        number = await next_number("quote")
        subtotal, tps, tvq, total = compute_totals(data.items, data.taxable)
        q = Quote(
            number=number,
            customer_id=data.customer_id,
            customer_snapshot=Party(**data.customer_snapshot.model_dump()),
            date=data.date,
            valid_until=data.valid_until,
            items=data.items,
            subtotal=subtotal, tps=tps, tvq=tvq, total=total,
            taxable=data.taxable, notes=data.notes, status=data.status,
            drawing_pages=data.drawing_pages,
        )
        await db.erp_quotes.insert_one(q.model_dump())
        return q

    @router.get("/quotes/{quote_id}", response_model=Quote)
    async def get_quote(quote_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Soumission introuvable")
        return Quote(**doc)

    @router.put("/quotes/{quote_id}", response_model=Quote)
    async def update_quote(quote_id: str, data: QuoteIn, _: dict = Depends(auth_dep)):
        existing = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Soumission introuvable")
        subtotal, tps, tvq, total = compute_totals(data.items, data.taxable)
        update_fields = {
            "customer_id": data.customer_id,
            "customer_snapshot": Party(**data.customer_snapshot.model_dump()).model_dump(),
            "date": data.date,
            "valid_until": data.valid_until,
            "items": [it.model_dump() for it in data.items],
            "subtotal": subtotal, "tps": tps, "tvq": tvq, "total": total,
            "taxable": data.taxable, "notes": data.notes, "status": data.status,
            "drawing_pages": data.drawing_pages,
        }
        await db.erp_quotes.update_one({"id": quote_id}, {"$set": update_fields})
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        return Quote(**doc)

    @router.delete("/quotes/{quote_id}")
    async def delete_quote(quote_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_quotes.delete_one({"id": quote_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Soumission introuvable")
        return {"deleted": quote_id}

    @router.get("/exports/quotes.csv")
    async def export_quotes_csv(_: dict = Depends(auth_dep)):
        quotes = await db.erp_quotes.find({}, {"_id": 0}).sort("number", -1).to_list(length=None)
        rows = []
        for q in quotes:
            cs = q.get("customer_snapshot") or {}
            rows.append({
                "Numéro": f"SO-{int(q.get('number', 0)):04d}",
                "Date": q.get("date") or "",
                "Valide jusqu'au": q.get("valid_until") or "",
                "Client": cs.get("name") or "",
                "Ville": cs.get("city") or "",
                "Courriel": cs.get("email") or "",
                "Sous-total": f"{q.get('subtotal', 0):.2f}",
                "TPS": f"{q.get('tps', 0):.2f}",
                "TVQ": f"{q.get('tvq', 0):.2f}",
                "Total": f"{q.get('total', 0):.2f}",
                "Statut": q.get("status") or "",
                "Notes": (q.get("notes") or "").replace("\n", " "),
            })
        return csv_response(rows, "soumissions-portech.csv")

    class DrawingsIn(BaseModel):
        pages: List[int] = []

    @router.patch("/quotes/{quote_id}/drawings", response_model=Quote)
    async def set_quote_drawings(quote_id: str, data: DrawingsIn,
                                 _: dict = Depends(auth_dep)):
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Soumission introuvable")
        pages = sorted({int(p) for p in data.pages})
        await db.erp_quotes.update_one(
            {"id": quote_id}, {"$set": {"drawing_pages": pages or None}})
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        return Quote(**doc)

    @router.get("/adams-rite/drawings")
    async def adams_rite_drawings(_: dict = Depends(auth_dep)):
        """Available Adams Rite Parts Manual drawings (label → printed page)."""
        return {"drawings": list(load_index())}

    @router.get("/quotes/{quote_id}/pdf")
    async def download_quote_pdf(quote_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Soumission introuvable")
        pdf_bytes = await asyncio.to_thread(render_quote_pdf, doc)
        if doc.get("drawing_pages"):
            pdf_bytes = await asyncio.to_thread(
                merge_drawing_pages, pdf_bytes, doc["drawing_pages"])
        filename = f"SO-{int(doc['number']):04d}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    @router.post("/quotes/{quote_id}/send-email")
    async def send_quote_email(quote_id: str, payload: EmailSendRequest,
                                _: dict = Depends(auth_dep)):
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Soumission introuvable")
        pdf_bytes = await asyncio.to_thread(render_quote_pdf, doc)
        if doc.get("drawing_pages"):
            pdf_bytes = await asyncio.to_thread(
                merge_drawing_pages, pdf_bytes, doc["drawing_pages"])
        number = f"SO-{int(doc['number']):04d}"
        cust = (doc.get("customer_snapshot") or {}).get("name") or ""
        subject = payload.subject or f"Portech — Soumission {number}"
        message_html = payload.message or (
            f"<p>Bonjour {cust},</p>"
            f"<p>Suite à votre demande, vous trouverez en pièce jointe notre "
            f"soumission <b>{number}</b> d'un total estimé de "
            f"<b>{doc.get('total', 0):.2f} $ CAD</b> (taxes incluses).</p>"
            "<p>Cette soumission est valide 30 jours. Pour l'accepter, "
            "répondez simplement à ce courriel — nous ferons suivre les "
            "prochaines étapes.</p>"
            "<p>Cordialement,<br/>L'équipe Portech</p>"
        )
        await send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes, filename=f"{number}.pdf",
            footer_note=f"Soumission {number} · Portech ERP",
        )
        if doc.get("status") == "brouillon":
            await db.erp_quotes.update_one(
                {"id": quote_id}, {"$set": {"status": "envoyée"}},
            )
        return {"sent": True, "to": payload.to_email}

    @router.post("/quotes/{quote_id}/convert-to-invoice", response_model=Invoice)
    async def convert_quote_to_invoice(quote_id: str,
                                         _: dict = Depends(auth_dep)):
        """One-click convert an accepted quote into a draft invoice.

        Line items, customer, taxes and totals are copied over. The new
        invoice starts in `brouillon` so Cédrick can adjust the due date
        before sending it. The quote is marked `acceptée` and linked to
        the invoice via `converted_invoice_id`.
        """
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Soumission introuvable")
        if doc.get("converted_invoice_id"):
            raise HTTPException(400,
                "Cette soumission a déjà été convertie en facture.")

        inv_number = await next_number("invoice")
        # Rehydrate items as LineItem-shaped dicts (Invoice model expects list).
        items = [
            {
                "description": it.get("description") or "",
                "quantity": float(it.get("quantity") or 0),
                "unit_price": float(it.get("unit_price") or 0),
                "product_id": it.get("product_id"),
                "total": it.get("total"),
            }
            for it in (doc.get("items") or [])
        ]
        invoice_doc = {
            "id": __import__("uuid").uuid4().hex,
            "number": inv_number,
            "customer_id": doc.get("customer_id"),
            "customer_snapshot": doc.get("customer_snapshot") or {},
            "date": doc.get("date"),
            "due_date": None,
            "items": items,
            "subtotal": doc.get("subtotal", 0),
            "tps": doc.get("tps", 0),
            "tvq": doc.get("tvq", 0),
            "total": doc.get("total", 0),
            "taxable": doc.get("taxable", True),
            "notes": (doc.get("notes") or "")
                      + f"\n\n[Générée depuis SO-{int(doc['number']):04d}]",
            "status": "brouillon",
            "reminder_level_sent": 0,
            "last_reminder_sent_at": None,
            "created_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(),
        }
        await db.erp_invoices.insert_one(invoice_doc)
        await db.erp_quotes.update_one(
            {"id": quote_id},
            {"$set": {"status": "acceptée",
                       "converted_invoice_id": invoice_doc["id"]}},
        )
        return Invoice(**invoice_doc)
