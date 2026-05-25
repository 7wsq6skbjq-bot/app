"""
Portech B2B prospection routes (vitreries / glass shops).

Endpoints (all under /admin/prospection/):
  - GET    /prospects               list with optional filters
  - POST   /prospects               create one
  - PUT    /prospects/{id}          update
  - DELETE /prospects/{id}          delete
  - POST   /prospects/scrape        OpenStreetMap scrape (free)
  - POST   /prospects/bulk          CSV-style bulk import
  - GET    /campaigns               list
  - POST   /campaigns               create
  - PUT    /campaigns/{id}
  - DELETE /campaigns/{id}
  - POST   /campaigns/send          send with explicit confirm + rate-limit
  - GET    /outbox                  send history
  - GET    /stats                   counts (today, last hour, by status)

Hard safeguards:
  - `confirm=true` MUST be passed to actually dispatch emails.
  - 50 emails/hour rolling rate-limit (protects domain reputation).
  - Prospects flagged `unsubscribed=true` are NEVER sent to.
"""
import asyncio
import base64
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import resend
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from prospection_models import (
    Campaign,
    CampaignIn,
    EnrichRequest,
    OutboxEntry,
    Prospect,
    ProspectBulkImport,
    ProspectIn,
    ScrapeRequest,
    SendCampaignRequest,
    now_iso,
)
from prospection_scraper import CATEGORIES, REGIONS, enrich_prospect, scrape_region

logger = logging.getLogger("portech.prospection")

HOURLY_SEND_LIMIT = int(os.environ.get("PROSPECTION_HOURLY_LIMIT", "50"))
FROM_EMAIL = os.environ.get("PROSPECTION_FROM_EMAIL", os.environ.get("SENDER_EMAIL", "info@portech.info"))
FROM_NAME = os.environ.get("PROSPECTION_FROM_NAME", "Cédrick Pimparé · Portech")

# Inline-attached banners (loaded once at import; small files, ~80KB total).
# Using CID attachments means recipients see the banners even if portech.info
# is unreachable, mis-configured, or blocked by their corporate email gateway.
# Banners live INSIDE the backend folder so they always ship with the backend
# container (the frontend's public/ may not be reachable in a multi-container
# deployment).
_BANNER_DIR = Path(__file__).parent / "email_assets"
HEADER_CID = "portech-header.png"
FOOTER_CID = "portech-footer.png"


def _load_banner(filename: str) -> Optional[str]:
    p = _BANNER_DIR / filename
    if not p.exists():
        logger.warning("Banner file not found: %s", p)
        return None
    return base64.b64encode(p.read_bytes()).decode("ascii")


_BANNER_HEADER_B64 = _load_banner("email-header.png")
_BANNER_FOOTER_B64 = _load_banner("email-footer.png")


# ===========================================================================
# Email body wrapper — shared across all category templates
# ===========================================================================
def _wrap_body(intro_paragraphs: str, sections_html: str, footer_note: str) -> str:
    """Build a full HTML email with header/footer banners and CTA."""
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, Helvetica, sans-serif; background:#f4f4f5; padding:0; margin:0;">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; max-width:600px;">'
        '<tr><td><img src="https://portech.info/email/email-header.png" alt="Portech" style="display:block; width:100%; max-width:600px; height:auto; border:0;"/></td></tr>'
        '<tr><td style="padding:32px 32px 8px 32px; color:#0c182b; font-size:15px; line-height:1.6;">'
        + intro_paragraphs
        + sections_html
        + '<p style="margin:24px 0 16px 0;">Si vous avez 15 minutes cette semaine, je serais content d\'en discuter avec vous.</p>'
        + '<p style="margin:0 0 4px 0;"><b><a href="tel:+14383764177" style="color:#0c182b; text-decoration:none;">438-376-4177</a></b></p>'
        + '<p style="margin:0 0 24px 0;"><a href="https://www.portech.info" style="color:#1d4ed8;">www.portech.info</a></p>'
        + '<p style="margin:0 0 4px 0;">Bonne journée!</p>'
        + '<p style="margin:16px 0 0 0;"><b>Cédrick Pimparé</b><br/>Portech — Quincaillerie de porte commerciale</p>'
        + '</td></tr>'
        + '<tr><td><img src="https://portech.info/email/email-footer.png" alt="Portech" style="display:block; width:100%; max-width:600px; height:auto; border:0;"/></td></tr>'
        + '<tr><td style="padding:16px 32px; color:#71717a; font-size:11px; text-align:center;">'
        + footer_note + '<br/>'
        + 'Pour ne plus recevoir de courriels de Portech, répondez simplement « RETIRER » à ce message.'
        + '</td></tr></table></td></tr></table>'
    )


# ===========================================================================
# Per-category templates (subject + intro + sections)
# ===========================================================================
TEMPLATES: dict[str, dict] = {
    # ----- VITRERIES -----
    "vitrerie": {
        "subject": "Sous-traitance quincaillerie pour vos projets vitrerie",
        "intro": (
            '<p style="margin:0 0 16px 0;">Bonjour {{Nom_Entreprise}},</p>'
            '<p style="margin:0 0 16px 0;">Cédrick Pimparé, fondateur de Portech.</p>'
            '<p style="margin:0 0 16px 0;">On est spécialisés en <b>quincaillerie de porte commerciale</b> dans le Grand Montréal, Laval, la Rive-Sud et la Rive-Nord.</p>'
            '<p style="margin:0 0 16px 0;">Je vous contacte parce qu\'on aide déjà plusieurs vitreries à gérer tout ce qui touche la quincaillerie commerciale et les portes aluminium.</p>'
            '<p style="margin:0 0 12px 0;">Concrètement, voici ce qu\'on peut faire pour vous :</p>'
        ),
        "sections": (
            '<p style="margin:18px 0 6px 0;"><b>• Sous-traitance de quincaillerie sur vos projets</b></p>'
            '<p style="margin:0 0 8px 0;">Barres antipaniques, ferme-portes, serrures mortaises, dispositifs de sortie, ajustements, installation complète, etc.</p>'
            '<p style="margin:0 0 4px 0;">Vous, vous conservez vos clients et votre marge de profit.</p>'
            '<p style="margin:0 0 16px 0;">Nous, nous prenons en charge l\'exécution.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Fourniture de portes en aluminium prêtes à poser</b></p>'
            '<p style="margin:0 0 8px 0;">Portes usinées en atelier ou sur chantier, quincaillerie installée et ajustée avant livraison.</p>'
            '<p style="margin:0 0 2px 0;">Moins de temps perdu sur le chantier.</p>'
            '<p style="margin:0 0 2px 0;">Moins de coordination.</p>'
            '<p style="margin:0 0 2px 0;">Finition plus propre et professionnelle.</p>'
            '<p style="margin:0 0 16px 0;">Garantie que toute quincaillerie est adéquate et adaptée au système.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Aucun conflit avec votre activité</b></p>'
            '<p style="margin:0 0 16px 0;">Nous ne faisons pas de vitrage ni d\'installations de verre. Notre rôle est de compléter votre service, pas de le remplacer.</p>'
        ),
        "footer_note": "Vous recevez ce courriel parce que votre entreprise est référencée comme vitrerie dans le Grand Montréal.",
    },

    # ----- ENTREPRENEURS GÉNÉRAUX -----
    "entrepreneur": {
        "subject": "Partenaire quincaillerie pour vos projets commerciaux",
        "intro": (
            '<p style="margin:0 0 16px 0;">Bonjour {{Nom_Entreprise}},</p>'
            '<p style="margin:0 0 16px 0;">Cédrick Pimparé, fondateur de <b>Portech</b> — quincaillerie de porte commerciale dans le Grand Montréal, Laval, Rive-Sud et Rive-Nord.</p>'
            '<p style="margin:0 0 16px 0;">Comme entrepreneur général, vous gérez des dizaines de fournisseurs sur chaque chantier. La quincaillerie de portes — c\'est souvent le détail qui retarde une remise des clés (codes du bâtiment, ajustements millimétriques, conformité NFPA 80).</p>'
            '<p style="margin:0 0 12px 0;">Ce que Portech peut faire pour vous :</p>'
        ),
        "sections": (
            '<p style="margin:18px 0 6px 0;"><b>• Fourniture et installation rapide de la quincaillerie</b></p>'
            '<p style="margin:0 0 16px 0;">Serrures, barres antipaniques, ferme-portes, dispositifs de sortie, contrôle d\'accès — livrés et installés selon votre calendrier de chantier.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Portes aluminium commerciales prêtes à poser</b></p>'
            '<p style="margin:0 0 16px 0;">Usinées en atelier avec toute la quincaillerie déjà ajustée. Vos installateurs posent en une fraction du temps.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Conformité aux codes du bâtiment</b></p>'
            '<p style="margin:0 0 16px 0;">RBQ, NBC, NFPA 80 — on s\'occupe que tout passe l\'inspection du premier coup. Moins de retours, moins de pénalités de retard.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Soumission rapide</b></p>'
            '<p style="margin:0 0 16px 0;">On répond aux demandes de prix sous 24-48h, plans à l\'appui.</p>'
        ),
        "footer_note": "Vous recevez ce courriel parce que votre entreprise est référencée comme entrepreneur général dans le Grand Montréal.",
    },

    # ----- ARCHITECTES -----
    "architecte": {
        "subject": "Spécification quincaillerie pour vos projets architecturaux",
        "intro": (
            '<p style="margin:0 0 16px 0;">Bonjour {{Nom_Entreprise}},</p>'
            '<p style="margin:0 0 16px 0;">Cédrick Pimparé, fondateur de <b>Portech</b> — atelier spécialisé en quincaillerie de porte commerciale (Grand Montréal et environs).</p>'
            '<p style="margin:0 0 16px 0;">Comme architecte, vous savez à quel point la spécification de la quincaillerie peut faire ou défaire un projet : retour d\'inspection, ferme-porte mal calibré, finition qui jure avec la vision du client…</p>'
            '<p style="margin:0 0 12px 0;">Mon objectif est de devenir votre référence pour ce volet :</p>'
        ),
        "sections": (
            '<p style="margin:18px 0 6px 0;"><b>• Consultation gratuite en phase devis</b></p>'
            '<p style="margin:0 0 16px 0;">Avant même que vos plans partent en soumission, je peux valider que les quincailleries spécifiées sont conformes (NBC, NFPA 80, RBQ) et compatibles avec les portes choisies.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Devis détaillés par numéro de porte</b></p>'
            '<p style="margin:0 0 16px 0;">Schedule complet avec marques, finis et quincaillerie associée — prêt à intégrer dans votre cahier des charges.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Finitions et marques haut de gamme</b></p>'
            '<p style="margin:0 0 16px 0;">Allegion (Schlage, Von Duprin, LCN), Sargent, Best, Hager, ASSA ABLOY. Je peux proposer des équivalents techniques quand le budget l\'exige.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Visites de chantier sur demande</b></p>'
            '<p style="margin:0 0 16px 0;">Pour valider l\'installation avant la livraison finale au client.</p>'
        ),
        "footer_note": "Vous recevez ce courriel parce que votre firme est référencée comme firme d'architectes dans la région.",
    },

    # ----- DESIGNERS D'INTÉRIEUR -----
    "designer": {
        "subject": "Quincaillerie haut de gamme pour vos projets de design",
        "intro": (
            '<p style="margin:0 0 16px 0;">Bonjour {{Nom_Entreprise}},</p>'
            '<p style="margin:0 0 16px 0;">Cédrick Pimparé, fondateur de <b>Portech</b> — quincaillerie de porte commerciale (Grand Montréal, Laval, Rive-Sud, Rive-Nord).</p>'
            '<p style="margin:0 0 16px 0;">Dans un projet de design commercial, le détail des portes — finition, poignée, serrure visible — peut faire toute la différence sur la perception du client final.</p>'
            '<p style="margin:0 0 12px 0;">Ce que je peux apporter à vos projets :</p>'
        ),
        "sections": (
            '<p style="margin:18px 0 6px 0;"><b>• Quincaillerie design coordonnée</b></p>'
            '<p style="margin:0 0 16px 0;">Finis brossés, noirs mats, laitons, chromes — toujours en harmonie avec votre charte. Marques : Allegion, Sargent, Emtek, Baldwin, ASSA ABLOY.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Portes aluminium sur mesure</b></p>'
            '<p style="margin:0 0 16px 0;">Profilés, vitrages et quincailleries assemblés selon vos rendus 3D. Aucun écart entre le concept et le résultat.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Cohérence acoustique et accessibilité</b></p>'
            '<p style="margin:0 0 16px 0;">Quincaillerie qui respecte les normes d\'accessibilité (RBQ) et les exigences acoustiques (commerces, cliniques, bureaux).</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Échantillons et fiches techniques</b></p>'
            '<p style="margin:0 0 16px 0;">Je peux vous monter une présentation visuelle pour vos clients en quelques jours.</p>'
        ),
        "footer_note": "Vous recevez ce courriel parce que votre studio est référencé comme designer d'intérieur dans la région.",
    },

    # ----- PROMOTEURS / CONSTRUCTEURS -----
    "promoteur": {
        "subject": "Contrat-cadre quincaillerie pour vos développements",
        "intro": (
            '<p style="margin:0 0 16px 0;">Bonjour {{Nom_Entreprise}},</p>'
            '<p style="margin:0 0 16px 0;">Cédrick Pimparé, fondateur de <b>Portech</b> — quincaillerie de porte commerciale dans le Grand Montréal.</p>'
            '<p style="margin:0 0 16px 0;">Quand on construit ou développe plusieurs projets simultanément, la quincaillerie représente un poste de coût souvent sous-estimé : entre 8 000 $ et 25 000 $ par bâtiment commercial moyen, sans compter les retours et reprises.</p>'
            '<p style="margin:0 0 12px 0;">Je vous propose un partenariat structuré :</p>'
        ),
        "sections": (
            '<p style="margin:18px 0 6px 0;"><b>• Contrat-cadre pluri-projets</b></p>'
            '<p style="margin:0 0 16px 0;">Prix fixés par catégorie de bâtiment (résidentiel multi-logements, commercial, institutionnel). Vous savez exactement combien chaque porte coûte, dès la phase devis.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Livraison synchronisée avec votre échéancier</b></p>'
            '<p style="margin:0 0 16px 0;">Quincailleries livrées et installées au bon moment du chantier — pas trop tôt (volages), pas trop tard (retards).</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Garantie unique sur l\'ensemble</b></p>'
            '<p style="margin:0 0 16px 0;">Une seule entreprise responsable pour tout ce qui est porte+quincaillerie — fini les renvois entre fournisseurs quand quelque chose bloque.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Études de cas disponibles</b></p>'
            '<p style="margin:0 0 16px 0;">Je peux vous partager des projets récents (commerces, bureaux, cliniques) avec ROI mesuré.</p>'
        ),
        "footer_note": "Vous recevez ce courriel parce que votre entreprise est référencée comme promoteur immobilier dans la région.",
    },

    # ----- CENTRES COMMERCIAUX & BÂTIMENTS COMMERCIAUX -----
    "commercial": {
        "subject": "Entretien et remplacement de quincaillerie commerciale",
        "intro": (
            '<p style="margin:0 0 16px 0;">Bonjour {{Nom_Entreprise}},</p>'
            '<p style="margin:0 0 16px 0;">Cédrick Pimparé, fondateur de <b>Portech</b> — spécialiste de la quincaillerie de porte commerciale (Grand Montréal).</p>'
            '<p style="margin:0 0 16px 0;">Dans un centre d\'achats ou un bâtiment commercial à fort achalandage, les portes prennent un usage 10 à 20 fois plus intense qu\'en résidentiel. Un ferme-porte mal calibré ou une barre antipanique défectueuse, c\'est une plainte par jour — et un risque légal en cas d\'évacuation.</p>'
            '<p style="margin:0 0 12px 0;">Ce que je peux offrir à votre établissement :</p>'
        ),
        "sections": (
            '<p style="margin:18px 0 6px 0;"><b>• Programme d\'entretien préventif</b></p>'
            '<p style="margin:0 0 16px 0;">Inspection annuelle de toutes les portes commerciales — ajustement, lubrification, remplacement des pièces usées. Rapport écrit pour vos archives RBQ.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Intervention rapide en cas de bris</b></p>'
            '<p style="margin:0 0 16px 0;">Serrure brisée, barre antipanique bloquée, ferme-porte qui ne ferme plus : intervention sous 24-48h pour éviter la fermeture temporaire d\'un commerce.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Mise aux normes lors de rénovations</b></p>'
            '<p style="margin:0 0 16px 0;">Conformité NFPA 80 (portes coupe-feu), RBQ, accessibilité — incontournable lors d\'un changement de locataire ou d\'une rénovation majeure.</p>'
            '<p style="margin:18px 0 6px 0;"><b>• Inspection et rapport d\'expertise</b></p>'
            '<p style="margin:0 0 16px 0;">Pour vos compagnies d\'assurance ou avant l\'achat/la vente d\'un bâtiment commercial.</p>'
        ),
        "footer_note": "Vous recevez ce courriel parce que votre établissement est référencé comme bâtiment commercial dans la région.",
    },
}


def _build_body_html(category: str) -> str:
    tpl = TEMPLATES.get(category) or TEMPLATES["vitrerie"]
    return _wrap_body(tpl["intro"], tpl["sections"], tpl["footer_note"])


def _render_template(html: str, prospect: dict) -> str:
    """Replace simple {{var}} placeholders in the HTML body."""
    out = html
    name = prospect.get("name") or ""
    out = out.replace("{{Nom_Entreprise}}", name)
    out = out.replace("{{Nom_Vitrerie}}", name)  # legacy alias
    out = out.replace("{{name}}", name)
    out = out.replace("{{contact_name}}", prospect.get("contact_name") or "")
    out = out.replace("{{city}}", prospect.get("city") or "")
    return out


async def _count_sent_last_hour(db: AsyncIOMotorDatabase) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    return await db.prospection_outbox.count_documents(
        {"sent_at": {"$gte": cutoff}, "status": {"$in": ["sent", "queued"]}}
    )


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    # =========================================================================
    # Prospects CRUD
    # =========================================================================
    @router.get("/prospection/prospects", response_model=List[Prospect])
    async def list_prospects(
        region: Optional[str] = None,
        status: Optional[str] = None,
        has_email: Optional[bool] = None,
        category: Optional[str] = None,
        _: dict = Depends(auth_dep),
    ):
        query: dict = {}
        if region:
            query["region"] = region
        if status:
            query["status"] = status
        if category:
            query["category"] = category
        if has_email is True:
            query["email"] = {"$nin": [None, ""]}
        elif has_email is False:
            query["$or"] = [{"email": None}, {"email": ""}]
        cur = db.prospection_prospects.find(query, {"_id": 0}).sort("created_at", -1).limit(500)
        return [Prospect(**d) async for d in cur]

    @router.post("/prospection/prospects", response_model=Prospect, status_code=201)
    async def create_prospect(data: ProspectIn, _: dict = Depends(auth_dep)):
        prospect = Prospect(**data.model_dump())
        await db.prospection_prospects.insert_one(prospect.model_dump())
        return prospect

    @router.put("/prospection/prospects/{prospect_id}", response_model=Prospect)
    async def update_prospect(prospect_id: str, data: ProspectIn, _: dict = Depends(auth_dep)):
        update = {k: v for k, v in data.model_dump().items() if v is not None}
        res = await db.prospection_prospects.update_one({"id": prospect_id}, {"$set": update})
        if res.matched_count == 0:
            raise HTTPException(404, "Prospect introuvable")
        doc = await db.prospection_prospects.find_one({"id": prospect_id}, {"_id": 0})
        return Prospect(**doc)

    @router.delete("/prospection/prospects/{prospect_id}")
    async def delete_prospect(prospect_id: str, _: dict = Depends(auth_dep)):
        res = await db.prospection_prospects.delete_one({"id": prospect_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Prospect introuvable")
        return {"deleted": prospect_id}

    @router.post("/prospection/prospects/bulk", status_code=201)
    async def bulk_import(payload: ProspectBulkImport, _: dict = Depends(auth_dep)):
        created = 0
        for p in payload.prospects:
            prospect = Prospect(**p.model_dump())
            await db.prospection_prospects.insert_one(prospect.model_dump())
            created += 1
        return {"created": created}

    # =========================================================================
    # Deep-enrich existing prospects (web-search + crawl contact pages)
    # =========================================================================
    @router.post("/prospection/prospects/enrich")
    async def enrich(payload: EnrichRequest, _: dict = Depends(auth_dep)):
        # Build filter
        query: dict = {}
        if payload.prospect_ids:
            query["id"] = {"$in": payload.prospect_ids}
        if payload.only_missing_email:
            query["$or"] = [{"email": None}, {"email": ""}]
        cur = db.prospection_prospects.find(query, {"_id": 0}).limit(payload.max_to_process)
        prospects = [p async for p in cur]
        if not prospects:
            return {"processed": 0, "enriched": 0, "emails_found": 0, "websites_found": 0}

        emails_found = 0
        websites_found = 0
        enriched = 0
        for p in prospects:
            had_email = bool(p.get("email"))
            had_website = bool(p.get("website"))
            try:
                await enrich_prospect(p)
            except Exception as exc:
                logger.warning("enrich %s failed: %s", p.get("name"), exc)
                continue
            update = {}
            if not had_email and p.get("email"):
                update["email"] = p["email"]
                emails_found += 1
            if not had_website and p.get("website"):
                update["website"] = p["website"]
                websites_found += 1
            if p.get("phone") and not p.get("phone_original_match"):
                update["phone"] = p["phone"]
            if update:
                await db.prospection_prospects.update_one({"id": p["id"]}, {"$set": update})
                enriched += 1
        return {
            "processed": len(prospects),
            "enriched": enriched,
            "emails_found": emails_found,
            "websites_found": websites_found,
        }

    # =========================================================================
    # Scrape via OpenStreetMap (Overpass) — free, no API key
    # =========================================================================
    @router.post("/prospection/prospects/scrape")
    async def scrape(payload: ScrapeRequest, _: dict = Depends(auth_dep)):
        # Validate category
        if payload.category not in CATEGORIES:
            raise HTTPException(400, f"Catégorie inconnue : {payload.category}")
        # Map location to region key
        location_lc = payload.location.lower()
        region_key = "montreal"
        for key in REGIONS:
            if key in location_lc.replace("é", "e").replace("-", "").replace(" ", ""):
                region_key = key
                break
        # If "all" passed, scrape all regions
        try:
            if "tout" in location_lc or location_lc == "all":
                from prospection_scraper import scrape_all_regions
                raw = await scrape_all_regions(payload.max_results, payload.category, payload.deep_enrich)
            else:
                raw = await scrape_region(region_key, payload.max_results, payload.category, payload.deep_enrich)
        except Exception as exc:
            logger.error("Scrape failed: %s", exc)
            raise HTTPException(502, f"Source de données indisponible : {exc}")

        # Dedupe vs existing prospects (by name + city)
        new_count = 0
        skipped = 0
        for p in raw:
            existing = await db.prospection_prospects.find_one({
                "name": p["name"],
                "city": p.get("city"),
            })
            if existing:
                skipped += 1
                continue
            prospect = Prospect(**p)
            await db.prospection_prospects.insert_one(prospect.model_dump())
            new_count += 1

        return {
            "scraped": len(raw),
            "new": new_count,
            "skipped_duplicates": skipped,
            "region": region_key,
        }

    # =========================================================================
    # Campaigns CRUD
    # =========================================================================
    @router.get("/prospection/campaigns", response_model=List[Campaign])
    async def list_campaigns(_: dict = Depends(auth_dep)):
        cur = db.prospection_campaigns.find({}, {"_id": 0}).sort("created_at", -1)
        return [Campaign(**d) async for d in cur]

    @router.get("/prospection/campaigns/default")
    async def get_default_template(category: str = "vitrerie", _: dict = Depends(auth_dep)):
        """Return the pre-approved template for a given prospect category."""
        if category not in TEMPLATES:
            category = "vitrerie"
        tpl = TEMPLATES[category]
        return {
            "category": category,
            "subject": tpl["subject"],
            "from_name": FROM_NAME,
            "from_email": FROM_EMAIL,
            "body_html": _build_body_html(category),
        }

    @router.get("/prospection/categories")
    async def list_categories(_: dict = Depends(auth_dep)):
        """Return all available scrape categories with their labels."""
        return [
            {"key": k, "label": v["label"]}
            for k, v in CATEGORIES.items()
        ]

    @router.post("/prospection/campaigns", response_model=Campaign, status_code=201)
    async def create_campaign(data: CampaignIn, _: dict = Depends(auth_dep)):
        campaign = Campaign(**data.model_dump())
        await db.prospection_campaigns.insert_one(campaign.model_dump())
        return campaign

    @router.put("/prospection/campaigns/{campaign_id}", response_model=Campaign)
    async def update_campaign(campaign_id: str, data: CampaignIn, _: dict = Depends(auth_dep)):
        update = data.model_dump()
        update["updated_at"] = now_iso()
        res = await db.prospection_campaigns.update_one({"id": campaign_id}, {"$set": update})
        if res.matched_count == 0:
            raise HTTPException(404, "Campagne introuvable")
        doc = await db.prospection_campaigns.find_one({"id": campaign_id}, {"_id": 0})
        return Campaign(**doc)

    @router.delete("/prospection/campaigns/{campaign_id}")
    async def delete_campaign(campaign_id: str, _: dict = Depends(auth_dep)):
        res = await db.prospection_campaigns.delete_one({"id": campaign_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Campagne introuvable")
        return {"deleted": campaign_id}

    # =========================================================================
    # Send — explicit confirm + rate-limit
    # =========================================================================
    @router.post("/prospection/campaigns/send")
    async def send_campaign(payload: SendCampaignRequest, _: dict = Depends(auth_dep)):
        if not payload.confirm:
            raise HTTPException(
                400,
                "Confirmation explicite requise (case 'Je confirme l'envoi').",
            )

        campaign = await db.prospection_campaigns.find_one(
            {"id": payload.campaign_id}, {"_id": 0}
        )
        if not campaign:
            raise HTTPException(404, "Campagne introuvable")

        # Rate-limit guard
        sent_last_hour = await _count_sent_last_hour(db)
        remaining = max(0, HOURLY_SEND_LIMIT - sent_last_hour)
        if remaining <= 0 and not payload.test_only:
            raise HTTPException(
                429,
                f"Limite horaire atteinte ({HOURLY_SEND_LIMIT} envois/h). Réessayez plus tard.",
            )

        # Test mode: send a single preview email to test_email
        if payload.test_only:
            if not payload.test_email:
                raise HTTPException(400, "test_email requis quand test_only=true")
            return await _dispatch_test(campaign, payload.test_email)

        # Load prospects to send to
        prospects_cur = db.prospection_prospects.find(
            {"id": {"$in": payload.prospect_ids}, "unsubscribed": {"$ne": True}},
            {"_id": 0},
        )
        prospects = [p async for p in prospects_cur]
        if not prospects:
            raise HTTPException(400, "Aucun prospect valide à contacter")

        # Filter out prospects without email BEFORE applying the quota cap —
        # otherwise a batch where the first N have no email would silently
        # waste the remaining quota.
        with_email = [p for p in prospects if p.get("email")]
        skipped_no_email = len(prospects) - len(with_email)
        to_send = with_email[:remaining]
        sent_ok = 0
        sent_fail = 0
        outbox_entries: list[dict] = []

        for p in to_send:
            ok, resend_id, err = await _dispatch_one(campaign, p)
            entry = OutboxEntry(
                campaign_id=campaign["id"],
                prospect_id=p["id"],
                to_email=p["email"],
                resend_id=resend_id,
                status="sent" if ok else "failed",
            )
            outbox_entries.append(entry.model_dump() | ({"error": err} if err else {}))
            # Update prospect counters
            update = {
                "last_sent_at": now_iso(),
                "status": "envoyé" if ok else p.get("status", "nouveau"),
                "send_count": (p.get("send_count") or 0) + (1 if ok else 0),
            }
            await db.prospection_prospects.update_one({"id": p["id"]}, {"$set": update})
            if ok:
                sent_ok += 1
            else:
                sent_fail += 1

        if outbox_entries:
            await db.prospection_outbox.insert_many(outbox_entries)

        return {
            "sent": sent_ok,
            "failed": sent_fail,
            "skipped_no_email": skipped_no_email,
            "skipped_over_quota": max(0, len(with_email) - len(to_send)),
            "remaining_this_hour": max(0, remaining - sent_ok),
        }

    # =========================================================================
    # Outbox + stats
    # =========================================================================
    @router.get("/prospection/outbox")
    async def list_outbox(limit: int = 200, _: dict = Depends(auth_dep)):
        cur = db.prospection_outbox.find({}, {"_id": 0}).sort("sent_at", -1).limit(limit)
        return [d async for d in cur]

    @router.get("/prospection/stats")
    async def prospection_stats(_: dict = Depends(auth_dep)):
        total_prospects = await db.prospection_prospects.count_documents({})
        with_email = await db.prospection_prospects.count_documents(
            {"email": {"$nin": [None, ""]}}
        )
        sent_total = await db.prospection_outbox.count_documents({"status": "sent"})
        failed_total = await db.prospection_outbox.count_documents({"status": "failed"})
        sent_last_hour = await _count_sent_last_hour(db)
        today_cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        sent_today = await db.prospection_outbox.count_documents(
            {"sent_at": {"$gte": today_cutoff}, "status": "sent"}
        )
        by_status_cur = db.prospection_prospects.aggregate([
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ])
        by_status = {d["_id"]: d["count"] async for d in by_status_cur}
        return {
            "total_prospects": total_prospects,
            "with_email": with_email,
            "sent_total": sent_total,
            "failed_total": failed_total,
            "sent_today": sent_today,
            "sent_last_hour": sent_last_hour,
            "hourly_limit": HOURLY_SEND_LIMIT,
            "remaining_this_hour": max(0, HOURLY_SEND_LIMIT - sent_last_hour),
            "by_status": by_status,
        }


# ==========================================================================
# Resend helpers
# ==========================================================================
async def _dispatch_one(campaign: dict, prospect: dict) -> tuple[bool, Optional[str], Optional[str]]:
    if not resend.api_key:
        return False, None, "RESEND_API_KEY non configurée"
    try:
        html = _render_template(campaign["body_html"], prospect)
        # Rewrite banner URLs to inline CID references so the images embed in
        # the email itself (not loaded from portech.info, which may be blocked
        # by recipient mail gateways or not yet deployed).
        html = html.replace("https://portech.info/email/email-header.png", f"cid:{HEADER_CID}")
        html = html.replace("https://portech.info/email/email-footer.png", f"cid:{FOOTER_CID}")
        params: dict = {
            "from": f"{campaign.get('from_name', FROM_NAME)} <{campaign.get('from_email', FROM_EMAIL)}>",
            "to": [prospect["email"]],
            "subject": campaign["subject"],
            "html": html,
        }
        attachments = []
        if _BANNER_HEADER_B64:
            attachments.append({
                "filename": "email-header.png",
                "content": _BANNER_HEADER_B64,
                "content_id": HEADER_CID,
                "content_type": "image/png",
            })
        if _BANNER_FOOTER_B64:
            attachments.append({
                "filename": "email-footer.png",
                "content": _BANNER_FOOTER_B64,
                "content_id": FOOTER_CID,
                "content_type": "image/png",
            })
        if attachments:
            params["attachments"] = attachments
        result = await asyncio.to_thread(resend.Emails.send, params)
        return True, result.get("id"), None
    except Exception as exc:
        logger.error("Resend send failed for %s: %s", prospect.get("email"), exc)
        return False, None, str(exc)


async def _dispatch_test(campaign: dict, test_email: str) -> dict:
    fake_prospect = {
        "name": "Vitrerie Exemple Inc.",
        "contact_name": "Jean Tremblay",
        "city": "Montréal",
        "email": test_email,
    }
    ok, resend_id, err = await _dispatch_one(campaign, fake_prospect)
    return {
        "test": True,
        "sent": ok,
        "resend_id": resend_id,
        "error": err,
        "to": test_email,
    }
