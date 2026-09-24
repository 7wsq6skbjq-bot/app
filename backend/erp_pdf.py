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
    "tagline": "Quincaillerie et portes commerciales en aluminium — Grand Montréal",
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


def _items_table_money(items: list[dict], hide_zero: bool = False) -> Table:
    """Items table for invoice & PO (with prices). When ``hide_zero`` is set,
    lines without a price show nothing instead of "0,00 $"."""
    header = ["Description", "Qté", "Prix unitaire", "Total"]
    data = [header]
    for it in items or []:
        qty = it.get("quantity") or 0
        unit = it.get("unit_price") or 0
        total = it.get("total")
        if total is None:
            total = float(qty) * float(unit)
        unit_s = "" if (hide_zero and not float(unit or 0)) else _money(unit)
        total_s = "" if (hide_zero and not float(total or 0)) else _money(total)
        data.append([
            Paragraph(it.get("description") or "—", _styles()["body"]),
            f"{qty}",
            unit_s,
            total_s,
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


def render_statement_pdf(customer: dict, invoices: list, *,
                          as_of: str | None = None, only_unpaid: bool = True) -> bytes:
    """État de compte — statement of account for one customer.

    Lists the customer's invoices (unpaid by default) with the balance due,
    then a grand total. `invoices` are raw invoice dicts already filtered to
    this customer.
    """
    s = _styles()
    buf, doc = _build_doc()
    story = []

    story.append(_header(s, "ÉTAT DE COMPTE", _date_fr(as_of) if as_of else _date_fr(None), None))
    story.append(Spacer(1, 8 * mm))

    party = _party_block(s, "Client", customer or {})
    meta = _meta_grid(s, [
        ("Date", _date_fr(as_of)),
        ("Type", "Soldes dus" if only_unpaid else "Historique complet"),
    ])
    side = Table([[party, meta]], colWidths=[95 * mm, 75 * mm])
    side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(side)
    story.append(Spacer(1, 6 * mm))

    header = ["No facture", "Date", "Échéance", "Statut", "Solde dû"]
    data = [header]
    balance = 0.0
    for inv in invoices:
        num = f"FAC-{int(inv.get('number', 0)):04d}"
        total = float(inv.get("total") or 0)
        balance += total
        data.append([
            num, _date_fr(inv.get("date")), _date_fr(inv.get("due_date")),
            (inv.get("status") or "—").upper(), _money(total),
        ])
    if len(data) == 1:
        data.append(["—", "—", "—", "—", _money(0)])
    t = Table(data, colWidths=[30 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), NAVY),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, NAVY_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 4 * mm))

    tot = Table([["SOLDE TOTAL DÛ", _money(balance)]], colWidths=[60 * mm, 40 * mm], hAlign="RIGHT")
    tot.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEABOVE", (0, 0), (-1, 0), 1.5, NAVY),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(tot)

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "Ce document est un état de compte à titre informatif. Pour toute "
        "question ou pour régler un solde, communiquez avec nous à "
        f"<b>{COMPANY['email']}</b>. Merci de votre confiance.",
        s["footer"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


SALES_CONDITIONS = [
    ("1. ACCEPTATION DE LA SOUMISSION",
     "L'acceptation de la soumission par le client constitue une autorisation ferme de procéder à la commande des matériaux, à la fabrication et/ou à l'exécution des travaux décrits à la soumission. Toute acceptation écrite, électronique ou toute autorisation permettant à Portech de débuter les travaux ou de commander les matériaux sera considérée comme une acceptation des présentes conditions. La soumission est valide pour une période de 30 jours, sauf indication contraire."),
    ("2. DESCRIPTION DES PRODUITS",
     "Les produits fournis sont ceux décrits à la soumission. Les dimensions, modèles, finis, couleurs, types de portes, cadres, vitrages, quincailleries et autres caractéristiques doivent être vérifiés et approuvés par le client avant la mise en production. Les représentations, images, dessins ou illustrations présentés dans une soumission sont à titre indicatif seulement et peuvent différer légèrement du produit final."),
    ("3. PORTES SUR MESURE",
     "Toute porte fabriquée ou commandée selon des dimensions, spécifications ou exigences particulières du client est considérée comme un produit sur mesure. Une fois la commande approuvée et/ou la fabrication débutée, les portes sur mesure ne peuvent être annulées, retournées ou remboursées, sauf entente écrite contraire de Portech. Le client est responsable de vérifier les dimensions, le sens d'ouverture, le type de porte, le fini, les ouvertures, la quincaillerie et toute autre spécification avant l'approbation finale."),
    ("4. PRISE DE MESURES",
     "Lorsque la prise de mesures est effectuée par Portech, les dimensions relevées servent de référence pour la fabrication. Lorsque les dimensions sont fournies par le client, un entrepreneur, un chargé de projet ou tout autre intervenant, la responsabilité de leur exactitude revient à la partie ayant fourni ces informations. Toute modification nécessaire en raison de dimensions incorrectes, de conditions existantes non divulguées ou de renseignements inexacts pourra entraîner des frais supplémentaires."),
    ("5. CONDITIONS EXISTANTES",
     "Le client reconnaît que les travaux peuvent être effectués sur des bâtiments et installations existants présentant certaines conditions imprévues. Portech ne peut être tenue responsable des conditions cachées, des défauts de structure, des murs hors niveau, des ouvertures non conformes, des problèmes de plomberie, d'électricité ou de structure, ni de toute autre condition existante qui n'était pas raisonnablement identifiable au moment de la soumission. Lorsque de telles conditions nécessitent du travail supplémentaire, celui-ci pourra faire l'objet d'une facturation additionnelle."),
    ("6. MODIFICATIONS ET TRAVAUX SUPPLÉMENTAIRES",
     "Toute modification demandée par le client après l'acceptation de la soumission, de même que tout travail non prévu dans celle-ci, pourra entraîner des frais supplémentaires. Les travaux supplémentaires seront, lorsque possible, soumis à l'approbation du client avant leur exécution. Toutefois, lorsqu'une intervention immédiate est nécessaire afin de poursuivre correctement les travaux ou d'assurer la sécurité des lieux, Portech pourra effectuer les travaux nécessaires et les facturer au client."),
    ("7. DÉLAIS",
     "Les délais de fabrication, d'approvisionnement, de livraison et d'installation sont donnés à titre estimatif. Portech ne peut être tenue responsable des retards causés par les fabricants, fournisseurs, transporteurs, conditions de chantier, retards d'autres intervenants, force majeure ou toute autre circonstance indépendante de son contrôle. Un retard dans la réception des matériaux ou composantes ne constitue pas un motif d'annulation sans l'accord écrit de Portech."),
    ("8. LIVRAISON",
     "La livraison est incluse uniquement lorsqu'elle est expressément indiquée dans la soumission. Le client doit s'assurer que les lieux sont accessibles et prêts à recevoir les matériaux. Toute livraison supplémentaire occasionnée par une absence du client, un accès impossible, un chantier non prêt ou toute autre situation indépendante de Portech pourra être facturée en supplément."),
    ("9. INSTALLATION",
     "Lorsque l'installation est incluse, celle-ci comprend uniquement les travaux expressément décrits à la soumission. Les travaux de finition, de peinture, de réparation de murs, de maçonnerie, de modification structurale, d'électricité ou tout autre travail non spécifiquement indiqué sont exclus, sauf mention contraire."),
    ("10. QUINCAILLERIE ET ACCESSOIRES",
     "Les portes et leurs composantes sont fournies avec la quincaillerie spécifiée dans la soumission. Toute modification de modèle, de finition, de fonction ou de quantité après l'approbation de la commande peut entraîner des frais supplémentaires ainsi qu'un délai additionnel. La compatibilité de la quincaillerie avec les systèmes existants doit être confirmée avant la commande lorsque celle-ci dépend d'une installation existante."),
    ("11. PRIX ET TAXES",
     "Les prix indiqués dans la soumission sont ceux applicables au moment de son émission et selon les conditions qui y sont décrites. Les taxes applicables sont facturées en sus, lorsqu'elles sont exigibles. Toute augmentation imposée par un fabricant ou fournisseur après l'expiration de la période de validité de la soumission pourra être répercutée au client."),
    ("12. CONDITIONS DE PAIEMENT",
     "Sauf indication contraire dans la soumission : dépôt de 50 % à l'acceptation de la commande ; solde payable à la livraison. Les produits fabriqués sur mesure peuvent nécessiter le paiement du dépôt avant leur mise en production. Tout montant en souffrance pourra entraîner la suspension des travaux, des commandes ou des livraisons jusqu'au règlement du compte."),
    ("13. PROPRIÉTÉ DES MATÉRIAUX",
     "Les matériaux demeurent la propriété de Portech jusqu'au paiement complet des sommes dues, dans la mesure permise par la loi. Aucune propriété sur les matériaux non entièrement payés ne sera transférée au client."),
    ("14. INSPECTION ET ACCEPTATION",
     "Le client doit inspecter les produits dès leur réception et signaler toute anomalie apparente dans un délai raisonnable. Les dommages visibles lors de la livraison doivent être signalés immédiatement afin de permettre les démarches nécessaires auprès du transporteur ou du fournisseur. Une installation ou une utilisation du produit sans réserve pourra être considérée comme une acceptation de son état apparent."),
    ("15. GARANTIE",
     "Les produits sont couverts, lorsqu'applicable, par la garantie offerte par leur fabricant respectif. La garantie ne couvre pas les dommages résultant notamment d'une mauvaise utilisation, d'une installation inadéquate effectuée par un tiers, de modifications non autorisées, d'un entretien insuffisant, d'un usage abusif ou de conditions anormales. La garantie de Portech, lorsqu'elle s'applique, est limitée aux travaux et produits fournis par Portech et ne couvre pas les dommages indirects, pertes d'exploitation ou autres dommages consécutifs."),
    ("16. ANNULATION",
     "Une commande peut être annulée uniquement avec l'accord écrit de Portech. Lorsque des matériaux ont déjà été commandés, fabriqués ou mis en production, les frais engagés ainsi que les frais d'annulation, de retour ou de restockage applicables pourront être facturés au client. Les produits fabriqués sur mesure ne sont généralement pas annulables ni retournables après le début de leur fabrication."),
    ("17. RESPONSABILITÉ DU CLIENT",
     "Le client demeure responsable de fournir à Portech toutes les informations nécessaires à la bonne exécution du mandat, notamment les dimensions, plans, exigences particulières, restrictions d'accès, conditions de chantier et spécifications applicables. Le client doit également s'assurer que les lieux sont accessibles, sécuritaires et prêts pour l'exécution des travaux."),
    ("18. EXCLUSIONS",
     "Sauf indication contraire dans la soumission, sont notamment exclus : les travaux structuraux ; les travaux électriques ; la peinture et les travaux de finition ; les réparations de murs ou de maçonnerie ; les travaux de cadrage non spécifiés ; les permis et autorisations ; les travaux effectués par d'autres entrepreneurs ; toute modification rendue nécessaire par une condition existante non connue au moment de la soumission."),
    ("19. CONFORMITÉ",
     "Le client reconnaît que les produits doivent être utilisés conformément à leur fonction prévue et aux exigences applicables au projet. Lorsque des exigences particulières de code, d'accessibilité, de sécurité incendie ou autres normes spécifiques s'appliquent au projet, celles-ci doivent être communiquées à Portech avant la commande afin de permettre leur prise en considération dans la soumission."),
    ("20. LIMITATION DE RESPONSABILITÉ",
     "Portech ne pourra être tenue responsable des dommages indirects, pertes de profits, pertes d'exploitation, pertes de revenus ou autres dommages consécutifs découlant d'un retard, d'une interruption de travaux ou d'un défaut d'un produit fourni par un fabricant tiers, sous réserve des droits impératifs prévus par la loi."),
    ("21. ACCEPTATION DES CONDITIONS",
     "En acceptant la soumission, le client reconnaît avoir pris connaissance des présentes conditions de vente et les accepter intégralement. Les présentes conditions prévalent sur toute condition d'achat ou autre condition provenant du client, à moins qu'une entente écrite contraire ait été conclue avec Portech."),
]


def _sales_conditions_story(styles: dict, q: dict) -> list:
    """Annexe des conditions de vente (contrat) ajoutee a chaque soumission."""
    clause_title = ParagraphStyle(
        "cond_title", parent=styles["body"], fontName="Helvetica-Bold",
        fontSize=8.5, spaceBefore=5, spaceAfter=1, textColor=NAVY)
    clause_body = ParagraphStyle(
        "cond_body", parent=styles["body"], fontSize=7.5, leading=9.5,
        alignment=4, spaceAfter=2)
    out = [PageBreak(),
           Paragraph("PORTECH — CONDITIONS DE VENTE", styles["title"]),
           Paragraph("Portes commerciales en aluminium — Annexe à la soumission", styles["label"]),
           Spacer(1, 3 * mm),
           Paragraph(
               "Les présentes conditions de vente font partie intégrante de "
               "toute soumission émise par Portech relativement à la fourniture, "
               "la fabrication, la modification, la livraison ou l'installation "
               "de portes commerciales en aluminium et de leurs composantes.", clause_body),
           Spacer(1, 2 * mm)]
    for title, body in SALES_CONDITIONS:
        out.append(Paragraph(title, clause_title))
        out.append(Paragraph(body, clause_body))
    out.append(Spacer(1, 4 * mm))
    out.append(Paragraph("ACCEPTATION DU CLIENT", clause_title))
    out.append(Paragraph(
        "Par la présente, le client confirme avoir pris connaissance de la "
        "soumission et des présentes conditions de vente et accepte les "
        "produits, prix, modalités et conditions qui y sont indiqués.", clause_body))
    num = q.get("number")
    num_s = f"SOU-{num:05d}" if isinstance(num, int) else (str(num) if num else "____________")
    sig_rows = [
        ["Soumission no :", num_s, "Date :", str(q.get("date") or "____________")],
        ["Projet :", str(q.get("project") or "____________________"), "", ""],
        ["Nom :", "____________________", "Signature :", "____________________"],
    ]
    sig = Table(sig_rows, colWidths=[26 * mm, 60 * mm, 26 * mm, 60 * mm])
    sig.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    out.append(Spacer(1, 3 * mm))
    out.append(sig)
    return out



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

    story.append(_items_table_money(q.get("items", []), hide_zero=True))
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

    # Annexe — conditions de vente (contrat), seulement si demandé
    if q.get("include_sales_conditions"):
        story += _sales_conditions_story(s, q)

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


# ============================================================
# Mosquito screens (Moustiquaires) — fabrication order PDF
# ============================================================
def _mosquito_items_table(items: list[dict]) -> Table:
    """Items table for a mosquito-screen fabrication order.

    Columns : # / Nom / Largeur (mm) / Hauteur (mm) / Qté / Cadre / Toile /
              Attache / Notes
    """
    header = [
        "#", "Identifiant", "Largeur\n(mm)", "Hauteur\n(mm)", "Qté",
        "Cadre", "Toile", "Attache", "Notes",
    ]
    data = [header]
    s = _styles()
    for idx, it in enumerate(items or [], start=1):
        data.append([
            str(idx),
            Paragraph(f"<b>{it.get('name') or '—'}</b>", s["body"]),
            f"{int(it.get('width_mm') or 0)}",
            f"{int(it.get('height_mm') or 0)}",
            f"{int(it.get('qty') or 0)}",
            Paragraph(it.get("frame_color") or "—", s["body"]),
            Paragraph(it.get("mesh_type") or "—", s["body"]),
            Paragraph(it.get("attachment_type") or "—", s["body"]),
            Paragraph(it.get("notes") or "", s["body"]),
        ])
    t = Table(
        data,
        colWidths=[
            8 * mm, 32 * mm, 15 * mm, 15 * mm, 10 * mm,
            22 * mm, 28 * mm, 22 * mm, 32 * mm,
        ],
        repeatRows=1,
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, NAVY_BORDER),
        ("TEXTCOLOR", (0, 1), (-1, -1), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def render_mosquito_screens_pdf(order: dict) -> bytes:
    """Render a "Bon de fabrication — Moustiquaires" PDF.

    `order` is expected to contain:
        order_number, date, needed_by, mode ("interne"|"fournisseur"),
        supplier_snapshot? {name, address...}, customer_name?, project_ref?,
        project_address?, status, items [{name, width_mm, height_mm, qty,
        frame_color, mesh_type, attachment_type, notes}], total_qty, notes
    """
    s = _styles()
    buf, doc = _build_doc()
    story = []
    number = order.get("order_number") or "MS-XXXX"
    status = (order.get("status") or "").upper() or None
    story.append(_header(s, "BON DE FABRICATION — MOUSTIQUAIRES",
                          number, status))
    story.append(Spacer(1, 8 * mm))

    mode = order.get("mode") or "interne"
    if mode == "fournisseur" and order.get("supplier_snapshot"):
        party = _party_block(s, "Fournisseur — fabrication",
                              order.get("supplier_snapshot") or {})
    else:
        internal = {
            "name": COMPANY["name"],
            "address_line1": "Fabrication à l'interne (atelier Portech)",
            "email": COMPANY["email"],
        }
        party = _party_block(s, "Fabrication", internal)

    meta_entries = [
        ("Numéro", number),
        ("Date émission", _date_fr(order.get("date"))),
        ("Requis pour", _date_fr(order.get("needed_by"))
                        if order.get("needed_by") else "—"),
        ("Mode", "Fabrication interne" if mode == "interne"
                 else "Fabrication fournisseur"),
        ("Statut", (order.get("status") or "brouillon").capitalize()),
        ("Qté totale", str(order.get("total_qty") or 0)),
    ]
    if order.get("customer_name"):
        meta_entries.append(("Client final", order["customer_name"]))
    if order.get("project_ref"):
        meta_entries.append(("Projet / Réf.", order["project_ref"]))
    meta = _meta_grid(s, meta_entries)

    side_by_side = Table([[party, meta]], colWidths=[80 * mm, 90 * mm])
    side_by_side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(side_by_side)
    story.append(Spacer(1, 6 * mm))

    if order.get("project_address"):
        story.append(Paragraph(
            f"<b>Adresse du projet :</b> {order['project_address']}",
            s["body"],
        ))
        story.append(Spacer(1, 4 * mm))

    story.append(_mosquito_items_table(order.get("items", [])))
    story.append(Spacer(1, 6 * mm))

    # Total quantity strip
    total_qty = int(order.get("total_qty") or 0)
    unit_count = len(order.get("items", []) or [])
    strip = Table(
        [[f"{unit_count} modèle(s) · {total_qty} unité(s) au total"]],
        colWidths=[170 * mm],
    )
    strip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(strip)
    story.append(Spacer(1, 8 * mm))

    # Instructions / notes fabricant
    if mode == "fournisseur":
        instructions = (
            "<b>Instructions au fournisseur</b><br/>"
            "Merci de nous confirmer par retour de courriel : le <b>prix "
            "unitaire</b>, le <b>délai de fabrication</b> et le <b>mode "
            "d'expédition</b>. Les dimensions ci-dessus sont exprimées "
            "en <b>millimètres (mm)</b> — largeur × hauteur. "
            "Toute question ou clarification, contactez-nous avant de "
            "démarrer la fabrication."
        )
    else:
        instructions = (
            "<b>Notes atelier</b><br/>"
            "Toutes les dimensions sont en <b>millimètres (mm)</b> — "
            "largeur × hauteur. Vérifier le stock de toile et de cadre "
            "avant de démarrer. Cocher chaque unité au fur et à mesure "
            "sur la copie papier."
        )
    story.append(Paragraph(instructions, s["body"]))

    if order.get("notes"):
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(
            f"<b>Notes :</b><br/>{order['notes']}", s["body"],
        ))

    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "Pour toute question, communiquez avec info@portech.info — merci.",
        s["footer"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()



# ============================================================
# Client-facing AT door order form — INTERACTIVE (AcroForm)
# ============================================================
def render_client_at_order_form_pdf() -> bytes:
    """Blank Portech-branded AT door order form — 2 pages, TRUE interactive
    PDF with real AcroForm text fields and check-boxes.

    Meant to be emailed to glazier clients ; they open in Adobe/Preview,
    click each field, tick the boxes, save and return by email.
    """
    from reportlab.pdfgen import canvas as canvas_mod

    buf = io.BytesIO()
    W, H = LETTER                        # 612 x 792 pt (8.5" x 11")
    c = canvas_mod.Canvas(buf, pagesize=LETTER)
    c.setTitle("Portech — Formulaire de commande de porte AT")
    form = c.acroForm

    field_counter = {"n": 0}

    def _uniq(prefix):
        field_counter["n"] += 1
        return f"{prefix}_{field_counter['n']}"

    def draw_banner(cnv, page_num):
        cnv.saveState()
        cnv.setFillColor(NAVY)
        cnv.rect(0, H - 22 * mm, W, 22 * mm, fill=1, stroke=0)
        # High-resolution white P-mark (335x335) drawn crisply as an icon
        mark_path = "/app/frontend/public/brand/portech-mark-white.png"
        if os.path.exists(mark_path):
            try:
                cnv.drawImage(mark_path, 12 * mm, H - 20 * mm,
                               width=16 * mm, height=16 * mm,
                               preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        # Draw PORTECH wordmark as text at high resolution
        cnv.setFillColor(colors.white)
        cnv.setFont("Helvetica-Bold", 20)
        cnv.drawString(31 * mm, H - 12 * mm, "PORTECH")
        cnv.setFont("Helvetica", 9)
        cnv.drawString(31 * mm, H - 17 * mm,
                        "Formulaire de commande \u2014 Porte AT")
        cnv.setFont("Courier", 7.5)
        cnv.setFillColor(colors.HexColor("#9bb6d8"))
        cnv.drawRightString(W - 12 * mm, H - 12 * mm,
                             f"V1  \u00b7  Page {page_num} / 2")
        cnv.drawRightString(W - 12 * mm, H - 17 * mm,
                             "Quincaillerie et portes commerciales en aluminium")
        cnv.restoreState()

    def draw_footer(cnv):
        cnv.saveState()
        cnv.setFillColor(NAVY)
        cnv.rect(0, 0, W, 10 * mm, fill=1, stroke=0)
        cnv.setFillColor(colors.white)
        cnv.setFont("Helvetica", 7.5)
        cnv.drawCentredString(
            W / 2, 4 * mm,
            "Retourner \u00e0 info@portech.info  \u00b7  438-376-4177  "
            "\u00b7  portech.info  \u00b7  Portech \u2014 "
            "Quincaillerie et portes commerciales en aluminium",
        )
        cnv.restoreState()

    def section_title(cnv, text, y):
        cnv.saveState()
        cnv.setFillColor(NAVY)
        cnv.rect(12 * mm, y - 4.2 * mm, W - 24 * mm, 4.6 * mm,
                 fill=1, stroke=0)
        cnv.setFillColor(colors.white)
        cnv.setFont("Helvetica-Bold", 8.5)
        cnv.drawString(14 * mm, y - 3.2 * mm, text.upper())
        cnv.restoreState()

    def label(cnv, text, x, y, size=7):
        cnv.saveState()
        cnv.setFont("Helvetica-Bold", size)
        cnv.setFillColor(TEXT_MUTED)
        cnv.drawString(x, y, text.upper())
        cnv.restoreState()

    def text_field(name, x, y, w, h, tooltip=""):
        form.textfield(
            name=name, tooltip=tooltip,
            x=x, y=y, width=w, height=h,
            borderStyle="underlined", borderWidth=0.5,
            borderColor=NAVY_BORDER, fillColor=colors.HexColor("#f7f9fc"),
            textColor=NAVY, forceBorder=True,
            fontName="Helvetica", fontSize=9,
        )

    def multiline_field(name, x, y, w, h, tooltip=""):
        form.textfield(
            name=name, tooltip=tooltip,
            x=x, y=y, width=w, height=h,
            borderStyle="solid", borderWidth=0.5,
            borderColor=NAVY_BORDER, fillColor=colors.HexColor("#f7f9fc"),
            textColor=NAVY, forceBorder=True,
            fontName="Helvetica", fontSize=9,
            fieldFlags="multiline",
        )

    def check(name, x, y, tooltip="", size=10):
        form.checkbox(
            name=name, tooltip=tooltip,
            x=x, y=y, size=size,
            buttonStyle="check", shape="square",
            fillColor=colors.HexColor("#f7f9fc"),
            textColor=NAVY, borderColor=NAVY,
            borderWidth=0.8, forceBorder=True, checked=False,
        )

    def check_with_label(cnv, name, lbl, x, y,
                          size=9, gap=1.5, font_size=8.5):
        check(name, x, y - 0.5, tooltip=lbl, size=size)
        cnv.setFont("Helvetica", font_size)
        cnv.setFillColor(NAVY)
        cnv.drawString(x + size + gap * mm, y + 1.5, lbl)

    def labeled_field(cnv, lbl, x, y, w, name):
        """`y` is the label baseline. Field sits 6mm below with a safe gap."""
        label(cnv, lbl, x, y)
        text_field(name, x, y - 6 * mm, w, 4.5 * mm, tooltip=lbl)

    col1_x = 14 * mm
    col2_x = W / 2 + 4 * mm
    col_w = W / 2 - 20 * mm

    # ============ PAGE 1 ============
    draw_banner(c, 1)
    draw_footer(c)

    y = H - 27 * mm
    section_title(c, "1. Client & projet", y)
    y -= 8 * mm
    labeled_field(c, "Client",       col1_x, y, col_w, _uniq("client"))
    labeled_field(c, "N\u00b0 commande", col2_x, y, col_w, _uniq("po_number"))
    y -= 13 * mm
    labeled_field(c, "Responsable",  col1_x, y, col_w, _uniq("contact"))
    labeled_field(c, "Nom du projet", col2_x, y, col_w, _uniq("project"))
    y -= 13 * mm
    labeled_field(c, "Date",         col1_x, y, col_w, _uniq("date"))
    labeled_field(c, "Date requise", col2_x, y, col_w, _uniq("date_needed"))
    y -= 13 * mm
    labeled_field(c, "T\u00e9l\u00e9phone", col1_x, y, col_w, _uniq("phone"))
    labeled_field(c, "Courriel",     col2_x, y, col_w, _uniq("email"))

    y -= 12 * mm
    section_title(c, "2. Mod\u00e8le de porte (cocher un choix)", y)
    y -= 8 * mm
    models = [
        ("Porte non-isol\u00e9e \u00b7 AT1000",  "model_at1000"),
        ("Porte isol\u00e9e \u00b7 ATi1000",     "model_ati1000"),
        ("Porte non-isol\u00e9e \u00b7 AT2000",  "model_at2000"),
        ("Porte isol\u00e9e \u00b7 ATi2000",     "model_ati2000"),
    ]
    for i, (lbl, nm) in enumerate(models):
        col = i % 2
        row = i // 2
        cx_i = 14 * mm + col * (W / 2 - 12 * mm)
        cy_i = y - row * 6.5 * mm
        check_with_label(c, nm, lbl, cx_i, cy_i)
    y -= 15 * mm

    section_title(c, "3. Dimensions", y)
    y -= 8 * mm
    check_with_label(c, "dim_standard_36x84",
                      "Standard 36\u00d784\" (914 \u00d7 2134 mm)",
                      14 * mm, y, size=11, font_size=10)
    y -= 8 * mm
    label(c, "Sur mesure \u2014 dimensions (L \u00d7 H)", 14 * mm, y)
    text_field(_uniq("dim_custom"), 14 * mm, y - 6 * mm,
                col_w, 4.5 * mm, tooltip="Largeur x Hauteur")
    label(c, "Ouverture (rough)", col2_x, y)
    text_field(_uniq("dim_opening"), col2_x, y - 6 * mm,
                col_w, 4.5 * mm, tooltip="Dimensions de l'ouverture")
    y -= 13 * mm
    label(c, "Fabrication", 14 * mm, y)
    text_field(_uniq("dim_fab"), 14 * mm, y - 6 * mm,
                col_w, 4.5 * mm, tooltip="Dimensions de fabrication")
    label(c, "Tag / rep\u00e8re", col2_x, y)
    text_field(_uniq("tag"), col2_x, y - 6 * mm,
                col_w, 4.5 * mm, tooltip="Identifiant de la porte")
    y -= 12 * mm

    section_title(c, "4. Fini aluminium \u2014 ext\u00e9rieur", y)
    y -= 7 * mm
    finishes = [
        "Anodis\u00e9 clair", "Noir",
        "Bronze", "Dark Bronze",
        "Champagne", "Mill finish (aucune anodisation)",
    ]
    for i, name in enumerate(finishes):
        col = i % 3
        row = i // 3
        cx_i = 14 * mm + col * (W - 28 * mm) / 3
        cy_i = y - row * 5.5 * mm
        check_with_label(c, f"finish_ext_{i}", name, cx_i, cy_i)
    y -= 13 * mm
    label(c, "Code couleur (si applicable)", 14 * mm, y)
    text_field(_uniq("finish_ext_code"), 14 * mm, y - 6 * mm,
                W - 28 * mm, 4.5 * mm)
    y -= 9 * mm

    section_title(c, "5. Fini aluminium \u2014 int\u00e9rieur", y)
    y -= 7 * mm
    for i, name in enumerate(finishes):
        col = i % 3
        row = i // 3
        cx_i = 14 * mm + col * (W - 28 * mm) / 3
        cy_i = y - row * 5.5 * mm
        check_with_label(c, f"finish_int_{i}", name, cx_i, cy_i)
    y -= 13 * mm
    label(c, "Code couleur (si applicable)", 14 * mm, y)
    text_field(_uniq("finish_int_code"), 14 * mm, y - 6 * mm,
                W - 28 * mm, 4.5 * mm)
    y -= 10 * mm

    section_title(c, "6. Sens d'ouverture & quantit\u00e9", y)
    y -= 8 * mm
    # Legend explaining the 6 codes — compact one-liner
    c.setFont("Helvetica", 7.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(
        14 * mm, y,
        "GE = gauche ext.  \u00b7  DE = droite ext.  \u00b7  PE = paire ext."
        "  \u00b7  GI = gauche int.  \u00b7  DI = droite int.  \u00b7  "
        "PI = paire int.",
    )
    y -= 7 * mm
    swings = [
        ("GE", "swing_ge"), ("DE", "swing_de"), ("PE", "swing_pe"),
        ("GI", "swing_gi"), ("DI", "swing_di"), ("PI", "swing_pi"),
    ]
    # 3 columns × 2 rows — short codes + QTÉ box comfortably fit
    swing_cell_w = (W - 28 * mm) / 3
    swing_row_h = 9 * mm
    for i, (lbl, nm) in enumerate(swings):
        col = i % 3
        row = i // 3
        cx_i = 14 * mm + col * swing_cell_w
        cy_i = y - row * swing_row_h
        # Checkbox + short 2-letter code label
        check_with_label(c, nm, lbl, cx_i, cy_i, size=10, font_size=10)
        # QTÉ label + text field on the right of the same cell
        qty_x = cx_i + 22 * mm
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(TEXT_MUTED)
        c.drawString(qty_x, cy_i + 2, "QT\u00c9")
        text_field(nm + "_qty",
                    qty_x + 9 * mm, cy_i - 1 * mm,
                    18 * mm, 5 * mm, tooltip=f"Quantit\u00e9 {lbl}")
    y -= swing_row_h * 2

    # ============ PAGE 2 ============
    c.showPage()
    draw_banner(c, 2)
    draw_footer(c)

    y = H - 27 * mm
    section_title(c, "7. Charni\u00e8res", y)
    y -= 8 * mm
    # Row A — Charnière 4½ + qty 1..4 grouped exclusively with this option
    check_with_label(c, "hinge_std",
                      "Charni\u00e8re 4\u00bd\u00d74\u00d70,134",
                      14 * mm, y, size=10, font_size=9)
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(85 * mm, y + 2, "QT\u00c9 PAR PORTE :")
    check_with_label(c, "hinge_qty_1", "1", 118 * mm, y, size=9, font_size=9)
    check_with_label(c, "hinge_qty_2", "2", 132 * mm, y, size=9, font_size=9)
    check_with_label(c, "hinge_qty_3", "3", 146 * mm, y, size=9, font_size=9)
    check_with_label(c, "hinge_qty_4", "4", 160 * mm, y, size=9, font_size=9)
    y -= 7 * mm
    # Row B — continuous hinges + supply/install
    check_with_label(c, "hinge_cont",
                      "Charni\u00e8re continue", 14 * mm, y,
                      size=10, font_size=9)
    check_with_label(c, "hinge_cont_hd",
                      "Charni\u00e8re continue HD", 80 * mm, y,
                      size=10, font_size=9)
    check_with_label(c, "hinge_supply_install",
                      "Fournir et installer", 140 * mm, y,
                      size=10, font_size=9)
    y -= 12 * mm

    section_title(c, "8. Poign\u00e9es & barres \u00e0 pousser", y)
    y -= 7 * mm
    handles = [
        "Poign\u00e9es 9\" dos \u00e0 dos", "Poign\u00e9e 9\" ext\u00e9rieure",
        "Poign\u00e9e 9\" int\u00e9rieure",
        "Poign\u00e9es 12\" dos \u00e0 dos", "Poign\u00e9e 12\" ext\u00e9rieure",
        "Poign\u00e9e 12\" int\u00e9rieure",
        "Barre \u00e0 pousser tubulaire", "Fournir et installer",
    ]
    for i, name in enumerate(handles):
        col = i % 3
        row = i // 3
        cx_i = 14 * mm + col * (W - 28 * mm) / 3
        cy_i = y - row * 5.5 * mm
        check_with_label(c, f"handle_{i}", name, cx_i, cy_i)
    y -= 18 * mm

    section_title(c, "9. Serrure & s\u00e9curit\u00e9", y)
    y -= 9 * mm
    label(c, "Serrure principale", 14 * mm, y + 1)
    y -= 4.5 * mm
    locks = [
        "Serrure SM 1850 AR", "Barillet ext\u00e9rieur",
        "Barillet int\u00e9rieur", "Barillet manuel int\u00e9rieur",
        "Projection courte (adaptateur MR)",
        "Serrure \u00e0 ressort 4510 AR",
        "Barillet ext\u00e9rieur (4510)",
        "Palette de rel\u00e2che 4590 AR",
    ]
    for i, name in enumerate(locks):
        col = i % 2
        row = i // 2
        cx_i = 14 * mm + col * (W - 28 * mm) / 2
        cy_i = y - row * 5.2 * mm
        check_with_label(c, f"lock_main_{i}", name, cx_i, cy_i,
                          size=8.5, font_size=8)
    y -= 5.2 * 4 * mm + 3 * mm

    label(c, "Barre panique", 14 * mm, y + 1)
    y -= 4.5 * mm
    panics = [
        "Barre panique 8400 AR", "Barre panique 8600 AR",
        "Barillet ext\u00e9rieur (active seulement)",
        "Barillet ext\u00e9rieur sur les 2 battants",
        "Pas de barillet ext\u00e9rieur",
        "Barillet manuel int\u00e9rieur (panique)",
    ]
    for i, name in enumerate(panics):
        col = i % 2
        row = i // 2
        cx_i = 14 * mm + col * (W - 28 * mm) / 2
        cy_i = y - row * 5.2 * mm
        check_with_label(c, f"panic_{i}", name, cx_i, cy_i,
                          size=8.5, font_size=8)
    y -= 5.2 * 3 * mm + 3 * mm

    label(c, "G\u00e2ches & protecteurs", 14 * mm, y + 1)
    y -= 4.5 * mm
    strikes = [
        "G\u00e2che standard", "G\u00e2che \u00e9lectrique",
        "Contact encastr\u00e9", "Prot\u00e8ge-p\u00eane",
        "Protecteur de barillet",
    ]
    for i, name in enumerate(strikes):
        col = i % 3
        row = i // 3
        cx_i = 14 * mm + col * (W - 28 * mm) / 3
        cy_i = y - row * 5.2 * mm
        check_with_label(c, f"strike_{i}", name, cx_i, cy_i,
                          size=8.5, font_size=8)
    y -= 15 * mm

    section_title(c, "10. Autre quincaillerie", y)
    y -= 8 * mm
    others = [
        "Astragale", "Verrous affleur\u00e9s",
        "Balai de porte", "Moulure thermo",
        "Moulure vitrage simple",
    ]
    for i, name in enumerate(others):
        col = i % 3
        row = i // 3
        cx_i = 14 * mm + col * (W - 28 * mm) / 3
        cy_i = y - row * 5.2 * mm
        check_with_label(c, f"other_{i}", name, cx_i, cy_i,
                          size=8.5, font_size=8)
    y -= 15 * mm

    section_title(c, "11. Seuil de porte", y)
    y -= 8 * mm
    thresholds = [
        ("Fournir",                            "thr_supply"),
        ("Non-isol\u00e9",                    "thr_non_iso"),
        ("Isol\u00e9",                        "thr_iso"),
        ("Allouer espace standard",         "thr_space_yes"),
        ("Ne pas allouer d'espace",         "thr_space_no"),
    ]
    for i, (lbl, nm) in enumerate(thresholds):
        col = i % 3
        row = i // 3
        cx_i = 14 * mm + col * (W - 28 * mm) / 3
        cy_i = y - row * 5.2 * mm
        check_with_label(c, nm, lbl, cx_i, cy_i, size=8.5, font_size=8)
    y -= 11 * mm
    label(c, "Type de seuil (pr\u00e9cisez)", 14 * mm, y)
    text_field(_uniq("thr_type"), 14 * mm, y - 6 * mm,
                W - 28 * mm, 4.5 * mm)
    y -= 10 * mm

    section_title(c, "12. Notes & informations suppl\u00e9mentaires", y)
    y -= 5 * mm
    multiline_field(_uniq("notes"), 14 * mm, y - 22 * mm,
                     W - 28 * mm, 22 * mm)

    c.save()
    buf.seek(0)
    return buf.read()

