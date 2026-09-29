"""Rapport de quincaillerie consommée (Hardware consumption report).

Given a production plan, produce a clean, Portech-branded, portrait PDF listing
the hardware consumed for the project — a grand total (all doors) plus a
per-door breakdown. Quantities account for the door quantity (qty per door ×
number of doors). Meant for the monthly hardware-usage report.
"""
from __future__ import annotations

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

NAVY = colors.HexColor("#0c182b")
NAVY_LIGHT = colors.HexColor("#2f4f7f")
NAVY_BORDER = colors.HexColor("#dde5f0")
BG_LIGHT = colors.HexColor("#f3f6fb")
TEXT_MUTED = colors.HexColor("#4b5d7a")
RED = colors.HexColor("#b3261e")

MARK_WHITE = "/app/frontend/public/brand/portech-mark-white.png"

COMPANY = {
    "name": "PORTECH",
    "tagline": "Quincaillerie et portes commerciales en aluminium",
    "line1": "Grand Montréal, QC",
    "phone": "438-376-4177",
    "email": "info@portech.info",
}

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


def _parse_qty(v) -> float:
    try:
        return float(str(v).replace(",", ".").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _fmt_qty(n: float) -> str:
    try:
        return str(int(n)) if float(n).is_integer() else f"{n:g}"
    except (TypeError, ValueError):
        return str(n)


def _aggregate(plan: dict):
    """Return (per_door, total_rows, grand_qty)."""
    doors = plan.get("doors") or []
    per_door = []
    totals = {}
    grand_qty = 0.0
    for i, d in enumerate(doors, 1):
        try:
            dq = int(d.get("qty") or 1)
        except (TypeError, ValueError):
            dq = 1
        rows = []
        for hw in (d.get("hardware") or []):
            desc = (hw.get("description") or "").strip()
            pn = (hw.get("part_number") or "").strip()
            if not desc and not pn:
                continue
            q = _parse_qty(hw.get("qty") or "1") * dq
            rows.append({"desc": desc or "—", "pn": pn or "—", "qty": q})
            grand_qty += q
            key = (pn.lower(), desc.lower())
            t = totals.setdefault(key, {"desc": desc or "—", "pn": pn or "—", "qty": 0.0})
            t["qty"] += q
        per_door.append({
            "tag": d.get("tag") or f"Porte {i}",
            "series": d.get("series") or "",
            "config": "Paire" if d.get("config") == "pair" else "Simple",
            "door_qty": dq,
            "rows": rows,
        })
    total_rows = sorted(totals.values(), key=lambda r: r["desc"].lower())
    return per_door, total_rows, grand_qty


def _header_footer(plan: dict):
    def _draw(c, doc):
        W, Hh = LETTER
        c.saveState()
        # top navy band
        c.setFillColor(NAVY)
        c.rect(0, Hh - 60, W, 60, fill=1, stroke=0)
        if os.path.exists(MARK_WHITE):
            try:
                c.drawImage(MARK_WHITE, 36, Hh - 52, width=38, height=38,
                            preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(82, Hh - 30, "PORTECH")
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#9bb6d8"))
        c.drawString(82, Hh - 42, COMPANY["tagline"])
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(W - 36, Hh - 30, "QUINCAILLERIE CONSOMMÉE")
        c.setFont("Courier", 7)
        c.setFillColor(colors.HexColor("#9bb6d8"))
        c.drawRightString(W - 36, Hh - 42, _date_fr(plan.get("date")))
        # footer band
        c.setFillColor(NAVY)
        c.rect(0, 0, W, 24, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 7)
        c.drawString(36, 9,
                     f"{COMPANY['name']}  ·  {COMPANY['line1']}  ·  "
                     f"Tél. {COMPANY['phone']}  ·  {COMPANY['email']}")
        c.setFont("Helvetica-Bold", 7.5)
        c.drawRightString(W - 36, 9, f"Page {doc.page}")
        c.restoreState()
    return _draw


def render_hardware_report_pdf(plan: dict) -> bytes:
    buf = io.BytesIO()
    W, Hh = LETTER
    doc = BaseDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=36, rightMargin=36, topMargin=72, bottomMargin=34,
        title=f"Portech — Quincaillerie consommée {plan.get('plan_number') or ''}",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame],
                                       onPage=_header_footer(plan))])

    st_title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15,
                              textColor=NAVY, spaceAfter=2, leading=18)
    st_sub = ParagraphStyle("s", fontName="Helvetica", fontSize=9,
                            textColor=TEXT_MUTED, spaceAfter=1, leading=12)
    st_sec = ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=10,
                            textColor=colors.white, leading=13)
    st_door = ParagraphStyle("door", fontName="Helvetica-Bold", fontSize=9.5,
                             textColor=NAVY, leading=12)
    st_cell = ParagraphStyle("c", fontName="Helvetica", fontSize=8,
                             textColor=NAVY, leading=10)
    st_cellm = ParagraphStyle("cm", fontName="Courier", fontSize=7.5,
                              textColor=TEXT_MUTED, leading=10)

    per_door, total_rows, grand_qty = _aggregate(plan)
    story = []

    # project info block
    proj = plan.get("project_name") or "—"
    story.append(Paragraph("Rapport de quincaillerie consommée", st_title))
    story.append(Paragraph(f"Projet : <b>{proj}</b>", st_sub))
    info = [
        ("Client", plan.get("client_name") or "—"),
        ("N° de projet", plan.get("project_number") or "—"),
        ("N° de plan", plan.get("plan_number") or "—"),
        ("Date", _date_fr(plan.get("date"))),
        ("Nombre de portes", str(len(per_door))),
    ]
    info_tbl = Table([[Paragraph(f"<b>{k}</b>", st_cell), Paragraph(v, st_cell)] for k, v in info],
                     colWidths=[110, doc.width - 110])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, NAVY_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 6))
    story.append(info_tbl)
    story.append(Spacer(1, 14))

    def _hw_table(rows, header_bg=NAVY):
        data = [[Paragraph("<font color='white'><b>QTÉ</b></font>", st_cell),
                 Paragraph("<font color='white'><b>DESCRIPTION</b></font>", st_cell),
                 Paragraph("<font color='white'><b>N° PIÈCE</b></font>", st_cell)]]
        for r in rows:
            data.append([Paragraph(f"<b>{_fmt_qty(r['qty'])}</b>", st_cell),
                         Paragraph(r["desc"], st_cell),
                         Paragraph(r["pn"], st_cellm)])
        if len(data) == 1:
            data.append([Paragraph("—", st_cell),
                         Paragraph("<i>Aucune quincaillerie.</i>", st_cell),
                         Paragraph("", st_cellm)])
        t = Table(data, colWidths=[46, doc.width - 46 - 120, 120], repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, NAVY_BORDER),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, NAVY_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), BG_LIGHT))
        t.setStyle(TableStyle(style))
        return t

    # ── Grand total ──
    story.append(Table(
        [[Paragraph(f"TOTAL DU PROJET — {_fmt_qty(grand_qty)} pièce(s)", st_sec)]],
        colWidths=[doc.width],
        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), RED),
                          ("TOPPADDING", (0, 0), (-1, -1), 4),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                          ("LEFTPADDING", (0, 0), (-1, -1), 6)])))
    story.append(Spacer(1, 3))
    story.append(_hw_table(total_rows))
    story.append(Spacer(1, 16))

    # ── Per-door breakdown ──
    story.append(Table(
        [[Paragraph("DÉTAIL PAR PORTE", st_sec)]],
        colWidths=[doc.width],
        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                          ("TOPPADDING", (0, 0), (-1, -1), 4),
                          ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                          ("LEFTPADDING", (0, 0), (-1, -1), 6)])))
    story.append(Spacer(1, 6))

    for d in per_door:
        head = (f"{d['tag']} — {d['series']} · {d['config']} · "
                f"Qté porte : {d['door_qty']}")
        block = [Paragraph(head, st_door), Spacer(1, 2),
                 _hw_table(d["rows"], header_bg=NAVY_LIGHT), Spacer(1, 12)]
        story.append(KeepTogether(block))

    doc.build(story)
    buf.seek(0)
    return buf.read()
