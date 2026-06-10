"""Shop drawing PDF for AT Fabrication door orders (Phase 1 MVP).

3 pages:
  1. Cover / recap (cartouche + client + project + order summary)
  2. Door elevations — one cell per door line, dimensioned (mm only, per user)
  3. Hardware nomenclature — checklist mirroring the AT order form

Uses ReportLab. Geometry of profiles will be wired in Phase 2 (DXF live render).
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

INCH_MM = 25.4


def _ascii(s):
    if s is None:
        return ""
    return "".join(c if ord(c) < 256 else "?" for c in str(s))


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _series_label(series: str) -> str:
    return {
        "AT1000": "AT1000 (non isolée)",
        "ATi1000": "ATi1000 (isolée)",
        "AT2000": "AT2000 (non isolée renforcée)",
        "ATi2000": "ATi2000 (isolée renforcée)",
    }.get(series, series)


def _hand_label(hand: str) -> str:
    return {
        "GE": "Gauche exterieure", "DE": "Droite exterieure", "PE": "Paire exterieure",
        "GI": "Gauche interieure", "DI": "Droite interieure", "PI": "Paire interieure",
    }.get(hand, hand or "-")


def _glazing_label(g: str) -> str:
    return {"thermos": "Thermos 25.4 mm", "simple": "Verre simple 6 mm"}.get(g, "Non specifie")


def _draw_header_band(c, page_w, page_h, page_title: str, order_number: str | None):
    c.setFillColor(colors.HexColor("#0c182b"))
    c.rect(0, page_h - 22 * mm, page_w, 22 * mm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(15 * mm, page_h - 12 * mm, _ascii(f"PORTECH — {page_title}"))
    c.setFont("Helvetica", 9)
    sub = f"Plan d'atelier — {_today()}"
    if order_number:
        sub += f"   |   Commande {_ascii(order_number)}"
    c.drawString(15 * mm, page_h - 18 * mm, sub)
    c.setFillColor(colors.black)


def _draw_footer_cartouche(c, page_w, order: dict, page_num: int, total: int):
    c.setStrokeColor(colors.HexColor("#0c182b"))
    c.setLineWidth(0.6)
    c.rect(15 * mm, 8 * mm, page_w - 30 * mm, 12 * mm, stroke=True, fill=False)
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#4b5d7a"))
    project = _ascii(order.get("project_name") or "")
    client = _ascii(order.get("client") or "")
    order_no = _ascii(order.get("order_number") or "")
    c.drawString(17 * mm, 15 * mm, f"CLIENT : {client}")
    c.drawString(17 * mm, 11 * mm, f"PROJET : {project}   |   COMMANDE : {order_no}")
    c.drawRightString(page_w - 17 * mm, 15 * mm, f"Date {_today()}")
    c.drawRightString(page_w - 17 * mm, 11 * mm, f"Page {page_num} / {total}")
    c.setFillColor(colors.black)


# ===========================================================================
# Page 1 — Cover / order recap
# ===========================================================================
def _page_cover(c, page_w, page_h, order: dict):
    _draw_header_band(c, page_w, page_h, "Plan d'atelier — Page de garde", order.get("order_number"))
    y = page_h - 35 * mm

    def kv(label, value, x=15 * mm, vx=70 * mm):
        nonlocal y
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#4b5d7a"))
        c.drawString(x, y, _ascii(label))
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(vx, y, _ascii(value or "-"))
        y -= 7 * mm

    # Client block
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#0c182b"))
    c.drawString(15 * mm, y, "Informations client")
    y -= 8 * mm
    c.setStrokeColor(colors.HexColor("#dde5f0"))
    c.line(15 * mm, y + 4 * mm, page_w - 15 * mm, y + 4 * mm)
    kv("CLIENT", order.get("client"))
    kv("RESPONSABLE", order.get("contact"))
    kv("TELEPHONE", order.get("phone"))
    kv("PROJET", order.get("project_name"))
    kv("COMMANDE", order.get("order_number"))
    kv("DATE COMMANDE", order.get("order_date"))
    kv("DATE REQUISE", order.get("required_date"))

    # Finishes
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#0c182b"))
    c.drawString(15 * mm, y, "Finis aluminium")
    y -= 8 * mm
    c.line(15 * mm, y + 4 * mm, page_w - 15 * mm, y + 4 * mm)
    kv("FINI EXTERIEUR", order.get("finish_exterior"))
    kv("CODE COULEUR EXT.", order.get("color_code_exterior"))
    kv("FINI INTERIEUR", order.get("finish_interior"))
    kv("CODE COULEUR INT.", order.get("color_code_interior"))

    # Doors summary
    doors = order.get("doors") or []
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#0c182b"))
    c.drawString(15 * mm, y, f"Resume des portes ({len(doors)} ligne(s))")
    y -= 8 * mm
    c.line(15 * mm, y + 4 * mm, page_w - 15 * mm, y + 4 * mm)

    # table header
    c.setFillColor(colors.HexColor("#f3f6fb"))
    c.rect(15 * mm, y - 2, page_w - 30 * mm, 6 * mm, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#4b5d7a"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(17 * mm, y, "TAG")
    c.drawString(45 * mm, y, "SERIE")
    c.drawString(90 * mm, y, "DIM. (po)")
    c.drawString(125 * mm, y, "DIM. (mm)")
    c.drawString(160 * mm, y, "QTE")
    c.drawString(175 * mm, y, "SENS")
    c.setFillColor(colors.black)
    y -= 6 * mm
    for d in doors:
        c.setFont("Helvetica", 8)
        c.drawString(17 * mm, y, _ascii(d.get("tag") or "-")[:18])
        c.drawString(45 * mm, y, _ascii(_series_label(d.get("series") or "")))
        w_in = d.get("width_in") or 0
        h_in = d.get("height_in") or 0
        c.drawString(90 * mm, y, f"{w_in:g}\" x {h_in:g}\"")
        c.drawString(125 * mm, y, f"{round(w_in * INCH_MM):.0f} x {round(h_in * INCH_MM):.0f}")
        c.drawString(160 * mm, y, str(d.get("qty") or 1))
        c.drawString(175 * mm, y, _ascii(d.get("hand") or "-"))
        y -= 6 * mm
        if y < 30 * mm:
            break


# ===========================================================================
# Page 2 — Door elevations
# ===========================================================================
def _draw_door_elevation(c, x0: float, y0: float, cell_w: float, cell_h: float, door: dict):
    """Draw one cell containing a dimensioned elevation of a door leaf."""
    w_in = float(door.get("width_in") or 36)
    h_in = float(door.get("height_in") or 84)
    w_mm = w_in * INCH_MM
    h_mm = h_in * INCH_MM

    # Reserve room for dimensions + caption
    pad = 8 * mm
    draw_area_w = cell_w - 2 * pad
    draw_area_h = cell_h - 30 * mm   # bottom = caption block (24 mm)
    # Compute scale so the door fits
    scale = min(draw_area_w / w_mm, draw_area_h / h_mm)
    door_w = w_mm * scale
    door_h = h_mm * scale
    # Center within the cell horizontally; align to top vertically
    cx = x0 + cell_w / 2
    door_left = cx - door_w / 2
    door_bottom = y0 + 26 * mm        # leave room above caption
    door_right = door_left + door_w
    door_top = door_bottom + door_h

    # ─── Frame outline (= leaf rectangle) ──
    c.setStrokeColor(colors.HexColor("#0c182b"))
    c.setLineWidth(1.4)
    c.rect(door_left, door_bottom, door_w, door_h, stroke=True, fill=False)

    # ─── Inner glazing area (offset to suggest the stiles/rails) ──
    series = door.get("series") or "AT1000"
    top_rail_mm = 55.5
    if series in ("AT2000", "ATi2000"):
        top_rail_mm = 98.43
        base_rail_mm = 174.625
        hinge_stile_mm = 88.9
        lock_stile_mm = 92.075
    else:
        base_rail_mm = 98.43
        hinge_stile_mm = 50.8
        lock_stile_mm = 53.975

    gl = door_left + lock_stile_mm * scale          # we draw hinge side on right by default
    gr = door_right - hinge_stile_mm * scale
    gb = door_bottom + base_rail_mm * scale
    gt = door_top - top_rail_mm * scale
    if gr > gl and gt > gb:
        c.setStrokeColor(colors.HexColor("#7d9ac2"))
        c.setLineWidth(0.6)
        c.rect(gl, gb, gr - gl, gt - gb, stroke=True, fill=False)
        # diagonal cross to indicate "vitrage"
        c.setStrokeColor(colors.HexColor("#dde5f0"))
        c.setDash(2, 2)
        c.line(gl, gb, gr, gt)
        c.line(gl, gt, gr, gb)
        c.setDash()

    # ─── Width dimension (below the door) ──
    dim_y = door_bottom - 6 * mm
    c.setStrokeColor(colors.HexColor("#0c182b"))
    c.setLineWidth(0.4)
    c.line(door_left, dim_y, door_right, dim_y)
    # extension lines
    c.line(door_left, door_bottom - 2 * mm, door_left, dim_y - 1 * mm)
    c.line(door_right, door_bottom - 2 * mm, door_right, dim_y - 1 * mm)
    # arrows (simple ticks)
    tick = 2 * mm
    c.line(door_left, dim_y - tick / 2, door_left, dim_y + tick / 2)
    c.line(door_right, dim_y - tick / 2, door_right, dim_y + tick / 2)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#0c182b"))
    c.drawCentredString(cx, dim_y - 4 * mm, f"{round(w_mm):.0f} mm")

    # ─── Height dimension (to the right) ──
    dim_x = door_right + 6 * mm
    c.line(dim_x, door_bottom, dim_x, door_top)
    c.line(door_right + 1 * mm, door_bottom, dim_x + 1 * mm, door_bottom)
    c.line(door_right + 1 * mm, door_top, dim_x + 1 * mm, door_top)
    c.line(dim_x - tick / 2, door_bottom, dim_x + tick / 2, door_bottom)
    c.line(dim_x - tick / 2, door_top, dim_x + tick / 2, door_top)
    c.saveState()
    c.translate(dim_x + 4 * mm, (door_bottom + door_top) / 2)
    c.rotate(90)
    c.drawCentredString(0, 0, f"{round(h_mm):.0f} mm")
    c.restoreState()

    # ─── Caption block under the elevation ──
    cap_y = y0 + 4 * mm
    c.setFillColor(colors.HexColor("#f3f6fb"))
    c.rect(x0 + 4 * mm, cap_y - 1 * mm, cell_w - 8 * mm, 18 * mm, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#0c182b"))
    c.setFont("Helvetica-Bold", 9)
    tag = door.get("tag") or "(sans TAG)"
    c.drawString(x0 + 6 * mm, cap_y + 13 * mm, _ascii(f"TAG : {tag}"))
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.black)
    c.drawString(x0 + 6 * mm, cap_y + 9 * mm,
                 _ascii(f"Serie : {_series_label(series)}"))
    c.drawString(x0 + 6 * mm, cap_y + 5 * mm,
                 _ascii(f"Sens : {_hand_label(door.get('hand') or '')}    Qte : {door.get('qty', 1)}"))
    c.drawString(x0 + 6 * mm, cap_y + 1 * mm,
                 _ascii(f"Vitrage : {_glazing_label(door.get('glazing') or '')}"))


def _page_elevations(c, page_w, page_h, order: dict, doors: list[dict]):
    _draw_header_band(c, page_w, page_h, "Elevations des portes", order.get("order_number"))
    # 2-column grid, as many rows as needed (chunk later if > 6 doors)
    cols = 2
    rows = 3
    margin = 15 * mm
    grid_w = page_w - 2 * margin
    grid_h = page_h - 22 * mm - 25 * mm    # under top band + above footer
    cell_w = grid_w / cols
    cell_h = grid_h / rows
    for idx, door in enumerate(doors[:cols * rows]):
        col = idx % cols
        row = idx // cols
        x0 = margin + col * cell_w
        y0 = (page_h - 22 * mm) - (row + 1) * cell_h
        # light cell border
        c.setStrokeColor(colors.HexColor("#dde5f0"))
        c.setLineWidth(0.4)
        c.rect(x0 + 2 * mm, y0 + 2 * mm, cell_w - 4 * mm, cell_h - 4 * mm, stroke=True, fill=False)
        _draw_door_elevation(c, x0, y0, cell_w, cell_h, door)


# ===========================================================================
# Page 3 — Hardware nomenclature (checklist)
# ===========================================================================
HARDWARE_GROUPS = [
    ("Charnieres", [
        ("hinge_4_5x4", "Charniere 4-1/2 x 4 x 0.134"),
        ("hinge_continuous", "Charniere continue"),
        ("hinge_continuous_hd", "Charniere continue HD"),
    ]),
    ("Poignees / Barres", [
        ("pull_9_back_to_back", "Poignees 9\" dos-a-dos"),
        ("pull_9_exterior", "Poignee 9\" exterieure"),
        ("pull_9_interior", "Poignee 9\" interieure"),
        ("push_bar_tubular", "Barre a pousser tubulaire"),
    ]),
    ("Serrures / Securite", [
        ("lock_4510_ar", "Serrure a ressort 4510 AR"),
        ("lock_4590_ar", "Palette de relache 4590 AR"),
        ("lock_sm_1850_ar", "Serrure SM 1850 AR"),
        ("panic_8400_ar", "Barre panique 8400 AR"),
        ("panic_8600_ar", "Barre panique 8600 AR"),
        ("cylinder_exterior", "Barillet exterieur"),
        ("cylinder_interior_manual", "Barillet manuel interieur"),
        ("cylinder_protector", "Protecteur de barillet"),
        ("bolt_protector", "Protege-pene"),
        ("strike_standard", "Gache standard"),
        ("strike_electric", "Gache electrique"),
        ("contact_recessed", "Contact encastre"),
    ]),
    ("Autre quincaillerie", [
        ("astragal", "Astragale"),
        ("flush_bolts", "Verrous affleures"),
        ("door_sweep", "Balai de porte"),
        ("moulding_thermo", "Moulure thermos (AT1050 plate 14.3)"),
        ("moulding_simple", "Moulure verre simple (AT1045 carree 13.48)"),
    ]),
]


def _draw_checkbox(c, x, y, checked: bool):
    c.setStrokeColor(colors.HexColor("#0c182b"))
    c.setLineWidth(0.5)
    side = 3 * mm
    c.rect(x, y, side, side, stroke=True, fill=False)
    if checked:
        c.setStrokeColor(colors.HexColor("#22a06b"))
        c.setLineWidth(1.2)
        c.line(x + 0.5 * mm, y + side / 2,
                x + side / 2, y + 0.5 * mm)
        c.line(x + side / 2, y + 0.5 * mm,
                x + side - 0.4 * mm, y + side - 0.4 * mm)


def _page_hardware(c, page_w, page_h, order: dict):
    _draw_header_band(c, page_w, page_h, "Quincaillerie commandee", order.get("order_number"))
    hardware = order.get("hardware") or {}
    y = page_h - 30 * mm
    for group_title, items in HARDWARE_GROUPS:
        if y < 35 * mm:
            break
        c.setFillColor(colors.HexColor("#0c182b"))
        c.rect(15 * mm, y - 1 * mm, page_w - 30 * mm, 6.5 * mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(17 * mm, y + 1 * mm, _ascii(group_title).upper())
        c.setFillColor(colors.black)
        y -= 9 * mm
        # 2-column layout
        col_x = [18 * mm, page_w / 2 + 2 * mm]
        for idx, (key, label) in enumerate(items):
            col = idx % 2
            x = col_x[col]
            checked = bool(hardware.get(key))
            _draw_checkbox(c, x, y - 0.5 * mm, checked)
            c.setFont("Helvetica" + ("-Bold" if checked else ""), 9)
            c.setFillColor(colors.HexColor("#0c182b") if checked else colors.HexColor("#4b5d7a"))
            c.drawString(x + 5 * mm, y, _ascii(label))
            # Extra info for hinge qty
            if key == "hinge_4_5x4" and checked and hardware.get("hinge_4_5x4_qty"):
                c.setFont("Helvetica", 8)
                c.setFillColor(colors.HexColor("#4b5d7a"))
                c.drawString(x + 5 * mm + 60 * mm, y, f"qte : {hardware['hinge_4_5x4_qty']}")
            if col == 1 or idx == len(items) - 1:
                y -= 6 * mm
        y -= 4 * mm

    # Notes footer
    notes = (order.get("notes") or "").strip()
    if notes and y > 35 * mm:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#0c182b"))
        c.drawString(15 * mm, y, "NOTES")
        y -= 5 * mm
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.black)
        for line in notes.splitlines()[:8]:
            c.drawString(15 * mm, y, _ascii(line)[:120])
            y -= 4.5 * mm
            if y < 35 * mm:
                break


# ===========================================================================
# Public render entry-point
# ===========================================================================
def render_shop_drawing_pdf(order: dict) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    page_w, page_h = LETTER

    doors = order.get("doors") or []
    # We can fit ~6 doors per elevation page → chunk if more.
    chunk = 6
    elevation_pages = max(1, (len(doors) + chunk - 1) // chunk) if doors else 1
    total_pages = 1 + elevation_pages + 1  # cover + N x elevation + hardware

    page_num = 1
    _page_cover(c, page_w, page_h, order)
    _draw_footer_cartouche(c, page_w, order, page_num, total_pages)
    c.showPage()

    for i in range(elevation_pages):
        page_num += 1
        slice_ = doors[i * chunk:(i + 1) * chunk]
        _page_elevations(c, page_w, page_h, order, slice_)
        _draw_footer_cartouche(c, page_w, order, page_num, total_pages)
        c.showPage()

    page_num += 1
    _page_hardware(c, page_w, page_h, order)
    _draw_footer_cartouche(c, page_w, order, page_num, total_pages)
    c.showPage()
    c.save()
    return buf.getvalue()
