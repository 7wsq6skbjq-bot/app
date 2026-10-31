# Portech ERP & Lead-Gen — PRD


## Changelog — 2026-06 (fork, Récap TPS/TVQ : détail factures + réconciliation)
- **Détail des factures de vente** dans le Récap TPS/TVQ (répond à la question du comptable « sous-total/TPS/TVQ par facture »).
  - Backend : `_compute_core` renvoie `collected_lines` (par facture : number, date, customer, status, subtotal, tps, tvq, total, `non_taxable` = tps 0 ou tps ≠ 5% du sous-total). erp_pdf `render_tax_recap_pdf` ajoute un tableau « Détail des factures de vente » (marqueur [NT] pour non taxable).
  - Frontend TaxRecapPanel : tableau `tax-recap-invoice-detail` avec ligne surlignée + badge « Non taxable », ligne TOTAUX.
- **COLLECTED_STATUSES élargi** → `envoyée, payée, partiellement payée, en retard` (la taxe est due à la date de facture ; une facture partiellement payée ou en retard reste une vente émise à inclure). Brouillon / en attente d'approbation / annulée restent exclus.
- **Réconciliation production confirmée (deployer, lecture seule)** : écart ~315 $ = facture #6 Vitrerie A2Z 2011 INC (2026-08-21, payée, 315,00 $, taxable=false, tps=0). Ligne 101 = 3 684,19 base taxable + 315,00 non taxable ; TPS 184,21 = 5% × 3 684,19. Aucun défaut système.
- Testé : JSON collected_lines (NT flaggé), PDF range contient « Détail des factures »/[NT], compile OK.


## Changelog — 2026-06 (fork, Récap TPS/TVQ : filtre par plage de dates)
- **Récap TPS/TVQ — mode « Plage de dates »** en plus du mode Trimestre.
  - Backend (erp_routes_tax_recap.py) : `_compute` refactorisé en `_compute_core` ; nouveau `_compute_range(db, start, end)` (end inclusif, garde-fou format date → 400, inversion si start>end, label « Du … au … »). Params `start`/`end` ajoutés à `GET /tax-recap`, `GET /tax-recap/pdf` et `POST /tax-recap/send` (champ start/end dans TaxSendIn). Nom de fichier PDF : `recap-tps-tvq-{start}_au_{end}.pdf`.
  - Frontend (TaxRecapPanel.jsx) : bascule `tax-recap-mode-quarter` / `tax-recap-mode-range`, champs Du/Au (`tax-recap-start` / `tax-recap-end`). Load, aperçu PDF et envoi au comptable utilisent start/end en mode plage.
  - Testé : JSON range (label « Du 19 août 2026 au 30 septembre 2026 », net calculé), PDF range valide, mode trimestre intact, dates invalides → 400, frontend compile.


## Changelog — 2026-06 (fork, outils comptables dépenses : comptable / catégorie / trimestriel / reçus)
- **Envoi du rapport au comptable** : `POST /api/admin/expenses/report/send` (start/end/category/include_receipts/to) → génère le PDF et l'envoie via `send_pdf_email` (défaut `ACCOUNTANT_EMAIL`). Bouton « Envoyer au comptable » (exp-report-send, prompt destinataire). Testé : 200, courriel envoyé.
- **Filtre par catégorie** dans le rapport : param `category` sur `report.pdf` + select `exp-report-cat`. Nom de fichier inclut la catégorie.
- **Résumé trimestriel TPS/TVQ** : `GET /api/admin/expenses/quarterly?year=` → 4 trimestres + total annuel. Carte `exp-quarterly-card` (tableau T1–T4 + Année, sélecteur d'année). Testé.
- **Annexe reçus dans le PDF** : case `exp-report-receipts` + param `include_receipts`. `render_expense_report_pdf(..., receipts)` ajoute une annexe avec les images (converties via PIL) ; reçus PDF notés comme fichiers séparés. Testé : PDF 2 pages avec « Annexe ».
- **Polish** (suite testing iter22, 100% pass) : ne plus quitter « Tous les mois » après un enregistrement ; libellés KPI/empty adaptés en mode « all » ; `_date_fr` (erp_pdf) utilise des abréviations de mois FR avec accents (déc, août) — s'applique à tous les PDF.
- Helper partagé `_build_report_inputs(db, start, end, category, include_receipts)` dans erp_routes_expenses.py.


## Changelog — 2026-06 (fork, rapport PDF de dépenses par plage de dates)
- **Nouveau rapport comptable PDF** (Comptabilité → Dépenses) : export détaillé filtré **d'une date à une autre** pour les déclarations de taxes.
  - Backend : `GET /api/admin/expenses/report.pdf?start=YYYY-MM-DD&end=YYYY-MM-DD[&category=]` (erp_routes_expenses.py) → `render_expense_report_pdf()` dans erp_pdf.py. Garde-fou format de date (400 si invalide), inversion auto si start>end, tri par date, limite 5000.
  - Contenu du PDF : en-tête Portech + période, **Sommaire** (sous-total/TPS/TVQ/total), **Crédits de taxes sur intrants** (CTI TPS + RTI TVQ + total récupérable + coût net), **répartition par catégorie**, **détail ligne par ligne** (date, fournisseur, description, catégorie, mode, sous-total, TPS, TVQ, total) + ligne TOTAUX.
  - Frontend : carte « Rapport comptable — PDF détaillé » dans ExpensesPanel avec 2 champs date + bouton `exp-report-pdf` + raccourcis (Ce trimestre / Trimestre dernier / Cette année / L'an dernier). Télécharge le PDF via blob.
  - Testé : PDF valide 95 Ko, contient CTI/RTI/catégories/fournisseur/totaux ; rendu visuel vérifié ; dates invalides → 400.


## Changelog — 2026-06 (fork, dépenses: récupération visibilité + téléchargement reçus)
- **AUCUNE PERTE DE DONNÉES** (confirmé via lecture base production par deployer) : 21 dépenses + images reçus intacts. Les reçus d'essence Ultramar existent, datés 2024-09-17 (année probablement saisie à tort), aucun reçu en août, aucune donnée 2025. Invisibles car ExpensesPanel filtrait toujours sur le mois courant (dropdown limité à 12 mois → sept. 2024 hors de portée).
- **Correctif « Tous les mois »** : option `{value:"all"}` en tête de `monthOptions` (ExpensesPanel). Backend : `GET /admin/expenses?month=all` et `export.csv?month=all` renvoient déjà tout (garde `len==7`) ; `GET /admin/expenses/summary` gère désormais `month=all` (agrégation globale). Testé : une dépense sans date (invisible par mois) réapparaît sous « Tous les mois ».
- **Téléchargement des reçus** : nouveau `downloadReceipt()` + bouton Download sur chaque ligne (`exp-download-receipt-{id}`) et dans l'aperçu de la fenêtre d'édition (`exp-download-receipt`). Récupère le blob via `GET /admin/expenses/{id}/receipt` (GridFS) et déclenche le téléchargement (nom `recu-{date}-{fournisseur}.{ext}`). Testé : upload PNG → download → octets PNG identiques. Message d'erreur clair si l'image est absente du stockage.
- Note : ~10 reçus référencés n'ont pas d'image dans GridFS en production (9 fichiers pour 19 références) — probablement d'anciennes images sur disque éphémère perdues avant la migration GridFS ; à investiguer séparément si besoin.


## Changelog — 2026-06 (fork, statuts étendus + police bannières + signatures perso + hero)
- **Statuts ERP étendus** : Factures = brouillon · en attente d'approbation · envoyée · partiellement payée · payée · en retard · annulée. Soumissions = brouillon · en attente d'approbation · envoyée · acceptée · refusée · expirée · annulée. Patterns regex élargis dans `erp_models.py` (Invoice/InvoiceIn + QUOTE_STATUS_PATTERN), listes + `STATUS_BADGE` dans `frontend/src/pages/erp/utils.js`. Testé : création statut « en retard »/« en attente d'approbation » → 201.
- **PDF client — masquage statuts internes** : `erp_pdf.py` nouveau `_client_status()` + `_PDF_HIDDEN_STATUSES={brouillon, en attente d'approbation}` appliqué au `_header()` et aux lignes « Statut » (facture + soumission). Testé : PDF brouillon → aucune mention « BROUILLON » (Statut = «—») ; PDF « en retard » → affiche bien EN RETARD.
- **Bannières courriel v2 — police agrandie** (plus lisible sans être agressant) ; régénérées + copiées dans `backend/email_assets/email-header.png`/`email-footer.png` (backend redémarré pour recharger le b64 inline).
- **Signatures personnelles** (courriels perso fournisseurs/collègues) : 2 styles générés avec avatar rond `brand/cedrick-avatar.png` (photo fournie, recadrée en cercle). Fichiers : `/email/portech-perso-navy.png` (1200×262) et `/email/portech-perso-light.png` (1200×279). Défauts : « Cédrick Pimparé — Propriétaire », info@portech.info — à confirmer par l'utilisateur.
- **Accueil** : hero → « Votre expert en quincaillerie et portes commerciales en aluminium » (retrait du « de »).
- Note : changements en preview ; redéploiement requis pour la production.


## Changelog — 2026-06 (fork, bannières courriel v2 + menu mobile ERP + accueil)
- **Bannières courriel refaites (v2)** : nouvel en-tête (fond blanc, logo transparent navy, téléphone + « Appel ou texto ») et pied (fond navy, logo blanc, services, contact, **porte en aluminium en fondu** à droite via dégradé). Tagline corrigée → « Quincaillerie et portes commerciales en aluminium » (quincaillerie d'abord). Message portes = **fourniture** uniquement (jamais « installation de portes » — Portech ne pose pas les portes). Aucun mot en majuscules dans une phrase.
  - Images générées localement via Chromium headless (crop sur fond repère magenta) : `/app/frontend/public/email/portech-header-v2.png` (1200×291) et `portech-footer-v2.png` (1200×545). Téléchargeables pour Gmail.
  - **Appliqué partout dans l'app** : fichiers `backend/email_assets/email-header.png` & `email-footer.png` remplacés par les v2. `erp_helpers.wrap_branded_email()` passe en **inline CID** (`cid:portech-header.png` / `cid:portech-footer.png`) + nouveau `banner_attachments()` ; `send_html_email`/`send_pdf_email` et `erp_routes_compose.compose-email` joignent les bannières inline. Plus aucune dépendance à `portech.info/email/*`. Prospection déjà sur `email_assets` → mise à jour auto. Lien « texto » (sms:) ajouté dans la signature. Testé : `/api/admin/compose-email` → 201, email réellement envoyé (resend_id).
- **Menu mobile ERP** : `MobileTabBar` mis à parité avec le desktop — ajout dans « Plus » de États de compte, Suivi des jobs, Demandes de porte, Assistante IA, Catalogue quincaillerie, Suivi des dépôts, Récap TPS/TVQ, Rapport kilométrique, Coûts Master (26 sections au total).
- **Accueil** : phrase hero → « Votre expert en quincaillerie et de portes commerciales en aluminium. »
- Note déploiement : changements en preview ; nécessite un redéploiement pour la production.


## Changelog — 2026-06 (fork, 4 améliorations aluminium : WebP, validation FR, ERP demandes de porte, SMS)
- **Images WebP + lazy-load** : les 11 visuels `/app/frontend/public/generated/aluminium/alu-*.png` convertis en `.webp` (qualité 80) — total 7,6 Mo → 0,7 Mo. Références mises à jour dans `PortesAluminium.jsx` (hero en background-image + cartes gammes + galerie) et `home/sections/HomeAluminium.jsx`. `loading="lazy" decoding="async"` sur les `<img>` sous la ligne de flottaison. Les `.png` sont conservés sur disque (regression test iter20). Vérifié : naturalWidth>0.
- **Validation formulaire Contact en français** : fonction `validate()` dans `Contact.jsx` (nom, téléphone ≥5, regex courriel, lieu, message) → messages FR dans `contact-error` avant envoi ; `catch` mappe 422/erreurs réseau en FR (plus d'erreur Pydantic en anglais). `maxLength` : message 3500, door_qty 20, door_width/height 40.
- **ERP « Demandes de porte »** : champs `door_gamme/door_config/door_qty/door_width/door_height/door_finish` ajoutés aux modèles `ContactSubmissionCreate`/`ContactSubmission` (server.py) et persistés ; le frontend envoie maintenant ces champs structurés (en plus de les replier dans `message` pour l'email). Nouvel endpoint `GET /api/admin/door-requests` (auth admin, filtre `$or/$nin` sur champs porte). Nouveau panneau `DoorRequestsPanel.jsx` + onglet `demandes-porte` (lien direct après « Suivi des jobs ») dans `AdminErp.jsx`.
- **Liens SMS « texto » cliquables** (`sms:+14383764177`) : navbar desktop (`nav-sms`), menu mobile (`mobile-nav-sms`, boutons Appeler/Texto côte à côte, icône MessageSquare), footer (`footer-sms`), page Contact (`contact-info-sms`).
- Tests : iteration_21.json — backend 31/31 pytest, frontend 100% (desktop + mobile). Polish appliqué après rapport (doublons loading retirés, colonne Qté espacée, maxLength).



## Changelog — 2026-06 (fork, détails KOVO réels + cartouche intégré)
- **Détails AT1000 remplacés par le vrai dessin client KOVO** (option a) : pages p.300 (détail en plan : 01–04/300 jambage simple, astragale de paire, jambages de paire) et p.400 (détail en coupe : linteau/seuil 01–02/400) extraites du PDF « KOVO INTERIEUR - DESSIN DE PRODUCTION - AVEC ETAMPE », recadrées sur la zone de dessin (sans l'étampe AT fabrication), orientées MD, avec cotes et bulles. Enregistrées en `ref/plan_at1000_*` et `ref/coupe_at1000_*`. ATi/AT2000 restent sur les feuilles génériques (pas encore fournies par le client).
- **Cartouche Portech tabulaire intégré** (style AT fabrication) : en-tête PORTECH + logo, NOM DU CLIENT, table DATE/VERSION (POUR PRODUCTION / APPROBATION), NOM DU PROJET, # DU PROJET, DESCRIPTION, PAGE — dessiné par-dessus l'ancienne étampe, bien aligné en bas à droite. Vérifié visuellement (p.300 et p.400 du projet Kovo).
- MG : reste orienté MD pour l'instant (option a « telles quelles »). Pour une vraie MG le client fournira une version miroir depuis sa CAO.


## Changelog — 2026-06 (fork, cartouche Portech + détails restaurés)
- **Dessins de détail restaurés** : retour aux feuilles A.T. originales **complètes** (exactes, avec cotes) — fini le nettoyage raster destructeur (qui coupait les profilés). Le miroir MG a été désactivé en attendant une source propre (le client exporte une version du dessin depuis sa CAO — option a).
- **Cartouche Portech auto-généré (étampe)** : `_draw_cartouche()` redessiné en style tabulaire A.T. (en-tête PORTECH + logo, NOM DU CLIENT, table DATE/VERSION « POUR PRODUCTION / APPROBATION », NOM DU PROJET, # DU PROJET, DESCRIPTION, PAGE), opaque par-dessus l'ancien cartouche 20308. Appliqué aux pages de détail (plan/coupe) et à la page d'ancrage. `_draw_cartouche(c, place, plan, desc, page_code, tag)`.
- Constatation technique clé : les PDF de référence n'ont **aucun texte extractible** (texte vectorisé) et les cotes sont collées à la géométrie → nettoyage/suppression automatique des cotes **impossible** proprement. Solution retenue : le client fournit le dessin voulu depuis sa CAO.
- EN ATTENTE : le client envoie un dessin à intégrer.


## Changelog — 2026-06 (fork, détails en plan orientés par main)
- **Détail en plan orienté selon la main (portes simples)** : on utilise le dessin EXACT fourni par le client (feuilles A.T.), désormais nettoyé de tout texte/cotes (bandes de cotes, notes, blocs-titres, « PLAN », cotes de profondeur, note 2,4). MD/MDR → feuille telle quelle (charnières à gauche) ; MG/MGR → feuille **miroir** (charnières à droite) — comme le texte est retiré avant le miroir, aucune cote n'apparaît à l'envers.
  - Variantes générées dans `ref/` : `plan_*_simple_*.png` (nettoyées, charn. gauche) + `plan_*_simple_*_mg.png` (miroir, charn. droite). `_resolve_detail_image(kind, door, mirrored)` choisit la variante miroir pour les simples MG/MGR.
  - Les **paires** et les **coupes** restent sur la feuille complète cotée (symétriques / pas de problème de main).
  - Résidu connu : quelques minuscules traits de cote (stubs) subsistent près des profilés (impossible de les retirer sans toucher au dessin) — plus aucun texte.
  - La tentative de redessin vectoriel a été ABANDONNÉE (le client exige son dessin exact, pas une recréation).


## Changelog — 2026-06 (fork, suite)
- **Détails en plan & en coupe auto-générés (vrais dessins A.T.)** : les PDF de référence du client (Plans 13 p. + Coupes 7 p.) ont été rasterisés par combinaison **série × simple/paire × vitrage (6,35 / 25,4 mm)** dans `backend/assets/production_details/ref/`. À la génération du dessin de production, quand « détails en plan » et/ou « détails en coupe » sont cochés, la **bonne feuille est auto-sélectionnée pour CHAQUE porte** (`_resolve_detail_image`), le bloc-titre projet 20308 d'origine est masqué, et un **panneau ORIENTATION** est estampillé : EXTÉRIEUR (haut) / INTÉRIEUR (bas, sens d'ouverture), côté charnières/serrure selon la main (MD/MGR → charnières à gauche ; MG/MDR → à droite). Une page de détail par porte. Fichiers : `erp_pdf_production.py` (`_resolve_detail_image`, `_orientation_panel`, `_detail_page_for_door`, `_anchor_page`).
  - LIMITE CONNUE : les PDF de référence n'ont pas de feuille ATi (isolée) en verre 6 mm → pour une porte isolée commandée en 6 mm, on utilise la feuille ATi 25,4 mm (correcte pour la série / bris thermique, mais montre le vitrage 25,4). À remplacer si le client fournit les feuilles ATi 6 mm.


## Changelog — 2026-06 (fork)
- **Cadre dessiné (Production Plans 2.0)** : le cadre est maintenant dessiné à l'échelle (linteau + 2 jambages, alu) autour de l'ouverture dans l'élévation PDF, UNIQUEMENT quand un type de cadre est sélectionné. Largeurs de profilé : `tube_fin`=1 3/4", `flush_non_iso`=1 3/4", `flush_iso`=2", `adapteur`=15/16". Sans cadre → contour mince conservé. Bloc de specs « Cadre (entrée complète) » ajouté. Voir `FRAME_FACE_IN`/`FRAME_LABELS` dans `erp_pdf_production.py`.
- **Rapport de quincaillerie consommée** : nouveau bouton (éditeur + liste des plans) → PDF portrait Portech listant la quincaillerie consommée du projet : TOTAL du projet + détail par porte. Quantités = qté ligne × qté portes. Module `erp_pdf_hardware_report.py`, endpoint `GET /api/admin/production-plans/{id}/hardware-report`.
  - NOTE UTILISATEUR : Cédrick veut sortir un **rapport mensuel** de la quincaillerie utilisée (agrégat multi-projets par mois). Backlog P2 : ajouter une vue « Rapport mensuel quincaillerie » qui agrège tous les plans d'un mois donné.

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

- MAJ 2026-06 (Listes de coupe — lousse -2mm largeur vitrage GLOBAL) : FAIT + VÉRIFIÉ.
  * cut_door_breakdown.decompose_at_door applique désormais GLASS_WIDTH_LOUSSE_MM=2.0 sur la LARGEUR du vitrage uniquement (glass_width_mm = largeur battant − 2 montants − 2 parcloses V − 2mm). Miroir de erp_pdf_production.GLASS_WIDTH_LOUSSE_MM. Appelé par battant => s'applique aussi par battant sur les paires. Hauteur du verre NON touchée (confirmé par le client : largeur seulement).
  * Validation machiniste (paire std AT1000, battant 799.3×2111.3) : traverses 799.30 ✓, montants 2111.3 ✓, moulure H 799.3 ✓. Moulure V dépend du vitrage (déjà correct dans les specs) : verre 6mm→AT1045 face 13.48→1930.42 ; thermos 25.4→AT1050 face 14.3→1928.78 (≈ machiniste 1928.9 ✓). Aucun changement de face parclose nécessaire — le code choisit déjà la bonne moulure selon Thermos/verre pour AT1000 et ATI1000.

- MAJ 2026-06 (Rebranding « portes commerciales EN ALUMINIUM » partout) : le client recevait des demandes de portes en acier. Toutes les mentions publiques « porte(s) commerciale(s) » précisent désormais « en aluminium » : Navbar, Footer, HomeHero (h1 + sous-titre), HomeSolution, pages Home/Services/About/Contact/Catalogue/Galerie/Legal, home/data.js, ET SEO critiques dans public/index.html (title, meta description, keywords, OG, Twitter, JSON-LD LocalBusiness/serviceType/OfferCatalog, contenu fallback crawlers) + public/manifest.json. Laissé intact : « quincaillerie sur tous types de portes / aluminium, acier et bois » (service de quincaillerie légitime sur portes existantes), Galerie 97 (déjà « aluminium »), titres internes ERP « Expert Portes Commerciales » (utils.js/ExpertReportsPanel). Vérifié par capture du hero. NÉCESSITE REDÉPLOIEMENT pour portech.info.

- MAJ 2026-06 (Dessins de production — Envoi au client par courriel) : FAIT + VÉRIFIÉ (envoi réel HTTP 200).
  * Backend : POST /api/admin/production-plans/{id}/send-email (EmailSendRequest : to_email, subject?, message?). Rend le PDF via render_production_plan_pdf et l'envoie en pièce jointe avec send_pdf_email (Resend, expéditeur info@portech.info). Sujet/message par défaut en français (préremplis avec plan_number + project_name + client). 404 si plan introuvable, 422 si email invalide. erp_routes_production_plans.py.
  * Frontend (ProductionPlansPanel.jsx) : bouton Mail « Envoyer au client » dans chaque ligne de la liste (data-testid pp-email-{id}) + dans la barre d'action de l'éditeur (pp-email-editor). Modale inline (pp-email-modal) : destinataire (pp-email-to, prérempli depuis client_contact si c'est un email), message optionnel (pp-email-message), bouton envoyer (pp-email-send). Note : envoie la version ENREGISTRÉE (enregistrer d'abord pour inclure les modifs). Réutilise le pattern éprouvé Factures/BC/Connaissements.
  * Vérifié : route 404/422 corrects, envoi réel vers info@portech.info = 200 {"sent":true} avec PDF joint. Frontend compile OK.

- MAJ 2026-06 (BUG paires — horizontaux/battants trop larges) : CORRIGÉ + VÉRIFIÉ.
  * Symptôme (job « Poké Monster ») : sur une PAIRE, l'horizontal (traverse) sortait > 840 mm au lieu de 799,30 mm.
  * Cause : erp_pdf_production.py — pour is_pair, l'offset ouverture→battant (OPENING_TO_LEAF_OFFSET_MM AT1000 = 115,1) n'était déduit qu'1× de l'ouverture totale (_tot_leaf_w_mm) puis /2 → 856,85 par battant. La déduction verre (wp=244,4) était déjà doublée mais pas l'offset battant.
  * Fix : offset largeur déduit PAR BATTANT (×2 = 230,2) pour les paires — lignes ~1176 (_foff_w pour cote « Fab. ») et ~1222 (_tot_leaf_w_mm). Porte simple inchangée.
  * Vérif : paire 72×84 AT1000 → 799,30/battant, horizontal 799,30 ✓ ; simple 36 po → 799,30 ✓ ; PDF paire+simple rendus OK. Correction en PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (BUG paires ASYMÉTRIQUES — battant actif ≠ 799) : CORRIGÉ + VÉRIFIÉ (suite à capture prod du client).
  * Symptôme : paire asymétrique (actif 36" thermos) affichait Horiz. actif 776.3 au lieu de 799.30.
  * Cause : erp_pdf_production.py répartissait l'offset largeur au PRORATA (_tot_leaf_w_mm * _fa) entre battants → fausse la largeur de chaque battant en asymétrique.
  * Fix : modèle PAR-BATTANT — _wa = aw_in*25.4 - offset ; _wi = iw_in*25.4 - offset (chaque battant perd l'offset complet 115.1). Un actif 36" = 799.30 quelle que soit la largeur de l'inactif. La cote « Fab. » totale reste opening - 2×offset (cohérent).
  * Vérif : sym 36+36 → 799.3/799.3 ; asym 36+24 → 799.3/494.5 ; asym 36+20 → 799.3/392.9 ; PDF paire+simple rendus OK. EN PREVIEW — redéployer + régénérer le plan pour portech.info.

- MAJ 2026-06 (Bannières + signatures COURRIEL « en aluminium ») : FAIT + VÉRIFIÉ.
  * Le client recevait encore « porte commerciale » dans les EN-TÊTES/PIEDS de courriel — c'étaient des IMAGES PNG (email-header.png / email-footer.png) avec le texte incrusté. Réécrit via PIL (grille 40px préservée, police Liberation Sans Bold, couleur 151,176,208) : en-tête « QUINCAILLERIE ET PORTES COMMERCIALES EN ALUMINIUM », pied « Quincaillerie de portes commerciales en aluminium ». Mis à jour dans frontend/public/email/ ET backend/email_assets/.
  * Signatures texte : erp_helpers.wrap_branded_email (pied courriel), prospection_routes.py (toutes campagnes), erp_monthly_recap.py (pied), gabarits PDF clients erp_pdf.py (tagline COMPANY, annexe conditions de vente, formulaire AT interactif, pied de page) et erp_pdf_production.py (tagline). Tous → « portes commerciales en aluminium ».
  * Laissé : prompts LLM internes (cut_routes, erp_routes_expenses), inspector_title « Expert Portes Commerciales », « toutes les portes commerciales » (service quincaillerie).
  * Vérif : imports OK, quote PDF rendu OK, footer courriel contient le nouveau texte, images revues visuellement. EN PREVIEW — redéployer pour portech.info (les courriels prod pointent vers https://portech.info/email/*.png).

- MAJ 2026-06 (Conditions de vente — dépôt 30% → 50%) : erp_pdf.py SALES_CONDITIONS clause 12 « CONDITIONS DE PAIEMENT » → dépôt de 50% à l acceptation. Seule occurrence dans les conditions de vente. PDF soumission rendu OK. EN PREVIEW — redéployer.

- MAJ 2026-08 (ADJOINTE VIRTUELLE — Brique 1 : Suivi des jobs) : FAIT + TESTÉ (agent 100% : 16/16 backend pytest + 7/7 flux frontend E2E, iteration_16.json).
  * Nouveau module : erp_routes_jobs.py (collection erp_jobs). Pipeline : a_approuver → depot_recu (50%) → en_fabrication → pret → livre → facture → paye (+ annule). Endpoints /api/admin : GET/POST /jobs, GET /jobs/stages, POST /jobs/from-quote/{quote_id} (idempotent), GET/PUT/DELETE /jobs/{id}, PATCH /jobs/{id}/stage {stage,note} (+historique), POST /jobs/{id}/links, POST /jobs/{id}/unlink (body — supporte doc_id avec '/'), GET /jobs-briefing/preview, POST /jobs-briefing/send.
  * Dépôt attendu auto-calculé = 50% du total. Champs nullables (target_date, client_email, party_id, notes) effaçables via PUT null.
  * Briefing quotidien : scheduler AsyncIOScheduler 7h30 America/Montreal (start_jobs_briefing_scheduler dans server.py) → courriel HTML brandé (helper send_html_email dans erp_helpers.py) à BRIEFING_EMAIL (fallback LEADS_RECIPIENT_EMAIL = portech.infos@gmail.com). Résume : compte par étape, en retard, à livrer d'ici 7j, en attente d'approbation/dépôt, en fabrication, prêtes.
  * Frontend : onglet "Suivi des jobs" (slug suivi-jobs) = JobsPanel.jsx, tableau Kanban (colonnes par étape, cartes déplaçables ◀▶), modale création, "Depuis une soumission" (picker), modale détail (édition, changement d'étape, documents liés add/remove, historique), modale briefing (aperçu + envoi manuel).
  * Choix client : commencer par la Brique 1 (fait) ; création job auto (depuis soumission) + manuelle ; briefing courriel matinal. EN PREVIEW — redéployer pour portech.info.

- BACKLOG : Brique 2 — Assistante IA (chat) : chat LLM lisant les données ERP (jobs, factures, soumissions) pour répondre en langage naturel + rédiger courriels/relances + briefing conversationnel. Modèle "choisis pour moi" → proposer Claude Sonnet 4.6 (rédaction FR) via Emergent LLM key. NON commencé.

- MAJ 2026-08 (Catalogue quincaillerie — import prix USD→CAD + taux configurable) : FAIT + backend vérifié (curl).
  * Backend (erp_routes_production_plans.py) : GET/PUT /api/admin/settings/exchange-rate (collection erp_settings, clé usd_cad_rate, défaut 1.38) ; POST /api/admin/production-hardware/import {rows:[{part_number,description,list_price_usd}], dry_run, markup_pct=30, vendor}. Logique : cost_cad = round(usd × taux, 2) ; price = arrondi 0,05$ (cost × 1.30). Upsert par part_number (existe → MàJ cost+price ; sinon création). dry_run=true → aperçu sans écriture. Vérifié : 100 USD×1.4=140 → vendant 182.00 ; 250.33→350.46→455.60 ; re-import même part# = update.
  * Frontend : nouvel onglet « Catalogue quincaillerie » (slug catalogue-quincaillerie) = CatalogPanel.jsx : éditeur de taux de change, import par collage (Nº pièce / description / prix USD, aperçu puis commit), table des articles (recherche, édition inline coût/vendant, suppression). Compile OK. UI pas encore testée E2E par l'agent.
  * DÉCISIONS client : taux fixe configurable ; vendant = coûtant CAD × 1.30 arrondi 0,05$ ; dedup par part# = MàJ coût + recalcul vendant.
  * BLOQUÉ : le fichier de prix envoyé (Adams_Rite_..._partial.pdf) ne contient QUE la page couverture (aucune donnée). Besoin du fichier de prix COMPLET pour extraire/importer. Fichiers dans /app/backend/vendor_catalogs/.

- MAJ 2026-08 (Suivi jobs — vue mobile + documents liés cliquables) : FAIT (frontend, compile OK, pas testé E2E ce tour).
  * JobsPanel.jsx : sur mobile (<sm) liste compacte par étape avec ◀▶ ; kanban sur sm+. Documents liés : sélecteur de vrais documents (soumission/facture/BC/connaissement/plan) + ouverture (« ouvrir ↗ ») via routes d'impression (facture/BC/connaissement) ou PDF blob (soumission/plan). Références manuelles restent en texte. Backend : POST /jobs/{id}/unlink (robuste aux '/').

- BACKLOG P1 : Dessins Adams Rite dans PDF soumission/fabrication. Parts Manual (adams_rite_parts_manual.pdf, 79 pages, 100% texte, index p.2) → construire un index série/part# → page, permettre de cocher quelles pages inclure selon la quincaillerie choisie, et annexer ces pages au PDF. Auto-détection confirmée faisable.
- BACKLOG P1 : Import réel du catalogue de prix Adams Rite dès réception du PDF complet.

- MAJ 2026-08 (Import prix Adams Rite + dessins dans soumissions) : FAIT + TESTÉ (frontend 4/4 iteration_17.json, backend curl 100%).
  * DÉCOUVERTE : le Parts Manual (79 p.) contient AUSSI les prix (colonne « 2026 PRICE »). Parseur /app/backend/parse_adams_rite.py → 480 lignes, 294 numéros de pièce uniques. IMPORTÉS dans le catalogue (erp_production_hardware) via POST /production-hardware/import (taux 1,40 au moment de l'import ; ex. 14 USD → 19,60 coût → 25,50 vendant). Le pricelist PDF fourni ne contenait qu'une page couverture (inutilisable) — les prix viennent du Parts Manual.
  * DESSINS DANS SOUMISSIONS : nouveau module /app/backend/adams_rite_drawings.py (load_index parse le sommaire p.2 → 39 dessins {label, page} ; merge_drawing_pages annexe la page dessin + page pièces via pypdf). Endpoints : GET /api/admin/adams-rite/drawings ; PATCH /api/admin/quotes/{id}/drawings {pages:[int]}. Champ Quote/QuoteIn.drawing_pages. GET /quotes/{id}/pdf et send-email annexent automatiquement les pages choisies (vérifié : PDF 3→5 pages avec [24]). Auto-détection par série (ex. 3600 CVR → p.24).
  * Frontend : QuotesPanel — action « Dessins » par soumission (icône compas) ouvre DrawingsModal (recherche + cases à cocher, persistance). Onglet « Catalogue quincaillerie » = CatalogPanel (taux de change, import par collage aperçu+commit, gestion coût/vendant). Vérifiés E2E.
  * Points cosmétiques corrigés : préfixes SO-/FAC-/BC-/CN- dans le picker de documents liés ; boutons ◀▶ mobiles horizontaux + opacité désactivée relevée. Manuel stocké : /app/backend/vendor_catalogs/adams_rite_parts_manual.pdf.
  * TOUT EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-08 (Dessins auto depuis quincaillerie + dessins dans plan de fabrication) : FAIT + backend vérifié (curl).
  * adams_rite_drawings.detect_from_hardware(texts) : associe la quincaillerie (description + part_number) aux dessins du manuel via tokens de série (codes à ≥3 chiffres, ex. 3600, MS1850S, 8800, 4591) avec correspondance bornée (évite faux positifs). Vérifié : « 3600 CVR »+« 4591-01 » → p24 + p68 ; générique → aucun.
  * ProductionPlan : champs include_hardware_drawings (défaut True) + drawing_pages (pages manuelles). _plan_drawing_pages(doc) = union manuelles + auto-détectées.
  * PDF du plan (download, preview-pdf, send-email) annexe désormais les pages détectées (vérifié : plan 5 → 9 pages avec 3600+4591). Nouvel endpoint GET /production-plans/{id}/detect-drawings (aperçu UI : detected, manual_pages, auto, all_drawings).
  * Frontend ProductionPlansPanel : case « Joindre les dessins Adams Rite (auto. selon la quincaillerie) » (data-testid pp-hw-drawings, défaut coché) + defaults utils.js. Compile OK. Case UI pas testée E2E par l'agent (backend prouvé).
  * EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-08 (Import catalogue de prix COMPLET Adams Rite + produits sélectionnables) : FAIT + vérifié (curl).
  * Fichier complet reçu (Adams_Rite_Feb_2_2026_Pricelist.pdf, 52 p., texte extractible). Parseur /app/backend/parse_adams_rite_pricelist.py → 282 numéros de produit uniques (part_number, description, prix USD).
  * Endpoint import étendu : param to_products (bool). Import lancé avec to_products=true, taux 1,40, majoration 30% arrondi 0,05$.
  * Résultat : catalogue quincaillerie erp_production_hardware = 575 articles (294 Parts Manual + 282 pricelist). Module Produits erp_products = 282 produits Adams Rite (sku=part_number, name='<sku> · <desc>', unit_price=vendant, cost_price=coûtant, category='Adams Rite'). Ex. 1004 → 50 USD → coûtant 70 → vendant 91.
  * Produits sélectionnables en SOUMISSIONS et FACTURES : DocumentPanel.jsx charge /admin/products, DocumentForm.jsx pickProduct → quick-pick. Confirmé.
  * Fix : ProductionHardware.name limité à 120 car. → troncature dans l'import (une description dépassait). CatalogPanel import par collage envoie désormais to_products=true.
  * Note technique : les gros POST via l'URL externe sont bloqués par Cloudflare (err 1010) — utiliser localhost:8001 pour les imports en masse côté agent. EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (Seed auto catalogue Adams Rite en PRODUCTION + fusion calculateur de prix dans les soumissions) : FAIT + VÉRIFIÉ.
  * PROBLÈME : le client ne voyait pas les 282 produits / 575 quincailleries sur portech.info. Cause = les imports avaient été faits dans la base du PREVIEW ; la PRODUCTION a une base SÉPARÉE. Le redéploiement pousse le code mais PAS les données importées.
  * SOLUTION (seed auto) : snapshot JSON groupé dans le repo — /app/backend/seed_data/adams_rite_products.json (282) + adams_rite_hardware.json (575). Nouveau module /app/backend/seed_adams_rite.py : seed_adams_rite_catalog(db) insère ces lignes UNIQUEMENT si la collection n'a aucune ligne category='Adams Rite' (idempotent, ne touche jamais aux données existantes, dédup par id/part_number). Branché au startup de server.py juste après seed_admin() (try/except pour ne jamais bloquer le démarrage). Prouvé : sur une base vide → 282 + 575 insérés ; 2e passage → aucun doublon. Donc APRÈS REDÉPLOIEMENT, la production aura automatiquement les mêmes produits que le preview (Produits, Catalogue quincaillerie, PDF catalogue, sélecteur soumissions/factures, détection dessins plans).
  * FUSION calculateur de prix : suppression du composant autonome PricingCalculator.jsx (bloc-notes déconnecté en haut de l'onglet Soumissions) — fichier supprimé + import retiré de QuotesPanel.jsx. Ses fonctions ont été fusionnées dans le ProfitMarginPanel du formulaire de soumission (DocumentForm.jsx) qui travaille sur les VRAIES lignes : tableau par ligne (desc, catégorie via produit lié, qté, coût, vente, marge), rentabilité projet (coût/vente/profit/markup/marge), profit par catégorie, simulateur de markup (+5..+100 % + perso), solveur de prix pour marge cible (30..60 % + perso), objectifs marge mini/cible éditables+enregistrables (PUT /admin/pricing/settings) avec alerte « sous le minimum »/« sous la cible », ajustement +X % en 1 clic sur toutes les lignes. Confidentiel — jamais sur le PDF. Aucune soumission perdue (changement d'interface seulement). Vérifié à l'écran : produit Adams Rite 1850S → coût 128,80 / vente 167,45 / markup 30,0 % / marge 23,1 %.
  * EN PREVIEW — redéployer pour que portech.info reçoive le code + le seed auto.


- MAJ 2026-09 (États de compte + facture coûts/profits + réponse auto site + conditions de vente optionnelles + annexes soumission + automatisations + Assistante IA) : FAIT + TESTÉ (agent iteration_18 : backend 7/7, frontend 8/8, 0 bug bloquant).
  * DÉPLOYÉ EN PRODUCTION (portech.info) — 2 environnements distincts. Redéployer pour pousser ces changements.
  * BLOQUEURS DÉPLOIEMENT réglés : reçus de dépenses (erp_routes_expenses.py) migrés vers GridFS (bucket expense_receipts, persistant aux redéploiements) ; uploads de coupes (cut_routes.py) → fichiers temporaires (transient, supprimés après OCR/DXF) ; F811 mm dans erp_pdf_production.py corrigé. Helpers GridFS durcis (dict-or-object) par l'agent de test.
  * ÉTATS DE COMPTE : nouveau module erp_routes_statements.py + render_statement_pdf (erp_pdf.py) + onglet « États de compte » (slug etats-de-compte, StatementsPanel.jsx). Regroupe les factures IMPAYÉES (statut « envoyée ») par client, PDF brandé (solde dû par facture + solde total), aperçu + envoi par client + « Envoyer à tous ». Endpoints GET /admin/statements/customers, GET /admin/statements/{key}/pdf, POST /admin/statements/{key}/send, POST /admin/statements/send-all. Auto mensuel : start_statements_scheduler (1er du mois 09:00).
  * FACTURE COÛTS/PROFITS : le ProfitMarginPanel (calculateur fusionné) s'affiche aussi sur le formulaire de FACTURE (DocumentForm kind invoice) — la conversion soumission→facture (déjà existante) conserve product_id donc coûts/profits calculés automatiquement.
  * RÉPONSE AUTO SITE : send_lead_autoreply dans server.py — sur POST /api/contact, courriel d'accusé de réception bilingue (français puis anglais plus petit) au demandeur, délai « dans les plus brefs délais / as soon as possible », reply_to = portech.infos@gmail.com.
  * CONDITIONS DE VENTE OPTIONNELLES : Quote.include_sales_conditions (défaut FALSE). render_quote_pdf n'ajoute l'annexe des 21 conditions QUE si coché. Case UI « Joindre les conditions de vente » (doc-quote-sales-conditions), décochée par défaut.
  * ANNEXES SOUMISSION : auto-détection dessins Adams Rite DÉSACTIVÉE par défaut (ProductionPlan.include_hardware_drawings défaut False ; quotes déjà 100% manuel via drawing_pages). Nouveau : téléversement de fichiers PDF/images propres joints au PDF de la soumission (quote_attachments.py, GridFS bucket quote_attachments, merge pypdf + images→PDF via PIL). Endpoints POST/DELETE /admin/quotes/{id}/attachments. Bloc UI « Fichiers en annexe » (quote-attachments) dans le formulaire.
  * AUTOMATISATIONS : (a) relances factures impayées — planificateur existant confirmé actif (08:00) ; (b) suivi soumissions envoyées sans réponse — start_quote_followup_scheduler (quotidien 08:30, courriel client 1×, idempotent via followup_sent_at, >7 jours) ; (c) états de compte mensuels auto (voir plus haut).
  * ASSISTANTE IA (Brique 2) : erp_routes_assistant.py — POST /admin/assistant/chat (+ GET/DELETE /assistant/history). Claude Sonnet 4.6 (anthropic/claude-sonnet-4-6) via EMERGENT_LLM_KEY (emergentintegrations LlmChat, non-streaming). Multi-tours via Mongo erp_assistant_messages (rejoué dans le system prompt) + snapshot ERP live (jobs par étape, factures impayées, soumissions en cours) injecté en contexte. Onglet « Assistante IA » (slug assistante-ia, AssistantPanel.jsx) : chat FR, suggestions, réinitialisation. Vérifié : répond correctement (4 factures impayées, solde 5 367,04 $).
  * RESTE / cosmétique : remplacer les <input type=date> natifs (mm/dd/yyyy US) par un sélecteur locale fr-CA (signalé iter17, non bloquant).

- MAJ 2026-09 (Assistante IA — ACTIONS : envoi d'états de compte et de relances depuis le chat) : FAIT + VÉRIFIÉ bout en bout.
  * erp_routes_assistant.py : couche d'actions ajoutée. Le system prompt décrit 3 actions déclenchables : send_statement (un client), send_statement_all (tous), send_quote_followup (une soumission SO-XXXX).
  * SÉCURITÉ : confirmation OBLIGATOIRE en 2 temps. Tour 1 = l'assistante résume précisément ce qui sera envoyé + demande « Confirmes-tu ? Réponds oui » (AUCUN envoi). Tour 2 (après « oui ») = elle termine par une ligne directive [[ACTION]] {json} que le backend parse (ACTION_RE), exécute (_execute_action réutilise erp_routes_statements.send_statement_email/unpaid_groups et send_html_email pour les relances), retire la directive du texte affiché et ajoute une confirmation ✅/⚠️. Réponse API expose aussi action_result.
  * Réponses en TEXTE SIMPLE (pas de Markdown) pour un rendu propre dans le chat.
  * Vérifié : tour 1 → résumé + demande de confirmation (action_result None) ; tour 2 « oui » → « ✅ État de compte envoyé à Validation E2E Inc (info@portech.info) ». Entrées invalides → avertissements sûrs sans envoi.
  * Suggestions du panneau (AssistantPanel.jsx) mises à jour avec 2 exemples d'action.


- MAJ 2026-09 (App dédiée « Adjointe Portech » — chat vocal installable) : FAIT + VÉRIFIÉ.
  * Route dédiée /adjointe (App.js) → pages/AdjointeApp.jsx : interface plein écran responsive (mobile + ordinateur), thème sombre, en-tête « Adjointe Portech », suggestions, bulles de chat, bouton micro, champ texte, toggle voix, réinitialiser, déconnexion. Réutilise les endpoints /admin/assistant/chat + /history (mêmes actions confirmées : états de compte, relances).
  * PWA installable : public/manifest.json renommé « Adjointe Portech » (short_name « Adjointe »), start_url /adjointe ; index.html apple-mobile-web-app-title = « Adjointe Portech ». Installable sur l'écran d'accueil ; ouvre directement le chat. L'ERP reste accessible au navigateur via /admin.
  * DICTÉE VOCALE (Whisper) : POST /api/admin/assistant/transcribe (erp_routes_assistant.py) — emergentintegrations OpenAISpeechToText, model whisper-1, language fr, via EMERGENT_LLM_KEY. Front : MediaRecorder (webm) → upload → texte → envoi auto. Vérifié HTTP 200.
  * LECTURE À VOIX HAUTE : synthèse vocale intégrée du navigateur (window.speechSynthesis, voix fr-CA) — gratuite, hors coût API. Toggle global + bouton haut-parleur par message.
  * SESSION PERSISTANTE (auth) : token JWT déplacé de sessionStorage → localStorage (context/AuthContext.jsx) ET ACCESS_TOKEN_TTL_MIN passé de 8 h à 30 jours (server.py). Le propriétaire se connecte une fois sur le téléphone et reste connecté ~30 jours. Compromis sécurité assumé (outil mono-utilisateur sur appareil personnel). AdminLogin.jsx : support du paramètre ?next= (useSearchParams) → après connexion depuis /adjointe, retour à /adjointe.
  * Vérifié à l'écran : /adjointe rend l'app, connexion→next→/adjointe OK, message « Combien de jobs actifs ? » → réponse correcte « aucun job actif », bouton lecture vocale présent. NB : le micro exige HTTPS (preview/prod OK) + autorisation micro du navigateur.


- MAJ 2026-09 (Assistante : action « changer l'étape d'un job » + bouton d'installation dans l'app dédiée) : FAIT + VÉRIFIÉ.
  * ACTION update_job_stage (erp_routes_assistant.py) : l'assistante change l'étape d'un job par chat/voix (ex. « passe le job 12 en installation »). Exécutée DIRECTEMENT (réversible, sans courriel — pas de double confirmation, contrairement aux envois de courriel). _resolve_stage tolère le langage libre (installation/fabric→en_fabrication, dépôt→depot_recu, prêt, livré, facturé, payé, annulé, approuver). Étapes valides : a_approuver, depot_recu, en_fabrication, pret, livre, facture, paye, annule. Retourne « ✅ Job #N : étape changée de X → Y ». Erreurs sûres (job introuvable, étape non reconnue). Prompt système mis à jour avec l'action + la liste des étapes. Vérifié e2e : « Passe le job 77 en fabrication » → BD stage=en_fabrication.
  * BOUTON D'INSTALLATION (AdjointeApp.jsx) : capture beforeinstallprompt (Android/Chrome → prompt() natif) ; sinon (iPhone/Safari) ouvre un modal d'instructions bilingue iPhone (Partager → Sur l'écran d'accueil) + Android (menu ⋮ → Installer l'application). Bouton icône dans l'en-tête + gros CTA « Installer sur mon téléphone » dans l'écran d'accueil. Caché si déjà en mode standalone (installé). Vérifié : CTA présent + modal s'ouvre.


- MAJ 2026-09 (Assistante : créer un job à la voix + résumé matinal parlé) : FAIT + VÉRIFIÉ e2e.
  * IMPORTANT correctif : les jobs utilisent job_number « JOB-0012 » (pas de champ number int). _erp_snapshot et update_job_stage corrigés pour utiliser job_number (lookup {$or:[job_number, number]}, format JOB-{n:04d}).
  * ACTION create_job (erp_routes_assistant.py) : « nouveau job porte arrière chez Clinique Laval » → crée un job (title obligatoire, client optionnel), numéro via next_number('job') → JOB-XXXX, étape a_approuver, history initial. register_assistant reçoit désormais next_number (erp.py) et assigne le module-level _create_job_fn. Exécuté DIRECTEMENT (réversible). Vérifié e2e : « JOB-0011 « Porte arrière » pour Clinique Laval ».
  * RÉSUMÉ MATINAL PARLÉ : GET /api/admin/assistant/briefing → texte simple (factures impayées + solde + jobs actifs + jobs à livrer aujourd'hui/en retard). Front AdjointeApp.jsx : bouton Sunrise (en-tête) + CTA « Mon résumé du matin » (écran d'accueil) + AUTO 1×/jour à l'ouverture (localStorage portech_adjointe_briefing_date) → affiché comme message + LU À VOIX HAUTE (speechSynthesis). loadHistory ne remplace plus par un historique vide (évite d'effacer le briefing). Vérifié : briefing auto affiché + parlé, bouton présent.


- MAJ 2026-09 (Assistante « fait tout » : date de livraison + suite d'actions ERP) : FAIT + VÉRIFIÉ.
  * Nouvelles actions (erp_routes_assistant.py, exécutées directement car réversibles/sans courriel) :
    - update_job {job, target_date (ISO), title, client, notes, total, deposit} — dont la DATE DE LIVRAISON. L'IA convertit le langage parlé (« vendredi », « demain », « le 15 ») en ISO AAAA-MM-JJ ; la date du jour + le jour de semaine sont injectés dans _erp_snapshot. Le backend valide ISO_DATE_RE (sinon avertissement). Vérifié e2e : « livraison du job 88 vendredi prochain » (jeu. 2026-09-24) → 2026-09-25 en base.
    - mark_invoice_paid {invoice: FAC-XXXX} → statut payée.
    - update_quote_status {quote: SO-XXXX, status} → brouillon/envoyée/acceptée/refusée/expirée/annulée (mappe accepté→acceptée, etc.).
    - create_client {name, email, phone, city, address} → insert erp_parties (Party model).
  * Helper _num_from (parse FAC-/SO-/JOB- → int). Prompt système mis à jour avec toutes les actions + exemples de directives + règle ISO pour les dates.
  * LIMITE connue : une seule directive [[ACTION]] par message (ACTION_RE prend la première). La création de soumissions/factures avec lignes détaillées reste dans l'UI ERP (trop complexe pour une commande vocale unique).
  * Récap complet des capacités de l'assistante : états de compte (1 client / tous, avec confirmation), relance soumission (avec confirmation), changer étape de job, créer job, modifier job (date livraison/titre/client/notes/total/dépôt), marquer facture payée, changer statut soumission, créer client, résumé matinal parlé.


- MAJ 2026-09 (Accès leads + Google Calendar) : leads FAIT+TESTÉ; Google Calendar IMPLÉMENTÉ (connexion à activer en prod).
  * LEADS : _erp_snapshot inclut les demandes du site (contact_submissions, non traités). Actions assistant reply_lead (courriel, confirmation) + mark_lead_done (assistant_status=traité). Testé.
  * GOOGLE CALENDAR : google_calendar.py (OAuth flow, refresh, create_event, list_upcoming). Routes /api/oauth/calendar/login|callback + /api/admin/calendar/status. GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI dans .env (redirect = https://portech.info/api/oauth/calendar/callback → connexion possible SEULEMENT en prod). Action assistant create_appointment (crée evenement Google, convertit demain 14h en ISO) + prochains RDV injectés dans le snapshot. Bouton Connecter Google Calendar dans AdjointeApp. Backend testé (status configured=true/connected=false, URL auth valide, message not-connected gracieux). Connexion réelle à faire après redeploy sur portech.info/adjointe.
  * PUSH NOTIFICATIONS : PAS ENCORE construit (VAPID + service worker + abonnement) — prochaine étape. Rappel: courriel nouveau lead + resume matinal existent deja.

- MAJ 2026-06 (NOTIFICATIONS PUSH — Web Push / VAPID) : FAIT + backend testé (curl). Delivery réelle vérifiable seulement sur PWA installée après redéploiement.
  * Backend : push_notifications.py (paire de clés VAPID générée UNE fois et stockée dans Mongo erp_settings clé « vapid_keys » → survit aux redéploiements ; PEM écrit dans /tmp pour pywebpush ; send_push() encode + envoie via pywebpush, aud = origine de l'endpoint (OK APNs/Apple), prune auto 404/410). Lib : pywebpush 2.5.0 + py-vapid 1.9.4 (cryptography maj 50.0.1). Collection push_subscriptions (index unique endpoint).
  * Routes (erp_routes_push.py, sous /api/admin, auth) : GET /push/vapid-public-key, POST /push/subscribe (upsert), POST /push/unsubscribe, POST /push/test. Câblé dans erp.py register_push + server.py startup (ensure_vapid_keys + index).
  * ÉVÉNEMENTS (choix client = TOUS) : (a) nouveau lead → push dans server.py create_contact_submission ; (b) factures en retard + (c) jobs du jour → push résumé matinal via start_push_scheduler cron 5h30 America/Montreal (run_morning_push : jobs actifs + à livrer/en retard + factures en retard) ; (d) nouveau RDV Google Calendar → push dans l'action create_appointment de l'assistant.
  * Frontend : service-worker.js (cache v5) → handlers push + notificationclick (ouvre/focus /adjointe). AdjointeApp.jsx : bouton cloche en-tête (adjointe-push-toggle) + CTA écran d'accueil (adjointe-push-cta) « Activer les notifications ». enablePush : Notification.requestPermission → subscribe(applicationServerKey=clé VAPID) → POST subscribe → push de confirmation. disablePush pour désabonner.
  * iPhone : push fonctionne SEULEMENT si l'app « Adjointe » est installée sur l'écran d'accueil (Partager → Sur l'écran d'accueil) sous iOS 16.4+, et l'activation doit venir d'un tap. Testé backend (vapid key générée, subscribe/test/morning push OK). EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (Numéros de taxe sur factures) : COMPANY['tps']='792834644' + COMPANY['tvq']='4032540070' (erp_pdf.py). Ligne « Nº TPS : … · Nº TVQ : … » ajoutée sous les totaux dans render_invoice_pdf. Vérifié (extraction texte PDF). EN PREVIEW — redéployer.

- MAJ 2026-06 (Suivi des jobs — pipeline administratif enrichi + vues + leads auto + push) : FAIT + vérifié (curl + captures + tests unitaires).
  * NOUVEAU PIPELINE (erp_routes_jobs.py JOB_STAGES) : lead → soumission_a_produire → soumission_envoyee (relance) → dessin_a_produire → attente_depot → depot_recu → en_fabrication → pret → livre → facture → paye (+ annule « Annulé / Perdu »). Ancien « a_approuver » migré → attente_depot (LEGACY_STAGE_MAP + migrate_and_backfill_jobs au startup ; STAGE_PATTERN accepte encore l'ancien pour compat).
  * LEADS AUTO (choix 3a) : create_lead_job(db, sub) crée un job étape « lead » (source=lead, lead_id) idempotent. Appelé dans server.py POST /api/contact (chaque nouvelle demande du site) + backfill au démarrage des leads non « traité » sans job. Job model : + champs source, lead_id. JobIn : + stage (défaut soumission_a_produire).
  * VUES RAPIDES (choix 2a) : frontend JobsPanel.jsx — barre de filtres au-dessus du MÊME Kanban : Tous · Leads · Soumissions à produire · En attente de réponse · Dessins à produire (avec compteurs). visibleStages filtre les colonnes (desktop + mobile).
  * RELANCE (choix 4b) : rappel VISUEL seulement (pas de courriel auto). Badge « En attente depuis X j · à relancer » sur les cartes en soumission_envoyee (≥ 3 j = ambre gras). Briefing courriel : nouvelle section « À relancer ».
  * PUSH (choix 5a) : (a) nouveau lead → push (server.py) ; (b) nouveau job en étape admin → _notify_new_job (create_job manuel + assistant _make_job) ; (c) résumé matinal 5h30 (push_notifications.run_morning_push) inclut désormais leads + à relancer (soumission_envoyee stale ≥3j) + à livrer/retard + factures en retard.
  * ASSISTANT (erp_routes_assistant.py) : JOB_STAGE_LABELS + JOB_STAGE_KEYWORDS + prompt système mis à jour aux nouvelles étapes ; _make_job crée en soumission_a_produire (source=assistant) + push. from-quote : non-accepté → soumission_envoyee, accepté → depot_recu.
  * Vérifié : /jobs/stages (12 étapes), création avec stage, migration (0 a_approuver), backfill (leads source=lead), rendu tableau + filtres + badge relance (captures), _resolve_stage OK pour toutes les étapes. EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (BUG FIX — dépenses scannées qui « disparaissent ») : FAIT + vérifié (capture).
  * CAUSE : la liste des dépenses est filtrée sur le mois courant. Quand l'OCR extrait une date dans un AUTRE mois (fréquent sur reçus d'essence/carburant), la dépense était bien enregistrée mais invisible → l'utilisateur croyait que ça n'avait pas sauvegardé et réessayait (doublons cachés dans un autre mois).
  * FIX (frontend ExpensesPanel.jsx save()) : après enregistrement, si le mois de la date sauvegardée ≠ mois affiché → bascule auto du filtre sur ce mois + bandeau vert « ✅ Dépense enregistrée au YYYY-MM ». Garde-fou description vide (fallback « Achat <fournisseur> » ou « Dépense ») pour éviter un 422 silencieux. Erreurs 422 (liste FastAPI) désormais affichées lisiblement. monthOptions inclut le mois sélectionné même hors des 12 derniers.
  * En prod, les tentatives précédentes du client peuvent exister comme doublons dans le mois de la date du reçu — à vérifier après redéploiement.

- MAJ 2026-06 (NOUVEAU MODULE — Rapport kilométrique) : FAIT + vérifié (curl + captures + rendu PDF).
  * Onglet « Rapport kilométrique » (slug kilometrage) dans AdminErp, après Dépenses. Panel MileagePanel.jsx.
  * Backend : erp_routes_mileage.py (collection erp_mileage). Modèle : date, client_id/client_name, origin, destination, purpose, odometer_start/end, distance_km, rate (défaut 0,73 $/km ARC/RQ 2026), amount (= km×taux, calculé serveur), vehicle, job_number, notes, ref (KM-0001 via make_next_number_fn « mileage »). SANS taxes. Distance : km direct OU odomètre début/fin (calcul auto max(0, fin-début)).
  * Endpoints (/api/admin) : GET /mileage/meta (default_rate), GET /mileage?month=&client_id=, GET /mileage/summary?month= (total km/$ + by_client), POST/PUT/DELETE /mileage, GET /mileage/{id}/report.pdf (rapport par trajet), GET /mileage/report.pdf?month=&client_id= (relevé regroupé). PDF auth via ?token= (get_current_admin lit le query param).
  * PDF (erp_pdf.py) : render_mileage_trip_pdf (en-tête Portech, bloc client, méta réf/date/véhicule/job, tableau départ→destination/motif/distance/taux/montant, TOTAL, note allocation RQ tout-inclus, ligne signature « Reçu par », nºs TPS/TVQ) + render_mileage_statement_pdf (relevé multi-trajets par client/période avec ligne TOTAL km+$). Style cohérent avec factures.
  * Frontend : tuiles (trajets/km/$), filtres mois+client, bouton « Relevé PDF », liste desktop + cartes mobile avec bouton PDF par trajet, modal avec bascule Km direct/Odomètre + distance & montant calculés en direct, répartition par client. PDF ouverts via URL token (comme états de compte).
  * Choix client : les deux (enregistrer + remettre PDF au client), les 2 formats PDF, km OU odomètre, sans taxes, 0,73 $/km défaut, SANS courriel (téléchargement/impression). Vérifié : km direct (42×0,73=30,66), odomètre (255,5 km=186,51), summary, PDF trajet+relevé (rendu pro confirmé). EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (Kilométrage — 3 améliorations : dashboard, facturation 1-clic, voix) : FAIT + vérifié (curl + chat LLM + capture).
  * DASHBOARD : erp_routes_dashboard.py ajoute kpi.mileage_km_month / mileage_amount_month / mileage_count_month. DashboardPanel.jsx : tuile « Kilométrage du mois » (montant + km + nb trajets). Vérifié (292 km / 213,16 $ + capture tuile).
  * FACTURATION 1-CLIC : POST /api/admin/mileage/invoice?month=&client_id= (erp_routes_mileage.py). Prend les trajets NON facturés du client pour le mois → crée une facture BROUILLON avec 1 ligne résumée « Frais de déplacement — X km (mois, N trajets) », AVEC TPS+TVQ (taxable=true, choix client), marque les trajets (invoiced_id/invoiced_number) pour éviter double facturation. Bouton « Facturer ce client » dans MileagePanel (visible quand un client est filtré) + badge « Facturé » sur les trajets. Vérifié : facture #348 subtotal 213,16 → total 245,08 (taxes), trajets marqués, re-facturation bloquée (400).
  * VOIX (Adjointe IA) : action create_mileage ajoutée au prompt + _execute_action (erp_routes_assistant.py). Params : distance_km (obligatoire), client, origin, destination, purpose, rate (défaut 0,73), date, round_trip. Réversible → émise directement. Match client par regex sur erp_parties. Vérifié via /admin/assistant/chat. EN PREVIEW — redéployer.

- MAJ 2026-06 (Kilométrage — 3 améliorations : filtre facturable, rapport annuel, voix aller-retour) : FAIT + vérifié (curl + chat LLM + captures + rendu PDF).
  * FILTRE FACTURABLE : MileagePanel.jsx — filtre segmenté Tous / À facturer / Facturés (client-side sur invoiced_id) + badge « À facturer : N trajet(s) · $ ». Rendu confirmé (capture).
  * RAPPORT ANNUEL : GET /api/admin/mileage/annual?year= (JSON : totals + by_month[12] + by_client) et GET /api/admin/mileage/annual.pdf?year= (PDF pro : en-tête, méta année/trajets/km/$, tableau 12 mois + TOTAL, détail par client, note fiscale RQ, TPS/TVQ). Routes déclarées AVANT /mileage/{id}/... (chemins .pdf distincts, pas de collision). render_mileage_annual_pdf dans erp_pdf.py (+_MONTHS_FR). Frontend : sélecteur d'année (5 ans) + bouton « Rapport annuel ». Vérifié (JSON totals 60 km/43,80 $, PDF rendu visuel « pour les impôts »).
  * VOIX ALLER-RETOUR : create_mileage accepte round_trip=true → crée le trajet aller + le retour (origin/destination inversés, purpose « Retour — … »). Prompt mis à jour (ex. « aller-retour de 30 km chez XYZ »). Vérifié via chat : KM aller + KM retour, 2×30 km = 43,80 $. EN PREVIEW — redéployer.


- MAJ 2026-06 (MASTER DE PRIX AT Fabrication — import comme référence coûts) : FAIT + vérifié (curl + capture).
  * Fichier de référence stocké : /app/backend/data/master_prix_reference.xlsx (donné par le client, 34 feuilles).
  * seed_master_pricing.py importe (idempotent, préserve les éditions manuelles) 4 collections : erp_hardware_master (102 quincailleries, LES 2 fournisseurs gardés), erp_door_prices (16 portes standards × groupes A-E), erp_pricing_params (20 paramètres : taux 50 $/h + matrice profit %), erp_extrusion_costs (21 profilés : coût mill + anodisation clair/noir). sync_hardware_to_production() aligne erp_production_hardware sur le coût le PLUS BAS par code. Appelé au startup de server.py.
  * erp_routes_master.py (/api/admin/master/*) : CRUD complet quincaillerie (recherche multi-mots description/code/couleur, filtres fournisseur/catégorie, meta), édition portes/params/extrusion, POST /master/reimport?force + /master/sync-production.
  * Frontend : onglet « Coûts Master » (slug couts-master) dans AdminErp → MasterCostsPanel.jsx, 4 sous-sections. Quincaillerie = CRUD + recherche + filtres + tuiles. Portes/Paramètres/Extrusion = édition en ligne (onBlur PUT). TOUT modifiable manuellement.
  * Choix client : importer maintenant, dans les 2 (catalogue production + onglet dédié), garder les 2 fournisseurs, + portes/extrusion/params, réimport futur en redonnant le fichier + édition manuelle. Vérifié : 102/16/20/21 importés, recherche « panique 8400 36 » = 9 résultats, synchro production (paniques → 365,80 $). EN PREVIEW — redéployer.
  * BACKLOG P1 : moteur de calcul auto des prix de porte (LDP) à partir des paramètres MASTER + extrusion + quincaillerie (Phase 2 pricing) — pas encore fait.
- MAJ 2026-06 (MOTEUR DE PRIX DE PORTE — calculateur type LDP) : FAIT (calculateur) + vérifié (curl exact + capture). Intégration DANS la soumission = PROCHAINE étape (P0).
  * seed_master_pricing._parse_door_models importe 24 modèles LDP → collection erp_door_models {model_key, label, series, finish, size, hand, isolated, is_pair, material_cost, labor_cost, labor_hours, material_labor_cost, profit_pct, hardware[{code,description,cost}], hardware_cost}. (2 feuilles ignorées : gabarit DSP.)
  * Moteur (erp_routes_master.py) : GET /master/door-models, POST /master/price-door {model_key, hardware[], profit_pct?, labor_hours?}. Formule = (mat+M.O.)×(1+profit_pct) + quincaillerie×(1+0.35). Taux 50$/h + markup 0.35 lus depuis erp_pricing_params. Vérifié : AT1000-10-36X84MDR → coût 555,54 / vendant 832,15 / marge 276,61 (49,8%) = IDENTIQUE au LDP (cellule AT29).
  * Frontend : sous-section « Calculateur de prix » dans MasterCostsPanel (CalculatorSection) : choix modèle → quincaillerie standard pré-remplie (ajout/retrait via recherche master), heures + profit ajustables → coûtant/marge$/marge%/PRIX VENDANT en direct. Calcul client-side (miroir du moteur). Vérifié par capture.
  * RESTE À FAIRE (P0) : intégrer le calculateur DANS le constructeur de soumission (ajouter une porte → prix auto + coûtant/marge PAR LIGNE et TOTAL, visible admin seulement, jamais sur le PDF client). Endpoint /master/price-door déjà prêt à réutiliser.

- MAJ 2026-06 (PRICING Phase 2 — Calculateur de porte LDP INTÉGRÉ au constructeur de soumission) : FAIT + TESTÉ (backend curl + frontend e2e).
  * DEMANDE client (résolue) : « Afficher le coûtant et la marge en direct pendant que tu bâtis une soumission de porte. » Le calculateur autonome (Coûts Master) est maintenant branché DANS le formulaire de soumission ET de facture.
  * Frontend (DocumentForm.jsx) : nouveau bouton « Ajouter une porte (LDP) » (data-testid doc-quote-add-door / doc-invoice-add-door) à côté de « + Ligne ». Ouvre DoorBuilderModal (data-testid door-builder-modal) : choix modèle LDP (/admin/master/door-models), quincaillerie pré-remplie (ajout/retrait via recherche /admin/master/hardware), heures M.O. + profit + qté ajustables ; COÛTANT / MARGE $ / % / PRIX VENDANT en DIRECT (mêmes formules que le moteur : (mat+M.O.)×(1+profit) + quinc.×(1+0.35)). Bouton « Ajouter à la soumission » (door-builder-add) crée une ligne : desc « Porte — <label> (quincaillerie incluse) », qté, unit_price=vendant, cost_price=coûtant, cost_category="Portes".
  * Le panneau confidentiel ProfitMarginPanel (déjà en bas des soumissions/factures) affiche désormais la ligne de porte : coût/vente/marge PAR LIGNE + rentabilité totale (coût, vente, profit, markup, marge) + profit par catégorie « Portes ». Rows utilisent product.cost_price OU it.cost_price (fallback), catégorie via product OU it.cost_category.
  * Backend : erp_models.LineItem + champs CONFIDENTIELS cost_price + cost_category (extra="ignore" ailleurs). VÉRIFIÉ : persistent au refetch, préservés à la conversion soumission→facture, et JAMAIS rendus sur le PDF (_items_table_money n'utilise que description/qty/unit_price/total — extraction texte du PDF confirme coûtant absent, vendant présent).
  * Vérifié e2e : modèle AT1000-36X84-MDR → coûtant 555,54 $ / marge 276,61 $ (49,8 %) / vendant 832,15 $ = identique au moteur ; ligne ajoutée, totaux TPS/TVQ OK, panneau rentabilité affiche la porte. EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (4 items post-calculateur porte : recherche Adams Rite, filtre Produits, portes multiples, Récap TPS/TVQ) : FAIT + TESTÉ (backend curl + frontend e2e).
  1. RECHERCHE PRODUIT (DocumentForm.jsx) : le <select> produit des lignes de soumission/facture remplacé par ProductPicker (combobox) — recherche par NOM + SKU (nº pièce Adams Rite) + catégorie, dropdown 25 max, puce SKU + effacer. Vérifié : « 1850 » → 1850S/MS1850S.
  2. FILTRE PRODUITS (ProductsPanel.jsx) : barre recherche (nom/SKU/desc) + <select> catégorie (avec compte) + bouton raccourci « Adams Rite » + Réinitialiser + compteur de résultats. Filtrage client-side. Vérifié : filtre Adams Rite → 282.
  3. PORTES MULTIPLES (DoorBuilderModal) : case « Une ligne distincte par porte » (visible si qté>1) → ajoute N lignes séparées (qté 1 chacune, desc « … · nº i/N ») au lieu d'une ligne ×N. addDoorLines accepte un tableau. Vérifié : qté 3 + split → 3 lignes.
  4. RÉCAP TPS/TVQ TRIMESTRIEL : backend erp_routes_tax_recap.py (GET /admin/tax-recap?year=&quarter= JSON + /tax-recap/pdf token) — TAXES PERÇUES (factures envoyée+payée datées dans le trimestre) − CRÉDITS DE TAXE (dépenses du trimestre) = NET par TPS/TVQ. render_tax_recap_pdf dans erp_pdf.py (brandé, nº TPS/TVQ, net à remettre/remboursement). Frontend TaxRecapPanel.jsx (onglet « Récap TPS/TVQ », slug recap-taxes) : sélecteur année + T1-T4, cartes perçu/payé, tableau net, aperçu PDF. Vérifié Q2 2026 : perçu 208,40/415,76 (3 fact.), payé 0,50/1,00 (1 dép.), net 622,66 $ ; PDF 200.
  * EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (Dépôt sur facture + envoi récap comptable + rappel trimestriel + portes variées) : FAIT + TESTÉ (backend curl + frontend e2e).
  * DÉPÔT REÇU SUR FACTURE (demande principale) : Invoice/InvoiceIn + deposit_received(bool), deposit_pct(float), deposit_amount, balance_due. Calcul = total (TAXES INCLUSES) × pct → dépôt ; solde = total − dépôt. erp_routes_invoices create/update calculent + stockent. render_invoice_pdf/_totals_box affichent : Sous-total → TPS → TVQ → TOTAL → « Dépôt reçu (X %) −montant » (rouge) → « SOLDE À PAYER » (vert). États de compte (unpaid_groups + render_statement_pdf) utilisent balance_due si dépôt reçu. Frontend DocumentForm (facture) : case « Dépôt reçu » + champ % + solde à payer en direct dans l'encadré totaux. Vérifié : 1000 $ +taxes = 1149,75 → dépôt 50 % 574,88 → solde 574,87 ; PDF contient SOLDE À PAYER/Dépôt/50 %.
  * BUG CORRIGÉ : DocumentPanel.save() strippait cost_price/cost_category des lignes → le coûtant des portes (calculateur LDP) était perdu à l'enregistrement via l'UI. Corrigé (préserve cost_price + cost_category).
  * ENVOI RÉCAP AU COMPTABLE : erp_routes_tax_recap — GET/PUT /admin/tax-recap/settings (accountant_email dans erp_settings clé tax_recap) + POST /admin/tax-recap/send {year,quarter,to_email?} (render PDF + send_pdf_email brandé). Frontend TaxRecapPanel : champ « Courriel du comptable » + Enregistrer + bouton « Envoyer au comptable ». Vérifié : send → {"sent":true}.
  * RAPPEL TRIMESTRIEL AUTO : start_tax_reminder_scheduler (CronTrigger month=1,4,7,10 day=1 08:00 America/Montreal) → run_tax_reminder : calcule le trimestre qui vient de fermer (_prev_quarter : jan→T4 an-1, avr→T1, juil→T2, oct→T3), PUSH (send_push, url /admin/gestion/recap-taxes) à tous les appareils + COURRIEL (PDF joint) au propriétaire (BRIEFING_EMAIL/LEADS_RECIPIENT) + comptable. Wiré dans server.py startup. Vérifié : scheduler démarre, _prev_quarter OK.
  * PORTES VARIÉES : DoorBuilderModal — bouton « Ajouter et continuer » (empile la porte + réinitialise pour choisir un autre modèle, compteur ✓ N porte(s)) + « Ajouter et terminer » (ajoute + ferme ; « Terminer » sans modèle = ferme). Vérifié e2e : 2 modèles différents (AT1000 simple 832,15 + paire 1377,74) empilés en 2 lignes.
  * EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (Suivi des dépôts + Reçu de dépôt PDF + Dépôt sur soumission) : FAIT + TESTÉ (backend curl + frontend e2e).
  * SUIVI DES DÉPÔTS : nouvel onglet « Suivi des dépôts » (slug suivi-depots, DepositsPanel.jsx). Backend GET /admin/invoices/deposits → factures deposit_received=true (hors annulée), colonnes total/dépôt reçu (montant+%)/solde restant (0 si payée)/statut + totaux (total_deposit, total_remaining). Route littérale placée AVANT /invoices/{id} (anti-shadowing). Vérifié : FAC 40 % de 1149,75 → dépôt 459,90 / solde 689,85.
  * REÇU DE DÉPÔT PDF : render_deposit_receipt_pdf (erp_pdf.py) — brandé, « REÇU DE DÉPÔT », facture liée, Total → Dépôt reçu (X %) → SOLDE RESTANT À PAYER. Endpoint GET /admin/invoices/{id}/deposit-receipt.pdf (token, inline, 400 si pas de dépôt). Bouton dans DepositsPanel. Vérifié : 200, contient REÇU DE DÉPÔT + SOLDE RESTANT.
  * DÉPÔT SUR SOUMISSION : Quote/QuoteIn + show_deposit(bool)/deposit_pct(défaut 50). render_quote_pdf ajoute après les totaux un encadré « Dépôt à verser à l'acceptation (X %) : montant » + « Solde payable à la livraison ». DocumentForm (soumission) : case « Afficher le dépôt à verser à l'acceptation » + champ % + aperçu en direct dans l'encadré totaux. create/update_quote persistent les champs. Vérifié : PDF contient « verser » + « livraison » ; aperçu UI présent.
  * EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (Reçu par courriel + Facturer le solde + Alerte solde) : FAIT + TESTÉ (backend curl + frontend e2e).
  * REÇU PAR COURRIEL : POST /admin/invoices/{id}/deposit-receipt/send {to_email?} — défaut = courriel du client (customer_snapshot.email), sinon prompt côté UI. send_pdf_email (PDF reçu joint, HTML confirmant dépôt + solde). Bouton courriel (icône Mail) par ligne dans DepositsPanel. Vérifié : sent→client@test.com.
  * FACTURER LE SOLDE (option SANS taxes, aucun risque de double taxe) : POST /admin/invoices/{id}/bill-balance — crée une NOUVELLE facture NON taxable (taxable=false, tps=tvq=0), 1 ligne « Solde final — réf. FAC-XXXX (après dépôt de Y %, taxes déjà facturées) » au montant du solde ; la facture d'origine passe à « payée ». Refuse si pas de dépôt / déjà payée / solde ≤ 0. Bouton « Facturer le solde » (si remaining>0) avec confirm. Vérifié : solde 689,85 non taxable, original→payée.
  * ALERTE SOLDE (Adjointe) : STALE_DEPOSIT_DAYS=30. _stale_deposit_balances(db,30) = factures deposit_received, statut ∉ payée/annulée, date +30 j, solde>0. Ajouté (1) au briefing quotidien courriel + preview (_deposit_alert_html, section « 💰 Soldes de dépôt à encaisser (+30 j) »), (2) au push matinal (run_morning_push : « N solde(s) de dépôt à encaisser »), (3) au contexte de l'Adjointe (erp_routes_assistant : « DÉPÔTS reçus avec solde à encaisser »). Vérifié : briefing preview liste le dépôt vieux de +30 j.
  * EN PREVIEW — redéployer pour portech.info.

- MAJ 2026-06 (Dépôts attendus) : FAIT + TESTÉ. /admin/invoices/deposits renvoie aussi `awaited` + `total_awaited` = soumissions status="acceptée", show_deposit=true, deposit_pct>0, pas encore reçu (converted_invoice_id absent OU facture liée sans deposit_received). Chaque ligne : expected_deposit = total×pct/100, converted (bool). DepositsPanel : 3e tuile « Dépôts attendus » + section tableau (SO-XXXX, client, total, dépôt attendu, état « À convertir en facture » / « Facture créée · dépôt à saisir »). Vérifié : SO acceptée 4599 $ → attendu 2299,50 $ (50 %).

- MAJ 2026-06 (Job depuis Facture + Menu condensé par catégories) : FAIT + TESTÉ (backend curl + frontend e2e).
  * JOB DEPUIS FACTURE : POST /admin/jobs/from-invoice/{id} (erp_routes_jobs) — mirroir de from-quote, idempotent (renvoie job existante si déjà liée). Étape auto : payée→paye, deposit_received→depot_recu, sinon→facture. source="invoice", lien FAC-XXXX, deposit_expected=deposit_amount ou total×0.5. Frontend JobsPanel : bouton « Depuis une facture » (jobs-from-invoice-btn) + sélecteur (jobs-invoice-picker) à côté de « Depuis une soumission ». Vérifié : JOB créée stage facture, idempotent.
  * MENU CONDENSÉ (AdminErp.jsx) : nav secondaire regroupée. Liens directs : Tableau de bord, Suivi des jobs, Assistante IA. Groupes déroulants (GroupedNav + ChevronDown, fermeture au clic extérieur) : Ventes (soumissions, factures, suivi-depots, etats-de-compte, avis-paiement), Comptabilité (depenses, recap-taxes, kilometrage), Fabrication (fabrication, inventaire-alu, commandes-at, bons-commande, connaissements), Produits & prix (produits, catalogue-quincaillerie, couts-master), Contacts (clients, fournisseurs, prospection), Outils (calendrier, rapports, courriel). TAB_MAP conserve slug/label/panel. Conteneur passé de overflow-x-auto à flex-wrap pour que les dropdowns s'affichent. data-testid conservés (erp-tab-*) + erp-group-{label}. Vérifié e2e : dropdowns s'ouvrent, item actif surligné.

- MAJ 2026-06 (Dessin de production de porte 2.0 — intégration Master, style Logikal) : FAIT + TESTÉ (frontend e2e + backend curl).
  * Décisions user : remplacer l'ancien outil, partir d'un modèle Master LDP (série auto-détectée), catalogue Master prioritaire, afficher coûtant+marge+vendant à l'écran (jamais PDF) + bouton pousser vers soumission, garder l'élévation auto (pas de liste coupe/BOM/CNC pour l'instant). Verre = ouverture de moulure − 7 mm (3,5/côté) [NON encore implémenté — voir plus bas].
  * Renommé partout « Dessins de production » → « Dessin de production de porte » (sous-onglet FabricationPanel + titre panneau).
  * Backend (erp_routes_production_plans) : HardwareLine + cost/included/from_master ; DoorPlan + master_model_key/material_cost/labor_hours/profit_pct. buildPayload filtre la quincaillerie décochée (included=false) → jamais sur le PDF ni dans le coût.
  * Frontend (ProductionPlansPanel.jsx) : charge /admin/master/door-models + params (taux 50, markup quinc. 0.35). Sélecteur « Modèle Master (LDP) » par porte → applyMasterModel : série auto (AT1000/ATi1000/AT2000/ATi2000 depuis le label), config (paire/simple), fini (clair/noir), material_cost/labor_hours/profit_pct, et quincaillerie par défaut en lignes COCHÉES (case Inclus). Recherche Master /admin/master/hardware pour ajouter. Colonnes table : Inclus / Qté / Desc / N° pièce / Coût (interne) / Prix U. / Actif / Inact. Décocher = retiré du coûtant + du PDF.
  * doorCost() + projectTotals (useMemo) : (material+heures×taux)×(1+profit) + quinc.×(1+0.35). Bandeau projet foncé « INTERNE · jamais sur le PDF » : coûtant / marge $/% / vendant. Mini-panneau coût par porte. Formules identiques au calculateur de soumission.
  * Bouton « Pousser vers soumission » (pp-push-quote) : POST /admin/quotes, 1 ligne/porte (unit_price=vendant, cost_price=coûtant caché, cost_category Portes), client = infos du dessin. Vérifié : décocher 1 quinc. → coûtant 555,54→486,54 ; push → SO créée vendant 739 $, cost_price 486,54 caché, PDF sans coût.
  * ⚠️ RESTE À FAIRE : formule verre = ouverture de moulure − 7 mm. Le backend erp_pdf_production a déjà un calcul verre « bible A.T. » (_glass_moulure) ; à confirmer avec le user avant de l'écraser pour éviter une régression.

- MAJ 2026-06 (Fix installation PWA iPhone — 2 apps distinctes) : FAIT + TESTÉ.
  * Problème : un seul manifest (name "Adjointe Portech", start_url /adjointe) + apple-mobile-web-app-title "Adjointe Portech" → toute installation « Ajouter à l'écran d'accueil » installait l'Adjointe, peu importe la page.
  * Fix : manifest.json renommé « Portech » (start_url /admin) ; nouveau public/manifest-adjointe.json (« Adjointe Portech », start_url /adjointe). Composant src/components/PwaManifest.jsx (monté dans App.js) bascule <link rel=manifest> + meta apple-mobile-web-app-title selon la route (/adjointe → Adjointe, sinon → Portech). index.html apple title défaut = Portech.
  * Vérifié e2e : /admin → /manifest.json + « Portech » ; /adjointe → /manifest-adjointe.json + « Adjointe Portech » ; les 2 JSON servis valides (name/start_url corrects).
  * NB : nécessite un redéploiement pour portech.info. Sur iPhone, iOS peut garder l'ancien nom en cache : supprimer l'ancienne icône, fermer Safari, recharger la page voulue, puis Ajouter à l'écran d'accueil.

- MAJ 2026-06 (Dessin de production de porte — corrections lot 1) : FAIT + TESTÉ.
  Règles user : marge = MAJORATION sur coûtant (vendant = coût × (1+%)), quinc. marge par ligne modifiable, tout affiché en % (pas ×1.x). Verre→moulure : 6mm→AT1045, thermos/isolé→AT1050. Épaisseur : ATi=2-1/4"+cladding alu intérieur, AT=1-3/4". Cadres 4 types (flush_iso, flush_non_iso, tube_fin, adapteur) = ligne séparée, coût/heures modifiables (0 défaut).
  * Backend : HardwareLine + margin_pct(35) ; DoorPlan + thickness/cladding/moulure/frame_type/frame_cost/frame_hours.
  * Frontend ProductionPlansPanel : marge matériel affichée en % (profit_pct×100) ; colonne « Marge % » par ligne quincaillerie (unit_price = coût×(1+marge%) auto-recalculé) ; applyMasterModel règle épaisseur+cladding (isIso = série ATi OU label isolé SAUF "non-isol"), moulure, quinc. à 35 % ; sélecteur vitrage → moulure auto (AT1045/AT1050) ; sélecteurs Épaisseur/Cladding/Moulure/Cadre(+coût/heures). doorCost inclut cadre + quinc. par ligne. Push vers soumission = ligne porte + LIGNE CADRE séparée (cost_category "Cadres").
  * BUG CORRIGÉ : prix du menu déroulant catalogue ne s'arrachait pas → onHwDescription tire maintenant part_number+coût+prix (prix = match.price sinon coût×(1+marge%)).
  * PDF (erp_pdf_production) : poignées grossies (grip 4pt, offset 8, plots 2.4/cercles 2.6) ; verrous affleurés TOUJOURS sur vantail inactif (impossible sur actif) ; protège-pêne dessiné APRÈS l'astragale (premier plan) et à 75 %. PDF vérifié 5 pages valides.
  * ⚠️ RESTE À FAIRE (lot 2) : dessiner le CADRE autour de la porte sur l'élévation (gauche/droite/haut ; bas = seuil). Nécessite largeur de profilé de cadre + travail sur les coordonnées de l'élévation. Non fait ce tour.


## 2026-10-05 — Refonte cartouche pages de détail (style Maupas)
- Pages Plan (300/301), Coupe (400/401) et Ancrage (500) refaites dans erp_pdf_production.py pour correspondre au PDF de référence Maupas.
- Nouveau cartouche vertical ancré à la marge droite: en-tête PORTECH navy + CLIENT/DATE/STATUT(POUR PRODUCTION)/PROJET/# PROJET/DESCRIPTION/REPÈRE(tag porte) + bande PAGE (gros numéro).
- Bandeau rouge "PRODUCTION · <date>" en haut à droite; cadre noir arrondi; ligne de pied de page descriptive.
- Dessin de détail décalé vers la gauche (bande droite réservée) => plus aucune superposition cartouche/dessin.
- Dessins de détail existants (AT1000, etc.) conservés tels quels.
- Vérifié par rendu PDF (plan réel, pages 300/400/500).

## 2026-10-05 — Export PDF anonyme (sous-traitance)
- Nouveau champ plan "anonymous" (ProductionPlanIn) + case à cocher "Version anonyme" dans ProductionPlansPanel (buildPayload + emptyProductionPlan).
- render_production_plan_pdf respecte plan["anonymous"]: retire logo/nom PORTECH + coordonnées sur couverture, bandeau haut/bas, cartouche (en-tête masqué, infos client conservées), ligne usinage/installation (INSTALLATION: —) et titre PDF.
- Dessins, cotes et mentions fournisseur (A.T. Fabrication) conservés. Vérifié par rendu PDF (couverture, élévation, détails, ancrage).

## 2026-10-05 — Note "Miroité et renversé" (portes MG, vue en plan)
- Pour les portes main gauche (MG/MGR), le dessin de reference reste en MD; une note encadree rouge "Miroite et renverse" est posee sur le dessin, centree juste au-dessus du detail.
- Uniquement sur la vue en plan (page 300), jamais sur la coupe (400) ni sur les portes MD. Verifie par rendu PDF.

## 2026-10-05 — Note "Miroite et renverse" : regle mise a jour
- La note sapplique desormais aux portes MD ET MG (pas MDR/MGR), toutes series (AT1000/AT2000), vue en plan (300) uniquement.
- Condition: kind==plan and handing in (MD, MG). Verifie par rendu AT2000 MD.

## 2026-10-05 — Dessins 11x17, pleine largeur, cartouche remplace celui du dessin
- PDF production passe en 11x17 (landscape TABLOID, 1224x792) dans erp_pdf_production.py (W,H + canvas).
- Pagination detail corrigee: code = 300/400 + (page_no-1) => 300,301 / 400,401.
- Pages detail (plan/coupe): dessin embed pleine page (24,26,W-24,H-20); _mask_ref_titleblock masque le bloc projet bas-droite + bloc SERIES haut-droite, redessine un cadre complet et renvoie la box ou notre cartouche est dessine (remplace celui du dessin). Bandeau rouge place sur zone SERIES masquee.
- _draw_cartouche accepte box=(bx,by,cw,ch) et sadapte pour remplir la zone.
- Elevation: largeur zone dessin = W*0.56, colonne droite recalculee; note VUE INTERIEUR (pastille) sur portes MD/MG seulement.
- Page ancrage 500: mise en page simple (reserve bande droite + cartouche par defaut), pas de masque.
- Verifie par rendu (AT2000 pair MDR, AT1000 simple MD, coupe, ancrage).

## 2026-10-05 — Nouvelle banque de dessins (plans/coupes) + marge ancrage
- Importe la banque REV-04-2026 (Plans 12 pages, Coupes 6 pages) et regenere les 18 PNG de /assets/production_details/ref (recadres sur le cadre, 3138x1966). AT1000 utilise desormais le meme gabarit KOVO que AT2000 (cadre + cartouches integres).
- Mapping: plans p1-12 -> plan_{at1000,ati1000,at2000,ati2000}_{simple,pair}_{6,25}; coupes p1-6 -> coupe_{...}_{6,25}.
- _mask_ref_titleblock recale sur le nouveau gabarit (bloc projet bas-droite + bloc series haut-droite masques, cadre redessine au bord).
- Page ancrage 500: bande droite elargie (embed (28,56,W-250,H-64)) => le cartouche ne couvre plus le dessin.
- Verifie par rendu (AT1000 simple MD 300, AT1000 paire MG 301, coupe 400, ancrage 500).

## 2026-10-06 — Dessins de plan par main (MD/MG/MDR/MGR) pour portes simples
- Banque Cedrick (24 pages) importee: plan_{at1000,ati1000,at2000,ati2000}_simple_{6,25}_{md,mg,mdr,mgr}.png (recadres).
- _resolve_detail_image (plan simple) essaie dabord le fichier specifique a la main, puis fallback.
- _mask_ref_titleblock(style): style=simple (un seul bloc bas-droite, garde le titre haut) pour ces dessins; style=kovo (2 blocs) pour lancienne banque. Cadre pleine largeur redessine.
- Note Miroite et renverse supprimee quand un dessin specifique a la main est utilise (le dessin est deja oriente correctement). Conservee en fallback pour MD/MG.
- Bandeau rouge PRODUCTION place en haut-droite (zone libre) pour le style simple.
- Verifie: AT1000 MD/MG, AT2000 MDR/MGR (plans 300-303), coupe 400, ancrage 500.

## 2026-10-06 — Coupes foncees + couverture complete de lancien cartouche
- Les 6 PNG coupe_*.png assombris/epaissis (gamma 2.1, white cut 243, MinFilter 3) pour des traits bien visibles.
- _mask_ref_titleblock style=simple: masque etendu vers le haut (h 0.560) pour couvrir aussi la petite case Par dautres au-dessus du cartouche => plus de reste visible.
- Verifie: coupe 400 (traits fonces), plans simples MD/MGR (cartouche couvre tout).

## 2026-10-07 — Quincaillerie (retour ligne + reorder) + Connaissement (facture/client) + dessins fonces
- _hardware_table (erp_pdf_production): description renvoyee a la ligne (wrap jusqu a 4 lignes) au lieu detre coupee a 48 car.; hauteur de ligne dynamique.
- ProductionPlansPanel: boutons Monter/Descendre (ChevronUp/Down, moveHw) sur chaque ligne de quincaillerie.
- BolPanel: select Creer depuis une facture (pre-remplit destinataire + articles depuis la facture) et select Destinataire depuis la base de clients (parties kind=customer). Charge /admin/invoices.
- Dessins de plan AT1000/AT2000 assombris (gamma 2.1 + MinFilter); portes doubles (pair) epaissies davantage (MinFilter x2 + contraste). Coupes aussi assombries precedemment.
- Verifie: rendu PDF (quincaillerie longue desc, plans/coupes fonces) + screenshots UI (BOL prefill, reorder).

## 2026-06 — Site public : offre "Portes commerciales en aluminium"
- Nouvelle page publique /portes-aluminium (PortesAluminium.jsx) : hero, intro/valeur, 5 gammes (AT1000, AT2000, isolées/bris thermique, simples & doubles, sur mesure), avantages, configurations & finis (mains MD/MG/MDR/MGR, vitrage simple/thermos, finis), galerie, note "prête à poser", CTA soumission.
- Soumission sur demande uniquement — AUCUN prix affiché. Tous les CTA pointent vers /contact.
- Route ajoutée dans App.js. Lien nav desktop+mobile (nav-link-aluminium) et footer (footer-link-aluminium).
- Nouvelle section accueil HomeAluminium.jsx (après HomeShowcase) avec CTA vers /portes-aluminium.
- Visuels IA (Gemini Nano Banana) dans /app/frontend/public/generated/aluminium/ : alu-hero, alu-at1000, alu-at2000, alu-isolee, alu-double, alu-surmesure, alu-finis, alu-gal1, alu-gal2, alu-cta. 3 images (at1000, isolee, finis) régénérées en style photo réaliste après retour utilisateur sur défauts.
- SEO: titre/description/canonical sur la nouvelle page.
- Testé: testing_agent iteration_19 — 7 flux PASS (desktop+mobile), frontend 100%, aucun prix, toutes images 200.
