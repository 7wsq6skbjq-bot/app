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
- ✅ **AT form V3 — remaining overlaps + section 7 restructure + threshold cleanup** (2026-07):
      **Bug** (visuel) : légendes / sous-labels de sections passaient sous les
      bandeaux navy (Section 6 GE=…, Section 9 SERRURE PRINCIPALE, Section 10
      Astragale). Corrigé en portant tous les gaps sous les section titles
      de 5-6 mm à **8-9 mm**. Rendu 180 DPI confirmé propre par testing agent.
      **Bug** (structure) : les cases QTÉ 1/2/3/4 s'appliquaient à toutes les
      charnières. Restructuré — Section 7 ligne 1 = *Charnière 4½ + QTÉ PAR
      PORTE + 4 cases 1..4* (dédiées à la 4½), ligne 2 = *Continue + Continue
      HD + Fournir/installer* (sans qté).
      **Nettoyage** : Section 11 Seuil — retrait de « (par Portech) » sur
      l'option *Fournir*.
      Tests : 7/7 pytest passants dans `test_at_form_iter13.py`.
- ✅ **AT form V2 — fixes overlap + logo quality + AcroForm parser** (2026-07):
      **Bug #1** : superposition section 6 (sens d'ouverture) corrigée —
      layout passe de 3 col × 2 rangs serrés à **2 col × 3 rangs** (10 mm par
      row) avec QTÉ box élargie à 18 mm. Zéro chevauchement confirmé.
      **Bug #2** : logo Portech basse résolution corrigé — utilise maintenant
      `portech-mark-white.png` (335×335 haute-res) rendu à 16×16 mm + le mot
      **"PORTECH" rendu en TEXTE vectoriel** Helvetica-Bold 20 pt (au lieu
      d'une image raster). Net à n'importe quel zoom.
      **Feature** : nouveau parser `at_form_parser.py` + endpoint
      `POST /admin/at-orders/parse-portech-form`. Lit directement les 90
      champs AcroForm du formulaire Portech rempli par un client vitrerie —
      **sans OCR / sans coût LLM / instantané / 100% déterministe**. Nouveau
      bouton **"Importer formulaire client (Portech)"** dans ATOrdersPanel
      à côté du "Parser un PDF" (OCR Gemini) existant. Mapping complet :
      client/projet, série (AT1000/ATi1000/AT2000/ATi2000), dimensions
      Standard 36×84 ou custom, finis ext/int, sens d'ouverture (6 mains +
      qté), charnières + qté, poignées 9"/12", serrures SM 1850 / 4510 /
      4590 / 8400 / 8600, gâches, protecteurs, autres quincailleries,
      seuil (isolé/non-isolé/espace), notes.
      Tests pytest : 6/6 passants dans
      `backend/tests/test_at_form_bugs_and_parser.py`.
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


## Module « Dessins de production » (Fabrication) — 2026-08-16
- Générateur de plans de production PDF paysage à partir des dimensions d'ouverture (template modifiable).
- Pages : présentation (fond devanture estompée + quadrillé), élévation à lundefined'échelle par porte (cotes mm [po], charnières, bulles, quincaillerie libre), détails en plan (300), coupe (400), ancrages (500).
- Détails 300/400/500 = vraies images CAO extraites des plans de référence, nettoyées (cartouche AT fabrication retiré) et intégrées sous entête Portech. Mappées par famille : AT1000/AT2000 -> détails AT (Kovo) ; ATi1000/ATi2000 -> détails ATi (AT064).
- Backend : erp_pdf_production.py (moteur canvas), erp_routes_production_plans.py (CRUD + /pdf + /preview-pdf), collection erp_production_plans. Assets : backend/assets/production_details/.
- Frontend : ProductionPlansPanel.jsx (3e sous-onglet Fabrication).
- Note : les libellés « de AT Fabrication » restent dans les images de détails (série de porte du manufacturier).

- MAJ 2026-08-16 : images de détails - mentions manufacturier remplacees par « de Portech » (OCR). Boite rouge PRODUCTION conditionnelle (affichee seulement si responsable/note production saisi). Bascules include_plan/section/anchor verifiees.

- MAJ 2026-08-17 (Dessins de production, lot 2) : (1) titre projet passe a la ligne + case client compacte ; (2) mentions « de AT Fabrication » restaurees dans les details ; (3) type de charniere (4 1/2 paumelles = 3 rects / continue = bande pleine hauteur -1/4 / aucune) ; (4) choix Usinage par + Installation par (Portech / A.T. Fabrication) dans lentete quincaillerie ; (5) selection des profils daluminium par element (tete/base/montant charniere/montant serrure) branchee sur at_profile_library (vraies dimensions), dessin delevation mis a lechelle des profils reels ; (6) details 03/04 (porte simple) pivotes 180 sur plan_at (convention fabricant). Nouveau endpoint GET /admin/production-plans/profile-catalog.

- MAJ 2026-08-17 (Dessins de production, lot 3) : (1) sens douverture MG/MD/MGR/MDR -> cote penture (MD,MGR=gauche / MG,MDR=droite) ; (2) cotes Fab. optionnelles (fab_width_in/fab_height_in) affichees en plus de louverture libre ; (3) details 03/04 (porte simple) - bande de dessin retournee verticalement, texte garde lisible (fini le texte a lenvers). plan_at.png finalise via /tmp/src/finalize.py.

- MAJ 2026-08-17 (Dessins de production, lot 4) : poignee sur 2 battants (handle_both) ; colonnes ACTIF/INACT. dans tableau quincaillerie (HardwareLine.on_active/on_inactive) ; detail 03/04 REVENU a original propre (rotation matricielle cassait la penture - besoin image corrigee du client).

- MAJ 2026-08-17 (Dessins de production, lot 5) : barre anti-panique horizontale sur battant actif (panic_bar/panic_height_in, std 40po modifiable) ; cote Fab. auto = ouverture + jeu configurable (fab_auto/fab_allowance_in au niveau projet, override manuel par porte toujours possible).

- MAJ 2026-08-17 (Dessins de production, lot 6) : cote hauteur de poignee corrigee - mesuree du bas de la porte au BAS de la poignee (la poignee s etend vers le haut ; 9po/12po = meme bas, fin plus haute).

- MAJ 2026-08-17 (Dessins de production, lot 7) : cotes de quincaillerie reorganisees en colonnes espacees au-dessus du vitrage (vers le centre du battant) - plus de chevauchement avec la bulle de detail ni entre elles. Hauteur poignee + longueur empilees en colonne 1, serrure en colonne 2.

- MAJ 2026-08-17 (Dessins de production, lot 8) : poignee - courbe orientee vers le vitrage (miroir corrige, par battant) ; profils par defaut AT1000/ATi1000 - montant charniere ATV1025 (ajoute a at_profile_library), serrure actif ATV1015, inactif ATV1010 (nouveau champ profile_lock_stile_inactive + 5e menu) ; base substituee ATT1005 ajoutee aux options de base ; bulles de detail (300/400) masquees quand les pages de detail correspondantes sont decochees.

- MAJ 2026-08-17 (Dessins de production, lot 9) : serrure positionnee horizontalement a 1-1/8 po (28.6mm) du bord meeting/serrure du battant (lock_cx dedie), distincte de la poignee (sur le montant) - fini le chevauchement des symboles.

- MAJ 2026-06 (Dessins de production, lot 10 - Paires asymetriques) : saisie de largeurs individuelles par ROLE (battant actif / battant inactif) pour les paires. Nouveaux champs backend DoorPlan.leaf_active_width_in / leaf_inactive_width_in (schema + payload). Auto-completion : si un seul champ saisi, l'autre = ouverture - saisi ; les deux a 0 = partage 50/50. Le mapping actif/inactif -> gauche/droite suit active_leaf. Le moteur PDF (erp_pdf_production._elevation_page) place desormais poignee/serrure/charnieres/barre-panique sur le montant de rencontre reel decale (fini le hardcode 50/50). Cote de largeur affichee PAR BATTANT sous les cotes du haut. Frontend : champs conditionnels (config=paire) dans ProductionPlansPanel.jsx + emptyProductionDoor. Verifie visuellement (rendu PDF actif=droite 24/auto 36, et actif=gauche 30/42 poignee-2-battants) + UI confirmee.

- MAJ 2026-06 (Dessins de production, lot 11 - Catalogue quincaillerie + quincaillerie dessinee configurable) :
  * Nouvelle collection erp_production_hardware + CRUD (GET/POST/PUT/DELETE /admin/production-hardware), upsert par nom. Auto-ajout : toute description saisie sur un plan s'ajoute au catalogue a l'enregistrement (_sync_hardware_catalog dans create/update). Frontend : combobox datalist (#pp-hw-catalog) sur la description avec auto-remplissage du n° de piece ; carte de gestion « Catalogue de quincaillerie » (ajout/suppression).
  * Bascules « Afficher sur le dessin » par porte : no_hardware (maitre), show_handle, show_lock, lever (Adams Rite), push_paddle (palette de relache), protection_plate (plaque KROME), flush_bolt (verrou affleure), panic_bar. Hauteurs dediees (lever/paddle/plate/panic).
  * NOUVEAUX dessins vectoriels : levier Adams Rite (bras HORIZONTAL sur platine), palette de relache (chassis + pad), plaque de protection KROME (cylindre sur le battant choisi, corps qui EMBARQUE sur le battant oppose/cadre - jamais a cheval 50/50), verrou affleure (haut+bas).
  * Choix du battant (actif/inactif) PAR ELEMENT dessine : handle_leaf/lock_leaf/lever_leaf/paddle_leaf/plate_leaf/panic_leaf/flush_leaf (defaut actif, flush=inactif). Selecteur actif/inactif visible dans l'UI uniquement pour les paires.
  * Barre panique : sur le battant choisi, bord a bord (touche les 2 cotes du battant). Palette + barre panique : TRAITS CACHES (pointilles) pour mains inversees MGR/MDR (derriere la porte), TRAITS PLEINS (surface) pour MG/MD.
  * Bloc « Verre & moulures (calc. coupe) » ajoute au bloc profils : dimensions du verre (H×L) et longueurs des moulures V/H, calcul IDENTIQUE aux listes de coupe (conversion ouverture->battant via offsets par serie AT1000 w=115.1 / AT2000 w=191.3, h=22.2, puis decompose_at_door). Verifie : AT1000 36" -> moulure H ~799 (=801 client), AT2000 36" -> ~723 (=724 client). Detection thermos (serie ATi ou texte verre) -> parclose AT1050 sinon AT1045.
  * Libelle du verre deplace en HAUT du vitrage + textes centres panic/palette remplaces par cotes laterales -> zero chevauchement de texte.
  * Tests : agent iteration_14 = 100% (9/9 backend, frontend e2e). Ajouts ulterieurs (selecteur battant, levier horizontal, traits caches) verifies au rendu PDF + UI.

- MAJ 2026-06 (Dessins de production, lot 12 - Mention, ferme-porte, astragale, calculateur de couts, correction Fab) :
  * MENTION de document (Pour approbation / Pour demande de prix / Pour production) : champ plan `mention`, affichee sur la page de presentation (cadre rouge) ET dans l'en-tete de CHAQUE page (bandeau, ambre). Selecteur UI pp-mention + constante PRODUCTION_MENTIONS.
  * FERME-PORTE (ferme-porte) : DoorPlan.door_closer + closer_leaf (actif/inactif). Dessin _draw_closer (boitier haut du battant cote charniere + bras articule vers le centre). Bascule UI pp-door-closer + selecteur battant.
  * ASTRAGALE : DoorPlan.astragal (paires seulement). Bande verticale au montant de rencontre + libelle rotationne. Bascule UI pp-door-astragal (visible si config=paire).
  * CALCULATEUR DE COUTS : catalogue quincaillerie a un `price` ; lignes quincaillerie ont `unit_price` auto-rempli depuis le catalogue (onHwDescription remplit n° piece + prix) ; total par porte affiche dans l'editeur (tfoot pp-door-cost). Bascule plan `show_costs` (pp-show-costs) -> ajoute un bloc « COUT QUINCAILLERIE (interne) » sur le PDF. PAR DEFAUT show_costs=false => AUCUN prix sur le plan remis au client. Auto-ajout au catalogue reporte aussi le prix.
  * CORRECTION Fab : la cote « Fab. » = ouverture − offset par serie (battant fini), MEME SOURCE que le decompose (offsets AT1000 w=115.1/h=22.2, AT2000 w=191.3). Ex : 84" -> Fab 2111.4 mm (client 2111.3) ; 36" AT1000 -> Fab 799.3 mm. Fini l'ancien « ouverture + jeu ».
  * Tests : agent iteration_15 = 100% (10/10 backend, frontend e2e, aucun JS error).

- MAJ 2026-06 (Dessins de production, lot 13 - Option « les deux » battants) : chaque quincaillerie dessinee peut maintenant etre placee sur actif / inactif / LES DEUX (Literal["active","inactive","both"] pour handle/lock/lever/paddle/plate/panic/flush/closer). Helper _roles() dans _elevation_page : chaque element boucle sur les battants choisis (cote + dim uniquement sur le 1er). Selecteur UI leafSelect a une 3e option « les deux ». Verifie au rendu (levier + barre panique + ferme-porte sur les 2 battants d'une paire).

- MAJ 2026-06 (Soumission - lignes sans prix) : le PDF de soumission (render_quote_pdf) n'affiche plus « 0,00 $ » pour les lignes sans prix (_items_table_money(hide_zero=True) pour la soumission uniquement ; factures/BC inchanges). Editeur : total coût par porte affiche « — » si 0.

- MAJ 2026-06 (PRICING - Phase 1 : moteur de prix & rentabilite) :
  * Nouveau module erp_pricing.py (moteur EXACT + teste) : markup=profit/cout, marge=profit/vente (JAMAIS confondus), prix depuis marge cible = cout/(1-marge), simulateur markup, « 1 pour N portes » (ceil), ventilation par categorie, alerte marge < mini. markup/marge = None si base 0.
  * Endpoints /api/admin/pricing/settings (GET/PUT singleton erp_pricing_settings) + /api/admin/pricing/compute. Parametres : taux (standard=90 confirme ; specialisee/fabrication/usinage/expertise = None => DONNEE MANQUANTE), km_rate=0.85, margin_min/target=None (a definir par le client, JAMAIS inventes).
  * Catalogue quincaillerie : DEUX champs Cout + Prix de vente (ProductionHardware.cost + price ; UI gestionnaire mise a jour).
  * Frontend : composant PricingCalculator.jsx integre dans l'onglet Soumissions (QuotesPanel) — parametres editables, table de lignes (categorie, qty, 1/N portes, cout U, vente U), tableau de rentabilite global + par categorie, simulateur (+5..+100 % + perso), solveur de marge cible (30..60 % + perso), alerte « MARGE SOUS LA CIBLE ». Style pro bleu foncé/turquoise.
  * Verifie : backend (curl projet 12 portes : markup 185 %, marge 64,9 %, qty 1-pour-2=6 ; solveur 50 %→prix=2×cout, markup 100 %) + UI e2e (capture). Formulaire facture/BC partage NON touche.
  * RESTE (Phase 2) : catalogue B2B fabricants (prix/operation, temps, capacite/jour), capacite de production (portes/jour-semaine-mois). Phase 3 : analytics de rentabilite (par type de projet/produit/client). Main-d'oeuvre : taux inseres manuellement dans les lignes pour l'instant (pas encore de picker auto depuis les parametres).

- MAJ 2026-06 (Soumission - contrat en annexe) : les 21 conditions de vente Portech + bloc ACCEPTATION DU CLIENT (n° soumission, projet, nom, signature, date) sont ajoutees automatiquement en annexe de CHAQUE soumission PDF (erp_pdf.SALES_CONDITIONS + _sales_conditions_story, PageBreak apres la soumission). Verifie : soumission = 3 pages, 21 clauses + acceptation presentes.

- A FAIRE (Fabrication - recalibration bible AT + lousse +2mm) : le client a fourni 2 nouvelles bibles AT Fabrication (dimensions de vitrage series AT/ATi). Deductions vitrage bible : AT1000/ATi1000 largeur -122.2 (simple) / -244.4 (paire /2), hauteur -185.7 ; AT2000/ATi2000 largeur -198.4 / -396.8 (/2), hauteur -303.2 ; charnieres 3.1mm, degagement sol 17.46mm. NOUVEAU : lousse elargi de 2mm en largeur pour 1 porte => thermos 2mm moins large (deduction largeur simple +2mm : AT1000 simple => 790.2 au lieu de 792.2). PROBLEME CONNU : le calcul verre/moulure actuel des Dessins de production (_glass_moulure via decompose_at_door) NE CORRESPOND PAS a ces deductions bible (ex AT1000 36" donnait 668 au lieu de ~790). A recalibrer proprement sur les deductions bible + regle 2mm. Question ouverte : le +2mm s'applique-t-il aussi aux paires ?

- MAJ 2026-06 (Dessins de production - choix vitrage + parclose auto + jambage/horizontal + verif) : FAIT.
  * Nouveau champ DoorPlan.glass_type Literal["6mm","tht"] + case UI « Type de vitrage » (Vitré 6 mm / Thermos 25,4 THT). _glass_thickness_mm priorise glass_type (6mm->6.0 / tht->25.4) -> pilote AUTOMATIQUEMENT la parclose (AT1045 pour 6mm, AT1050 pour thermos). Retrocompat : plans existants sans glass_type retombent sur detection serie/texte (ATi->25.4). Application AUTO aux plans deja crees (PDF genere a la volee depuis les donnees stockees).
  * Mention « bible A.T. » retiree du titre -> « Verre & moulures ».
  * Ajout dans l'encadre : « Jambage V (long.) » (=mv, longueur parclose verticale) et « Horiz. h/b (larg.) » (=mh, parclose horizontale ; pour paires : actif/inactif).
  * Verification integree : marqueur ⚠ dans le titre si (parclose horizontale <= largeur verre) OU (parclose verticale >= hauteur verre). Regle client : H parclose TOUJOURS > verre, V parclose TOUJOURS < verre. Avec les valeurs actuelles (mh~799 > verre 790 ; mv~1930 < verre 1948) la verif PASSE.
  * NOTE : le client a defini l'horizontale = largeur battant - montants (=~695 pour AT1000), ce qui serait INFERIEUR au verre 790 et VIOLERAIT sa propre regle de verif. J'affiche donc mh (parclose horizontale cut-list ~799) qui respecte la regle. A reconcilier avec le client si l'ecart verre/parclose horizontale doit etre revu (incoherence entre largeur verre bible 790 et largeur battant 799). Nouveau GLASS_DEDUCT_MM + _glass_deduct + _glass_dims_bible dans erp_pdf_production.py. Dimensions REELLES du thermos = ouverture - deduction bible, moins GLASS_WIDTH_LOUSSE_MM=2mm PAR porte (simples ET chaque battant des paires, confirme par le client). Deductions : AT1000/ATi1000 ws=122.2 wp=244.4 h=185.7 ; AT2000/ATi2000 ws=198.4 wp=396.8 h=303.2. Paire : largeur totale (ow-wp) repartie par fraction de battant puis -2mm chacun. Verifie : AT1000 36x84 simple => 1948 x 790 mm (PDF), AT2000 => 1830 x 714, paire 72" AT1000 => 790/battant. Le bloc spec affiche « Verre & moulures (bible A.T.) ». NB : les longueurs de moulures restent issues de _glass_moulure (decompose) — a verifier avec le client si besoin de recalibrer aussi les moulures sur la bible.
