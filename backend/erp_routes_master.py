"""Routes API — Master des coûts (quincaillerie, portes, paramètres, extrusion)."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field

from seed_master_pricing import seed_master_pricing, sync_hardware_to_production


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HardwareMasterIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str = Field(min_length=1, max_length=300)
    color: Optional[str] = ""
    product_code: Optional[str] = ""
    supplier: Optional[str] = ""
    unit_cost: float = 0.0
    cost_date: Optional[str] = ""
    kanban_min: float = 0
    kanban_order: float = 0
    kanban_max: float = 0
    category: Optional[str] = "Autre"


class DoorPriceIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    part_number: str
    description: Optional[str] = ""
    color: Optional[str] = ""
    isolated: bool = False
    is_pair: bool = False
    group_a: object = 0
    group_b: object = 0
    group_c: object = 0
    group_d: object = 0
    group_e: object = "SUR DEMANDE"


class ParamIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    label: str
    value: float


class ExtrusionIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    part_number: str
    description: Optional[str] = ""
    price_per_kg: Optional[float] = None
    cost_per_length_mill: Optional[float] = None
    anod_clair_per_length: Optional[float] = None
    anod_noir_per_length: Optional[float] = None


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:

    # ── Moteur de prix de porte (basé sur les 26 LDP standards) ──────
    async def _hw_markup() -> float:
        p = await db.erp_pricing_params.find_one(
            {"label": {"$regex": "QUINCAILLERIE", "$options": "i"}}, {"_id": 0, "value": 1})
        return float(p["value"]) if p else 0.35

    def _compute(ml_cost: float, hw_cost: float, profit_pct: float, hw_markup: float) -> dict:
        ml_profit = round(ml_cost * profit_pct, 2)
        hw_profit = round(hw_cost * hw_markup, 2)
        sell = round(ml_cost + ml_profit + hw_cost + hw_profit, 2)
        cost = round(ml_cost + hw_cost, 2)
        margin = round(sell - cost, 2)
        return {
            "material_labor_cost": round(ml_cost, 2),
            "material_labor_profit": ml_profit,
            "hardware_cost": round(hw_cost, 2),
            "hardware_profit": hw_profit,
            "hardware_markup": hw_markup,
            "cost_total": cost, "sell_total": sell,
            "margin_amount": margin,
            "margin_pct": round(margin / cost * 100, 1) if cost else 0,
        }

    @router.get("/master/door-models")
    async def list_door_models(_: dict = Depends(auth_dep)):
        return await db.erp_door_models.find({}, {"_id": 0}).sort("label", 1).to_list(100)

    class PriceDoorIn(BaseModel):
        model_config = ConfigDict(extra="ignore")
        model_key: str
        hardware: list = []            # [{code, description, cost}]
        profit_pct: Optional[float] = None
        labor_hours: Optional[float] = None

    @router.post("/master/price-door")
    async def price_door(data: PriceDoorIn, _: dict = Depends(auth_dep)):
        model = await db.erp_door_models.find_one({"model_key": data.model_key}, {"_id": 0})
        if not model:
            raise HTTPException(404, "Modèle introuvable")
        rate_param = await db.erp_pricing_params.find_one(
            {"label": {"$regex": "TAUX HORAIRE", "$options": "i"}}, {"_id": 0, "value": 1})
        rate = float(rate_param["value"]) if rate_param else 50.0
        material_cost = float(model.get("material_cost", 0))
        # Recalcule la M.O. si l'utilisateur change les heures, sinon garde le LDP.
        if data.labor_hours is not None:
            labor_cost = round(float(data.labor_hours) * rate, 2)
        else:
            labor_cost = float(model.get("labor_cost", 0))
        ml_cost = round(material_cost + labor_cost, 2)
        hw = data.hardware if data.hardware else model.get("hardware", [])
        hw_cost = round(sum(float(h.get("cost", 0)) for h in hw), 2)
        profit_pct = data.profit_pct if data.profit_pct is not None else float(model.get("profit_pct", 0.6))
        result = _compute(ml_cost, hw_cost, profit_pct, await _hw_markup())
        result.update({"model_key": data.model_key, "label": model.get("label"),
                       "labor_cost": labor_cost, "profit_pct": profit_pct,
                       "hardware": hw})
        return result

    # ── Quincaillerie master (CRUD complet + recherche) ──────────────
    @router.get("/master/hardware")
    async def list_hardware(q: Optional[str] = None, supplier: Optional[str] = None,
                            category: Optional[str] = None, _: dict = Depends(auth_dep)):
        query: dict = {}
        if supplier:
            query["supplier"] = supplier
        if category:
            query["category"] = category
        if q:
            tokens = [tok for tok in q.split() if tok]
            if tokens:
                query["$and"] = [
                    {"$or": [
                        {"description": {"$regex": tok, "$options": "i"}},
                        {"product_code": {"$regex": tok, "$options": "i"}},
                        {"color": {"$regex": tok, "$options": "i"}},
                    ]} for tok in tokens
                ]
        rows = await db.erp_hardware_master.find(query, {"_id": 0}).sort("description", 1).to_list(1000)
        return rows

    @router.get("/master/hardware/meta")
    async def hardware_meta(_: dict = Depends(auth_dep)):
        rows = await db.erp_hardware_master.find({}, {"_id": 0, "supplier": 1, "category": 1, "unit_cost": 1}).to_list(1000)
        return {
            "count": len(rows),
            "suppliers": sorted({r.get("supplier") for r in rows if r.get("supplier")}),
            "categories": sorted({r.get("category") for r in rows if r.get("category")}),
            "total_cost": round(sum(float(r.get("unit_cost", 0)) for r in rows), 2),
        }

    @router.post("/master/hardware", status_code=201)
    async def create_hardware(data: HardwareMasterIn, _: dict = Depends(auth_dep)):
        doc = {"id": uuid.uuid4().hex, **data.model_dump(), "source": "manuel", "updated_at": _now()}
        await db.erp_hardware_master.insert_one(dict(doc))
        return doc

    @router.put("/master/hardware/{item_id}")
    async def update_hardware(item_id: str, data: HardwareMasterIn, _: dict = Depends(auth_dep)):
        res = await db.erp_hardware_master.update_one(
            {"id": item_id}, {"$set": {**data.model_dump(), "updated_at": _now()}})
        if res.matched_count == 0:
            raise HTTPException(404, "Item introuvable")
        return await db.erp_hardware_master.find_one({"id": item_id}, {"_id": 0})

    @router.delete("/master/hardware/{item_id}", status_code=204)
    async def delete_hardware(item_id: str, _: dict = Depends(auth_dep)):
        await db.erp_hardware_master.delete_one({"id": item_id})

    # ── Prix portes standards ────────────────────────────────────────
    @router.get("/master/door-prices")
    async def list_door_prices(_: dict = Depends(auth_dep)):
        return await db.erp_door_prices.find({}, {"_id": 0}).sort("part_number", 1).to_list(200)

    @router.put("/master/door-prices/{item_id}")
    async def update_door_price(item_id: str, data: DoorPriceIn, _: dict = Depends(auth_dep)):
        res = await db.erp_door_prices.update_one(
            {"id": item_id}, {"$set": {**data.model_dump(), "updated_at": _now()}})
        if res.matched_count == 0:
            raise HTTPException(404, "Introuvable")
        return await db.erp_door_prices.find_one({"id": item_id}, {"_id": 0})

    # ── Paramètres MASTER ────────────────────────────────────────────
    @router.get("/master/params")
    async def list_params(_: dict = Depends(auth_dep)):
        return await db.erp_pricing_params.find({}, {"_id": 0}).sort("order", 1).to_list(100)

    @router.put("/master/params/{item_id}")
    async def update_param(item_id: str, data: ParamIn, _: dict = Depends(auth_dep)):
        res = await db.erp_pricing_params.update_one(
            {"id": item_id}, {"$set": {"label": data.label, "value": data.value, "updated_at": _now()}})
        if res.matched_count == 0:
            raise HTTPException(404, "Introuvable")
        return await db.erp_pricing_params.find_one({"id": item_id}, {"_id": 0})

    # ── Coûts extrusion / anodisation ────────────────────────────────
    @router.get("/master/extrusion")
    async def list_extrusion(_: dict = Depends(auth_dep)):
        return await db.erp_extrusion_costs.find({}, {"_id": 0}).sort("part_number", 1).to_list(200)

    @router.put("/master/extrusion/{item_id}")
    async def update_extrusion(item_id: str, data: ExtrusionIn, _: dict = Depends(auth_dep)):
        res = await db.erp_extrusion_costs.update_one(
            {"id": item_id}, {"$set": {**data.model_dump(), "updated_at": _now()}})
        if res.matched_count == 0:
            raise HTTPException(404, "Introuvable")
        return await db.erp_extrusion_costs.find_one({"id": item_id}, {"_id": 0})

    # ── Ré-import / synchronisation ──────────────────────────────────
    @router.post("/master/reimport")
    async def reimport(force: bool = True, _: dict = Depends(auth_dep)):
        res = await seed_master_pricing(db, force=force)
        synced = await sync_hardware_to_production(db)
        return {"import": res, "synced_to_production": synced}

    @router.post("/master/sync-production")
    async def sync_production(_: dict = Depends(auth_dep)):
        return {"synced": await sync_hardware_to_production(db)}
