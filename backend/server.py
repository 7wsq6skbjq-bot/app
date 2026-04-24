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
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

# ==============================================================
# Configuration
# ==============================================================
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_MIN = 60 * 8  # 8 hours

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


class ContactSubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    email: EmailStr
    message: str
    project_type: Optional[str] = None
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
    username = os.environ.get("ADMIN_USERNAME", "PortechAdmin")
    password = os.environ.get("ADMIN_PASSWORD", "admin")
    existing = await db.admin_users.find_one({"username": username})
    if existing is None:
        await db.admin_users.insert_one(
            {
                "username": username,
                "password_hash": hash_password(password),
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("Seeded admin user: %s", username)
    elif not verify_password(password, existing.get("password_hash", "")):
        await db.admin_users.update_one(
            {"username": username},
            {"$set": {"password_hash": hash_password(password)}},
        )
        logger.info("Rehashed admin password for: %s", username)


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
              <tr><td style="color:#71717a; vertical-align:top;"><b>Téléphone</b></td><td>{sub.phone}</td></tr>
              <tr><td style="color:#71717a; vertical-align:top;"><b>Courriel</b></td><td><a href="mailto:{sub.email}" style="color:#1d4ed8;">{sub.email}</a></td></tr>
              <tr><td style="color:#71717a; vertical-align:top;"><b>Type de projet</b></td><td>{sub.project_type or '—'}</td></tr>
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

    doc = submission.model_dump()
    doc["email"] = str(doc["email"])
    doc["created_at"] = doc["created_at"].isoformat()
    await db.contact_submissions.insert_one(doc)
    logger.info("New contact submission from %s (email_sent=%s)", submission.email, email_ok)
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
# Wire up
# ==============================================================
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await db.admin_users.create_index("username", unique=True)
    await db.contact_submissions.create_index([("created_at", -1)])
    await seed_admin()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
