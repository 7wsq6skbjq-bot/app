"""États de compte (customer statements of account) + monthly auto-send.

Groups a customer's UNPAID invoices (status == "envoyée") into a branded PDF,
downloadable or emailed. Supports per-customer send, bulk "send to all
customers with a balance due", and an automatic monthly run.
"""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr

from erp_helpers import send_pdf_email
from erp_pdf import render_statement_pdf

logger = logging.getLogger("portech.erp.statements")

UNPAID_STATUSES = ("envoyée",)


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _cust_key(inv: dict) -> str | None:
    cid = inv.get("customer_id")
    if cid:
        return f"id:{cid}"
    email = ((inv.get("customer_snapshot") or {}).get("email") or "").strip().lower()
    if email:
        return f"email:{email}"
    return None


async def unpaid_groups(db) -> dict:
    """Return {key: {name, email, invoices[], balance}} for unpaid invoices."""
    cur = db.erp_invoices.find(
        {"status": {"$in": list(UNPAID_STATUSES)}}, {"_id": 0}
    ).sort("number", 1)
    groups: dict = {}
    async for inv in cur:
        key = _cust_key(inv)
        if not key:
            continue
        snap = inv.get("customer_snapshot") or {}
        g = groups.setdefault(key, {
            "key": key, "customer_id": inv.get("customer_id"),
            "name": snap.get("name") or "Client",
            "email": (snap.get("email") or "").strip(),
            "invoices": [], "balance": 0.0,
        })
        g["invoices"].append(inv)
        _eff = inv.get("balance_due")
        if _eff is None or not inv.get("deposit_received"):
            _eff = float(inv.get("total") or 0)
        g["balance"] += float(_eff or 0)
        if snap.get("email") and not g["email"]:
            g["email"] = snap["email"].strip()
    return groups


async def send_statement_email(g: dict, to_email: str,
                                subject: str | None = None,
                                message: str | None = None) -> None:
    pdf = await asyncio.to_thread(
        render_statement_pdf, {"name": g["name"], "email": g["email"]},
        g["invoices"], as_of=_today(), only_unpaid=True,
    )
    subj = subject or f"Portech — État de compte ({_today()})"
    html = message or (
        f"<p>Bonjour {g['name']},</p>"
        f"<p>Vous trouverez ci-joint votre état de compte à jour. "
        f"Le solde total dû est de <b>{g['balance']:.2f} $ CAD</b> "
        f"({len(g['invoices'])} facture(s)).</p>"
        "<p>Pour toute question ou pour régler votre solde, répondez "
        "simplement à ce courriel.</p>"
        "<p>Merci de votre confiance,<br/>L'équipe Portech</p>"
    )
    safe = (g["name"] or "client").replace(" ", "_")[:40]
    await send_pdf_email(
        to_email=to_email, subject=subj, html=html, pdf_bytes=pdf,
        filename=f"etat-compte-{safe}.pdf",
        footer_note=f"État de compte · {_today()} · Portech ERP",
    )


async def run_monthly_statements(db) -> dict:
    groups = await unpaid_groups(db)
    sent, skipped = 0, 0
    for g in groups.values():
        to_email = (g["email"] or "").strip()
        if not to_email:
            skipped += 1
            continue
        try:
            await send_statement_email(g, to_email)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("Monthly statement to %s failed: %s", g["name"], exc)
            skipped += 1
    logger.info("Monthly statements run: sent=%d skipped=%d", sent, skipped)
    return {"sent": sent, "skipped": skipped, "date": _today()}


def start_statements_scheduler(db: AsyncIOMotorDatabase) -> AsyncIOScheduler:
    """Send statements to all customers with a balance on the 1st @ 09:00."""
    sched = AsyncIOScheduler(timezone="America/Montreal")
    sched.add_job(run_monthly_statements, "cron", args=[db],
                  day=1, hour=9, minute=0,
                  id="erp_monthly_statements", replace_existing=True)
    sched.start()
    logger.info("Monthly statements scheduler started (1st @ 09:00 America/Montreal)")
    return sched


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    @router.get("/statements/customers")
    async def list_customers_with_balance(_: dict = Depends(auth_dep)):
        groups = await unpaid_groups(db)
        out = [{
            "key": g["key"], "customer_id": g["customer_id"], "name": g["name"],
            "email": g["email"], "invoice_count": len(g["invoices"]),
            "balance": round(g["balance"], 2),
        } for g in groups.values()]
        out.sort(key=lambda x: -x["balance"])
        return {"customers": out, "total_balance": round(sum(x["balance"] for x in out), 2)}

    async def _group_for_key(key: str) -> dict:
        groups = await unpaid_groups(db)
        g = groups.get(key)
        if not g:
            raise HTTPException(404, "Aucun solde dû pour ce client")
        return g

    @router.get("/statements/{key:path}/pdf")
    async def statement_pdf(key: str, _: dict = Depends(auth_dep)):
        g = await _group_for_key(key)
        pdf = await asyncio.to_thread(
            render_statement_pdf, {"name": g["name"], "email": g["email"]},
            g["invoices"], as_of=_today(), only_unpaid=True)
        safe = (g["name"] or "client").replace(" ", "_")[:40]
        return Response(content=pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="etat-compte-{safe}.pdf"'})

    class StatementSend(BaseModel):
        to_email: EmailStr | None = None
        subject: str | None = None
        message: str | None = None

    @router.post("/statements/{key:path}/send")
    async def send_statement(key: str, payload: StatementSend, _: dict = Depends(auth_dep)):
        g = await _group_for_key(key)
        to_email = (payload.to_email or g["email"] or "").strip()
        if not to_email:
            raise HTTPException(400, "Aucune adresse courriel pour ce client")
        await send_statement_email(g, to_email, payload.subject, payload.message)
        return {"sent": True, "to": to_email, "balance": round(g["balance"], 2)}

    @router.post("/statements/send-all")
    async def send_all_statements(_: dict = Depends(auth_dep)):
        groups = await unpaid_groups(db)
        sent, skipped = [], []
        for g in groups.values():
            to_email = (g["email"] or "").strip()
            if not to_email:
                skipped.append({"name": g["name"], "reason": "aucun courriel"})
                continue
            try:
                await send_statement_email(g, to_email)
                sent.append({"name": g["name"], "to": to_email, "balance": round(g["balance"], 2)})
            except Exception as exc:  # noqa: BLE001
                skipped.append({"name": g["name"], "reason": str(exc)})
        return {"sent_count": len(sent), "sent": sent, "skipped": skipped}
