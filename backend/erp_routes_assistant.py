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
from erp_routes_statements import send_statement_email, unpaid_groups

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
ASSISTANT_MODEL = ("anthropic", "claude-sonnet-4-6")

ACTION_RE = re.compile(r"\[\[ACTION\]\]\s*(\{.*?\})", re.DOTALL)

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
    "    Étapes VALIDES (utilise EXACTEMENT une de ces valeurs pour stage) : "
    "a_approuver (À approuver), depot_recu (Dépôt reçu 50%), en_fabrication (En fabrication), "
    "pret (Prêt), livre (Livré), facture (Facturé), paye (Payé), annule (Annulé).\n"
    "RÈGLES STRICTES (sécurité) :\n"
    "  1. Pour les ENVOIS DE COURRIEL (send_statement, send_statement_all, send_quote_followup) : tu résumes "
    "D'ABORD ce qui sera envoyé et à qui, puis tu demandes une confirmation explicite « Confirmes-tu ? Réponds oui ». "
    "N'émets JAMAIS la directive à cette étape ; SEULEMENT après un « oui ».\n"
    "  2. Pour update_job_stage (réversible, sans courriel) : tu peux émettre la directive DIRECTEMENT dans le même "
    "message, après avoir reformulé clairement le changement (ex. « Je passe le job 12 à En fabrication »).\n"
    "  3. Format EXACT de la directive, seule sur sa ligne à la fin du message :\n"
    "     [[ACTION]] {\"type\":\"send_statement\",\"client\":\"Nom du client\"}\n"
    "     [[ACTION]] {\"type\":\"send_statement_all\"}\n"
    "     [[ACTION]] {\"type\":\"send_quote_followup\",\"quote\":\"SO-0007\"}\n"
    "     [[ACTION]] {\"type\":\"update_job_stage\",\"job\":\"12\",\"stage\":\"en_fabrication\"}\n"
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
        job = await db.erp_jobs.find_one({"number": n}, {"_id": 0})
        if not job:
            return f"⚠️ Job #{n} introuvable."
        stage = _resolve_stage(action.get("stage", ""))
        if not stage:
            return (f"⚠️ Étape « {action.get('stage','')} » non reconnue. "
                    f"Étapes possibles : {', '.join(JOB_STAGE_LABELS.values())}.")
        old = JOB_STAGE_LABELS.get(job.get("stage"), job.get("stage") or "—")
        await db.erp_jobs.update_one(
            {"id": job["id"]},
            {"$set": {"stage": stage, "updated_at": datetime.now(timezone.utc).isoformat()}})
        return (f"✅ Job #{n} « {job.get('title','')} » : étape changée de "
                f"{old} → {JOB_STAGE_LABELS[stage]}.")
    return "⚠️ Action inconnue."


def _money(v) -> str:
    return f"{float(v or 0):.2f} $"


async def _erp_snapshot(db) -> str:
    lines = []
    # Jobs by stage
    jobs = await db.erp_jobs.find({}, {"_id": 0}).to_list(500)
    active = [j for j in jobs if j.get("stage") != "annule"]
    by_stage = {}
    for j in active:
        by_stage[j.get("stage", "?")] = by_stage.get(j.get("stage", "?"), 0) + 1
    lines.append(f"JOBS actifs: {len(active)} — par étape: "
                 + ", ".join(f"{k}={v}" for k, v in by_stage.items()))
    for j in active[:20]:
        lines.append(f"  • Job {j.get('number','')} « {j.get('title','')} » "
                     f"[{j.get('stage','')}] client={j.get('client_name') or '—'} "
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
    return "\n".join(lines) if lines else "Aucune donnée ERP."


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    class ChatIn(BaseModel):
        message: str
        session_id: str | None = None

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
