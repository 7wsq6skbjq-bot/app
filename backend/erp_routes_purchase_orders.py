"""Purchase-order CRUD + CSV export + PDF download + send-email routes."""
import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_helpers import compute_totals, csv_response, send_pdf_email
from erp_models import EmailSendRequest, Party, PurchaseOrder, PurchaseOrderIn
from erp_pdf import render_purchase_order_pdf


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep, next_number) -> None:
    @router.get("/purchase-orders", response_model=List[PurchaseOrder])
    async def list_pos(_: dict = Depends(auth_dep)):
        cur = db.erp_purchase_orders.find({}, {"_id": 0}).sort("number", -1)
        return [PurchaseOrder(**d) async for d in cur]

    @router.post("/purchase-orders", response_model=PurchaseOrder, status_code=201)
    async def create_po(data: PurchaseOrderIn, _: dict = Depends(auth_dep)):
        number = await next_number("purchase_order")
        subtotal, tps, tvq, total = compute_totals(data.items, data.taxable)
        po = PurchaseOrder(
            number=number,
            supplier_id=data.supplier_id,
            supplier_snapshot=Party(**data.supplier_snapshot.model_dump()),
            date=data.date,
            expected_delivery=data.expected_delivery,
            items=data.items,
            subtotal=subtotal, tps=tps, tvq=tvq, total=total,
            taxable=data.taxable, notes=data.notes, status=data.status,
        )
        await db.erp_purchase_orders.insert_one(po.model_dump())
        return po

    @router.get("/purchase-orders/{po_id}", response_model=PurchaseOrder)
    async def get_po(po_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_purchase_orders.find_one({"id": po_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Bon de commande introuvable")
        return PurchaseOrder(**doc)

    @router.put("/purchase-orders/{po_id}", response_model=PurchaseOrder)
    async def update_po(po_id: str, data: PurchaseOrderIn, _: dict = Depends(auth_dep)):
        existing = await db.erp_purchase_orders.find_one({"id": po_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Bon de commande introuvable")
        subtotal, tps, tvq, total = compute_totals(data.items, data.taxable)
        update_fields = {
            "supplier_id": data.supplier_id,
            "supplier_snapshot": Party(**data.supplier_snapshot.model_dump()).model_dump(),
            "date": data.date,
            "expected_delivery": data.expected_delivery,
            "items": [it.model_dump() for it in data.items],
            "subtotal": subtotal, "tps": tps, "tvq": tvq, "total": total,
            "taxable": data.taxable, "notes": data.notes, "status": data.status,
        }
        await db.erp_purchase_orders.update_one({"id": po_id}, {"$set": update_fields})
        doc = await db.erp_purchase_orders.find_one({"id": po_id}, {"_id": 0})
        return PurchaseOrder(**doc)

    @router.delete("/purchase-orders/{po_id}")
    async def delete_po(po_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_purchase_orders.delete_one({"id": po_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Bon de commande introuvable")
        return {"deleted": po_id}

    @router.get("/exports/purchase-orders.csv")
    async def export_pos(_: dict = Depends(auth_dep)):
        rows_db = await db.erp_purchase_orders.find({}, {"_id": 0}).sort("number", -1).to_list(length=None)
        rows = []
        for i in rows_db:
            ss = i.get("supplier_snapshot") or {}
            rows.append({
                "Numéro": f"BC-{int(i.get('number', 0)):04d}",
                "Date": i.get("date"),
                "Livraison attendue": i.get("expected_delivery") or "",
                "Fournisseur": ss.get("name") or "",
                "Sous-total": f"{i.get('subtotal', 0):.2f}",
                "Total": f"{i.get('total', 0):.2f}",
                "Statut": i.get("status") or "",
            })
        return csv_response(rows, "bons-commande-portech.csv")

    @router.get("/purchase-orders/{po_id}/pdf")
    async def download_po_pdf(po_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_purchase_orders.find_one({"id": po_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Bon de commande introuvable")
        pdf_bytes = await asyncio.to_thread(render_purchase_order_pdf, doc)
        filename = f"BC-{int(doc['number']):04d}.pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.post("/purchase-orders/{po_id}/send-email")
    async def send_po_email(po_id: str, payload: EmailSendRequest, _: dict = Depends(auth_dep)):
        doc = await db.erp_purchase_orders.find_one({"id": po_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Bon de commande introuvable")
        pdf_bytes = await asyncio.to_thread(render_purchase_order_pdf, doc)
        number = f"BC-{int(doc['number']):04d}"
        supplier = (doc.get("supplier_snapshot") or {}).get("name") or ""
        subject = payload.subject or f"Portech — Bon de commande {number}"
        message_html = payload.message or (
            f"<p>Bonjour {supplier},</p>"
            f"<p>Vous trouverez en pièce jointe notre bon de commande <b>{number}</b> "
            f"d'un total de <b>{doc.get('total', 0):.2f} $ CAD</b>.</p>"
            "<p>Merci de bien vouloir confirmer la disponibilité et la date de livraison.</p>"
            "<p>Cordialement,<br/>Portech</p>"
        )
        await send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes, filename=f"{number}.pdf",
        )
        if doc.get("status") == "brouillon":
            await db.erp_purchase_orders.update_one(
                {"id": po_id}, {"$set": {"status": "envoyée"}},
            )
        return {"sent": True, "to": payload.to_email}
