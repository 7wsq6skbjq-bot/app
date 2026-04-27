"""
Server-side PDF generation for ERP documents (invoice, PO, BOL).
Uses reportlab — no headless browser, deterministic output.
"""
import io
import os
from datetime import datetime
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0c182b")
NAVY_LIGHT = colors.HexColor("#2f4f7f")
NAVY_BORDER = colors.HexColor("#dde5f0")
BG_LIGHT = colors.HexColor("#f3f6fb")
TEXT_MUTED = colors.HexColor("#4b5d7a")

LOGO_PATH = "/app/frontend/public/brand/logo-portech.png"
COMPANY = {
    "name": "Portech",
    "tagline": "Quincaillerie commerciale — Grand Montréal",
    "email": "info@portech.info",
    "site": "portech.info",
}


def _money(v) -> str:
    try:
        v = float(v or 0)
    except (TypeError, ValueError):
        v = 0.0
    s = f"{v:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} $"


def _date_fr(iso) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00")) if "T" in str(iso) else datetime.strptime(str(iso)[:10], "%Y-%m-%d")
        return d.strftime("%d %b %Y")
    except Exception:
        return str(iso)


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=ss["Heading1"],
            fontName="Helvetica-Bold", fontSize=24, leading=26,
            textColor=NAVY, alignment=2,  # right
            spaceAfter=2,
        ),
        "number": ParagraphStyle(
            "number", parent=ss["Normal"],
            fontName="Courier", fontSize=12, textColor=NAVY_LIGHT, alignment=2,
        ),
        "label": ParagraphStyle(
            "label", parent=ss["Normal"],
            fontName="Courier", fontSize=7, textColor=TEXT_MUTED,
            spaceBefore=0, spaceAfter=2,
        ),
        "party_name": ParagraphStyle(
            "party_name", parent=ss["Normal"],
            fontName="Helvetica-Bold", fontSize=11, textColor=NAVY, leading=13,
        ),
        "party_addr": ParagraphStyle(
            "party_addr", parent=ss["Normal"],
            fontName="Helvetica", fontSize=9, textColor=NAVY, leading=12,
        ),
        "body": ParagraphStyle(
            "body", parent=ss["Normal"],
            fontName="Helvetica", fontSize=9, textColor=NAVY, leading=12,
        ),
        "footer": ParagraphStyle(
            "footer", parent=ss["Normal"],
            fontName="Helvetica", fontSize=7.5, textColor=TEXT_MUTED, leading=10,
        ),
    }


def _header(styles, doc_title: str, doc_number: str, status: str | None):
    """Return a Table containing logo+company on the left and title+number on the right."""
    left_cells = []
    if os.path.exists(LOGO_PATH):
        try:
            img = Image(LOGO_PATH, width=42 * mm, height=14 * mm, kind="proportional")
            left_cells.append(img)
        except Exception:
            pass
    left_cells.append(Spacer(1, 4))
    left_cells.append(Paragraph(
        f"<b>{COMPANY['name']}</b> · {COMPANY['tagline']}<br/>"
        f"{COMPANY['email']} · {COMPANY['site']}",
        styles["footer"],
    ))

    title_html = doc_title
    if status:
        title_html += f' <font face="Courier" size="8" color="#2f4f7f">[{status.upper()}]</font>'

    right_cells = [
        Paragraph(title_html, styles["title"]),
        Paragraph(doc_number, styles["number"]),
    ]

    t = Table(
        [[left_cells, right_cells]],
        colWidths=[95 * mm, 80 * mm],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 2, NAVY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _party_block(styles, label: str, party: dict):
    p = party or {}
    lines = []
    if p.get("contact"):
        lines.append(p["contact"])
    if p.get("address_line1"):
        lines.append(p["address_line1"])
    if p.get("address_line2"):
        lines.append(p["address_line2"])
    region_bits = [p.get("city"), p.get("province"), p.get("postal_code")]
    region = " · ".join([b for b in region_bits if b])
    if region:
        lines.append(region)
    if p.get("country") and p["country"] != "Canada":
        lines.append(p["country"])
    if p.get("phone"):
        lines.append(f"Tél. {p['phone']}")
    if p.get("email"):
        lines.append(p["email"])
    if p.get("tax_number"):
        lines.append(f"NEQ/TPS : {p['tax_number']}")

    inner = [
        Paragraph(label.upper(), styles["label"]),
        Paragraph(p.get("name") or "—", styles["party_name"]),
        Paragraph("<br/>".join(lines) if lines else "—", styles["party_addr"]),
    ]
    t = Table([[inner]], colWidths=[80 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, NAVY_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _meta_grid(styles, entries: Iterable[tuple]):
    """entries = list of (label, value) tuples — render in 2 cols."""
    rows, row = [], []
    for lbl, val in entries:
        cell = [
            Paragraph(lbl.upper(), styles["label"]),
            Paragraph(f"<b>{val or '—'}</b>", styles["body"]),
        ]
        row.append(cell)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        if len(row) == 1:
            row.append([Paragraph("", styles["body"])])
        rows.append(row)

    t = Table(rows, colWidths=[40 * mm, 40 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, NAVY_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, NAVY_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fbfd")),
    ]))
    return t


def _items_table_money(items: list[dict]) -> Table:
    """Items table for invoice & PO (with prices)."""
    header = ["Description", "Qté", "Prix unitaire", "Total"]
    data = [header]
    for it in items or []:
        qty = it.get("quantity") or 0
        unit = it.get("unit_price") or 0
        total = it.get("total")
        if total is None:
            total = float(qty) * float(unit)
        data.append([
            Paragraph(it.get("description") or "—", _styles()["body"]),
            f"{qty}",
            _money(unit),
            _money(total),
        ])
    t = Table(data, colWidths=[95 * mm, 18 * mm, 32 * mm, 32 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, NAVY_BORDER),
        ("TEXTCOLOR", (0, 1), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _items_table_bol(items: list[dict]) -> Table:
    """Items table for BOL (no prices, weight + dimensions)."""
    header = ["Description", "Qté", "Unité", "Poids (kg)", "Dimensions"]
    data = [header]
    for it in items or []:
        data.append([
            Paragraph(it.get("description") or "—", _styles()["body"]),
            f"{it.get('quantity', 0)}",
            it.get("unit") or "—",
            f"{it.get('weight_kg')}" if it.get("weight_kg") is not None else "—",
            it.get("dimensions") or "—",
        ])
    t = Table(data, colWidths=[75 * mm, 18 * mm, 22 * mm, 25 * mm, 35 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, NAVY_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _totals_box(subtotal, tps, tvq, total, taxable, label_total="Total à payer"):
    rows = [["Sous-total", _money(subtotal)]]
    if taxable:
        rows.append(["TPS (5 %)", _money(tps)])
        rows.append(["TVQ (9,975 %)", _money(tvq)])
    rows.append([label_total.upper(), _money(total)])
    t = Table(rows, colWidths=[50 * mm, 35 * mm], hAlign="RIGHT")
    last = len(rows) - 1
    t.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -2), 10),
        ("LINEABOVE", (0, last), (-1, last), 1.5, NAVY),
        ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
        ("FONTSIZE", (0, last), (-1, last), 12),
        ("TOPPADDING", (0, last), (-1, last), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -2), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


# ============================================================
# Public functions
# ============================================================
def _build_doc():
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Portech",
    )
    return buf, doc


def render_invoice_pdf(inv: dict) -> bytes:
    s = _styles()
    buf, doc = _build_doc()
    story = []

    number = f"FAC-{int(inv['number']):04d}"
    story.append(_header(s, "FACTURE", number, inv.get("status")))
    story.append(Spacer(1, 8 * mm))

    # Two cols: customer + meta
    party = _party_block(s, "Facturé à", inv.get("customer_snapshot") or {})
    meta = _meta_grid(s, [
        ("Numéro", number),
        ("Date", _date_fr(inv.get("date"))),
        ("Échéance", _date_fr(inv.get("due_date"))),
        ("Statut", (inv.get("status") or "—").upper()),
    ])
    side_by_side = Table([[party, meta]], colWidths=[80 * mm, 90 * mm])
    side_by_side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(side_by_side)
    story.append(Spacer(1, 6 * mm))

    story.append(_items_table_money(inv.get("items", [])))
    story.append(Spacer(1, 4 * mm))
    story.append(_totals_box(
        inv.get("subtotal", 0), inv.get("tps", 0),
        inv.get("tvq", 0), inv.get("total", 0),
        inv.get("taxable", True), "Total à payer",
    ))

    if inv.get("notes"):
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(f"<b>Notes :</b><br/>{inv['notes']}", s["body"]))

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "<b>Modalités de paiement</b> · Net 30 jours. "
        "Intérêts de 1,5 % par mois sur les soldes en souffrance.<br/>"
        "Merci pour votre confiance — info@portech.info",
        s["footer"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def render_purchase_order_pdf(po: dict) -> bytes:
    s = _styles()
    buf, doc = _build_doc()
    story = []
    number = f"BC-{int(po['number']):04d}"
    story.append(_header(s, "BON DE COMMANDE", number, po.get("status")))
    story.append(Spacer(1, 8 * mm))

    party = _party_block(s, "Fournisseur", po.get("supplier_snapshot") or {})
    meta = _meta_grid(s, [
        ("Numéro", number),
        ("Date", _date_fr(po.get("date"))),
        ("Livraison attendue", _date_fr(po.get("expected_delivery"))),
        ("Statut", (po.get("status") or "—").upper()),
    ])
    side_by_side = Table([[party, meta]], colWidths=[80 * mm, 90 * mm])
    side_by_side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(side_by_side)
    story.append(Spacer(1, 6 * mm))

    story.append(_items_table_money(po.get("items", [])))
    story.append(Spacer(1, 4 * mm))
    story.append(_totals_box(
        po.get("subtotal", 0), po.get("tps", 0),
        po.get("tvq", 0), po.get("total", 0),
        po.get("taxable", True), "Total commandé",
    ))

    if po.get("notes"):
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(f"<b>Notes :</b><br/>{po['notes']}", s["body"]))

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "<b>Adresse de livraison</b> · À confirmer avec Portech avant expédition.<br/>"
        "Contact : info@portech.info",
        s["footer"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def render_bol_pdf(bol: dict) -> bytes:
    s = _styles()
    buf, doc = _build_doc()
    story = []
    number = f"CONN-{int(bol['number']):04d}"
    story.append(_header(s, "CONNAISSEMENT", number, bol.get("status")))
    story.append(Spacer(1, 8 * mm))

    shipper = _party_block(s, "Expéditeur", bol.get("shipper_snapshot") or {})
    consignee = _party_block(s, "Destinataire", bol.get("consignee_snapshot") or {})
    side_by_side = Table([[shipper, consignee]], colWidths=[85 * mm, 85 * mm])
    side_by_side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(side_by_side)
    story.append(Spacer(1, 5 * mm))

    story.append(_meta_grid(s, [
        ("Numéro", number),
        ("Date", _date_fr(bol.get("date"))),
        ("Livraison attendue", _date_fr(bol.get("expected_delivery"))),
        ("Transporteur", bol.get("carrier") or "—"),
    ]))
    story.append(Spacer(1, 5 * mm))

    story.append(_items_table_bol(bol.get("items", [])))
    story.append(Spacer(1, 4 * mm))

    if bol.get("total_weight_kg") is not None:
        tw = Table(
            [["POIDS TOTAL", f"{bol['total_weight_kg']} kg"]],
            colWidths=[50 * mm, 35 * mm], hAlign="RIGHT",
        )
        tw.setStyle(TableStyle([
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("LINEABOVE", (0, 0), (-1, -1), 1.5, NAVY),
            ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tw)

    if bol.get("special_instructions"):
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(f"<b>Instructions spéciales :</b><br/>{bol['special_instructions']}", s["body"]))

    story.append(Spacer(1, 18 * mm))
    sig = Table(
        [[
            Paragraph(
                "<u>" + " " * 60 + "</u><br/><font size=7 color=#4b5d7a>"
                "Signature de l'expéditeur · Date</font>",
                s["body"],
            ),
            Paragraph(
                "<u>" + " " * 60 + "</u><br/><font size=7 color=#4b5d7a>"
                "Signature du destinataire · Date de réception</font>",
                s["body"],
            ),
        ]],
        colWidths=[85 * mm, 85 * mm],
    )
    story.append(sig)

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "<b>Accord de transport</b> · La réception de la marchandise atteste de son état apparent satisfaisant. "
        "Réserves éventuelles à noter au verso.<br/>Contact Portech : info@portech.info",
        s["footer"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
