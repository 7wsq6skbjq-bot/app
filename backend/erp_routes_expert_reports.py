"""Expert Report (Rapport d'expertise) — CRUD + photo upload + PDF + email.

Lets Cédrick create a fully-fledged technical inspection report from the
field: doors inspected, deficiencies observed, photos attached per door,
recommendations and conclusion. The generated PDF matches the professional
layout he already uses (5 numbered sections + cover page).

Photo storage: on disk under `/app/backend/uploads/expert_reports/{id}/`
so we can support arbitrary photo counts without bloating Mongo.
"""
from __future__ import annotations

import asyncio
import base64
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from erp_helpers import csv_response, send_pdf_email
from erp_models import ExpertReport, ExpertReportIn, Party, ReportPhoto
from erp_pdf import render_expert_report_pdf


UPLOADS_ROOT = os.path.join(os.path.dirname(__file__), "uploads", "expert_reports")
os.makedirs(UPLOADS_ROOT, exist_ok=True)

# Very rough per-file cap for uploaded photos (10 MB), plenty for phone JPEGs.
MAX_PHOTO_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


class PhotoUploadItem(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    content_base64: str = Field(..., min_length=1)
    caption: Optional[str] = ""
    door_index: Optional[int] = None
    order: int = 0


class PhotoUploadRequest(BaseModel):
    photos: List[PhotoUploadItem]


class ReportEmailRequest(BaseModel):
    to_email: EmailStr
    subject: Optional[str] = None
    message: Optional[str] = None


def _report_dir(report_id: str) -> str:
    p = os.path.join(UPLOADS_ROOT, report_id)
    os.makedirs(p, exist_ok=True)
    return p


def _safe_ext(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"Extension non supportée : {ext}. "
                                  f"Autorisées : {', '.join(sorted(ALLOWED_EXTENSIONS))}.")
    return ext


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep, next_number) -> None:

    @router.get("/expert-reports", response_model=List[ExpertReport])
    async def list_reports(_: dict = Depends(auth_dep)):
        cur = db.erp_expert_reports.find({}, {"_id": 0}).sort("number", -1)
        return [ExpertReport(**d) async for d in cur]

    @router.post("/expert-reports", response_model=ExpertReport, status_code=201)
    async def create_report(data: ExpertReportIn, _: dict = Depends(auth_dep)):
        number = await next_number("expert_report")
        report = ExpertReport(
            number=number,
            client_snapshot=Party(**data.client_snapshot.model_dump()),
            project_name=data.project_name,
            project_address=data.project_address,
            project_city=data.project_city,
            inspection_date=data.inspection_date,
            inspector_name=data.inspector_name or "Cédrick Pimparé",
            inspector_title=data.inspector_title or "Expert Portes Commerciales – Portech",
            mandated_by=data.mandated_by,
            purpose=data.purpose,
            doors=data.doors,
            risks=data.risks,
            conclusion=data.conclusion,
            status=data.status,
        )
        await db.erp_expert_reports.insert_one(report.model_dump())
        return report

    @router.get("/expert-reports/{report_id}", response_model=ExpertReport)
    async def get_report(report_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Rapport introuvable")
        return ExpertReport(**doc)

    @router.put("/expert-reports/{report_id}", response_model=ExpertReport)
    async def update_report(report_id: str, data: ExpertReportIn,
                             _: dict = Depends(auth_dep)):
        existing = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Rapport introuvable")
        update_fields = {
            "client_snapshot": Party(**data.client_snapshot.model_dump()).model_dump(),
            "project_name": data.project_name,
            "project_address": data.project_address,
            "project_city": data.project_city,
            "inspection_date": data.inspection_date,
            "inspector_name": data.inspector_name or "Cédrick Pimparé",
            "inspector_title": data.inspector_title or "Expert Portes Commerciales – Portech",
            "mandated_by": data.mandated_by,
            "purpose": data.purpose,
            "doors": [d.model_dump() for d in data.doors],
            "risks": data.risks,
            "conclusion": data.conclusion,
            "status": data.status,
        }
        await db.erp_expert_reports.update_one({"id": report_id}, {"$set": update_fields})
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        return ExpertReport(**doc)

    @router.delete("/expert-reports/{report_id}")
    async def delete_report(report_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_expert_reports.delete_one({"id": report_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Rapport introuvable")
        # Cleanup photos on disk
        d = os.path.join(UPLOADS_ROOT, report_id)
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
        return {"deleted": report_id}

    @router.post("/expert-reports/{report_id}/photos",
                  response_model=ExpertReport)
    async def upload_photos(report_id: str, payload: PhotoUploadRequest,
                              _: dict = Depends(auth_dep)):
        """Upload one or more photos to a report. Photos are decoded from
        base64 and written to disk under the report's folder."""
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Rapport introuvable")

        rdir = _report_dir(report_id)
        new_photos: list[dict] = list(doc.get("photos") or [])
        # Determine next order value per door_index
        max_order = {}
        for p in new_photos:
            di = p.get("door_index")
            max_order[di] = max(max_order.get(di, -1), p.get("order", 0))

        for item in payload.photos:
            ext = _safe_ext(item.filename)
            try:
                raw = base64.b64decode(item.content_base64, validate=False)
            except Exception:
                raise HTTPException(400, f"Image « {item.filename} » illisible (base64 invalide).")
            if len(raw) > MAX_PHOTO_BYTES:
                raise HTTPException(413,
                    f"Photo « {item.filename} » trop volumineuse "
                    f"({len(raw) / 1024 / 1024:.1f} Mo). Maximum 10 Mo par photo.")
            photo_id = str(uuid.uuid4())
            stored_name = f"{photo_id}{ext}"
            with open(os.path.join(rdir, stored_name), "wb") as fp:
                fp.write(raw)
            di = item.door_index
            max_order[di] = max_order.get(di, -1) + 1
            new_photos.append(ReportPhoto(
                id=photo_id, filename=stored_name,
                caption=item.caption or "",
                door_index=di, order=item.order or max_order[di],
            ).model_dump())

        await db.erp_expert_reports.update_one(
            {"id": report_id}, {"$set": {"photos": new_photos}},
        )
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        return ExpertReport(**doc)

    @router.delete("/expert-reports/{report_id}/photos/{photo_id}",
                    response_model=ExpertReport)
    async def delete_photo(report_id: str, photo_id: str,
                             _: dict = Depends(auth_dep)):
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Rapport introuvable")
        remaining = []
        removed_filename = None
        for p in doc.get("photos") or []:
            if p.get("id") == photo_id:
                removed_filename = p.get("filename")
                continue
            remaining.append(p)
        if removed_filename is None:
            raise HTTPException(404, "Photo introuvable dans ce rapport")
        # Remove file from disk (best-effort)
        try:
            os.remove(os.path.join(UPLOADS_ROOT, report_id, removed_filename))
        except OSError:
            pass
        await db.erp_expert_reports.update_one(
            {"id": report_id}, {"$set": {"photos": remaining}},
        )
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        return ExpertReport(**doc)

    @router.get("/expert-reports/{report_id}/photos/{filename}")
    async def serve_photo(report_id: str, filename: str,
                            _: dict = Depends(auth_dep)):
        """Serve a photo file back to the UI for thumbnails / previews."""
        # Prevent path traversal
        if not re.match(r"^[A-Za-z0-9\-_.]+$", filename):
            raise HTTPException(400, "Nom de fichier invalide")
        path = os.path.join(UPLOADS_ROOT, report_id, filename)
        if not os.path.isfile(path):
            raise HTTPException(404, "Photo introuvable")
        ext = os.path.splitext(filename)[1].lower()
        media = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
            ".heic": "image/heic",
        }.get(ext, "application/octet-stream")
        with open(path, "rb") as fp:
            data = fp.read()
        return Response(content=data, media_type=media)

    @router.get("/expert-reports/{report_id}/pdf")
    async def download_report_pdf(report_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Rapport introuvable")
        rdir = _report_dir(report_id)
        pdf_bytes = await asyncio.to_thread(render_expert_report_pdf, doc, rdir)
        number = f"RAP-{int(doc['number']):04d}"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'},
        )

    @router.post("/expert-reports/{report_id}/send-email")
    async def send_report_email(report_id: str, payload: ReportEmailRequest,
                                  _: dict = Depends(auth_dep)):
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Rapport introuvable")
        rdir = _report_dir(report_id)
        pdf_bytes = await asyncio.to_thread(render_expert_report_pdf, doc, rdir)
        number = f"RAP-{int(doc['number']):04d}"
        client_name = (doc.get("client_snapshot") or {}).get("name") or ""
        project = doc.get("project_name") or ""

        subject = payload.subject or f"Portech — Rapport d'expertise {number} — {project}"
        message_html = payload.message or (
            f"<p>Bonjour {client_name},</p>"
            f"<p>Vous trouverez en pièce jointe notre <b>rapport d'expertise "
            f"technique {number}</b> concernant le projet <b>{project}</b>.</p>"
            "<p>Nous restons disponibles pour toute clarification ou pour "
            "vous accompagner dans la mise en œuvre des recommandations.</p>"
            "<p>Cordialement,<br/>L'équipe Portech</p>"
        )

        await send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes, filename=f"{number}.pdf",
            footer_note=f"Rapport d'expertise {number} · Portech ERP",
        )

        await db.erp_expert_reports.update_one(
            {"id": report_id},
            {"$set": {
                "status": "envoyé",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_to": payload.to_email,
            }},
        )
        return {"sent": True, "to": payload.to_email}

    @router.get("/exports/expert-reports.csv")
    async def export_reports_csv(_: dict = Depends(auth_dep)):
        rows = []
        async for r in db.erp_expert_reports.find({}, {"_id": 0}).sort("number", -1):
            cs = r.get("client_snapshot") or {}
            rows.append({
                "Numéro": f"RAP-{int(r.get('number', 0)):04d}",
                "Date inspection": r.get("inspection_date") or "",
                "Client": cs.get("name") or "",
                "Projet": r.get("project_name") or "",
                "Ville": r.get("project_city") or "",
                "Nb portes": len(r.get("doors") or []),
                "Nb photos": len(r.get("photos") or []),
                "Statut": r.get("status") or "",
                "Envoyé à": r.get("sent_to") or "",
            })
        return csv_response(rows, "rapports-expertise-portech.csv")
