"""Récapitulatif trimestriel TPS/TVQ — à remettre au comptable.

Regroupe, pour un trimestre civil (T1 jan-mar, T2 avr-juin, T3 juil-sep,
T4 oct-déc) :
  * TAXES PERÇUES  : factures émises (statut envoyée + payée) datées dans la période
  * CRÉDITS DE TAXE : taxes payées sur les dépenses enregistrées dans la période
  * NET à remettre  : perçu − payé (par TPS et TVQ)

Endpoints (sous /api/admin) :
  GET  /tax-recap?year=&quarter=  -> JSON résumé + années disponibles
  GET  /tax-recap/pdf?year=&quarter=  -> PDF brandé (aperçu inline)
"""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from erp_pdf import render_tax_recap_pdf

logger = logging.getLogger("portech.erp.tax_recap")
_TAX_SETTINGS_KEY = "tax_recap"

COLLECTED_STATUSES = ("envoyée", "payée")
_MONTH_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]
_QUARTER_MONTHS = {1: "janvier à mars", 2: "avril à juin",
                   3: "juillet à septembre", 4: "octobre à décembre"}


def _quarter_bounds(year: int, quarter: int) -> tuple[str, str, str]:
    """Return (start_iso_inclusive, end_iso_inclusive, end_exclusive_iso)."""
    m0 = (quarter - 1) * 3 + 1          # 1,4,7,10
    start = f"{year:04d}-{m0:02d}-01"
    if quarter == 4:
        end_excl = f"{year + 1:04d}-01-01"
    else:
        end_excl = f"{year:04d}-{m0 + 3:02d}-01"
    # last day = end_excl minus 1 day (string display only)
    from datetime import date, timedelta
    ex = date.fromisoformat(end_excl)
    last = ex - timedelta(days=1)
    return start, last.isoformat(), end_excl


def _date_fr(iso: str) -> str:
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d")
        return f"{d.day} {_MONTH_FR[d.month - 1]} {d.year}"
    except Exception:
        return iso


async def _compute_core(db, start, end_incl, end_excl, period_label, year, quarter) -> dict:
    inv_cur = db.erp_invoices.find(
        {"status": {"$in": list(COLLECTED_STATUSES)},
         "date": {"$gte": start, "$lt": end_excl}},
        {"_id": 0, "subtotal": 1, "tps": 1, "tvq": 1, "total": 1})
    col = {"subtotal": 0.0, "tps": 0.0, "tvq": 0.0, "total": 0.0, "count": 0}
    async for r in inv_cur:
        col["subtotal"] += float(r.get("subtotal") or 0)
        col["tps"] += float(r.get("tps") or 0)
        col["tvq"] += float(r.get("tvq") or 0)
        col["total"] += float(r.get("total") or 0)
        col["count"] += 1

    exp_cur = db.erp_expenses.find(
        {"date": {"$gte": start, "$lt": end_excl}},
        {"_id": 0, "subtotal": 1, "tps": 1, "tvq": 1, "total": 1})
    paid = {"subtotal": 0.0, "tps": 0.0, "tvq": 0.0, "total": 0.0, "count": 0}
    async for r in exp_cur:
        paid["subtotal"] += float(r.get("subtotal") or 0)
        paid["tps"] += float(r.get("tps") or 0)
        paid["tvq"] += float(r.get("tvq") or 0)
        paid["total"] += float(r.get("total") or 0)
        paid["count"] += 1

    for blk in (col, paid):
        for k in ("subtotal", "tps", "tvq", "total"):
            blk[k] = round(blk[k], 2)

    net = {
        "tps": round(col["tps"] - paid["tps"], 2),
        "tvq": round(col["tvq"] - paid["tvq"], 2),
    }
    net["total"] = round(net["tps"] + net["tvq"], 2)

    return {
        "year": year, "quarter": quarter,
        "period_label": period_label,
        "start": start, "end": end_incl,
        "start_fr": _date_fr(start), "end_fr": _date_fr(end_incl),
        "collected": col, "paid": paid, "net": net,
    }


async def _compute(db, year: int, quarter: int) -> dict:
    start, end_incl, end_excl = _quarter_bounds(year, quarter)
    return await _compute_core(
        db, start, end_incl, end_excl,
        f"T{quarter} {year} ({_QUARTER_MONTHS[quarter]})", year, quarter)


async def _compute_range(db, start: str, end: str) -> dict:
    from datetime import date, timedelta
    import re as _re
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", start) or not _re.match(r"^\d{4}-\d{2}-\d{2}$", end):
        raise HTTPException(400, "Dates invalides (format attendu : AAAA-MM-JJ).")
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    if s > e:
        s, e = e, s
    end_excl = (e + timedelta(days=1)).isoformat()
    label = f"Du {_date_fr(s.isoformat())} au {_date_fr(e.isoformat())}"
    return await _compute_core(db, s.isoformat(), e.isoformat(), end_excl, label, s.year, 0)


async def _available_years(db) -> list[int]:
    years: set[int] = set()
    for coll in (db.erp_invoices, db.erp_expenses):
        for d in await coll.distinct("date"):
            if isinstance(d, str) and len(d) >= 4 and d[:4].isdigit():
                years.add(int(d[:4]))
    now_year = datetime.now(timezone.utc).year
    years.add(now_year)
    return sorted(years, reverse=True)


async def _get_accountant_email(db) -> str:
    doc = await db.erp_settings.find_one({"key": _TAX_SETTINGS_KEY}, {"_id": 0})
    return ((doc or {}).get("accountant_email") or "").strip()


def _recap_email_html(data: dict) -> str:
    col = data["collected"]
    paid = data["paid"]
    net = data["net"]
    net_total = net["total"]
    net_line = (f"<b>Montant net à remettre : {net_total:,.2f} $</b>"
                if net_total >= 0
                else f"<b>Remboursement net attendu : {abs(net_total):,.2f} $</b>")
    return (
        f"<p>Bonjour,</p>"
        f"<p>Voici le récapitulatif des taxes pour la période "
        f"<b>{data['period_label']}</b> ({data['start_fr']} au {data['end_fr']}).</p>"
        f"<p><b>Taxes perçues (ventes)</b> — TPS {col['tps']:,.2f} $ · TVQ {col['tvq']:,.2f} $ "
        f"({col['count']} facture(s))<br/>"
        f"<b>Crédits de taxe (achats)</b> — TPS {paid['tps']:,.2f} $ · TVQ {paid['tvq']:,.2f} $ "
        f"({paid['count']} dépense(s))<br/>"
        f"<b>Net</b> — TPS {net['tps']:,.2f} $ · TVQ {net['tvq']:,.2f} $</p>"
        f"<p>{net_line}</p>"
        f"<p>Le rapport détaillé est en pièce jointe (PDF).</p>"
        f"<p style='color:#8a97a8;font-size:12px'>Document à titre indicatif, basé sur les "
        f"factures émises et les dépenses enregistrées. À valider avant toute déclaration "
        f"officielle à Revenu Québec / ARC.</p>"
    )


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    def _now_quarter() -> tuple[int, int]:
        n = datetime.now(timezone.utc)
        return n.year, (n.month - 1) // 3 + 1

    @router.get("/tax-recap")
    async def tax_recap(year: int | None = None, quarter: int | None = None,
                        start: str | None = None, end: str | None = None,
                        _: dict = Depends(auth_dep)):
        if start and end:
            data = await _compute_range(db, start, end)
        else:
            y, q = _now_quarter()
            year = year or y
            quarter = quarter or q
            if quarter < 1 or quarter > 4:
                raise HTTPException(400, "Trimestre invalide (1-4).")
            data = await _compute(db, year, quarter)
        data["available_years"] = await _available_years(db)
        return data

    @router.get("/tax-recap/pdf")
    async def tax_recap_pdf(year: int | None = None, quarter: int | None = None,
                            start: str | None = None, end: str | None = None,
                            _: dict = Depends(auth_dep)):
        if start and end:
            data = await _compute_range(db, start, end)
            fname = f"recap-tps-tvq-{data['start']}_au_{data['end']}.pdf"
        else:
            y, q = _now_quarter()
            year = year or y
            quarter = quarter or q
            if quarter < 1 or quarter > 4:
                raise HTTPException(400, "Trimestre invalide (1-4).")
            data = await _compute(db, year, quarter)
            fname = f"recap-tps-tvq-T{quarter}-{year}.pdf"
        pdf = await asyncio.to_thread(render_tax_recap_pdf, data)
        return Response(content=pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{fname}"'})

    @router.get("/tax-recap/settings")
    async def get_settings(_: dict = Depends(auth_dep)):
        return {"accountant_email": await _get_accountant_email(db)}

    class TaxSettingsIn(BaseModel):
        accountant_email: str = ""

    @router.put("/tax-recap/settings")
    async def put_settings(data: TaxSettingsIn, _: dict = Depends(auth_dep)):
        email = (data.accountant_email or "").strip()
        await db.erp_settings.update_one(
            {"key": _TAX_SETTINGS_KEY},
            {"$set": {"key": _TAX_SETTINGS_KEY, "accountant_email": email}},
            upsert=True)
        return {"accountant_email": email}

    class TaxSendIn(BaseModel):
        year: int | None = None
        quarter: int | None = None
        start: str | None = None
        end: str | None = None
        to_email: str | None = None

    @router.post("/tax-recap/send")
    async def send_recap(data: TaxSendIn, _: dict = Depends(auth_dep)):
        from erp_helpers import send_pdf_email
        if data.start and data.end:
            recap = await _compute_range(db, data.start, data.end)
            fname = f"recap-tps-tvq-{recap['start']}_au_{recap['end']}.pdf"
        else:
            y, q = _now_quarter()
            year = data.year or y
            quarter = data.quarter or q
            if quarter < 1 or quarter > 4:
                raise HTTPException(400, "Trimestre invalide (1-4).")
            recap = await _compute(db, year, quarter)
            fname = f"recap-tps-tvq-T{quarter}-{year}.pdf"
        to_email = (data.to_email or "").strip() or await _get_accountant_email(db)
        if not to_email:
            raise HTTPException(400, "Aucun courriel de comptable enregistré. "
                                     "Entrez une adresse ou enregistrez-la dans les réglages.")
        pdf = await asyncio.to_thread(render_tax_recap_pdf, recap)
        await send_pdf_email(
            to_email=to_email,
            subject=f"Récap TPS/TVQ — {recap['period_label']} — Portech",
            html=_recap_email_html(recap),
            pdf_bytes=pdf,
            filename=fname,
        )
        return {"sent": True, "to_email": to_email, "period_label": recap["period_label"]}


# ── Rappel trimestriel automatique (push + courriel) ─────────────────
def _prev_quarter(now: datetime) -> tuple[int, int]:
    """Quarter that just closed relative to `now` (1st day of a new quarter)."""
    q = (now.month - 1) // 3 + 1
    if q == 1:
        return now.year - 1, 4
    return now.year, q - 1


async def run_tax_reminder(db) -> dict:
    """Compute the just-closed quarter and notify the owner (push + email)
    + the accountant (email) that a new tax period is ready to declare."""
    import os
    from erp_helpers import send_pdf_email
    from push_notifications import send_push

    now = datetime.now(timezone.utc)
    year, quarter = _prev_quarter(now)
    recap = await _compute(db, year, quarter)
    net_total = recap["net"]["total"]
    net_txt = (f"{net_total:,.2f} $ à remettre" if net_total >= 0
               else f"remboursement de {abs(net_total):,.2f} $")

    # Push to all subscribed devices
    try:
        await send_push(
            db,
            title=f"Taxes prêtes — {recap['period_label']}",
            body=f"Nouveau trimestre à déclarer : net {net_txt}. Tape pour voir le récap.",
            url="/admin/gestion/recap-taxes",
            tag="tax-recap",
        )
    except Exception as exc:
        logger.warning("tax reminder push failed: %s", exc)

    # Email owner + accountant (with PDF)
    owner = (os.environ.get("BRIEFING_EMAIL")
             or os.environ.get("LEADS_RECIPIENT_EMAIL")
             or "portech.infos@gmail.com")
    accountant = await _get_accountant_email(db)
    recipients = [e for e in {owner, accountant} if e]
    pdf = await asyncio.to_thread(render_tax_recap_pdf, recap)
    sent = []
    for to in recipients:
        try:
            await send_pdf_email(
                to_email=to,
                subject=f"Rappel — Taxes à déclarer : {recap['period_label']} (Portech)",
                html=_recap_email_html(recap),
                pdf_bytes=pdf,
                filename=f"recap-tps-tvq-T{quarter}-{year}.pdf",
            )
            sent.append(to)
        except Exception as exc:
            logger.warning("tax reminder email to %s failed: %s", to, exc)
    logger.info("Tax reminder sent for %s → %s", recap["period_label"], sent)
    return {"period_label": recap["period_label"], "net_total": net_total, "emailed": sent}


def start_tax_reminder_scheduler(db) -> AsyncIOScheduler:
    """1st day of each calendar quarter (Jan/Apr/Jul/Oct) at 08:00 Montréal:
    remind the owner + accountant that the just-closed quarter is ready."""
    sched = AsyncIOScheduler(timezone="America/Montreal")
    sched.add_job(
        lambda: asyncio.create_task(run_tax_reminder(db)),
        CronTrigger(month="1,4,7,10", day=1, hour=8, minute=0),
        id="tax_recap_reminder", replace_existing=True,
    )
    sched.start()
    logger.info("Tax recap reminder scheduler started (1st of quarter @ 08:00 America/Montreal)")
    return sched
