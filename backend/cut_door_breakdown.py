"""Door breakdown — turn a single 'door panel' item into its 4 frame pieces
(2 verticals + 2 horizontals) + 8 glazing moulures, based on AT Fabrication's
AT1000 / AT2000 conventions and Portech's standard hardware positioning.

The formulas are derived from real Portech production data:
- AT1000 std (1¾" leaf):
    top rail height       = 2¼" = 57.15 mm
    bottom rail height    = 2¼" = 57.15 mm (or 6⅞" = 174.6 mm if AT2000 base)
    hinge stile width     = 2"   = 50.8 mm
    lock stile width      = 2⅛" = 53.975 mm
- AT2000 base substitution: only the bottom rail differs (6⅞" instead of 2¼")
- Glazing moulures: square stops, sit on the inside flange of each rail/stile.
"""
from dataclasses import dataclass
from typing import List
from uuid import uuid4

# AT door series geometry — all in mm
TOP_RAIL_HEIGHT_MM = 57.15        # 2¼"
BOTTOM_RAIL_STD_MM = 57.15        # 2¼" (AT1000 standard)
BOTTOM_RAIL_AT2000_MM = 174.6     # 6⅞" (AT2000 base substituted on AT1000)
HINGE_STILE_WIDTH_MM = 50.8       # 2"
LOCK_STILE_WIDTH_MM = 53.975      # 2⅛"

# Glazing moulure offsets — distance from inside edge of rail/stile to glass edge.
# Square stops on AT1000 non-insulated, 1/4" rebate.
MOULURE_OFFSET_MM = 6.35          # 1/4"


@dataclass
class DoorBreakdown:
    """Result of decomposing one door into its components."""
    items: List[dict]              # New CutItem dicts to insert
    hardware: List[dict]            # Hardware items with computed positions
    notes: List[str]                 # Warnings / explanations


def decompose_at_door(
    door_width_mm: float,
    door_height_mm: float,
    series: str = "AT1000",         # "AT1000" or "AT1000-AT2000-base"
    glass_thickness_mm: float = 6.0,
    material: str = "Aluminium anodisé bronze",
    label_prefix: str = "Porte",
    qty: int = 1,
    hardware_rules: dict | None = None,
) -> DoorBreakdown:
    """Turn a single door panel into 4 frame pieces + 8 moulures + hardware
    positions, applying Portech's AT1000 cutting formulas.

    `door_width_mm` / `door_height_mm` are the FINAL door-leaf dimensions
    (after subtracting frame + clearances from the rough opening).
    """
    notes: list[str] = []
    bottom_rail = (BOTTOM_RAIL_AT2000_MM
                   if "AT2000" in series.upper() else BOTTOM_RAIL_STD_MM)
    if "AT2000" in series.upper():
        notes.append(
            f"Base AT2000 substituée — traverse basse {bottom_rail:.1f} mm (vs {BOTTOM_RAIL_STD_MM:.1f} mm pour AT1000 std)."
        )

    # ----- Frame pieces -----
    horiz_length = door_width_mm - HINGE_STILE_WIDTH_MM - LOCK_STILE_WIDTH_MM
    vert_length = door_height_mm  # stiles run full height
    items = [
        # 2 horizontaux
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Traverse haute",
            "profile": f"{series} — traverse 2¼\"",
            "material": material,
            "length_mm": round(horiz_length, 1),
            "qty": qty, "source": "computed",
            "notes": f"H = {door_width_mm:.1f} - {HINGE_STILE_WIDTH_MM} (montant charnière) - {LOCK_STILE_WIDTH_MM} (montant serrure)",
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Traverse basse",
            "profile": (f'{series} — traverse 6⅞"' if bottom_rail > 100
                        else f'{series} — traverse 2¼"'),
            "material": material,
            "length_mm": round(horiz_length, 1),
            "qty": qty, "source": "computed",
            "notes": ("Idem traverse haute. Base AT2000 6⅞\"."
                      if bottom_rail > 100
                      else "Idem traverse haute. Base std 2¼\"."),
        },
        # 2 verticaux (stiles) — different widths
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Montant côté charnière",
            "profile": f"{series} — montant 2\"",
            "material": material,
            "length_mm": round(vert_length, 1),
            "qty": qty, "source": "computed",
            "notes": "Pleine hauteur de porte. Largeur 2\" (50.8 mm).",
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Montant côté serrure",
            "profile": f"{series} — montant 2⅛\"",
            "material": material,
            "length_mm": round(vert_length, 1),
            "qty": qty, "source": "computed",
            "notes": "Pleine hauteur de porte. Largeur 2⅛\" (53.975 mm).",
        },
    ]

    # ----- Glass moulures (4 vertical + 4 horizontal for non-insulated) -----
    moulure_vert = door_height_mm - TOP_RAIL_HEIGHT_MM - bottom_rail - 2 * MOULURE_OFFSET_MM
    moulure_horiz = horiz_length - 2 * MOULURE_OFFSET_MM
    items.extend([
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Moulure verticale (verre {glass_thickness_mm:.0f}mm)",
            "profile": f"{series} — moulure carrée {glass_thickness_mm:.0f}mm",
            "material": material,
            "length_mm": round(moulure_vert, 1),
            "qty": 4 * qty, "source": "computed",
            "notes": f"4 par porte (porte non-isolée). Calc : H_porte - traverse_haute - traverse_basse - 2×{MOULURE_OFFSET_MM}.",
        },
        {
            "id": str(uuid4()), "item_type": "frame",
            "label": f"{label_prefix} — Moulure horizontale (verre {glass_thickness_mm:.0f}mm)",
            "profile": f"{series} — moulure carrée {glass_thickness_mm:.0f}mm",
            "material": material,
            "length_mm": round(moulure_horiz, 1),
            "qty": 4 * qty, "source": "computed",
            "notes": f"4 par porte. Calc : L_traverse - 2×{MOULURE_OFFSET_MM}.",
        },
    ])

    # ----- Glass panel itself -----
    glass_w = moulure_horiz  # same as moulure horizontal length
    glass_h = moulure_vert   # same as moulure vertical length
    items.append({
        "id": str(uuid4()), "item_type": "glass",
        "label": f"{label_prefix} — Vitrage",
        "material": f"Verre trempé {glass_thickness_mm:.0f}mm",
        "length_mm": round(glass_h, 1),
        "width_mm": round(glass_w, 1),
        "thickness_mm": glass_thickness_mm,
        "qty": qty, "source": "computed",
        "notes": "Vitrage simple trempé pour porte non-isolée.",
    })

    # ----- Hardware positions (from bottom of door leaf) -----
    rules = hardware_rules or {}
    cyl_h = rules.get("cylinder_height_mm", 1016.0)
    strike_off = rules.get("strike_offset_mm", 19.05)
    handle_h = rules.get("handle_height_mm", 876.3)
    hardware = [
        {
            "id": str(uuid4()), "item_type": "hole",
            "label": "Perçage cylindre / serrure MS",
            "length_mm": 0, "qty": qty,
            "position_y": round(cyl_h, 1),
            "notes": f"Centré à {cyl_h:.0f} mm du bas de la porte sur le montant côté serrure.",
            "source": "computed",
        },
        {
            "id": str(uuid4()), "item_type": "hole",
            "label": "Machinage gâche (sur cadre)",
            "length_mm": 0, "qty": qty,
            "position_y": round(cyl_h + strike_off, 1),
            "notes": f"Centré à {cyl_h + strike_off:.0f} mm du bas — 3/4\" plus bas que le cylindre, sur le montant vertical du cadre.",
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
            "length_mm": round(door_height_mm - 6.35, 1),  # full minus 1/4" at bottom
            "qty": qty,
            "notes": "Flush au sommet de la porte. Coupée à 1/4\" du bas pour dégager le seuil.",
            "source": "computed",
        },
    ]

    notes.append(
        f"Porte décomposée : 2 traverses {horiz_length:.0f} mm × 2 montants {vert_length:.0f} mm "
        f"+ 4 moulures vert {moulure_vert:.0f} mm + 4 moulures horiz {moulure_horiz:.0f} mm + 1 vitrage."
    )
    return DoorBreakdown(items=items, hardware=hardware, notes=notes)
