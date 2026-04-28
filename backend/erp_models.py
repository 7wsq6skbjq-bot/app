"""Pydantic models + constants for the Portech ERP."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


TPS_RATE = 0.05       # Taxe sur les produits et services (fédérale)
TVQ_RATE = 0.09975    # Taxe de vente du Québec


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Parties ----------
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


# ---------- Products ----------
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


# ---------- Line items ----------
class LineItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    product_id: Optional[str] = None
    total: Optional[float] = None


class BolItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: str = "unité"
    weight_kg: Optional[float] = None
    dimensions: Optional[str] = None


# ---------- Invoices ----------
class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    customer_id: Optional[str] = None
    customer_snapshot: Party
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
    reminder_level_sent: int = 0  # 0 = none, 7 = J+7 palier sent, 30 = J+30 palier sent
    last_reminder_sent_at: Optional[str] = None
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


# ---------- Purchase Orders ----------
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


# ---------- Bills of Lading ----------
class BillOfLading(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    shipper_snapshot: Party
    consignee_snapshot: Party
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


# ---------- Email ----------
class EmailSendRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    to_email: EmailStr
    subject: Optional[str] = None
    message: Optional[str] = None
