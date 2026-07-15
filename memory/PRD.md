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
- ✅ **Expert Reports (Rapports d'expertise)** (2026-07): field
      inspection report builder matching Cédrick's PDF template
      (5 numbered sections + cover). Doors are dynamic (dimensions,
      series, hardware, deficiency bullet lists, recommendation).
      Photos are uploaded per door (mobile camera capture supported),
      stored on disk under `/app/backend/uploads/expert_reports/{id}/`
      **AND in GridFS** (bucket `expert_report_photos`, keyed by
      `metadata.photo_id`) so they survive Kubernetes redeploys.
      Disk is used as a hot cache; missing files are re-hydrated from
      GridFS on-demand before PDF render / photo serve.
      Branded PDF `RAP-YYYY-NNNN` embeds photos inline in section 3 —
      photos are chunked into 1-row-per-pair tables so ReportLab can
      page-break cleanly (fixes 13-photo truncation bug).
      Frontend uploads photos ONE-AT-A-TIME after resizing them to
      max 2000 px JPEG q82 in-browser (fixes HEIC + 10 MB iPhone
      cases + K8s ingress body-size limits).
      Inline editable **caption/note** per photo — user types
      "Réf. #1" etc. and it appears in the PDF next to the photo.
      Backend: `erp_routes_expert_reports.py` + `render_expert_report_pdf`
      in `erp_pdf.py` + `ExpertReport` / `InspectedDoor` / `ReportPhoto`
      models. Frontend: `ExpertReportsPanel.jsx`.
- ✅ **Expert Report daily backups** (2026-07): `erp_expert_report_backup.py`
      — APScheduler daily 02:00 America/Montreal snapshots the FULL
      report doc (metadata + photo-id references — GridFS entries left
      alone) into `erp_expert_report_backups`. 90-day retention with
      auto-prune. Admin endpoints: `POST /admin/expert-reports/backup/run`,
      `GET /admin/expert-reports/backup/list?report_id=…`,
      `POST /admin/expert-reports/backup/{snapshot_id}/restore`.
- ✅ **Cost price + profit margin on quotes** (2026-07):
      `Product.cost_price` (confidential — never on quote PDF).
      New "🔒 Marge de profit" panel inside quote form only —
      shows per-line cost/sell/margin, totals with color-coded %
      indicator, and one-click "+X %" price bump buttons (5/10/15/20
      plus custom %). Data lives purely in-browser (looked up from
      products cache on-the-fly, `_cost_price` on LineItem stripped
      by backend `extra="ignore"`).
- ✅ **AT order form — refonte interactive AcroForm (2 pages)** (2026-07):
      Le formulaire de commande porte AT a été **entièrement réécrit** en
      utilisant les vraies `AcroForm` de ReportLab (via `canvas.acroForm`) —
      90 champs interactifs (text fields + checkboxes) que les vitreries
      peuvent cliquer/cocher directement dans Adobe Reader ou Preview macOS.
      Compactage à **exactement 2 pages** Letter (au lieu de 4 auparavant).
      Ajout d'une **case "Standard 36×84" (914×2134 mm)** en tête de section
      Dimensions. Tout le reste conservé : sections 1-12, séries
      AT1000/ATi1000/AT2000/ATi2000, 6 finis, poignées 9" et 12", serrures
      SM 1850 / 4510 / 8400 / 8600, gâches, seuils, notes multi-lignes.
- ✅ **Branding refresh — Quincaillerie et porte commerciale** (2026-07):
      unification de la tagline sur TOUT le site + tous les documents PDF +
      emails à **"Quincaillerie et porte commerciale"** (fini les variantes
      "quincaillerie commerciale" et "quincaillerie de porte commerciale" —
      pour éviter la confusion avec RONA/Home Hardware). Nouveau visuel
      d'entête email (`/frontend/public/email/email-header.png`) avec
      **"PORTECH" réduit d'environ 30 %** (100 px au lieu de ~150 px) et
      la nouvelle tagline. 15 fichiers mis à jour (backend PDF templates,
      prospection intros, signatures email, meta SEO, JSON-LD, manifest.json,
      pages publiques Services / Catalogue / Galerie / About / Home /
      Contact / Legal / HomeSolution).
- ✅ **Client AT door order form + PDF-inline preview + number-input auto-select** (2026-07):
      **Feature** — nouveau formulaire vierge PDF de commande de porte AT
      (`GET /admin/at-order-form.pdf` — 99 KB, brandé Portech, cases à cocher
      Unicode). Toutes les séries (AT1000/ATi1000/AT2000/ATi2000), tous les
      finis (anodisé clair, noir, bronze, dark bronze, champagne, mill),
      poignées 9" ET 12" (dos-à-dos / extérieure / intérieure), sens
      d'ouverture (GE/DE/PE/GI/DI/PI), serrures (SM 1850, 4510 AR, 8400,
      8600), gâches, protecteurs, seuil, notes. Boutons : "Joindre formulaire
      commande porte AT" (Composer courriel) et "Formulaire client vierge"
      (Commandes AT). Backend : `erp_routes_at_order_form.py` +
      `render_client_at_order_form_pdf()` dans `erp_pdf.py`.
      **Bug UX #1** — champs `input[type=number]` pré-remplis avec `0` :
      handler global `focusin` dans `App.js` qui appelle `el.select()` — taper
      un chiffre remplace automatiquement le 0.
      **Bug UX #2** — PDFs auto-téléchargés : tous les endpoints PDF ERP
      utilisent maintenant `Content-Disposition: inline` (prévisualisation
      dans l'onglet du navigateur au lieu de download). Les exports CSV
      restent en `attachment`. 12 endpoints migrés.
      Tests pytest : 6/6 passants dans `backend/tests/test_pdf_inline_and_at_form.py`.
- ✅ **Fabrication tab + Moustiquaires module** (2026-07):
      renommage de l'onglet "Coupes" → **"Fabrication"** avec deux
      sous-onglets : "Listes de coupe" (existant) et "Moustiquaires" (nouveau).
      Nouveau module **Bons de fabrication moustiquaires** —
      `MS-YYYY-NNN`, mode double (fabrication interne / envoi à un
      fournisseur), champs par unité : identifiant/nom, largeur, hauteur (mm),
      qté, couleur de cadre, type de toile, type d'attache, notes.
      PDF brandé + envoi Resend au fournisseur (mode fournisseur).
      Backend : `erp_routes_mosquito_screens.py` + `render_mosquito_screens_pdf`.
      Frontend : `FabricationPanel.jsx` (wrapper sous-onglets) +
      `MosquitoScreensPanel.jsx`. Slug `coupes` redirige vers `fabrication`
      (compatibilité URL). Sous-onglet actif persisté en localStorage.
- ✅ **Realistic image swap** (2026-07): replaced 3 unrealistic AI images
      on the public site (`services-upgrade.png`, `home-service-upgrade.png`,
      `precision-install.png`) with existing gallery photos
      (`gal-lock-2.png`, `gal-lock-4.png`, `gal-chantier-3.png`).
      Files edited: `Services.jsx`, `home/data.js`.
- ✅ **Inventory bug fix** (2026-07): `<EditMetaModal>` and
      `<ThresholdsModal>` now receive `key={row.id}` — prevents state
      leakage across rows when editing multiple aluminum profiles
      back-to-back (previous bug: edits applied to wrong product).
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
