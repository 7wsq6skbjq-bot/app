"""Door breakdown — turn a single 'door panel' item into its frame pieces
+ glazing moulures + hardware positions.

All dimensions are CALIBRATED against the official AT Fabrication shop drawing
"DÉTAILS DE PORTE AT1000 ET 2000 — REV-04-2026.dxf" (provided by Portech).
The four production models are:
  - AT1000  : non-insulated, 2¼" (55.5 mm) rails+stiles, 1/4" or 1" glass
  - AT2000  : non-insulated, 3-11/16" (93.85 mm) rails+stiles, 1/4" or 1" glass
  - ATi1000 : insulated (thermal break), 2¼" sections, 1" glass only
  - ATi2000 : insulated, 3-11/16" sections, 1" glass only

For a STANDARD 36"×84" rough opening (914.4 × 2133.6 mm), the DXF gives:
                   Rail cut    Stile cut   Moulure-V (6mm)   Moulure-V (25mm)
  AT1000           799.30      2111.40     1928.90           1927.30
  AT2000           723.10      2111.40     1811.70           1809.80
  ATi1000          799.30      2105.70        —              1927.30
  ATi2000          723.10      2105.70        —              1809.80

The OFFSETS (opening − cut) are CONSTANT — that's how we scale to other
rough opening sizes :

  width_offset_mm   = 914.4  − rail_cut    → 115.10 (AT1000/i1000)  / 191.30 (AT2000/i2000)
  height_offset_mm  = 2133.6 − stile_cut   →  22.20 (AT-non-insulated) / 27.90 (ATi-insulated)
  moulure_v_offset  = stile_cut − moulure  → varies by glass thickness & section
"""
from dataclasses import dataclass
from typing import List, Optional
from uuid import uuid4

# ----- Section profile heights (rail = horizontal, stile = vertical) -----
SECTION_HEIGHT_MM = {
    "AT1000": 55.5,
    "AT2000": 93.85,
    "ATI1000": 55.5,
    "ATI2000": 93.85,
}

# ----- Width offset: opening_width - rail_cut_length -----
WIDTH_OFFSET_MM = {
    "AT1000": 115.10,
    "AT2000": 191.30,
    "ATI1000": 115.10,
    "ATI2000": 191.30,
}

# ----- Height offset: opening_height - stile_cut_length -----
# (clearances: top + undercut + threshold/thermal-break adjustments)
HEIGHT_OFFSET_MM = {
    "AT1000": 22.20,
    "AT2000": 22.20,
    "ATI1000": 27.90,
    "ATI2000": 27.90,
}

# ----- Vertical moulure offset: stile_cut - moulure_v_length -----
# Indexed by (model, glass_thickness_mm_rounded)
MOULURE_V_OFFSET_MM = {
    ("AT1000", 6):    182.50,    # 2111.4 - 1928.9
    ("AT1000", 25):   184.10,    # 2111.4 - 1927.3
    ("AT2000", 6):    299.70,    # 2111.4 - 1811.7
    ("AT2000", 25):   301.60,    # 2111.4 - 1809.8
    ("ATI1000", 25):  178.40,    # 2105.7 - 1927.3 (insulated only uses 1" glass)
    ("ATI2000", 25):  295.90,    # 2105.7 - 1809.8
}

# Square moulure offset (rebate from rail inside edge to glass edge)
MOULURE_H_OFFSET_MM = 6.35     # 1/4" rebate — standard AT square stop

# Hardware position rules (mm from BOTTOM of door leaf)
DEFAULT_CYL_HEIGHT_MM = 1016.0       # 40"
DEFAULT_STRIKE_OFFSET_MM = 19.05     # 3/4" lower than cylinder on jamb
DEFAULT_HANDLE_HEIGHT_MM = 876.3     # 34½"
HINGE_BOTTOM_UNDERCUT_MM = 6.35      # 1/4" cut at bottom of continuous hinge


@dataclass
class DoorBreakdown:
    items: List[dict]
    hardware: List[dict]
    notes: List[str]


def _normalize_series(raw: str) -> str:
    """Map any user-supplied series string to a canonical key in our spec tables."""
    s = (raw or "").upper().replace(" ", "").replace("-", "").replace("_", "")
    if "ATI2000" in s or "AT-I2000" in s or "AT_I2000" in s:
        return "ATI2000"
    if "ATI1000" in s:
        return "ATI1000"
    if "AT2000" in s:
        return "AT2000"
    return "AT1000"  # default


def decompose_at_door(
    door_width_mm: float,
    door_height_mm: float,
    series: str = "AT1000",
    glass_thickness_mm: float = 6.0,
    material: str = "Aluminium anodisé bronze",
    label_prefix: str = "Porte",
    qty: int = 1,
    hardware_rules: Optional[dict] = None,
) -> DoorBreakdown:
    """Decompose a door into its actual cut pieces.

    ⚠ `door_width_mm` and `door_height_mm` here are the **rough-opening**
    dimensions (ouverture libre) — same as what the AT detail drawing uses.
    The function applies the AT-series offsets to derive the cut lengths.

    Example: a 36"×84" opening on AT1000 1/4" gives :
        rail cut    = 914.4  − 115.10 = 799.30 mm  ×2
        stile cut   = 2133.6 −  22.20 = 2111.40 mm ×2
        moulure-V   = 2111.4 − 182.50 = 1928.90 mm ×4
        moulure-H   = 799.30 − 2×6.35 = 786.60 mm  ×4
    """
    notes: list[str] = []
    series_key = _normalize_series(series)
    section_h = SECTION_HEIGHT_MM[series_key]
    width_off = WIDTH_OFFSET_MM[series_key]
    height_off = HEIGHT_OFFSET_MM[series_key]

    glass_key = 6 if glass_thickness_mm < 12 else 25
    moulure_v_off = MOULURE_V_OFFSET_MM.get((series_key, glass_key))
    if moulure_v_off is None:
        # Insulated models with 6mm glass don't exist in production; fall back
        # to closest available spec and warn.
        moulure_v_off = MOULURE_V_OFFSET_MM.get((series_key, 25)) \
            or MOULURE_V_OFFSET_MM[("AT1000", 25)]
        notes.append(
            f"Combinaison série/verre non standard ({series_key} + {glass_thickness_mm}mm) — "
            f"offset moulure verticale estimé."
        )

    # ----- Cut lengths -----
    rail_cut = door_width_mm - width_off
    stile_cut = door_height_mm - height_off
    moulure_v = stile_cut - moulure_v_off
    moulure_h = rail_cut - 2 * MOULURE_H_OFFSET_MM

    is_insulated = series_key.startswith("ATI")
    # Stile widths (hinge vs lock differ by 4mm in AT std; symmetric in AT2000)
    hinge_stile = 50.8 if not series_key.endswith("2000") else section_h
    lock_stile = 53.975 if not series_key.endswith("2000") else section_h

    # Profile name shown to the workshop (also normalized by the optimizer)
    profile = f'{series_key} — tube 1¾" × 4"' if section_h < 70 \
        else f'{series_key} — tube 3-11/16" × 4"'

    items = [
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Traverse haute",
            "profile": profile, "material": material,
            "length_mm": round(rail_cut, 1), "qty": qty, "source": "computed",
            "notes": f"Ouverture {door_width_mm:.1f} − {width_off} (offset {series_key}) = {rail_cut:.1f}",
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Traverse basse",
            "profile": profile, "material": material,
            "length_mm": round(rail_cut, 1), "qty": qty, "source": "computed",
            "notes": "Identique traverse haute (sections symétriques sur AT).",
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Montant côté charnière",
            "profile": profile, "material": material,
            "length_mm": round(stile_cut, 1), "qty": qty, "source": "computed",
            "notes": (
                f"Hauteur ouverture {door_height_mm:.1f} − {height_off} = {stile_cut:.1f}."
                f" Largeur montant : {hinge_stile} mm."
            ),
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Montant côté serrure",
            "profile": profile, "material": material,
            "length_mm": round(stile_cut, 1), "qty": qty, "source": "computed",
            "notes": f"Identique côté charnière. Largeur montant : {lock_stile} mm.",
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Moulure verticale verre {glass_thickness_mm:.1f}mm",
            "profile": f"{series_key} — moulure verre {glass_thickness_mm:.1f}mm",
            "material": material,
            "length_mm": round(moulure_v, 1),
            "qty": 4 * qty, "source": "computed",
            "notes": f"4 par porte. Calc : {stile_cut:.1f} − {moulure_v_off} (offset moulure V) = {moulure_v:.1f}",
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Moulure horizontale verre {glass_thickness_mm:.1f}mm",
            "profile": f"{series_key} — moulure verre {glass_thickness_mm:.1f}mm",
            "material": material,
            "length_mm": round(moulure_h, 1),
            "qty": 4 * qty, "source": "computed",
            "notes": f"4 par porte. Calc : rail {rail_cut:.1f} − 2 × {MOULURE_H_OFFSET_MM} = {moulure_h:.1f}",
        },
        {
            "id": str(uuid4()), "item_type": "glass",
            "label": f"{label_prefix} — Vitrage",
            "material": f"Verre {'thermos' if glass_thickness_mm >= 12 else 'trempé'} {glass_thickness_mm:.1f}mm",
            "length_mm": round(moulure_v, 1),
            "width_mm": round(moulure_h, 1),
            "thickness_mm": glass_thickness_mm,
            "qty": qty, "source": "computed",
            "notes": "Dimensions = aire des moulures (vitrage 6mm trempé ou thermos 25.4mm).",
        },
    ]

    # ----- Hardware positions (from bottom of door leaf) -----
    rules = hardware_rules or {}
    cyl_h = rules.get("cylinder_height_mm", DEFAULT_CYL_HEIGHT_MM)
    strike_off = rules.get("strike_offset_mm", DEFAULT_STRIKE_OFFSET_MM)
    handle_h = rules.get("handle_height_mm", DEFAULT_HANDLE_HEIGHT_MM)
    hardware = [
        {
            "id": str(uuid4()), "item_type": "hole",
            "label": "Perçage cylindre / serrure MS",
            "length_mm": 0, "qty": qty,
            "position_y": round(cyl_h, 1),
            "notes": f"Centré à {cyl_h:.0f} mm du bas, montant côté serrure.",
            "source": "computed",
        },
        {
            "id": str(uuid4()), "item_type": "hole",
            "label": "Machinage gâche (cadre)",
            "length_mm": 0, "qty": qty,
            "position_y": round(cyl_h + strike_off, 1),
            "notes": f"3/4\" plus bas que le cylindre — à {cyl_h + strike_off:.0f} mm sur montant vertical du cadre.",
            "source": "computed",
        },
        {
            "id": str(uuid4()), "item_type": "hole",
            "label": "Poignée / paddle / push bar",
            "length_mm": 0, "qty": qty,
            "position_y": round(handle_h, 1),
            "notes": f"Centré à {handle_h:.0f} mm du bas (34½\").",
            "source": "computed",
        },
        {
            "id": str(uuid4()), "item_type": "hardware",
            "label": "Charnière continue — installation",
            "length_mm": round(stile_cut - HINGE_BOTTOM_UNDERCUT_MM, 1),
            "qty": qty,
            "notes": "Flush sommet, coupée à 1/4\" du bas (dégagement seuil).",
            "source": "computed",
        },
    ]

    notes.append(
        f"Porte {series_key} (verre {glass_thickness_mm:.1f}mm{' — isolée' if is_insulated else ''}) "
        f"décomposée : 2 rails {rail_cut:.0f} mm + 2 montants {stile_cut:.0f} mm "
        f"+ 4 mouls V {moulure_v:.0f} mm + 4 mouls H {moulure_h:.0f} mm + 1 vitrage."
    )
    return DoorBreakdown(items=items, hardware=hardware, notes=notes)
