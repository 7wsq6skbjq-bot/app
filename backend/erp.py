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
import uuid
from datetime import date as date_cls, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ReturnDocument


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

    return router
