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

from erp_helpers import csv_response, send_pdf_email
from erp_models import EmailSendRequest
from erp_pdf_production import render_production_plan_pdf
from adams_rite_drawings import detect_from_hardware, load_index, merge_drawing_pages


def _plan_drawing_pages(doc: dict) -> list:
    """Union of manually-selected pages + auto-detected pages from hardware."""
    pages = set(int(p) for p in (doc.get("drawing_pages") or []))
    if doc.get("include_hardware_drawings", True):
        texts = []
        for d in doc.get("doors", []):
            for hw in (d.get("hardware") or []):
                texts.append(f"{hw.get('description', '')} {hw.get('part_number', '')}")
        for hit in detect_from_hardware(texts):
            pages.add(hit["page"])
    return sorted(pages)


DoorSeries = Literal["AT1000", "ATi1000", "AT2000", "ATi2000"]
DoorConfig = Literal["simple", "pair"]
PlanStatus = Literal["brouillon", "en production", "en hold", "produit", "annulé"]


class HardwareLine(BaseModel):
    qty: str = "1"
    description: str = ""
    part_number: str = ""
    note: str = ""
    unit_price: float = 0
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
    leaf_active_width_in: float = 0
    leaf_inactive_width_in: float = 0
    fab_width_in: float = 0
    fab_height_in: float = 0
    handle_height_in: float = 34.5
    handle_length_in: float = 9
    handle_both: bool = False
    lock_height_in: float = 40
    panic_bar: bool = False
    panic_height_in: float = 40
    no_hardware: bool = False
    show_handle: bool = True
    show_lock: bool = True
    lever: bool = False
    lever_height_in: float = 40
    push_paddle: bool = False
    paddle_height_in: float = 40
    protection_plate: bool = False
    plate_height_in: float = 40
    flush_bolt: bool = False
    door_closer: bool = False
    astragal: bool = False
    handle_leaf: Literal["active", "inactive", "both"] = "active"
    lock_leaf: Literal["active", "inactive", "both"] = "active"
    lever_leaf: Literal["active", "inactive", "both"] = "active"
    paddle_leaf: Literal["active", "inactive", "both"] = "active"
    plate_leaf: Literal["active", "inactive", "both"] = "active"
    panic_leaf: Literal["active", "inactive", "both"] = "active"
    flush_leaf: Literal["active", "inactive", "both"] = "inactive"
    closer_leaf: Literal["active", "inactive", "both"] = "active"
    undercut_mm: float = 17.5
    finish_ext: str = ""
    finish_int: str = ""
    glass: str = ""
    glass_type: Literal["6mm", "tht"] = "6mm"
    hinges: str = ""
    hinge_type: Literal["butt45", "continue", "none"] = "butt45"
    profile_head: str = ""
    profile_base: str = ""
    profile_hinge_stile: str = ""
    profile_lock_stile: str = ""
    profile_lock_stile_inactive: str = ""
    scale_note: str = "1:30"
    hardware: List[HardwareLine] = Field(default_factory=list)
    notes: str = ""


class ProductionPlanIn(BaseModel):
    project_name: str = Field("", max_length=120)
    project_number: str = Field("", max_length=40)
    production_name: str = ""
    production_note: str = ""
    revision: str = "no00"
    mention: str = "Pour production"
    date: DateT = Field(default_factory=DateT.today)
    client_name: str = ""
    client_address: str = ""
    client_contact: str = ""
    client_phone: str = ""
    machining_by: str = "A.T. Fabrication"
    installer: str = "Portech"
    fab_auto: bool = True
    fab_allowance_in: float = 0
    include_plan_details: bool = True
    include_section_details: bool = True
    include_anchors: bool = True
    show_costs: bool = False
    include_hardware_drawings: bool = True   # annexer auto les dessins Adams Rite
    drawing_pages: Optional[List[int]] = None  # pages manuelles supplémentaires
    status: PlanStatus = "brouillon"
    doors: List[DoorPlan] = Field(default_factory=list)
    notes: str = ""


class ProductionPlan(ProductionPlanIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_number: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductionHardwareIn(BaseModel):
    name: str = Field("", max_length=120)
    part_number: str = Field("", max_length=60)
    category: str = Field("", max_length=60)
    cost: float = 0
    price: float = 0


class ProductionHardware(ProductionHardwareIn):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExchangeRateIn(BaseModel):
    usd_cad: float = Field(gt=0, le=100)


class PriceRow(BaseModel):
    part_number: str = ""
    description: str = ""
    list_price_usd: float = 0


class PriceImportIn(BaseModel):
    rows: List[PriceRow]
    dry_run: bool = True
    markup_pct: float = 30.0     # majoration sur le coûtant (%)
    vendor: str = "Adams Rite"


DEFAULT_USD_CAD = 1.38


def _round_005(v: float) -> float:
    """Arrondi au 0,05 $ le plus proche."""
    return round(round((v or 0) / 0.05) * 0.05, 2)


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

    async def _sync_hardware_catalog(doors: list) -> None:
        """Auto-add any new hardware descriptions used on a plan to the catalog."""
        for d in doors or []:
            for hw in (d.get("hardware") or []):
                name = (hw.get("description") or "").strip()
                if not name:
                    continue
                existing = await db.erp_production_hardware.find_one({"name": name})
                if not existing:
                    item = ProductionHardware(
                        name=name, part_number=(hw.get("part_number") or "").strip(),
                        price=float(hw.get("unit_price") or 0))
                    await db.erp_production_hardware.insert_one(item.model_dump(mode="json"))

    # ── hardware catalog (searchable dropdown source) ──────────────
    @router.get("/production-hardware", response_model=List[ProductionHardware])
    async def list_hardware(_: dict = Depends(auth_dep)):
        cur = db.erp_production_hardware.find({}, {"_id": 0}).sort("name", 1)
        return [ProductionHardware(**d) async for d in cur]

    @router.post("/production-hardware", response_model=ProductionHardware, status_code=201)
    async def create_hardware(data: ProductionHardwareIn, _: dict = Depends(auth_dep)):
        name = (data.name or "").strip()
        if not name:
            raise HTTPException(400, "Le nom est requis.")
        existing = await db.erp_production_hardware.find_one({"name": name}, {"_id": 0})
        if existing:
            patch = {"part_number": data.part_number.strip(),
                     "category": data.category.strip(),
                     "cost": float(data.cost or 0), "price": float(data.price or 0)}
            await db.erp_production_hardware.update_one({"id": existing["id"]}, {"$set": patch})
            existing.update(patch)
            return ProductionHardware(**existing)
        item = ProductionHardware(name=name,
                                  part_number=data.part_number.strip(),
                                  category=data.category.strip(),
                                  cost=float(data.cost or 0),
                                  price=float(data.price or 0))
        await db.erp_production_hardware.insert_one(item.model_dump(mode="json"))
        return item

    @router.put("/production-hardware/{item_id}", response_model=ProductionHardware)
    async def update_hardware(item_id: str, data: ProductionHardwareIn,
                              _: dict = Depends(auth_dep)):
        existing = await db.erp_production_hardware.find_one({"id": item_id}, {"_id": 0})
        if not existing:
            raise HTTPException(404, "Quincaillerie introuvable.")
        patch = {"name": (data.name or "").strip(),
                 "part_number": data.part_number.strip(),
                 "category": data.category.strip(),
                 "cost": float(data.cost or 0), "price": float(data.price or 0)}
        await db.erp_production_hardware.update_one({"id": item_id}, {"$set": patch})
        existing.update(patch)
        return ProductionHardware(**existing)

    @router.delete("/production-hardware/{item_id}", status_code=204)
    async def delete_hardware(item_id: str, _: dict = Depends(auth_dep)):
        res = await db.erp_production_hardware.delete_one({"id": item_id})
        if not res.deleted_count:
            raise HTTPException(404, "Quincaillerie introuvable.")
        return Response(status_code=204)

    # ── Taux de change USD→CAD (configurable) ──────────────────────
    async def _get_rate() -> float:
        doc = await db.erp_settings.find_one({"key": "usd_cad_rate"})
        try:
            return float(doc["value"]) if doc and doc.get("value") else DEFAULT_USD_CAD
        except (TypeError, ValueError):
            return DEFAULT_USD_CAD

    @router.get("/settings/exchange-rate")
    async def get_exchange_rate(_: dict = Depends(auth_dep)):
        doc = await db.erp_settings.find_one({"key": "usd_cad_rate"}, {"_id": 0})
        return {
            "usd_cad": (float(doc["value"]) if doc and doc.get("value") else DEFAULT_USD_CAD),
            "updated_at": (doc.get("updated_at") if doc else None),
        }

    @router.put("/settings/exchange-rate")
    async def set_exchange_rate(data: ExchangeRateIn, _: dict = Depends(auth_dep)):
        now = datetime.now(timezone.utc).isoformat()
        await db.erp_settings.update_one(
            {"key": "usd_cad_rate"},
            {"$set": {"value": data.usd_cad, "updated_at": now}},
            upsert=True,
        )
        return {"usd_cad": data.usd_cad, "updated_at": now}

    # ── Import d'une liste de prix (USD → CAD + majoration) ─────────
    @router.post("/production-hardware/import")
    async def import_prices(data: PriceImportIn, _: dict = Depends(auth_dep)):
        """Convertit USD→CAD (taux configuré), applique la majoration (30% par
        défaut) arrondie au 0,05 $, puis crée/maj chaque item par numéro de
        pièce. dry_run=True → aperçu sans écriture."""
        rate = await _get_rate()
        markup = 1 + (data.markup_pct if data.markup_pct is not None else 30.0) / 100.0
        created = updated = skipped = 0
        items = []
        for r in data.rows:
            pn = (r.part_number or "").strip()
            desc = (r.description or "").strip()
            cost = round((r.list_price_usd or 0) * rate, 2)
            price = _round_005(cost * markup)
            existing = await db.erp_production_hardware.find_one({"part_number": pn}) if pn else None
            if not pn and not desc:
                action = "skipped"
                skipped += 1
            elif data.dry_run:
                action = "update" if existing else "create"
            elif existing:
                patch = {"cost": cost, "price": price}
                if not (existing.get("name") or "").strip() and desc:
                    patch["name"] = desc
                await db.erp_production_hardware.update_one({"id": existing["id"]}, {"$set": patch})
                action = "updated"; updated += 1
            else:
                item = ProductionHardware(name=desc or pn, part_number=pn,
                                          category=data.vendor, cost=cost, price=price)
                await db.erp_production_hardware.insert_one(item.model_dump(mode="json"))
                action = "created"; created += 1
            items.append({
                "part_number": pn, "description": desc,
                "list_price_usd": round(r.list_price_usd or 0, 2),
                "cost_cad": cost, "price_cad": price, "action": action,
            })
        return {
            "rate": rate, "markup_pct": data.markup_pct, "dry_run": data.dry_run,
            "count": len(data.rows), "created": created, "updated": updated,
            "skipped": skipped, "items": items,
        }

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
            "bases": [opt(k) for k in ("ATB1000", "ATB2000", "ATT1005")],
            "stiles": [opt(k) for k in ("ATV1025", "ATV1015", "ATV1010", "ATV2010", "ATV2015")],
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
        await _sync_hardware_catalog(plan.model_dump(mode="json").get("doors") or [])
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
        await _sync_hardware_catalog(data.model_dump(mode="json").get("doors") or [])
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

    @router.get("/production-plans/{plan_id}/detect-drawings")
    async def detect_drawings(plan_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_production_plans.find_one({"id": plan_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Plan introuvable")
        texts = []
        for d in doc.get("doors", []):
            for hw in (d.get("hardware") or []):
                texts.append(f"{hw.get('description', '')} {hw.get('part_number', '')}")
        return {"detected": detect_from_hardware(texts),
                "manual_pages": doc.get("drawing_pages") or [],
                "auto": doc.get("include_hardware_drawings", True),
                "all_drawings": list(load_index())}

    @router.get("/production-plans/{plan_id}/pdf")
    async def download_pdf(plan_id: str, _: dict = Depends(auth_dep)):
        doc = await db.erp_production_plans.find_one({"id": plan_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Plan introuvable")
        pdf_bytes = await asyncio.to_thread(render_production_plan_pdf, doc)
        pages = _plan_drawing_pages(doc)
        if pages:
            pdf_bytes = await asyncio.to_thread(merge_drawing_pages, pdf_bytes, pages)
        filename = f"{doc.get('plan_number') or 'PLAN'}.pdf"
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    @router.post("/production-plans/preview-pdf")
    async def preview_pdf(data: ProductionPlanIn, _: dict = Depends(auth_dep)):
        """Render a PDF from an unsaved draft (live preview)."""
        plan = ProductionPlan(**data.model_dump(), plan_number="APERÇU")
        doc = plan.model_dump(mode="json")
        pdf_bytes = await asyncio.to_thread(render_production_plan_pdf, doc)
        pages = _plan_drawing_pages(doc)
        if pages:
            pdf_bytes = await asyncio.to_thread(merge_drawing_pages, pdf_bytes, pages)
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="apercu-plan.pdf"'},
        )

    @router.post("/production-plans/{plan_id}/send-email")
    async def send_plan_email(plan_id: str, payload: EmailSendRequest,
                              _: dict = Depends(auth_dep)):
        """Email the production-drawing PDF straight to the client."""
        doc = await db.erp_production_plans.find_one({"id": plan_id}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Plan introuvable")
        pdf_bytes = await asyncio.to_thread(render_production_plan_pdf, doc)
        pages = _plan_drawing_pages(doc)
        if pages:
            pdf_bytes = await asyncio.to_thread(merge_drawing_pages, pdf_bytes, pages)
        number = doc.get("plan_number") or "PLAN"
        project = doc.get("project_name") or ""
        client = doc.get("client_contact") or doc.get("client_name") or ""
        subject = payload.subject or (
            f"Portech — Dessin de production {number}"
            + (f" · {project}" if project else "")
        )
        message_html = payload.message or (
            f"<p>Bonjour{(' ' + client) if client else ''},</p>"
            f"<p>Vous trouverez en pièce jointe le dessin de production "
            f"<b>{number}</b>"
            + (f" pour le projet <b>{project}</b>" if project else "")
            + ".</p>"
            "<p>N'hésitez pas à nous revenir pour toute question ou approbation.</p>"
        )
        await send_pdf_email(
            to_email=payload.to_email, subject=subject,
            html=message_html, pdf_bytes=pdf_bytes,
            filename=f"{number}.pdf",
            footer_note=f"Dessin de production {number} · Portech ERP",
        )
        return {"sent": True, "to": payload.to_email}
