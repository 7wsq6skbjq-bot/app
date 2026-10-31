# Portech ERP — Vue d'ensemble complète (pour revue par un agent IA externe)

## 1. Contexte de l'entreprise
- **Portech** — Quincaillerie et portes commerciales en aluminium (Québec, Canada).
- Activité : **vente/fourniture** de portes commerciales en aluminium + vente, installation et remplacement de **quincaillerie** (serrures, cylindres, ferme-portes, barres anti-panique, gâches électriques, etc.).
- ⚠️ Portech **n'installe PAS les portes** elles-mêmes — fourniture seulement. L'installation concerne la quincaillerie.
- Propriétaire / utilisateur unique principal : Cédrick Pimparé (expert portes commerciales).
- Fiscalité : taxes canadiennes **TPS 5 %** + **TVQ 9,975 %** (Québec). Déclarations trimestrielles à Revenu Québec.
- Langue : **français** partout (interface, PDF, courriels).

## 2. Stack technique
- **Frontend** : React 19, React Router 7, Tailwind CSS 3, composants Radix UI / shadcn, Recharts (graphiques), lucide-react (icônes), axios, sonner (toasts).
- **Backend** : FastAPI 0.110, Python, Motor/PyMongo (MongoDB async).
- **Base de données** : MongoDB.
- **PDF** : ReportLab (génération serveur) + pypdf, pdf2image, ezdxf (découpe/DXF).
- **Courriels** : Resend (images de bannières jointes en CID inline).
- **IA** : emergentintegrations + litellm/openai/google-genai (assistant ERP + OCR reçus via pytesseract).
- **Paiements/divers** : Stripe (présent), boto3/S3 (stockage), APScheduler (rappels automatiques), pywebpush (notifications push).
- **Auth** : JWT (PyJWT / python-jose), bcrypt/passlib.
- Toutes les routes backend sont préfixées `/api`. Config via variables d'environnement uniquement.

## 3. Modules / Panneaux de l'ERP (≈30 sections)

### Ventes & documents
- **Tableau de bord** (`DashboardPanel`) — KPIs, graphiques, aperçu de l'activité.
- **Tiers / Parties** (`PartiesPanel`) — clients et fournisseurs (nom, contact, courriel, téléphone, adresse, numéro de taxe).
- **Produits** (`ProductsPanel`) — catalogue avec prix de vente public + **prix coûtant confidentiel** (jamais sur les PDF clients).
- **Soumissions / Devis** (`QuotesPanel`) — statuts : brouillon, en attente d'approbation, envoyée, acceptée, refusée, expirée, annulée. Conversion devis → facture. Annexe conditions de vente, dessins Adams Rite, dépôt affichable, pièces jointes (GridFS).
- **Factures** (`InvoicesPanel`) — statuts : brouillon, en attente d'approbation, envoyée, partiellement payée, payée, en retard, annulée. Dépôts, solde dû, rappels automatiques (J+7, J+30).
- **Bons de commande** (`PurchaseOrdersPanel`) — achats fournisseurs.
- **Bons de livraison / BOL** (`BolPanel`) — expédition (expéditeur, destinataire, transporteur, poids).
- **États de compte** (`StatementsPanel`) — relevés client.
- **Avis de paiement** (`PaymentNoticesPanel`).
- **Suivi des dépôts** (`DepositsPanel`).

### Comptabilité & taxes
- **Dépenses** (`ExpensesPanel`) — saisie de dépenses avec catégories (Matériaux, Carburant, Outils, Véhicule, Sous-traitance, etc.), TPS/TVQ, mode de paiement, **photos de reçus** (GridFS, upload/aperçu/téléchargement, OCR). Filtre par mois ou « Tous les mois », filtre par catégorie. Rapport PDF détaillé par plage de dates (sommaire, coût net, CTI/RTI, ventilation par catégorie, détail ligne par ligne, annexe de reçus, envoi au comptable, résumé trimestriel).
- **Récap TPS/TVQ** (`TaxRecapPanel`) — calcul des taxes collectées vs payées, par trimestre OU par plage de dates. Détail par facture (client, nº, date, sous-total, TPS, TVQ, total, indicateur taxable/non taxable). PDF + envoi au comptable.
- **Rapport kilométrique** (`MileagePanel`) — suivi des déplacements pour déductions.
- **Coûts Master** (`MasterCostsPanel`) — grille de prix coûtants de référence.

### Production & atelier
- **Plans de production** (`ProductionPlansPanel`).
- **Fabrication** (`FabricationPanel`).
- **Liste de découpe** (`CutListPanel`) — optimiseur de découpe aluminium, export DXF/PDF.
- **Inventaire** (`InventoryPanel`).
- **Moustiquaires** (`MosquitoScreensPanel`).
- **Commandes AT / formulaire fournisseur** (`ATOrdersPanel`) — bons de commande pré-remplis (profilés AT, bibliothèque de profils).
- **Catalogue quincaillerie** (`CatalogPanel`) — Adams Rite, profils, dessins techniques.

### Clients / terrain / IA
- **Rapports d'expertise** (`ExpertReportsPanel`) — inspection de portes commerciales : portes inspectées (série, modèle, dimensions, serrure, gâche, seuil, etc.), observations, impacts, recommandations, photos, conclusion. PDF professionnel.
- **Demandes de porte** (`DoorRequestsPanel`) — leads du site public (type, dimensions, quantité).
- **Prospection** (`ProspectionPanel`) — scraping/suivi de prospects.
- **Calendrier / Rendez-vous** (`CalendarPanel`) — agenda interne (lié à Google Calendar).
- **Composer un courriel** (`ComposeEmailPanel`) — éditeur courriel avec bannières header/footer de marque (CID inline).
- **Assistante IA** (`AssistantPanel`) — assistant conversationnel sur les données de l'ERP.
- **Jobs / Suivi des jobs** (`JobsPanel`) — suivi de projets/chantiers.

## 4. Modèles de données clés (MongoDB)

**Party** (client/fournisseur) : id, kind (customer|supplier), name, contact, email, phone, adresse, province (QC), tax_number, notes.

**Product** : id, sku, name, unit, unit_price (public), cost_price (CONFIDENTIEL), category, is_service.

**LineItem** : description, quantity, unit_price, product_id, total, + cost_price / cost_category / margin_pct (CONFIDENTIELS — jamais sur PDF).

**Invoice** : number, customer_snapshot, date, due_date, items[], subtotal, tps, tvq, total, taxable, status, deposit_received/pct/amount, balance_due, reminder_level_sent (0/7/30).

**Quote** : number, customer_snapshot, date, valid_until, items[], totaux, status, converted_invoice_id, drawing_pages, include_sales_conditions, show_deposit, deposit_pct, attachments[].

**PurchaseOrder / BillOfLading** : similaires avec fournisseur/transporteur.

**Expense** : date, supplier_name, description, category, subtotal, tps, tvq, total, payment_method, status (payée|à payer), invoice_ref, receipt_filename (GridFS).

**ExpertReport** : number, client_snapshot, projet, inspection_date, inspector, doors[] (InspectedDoor: tag, série, modèle, dimensions, serrure, gâche, seuil, observations, impacts, recommandation), risks, conclusion, photos[], status.

**Appointment** : title, start, end, party, location, status (prévu|fait|annulé), color.

Taux : TPS_RATE = 0.05, TVQ_RATE = 0.09975.

## 5. Conventions / règles importantes
- Les **prix coûtants et marges** ne doivent JAMAIS apparaître sur les documents clients (soumissions, factures, PDF).
- Les statuts internes « brouillon » et « en attente d'approbation » sont **masqués sur les PDF clients**.
- Snapshots : chaque document stocke une copie figée du client/fournisseur (customer_snapshot) pour conserver l'historique même si le tiers change.
- Numéros de documents séquentiels (number entier auto-incrémenté).
- Dates stockées en ISO (YYYY-MM-DD ou datetime UTC).

## 6. Points d'amélioration déjà identifiés (non bloquants)
- Incohérence historique de stockage : 19 dépenses référencent un reçu mais seulement 9 fichiers existent en GridFS (migration à investiguer).
- Pas de navigation par année sur les dépenses (seulement 12 derniers mois + « Tous les mois »).
- Conformité fiscale finale (exigibilité des taxes, factures émises avant inscription) à confirmer avec un comptable — l'ERP ne remplace pas un avis fiscal.
