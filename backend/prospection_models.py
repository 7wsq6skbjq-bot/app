"""Pydantic models for the Portech prospection (vitreries) campaigns."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Prospect (a vitrerie / glass shop) ----------
class Prospect(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=200)
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None  # "montreal", "laval", "rive-sud", "rive-nord"
    source: str = "manual"        # "manual" | "google-maps" | "csv"
    google_place_id: Optional[str] = None
    rating: Optional[float] = None
    notes: Optional[str] = None
    status: str = Field(
        default="nouveau",
        pattern="^(nouveau|à contacter|envoyé|ouvert|cliqué|répondu|client|non-intéressé|invalide)$",
    )
    last_sent_at: Optional[str] = None
    last_opened_at: Optional[str] = None
    last_clicked_at: Optional[str] = None
    send_count: int = 0
    unsubscribed: bool = False
    created_at: str = Field(default_factory=now_iso)


class ProspectIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=200)
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = "nouveau"


class ProspectBulkImport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    prospects: List[ProspectIn]


# ---------- Campaign (an email template) ----------
class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=200)
    from_name: str = "Portech"
    from_email: str = "info@portech.info"
    body_html: str
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class CampaignIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    subject: str
    from_name: str = "Portech"
    from_email: str = "info@portech.info"
    body_html: str


# ---------- Google Maps scrape request ----------
class ScrapeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: str = Field(default="vitrerie", description="Search keyword")
    location: str = Field(description="City or region e.g. 'Montréal, QC'")
    max_results: int = Field(default=20, ge=1, le=60)


# ---------- Send campaign request ----------
class SendCampaignRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    campaign_id: str
    prospect_ids: List[str] = Field(min_length=1)
    confirm: bool = Field(
        description="Must be True — explicit confirmation to send",
    )
    test_only: bool = Field(
        default=False,
        description="If True, send only to test_email (override prospects)",
    )
    test_email: Optional[EmailStr] = None


# ---------- Outbox entry (one prospect × one campaign send) ----------
class OutboxEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    prospect_id: str
    to_email: str
    sent_at: str = Field(default_factory=now_iso)
    resend_id: Optional[str] = None
    opened_at: Optional[str] = None
    clicked_at: Optional[str] = None
    status: str = "queued"  # queued | sent | failed | opened | clicked
