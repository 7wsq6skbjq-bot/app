"""
Production drawings generator (Dessins de production).

Given door opening dimensions + hardware, produce a multi-page, landscape,
Portech-branded production-drawing PDF that mimics the AT fabrication layout:

    * Page 1  — Présentation (cover) : logo, PRODUCTION block, project, client, INDEX
    * Page 200 — Élévation (one page per door) : to-scale drawing + specs + hardware table
    * Page 300 — Détails en plan  (standard horizontal cross-sections per series)
    * Page 400 — Détails en coupe (standard vertical sections per series)
    * Page 500 — Ancrages         (standard anchor detail)

Pure reportlab canvas — deterministic vector output, no headless browser.
"""
from __future__ import annotations

import io
import os
from datetime import datetime
from fractions import Fraction

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as canvas_mod

# ── Brand palette (mirrors erp_pdf.py) ─────────────────────────────
NAVY = colors.HexColor("#0c182b")
NAVY_LIGHT = colors.HexColor("#2f4f7f")
NAVY_BORDER = colors.HexColor("#dde5f0")
BG_LIGHT = colors.HexColor("#f3f6fb")
TEXT_MUTED = colors.HexColor("#4b5d7a")
RED = colors.HexColor("#b3261e")
LINE = colors.HexColor("#1b2a44")
GLASS = colors.HexColor("#dbeafe")
ALU = colors.HexColor("#c9d4e3")

MARK_WHITE = "/app/frontend/public/brand/portech-mark-white.png"
LOGO_PATH = "/app/frontend/public/brand/logo-portech.png"

COMPANY = {
    "name": "PORTECH",
    "tagline": "Quincaillerie et porte commerciale",
    "line1": "Grand Montréal, QC",
    "phone": "438-376-4177",
    "email": "info@portech.info",
    "site": "portech.info",
}

# Standard specifications per door series (editable defaults).
SERIES_SPECS = {
    "AT1000": {
        "title": "Porte non-isolée série AT1000 de Portech",
        "insulated": False,
        "rows": [
            ("Tête", "2\" × 4 1/2\""),
            ("Jambage", "2\" × 4 1/2\""),
            ("Base", "2\" × 10\""),
            ("Épaisseur", "1 3/4\""),
            ("Parclose", "Moulure à vitrage simple"),
        ],
    },
    "ATi1000": {
        "title": "Porte isolée série ATi1000 p+ de Portech",
        "insulated": True,
        "rows": [
            ("Tête", "2\" × 4 1/2\""),
            ("Jambage", "2\" × 4 1/2\""),
            ("Base", "2\" × 10\""),
            ("Épaisseur", "2 1/4\" (bris thermique)"),
            ("Parclose", "Moulure thermo"),
        ],
    },
    "AT2000": {
        "title": "Porte non-isolée série AT2000 de Portech",
        "insulated": False,
        "rows": [
            ("Tête", "2 1/2\" × 4 1/2\""),
            ("Jambage", "2 1/2\" × 4 1/2\""),
            ("Base", "2 1/2\" × 10\""),
            ("Épaisseur", "1 3/4\""),
            ("Parclose", "Moulure à vitrage simple"),
        ],
    },
    "ATi2000": {
        "title": "Porte isolée série ATi2000 de Portech",
        "insulated": True,
        "rows": [
            ("Tête", "2 1/2\" × 4 1/2\""),
            ("Jambage", "2 1/2\" × 4 1/2\""),
            ("Base", "2 1/2\" × 10\""),
            ("Épaisseur", "2 1/4\" (bris thermique)"),
            ("Parclose", "Moulure thermo"),
        ],
    },
}

W, H = landscape(LETTER)          # 792 x 612 pt


# ── unit / text helpers ────────────────────────────────────────────
def _inch_fmt(v: float) -> str:
    """Format inches as a mixed fraction (nearest 1/16), e.g. 34.5 -> 34 1/2\"."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    whole = int(v)
    frac = Fraction(round((v - whole) * 16), 16)
    if frac == 0:
        return f'{whole}"'
    if whole == 0:
        return f'{frac.numerator}/{frac.denominator}"'
    return f'{whole} {frac.numerator}/{frac.denominator}"'


def _dual(inches: float) -> str:
    """Return 'mm [inch]' the way AT fabrication drawings label dimensions."""
    try:
        inches = float(inches)
    except (TypeError, ValueError):
        return "—"
    return f'{inches * 25.4:.1f} [{_inch_fmt(inches)}]'


_FR_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
              "août", "septembre", "octobre", "novembre", "décembre"]


def _date_fr(iso) -> str:
    if not iso:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        d = datetime.strptime(str(iso)[:10], "%Y-%m-%d")
        return f"{d.day} {_FR_MONTHS[d.month - 1]} {d.year}"
    except Exception:
        return str(iso)


# ── low-level drawing primitives ───────────────────────────────────
def _arrow(c, x, y, dx, dy, size=4):
    """Small filled arrowhead pointing in (dx,dy) direction (unit-ish)."""
    import math
    ang = math.atan2(dy, dx)
    a1 = ang + math.radians(160)
    a2 = ang - math.radians(160)
    p = c.beginPath()
    p.moveTo(x, y)
    p.lineTo(x + size * math.cos(a1), y + size * math.sin(a1))
    p.lineTo(x + size * math.cos(a2), y + size * math.sin(a2))
    p.close()
    c.setFillColor(LINE)
    c.drawPath(p, fill=1, stroke=0)


def _dim_h(c, x1, x2, y, label, ext_from=None):
    """Horizontal dimension line with arrowheads + centered label above."""
    c.saveState()
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(x1, y, x2, y)
    if ext_from is not None:
        c.setDash(1, 2)
        c.line(x1, ext_from, x1, y)
        c.line(x2, ext_from, x2, y)
        c.setDash()
    _arrow(c, x1, y, 1, 0)
    _arrow(c, x2, y, -1, 0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7)
    c.drawCentredString((x1 + x2) / 2, y + 2.5, label)
    c.restoreState()


def _dim_v(c, y1, y2, x, label, ext_from=None):
    """Vertical dimension line with arrowheads + rotated label."""
    c.saveState()
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(x, y1, x, y2)
    if ext_from is not None:
        c.setDash(1, 2)
        c.line(ext_from, y1, x, y1)
        c.line(ext_from, y2, x, y2)
        c.setDash()
    _arrow(c, x, y1, 0, 1)
    _arrow(c, x, y2, 0, -1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7)
    c.saveState()
    c.translate(x - 2.5, (y1 + y2) / 2)
    c.rotate(90)
    c.drawCentredString(0, 0, label)
    c.restoreState()
    c.restoreState()


def _bubble(c, x, y, num, ref="300", r=6):
    """Detail callout bubble : top half = detail #, bottom half = page ref."""
    c.saveState()
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.setFillColor(colors.white)
    c.circle(x, y, r, stroke=1, fill=1)
    c.setStrokeColor(LINE)
    c.line(x - r, y, x + r, y)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(x, y + 1.4, str(num))
    c.setFont("Helvetica", 5.5)
    c.setFillColor(TEXT_MUTED)
    c.drawCentredString(x, y - 5, str(ref))
    c.restoreState()


# ── page chrome (header / footer bands) ────────────────────────────
def _band_top(c, plan, doc_title):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, H - 48, W, 48, fill=1, stroke=0)
    if os.path.exists(MARK_WHITE):
        try:
            c.drawImage(MARK_WHITE, 14, H - 42, width=34, height=34,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(54, H - 24, "PORTECH")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#9bb6d8"))
    c.drawString(54, H - 36, COMPANY["tagline"])
    # doc title (centered-ish)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(230, H - 30, doc_title.upper())
    # PRODUCTION box on the right
    bx, bw, bh = W - 214, 200, 38
    c.setFillColor(RED)
    c.rect(bx, H - 44, bw, bh, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(bx + 6, H - 16, "PRODUCTION")
    c.setFont("Helvetica", 7)
    c.drawString(bx + 6, H - 26, (plan.get("production_name") or "").upper()[:34])
    c.setFont("Courier", 6.5)
    c.drawString(bx + 6, H - 36,
                 f"{_date_fr(plan.get('date'))}  ·  REV. {plan.get('revision') or 'no00'}")
    c.restoreState()


def _band_bottom(c, plan, page_label):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, 0, W, 26, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 7)
    c.drawString(14, 15,
                 f"{COMPANY['name']}  ·  {COMPANY['line1']}  ·  "
                 f"Tél. {COMPANY['phone']}  ·  {COMPANY['email']}")
    c.setFont("Courier", 6.5)
    c.setFillColor(colors.HexColor("#9bb6d8"))
    proj = plan.get("project_name") or "—"
    num = plan.get("project_number") or "—"
    c.drawCentredString(W / 2 + 60, 15,
                        f"PROJET : {proj}  ·  # {num}")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawRightString(W - 14, 15, page_label)
    c.restoreState()


def _content_border(c):
    c.saveState()
    c.setStrokeColor(NAVY_BORDER)
    c.setLineWidth(0.8)
    c.rect(10, 30, W - 20, H - 80, fill=0, stroke=1)
    c.restoreState()


def _page_frame(c, plan, doc_title, page_label):
    _band_top(c, plan, doc_title)
    _band_bottom(c, plan, page_label)
    _content_border(c)


# ── cover page ─────────────────────────────────────────────────────
COVER_BG = "/app/backend/assets/production_details/cover_bg.png"


def _cover(c, plan):
    # full-bleed faded storefront + blueprint grid background
    if os.path.exists(COVER_BG):
        try:
            c.drawImage(COVER_BG, 0, 0, width=W, height=H, mask="auto")
        except Exception:
            pass
    # top navy band
    c.setFillColor(NAVY)
    c.rect(0, H - 96, W, 96, fill=1, stroke=0)
    if os.path.exists(MARK_WHITE):
        try:
            c.drawImage(MARK_WHITE, 24, H - 78, width=56, height=56,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(92, H - 52, "PORTECH")
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#9bb6d8"))
    c.drawString(94, H - 68, COMPANY["tagline"])
    c.setFont("Courier", 8)
    c.drawString(94, H - 82,
                 f"{COMPANY['line1']}  ·  Tél. {COMPANY['phone']}  ·  {COMPANY['email']}")

    # PRODUCTION box
    bx = W - 250
    c.setFillColor(RED)
    c.rect(bx, H - 78, 224, 52, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(bx + 10, H - 42, "PRODUCTION")
    c.setFont("Helvetica", 9)
    c.drawString(bx + 10, H - 56, (plan.get("production_name") or "—").upper()[:34])
    c.setFont("Courier", 7.5)
    if plan.get("production_note"):
        c.drawString(bx + 10, H - 68, plan["production_note"][:38])

    # big project title
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 11)
    c.drawString(40, H - 150, "DESSINS POUR PRODUCTION")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 34)
    c.drawString(40, H - 200, f"PROJET : {plan.get('project_name') or '—'}"[:46])
    c.setFillColor(NAVY_LIGHT)
    c.setFont("Courier", 16)
    c.drawString(40, H - 228, f"# PROJET : {plan.get('project_number') or '—'}")

    # accent rule
    c.setStrokeColor(RED)
    c.setLineWidth(3)
    c.line(40, H - 240, 320, H - 240)

    # CLIENT block (right)
    cx, cy = W - 300, H - 150
    c.setFillColor(BG_LIGHT)
    c.rect(cx, cy - 96, 262, 92, fill=1, stroke=0)
    c.setStrokeColor(NAVY_BORDER)
    c.rect(cx, cy - 96, 262, 92, fill=0, stroke=1)
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(cx + 10, cy - 16, "CLIENT")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(cx + 10, cy - 34, (plan.get("client_name") or "—")[:34])
    c.setFont("Helvetica", 9)
    yy = cy - 50
    for ln in [plan.get("client_address"), plan.get("client_contact"),
               plan.get("client_phone")]:
        if ln:
            c.drawString(cx + 10, yy, str(ln)[:40])
            yy -= 13

    # INDEX block (bottom right)
    ix, iy = W - 300, 120
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(ix, iy + 6, "INDEX")
    c.setStrokeColor(NAVY_BORDER)
    c.line(ix, iy, ix + 262, iy)
    entries = [("p.200", "Élévations")]
    if plan.get("include_plan_details", True):
        entries.append(("p.300", "Détails en plan"))
    if plan.get("include_section_details", True):
        entries.append(("p.400", "Détails en coupe"))
    if plan.get("include_anchors", True):
        entries.append(("p.500", "Ancrages"))
    c.setFont("Courier", 9)
    yy = iy - 16
    for pg, lbl in entries:
        c.setFillColor(NAVY_LIGHT)
        c.drawString(ix, yy, pg)
        c.setFillColor(NAVY)
        c.drawString(ix + 52, yy, f"= {lbl}")
        yy -= 15

    # footer band
    c.setFillColor(NAVY)
    c.rect(0, 0, W, 26, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(W / 2, 10,
                        f"{COMPANY['name']}  ·  {COMPANY['tagline']}  ·  "
                        f"{COMPANY['email']}  ·  {COMPANY['site']}")
    c.showPage()


# ── elevation page (one door) ──────────────────────────────────────
def _spec_block(c, x, y, w, title, rows, tint=BG_LIGHT):
    """Draws a titled spec block, returns the y after the block."""
    line_h = 11
    height = 16 + line_h * len(rows) + 4
    c.setFillColor(tint)
    c.rect(x, y - height, w, height, fill=1, stroke=0)
    c.setStrokeColor(NAVY_BORDER)
    c.rect(x, y - height, w, height, fill=0, stroke=1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 5, y - 11, title.upper()[:52])
    c.setFont("Helvetica", 7)
    yy = y - 24
    for k, v in rows:
        c.setFillColor(TEXT_MUTED)
        c.drawString(x + 5, yy, f"{k} :")
        c.setFillColor(NAVY)
        c.drawString(x + 62, yy, str(v)[:34])
        yy -= line_h
    return y - height - 8


def _hardware_table(c, x, y, w, hardware):
    """Quincaillerie table. Returns y after the table."""
    c.setFillColor(NAVY)
    c.rect(x, y - 12, w, 12, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x + 4, y - 8.5, "QUINCAILLERIE FOURNIE, MACHINÉE ET INSTALLÉE PAR PORTECH")
    yy = y - 12
    c.setFont("Helvetica", 6.5)
    col_qty, col_no = 16, w - 96
    if not hardware:
        yy -= 12
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(x + 4, yy + 3.5, "Aucune quincaillerie saisie.")
        c.setStrokeColor(NAVY_BORDER)
        c.rect(x, yy, w, 12, fill=0, stroke=1)
        return yy - 6
    for i, hw in enumerate(hardware):
        rh = 12
        yy -= rh
        if i % 2 == 0:
            c.setFillColor(BG_LIGHT)
            c.rect(x, yy, w, rh, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(x + 3, yy + 3.5, str(hw.get("qty") or "1"))
        c.setFont("Helvetica", 6.5)
        desc = str(hw.get("description") or "—")
        c.drawString(x + col_qty, yy + 3.5, desc[:58])
        c.setFont("Courier", 6)
        c.setFillColor(TEXT_MUTED)
        c.drawString(x + col_no, yy + 3.5, str(hw.get("part_number") or "")[:16])
    c.setStrokeColor(NAVY_BORDER)
    c.rect(x, yy, w, (y - 12) - yy, fill=0, stroke=1)
    return yy - 6


def _draw_leaf(c, x, y, lw, lh, glass_label, insulated):
    """Draw a single door leaf with stiles/rails and a glazed area."""
    # leaf outline (aluminium)
    c.setFillColor(ALU)
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.rect(x, y, lw, lh, fill=1, stroke=1)
    # stile / rail thickness in pt (scaled visual, not to exact scale)
    st = max(6, lw * 0.14)
    bottom_rail = max(18, lh * 0.12)
    top_rail = max(8, lh * 0.05)
    gx, gy = x + st, y + bottom_rail
    gw, gh = lw - 2 * st, lh - bottom_rail - top_rail
    if gw > 4 and gh > 4:
        c.setFillColor(GLASS)
        c.rect(gx, gy, gw, gh, fill=1, stroke=1)
        # subtle glass reflection lines
        c.setStrokeColor(colors.white)
        c.setLineWidth(0.6)
        c.line(gx + gw * 0.2, gy, gx + gw * 0.05, gy + gh)
        c.line(gx + gw * 0.5, gy, gx + gw * 0.35, gy + gh)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        if glass_label:
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(gx + gw / 2, gy + gh / 2 - 3, glass_label[:12])
    if insulated:
        c.setFillColor(NAVY_LIGHT)
        c.setFont("Helvetica-Oblique", 5.5)
        c.drawCentredString(x + lw / 2, y + 5, "ISOLÉE")


def _elevation_page(c, plan, door, page_no):
    series = door.get("series") or "AT1000"
    spec = SERIES_SPECS.get(series, SERIES_SPECS["AT1000"])
    tag = door.get("tag") or f"Porte {page_no}"
    _page_frame(c, plan, f"{tag} — Élévation de porte",
                f"200 · {tag}")

    # meta strip under header
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawString(20, H - 62,
                 f"Échelle : {door.get('scale_note') or '1:30'}   ·   "
                 f"Qté : {door.get('qty') or 1}   ·   Série : {series}   ·   "
                 f"Config. : {'Paire de portes' if door.get('config') == 'pair' else 'Porte simple'}")

    # ── drawing area (left) ──
    ax0, ay0, ax1, ay1 = 40, 46, 430, H - 78
    try:
        rw = float(door.get("opening_width_in") or 36)
        rh = float(door.get("opening_height_in") or 84)
    except (TypeError, ValueError):
        rw, rh = 36.0, 84.0
    rw = max(rw, 1)
    rh = max(rh, 1)
    # leave margins for dim lines: top 34, left 46, bottom 30, right 20
    dx0, dx1 = ax0 + 46, ax1 - 20
    dy0, dy1 = ay0 + 30, ay1 - 40
    scale = min((dx1 - dx0) / rw, (dy1 - dy0) / rh)
    dw, dh = rw * scale, rh * scale
    ox = dx0 + ((dx1 - dx0) - dw) / 2
    oy = dy0 + ((dy1 - dy0) - dh) / 2

    is_pair = door.get("config") == "pair"
    glass_label = (door.get("glass") or "").split("·")[0].strip() or ""

    # frame (jamb) drawn slightly outside opening
    fo = 6
    c.setFillColor(colors.white)
    c.setStrokeColor(LINE)
    c.setLineWidth(1.4)
    c.rect(ox - fo, oy - fo, dw + 2 * fo, dh + fo, fill=1, stroke=1)

    if is_pair:
        gap = 3
        leaf_w = (dw - gap) / 2
        _draw_leaf(c, ox, oy, leaf_w, dh, glass_label, spec["insulated"])
        _draw_leaf(c, ox + leaf_w + gap, oy, leaf_w, dh, glass_label, spec["insulated"])
        hinge_xs = [(ox, "L"), (ox + dw, "R")]
    else:
        _draw_leaf(c, ox, oy, dw, dh, glass_label, spec["insulated"])
        hinge_xs = [(ox, "L")]

    # hinges (marks on hinge jamb)
    c.setFillColor(RED)
    for hx, _side in hinge_xs:
        for frac in (0.9, 0.55, 0.12):
            hy = oy + dh * frac
            c.rect(hx - 2, hy - 4, 4, 8, fill=1, stroke=0)

    # detail bubbles (jamb + head refs)
    _bubble(c, ox - fo - 8, oy + dh * 0.5, "01", "300")
    _bubble(c, ox + dw + fo + 8, oy + dh * 0.5, "02", "300")
    _bubble(c, ox + dw / 2, oy + dh + fo + 12, "01", "400")

    # dimensions — width (top), height (left)
    _dim_h(c, ox, ox + dw, oy + dh + 22,
           f"{_dual(rw)} Ouverture libre", ext_from=oy + dh)
    _dim_v(c, oy, oy + dh, ox - fo - 26,
           f"{_dual(rh)} Ouverture libre", ext_from=ox - fo)

    # tag label under drawing
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString((ox + dw / 2), oy - 20, f"Élévation {tag}")

    # ── right column : specs + hardware ──
    rx, rw_col = 448, W - 448 - 22
    ry = H - 62
    ry = _spec_block(c, rx, ry, rw_col, spec["title"], [
        ("Fini ext.", door.get("finish_ext") or "—"),
        ("Fini int.", door.get("finish_int") or "—"),
        *spec["rows"],
    ])
    if door.get("glass"):
        ry = _spec_block(c, rx, ry, rw_col, "Vitrage (fourni et installé par autres)", [
            ("Type", door.get("glass") or "—"),
        ], tint=colors.HexColor("#eef4ff"))
    if door.get("hinges"):
        ry = _spec_block(c, rx, ry, rw_col, "Charnières / Pentures", [
            ("Détail", door.get("hinges") or "—"),
        ])
    ry = _hardware_table(c, rx, ry, rw_col, door.get("hardware") or [])

    if door.get("notes"):
        c.setFillColor(colors.HexColor("#fff7e6"))
        nh = 30
        c.rect(rx, ry - nh, rw_col, nh, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#e0b34d"))
        c.rect(rx, ry - nh, rw_col, nh, fill=0, stroke=1)
        c.setFillColor(colors.HexColor("#8a5a00"))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(rx + 5, ry - 11, "NOTE")
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 6.8)
        txt = str(door["notes"])
        # wrap crudely
        max_chars = 78
        yy = ry - 21
        for i in range(0, len(txt), max_chars):
            c.drawString(rx + 5, yy, txt[i:i + max_chars])
            yy -= 9
    c.showPage()


# ── standard detail pages (plan / section / anchor) ────────────────
# Real, cleaned CAD details extracted from the reference production plans,
# embedded under the Portech header/footer. Mapped per door family.
DETAIL_DIR = "/app/backend/assets/production_details"
DETAIL_MAP = {
    "AT": {"plan": "plan_at.png", "section": "coupe_at.png", "anchor": "ancrage_ati.png"},
    "ATi": {"plan": "plan_ati.png", "section": "coupe_ati.png", "anchor": "ancrage_ati.png"},
}


def _embed_detail(c, path, box):
    """Draw a detail image centered inside box=(x0,y0,x1,y1), keep aspect."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    try:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(path)
        iw, ih = img.getSize()
    except Exception:
        return False
    scale = min(bw / iw, bh / ih)
    dw, dh = iw * scale, ih * scale
    dx = x0 + (bw - dw) / 2
    dy = y0 + (bh - dh) / 2
    try:
        c.drawImage(path, dx, dy, width=dw, height=dh,
                    preserveAspectRatio=True, mask="auto")
        return True
    except Exception:
        return False


def _detail_page(c, plan, kind, page_no):
    titles = {
        "plan": ("Détails en plan", "300"),
        "section": ("Détails en coupe", "400"),
        "anchor": ("Ancrages", "500"),
    }
    label, code = titles[kind]
    _page_frame(c, plan, label, code)

    # pick the primary door family in the project
    doors = plan.get("doors") or []
    primary = (doors[0].get("series") if doors else "AT1000") or "AT1000"
    fam = "ATi" if str(primary).startswith("ATi") else "AT"
    fname = DETAIL_MAP[fam][kind]
    path = os.path.join(DETAIL_DIR, fname)

    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawString(20, H - 60,
                 f"Détail standard Portech — série {primary} · cotes en mm [pouces].")

    ok = _embed_detail(c, path, (20, 38, W - 20, H - 66))
    if not ok:
        c.setFillColor(RED)
        c.setFont("Helvetica", 9)
        c.drawCentredString(W / 2, H / 2, "Détail indisponible.")
    c.showPage()


# ── public entry point ─────────────────────────────────────────────
def render_production_plan_pdf(plan: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas_mod.Canvas(buf, pagesize=landscape(LETTER))
    c.setTitle(f"Portech — Dessins de production {plan.get('plan_number') or ''}")

    _cover(c, plan)

    doors = plan.get("doors") or []
    if not doors:
        doors = [{}]
    for i, door in enumerate(doors, start=1):
        _elevation_page(c, plan, door, i)

    if plan.get("include_plan_details", True):
        _detail_page(c, plan, "plan", 300)
    if plan.get("include_section_details", True):
        _detail_page(c, plan, "section", 400)
    if plan.get("include_anchors", True):
        _detail_page(c, plan, "anchor", 500)

    c.save()
    buf.seek(0)
    return buf.read()
