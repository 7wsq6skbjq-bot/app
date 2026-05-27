"""DXF parser for the Cut List feature.

Walks an uploaded DXF, extracts simple linear entities (LINE, LWPOLYLINE) and
rectangles (CLOSED LWPOLYLINE with 4 corners), and returns a list of
CutItem-like dicts ready to be reviewed by the user.

PROBLEM (2026-05): a DXF of a single door was producing 400+ items because
the parser was returning every LINE in the file, including dimension lines,
hatch patterns, centerlines and annotation arrows. The vast majority of those
are NOT real cuts.

SOLUTION: aggressive filtering with 3 strategies:
  1. **Layer blacklist** — skip well-known annotation / dimension layer names.
  2. **Minimum length** — ignore any segment < 50mm (cote arrows are typically
     10-30mm, while real frame cuts are ≥ 200mm).
  3. **Per-layer deduplication** — collapse all identical (length_mm rounded
     to integer) entries on the same layer into a single item with qty=N.
"""
import logging
import math
import re
from collections import defaultdict
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

# Anything matching one of these patterns in the LAYER name is dropped.
# These names cover AutoCAD, BricsCAD, FreeCAD, Inventor and AT Fabrication
# native DXF conventions seen in the field.
LAYER_BLACKLIST_PATTERNS = [
    r"^DEFPOINTS$",                        # ezdxf internal
    r"^0$",                                # default layer — almost always annotations
    r"DIM(ENSION)?S?(_|$)",                # COTAGE / DIM_LAYER / DIMENSIONS / DIM-LINE
    r"COTE",                               # cote / cotes / cotation
    r"COTATION",
    r"HATCH",                              # hachures
    r"HACHURE",
    r"TEXT",                               # textes / text / TEXTE
    r"ANNOT",                              # annotations
    r"CENTER",                             # centerlines
    r"AXIS",                               # axes
    r"AXE",                                # axes en français
    r"REPERE",                             # repères
    r"REFERENCE",
    r"LEADER",                             # flèches de cote
    r"FLECHE",
    r"NOTE",
    r"^(?:CENTRE|CL)$",                    # CL / CENTRE common centerline names
    r"MASQU",                              # masques d'annotations
    r"VIEWPORT",
    r"GUIDE",
]
_LAYER_BLACKLIST_RE = re.compile("|".join(LAYER_BLACKLIST_PATTERNS), re.IGNORECASE)

# Real frame cuts at Portech are at minimum ~150mm (a short transom). Anything
# below 50mm is almost certainly a cote arrow / hatch tick / annotation.
MIN_REAL_CUT_MM = 50.0


def _to_mm(doc) -> float:
    """Return the multiplier to convert document units to mm."""
    insunits = doc.header.get("$INSUNITS", 0)
    return INSUNITS_TO_MM.get(insunits, 1.0)


def _line_length(start, end, k: float) -> float:
    dx = (end[0] - start[0]) * k
    dy = (end[1] - start[1]) * k
    return math.hypot(dx, dy)


def _is_annotation_layer(layer: str) -> bool:
    return bool(_LAYER_BLACKLIST_RE.search(layer or ""))


def parse_dxf(file_path: str) -> dict:
    """Read a DXF file and return:

    {
      "unit_factor_mm": float,
      "items": [ {item_type, length_mm, width_mm?, label, source="dxf", qty}, ... ],
      "warnings": [str, ...],
    }
    """
    try:
        doc = ezdxf.readfile(file_path)
    except (IOError, ezdxf.DXFStructureError) as exc:
        return {"items": [], "warnings": [f"Fichier DXF invalide : {exc}"]}

    k = _to_mm(doc)
    msp = doc.modelspace()
    warnings: list[str] = []

    # ── Pass 1: collect linear cuts grouped by (layer, rounded length) ──
    # Filter: skip blacklisted layers + tiny segments.
    # Aggregate: identical (layer, length-to-nearest-1mm) → single item w/ qty=N.
    line_buckets: dict[tuple[str, int], dict] = {}
    skipped_layers = 0
    skipped_short = 0

    for line in msp.query("LINE"):
        layer = line.dxf.layer or ""
        if _is_annotation_layer(layer):
            skipped_layers += 1
            continue
        L = _line_length(line.dxf.start, line.dxf.end, k)
        if L < MIN_REAL_CUT_MM:
            skipped_short += 1
            continue
        key = (layer, round(L))
        bucket = line_buckets.setdefault(key, {
            "length_mm": round(L, 1),
            "qty": 0,
            "layer": layer,
        })
        bucket["qty"] += 1

    items: list[dict] = []
    for (layer, _), b in line_buckets.items():
        items.append({
            "item_type": "frame",
            "label": f"Ligne (calque {layer})" if layer else "Ligne",
            "length_mm": b["length_mm"],
            "qty": b["qty"],
            "profile": layer or None,
            "source": "dxf",
        })

    # ── Pass 2: rectangles (LWPOLYLINE closed, 4 corners) → glass/panel ──
    rect_buckets: dict[tuple, dict] = {}
    for pl in msp.query("LWPOLYLINE"):
        layer = pl.dxf.layer or ""
        if _is_annotation_layer(layer):
            continue
        try:
            points = [(p[0], p[1]) for p in pl.get_points()]
        except Exception:
            continue
        if not pl.closed or len(points) != 4:
            # Open polyline or non-rectangle → sum segments as a linear cut
            total = 0.0
            seq = points + ([points[0]] if pl.closed else [])
            for a, b in zip(seq, seq[1:]):
                total += _line_length(a, b, k)
            if total >= MIN_REAL_CUT_MM:
                key = (layer, round(total))
                bucket = line_buckets.setdefault(key, {
                    "length_mm": round(total, 1),
                    "qty": 0,
                    "layer": layer,
                })
                # if already present, this just bumps qty
                if "_added_polyline" not in bucket:
                    bucket["_added_polyline"] = True
                items.append({
                    "item_type": "frame",
                    "label": f"Polyligne (calque {layer})",
                    "length_mm": round(total, 1),
                    "qty": 1,
                    "profile": layer or None,
                    "source": "dxf",
                })
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        w = (max(xs) - min(xs)) * k
        h = (max(ys) - min(ys)) * k
        if w < MIN_REAL_CUT_MM or h < MIN_REAL_CUT_MM:
            continue
        layer_l = layer.lower()
        if "verre" in layer_l or "glass" in layer_l or "vitr" in layer_l:
            t = "glass"
            material = "Verre"
        else:
            t = "panel"
            material = layer or None
        key = (layer, t, round(max(w, h)), round(min(w, h)))
        bucket = rect_buckets.setdefault(key, {
            "item_type": t,
            "label": f"Rectangle (calque {layer})" if layer else "Rectangle",
            "length_mm": round(max(w, h), 1),
            "width_mm": round(min(w, h), 1),
            "qty": 0,
            "material": material,
            "source": "dxf",
        })
        bucket["qty"] += 1

    items.extend(rect_buckets.values())

    # ── Pass 3: CIRCLE → drilling positions (still individual: positions differ) ──
    for circ in msp.query("CIRCLE"):
        if _is_annotation_layer(circ.dxf.layer or ""):
            continue
        d = circ.dxf.radius * 2 * k
        if d < 1:
            continue
        items.append({
            "item_type": "hole",
            "label": f"Perçage Ø{round(d, 1)} mm (calque {circ.dxf.layer})",
            "length_mm": round(d, 1),
            "position_x": round(circ.dxf.center[0] * k, 1),
            "position_y": round(circ.dxf.center[1] * k, 1),
            "qty": 1,
            "source": "dxf",
        })

    # Sort: longest pieces first (workshop priority).
    items.sort(key=lambda it: -(it.get("length_mm") or 0))

    if not items:
        warnings.append("Aucune entité exploitable trouvée (LINE, LWPOLYLINE, CIRCLE).")
    if k == 1.0 and doc.header.get("$INSUNITS", 0) == 0:
        warnings.append("Unités non spécifiées dans le DXF — millimètres présumés.")
    if skipped_layers or skipped_short:
        warnings.append(
            f"Filtrage automatique : {skipped_layers} entité(s) ignorée(s) "
            f"sur les calques d'annotation/cotation, {skipped_short} segment(s) "
            f"trop court(s) (< {MIN_REAL_CUT_MM:.0f} mm) écarté(s)."
        )

    return {
        "unit_factor_mm": k,
        "insunits": doc.header.get("$INSUNITS", 0),
        "items": items,
        "warnings": warnings,
    }
