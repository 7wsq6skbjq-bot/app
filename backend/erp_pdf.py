"""
Server-side PDF generation for ERP documents (invoice, PO, BOL).
Uses reportlab — no headless browser, deterministic output.
"""
import io
import os
import re
from datetime import datetime
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
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


def render_quote_pdf(q: dict) -> bytes:
    """Render a quote / soumission PDF — same layout family as invoices
    but with 'SOUMISSION' branding and a validity window instead of a
    payment due date."""
    s = _styles()
    buf, doc = _build_doc()
    story = []

    number = f"SO-{int(q['number']):04d}"
    story.append(_header(s, "SOUMISSION", number, q.get("status")))
    story.append(Spacer(1, 8 * mm))

    party = _party_block(s, "Soumis à", q.get("customer_snapshot") or {})
    meta = _meta_grid(s, [
        ("Numéro", number),
        ("Date", _date_fr(q.get("date"))),
        ("Valide jusqu'au", _date_fr(q.get("valid_until"))),
        ("Statut", (q.get("status") or "—").upper()),
    ])
    side_by_side = Table([[party, meta]], colWidths=[80 * mm, 90 * mm])
    side_by_side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(side_by_side)
    story.append(Spacer(1, 6 * mm))

    story.append(_items_table_money(q.get("items", [])))
    story.append(Spacer(1, 4 * mm))
    story.append(_totals_box(
        q.get("subtotal", 0), q.get("tps", 0),
        q.get("tvq", 0), q.get("total", 0),
        q.get("taxable", True), "Total estimé",
    ))

    if q.get("notes"):
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(f"<b>Notes :</b><br/>{q['notes']}", s["body"]))

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "<b>Cette soumission est valide 30 jours</b> à compter de la date "
        "d'émission (sauf mention contraire ci-dessus). Prix en dollars "
        "canadiens, hors taxes indiquées ci-dessus, sous réserve de la "
        "disponibilité des matériaux chez nos fournisseurs.<br/>"
        "Pour accepter : répondez à ce courriel ou signez et retournez ce "
        "document — info@portech.info",
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



def _items_table_payment(items: list[dict]) -> Table:
    """Items table for payment notice (Invoice # | Description | Amount)."""
    s = _styles()
    header = ["N° facture", "Description", "Montant"]
    data = [header]
    for it in items or []:
        amount = float(it.get("amount") or 0)
        data.append([
            Paragraph(it.get("invoice_number") or "—", s["body"]),
            Paragraph(it.get("description") or "—", s["body"]),
            _money(amount),
        ])
    t = Table(data, colWidths=[40 * mm, 105 * mm, 32 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
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


def _payment_total_box(total: float) -> Table:
    """Stacked box showing the grand total paid."""
    s = _styles()
    rows = [
        [Paragraph("<b>TOTAL PAYÉ</b>", s["body"]),
         Paragraph(f"<b>{_money(total)} CAD</b>", s["body"])],
    ]
    t = Table(rows, colWidths=[60 * mm, 50 * mm], hAlign="RIGHT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def render_payment_notice_pdf(notice: dict) -> bytes:
    """Render a supplier payment notice (avis de paiement / remittance advice).

    `notice` is expected to contain:
        notice_number, date, supplier_snapshot {name, address?, email?, contact_name?},
        items [{invoice_number, description, amount}], total,
        payment_method, payment_date, reference_number, notes
    """
    s = _styles()
    buf, doc = _build_doc()
    story = []
    number = notice.get("notice_number") or "AP-XXXX"
    story.append(_header(s, "AVIS DE PAIEMENT", number, "PAYÉ"))
    story.append(Spacer(1, 8 * mm))

    party = _party_block(s, "Fournisseur payé",
                          notice.get("supplier_snapshot") or {})
    meta = _meta_grid(s, [
        ("Numéro", number),
        ("Date émission", _date_fr(notice.get("date"))),
        ("Date du paiement", _date_fr(notice.get("payment_date"))),
        ("Méthode", notice.get("payment_method") or "—"),
        ("N° référence", notice.get("reference_number") or "—"),
    ])
    side_by_side = Table([[party, meta]], colWidths=[80 * mm, 90 * mm])
    side_by_side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(side_by_side)
    story.append(Spacer(1, 6 * mm))

    story.append(_items_table_payment(notice.get("items", [])))
    story.append(Spacer(1, 4 * mm))
    story.append(_payment_total_box(float(notice.get("total") or 0)))
    story.append(Spacer(1, 8 * mm))

    # Confirmation block — explains the 3-5 business day arrival window.
    confirmation = (
        "<b>Confirmation de paiement</b><br/>"
        "Le paiement ci-dessus a été émis par Portech à la date indiquée. "
        "Selon votre institution financière, le montant devrait être crédité "
        "dans votre compte d'ici <b>3 à 5 jours ouvrables</b> suivant la date "
        "d'émission. "
        "Veuillez utiliser le numéro de référence pour le rapprochement."
    )
    story.append(Paragraph(confirmation, s["body"]))

    if notice.get("notes"):
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(f"<b>Notes :</b><br/>{notice['notes']}", s["body"]))

    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "Pour toute question concernant ce paiement, communiquez avec "
        "info@portech.info — merci pour votre service.",
        s["footer"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ============================================================
# Product catalogue PDF (Catalogue produits & services)
# ============================================================
def _catalog_cover(styles) -> list:
    """Cover page — branded, presentable to clients."""
    story = []
    # Top spacer pushes content to vertical center-ish
    story.append(Spacer(1, 40 * mm))

    # Big logo
    if os.path.exists(LOGO_PATH):
        try:
            story.append(Image(LOGO_PATH, width=90 * mm, height=30 * mm,
                                kind="proportional", hAlign="CENTER"))
        except Exception:
            pass

    story.append(Spacer(1, 18 * mm))

    title_style = ParagraphStyle(
        "cover_title", fontName="Helvetica-Bold", fontSize=36,
        textColor=NAVY, alignment=1, leading=40,
    )
    sub_style = ParagraphStyle(
        "cover_sub", fontName="Helvetica", fontSize=14,
        textColor=NAVY_LIGHT, alignment=1, leading=18,
    )
    meta_style = ParagraphStyle(
        "cover_meta", fontName="Courier", fontSize=9,
        textColor=TEXT_MUTED, alignment=1, leading=14,
    )

    story.append(Paragraph("CATALOGUE", title_style))
    story.append(Paragraph("Produits &amp; services", sub_style))
    story.append(Spacer(1, 25 * mm))
    story.append(Paragraph(COMPANY["tagline"].upper(), meta_style))
    story.append(Spacer(1, 4 * mm))
    today = datetime.now().strftime("%d %B %Y").replace(
        "January", "janvier").replace("February", "février").replace(
        "March", "mars").replace("April", "avril").replace(
        "May", "mai").replace("June", "juin").replace(
        "July", "juillet").replace("August", "août").replace(
        "September", "septembre").replace("October", "octobre").replace(
        "November", "novembre").replace("December", "décembre")
    story.append(Paragraph(f"ÉDITION DU {today.upper()}", meta_style))

    story.append(Spacer(1, 40 * mm))
    story.append(Paragraph(
        f"<b>{COMPANY['name']}</b> &nbsp;·&nbsp; {COMPANY['email']} &nbsp;·&nbsp; {COMPANY['site']}",
        styles["footer"],
    ))
    return story


def _money_no_zero(v) -> str:
    """Format money but show 'sur demande' for $0 (typical for services)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f <= 0:
        return "sur demande"
    return _money(f)


def _catalog_category_block(styles, category: str, items: list[dict]) -> Table:
    """Render one category section : title + items table."""
    s = styles
    header = ["Code", "Nom", "Description", "Unité", "Prix"]
    data = [header]
    for it in items:
        name_html = it.get("name") or "—"
        if it.get("is_service"):
            name_html = f"{name_html} <font face='Courier' size='6' color='#2f4f7f'>[SERVICE]</font>"
        data.append([
            Paragraph(it.get("sku") or "—",
                      ParagraphStyle("sku", fontName="Courier", fontSize=8,
                                      textColor=NAVY)),
            Paragraph(f"<b>{name_html}</b>", s["body"]),
            Paragraph(it.get("description") or "", s["body"]),
            Paragraph(it.get("unit") or "unité",
                      ParagraphStyle("u", fontName="Helvetica", fontSize=8,
                                      textColor=TEXT_MUTED)),
            _money_no_zero(it.get("unit_price")),
        ])

    t = Table(
        data,
        colWidths=[22 * mm, 50 * mm, 65 * mm, 18 * mm, 22 * mm],
        repeatRows=1,
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, NAVY_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def render_product_catalog_pdf(products: list[dict]) -> bytes:
    """Generate a printable catalog of all products & services.

    Layout:
      * Cover page (logo, title, edition date)
      * For each category : a section with a clean items table
      * Items inside a category are sorted alphabetically by name
      * `unit_price == 0` displays "sur demande" — typical for services
      * Items with `is_service=True` get a `[SERVICE]` mini-badge
    """
    s = _styles()
    buf, doc = _build_doc()
    story = []

    # ── Cover ─────────────────────────────────────────────────
    story.extend(_catalog_cover(s))
    story.append(PageBreak())

    # ── Header (small) on subsequent pages, then content ──────
    story.append(_header(s, "CATALOGUE", "Produits & services", None))
    story.append(Spacer(1, 8 * mm))

    intro_style = ParagraphStyle(
        "intro", fontName="Helvetica", fontSize=10, textColor=NAVY, leading=14,
    )
    story.append(Paragraph(
        "Ce catalogue présente l'ensemble des produits et services offerts par "
        "Portech à ses clients de confiance. Les prix indiqués sont en dollars "
        "canadiens, hors taxes (TPS &amp; TVQ), et susceptibles d'évoluer "
        "selon les fluctuations du marché et la disponibilité chez nos "
        "fournisseurs. Pour toute commande personnalisée ou volume important, "
        f"communiquez avec nous à <b>{COMPANY['email']}</b>.",
        intro_style,
    ))
    story.append(Spacer(1, 6 * mm))

    # ── Group by category ────────────────────────────────────
    by_category: dict[str, list[dict]] = {}
    for p in products or []:
        cat = (p.get("category") or "").strip() or "Sans catégorie"
        by_category.setdefault(cat, []).append(p)

    # Sort categories alphabetically, "Sans catégorie" last
    def cat_sort_key(c: str) -> tuple[int, str]:
        return (1 if c == "Sans catégorie" else 0, c.lower())

    category_style = ParagraphStyle(
        "category", fontName="Helvetica-Bold", fontSize=14,
        textColor=NAVY, leading=18, spaceBefore=2, spaceAfter=4,
        borderPadding=0,
    )
    count_style = ParagraphStyle(
        "count", fontName="Courier", fontSize=8,
        textColor=TEXT_MUTED, leading=10,
    )

    for cat in sorted(by_category.keys(), key=cat_sort_key):
        items = sorted(by_category[cat], key=lambda p: (p.get("name") or "").lower())
        n = len(items)
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(cat.upper(), category_style))
        story.append(Paragraph(
            f"{n} {'article' if n == 1 else 'articles'}",
            count_style,
        ))
        story.append(Spacer(1, 2 * mm))
        story.append(_catalog_category_block(s, cat, items))

    # ── Closing ──────────────────────────────────────────────
    if not by_category:
        story.append(Paragraph(
            "Aucun produit ou service n'est répertorié pour le moment.",
            s["body"],
        ))

    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "Document confidentiel — Pour usage exclusif de nos partenaires de "
        f"confiance. © {datetime.now().year} {COMPANY['name']} · "
        f"{COMPANY['site']}",
        s["footer"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()



# ============================================================
# Expert Report (Rapport d'expertise technique)
# ============================================================
def _report_cover(styles, report: dict) -> list:
    """Cover page — professional, matches VERRE SELECT / 750 Peel style."""
    story = []
    story.append(Spacer(1, 25 * mm))

    if os.path.exists(LOGO_PATH):
        try:
            story.append(Image(LOGO_PATH, width=80 * mm, height=27 * mm,
                                kind="proportional", hAlign="CENTER"))
        except Exception:
            pass

    story.append(Spacer(1, 20 * mm))

    title_style = ParagraphStyle(
        "cover_title", fontName="Helvetica-Bold", fontSize=28,
        textColor=NAVY, alignment=1, leading=32,
    )
    sub_style = ParagraphStyle(
        "cover_sub", fontName="Helvetica-Bold", fontSize=13,
        textColor=NAVY_LIGHT, alignment=1, leading=17,
    )
    meta_style = ParagraphStyle(
        "cover_meta", fontName="Helvetica", fontSize=10,
        textColor=NAVY, alignment=1, leading=15,
    )
    small_style = ParagraphStyle(
        "cover_small", fontName="Courier", fontSize=8,
        textColor=TEXT_MUTED, alignment=1, leading=12,
    )

    story.append(Paragraph("RAPPORT D'EXPERTISE", title_style))
    story.append(Paragraph("TECHNIQUE", title_style))
    story.append(Spacer(1, 8 * mm))
    client_name = (report.get("client_snapshot") or {}).get("name") or "—"
    story.append(Paragraph(f"PRÉPARÉ POUR<br/><b>{client_name.upper()}</b>", sub_style))
    story.append(Spacer(1, 20 * mm))

    proj = report.get("project_name") or "—"
    city = report.get("project_city") or ""
    addr = report.get("project_address") or ""
    project_line = f"<b>PROJET :</b> {proj}"
    if addr or city:
        project_line += f"<br/>{addr}"
        if city:
            project_line += f"{'  ·  ' if addr else ''}{city}"
    story.append(Paragraph(project_line, meta_style))

    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        f"Date d'inspection : <b>{_date_fr(report.get('inspection_date'))}</b><br/>"
        f"Inspecteur : <b>{report.get('inspector_name') or 'Cédrick Pimparé'}</b><br/>"
        f"{report.get('inspector_title') or 'Expert Portes Commerciales – Portech'}"
        + (f"<br/>Mandaté par : {report['mandated_by']}" if report.get("mandated_by") else ""),
        meta_style,
    ))

    story.append(Spacer(1, 30 * mm))
    number = f"RAP-{int(report.get('number', 0)):04d}"
    story.append(Paragraph(f"RÉFÉRENCE {number}", small_style))
    story.append(Paragraph(
        f"{COMPANY['name']} · {COMPANY['email']} · {COMPANY['site']}",
        small_style,
    ))
    return story


def _section_heading(styles, num: str, label: str) -> Paragraph:
    style = ParagraphStyle(
        f"h_{num}", fontName="Helvetica-Bold", fontSize=13,
        textColor=NAVY, leading=17, spaceBefore=6, spaceAfter=4,
    )
    return Paragraph(f"<b>{num}. {label.upper()}</b>", style)


def _subheading(styles, text: str) -> Paragraph:
    style = ParagraphStyle(
        "sub", fontName="Helvetica-Bold", fontSize=10.5,
        textColor=NAVY, leading=14, spaceBefore=3, spaceAfter=2,
    )
    return Paragraph(text, style)


def _paragraph_free(styles, text: str) -> Paragraph:
    """Preserve line breaks and blank lines from a user-typed textarea."""
    if not text:
        return Paragraph("<i>—</i>", styles["body"])
    # Blank lines → paragraph breaks ; single \n → <br/>
    parts = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    html = "<br/><br/>".join(p.replace("\n", "<br/>") for p in parts)
    return Paragraph(html, styles["body"])


def _door_specs_table(styles, door: dict) -> Table:
    """Render the technical description block of one door."""
    fields = [
        ("Modèle", door.get("model")),
        ("Série", door.get("series")),
        ("Dimensions", _dims_fmt(door.get("width_mm"), door.get("height_mm"))),
        ("Finition", door.get("finish")),
        ("Configuration", door.get("configuration")),
        ("Pentures", door.get("hinges")),
        ("Serrure", door.get("lock")),
        ("Gâche électrique", door.get("electric_strike")),
        ("Seuil", door.get("threshold")),
        ("Trim / Moulure", door.get("trim")),
    ]
    rows = [
        [Paragraph(f"<b>{k}</b>", styles["body"]),
         Paragraph(v or "—", styles["body"])]
        for k, v in fields if v
    ]
    if not rows:
        rows = [[Paragraph("—", styles["body"]), Paragraph("", styles["body"])]]
    t = Table(rows, colWidths=[42 * mm, 118 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.3, NAVY_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, NAVY_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), BG_LIGHT),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _dims_fmt(w: float | None, h: float | None) -> str:
    if not w and not h:
        return ""
    parts = []
    if w:
        parts.append(f"{int(w) if float(w).is_integer() else w} mm L")
    if h:
        parts.append(f"{int(h) if float(h).is_integer() else h} mm H")
    return " × ".join(parts)


def _bullet_list(styles, items: list) -> list:
    """Render a list of bullet items as flowables."""
    flowables = []
    bullet_style = ParagraphStyle(
        "bullet", parent=styles["body"], leftIndent=12, bulletIndent=2,
        spaceAfter=1, spaceBefore=0,
    )
    for it in items or []:
        text = str(it or "").strip()
        if text:
            flowables.append(Paragraph(f"•  {text}", bullet_style))
    if not flowables:
        flowables.append(Paragraph("<i>—</i>", styles["body"]))
    return flowables


def _door_photos_flowables(photos: list[dict], uploads_dir: str) -> list:
    """Return one Table per pair of photos so ReportLab can page-break
    between pairs (a single big Table with N rows sometimes silently
    truncates when it doesn't fit — we hit this at 13 photos)."""
    if not photos:
        return []
    caption_style = ParagraphStyle(
        "caption", fontName="Helvetica-Oblique", fontSize=7.5,
        textColor=TEXT_MUTED, alignment=1, leading=10, spaceBefore=1,
    )
    max_w = 76 * mm
    max_h = 55 * mm

    cells: list = []
    for p in sorted(photos, key=lambda x: x.get("order", 0)):
        path = os.path.join(uploads_dir, p.get("filename", ""))
        if not os.path.exists(path):
            continue
        try:
            img = Image(path, width=max_w, height=max_h, kind="proportional")
        except Exception:
            # Corrupt / unsupported file — skip silently rather than crash the PDF.
            continue
        cap = p.get("caption") or ""
        cell = [img]
        if cap:
            cell.append(Spacer(1, 1 * mm))
            cell.append(Paragraph(cap, caption_style))
        cells.append(cell)

    if not cells:
        return []

    tables: list = []
    for i in range(0, len(cells), 2):
        pair = cells[i:i + 2]
        while len(pair) < 2:
            pair.append("")
        t = Table([pair], colWidths=[80 * mm, 80 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        tables.append(t)
    return tables


def _door_photos_grid(photos: list[dict], uploads_dir: str):
    """Legacy wrapper — kept for backward compat but now returns a list."""
    return _door_photos_flowables(photos, uploads_dir)


def render_expert_report_pdf(report: dict, uploads_dir: str) -> bytes:
    """Render the full technical inspection report PDF.

    `uploads_dir` : absolute path to the directory holding this report's
    photo files. Files are referenced by `report["photos"][*]["filename"]`.
    """
    s = _styles()
    buf, doc = _build_doc()
    story = []

    # ── Cover ─────────────────────────────────────────────────
    story.extend(_report_cover(s, report))
    story.append(PageBreak())

    # ── Section 1 — Purpose ──────────────────────────────────
    story.append(_section_heading(s, "1", "Objet du rapport"))
    story.append(_paragraph_free(s, report.get("purpose") or ""))
    story.append(Spacer(1, 5 * mm))

    # ── Section 2 — Technical description ────────────────────
    story.append(_section_heading(s, "2", "Description technique des ensembles inspectés"))
    doors = report.get("doors") or []
    if not doors:
        story.append(Paragraph("<i>Aucune porte inspectée n'a été saisie.</i>", s["body"]))
    for i, d in enumerate(doors, start=1):
        title = f"2.{i} {d.get('tag') or f'Porte {i}'}"
        if d.get("location"):
            title += f" — <font color='#4b5d7a'>{d['location']}</font>"
        story.append(_subheading(s, title))
        story.append(_door_specs_table(s, d))
        if d.get("other_specs"):
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(
                f"<b>Notes :</b> {d['other_specs']}", s["body"],
            ))
        story.append(Spacer(1, 4 * mm))

    story.append(Spacer(1, 3 * mm))

    # ── Section 3 — Deficiencies (with photos) ───────────────
    story.append(_section_heading(s, "3", "Déficiences observées"))
    photos_by_door: dict[int, list[dict]] = {}
    for p in report.get("photos") or []:
        idx = p.get("door_index")
        if idx is None:
            continue
        photos_by_door.setdefault(int(idx), []).append(p)

    any_deficiency = False
    for i, d in enumerate(doors, start=1):
        if not (d.get("observations") or d.get("impacts")
                 or d.get("recommendation") or photos_by_door.get(i - 1)):
            continue
        any_deficiency = True
        title = f"3.{i} {d.get('tag') or f'Porte {i}'}"
        story.append(_subheading(s, title))
        # Observations
        if d.get("observations"):
            story.append(Paragraph("<b>Observations :</b>", s["body"]))
            story.extend(_bullet_list(s, d["observations"]))
        # Impacts
        if d.get("impacts"):
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph("<b>Impacts :</b>", s["body"]))
            story.extend(_bullet_list(s, d["impacts"]))
        # Recommendation
        if d.get("recommendation"):
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(
                f"<b>Recommandation :</b> {d['recommendation']}", s["body"],
            ))
        # Photos
        photo_flowables = _door_photos_flowables(photos_by_door.get(i - 1, []), uploads_dir)
        if photo_flowables:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph("<b>Photos :</b>", s["body"]))
            story.extend(photo_flowables)
        story.append(Spacer(1, 4 * mm))

    if not any_deficiency:
        story.append(Paragraph(
            "<i>Aucune déficience n'a été relevée lors de l'inspection.</i>",
            s["body"],
        ))
        story.append(Spacer(1, 5 * mm))

    # ── Section 4 — Risks & liability ────────────────────────
    story.append(_section_heading(s, "4", "Risques et responsabilités potentielles"))
    story.append(_paragraph_free(s, report.get("risks") or ""))
    story.append(Spacer(1, 5 * mm))

    # ── Section 5 — Conclusion ───────────────────────────────
    story.append(_section_heading(s, "5", "Conclusion"))
    story.append(_paragraph_free(s, report.get("conclusion") or ""))
    story.append(Spacer(1, 15 * mm))

    # Signature block
    sig_style = ParagraphStyle(
        "sig", fontName="Helvetica", fontSize=10, textColor=NAVY, leading=14,
    )
    story.append(Paragraph(
        f"<b>Rédigé par :</b><br/>"
        f"{report.get('inspector_name') or 'Cédrick Pimparé'}<br/>"
        f"<font size='8' color='#4b5d7a'>{report.get('inspector_title') or ''}</font><br/><br/>"
        f"<b>Date :</b> {_date_fr(report.get('inspection_date'))}",
        sig_style,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()

