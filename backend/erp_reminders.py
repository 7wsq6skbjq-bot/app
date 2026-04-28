"""
Automatic invoice reminders — 2 paliers (J+7 amical, J+30 ferme).

The scheduler runs daily at 08:00 America/Montreal and emails a reminder to
any invoice whose `due_date` is 7 or 30 days past *and* whose `status` is
'envoyée' (never to drafts or paid/cancelled invoices).

Idempotency is enforced by the `reminder_level_sent` field on each invoice
(values: 0, 7, 30). We only send a reminder for a level that hasn't been
sent yet. A manual admin endpoint `POST /admin/invoices/{id}/send-reminder`
is also exposed for testing or overrides.
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_helpers import send_pdf_email
from erp_pdf import render_invoice_pdf
from erp_models import EmailSendRequest  # noqa: F401 — re-exported for callers

logger = logging.getLogger("portech.erp.reminders")

# Tolerance window: we consider an invoice "7 days past due" if it's between
# 7 and 13 days past due (so a one-off missed run still catches it).
PALIERS = [
    {"level": 7, "window_days": (7, 13), "tone": "friendly"},
    {"level": 30, "window_days": (30, 999), "tone": "firm"},
]


def _days_past_due(due_date_iso: str | None, today: date) -> int | None:
    if not due_date_iso:
        return None
    try:
        due = datetime.strptime(due_date_iso[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return (today - due).days


def _friendly_message(invoice: dict, number: str, days: int) -> tuple[str, str]:
    cust = (invoice.get("customer_snapshot") or {}).get("name") or "Bonjour"
    total = float(invoice.get("total", 0))
    subject = f"Rappel — Facture {number} échue depuis {days} jour{'s' if days > 1 else ''}"
    html = (
        f"<p>Bonjour {cust},</p>"
        f"<p>Un petit rappel amical : la facture <b>{number}</b> "
        f"d'un montant de <b>{total:.2f} $ CAD</b> est échue depuis {days} jour"
        f"{'s' if days > 1 else ''}.</p>"
        "<p>Vous trouverez en pièce jointe une copie de la facture. "
        "Si le paiement a déjà été effectué, merci d'ignorer ce courriel.</p>"
        "<p>Pour toute question, répondez simplement à ce message.</p>"
        "<p>Cordialement,<br/>Portech</p>"
    )
    return subject, html


def _firm_message(invoice: dict, number: str, days: int) -> tuple[str, str]:
    cust = (invoice.get("customer_snapshot") or {}).get("name") or "Bonjour"
    total = float(invoice.get("total", 0))
    subject = f"[Important] Facture {number} — {days} jours de retard"
    html = (
        f"<p>Bonjour {cust},</p>"
        f"<p>Malgré notre précédent rappel, la facture <b>{number}</b> "
        f"d'un montant de <b>{total:.2f} $ CAD</b> est toujours impayée "
        f"après <b>{days} jours de retard</b>.</p>"
        "<p>Conformément à nos modalités (Net 30), des intérêts de "
        "<b>1,5 % par mois</b> s'appliquent sur le solde en souffrance à "
        "compter de ce jour.</p>"
        "<p>Merci de régulariser la situation dans les meilleurs délais, "
        "ou de nous contacter pour convenir d'un arrangement.</p>"
        "<p>Cordialement,<br/>Portech</p>"
    )
    return subject, html


async def send_reminder_for_invoice(
    db: AsyncIOMotorDatabase, invoice: dict, level: int,
) -> bool:
    """Send a reminder email for a specific invoice at the given palier level.
    Returns True on success, False otherwise. Updates the invoice record with
    `reminder_level_sent` and `last_reminder_sent_at`.
    """
    to_email = (invoice.get("customer_snapshot") or {}).get("email")
    if not to_email:
        logger.warning("Skip reminder for %s — no customer email", invoice.get("id"))
        return False

    number = f"FAC-{int(invoice['number']):04d}"
    days = level  # display exactly the palier label
    if level == 7:
        subject, html = _friendly_message(invoice, number, days)
    else:
        subject, html = _firm_message(invoice, number, days)

    pdf_bytes = await asyncio.to_thread(render_invoice_pdf, invoice)
    try:
        await send_pdf_email(
            to_email=to_email, subject=subject, html=html,
            pdf_bytes=pdf_bytes, filename=f"{number}.pdf",
        )
    except HTTPException as exc:
        logger.error("Reminder email failed for %s: %s", number, exc.detail)
        return False

    await db.erp_invoices.update_one(
        {"id": invoice["id"]},
        {"$set": {
            "reminder_level_sent": level,
            "last_reminder_sent_at": datetime.utcnow().isoformat(),
        }},
    )
    logger.info("Reminder sent %s level=%d to=%s", number, level, to_email)
    return True


async def run_daily_reminders(db: AsyncIOMotorDatabase) -> dict:
    """Scan all 'envoyée' invoices and send reminders for any that are due.
    Idempotent: only sends a palier that hasn't been sent yet for that invoice.
    """
    today = date.today()
    cursor = db.erp_invoices.find({"status": "envoyée"}, {"_id": 0})
    sent_count = 0
    skipped_count = 0
    async for inv in cursor:
        days = _days_past_due(inv.get("due_date"), today)
        if days is None or days < 7:
            continue
        already_sent = int(inv.get("reminder_level_sent", 0) or 0)

        # Choose the highest applicable palier not yet sent
        target = None
        for p in PALIERS:
            lo, hi = p["window_days"]
            if lo <= days <= hi and already_sent < p["level"]:
                target = p["level"]
        if target is None:
            skipped_count += 1
            continue
        ok = await send_reminder_for_invoice(db, inv, target)
        if ok:
            sent_count += 1
    logger.info("Daily reminder run: sent=%d skipped=%d", sent_count, skipped_count)
    return {"sent": sent_count, "skipped": skipped_count, "date": today.isoformat()}


def start_scheduler(db: AsyncIOMotorDatabase) -> AsyncIOScheduler:
    """Create and start the APScheduler that runs `run_daily_reminders` each
    morning at 08:00 America/Montreal. Returns the scheduler instance so the
    caller can shut it down cleanly on app shutdown."""
    sched = AsyncIOScheduler(timezone="America/Montreal")
    sched.add_job(
        run_daily_reminders, "cron",
        args=[db],
        hour=8, minute=0,
        id="erp_daily_reminders",
        replace_existing=True,
    )
    sched.start()
    logger.info("Invoice reminder scheduler started (daily 08:00 America/Montreal)")
    return sched


def register_routes(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    """Expose admin endpoints for manual triggering + status introspection."""

    @router.post("/invoices/{invoice_id}/send-reminder")
    async def send_reminder_manual(
        invoice_id: str,
        level: int = 7,
        _: dict = Depends(auth_dep),
    ):
        if level not in (7, 30):
            raise HTTPException(400, "Palier invalide (7 ou 30 seulement)")
        inv = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not inv:
            raise HTTPException(404, "Facture introuvable")
        if not (inv.get("customer_snapshot") or {}).get("email"):
            raise HTTPException(400, "Aucun courriel client sur cette facture")
        ok = await send_reminder_for_invoice(db, inv, level)
        if not ok:
            raise HTTPException(502, "Échec de l'envoi")
        return {"sent": True, "level": level, "invoice_id": invoice_id}

    @router.post("/reminders/run-now")
    async def run_reminders_now(_: dict = Depends(auth_dep)):
        """Manually trigger the full daily reminder scan (used for testing)."""
        return await run_daily_reminders(db)
