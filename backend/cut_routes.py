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
from cut_door_breakdown import decompose_at_door
from cut_models import (
    DEFAULT_ALU_STOCK_LENGTHS_MM,
    DEFAULT_SAW_KERF_MM,
    CutItem,
    CutList,
    CutListIn,
    FrameSpecs,
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
    "(Portech, Grand Montréal). Tu analyses des plans d'atelier (AT Fabrication, "
    "Kawneer, Reynaers, etc.) pour produire une LISTE DE COUPE PRÊTE À "
    "FABRIQUER. Tu sais lire les CARTOUCHES de détails techniques où sont "
    "indiquées les épaisseurs de profilés, les lousses, le finis (couleur "
    "anodisée), la SÉRIE de porte (AT1000, AT2000), et la liste exhaustive "
    "de quincaillerie avec numéros de pièce (UH-120-DA, ADAM-MS1853S320, "
    "UNIQ-AC4-36, ILCO-..., etc.). Tu retournes UNIQUEMENT du JSON valide."
)

OCR_USER = (
    "Analyse ce plan d'atelier commercial et produis une LISTE DE COUPE EXHAUSTIVE.\n"
    "\n"
    "ÉTAPE 1 — Lis SOIGNEUSEMENT le cartouche / les blocs de détails :\n"
    "- COULEUR / FINI du cadre ET de la porte (souvent différents) : "
    "  'Anodisé bronze architectural', 'Anodisé noir', 'Anodisé clair', etc.\n"
    "- SÉRIE de la porte : AT1000, AT2000, ATi1000 (isolée), ATi2000 (isolée). "
    "  C'est UN de ces 4 modèles — pas d'hybride 'AT1000-AT2000-base'.\n"
    "- Épaisseurs des PROFILÉS du cadre (montants, linteau) — souvent un même "
    "  tube à ailettes 1¾\" × 4\" pour tous les côtés.\n"
    "- Épaisseurs des PROFILÉS de la porte : traverse haute (top rail), "
    "  traverse basse (bottom rail), montant charnière, montant serrure.\n"
    "- LOUSSES (clearances) : lousse latérale, lousse haut, lousse sous-porte.\n"
    "- SEUIL (threshold) : présent ou non, épaisseur (typiquement 12.7 mm = ½\").\n"
    "- VITRAGE : type (trempé / thermos), épaisseur (6 mm simple ou 25.4 mm thermos).\n"
    "\n"
    "ÉTAPE 2 — Liste TOUS les éléments de QUINCAILLERIE du cartouche, MÊME "
    "ceux qui semblent anodins. Pour CHACUN, donne :\n"
    "- label (court, ex. 'Serrure MS Adams Rite')\n"
    "- part_number (ex. 'ADAM-MS1853S320', 'UH-120-DA', 'UNIQ-AC4-36', "
    "  'ILCO-7165SC229KD') — RECOPIE le numéro EXACTEMENT comme écrit\n"
    "- manufacturer (ex. 'AT Fabrication', 'ASSA ABLOY Adams Rite', 'ILCO Kaba', "
    "  'Unique', 'LCN', 'Norton')\n"
    "- qty (1 par défaut si non indiqué)\n"
    "Inclus : charnière, serrure, têtière, cylindre extérieur, tourniquet "
    "intérieur, collets, gâche, ferme-porte, barre anti-panique, paddle, "
    "poignée, butoir, seuil, joints, etc.\n"
    "\n"
    "ÉTAPE 3 — Pour les CADRES (encadrement), liste les coupes avec règle :\n"
    "- Montants verticaux = hauteur totale du cadre (fabrication height brute)\n"
    "- Linteau / seuil horizontal = largeur du cadre - 2 × épaisseur_montant "
    "  (toujours ! Le linteau passe ENTRE les montants verticaux)\n"
    "- Renseigne opening_length_mm (cote brute du plan) ET length_mm (cote finale après soustraction).\n"
    "\n"
    "ÉTAPE 4 — Pour les VITRAGES adjacents (sidelites, transoms), donne "
    "dimensions finales (après lousses).\n"
    "\n"
    "ÉTAPE 5 — Pour la PORTE elle-même, NE LA DÉCOMPOSE PAS en 4 pièces "
    "(le backend Portech le fait automatiquement). Liste-la comme UN SEUL "
    "item type='panel' avec :\n"
    "- label = 'Porte AT1000' (ou AT2000 selon la série détectée)\n"
    "- profile = la série exacte (ex. 'AT1000 avec base AT2000')\n"
    "- length_mm = hauteur finale de la PORTE LEAF (après lousses haut+bas+seuil)\n"
    "- width_mm = largeur finale de la PORTE LEAF (après lousses latérales)\n"
    "- thickness_mm = 44.5 (1¾\")\n"
    "- opening_length_mm / opening_width_mm = ouverture libre brute (avant lousses)\n"
    "- material = couleur anodisée exacte\n"
    "\n"
    "Retourne ce JSON STRICT :\n"
    "{\n"
    '  "items": [ { item_type, label, profile?, material?, part_number?, '
    'manufacturer?, length_mm, width_mm?, thickness_mm?, qty, '
    'opening_length_mm?, opening_width_mm?, notes? }, ... ],\n'
    '  "frame_specs": {\n'
    '    "mullion_thickness_mm"?: number,\n'
    '    "jamb_thickness_mm"?: number,\n'
    '    "head_thickness_mm"?: number,\n'
    '    "profile_depth_mm"?: number,\n'
    '    "side_clearance_mm"?: number,\n'
    '    "head_clearance_mm"?: number,\n'
    '    "undercut_clearance_mm"?: number,\n'
    '    "threshold_thickness_mm"?: number,\n'
    '    "has_threshold"?: boolean\n'
    "  },\n"
    '  "door_info": {\n'
    '    "series"?: "AT1000" | "AT2000" | "ATi1000" | "ATi2000",\n'
    '    "leaf_width_mm"?: number,\n'
    '    "leaf_height_mm"?: number,\n'
    '    "is_insulated"?: boolean,\n'
    '    "glass_thickness_mm"?: number,\n'
    '    "frame_finish"?: "Anodisé bronze" | "Anodisé noir" | ...,\n'
    '    "door_finish"?: "..."\n'
    "  },\n"
    '  "unit_detected": "mm" | "in" | "cm" | "ft" | "unknown",\n'
    '  "confidence": 0..1,\n'
    '  "warnings": ["..."]\n'
    "}\n"
    "\n"
    "Règles :\n"
    "- Toutes dimensions en MILLIMÈTRES (1 in = 25.4 mm, fractions: 11/16\" = 17.46 mm, 3/4\" = 19.05 mm, 1¾\" = 44.45 mm).\n"
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
            "part_number": (it.get("part_number") or None) or None,
            "manufacturer": (it.get("manufacturer") or None) or None,
            "length_mm": float(it.get("length_mm") or 0),
            "width_mm": float(it.get("width_mm")) if it.get("width_mm") not in (None, "") else None,
            "thickness_mm": float(it.get("thickness_mm")) if it.get("thickness_mm") not in (None, "") else None,
            "qty": int(it.get("qty") or 1) if str(it.get("qty") or "").replace(".", "").isdigit() else 1,
            "opening_length_mm": float(it.get("opening_length_mm")) if it.get("opening_length_mm") not in (None, "") else None,
            "opening_width_mm": float(it.get("opening_width_mm")) if it.get("opening_width_mm") not in (None, "") else None,
            "notes": (it.get("notes") or None) or None,
            "source": "ocr",
        })
    return {
        "items": items,
        "frame_specs": data.get("frame_specs") or {},
        "door_info": data.get("door_info") or {},
        "unit_detected": data.get("unit_detected", "unknown"),
        "confidence": float(data.get("confidence") or 0),
        "warnings": data.get("warnings", []) or [],
    }


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.post("/cuts/decompose-door")
    async def decompose_door(payload: dict, _: dict = Depends(auth_dep)):
        """Take a 'panel'-type door spec and return the 4 frame pieces + 8 mouldings
        + hardware positions. Frontend calls this after the user fills in or
        confirms the door dimensions / series. No persistence.
        """
        try:
            door_w = float(payload.get("door_width_mm") or 0)
            door_h = float(payload.get("door_height_mm") or 0)
        except (TypeError, ValueError):
            raise HTTPException(400, "door_width_mm et door_height_mm requis (mm).")
        if door_w <= 0 or door_h <= 0:
            raise HTTPException(400, "door_width_mm et door_height_mm doivent être > 0.")
        result = decompose_at_door(
            door_width_mm=door_w,
            door_height_mm=door_h,
            series=str(payload.get("series") or "AT1000"),
            glass_thickness_mm=float(payload.get("glass_thickness_mm") or 6.0),
            material=str(payload.get("material") or "Aluminium anodisé bronze"),
            label_prefix=str(payload.get("label_prefix") or "Porte"),
            qty=int(payload.get("qty") or 1),
            hardware_rules=payload.get("hardware_rules") or None,
        )
        return {
            "items": result.items + result.hardware,
            "notes": result.notes,
        }

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

        # AUTO-DECOMPOSE any AT door panel the OCR detected. This was previously
        # a manual click ("Décomposer porte AT") — users want it to happen
        # automatically on import (#1 from feedback session).
        items = result.get("items") or []
        door_info = result.get("door_info") or {}
        decomposed_notes: list[str] = []
        if door_info:
            # Use door_info if present, else look for a panel matching AT*
            series = door_info.get("series") or ""
            leaf_w = door_info.get("leaf_width_mm")
            leaf_h = door_info.get("leaf_height_mm")
            glass_t = door_info.get("glass_thickness_mm") or 6.0
            finish = door_info.get("door_finish") or door_info.get("frame_finish") \
                or "Aluminium anodisé bronze"
            if series and leaf_w and leaf_h:
                br = decompose_at_door(
                    door_width_mm=float(leaf_w),
                    door_height_mm=float(leaf_h),
                    series=str(series),
                    glass_thickness_mm=float(glass_t),
                    material=str(finish),
                    label_prefix="Porte",
                    qty=1,
                )
                # Remove any panel item the OCR added for the door (so we don't double-count)
                items = [
                    it for it in items
                    if not (it.get("item_type") == "panel"
                            and re.search(r"AT\s*1?2?000", (it.get("profile") or "") + (it.get("label") or ""), re.I))
                ]
                items.extend(br.items + br.hardware)
                decomposed_notes.extend(br.notes)
                decomposed_notes.append(
                    f"Porte AT décomposée automatiquement à l'import (série {series})."
                )

        warnings = list(result.get("warnings") or []) + decomposed_notes
        return {
            "source_filename": fname,
            "source_type": "pdf" if ext == ".pdf" else "image",
            "items": items,
            "frame_specs": result.get("frame_specs") or {},
            "door_info": door_info,
            "unit_detected": result.get("unit_detected", "unknown"),
            "confidence": result.get("confidence", 0),
            "warnings": warnings,
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
                    "N° pièce", "Fabricant",
                    "Long. (mm)", "Larg. (mm)", "Épais. (mm)", "Qté",
                    "Pos. X", "Pos. Y", "Notes"])
        for it in doc.get("items", []):
            w.writerow([
                it.get("item_type", ""),
                it.get("label", ""),
                it.get("profile") or "",
                it.get("material") or "",
                it.get("part_number") or "",
                it.get("manufacturer") or "",
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
