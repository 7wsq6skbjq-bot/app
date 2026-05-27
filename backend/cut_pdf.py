"""PDF workshop sheet generator for the Cut List feature.

Produces an A4-portrait sheet for the workshop: header (project + date),
optimized bar-cutting plan grouped by profile, glass panels table,
hardware checklist. ReportLab, deterministic, no browser.
"""
import io
import re
from datetime import datetime
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from cut_models import ITEM_TYPE_LABELS_FR

NAVY = colors.HexColor("#0c182b")
NAVY_LIGHT = colors.HexColor("#2f4f7f")
BORDER = colors.HexColor("#dde5f0")
BG_LIGHT = colors.HexColor("#f3f6fb")
GREEN = colors.HexColor("#0b6b2f")
RED_WARN = colors.HexColor("#a83a2f")
TEXT_MUTED = colors.HexColor("#4b5d7a")

# ─── Unicode → ASCII for ReportLab Helvetica (black-square fix) ───────────
# Helvetica (the default) doesn't have glyphs for vulgar fractions, em-dashes,
# checkboxes, super/subscript digits — they render as ▢. We replace every such
# char with a printable ASCII equivalent before passing to Paragraph().
_UNICODE_REPLACE = {
    # Vulgar fractions → decimal (mm-friendly)
    "¼": ".25", "½": ".5", "¾": ".75",
    "⅛": ".125", "⅜": ".375", "⅝": ".625", "⅞": ".875",
    "⅓": ".333", "⅔": ".667", "⅕": ".2", "⅖": ".4", "⅗": ".6", "⅘": ".8",
    "⅙": ".167", "⅚": ".833",
    # Quotes, dashes, prime
    "—": " - ", "–": "-", "…": "...",
    "«": "\"", "»": "\"", "“": "\"", "”": "\"", "‘": "'", "’": "'",
    "″": "\"", "′": "'",
    # Checkboxes
    "☐": "[ ]", "☑": "[X]", "✓": "[X]", "✗": "[X]",
    # Superscripts / subscripts (²×³ are common in m² etc.)
    "²": "2", "³": "3", "¹": "1", "⁰": "0",
    # Misc that Helvetica also lacks
    "•": "*", "·": "-", "→": "->", "←": "<-", "×": "x",
}
_UNICODE_REPLACE_RE = re.compile("|".join(re.escape(k) for k in _UNICODE_REPLACE))


def _sanitize(text) -> str:
    """Strip / replace any non-Helvetica-safe character so the PDF never shows
    black squares. Inputs `None` or non-str values are coerced to str safely."""
    if text is None:
        return ""
    s = str(text)
    if not s:
        return s
    s = _UNICODE_REPLACE_RE.sub(lambda m: _UNICODE_REPLACE[m.group(0)], s)
    # Catch any remaining char outside basic latin + extended-A (Helvetica safe)
    # by replacing it with '?'. Preserve HTML markup ('<', '>', '&') though.
    out = []
    for ch in s:
        cp = ord(ch)
        # ASCII printable + Latin-1 + Latin Extended-A
        if cp < 0x250 or ch in ("\n", "\t"):
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


def _para(text: str, **kw) -> Paragraph:
    style = ParagraphStyle("p", fontName=kw.get("font", "Helvetica"),
                           fontSize=kw.get("size", 9),
                           textColor=kw.get("color", colors.black),
                           leading=kw.get("leading", 11),
                           alignment=kw.get("align", 0))
    return Paragraph(_sanitize(text), style)


def render_cut_list_pdf(cut_list: dict, optimization: dict) -> bytes:
    """Return PDF bytes for the cut list workshop sheet."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"Liste de coupe — {cut_list.get('name', '')}",
    )
    elements: list = []

    # ===== Header =====
    header_rows = [
        [
            _para("PORTECH", font="Helvetica-Bold", size=14, color=NAVY),
            _para(
                f"Date : {datetime.now().strftime('%Y-%m-%d')}<br/>"
                f"Projet : <b>{cut_list.get('name', '')}</b><br/>"
                f"Réf. : {cut_list.get('project_ref') or '—'}",
                size=8, color=TEXT_MUTED, align=2,
            ),
        ],
    ]
    h_table = Table(header_rows, colWidths=[None, 90 * mm])
    h_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(h_table)
    elements.append(Spacer(1, 4 * mm))

    elements.append(_para("LISTE DE COUPE — ATELIER", font="Helvetica-Bold",
                          size=13, color=NAVY))
    if cut_list.get("customer_name"):
        elements.append(_para(f"Client : {cut_list['customer_name']}",
                              size=9, color=TEXT_MUTED))
    elements.append(Spacer(1, 3 * mm))

    # ===== Summary tiles =====
    eff = optimization.get("efficiency_pct", 0)
    eff_color = GREEN if eff >= 85 else (NAVY_LIGHT if eff >= 70 else RED_WARN)
    sum_rows = [[
        _para(f"<b>{optimization.get('total_bars', 0)}</b><br/>"
              f"<font size=7 color='#4b5d7a'>BARRES NÉCESSAIRES</font>", size=12, align=1),
        _para(f"<b>{optimization.get('total_waste_mm', 0):.0f} mm</b><br/>"
              f"<font size=7 color='#4b5d7a'>CHUTE TOTALE</font>", size=12, align=1),
        _para(f"<b><font color='{eff_color.hexval()}'>{eff:.1f}%</font></b><br/>"
              f"<font size=7 color='#4b5d7a'>EFFICACITÉ</font>", size=12, align=1),
        _para(f"<b>{cut_list.get('saw_kerf_mm', 0)} mm</b><br/>"
              f"<font size=7 color='#4b5d7a'>SAIGNÉE LAME</font>", size=12, align=1),
    ]]
    s_table = Table(sum_rows, colWidths=[44 * mm] * 4, rowHeights=[16 * mm])
    s_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(s_table)
    elements.append(Spacer(1, 6 * mm))

    # ===== Per-group cutting plans =====
    for grp in optimization.get("groups", []):
        plan = grp["plan"]
        elements.append(_para(
            f"PROFILÉ : <b>{grp['profile']}</b>"
            f" &nbsp; · &nbsp; Matériau : {grp['material']}"
            f" &nbsp; · &nbsp; Barres : <b>{plan.get('bars_count', 0)}</b> × "
            f"{plan.get('stock_length_mm', 0):.0f} mm"
            f" &nbsp; · &nbsp; Chute : {plan.get('total_waste_mm', 0):.0f} mm",
            font="Helvetica-Bold", size=10, color=NAVY,
        ))
        elements.append(Spacer(1, 2 * mm))

        # Bars table: # | Coupes (mm, séparées par +) | Util. | Chute
        data: list[list] = [[
            _para("#", font="Helvetica-Bold", size=8, color=colors.white, align=1),
            _para("COUPES (mm)", font="Helvetica-Bold", size=8, color=colors.white),
            _para("UTILISÉ", font="Helvetica-Bold", size=8, color=colors.white, align=2),
            _para("CHUTE", font="Helvetica-Bold", size=8, color=colors.white, align=2),
        ]]
        for i, bar in enumerate(plan.get("bars", []), start=1):
            cuts_str = "  +  ".join(f"{c:.0f}" for c in bar["cuts"])
            data.append([
                _para(str(i), size=9, align=1),
                _para(cuts_str, size=9),
                _para(f"{bar['used_mm']:.0f}", size=9, align=2),
                _para(f"{bar['waste_mm']:.0f}", size=9, align=2,
                      color=RED_WARN if bar['waste_mm'] > 500 else TEXT_MUTED),
            ])
        plan_table = Table(data, colWidths=[8 * mm, 120 * mm, 25 * mm, 25 * mm])
        plan_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(plan_table)
        elements.append(Spacer(1, 6 * mm))

    # ===== Glass panels =====
    glass = optimization.get("glass_summary", {})
    if glass.get("panels"):
        elements.append(_para("VITRAGES / PANNEAUX", font="Helvetica-Bold",
                              size=10, color=NAVY))
        elements.append(Spacer(1, 2 * mm))
        gdata: list[list] = [[
            _para("LABEL", font="Helvetica-Bold", size=8, color=colors.white),
            _para("DIM. (mm)", font="Helvetica-Bold", size=8, color=colors.white),
            _para("ÉPAIS.", font="Helvetica-Bold", size=8, color=colors.white),
            _para("QTÉ", font="Helvetica-Bold", size=8, color=colors.white, align=1),
            _para("SURFACE (m²)", font="Helvetica-Bold", size=8, color=colors.white, align=2),
        ]]
        for p in glass["panels"]:
            t = p.get("thickness_mm")
            gdata.append([
                _para(p["label"], size=9),
                _para(f"{p['length_mm']:.0f} × {p['width_mm']:.0f}", size=9),
                _para(f"{t:.1f} mm" if t else "—", size=9),
                _para(str(p["qty"]), size=9, align=1),
                _para(f"{p['area_m2']:.3f}", size=9, align=2),
            ])
        gdata.append([
            _para("", size=9), _para("", size=9), _para("", size=9),
            _para(f"<b>{glass['count']}</b>", size=9, align=1, color=NAVY),
            _para(f"<b>{glass['total_area_m2']:.3f}</b>", size=9, align=2, color=NAVY),
        ])
        g_table = Table(gdata, colWidths=[55 * mm, 35 * mm, 22 * mm, 18 * mm, 36 * mm])
        g_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("BACKGROUND", (0, -1), (-1, -1), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(g_table)
        elements.append(Spacer(1, 6 * mm))

    # ===== Hardware list (full items, no optimization) =====
    hw_items = [i for i in cut_list.get("items", []) if i.get("item_type") in ("hardware", "hole")]
    if hw_items:
        elements.append(_para("QUINCAILLERIE & PERÇAGES", font="Helvetica-Bold",
                              size=10, color=NAVY))
        elements.append(Spacer(1, 2 * mm))
        hdata: list[list] = [[
            _para("☐", font="Helvetica-Bold", size=8, color=colors.white, align=1),
            _para("TYPE", font="Helvetica-Bold", size=8, color=colors.white),
            _para("DESCRIPTION", font="Helvetica-Bold", size=8, color=colors.white),
            _para("N° PIÈCE", font="Helvetica-Bold", size=8, color=colors.white),
            _para("FABRICANT", font="Helvetica-Bold", size=8, color=colors.white),
            _para("POSITION", font="Helvetica-Bold", size=8, color=colors.white),
            _para("QTÉ", font="Helvetica-Bold", size=8, color=colors.white, align=1),
        ]]
        for it in hw_items:
            pos = ""
            if it.get("position_y") is not None:
                pos = f"Y={it['position_y']:.0f} mm"
                if it.get("position_x") is not None:
                    pos = f"X={it['position_x']:.0f} · " + pos
            hdata.append([
                _para("☐", size=11, align=1),
                _para(ITEM_TYPE_LABELS_FR.get(it.get("item_type", "other"), "—"), size=8),
                _para(it.get("label") or it.get("notes") or "—", size=8),
                _para(it.get("part_number") or "—", size=8, font="Courier"),
                _para(it.get("manufacturer") or "—", size=8),
                _para(pos or "—", size=7, color=TEXT_MUTED),
                _para(str(it.get("qty", 1)), size=9, align=1),
            ])
        h_table = Table(hdata, colWidths=[8 * mm, 22 * mm, 50 * mm, 33 * mm, 30 * mm, 22 * mm, 10 * mm])
        h_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(h_table)
        elements.append(Spacer(1, 4 * mm))

    # ===== Gaskets (joints / weatherseals) =====
    gasket_items = [i for i in cut_list.get("items", []) if i.get("item_type") == "gasket"]
    if gasket_items:
        elements.append(_para("GASKETS / JOINTS", font="Helvetica-Bold",
                              size=10, color=NAVY))
        elements.append(Spacer(1, 2 * mm))
        gk_data: list[list] = [[
            _para("[ ]", font="Helvetica-Bold", size=8, color=colors.white, align=1),
            _para("DESCRIPTION", font="Helvetica-Bold", size=8, color=colors.white),
            _para("N° PIECE", font="Helvetica-Bold", size=8, color=colors.white),
            _para("FABRICANT", font="Helvetica-Bold", size=8, color=colors.white),
            _para("LONGUEUR (mm)", font="Helvetica-Bold", size=8, color=colors.white, align=2),
            _para("QTE", font="Helvetica-Bold", size=8, color=colors.white, align=1),
        ]]
        total_gasket_mm = 0.0
        for it in gasket_items:
            length = float(it.get("length_mm") or 0)
            qty = int(it.get("qty") or 1)
            total_gasket_mm += length * qty
            gk_data.append([
                _para("[ ]", size=11, align=1),
                _para(it.get("label") or "-", size=8),
                _para(it.get("part_number") or "-", size=8, font="Courier"),
                _para(it.get("manufacturer") or "-", size=8),
                _para(f"{length:.1f}", size=9, align=2),
                _para(str(qty), size=9, align=1),
            ])
        gk_data.append([
            _para("", size=9), _para("", size=9),
            _para("", size=9), _para("TOTAL", font="Helvetica-Bold", size=9, color=NAVY, align=2),
            _para(f"<b>{total_gasket_mm:.0f} mm</b>", size=9, align=2, color=NAVY),
            _para("", size=9),
        ])
        gk_table = Table(gk_data, colWidths=[8 * mm, 55 * mm, 28 * mm, 32 * mm, 35 * mm, 12 * mm])
        gk_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("BACKGROUND", (0, -1), (-1, -1), BG_LIGHT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, BG_LIGHT]),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(gk_table)
        elements.append(Spacer(1, 4 * mm))

    # ===== Footer =====
    elements.append(_para(
        f"<i>Imprimé le {datetime.now().strftime('%Y-%m-%d à %H:%M')} · "
        f"Portech ERP · Saignée appliquée : {cut_list.get('saw_kerf_mm', 0)} mm</i>",
        size=7, color=TEXT_MUTED, align=1,
    ))

    doc.build(elements)
    return buf.getvalue()
