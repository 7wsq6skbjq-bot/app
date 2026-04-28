"""
Portech internal ERP — router orchestrator.

The ERP exposes 5 resource domains (Parties, Products, Invoices, POs, BOLs)
plus a Dashboard. Each domain lives in its own `erp_routes_*.py` module so
this file stays an assembly point.
"""
from fastapi import APIRouter
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_helpers import make_next_number_fn
from erp_routes_bols import register as register_bols
from erp_routes_dashboard import register as register_dashboard
from erp_routes_invoices import register as register_invoices
from erp_routes_parties import register as register_parties
from erp_routes_products import register as register_products
from erp_routes_purchase_orders import register as register_pos


def build_erp_router(db: AsyncIOMotorDatabase, auth_dep) -> APIRouter:
    """Assemble all ERP routes under /admin/. `auth_dep` is the FastAPI
    dependency that protects admin routes (injected from server.py)."""
    router = APIRouter(prefix="/admin", tags=["erp"])
    next_number = make_next_number_fn(db)

    register_parties(router, db, auth_dep)
    register_products(router, db, auth_dep)
    register_invoices(router, db, auth_dep, next_number)
    register_pos(router, db, auth_dep, next_number)
    register_bols(router, db, auth_dep, next_number)
    register_dashboard(router, db, auth_dep)

    return router
