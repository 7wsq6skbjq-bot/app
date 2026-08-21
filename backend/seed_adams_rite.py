"""Idempotent seeding of the Adams Rite catalog (products + production hardware).

The Adams Rite data was imported into the PREVIEW database. Production uses a
SEPARATE database, so the imported rows never migrate on deploy. This seeder
bundles a JSON snapshot in the repo and inserts it on startup ONLY when the
target collections have no Adams Rite rows yet — it never overwrites or
duplicates existing data.
"""
import json
import os

_DIR = os.path.join(os.path.dirname(__file__), "seed_data")


def _load(name):
    path = os.path.join(_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_adams_rite_catalog(db) -> None:
    """Insert bundled Adams Rite products + hardware if absent (idempotent)."""
    # Products
    have = await db.erp_products.count_documents({"category": "Adams Rite"})
    if have == 0:
        rows = _load("adams_rite_products.json")
        if rows:
            # skip any row whose id already exists (defensive)
            existing_ids = set()
            async for d in db.erp_products.find({}, {"id": 1}):
                existing_ids.add(d.get("id"))
            fresh = [r for r in rows if r.get("id") not in existing_ids]
            if fresh:
                await db.erp_products.insert_many(fresh)
                print(f"[seed] Adams Rite products inserted: {len(fresh)}")

    # Production hardware
    have_hw = await db.erp_production_hardware.count_documents({"category": "Adams Rite"})
    if have_hw == 0:
        rows = _load("adams_rite_hardware.json")
        if rows:
            existing_pns = set()
            async for d in db.erp_production_hardware.find({}, {"part_number": 1}):
                existing_pns.add(d.get("part_number"))
            fresh = [r for r in rows if r.get("part_number") not in existing_pns]
            if fresh:
                await db.erp_production_hardware.insert_many(fresh)
                print(f"[seed] Adams Rite hardware inserted: {len(fresh)}")
