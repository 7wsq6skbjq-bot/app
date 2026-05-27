"""Template-based deterministic cut-list builders.

When OCR is unreliable (the LLM may miss elevations, confuse opening vs leaf,
hallucinate counts), the user can instead use these guided forms. The user
provides the GEOMETRY (counts + lengths) — Python computes the DETERMINISTIC
list of cuts, glass items, garniture totals and hardware.

Three supported systems:
  - 'at_door'      : standalone AT1000/AT2000/ATi door (just the leaf+frame).
  - 'flush_glaze'  : Trifab VG450 — Tube à poche (linteau + intermédiaires) +
                     Tube escalier (bas de chaque verre). Garniture #027074.
  - 'curtain_wall' : Kawneer 1620 — Meneaux + couvercles + bris thermique
                     (#162-310) + garniture #027-850.

Door integration: if the user toggles a door inside a FG or MR elevation, we
decompose the door via decompose_at_door() and APPEND those items.
"""
from typing import List, Optional
from uuid import uuid4

from cut_door_breakdown import decompose_at_door

# ===========================================================================
# Profile / part-number catalog (per system)
# ===========================================================================
TRIFAB_VG450 = {
    "tube_poche": {
        "label": "Tube à poche 1¾\" × 4½\"",
        "part_number": "450CG005",
        "manufacturer": "Trifab VG450",
    },
    "tube_escalier": {
        "label": "Tube escalier 1¾\" × 4½\"",
        "part_number": "450CG011",
        "manufacturer": "Trifab VG450",
    },
    "garniture": {
        "label": "Garniture de vitrage 6mm",
        "part_number": "027074",
        "manufacturer": "Trifab VG450",
    },
}

KAWNEER_1620 = {
    "meneau": {
        "label": "Meneau 2\" × 3¾\"",
        "part_number": "178-001",
        "manufacturer": "Kawneer 1620",
    },
    "couvercle": {
        "label": "Couvercle 2\" × ¾\"",
        "part_number": "178-006",
        "manufacturer": "Kawneer 1620",
    },
    "plaque_pression": {
        "label": "Plaque à pression 2\"",
        "part_number": "178-300",
        "manufacturer": "Kawneer 1620",
    },
    "bris_thermique": {
        "label": "Bris thermique",
        "part_number": "162-310",
        "manufacturer": "Kawneer 1620",
    },
    "garniture": {
        "label": "Garniture ext + int",
        "part_number": "027-850",
        "manufacturer": "Kawneer 1620",
    },
}


# ===========================================================================
# Helpers
# ===========================================================================

def _make_item(item_type: str, label: str, length_mm: float, qty: int,
               profile_def: Optional[dict] = None,
               material: str = "Aluminium anodisé",
               width_mm: Optional[float] = None,
               thickness_mm: Optional[float] = None,
               notes: Optional[str] = None) -> dict:
    return {
        "id": str(uuid4()),
        "item_type": item_type,
        "label": label,
        "profile": (profile_def or {}).get("label"),
        "part_number": (profile_def or {}).get("part_number"),
        "manufacturer": (profile_def or {}).get("manufacturer"),
        "material": material,
        "length_mm": round(float(length_mm), 2),
        "width_mm": round(float(width_mm), 2) if width_mm is not None else None,
        "thickness_mm": float(thickness_mm) if thickness_mm is not None else None,
        "qty": int(qty),
        "source": "template",
        "notes": notes,
    }


def _glass_perimeter_total(glasses: List[dict]) -> float:
    """Sum of (2 × (W + H) × qty) for every glass in the list."""
    total = 0.0
    for g in glasses:
        w = float(g.get("width_mm") or 0)
        h = float(g.get("height_mm") or 0)
        q = int(g.get("qty") or 1)
        total += 2 * (w + h) * q
    return total


# ===========================================================================
# Builder 1 — AT door alone
# ===========================================================================
def build_at_door(
    series: str,
    leaf_width_mm: float,
    leaf_height_mm: float,
    glass_thickness_mm: float = 6.0,
    door_finish: str = "Aluminium anodisé bronze",
    door_number: Optional[str] = None,
    handing: Optional[str] = None,
    qty: int = 1,
) -> dict:
    """Wraps decompose_at_door() into the unified template-build response shape."""
    label_prefix = f"Porte {door_number}" if door_number else "Porte"
    br = decompose_at_door(
        leaf_width_mm=leaf_width_mm,
        leaf_height_mm=leaf_height_mm,
        series=series,
        glass_thickness_mm=glass_thickness_mm,
        material=door_finish,
        label_prefix=label_prefix,
        qty=qty,
    )
    return {
        "elevation_type": "door",
        "system_label": f"Porte {series}",
        "finish_ext": door_finish,
        "finish_int": door_finish,
        "items": br.items + br.hardware,
        "notes": br.notes + ([f"Sens d'ouverture : {handing}"] if handing else []),
    }


# ===========================================================================
# Builder 2 — Flush Glaze (Trifab VG450)
# ===========================================================================
def build_flush_glaze(
    total_width_mm: float,
    total_height_mm: float,
    verticals: List[dict],          # [{"length_mm": X, "qty": N}, ...]
    horizontals_poche: List[dict],  # tube à poche horizontals (linteau + intermediates)
    horizontals_escalier: List[dict],  # tube escalier (bas de chaque verre)
    glasses: List[dict],            # [{"width_mm": W, "height_mm": H, "qty": N, "thickness_mm": 6}]
    finish_ext: str = "Anodisé Noir",
    finish_int: Optional[str] = None,
    code: str = "FG01",
    door: Optional[dict] = None,    # {series, leaf_width_mm, leaf_height_mm, glass_thickness_mm, door_number, handing}
) -> dict:
    """Build a deterministic Trifab VG450 flush-glaze elevation."""
    finish_int = finish_int or finish_ext
    items: List[dict] = []
    notes: List[str] = []
    material = f"Aluminium anodisé ({finish_ext})"

    # Vertical mullions — Tube à poche
    for i, v in enumerate(verticals, start=1):
        items.append(_make_item(
            "frame",
            f"[{code}] Meneau vertical #{i}",
            v["length_mm"], v.get("qty", 1),
            profile_def=TRIFAB_VG450["tube_poche"],
            material=material,
            notes="Meneau pleine hauteur." if i == 1 else None,
        ))

    # Horizontal — Tube à poche (linteau supérieur + intermédiaires entre vitres superposées)
    for i, h in enumerate(horizontals_poche, start=1):
        items.append(_make_item(
            "frame",
            f"[{code}] Tube à poche horizontal #{i}",
            h["length_mm"], h.get("qty", 1),
            profile_def=TRIFAB_VG450["tube_poche"],
            material=material,
            notes="Linteau ou traverse intermédiaire entre 2 vitres.",
        ))

    # Horizontal — Tube escalier (bas de chaque verre, y compris au-dessus d'une porte)
    for i, h in enumerate(horizontals_escalier, start=1):
        items.append(_make_item(
            "frame",
            f"[{code}] Tube escalier horizontal #{i}",
            h["length_mm"], h.get("qty", 1),
            profile_def=TRIFAB_VG450["tube_escalier"],
            material=material,
            notes="Bas du vitrage (incl. verre au-dessus d'une porte).",
        ))

    # Glass
    for i, g in enumerate(glasses, start=1):
        thick = g.get("thickness_mm") or 6
        glass_label = "thermos" if thick >= 12 else "trempé"
        items.append({
            "id": str(uuid4()),
            "item_type": "glass",
            "label": f"[{code}] Vitrage #{i}",
            "material": f"Verre {glass_label} {thick}mm",
            "length_mm": float(g["height_mm"]),
            "width_mm": float(g["width_mm"]),
            "thickness_mm": float(thick),
            "qty": int(g.get("qty", 1)),
            "source": "template",
        })

    # Garniture de vitrage #027074 = total glass perimeter × 2 (mm linear)
    garniture_total = _glass_perimeter_total(glasses) * 2.0
    if garniture_total > 0:
        items.append(_make_item(
            "hardware",
            f"[{code}] Garniture de vitrage 6mm",
            garniture_total, 1,
            profile_def=TRIFAB_VG450["garniture"],
            material=material,
            notes=f"Calc : Σ(périmètre vitres) × 2 = {garniture_total:.0f} mm.",
        ))

    # Integrated door (if any)
    if door:
        d = build_at_door(
            series=door["series"],
            leaf_width_mm=float(door["leaf_width_mm"]),
            leaf_height_mm=float(door["leaf_height_mm"]),
            glass_thickness_mm=float(door.get("glass_thickness_mm") or 6.0),
            door_finish=door.get("door_finish") or material,
            door_number=door.get("door_number"),
            handing=door.get("handing"),
            qty=1,
        )
        items.extend(d["items"])
        notes.extend(d["notes"])

    elevation_type = "mixed" if door else "flush_glaze"
    notes.append(
        f"[{code}] Système Trifab VG450 — {len(verticals)} meneau(x) V, "
        f"{len(horizontals_poche)} tube à poche H, {len(horizontals_escalier)} tube escalier H, "
        f"{len(glasses)} type(s) de vitrage."
    )

    return {
        "elevation_type": elevation_type,
        "system_label": "ENCADREMENT À POCHE NON-ISOLÉ SÉRIE TRIFAB VG450",
        "finish_ext": finish_ext,
        "finish_int": finish_int,
        "total_width_mm": float(total_width_mm),
        "total_height_mm": float(total_height_mm),
        "items": items,
        "notes": notes,
    }


# ===========================================================================
# Builder 3 — Mur-rideau (Kawneer 1620)
# ===========================================================================
def build_curtain_wall(
    total_width_mm: float,
    total_height_mm: float,
    verticals: List[dict],          # Kawneer meneaux V
    horizontals: List[dict],        # Kawneer meneaux H
    glasses: List[dict],            # thermos panels
    finish_ext: str = "Anodisé Champagne",
    finish_int: str = "Anodisé Clair Classe II (10 microns)",
    code: str = "MR1",
    door: Optional[dict] = None,
) -> dict:
    """Build a deterministic Kawneer 1620 curtain-wall elevation."""
    items: List[dict] = []
    notes: List[str] = []
    material_ext = f"Aluminium anodisé ({finish_ext})"

    total_mullion_linear = 0.0

    # Vertical mullions
    for i, v in enumerate(verticals, start=1):
        items.append(_make_item(
            "frame",
            f"[{code}] Meneau vertical #{i}",
            v["length_mm"], v.get("qty", 1),
            profile_def=KAWNEER_1620["meneau"],
            material=material_ext,
        ))
        # Couvercle ext (same length)
        items.append(_make_item(
            "frame",
            f"[{code}] Couvercle vertical ext #{i}",
            v["length_mm"], v.get("qty", 1),
            profile_def=KAWNEER_1620["couvercle"],
            material=f"Aluminium anodisé ({finish_ext})",
        ))
        # Plaque à pression vertical
        items.append(_make_item(
            "frame",
            f"[{code}] Plaque à pression V #{i}",
            v["length_mm"], v.get("qty", 1),
            profile_def=KAWNEER_1620["plaque_pression"],
            material=material_ext,
        ))
        total_mullion_linear += float(v["length_mm"]) * int(v.get("qty", 1))

    # Horizontal mullions
    for i, h in enumerate(horizontals, start=1):
        items.append(_make_item(
            "frame",
            f"[{code}] Meneau horizontal #{i}",
            h["length_mm"], h.get("qty", 1),
            profile_def=KAWNEER_1620["meneau"],
            material=material_ext,
        ))
        items.append(_make_item(
            "frame",
            f"[{code}] Couvercle horizontal ext #{i}",
            h["length_mm"], h.get("qty", 1),
            profile_def=KAWNEER_1620["couvercle"],
            material=f"Aluminium anodisé ({finish_ext})",
        ))
        items.append(_make_item(
            "frame",
            f"[{code}] Plaque à pression H #{i}",
            h["length_mm"], h.get("qty", 1),
            profile_def=KAWNEER_1620["plaque_pression"],
            material=material_ext,
        ))
        total_mullion_linear += float(h["length_mm"]) * int(h.get("qty", 1))

    # Glass
    for i, g in enumerate(glasses, start=1):
        thick = g.get("thickness_mm") or 25.4
        items.append({
            "id": str(uuid4()),
            "item_type": "glass",
            "label": f"[{code}] Thermos #{i}",
            "material": f"Thermos {thick}mm",
            "length_mm": float(g["height_mm"]),
            "width_mm": float(g["width_mm"]),
            "thickness_mm": float(thick),
            "qty": int(g.get("qty", 1)),
            "source": "template",
        })

    # Bris thermique #162-310 = total linear of vertical+horizontal mullions
    if total_mullion_linear > 0:
        items.append(_make_item(
            "hardware",
            f"[{code}] Bris thermique",
            total_mullion_linear, 1,
            profile_def=KAWNEER_1620["bris_thermique"],
            material=material_ext,
            notes=f"Calc : Σ(meneaux V + H) = {total_mullion_linear:.0f} mm linéaire.",
        ))

    # Garniture ext + int #027-850 = sum perimeters × 2
    garniture_total = _glass_perimeter_total(glasses) * 2.0
    if garniture_total > 0:
        items.append(_make_item(
            "hardware",
            f"[{code}] Garniture ext + int",
            garniture_total, 1,
            profile_def=KAWNEER_1620["garniture"],
            material=material_ext,
            notes=f"Calc : Σ(périmètre thermos) × 2 = {garniture_total:.0f} mm.",
        ))

    # Integrated door (if any)
    if door:
        d = build_at_door(
            series=door["series"],
            leaf_width_mm=float(door["leaf_width_mm"]),
            leaf_height_mm=float(door["leaf_height_mm"]),
            glass_thickness_mm=float(door.get("glass_thickness_mm") or 25.4),
            door_finish=door.get("door_finish") or finish_ext,
            door_number=door.get("door_number"),
            handing=door.get("handing"),
            qty=1,
        )
        items.extend(d["items"])
        notes.extend(d["notes"])

    elevation_type = "mixed" if door else "curtain_wall"
    notes.append(
        f"[{code}] Système Kawneer 1620 — {len(verticals)} meneau(x) V, "
        f"{len(horizontals)} meneau(x) H, {len(glasses)} type(s) thermos. "
        f"Bris thermique total = {total_mullion_linear:.0f} mm linéaire."
    )

    return {
        "elevation_type": elevation_type,
        "system_label": "MUR-RIDEAU SÉRIE KAWNEER 1620",
        "finish_ext": finish_ext,
        "finish_int": finish_int,
        "total_width_mm": float(total_width_mm),
        "total_height_mm": float(total_height_mm),
        "items": items,
        "notes": notes,
    }


# ===========================================================================
# Public dispatch
# ===========================================================================
def build_elevation_from_template(payload: dict) -> dict:
    """Public entrypoint. Routes to the correct builder based on payload['kind']."""
    kind = (payload.get("kind") or "").lower().strip()
    if kind == "at_door":
        return build_at_door(
            series=payload["series"],
            leaf_width_mm=float(payload["leaf_width_mm"]),
            leaf_height_mm=float(payload["leaf_height_mm"]),
            glass_thickness_mm=float(payload.get("glass_thickness_mm") or 6.0),
            door_finish=payload.get("door_finish") or "Aluminium anodisé bronze",
            door_number=payload.get("door_number"),
            handing=payload.get("handing"),
            qty=int(payload.get("qty") or 1),
        )
    if kind == "flush_glaze":
        return build_flush_glaze(
            total_width_mm=float(payload["total_width_mm"]),
            total_height_mm=float(payload["total_height_mm"]),
            verticals=payload.get("verticals") or [],
            horizontals_poche=payload.get("horizontals_poche") or [],
            horizontals_escalier=payload.get("horizontals_escalier") or [],
            glasses=payload.get("glasses") or [],
            finish_ext=payload.get("finish_ext") or "Anodisé Noir",
            finish_int=payload.get("finish_int"),
            code=payload.get("code") or "FG01",
            door=payload.get("door"),
        )
    if kind == "curtain_wall":
        return build_curtain_wall(
            total_width_mm=float(payload["total_width_mm"]),
            total_height_mm=float(payload["total_height_mm"]),
            verticals=payload.get("verticals") or [],
            horizontals=payload.get("horizontals") or [],
            glasses=payload.get("glasses") or [],
            finish_ext=payload.get("finish_ext") or "Anodisé Champagne",
            finish_int=payload.get("finish_int") or "Anodisé Clair Classe II (10 microns)",
            code=payload.get("code") or "MR1",
            door=payload.get("door"),
        )
    raise ValueError(f"Unknown template kind: {kind!r}. Expected 'at_door', 'flush_glaze', or 'curtain_wall'.")
