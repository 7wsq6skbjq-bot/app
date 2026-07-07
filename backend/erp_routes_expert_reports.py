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
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
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


# ───────────────────────────────────────────────────────────────────
# GridFS-backed photo storage (survives container redeploys)
# ───────────────────────────────────────────────────────────────────
# Photos are stored twice:
#   1. Immediately on the local disk (fast for the very next PDF render)
#   2. In MongoDB GridFS, keyed by our own photo_id in the file's metadata
#
# On any redeploy, the disk is wiped — before serving/PDF-rendering we
# re-hydrate the disk from GridFS on-demand.

def _gridfs(db: AsyncIOMotorDatabase) -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(db, bucket_name="expert_report_photos")


async def _hydrate_disk_from_gridfs(db: AsyncIOMotorDatabase,
                                     report_id: str,
                                     photos: list[dict]) -> None:
    """For each photo, make sure the file exists on disk. If not, fetch
    from GridFS and write it. Silently skips photos that have no GridFS
    entry (legacy / already-lost)."""
    if not photos:
        return
    bucket = _gridfs(db)
    rdir = _report_dir(report_id)
    for p in photos:
        stored = p.get("filename")
        if not stored:
            continue
        path = os.path.join(rdir, stored)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        # Locate the GridFS file by metadata.photo_id
        photo_id = p.get("id")
        if not photo_id:
            continue
        cursor = bucket.find({"metadata.photo_id": photo_id})
        gf_doc = await cursor.to_list(length=1)
        if not gf_doc:
            continue
        try:
            stream = await bucket.open_download_stream(gf_doc[0]["_id"])
            data = await stream.read()
        except NoFile:
            continue
        with open(path, "wb") as fp:
            fp.write(data)


async def _store_in_gridfs(db: AsyncIOMotorDatabase, *,
                            photo_id: str, report_id: str,
                            filename: str, content_type: str,
                            raw: bytes) -> None:
    bucket = _gridfs(db)
    await bucket.upload_from_stream(
        filename, raw,
        metadata={
            "photo_id": photo_id,
            "report_id": report_id,
            "content_type": content_type,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        },
    )


async def _delete_from_gridfs(db: AsyncIOMotorDatabase, photo_id: str) -> None:
    bucket = _gridfs(db)
    cursor = bucket.find({"metadata.photo_id": photo_id})
    async for gf in cursor:
        try:
            await bucket.delete(gf["_id"])
        except NoFile:
            pass


async def _delete_all_report_photos_from_gridfs(db: AsyncIOMotorDatabase,
                                                  report_id: str) -> None:
    bucket = _gridfs(db)
    cursor = bucket.find({"metadata.report_id": report_id})
    async for gf in cursor:
        try:
            await bucket.delete(gf["_id"])
        except NoFile:
            pass


def _ext_to_media(ext: str) -> str:
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".heic": "image/heic",
    }.get(ext.lower(), "application/octet-stream")


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
        # Cascade delete: photos on disk AND in GridFS
        d = os.path.join(UPLOADS_ROOT, report_id)
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
        await _delete_all_report_photos_from_gridfs(db, report_id)
        return {"deleted": report_id}

    @router.post("/expert-reports/{report_id}/photos",
                  response_model=ExpertReport)
    async def upload_photos(report_id: str, payload: PhotoUploadRequest,
                              _: dict = Depends(auth_dep)):
        """Upload one or more photos to a report. Photos are decoded from
        base64 and written to disk under the report's folder.

        Per-photo errors are tolerated : if one file fails validation, we
        skip it and keep going. Callers using the recommended
        one-at-a-time client flow will therefore still get useful HTTP
        status codes on truly bad payloads, but a batch that has ONE bad
        file won't nuke the whole upload.
        """
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Rapport introuvable")

        rdir = _report_dir(report_id)
        new_photos: list[dict] = list(doc.get("photos") or [])
        max_order: dict = {}
        for p in new_photos:
            di = p.get("door_index")
            max_order[di] = max(max_order.get(di, -1), p.get("order", 0))

        rejected: list[dict] = []
        accepted_count = 0
        for item in payload.photos:
            try:
                ext = _safe_ext(item.filename)
            except HTTPException as e:
                rejected.append({"filename": item.filename, "reason": e.detail})
                continue
            try:
                raw = base64.b64decode(item.content_base64, validate=False)
            except Exception:
                rejected.append({"filename": item.filename,
                                  "reason": "base64 invalide"})
                continue
            if len(raw) > MAX_PHOTO_BYTES:
                rejected.append({
                    "filename": item.filename,
                    "reason": f"trop volumineuse ({len(raw) / 1024 / 1024:.1f} Mo)",
                })
                continue
            photo_id = str(uuid.uuid4())
            stored_name = f"{photo_id}{ext}"
            try:
                with open(os.path.join(rdir, stored_name), "wb") as fp:
                    fp.write(raw)
            except OSError as e:
                rejected.append({"filename": item.filename,
                                  "reason": f"erreur disque : {e}"})
                continue
            # ── ALSO persist in GridFS so photos survive redeploys ──
            try:
                await _store_in_gridfs(
                    db, photo_id=photo_id, report_id=report_id,
                    filename=stored_name,
                    content_type=_ext_to_media(ext), raw=raw,
                )
            except Exception as e:
                # Roll back disk file so we never claim ownership of a photo
                # that has no persistent copy.
                try:
                    os.remove(os.path.join(rdir, stored_name))
                except OSError:
                    pass
                rejected.append({"filename": item.filename,
                                  "reason": f"erreur GridFS : {e}"})
                continue
            di = item.door_index
            max_order[di] = max_order.get(di, -1) + 1
            new_photos.append(ReportPhoto(
                id=photo_id, filename=stored_name,
                caption=item.caption or "",
                door_index=di,
                order=item.order if item.order > 0 else max_order[di],
            ).model_dump())
            accepted_count += 1

        # If EVERYTHING was rejected, tell the caller
        if accepted_count == 0 and rejected:
            raise HTTPException(400, f"Aucune photo acceptée. Refus : {rejected}")

        await db.erp_expert_reports.update_one(
            {"id": report_id}, {"$set": {"photos": new_photos}},
        )
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        # We return the standard ExpertReport model — the response_model
        # strips any extra fields, so rejected info goes into the log only.
        if rejected:
            import logging as _lg
            _lg.getLogger("portech.erp").warning(
                "Rapport %s : %d photo(s) refusée(s) — %s",
                report_id, len(rejected), rejected,
            )
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
        # Remove from GridFS (persistent)
        await _delete_from_gridfs(db, photo_id)
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
        # If missing on disk (e.g. after container redeploy) try GridFS
        if not os.path.isfile(path):
            doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
            if doc:
                await _hydrate_disk_from_gridfs(
                    db, report_id, doc.get("photos") or [],
                )
        if not os.path.isfile(path):
            raise HTTPException(404, "Photo introuvable")
        ext = os.path.splitext(filename)[1].lower()
        media = _ext_to_media(ext)
        with open(path, "rb") as fp:
            data = fp.read()
        return Response(content=data, media_type=media)

    @router.get("/expert-reports/{report_id}/pdf")
    async def download_report_pdf(report_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_expert_reports.find_one({"id": report_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Rapport introuvable")
        # Make sure every photo file is on disk before the sync renderer runs
        await _hydrate_disk_from_gridfs(db, report_id, doc.get("photos") or [])
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
        # Rehydrate photos from GridFS if disk cache is empty
        await _hydrate_disk_from_gridfs(db, report_id, doc.get("photos") or [])
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
