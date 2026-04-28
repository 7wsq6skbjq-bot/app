"""Appointment (calendrier admin interne) CRUD routes."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_models import Appointment, AppointmentIn


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.get("/appointments", response_model=List[Appointment])
    async def list_appointments(
        start_from: Optional[str] = Query(None, description="ISO date — only return appointments with start >= this"),
        start_to: Optional[str] = Query(None, description="ISO date — only return appointments with start <= this"),
        _: dict = Depends(auth_dep),
    ):
        query: dict = {}
        if start_from or start_to:
            range_q: dict = {}
            if start_from:
                range_q["$gte"] = start_from
            if start_to:
                range_q["$lte"] = start_to
            query["start"] = range_q
        cur = db.erp_appointments.find(query, {"_id": 0}).sort("start", 1)
        return [Appointment(**d) async for d in cur]

    @router.post("/appointments", response_model=Appointment, status_code=201)
    async def create_appointment(data: AppointmentIn, _: dict = Depends(auth_dep)):
        appt = Appointment(**data.model_dump())
        await db.erp_appointments.insert_one(appt.model_dump())
        return appt

    @router.get("/appointments/{appt_id}", response_model=Appointment)
    async def get_appointment(appt_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_appointments.find_one({"id": appt_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Rendez-vous introuvable")
        return Appointment(**doc)

    @router.put("/appointments/{appt_id}", response_model=Appointment)
    async def update_appointment(appt_id: str, data: AppointmentIn, _: dict = Depends(auth_dep)):
        result = await db.erp_appointments.update_one(
            {"id": appt_id}, {"$set": data.model_dump()},
        )
        if result.matched_count == 0:
            raise HTTPException(404, "Rendez-vous introuvable")
        doc = await db.erp_appointments.find_one({"id": appt_id}, {"_id": 0})
        return Appointment(**doc)

    @router.delete("/appointments/{appt_id}")
    async def delete_appointment(appt_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_appointments.delete_one({"id": appt_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Rendez-vous introuvable")
        return {"deleted": appt_id}
