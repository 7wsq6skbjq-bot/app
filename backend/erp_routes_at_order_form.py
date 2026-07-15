"""Public / admin route to download the blank client-facing AT door
order form PDF.

Cédrick sends this form to glazier clients so they can order AT doors
directly by returning a completed copy by email.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_pdf import render_client_at_order_form_pdf


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.get("/at-order-form.pdf")
    async def download_at_order_form(_: dict = Depends(auth_dep)):
        """Blank AT door order form — Portech-branded, printable / fillable."""
        pdf_bytes = await asyncio.to_thread(render_client_at_order_form_pdf)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    'inline; filename="portech-formulaire-commande-porte-AT.pdf"',
            },
        )
