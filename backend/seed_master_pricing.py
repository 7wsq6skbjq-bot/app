"""Importe le MASTER de prix AT Fabrication (xlsx) dans les collections ERP.

Collections peuplées (idempotent — ne réécrit pas si déjà présent, sauf force=True) :
  • erp_hardware_master   — quincaillerie (102 items, les 2 fournisseurs gardés)
  • erp_door_prices        — prix vendants portes standards par groupe de quantité
  • erp_pricing_params     — paramètres MASTER (taux horaire, matrice de profit %)
  • erp_extrusion_costs    — coûts extrusion (mill) + anodisation clair/noir par profilé

Le fichier de référence est /app/backend/data/master_prix_reference.xlsx.
Chaque item reste MODIFIABLE via l'API (CRUD).
"""
import os
import uuid
from datetime import datetime, date, timezone

import openpyxl

REF_FILE = os.path.join(os.path.dirname(__file__), "data", "master_prix_reference.xlsx")

_FAMILIES = [
    ("PANIQUE", "Barre panique"), ("CHARNIÈRE", "Charnière"), ("POIGNÉE", "Poignée"),
    ("SERRURE", "Serrure"), ("TÊTIÈRE", "Têtière"), ("GÂCHE", "Gâche"),
    ("PALETTE", "Palette de relâche"), ("TARGETTE", "Targette"),
    ("CYLINDRE", "Cylindre"), ("TOURNIQUET", "Tourniquet"), ("COLLET", "Collet"),
    ("SEUIL", "Seuil"), ("PROTEGE", "Protège-pêne"), ("TRANSMET", "Transmetteur"),
    ("ESPACEUR", "Espaceur"), ("FACEPLATE", "Faceplate"),
]


def _family(desc: str) -> str:
    d = (desc or "").upper()
    for kw, label in _FAMILIES:
        if kw in d:
            return label
    return "Autre"


def _s(v):
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()


def _num(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _parse_hardware(wb) -> list:
    ws = wb["QUINCAILLERIE DE PORTE"]
    out = []
    for r in ws.iter_rows(min_row=4, max_row=110, values_only=True):
        desc, color, code, supplier, price = r[0], r[1], r[2], r[3], r[4]
        if not desc or not code or _s(code).upper() == "HOLD":
            continue
        cost = _num(price)
        if cost is None:
            continue
        out.append({
            "id": uuid.uuid4().hex,
            "description": _s(desc),
            "color": _s(color),
            "product_code": _s(code),
            "supplier": _s(supplier),
            "unit_cost": cost,
            "cost_date": _s(r[5]),
            "kanban_min": _num(r[6]) or 0,
            "kanban_order": _num(r[7]) or 0,
            "kanban_max": _num(r[8]) or 0,
            "category": _family(desc),
            "source": "master",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return out


def _parse_door_prices(wb) -> list:
    ws = wb["LISTE DE PRIX PORTE STANDARD"]
    out = []
    for r in ws.iter_rows(min_row=4, max_row=ws.max_row, values_only=True):
        num = _s(r[0])
        if "-S84-" not in num and "-P84-" not in num:
            continue

        def g(i):
            v = _num(r[i])
            return v if v is not None else _s(r[i])
        out.append({
            "id": uuid.uuid4().hex,
            "part_number": num,
            "description": _s(r[1]),
            "color": _s(r[2]),
            "isolated": num.startswith("ATI"),
            "is_pair": "-P84-" in num,
            "group_a": g(3), "group_b": g(4), "group_c": g(5),
            "group_d": g(6), "group_e": g(7),
            "source": "master",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return out


def _parse_params(wb) -> list:
    ws = wb["DONNEES MASTER"]
    out = []
    order = 0
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
        label, val = _s(r[0]), _num(r[1])
        if not label or val is None:
            continue
        order += 1
        out.append({
            "id": uuid.uuid4().hex, "label": label, "value": val,
            "order": order, "source": "master",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return out


def _parse_extrusion(wb) -> list:
    ext = {}
    ws = wb["HYDRO EXTRUSION"]
    header_seen = False
    for r in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
        part = _s(r[0])
        if part == "# DE PIECE AT FABRICATION":
            header_seen = True
            continue
        if not header_seen or not part or not part.upper().startswith("AT"):
            continue
        ext[part] = {
            "id": uuid.uuid4().hex, "part_number": part,
            "description": _s(r[1]),
            "price_per_kg": _num(r[7]),
            "cost_per_length_mill": _num(r[8]),
            "anod_clair_per_length": None, "anod_noir_per_length": None,
            "source": "master",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ws = wb["PRIX POUR ANODISATION"]
    for r in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
        part = _s(r[0])
        if part not in ext:
            continue
        ext[part]["anod_clair_per_length"] = _num(r[4])
        ext[part]["anod_noir_per_length"] = _num(r[8])
    return list(ext.values())


async def seed_master_pricing(db, force: bool = False) -> dict:
    if not os.path.isfile(REF_FILE):
        return {"skipped": "ref file not found"}
    wb = openpyxl.load_workbook(REF_FILE, data_only=True)
    result = {}
    jobs = [
        ("erp_hardware_master", _parse_hardware(wb)),
        ("erp_door_prices", _parse_door_prices(wb)),
        ("erp_pricing_params", _parse_params(wb)),
        ("erp_extrusion_costs", _parse_extrusion(wb)),
    ]
    for coll_name, docs in jobs:
        coll = db[coll_name]
        existing = await coll.count_documents({})
        if existing and not force:
            result[coll_name] = f"skip ({existing} existants)"
            continue
        if force:
            await coll.delete_many({"source": "master"})
        if docs:
            await coll.insert_many(docs)
        result[coll_name] = f"importé {len(docs)}"
    return result


async def sync_hardware_to_production(db) -> int:
    """Aligne le catalogue quincaillerie des Plans de production sur le master :
    pour chaque code, utilise le coût le PLUS BAS comme référence."""
    master = await db.erp_hardware_master.find({}, {"_id": 0}).to_list(500)
    best = {}
    for m in master:
        key = m["product_code"]
        if key not in best or m["unit_cost"] < best[key]["unit_cost"]:
            best[key] = m
    n = 0
    for m in best.values():
        await db.erp_production_hardware.update_one(
            {"part_number": m["product_code"]},
            {"$set": {"name": m["description"], "part_number": m["product_code"],
                      "category": m["category"], "cost": m["unit_cost"]}},
            upsert=True,
        )
        n += 1
    return n
