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
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import resend
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from prospection_models import (
    Campaign,
    CampaignIn,
    OutboxEntry,
    Prospect,
    ProspectBulkImport,
    ProspectIn,
    ScrapeRequest,
    SendCampaignRequest,
    now_iso,
)
from prospection_scraper import REGIONS, scrape_region

logger = logging.getLogger("portech.prospection")

HOURLY_SEND_LIMIT = int(os.environ.get("PROSPECTION_HOURLY_LIMIT", "50"))
FROM_EMAIL = os.environ.get("PROSPECTION_FROM_EMAIL", os.environ.get("SENDER_EMAIL", "info@portech.info"))
FROM_NAME = os.environ.get("PROSPECTION_FROM_NAME", "Cédrick Pimparé · Portech")

# Default subcontracting email template (French, with header/footer banners)
DEFAULT_SUBJECT = "Sous-traitance quincaillerie pour vos projets vitrerie"
DEFAULT_BODY_HTML = """
<table width="100%" cellpadding="0" cellspacing="0" style="font-family: Arial, Helvetica, sans-serif; background:#f4f4f5; padding:0; margin:0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff; max-width:600px;">
      <tr><td><img src="https://portech.info/email/email-header.png" alt="Portech" style="display:block; width:100%; max-width:600px; height:auto; border:0;"/></td></tr>
      <tr><td style="padding:32px 32px 8px 32px; color:#0c182b; font-size:15px; line-height:1.6;">
        <p style="margin:0 0 16px 0;">Bonjour,</p>
        <p style="margin:0 0 16px 0;">Je m'appelle <b>Cédrick Pimparé</b>, je dirige <b>Portech</b> — un atelier spécialisé exclusivement dans la <b>quincaillerie de portes commerciales</b> (serrures, barres antipaniques, ferme-portes, charnières continues, contrôle d'accès) dans le Grand Montréal.</p>
        <p style="margin:0 0 16px 0;">Je m'adresse à vous parce que <b>les vitreries font régulièrement face au même casse-tête</b> : poser une devanture parfaite, puis devoir gérer une quincaillerie complexe (codes du bâtiment, compatibilité, ajustements millimétriques) qui n'est ni votre cœur de métier ni votre formation.</p>
        <p style="margin:0 0 16px 0;"><b>Ma proposition :</b> me sous-traiter cette portion. Je m'occupe uniquement de la quincaillerie sur vos chantiers — vous gardez le client, le contrat, la facturation. Je travaille en arrière-boutique, sans logo, sans véhicule identifié si vous le souhaitez.</p>
        <p style="margin:0 0 16px 0;"><b>Ce que ça vous donne :</b></p>
        <ul style="margin:0 0 16px 0; padding-left:20px;">
          <li>Quincaillerie posée du premier coup (10 ans en atelier)</li>
          <li>Conformité aux codes (NBC, NFPA 80, RBQ)</li>
          <li>Marge protégée — vous gardez la portion vitrerie, je m'occupe du reste</li>
          <li>Moins de retours, moins d'inspections échouées</li>
        </ul>
        <p style="margin:0 0 16px 0;">Si ça résonne, on peut prendre <b>15 minutes au téléphone</b> cette semaine pour voir si une collaboration ponctuelle ou continue a du sens pour vous.</p>
        <p style="margin:0 0 24px 0;">Au plaisir,<br/><b>Cédrick Pimparé</b><br/>Portech — Quincaillerie de portes commerciales<br/>📧 <a href="mailto:info@portech.info" style="color:#1d4ed8;">info@portech.info</a> · 🌐 <a href="https://portech.info" style="color:#1d4ed8;">portech.info</a></p>
      </td></tr>
      <tr><td><img src="https://portech.info/email/email-footer.png" alt="Portech" style="display:block; width:100%; max-width:600px; height:auto; border:0;"/></td></tr>
      <tr><td style="padding:16px 32px; color:#71717a; font-size:11px; text-align:center;">
        Vous recevez ce courriel parce que votre entreprise est référencée comme vitrerie dans le Grand Montréal.<br/>
        Pour ne plus recevoir de courriels de Portech, répondez simplement « RETIRER » à ce message.
      </td></tr>
    </table>
  </td></tr>
</table>
"""


def _render_template(html: str, prospect: dict) -> str:
    """Replace simple {{var}} placeholders in the HTML body."""
    out = html
    out = out.replace("{{name}}", prospect.get("name") or "")
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
        _: dict = Depends(auth_dep),
    ):
        query: dict = {}
        if region:
            query["region"] = region
        if status:
            query["status"] = status
        if has_email is True:
            query["email"] = {"$nin": [None, ""]}
        elif has_email is False:
            query["$or"] = [{"email": None}, {"email": ""}]
        cur = db.prospection_prospects.find(query, {"_id": 0}).sort("created_at", -1)
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
    # Scrape via OpenStreetMap (Overpass) — free, no API key
    # =========================================================================
    @router.post("/prospection/prospects/scrape")
    async def scrape(payload: ScrapeRequest, _: dict = Depends(auth_dep)):
        # Map "Montréal, QC" → region key. Simple heuristic.
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
                raw = await scrape_all_regions(payload.max_results)
            else:
                raw = await scrape_region(region_key, payload.max_results)
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
    async def get_default_template(_: dict = Depends(auth_dep)):
        """Return the pre-approved subcontracting template the admin can copy into a new campaign."""
        return {
            "subject": DEFAULT_SUBJECT,
            "from_name": FROM_NAME,
            "from_email": FROM_EMAIL,
            "body_html": DEFAULT_BODY_HTML,
        }

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

        # Truncate to remaining quota
        to_send = prospects[:remaining]
        skipped_no_email = 0
        sent_ok = 0
        sent_fail = 0
        outbox_entries: list[dict] = []

        for p in to_send:
            if not p.get("email"):
                skipped_no_email += 1
                continue
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
            "skipped_over_quota": max(0, len(prospects) - len(to_send)),
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
        params = {
            "from": f"{campaign.get('from_name', FROM_NAME)} <{campaign.get('from_email', FROM_EMAIL)}>",
            "to": [prospect["email"]],
            "subject": campaign["subject"],
            "html": html,
        }
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
