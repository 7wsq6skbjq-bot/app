"""Shared helpers for the Portech ERP: tax math, counters, CSV, email, date parse."""
import asyncio
import base64
import csv
import html as _html_mod
import io
import logging
import os
import re
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

# Inbox that actually RECEIVES replies. The portech.info domain has no MX
# records (Resend is send-only) so a client clicking "Reply" on info@portech.info
# would bounce into the void — that's exactly the bug Cédrick reported (clients
# replying to POs/invoices and Cédrick never seeing it). We mirror the same
# default the prospection routes already use so replies all land in one inbox.
REPLY_TO_EMAIL = os.environ.get(
    "ERP_REPLY_TO_EMAIL",
    os.environ.get("LEADS_RECIPIENT_EMAIL", "portech.infos@gmail.com"),
)


# Matches any HTML tag the user might have typed deliberately ; if present we
# assume the caller already provided ready-to-send HTML and leave it alone.
_HTML_TAG_RE = re.compile(r"<\s*(p|br|div|table|ul|ol|li|h[1-6]|strong|em|b|i|a|img|hr)\b",
                          re.IGNORECASE)


def normalize_message_to_html(msg: str) -> str:
    """Convert a user-typed message into safe HTML preserving whitespace.

    The ERP UI (PO, BOL, invoice, supplier emails) is a plain `<textarea>` —
    when Cédrick presses Enter twice to make a blank line between paragraphs,
    those newlines must reach the recipient. Without conversion the HTML
    renderer collapses them and the supplier sees a wall of text.

    Behaviour :
      * If the input already contains an HTML tag (the route default messages
        are written in HTML) → return as-is. No double-escaping.
      * Otherwise : escape HTML entities, split on blank lines into <p>s,
        and convert remaining single newlines to <br/>. Preserve runs of
        spaces with &nbsp; chains so indentation doesn't collapse.
    """
    if not msg:
        return ""
    if _HTML_TAG_RE.search(msg):
        return msg
    # 1. Escape so the user can safely type <, > or & without breaking HTML.
    safe = _html_mod.escape(msg, quote=False)
    # 2. Preserve runs of >1 spaces (Outlook/Gmail collapse them otherwise).
    safe = re.sub(r" {2,}", lambda m: "&nbsp;" * len(m.group(0)), safe)
    # 3. Normalize newlines, split on blank line(s) → paragraphs.
    safe = safe.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n\s*\n", safe.strip("\n"))
    out_parts: list[str] = []
    for p in paragraphs:
        # Within a paragraph, single \n → <br/>
        p_html = p.replace("\n", "<br/>")
        out_parts.append(f'<p style="margin:0 0 12px 0;">{p_html}</p>')
    return "".join(out_parts)


# ---------- Branded email wrapper (matches prospection campaigns) ----------
def wrap_branded_email(body_html: str, footer_note: str = "") -> str:
    """Wrap a transactional email body with the same banner header/footer that
    the prospection campaign uses. Keeps look-and-feel consistent across ALL
    Portech outbound emails (POs, BOLs, invoices, reminders, expense recaps).

    `body_html` is the actual message content (Bonjour ... + paragraphs).
    `footer_note` is the small grey text under the bottom banner (e.g.,
    a unsubscribe hint or document number for traceability).
    """
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="font-family: Arial, Helvetica, sans-serif; background:#f4f4f5; padding:0; margin:0;">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; max-width:600px;">'
        '<tr><td><img src="https://portech.info/email/email-header.png" alt="Portech" '
        'style="display:block; width:100%; max-width:600px; height:auto; border:0;"/></td></tr>'
        '<tr><td style="padding:32px 32px 16px 32px; color:#0c182b; font-size:15px; line-height:1.6;">'
        + body_html
        + '<p style="margin:24px 0 4px 0;"><b><a href="tel:+14383764177" '
          'style="color:#0c182b; text-decoration:none;">438-376-4177</a></b></p>'
        + '<p style="margin:0 0 24px 0;"><a href="https://www.portech.info" '
          'style="color:#1d4ed8;">www.portech.info</a></p>'
        + '<p style="margin:16px 0 0 0;"><b>Cédrick Pimparé</b><br/>'
          'Portech — Quincaillerie et porte commerciale</p>'
        + '</td></tr>'
        + '<tr><td><img src="https://portech.info/email/email-footer.png" alt="Portech" '
          'style="display:block; width:100%; max-width:600px; height:auto; border:0;"/></td></tr>'
        + (
            '<tr><td style="padding:16px 32px; color:#71717a; font-size:11px; text-align:center;">'
            + footer_note + '</td></tr>'
            if footer_note else ''
        )
        + '</table></td></tr></table>'
    )


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
                        pdf_bytes: bytes, filename: str,
                        branded: bool = True,
                        footer_note: str = "") -> None:
    """Send a transactional email with a PDF attachment via Resend.

    If `branded=True` (default), the message HTML is wrapped with the Portech
    header/footer banners — same look-and-feel as the prospection campaign.
    Set `branded=False` to send raw HTML (used by tests or low-level callers).
    """
    if not resend.api_key:
        raise HTTPException(503, "Service courriel non configuré (RESEND_API_KEY manquante)")
    # Convert user-typed plain text (with line breaks / blank lines) into proper
    # HTML so suppliers / clients see the same layout that Cédrick typed.
    # If `html` already contains HTML tags, this is a no-op.
    html = normalize_message_to_html(html)
    final_html = wrap_branded_email(html, footer_note=footer_note) if branded else html
    params = {
        "from": f"Portech <{SENDER_EMAIL}>",
        "to": [to_email],
        "reply_to": REPLY_TO_EMAIL,
        "subject": subject,
        "html": final_html,
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
