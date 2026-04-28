"""Shared helpers for the Portech ERP: tax math, counters, CSV, email, date parse."""
import asyncio
import base64
import csv
import io
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import resend
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from erp_models import LineItem, TPS_RATE, TVQ_RATE

logger = logging.getLogger("portech.erp")

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")


# ---------- Tax math ----------
def compute_totals(items: List[LineItem], taxable: bool = True):
    """Mutate items in place to set .total, then return (subtotal, tps, tvq, total)."""
    for it in items:
        it.total = round(it.quantity * it.unit_price, 2)
    subtotal = round(sum((it.total or 0) for it in items), 2)
    if taxable:
        tps = round(subtotal * TPS_RATE, 2)
        tvq = round(subtotal * TVQ_RATE, 2)
    else:
        tps = 0.0
        tvq = 0.0
    total = round(subtotal + tps + tvq, 2)
    return subtotal, tps, tvq, total


# ---------- Sequential numbering ----------
def make_next_number_fn(db: AsyncIOMotorDatabase):
    """Return an async `next_number(counter_type)` closure bound to the given DB."""
    async def next_number(counter_type: str) -> int:
        doc = await db.counters.find_one_and_update(
            {"type": counter_type},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(doc["value"])
    return next_number


# ---------- CSV ----------
def csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    if not rows:
        return StreamingResponse(
            iter([""]), media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------- Email ----------
async def send_pdf_email(*, to_email: str, subject: str, html: str,
                        pdf_bytes: bytes, filename: str) -> None:
    """Send a transactional email with a PDF attachment via Resend."""
    if not resend.api_key:
        raise HTTPException(503, "Service courriel non configuré (RESEND_API_KEY manquante)")
    params = {
        "from": f"Portech <{SENDER_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "html": html,
        "attachments": [{
            "filename": filename,
            "content": base64.b64encode(pdf_bytes).decode("ascii"),
        }],
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info("ERP email sent id=%s to=%s", result.get("id"), to_email)
    except Exception as exc:
        logger.error("ERP email failed: %s", exc)
        raise HTTPException(502, f"Échec de l'envoi : {exc}")


# ---------- Date parsing ----------
def parse_date_safe(d) -> Optional[datetime]:
    """Parse an ISO date string (YYYY-MM-DD) into a tz-aware datetime, or None."""
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None
