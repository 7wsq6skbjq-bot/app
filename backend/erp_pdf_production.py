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
from reportlab.lib.pagesizes import LETTER, TABLOID, landscape
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
    "tagline": "Quincaillerie et portes commerciales en aluminium",
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

W, H = landscape(TABLOID)         # 1224 x 792 pt (11x17)

# Default aluminium profile per element for each series (codes from
# at_profile_library.PROFILES — the single source of truth for dimensions).
SERIES_DEFAULT_PROFILES = {
    "AT1000":  {"head": "ATT1005", "base": "ATB1000", "hinge": "ATV1025", "lock": "ATV1015", "lock_inactive": "ATV1010"},
    "ATi1000": {"head": "ATT1005", "base": "ATB1000", "hinge": "ATV1025", "lock": "ATV1015", "lock_inactive": "ATV1010"},
    "AT2000":  {"head": "ATB1000", "base": "ATB2000", "hinge": "ATV2010", "lock": "ATV2015", "lock_inactive": "ATV2010"},
    "ATi2000": {"head": "ATB1000", "base": "ATB2000", "hinge": "ATV2010", "lock": "ATV2015", "lock_inactive": "ATV2010"},
}

# Cadre (frame) — largeur de profilé visible (pouces) par type. Dessiné à
# l'échelle autour de l'ouverture UNIQUEMENT lorsqu'un type est sélectionné.
FRAME_FACE_IN = {
    "tube_fin": 1.75,        # Tube à fin
    "flush_non_iso": 1.75,   # Flush glazed non isolé
    "flush_iso": 2.0,        # Flush glazed isolé (isolé)
    "adapteur": 0.9375,      # Adapteur (15/16")
}
FRAME_LABELS = {
    "tube_fin": "Tube à fin",
    "flush_non_iso": "Flush glazed non isolé",
    "flush_iso": "Flush glazed isolé",
    "adapteur": "Adapteur",
}


def _door_profiles(door):
    """Resolve the element profile codes for a door (selection or default)."""
    series = door.get("series") or "AT1000"
    d = SERIES_DEFAULT_PROFILES.get(series, SERIES_DEFAULT_PROFILES["AT1000"])
    return {
        "head": door.get("profile_head") or d["head"],
        "base": door.get("profile_base") or d["base"],
        "hinge": door.get("profile_hinge_stile") or d["hinge"],
        "lock": door.get("profile_lock_stile") or d["lock"],
        "lock_inactive": door.get("profile_lock_stile_inactive") or d["lock_inactive"],
    }


def _face_in(code, fallback=2.0):
    """Visible face width of a profile, in inches (from the catalog)."""
    p = AL_PROFILES.get(code)
    return (p["face_w"] / 25.4) if p else fallback


# ── glass + parclose (moulure) sizing — reuse the Cut-List calculation ──
def _glass_thickness_mm(door) -> float:
    """Detect glass thickness. Explicit glass_type wins; else insulated series
    or thermos text -> 25.4, otherwise 6 mm."""
    gt = (door.get("glass_type") or "").lower()
    if gt == "tht":
        return 25.4
    if gt == "6mm":
        return 6.0
    s = (door.get("series") or "").upper().replace(" ", "")
    if s.startswith("ATI"):
        return 25.4
    g = (door.get("glass") or "").lower()
    if "thermo" in g or "25" in g or '1"' in g or "1 po" in g or "1po" in g:
        return 25.4
    return 6.0


# Opening (rough) -> finished-leaf offsets (mm), per series — same values the
# Cut-List / AT-order conversion uses (profile_catalog.SYSTEMS.offsets_mm).
OPENING_TO_LEAF_OFFSET_MM = {
    "AT1000":  {"width": 115.1, "height": 22.2},
    "ATI1000": {"width": 115.1, "height": 22.2},
    "AT2000":  {"width": 191.3, "height": 22.2},
    "ATI2000": {"width": 191.3, "height": 22.2},
}


def _leaf_offset(series):
    s = (series or "AT1000").upper().replace(" ", "").replace("_", "")
    if s.startswith("ATI2000"):
        return OPENING_TO_LEAF_OFFSET_MM["ATI2000"]
    if s.startswith("ATI1000"):
        return OPENING_TO_LEAF_OFFSET_MM["ATI1000"]
    if s.startswith("AT2000"):
        return OPENING_TO_LEAF_OFFSET_MM["AT2000"]
    return OPENING_TO_LEAF_OFFSET_MM["AT1000"]


# Déductions de vitrage (thermos) — bible A.T. Fabrication (mm).
# ws = déduction largeur porte simple ; wp = déduction largeur totale d'une paire
# (répartie ensuite entre les 2 battants) ; h = déduction hauteur.
GLASS_DEDUCT_MM = {
    "AT1000":  {"ws": 122.2, "wp": 244.4, "h": 185.7},
    "ATI1000": {"ws": 122.2, "wp": 244.4, "h": 185.7},
    "AT2000":  {"ws": 198.4, "wp": 396.8, "h": 303.2},
    "ATI2000": {"ws": 198.4, "wp": 396.8, "h": 303.2},
}
# Lousse agrandi de 2 mm en largeur : le thermos est 2 mm moins large PAR porte
# (portes simples ET chaque battant des paires).
GLASS_WIDTH_LOUSSE_MM = 2.0


def _glass_deduct(series):
    s = (series or "AT1000").upper().replace(" ", "").replace("_", "")
    if s.startswith("ATI2000"):
        return GLASS_DEDUCT_MM["ATI2000"]
    if s.startswith("ATI1000"):
        return GLASS_DEDUCT_MM["ATI1000"]
    if s.startswith("AT2000"):
        return GLASS_DEDUCT_MM["AT2000"]
    return GLASS_DEDUCT_MM["AT1000"]


def _glass_dims_bible(series, opening_w_in, opening_h_in, is_pair, leaf_frac=0.5):
    """Dimensions RÉELLES du thermos (mm) selon la bible A.T. + lousse -2 mm.
    Retourne (hauteur_mm, largeur_mm). Pour une paire, largeur PAR battant."""
    d = _glass_deduct(series)
    ow = float(opening_w_in) * 25.4
    oh = float(opening_h_in) * 25.4
    h = oh - d["h"]
    if is_pair:
        total_w = ow - d["wp"]                       # largeur vitrage totale (2 battants)
        w = total_w * float(leaf_frac) - GLASS_WIDTH_LOUSSE_MM
    else:
        w = ow - d["ws"] - GLASS_WIDTH_LOUSSE_MM
    return max(h, 0), max(w, 0)



def _glass_moulure(door, leaf_w_mm: float, leaf_h_mm: float):
    """Return glass H/W + parclose V/H lengths (mm) using the SAME formula as
    the Cut-List module. `leaf_w_mm`/`leaf_h_mm` must already be the FINISHED
    leaf dimensions (opening minus the per-series offset)."""
    try:
        from cut_door_breakdown import decompose_at_door
        gt = _glass_thickness_mm(door)
        bd = decompose_at_door(
            max(float(leaf_w_mm), 1), max(float(leaf_h_mm), 1),
            series=door.get("series") or "AT1000",
            glass_thickness_mm=gt, qty=1)
        glass = mv = mh = None
        for it in bd.items:
            lbl = (it.get("label") or "").lower()
            if it.get("item_type") == "glass":
                glass = it
            elif "parclose verticale" in lbl:
                mv = it
            elif "parclose horizontale" in lbl:
                mh = it
        return {
            "gh": (glass or {}).get("length_mm", 0),
            "gw": (glass or {}).get("width_mm", 0),
            "mv": (mv or {}).get("length_mm", 0),
            "mh": (mh or {}).get("length_mm", 0),
            "pn": (mv or {}).get("part_number") or "",
            "gt": gt,
        }
    except Exception:
        return None


# ── drawn-hardware symbols (vector) ────────────────────────────────
def _draw_lever(c, x, y, facing=1):
    """Adams Rite style lever handle on a small escutcheon plate.
    x = stile centre, y = lever centre height, facing +1 = arm toward glass."""
    pw, ph = 8, 30
    c.saveState()
    c.setFillColor(colors.HexColor("#39414f"))
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.roundRect(x - pw / 2, y - ph / 2, pw, ph, 2, fill=1, stroke=1)
    c.setFillColor(colors.white)
    c.circle(x, y + ph / 2 - 4, 1.1, fill=1, stroke=0)
    c.circle(x, y - ph / 2 + 4, 1.1, fill=1, stroke=0)
    # horizontal lever arm (tapered)
    c.setStrokeColor(colors.HexColor("#1c2330"))
    c.setLineCap(1)
    c.setLineWidth(3.6)
    c.line(x, y, x + facing * 15, y)
    c.setLineWidth(2.2)
    c.line(x + facing * 7, y, x + facing * 15, y)
    c.restoreState()


def _draw_paddle(c, x0, x1, y, hidden=False):
    """Push paddle (palette de relâche) — a push pad on a mounting chassis.
    `hidden` draws it as a dashed hidden line (behind-the-door, reverse hands)."""
    w = min(max((x1 - x0) * 0.55, 26), 80)
    cx = (x0 + x1) / 2
    c.saveState()
    c.setStrokeColor(LINE)
    if hidden:
        c.setDash(2, 2)
        c.setLineWidth(0.8)
        c.setFillColor(colors.white)
        c.roundRect(x0, y - 6, x1 - x0, 12, 2, fill=0, stroke=1)   # chassis
        c.roundRect(cx - w / 2, y - 4, w, 8, 3.5, fill=0, stroke=1)  # paddle
    else:
        c.setLineWidth(0.9)
        c.setFillColor(colors.HexColor("#b9c2cf"))
        c.roundRect(x0, y - 6, x1 - x0, 12, 2, fill=1, stroke=1)   # chassis rail
        c.setFillColor(colors.HexColor("#8b98ab"))
        c.roundRect(cx - w / 2, y - 4.5, w, 9, 3.5, fill=1, stroke=1)  # paddle pad
    c.restoreState()
    return w


def _draw_protection_plate(c, cyl_x, meeting_x, y, ph_pts, toward):
    """KROME protection plate. The cylinder hole sits over the ACTIVE leaf
    cylinder (cyl_x); the body extends `toward` (+1/-1) across the meeting so it
    rides ONTO the inactive leaf / frame (never split 50/50 on the meeting)."""
    ph = max(ph_pts, 46)
    top = y + ph * 0.30
    bot = y - ph * 0.60
    overlap = 15                       # how far it rides onto the inactive/frame
    active_end = cyl_x - toward * 5     # just beyond the cylinder on the active side
    far_end = meeting_x + toward * overlap
    left = min(active_end, far_end)
    right = max(active_end, far_end)
    width = max(right - left, 12)
    c.saveState()
    c.setFillColor(colors.HexColor("#cdd4dd"))
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.roundRect(left, bot, width, top - bot, 2.5, fill=1, stroke=1)
    # cylinder hole (upper area, over the active-leaf cylinder)
    c.setFillColor(colors.white)
    c.circle(cyl_x, y + ph * 0.14, 2.6, fill=1, stroke=1)
    # screw holes
    c.setFillColor(colors.HexColor("#8a97a8"))
    for yy in (top - 3, (y + bot) / 2, bot + 3):
        c.circle(left + 3, yy, 0.8, fill=1, stroke=0)
        c.circle(right - 3, yy, 0.8, fill=1, stroke=0)
    c.restoreState()


def _draw_flush_bolt(c, x, y):
    """Flush bolt (verrou affleuré) faceplate + thumb-turn on the inactive leaf."""
    c.saveState()
    c.setFillColor(colors.HexColor("#5a6678"))
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.roundRect(x - 2.6, y - 10, 5.2, 20, 1.4, fill=1, stroke=1)
    c.setFillColor(colors.white)
    c.circle(x, y, 1.3, fill=1, stroke=0)
    c.restoreState()


def _draw_closer(c, hinge_x, y, facing=1):
    """Surface door closer — body box near the top of the leaf (hinge side) with
    an articulated arm reaching toward the leaf centre. facing +1 = arm to right."""
    bw, bh = 22, 9
    left = hinge_x if facing > 0 else hinge_x - bw
    c.saveState()
    c.setFillColor(colors.HexColor("#3a4658"))
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.roundRect(left, y - bh / 2, bw, bh, 1.5, fill=1, stroke=1)     # closer body
    c.setFillColor(colors.HexColor("#8a97a8"))
    c.circle(left + (bw if facing > 0 else 0), y, 1.6, fill=1, stroke=1)  # arm pivot
    # articulated arm
    c.setStrokeColor(colors.HexColor("#1c2330"))
    c.setLineWidth(2)
    c.setLineCap(1)
    ax = left + bw if facing > 0 else left
    c.line(ax, y, ax + facing * 15, y + 6)
    c.line(ax + facing * 15, y + 6, ax + facing * 24, y + 1)
    c.restoreState()


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


def _dual_mm(mm_val) -> str:
    """Return 'mm [inch]' from a millimetre value."""
    try:
        mm_val = float(mm_val)
    except (TypeError, ValueError):
        return "—"
    return f'{mm_val:.1f} [{_inch_fmt(mm_val / 25.4)}]'


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
    anon = bool(plan.get("anonymous"))
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, H - 48, W, 48, fill=1, stroke=0)
    if not anon:
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
    tx = 54 if anon else 230
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(tx, H - 24, doc_title.upper())
    mention = (plan.get("mention") or "").strip()
    if mention:
        c.setFillColor(colors.HexColor("#ffd27f"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(tx, H - 37, mention.upper())
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
    anon = bool(plan.get("anonymous"))
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, 0, W, 26, fill=1, stroke=0)
    if not anon:
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
    anon = bool(plan.get("anonymous"))
    # full-bleed faded storefront + blueprint grid background
    if os.path.exists(COVER_BG):
        try:
            c.drawImage(COVER_BG, 0, 0, width=W, height=H, mask="auto")
        except Exception:
            pass
    # top navy band
    c.setFillColor(NAVY)
    c.rect(0, H - 96, W, 96, fill=1, stroke=0)
    if not anon:
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
    mention = (plan.get("mention") or "").strip()
    if mention:
        c.setFont("Helvetica-Bold", 11)
        tw = c.stringWidth(mention.upper(), "Helvetica-Bold", 11)
        c.setFillColor(RED)
        c.rect(40, H - 132, tw + 16, 18, fill=0, stroke=1)
        c.drawString(48, H - 128, mention.upper())

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
    if not anon:
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
            c.drawCentredString(gx + gw / 2, gy + gh - 10, glass_label[:12])
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
    ax0, ay0, ax1, ay1 = 40, 46, int(W * 0.56), H - 78
    _handing0 = (door.get("handing") or "MD").upper()
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
    lock_inactive_pt = _face_in(prof.get("lock_inactive"), 2.0) * scale

    # frame around the opening — drawn to scale (head + 2 jambs, aluminium)
    # ONLY when a frame type is selected. Otherwise a thin contour is kept.
    frame_type = (door.get("frame_type") or "").strip()
    frame_face_in = FRAME_FACE_IN.get(frame_type)
    if frame_face_in:
        fo = frame_face_in * scale
        c.setFillColor(ALU)
        c.setStrokeColor(LINE)
        c.setLineWidth(1.1)
        c.rect(ox - fo, oy + dh, dw + 2 * fo, fo, fill=1, stroke=1)   # head (linteau)
        c.rect(ox - fo, oy, fo, dh, fill=1, stroke=1)                 # left jamb (jambage)
        c.rect(ox + dw, oy, fo, dh, fill=1, stroke=1)                 # right jamb (jambage)
        # mitre lines in the corners for a picture-frame look
        c.setLineWidth(0.5)
        c.line(ox - fo, oy + dh, ox, oy + dh + 0)
        c.line(ox - fo, oy + dh + fo, ox, oy + dh)
        c.line(ox + dw + fo, oy + dh + fo, ox + dw, oy + dh)
    else:
        fo = 6
        c.setFillColor(colors.white)
        c.setStrokeColor(LINE)
        c.setLineWidth(1.4)
        c.rect(ox - fo, oy - fo, dw + 2 * fo, dh + fo, fill=1, stroke=1)

    if is_pair:
        gap = 3

        def _lw(k):
            try:
                return float(door.get(k) or 0)
            except (TypeError, ValueError):
                return 0.0
        active = door.get("active_leaf") or "right"
        aw_in, iw_in = _lw("leaf_active_width_in"), _lw("leaf_inactive_width_in")
        # auto-complete the missing leaf from the opening when only one is given
        if aw_in > 0 and iw_in <= 0:
            iw_in = max(rw - aw_in, 0)
        elif iw_in > 0 and aw_in <= 0:
            aw_in = max(rw - iw_in, 0)
        # map active/inactive role -> physical left/right leaf
        if active == "right":
            leaf_R_in, leaf_L_in = aw_in, iw_in
        else:
            leaf_L_in, leaf_R_in = aw_in, iw_in
        if leaf_L_in > 0 and leaf_R_in > 0:
            frac_L = leaf_L_in / (leaf_L_in + leaf_R_in)
        else:
            frac_L = 0.5
            leaf_L_in = leaf_R_in = rw / 2
        pair_lwL = (dw - gap) * frac_L
        pair_lwR = (dw - gap) - pair_lwL
        pair_meet = ox + pair_lwL + gap / 2
        left_lock = lock_pt if active == "left" else lock_inactive_pt
        right_lock = lock_pt if active == "right" else lock_inactive_pt
        # left leaf: hinge (outer/left) + lock (inner/right)
        _draw_leaf(c, ox, oy, pair_lwL, dh, glass_label, spec["insulated"],
                   hinge_pt, left_lock, head_pt, base_pt)
        # right leaf: lock (inner/left) + hinge (outer/right)
        _draw_leaf(c, ox + pair_lwL + gap, oy, pair_lwR, dh, glass_label, spec["insulated"],
                   right_lock, hinge_pt, head_pt, base_pt)
        hinge_xs = [(ox, "L"), (ox + pair_lwL + gap + pair_lwR, "R")]
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
    no_hw = bool(door.get("no_hardware"))
    show_handle = (not no_hw) and door.get("show_handle", True)
    show_lock = (not no_hw) and door.get("show_lock", True)

    gap = 3
    handing = (door.get("handing") or "MD").upper()
    active = door.get("active_leaf") or "right"
    hidden_push = handing in ("MGR", "MDR")   # reverse hands → push trim behind door

    def _leaf_geom(role):
        """Geometry for the leaf a given item sits on (role 'active'|'inactive').
        Returns (x0, x1, meet_x, cyl_x, toward); toward points from the meeting/
        strike edge outward (onto the other leaf / frame)."""
        if is_pair:
            side = active if role == "active" else ("left" if active == "right" else "right")
            if side == "left":
                return ox, ox + pair_lwL, pair_meet - gap / 2, pair_meet - gap / 2 - 1.125 * scale, 1
            return ox + pair_lwL + gap, ox + dw, pair_meet + gap / 2, pair_meet + gap / 2 + 1.125 * scale, -1
        hl = handing in ("MD", "MGR")   # hinge left ⇒ strike right
        if hl:
            return ox, ox + dw, ox + dw, ox + dw - 1.125 * scale, 1
        return ox, ox + dw, ox, ox + 1.125 * scale, -1

    def _dim_cols(x0, x1, cyl):
        lc = (x0 + x1) / 2
        d = 1 if lc >= cyl else -1
        return (max(x0 + 6, min(x1 - 6, cyl + d * 22)),
                max(x0 + 6, min(x1 - 6, cyl + d * 44)))

    def _roles(v):
        """Which leaves to draw an item on. 'both' → active + inactive (pairs
        only); a simple door always has a single leaf."""
        if not is_pair:
            return ["active"]
        return ["active", "inactive"] if (v or "active") == "both" else [(v or "active")]

    if show_handle and handle_h > 0:
        hy0 = oy + handle_h * scale
        lpt = max(handle_len * scale, 10)
        hy1 = hy0 + lpt
        h_roles = _roles(door.get("handle_leaf") or "active")
        if is_pair and door.get("handle_both") and h_roles == ["active"]:
            h_roles = ["active", "inactive"]
        first = True
        for role in h_roles:
            hx0, hx1, _hm, hcyl, _tw = _leaf_geom(role)
            if is_pair:
                lc = (ox + pair_lwL / 2) if hcyl < pair_meet else (ox + pair_lwL + gap + pair_lwR / 2)
            else:
                lc = ox + dw / 2
            off = 8 if lc >= hcyl else -8              # grip curves toward the glass
            c.setStrokeColor(NAVY)
            c.setFillColor(NAVY)
            c.setLineWidth(4)
            c.line(hcyl + off, hy0, hcyl + off, hy1)          # grip
            c.setLineWidth(2.4)
            c.line(hcyl, hy0, hcyl + off, hy0)                # stand-offs
            c.line(hcyl, hy1, hcyl + off, hy1)
            c.circle(hcyl, hy0, 2.6, fill=1, stroke=0)
            c.circle(hcyl, hy1, 2.6, fill=1, stroke=0)
            if first:
                hdcol1, _ = _dim_cols(hx0, hx1, hcyl)
                _dim_v(c, oy, hy0, hdcol1, f"{_dual(handle_h)}")
                _dim_v(c, hy0, hy1, hdcol1, f"{_dual(handle_len)}")
                first = False

    if show_lock and lock_h > 0:
        ly = oy + lock_h * scale
        first = True
        for role in _roles(door.get("lock_leaf") or "active"):
            lx0, lx1, _lm, lcyl, _tw = _leaf_geom(role)
            c.setFillColor(NAVY)
            c.rect(lcyl - 3, ly - 5, 6, 10, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.circle(lcyl, ly, 1.6, fill=1, stroke=0)
            if first:
                _, ldcol2 = _dim_cols(lx0, lx1, lcyl)
                _dim_v(c, oy, ly, ldcol2, f"{_dual(lock_h)}")
                first = False

    # Adams Rite lever
    if (not no_hw) and door.get("lever"):
        lv_h = _num("lever_height_in", 40.0)
        lvy = oy + lv_h * scale
        first = True
        for role in _roles(door.get("lever_leaf") or "active"):
            vx0, vx1, _vm, vcyl, _tw = _leaf_geom(role)
            facing = 1 if (vx0 + vx1) / 2 >= vcyl else -1
            _draw_lever(c, vcyl, lvy, facing)
            if first:
                vdcol1, _ = _dim_cols(vx0, vx1, vcyl)
                _dim_v(c, oy, lvy, vdcol1, f"{_dual(lv_h)}")
                first = False

    # KROME protection plate (protège-pêne) — DRAWN LATER so it sits on top of
    # the astragal. See the deferred block after the astragal below.

    # push paddle (palette de relâche) — chosen leaf; hidden line for reverse hands
    if (not no_hw) and door.get("push_paddle"):
        pd_h = _num("paddle_height_in", 40.0)
        pdy = oy + pd_h * scale
        first = True
        for role in _roles(door.get("paddle_leaf") or "active"):
            qx0, qx1, _qm, qcyl, _tw = _leaf_geom(role)
            s0 = qx0 + max(hinge_pt, 8) + 3
            s1 = qx1 - max(hinge_pt, 8) - 3
            if s1 - s0 > 12:
                _draw_paddle(c, s0, s1, pdy, hidden_push)
                if first:
                    qdcol1, _ = _dim_cols(qx0, qx1, qcyl)
                    _dim_v(c, oy, pdy, qdcol1, f"{_dual(pd_h)}")
                    first = False

    # flush bolts (verrou affleuré) — TOUJOURS sur le vantail INACTIF (jamais actif)
    if (not no_hw) and door.get("flush_bolt") and is_pair:
        for role in ["inactive"]:
            _, _, fmeet, _, ftoward = _leaf_geom(role)
            fb_x = fmeet + ftoward * (lock_inactive_pt * 0.5)
            _draw_flush_bolt(c, fb_x, oy + dh - 14)
            _draw_flush_bolt(c, fb_x, oy + 14)

    # door closer (ferme-porte) — top of the chosen leaf(s), hinge side, arm inward
    if (not no_hw) and door.get("door_closer"):
        for role in _roles(door.get("closer_leaf") or "active"):
            cx0, cx1, cmeet, _cc, _tw = _leaf_geom(role)
            if abs(cmeet - cx1) < abs(cmeet - cx0):
                hinge_x, cfacing = cx0, 1
            else:
                hinge_x, cfacing = cx1, -1
            hinge_x = hinge_x + cfacing * (hinge_pt + 2)
            _draw_closer(c, hinge_x, oy + dh - head_pt - 10, cfacing)

    # astragal (astragale) — vertical meeting-gap cover on a pair
    if (not no_hw) and door.get("astragal") and is_pair:
        c.saveState()
        c.setFillColor(colors.HexColor("#9aa7b8"))
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.rect(pair_meet - 2.5, oy, 5, dh, fill=1, stroke=1)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Oblique", 5)
        c.translate(pair_meet + 5, oy + dh * 0.72)
        c.rotate(90)
        c.drawString(0, 0, "Astragale")
        c.restoreState()

    # KROME protection plate (protège-pêne) — drawn AFTER the astragal so it sits
    # ON TOP, and scaled to 75 % (was too bulky).
    if (not no_hw) and door.get("protection_plate"):
        pl_h = _num("plate_height_in", 40.0)
        ply = oy + pl_h * scale
        first = True
        for role in _roles(door.get("plate_leaf") or "active"):
            px0, px1, pmeet, pcyl, ptoward = _leaf_geom(role)
            _draw_protection_plate(c, pcyl, pmeet, ply, max(dh * 0.14, 46) * 0.75, ptoward)
            if first:
                _, pdcol2 = _dim_cols(px0, px1, pcyl)
                _dim_v(c, oy, ply, pdcol2, f"{_dual(pl_h)}")
                first = False

    # panic bar (barre anti-panique) — chosen leaf(s), edge to edge (touches both
    # sides of the leaf); hidden line for reverse hands (MGR/MDR)
    if (not no_hw) and door.get("panic_bar"):
        ph = _num("panic_height_in", 40.0)
        py = oy + ph * scale

        def _panic_seg(bx0, bx1, hidden):
            if bx1 - bx0 <= 12:
                return
            c.saveState()
            c.setStrokeColor(NAVY)
            if hidden:
                c.setDash(2, 2)
                c.setFillColor(colors.white)
                c.setLineWidth(0.8)
                c.rect(bx0, py - 3, bx1 - bx0, 6, fill=0, stroke=1)
                c.rect(bx0, py - 5, 5, 10, fill=0, stroke=1)
                c.rect(bx1 - 5, py - 5, 5, 10, fill=0, stroke=1)
            else:
                c.setFillColor(colors.HexColor("#7f8fa6"))
                c.setLineWidth(1)
                c.rect(bx0, py - 3, bx1 - bx0, 6, fill=1, stroke=1)
                c.setFillColor(NAVY)
                c.rect(bx0, py - 5, 5, 10, fill=1, stroke=0)
                c.rect(bx1 - 5, py - 5, 5, 10, fill=1, stroke=0)
            c.restoreState()

        first = True
        for role in _roles(door.get("panic_leaf") or "active"):
            nx0, nx1, _nm, ncyl, _tw = _leaf_geom(role)
            _panic_seg(nx0, nx1, hidden_push)
            if first:
                _, ndcol2 = _dim_cols(nx0, nx1, ncyl)
                _dim_v(c, oy, py, ndcol2, f"{_dual(ph)}")
                first = False

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
    # detail bubbles (only when the corresponding detail pages are included)
    if plan.get("include_plan_details", True):
        _bubble(c, ox - fo - 8, oy + dh * 0.5, "01", "300")
        _bubble(c, ox + dw + fo + 8, oy + dh * 0.5, "02", "300")
    if plan.get("include_section_details", True):
        _bubble(c, ox + dw / 2, oy + dh + fo + 12, "01", "400")

    # dimensions — per-leaf width (pairs), opening width (top), height (left)
    if is_pair:
        _dim_h(c, ox, ox + pair_lwL, oy + dh + 9, _dual(leaf_L_in), ext_from=oy + dh)
        _dim_h(c, ox + pair_lwL + gap, ox + pair_lwL + gap + pair_lwR,
               oy + dh + 9, _dual(leaf_R_in), ext_from=oy + dh)
        _dim_h(c, ox, ox + dw, oy + dh + 27,
               f"{_dual(rw)} Ouverture libre", ext_from=oy + dh + 9)
    else:
        _dim_h(c, ox, ox + dw, oy + dh + 22,
               f"{_dual(rw)} Ouverture libre", ext_from=oy + dh)
    _dim_v(c, oy, oy + dh, ox - fo - 26,
           f"{_dual(rh)} Ouverture libre", ext_from=ox - fo)

    # fabrication dimensions ("Fab.") = finished leaf = opening − per-series offset
    def _fnum(v, dflt=0.0):
        try:
            return float(v if v not in (None, "") else dflt)
        except (TypeError, ValueError):
            return dflt

    fab_auto = plan.get("fab_auto", True)
    allow = _fnum(plan.get("fab_allowance_in"), 0.0)
    _foff = _leaf_offset(series)
    # Une paire déduit l'offset largeur PAR BATTANT (2×), comme la bible verre
    # (wp = 2×ws). Sinon chaque battant sortirait ~57 mm trop large.
    _foff_w = _foff["width"] * (2 if is_pair else 1)
    fw = _fnum(door.get("fab_width_in"), 0.0)
    fh = _fnum(door.get("fab_height_in"), 0.0)
    if fw <= 0 and fab_auto:
        fw = rw - _foff_w / 25.4 + allow
    if fh <= 0 and fab_auto:
        fh = rh - _foff["height"] / 25.4 + allow
    if fw > 0:
        _dim_h(c, ox - 8, ox + dw + 8, oy + dh + 40, f"{_dual(fw)} Fab.")
    if fh > 0:
        _dim_v(c, oy - 8, oy + dh + 8, ox - fo - 46, f"{_dual(fh)} Fab.")

    # tag label under drawing
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString((ox + dw / 2), oy - 20, f"Élévation {tag}")

    # Grosse note "VUE INTÉRIEUR" sur l'élévation (portes MD / MG seulement)
    if _handing0 in ("MD", "MG"):
        c.saveState()
        nw, nh = 156, 26
        ncx = ox + dw / 2
        ny = oy + dh - nh - 14
        c.setFillColor(colors.white)
        c.setStrokeColor(NAVY)
        c.setLineWidth(1.3)
        c.roundRect(ncx - nw / 2, ny, nw, nh, 5, fill=1, stroke=1)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(ncx, ny + 8, "VUE INTÉRIEUR")
        c.restoreState()

    # ── right column : specs + hardware ──
    rx, rw_col = ax1 + 18, W - (ax1 + 18) - 22
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
    if frame_face_in:
        ry = _spec_block(c, rx, ry, rw_col, "Cadre (entrée complète)", [
            ("Type", FRAME_LABELS.get(frame_type, frame_type)),
            ("Profilé", f'{_inch_fmt(frame_face_in)} ({frame_face_in * 25.4:.1f} mm)'),
        ], tint=colors.HexColor("#f6efdc"))

    # Verre & moulures — same calculation as the Cut-List module. Convert the
    # OPENING into the FINISHED-LEAF dimensions with the per-series offsets first.
    _off = _leaf_offset(series)
    _leaf_h_mm = max(rh * 25.4 - _off["height"], 1)
    if is_pair:
        # Chaque battant = (sa portion d'ouverture en po × 25.4) − offset largeur.
        # Modèle par-battant (et non un offset total réparti au prorata) : un
        # battant actif de 36" donne toujours 36×25.4 − 115.1 = 799.30 mm,
        # peu importe la largeur du battant inactif.
        _awi = aw_in if aw_in > 0 else rw / 2
        _iwi = iw_in if iw_in > 0 else rw / 2
        _wa = max(_awi * 25.4 - _off["width"], 1)
        _wi = max(_iwi * 25.4 - _off["width"], 1)
        _fa = _awi / (_awi + _iwi) if (_awi + _iwi) else 0.5
        _gmA = _glass_moulure(door, _wa, _leaf_h_mm)
        _gmI = _glass_moulure(door, _wi, _leaf_h_mm)
        if _gmA and _gmI:
            _ghA, _gwA = _glass_dims_bible(series, rw, rh, True, _fa if _fa > 0 else 0.5)
            _ghI, _gwI = _glass_dims_bible(series, rw, rh, True, (1 - _fa) if _fa > 0 else 0.5)
            _warn = "  ⚠" if (_gmA['mh'] <= _gwA or _gmA['mv'] >= _ghA) else ""
            ry = _spec_block(c, rx, ry, rw_col, "Verre & moulures" + _warn, [
                ("Verre actif", f"{_ghA:.0f} × {_gwA:.0f} mm"),
                ("Verre inact.", f"{_ghI:.0f} × {_gwI:.0f} mm"),
                ("Jambage V (long.)", _dual_mm(_gmA['mv'])),
                ("Horiz. actif (long.)", _dual_mm(_gmA['mh'])),
                ("Horiz. inact. (long.)", _dual_mm(_gmI['mh'])),
                ("Parclose", f"{_gmA['pn'] or '—'} · verre {_gmA['gt']:.0f} mm"),
            ], tint=colors.HexColor("#eef7ee"))
    else:
        _leaf_w_mm = max(rw * 25.4 - _off["width"], 1)
        _gm = _glass_moulure(door, _leaf_w_mm, _leaf_h_mm)
        if _gm:
            _gh, _gw = _glass_dims_bible(series, rw, rh, False)
            _warn = "  ⚠" if (_gm['mh'] <= _gw or _gm['mv'] >= _gh) else ""
            ry = _spec_block(c, rx, ry, rw_col, "Verre & moulures" + _warn, [
                ("Verre (H×L)", f"{_gh:.0f} × {_gw:.0f} mm"),
                ("Jambage V (long.)", _dual_mm(_gm['mv'])),
                ("Horiz. h/b (long.)", _dual_mm(_gm['mh'])),
                ("Parclose", f"{_gm['pn'] or '—'} · verre {_gm['gt']:.0f} mm"),
            ], tint=colors.HexColor("#eef7ee"))
    if door.get("hinges"):
        ry = _spec_block(c, rx, ry, rw_col, "Charnières / Pentures", [
            ("Détail", door.get("hinges") or "—"),
        ])
    _installer = plan.get("installer") or ("—" if plan.get("anonymous") else "Portech")
    ry = _hardware_table(c, rx, ry, rw_col, door.get("hardware") or [],
                         plan.get("machining_by") or "A.T. Fabrication",
                         _installer)

    # optional internal cost total — shown only when enabled AND a price exists
    # (never print "0.00 $" when nothing was entered)
    if plan.get("show_costs"):
        total = 0.0
        has_price = False
        for hw in (door.get("hardware") or []):
            try:
                q = float(str(hw.get("qty") or "1").replace(",", "."))
            except (TypeError, ValueError):
                q = 1.0
            try:
                up = float(hw.get("unit_price") or 0)
            except (TypeError, ValueError):
                up = 0.0
            if up > 0:
                has_price = True
            total += q * up
        if has_price and total > 0:
            ch = 14
            c.setFillColor(colors.HexColor("#fff3cf"))
            c.rect(rx, ry - ch, rw_col, ch, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor("#e0b34d"))
            c.rect(rx, ry - ch, rw_col, ch, fill=0, stroke=1)
            c.setFillColor(colors.HexColor("#8a5a00"))
            c.setFont("Helvetica-Bold", 7)
            c.drawString(rx + 5, ry - 10, "COÛT QUINCAILLERIE (interne)")
            c.drawRightString(rx + rw_col - 5, ry - 10, f"{total:,.2f} $".replace(",", " "))
            ry = ry - ch - 8

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
# Reference CAD sheets (client A.T. Fabrication drawings) rasterised per
# combination of série × config × vitrage, embedded under the Portech
# header/footer. The correct sheet is auto-selected for EACH door, and an
# orientation panel (INT/EXT + hinge side) is stamped per the door's handing.
DETAIL_DIR = "/app/backend/assets/production_details"
REF_DIR = os.path.join(DETAIL_DIR, "ref")
ANCHOR_MAP = {"AT": "ancrage_ati.png", "ATi": "ancrage_ati.png"}


def _series_key(series):
    return (series or "AT1000").upper().replace(" ", "").replace("_", "")


def _glz_key(door):
    """'6' or '25' from the door glazing thickness."""
    return "25" if _glass_thickness_mm(door) >= 20 else "6"


def _resolve_detail_image(kind, door, mirrored=False):
    """Best-matching reference PNG for a door, or None. Falls back on glazing
    when an exact sheet is missing (ex. porte isolée commandée avec verre
    6 mm → feuille ATi 25 mm, correcte pour la série / bris thermique).
    When `mirrored` is set (single door, left hand) the horizontally-flipped
    variant (charnières à droite) is preferred."""
    s = _series_key(door.get("series")).lower()  # at1000 / ati1000 / at2000 / ati2000
    glz = _glz_key(door)
    config = "pair" if door.get("config") == "pair" else "simple"
    other = "simple" if config == "pair" else "pair"
    if kind == "plan":
        hand = (door.get("handing") or "MD").lower()
        cands = []
        if config == "simple":
            cands += [f"plan_{s}_simple_{glz}_{hand}",
                      f"plan_{s}_simple_25_{hand}",
                      f"plan_{s}_simple_6_{hand}"]
        cands += [f"plan_{s}_{config}_{glz}", f"plan_{s}_{config}_25",
                  f"plan_{s}_{config}_6", f"plan_{s}_{other}_{glz}",
                  f"plan_{s}_{other}_25"]
    else:  # coupe sheets are not split by config
        cands = [f"coupe_{s}_{glz}", f"coupe_{s}_25", f"coupe_{s}_6"]
    for name in cands:
        if mirrored:
            pm = os.path.join(REF_DIR, name + "_mg.png")
            if os.path.exists(pm):
                return pm
        p = os.path.join(REF_DIR, name + ".png")
        if os.path.exists(p):
            return p
    return None


def _embed_detail(c, path, box):
    """Draw a detail image centered inside box=(x0,y0,x1,y1), keep aspect.
    Returns the placement (dx, dy, dw, dh) or None."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    try:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(path)
        iw, ih = img.getSize()
    except Exception:
        return None
    scale = min(bw / iw, bh / ih)
    dw, dh = iw * scale, ih * scale
    dx = x0 + (bw - dw) / 2
    dy = y0 + (bh - dh) / 2
    try:
        c.drawImage(path, dx, dy, width=dw, height=dh,
                    preserveAspectRatio=True, mask="auto")
        return (dx, dy, dw, dh)
    except Exception:
        return None


def _mask_ref_titleblock(c, place, style="kovo"):
    """Cover the reference sheet's embedded title block(s) with white, redraw a
    clean frame flush to the image edges (encadré pleine largeur) and return the
    bottom-right box (bx, by, cw, ch) where our own cartouche replaces the
    drawing's. style='kovo' masks the two KOVO blocks (bottom-right project +
    top-right series). style='simple' masks only the single bottom-right block
    of the per-hand plan sheets (which keep their top title)."""
    dx, dy, dw, dh = place
    c.saveState()
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.white)
    if style == "simple":
        # couvre le bloc cartouche + la petite case « Par d'autres » au-dessus
        c.rect(dx + dw * 0.810, dy + dh * 0.010, dw * 0.188, dh * 0.560,
               fill=1, stroke=1)
        box = (dx + dw * 0.824, dy + dh * 0.026, dw * 0.168, dh * 0.418)
    else:
        # bottom-right project title block
        c.rect(dx + dw * 0.820, dy + dh * 0.004, dw * 0.178, dh * 0.470,
               fill=1, stroke=1)
        # top-right 'SERIES … DOOR DETAILS' block
        c.rect(dx + dw * 0.728, dy + dh * 0.790, dw * 0.270, dh * 0.206,
               fill=1, stroke=1)
        box = (dx + dw * 0.826, dy + dh * 0.014, dw * 0.167, dh * 0.440)
    # redraw a clean frame flush to the image edges
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setLineWidth(2.2)
    c.rect(dx + dw * 0.006, dy + dh * 0.010, dw * 0.988, dh * 0.980,
           fill=0, stroke=1)
    c.restoreState()
    return box


def _date_fr_short(iso) -> str:
    _abbr = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juill.",
             "août", "sept.", "oct.", "nov.", "déc."]
    try:
        d = datetime.strptime(str(iso)[:10], "%Y-%m-%d")
        return f"{d.day} {_abbr[d.month - 1]} {d.year}"
    except Exception:
        return _date_fr(iso)


def _prod_banner(c, plan, bx=None, by=None):
    """Red PRODUCTION banner. Defaults to the page's top-right corner; a custom
    (bx, by) is used to drop it over the drawing's masked top-right block."""
    bw, bh = 182, 22
    if bx is None:
        bx = (W - 24) - bw
    if by is None:
        by = H - 72
    c.saveState()
    c.setFillColor(RED)
    c.rect(bx, by, bw, bh, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(bx + bw / 2, by + 7,
                        f"PRODUCTION   ·   {_date_fr_short(plan.get('date'))}")
    c.restoreState()


def _detail_frame(c, footer):
    """Thin black rounded page border + a discreet footer line (Maupas style)."""
    c.saveState()
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.3)
    c.roundRect(18, 28, W - 36, H - 52, 8, fill=0, stroke=1)
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7)
    c.drawString(22, 15, footer)
    c.restoreState()


def _draw_cartouche(c, plan, desc, page_code, repere=None, box=None):
    """Portech title block (Maupas style). When `box`=(bx,by,cw,ch) is given the
    block is laid out to fill that box (used to replace the reference drawing's
    own title block). In anonymous mode the PORTECH header band is omitted."""
    anon = bool(plan.get("anonymous"))
    rows = [
        ("CLIENT", plan.get("client_name") or "—"),
        ("DATE", _date_fr(plan.get("date"))),
        ("STATUT", "POUR PRODUCTION"),
        ("PROJET", plan.get("project_name") or "—"),
        ("# PROJET", str(plan.get("project_number") or "—")),
        ("DESCRIPTION", desc),
        ("REPÈRE", repere or "—"),
    ]
    n = len(rows)
    if box:
        bx, by, cw, ch = box
    else:
        cw = 150
        bx = (W - 24) - cw
        by = 46
        ch = (0 if anon else 34) + 29 * n + 32
    H_PAGE = max(28, min(42, ch * 0.13))
    H_HDR = 0 if anon else max(28, min(40, ch * 0.13))
    H_ROW = (ch - H_HDR - H_PAGE) / n
    top = by + ch
    lab_sz = 5.6 if H_ROW < 26 else 6.6
    val_sz = 8.0 if H_ROW < 26 else 9.5

    def fit(t, font, size, mw):
        t = str(t)
        while c.stringWidth(t, font, size) > mw and len(t) > 2:
            t = t[:-2]
        return t

    c.saveState()
    c.setFillColor(colors.white)
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.1)
    c.rect(bx, by, cw, ch, fill=1, stroke=1)

    # header (hidden in anonymous mode)
    y = top - H_HDR
    if not anon:
        c.setFillColor(NAVY)
        c.rect(bx, y, cw, H_HDR, fill=1, stroke=0)
        ms = min(22, H_HDR - 12)
        if os.path.exists(MARK_WHITE):
            try:
                c.drawImage(MARK_WHITE, bx + 7, y + (H_HDR - ms) / 2,
                            width=ms, height=ms, mask="auto")
            except Exception:
                pass
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(bx + 9 + ms + 4, y + H_HDR / 2 - 1, "PORTECH")
        c.setFont("Helvetica", 5.8)
        c.setFillColor(colors.HexColor("#9bb6d8"))
        c.drawString(bx + 9 + ms + 4, y + H_HDR / 2 - 11, "Portes et quincaillerie")

    # labelled rows
    CREAM = colors.HexColor("#f4f1e6")
    for i, (lab, val) in enumerate(rows):
        y -= H_ROW
        c.setFillColor(CREAM if i % 2 == 0 else colors.white)
        c.rect(bx, y, cw, H_ROW, fill=1, stroke=0)
        c.setStrokeColor(NAVY_BORDER)
        c.setLineWidth(0.5)
        c.line(bx, y + H_ROW, bx + cw, y + H_ROW)
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica", lab_sz)
        c.drawString(bx + 8, y + H_ROW - lab_sz - 4, lab)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", val_sz)
        c.drawString(bx + 8, y + 5, fit(val, "Helvetica-Bold", val_sz, cw - 16))

    # page band
    y -= H_PAGE
    c.setFillColor(NAVY)
    c.rect(bx, y, cw, H_PAGE, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#9bb6d8"))
    c.setFont("Helvetica", 6.5)
    c.drawString(bx + 8, y + H_PAGE - 12, "PAGE")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", min(28, H_PAGE * 0.72))
    c.drawRightString(bx + cw - 10, y + 7, str(page_code))
    c.restoreState()


def _detail_page_for_door(c, plan, door, kind, page_no):
    tag = door.get("tag") or f"P-{page_no:02d}"
    series = door.get("series") or "AT1000"
    is_pair = door.get("config") == "pair"
    config = "paire" if is_pair else "simple"
    iso = "isolée" if _series_key(series).startswith("ATI") else "non isolée"
    handing = (door.get("handing") or "MD").upper()
    swing = "intérieur" if handing in ("MD", "MG") else "extérieur"
    glz = "25,4 mm" if _glz_key(door) == "25" else "6,35 mm"
    label = "Détail en plan" if kind == "plan" else "Détail en coupe"
    code = str((300 if kind == "plan" else 400) + (page_no - 1))
    real = "plan réel" if kind == "plan" else "coupe réelle"
    footer = (f"{tag}  ·  {config}  ·  {series} {iso}  ·  vitrage {glz}  ·  "
              f"Main {handing} (ouvrant {swing})  ·  {real}")

    _handing0 = handing  # already uppercased above

    path = _resolve_detail_image(kind, door, mirrored=False)
    # Dessin spécifique à la main (nouvelle banque de plans) ? -> cartouche simple
    # et pas de note « Miroité » (le dessin est déjà dans le bon sens).
    hand_specific = bool(path) and os.path.splitext(os.path.basename(path))[0] \
        .rsplit("_", 1)[-1] in ("md", "mg", "mdr", "mgr")
    # Dessin en PLEINE LARGEUR : l'encadré du dessin occupe presque toute la page.
    place = _embed_detail(c, path, (24, 26, W - 24, H - 20)) if path else None
    if not place:
        c.setFillColor(RED)
        c.setFont("Helvetica", 9)
        c.drawCentredString(W / 2, H / 2,
                            "Détail indisponible pour ce type de porte.")
        cart_box = None
    else:
        # Masque le cartouche intégré du dessin et renvoie la zone où dessiner le nôtre.
        cart_box = _mask_ref_titleblock(c, place,
                                        style="simple" if hand_specific else "kovo")

    # Bandeau rouge PRODUCTION (haut à droite, dans la zone libérée)
    if place:
        dx, dy, dw, dh = place
        if hand_specific:
            _prod_banner(c, plan, dx + dw * 0.992 - 182, dy + dh * 0.935)
        else:
            _prod_banner(c, plan, dx + dw * 0.952 - 182, dy + dh * 0.905)
    else:
        _prod_banner(c, plan)

    # Note « Miroité et renversé » : seulement si le dessin n'est PAS spécifique à
    # la main (ancien gabarit MD unique), vue en plan, portes MD/MG.
    if place and kind == "plan" and not hand_specific and _handing0 in ("MD", "MG"):
        dx, dy, dw, dh = place
        nw, nh = 170, 24
        nx = dx + dw / 2 - nw / 2
        ny = dy + dh - nh - 10
        c.saveState()
        c.setFillColor(colors.white)
        c.setStrokeColor(RED)
        c.setLineWidth(1.1)
        c.roundRect(nx, ny, nw, nh, 4, fill=1, stroke=1)
        c.setFillColor(RED)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawCentredString(nx + nw / 2, ny + 8.5, "Miroité et renversé")
        c.restoreState()

    # Notre cartouche, placé à la place du cartouche d'origine du dessin
    _draw_cartouche(c, plan, label, code, tag, box=cart_box)

    # Pied de page discret sous le dessin
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7)
    c.drawString(22, 11, footer)
    c.showPage()


def _anchor_page(c, plan, page_no):
    doors = plan.get("doors") or []
    primary = (doors[0].get("series") if doors else "AT1000") or "AT1000"
    fam = "ATi" if _series_key(primary).startswith("ATI") else "AT"
    path = os.path.join(DETAIL_DIR, ANCHOR_MAP[fam])
    footer = (f"Détail d'ancrage standard  ·  série {primary}"
              if plan.get("anonymous")
              else f"Détail d'ancrage standard Portech  ·  série {primary}")
    _prod_banner(c, plan)
    # drawing reserves a generous right band so the cartouche never covers it
    place = _embed_detail(c, path, (28, 56, W - 250, H - 64))
    if not place:
        c.setFillColor(RED)
        c.setFont("Helvetica", 9)
        c.drawCentredString((W - 180) / 2, H / 2, "Détail indisponible.")
    _draw_cartouche(c, plan, "Détail d'ancrage", "500", primary)
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7)
    c.drawString(22, 11, footer)
    c.showPage()


# ── public entry point ─────────────────────────────────────────────
def render_production_plan_pdf(plan: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas_mod.Canvas(buf, pagesize=landscape(TABLOID))
    title = (f"Dessins de production {plan.get('plan_number') or ''}"
             if plan.get("anonymous")
             else f"Portech — Dessins de production {plan.get('plan_number') or ''}")
    c.setTitle(title)

    _cover(c, plan)

    doors = plan.get("doors") or []
    if not doors:
        doors = [{}]
    for i, door in enumerate(doors, start=1):
        _elevation_page(c, plan, door, i)

    if plan.get("include_plan_details", True):
        for i, door in enumerate(doors, start=1):
            _detail_page_for_door(c, plan, door, "plan", i)
    if plan.get("include_section_details", True):
        for i, door in enumerate(doors, start=1):
            _detail_page_for_door(c, plan, door, "section", i)
    if plan.get("include_anchors", True):
        _anchor_page(c, plan, 500)

    c.save()
    buf.seek(0)
    return buf.read()
