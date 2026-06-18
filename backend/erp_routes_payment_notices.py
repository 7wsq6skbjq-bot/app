"""Payment-notice (avis de paiement / remittance advice) CRUD + PDF + email.

Lets Cédrick generate a branded document showing a supplier that their
invoice has been paid — eliminates the "you didn't pay us" follow-up
emails that arrive while the bank transfer is still in transit.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date as DateT, datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from erp_helpers import csv_response, send_pdf_email
from erp_models import Party
from erp_pdf import render_payment_notice_pdf


PaymentMethodT = Literal[
    "Virement bancaire (EFT)",
    "Chèque",
    "Carte de crédit",
    "Comptant",
    "Virement Interac",
    "Autre",
]


class PaymentNoticeItem(BaseModel):
    invoice_number: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = ""
    amount: float = Field(..., ge=0)


class PaymentNoticeIn(BaseModel):
    """Payload posted from the UI to create / update a notice."""
    supplier_id: Optional[str] = None
    supplier_snapshot: Party
    date: DateT = Field(default_factory=DateT.today)
    payment_date: DateT
    payment_method: PaymentMethodT = "Virement bancaire (EFT)"
    reference_number: Optional[str] = ""
    items: List[PaymentNoticeItem] = Field(default_factory=list)
    notes: Optional[str] = ""


class PaymentNotice(PaymentNoticeIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    notice_number: str = ""                            # AP-2026-001
    total: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    sent_to: Optional[str] = None


class PaymentNoticeEmailRequest(BaseModel):
    to_email: EmailStr
    subject: Optional[str] = None
    message: Optional[str] = None


def _format_number(year: int, seq: int) -> str:
    return f"AP-{year}-{seq:03d}"


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    async def _next_notice_number() -> str:
        """Return the next AP-YYYY-NNN number for the current calendar year."""
        now = datetime.now(timezone.utc)
        year = now.year
        counter = await db.erp_counters.find_one_and_update(
            {"key": f"payment_notice_{year}"},
            {"$inc": {"seq": 1}},
            upsert=True, return_document=True,
        )
        return _format_number(year, counter.get("seq") or 1)

    def _compute_total(items: List[PaymentNoticeItem]) -> float:
        return round(sum(float(i.amount) for i in items), 2)

    # ─── Routes ────────────────────────────────────────────────
    @router.get("/payment-notices", response_model=List[PaymentNotice])
    async def list_notices(_: dict = Depends(auth_dep)):
        cur = db.erp_payment_notices.find({}, {"_id": 0}).sort("created_at", -1)
        return [PaymentNotice(**d) async for d in cur]

    @router.post("/payment-notices", response_model=PaymentNotice, status_code=201)
    async def create_notice(data: PaymentNoticeIn, _: dict = Depends(auth_dep)):
        notice = PaymentNotice(
            **data.model_dump(),
            notice_number=await _next_notice_number(),
            total=_compute_total(data.items),
        )
        await db.erp_payment_notices.insert_one(notice.model_dump(mode="json"))
        return notice

    @router.get("/payment-notices/{notice_id}", response_model=PaymentNotice)
    async def get_notice(notice_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_payment_notices.find_one({"id": notice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Avis de paiement introuvable")
        return PaymentNotice(**doc)

    @router.put("/payment-notices/{notice_id}", response_model=PaymentNotice)
    async def update_notice(notice_id: str, data: PaymentNoticeIn,
                             _: dict = Depends(auth_dep)):
        existing = await db.erp_payment_notices.find_one({"id": notice_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Avis de paiement introuvable")
        update_fields = data.model_dump(mode="json")
        update_fields["total"] = _compute_total(data.items)
        await db.erp_payment_notices.update_one(
            {"id": notice_id}, {"$set": update_fields},
        )
        doc = await db.erp_payment_notices.find_one({"id": notice_id}, {"_id": 0})
        return PaymentNotice(**doc)

    @router.delete("/payment-notices/{notice_id}", status_code=204)
    async def delete_notice(notice_id: str, _: dict = Depends(auth_dep)):
        res = await db.erp_payment_notices.delete_one({"id": notice_id})
        if not res.deleted_count:
            raise HTTPException(404, "Avis de paiement introuvable")
        return Response(status_code=204)

    @router.get("/payment-notices.csv")
    async def export_notices_csv(_: dict = Depends(auth_dep)):
        rows = []
        async for n in db.erp_payment_notices.find({}, {"_id": 0}).sort("created_at", -1):
            ss = n.get("supplier_snapshot") or {}
            rows.append({
                "Numéro": n.get("notice_number") or "",
                "Date émission": n.get("date") or "",
                "Date paiement": n.get("payment_date") or "",
                "Fournisseur": ss.get("name") or "",
                "Méthode": n.get("payment_method") or "",
                "Référence": n.get("reference_number") or "",
                "Total": f"{n.get('total', 0):.2f}",
                "Envoyé à": n.get("sent_to") or "",
            })
        return csv_response(rows, "avis-paiement-portech.csv")

    @router.get("/payment-notices/{notice_id}/pdf")
    async def download_notice_pdf(notice_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_payment_notices.find_one({"id": notice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Avis de paiement introuvable")
        pdf_bytes = await asyncio.to_thread(render_payment_notice_pdf, doc)
        filename = f"{doc.get('notice_number') or 'AP'}.pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.post("/payment-notices/{notice_id}/send-email")
    async def send_notice_email(notice_id: str,
                                  payload: PaymentNoticeEmailRequest,
                                  _: dict = Depends(auth_dep)):
        doc = await db.erp_payment_notices.find_one({"id": notice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Avis de paiement introuvable")

        pdf_bytes = await asyncio.to_thread(render_payment_notice_pdf, doc)
        number = doc.get("notice_number") or "AP"
        supplier = (doc.get("supplier_snapshot") or {}).get("name") or ""
        total = float(doc.get("total") or 0)

        subject = payload.subject or f"Portech — Avis de paiement {number}"
        message_html = payload.message or (
            f"<p>Bonjour {supplier},</p>"
            f"<p>Vous trouverez en pièce jointe notre <b>avis de paiement {number}</b> "
            f"confirmant le règlement d'un montant total de <b>{total:.2f} $ CAD</b>.</p>"
            "<p>Le paiement a été émis et devrait être crédité dans votre compte "
            "d'ici <b>3 à 5 jours ouvrables</b>. Vous pouvez utiliser le numéro de "
            "référence indiqué sur l'avis pour le rapprochement.</p>"
            "<p>Merci pour votre service.</p>"
        )

        await send_pdf_email(
            to_email=payload.to_email,
            subject=subject,
            html=message_html,
            pdf_bytes=pdf_bytes,
            filename=f"{number}.pdf",
            footer_note=f"Avis de paiement {number} · Portech ERP",
        )

        await db.erp_payment_notices.update_one(
            {"id": notice_id},
            {"$set": {
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_to": payload.to_email,
            }},
        )
        return {"sent": True, "to": payload.to_email}
