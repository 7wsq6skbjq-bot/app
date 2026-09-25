"""
Portech internal ERP — router orchestrator.

The ERP exposes 5 resource domains (Parties, Products, Invoices, POs, BOLs)
plus a Dashboard. Each domain lives in its own `erp_routes_*.py` module so
this file stays an assembly point.
"""
from fastapi import APIRouter
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_helpers import make_next_number_fn
from erp_reminders import register_routes as register_reminder_routes
from erp_routes_appointments import register as register_appointments
from erp_routes_bols import register as register_bols
from erp_routes_dashboard import register as register_dashboard
from erp_routes_invoices import register as register_invoices
from erp_routes_quotes import register as register_quotes
from erp_routes_expert_reports import register as register_expert_reports
from erp_expert_report_backup import register_routes as register_backup_routes
from erp_routes_parties import register as register_parties
from erp_routes_products import register as register_products
from erp_routes_purchase_orders import register as register_pos
from erp_routes_expenses import register as register_expenses
from erp_routes_payment_notices import register as register_payment_notices
from erp_routes_mosquito_screens import register as register_mosquito_screens
from erp_routes_production_plans import register as register_production_plans
from erp_routes_statements import register as register_statements
from erp_routes_assistant import register as register_assistant
from erp_routes_jobs import register as register_jobs
from erp_routes_mileage import register as register_mileage
from erp_routes_push import register as register_push
from erp_pricing import register as register_pricing
from erp_routes_at_order_form import register as register_at_order_form
from erp_routes_compose import register as register_compose
from erp_monthly_recap import register_routes as register_monthly_recap
from cut_routes import register as register_cuts
from prospection_routes import register as register_prospection


def build_erp_router(db: AsyncIOMotorDatabase, auth_dep) -> APIRouter:
    """Assemble all ERP routes under /admin/. `auth_dep` is the FastAPI
    dependency that protects admin routes (injected from server.py)."""
    router = APIRouter(prefix="/admin", tags=["erp"])
    next_number = make_next_number_fn(db)

    register_parties(router, db, auth_dep)
    register_products(router, db, auth_dep)
    register_invoices(router, db, auth_dep, next_number)
    register_quotes(router, db, auth_dep, next_number)
    register_expert_reports(router, db, auth_dep, next_number)
    register_backup_routes(router, db, auth_dep)
    register_pos(router, db, auth_dep, next_number)
    register_bols(router, db, auth_dep, next_number)
    register_appointments(router, db, auth_dep)
    register_dashboard(router, db, auth_dep)
    register_reminder_routes(router, db, auth_dep)
    register_expenses(router, db, auth_dep)
    register_payment_notices(router, db, auth_dep)
    register_mosquito_screens(router, db, auth_dep)
    register_production_plans(router, db, auth_dep)
    register_statements(router, db, auth_dep)
    register_assistant(router, db, auth_dep, next_number)
    register_jobs(router, db, auth_dep, next_number)
    register_push(router, db, auth_dep)
    register_mileage(router, db, auth_dep)
    register_pricing(router, db, auth_dep)
    register_at_order_form(router, db, auth_dep)
    register_compose(router, db, auth_dep)
    register_monthly_recap(router, db, auth_dep)
    register_cuts(router, db, auth_dep)
    register_prospection(router, db, auth_dep)

    return router
