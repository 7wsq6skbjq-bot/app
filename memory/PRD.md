# Portech — PRD

## Problem statement (verbatim, itération initiale)
> "Je veux créé un site pour mon entreprise. Portech est une entreprise spécialisée dans l'installation de quincaillerie pour portes commerciales..."

## Itération 2 — mise à jour (user input verbatim)
> "Je veux que tu retire le fond blanc de mon Logo, assure toi qu'il est bien grand, gros et visible sur le site. Mon courriel pro est: portech.infos@gmail.com. je déserrverai tout le grand montréal. attention, je n'installe pas des portes, je ne fait qu'installer la quincailerie. Utilse les ton de bleu marine comme mon logo. Resend. Auth admin + dashboard. Plus d'images."

## Itération 3 — ajustements
> "Hero: 'Votre expert en quincaillerie de portes commerciales.' Admin login: plus de blanc/contraste, mélanger les tons."

## Architecture
- **Backend** : FastAPI + motor (MongoDB). Routes préfixées `/api`.
  - Public : `GET /` (health), `POST /contact`, `GET/POST /status`
  - Auth : `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
  - Admin (JWT requis) : `GET /admin/submissions`, `GET /admin/stats`, `DELETE /admin/submissions/{id}`
  - Intégrations : **Resend** (notification email leads) + **Nano Banana** (génération images hors-runtime)
- **Frontend** : React 19 + React Router 7 + Tailwind + lucide-react.
  - Public : Home, Services, About, Contact (Layout wrapper)
  - Admin : `/admin/login` + `/admin` (hors Layout, ProtectedRoute)
  - AuthContext avec localStorage token fallback (cross-origin)
- **MongoDB** : `contact_submissions`, `admin_users`, `status_checks`

## User personas
- Gestionnaires d'immeubles / syndics (tours à condos)
- Directeurs de commerce, restaurant, épicerie, boulangerie
- Directeurs d'écoles / institutions
- Entrepreneurs généraux cherchant un sous-traitant quincaillerie

## Core requirements
- Site lead-gen avec CTA "Demander une soumission" répétés
- Clarifier : Portech = **quincaillerie uniquement** (pas installation de portes — c'est le vitrier)
- 4 pages SEO + formulaire contact + dashboard admin
- Palette **bleu marine** cohérente avec le logo
- Service : **Grand Montréal**

## What's been implemented

### 2026-01 — MVP (iter 1)
- 4 pages publiques, formulaire contact, design industriel monochrome + bleu
- Backend + MongoDB, 100% tests réussis

### 2026-01 — Iter 2
- **Logo Portech** avec fond transparent (PNG, +version blanche pour fonds sombres), affiché grand dans le nav et le footer
- **Copywriting repositionné** — accent sur "quincaillerie" partout ; nouvelle section "Notre périmètre" sur la page Services qui clarifie que Portech ne pose pas les portes elles-mêmes (vitrier)
- **Palette bleu marine** (10 teintes navy #0c182b → #f3f6fb) remplace le monochrome + accent bleu
- **Coordonnées** : `portech.infos@gmail.com` + `Grand Montréal` dans footer, page Contact, métadonnées
- **Resend** intégré — chaque soumission du formulaire envoie un email HTML formaté à `portech.infos@gmail.com` (sender `onboarding@resend.dev`, reply-to = email du lead). Fallback : si Resend échoue, la soumission est quand même sauvée.
- **Auth JWT admin** : bcrypt + JWT (HS256, 8h), seed au startup depuis env, cookie httpOnly + bearer fallback
- **Dashboard admin** (`/admin`) : stats (total, 30j, emails envoyés), tableau recherchable, détail en drawer avec bouton Répondre (mailto préformaté) + Supprimer
- **14 images générées** via Gemini Nano Banana (barres antipaniques, ferme-portes, serrures, techniciens, avant/après, corridor école, lobby condo, etc.) — servies depuis `/public/generated/`
- **Tests** : backend 100% (20/20 pytest), frontend 100%, Resend live confirmé

### 2026-01 — Iter 3
- Hero title → "Votre expert en quincaillerie de portes commerciales."
- Page admin login redesignée en split 42/58 (panneau bleu branding + panneau blanc form) — beaucoup plus de contraste

### 2026-04 — Iter 4 (Restauration + ajouts)
- **Restauration complète** du projet depuis ZIP utilisateur (suite à fermeture accidentelle de session)
- **Photo réelle du fondateur** intégrée dans la page À propos (`/uploads/founder.png`) — remplace l'image IA. Photo professionnelle, polo Portech, fond branding noir.
- **Photo réelle de chantier** (porte vitrée pivot haut de gamme + quincaillerie partiellement installée) ajoutée au showcase Home (`/uploads/glass-door-hardware.jpg`) — remplace l'image IA "Mesure · Ajustement". Label "Chantier réel · Haut de gamme".
- **4ᵉ témoignage client** (restaurant gastronomique Vieux-Montréal) ajouté — positionnement haut de gamme, portes pivots sur mesure très chères, met en valeur que Portech accepte les projets que les autres refusent par peur de mal faire. Grille testimonials passe à 4 colonnes.
- **Service 05 — Consultation pour vitreries** : nouveau bloc service complet (Home + page Services). Portech agit comme consultant auprès des vitriers pour le choix et l'achat de la quincaillerie (compatibilité, codes, fournisseurs).
- **Service 06 — Inspection & rapport d'expertise** : nouveau bloc service complet (Home + page Services). Inspection post-installation des sous-traitants en quincaillerie pour les entrepreneurs généraux, avec rapport écrit (photos, observations, liste de correctifs).
- Chips header Services mis à jour (ajout "Consultation vitreries" + "Inspection & expertise")
- Backend, MongoDB, JWT auth, dashboard admin → tous opérationnels après restauration

### 2026-04 — Iter 5 (Légal + form + visuels + branding)
- **Resend configuré** (clé live `re_dhhg7MKi_...`) — emails de leads arrivent maintenant à `portech.infos@gmail.com` (`email_sent: true` confirmé en test)
- **Page `/mentions-legales`** créée (`Legal.jsx`) — Mentions légales (éditeur, hébergement, propriété intellectuelle, marques déposées, limitation de responsabilité) + Politique de confidentialité conforme **Loi 25 du Québec** (collecte, usage, sous-traitants, durée, droits de l'utilisateur, cookies). Lien dans le footer.
- **Formulaire contact étendu** — ajout `Entreprise` (facultatif) + `Lieu des travaux` (obligatoire). Backend : `ContactSubmissionCreate` strict, `ContactSubmission` (réponse) tolérant aux anciennes soumissions sans `work_location`. Email Resend mis à jour.
- **Marquee "secteurs" enrichi** : ajout Cinémas, Banques, Dépanneurs.
- **Mur de marques** (12 marques de quincaillerie) : Adams Rite, Von Duprin, Sargent, LCN, Schlage, Yale, Norton, dormakaba, Corbin Russwin, Best, Hager, Stanley — typographies variées (italic, condensed, wide, block) pour donner l'impression d'un wall of brands sans utiliser de logos copyrightés.
- **Image `heritage-torch.png`** générée via Gemini Nano Banana — main expérimentée transmettant la quincaillerie à une main plus jeune au-dessus d'un établi sombre. Symbolise le passage du flambeau du mentor à Cédrick. Affichée au chapitre 05 dans À propos.
- **Image `panic-bar.png`** régénérée — barre antipanique stock-photo réaliste (sans défauts) sur porte de couloir d'hôpital.
- **Image `workshop-tools.png`** régénérée — étagère industrielle remplie de boîtes de quincaillerie alignées (replace flatlay précédent peu lisible).
- **Nom "Cédrick Pimparé"** affiché dans un bel encart en bas de la photo du fondateur (page À propos).
- **Photos Service 05 ↔ 06 inversées** : 05 (Consultation) montre maintenant la grille de catalogue, 06 (Inspection) montre la vraie photo de chantier en cours d'installation.
- **Titre périmètre Services** : "LA QUINCAILLERIE — C'EST TOUT CE QU'ON FAIT" (renforcé).
- **Tests** : 23/23 pytest backend, frontend 100% via testing agent.

### 2026-04 — Iter 13 (Système de gestion interne + retouches contenu)
**Retouches contenu**
- Home · Problems : « inspections qui tombent à plat » → « inspections échouées »
- Home · Fiche technique : « 10+ ans terrain » → « 10 ans en atelier »
- Home · Benefits : « Plus de 10 ans sur le chantier » → « Plus de 10 ans en atelier »
- Home · Testimonials : section « Retours terrain » → « Retours atelier » + **tous les noms d'auteurs retirés** (garde poste + lieu)
- About : « Sur le terrain, pas dans les livres » → « En atelier, pas dans les livres » (+ textes connexes mis à jour)
- Footer : « service sur le terrain » → « service en atelier »
- Services : retiré « Ouvertures pour fenêtres, grilles, hublots, passe-plats »
- Conservée telle quelle (requête explicite) : « Parce qu'une quincaillerie bien posée… sur chaque chantier, sans exception. »

**Catalogue doublé** : passé de 3 → **6 fiches par catégorie** = **36 fiches** au total. Nouvelles sélections extraites des PDF (handle-4 à handle-6, lock-4 à lock-6, etc.).

**Nouveau module ERP dans le portail admin** (`/admin/gestion/*`)
- **Backend** (`/app/backend/erp.py`) : 6 collections MongoDB (erp_parties, erp_products, erp_invoices, erp_purchase_orders, erp_bills_of_lading, counters) + 23 endpoints CRUD auth-protégés.
- **Frontend** : navigation à 6 onglets — Clients / Fournisseurs / Produits / Factures / Bons de commande / Connaissements.
  - Base de données réutilisable clients + fournisseurs (option B).
  - Catalogue interne produits/services avec prix (option B) — auto-complétion sur les lignes de facture/BC.
  - Numérotation séquentielle continue : `FAC-0001`, `BC-0001`, `CONN-0001` (option B).
  - Taxes Québec auto-calculées : TPS 5 % + TVQ 9,975 % avec case « exonéré » (option A).
- **Impression PDF** : pages dédiées `/admin/imprimer/{facture|bon-commande|connaissement}/:id` avec CSS `@media print` → l'utilisateur clique sur l'imprimante → navigateur → « Enregistrer en PDF ». Logo Portech, coordonnées, mentions Net 30, zones signature sur connaissement.
- **Intégration AdminHeader** : bouton « Gestion » visible depuis le dashboard principal.
- **Testé bout-en-bout** : création client → produit → facture (FAC-0001, sous-total 2 598 $ + TPS 129,90 $ + TVQ 259,15 $ = 2 987,05 $) → impression PDF OK.

### 2026-04 — Iter 12 (Refactoring + SEO + CORS)
- **Home.jsx refactorisé** : 796 → 46 lignes (94 % de réduction). Architecture :
  - `/pages/home/data.js` — toutes les données (IMG, problems, services, benefits, sectors, brands, testimonials, showcaseTiles, clientTypes)
  - `/pages/home/sections/` — 9 composants section : HomeHero, HomeSectors, HomeShowcase, HomeBrandsWall, HomeProblems, HomeSolution, HomeServices, HomeClients, HomeWhy, HomeTestimonials
- **AdminDashboard.jsx refactorisé** : 409 → 115 lignes (72 % de réduction). Composants extraits :
  - `/pages/admin/AdminHeader.jsx` (header + logout)
  - `/pages/admin/AdminStats.jsx` (3 KPI tiles)
  - `/pages/admin/AdminControls.jsx` (search + refresh)
  - `/pages/admin/AdminTable.jsx` (table + empty state)
  - `/pages/admin/AdminDrawer.jsx` (detail drawer + reply/delete)
  - `/pages/admin/utils.js` (formatDate)
- **SEO meta tags** : nouveau hook `useSeo({ title, description })` dans `/hooks/use-seo.js` (sans dépendance externe, met à jour `document.title`, `meta[name=description]`, `og:title`, `og:description`, `link rel=canonical`). Appliqué sur Home, Services, About, Contact, Legal, Galerie (5 sous-pages avec descriptions locales Grand Montréal), Catalogue.
- **CORS restreint** : `CORS_ORIGINS` passé de `*` à `https://portech.info,https://www.portech.info,https://dev-retrieval.preview.emergentagent.com`. Vérifié : origin malveillant retourne 400, portech.info accepté avec `access-control-allow-origin` correct. Backend redémarré.
- **Vérifié** : Home charge sans erreur, Admin login → dashboard fonctionne (12 leads affichés, search/stats/drawer OK), POST /api/contact toujours 201 + Resend OK.

### 2026-04 — Iter 11 (Capture de leads sur téléchargement PDF)
- **Modal de capture** : au clic sur « Télécharger la fiche PDF », le PDF se télécharge ET une modale apparaît immédiatement avec :
  - Bandeau « Téléchargement démarré · [Catégorie] »
  - Titre « Vous étudiez un projet ? »
  - Description contextuelle mentionnant la catégorie + délai « 24 h »
  - CTA principal « Demander une soumission » → `/contact?categorie=...`
  - Bouton secondaire « Plus tard »
  - Backdrop navy floutée, fermeture par Esc / X / clic backdrop / dismiss
- **Pré-remplissage Contact** : `Contact.jsx` lit `?categorie=...` et pré-remplit le champ message : « Bonjour, je viens de télécharger votre fiche « X » et j'aimerais discuter d'un projet. ».
- Vérifié bout-en-bout : modal s'affiche, CTA ouvre `/contact` avec query param URL-encoded, message du formulaire pré-rempli automatiquement.

### 2026-04 — Iter 10 (Catalogue complet 6/6 + téléchargement PDF)
- **5 nouveaux PDF parsés** : Hager Commercial Hinges, Sargent Specialty, Dormakaba Commercial / Full, Von Duprin Electrical Security.
- **Catalogue 100 % complet** :
  - Charnières & pivots → **Hager Commercial Hinges** (cover, Specialty Hinges, Full Mortise Concealed Electric)
  - Contrôle d'accès → **Von Duprin Electrical Security** (cover électrifié, 5100 Series electric strikes, 6400 Series modular) — remplace l'ancienne FM6100.
- **Bouton « Télécharger la fiche PDF »** sur chaque onglet : 6/6 catégories pointent vers le PDF officiel correspondant servi depuis `/catalogue/pdf/` (Sargent Studio 45 MB, Degree Key 5 MB, 5300 Alarmed Exit 2 MB, 2300/2409 Fire Guard 4 MB, Von Duprin Electrical 7 MB, Hager Hinges 1 MB).
- 18 fiches catalogue extraites (au lieu de 15), placeholder « En construction » supprimé.

### 2026-04 — Iter 9 (Catalogue produit avec vraies photos SARGENT)
- **5 PDF SARGENT/ASSA ABLOY reçus de l'utilisateur**, parsés et photos extraites :
  - AADSS1004765 → Studio Collection (poignées & leviers)
  - AADSS1004587 → Degree Key System (serrures & cylindres)
  - AADSS1086801 → 5300 Series Alarmed Exit Device (barres antipaniques)
  - AADSS1257255 → 2300/2409 Fire Guard (ferme-portes)
  - AADSS1052882 → FM6100 Multi-Point (contrôle d'accès / multi-points)
- **15 fiches catalogue** générées (pages PDF rendues à 200 dpi puis croppées) dans `/public/catalogue/`.
- **Catalogue.jsx** refondu : object-contain (au lieu d'object-cover) pour respecter les fiches produit ; sous-titres en anglais avec mention de la marque.
- **Charnières & pivots** : tuile « Catalogue · En construction · Demander une pièce » (PDF Hager/Stanley pas encore reçu).
- Suppression des 18 photos AI catalogue précédentes (`cat-*.png`) et du dossier `/public/_catprev/`.
- Script : `/app/scripts/crop_catalogue.py`.

### 2026-04 — Iter 8 (Marquage Portech, outils DeWalt, signalétique FR, logos marques)
- **15 images régénérées** (gal-interv 1-4, gal-chantier-2, gal-exit 1, 2, 4, gal-panic 1-4, gal-lock 1+3, services-installation/machining/repair) avec règles strictes :
  - Technicien en **chandail/polo/hoodie noir avec « PORTECH » en blanc** (gros au dos OU petit côté cœur)
  - **Outils DeWalt jaune et noir** uniquement (perceuses, visseuses)
  - Toute signalétique en **FRANÇAIS** (« SORTIE » au lieu de « EXIT »)
- **gal-chantier-2** entièrement remplacée : technicien Portech en hoodie noir agenouillé en lobby de tour à condo de luxe (marbre, mur navy).
- **Brand wall** : ajout des **logos officiels** (Schlage, Yale, dormakaba, Stanley, Best — Wikimedia) + **wordmarks AI** stylisés (Sargent, Hager, Von Duprin, LCN, Adams Rite, Corbin Russwin, Norton). 12/12 marques avec logo.
- **Texte « Pourquoi nous »** corrigé : « Chaque pièce **de** quincaillerie est bien ajustée ».
- **Catalogue : à reprendre** — les 18 photos produit AI ont été rejetées par l'utilisateur. Sites manufacturiers bloquent le scraping automatisé (403 Forbidden). En attente des PDF catalogues de l'utilisateur (Schlage, Sargent, Von Duprin, LCN, dormakaba, Hager, etc.).

### 2026-04 — Iter 7 (Banque d'images 100% commercial, zéro doublon)
- **61 images générées via Nano Banana** dans `/generated/portfolio/` — strictement portes commerciales en aluminium / acier (devantures, tours à bureaux, cinémas, écoles, pharmacies, hôpitaux). Zéro porte résidentielle.
- **Zéro doublon** : chaque image est utilisée à un seul endroit unique sur tout le site (Home, Services, Galerie, Catalogue).
- **Home** repensé : nouveau fond hero (devanture commerciale au crépuscule), 5 tuiles showcase uniques, 6 images de services distinctes, 4 photos clients (restaurant, école, condo, bureau).
- **Services** : nouveau hero + 6 images de blocs services uniques, différentes de celles du Home.
- **Galerie** (5 catégories × 4 photos = 20) : interventions, chantiers haut de gamme, dispositifs de sortie, barres antipaniques, serrures — toutes en contexte commercial.
- **Catalogue** (6 catégories × 3 photos = 18) : poignées, serrures, barres antipaniques, ferme-portes, contrôle d'accès, charnières — produit studio sur fond bleu marine.
- **Script** : `/app/scripts/generate_portfolio_images.py` (idempotent, skip si déjà existant).

### 2026-04 — Iter 6 (Polissage témoignages + textes À propos)
- **Section Avant/Après supprimée** — photos pas réalistes ; section retirée du Home.
- **Témoignages passés de 4 → 6** (grille 3×2). Nouveaux ajouts :
  - Tour à condos · 30 étages · Rue Peel, Montréal (positionnement haut de gamme)
  - Complexe cinématographique · Rive-Sud (ancre le secteur Cinémas)
- **Titre header À propos** : "10 ans de chantier" → "10 ans en atelier" (positionnement plus précis).
- **Chapitre 03 Story À propos** retitré : "J'ai commencé comme tous ceux qui apprennent pour vrai : en bas de l'échelle. Couper des matériaux. Observer. Comprendre." (déplacé du chapitre 02).
- **Phrase finale chapitre 05** : "C'est ainsi qu'est née Portech." → "C'est ainsi que naît Portech." (présent narratif, plus vivant).
- **Vision À propos** mis à jour : public élargi → "directeurs d'entreprise, propriétaires de commerce et monsieur-madame tout le monde" (avant : "directeurs d'école").
- **Pourquoi nous** : "Chaque quincaillerie est bien ajustée" → "Chaque pièce quincaillerie est bien ajustée".
- **CTA "Faisons connaissance"** À propos : "Donnez à vos portes le travail qu'elles méritent." → "Donnez à vos portes l'amour qu'elles méritent."

### 2026-04 — Iter 22 (Fix DÉFINITIF login — portech.info prod)
**Diagnostic approfondi sur portech.info** (pas seulement preview) :
- Frontend déployé à `https://portech.info`
- Backend déployé à `https://dev-retrieval.emergent.host/api` (**cross-origin**)
- **BUG CRITIQUE CORS** : le backend production renvoie simultanément :
  - `Access-Control-Allow-Origin: *`
  - `Access-Control-Allow-Credentials: true`
- **Cette combinaison est interdite par la spec CORS** → tous les navigateurs modernes rejettent la réponse de façon intermittente (dépend du cache / état CDN / round robin) → **login échoue aléatoirement**.

**Fix définitif** : retrait de `withCredentials: true` dans `AuthContext.jsx`. Comme on utilise déjà `Authorization: Bearer <token>` depuis `sessionStorage` (iter 21), on n'a plus besoin du cookie. Avec `withCredentials: false`, le `*` wildcard devient légal et le navigateur accepte la réponse systématiquement.

**Validation** : 10/10 logins rapides consécutifs en preview. 72/72 pytest backend passent. L'utilisateur doit redéployer pour que le fix prenne effet en prod.

### 2026-04 — Iter 21 (Fix login résiduel — Bearer fallback)
**Bug reporté à nouveau** : malgré le fix race condition de l'iter 20, l'utilisateur signalait encore des échecs de login occasionnels.

**Hypothèse nouvelle** : certains navigateurs (Safari ITP, mode privé strict, bloqueurs de cookies, antivirus qui filtrent les cookies tiers) **rejettent silencieusement le cookie `SameSite=None; Secure`**. Dans ce cas, `login()` retourne 200 + token dans le body, mais la requête suivante n'a aucun cookie → 401 → bounce-back.

**Fix définitif** — découplage cookie/auth :
- Le backend **renvoyait déjà** `access_token` dans le body de `/auth/login` et **acceptait déjà** un header `Authorization: Bearer …` en fallback (ligne 124-126 de `server.py`)
- `AuthContext.jsx` stocke maintenant le token dans **`sessionStorage`** (expire à la fermeture du tab, plus sûr que localStorage)
- Axios **intercepteur de requête** ajoute `Authorization: Bearer <token>` automatiquement sur tous les appels
- `logout()` clear le sessionStorage en plus du cookie

**Validation robuste** :
- 10/10 logins rapides consécutifs avec cookies + storage reset → 100 % succès
- **Test « cookie bloqué »** : login → effacement forcé des cookies → reload → reste connecté via Bearer ✅

Résultat : l'authentification est maintenant **indépendante des cookies**. Peu importe ce que fait le navigateur côté cookies, l'utilisateur reste authentifié tant que l'onglet est ouvert.

### 2026-04 — Iter 20 (Fix CRITIQUE race condition login)
**Bug signalé par l'utilisateur** : « les identifiants ne fonctionnent pas 4× sur 5, je dois cliquer 3-4 fois sur se connecter avant que ça marche ».

**Root cause identifiée** : race condition entre `fetchMe()` (auto-lancé au mount d'AuthProvider) et `login()` (déclenché par le clic). Quand l'utilisateur cliquait vite, `login()` finissait en premier (setUser = objet + redirect) mais `fetchMe()` — qui avait démarré avant et subissait un 401 parce que pas encore de cookie — écrasait avec `setUser(false)` → redirection back to login.

**Fix** : ajout d'un `sessionVersionRef` dans `AuthContext.jsx`. Incrémenté à chaque `login`/`logout`. `fetchMe()` capture la version au début et n'appelle `setUser` que si elle n'a pas changé. Empêche toute réponse en retard d'écraser une action plus récente.

**Validation** : 5 logins consécutifs avec cookies reset à chaque tour, 5/5 réussissent sans bounce-back (vs ~1/5 avant). 72/72 pytest passent.

### 2026-04 — Iter 19 (Calendrier admin interne)
**Module Calendrier complet** (`/admin/gestion/calendrier`) :
- Vue **mensuelle 6×7** avec navigation Préc / Aujourd'hui / Suiv
- Cellule jour cliquable → ouvre la création de RDV à cette date
- Jusqu'à 3 événements visibles par cellule, badge "+X autre(s)" sinon
- **Sidebar « Rendez-vous à venir »** (5 prochains, hors annulés) avec aperçu titre / date / client / lieu
- **Statuts** : prévu / fait / annulé (couleurs distinctes)
- **Champs RDV** : titre*, début* (datetime-local), fin (optionnel), client/contact (lié à la table parties), lieu/adresse, notes, statut
- **Backend** : `erp_routes_appointments.py` + nouveau modèle `Appointment` (collection MongoDB `erp_appointments`) avec filtres `?start_from=&start_to=` pour le rendu mois
- **8 nouveaux tests pytest** ✅ (CRUD, range filter, validation, 401)
- **Total 72/72 pytest** passent. Lint backend + frontend clean.

**Bug fix UI** : colonnes des panels Factures/PO étaient trop étroites — les badges "RAPPELÉ J+7 · 15J RETARD" débordaient sur les boutons d'action (signalé par l'utilisateur via screenshot). Grille rééquilibrée : Numéro 2 / Client 3 / Date **1** / Total 2 / **Statut 2** / Actions 2.

### 2026-04 — Iter 18 (Bouton « Marquer payée » + badges visuels)
**Bouton vert one-click** dans la table factures (`DocumentPanel.jsx`) :
- Visible uniquement sur factures `brouillon` ou `envoyée` (pas sur `payée`/`annulée`)
- Confirmation puis `POST /api/admin/invoices/{id}/mark-paid`
- Statut → `payée` → **stoppe automatiquement les rappels** (le scheduler ignore les factures non `envoyée`)
- KPI dashboard mis à jour automatiquement

**Badges visuels** dans la même table (invoices uniquement) :
- 🔴 **« En retard · Xj »** (rouge clair) — facture `envoyée` avec `due_date` dépassée et aucun rappel envoyé
- 🟠 **« Rappelé J+7 · Xj retard »** (orange) — palier amical envoyé
- 🔴 **« Rappelé J+30 · Xj retard »** (rouge ferme) — palier ferme envoyé
- Logique dans `utils.js::overdueState()` + `OVERDUE_BADGE` colors

**Bug fix** : la fenêtre J+7 du scheduler était trop étroite (7-13j → manquait les factures à 14-29j). Corrigé : seuils linéaires (≥7 → J+7 si pas envoyé, ≥30 → J+30 si pas envoyé). Test pytest existant attrape la régression.

**Nouveau endpoint** : `POST /api/admin/invoices/{id}/mark-paid` (idempotent, refuse si annulée).
**Tests** : `tests/test_erp_mark_paid.py` (3 cas) + cleanup. **Total 64/64 pytest ✅**.

### 2026-04 — Iter 17 (Rappels automatiques de factures)
**Fonctionnalité** : relances automatiques quotidiennes des factures en souffrance via Resend.
- **2 paliers configurables** :
  - **J+7** (amical) : rappel poli avec copie PDF de la facture
  - **J+30** (ferme) : mention des intérêts Net 30 (1,5 % / mois)
- **Scheduler APScheduler** : cron quotidien à **08:00 America/Montreal** (démarré au startup FastAPI, stoppé proprement au shutdown)
- **Idempotence** : champ `reminder_level_sent` sur la facture (0 → 7 → 30) empêche le double envoi
- **Endpoints admin** :
  - `POST /api/admin/invoices/{id}/send-reminder?level=7|30` — déclenchement manuel
  - `POST /api/admin/reminders/run-now` — re-lance le scan complet (utile en test)
- **Nouvelle variable env** `DISABLE_SCHEDULER=1` pour tests (empêche le job de tourner pendant pytest)
- **Nouveau fichier** : `/app/backend/erp_reminders.py` (170 lignes) — scheduler + templates HTML FR + endpoints
- **Dépendance ajoutée** : `APScheduler==3.11.2` (+ `tzlocal`)
- **Tests** : 5 nouveaux pytest (`tests/test_erp_reminders.py`) vérifient envoi J+7, idempotence, envoi manuel J+30, rejet niveau invalide, 404 facture inconnue. **61/61 pytest passent globalement**.

### 2026-04 — Iter 16 (Code quality — refactor + fixes review)
**Refactor majeur de `erp.py`** (revue de code : complexité cyclomatique 90, 831 lignes, 54 variables locales) :
- Découpé en 7 modules chacun < 130 lignes :
  - `erp_models.py` (199 l.) — tous les modèles Pydantic + constantes TPS/TVQ
  - `erp_helpers.py` (103 l.) — `compute_totals`, `csv_response`, `send_pdf_email`, `parse_date_safe`, `make_next_number_fn`
  - `erp_routes_parties.py` (47 l.), `erp_routes_products.py` (37 l.), `erp_routes_invoices.py` (130 l.), `erp_routes_purchase_orders.py` (123 l.), `erp_routes_bols.py` (126 l.), `erp_routes_dashboard.py` (99 l.)
  - `erp.py` (33 l.) — orchestrateur qui appelle `register(...)` pour chaque domaine
- **Complexité** : `build_erp_router` 90 → 7, `erp_dashboard` 21 → ~5 (split en 4 helpers : `_kpis`, `_monthly_revenue`, `_top_customers`, `_outstanding_invoices`)

**Fixes frontend (review)** :
- Clés tableau stables : `_key` unique ajouté aux templates `emptyLineItem`/`emptyBolItem`, helper `stripKeys` pour les strip avant POST/PUT. Plus de `key={idx}` sur les champs éditables.
- Clés tableau composites sur les vues d'impression (`item-${i}-${description}`) — `AdminPrintInvoice/PO/Bol`.
- `console.error` retiré d'`AuthContext.jsx` (fetchMe + logout).

**Tests** : 56/56 backend pytest passent (test_erp_api 33/33 + test_portech_api 23/23). Frontend lint ✅ clean. Endpoints `/api/admin/{invoices,purchase-orders,bills-of-lading,parties,products,dashboard,exports/*}` tous 200.

**Note sur la revue** : les alertes « React Hook missing dependencies » du rapport étaient des faux positifs — `http` est un constant module-level (ligne 17 d'AuthContext), `setUser`/`setError` sont des setState stables par React. Notre linter ESLint v9 (react-hooks/exhaustive-deps) ne signale aucun problème.

### 2026-04 — Iter 14 + 15 (Refonte photo quincaillerie catalogue style + fixes ERP)
**Feedback utilisateur** : les photos générées avec techniciens Portech + outils DeWalt ne plaisent pas. Remplacées par **gros plans produit** style catalogue manufacturier (SALTO, Sargent, Von Duprin) — aucune personne, aucun outil, aucun logo, aucune signalétique, rien de partiellement exposé.

**Photos régénérées (30 au total)** :
- **Galerie interventions** (4) : poignée levier sur alu foncé / ferme-porte régulier (corps sur porte, bras sur cadre) / charnière continue pleine hauteur / cylindre haute sécurité installé
- **Galerie serrures** (4) : mortaise installée complète / levier cylindrique noir mat / mortaise électronique style SALTO XS4 / mortaise storeroom industrielle
- **Galerie dispositifs de sortie** (3, sauf #3 conservée) : rim chromé / tige verticale dissimulée / touchpad Von Duprin 98/99
- **Galerie barre antipanique** (1 seule, #2) : cross-bar stainless avec dogging — cinéma
- **Home showcase + services** (9) : showcase tech / install / usinage / répar / upgrade / showcase exit/panic/lock / precision-install
- **Page Services** (4) : installation, usinage, réparation, mise à niveau

**Conservées** : tous les chantiers haut de gamme, gal-panic-1/3/4, gal-exit-3, hero Home, brand wall, clients (restaurant/école/condo/bureau), catalogue PDF extraits.

**Fixes ERP (action items testing agent v3)** :
- ✅ Endpoint manquant **`GET /api/admin/exports/bills-of-lading.csv`** ajouté dans `erp.py`
- ✅ `BolPanel.jsx` : ajout bouton **Export CSV** + **barre de recherche** (alignement avec Invoices/PO panels)
- ✅ Route **`/galerie`** (sans catégorie) redirige vers `/galerie/interventions` — fini la page blanche

**Caption fixes** : supprimé toute mention "partiellement exposé" des légendes Galerie (demande utilisateur : rien ne doit être partiellement exposé, ni visuellement ni textuellement).

**Tests backend** : 55/55 pytest passent après ajout BOL CSV. Login/CSV/galerie redirect tous 200.

## Backlog / P1
- [ ] Acheter le domaine `portech.ca` et le vérifier sur Resend pour pouvoir envoyer à n'importe quelle adresse en mode prod
- [ ] Photos avant/après réelles (remplacer les placeholders IA)
- [ ] Numéro de téléphone lorsque disponible
- [ ] Restreindre `CORS_ORIGINS` au domaine de prod (✅ fait — seulement prod + preview)
- [ ] Bouton flottant « Appelez maintenant » / WhatsApp sur mobile
- [ ] Page « Soumission Express » (calculateur de coûts)

### 2026-05 — Iter 23 (Outil de prospection B2B vitreries)
**Nouveau module Prospection** (`/admin/gestion/prospection`) :
- **Backend** (`prospection_routes.py`, `prospection_models.py`, `prospection_scraper.py`) :
  - Scraping OpenStreetMap/Overpass gratuit (vitreries Grand Montréal / Laval / Rive-Sud / Rive-Nord)
  - 2 nouvelles collections : `prospection_prospects`, `prospection_campaigns`, `prospection_outbox`
  - CRUD complet prospects + campagnes
  - Modèle FR pré-approuvé (sous-traitance vitrerie) chargeable via `GET /campaigns/default` avec bannières `https://portech.info/email/email-header.png` et `email-footer.png`
  - Envoi via Resend depuis `info@portech.info` (domaine vérifié)
  - **Garde-fous** : `confirm=true` obligatoire (400 sinon) + **limite 50 envois/heure** (configurable via `PROSPECTION_HOURLY_LIMIT`) + skip prospects `unsubscribed`
  - Mode `test_only=true` pour preview à une adresse de test sans toucher la prod
  - Filtrage des prospects par courriel AVANT troncature quota (évite le gaspillage de quota)
- **Frontend** (`ProspectionPanel.jsx`) : 4 sous-onglets — **Vitreries** (liste, scrape par région, ajout manuel) · **Campagnes** (éditeur HTML + aperçu live des bannières) · **Envoi** (sélection multi-cases + checkbox « Je confirme l'envoi » + envoi test) · **Historique** (outbox Resend IDs).
- **Stats banner** : 5 tuiles (prospects, avec courriel, envoyés 24h, envoyés/quota 1h, restant cette heure).
- **Tests** : 20 nouveaux tests pytest (`test_prospection_api.py`). **Total 92/92 pytest ✅**. Smoke test live Overpass (10 vitreries Montréal scrapées, 1 avec courriel) + Resend (id confirmé).
- **UI fix** : padding onglets secondaires `px-4 → px-3` pour éviter le clipping à 1920px.

## Backlog / P1

## Backlog / P2
- [ ] Notification SMS Twilio en plus du courriel (alerte lead <30s)
- [ ] Blog SEO (barres antipaniques, codes du bâtiment QC)
- [ ] Upload de photos dans le formulaire de contact
- [ ] Export CSV des soumissions depuis le dashboard
- [ ] Calendrier des rendez-vous / intégration Google Calendar

## Key URLs
- Site : `https://web-project-fr-2.preview.emergentagent.com`
- Admin : `https://web-project-fr-2.preview.emergentagent.com/admin/login`
- Identifiants : voir `/app/memory/test_credentials.md`

## Notes techniques
- Resend en mode test : les emails ne partent qu'à l'adresse du compte Resend (sauf domaine vérifié). Pour envoyer librement à portech.infos@gmail.com, le compte Resend doit être créé avec cette adresse OU un domaine doit être vérifié.
- Script de régénération d'images : `python3 /app/scripts/generate_images.py` (idempotent, écrase les PNGs existants).
