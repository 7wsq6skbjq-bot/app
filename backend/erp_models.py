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
    unit_price: float = Field(ge=0)                     # sell price (public)
    cost_price: Optional[float] = Field(default=None, ge=0)   # CONFIDENTIAL — never on quotes/invoices
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
    cost_price: Optional[float] = Field(default=None, ge=0)
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
    cost_price: Optional[float] = Field(default=None, ge=0)   # CONFIDENTIEL — jamais sur le PDF
    cost_category: Optional[str] = None                        # CONFIDENTIEL — regroupement marge


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
    deposit_received: bool = False
    deposit_pct: float = 0.0
    deposit_amount: float = 0.0
    balance_due: Optional[float] = None
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
    deposit_received: bool = False
    deposit_pct: float = 0.0



# ---------- Quotes (Soumissions) ----------
QUOTE_STATUS_PATTERN = "^(brouillon|envoyée|acceptée|refusée|expirée|annulée)$"


class Quote(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    customer_id: Optional[str] = None
    customer_snapshot: Party
    date: str
    valid_until: Optional[str] = None
    items: List[LineItem]
    subtotal: float
    tps: float
    tvq: float
    total: float
    taxable: bool = True
    notes: Optional[str] = None
    status: str = Field(default="brouillon", pattern=QUOTE_STATUS_PATTERN)
    converted_invoice_id: Optional[str] = None       # set when converted → facture
    drawing_pages: Optional[List[int]] = None         # Adams Rite Parts Manual pages
    include_sales_conditions: bool = False            # joindre l'annexe conditions de vente
    show_deposit: bool = False                        # afficher le dépôt à verser sur le PDF
    deposit_pct: float = 50.0                         # pourcentage du dépôt affiché
    attachments: Optional[List[dict]] = None          # fichiers annexés (GridFS): [{id,filename,content_type}]
    created_at: str = Field(default_factory=now_iso)


class QuoteIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_id: Optional[str] = None
    customer_snapshot: PartyIn
    date: str
    valid_until: Optional[str] = None
    items: List[LineItem] = Field(min_length=1)
    taxable: bool = True
    notes: Optional[str] = None
    status: str = Field(default="brouillon", pattern=QUOTE_STATUS_PATTERN)
    drawing_pages: Optional[List[int]] = None         # Adams Rite Parts Manual pages
    include_sales_conditions: bool = False
    show_deposit: bool = False
    deposit_pct: float = 50.0



# ---------- Expert reports (Rapports d'expertise) ----------
class ReportPhoto(BaseModel):
    """Photo attached to a report door — metadata only (file lives on disk)."""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    caption: Optional[str] = ""
    door_index: Optional[int] = None  # which door this photo belongs to (0-based)
    order: int = 0                     # display order within the door


class InspectedDoor(BaseModel):
    """One door being inspected in an expert report."""
    model_config = ConfigDict(extra="ignore")
    tag: str = Field(default="", max_length=80)                # e.g. "P-100" / "Entrée principale"
    location: Optional[str] = ""                                # "Rez-de-chaussée, façade Peel"
    series: Optional[str] = ""                                  # AT1000 / ATi2000 / Kawneer 190 / etc.
    model: Optional[str] = ""                                   # Free text (e.g. "Aluminium blanc")
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    finish: Optional[str] = ""
    configuration: Optional[str] = ""                           # Simple / double / porte-fenêtre
    hinges: Optional[str] = ""
    lock: Optional[str] = ""
    electric_strike: Optional[str] = ""
    threshold: Optional[str] = ""
    trim: Optional[str] = ""
    other_specs: Optional[str] = ""                             # Free notes on this door
    # Deficiency block
    observations: List[str] = Field(default_factory=list)       # bullets
    impacts: List[str] = Field(default_factory=list)            # bullets
    recommendation: Optional[str] = ""


class ExpertReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    # Client (recipient of the report)
    client_snapshot: Party
    # Project details
    project_name: str = Field(default="", max_length=200)
    project_address: Optional[str] = ""
    project_city: Optional[str] = ""
    inspection_date: str                                        # YYYY-MM-DD
    inspector_name: str = "Cédrick Pimparé"
    inspector_title: str = "Expert Portes Commerciales – Portech"
    mandated_by: Optional[str] = ""                             # "Marc Tremblay – VERRE SELECT"
    # Report body
    purpose: Optional[str] = ""                                  # Section 1 — free text
    doors: List[InspectedDoor] = Field(default_factory=list)     # Sections 2 & 3
    risks: Optional[str] = ""                                     # Section 4
    conclusion: Optional[str] = ""                                # Section 5
    photos: List[ReportPhoto] = Field(default_factory=list)
    # Metadata
    status: str = Field(default="brouillon",
                         pattern="^(brouillon|finalisé|envoyé|archivé)$")
    sent_at: Optional[str] = None
    sent_to: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


class ExpertReportIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    client_snapshot: PartyIn
    project_name: str = ""
    project_address: Optional[str] = ""
    project_city: Optional[str] = ""
    inspection_date: str
    inspector_name: Optional[str] = "Cédrick Pimparé"
    inspector_title: Optional[str] = "Expert Portes Commerciales – Portech"
    mandated_by: Optional[str] = ""
    purpose: Optional[str] = ""
    doors: List[InspectedDoor] = Field(default_factory=list)
    risks: Optional[str] = ""
    conclusion: Optional[str] = ""
    status: str = Field(default="brouillon",
                         pattern="^(brouillon|finalisé|envoyé|archivé)$")


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


# ---------- Appointments (calendrier admin interne) ----------
class Appointment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(min_length=1, max_length=200)
    start: str  # ISO datetime "YYYY-MM-DDTHH:MM"
    end: Optional[str] = None
    party_id: Optional[str] = None
    party_name: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: str = Field(default="prévu", pattern="^(prévu|fait|annulé)$")
    color: Optional[str] = None  # hex color for UI accent (optional)
    created_at: str = Field(default_factory=now_iso)


class AppointmentIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = Field(min_length=1, max_length=200)
    start: str
    end: Optional[str] = None
    party_id: Optional[str] = None
    party_name: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: str = Field(default="prévu", pattern="^(prévu|fait|annulé)$")
    color: Optional[str] = None
