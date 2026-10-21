from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import bcrypt
import jwt
import resend
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from erp import build_erp_router
from erp_reminders import start_scheduler
from erp_monthly_recap import start_recap_scheduler
from erp_expert_report_backup import start_backup_scheduler
from erp_routes_jobs import start_jobs_briefing_scheduler

# ==============================================================
# Configuration
# ==============================================================
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MIN = 60 * 24 * 30  # 30 days — keeps the phone app logged in

resend.api_key = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
LEADS_RECIPIENT_EMAIL = os.environ.get("LEADS_RECIPIENT_EMAIL", "portech.infos@gmail.com")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("portech")

app = FastAPI(title="Portech API")
api_router = APIRouter(prefix="/api")


# ==============================================================
# Models
# ==============================================================
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


class ContactSubmissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    phone: str = Field(..., min_length=5, max_length=40)
    email: EmailStr
    message: str = Field(..., min_length=1, max_length=4000)
    project_type: Optional[str] = Field(default=None, max_length=120)
    company: Optional[str] = Field(default=None, max_length=160)
    work_location: str = Field(..., min_length=1, max_length=240)
    door_gamme: Optional[str] = Field(default=None, max_length=80)
    door_config: Optional[str] = Field(default=None, max_length=40)
    door_qty: Optional[str] = Field(default=None, max_length=20)
    door_width: Optional[str] = Field(default=None, max_length=40)
    door_height: Optional[str] = Field(default=None, max_length=40)
    door_finish: Optional[str] = Field(default=None, max_length=60)


class ContactSubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    email: EmailStr
    message: str
    project_type: Optional[str] = None
    company: Optional[str] = None
    work_location: Optional[str] = ""
    door_gamme: Optional[str] = None
    door_config: Optional[str] = None
    door_qty: Optional[str] = None
    door_width: Optional[str] = None
    door_height: Optional[str] = None
    door_finish: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    email_sent: bool = False


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminUser(BaseModel):
    username: str
    role: str = "admin"


# ==============================================================
# Auth helpers
# ==============================================================
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(username: str) -> str:
    payload = {
        "sub": username,
        "role": "admin",
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TTL_MIN),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


async def get_current_admin(request: Request) -> AdminUser:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        # Allow ?token= in the URL for native browser downloads where setting a
        # Bearer header is impossible (e.g., <a href> or window.location.href).
        # Same JWT — short-lived, scoped to access tokens. Acceptable trade-off
        # because the URL is over HTTPS and the token is already in localStorage.
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access" or payload.get("role") != "admin":
            raise HTTPException(status_code=401, detail="Jeton invalide")
        username = payload.get("sub")
        user_doc = await db.admin_users.find_one({"username": username}, {"_id": 0})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")
        return AdminUser(username=user_doc["username"], role=user_doc.get("role", "admin"))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Jeton invalide")


async def seed_admin() -> None:
    # Strip whitespace defensively — env vars sometimes get a stray space or
    # newline depending on how they were entered in the deployment dashboard.
    username = (os.environ.get("ADMIN_USERNAME") or "").strip()
    password = (os.environ.get("ADMIN_PASSWORD") or "").strip()
    if not username or not password:
        # Fail fast instead of seeding an admin with the silent default password.
        # The previous fallback ("admin") created an admin nobody knew about and
        # caused recurring 401s on production when the env vars weren't set.
        raise RuntimeError(
            "ADMIN_USERNAME and ADMIN_PASSWORD must be set in the environment. "
            "Refusing to seed an admin with a default password."
        )
    existing = await db.admin_users.find_one({"username": username})
    if not existing:
        await db.admin_users.insert_one(
            {
                "username": username,
                "password_hash": hash_password(password),
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("Seeded admin user %s (new account)", username)
    elif not verify_password(password, existing.get("password_hash", "")):
        await db.admin_users.update_one(
            {"username": username},
            {"$set": {"password_hash": hash_password(password)}},
        )
        logger.info("Admin %s : password rehashed to match ADMIN_PASSWORD env var", username)
    else:
        logger.info("Admin %s : ready (password verified)", username)


# ==============================================================
# Resend email
# ==============================================================
def build_lead_email_html(sub: ContactSubmission) -> str:
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, sans-serif; background:#f4f4f5; padding:24px;">
      <tr><td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border:1px solid #e4e4e7;">
          <tr><td style="background:#0f1e3d; padding:24px;">
            <h1 style="color:#ffffff; font-size:22px; margin:0; letter-spacing:1px; text-transform:uppercase;">PORTECH · Nouvelle soumission</h1>
            <p style="color:#93a5c9; margin:8px 0 0 0; font-size:13px;">Une nouvelle demande vient d'être envoyée via le formulaire du site.</p>
          </td></tr>
          <tr><td style="padding:24px;">
            <table width="100%" cellpadding="8" cellspacing="0" style="font-size:14px; color:#27272a;">
              <tr><td style="width:140px; color:#71717a; vertical-align:top;"><b>Nom</b></td><td>{sub.name}</td></tr>
              <tr><td style="color:#71717a; vertical-align:top;"><b>Entreprise</b></td><td>{sub.company or '—'}</td></tr>
              <tr><td style="color:#71717a; vertical-align:top;"><b>Téléphone</b></td><td>{sub.phone}</td></tr>
              <tr><td style="color:#71717a; vertical-align:top;"><b>Courriel</b></td><td><a href="mailto:{sub.email}" style="color:#1d4ed8;">{sub.email}</a></td></tr>
              <tr><td style="color:#71717a; vertical-align:top;"><b>Type de projet</b></td><td>{sub.project_type or '—'}</td></tr>
              <tr><td style="color:#71717a; vertical-align:top;"><b>Lieu des travaux</b></td><td>{sub.work_location}</td></tr>
              <tr><td style="color:#71717a; vertical-align:top;"><b>Message</b></td><td style="white-space:pre-wrap;">{sub.message}</td></tr>
              <tr><td style="color:#71717a;"><b>Reçu le</b></td><td>{sub.created_at.strftime('%Y-%m-%d %H:%M UTC')}</td></tr>
            </table>
          </td></tr>
          <tr><td style="padding:16px 24px; background:#f4f4f5; color:#52525b; font-size:12px;">
            ID de soumission : <code>{sub.id}</code>
          </td></tr>
        </table>
      </td></tr>
    </table>
    """


async def send_lead_notification(sub: ContactSubmission) -> bool:
    if not resend.api_key:
        logger.warning("RESEND_API_KEY not set — skipping email notification")
        return False
    try:
        params = {
            "from": f"Portech <{SENDER_EMAIL}>",
            "to": [LEADS_RECIPIENT_EMAIL],
            "reply_to": str(sub.email),
            "subject": f"Nouvelle soumission Portech — {sub.name}",
            "html": build_lead_email_html(sub),
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info("Lead email sent (id=%s)", result.get("id"))
        return True
    except Exception as exc:
        logger.error("Failed to send lead email: %s", exc)
        return False


async def send_lead_autoreply(sub: ContactSubmission) -> bool:
    """Send an automatic branded acknowledgment to the person who submitted
    the website quote request (French first, English smaller below)."""
    if not resend.api_key:
        return False
    try:
        html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, sans-serif; background:#f4f4f5; padding:24px;">
          <tr><td align="center">
            <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; border:1px solid #e4e4e7;">
              <tr><td style="background:#0c182b; padding:24px;">
                <h1 style="color:#ffffff; font-size:20px; margin:0; letter-spacing:1px; text-transform:uppercase;">PORTECH</h1>
                <p style="color:#93a5c9; margin:6px 0 0 0; font-size:12px;">Quincaillerie et portes commerciales en aluminium</p>
              </td></tr>
              <tr><td style="padding:26px 26px 8px 26px; color:#27272a; font-size:14px; line-height:1.6;">
                <p style="margin:0 0 12px 0;">Bonjour {sub.name},</p>
                <p style="margin:0 0 12px 0;">Nous vous confirmons la bonne réception de votre demande de soumission.
                Merci de votre intérêt envers Portech. Un membre de notre équipe communiquera avec vous
                <b>dans les plus brefs délais</b> afin de bien comprendre votre projet et vous fournir une soumission adaptée.</p>
                <p style="margin:0 0 4px 0;">Cordialement,</p>
                <p style="margin:0; font-weight:bold;">L'équipe Portech</p>
              </td></tr>
              <tr><td style="padding:6px 26px 22px 26px; color:#71717a; font-size:12px; line-height:1.6; border-top:1px solid #eef2f8;">
                <p style="margin:12px 0 8px 0;">Hello {sub.name},</p>
                <p style="margin:0 0 8px 0;">We confirm we have received your quote request.
                Thank you for your interest in Portech. A member of our team will get back to you
                <b>as soon as possible</b> to better understand your project and provide a tailored quote.</p>
                <p style="margin:0;">Best regards,<br/>The Portech Team</p>
              </td></tr>
              <tr><td style="padding:14px 26px; background:#f4f4f5; color:#52525b; font-size:11px;">
                Portech · {SENDER_EMAIL} · portech.info
              </td></tr>
            </table>
          </td></tr>
        </table>
        """
        params = {
            "from": f"Portech <{SENDER_EMAIL}>",
            "to": [str(sub.email)],
            "reply_to": LEADS_RECIPIENT_EMAIL,
            "subject": "Portech — Demande reçue / Request received",
            "html": html,
        }
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info("Lead auto-reply sent (id=%s) to %s", result.get("id"), sub.email)
        return True
    except Exception as exc:
        logger.error("Failed to send lead auto-reply: %s", exc)
        return False


# ==============================================================
# Public routes
# ==============================================================
@api_router.get("/")
async def root():
    return {"message": "Portech API — online"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(payload: StatusCheckCreate):
    status_obj = StatusCheck(**payload.model_dump())
    doc = status_obj.model_dump()
    doc["timestamp"] = doc["timestamp"].isoformat()
    await db.status_checks.insert_one(doc)
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    rows = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for r in rows:
        if isinstance(r.get("timestamp"), str):
            r["timestamp"] = datetime.fromisoformat(r["timestamp"])
    return rows


@api_router.post("/contact", response_model=ContactSubmission, status_code=201)
async def create_contact_submission(payload: ContactSubmissionCreate):
    submission = ContactSubmission(**payload.model_dump())
    email_ok = await send_lead_notification(submission)
    submission.email_sent = email_ok
    # Fire-and-forget style auto-reply to the requester (bilingual FR/EN)
    await send_lead_autoreply(submission)

    doc = submission.model_dump()
    doc["email"] = str(doc["email"])
    doc["created_at"] = doc["created_at"].isoformat()
    await db.contact_submissions.insert_one(doc)
    logger.info("New contact submission from %s (email_sent=%s)", submission.email, email_ok)
    # Auto-create a "lead" job in the tracking board + push notification.
    try:
        from erp_routes_jobs import create_lead_job
        await create_lead_job(db, doc)
    except Exception as exc:  # never fail the request on a board error
        logger.error("Lead job creation failed: %s", exc)
    try:
        import push_notifications as push
        await push.send_push(
            db,
            title="Nouveau lead 🔔",
            body=f"{submission.name} — {submission.email}",
            url="/adjointe",
            tag="lead",
        )
    except Exception as exc:  # never fail the request on a push error
        logger.error("Lead push failed: %s", exc)
    return submission


# ==============================================================
# Auth routes
# ==============================================================
@api_router.post("/auth/login")
async def login(payload: LoginRequest, response: Response):
    user_doc = await db.admin_users.find_one({"username": payload.username})
    if not user_doc or not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Identifiant ou mot de passe incorrect")

    token = create_access_token(payload.username)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_TOKEN_TTL_MIN * 60,
        path="/",
    )
    return {"username": user_doc["username"], "role": user_doc.get("role", "admin"), "access_token": token}


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"message": "Déconnecté"}


@api_router.get("/auth/me", response_model=AdminUser)
async def me(current: AdminUser = Depends(get_current_admin)):
    return current


# ==============================================================
# Admin routes
# ==============================================================
@api_router.get("/admin/submissions", response_model=List[ContactSubmission])
async def list_submissions(_: AdminUser = Depends(get_current_admin)):
    rows = await db.contact_submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for r in rows:
        if isinstance(r.get("created_at"), str):
            r["created_at"] = datetime.fromisoformat(r["created_at"])
    return rows


@api_router.get("/admin/door-requests", response_model=List[ContactSubmission])
async def list_door_requests(_: AdminUser = Depends(get_current_admin)):
    door_fields = ["door_gamme", "door_config", "door_qty", "door_width", "door_height", "door_finish"]
    query = {"$or": [{f: {"$nin": [None, ""]}} for f in door_fields]}
    rows = await db.contact_submissions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for r in rows:
        if isinstance(r.get("created_at"), str):
            r["created_at"] = datetime.fromisoformat(r["created_at"])
    return rows


@api_router.get("/admin/stats")
async def stats(_: AdminUser = Depends(get_current_admin)):
    total = await db.contact_submissions.count_documents({})
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    last_30 = await db.contact_submissions.count_documents({"created_at": {"$gte": since}})
    return {"total": total, "last_30_days": last_30}


@api_router.delete("/admin/submissions/{submission_id}")
async def delete_submission(submission_id: str, _: AdminUser = Depends(get_current_admin)):
    result = await db.contact_submissions.delete_one({"id": submission_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Soumission introuvable")
    return {"deleted": submission_id}


# ==============================================================
# Google Calendar OAuth
# ==============================================================
@api_router.get("/oauth/calendar/login")
async def calendar_login(_: AdminUser = Depends(get_current_admin)):
    import google_calendar as gcal
    if not gcal.is_configured():
        raise HTTPException(503, "Google Calendar non configuré (clés manquantes).")
    return {"authorization_url": gcal.authorization_url()}


@api_router.get("/oauth/calendar/callback")
async def calendar_callback(code: str = "", error: str = ""):
    import google_calendar as gcal
    if error:
        return RedirectResponse(f"/adjointe?calendar=error&reason={error}")
    try:
        await gcal.exchange_code(db, code)
        return RedirectResponse("/adjointe?calendar=connected")
    except Exception as exc:  # noqa: BLE001
        logger.error("Calendar OAuth failed: %s", exc)
        return RedirectResponse("/adjointe?calendar=error")


@api_router.get("/admin/calendar/status")
async def calendar_status(_: AdminUser = Depends(get_current_admin)):
    import google_calendar as gcal
    return {"configured": gcal.is_configured(), "connected": await gcal.is_connected(db)}


# ==============================================================
# Wire up
# ==============================================================
# Mount ERP (customers/products/invoices/POs/BOLs) under the /api/admin prefix.
api_router.include_router(build_erp_router(db, get_current_admin))

# Atelier — inventory + cut confirmation + label sheets.
from atelier_routes import build_atelier_router  # noqa: E402
api_router.include_router(build_atelier_router(auth_dep=get_current_admin, get_db=lambda: db))

from at_order_routes import build_at_order_router  # noqa: E402
api_router.include_router(build_at_order_router(auth_dep=get_current_admin, get_db=lambda: db))

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    # We use Authorization Bearer tokens (sessionStorage), NOT cookies.
    # Setting allow_credentials=False makes the wildcard origin legal and
    # eliminates the CORS-spec contradiction that was breaking prod logins.
    allow_credentials=False,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await db.admin_users.create_index("username", unique=True)
    await db.contact_submissions.create_index([("created_at", -1)])
    await seed_admin()
    # Seed the Adams Rite catalog (idempotent) so production gets the same
    # products/hardware that were imported in preview.
    try:
        from seed_adams_rite import seed_adams_rite_catalog
        await seed_adams_rite_catalog(db)
    except Exception as exc:  # never block startup on a seed failure
        print(f"[seed] Adams Rite seed skipped: {exc}")
    # Ensure a stable VAPID key pair exists for Web Push notifications.
    try:
        import push_notifications as push
        await push.ensure_vapid_keys(db)
        await db.push_subscriptions.create_index("endpoint", unique=True)
    except Exception as exc:  # never block startup on push setup
        print(f"[push] VAPID setup skipped: {exc}")
    # Migrate legacy job stages + backfill lead jobs from untreated website leads.
    try:
        from erp_routes_jobs import migrate_and_backfill_jobs
        await migrate_and_backfill_jobs(db)
    except Exception as exc:  # never block startup on migration
        print(f"[jobs] migration/backfill skipped: {exc}")
    # Import the AT Fabrication master price list (idempotent) + sync hardware costs.
    try:
        from seed_master_pricing import seed_master_pricing, sync_hardware_to_production
        res = await seed_master_pricing(db)
        await sync_hardware_to_production(db)
        print(f"[master] pricing import: {res}")
    except Exception as exc:
        print(f"[master] pricing import skipped: {exc}")
    # Start the daily reminder scheduler unless explicitly disabled
    # (e.g. inside pytest runs where scheduler side-effects are unwanted).
    if os.environ.get("DISABLE_SCHEDULER", "").lower() not in ("1", "true", "yes"):
        app.state.scheduler = start_scheduler(db)
        app.state.recap_scheduler = start_recap_scheduler(db)
        app.state.backup_scheduler = start_backup_scheduler(db)
        app.state.briefing_scheduler = start_jobs_briefing_scheduler(db)
        from erp_routes_statements import start_statements_scheduler
        from erp_routes_quotes import start_quote_followup_scheduler
        app.state.statements_scheduler = start_statements_scheduler(db)
        app.state.quote_followup_scheduler = start_quote_followup_scheduler(db)
        from push_notifications import start_push_scheduler
        app.state.push_scheduler = start_push_scheduler(db)
        from erp_routes_tax_recap import start_tax_reminder_scheduler
        app.state.tax_reminder_scheduler = start_tax_reminder_scheduler(db)
    else:
        app.state.scheduler = None
        app.state.recap_scheduler = None
        app.state.backup_scheduler = None
        app.state.briefing_scheduler = None
        app.state.push_scheduler = None


@app.on_event("shutdown")
async def shutdown_db_client():
    sched = getattr(app.state, "scheduler", None)
    if sched is not None:
        sched.shutdown(wait=False)
    recap_sched = getattr(app.state, "recap_scheduler", None)
    if recap_sched is not None:
        recap_sched.shutdown(wait=False)
    backup_sched = getattr(app.state, "backup_scheduler", None)
    if backup_sched is not None:
        backup_sched.shutdown(wait=False)
    briefing_sched = getattr(app.state, "briefing_scheduler", None)
    if briefing_sched is not None:
        briefing_sched.shutdown(wait=False)
    push_sched = getattr(app.state, "push_scheduler", None)
    if push_sched is not None:
        push_sched.shutdown(wait=False)
    client.close()
