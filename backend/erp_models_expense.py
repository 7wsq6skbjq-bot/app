"""Expense models — business expenses with Quebec tax tracking."""
import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from erp_models import now_iso

# Hard-coded categories — French, ordered by frequency of use for Portech.
EXPENSE_CATEGORIES = [
    "Matériaux",
    "Carburant",
    "Outils",
    "Véhicule",
    "Sous-traitance",
    "Bureau",
    "Marketing",
    "Abonnements logiciels",
    "Repas/Représentation",
    "Téléphonie/Internet",
    "Loyer",
    "Assurances",
    "Formation",
    "Autre",
]

PAYMENT_METHODS = [
    "Carte",
    "Chèque",
    "Comptant",
    "Transfert",
    "Autre",
]

STATUSES = ["payée", "à payer"]


class Expense(BaseModel):
    """A single business expense — receipt or invoice from a supplier."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str  # YYYY-MM-DD
    supplier_name: Optional[str] = None
    supplier_id: Optional[str] = None  # FK to erp_parties (kind=supplier)
    description: str = Field(min_length=1, max_length=500)
    category: str = Field(default="Autre")
    subtotal: float = 0.0      # HT (before taxes)
    tps: float = 0.0           # GST 5%
    tvq: float = 0.0           # QST 9.975%
    total: float = 0.0         # subtotal + tps + tvq
    payment_method: str = Field(default="Carte")
    status: str = Field(default="payée")
    invoice_ref: Optional[str] = None  # supplier invoice number for accountant
    receipt_filename: Optional[str] = None  # stored under /app/backend/receipts/
    notes: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class ExpenseIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    date: str
    supplier_name: Optional[str] = None
    supplier_id: Optional[str] = None
    description: str = Field(min_length=1, max_length=500)
    category: str = "Autre"
    subtotal: float = 0.0
    tps: float = 0.0
    tvq: float = 0.0
    total: float = 0.0
    payment_method: str = "Carte"
    status: str = "payée"
    invoice_ref: Optional[str] = None
    receipt_filename: Optional[str] = None
    notes: Optional[str] = None
