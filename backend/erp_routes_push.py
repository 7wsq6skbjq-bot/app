"""Routes API pour les notifications push (Web Push / VAPID)."""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

import push_notifications as push


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class Subscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    endpoint: str
    keys: PushKeys


class TestPush(BaseModel):
    title: str = Field(default="Portech", max_length=120)
    body: str = Field(default="Test de notification 🔔", max_length=500)


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    @router.get("/push/vapid-public-key")
    async def vapid_public_key(_: dict = Depends(auth_dep)):
        key = push.get_public_key()
        if not key:
            key = await push.ensure_vapid_keys(db)
        return {"publicKey": key}

    @router.post("/push/subscribe", status_code=201)
    async def subscribe(sub: Subscription, _: dict = Depends(auth_dep)):
        doc = sub.model_dump()
        from datetime import datetime, timezone
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.push_subscriptions.update_one(
            {"endpoint": sub.endpoint}, {"$set": doc}, upsert=True,
        )
        return {"ok": True}

    @router.post("/push/unsubscribe")
    async def unsubscribe(sub: Subscription, _: dict = Depends(auth_dep)):
        await db.push_subscriptions.delete_one({"endpoint": sub.endpoint})
        return {"ok": True}

    @router.post("/push/test")
    async def test_push(body: TestPush, _: dict = Depends(auth_dep)):
        return await push.send_push(db, title=body.title, body=body.body, tag="test")
