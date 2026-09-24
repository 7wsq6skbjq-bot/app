"""Assistante IA — French ERP chat assistant (Claude Sonnet 4.6 via Emergent key).

Non-streaming, multi-turn. Conversation history is stored in Mongo
(`erp_assistant_messages`) and replayed into the system prompt each turn so
answers stay coherent across requests. A compact live snapshot of the ERP
(jobs, unpaid invoices, pending quotes) is injected as context.
"""
import os
import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
ASSISTANT_MODEL = ("anthropic", "claude-sonnet-4-6")

SYSTEM_BASE = (
    "Tu es l'assistante administrative virtuelle de Portech, une entreprise de "
    "quincaillerie et portes commerciales en aluminium au Québec. Tu réponds "
    "TOUJOURS en français, de façon professionnelle, concise et concrète. "
    "Tu aides Cédrick à suivre ses jobs, soumissions et factures, et tu peux "
    "rédiger des courriels ou des relances en français quand on te le demande. "
    "Base tes réponses sur les DONNÉES ERP fournies ci-dessous. Si l'information "
    "n'est pas dans les données, dis-le clairement au lieu d'inventer."
)


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

        now = datetime.now(timezone.utc).isoformat()
        await db.erp_assistant_messages.insert_many([
            {"session_id": session_id, "role": "user", "content": text, "created_at": now},
            {"session_id": session_id, "role": "assistant", "content": reply, "created_at": now},
        ])
        return {"session_id": session_id, "reply": reply}
