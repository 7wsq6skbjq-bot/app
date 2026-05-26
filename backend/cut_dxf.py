"""DXF parser for the Cut List feature.

Walks an uploaded DXF, extracts simple linear entities (LINE, LWPOLYLINE) and
rectangles (CLOSED LWPOLYLINE with 4 corners), and returns a list of
CutItem-like dicts ready to be reviewed by the user.

Unit handling: DXF files declare units via `$INSUNITS` ($INSUNITS=4 = mm,
=1 = inch, =0 = unitless). We always convert to mm. If the file says
"unitless", we assume mm (the most common in commercial door projects).
"""
import logging
import math
from typing import Optional

import ezdxf

logger = logging.getLogger("portech.cuts.dxf")

# DXF insunits enum → mm conversion factor
INSUNITS_TO_MM = {
    0: 1.0,    # unitless → assume mm
    1: 25.4,   # inches
    2: 304.8,  # feet
    4: 1.0,    # mm
    5: 10.0,   # cm
    6: 1000.0, # m
}


def _to_mm(doc) -> float:
    """Return the multiplier to convert document units to mm."""
    insunits = doc.header.get("$INSUNITS", 0)
    return INSUNITS_TO_MM.get(insunits, 1.0)


def _line_length(start, end, k: float) -> float:
    dx = (end[0] - start[0]) * k
    dy = (end[1] - start[1]) * k
    return math.hypot(dx, dy)


def parse_dxf(file_path: str) -> dict:
    """Read a DXF file and return:

    {
      "unit_factor_mm": float,
      "items": [ {item_type, length_mm, width_mm?, label, source="dxf"}, ... ],
      "warnings": [str, ...],
    }
    """
    try:
        doc = ezdxf.readfile(file_path)
    except (IOError, ezdxf.DXFStructureError) as exc:
        return {"items": [], "warnings": [f"Fichier DXF invalide : {exc}"]}

    k = _to_mm(doc)
    msp = doc.modelspace()
    items: list[dict] = []
    warnings: list[str] = []

    # Pass 1 — LINE entities → frame cuts
    for line in msp.query("LINE"):
        L = _line_length(line.dxf.start, line.dxf.end, k)
        if L < 1:  # ignore noise < 1mm
            continue
        items.append({
            "item_type": "frame",
            "label": f"Ligne (calque {line.dxf.layer})",
            "length_mm": round(L, 1),
            "qty": 1,
            "profile": line.dxf.layer or None,
            "source": "dxf",
        })

    # Pass 2 — Closed LWPOLYLINE with 4 corners → glass/panel rectangles
    for pl in msp.query("LWPOLYLINE"):
        try:
            points = [(p[0], p[1]) for p in pl.get_points()]
        except Exception:
            continue
        if not pl.closed or len(points) != 4:
            # Open polyline or non-rectangle → sum segments as a linear cut
            total = 0.0
            for a, b in zip(points, points[1:] + ([points[0]] if pl.closed else [])):
                total += _line_length(a, b, k)
            if total > 1:
                items.append({
                    "item_type": "frame",
                    "label": f"Polyligne (calque {pl.dxf.layer})",
                    "length_mm": round(total, 1),
                    "qty": 1,
                    "profile": pl.dxf.layer or None,
                    "source": "dxf",
                })
            continue
        # Closed 4-corner: treat as rectangle (axis-aligned bounding box)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        w = (max(xs) - min(xs)) * k
        h = (max(ys) - min(ys)) * k
        if w < 1 or h < 1:
            continue
        # Heuristic: if layer name contains "verre"/"glass" → glass; else panel
        layer = (pl.dxf.layer or "").lower()
        if "verre" in layer or "glass" in layer or "vitr" in layer:
            t = "glass"
            material = "Verre"
        else:
            t = "panel"
            material = pl.dxf.layer or None
        items.append({
            "item_type": t,
            "label": f"Rectangle (calque {pl.dxf.layer})",
            "length_mm": round(max(w, h), 1),
            "width_mm": round(min(w, h), 1),
            "qty": 1,
            "material": material,
            "source": "dxf",
        })

    # Pass 3 — CIRCLE entities → drilling positions (hole)
    for circ in msp.query("CIRCLE"):
        d = circ.dxf.radius * 2 * k
        items.append({
            "item_type": "hole",
            "label": f"Perçage Ø{round(d, 1)} mm (calque {circ.dxf.layer})",
            "length_mm": round(d, 1),
            "position_x": round(circ.dxf.center[0] * k, 1),
            "position_y": round(circ.dxf.center[1] * k, 1),
            "qty": 1,
            "source": "dxf",
        })

    if not items:
        warnings.append("Aucune entité exploitable trouvée (LINE, LWPOLYLINE, CIRCLE).")
    if k == 1.0 and doc.header.get("$INSUNITS", 0) == 0:
        warnings.append("Unités non spécifiées dans le DXF — millimètres présumés.")

    return {
        "unit_factor_mm": k,
        "insunits": doc.header.get("$INSUNITS", 0),
        "items": items,
        "warnings": warnings,
    }
