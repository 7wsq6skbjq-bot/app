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

from at_profile_library import PROFILES as AL_PROFILES

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
        "title": "Porte non-isolée série AT1000 de A.T. Fabrication",
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
        "title": "Porte isolée série ATi1000 p+ de A.T. Fabrication",
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
        "title": "Porte non-isolée série AT2000 de A.T. Fabrication",
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
        "title": "Porte isolée série ATi2000 de A.T. Fabrication",
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

# Default aluminium profile per element for each series (codes from
# at_profile_library.PROFILES — the single source of truth for dimensions).
SERIES_DEFAULT_PROFILES = {
    "AT1000":  {"head": "ATT1005", "base": "ATB1000", "hinge": "ATV1010", "lock": "ATV1015"},
    "ATi1000": {"head": "ATT1005", "base": "ATB1000", "hinge": "ATV1010", "lock": "ATV1015"},
    "AT2000":  {"head": "ATB1000", "base": "ATB2000", "hinge": "ATV2010", "lock": "ATV2015"},
    "ATi2000": {"head": "ATB1000", "base": "ATB2000", "hinge": "ATV2010", "lock": "ATV2015"},
}


def _door_profiles(door):
    """Resolve the 4 element profile codes for a door (selection or default)."""
    series = door.get("series") or "AT1000"
    d = SERIES_DEFAULT_PROFILES.get(series, SERIES_DEFAULT_PROFILES["AT1000"])
    return {
        "head": door.get("profile_head") or d["head"],
        "base": door.get("profile_base") or d["base"],
        "hinge": door.get("profile_hinge_stile") or d["hinge"],
        "lock": door.get("profile_lock_stile") or d["lock"],
    }


def _face_in(code, fallback=2.0):
    """Visible face width of a profile, in inches (from the catalog)."""
    p = AL_PROFILES.get(code)
    return (p["face_w"] / 25.4) if p else fallback


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
    # PRODUCTION box on the right — only when a production name/note is set
    if plan.get("production_name") or plan.get("production_note"):
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

    # PRODUCTION box — only when a production name/note is set
    if plan.get("production_name") or plan.get("production_note"):
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

    # big project title (drawn after the client box so it can wrap clear of it)
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 11)
    c.drawString(40, H - 150, "DESSINS POUR PRODUCTION")

    # CLIENT block (right) — sized to its content
    name = plan.get("client_name") or "—"
    extra = [str(l) for l in (plan.get("client_address"), plan.get("client_contact"),
                              plan.get("client_phone")) if l]
    widths = [c.stringWidth(name, "Helvetica-Bold", 13)]
    widths += [c.stringWidth(l, "Helvetica", 9) for l in extra]
    box_w = max(150, min(262, max(widths) + 22))
    box_h = 42 + len(extra) * 13 + 6
    cx = (W - 38) - box_w
    cy = H - 150
    c.setFillColor(BG_LIGHT)
    c.rect(cx, cy - box_h, box_w, box_h, fill=1, stroke=0)
    c.setStrokeColor(NAVY_BORDER)
    c.rect(cx, cy - box_h, box_w, box_h, fill=0, stroke=1)
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(cx + 10, cy - 15, "CLIENT")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(cx + 10, cy - 33, name)
    c.setFont("Helvetica", 9)
    yy = cy - 48
    for l in extra:
        c.drawString(cx + 10, yy, l)
        yy -= 13

    # project title — wraps downward, kept clear of the client box
    max_title_w = cx - 40 - 16
    size = 34

    def _wrap(txt, sz):
        out, cur = [], ""
        for wd in txt.split():
            trial = (cur + " " + wd).strip()
            if not cur or c.stringWidth(trial, "Helvetica-Bold", sz) <= max_title_w:
                cur = trial
            else:
                out.append(cur)
                cur = wd
        if cur:
            out.append(cur)
        return out

    title = f"PROJET : {plan.get('project_name') or '—'}"
    lines = _wrap(title, size)
    while len(lines) > 2 and size > 18:
        size -= 2
        lines = _wrap(title, size)
    c.setFillColor(NAVY)
    ty = H - 176
    for ln in lines:
        c.setFont("Helvetica-Bold", size)
        c.drawString(40, ty, ln)
        ty -= size + 4
    c.setFillColor(NAVY_LIGHT)
    c.setFont("Courier", 16)
    c.drawString(40, ty - 4, f"# PROJET : {plan.get('project_number') or '—'}")

    # accent rule
    c.setStrokeColor(RED)
    c.setLineWidth(3)
    c.line(40, ty - 16, 320, ty - 16)

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


def _hardware_table(c, x, y, w, hardware, machining_by="A.T. Fabrication",
                    installer="Portech"):
    """Quincaillerie table with ACTIF / INACT. placement columns."""
    c.setFillColor(NAVY)
    c.rect(x, y - 12, w, 12, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 6.5)
    hdr = (f"QUINCAILLERIE  ·  USINAGE : {machining_by.upper()}"
           f"  ·  INSTALLATION : {installer.upper()}")
    c.drawString(x + 4, y - 8.5, hdr[:82])

    col_qty, col_no = 16, w - 118
    col_act, col_inact = w - 54, w - 24

    # column-label row
    yh = y - 12
    c.setFillColor(NAVY_LIGHT)
    c.rect(x, yh - 9, w, 9, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 5.3)
    c.drawString(x + 3, yh - 6.5, "QTÉ")
    c.drawString(x + col_qty, yh - 6.5, "DESCRIPTION")
    c.drawString(x + col_no, yh - 6.5, "N° PIÈCE")
    c.drawCentredString(x + col_act, yh - 6.5, "ACTIF")
    c.drawCentredString(x + col_inact, yh - 6.5, "INACT.")
    yy = yh - 9

    c.setFont("Helvetica", 6.5)
    if not hardware:
        yy -= 12
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(x + 4, yy + 3.5, "Aucune quincaillerie saisie.")
        c.setStrokeColor(NAVY_BORDER)
        c.rect(x, yy, w, (y - 12) - yy, fill=0, stroke=1)
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
        c.drawString(x + col_qty, yy + 3.5, str(hw.get("description") or "—")[:48])
        c.setFont("Courier", 6)
        c.setFillColor(TEXT_MUTED)
        c.drawString(x + col_no, yy + 3.5, str(hw.get("part_number") or "")[:13])
        for flag, cx in ((hw.get("on_active"), col_act), (hw.get("on_inactive"), col_inact)):
            if flag:
                c.setFillColor(NAVY)
                c.circle(x + cx, yy + 5.5, 2.4, fill=1, stroke=0)
    c.setStrokeColor(NAVY_BORDER)
    c.rect(x, yy, w, (yh - 9) - yy, fill=0, stroke=1)
    return yy - 6


def _draw_leaf(c, x, y, lw, lh, glass_label, insulated,
               left_w, right_w, top_h, bot_h):
    """Draw a single door leaf with real stile/rail widths (in points)."""
    # leaf outline (aluminium)
    c.setFillColor(ALU)
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.rect(x, y, lw, lh, fill=1, stroke=1)
    gx, gy = x + left_w, y + bot_h
    gw, gh = lw - left_w - right_w, lh - bot_h - top_h
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
        c.drawCentredString(x + lw / 2, y + max(6, bot_h * 0.4), "ISOLÉE")


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
                 f"Config. : {'Paire de portes' if door.get('config') == 'pair' else 'Porte simple'}"
                 f"   ·   Main : {(door.get('handing') or 'MD').upper()}")

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

    # real profile widths (points) for stiles/rails
    prof = _door_profiles(door)
    head_pt = _face_in(prof["head"]) * scale
    base_pt = _face_in(prof["base"], 3.875) * scale
    hinge_pt = _face_in(prof["hinge"]) * scale
    lock_pt = _face_in(prof["lock"], 2.125) * scale

    # frame (jamb) drawn slightly outside opening
    fo = 6
    c.setFillColor(colors.white)
    c.setStrokeColor(LINE)
    c.setLineWidth(1.4)
    c.rect(ox - fo, oy - fo, dw + 2 * fo, dh + fo, fill=1, stroke=1)

    if is_pair:
        gap = 3
        leaf_w = (dw - gap) / 2        # left leaf: hinge (outer/left) + lock (inner/right)
        _draw_leaf(c, ox, oy, leaf_w, dh, glass_label, spec["insulated"],
                   hinge_pt, lock_pt, head_pt, base_pt)
        # right leaf: lock (inner/left) + hinge (outer/right)
        _draw_leaf(c, ox + leaf_w + gap, oy, leaf_w, dh, glass_label, spec["insulated"],
                   lock_pt, hinge_pt, head_pt, base_pt)
        hinge_xs = [(ox, "L"), (ox + dw, "R")]
    else:
        # simple door — hinge side follows the handing (sens d'ouverture)
        handing = (door.get("handing") or "MD").upper()
        hinge_left = handing in ("MD", "MGR")
        if hinge_left:
            _draw_leaf(c, ox, oy, dw, dh, glass_label, spec["insulated"],
                       hinge_pt, lock_pt, head_pt, base_pt)
            hinge_xs = [(ox, "L")]
        else:
            _draw_leaf(c, ox, oy, dw, dh, glass_label, spec["insulated"],
                       lock_pt, hinge_pt, head_pt, base_pt)
            hinge_xs = [(ox + dw, "R")]

    # hinges — rendered according to the hinge type
    hinge_type = door.get("hinge_type") or "butt45"
    c.setFillColor(RED)
    if hinge_type == "butt45":
        for hx, _side in hinge_xs:
            for frac in (0.9, 0.55, 0.12):
                hy = oy + dh * frac
                c.rect(hx - 2, hy - 4, 4, 8, fill=1, stroke=0)
    elif hinge_type == "continue":
        inset = 0.125 * scale  # continuous hinge = full leaf height minus 1/4"
        for hx, _side in hinge_xs:
            c.rect(hx - 2, oy + inset, 4, dh - 2 * inset, fill=1, stroke=0)
    # hinge_type == "none" -> no hinge marks

    # ── door hardware on the drawing (pull handle + lock) + undercut ──
    def _num(key, dflt=0.0):
        try:
            return float(door.get(key) if door.get(key) not in (None, "") else dflt)
        except (TypeError, ValueError):
            return dflt

    handle_h = _num("handle_height_in", 34.5)
    handle_len = _num("handle_length_in", 9.0)
    lock_h = _num("lock_height_in", 40.0)
    undercut = _num("undercut_mm", 17.5)

    gap = 3
    if is_pair:
        active = door.get("active_leaf") or "right"
        cxm = ox + dw / 2
        lx_right = cxm + gap / 2 + lock_pt * 0.5
        lx_left = cxm - gap / 2 - lock_pt * 0.5
        lock_x = lx_right if active == "right" else lx_left
        handle_xs = [lx_left, lx_right] if door.get("handle_both") else [lock_x]
    else:
        hl = (door.get("handing") or "MD").upper() in ("MD", "MGR")
        lock_x = (ox + dw - lock_pt * 0.5) if hl else (ox + lock_pt * 0.5)
        handle_xs = [lock_x]
    dim_x = min(lock_x + 22, ox + dw + fo + 4)

    if handle_h > 0:
        hy0 = oy + handle_h * scale               # bottom of the handle (from door bottom)
        lpt = max(handle_len * scale, 10)
        hy1 = hy0 + lpt                            # handle extends upward
        for hxp in handle_xs:
            off = -4 if hxp >= (ox + dw / 2) else 4       # grip toward meeting/edge
            c.setStrokeColor(NAVY)
            c.setFillColor(NAVY)
            c.setLineWidth(2)
            c.line(hxp + off, hy0, hxp + off, hy1)          # grip
            c.setLineWidth(1.2)
            c.line(hxp, hy0, hxp + off, hy0)                # stand-offs
            c.line(hxp, hy1, hxp + off, hy1)
            c.circle(hxp, hy0, 1.6, fill=1, stroke=0)
            c.circle(hxp, hy1, 1.6, fill=1, stroke=0)
        _dim_v(c, oy, hy0, dim_x, f"{_dual(handle_h)}")     # door bottom -> handle bottom
        _dim_v(c, hy0, hy1, dim_x + 16, f"{_dual(handle_len)}")

    if lock_h > 0:
        ly = oy + lock_h * scale
        c.setFillColor(NAVY)
        c.rect(lock_x - 3, ly - 5, 6, 10, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.circle(lock_x, ly, 1.6, fill=1, stroke=0)
        _dim_v(c, oy, ly, dim_x + 32, f"{_dual(lock_h)}")

    # panic bar (barre anti-panique) — horizontal push bar on the active leaf
    if door.get("panic_bar"):
        ph = _num("panic_height_in", 40.0)
        py = oy + ph * scale
        if is_pair:
            lw2 = (dw - gap) / 2
            if (door.get("active_leaf") or "right") == "right":
                ax0, ax1 = ox + lw2 + gap, ox + dw
            else:
                ax0, ax1 = ox, ox + lw2
        else:
            ax0, ax1 = ox, ox + dw
        bx0 = ax0 + max(hinge_pt, 8) + 3
        bx1 = ax1 - max(lock_pt, 8) - 3
        if bx1 - bx0 > 12:
            c.setStrokeColor(NAVY)
            c.setFillColor(colors.HexColor("#7f8fa6"))
            c.setLineWidth(1)
            c.rect(bx0, py - 3, bx1 - bx0, 6, fill=1, stroke=1)      # push pad
            c.setFillColor(NAVY)
            c.rect(bx0, py - 5, 5, 10, fill=1, stroke=0)             # end brackets
            c.rect(bx1 - 5, py - 5, 5, 10, fill=1, stroke=0)
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Oblique", 5.5)
            c.drawCentredString((bx0 + bx1) / 2, py + 6,
                                f"Barre anti-panique · {_dual(ph)}")

    if undercut > 0:
        ucp = (undercut / 25.4) * scale
        yf = oy - ucp
        c.setStrokeColor(LINE)
        c.setLineWidth(0.8)
        c.line(ox - fo, yf, ox + dw + fo, yf)
        for hx in range(int(ox - fo), int(ox + dw + fo), 8):
            c.line(hx, yf, hx - 3, yf - 3)
        _dim_v(c, yf, oy, ox - fo - 26, f"{_dual(undercut / 25.4)}")

    # detail bubbles (jamb + head refs)
    _bubble(c, ox - fo - 8, oy + dh * 0.5, "01", "300")
    _bubble(c, ox + dw + fo + 8, oy + dh * 0.5, "02", "300")
    _bubble(c, ox + dw / 2, oy + dh + fo + 12, "01", "400")

    # dimensions — width (top), height (left)
    _dim_h(c, ox, ox + dw, oy + dh + 22,
           f"{_dual(rw)} Ouverture libre", ext_from=oy + dh)
    _dim_v(c, oy, oy + dh, ox - fo - 26,
           f"{_dual(rh)} Ouverture libre", ext_from=ox - fo)

    # optional fabrication dimensions ("Fab.") — auto = opening + configurable allowance
    def _fnum(v, dflt=0.0):
        try:
            return float(v if v not in (None, "") else dflt)
        except (TypeError, ValueError):
            return dflt

    fab_auto = plan.get("fab_auto", True)
    allow = _fnum(plan.get("fab_allowance_in"), 0.0)
    fw = _fnum(door.get("fab_width_in"), 0.0)
    fh = _fnum(door.get("fab_height_in"), 0.0)
    if fw <= 0 and fab_auto:
        fw = rw + allow
    if fh <= 0 and fab_auto:
        fh = rh + allow
    if fw > 0:
        _dim_h(c, ox - 8, ox + dw + 8, oy + dh + 40, f"{_dual(fw)} Fab.")
    if fh > 0:
        _dim_v(c, oy - 8, oy + dh + 8, ox - fo - 46, f"{_dual(fh)} Fab.")

    # tag label under drawing
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString((ox + dw / 2), oy - 20, f"Élévation {tag}")

    # ── right column : specs + hardware ──
    rx, rw_col = 448, W - 448 - 22
    ry = H - 62

    def _prow(label, code):
        p = AL_PROFILES.get(code)
        if not p:
            return (label, code or "—")
        return (label, f'{code} · {_inch_fmt(p["face_w"] / 25.4)} ({p["face_w"]:.1f} mm)')

    ry = _spec_block(c, rx, ry, rw_col, spec["title"], [
        ("Fini ext.", door.get("finish_ext") or "—"),
        ("Fini int.", door.get("finish_int") or "—"),
        _prow("Tête", prof["head"]),
        _prow("Base", prof["base"]),
        _prow("Mont. charn.", prof["hinge"]),
        _prow("Mont. serrure", prof["lock"]),
        ("Épaisseur", '1 3/4" (44.45 mm)'),
    ])
    if door.get("glass"):
        ry = _spec_block(c, rx, ry, rw_col, "Vitrage (fourni et installé par autres)", [
            ("Type", door.get("glass") or "—"),
        ], tint=colors.HexColor("#eef4ff"))
    if door.get("hinges"):
        ry = _spec_block(c, rx, ry, rw_col, "Charnières / Pentures", [
            ("Détail", door.get("hinges") or "—"),
        ])
    ry = _hardware_table(c, rx, ry, rw_col, door.get("hardware") or [],
                         plan.get("machining_by") or "A.T. Fabrication",
                         plan.get("installer") or "Portech")

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
