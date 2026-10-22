"""Free-form branded email composer for the ERP.

Lets Cédrick send any client / supplier a fully branded email (same header /
footer banners as POs and invoices) directly from the ERP UI, with optional
file attachments and a recipient autocomplete fed from the Parties module.

Every send is logged in `erp_email_log` so the admin has a paper trail of
what went out, when, and to whom.
"""
from __future__ import annotations

import asyncio
import base64
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import resend
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from erp_helpers import (
    REPLY_TO_EMAIL,
    SENDER_EMAIL,
    banner_attachments,
    normalize_message_to_html,
    wrap_branded_email,
)


# Hard cap on attachment payload — Resend hard limit is 40 MB total, we leave
# some headroom for the HTML + headers. 20 MB total per email is plenty for
# shop drawings / invoices / photos.
MAX_TOTAL_ATTACHMENT_MB = 20


class ComposeAttachment(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    content_base64: str = Field(..., min_length=1)
    content_type: Optional[str] = None


class ComposeEmailRequest(BaseModel):
    to_email: EmailStr
    cc_email: Optional[EmailStr] = None
    subject: str = Field(..., min_length=1, max_length=300)
    message: str = Field(..., min_length=1, max_length=20_000)
    attachments: List[ComposeAttachment] = Field(default_factory=list)
    # Optional link to a customer/supplier record for the audit log
    party_id: Optional[str] = None
    party_name: Optional[str] = None


class EmailLogEntry(BaseModel):
    id: str
    sent_at: datetime
    to_email: str
    cc_email: Optional[str] = None
    subject: str
    message_excerpt: str
    attachment_filenames: List[str] = Field(default_factory=list)
    party_id: Optional[str] = None
    party_name: Optional[str] = None
    resend_id: Optional[str] = None
    status: str = "sent"          # sent | failed
    error: Optional[str] = None


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    @router.post("/compose-email", status_code=201)
    async def compose_and_send(payload: ComposeEmailRequest,
                                _: dict = Depends(auth_dep)):
        if not resend.api_key:
            raise HTTPException(503, "Service courriel non configuré (RESEND_API_KEY manquante)")

        # ── Validate attachment size budget ──────────────────────
        total_bytes = 0
        decoded_atts: list[dict] = []
        for att in payload.attachments:
            try:
                raw = base64.b64decode(att.content_base64, validate=False)
            except Exception:
                raise HTTPException(400, f"Pièce jointe « {att.filename} » illisible (base64 invalide).")
            total_bytes += len(raw)
            decoded_atts.append({"filename": att.filename, "raw": raw,
                                  "content_type": att.content_type})
        if total_bytes > MAX_TOTAL_ATTACHMENT_MB * 1024 * 1024:
            raise HTTPException(
                413,
                f"Pièces jointes trop volumineuses ({total_bytes / 1024 / 1024:.1f} MB). "
                f"Maximum {MAX_TOTAL_ATTACHMENT_MB} MB au total.",
            )

        # ── Build branded HTML ───────────────────────────────────
        body_html = normalize_message_to_html(payload.message)
        footer_note = f"Courriel envoyé via Portech ERP · {payload.to_email}"
        final_html = wrap_branded_email(body_html, footer_note=footer_note)

        # ── Build Resend params ──────────────────────────────────
        params = {
            "from": f"Portech <{SENDER_EMAIL}>",
            "to": [payload.to_email],
            "reply_to": REPLY_TO_EMAIL,
            "subject": payload.subject,
            "html": final_html,
        }
        if payload.cc_email:
            params["cc"] = [payload.cc_email]
        # Inline header/footer banners (CID) + any user attachments.
        params["attachments"] = banner_attachments() + [
            {
                "filename": a["filename"],
                "content": base64.b64encode(a["raw"]).decode("ascii"),
            }
            for a in decoded_atts
        ]

        # ── Send and log ─────────────────────────────────────────
        log = EmailLogEntry(
            id=str(uuid.uuid4()),
            sent_at=datetime.now(timezone.utc),
            to_email=payload.to_email,
            cc_email=payload.cc_email,
            subject=payload.subject,
            message_excerpt=payload.message.strip()[:200],
            attachment_filenames=[a["filename"] for a in decoded_atts],
            party_id=payload.party_id,
            party_name=payload.party_name,
        )
        try:
            result = await asyncio.to_thread(resend.Emails.send, params)
            log.resend_id = result.get("id") if isinstance(result, dict) else None
            log.status = "sent"
        except Exception as exc:
            log.status = "failed"
            log.error = str(exc)[:500]
            await db.erp_email_log.insert_one(log.model_dump())
            raise HTTPException(502, f"Échec de l'envoi : {exc}")

        await db.erp_email_log.insert_one(log.model_dump())
        return {"id": log.id, "resend_id": log.resend_id, "status": "sent",
                "to": payload.to_email}

    @router.get("/compose-email/log", response_model=List[EmailLogEntry])
    async def list_email_log(limit: int = 30, _: dict = Depends(auth_dep)):
        cur = db.erp_email_log.find({}, {"_id": 0}).sort("sent_at", -1).limit(max(1, min(limit, 200)))
        return [EmailLogEntry(**d) async for d in cur]
