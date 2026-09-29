"""Notifications push (Web Push / VAPID) pour l'app « Adjointe Portech ».

Aucun service tiers : on génère notre propre paire de clés VAPID (stockée dans
Mongo `erp_settings` pour survivre aux redéploiements) et on envoie les
notifications directement via `pywebpush` (compatible iOS 16.4+ / APNs).
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid.utils import b64urlencode
from pywebpush import WebPushException, webpush

logger = logging.getLogger("portech.push")

VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:portech.infos@gmail.com")
_PRIV_PEM_PATH = "/tmp/portech_vapid_private.pem"

# Filled at startup by ensure_vapid_keys().
_PUBLIC_KEY: str | None = None


async def ensure_vapid_keys(db) -> str:
    """Generate (once) or load the VAPID key pair from Mongo. Returns the
    URL-safe base64 public application-server key. Writes the private PEM to
    disk so pywebpush can read it."""
    global _PUBLIC_KEY
    doc = await db.erp_settings.find_one({"key": "vapid_keys"})
    if doc and doc.get("private_pem") and doc.get("public_key"):
        private_pem = doc["private_pem"]
        public_key = doc["public_key"]
    else:
        priv = ec.generate_private_key(ec.SECP256R1())
        private_pem = priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        pub_raw = priv.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        public_key = b64urlencode(pub_raw)
        await db.erp_settings.update_one(
            {"key": "vapid_keys"},
            {"$set": {"key": "vapid_keys", "private_pem": private_pem, "public_key": public_key}},
            upsert=True,
        )
        logger.info("Generated a new VAPID key pair for push notifications.")
    with open(_PRIV_PEM_PATH, "w") as f:
        f.write(private_pem)
    _PUBLIC_KEY = public_key
    return public_key


def get_public_key() -> str | None:
    return _PUBLIC_KEY


def _audience(endpoint: str) -> str:
    p = urlsplit(endpoint)
    return f"{p.scheme}://{p.netloc}"


def _send_one_sync(sub_doc: dict, payload: dict) -> None:
    claims = {
        "sub": VAPID_SUBJECT,
        "aud": _audience(sub_doc["endpoint"]),
        "exp": int(time.time()) + 12 * 60 * 60,
    }
    webpush(
        subscription_info={"endpoint": sub_doc["endpoint"], "keys": sub_doc["keys"]},
        data=json.dumps(payload),
        vapid_private_key=_PRIV_PEM_PATH,
        vapid_claims=claims,
        ttl=86400,
        timeout=15,
    )


async def send_push(db, *, title: str, body: str, url: str = "/adjointe", tag: str | None = None) -> dict:
    """Send a push notification to every registered device. Prunes dead subs."""
    if not os.path.isfile(_PRIV_PEM_PATH):
        try:
            await ensure_vapid_keys(db)
        except Exception as exc:  # noqa: BLE001
            logger.error("Push skipped — no VAPID keys: %s", exc)
            return {"attempted": 0, "sent": 0}
    subs = await db.push_subscriptions.find({}, {"_id": 0}).to_list(length=None)
    payload = {"title": title, "body": body, "url": url, "tag": tag or "portech"}
    sent = 0
    for doc in subs:
        try:
            await asyncio.to_thread(_send_one_sync, doc, payload)
            sent += 1
        except WebPushException as exc:  # noqa: PERF203
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                await db.push_subscriptions.delete_one({"endpoint": doc["endpoint"]})
        except Exception as exc:  # noqa: BLE001
            logger.error("Push delivery failed: %s", exc)
    return {"attempted": len(subs), "sent": sent}


# ── Morning summary push (jobs du jour + factures en retard) ──────────────
def _stale_days(ts: str) -> int:
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).date()
    except Exception:
        return 0
    return (datetime.now(timezone.utc).date() - d).days


async def run_morning_push(db) -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    jobs = await db.erp_jobs.find({}, {"_id": 0}).to_list(500)
    active = [j for j in jobs if j.get("stage") not in ("annule", "paye", "livre", "facture")]
    due = [j for j in active if j.get("target_date") and j["target_date"] <= today]
    leads = [j for j in active if j.get("stage") == "lead"]
    relance = [j for j in active if j.get("stage") == "soumission_envoyee"
               and _stale_days(j.get("updated_at") or j.get("created_at")) >= 3]
    inv = await db.erp_invoices.find({"status": "envoyée"}, {"_id": 0}).to_list(300)
    overdue_inv = [i for i in inv if i.get("due_date") and i["due_date"] < today]
    # Dépôts reçus dont le solde traîne (+30 j)
    dep_inv = await db.erp_invoices.find(
        {"deposit_received": True, "status": {"$nin": ["payée", "annulée"]}}, {"_id": 0}).to_list(300)
    stale_dep = [i for i in dep_inv if i.get("date") and _stale_days(i.get("date")) >= 30
                 and float(i.get("balance_due") if i.get("balance_due") is not None
                           else (i.get("total", 0) - i.get("deposit_amount", 0))) > 0]

    parts = [f"{len(active)} job(s) actif(s)"]
    if leads:
        parts.append(f"{len(leads)} lead(s)")
    if relance:
        parts.append(f"{len(relance)} à relancer")
    if due:
        parts.append(f"{len(due)} à livrer/en retard")
    if overdue_inv:
        parts.append(f"{len(overdue_inv)} facture(s) en retard")
    if stale_dep:
        parts.append(f"{len(stale_dep)} solde(s) de dépôt à encaisser")
    body = " · ".join(parts) if (leads or relance or due or overdue_inv or stale_dep) else (
        f"{len(active)} job(s) actif(s). Aucune urgence aujourd'hui — bonne journée !"
    )
    return await send_push(db, title=f"Résumé du matin — {today}", body=body, tag="briefing")


def start_push_scheduler(db) -> AsyncIOScheduler:
    """Résumé matinal poussé à 5h30 (heure du Québec)."""
    sched = AsyncIOScheduler(timezone="America/Montreal")
    sched.add_job(
        run_morning_push, "cron", hour=5, minute=30,
        args=[db], id="portech_morning_push", replace_existing=True,
    )
    sched.start()
    return sched
