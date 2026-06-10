"""Pre-rendered library of AT Fabrication profile cross-sections.

Each function draws ONE profile (head / base / jamb / moulure) as a stylized
cross-section card inside a given rectangle on a ReportLab canvas. The drawing
uses the profile's true face dimension (from `profile_catalog.HYDRO_PARTS` /
`cut_door_breakdown` constants) so the proportions are faithful, while the
internal geometry (chambers, walls, hardware grooves) is rendered as a
deterministic schematic — enough for shop floor identification.

Why "pre-rendered library" : each profile is a NAMED function in this module,
so an artist (or a future agent) can swap in a more detailed drawing per
profile without touching the PDF generator. The PDF generator just calls
`draw_profile_card(c, key, ...)`.

All units are mm on the canvas (ReportLab `mm` already applied by caller).
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.units import mm

# ---------------------------------------------------------------------------
# Profile face dimensions (mm) — single source of truth for the library.
# face_w  : visible width (the dimension that's quoted on shop drawings)
# face_h  : depth (= leaf thickness for stiles/rails ; ~14-25 mm for moulures)
# The renderer scales the card so the face fits within the card area while
# preserving the aspect ratio.
# ---------------------------------------------------------------------------
PROFILES = {
    # ── AT1000 / ATi1000 family (1¾" depth = 44.45 mm) ──────────────────────
    "ATT1005": {
        "label": "Tête / haut de cadre",
        "at_code": "ATT1005",
        "hydro": "MH80477",
        "face_w": 55.5,     # 2¼"
        "face_h": 44.45,    # 1¾"
        "series": "AT1000 / ATi1000 / hybride",
        "category": "head",
        "note": "Linteau supérieur — tube 2¼\". Coupe = largeur du battant.",
    },
    "ATB1000": {
        "label": "Base (seuil) 3⅞\"",
        "at_code": "ATB1000",
        "hydro": "MH80476",
        "face_w": 98.43,
        "face_h": 44.45,
        "series": "AT1000 / ATi1000 / tête AT2000",
        "category": "base",
        "note": "Seuil renforcé 3⅞\". Sert également de TÊTE sur AT2000.",
    },
    "ATV1010": {
        "label": "Jambage côté gâche (strike) 2\"",
        "at_code": "ATV1010",
        "hydro": "MH80478",
        "face_w": 50.8,
        "face_h": 44.45,
        "series": "AT1000 / ATi1000",
        "category": "jamb",
        "note": "Stile côté charnière. Coupe = hauteur du battant.",
    },
    "ATV1015": {
        "label": "Jambage côté serrure (lock) 2⅛\"",
        "at_code": "ATV1015",
        "hydro": "MH80479",
        "face_w": 53.975,
        "face_h": 44.45,
        "series": "AT1000 / ATi1000",
        "category": "jamb",
        "note": "Stile côté serrure — usinage MS Adams Rite.",
    },
    # ── AT2000 / ATi2000 family (asymétrique) ───────────────────────────────
    "ATB2000": {
        "label": "Base lourde (seuil) 6⅞\"",
        "at_code": "ATB2000",
        "hydro": "MH80321",
        "face_w": 174.625,
        "face_h": 44.45,
        "series": "AT2000 / ATi2000",
        "category": "base",
        "note": "Traverse basse renforcée 6⅞\" — caractéristique AT2000.",
    },
    "ATV2010": {
        "label": "Jambage côté gâche (strike) 3½\"",
        "at_code": "ATV2010",
        "hydro": "MH81325",
        "face_w": 88.9,
        "face_h": 44.45,
        "series": "AT2000 / ATi2000",
        "category": "jamb",
        "note": "Stile côté charnière (heavy-duty).",
    },
    "ATV2015": {
        "label": "Jambage côté serrure (lock) 3⅝\"",
        "at_code": "ATV2015",
        "hydro": "MH81326",
        "face_w": 92.075,
        "face_h": 44.45,
        "series": "AT2000 / ATi2000",
        "category": "jamb",
        "note": "Stile côté serrure — usinage MS Adams Rite.",
    },
    # ── Moulures (parclose) ─────────────────────────────────────────────────
    "AT1045": {
        "label": "Moulure CARRÉE 13.48 mm",
        "at_code": "AT1045",
        "hydro": "MH80485",
        "face_w": 13.48,
        "face_h": 13.48,
        "series": "Toutes séries — verre simple 6 mm",
        "category": "moulure",
        "note": "Moulure carrée. 4 V + 4 H par porte, mitrés 45°.",
    },
    "AT1050": {
        "label": "Moulure PLATE 14.3 mm",
        "at_code": "AT1050",
        "hydro": "MH80486",
        "face_w": 14.3,
        "face_h": 6.0,
        "series": "Toutes séries — thermos 25.4 mm",
        "category": "moulure",
        "note": "Moulure plate (épaule mince). 4 V + 4 H, mitrés 45°.",
    },
    # ── Cladding (ATi only) ────────────────────────────────────────────────
    "ATCV1030": {
        "label": "Cladding vertical (revêtement isolé)",
        "at_code": "ATCV1030",
        "hydro": "MH80483",
        "face_w": 55.5,
        "face_h": 12.7,
        "series": "ATi1000",
        "category": "cladding",
        "note": "Cladding vertical — leaf_height − 5.7 mm. 2 par porte.",
    },
    "ATCV2030": {
        "label": "Cladding vertical (revêtement isolé)",
        "at_code": "ATCV2030",
        "hydro": "MH81324",
        "face_w": 55.5,
        "face_h": 12.7,
        "series": "ATi2000",
        "category": "cladding",
        "note": "Cladding vertical AT2000. 2 par porte.",
    },
    "ATCHA1035": {
        "label": "Cladding horizontal (revêtement isolé)",
        "at_code": "ATCHA1035",
        "hydro": "MH80482",
        "face_w": 55.5,
        "face_h": 12.7,
        "series": "ATi1000 / ATi2000",
        "category": "cladding",
        "note": "Cladding horizontal — leaf_width − 5.7 mm. 2 par porte.",
    },
}


# Which profiles are used by which series — drives the per-order selection.
SERIES_PROFILES = {
    "AT1000":  ["ATT1005", "ATB1000", "ATV1010", "ATV1015", "AT1045", "AT1050"],
    "ATi1000": ["ATT1005", "ATB1000", "ATV1010", "ATV1015",
                "ATCV1030", "ATCHA1035", "AT1045", "AT1050"],
    "AT2000":  ["ATB1000", "ATB2000", "ATV2010", "ATV2015", "AT1045", "AT1050"],
    "ATi2000": ["ATB1000", "ATB2000", "ATV2010", "ATV2015",
                "ATCV2030", "ATCHA1035", "AT1045", "AT1050"],
}


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
NAVY = colors.HexColor("#0c182b")
STEEL = colors.HexColor("#4b5d7a")
LIGHT = colors.HexColor("#dde5f0")
PAPER = colors.HexColor("#f7f9fc")
GREEN = colors.HexColor("#22a06b")


def _draw_dim_line(c, x0, y0, x1, y1, label, *, side="bottom"):
    """Tiny ASME-style dimension line with two ticks + centered text."""
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.4)
    c.line(x0, y0, x1, y1)
    tick = 1.6 * mm
    if abs(y0 - y1) < 0.01:   # horizontal dim
        c.line(x0, y0 - tick / 2, x0, y0 + tick / 2)
        c.line(x1, y0 - tick / 2, x1, y0 + tick / 2)
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(NAVY)
        cx = (x0 + x1) / 2
        if side == "bottom":
            c.drawCentredString(cx, y0 - 3 * mm, label)
        else:
            c.drawCentredString(cx, y0 + 1.5 * mm, label)
        c.setFillColor(colors.black)
    else:                     # vertical dim
        c.line(x0 - tick / 2, y0, x0 + tick / 2, y0)
        c.line(x0 - tick / 2, y1, x0 + tick / 2, y1)
        cy = (y0 + y1) / 2
        c.saveState()
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(NAVY)
        c.translate(x0 - 3.5 * mm, cy)
        c.rotate(90)
        c.drawCentredString(0, 0, label)
        c.restoreState()
        c.setFillColor(colors.black)


def _draw_schematic_hollow_box(c, x, y, w, h, *, category):
    """Draw the simplified inner geometry of an extrusion based on category."""
    # outer shell
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.2)
    c.setFillColor(colors.white)
    c.rect(x, y, w, h, stroke=True, fill=True)

    # inner wall (offset = 2 mm — represents the 2 mm aluminum wall)
    wall = 1.5
    if min(w, h) > 2 * wall + 0.5:
        c.setStrokeColor(STEEL)
        c.setLineWidth(0.45)
        c.setFillColor(PAPER)
        c.rect(x + wall, y + wall, w - 2 * wall, h - 2 * wall,
               stroke=True, fill=True)

    if category in ("head", "base", "jamb"):
        # glazing groove — small notch on the inner side (left in the card)
        groove_w = min(7, w * 0.18)
        groove_h = min(4, h * 0.35)
        gx = x + w / 2 - groove_w / 2
        gy = y + h - wall - groove_h
        c.setFillColor(LIGHT)
        c.setStrokeColor(STEEL)
        c.setLineWidth(0.35)
        c.rect(gx, gy, groove_w, groove_h, stroke=True, fill=True)
        # screw boss in the middle
        if w > 20 and h > 20:
            c.setStrokeColor(NAVY)
            c.setLineWidth(0.6)
            c.circle(x + w / 2, y + h / 2, min(w, h) * 0.10, stroke=True, fill=False)
    elif category == "moulure":
        # solid little bead
        c.setFillColor(LIGHT)
        c.rect(x + 0.5, y + 0.5, w - 1, h - 1, stroke=False, fill=True)
    elif category == "cladding":
        # outer "L" shape — thinner top and sides
        c.setFillColor(STEEL)
        c.rect(x, y + h - 1.0, w, 1.0, stroke=False, fill=True)
        c.setFillColor(NAVY)
        c.setLineWidth(0.4)


def draw_profile_card(c, key, *, x, y, w, h):
    """Draw one profile cross-section card filling (x, y, w, h).

    Layout:
      ┌─────────────────────────────────────┐
      │  LABEL                              │
      │  AT code · Hydro · Série            │
      │     ┌─────── cross-section ───────┐ │
      │     │                             │ │
      │     │                             │ │
      │     └─────── width (mm) ──────────┘ │
      │  note / usage                       │
      └─────────────────────────────────────┘
    """
    p = PROFILES.get(key)
    if not p:
        return

    # ─── Card frame ──────────────────────────────────────────────
    c.setStrokeColor(LIGHT)
    c.setLineWidth(0.5)
    c.setFillColor(colors.white)
    c.rect(x, y, w, h, stroke=True, fill=True)

    # ─── Title block ─────────────────────────────────────────────
    c.setFillColor(NAVY)
    c.rect(x, y + h - 8 * mm, w, 8 * mm, stroke=False, fill=True)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 3 * mm, y + h - 4.4 * mm, p["label"][:40])
    c.setFont("Helvetica", 6.5)
    sub = f"{p['at_code']}  /  Hydro {p['hydro']}  /  {p['series']}"
    c.drawString(x + 3 * mm, y + h - 7 * mm, sub[:54])
    c.setFillColor(colors.black)

    # ─── Cross-section area ─────────────────────────────────────
    inner_top = y + h - 9 * mm
    inner_bot = y + 11 * mm   # room for bottom dim + note line
    inner_left = x + 8 * mm
    inner_right = x + w - 8 * mm
    inner_w = inner_right - inner_left
    inner_h = inner_top - inner_bot

    face_w = p["face_w"]
    face_h = p["face_h"]

    # Real dimensions in mm. Convert to canvas mm via reportlab.mm constant.
    # Find a scale that fits the face inside the inner area, leaving 30% room
    # for clarity (a 13 mm moulure on its own would be tiny, so we cap min).
    scale_w = (inner_w * 0.85) / (face_w * mm)
    scale_h = (inner_h * 0.65) / (face_h * mm)
    scale = min(scale_w, scale_h)
    # Cap scale so very small profiles still look readable
    scale = min(scale, 1.4)
    draw_w = face_w * mm * scale
    draw_h = face_h * mm * scale
    cx = (inner_left + inner_right) / 2
    cy = (inner_bot + inner_top) / 2 + 1 * mm  # slight upward offset for dims
    bx = cx - draw_w / 2
    by = cy - draw_h / 2

    _draw_schematic_hollow_box(c, bx, by, draw_w, draw_h, category=p["category"])

    # ─── Dimension lines (width below, depth on the right) ─────
    _draw_dim_line(c, bx, by - 4 * mm, bx + draw_w, by - 4 * mm,
                   f"{face_w:.2f} mm")
    _draw_dim_line(c, bx + draw_w + 4 * mm, by,
                   bx + draw_w + 4 * mm, by + draw_h,
                   f"{face_h:.2f} mm")

    # ─── Note line ──────────────────────────────────────────────
    c.setFont("Helvetica", 6.8)
    c.setFillColor(STEEL)
    note = p.get("note", "")
    c.drawString(x + 3 * mm, y + 3 * mm, note[:70])
    c.setFillColor(colors.black)


def profiles_for_order(order: dict) -> list[str]:
    """Return the unique profile keys needed by an AT door order, ordered
    by category (head → base → jamb → moulure → cladding) for a stable
    page layout."""
    keys: list[str] = []
    seen: set[str] = set()
    # Determine which moulure based on glazing
    needs_simple = False
    needs_thermo = False
    series_used: set[str] = set()
    for d in (order.get("doors") or []):
        s = d.get("series") or "AT1000"
        series_used.add(s)
        g = d.get("glazing") or "unknown"
        if g == "simple":
            needs_simple = True
        elif g == "thermos":
            needs_thermo = True
        else:
            # unknown → include both so the shop can choose
            needs_simple = True
            needs_thermo = True

    for s in series_used:
        for k in SERIES_PROFILES.get(s, []):
            if k == "AT1045" and not needs_simple:
                continue
            if k == "AT1050" and not needs_thermo:
                continue
            if k not in seen:
                seen.add(k)
                keys.append(k)

    # Stable category order
    order_idx = {"head": 0, "base": 1, "jamb": 2, "cladding": 3, "moulure": 4}
    keys.sort(key=lambda k: order_idx.get(PROFILES[k]["category"], 9))
    return keys
