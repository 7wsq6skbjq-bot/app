"""Production drawings (Dessins de production) — CRUD + PDF.

Lets Cédrick generate a full, branded, multi-page production-drawing PDF
just by filling a template : project info, client, and a list of doors
(dimensions, series, config, finishes, glass, hardware). The elevation is
drawn to scale from the opening dimensions; standard plan / section / anchor
detail pages are appended per series.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date as DateT, datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from erp_helpers import csv_response
from erp_pdf_production import render_production_plan_pdf


DoorSeries = Literal["AT1000", "ATi1000", "AT2000", "ATi2000"]
DoorConfig = Literal["simple", "pair"]
PlanStatus = Literal["brouillon", "en production", "en hold", "produit", "annulé"]


class HardwareLine(BaseModel):
    qty: str = "1"
    description: str = ""
    part_number: str = ""
    note: str = ""
    on_active: bool = False
    on_inactive: bool = False


class DoorPlan(BaseModel):
    tag: str = Field("", max_length=60)                 # ex : P-104
    series: DoorSeries = "AT1000"
    config: DoorConfig = "simple"
    opening_width_in: float = Field(36, ge=1)
    opening_height_in: float = Field(84, ge=1)
    qty: int = Field(1, ge=1)
    handing: Literal["MG", "MD", "MGR", "MDR"] = "MD"
    active_leaf: Literal["left", "right"] = "right"
    fab_width_in: float = 0
    fab_height_in: float = 0
    handle_height_in: float = 34.5
    handle_length_in: float = 9
    handle_both: bool = False
    lock_height_in: float = 40
    undercut_mm: float = 17.5
    finish_ext: str = ""
    finish_int: str = ""
    glass: str = ""
    hinges: str = ""
    hinge_type: Literal["butt45", "continue", "none"] = "butt45"
    profile_head: str = ""
    profile_base: str = ""
    profile_hinge_stile: str = ""
    profile_lock_stile: str = ""
    scale_note: str = "1:30"
    hardware: List[HardwareLine] = Field(default_factory=list)
    notes: str = ""


class ProductionPlanIn(BaseModel):
    project_name: str = Field("", max_length=120)
    project_number: str = Field("", max_length=40)
    production_name: str = ""
    production_note: str = ""
    revision: str = "no00"
    date: DateT = Field(default_factory=DateT.today)
    client_name: str = ""
    client_address: str = ""
    client_contact: str = ""
    client_phone: str = ""
    machining_by: str = "A.T. Fabrication"
    installer: str = "Portech"
    include_plan_details: bool = True
    include_section_details: bool = True
    include_anchors: bool = True
    status: PlanStatus = "brouillon"
    doors: List[DoorPlan] = Field(default_factory=list)
    notes: str = ""


class ProductionPlan(ProductionPlanIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_number: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _format_number(year: int, seq: int) -> str:
    return f"PLAN-{year}-{seq:03d}"


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    async def _next_number() -> str:
        year = datetime.now(timezone.utc).year
        counter = await db.erp_counters.find_one_and_update(
            {"key": f"production_plan_{year}"},
            {"$inc": {"seq": 1}},
            upsert=True, return_document=True,
        )
        return _format_number(year, counter.get("seq") or 1)

    @router.get("/production-plans/profile-catalog")
    async def profile_catalog(_: dict = Depends(auth_dep)):
        """Aluminium profile options (per element) + per-series defaults."""
        from at_profile_library import PROFILES
        from erp_pdf_production import SERIES_DEFAULT_PROFILES

        def opt(code):
            p = PROFILES[code]
            return {"code": code, "label": p["label"],
                    "face_mm": round(p["face_w"], 1),
                    "face_in": round(p["face_w"] / 25.4, 3)}

        return {
            "heads": [opt(k) for k in ("ATT1005", "ATB1000")],
            "bases": [opt(k) for k in ("ATB1000", "ATB2000")],
            "stiles": [opt(k) for k in ("ATV1010", "ATV1015", "ATV2010", "ATV2015")],
            "defaults": SERIES_DEFAULT_PROFILES,
        }

    @router.get("/production-plans", response_model=List[ProductionPlan])
    async def list_plans(_: dict = Depends(auth_dep)):
        cur = db.erp_production_plans.find({}, {"_id": 0}).sort("created_at", -1)
        return [ProductionPlan(**d) async for d in cur]

    @router.post("/production-plans", response_model=ProductionPlan, status_code=201)
    async def create_plan(data: ProductionPlanIn, _: dict = Depends(auth_dep)):
        plan = ProductionPlan(**data.model_dump(), plan_number=await _next_number())
        await db.erp_production_plans.insert_one(plan.model_dump(mode="json"))
        return plan

    @router.get("/production-plans/{plan_id}", response_model=ProductionPlan)
    async def get_plan(plan_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_production_plans.find_one({"id": plan_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Plan introuvable")
        return ProductionPlan(**doc)

    @router.put("/production-plans/{plan_id}", response_model=ProductionPlan)
    async def update_plan(plan_id: str, data: ProductionPlanIn,
                          _: dict = Depends(auth_dep)):
        existing = await db.erp_production_plans.find_one({"id": plan_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Plan introuvable")
        await db.erp_production_plans.update_one(
            {"id": plan_id}, {"$set": data.model_dump(mode="json")},
        )
        doc = await db.erp_production_plans.find_one({"id": plan_id}, {"_id": 0})
        return ProductionPlan(**doc)

    @router.delete("/production-plans/{plan_id}", status_code=204)
    async def delete_plan(plan_id: str, _: dict = Depends(auth_dep)):
        res = await db.erp_production_plans.delete_one({"id": plan_id})
        if not res.deleted_count:
            raise HTTPException(404, "Plan introuvable")
        return Response(status_code=204)

    @router.get("/production-plans.csv")
    async def export_csv(_: dict = Depends(auth_dep)):
        rows = []
        async for p in db.erp_production_plans.find({}, {"_id": 0}).sort("created_at", -1):
            rows.append({
                "Numéro":  p.get("plan_number") or "",
                "Date":    p.get("date") or "",
                "Projet":  p.get("project_name") or "",
                "# Projet": p.get("project_number") or "",
                "Client":  p.get("client_name") or "",
                "Portes":  len(p.get("doors") or []),
                "Statut":  p.get("status") or "",
            })
        return csv_response(rows, "dessins-production-portech.csv")

    @router.get("/production-plans/{plan_id}/pdf")
    async def download_pdf(plan_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_production_plans.find_one({"id": plan_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Plan introuvable")
        pdf_bytes = await asyncio.to_thread(render_production_plan_pdf, doc)
        filename = f"{doc.get('plan_number') or 'PLAN'}.pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    @router.post("/production-plans/preview-pdf")
    async def preview_pdf(data: ProductionPlanIn, _: dict = Depends(auth_dep)):
        """Render a PDF from an unsaved draft (live preview)."""
        plan = ProductionPlan(**data.model_dump(), plan_number="APERÇU")
        pdf_bytes = await asyncio.to_thread(
            render_production_plan_pdf, plan.model_dump(mode="json"))
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="apercu-plan.pdf"'},
        )
