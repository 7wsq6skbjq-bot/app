"""Expense CRUD + monthly summary + CSV export + receipt photo upload + OCR."""
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
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_models_expense import (
    EXPENSE_CATEGORIES,
    PAYMENT_METHODS,
    STATUSES,
    Expense,
    ExpenseIn,
)

logger = logging.getLogger("portech.expenses")

RECEIPTS_DIR = Path(os.environ.get("EXPENSE_RECEIPTS_DIR", "/app/backend/receipts"))
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_RECEIPT_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"}
ALLOWED_RECEIPT_MIME = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif",
    "application/pdf",
}
MAX_RECEIPT_BYTES = 8 * 1024 * 1024  # 8 MB

# ---------------------------------------------------------------------------
# OCR — Gemini multimodal
# ---------------------------------------------------------------------------
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
OCR_MODEL = os.environ.get("EXPENSE_OCR_MODEL", "gemini-3-flash-preview")

# Mime types Gemini handles directly via file path
GEMINI_MIME_BY_EXT = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".heic": "image/heic", ".heif": "image/heif",
    ".pdf": "application/pdf",
}

OCR_SYSTEM_PROMPT = (
    "Tu es un assistant de comptabilité qui analyse les reçus de dépenses d'une "
    "entreprise québécoise (Portech, quincaillerie de portes commerciales). "
    "Tu retournes UNIQUEMENT du JSON valide, sans aucun texte avant ou après, "
    "sans bloc de code markdown."
)

OCR_USER_PROMPT = (
    "Analyse l'image du reçu/facture ci-jointe et retourne un objet JSON avec "
    "exactement ces champs :\n"
    "- merchant_name (string ou null) : nom du commerce/fournisseur sur le reçu\n"
    "- date (string YYYY-MM-DD ou null) : date du reçu\n"
    "- subtotal (number ou null) : montant avant taxes (sous-total HT)\n"
    "- tps (number ou null) : montant de la TPS (GST, taxe fédérale 5%)\n"
    "- tvq (number ou null) : montant de la TVQ (taxe Québec 9.975%)\n"
    "- total (number ou null) : montant total payé\n"
    "- suggested_category (string) : une seule valeur parmi : "
    f"{', '.join(EXPENSE_CATEGORIES)}\n"
    "- invoice_ref (string ou null) : numéro de facture/reçu visible\n"
    "- confidence (number 0 à 1) : ta confiance globale dans l'extraction\n"
    "\n"
    "Règles :\n"
    "- Si le reçu n'a qu'un montant total (sans détail des taxes), "
    "  calcule subtotal/tps/tvq à rebours avec les taux 5% et 9.975%.\n"
    "- Pour la catégorie, déduis-la du commerce : Canadian Tire/Rona/Home Depot → "
    "Matériaux ; station-service → Carburant ; restaurant → Repas/Représentation ; "
    "logiciel SaaS → Abonnements logiciels ; etc.\n"
    "- Si tu ne peux pas lire le reçu, retourne tous les champs à null mais "
    "  garde confidence à 0.\n"
    "- AUCUN texte hors du JSON. Pas de ```json ... ```."
)


def _strip_json_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


async def _ocr_receipt(file_path: Path, mime_type: str) -> dict:
    """Call Gemini multimodal to extract structured data from a receipt image."""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "EMERGENT_LLM_KEY non configurée — OCR indisponible.")
    chat = (
        LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ocr-receipt-{uuid.uuid4().hex[:8]}",
            system_message=OCR_SYSTEM_PROMPT,
        )
        .with_model("gemini", OCR_MODEL)
    )
    file_content = FileContentWithMimeType(
        file_path=str(file_path),
        mime_type=mime_type,
    )
    msg = UserMessage(text=OCR_USER_PROMPT, file_contents=[file_content])
    raw = await chat.send_message(msg)
    raw_text = raw if isinstance(raw, str) else str(raw)
    try:
        data = json.loads(_strip_json_fence(raw_text))
    except json.JSONDecodeError:
        logger.warning("OCR non-JSON response: %s", raw_text[:300])
        # Sometimes the model wraps in extra text — find the first { … } block
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if not match:
            raise HTTPException(502, "Réponse OCR invalide")
        data = json.loads(match.group(0))
    # Sanitize numeric fields
    for k in ("subtotal", "tps", "tvq", "total", "confidence"):
        v = data.get(k)
        if v in ("", None):
            data[k] = None
        else:
            try:
                data[k] = float(v)
            except (TypeError, ValueError):
                data[k] = None
    # Validate category
    if data.get("suggested_category") not in EXPENSE_CATEGORIES:
        data["suggested_category"] = "Autre"
    return data


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.get("/expenses/meta")
    async def expense_meta(_: dict = Depends(auth_dep)):
        """Return categories + payment methods + statuses for the frontend."""
        return {
            "categories": EXPENSE_CATEGORIES,
            "payment_methods": PAYMENT_METHODS,
            "statuses": STATUSES,
        }

    @router.get("/expenses")
    async def list_expenses(
        category: Optional[str] = None,
        status: Optional[str] = None,
        month: Optional[str] = None,  # "YYYY-MM"
        supplier_id: Optional[str] = None,
        _: dict = Depends(auth_dep),
    ):
        query: dict = {}
        if category:
            query["category"] = category
        if status:
            query["status"] = status
        if supplier_id:
            query["supplier_id"] = supplier_id
        if month and len(month) == 7:
            query["date"] = {"$gte": f"{month}-01", "$lt": f"{month}-32"}
        cur = db.erp_expenses.find(query, {"_id": 0}).sort("date", -1).limit(1000)
        return [d async for d in cur]

    @router.post("/expenses", status_code=201, response_model=Expense)
    async def create_expense(data: ExpenseIn, _: dict = Depends(auth_dep)):
        exp = Expense(**data.model_dump())
        await db.erp_expenses.insert_one(exp.model_dump())
        return exp

    @router.put("/expenses/{expense_id}", response_model=Expense)
    async def update_expense(expense_id: str, data: ExpenseIn, _: dict = Depends(auth_dep)):
        update = data.model_dump()
        update["updated_at"] = datetime.now(timezone.utc).isoformat()
        res = await db.erp_expenses.update_one({"id": expense_id}, {"$set": update})
        if res.matched_count == 0:
            raise HTTPException(404, "Dépense introuvable")
        doc = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        return Expense(**doc)

    @router.delete("/expenses/{expense_id}")
    async def delete_expense(expense_id: str, _: dict = Depends(auth_dep)):
        # Delete receipt file too
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if exp and exp.get("receipt_filename"):
            fp = RECEIPTS_DIR / exp["receipt_filename"]
            if fp.exists():
                try:
                    fp.unlink()
                except Exception:
                    pass
        res = await db.erp_expenses.delete_one({"id": expense_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Dépense introuvable")
        return {"deleted": expense_id}

    @router.get("/expenses/summary")
    async def expenses_summary(
        month: Optional[str] = Query(default=None),
        _: dict = Depends(auth_dep),
    ):
        """Return totals + by-category breakdown for a given month (default: current)."""
        if not month:
            month = datetime.now(timezone.utc).strftime("%Y-%m")
        cur = db.erp_expenses.find(
            {"date": {"$gte": f"{month}-01", "$lt": f"{month}-32"}},
            {"_id": 0},
        )
        rows = [d async for d in cur]
        total = sum(float(r.get("total", 0)) for r in rows)
        subtotal = sum(float(r.get("subtotal", 0)) for r in rows)
        tps = sum(float(r.get("tps", 0)) for r in rows)
        tvq = sum(float(r.get("tvq", 0)) for r in rows)
        by_cat: dict[str, float] = {}
        for r in rows:
            c = r.get("category", "Autre")
            by_cat[c] = by_cat.get(c, 0.0) + float(r.get("total", 0))
        by_category = sorted(
            [{"category": k, "total": round(v, 2)} for k, v in by_cat.items()],
            key=lambda x: -x["total"],
        )
        return {
            "month": month,
            "count": len(rows),
            "subtotal": round(subtotal, 2),
            "tps": round(tps, 2),
            "tvq": round(tvq, 2),
            "total": round(total, 2),
            "by_category": by_category,
        }

    @router.post("/expenses/{expense_id}/receipt", status_code=201)
    async def upload_receipt(
        expense_id: str,
        file: UploadFile = File(...),
        _: dict = Depends(auth_dep),
    ):
        """Upload a receipt photo (or PDF) for an expense.

        Replaces any existing receipt. Returns the new filename.
        """
        # Validate
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_RECEIPT_EXTS:
            raise HTTPException(400, f"Format non supporté. Formats acceptés : {', '.join(sorted(ALLOWED_RECEIPT_EXTS))}")
        if file.content_type and file.content_type not in ALLOWED_RECEIPT_MIME:
            # Some browsers send `application/octet-stream`; only block if it's a known bad type
            if file.content_type.startswith("text/") or "script" in file.content_type:
                raise HTTPException(400, "Type de fichier non autorisé")

        # Check the expense exists
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if not exp:
            raise HTTPException(404, "Dépense introuvable")

        # Read with size cap
        contents = await file.read(MAX_RECEIPT_BYTES + 1)
        if len(contents) > MAX_RECEIPT_BYTES:
            raise HTTPException(413, f"Fichier trop volumineux (max {MAX_RECEIPT_BYTES // 1024 // 1024} MB)")

        # Remove previous file if any
        if exp.get("receipt_filename"):
            old = RECEIPTS_DIR / exp["receipt_filename"]
            if old.exists():
                try:
                    old.unlink()
                except Exception:
                    pass

        # Save with a fresh UUID name to avoid collisions
        fname = f"{expense_id}_{uuid.uuid4().hex[:8]}{ext}"
        out_path = RECEIPTS_DIR / fname
        out_path.write_bytes(contents)

        await db.erp_expenses.update_one(
            {"id": expense_id},
            {"$set": {"receipt_filename": fname, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"receipt_filename": fname, "size": len(contents)}

    @router.get("/expenses/{expense_id}/receipt")
    async def download_receipt(expense_id: str, _: dict = Depends(auth_dep)):
        """Stream the receipt file. Authenticated only."""
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if not exp or not exp.get("receipt_filename"):
            raise HTTPException(404, "Aucun reçu pour cette dépense")
        fp = RECEIPTS_DIR / exp["receipt_filename"]
        if not fp.exists():
            raise HTTPException(404, "Fichier introuvable")
        # Pick mime by extension
        mime_by_ext = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".webp": "image/webp", ".heic": "image/heic", ".heif": "image/heif",
            ".pdf": "application/pdf",
        }
        mime = mime_by_ext.get(fp.suffix.lower(), "application/octet-stream")
        return FileResponse(fp, media_type=mime, filename=fp.name)

    @router.delete("/expenses/{expense_id}/receipt")
    async def delete_receipt(expense_id: str, _: dict = Depends(auth_dep)):
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if not exp:
            raise HTTPException(404, "Dépense introuvable")
        fname = exp.get("receipt_filename")
        if fname:
            fp = RECEIPTS_DIR / fname
            if fp.exists():
                try:
                    fp.unlink()
                except Exception:
                    pass
        await db.erp_expenses.update_one(
            {"id": expense_id},
            {"$set": {"receipt_filename": None, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"deleted": True}

    @router.post("/expenses/{expense_id}/receipt/ocr")
    async def ocr_existing_receipt(expense_id: str, _: dict = Depends(auth_dep)):
        """Run OCR on a receipt already attached to an expense."""
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if not exp or not exp.get("receipt_filename"):
            raise HTTPException(404, "Aucun reçu pour cette dépense")
        fp = RECEIPTS_DIR / exp["receipt_filename"]
        if not fp.exists():
            raise HTTPException(404, "Fichier introuvable")
        mime = GEMINI_MIME_BY_EXT.get(fp.suffix.lower(), "image/jpeg")
        return await _ocr_receipt(fp, mime)

    @router.post("/expenses/ocr-scan")
    async def ocr_scan(file: UploadFile = File(...), _: dict = Depends(auth_dep)):
        """Scan a raw image upload (snap-first workflow).

        Saves the file to a temp slot, runs OCR, returns the extracted fields
        plus a `temp_filename` the frontend can pass to /expenses + then call
        /expenses/{id}/receipt/attach-temp to move it permanently.
        """
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_RECEIPT_EXTS:
            raise HTTPException(400, f"Format non supporté. Acceptés : {', '.join(sorted(ALLOWED_RECEIPT_EXTS))}")
        contents = await file.read(MAX_RECEIPT_BYTES + 1)
        if len(contents) > MAX_RECEIPT_BYTES:
            raise HTTPException(413, f"Fichier trop volumineux (max {MAX_RECEIPT_BYTES // 1024 // 1024} MB)")
        # Save to temp slot (will be moved to permanent when attach-temp is called)
        temp_fname = f"_tmp_{uuid.uuid4().hex}{ext}"
        out_path = RECEIPTS_DIR / temp_fname
        out_path.write_bytes(contents)
        mime = GEMINI_MIME_BY_EXT.get(ext, "image/jpeg")
        try:
            extracted = await _ocr_receipt(out_path, mime)
        except Exception as exc:
            # Don't delete the temp file — user might still want to keep it without OCR
            logger.warning("OCR failed: %s", exc)
            extracted = {"confidence": 0, "error": str(exc)}
        return {"temp_filename": temp_fname, **extracted}

    @router.post("/expenses/{expense_id}/receipt/attach-temp")
    async def attach_temp_receipt(
        expense_id: str,
        temp_filename: str = Query(...),
        _: dict = Depends(auth_dep),
    ):
        """Move a temp receipt (from /ocr-scan) onto an existing expense."""
        if not temp_filename.startswith("_tmp_"):
            raise HTTPException(400, "Nom de fichier temporaire invalide")
        temp_path = RECEIPTS_DIR / temp_filename
        if not temp_path.exists():
            raise HTTPException(404, "Fichier temporaire introuvable")
        exp = await db.erp_expenses.find_one({"id": expense_id}, {"_id": 0})
        if not exp:
            raise HTTPException(404, "Dépense introuvable")
        # Remove previous receipt if any
        if exp.get("receipt_filename"):
            old = RECEIPTS_DIR / exp["receipt_filename"]
            if old.exists():
                try:
                    old.unlink()
                except Exception:
                    pass
        ext = temp_path.suffix
        new_name = f"{expense_id}_{uuid.uuid4().hex[:8]}{ext}"
        temp_path.rename(RECEIPTS_DIR / new_name)
        await db.erp_expenses.update_one(
            {"id": expense_id},
            {"$set": {"receipt_filename": new_name, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"receipt_filename": new_name}

    @router.get("/expenses/export.csv")
    async def export_csv(
        month: Optional[str] = None,
        _: dict = Depends(auth_dep),
    ):
        """Export expenses as CSV for accountant. UTF-8 with BOM for Excel."""
        query: dict = {}
        if month and len(month) == 7:
            query["date"] = {"$gte": f"{month}-01", "$lt": f"{month}-32"}
        cur = db.erp_expenses.find(query, {"_id": 0}).sort("date", 1)
        rows = [d async for d in cur]

        buf = io.StringIO()
        buf.write("\ufeff")  # BOM so Excel detects UTF-8
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
        buf.seek(0)
        fn_month = month or "all"
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="depenses-{fn_month}.csv"'},
        )
