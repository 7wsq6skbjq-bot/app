"""
Monthly expense recap — automatic email to the accountant.

On the LAST FRIDAY of each month at 09:00 America/Montreal, the scheduler
builds a summary of the current month's expenses (count, subtotal, TPS, TVQ,
total, breakdown by category) and emails it to the configured accountant
address with the full CSV export attached.

Admin endpoints expose preview + manual-send for testing or off-cycle runs.
"""
import asyncio
import base64
import csv
import io
import logging
import os
from datetime import date, datetime, timezone
from typing import Optional

import resend

from erp_helpers import REPLY_TO_EMAIL, wrap_branded_email
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("portech.erp.monthly_recap")

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
ACCOUNTANT_EMAIL = os.environ.get(
    "ACCOUNTANT_EMAIL",
    os.environ.get("LEADS_RECIPIENT_EMAIL", "portech.infos@gmail.com"),
)

MONTH_LABEL_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def _fmt_money(v: float) -> str:
    return f"{v:,.2f} $".replace(",", " ").replace(".", ",")


async def build_recap(db: AsyncIOMotorDatabase, month: str) -> dict:
    """Return summary dict + CSV bytes for the given YYYY-MM month."""
    if len(month) != 7 or month[4] != "-":
        raise ValueError("month must be YYYY-MM")
    cur = db.erp_expenses.find(
        {"date": {"$gte": f"{month}-01", "$lt": f"{month}-32"}},
        {"_id": 0},
    ).sort("date", 1)
    rows = [r async for r in cur]

    subtotal = sum(float(r.get("subtotal", 0)) for r in rows)
    tps = sum(float(r.get("tps", 0)) for r in rows)
    tvq = sum(float(r.get("tvq", 0)) for r in rows)
    total = sum(float(r.get("total", 0)) for r in rows)
    by_cat: dict[str, float] = {}
    for r in rows:
        c = r.get("category", "Autre")
        by_cat[c] = by_cat.get(c, 0.0) + float(r.get("total", 0))
    by_category = sorted(
        [{"category": k, "total": round(v, 2)} for k, v in by_cat.items()],
        key=lambda x: -x["total"],
    )

    # Build CSV bytes (same shape as /expenses/export.csv)
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf)
    writer.writerow([
        "Date", "Fournisseur", "Description", "Catégorie",
        "Sous-total", "TPS", "TVQ", "Total",
        "Mode paiement", "Statut", "Réf. facture", "Reçu", "Notes",
    ])
    for r in rows:
        writer.writerow([
            r.get("date", ""),
            r.get("supplier_name", ""),
            r.get("description", ""),
            r.get("category", ""),
            f"{float(r.get('subtotal', 0)):.2f}",
            f"{float(r.get('tps', 0)):.2f}",
            f"{float(r.get('tvq', 0)):.2f}",
            f"{float(r.get('total', 0)):.2f}",
            r.get("payment_method", ""),
            r.get("status", ""),
            r.get("invoice_ref", ""),
            "Oui" if r.get("receipt_filename") else "",
            (r.get("notes") or "").replace("\n", " "),
        ])
    csv_bytes = buf.getvalue().encode("utf-8")

    return {
        "month": month,
        "count": len(rows),
        "subtotal": round(subtotal, 2),
        "tps": round(tps, 2),
        "tvq": round(tvq, 2),
        "total": round(total, 2),
        "by_category": by_category,
        "csv_bytes": csv_bytes,
    }


def render_recap_html(recap: dict) -> tuple[str, str]:
    """Return (subject, html) for the recap email."""
    y, m = recap["month"].split("-")
    label = f"{MONTH_LABEL_FR[int(m)]} {y}"
    subject = f"Portech — Récapitulatif des dépenses · {label}"

    cat_rows = "".join(
        f"<tr><td style='padding:6px 12px;border-bottom:1px solid #dde5f0'>{c['category']}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #dde5f0;text-align:right;font-weight:600'>{_fmt_money(c['total'])}</td></tr>"
        for c in recap["by_category"]
    ) or "<tr><td colspan='2' style='padding:12px;color:#4b5d7a;text-align:center'>Aucune dépense ce mois-ci.</td></tr>"

    html = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;color:#0c182b;max-width:640px">
      <div style="background:#0c182b;color:#fff;padding:24px 28px">
        <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#9bb6d8">Portech · Comptabilité</div>
        <h1 style="margin:6px 0 0;font-size:24px;letter-spacing:-0.5px">Récapitulatif des dépenses</h1>
        <div style="font-size:14px;color:#cfd9e8;margin-top:4px">{label.capitalize()}</div>
      </div>

      <div style="padding:24px 28px;background:#f3f6fb;border-left:1px solid #dde5f0;border-right:1px solid #dde5f0">
        <p style="margin:0 0 16px;font-size:14px">Bonjour,</p>
        <p style="margin:0 0 20px;font-size:14px">Voici le récapitulatif mensuel automatique des dépenses Portech pour <b>{label}</b>. Le CSV complet est en pièce jointe, prêt pour l'import dans votre logiciel comptable.</p>

        <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #dde5f0">
          <tr>
            <td style="padding:12px 16px;border-bottom:1px solid #dde5f0">
              <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#4b5d7a">Dépenses ({recap['count']})</div>
              <div style="font-size:22px;font-weight:700;letter-spacing:-0.5px">{_fmt_money(recap['total'])}</div>
            </td>
            <td style="padding:12px 16px;border-bottom:1px solid #dde5f0;border-left:1px solid #dde5f0">
              <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#4b5d7a">Sous-total HT</div>
              <div style="font-size:18px;font-weight:600">{_fmt_money(recap['subtotal'])}</div>
            </td>
          </tr>
          <tr>
            <td style="padding:12px 16px;background:#e6f4ea">
              <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#0b6b2f">TPS récupérable</div>
              <div style="font-size:18px;font-weight:600;color:#0b6b2f">{_fmt_money(recap['tps'])}</div>
            </td>
            <td style="padding:12px 16px;background:#e6f4ea;border-left:1px solid #dde5f0">
              <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#0b6b2f">TVQ récupérable</div>
              <div style="font-size:18px;font-weight:600;color:#0b6b2f">{_fmt_money(recap['tvq'])}</div>
            </td>
          </tr>
        </table>

        <h3 style="margin:24px 0 8px;font-size:13px;letter-spacing:1.5px;text-transform:uppercase;color:#4b5d7a">Répartition par catégorie</h3>
        <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #dde5f0;font-size:14px">
          {cat_rows}
        </table>

        <p style="margin:24px 0 0;font-size:12px;color:#4b5d7a;line-height:1.6">
          Ce courriel est envoyé automatiquement par le système Portech le dernier vendredi de chaque mois.
          Toutes les pièces justificatives (photos de reçus) restent disponibles dans le tableau de bord admin
          si un audit est nécessaire.
        </p>
      </div>

      <div style="padding:16px 28px;background:#0c182b;color:#9bb6d8;font-size:11px;text-align:center;letter-spacing:1px;text-transform:uppercase">
        Portech · Quincaillerie de portes commerciales · Grand Montréal
      </div>
    </div>
    """
    return subject, html


async def send_recap(
    db: AsyncIOMotorDatabase,
    month: str,
    to_email: Optional[str] = None,
) -> dict:
    """Build the recap for `month` and email it to the accountant.

    Returns {sent, to, month, resend_id?}. Raises HTTPException on failure.
    """
    if not resend.api_key:
        raise HTTPException(503, "Service courriel non configuré (RESEND_API_KEY manquante)")
    target_email = to_email or ACCOUNTANT_EMAIL
    if not target_email:
        raise HTTPException(400, "Aucun courriel destinataire configuré (ACCOUNTANT_EMAIL)")

    recap = await build_recap(db, month)
    subject, html = render_recap_html(recap)
    branded_html = wrap_branded_email(
        html,
        footer_note=f"Récapitulatif dépenses {month} · Portech ERP",
    )
    fn = f"depenses-portech-{month}.csv"
    params = {
        "from": f"Portech <{SENDER_EMAIL}>",
        "to": [target_email],
        "reply_to": REPLY_TO_EMAIL,
        "subject": subject,
        "html": branded_html,
        "attachments": [{
            "filename": fn,
            "content": base64.b64encode(recap["csv_bytes"]).decode("ascii"),
        }],
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
    except Exception as exc:
        logger.error("Monthly recap send failed: %s", exc)
        raise HTTPException(502, f"Échec de l'envoi : {exc}")

    rid = result.get("id") if isinstance(result, dict) else None
    # Audit log
    await db.erp_monthly_recap_log.insert_one({
        "month": month,
        "to": target_email,
        "count": recap["count"],
        "total": recap["total"],
        "subtotal": recap["subtotal"],
        "tps": recap["tps"],
        "tvq": recap["tvq"],
        "resend_id": rid,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info("Monthly recap sent month=%s to=%s id=%s", month, target_email, rid)
    return {"sent": True, "to": target_email, "month": month, "resend_id": rid}


def _current_month_str() -> str:
    return date.today().strftime("%Y-%m")


async def run_scheduled_recap(db: AsyncIOMotorDatabase) -> dict:
    """Job entrypoint: send the recap for the CURRENT month (last-Friday job)."""
    month = _current_month_str()
    # Idempotency: skip if a recap was already sent for this month in the last 6 days.
    six_days_ago = datetime.now(timezone.utc).timestamp() - 6 * 86400
    last = await db.erp_monthly_recap_log.find_one(
        {"month": month},
        sort=[("sent_at", -1)],
        projection={"_id": 0, "sent_at": 1},
    )
    if last and last.get("sent_at"):
        try:
            ts = datetime.fromisoformat(last["sent_at"].replace("Z", "+00:00")).timestamp()
            if ts > six_days_ago:
                logger.info("Skip recap %s — already sent recently (%s)", month, last["sent_at"])
                return {"sent": False, "reason": "already_sent_recently", "month": month}
        except Exception:
            pass
    try:
        return await send_recap(db, month)
    except HTTPException as exc:
        logger.error("Scheduled recap failed: %s", exc.detail)
        return {"sent": False, "error": exc.detail, "month": month}


def start_recap_scheduler(db: AsyncIOMotorDatabase) -> AsyncIOScheduler:
    """Run on the LAST FRIDAY of each month at 09:00 America/Montreal.

    APScheduler supports `day='last fri'` natively, which evaluates to the
    last Friday of the configured month.
    """
    sched = AsyncIOScheduler(timezone="America/Montreal")
    sched.add_job(
        run_scheduled_recap, "cron",
        args=[db],
        day="last fri", hour=9, minute=0,
        id="erp_monthly_expense_recap",
        replace_existing=True,
    )
    sched.start()
    logger.info("Monthly recap scheduler started (last Friday 09:00 America/Montreal)")
    return sched


def register_routes(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    """Expose admin endpoints for previewing and manually sending the recap."""

    @router.get("/expenses/recap/preview")
    async def preview_recap(
        month: Optional[str] = Query(default=None),
        _: dict = Depends(auth_dep),
    ):
        month = month or _current_month_str()
        recap = await build_recap(db, month)
        # Don't ship the CSV bytes back as JSON
        return {
            "month": recap["month"],
            "count": recap["count"],
            "subtotal": recap["subtotal"],
            "tps": recap["tps"],
            "tvq": recap["tvq"],
            "total": recap["total"],
            "by_category": recap["by_category"],
            "default_recipient": ACCOUNTANT_EMAIL,
        }

    @router.post("/expenses/recap/send")
    async def send_recap_now(
        month: Optional[str] = Query(default=None),
        to: Optional[str] = Query(default=None),
        _: dict = Depends(auth_dep),
    ):
        month = month or _current_month_str()
        return await send_recap(db, month, to_email=to)

    @router.get("/expenses/recap/log")
    async def recap_log(_: dict = Depends(auth_dep)):
        """Return the last 20 recap send events for audit."""
        cur = db.erp_monthly_recap_log.find(
            {}, {"_id": 0},
        ).sort("sent_at", -1).limit(20)
        return [d async for d in cur]
