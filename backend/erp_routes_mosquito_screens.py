"""Mosquito screens (Moustiquaires) — fabrication orders CRUD + PDF + email.

Fabrication tab helper : lets Cédrick capture a list of mosquito screens
with dimensions, quantities, frame color, mesh type and attachment type —
either to fabricate in-house or to send to an external supplier as a
branded "Bon de fabrication moustiquaires" PDF.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date as DateT, datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from erp_helpers import csv_response, send_pdf_email
from erp_models import Party
from erp_pdf import render_mosquito_screens_pdf


ScreenStatus = Literal["brouillon", "envoyé", "en fabrication", "reçu",
                        "fabriqué", "annulé"]

FRAME_COLORS = [
    "Blanc", "Noir", "Bronze", "Brun commercial", "Naturel (anodisé)",
    "Sur mesure",
]
MESH_TYPES = [
    "Fibre de verre standard",
    "Anti-pollen (No-see-um)",
    "Anti-chat renforcée",
    "Solaire (Solar Screen)",
    "Aluminium",
    "Sur mesure",
]
ATTACHMENT_TYPES = [
    "Accroches (clips)",
    "Rails coulissants",
    "À visser",
    "Magnétique",
    "Sur cadre existant",
    "Sur mesure",
]


class MosquitoScreenItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)   # ex : "M-01 · Cuisine"
    width_mm: float = Field(..., ge=0)
    height_mm: float = Field(..., ge=0)
    qty: int = Field(1, ge=1)
    frame_color: str = "Blanc"
    mesh_type: str = "Fibre de verre standard"
    attachment_type: str = "Accroches (clips)"
    notes: Optional[str] = ""


class MosquitoScreenIn(BaseModel):
    """Payload posted from the UI to create / update a fabrication order."""
    mode: Literal["interne", "fournisseur"] = "interne"
    supplier_id: Optional[str] = None
    supplier_snapshot: Optional[Party] = None
    customer_name: Optional[str] = ""       # end client (optional)
    project_ref: Optional[str] = ""
    project_address: Optional[str] = ""
    date: DateT = Field(default_factory=DateT.today)
    needed_by: Optional[DateT] = None
    status: ScreenStatus = "brouillon"
    items: List[MosquitoScreenItem] = Field(default_factory=list)
    notes: Optional[str] = ""


class MosquitoScreenOrder(MosquitoScreenIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str = ""                                  # MS-2026-001
    total_qty: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    sent_to: Optional[str] = None


class MosquitoScreenEmailRequest(BaseModel):
    to_email: EmailStr
    subject: Optional[str] = None
    message: Optional[str] = None


def _format_number(year: int, seq: int) -> str:
    return f"MS-{year}-{seq:03d}"


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    async def _next_order_number() -> str:
        now = datetime.now(timezone.utc)
        year = now.year
        counter = await db.erp_counters.find_one_and_update(
            {"key": f"mosquito_screen_{year}"},
            {"$inc": {"seq": 1}},
            upsert=True, return_document=True,
        )
        return _format_number(year, counter.get("seq") or 1)

    def _compute_total_qty(items: List[MosquitoScreenItem]) -> int:
        return int(sum(int(i.qty) for i in items))

    # ─── Routes ────────────────────────────────────────────────
    @router.get("/mosquito-screens", response_model=List[MosquitoScreenOrder])
    async def list_orders(_: dict = Depends(auth_dep)):
        cur = db.erp_mosquito_screens.find({}, {"_id": 0}).sort("created_at", -1)
        return [MosquitoScreenOrder(**d) async for d in cur]

    @router.post("/mosquito-screens", response_model=MosquitoScreenOrder,
                 status_code=201)
    async def create_order(data: MosquitoScreenIn, _: dict = Depends(auth_dep)):
        order = MosquitoScreenOrder(
            **data.model_dump(),
            order_number=await _next_order_number(),
            total_qty=_compute_total_qty(data.items),
        )
        await db.erp_mosquito_screens.insert_one(order.model_dump(mode="json"))
        return order

    @router.get("/mosquito-screens/{order_id}",
                response_model=MosquitoScreenOrder)
    async def get_order(order_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_mosquito_screens.find_one({"id": order_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Bon de fabrication introuvable")
        return MosquitoScreenOrder(**doc)

    @router.put("/mosquito-screens/{order_id}",
                response_model=MosquitoScreenOrder)
    async def update_order(order_id: str, data: MosquitoScreenIn,
                            _: dict = Depends(auth_dep)):
        existing = await db.erp_mosquito_screens.find_one({"id": order_id},
                                                          {"_id": 0})
        if not existing:
            raise HTTPException(404, "Bon de fabrication introuvable")
        update_fields = data.model_dump(mode="json")
        update_fields["total_qty"] = _compute_total_qty(data.items)
        await db.erp_mosquito_screens.update_one(
            {"id": order_id}, {"$set": update_fields},
        )
        doc = await db.erp_mosquito_screens.find_one({"id": order_id},
                                                     {"_id": 0})
        return MosquitoScreenOrder(**doc)

    @router.delete("/mosquito-screens/{order_id}", status_code=204)
    async def delete_order(order_id: str, _: dict = Depends(auth_dep)):
        res = await db.erp_mosquito_screens.delete_one({"id": order_id})
        if not res.deleted_count:
            raise HTTPException(404, "Bon de fabrication introuvable")
        return Response(status_code=204)

    @router.get("/mosquito-screens.csv")
    async def export_orders_csv(_: dict = Depends(auth_dep)):
        rows = []
        async for o in db.erp_mosquito_screens.find({}, {"_id": 0}).sort("created_at", -1):
            ss = o.get("supplier_snapshot") or {}
            rows.append({
                "Numéro":       o.get("order_number") or "",
                "Date":         o.get("date") or "",
                "Requis pour":  o.get("needed_by") or "",
                "Mode":         o.get("mode") or "",
                "Fournisseur":  ss.get("name") or "",
                "Client final": o.get("customer_name") or "",
                "Projet":       o.get("project_ref") or "",
                "Statut":       o.get("status") or "",
                "Qté totale":   o.get("total_qty") or 0,
                "Envoyé à":     o.get("sent_to") or "",
            })
        return csv_response(rows, "moustiquaires-portech.csv")

    @router.get("/mosquito-screens/{order_id}/pdf")
    async def download_order_pdf(order_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_mosquito_screens.find_one({"id": order_id},
                                                     {"_id": 0})
        if not doc:
            raise HTTPException(404, "Bon de fabrication introuvable")
        pdf_bytes = await asyncio.to_thread(render_mosquito_screens_pdf, doc)
        filename = f"{doc.get('order_number') or 'MS'}.pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.post("/mosquito-screens/{order_id}/send-email")
    async def send_order_email(order_id: str,
                                payload: MosquitoScreenEmailRequest,
                                _: dict = Depends(auth_dep)):
        doc = await db.erp_mosquito_screens.find_one({"id": order_id},
                                                     {"_id": 0})
        if not doc:
            raise HTTPException(404, "Bon de fabrication introuvable")

        pdf_bytes = await asyncio.to_thread(render_mosquito_screens_pdf, doc)
        number = doc.get("order_number") or "MS"
        supplier = (doc.get("supplier_snapshot") or {}).get("name") or ""
        total_qty = int(doc.get("total_qty") or 0)
        needed_by = doc.get("needed_by") or ""

        subject = payload.subject or (
            f"Portech — Bon de fabrication moustiquaires {number}"
        )
        message_html = payload.message or (
            f"<p>Bonjour {supplier or ''},</p>"
            f"<p>Vous trouverez en pièce jointe notre <b>bon de fabrication "
            f"moustiquaires {number}</b> — <b>{total_qty}</b> unité(s) au total.</p>"
            + (f"<p><b>Requis pour le :</b> {needed_by}</p>" if needed_by else "")
            + "<p>Les dimensions, la teinte de cadre, le type de toile et le "
            "type d'attache sont détaillés pour chaque unité dans le tableau. "
            "Confirmez-nous les délais et le prix par retour de courriel — "
            "merci !</p>"
        )

        await send_pdf_email(
            to_email=payload.to_email,
            subject=subject,
            html=message_html,
            pdf_bytes=pdf_bytes,
            filename=f"{number}.pdf",
            footer_note=f"Bon de fabrication moustiquaires {number} · Portech ERP",
        )

        await db.erp_mosquito_screens.update_one(
            {"id": order_id},
            {"$set": {
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_to": payload.to_email,
                "status": "envoyé",
            }},
        )
        return {"sent": True, "to": payload.to_email}
