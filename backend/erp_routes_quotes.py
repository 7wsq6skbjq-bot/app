"""Quote (soumission / devis) CRUD + PDF download + email + convert-to-invoice.

Mirrors the invoice pipeline (same shape, same helpers) but:
  * Uses `valid_until` instead of `due_date`
  * Statuses : brouillon / envoyée / acceptée / refusée / expirée / annulée
  * No overdue math, no reminder scheduler — a quote is a proposal, not a
    debt. When Cédrick marks it "acceptée" he can one-click convert into
    an invoice via `POST /admin/quotes/{id}/convert-to-invoice`.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from erp_helpers import compute_totals, csv_response, send_html_email, send_pdf_email
from erp_models import EmailSendRequest, Invoice, Party, Quote, QuoteIn
from erp_pdf import render_invoice_pdf, render_quote_pdf
from adams_rite_drawings import load_index, merge_drawing_pages
from quote_attachments import (
    append_files_to_pdf, delete_attachment, fetch_attachment, store_attachment,
)

logger = logging.getLogger("portech.erp.quotes")
QUOTE_FOLLOWUP_DAYS = 7

ALLOWED_ATTACH_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
MAX_ATTACH_BYTES = 15 * 1024 * 1024
ATTACH_MIME = {
    ".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp", ".heic": "image/heic",
    ".heif": "image/heif",
}


async def _quote_pdf_with_annexes(db, doc: dict) -> bytes:
    """Render the quote PDF then append Adams Rite pages + client attachments."""
    pdf_bytes = await asyncio.to_thread(render_quote_pdf, doc)
    if doc.get("drawing_pages"):
        pdf_bytes = await asyncio.to_thread(
            merge_drawing_pages, pdf_bytes, doc["drawing_pages"])
    atts = doc.get("attachments") or []
    if atts:
        files = []
        for a in atts:
            raw, ct = await fetch_attachment(db, a.get("id"))
            if raw is not None:
                files.append((raw, ct or a.get("content_type"), a.get("filename")))
        if files:
            pdf_bytes = await asyncio.to_thread(append_files_to_pdf, pdf_bytes, files)
    return pdf_bytes


async def run_quote_followups(db, days: int = QUOTE_FOLLOWUP_DAYS) -> dict:
    """Send a polite one-time follow-up to clients for quotes still 'envoyée'
    after `days` days without a response. Idempotent via `followup_sent_at`."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    cur = db.erp_quotes.find(
        {"status": "envoyée", "followup_sent_at": {"$in": [None, ""]},
         "created_at": {"$lte": cutoff}}, {"_id": 0})
    sent = 0
    async for q in cur:
        snap = q.get("customer_snapshot") or {}
        to_email = (snap.get("email") or "").strip()
        number = f"SO-{int(q.get('number', 0)):04d}"
        if not to_email:
            await db.erp_quotes.update_one(
                {"id": q["id"]},
                {"$set": {"followup_sent_at": datetime.now(timezone.utc).isoformat()}})
            continue
        html = (
            f"<p>Bonjour {snap.get('name') or ''},</p>"
            f"<p>Nous faisons un suivi concernant notre soumission <b>{number}</b> "
            f"(total estimé {float(q.get('total') or 0):.2f} $ CAD) que nous vous avons "
            "fait parvenir récemment. Avez-vous des questions ou souhaitez-vous aller "
            "de l'avant ?</p>"
            "<p>Nous restons disponibles pour ajuster la soumission au besoin. "
            "Il suffit de répondre à ce courriel.</p>"
            "<p>Cordialement,<br/>L'équipe Portech</p>"
        )
        try:
            await send_html_email(to_email=to_email,
                                  subject=f"Portech — Suivi de votre soumission {number}",
                                  html=html, footer_note=f"Suivi soumission {number}")
            await db.erp_quotes.update_one(
                {"id": q["id"]},
                {"$set": {"followup_sent_at": datetime.now(timezone.utc).isoformat()}})
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("Quote follow-up %s failed: %s", number, exc)
    logger.info("Quote follow-up run: sent=%d", sent)
    return {"sent": sent}


def start_quote_followup_scheduler(db: AsyncIOMotorDatabase) -> AsyncIOScheduler:
    """Daily @ 08:30 America/Montreal — follow up on unanswered sent quotes."""
    sched = AsyncIOScheduler(timezone="America/Montreal")
    sched.add_job(run_quote_followups, "cron", args=[db],
                  hour=8, minute=30, id="erp_quote_followups", replace_existing=True)
    sched.start()
    logger.info("Quote follow-up scheduler started (daily 08:30 America/Montreal)")
    return sched


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
            include_sales_conditions=data.include_sales_conditions,
            show_deposit=data.show_deposit,
            deposit_pct=data.deposit_pct,
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
            "include_sales_conditions": data.include_sales_conditions,
            "show_deposit": data.show_deposit,
            "deposit_pct": data.deposit_pct,
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
        pdf_bytes = await _quote_pdf_with_annexes(db, doc)
        filename = f"SO-{int(doc['number']):04d}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    # ── Attachments (client-chosen annex files) ──────────────────
    @router.post("/quotes/{quote_id}/attachments", response_model=Quote)
    async def add_quote_attachment(quote_id: str,
                                   file: UploadFile = File(...),
                                   _: dict = Depends(auth_dep)):
        from pathlib import Path as _P
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Soumission introuvable")
        ext = _P(file.filename or "").suffix.lower()
        if ext not in ALLOWED_ATTACH_EXTS:
            raise HTTPException(400, f"Format non supporté. Acceptés : {', '.join(sorted(ALLOWED_ATTACH_EXTS))}")
        raw = await file.read(MAX_ATTACH_BYTES + 1)
        if len(raw) > MAX_ATTACH_BYTES:
            raise HTTPException(413, f"Fichier trop volumineux (max {MAX_ATTACH_BYTES // 1024 // 1024} MB)")
        att_id = uuid.uuid4().hex
        content_type = file.content_type or ATTACH_MIME.get(ext, "application/octet-stream")
        await store_attachment(db, att_id=att_id, quote_id=quote_id,
                               filename=file.filename or f"annexe{ext}",
                               content_type=content_type, raw=raw)
        meta = {"id": att_id, "filename": file.filename or f"annexe{ext}",
                "content_type": content_type, "size": len(raw)}
        atts = (doc.get("attachments") or []) + [meta]
        await db.erp_quotes.update_one({"id": quote_id}, {"$set": {"attachments": atts}})
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        return Quote(**doc)

    @router.delete("/quotes/{quote_id}/attachments/{att_id}", response_model=Quote)
    async def remove_quote_attachment(quote_id: str, att_id: str,
                                      _: dict = Depends(auth_dep)):
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Soumission introuvable")
        await delete_attachment(db, att_id)
        atts = [a for a in (doc.get("attachments") or []) if a.get("id") != att_id]
        await db.erp_quotes.update_one({"id": quote_id}, {"$set": {"attachments": atts or None}})
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        return Quote(**doc)

    @router.post("/quotes/{quote_id}/send-email")
    async def send_quote_email(quote_id: str, payload: EmailSendRequest,
                                _: dict = Depends(auth_dep)):
        doc = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Soumission introuvable")
        pdf_bytes = await _quote_pdf_with_annexes(db, doc)
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
                "cost_price": it.get("cost_price"),
                "cost_category": it.get("cost_category"),
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
