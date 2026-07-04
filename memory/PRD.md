# Portech ERP & Lead-Gen — PRD

## Original Problem Statement
Fully functional lead-generation **and** ERP web app for a commercial door
hardware business (Portech). Internal ERP for Clients, POs, BOL, Appointments,
Invoices, Expenses, PDF generation, B2B cold-email tool, deterministic Cut List
module (with AI OCR + DXF + 1D bin-packing optimizer), aluminum inventory,
branded transactional emails.

User language: **French**.

## Stack
- React 19 + FastAPI + MongoDB (Motor)
- Resend (transactional email), Meta Pixel (tracking)
- Emergent LLM key — Gemini Vision 3 Flash Preview (OCR)
- ReportLab (PDF), ezdxf (DXF parsing), APScheduler (cron)
- PWA service worker with auto-update banner

## Implemented (chronological)
- ✅ Lead-gen marketing site + admin panels
- ✅ ERP modules: Clients, POs, BOL, Appointments, Invoices, Expenses
- ✅ Branded transactional emails (banner-unified)
- ✅ Cut-List module: AI OCR (Gemini Vision), DXF extractor (filtered to frame
      layers, short-line discard), deterministic template builder
      (Flush-Glaze Trifab, Curtain-Wall Kawneer, AT doors), 1D bin-packing
      optimizer with kerf, Gasket classification, Unicode-fraction PDF safe
- ✅ Aluminum profile catalog + inventory bars + "Confirm cuts" deduction
- ✅ PWA auto-update banner (Windows caching fix)
- ✅ **AT door breakdown : exact AT Fabrication part numbers + glass-dependent
      parclose** (2026-02)
- ✅ **Inventory finishes (clair/noir) + min/max thresholds + Purchase-Order
      PDF + filter chips + status badges** (2026-06)
- ✅ **AT Orders Phase 1**: Gemini Vision OCR of order forms → 3-page Shop
      Drawing PDF (cover, elevations, hardware checklist) (2026-06)
- ✅ **AT Orders Phase 2** (2026-06):
    - Per-door hardware matrix (UI + backend `DoorLine.hardware`)
    - 12" pulls added (pull_12_back_to_back / exterior / interior)
    - Copy-hardware-to-all-doors button per column
    - Profile cross-section library pages 4+ in Shop Drawing PDF
      (`at_profile_library.py` — ATT1005 / ATB1000 / ATB2000 / ATV1010 /
       ATV1015 / ATV2010 / ATV2015 / AT1045 / AT1050 / ATCV* / ATCHA1035)
    - "Créer liste de coupe" button — pushes AT order into a new ERP CutList
      via `POST /admin/at-orders/to-cut-list` (uses `decompose_at_door`)
    - Legacy v1 top-level hardware migrated to per-door on load
    - Encoding sanitizer fixes "?" rendering for em-dash / quotes / fractions
- ✅ **Email line-break preservation** (2026-06): `normalize_message_to_html`
      in `erp_helpers.py` converts textarea newlines / blank lines to proper
      `<p>` / `<br/>` so suppliers see the layout Cédrick typed
- ✅ **Email Reply-To routing** (2026-06): every ERP outbound (POs, BOLs,
      invoices, reminders, monthly recap) now sets `reply_to` to
      `portech.infos@gmail.com` so client replies land in Cédrick's inbox
      instead of bouncing off `info@portech.info` (no MX records)
- ✅ **Compose Email panel** (2026-06): new ERP tab "Composer courriel" —
      free-form branded email composer with party autocomplete, multi-file
      attachments (20 MB cap), full audit log in `erp_email_log`. Backend:
      `erp_routes_compose.py` with `POST /admin/compose-email` + GET log
- ✅ **Payment Notices (Avis de paiement)** (2026-06): new ERP tab to
      generate branded "remittance advice" PDFs proving suppliers have been
      paid (eliminates "you didn't pay us" follow-up emails). Backend:
      `erp_routes_payment_notices.py` + `render_payment_notice_pdf` in
      `erp_pdf.py`. Auto-number `AP-YYYY-NNN`, methods (EFT / chèque /
      Interac / etc.), free-form items (invoice # / description / amount),
      PDF banner says "3 à 5 jours ouvrables" for bank transfer arrival.
      Email send route attaches the PDF + tracks `sent_at`/`sent_to`.
- ✅ **Product catalog PDF** (2026-06): new "Catalogue PDF" button in
      Products panel (`erp_routes_products.py` GET /products/catalog.pdf).
      Branded cover + grouped-by-category tables (SKU / Name / Description
      / Unit / Price), `is_service` badge, "sur demande" for $0 items.
      Hand out to trusted clients without exposing the internal ERP.
- ✅ **Quotes / Soumissions module** (2026-07): new ERP tab to build
      client quotes, download branded PDF (SO-YYYY numbering), email
      directly to prospects with 30-day validity clause. Statuses:
      brouillon / envoyée / acceptée / refusée / expirée / annulée.
      Backend: `erp_routes_quotes.py` + `render_quote_pdf` +
      Quote/QuoteIn models. One-click **"Convertir en facture"** creates
      a draft invoice from an accepted quote (line items + customer
      cloned, quote marked "acceptée" and linked via
      `converted_invoice_id`). Frontend: `QuotesPanel.jsx` extends the
      shared `DocumentPanel` (which now supports `extraRowActions` +
      optional `printPath`). Also added quotes tab to mobile menu.
    - InventoryRowIn supports `finish`, `restock_min`, `restock_max`
    - New endpoints: `PATCH /admin/alu-inventory/{id}/thresholds`,
      `GET /admin/alu-inventory/purchase-order.pdf?finish=&token=`
    - Cut confirm deducts from `cl.finish` preferred row, falls back to any
    - `_normalize_row` migrates legacy rows (defaults `finish=clair`)
    - 13 new pytest cases (test_alu_inventory.py) — 155/155 total green
    - AT1000 base = 3⅞" (extrusion "AT1000", same as AT2000 head)
    - 6 mm glass → parclose carrée 13.48 mm
    - 25.4 mm thermos → parclose plate 14.3 mm
    - Part numbers: ATT1005, AT1000, AT2000, AT1020, AT1025, AT2020, AT2025,
      ATV1030, ATCHA1035, ATV2030, ATCHA2025
    - 142/142 pytest pass

## Backlog
**P1**
- Floating "Call Now" / WhatsApp button (public site, mobile-first)
- Express Quote (Devis Express) calculator page
- Recovery / follow-up email campaign template (Resend)

**P2**
- Google Calendar sync (ERP appointments)
- Quarterly TPS/TVQ automated recap report

**P3**
- Before/after photo gallery builder (admin)

## Key Files
- `backend/cut_door_breakdown.py` — door piece decomposition
- `backend/profile_catalog.py` — read-only profile catalog
- `backend/cut_templates.py` — deterministic templates
- `backend/cut_optimizer.py` — 1D bin packing
- `backend/atelier_routes.py` — inventory
- `frontend/src/pages/erp/panels/CutListPanel.jsx`
- `frontend/src/pages/erp/panels/TemplateBuilderModal.jsx`
- `frontend/src/pages/erp/panels/InventoryPanel.jsx`
