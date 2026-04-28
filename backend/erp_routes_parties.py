"""Party (customer/supplier) CRUD routes."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_models import Party, PartyIn


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.get("/parties", response_model=List[Party])
    async def list_parties(kind: Optional[str] = None, _: dict = Depends(auth_dep)):
        query = {}
        if kind:
            query["kind"] = kind
        cur = db.erp_parties.find(query, {"_id": 0}).sort("name", 1)
        return [Party(**d) async for d in cur]

    @router.post("/parties", response_model=Party, status_code=201)
    async def create_party(data: PartyIn, _: dict = Depends(auth_dep)):
        party = Party(**data.model_dump())
        await db.erp_parties.insert_one(party.model_dump())
        return party

    @router.get("/parties/{party_id}", response_model=Party)
    async def get_party(party_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_parties.find_one({"id": party_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Tier introuvable")
        return Party(**doc)

    @router.put("/parties/{party_id}", response_model=Party)
    async def update_party(party_id: str, data: PartyIn, _: dict = Depends(auth_dep)):
        result = await db.erp_parties.update_one(
            {"id": party_id}, {"$set": data.model_dump()}
        )
        if result.matched_count == 0:
            raise HTTPException(404, "Tier introuvable")
        doc = await db.erp_parties.find_one({"id": party_id}, {"_id": 0})
        return Party(**doc)

    @router.delete("/parties/{party_id}")
    async def delete_party(party_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_parties.delete_one({"id": party_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Tier introuvable")
        return {"deleted": party_id}
