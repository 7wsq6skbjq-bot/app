"""Suivi des jobs (Adjointe virtuelle — Brique 1).

Une "job" relie tous les documents d'un même projet (soumission, plan de
production, bon de commande, moustiquaires, connaissement, facture, avis de
paiement, rapport) et suit son avancement dans un pipeline visuel.

Pipeline : à approuver → dépôt reçu (50%) → en fabrication → prêt → livré →
facturé → payé (+ annulé).

Un briefing quotidien par courriel résume « où en sont mes jobs ».
"""
import os
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from erp_helpers import send_html_email

# ── Pipeline ──────────────────────────────────────────────
JOB_STAGES = [
    "a_approuver", "depot_recu", "en_fabrication", "pret",
    "livre", "facture", "paye", "annule",
]
STAGE_LABELS = {
    "a_approuver": "À approuver",
    "depot_recu": "Dépôt reçu (50%)",
    "en_fabrication": "En fabrication",
    "pret": "Prêt",
    "livre": "Livré",
    "facture": "Facturé",
    "paye": "Payé",
    "annule": "Annulé",
}
STAGE_PATTERN = "^(" + "|".join(JOB_STAGES) + ")$"
DOC_TYPES = [
    "quote", "production_plan", "purchase_order", "mosquito_order",
    "bol", "invoice", "payment_notice", "expert_report",
]

BRIEFING_EMAIL = (
    os.environ.get("BRIEFING_EMAIL")
    or os.environ.get("LEADS_RECIPIENT_EMAIL")
    or "info@portech.info"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Models ────────────────────────────────────────────────
class JobLink(BaseModel):
    model_config = ConfigDict(extra="ignore")
    doc_type: str
    doc_id: str
    number: Optional[str] = None
    label: Optional[str] = None
    added_at: str = Field(default_factory=_now)


class Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_number: str
    title: str
    client_name: Optional[str] = ""
    client_email: Optional[str] = None
    party_id: Optional[str] = None
    stage: str = Field(default="a_approuver", pattern=STAGE_PATTERN)
    total: float = 0.0
    deposit_expected: float = 0.0
    priority: str = Field(default="normal", pattern="^(normal|urgent)$")
    target_date: Optional[str] = None      # YYYY-MM-DD — livraison/échéance visée
    notes: Optional[str] = ""
    links: List[JobLink] = Field(default_factory=list)
    history: List[dict] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class JobIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = Field(min_length=1, max_length=200)
    client_name: Optional[str] = ""
    client_email: Optional[str] = None
    party_id: Optional[str] = None
    total: float = 0.0
    priority: str = Field(default="normal", pattern="^(normal|urgent)$")
    target_date: Optional[str] = None
    notes: Optional[str] = ""


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    party_id: Optional[str] = None
    total: Optional[float] = None
    deposit_expected: Optional[float] = None
    priority: Optional[str] = Field(default=None, pattern="^(normal|urgent)$")
    target_date: Optional[str] = None
    notes: Optional[str] = None


class StageIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    stage: str = Field(pattern=STAGE_PATTERN)
    note: Optional[str] = ""


class LinkIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    doc_type: str
    doc_id: str
    number: Optional[str] = None
    label: Optional[str] = None


# ── Briefing builder ──────────────────────────────────────
def _parse_date(d: Optional[str]) -> Optional[date]:
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _fmt_money(v) -> str:
    try:
        s = f"{float(v or 0):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        s = "0,00"
    return f"{s} $"


def build_briefing(jobs: List[dict]) -> dict:
    today = datetime.now(timezone.utc).date()
    active = [j for j in jobs if j.get("stage") != "annule"]
    counts = {s: 0 for s in JOB_STAGES}
    for j in jobs:
        counts[j.get("stage", "a_approuver")] = counts.get(j.get("stage", "a_approuver"), 0) + 1

    awaiting = [j for j in active if j.get("stage") == "a_approuver"]
    in_fab = [j for j in active if j.get("stage") in ("depot_recu", "en_fabrication")]
    ready = [j for j in active if j.get("stage") == "pret"]

    soon, overdue = [], []
    done_stages = {"livre", "facture", "paye", "annule"}
    for j in active:
        td = _parse_date(j.get("target_date"))
        if not td or j.get("stage") in done_stages:
            continue
        delta = (td - today).days
        if delta < 0:
            overdue.append(j)
        elif delta <= 7:
            soon.append(j)

    return {
        "date": today.isoformat(),
        "total_active": len(active),
        "counts": counts,
        "awaiting": awaiting,
        "in_fab": in_fab,
        "ready": ready,
        "soon": soon,
        "overdue": overdue,
    }


def render_briefing_html(b: dict) -> str:
    def _row(j):
        td = j.get("target_date")
        extra = f" · échéance {td}" if td else ""
        star = "🔴 " if j.get("priority") == "urgent" else ""
        return (
            f"<li style='margin:0 0 6px 0;'>{star}<b>{j.get('job_number','')}"
            f"</b> — {j.get('title','')} "
            f"<span style='color:#4b5d7a;'>({j.get('client_name') or 'client ?'}"
            f"{extra})</span></li>"
        )

    def _section(title, items, empty="Rien pour l'instant."):
        if not items:
            body = f"<p style='margin:0 0 4px 0;color:#71717a;'>{empty}</p>"
        else:
            body = "<ul style='margin:0 0 4px 0;padding-left:18px;'>" + "".join(_row(j) for j in items) + "</ul>"
        return (
            f"<p style='margin:16px 0 4px 0;font-weight:bold;color:#0c182b;'>{title}</p>{body}"
        )

    counts = b["counts"]
    chips = " · ".join(
        f"{STAGE_LABELS[s]}: <b>{counts.get(s,0)}</b>"
        for s in JOB_STAGES if s != "annule"
    )
    return (
        f"<p style='margin:0 0 8px 0;'>Bonjour Cédrick, voici votre briefing du "
        f"<b>{b['date']}</b> — <b>{b['total_active']}</b> job(s) active(s).</p>"
        f"<p style='margin:0 0 4px 0;color:#4b5d7a;font-size:13px;'>{chips}</p>"
        + _section("🔴 En retard (échéance dépassée)", b["overdue"], "Aucune job en retard 🎉")
        + _section("⏳ À livrer d'ici 7 jours", b["soon"])
        + _section("🖊️ En attente d'approbation / dépôt", b["awaiting"])
        + _section("🏭 En fabrication", b["in_fab"])
        + _section("📦 Prêtes (à livrer)", b["ready"])
    )


async def run_daily_briefing(db: AsyncIOMotorDatabase) -> dict:
    jobs = await db.erp_jobs.find({}, {"_id": 0}).to_list(length=None)
    b = build_briefing(jobs)
    subject = f"Portech — Briefing du {b['date']} · {b['total_active']} job(s) active(s)"
    html = render_briefing_html(b)
    try:
        await send_html_email(
            to_email=BRIEFING_EMAIL, subject=subject, html=html,
            footer_note="Briefing quotidien · Portech ERP",
        )
        return {"sent": True, "to": BRIEFING_EMAIL, **b}
    except Exception as exc:  # pragma: no cover - email issues shouldn't crash scheduler
        return {"sent": False, "error": str(exc), **b}


def start_jobs_briefing_scheduler(db: AsyncIOMotorDatabase) -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="America/Montreal")
    sched.add_job(
        run_daily_briefing, "cron", hour=7, minute=30,
        args=[db], id="jobs_daily_briefing", replace_existing=True,
    )
    sched.start()
    return sched


# ── Routes ────────────────────────────────────────────────
def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep, next_number) -> None:

    async def _job_number() -> str:
        n = await next_number("job")
        return f"JOB-{n:04d}"

    @router.get("/jobs", response_model=List[Job])
    async def list_jobs(_: dict = Depends(auth_dep)):
        cur = db.erp_jobs.find({}, {"_id": 0}).sort("created_at", -1)
        return [Job(**d) async for d in cur]

    @router.get("/jobs/stages")
    async def job_stages(_: dict = Depends(auth_dep)):
        return {"stages": JOB_STAGES, "labels": STAGE_LABELS, "doc_types": DOC_TYPES}

    @router.post("/jobs", response_model=Job, status_code=201)
    async def create_job(data: JobIn, _: dict = Depends(auth_dep)):
        job = Job(
            job_number=await _job_number(),
            title=data.title,
            client_name=data.client_name or "",
            client_email=data.client_email,
            party_id=data.party_id,
            total=data.total or 0.0,
            deposit_expected=round((data.total or 0.0) * 0.5, 2),
            priority=data.priority,
            target_date=data.target_date,
            notes=data.notes or "",
            history=[{"stage": "a_approuver", "at": _now(), "note": "Job créée"}],
        )
        await db.erp_jobs.insert_one(job.model_dump())
        return job

    @router.post("/jobs/from-quote/{quote_id}", response_model=Job)
    async def create_job_from_quote(quote_id: str, _: dict = Depends(auth_dep)):
        q = await db.erp_quotes.find_one({"id": quote_id}, {"_id": 0})
        if not q:
            raise HTTPException(404, "Soumission introuvable")
        # Éviter les doublons : renvoyer la job existante liée à cette soumission.
        existing = await db.erp_jobs.find_one(
            {"links.doc_type": "quote", "links.doc_id": quote_id}, {"_id": 0})
        if existing:
            return Job(**existing)
        cust = q.get("customer_snapshot") or {}
        num = f"SO-{int(q.get('number', 0)):04d}"
        total = float(q.get("total") or 0)
        stage = "depot_recu" if q.get("status") == "acceptée" else "a_approuver"
        job = Job(
            job_number=await _job_number(),
            title=f"Soumission {num}" + (f" — {cust.get('name')}" if cust.get("name") else ""),
            client_name=cust.get("name") or "",
            client_email=cust.get("email"),
            party_id=q.get("customer_id"),
            stage=stage,
            total=total,
            deposit_expected=round(total * 0.5, 2),
            links=[JobLink(doc_type="quote", doc_id=quote_id, number=num,
                           label=f"Soumission {num}")],
            history=[{"stage": stage, "at": _now(),
                      "note": f"Job créée depuis la soumission {num}"}],
        )
        await db.erp_jobs.insert_one(job.model_dump())
        return job

    @router.get("/jobs/{job_id}", response_model=Job)
    async def get_job(job_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_jobs.find_one({"id": job_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Job introuvable")
        return Job(**doc)

    @router.put("/jobs/{job_id}", response_model=Job)
    async def update_job(job_id: str, data: JobUpdate, _: dict = Depends(auth_dep)):
        doc = await db.erp_jobs.find_one({"id": job_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Job introuvable")
        raw = data.model_dump(exclude_unset=True)
        # Champs non-nullables : on ignore un None accidentel. Les autres
        # (target_date, client_email, party_id, notes) peuvent être vidés → null.
        non_nullable = {"title", "priority", "total"}
        fields = {k: v for k, v in raw.items() if not (k in non_nullable and v is None)}
        if "total" in fields and "deposit_expected" not in fields:
            fields["deposit_expected"] = round(float(fields["total"] or 0) * 0.5, 2)
        fields["updated_at"] = _now()
        await db.erp_jobs.update_one({"id": job_id}, {"$set": fields})
        doc = await db.erp_jobs.find_one({"id": job_id}, {"_id": 0})
        return Job(**doc)

    @router.patch("/jobs/{job_id}/stage", response_model=Job)
    async def set_stage(job_id: str, data: StageIn, _: dict = Depends(auth_dep)):
        doc = await db.erp_jobs.find_one({"id": job_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Job introuvable")
        entry = {"stage": data.stage, "at": _now(), "note": data.note or ""}
        await db.erp_jobs.update_one(
            {"id": job_id},
            {"$set": {"stage": data.stage, "updated_at": _now()},
             "$push": {"history": entry}},
        )
        doc = await db.erp_jobs.find_one({"id": job_id}, {"_id": 0})
        return Job(**doc)

    @router.delete("/jobs/{job_id}")
    async def delete_job(job_id: str, _: dict = Depends(auth_dep)):
        res = await db.erp_jobs.delete_one({"id": job_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Job introuvable")
        return {"deleted": job_id}

    @router.post("/jobs/{job_id}/links", response_model=Job)
    async def add_link(job_id: str, data: LinkIn, _: dict = Depends(auth_dep)):
        if data.doc_type not in DOC_TYPES:
            raise HTTPException(400, "Type de document invalide")
        doc = await db.erp_jobs.find_one({"id": job_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Job introuvable")
        if any(l.get("doc_type") == data.doc_type and l.get("doc_id") == data.doc_id
               for l in doc.get("links", [])):
            return Job(**doc)
        link = JobLink(**data.model_dump())
        await db.erp_jobs.update_one(
            {"id": job_id},
            {"$push": {"links": link.model_dump()}, "$set": {"updated_at": _now()}},
        )
        doc = await db.erp_jobs.find_one({"id": job_id}, {"_id": 0})
        return Job(**doc)

    @router.post("/jobs/{job_id}/unlink", response_model=Job)
    async def remove_link(job_id: str, data: LinkIn, _: dict = Depends(auth_dep)):
        """Detach a linked document (body-based so doc_id may contain '/')."""
        doc = await db.erp_jobs.find_one({"id": job_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Job introuvable")
        await db.erp_jobs.update_one(
            {"id": job_id},
            {"$pull": {"links": {"doc_type": data.doc_type, "doc_id": data.doc_id}},
             "$set": {"updated_at": _now()}},
        )
        doc = await db.erp_jobs.find_one({"id": job_id}, {"_id": 0})
        return Job(**doc)

    @router.get("/jobs-briefing/preview")
    async def briefing_preview(_: dict = Depends(auth_dep)):
        jobs = await db.erp_jobs.find({}, {"_id": 0}).to_list(length=None)
        b = build_briefing(jobs)
        b["html"] = render_briefing_html(b)
        b["to"] = BRIEFING_EMAIL
        return b

    @router.post("/jobs-briefing/send")
    async def briefing_send(_: dict = Depends(auth_dep)):
        return await run_daily_briefing(db)
