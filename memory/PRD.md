# Portech — PRD

## Problem statement (verbatim)
> "Je veux créé un site pour mon entreprise. Portech est une entreprise spécialisée dans l'installation de quincaillerie pour portes commerciales. Clients : commerces, restaurants, écoles, tours à condos, bureaux. Services : achat de portes en aluminium, usinage, installation de quincaillerie (barres antipaniques, ferme-portes, serrures), préparation complète prête à installer. Objectif : générer des leads, inspirer confiance, montrer l'expertise, inciter les visiteurs à contacter. Style : moderne, professionnel, industriel, noir/blanc/gris + accent métallique/bleu. 4 pages : Accueil, Services, À propos (avec storytelling fondateur), Contact (formulaire)."

## Architecture
- **Backend**: FastAPI (`/app/backend/server.py`) + MongoDB (motor). Routes préfixées `/api`.
  - `GET /api/` — health
  - `POST /api/contact` — stocke une soumission (name, phone, email, message, project_type?) → 201
  - `GET /api/contact` — liste des soumissions (admin — à protéger en prod)
  - Models Pydantic v2 avec `EmailStr`, UUID, datetime ISO.
- **Frontend**: React 19 + React Router v7 + Tailwind + lucide-react.
  - `Layout` (Navbar sticky + Outlet + Footer) wrap toutes les routes.
  - Pages : `Home`, `Services`, `About`, `Contact`.
  - Fonts : Barlow Condensed (display) + IBM Plex Sans (body) + JetBrains Mono (accents).
- **MongoDB collections**: `contact_submissions`, `status_checks`.

## User personas
- **Gestionnaire d'immeuble / syndic de copropriété** — cherche une solution durable pour des portes qui coûtent cher en service.
- **Directeur de commerce / restaurant / épicerie** — veut une porte commerciale qui ne bloque pas les opérations.
- **Directeur d'école / institution** — sécurité + conformité des barres antipaniques.
- **Entrepreneur général / contracteur** — a besoin d'un sous-traitant fiable pour la quincaillerie.

## Core requirements (static)
- 4 pages SEO-optimisées (mots-clés : « quincaillerie porte commerciale », « installation porte commerciale », « barre antipaniques installation »).
- Formulaire de contact fonctionnel (stockage MongoDB).
- Design industriel épuré, haut de gamme, monochrome + bleu métallique.
- Storytelling fondateur intégré (10+ ans, 45 ans transmis).
- CTA répétés « Demander une soumission ».
- Section problèmes / solution / avant-après pour conversion.

## What's been implemented (2026-01)
- **Backend** : endpoint `/api/contact` (POST/GET) avec validation Pydantic, stockage MongoDB UUID + ISO datetime.
- **Frontend** — Page Accueil : hero plein écran avec fiche technique, marquee secteurs, grille problèmes (4 pain points), solution Portech, grille 4 services, pourquoi Portech (4 bénéfices), avant/après visuel, 3 témoignages, CTA final.
- **Frontend** — Page Services : hero, 4 blocs détaillés avec check-lists, 4 étapes processus, CTA final.
- **Frontend** — Page À propos : hero, storytelling en 5 chapitres avec image fondateur sticky, Mission + Vision (split card), pourquoi nous, CTA final.
- **Frontend** — Page Contact : hero, formulaire complet (nom, téléphone, email, type de projet, message) avec états success/error, panneau coordonnées sombre, note confidentialité.
- **SEO** : meta description + keywords + OG tags, H1/H2 structurés.
- **data-testid** sur tous les éléments interactifs.
- **Testing** : testing_agent_v3 → 100% backend, 100% frontend (iteration_1.json).

## Backlog / P1
- [ ] Intégration envoi d'email (SendGrid ou Resend) pour notifier le propriétaire à chaque soumission.
- [ ] Authentification admin pour protéger `GET /api/contact` + petit dashboard de leads.
- [ ] Restreindre `CORS_ORIGINS` au domaine de prod.
- [ ] Galerie photos avant/après réelles (remplacer les placeholders).
- [ ] Coordonnées réelles (téléphone, adresse) dans le footer et Contact.
- [ ] Page `/mentions-legales` + `/politique-de-confidentialite`.

## Backlog / P2
- [ ] Blog / articles SEO (« comment choisir une barre antipaniques », « signes qu'une porte commerciale doit être remplacée »).
- [ ] Formulaire multi-étape avec photo upload pour soumissions.
- [ ] Intégration Google Maps pour zone de service.
- [ ] Témoignages vidéo ou avec photos réelles.
- [ ] Animation scroll-reveal plus poussée (Framer Motion / Motion).
- [ ] Mode sombre optionnel.

## Key URLs
- Preview : `https://web-project-fr-2.preview.emergentagent.com`
- Backend test : `{REACT_APP_BACKEND_URL}/api/`

## Notes
- Testid À propos généré par regex supprime « à » → `nav-link-propos` (fonctionnel mais convention à améliorer).
- Test de soumission contact validé en prod via curl (id UUID retourné, stocké en base).
