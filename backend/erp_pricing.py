"""
Portech — moteur de calcul de prix & rentabilité (Phase 1).

Règles financières EXACTES (ne jamais confondre markup et marge) :
    profit  = prix_vente - cout
    markup% = profit / cout            (base = coût)
    marge%  = profit / prix_vente      (base = prix de vente)
    prix depuis marge cible : prix = cout / (1 - marge)     (marge en fraction)

Aucune donnée n'est inventée : les taux/seuils manquants restent None et sont
signalés « DONNÉE MANQUANTE » côté interface.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# Catégories reconnues (pour la ventilation de rentabilité)
CATEGORIES = [
    "porte", "quincaillerie", "main_doeuvre", "deplacement",
    "forfait", "expertise", "fabrication", "usinage", "autre",
]

DEFAULT_SETTINGS = {
    "labor_rates": {
        "standard": 90.0,       # confirmé par le client
        "specialized": None,    # DONNÉE MANQUANTE
        "fabrication": None,
        "machining": None,
        "expertise": None,
    },
    "km_rate": 0.85,            # $/km (aller + retour)
    "margin_min": None,         # seuil d'alerte (fraction, ex 0.30)
    "margin_target": None,      # marge cible (fraction)
}


def _f(v, dflt: float = 0.0) -> float:
    try:
        return float(v if v not in (None, "") else dflt)
    except (TypeError, ValueError):
        return dflt


def markup_pct(cost: float, profit: float) -> Optional[float]:
    """Profit / coût. None si coût = 0 (markup indéfini)."""
    cost = _f(cost)
    if cost <= 0:
        return None
    return _f(profit) / cost


def margin_pct(sell: float, profit: float) -> Optional[float]:
    """Profit / prix de vente. None si vente = 0."""
    sell = _f(sell)
    if sell <= 0:
        return None
    return _f(profit) / sell


def price_from_margin(cost: float, margin: float) -> Optional[float]:
    """Prix requis pour atteindre une marge brute cible : cout / (1 - marge).
    `margin` est une fraction (0.30 = 30 %). None si marge >= 1."""
    cost = _f(cost)
    margin = _f(margin)
    if margin >= 1:
        return None
    return cost / (1.0 - margin)


def price_from_markup(cost: float, markup: float) -> float:
    """Prix depuis un markup (fraction) : cout * (1 + markup)."""
    return _f(cost) * (1.0 + _f(markup))


class PricingLine(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str = ""
    category: str = "autre"
    # quantité : soit qty directe, soit "1 pour N portes" × nb_portes
    qty: float = 1
    per_n_doors: float = 0        # si > 0 : 1 pièce couvre N portes
    doors: float = 0              # nombre total de portes du projet
    unit_cost: float = 0
    unit_price: float = 0         # prix de vente unitaire


def line_qty(line: PricingLine) -> float:
    """Quantité effective. Si per_n_doors>0 et doors>0 :
    ceil(doors / per_n_doors) (ex : 1 pour 2 portes, 6 portes → 3)."""
    if line.per_n_doors and line.per_n_doors > 0 and line.doors and line.doors > 0:
        import math
        return math.ceil(line.doors / line.per_n_doors)
    return _f(line.qty, 1)


def compute_line(line: PricingLine) -> dict:
    q = line_qty(line)
    cost = q * _f(line.unit_cost)
    sell = q * _f(line.unit_price)
    profit = sell - cost
    return {
        "description": line.description,
        "category": line.category if line.category in CATEGORIES else "autre",
        "qty": q,
        "unit_cost": _f(line.unit_cost),
        "unit_price": _f(line.unit_price),
        "cost_total": round(cost, 2),
        "sell_total": round(sell, 2),
        "profit": round(profit, 2),
        "markup": markup_pct(cost, profit),
        "margin": margin_pct(sell, profit),
    }


def compute_summary(lines: List[PricingLine],
                    margin_min: Optional[float] = None) -> dict:
    rows = [compute_line(ln) for ln in lines]
    by_cat: dict = {}
    tot_cost = tot_sell = 0.0
    for r in rows:
        tot_cost += r["cost_total"]
        tot_sell += r["sell_total"]
        c = by_cat.setdefault(r["category"], {"cost": 0.0, "sell": 0.0})
        c["cost"] += r["cost_total"]
        c["sell"] += r["sell_total"]
    for c in by_cat.values():
        c["profit"] = round(c["sell"] - c["cost"], 2)
        c["markup"] = markup_pct(c["cost"], c["sell"] - c["cost"])
        c["margin"] = margin_pct(c["sell"], c["sell"] - c["cost"])
        c["cost"] = round(c["cost"], 2)
        c["sell"] = round(c["sell"], 2)
    profit = tot_sell - tot_cost
    margin = margin_pct(tot_sell, profit)
    below_min = (margin_min is not None and margin is not None
                 and margin < _f(margin_min))
    return {
        "lines": rows,
        "cost_total": round(tot_cost, 2),
        "sell_total": round(tot_sell, 2),
        "profit": round(profit, 2),
        "markup": markup_pct(tot_cost, profit),
        "margin": margin,
        "by_category": by_cat,
        "below_min": below_min,
    }


class PricingSettingsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    labor_rates: dict = Field(default_factory=dict)
    km_rate: Optional[float] = None
    margin_min: Optional[float] = None
    margin_target: Optional[float] = None


class PricingComputeIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    lines: List[PricingLine] = Field(default_factory=list)
    margin_min: Optional[float] = None


def register(router, db, auth_dep):
    from fastapi import Depends

    async def _get_settings() -> dict:
        doc = await db.erp_pricing_settings.find_one({"_id": "singleton"})
        if not doc:
            return dict(DEFAULT_SETTINGS)
        doc.pop("_id", None)
        # merge with defaults so new keys always exist
        merged = dict(DEFAULT_SETTINGS)
        merged.update(doc)
        rates = dict(DEFAULT_SETTINGS["labor_rates"])
        rates.update(doc.get("labor_rates") or {})
        merged["labor_rates"] = rates
        return merged

    @router.get("/pricing/settings")
    async def get_pricing_settings(_: dict = Depends(auth_dep)):
        return await _get_settings()

    @router.put("/pricing/settings")
    async def put_pricing_settings(data: PricingSettingsIn, _: dict = Depends(auth_dep)):
        cur = await _get_settings()
        rates = dict(cur["labor_rates"])
        for k, v in (data.labor_rates or {}).items():
            rates[k] = (None if v in (None, "") else _f(v))
        payload = {
            "labor_rates": rates,
            "km_rate": _f(data.km_rate, cur["km_rate"]) if data.km_rate not in (None, "") else cur["km_rate"],
            "margin_min": None if data.margin_min in (None, "") else _f(data.margin_min),
            "margin_target": None if data.margin_target in (None, "") else _f(data.margin_target),
        }
        await db.erp_pricing_settings.update_one(
            {"_id": "singleton"}, {"$set": payload}, upsert=True)
        return {**payload}

    @router.post("/pricing/compute")
    async def compute(data: PricingComputeIn, _: dict = Depends(auth_dep)):
        mm = data.margin_min
        if mm is None:
            mm = (await _get_settings()).get("margin_min")
        return compute_summary(data.lines, mm)
