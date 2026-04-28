"""
Portech internal ERP:
- Customers (clients)
- Suppliers (fournisseurs, shared model with customers in practice)
- Products (produits/services)
- Invoices (factures)
- Purchase orders (bons de commande)
- Bills of lading (connaissements)

All routes are mounted under /api/admin/ and require admin auth (injected from server.py).
"""
import asyncio
import base64
import csv
import io
import logging
import os
import uuid
from datetime import date as date_cls, datetime, timedelta, timezone
from typing import List, Optional

import resend
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pymongo import ReturnDocument

from erp_pdf import render_bol_pdf, render_invoice_pdf, render_purchase_order_pdf

logger = logging.getLogger("portech.erp")


TPS_RATE = 0.05       # Taxe sur les produits et services (fédérale)
TVQ_RATE = 0.09975    # Taxe de vente du Québec


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ==============================================================
# Shared Pydantic models
# ==============================================================
class Party(BaseModel):
    """Customer or supplier — shared fields."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: str = Field(default="customer", pattern="^(customer|supplier)$")
    name: str = Field(min_length=1, max_length=200)
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = "QC"
    postal_code: Optional[str] = None
    country: Optional[str] = "Canada"
    tax_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


class PartyIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: str = Field(default="customer", pattern="^(customer|supplier)$")
    name: str = Field(min_length=1, max_length=200)
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = "QC"
    postal_code: Optional[str] = None
    country: Optional[str] = "Canada"
    tax_number: Optional[str] = None
    notes: Optional[str] = None


class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sku: Optional[str] = None
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    unit: str = "unité"
    unit_price: float = Field(ge=0)
    category: Optional[str] = None
    is_service: bool = False
    created_at: str = Field(default_factory=now_iso)


class ProductIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sku: Optional[str] = None
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    unit: str = "unité"
    unit_price: float = Field(ge=0)
    category: Optional[str] = None
    is_service: bool = False


class LineItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    product_id: Optional[str] = None  # optional ref
    total: Optional[float] = None     # computed


def _compute_totals(items: List[LineItem], taxable: bool = True):
    for it in items:
        it.total = round(it.quantity * it.unit_price, 2)
    subtotal = round(sum((it.total or 0) for it in items), 2)
    if taxable:
        tps = round(subtotal * TPS_RATE, 2)
        tvq = round(subtotal * TVQ_RATE, 2)
    else:
        tps = 0.0
        tvq = 0.0
    total = round(subtotal + tps + tvq, 2)
    return subtotal, tps, tvq, total


# ==============================================================
# Document models — Invoice / PO / BOL
# ==============================================================
class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int  # sequential
    customer_id: Optional[str] = None
    customer_snapshot: Party  # frozen party info at time of creation
    date: str
    due_date: Optional[str] = None
    items: List[LineItem]
    subtotal: float
    tps: float
    tvq: float
    total: float
    taxable: bool = True
    notes: Optional[str] = None
    status: str = Field(default="brouillon", pattern="^(brouillon|envoyée|payée|annulée)$")
    created_at: str = Field(default_factory=now_iso)


class InvoiceIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_id: Optional[str] = None
    customer_snapshot: PartyIn
    date: str
    due_date: Optional[str] = None
    items: List[LineItem] = Field(min_length=1)
    taxable: bool = True
    notes: Optional[str] = None
    status: str = Field(default="brouillon", pattern="^(brouillon|envoyée|payée|annulée)$")


class PurchaseOrder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    supplier_id: Optional[str] = None
    supplier_snapshot: Party
    date: str
    expected_delivery: Optional[str] = None
    items: List[LineItem]
    subtotal: float
    tps: float
    tvq: float
    total: float
    taxable: bool = True
    notes: Optional[str] = None
    status: str = Field(default="brouillon", pattern="^(brouillon|envoyée|reçue|annulée)$")
    created_at: str = Field(default_factory=now_iso)


class PurchaseOrderIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    supplier_id: Optional[str] = None
    supplier_snapshot: PartyIn
    date: str
    expected_delivery: Optional[str] = None
    items: List[LineItem] = Field(min_length=1)
    taxable: bool = True
    notes: Optional[str] = None
    status: str = Field(default="brouillon", pattern="^(brouillon|envoyée|reçue|annulée)$")


class BolItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: str = "unité"
    weight_kg: Optional[float] = None
    dimensions: Optional[str] = None  # free text e.g. "40×30×20 cm"


class BillOfLading(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    shipper_snapshot: Party  # expéditeur
    consignee_snapshot: Party  # destinataire
    carrier: Optional[str] = None
    date: str
    expected_delivery: Optional[str] = None
    items: List[BolItem]
    total_weight_kg: Optional[float] = None
    special_instructions: Optional[str] = None
    status: str = Field(default="brouillon", pattern="^(brouillon|expédié|livré|annulé)$")
    created_at: str = Field(default_factory=now_iso)


class BillOfLadingIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shipper_snapshot: PartyIn
    consignee_snapshot: PartyIn
    carrier: Optional[str] = None
    date: str
    expected_delivery: Optional[str] = None
    items: List[BolItem] = Field(min_length=1)
    total_weight_kg: Optional[float] = None
    special_instructions: Optional[str] = None
    status: str = Field(default="brouillon", pattern="^(brouillon|expédié|livré|annulé)$")


# ==============================================================
# Router factory
# ==============================================================
def build_erp_router(db: AsyncIOMotorDatabase, auth_dep) -> APIRouter:
    """Return an APIRouter with all ERP endpoints; auth_dep is the FastAPI dependency
    that protects admin routes (injected from server.py)."""
    router = APIRouter(prefix="/admin", tags=["erp"])

    # ----------- Counters (sequential numbering) -----------
    async def next_number(counter_type: str) -> int:
        doc = await db.counters.find_one_and_update(
            {"type": counter_type},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(doc["value"])

    # ============== Parties (customers + suppliers) ==============
    @router.get("/parties", response_model=List[Party])
    async def list_parties(kind: Optional[str] = None, _: dict = Depends(auth_dep)):
        query = {}
        if kind:
            query["kind"] = kind
        cur = db.erp_parties.find(query, {"_id": 0}).sort("name", 1)
        return [Party(**d) async for d in cur]

    @router.post("/parties", response_model=Party, status_code=201)
    async def create_party(data: PartyIn, _: dict = Depends(auth_dep)):
        party = Party(**data.model_dump())
        await db.erp_parties.insert_one(party.model_dump())
        return party

    @router.get("/parties/{party_id}", response_model=Party)
    async def get_party(party_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_parties.find_one({"id": party_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Tier introuvable")
        return Party(**doc)

    @router.put("/parties/{party_id}", response_model=Party)
    async def update_party(party_id: str, data: PartyIn, _: dict = Depends(auth_dep)):
        result = await db.erp_parties.update_one(
            {"id": party_id},
            {"$set": data.model_dump()},
        )
        if result.matched_count == 0:
            raise HTTPException(404, "Tier introuvable")
        doc = await db.erp_parties.find_one({"id": party_id}, {"_id": 0})
        return Party(**doc)

    @router.delete("/parties/{party_id}")
    async def delete_party(party_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_parties.delete_one({"id": party_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Tier introuvable")
        return {"deleted": party_id}

    # ============== Products ==============
    @router.get("/products", response_model=List[Product])
    async def list_products(_: dict = Depends(auth_dep)):
        cur = db.erp_products.find({}, {"_id": 0}).sort("name", 1)
        return [Product(**d) async for d in cur]

    @router.post("/products", response_model=Product, status_code=201)
    async def create_product(data: ProductIn, _: dict = Depends(auth_dep)):
        p = Product(**data.model_dump())
        await db.erp_products.insert_one(p.model_dump())
        return p

    @router.put("/products/{product_id}", response_model=Product)
    async def update_product(product_id: str, data: ProductIn, _: dict = Depends(auth_dep)):
        result = await db.erp_products.update_one(
            {"id": product_id}, {"$set": data.model_dump()}
        )
        if result.matched_count == 0:
            raise HTTPException(404, "Produit introuvable")
        doc = await db.erp_products.find_one({"id": product_id}, {"_id": 0})
        return Product(**doc)

    @router.delete("/products/{product_id}")
    async def delete_product(product_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_products.delete_one({"id": product_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Produit introuvable")
        return {"deleted": product_id}

    # ============== Invoices ==============
    @router.get("/invoices", response_model=List[Invoice])
    async def list_invoices(_: dict = Depends(auth_dep)):
        cur = db.erp_invoices.find({}, {"_id": 0}).sort("number", -1)
        return [Invoice(**d) async for d in cur]

    @router.post("/invoices", response_model=Invoice, status_code=201)
    async def create_invoice(data: InvoiceIn, _: dict = Depends(auth_dep)):
        number = await next_number("invoice")
        subtotal, tps, tvq, total = _compute_totals(data.items, data.taxable)
        inv = Invoice(
            number=number,
            customer_id=data.customer_id,
            customer_snapshot=Party(**data.customer_snapshot.model_dump()),
            date=data.date,
            due_date=data.due_date,
            items=data.items,
            subtotal=subtotal,
            tps=tps,
            tvq=tvq,
            total=total,
            taxable=data.taxable,
            notes=data.notes,
            status=data.status,
        )
        await db.erp_invoices.insert_one(inv.model_dump())
        return inv

    @router.get("/invoices/{invoice_id}", response_model=Invoice)
    async def get_invoice(invoice_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        return Invoice(**doc)

    @router.put("/invoices/{invoice_id}", response_model=Invoice)
    async def update_invoice(invoice_id: str, data: InvoiceIn, _: dict = Depends(auth_dep)):
        existing = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Facture introuvable")
        subtotal, tps, tvq, total = _compute_totals(data.items, data.taxable)
        update_fields = {
            "customer_id": data.customer_id,
            "customer_snapshot": Party(**data.customer_snapshot.model_dump()).model_dump(),
            "date": data.date,
            "due_date": data.due_date,
            "items": [it.model_dump() for it in data.items],
            "subtotal": subtotal,
            "tps": tps,
            "tvq": tvq,
            "total": total,
            "taxable": data.taxable,
            "notes": data.notes,
            "status": data.status,
        }
        await db.erp_invoices.update_one({"id": invoice_id}, {"$set": update_fields})
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        return Invoice(**doc)

    @router.delete("/invoices/{invoice_id}")
    async def delete_invoice(invoice_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_invoices.delete_one({"id": invoice_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Facture introuvable")
        return {"deleted": invoice_id}

    # ============== Purchase Orders ==============
    @router.get("/purchase-orders", response_model=List[PurchaseOrder])
    async def list_pos(_: dict = Depends(auth_dep)):
        cur = db.erp_purchase_orders.find({}, {"_id": 0}).sort("number", -1)
        return [PurchaseOrder(**d) async for d in cur]

    @router.post("/purchase-orders", response_model=PurchaseOrder, status_code=201)
    async def create_po(data: PurchaseOrderIn, _: dict = Depends(auth_dep)):
        number = await next_number("purchase_order")
        subtotal, tps, tvq, total = _compute_totals(data.items, data.taxable)
        po = PurchaseOrder(
            number=number,
            supplier_id=data.supplier_id,
            supplier_snapshot=Party(**data.supplier_snapshot.model_dump()),
            date=data.date,
            expected_delivery=data.expected_delivery,
            items=data.items,
            subtotal=subtotal,
            tps=tps,
            tvq=tvq,
            total=total,
            taxable=data.taxable,
            notes=data.notes,
            status=data.status,
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
        subtotal, tps, tvq, total = _compute_totals(data.items, data.taxable)
        update_fields = {
            "supplier_id": data.supplier_id,
            "supplier_snapshot": Party(**data.supplier_snapshot.model_dump()).model_dump(),
            "date": data.date,
            "expected_delivery": data.expected_delivery,
            "items": [it.model_dump() for it in data.items],
            "subtotal": subtotal,
            "tps": tps,
            "tvq": tvq,
            "total": total,
            "taxable": data.taxable,
            "notes": data.notes,
            "status": data.status,
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

    # ============== Bills of Lading ==============
    @router.get("/bills-of-lading", response_model=List[BillOfLading])
    async def list_bols(_: dict = Depends(auth_dep)):
        cur = db.erp_bills_of_lading.find({}, {"_id": 0}).sort("number", -1)
        return [BillOfLading(**d) async for d in cur]

    @router.post("/bills-of-lading", response_model=BillOfLading, status_code=201)
    async def create_bol(data: BillOfLadingIn, _: dict = Depends(auth_dep)):
        number = await next_number("bill_of_lading")
        bol = BillOfLading(
            number=number,
            shipper_snapshot=Party(**data.shipper_snapshot.model_dump()),
            consignee_snapshot=Party(**data.consignee_snapshot.model_dump()),
            carrier=data.carrier,
            date=data.date,
            expected_delivery=data.expected_delivery,
            items=data.items,
            total_weight_kg=data.total_weight_kg,
            special_instructions=data.special_instructions,
            status=data.status,
        )
        await db.erp_bills_of_lading.insert_one(bol.model_dump())
        return bol

    @router.get("/bills-of-lading/{bol_id}", response_model=BillOfLading)
    async def get_bol(bol_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Connaissement introuvable")
        return BillOfLading(**doc)

    @router.put("/bills-of-lading/{bol_id}", response_model=BillOfLading)
    async def update_bol(bol_id: str, data: BillOfLadingIn, _: dict = Depends(auth_dep)):
        existing = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Connaissement introuvable")
        update_fields = {
            "shipper_snapshot": Party(**data.shipper_snapshot.model_dump()).model_dump(),
            "consignee_snapshot": Party(**data.consignee_snapshot.model_dump()).model_dump(),
            "carrier": data.carrier,
            "date": data.date,
            "expected_delivery": data.expected_delivery,
            "items": [it.model_dump() for it in data.items],
            "total_weight_kg": data.total_weight_kg,
            "special_instructions": data.special_instructions,
            "status": data.status,
        }
        await db.erp_bills_of_lading.update_one({"id": bol_id}, {"$set": update_fields})
        doc = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        return BillOfLading(**doc)

    @router.delete("/bills-of-lading/{bol_id}")
    async def delete_bol(bol_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_bills_of_lading.delete_one({"id": bol_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Connaissement introuvable")
        return {"deleted": bol_id}

    # ============== Dashboard & analytics ==============
    @router.get("/dashboard")
    async def erp_dashboard(_: dict = Depends(auth_dep)):
        # Aggregate basic financial metrics from invoices.
        invoices = await db.erp_invoices.find({}, {"_id": 0}).to_list(length=None)

        now = datetime.now(timezone.utc)
        first_day_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def _parse_date(d):
            try:
                return datetime.strptime(str(d)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                return None

        total_invoiced = sum(float(i.get("total", 0)) for i in invoices)
        invoices_count = len(invoices)
        total_paid = sum(float(i.get("total", 0)) for i in invoices if i.get("status") == "payée")
        total_outstanding = sum(
            float(i.get("total", 0))
            for i in invoices
            if i.get("status") in ("envoyée", "brouillon")
        )

        revenue_this_month = 0.0
        for i in invoices:
            d = _parse_date(i.get("date"))
            if d and d >= first_day_month and i.get("status") == "payée":
                revenue_this_month += float(i.get("total", 0))

        # 6-month revenue trend (paid only)
        months = []
        for offset in range(5, -1, -1):
            month_start = (first_day_month - timedelta(days=offset * 30)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            total = 0.0
            for i in invoices:
                d = _parse_date(i.get("date"))
                if d and month_start <= d < month_end and i.get("status") == "payée":
                    total += float(i.get("total", 0))
            months.append({
                "month": month_start.strftime("%Y-%m"),
                "label": month_start.strftime("%b %Y"),
                "total": round(total, 2),
            })

        # Top customers by invoiced total
        top = {}
        for i in invoices:
            cust = (i.get("customer_snapshot") or {}).get("name") or "—"
            top[cust] = top.get(cust, 0.0) + float(i.get("total", 0))
        top_customers = sorted(
            [{"name": k, "total": round(v, 2)} for k, v in top.items()],
            key=lambda x: -x["total"],
        )[:5]

        # Outstanding invoices list (top 5 unpaid)
        outstanding_list = [
            {
                "id": i.get("id"),
                "number": i.get("number"),
                "customer": (i.get("customer_snapshot") or {}).get("name"),
                "date": i.get("date"),
                "due_date": i.get("due_date"),
                "total": i.get("total"),
                "status": i.get("status"),
            }
            for i in invoices
            if i.get("status") in ("envoyée", "brouillon")
        ]
        outstanding_list.sort(key=lambda x: x.get("date") or "", reverse=True)

        # Counts
        parties_count = await db.erp_parties.count_documents({"kind": "customer"})
        suppliers_count = await db.erp_parties.count_documents({"kind": "supplier"})
        products_count = await db.erp_products.count_documents({})
        po_count = await db.erp_purchase_orders.count_documents({})
        bol_count = await db.erp_bills_of_lading.count_documents({})

        return {
            "kpi": {
                "invoiced_total": round(total_invoiced, 2),
                "paid_total": round(total_paid, 2),
                "outstanding_total": round(total_outstanding, 2),
                "revenue_this_month": round(revenue_this_month, 2),
                "invoices_count": invoices_count,
                "customers_count": parties_count,
                "suppliers_count": suppliers_count,
                "products_count": products_count,
                "po_count": po_count,
                "bol_count": bol_count,
            },
            "monthly_revenue": months,
            "top_customers": top_customers,
            "outstanding_invoices": outstanding_list[:8],
        }

    # ============== CSV export ==============
    def _csv_response(rows: list[dict], filename: str) -> StreamingResponse:
        buf = io.StringIO()
        if not rows:
            return StreamingResponse(
                iter([""]), media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @router.get("/exports/invoices.csv")
    async def export_invoices(_: dict = Depends(auth_dep)):
        invoices = await db.erp_invoices.find({}, {"_id": 0}).sort("number", -1).to_list(length=None)
        rows = []
        for i in invoices:
            cs = i.get("customer_snapshot") or {}
            rows.append({
                "Numéro": f"FAC-{int(i.get('number', 0)):04d}",
                "Date": i.get("date"),
                "Échéance": i.get("due_date") or "",
                "Client": cs.get("name") or "",
                "Ville": cs.get("city") or "",
                "Courriel": cs.get("email") or "",
                "Sous-total": f"{i.get('subtotal', 0):.2f}",
                "TPS": f"{i.get('tps', 0):.2f}",
                "TVQ": f"{i.get('tvq', 0):.2f}",
                "Total": f"{i.get('total', 0):.2f}",
                "Statut": i.get("status") or "",
                "Notes": (i.get("notes") or "").replace("\n", " "),
            })
        return _csv_response(rows, "factures-portech.csv")

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
        return _csv_response(rows, "bons-commande-portech.csv")

    @router.get("/exports/bills-of-lading.csv")
    async def export_bols(_: dict = Depends(auth_dep)):
        rows_db = await db.erp_bills_of_lading.find({}, {"_id": 0}).sort("number", -1).to_list(length=None)
        rows = []
        for b in rows_db:
            sh = b.get("shipper_snapshot") or {}
            cn = b.get("consignee_snapshot") or {}
            rows.append({
                "Numéro": f"CONN-{int(b.get('number', 0)):04d}",
                "Date": b.get("date"),
                "Livraison attendue": b.get("expected_delivery") or "",
                "Expéditeur": sh.get("name") or "",
                "Destinataire": cn.get("name") or "",
                "Transporteur": b.get("carrier") or "",
                "Poids total (kg)": b.get("total_weight_kg") or "",
                "Statut": b.get("status") or "",
            })
        return _csv_response(rows, "connaissements-portech.csv")

    # ============== PDF download (server-side) ==============
    @router.get("/invoices/{invoice_id}/pdf")
    async def download_invoice_pdf(invoice_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        pdf_bytes = await asyncio.to_thread(render_invoice_pdf, doc)
        filename = f"FAC-{int(doc['number']):04d}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

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

    @router.get("/bills-of-lading/{bol_id}/pdf")
    async def download_bol_pdf(bol_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Connaissement introuvable")
        pdf_bytes = await asyncio.to_thread(render_bol_pdf, doc)
        filename = f"CONN-{int(doc['number']):04d}.pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # ============== Send-by-email endpoints ==============
    class EmailSendRequest(BaseModel):
        model_config = ConfigDict(extra="ignore")
        to_email: EmailStr
        subject: Optional[str] = None
        message: Optional[str] = None

    sender_email = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

    async def _send_pdf_email(*, to_email: str, subject: str, html: str, pdf_bytes: bytes, filename: str) -> None:
        if not resend.api_key:
            raise HTTPException(503, "Service courriel non configuré (RESEND_API_KEY manquante)")
        params = {
            "from": f"Portech <{sender_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html,
            "attachments": [{
                "filename": filename,
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }],
        }
        try:
            result = await asyncio.to_thread(resend.Emails.send, params)
            logger.info("ERP email sent id=%s to=%s", result.get("id"), to_email)
        except Exception as exc:
            logger.error("ERP email failed: %s", exc)
            raise HTTPException(502, f"Échec de l'envoi : {exc}")

    @router.post("/invoices/{invoice_id}/send-email")
    async def send_invoice_email(invoice_id: str, payload: EmailSendRequest, _: dict = Depends(auth_dep)):
        doc = await db.erp_invoices.find_one({"id": invoice_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Facture introuvable")
        pdf_bytes = await asyncio.to_thread(render_invoice_pdf, doc)
        number = f"FAC-{int(doc['number']):04d}"
        filename = f"{number}.pdf"
        cust = (doc.get("customer_snapshot") or {}).get("name") or ""
        subject = payload.subject or f"Portech — Facture {number}"
        message_html = payload.message or (
            f"<p>Bonjour {cust},</p>"
            f"<p>Vous trouverez en pièce jointe votre facture <b>{number}</b> "
            f"d'un total de <b>{doc.get('total', 0):.2f} $ CAD</b>.</p>"
            "<p>Modalités : paiement net 30 jours.<br/>"
            "Pour toute question, répondez simplement à ce courriel.</p>"
            "<p>Cordialement,<br/>Portech</p>"
        )
        await _send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes, filename=filename,
        )
        # Mark as "envoyée" if currently brouillon
        if doc.get("status") == "brouillon":
            await db.erp_invoices.update_one(
                {"id": invoice_id}, {"$set": {"status": "envoyée"}},
            )
        return {"sent": True, "to": payload.to_email}

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
        await _send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes, filename=f"{number}.pdf",
        )
        if doc.get("status") == "brouillon":
            await db.erp_purchase_orders.update_one(
                {"id": po_id}, {"$set": {"status": "envoyée"}},
            )
        return {"sent": True, "to": payload.to_email}

    @router.post("/bills-of-lading/{bol_id}/send-email")
    async def send_bol_email(bol_id: str, payload: EmailSendRequest, _: dict = Depends(auth_dep)):
        doc = await db.erp_bills_of_lading.find_one({"id": bol_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Connaissement introuvable")
        pdf_bytes = await asyncio.to_thread(render_bol_pdf, doc)
        number = f"CONN-{int(doc['number']):04d}"
        consignee = (doc.get("consignee_snapshot") or {}).get("name") or ""
        subject = payload.subject or f"Portech — Connaissement {number}"
        message_html = payload.message or (
            f"<p>Bonjour {consignee},</p>"
            f"<p>Vous trouverez en pièce jointe le connaissement <b>{number}</b> "
            "couvrant l'expédition à venir.</p>"
            "<p>Cordialement,<br/>Portech</p>"
        )
        await _send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes, filename=f"{number}.pdf",
        )
        if doc.get("status") == "brouillon":
            await db.erp_bills_of_lading.update_one(
                {"id": bol_id}, {"$set": {"status": "expédié"}},
            )
        return {"sent": True, "to": payload.to_email}

    return router
