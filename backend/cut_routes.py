"""Cut List routes — upload, OCR extraction, DXF parsing, optimization, PDF.

Endpoints (mounted under /api/admin):
- GET    /cuts                          List cut lists
- POST   /cuts                          Create
- GET    /cuts/{id}                     Read
- PUT    /cuts/{id}                     Update
- DELETE /cuts/{id}                     Delete
- POST   /cuts/extract                  Upload PDF/image, run Gemini Vision OCR
- POST   /cuts/extract-dxf              Upload DXF, parse with ezdxf
- POST   /cuts/{id}/optimize            Run the 1D optimizer on the cut list
- GET    /cuts/{id}/export.csv          CSV export
- GET    /cuts/{id}/export.pdf          PDF workshop sheet
"""
import csv
import io
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from emergentintegrations.llm.chat import (
    FileContentWithMimeType,
    LlmChat,
    UserMessage,
)
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from cut_dxf import parse_dxf
from cut_models import (
    DEFAULT_ALU_STOCK_LENGTHS_MM,
    DEFAULT_SAW_KERF_MM,
    CutItem,
    CutList,
    CutListIn,
    ITEM_TYPES,
)
from cut_optimizer import optimize_cut_list
from cut_pdf import render_cut_list_pdf

logger = logging.getLogger("portech.cuts")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
OCR_MODEL = os.environ.get("EXPENSE_OCR_MODEL", "gemini-3-flash-preview")
UPLOADS_DIR = Path(os.environ.get("CUT_UPLOADS_DIR", "/app/backend/cut_uploads"))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_PLAN_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
ALLOWED_DXF_EXTS = {".dxf"}
MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".heic": "image/heic", ".heif": "image/heif",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

OCR_SYSTEM = (
    "Tu es un assistant expert en quincaillerie de portes commerciales "
    "(Portech, Grand Montréal). Tu analyses des plans d'architectes / "
    "ingénieurs ou des croquis cotés pour en extraire la liste des éléments "
    "à fabriquer ou installer. Tu retournes UNIQUEMENT du JSON valide."
)

OCR_USER = (
    "Analyse le plan/dessin ci-joint et extrais TOUS les éléments cotés "
    "qui correspondent à de la quincaillerie de porte commerciale.\n"
    "\n"
    "Retourne un objet JSON STRICT avec :\n"
    "{\n"
    '  "items": [ {item_type, label, profile?, material?, length_mm, '
    'width_mm?, thickness_mm?, qty, notes?}, ... ],\n'
    '  "unit_detected": "mm" | "in" | "cm" | "ft" | "unknown",\n'
    '  "confidence": 0..1,\n'
    '  "warnings": ["..."]\n'
    "}\n"
    "\n"
    "Règles d'extraction :\n"
    "- item_type : un de {frame, glass, panel, hardware, hole, other}\n"
    "  • frame = cadre/profilé aluminium linéaire (linteau, montant, traverse)\n"
    "  • glass = vitrage rectangle (longueur × largeur)\n"
    "  • panel = panneau plein (acier, composite)\n"
    "  • hardware = serrure / charnière / ferme-porte / barre antipanique\n"
    "  • hole = perçage / trou Ø\n"
    "- Toutes dimensions en MILLIMÈTRES. Convertis si tu vois des pouces "
    "  (1 in = 25.4 mm) ou pieds (1 ft = 304.8 mm).\n"
    "- Si la même cote apparaît N fois (qty visible), incrémente `qty`.\n"
    "- profile : si tu vois une référence de profilé (Reynaers CS68, "
    "  Kawneer 451, Sapa 5500, etc.), mets-la ici.\n"
    "- material : type de matériau si visible (Alu anodisé, Verre trempé 6mm, etc.)\n"
    "- label : court, ex. 'Linteau haut', 'Vitrage gauche', 'Charnière 3'.\n"
    "- Si tu doutes d'une cote, mets-la quand même mais ajoute un warning.\n"
    "- AUCUN texte hors du JSON. Pas de ```json. Pas d'explication."
)


def _strip_json_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


async def _ocr_plan(file_path: Path, mime: str) -> dict:
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "EMERGENT_LLM_KEY non configurée — OCR indisponible.")
    chat = (
        LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ocr-plan-{uuid.uuid4().hex[:8]}",
            system_message=OCR_SYSTEM,
        )
        .with_model("gemini", OCR_MODEL)
    )
    msg = UserMessage(
        text=OCR_USER,
        file_contents=[FileContentWithMimeType(file_path=str(file_path), mime_type=mime)],
    )
    raw = await chat.send_message(msg)
    raw_text = raw if isinstance(raw, str) else str(raw)
    try:
        data = json.loads(_strip_json_fence(raw_text))
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw_text)
        if not m:
            raise HTTPException(502, "Réponse OCR invalide")
        data = json.loads(m.group(0))

    # Sanitize
    items = []
    for it in data.get("items", []) or []:
        item_type = it.get("item_type", "frame")
        if item_type not in ITEM_TYPES:
            item_type = "other"
        items.append({
            "id": str(uuid.uuid4()),
            "item_type": item_type,
            "label": str(it.get("label") or "")[:140],
            "profile": (it.get("profile") or None) or None,
            "material": (it.get("material") or None) or None,
            "length_mm": float(it.get("length_mm") or 0),
            "width_mm": float(it.get("width_mm")) if it.get("width_mm") not in (None, "") else None,
            "thickness_mm": float(it.get("thickness_mm")) if it.get("thickness_mm") not in (None, "") else None,
            "qty": int(it.get("qty") or 1) if str(it.get("qty") or "").replace(".", "").isdigit() else 1,
            "notes": (it.get("notes") or None) or None,
            "source": "ocr",
        })
    return {
        "items": items,
        "unit_detected": data.get("unit_detected", "unknown"),
        "confidence": float(data.get("confidence") or 0),
        "warnings": data.get("warnings", []) or [],
    }


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.get("/cuts/meta")
    async def cuts_meta(_: dict = Depends(auth_dep)):
        return {
            "item_types": ITEM_TYPES,
            "default_stock_lengths_mm": DEFAULT_ALU_STOCK_LENGTHS_MM,
            "default_saw_kerf_mm": DEFAULT_SAW_KERF_MM,
        }

    @router.get("/cuts")
    async def list_cuts(_: dict = Depends(auth_dep)):
        cur = db.erp_cut_lists.find({}, {"_id": 0}).sort("updated_at", -1).limit(200)
        rows = [d async for d in cur]
        # Drop heavy "items" from list view to keep payload light
        return [{k: v for k, v in r.items() if k not in ("items", "last_optimization")} | {"items_count": len(r.get("items", []))} for r in rows]

    @router.post("/cuts", status_code=201, response_model=CutList)
    async def create_cut(data: CutListIn, _: dict = Depends(auth_dep)):
        cut = CutList(**data.model_dump())
        await db.erp_cut_lists.insert_one(cut.model_dump())
        return cut

    @router.get("/cuts/{cut_id}", response_model=CutList)
    async def get_cut(cut_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Liste de coupe introuvable")
        return CutList(**doc)

    @router.put("/cuts/{cut_id}", response_model=CutList)
    async def update_cut(cut_id: str, data: CutListIn, _: dict = Depends(auth_dep)):
        update = data.model_dump()
        update["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = await db.erp_cut_lists.update_one({"id": cut_id}, {"$set": update})
        if res.matched_count == 0:
            raise HTTPException(404, "Liste de coupe introuvable")
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        return CutList(**doc)

    @router.delete("/cuts/{cut_id}")
    async def delete_cut(cut_id: str, _: dict = Depends(auth_dep)):
        res = await db.erp_cut_lists.delete_one({"id": cut_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Liste de coupe introuvable")
        return {"deleted": cut_id}

    @router.post("/cuts/extract")
    async def extract_from_plan(
        file: UploadFile = File(...),
        _: dict = Depends(auth_dep),
    ):
        """Upload a PDF/image plan, run Gemini Vision OCR, return items."""
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_PLAN_EXTS:
            raise HTTPException(400, f"Format non supporté. Acceptés : {', '.join(sorted(ALLOWED_PLAN_EXTS))}")
        contents = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"Fichier trop volumineux (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB)")
        fname = f"plan_{uuid.uuid4().hex}{ext}"
        out_path = UPLOADS_DIR / fname
        out_path.write_bytes(contents)
        mime = MIME_BY_EXT.get(ext, "application/octet-stream")
        try:
            result = await _ocr_plan(out_path, mime)
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("OCR plan failed: %s", exc)
            raise HTTPException(502, f"Échec de l'extraction OCR : {exc}")
        finally:
            # Remove uploaded file after parsing — we keep only the structured items
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
        return {
            "source_filename": fname,
            "source_type": "pdf" if ext == ".pdf" else "image",
            **result,
        }

    @router.post("/cuts/extract-dxf")
    async def extract_from_dxf(
        file: UploadFile = File(...),
        _: dict = Depends(auth_dep),
    ):
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_DXF_EXTS:
            raise HTTPException(400, "Format non supporté. Utilisez un fichier .dxf")
        contents = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"Fichier trop volumineux (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB)")
        fname = f"plan_{uuid.uuid4().hex}{ext}"
        out_path = UPLOADS_DIR / fname
        out_path.write_bytes(contents)
        try:
            result = parse_dxf(str(out_path))
        finally:
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
        # Attach UUIDs to items
        for it in result.get("items", []):
            it["id"] = str(uuid.uuid4())
        return {
            "source_filename": fname,
            "source_type": "dxf",
            **result,
        }

    @router.post("/cuts/{cut_id}/optimize")
    async def optimize(cut_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Liste de coupe introuvable")
        opt = optimize_cut_list(
            items=doc.get("items", []),
            stock_lengths_mm=doc.get("stock_lengths_mm") or DEFAULT_ALU_STOCK_LENGTHS_MM,
            kerf_mm=int(doc.get("saw_kerf_mm") or DEFAULT_SAW_KERF_MM),
        )
        await db.erp_cut_lists.update_one(
            {"id": cut_id},
            {"$set": {
                "last_optimization": opt,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return opt

    @router.post("/cuts/optimize-preview")
    async def optimize_preview(payload: CutListIn, _: dict = Depends(auth_dep)):
        """Run the optimizer on the inline payload without persisting."""
        items = [it.model_dump() if hasattr(it, "model_dump") else it for it in payload.items]
        return optimize_cut_list(
            items=items,
            stock_lengths_mm=payload.stock_lengths_mm or DEFAULT_ALU_STOCK_LENGTHS_MM,
            kerf_mm=int(payload.saw_kerf_mm or DEFAULT_SAW_KERF_MM),
        )

    @router.get("/cuts/{cut_id}/export.csv")
    async def export_csv(cut_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Liste de coupe introuvable")
        buf = io.StringIO()
        buf.write("\ufeff")
        w = csv.writer(buf)
        w.writerow(["Type", "Label", "Profilé", "Matériau",
                    "Long. (mm)", "Larg. (mm)", "Épais. (mm)", "Qté",
                    "Pos. X", "Pos. Y", "Notes"])
        for it in doc.get("items", []):
            w.writerow([
                it.get("item_type", ""),
                it.get("label", ""),
                it.get("profile") or "",
                it.get("material") or "",
                f"{float(it.get('length_mm', 0) or 0):.1f}",
                f"{float(it.get('width_mm') or 0):.1f}" if it.get("width_mm") else "",
                f"{float(it.get('thickness_mm') or 0):.1f}" if it.get("thickness_mm") else "",
                str(it.get("qty", 1) or 1),
                str(it.get("position_x") or ""),
                str(it.get("position_y") or ""),
                (it.get("notes") or "").replace("\n", " "),
            ])
        buf.seek(0)
        safe_name = re.sub(r"[^a-zA-Z0-9-]+", "-", (doc.get("name") or "liste-coupe"))
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="coupes-{safe_name}.csv"'},
        )

    @router.get("/cuts/{cut_id}/export.pdf")
    async def export_pdf(cut_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_cut_lists.find_one({"id": cut_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Liste de coupe introuvable")
        # Always recompute optimization for the latest items
        opt = optimize_cut_list(
            items=doc.get("items", []),
            stock_lengths_mm=doc.get("stock_lengths_mm") or DEFAULT_ALU_STOCK_LENGTHS_MM,
            kerf_mm=int(doc.get("saw_kerf_mm") or DEFAULT_SAW_KERF_MM),
        )
        pdf_bytes = render_cut_list_pdf(doc, opt)
        safe_name = re.sub(r"[^a-zA-Z0-9-]+", "-", (doc.get("name") or "liste-coupe"))
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="coupes-{safe_name}.pdf"'},
        )
