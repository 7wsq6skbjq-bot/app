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

## Backlog / P1
- [ ] Acheter le domaine `portech.ca` et le vérifier sur Resend pour pouvoir envoyer à n'importe quelle adresse en mode prod (actuellement, mode test Resend = limites possibles)
- [ ] Photos avant/après réelles (remplacer les placeholders IA)
- [ ] Numéro de téléphone lorsque disponible
- [ ] Restreindre `CORS_ORIGINS` au domaine de prod
- [ ] Page mentions légales + politique de confidentialité

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
