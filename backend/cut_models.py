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
    "gasket",     # joint / gasket / weatherseal — measured in mm linear
    "hardware",   # bracket / hinge / lock — position, not a cut
    "hole",       # drilling position
    "other",
]

ITEM_TYPE_LABELS_FR = {
    "frame": "Cadre/Profilé",
    "glass": "Verre/Vitrage",
    "panel": "Panneau",
    "gasket": "Gasket/Joint",
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
    part_number: Optional[str] = None  # e.g., "UH-120-DA", "ADAM-MS1853S320"
    manufacturer: Optional[str] = None  # e.g., "AT Fabrication", "ASSA ABLOY", "ILCO"
    length_mm: float = 0.0
    width_mm: Optional[float] = None  # only for 2D items (glass/panel)
    thickness_mm: Optional[float] = None  # glass thickness
    qty: int = 1
    # Raw rough-opening dimensions (BEFORE subtracting mullions + clearances).
    opening_length_mm: Optional[float] = None
    opening_width_mm: Optional[float] = None
    position_x: Optional[float] = None   # for hardware/holes — from bottom-left of door
    position_y: Optional[float] = None
    notes: Optional[str] = None
    source: str = "manual"           # "manual" | "ocr" | "dxf" | "computed"


class FrameSpecs(BaseModel):
    """Profile + clearance specs used to compute final cut dimensions.

    These are EDITABLE by the user — the AI tries to extract them from the
    plan's detail cartouche, but the user can override them at any time.
    The defaults match Portech's standard practice for commercial alu doors.
    """
    # Frame profile thicknesses (in mm)
    mullion_thickness_mm: float = 44.5      # 1¾" tube — vertical mullion / jamb width
    jamb_thickness_mm: float = 44.5         # vertical jambs (same as mullion at Portech)
    head_thickness_mm: float = 44.5         # horizontal head (same — symmetric profile)
    profile_depth_mm: float = 101.6         # 4" tube depth (front-to-back)

    # Door-to-frame clearances (in mm)
    side_clearance_mm: float = 3.0          # gap on each side (jamb ↔ door)
    head_clearance_mm: float = 4.84         # gap on top (head ↔ door)
    undercut_clearance_mm: float = 17.46    # 11/16" — gap under door (door bottom to floor)
    threshold_thickness_mm: float = 12.7    # 1/2" — threshold/seuil thickness if present
    has_threshold: bool = True

    # Hardware position rules (in mm from BOTTOM of door leaf)
    cylinder_height_mm: float = 1016.0      # cylinder/MS lock centerline
    strike_offset_mm: float = 19.05         # strike is 3/4" lower than cylinder on jamb
    handle_height_mm: float = 876.3         # 34½" — pull/paddle handle centerline
    hinge_top_flush: bool = True            # continuous hinge flush at top
    hinge_bottom_undercut_mm: float = 6.35  # 1/4" cut at bottom of continuous hinge


class CutListIn(BaseModel):
    name: str
    project_ref: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    items: List[CutItem] = Field(default_factory=list)
    stock_lengths_mm: List[int] = Field(default_factory=lambda: list(DEFAULT_ALU_STOCK_LENGTHS_MM))
    saw_kerf_mm: int = DEFAULT_SAW_KERF_MM
    frame_specs: Optional[FrameSpecs] = None
    notes: Optional[str] = None


class CutList(CutListIn):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_filename: Optional[str] = None
    source_type: Optional[str] = None   # "pdf" | "image" | "dxf" | "manual"
    last_optimization: Optional[dict] = None
