"""Models for the Cut List feature.

A `CutList` is a project that holds N `CutItem`s (frames, glass, brackets, holes).
Items are extracted from a PDF/photo via Gemini Vision, from a DXF via ezdxf,
or entered manually. The 1D optimizer turns linear-extrusion items (frames)
into a bar-cutting plan; the 2D glass cutter handles panels.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stock — Quebec/commercial aluminum + glass defaults (configurable per project)
# ---------------------------------------------------------------------------
DEFAULT_ALU_STOCK_LENGTHS_MM = [6800, 7000, 7315]
DEFAULT_SAW_KERF_MM = 10
DEFAULT_GLASS_THICKNESSES_MM = [6.0, 25.4]  # Single 6mm or 1" thermos

ITEM_TYPES = [
    "frame",      # aluminum extrusion (linear cut)
    "glass",      # glass panel (rectangle)
    "panel",      # other panel (steel/composite)
    "hardware",   # bracket / hinge / lock — position, not a cut
    "hole",       # drilling position
    "other",
]

ITEM_TYPE_LABELS_FR = {
    "frame": "Cadre/Profilé",
    "glass": "Verre/Vitrage",
    "panel": "Panneau",
    "hardware": "Quincaillerie",
    "hole": "Perçage",
    "other": "Autre",
}


class CutItem(BaseModel):
    """A single line on the cut list."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    item_type: str = "frame"        # one of ITEM_TYPES
    label: str = ""                  # free-text: "Linteau", "Vitrage haut", etc.
    profile: Optional[str] = None    # e.g., "Reynaers CS68", "Sapa 5500" — for grouping
    material: Optional[str] = None   # e.g., "Alu anodisé clair", "Verre trempé 6mm"
    length_mm: float = 0.0
    width_mm: Optional[float] = None  # only for 2D items (glass/panel)
    thickness_mm: Optional[float] = None  # glass thickness
    qty: int = 1
    position_x: Optional[float] = None   # for hardware/holes
    position_y: Optional[float] = None
    notes: Optional[str] = None
    source: str = "manual"           # "manual" | "ocr" | "dxf"


class CutListIn(BaseModel):
    name: str
    project_ref: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    items: List[CutItem] = Field(default_factory=list)
    stock_lengths_mm: List[int] = Field(default_factory=lambda: list(DEFAULT_ALU_STOCK_LENGTHS_MM))
    saw_kerf_mm: int = DEFAULT_SAW_KERF_MM
    notes: Optional[str] = None


class CutList(CutListIn):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_filename: Optional[str] = None
    source_type: Optional[str] = None   # "pdf" | "image" | "dxf" | "manual"
    last_optimization: Optional[dict] = None
