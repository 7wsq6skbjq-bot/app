"""Assistante IA — French ERP chat assistant (Claude Sonnet 4.6 via Emergent key).

Non-streaming, multi-turn. Conversation history is stored in Mongo
(`erp_assistant_messages`) and replayed into the system prompt each turn so
answers stay coherent across requests. A compact live snapshot of the ERP
(jobs, unpaid invoices, pending quotes) is injected as context.
"""
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai import OpenAISpeechToText
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from erp_helpers import send_html_email
from erp_models import Party
from erp_routes_statements import send_statement_email, unpaid_groups

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
ASSISTANT_MODEL = ("anthropic", "claude-sonnet-4-6")

ACTION_RE = re.compile(r"\[\[ACTION\]\]\s*(\{.*?\})", re.DOTALL)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _num_from(raw, prefix=""):
    s = str(raw or "").upper().replace(prefix, "").replace("#", "").strip()
    try:
        return int(s.lstrip("0") or "0")
    except ValueError:
        return None

JOB_STAGE_LABELS = {
    "a_approuver": "À approuver", "depot_recu": "Dépôt reçu (50%)",
    "en_fabrication": "En fabrication", "pret": "Prêt", "livre": "Livré",
    "facture": "Facturé", "paye": "Payé", "annule": "Annulé",
}
# Keyword → stage key, to tolerate free-form phrasing from the LLM/user.
JOB_STAGE_KEYWORDS = [
    ("fabric", "en_fabrication"), ("installation", "en_fabrication"),
    ("approuv", "a_approuver"), ("depot", "depot_recu"), ("dépôt", "depot_recu"),
    ("acompte", "depot_recu"), ("pret", "pret"), ("prêt", "pret"),
    ("livr", "livre"), ("factur", "facture"), ("pay", "paye"),
    ("annul", "annule"),
]


# Set in register() (needs the job number generator). Called by _execute_action.
_create_job_fn = None


def _resolve_stage(raw: str):
    s = (raw or "").strip().lower()
    if s in JOB_STAGE_LABELS:
        return s
    for key, label in JOB_STAGE_LABELS.items():
        if s == label.lower():
            return key
    for kw, key in JOB_STAGE_KEYWORDS:
        if kw in s:
            return key
    return None

SYSTEM_BASE = (
    "Tu es l'assistante administrative virtuelle de Portech, une entreprise de "
    "quincaillerie et portes commerciales en aluminium au Québec. Tu réponds "
    "TOUJOURS en français, de façon professionnelle, concise et concrète. "
    "Tu aides Cédrick à suivre ses jobs, soumissions et factures, et tu peux "
    "rédiger des courriels ou des relances en français quand on te le demande. "
    "Base tes réponses sur les DONNÉES ERP fournies ci-dessous. Si l'information "
    "n'est pas dans les données, dis-le clairement au lieu d'inventer. "
    "Réponds en TEXTE SIMPLE, sans Markdown : n'utilise ni #, ni **, ni tableaux ; "
    "pour une liste, utilise des tirets simples (- ) en début de ligne.\n\n"
    "=== ENVOI D'ACTIONS (états de compte, relances) et GESTION DES JOBS ===\n"
    "Tu peux DÉCLENCHER de vraies actions. Actions possibles :\n"
    "  • send_statement — envoyer l'état de compte à UN client. Paramètre: client (nom exact du client).\n"
    "  • send_statement_all — envoyer l'état de compte à TOUS les clients ayant un solde dû.\n"
    "  • send_quote_followup — envoyer une relance pour UNE soumission. Paramètre: quote (numéro, ex. SO-0007).\n"
    "  • update_job_stage — changer l'étape d'un job. Paramètres: job (numéro du job) et stage.\n"
    "  • create_job — créer un NOUVEAU job. Paramètres: title (titre/description du travail, obligatoire) "
    "et client (nom du client, optionnel). Ex. « nouveau job porte arrière chez Clinique Laval » → "
    "title=\"Porte arrière\", client=\"Clinique Laval\".\n"
    "  • update_job — modifier un job existant. Paramètres: job (numéro) + un ou plusieurs de : "
    "target_date (date de livraison AU FORMAT ISO AAAA-MM-JJ), title, client, notes, total, deposit. "
    "Ex. « livraison vendredi pour le job 12 » → {job:\"12\", target_date:\"<date ISO du prochain vendredi>\"}.\n"
    "  • mark_invoice_paid — marquer une facture PAYÉE. Paramètre: invoice (numéro, ex. FAC-0007).\n"
    "  • update_quote_status — changer le statut d'une soumission. Paramètres: quote (SO-XXXX) et status "
    "(brouillon, envoyée, acceptée, refusée, expirée, annulée).\n"
    "  • create_client — créer un client. Paramètres: name (obligatoire), email, phone, city, address (optionnels).\n"
    "  • reply_lead — répondre par courriel à un lead du site. Paramètres: lead (courriel ou nom) et message (texte de la réponse). ENVOI DE COURRIEL → demande confirmation d'abord.\n"
    "  • mark_lead_done — marquer un lead « traité ». Paramètre: lead (courriel ou nom).\n"
    "  • create_appointment — ajouter un rendez-vous au Google Calendar. Paramètres: title, start "
    "(date-heure ISO, ex. 2026-06-19T14:00:00), end (optionnel), location, notes. Convertis « demain 14h » en ISO.\n"
    "IMPORTANT dates : convertis TOUJOURS les dates parlées (« vendredi », « demain », « le 15 ») en "
    "format ISO AAAA-MM-JJ en te basant sur la date d'aujourd'hui donnée dans les DONNÉES ERP.\n"
    "    Étapes VALIDES (utilise EXACTEMENT une de ces valeurs pour stage) : "
    "a_approuver (À approuver), depot_recu (Dépôt reçu 50%), en_fabrication (En fabrication), "
    "pret (Prêt), livre (Livré), facture (Facturé), paye (Payé), annule (Annulé).\n"
    "RÈGLES STRICTES (sécurité) :\n"
    "  1. Pour les ENVOIS DE COURRIEL (send_statement, send_statement_all, send_quote_followup) : tu résumes "
    "D'ABORD ce qui sera envoyé et à qui, puis tu demandes une confirmation explicite « Confirmes-tu ? Réponds oui ». "
    "N'émets JAMAIS la directive à cette étape ; SEULEMENT après un « oui ».\n"
    "  2. Pour update_job_stage, create_job, update_job, mark_invoice_paid, update_quote_status, create_client "
    "et mark_lead_done (réversibles, sans courriel) : tu peux émettre la directive DIRECTEMENT dans le même message, "
    "après avoir reformulé clairement l'action. Pour reply_lead (envoi de courriel), demande confirmation D'ABORD. "
    "create_appointment peut être émis directement.\n"
    "  3. Format EXACT de la directive, seule sur sa ligne à la fin du message :\n"
    "     [[ACTION]] {\"type\":\"send_statement\",\"client\":\"Nom du client\"}\n"
    "     [[ACTION]] {\"type\":\"send_statement_all\"}\n"
    "     [[ACTION]] {\"type\":\"send_quote_followup\",\"quote\":\"SO-0007\"}\n"
    "     [[ACTION]] {\"type\":\"update_job_stage\",\"job\":\"12\",\"stage\":\"en_fabrication\"}\n"
    "     [[ACTION]] {\"type\":\"create_job\",\"title\":\"Porte arrière\",\"client\":\"Clinique Laval\"}\n"
    "     [[ACTION]] {\"type\":\"update_job\",\"job\":\"12\",\"target_date\":\"2026-06-19\"}\n"
    "     [[ACTION]] {\"type\":\"mark_invoice_paid\",\"invoice\":\"FAC-0007\"}\n"
    "     [[ACTION]] {\"type\":\"update_quote_status\",\"quote\":\"SO-0007\",\"status\":\"acceptée\"}\n"
    "     [[ACTION]] {\"type\":\"create_client\",\"name\":\"Clinique Laval\",\"email\":\"info@x.ca\"}\n"
    "  4. Utilise EXACTEMENT les noms de clients et numéros présents dans les DONNÉES ERP. "
    "Le système exécute l'action et te confirme le résultat — n'invente jamais de confirmation toi-même."
)


async def _find_statement_group(db, client: str):
    groups = await unpaid_groups(db)
    c = (client or "").strip().lower()
    if not c:
        return None
    for g in groups.values():
        name = (g.get("name") or "").lower()
        email = (g.get("email") or "").lower()
        if c == email or c in name or name in c:
            return g
    return None


async def _execute_action(db, action: dict) -> str:
    t = action.get("type")
    if t == "send_statement":
        g = await _find_statement_group(db, action.get("client", ""))
        if not g:
            return f"⚠️ Aucun client « {action.get('client','')} » avec un solde dû n'a été trouvé."
        if not g.get("email"):
            return f"⚠️ {g['name']} n'a pas de courriel enregistré — envoi impossible."
        await send_statement_email(g, g["email"])
        return f"✅ État de compte envoyé à {g['name']} ({g['email']}) — solde dû {g['balance']:.2f} $ CAD."
    if t == "send_statement_all":
        groups = await unpaid_groups(db)
        sent, skipped = 0, 0
        for g in groups.values():
            if g.get("email"):
                try:
                    await send_statement_email(g, g["email"])
                    sent += 1
                except Exception:  # noqa: BLE001
                    skipped += 1
            else:
                skipped += 1
        return f"✅ {sent} état(s) de compte envoyé(s)." + (f" {skipped} ignoré(s) (sans courriel)." if skipped else "")
    if t == "send_quote_followup":
        raw = str(action.get("quote", "")).upper().replace("SO-", "").strip()
        try:
            n = int(raw.lstrip("0") or "0")
        except ValueError:
            return "⚠️ Numéro de soumission invalide."
        q = await db.erp_quotes.find_one({"number": n}, {"_id": 0})
        if not q:
            return f"⚠️ Soumission SO-{n:04d} introuvable."
        snap = q.get("customer_snapshot") or {}
        email = (snap.get("email") or "").strip()
        if not email:
            return f"⚠️ La soumission SO-{n:04d} n'a pas de courriel client."
        html = (
            f"<p>Bonjour {snap.get('name') or ''},</p>"
            f"<p>Nous faisons un suivi concernant notre soumission <b>SO-{n:04d}</b> "
            f"(total estimé {float(q.get('total') or 0):.2f} $ CAD). "
            "Avez-vous des questions ou souhaitez-vous aller de l'avant ?</p>"
            "<p>Il suffit de répondre à ce courriel — nous restons disponibles.</p>"
            "<p>Cordialement,<br/>L'équipe Portech</p>"
        )
        await send_html_email(to_email=email, subject=f"Portech — Suivi de votre soumission SO-{n:04d}",
                              html=html, footer_note=f"Relance soumission SO-{n:04d}")
        await db.erp_quotes.update_one({"id": q["id"]},
                                       {"$set": {"followup_sent_at": datetime.now(timezone.utc).isoformat()}})
        return f"✅ Relance envoyée à {snap.get('name','')} ({email}) pour SO-{n:04d}."
    if t == "update_job_stage":
        raw = str(action.get("job", "")).upper().replace("JOB", "").replace("#", "").strip()
        try:
            n = int(raw.lstrip("0") or "0")
        except ValueError:
            return "⚠️ Numéro de job invalide."
        job_number = f"JOB-{n:04d}"
        job = await db.erp_jobs.find_one(
            {"$or": [{"job_number": job_number}, {"number": n}]}, {"_id": 0})
        if not job:
            return f"⚠️ Job {job_number} introuvable."
        stage = _resolve_stage(action.get("stage", ""))
        if not stage:
            return (f"⚠️ Étape « {action.get('stage','')} » non reconnue. "
                    f"Étapes possibles : {', '.join(JOB_STAGE_LABELS.values())}.")
        old = JOB_STAGE_LABELS.get(job.get("stage"), job.get("stage") or "—")
        await db.erp_jobs.update_one(
            {"id": job["id"]},
            {"$set": {"stage": stage, "updated_at": datetime.now(timezone.utc).isoformat()}})
        return (f"✅ {job.get('job_number', job_number)} « {job.get('title','')} » : étape changée de "
                f"{old} → {JOB_STAGE_LABELS[stage]}.")
    if t == "create_job":
        title = (action.get("title") or "").strip()
        if not title:
            return "⚠️ Il me faut un titre pour créer le job."
        if _create_job_fn is None:
            return "⚠️ Création de job indisponible."
        job = await _create_job_fn(db, title=title, client_name=(action.get("client") or "").strip())
        return (f"✅ Nouveau job créé : {job['job_number']} « {job['title']} »"
                + (f" pour {job['client_name']}" if job.get("client_name") else "")
                + f" (étape : {JOB_STAGE_LABELS.get(job['stage'], job['stage'])}).")
    if t == "update_job":
        n = _num_from(action.get("job"), "JOB-")
        if n is None:
            return "⚠️ Numéro de job invalide."
        job = await db.erp_jobs.find_one(
            {"$or": [{"job_number": f"JOB-{n:04d}"}, {"number": n}]}, {"_id": 0})
        if not job:
            return f"⚠️ Job JOB-{n:04d} introuvable."
        upd, changes = {}, []
        if action.get("target_date"):
            d = str(action["target_date"]).strip()
            if not ISO_DATE_RE.match(d):
                return "⚠️ Date invalide (format attendu AAAA-MM-JJ)."
            upd["target_date"] = d
            changes.append(f"livraison au {d}")
        if action.get("title"):
            upd["title"] = str(action["title"]).strip()
            changes.append("titre")
        if action.get("client") is not None:
            upd["client_name"] = str(action["client"]).strip()
            changes.append(f"client {upd['client_name']}")
        if action.get("notes") is not None:
            upd["notes"] = str(action["notes"])
            changes.append("notes")
        for k in ("total", "deposit"):
            if action.get(k) is not None:
                try:
                    val = float(str(action[k]).replace("$", "").replace(",", ".").strip())
                except ValueError:
                    return f"⚠️ Montant « {action[k]} » invalide."
                upd["deposit_expected" if k == "deposit" else "total"] = val
                changes.append(f"{k} {val:.2f} $")
        if not upd:
            return "⚠️ Rien à modifier — précise la date, le titre, le client, etc."
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.erp_jobs.update_one({"id": job["id"]}, {"$set": upd})
        return f"✅ {job.get('job_number', f'JOB-{n:04d}')} mis à jour : {', '.join(changes)}."
    if t == "mark_invoice_paid":
        n = _num_from(action.get("invoice"), "FAC-")
        if n is None:
            return "⚠️ Numéro de facture invalide."
        inv = await db.erp_invoices.find_one({"number": n}, {"_id": 0})
        if not inv:
            return f"⚠️ Facture FAC-{n:04d} introuvable."
        await db.erp_invoices.update_one(
            {"id": inv["id"]},
            {"$set": {"status": "payée", "updated_at": datetime.now(timezone.utc).isoformat()}})
        cs = inv.get("customer_snapshot") or {}
        return f"✅ Facture FAC-{n:04d} ({cs.get('name','')}, {float(inv.get('total') or 0):.2f} $) marquée PAYÉE."
    if t == "update_quote_status":
        n = _num_from(action.get("quote"), "SO-")
        if n is None:
            return "⚠️ Numéro de soumission invalide."
        q = await db.erp_quotes.find_one({"number": n}, {"_id": 0})
        if not q:
            return f"⚠️ Soumission SO-{n:04d} introuvable."
        raw = str(action.get("status", "")).strip().lower()
        smap = {"accepté": "acceptée", "acceptee": "acceptée", "acceptée": "acceptée",
                "refusé": "refusée", "refusee": "refusée", "refusée": "refusée",
                "envoyé": "envoyée", "envoye": "envoyée", "envoyée": "envoyée",
                "brouillon": "brouillon", "expiré": "expirée", "expiree": "expirée",
                "expirée": "expirée", "annulé": "annulée", "annulee": "annulée", "annulée": "annulée"}
        status = smap.get(raw)
        if not status:
            return "⚠️ Statut inconnu (brouillon, envoyée, acceptée, refusée, expirée, annulée)."
        await db.erp_quotes.update_one(
            {"id": q["id"]},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}})
        return f"✅ Soumission SO-{n:04d} : statut → {status}."
    if t == "create_client":
        name = (action.get("name") or "").strip()
        if not name:
            return "⚠️ Il me faut au moins le nom du client."
        party = Party(
            kind="customer", name=name,
            email=(action.get("email") or None),
            phone=(action.get("phone") or None),
            address_line1=(action.get("address") or None),
            city=(action.get("city") or None),
        )
        await db.erp_parties.insert_one(party.model_dump())
        extra = ", ".join(x for x in [party.email, party.phone, party.city] if x)
        return f"✅ Client créé : {name}" + (f" ({extra})" if extra else "") + "."
    if t in ("reply_lead", "mark_lead_done"):
        who = (action.get("lead") or "").strip().lower()
        if not who:
            return "⚠️ Précise le lead (courriel ou nom)."
        leads = await db.contact_submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
        lead = next((l for l in leads if who == (l.get("email") or "").lower()
                     or who in (l.get("name") or "").lower()), None)
        if not lead:
            return f"⚠️ Aucun lead « {action.get('lead')} » trouvé."
        if t == "mark_lead_done":
            await db.contact_submissions.update_one(
                {"id": lead["id"]},
                {"$set": {"assistant_status": "traité", "handled_at": datetime.now(timezone.utc).isoformat()}})
            return f"✅ Lead de {lead.get('name','')} marqué « traité »."
        # reply_lead — send an email to the lead
        to_email = (lead.get("email") or "").strip()
        if not to_email:
            return f"⚠️ Le lead {lead.get('name','')} n'a pas de courriel."
        body = (action.get("message") or "").strip()
        if not body:
            return "⚠️ Il me faut le texte de la réponse à envoyer."
        html = "".join(f"<p>{p}</p>" for p in body.split("\n") if p.strip()) + \
               "<p>Cordialement,<br/>L'équipe Portech</p>"
        await send_html_email(to_email=to_email, subject="Portech — Réponse à votre demande",
                              html=html, footer_note="Réponse à un lead")
        await db.contact_submissions.update_one(
            {"id": lead["id"]},
            {"$set": {"assistant_status": "traité", "handled_at": datetime.now(timezone.utc).isoformat()}})
        return f"✅ Réponse envoyée à {lead.get('name','')} ({to_email}) et lead marqué « traité »."
    if t == "create_appointment":
        import google_calendar as gcal
        if not await gcal.is_connected(db):
            return "⚠️ Google Calendar n'est pas encore connecté. Touche « Connecter Google Calendar » dans l'app."
        title = (action.get("title") or "").strip()
        start = (action.get("start") or "").strip()
        if not title or not start:
            return "⚠️ Il me faut un titre et une date/heure de début (ISO)."
        try:
            ev = await gcal.create_event(
                db, title=title, start=start, end=(action.get("end") or None),
                location=(action.get("location") or None), notes=(action.get("notes") or None))
        except Exception as exc:  # noqa: BLE001
            return f"⚠️ Échec de la création du rendez-vous : {exc}"
        try:
            import push_notifications as push
            await push.send_push(db, title="Nouveau rendez-vous 📅",
                                  body=f"{title} · {start}", url="/adjointe", tag="rdv")
        except Exception:  # noqa: BLE001
            pass
        return f"✅ Rendez-vous ajouté à Google Calendar : « {title} » le {start}."
    return "⚠️ Action inconnue."


def _money(v) -> str:
    return f"{float(v or 0):.2f} $"


async def _erp_snapshot(db) -> str:
    _JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    _now = datetime.now(timezone.utc)
    lines = [f"Date d'aujourd'hui : {_now.date().isoformat()} ({_JOURS[_now.weekday()]})."]
    # Jobs by stage
    jobs = await db.erp_jobs.find({}, {"_id": 0}).to_list(500)
    active = [j for j in jobs if j.get("stage") != "annule"]
    by_stage = {}
    for j in active:
        by_stage[j.get("stage", "?")] = by_stage.get(j.get("stage", "?"), 0) + 1
    lines.append(f"JOBS actifs: {len(active)} — par étape: "
                 + ", ".join(f"{k}={v}" for k, v in by_stage.items()))
    for j in active[:20]:
        lines.append(f"  • {j.get('job_number','JOB-?')} « {j.get('title','')} » "
                     f"[{JOB_STAGE_LABELS.get(j.get('stage'), j.get('stage',''))}] "
                     f"client={j.get('client_name') or '—'} "
                     f"échéance={j.get('target_date') or '—'}")
    # Unpaid invoices
    inv = await db.erp_invoices.find({"status": "envoyée"}, {"_id": 0}).sort("number", 1).to_list(200)
    bal = sum(float(i.get("total") or 0) for i in inv)
    lines.append(f"FACTURES impayées (envoyées): {len(inv)} — solde total {_money(bal)}")
    for i in inv[:20]:
        cs = i.get("customer_snapshot") or {}
        lines.append(f"  • FAC-{int(i.get('number',0)):04d} {cs.get('name','')} "
                     f"{_money(i.get('total'))} échéance={i.get('due_date') or '—'}")
    # Pending quotes
    q = await db.erp_quotes.find({"status": {"$in": ["brouillon", "envoyée"]}}, {"_id": 0}).sort("number", 1).to_list(200)
    lines.append(f"SOUMISSIONS en cours: {len(q)}")
    for x in q[:20]:
        cs = x.get("customer_snapshot") or {}
        lines.append(f"  • SO-{int(x.get('number',0)):04d} {cs.get('name','')} "
                     f"{_money(x.get('total'))} [{x.get('status','')}]")
    # Recent website leads (contact submissions)
    leads = await db.contact_submissions.find({}, {"_id": 0}).sort("created_at", -1).to_list(15)
    new_leads = [l for l in leads if l.get("assistant_status") != "traité"]
    lines.append(f"LEADS du site (demandes de soumission) : {len(new_leads)} non traité(s) sur {len(leads)} récents")
    for l in new_leads[:10]:
        msg = (l.get("message") or "").replace("\n", " ")[:80]
        lines.append(f"  • {l.get('name','?')} <{l.get('email','')}> "
                     f"{('· ' + l.get('phone')) if l.get('phone') else ''} — « {msg} »")
    # Upcoming Google Calendar events
    try:
        import google_calendar as gcal
        if await gcal.is_connected(db):
            evs = await gcal.list_upcoming(db, 8)
            lines.append(f"CALENDRIER (prochains rendez-vous Google) : {len(evs)}")
            for e in evs:
                st = (e.get("start") or {}).get("dateTime") or (e.get("start") or {}).get("date") or "?"
                lines.append(f"  • {st} — {e.get('summary','(sans titre)')}"
                             + (f" @ {e.get('location')}" if e.get("location") else ""))
        else:
            lines.append("CALENDRIER : Google Calendar non connecté.")
    except Exception:
        pass
    return "\n".join(lines) if lines else "Aucune donnée ERP."


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep, next_number) -> None:

    async def _make_job(_db, *, title: str, client_name: str = "") -> dict:
        n = await next_number("job")
        now = datetime.now(timezone.utc).isoformat()
        job = {
            "id": uuid.uuid4().hex,
            "job_number": f"JOB-{n:04d}",
            "title": title,
            "client_name": client_name or "",
            "client_email": None, "party_id": None,
            "stage": "a_approuver", "total": 0.0, "deposit_expected": 0.0,
            "priority": "normal", "target_date": None, "notes": "",
            "links": [], "history": [{"stage": "a_approuver", "at": now, "note": "Job créée par l'assistante"}],
            "created_at": now, "updated_at": now,
        }
        await _db.erp_jobs.insert_one(dict(job))
        return job

    global _create_job_fn
    _create_job_fn = _make_job

    class ChatIn(BaseModel):
        message: str
        session_id: str | None = None

    @router.get("/assistant/briefing")
    async def briefing(_: dict = Depends(auth_dep)):
        """Résumé du matin (texte simple, pour lecture à voix haute) : factures dues + jobs du jour."""
        today = datetime.now(timezone.utc).date().isoformat()
        parts = [f"Bonjour Cédrick, voici ton résumé du {datetime.now(timezone.utc).strftime('%d/%m/%Y')}."]
        # Unpaid invoices
        inv = await db.erp_invoices.find({"status": "envoyée"}, {"_id": 0}).sort("number", 1).to_list(200)
        bal = sum(float(i.get("total") or 0) for i in inv)
        if inv:
            parts.append(f"Tu as {len(inv)} facture(s) impayée(s) pour un solde total de {bal:.2f} $.")
            for i in inv[:6]:
                cs = i.get("customer_snapshot") or {}
                over = " (en retard)" if (i.get("due_date") and i["due_date"] < today) else ""
                parts.append(f"- FAC-{int(i.get('number',0)):04d}, {cs.get('name','')}, {float(i.get('total') or 0):.2f} ${over}.")
        else:
            parts.append("Aucune facture impayée. Bravo !")
        # Jobs: active + due today/overdue
        jobs = await db.erp_jobs.find({}, {"_id": 0}).to_list(500)
        active = [j for j in jobs if j.get("stage") not in ("annule", "paye", "livre", "facture")]
        due = [j for j in active if j.get("target_date") and j["target_date"] <= today]
        parts.append(f"Côté jobs : {len(active)} job(s) actif(s).")
        if due:
            parts.append(f"{len(due)} job(s) à livrer aujourd'hui ou en retard :")
            for j in due[:6]:
                parts.append(f"- {j.get('job_number','')}, {j.get('title','')}, {j.get('client_name') or 'client ?'}.")
        else:
            parts.append("Aucun job à livrer aujourd'hui.")
        return {"text": "\n".join(parts), "date": today}

    @router.get("/assistant/history")
    async def history(session_id: str, _: dict = Depends(auth_dep)):
        msgs = await db.erp_assistant_messages.find(
            {"session_id": session_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
        return {"session_id": session_id, "messages": msgs}

    ALLOWED_AUDIO = {".webm", ".mp3", ".mp4", ".m4a", ".wav", ".mpeg", ".mpga", ".ogg"}

    @router.post("/assistant/transcribe")
    async def transcribe(file: UploadFile = File(...), _: dict = Depends(auth_dep)):
        """Dictée vocale → texte (Whisper). Returns {text}."""
        if not EMERGENT_LLM_KEY:
            raise HTTPException(503, "EMERGENT_LLM_KEY non configurée.")
        ext = os.path.splitext(file.filename or "")[1].lower() or ".webm"
        if ext not in ALLOWED_AUDIO:
            ext = ".webm"
        raw = await file.read(25 * 1024 * 1024 + 1)
        if len(raw) > 25 * 1024 * 1024:
            raise HTTPException(413, "Audio trop volumineux (max 25 MB).")
        stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        tf = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        try:
            tf.write(raw)
            tf.close()
            with open(tf.name, "rb") as audio_file:
                resp = await stt.transcribe(file=audio_file, model="whisper-1",
                                            language="fr", response_format="json")
            text = resp.text if hasattr(resp, "text") else str(resp)
            return {"text": (text or "").strip()}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"Échec de la transcription : {exc}")
        finally:
            try:
                os.unlink(tf.name)
            except OSError:
                pass

    @router.delete("/assistant/history")
    async def clear_history(session_id: str, _: dict = Depends(auth_dep)):
        await db.erp_assistant_messages.delete_many({"session_id": session_id})
        return {"cleared": True}

    @router.post("/assistant/chat")
    async def chat(payload: ChatIn, _: dict = Depends(auth_dep)):
        if not EMERGENT_LLM_KEY:
            raise HTTPException(503, "EMERGENT_LLM_KEY non configurée — assistant indisponible.")
        text = (payload.message or "").strip()
        if not text:
            raise HTTPException(400, "Message vide")
        session_id = payload.session_id or uuid.uuid4().hex

        # Replay recent conversation into the system prompt for continuity.
        prior = await db.erp_assistant_messages.find(
            {"session_id": session_id}, {"_id": 0}).sort("created_at", 1).to_list(30)
        transcript = "\n".join(
            f"{'Cédrick' if m['role'] == 'user' else 'Assistante'}: {m['content']}"
            for m in prior[-12:]
        )
        snapshot = await _erp_snapshot(db)
        system_message = (
            f"{SYSTEM_BASE}\n\n=== DONNÉES ERP (à jour) ===\n{snapshot}\n"
            + (f"\n=== CONVERSATION RÉCENTE ===\n{transcript}\n" if transcript else "")
        )

        chat_client = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_message,
        ).with_model(*ASSISTANT_MODEL)

        try:
            reply = await chat_client.send_message(UserMessage(text=text))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(502, f"Échec de l'assistant : {exc}")
        reply = reply if isinstance(reply, str) else str(reply)

        # Detect + execute an action directive, strip it from the visible reply.
        action_result = None
        m = ACTION_RE.search(reply)
        if m:
            reply = ACTION_RE.sub("", reply).strip()
            try:
                action = json.loads(m.group(1))
                action_result = await _execute_action(db, action)
            except json.JSONDecodeError:
                action_result = "⚠️ Directive d'action illisible — aucun envoi effectué."
            except Exception as exc:  # noqa: BLE001
                action_result = f"⚠️ Échec de l'envoi : {exc}"
        if action_result:
            reply = (reply + "\n\n" + action_result).strip() if reply else action_result

        now = datetime.now(timezone.utc).isoformat()
        await db.erp_assistant_messages.insert_many([
            {"session_id": session_id, "role": "user", "content": text, "created_at": now},
            {"session_id": session_id, "role": "assistant", "content": reply, "created_at": now},
        ])
        return {"session_id": session_id, "reply": reply, "action_result": action_result}
