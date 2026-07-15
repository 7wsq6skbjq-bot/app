"""Product catalogue CRUD routes."""
import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_models import Product, ProductIn
from erp_pdf import render_product_catalog_pdf


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.get("/products", response_model=List[Product])
    async def list_products(_: dict = Depends(auth_dep)):
        cur = db.erp_products.find({}, {"_id": 0}).sort("name", 1)
        return [Product(**d) async for d in cur]

    @router.get("/products/catalog.pdf")
    async def download_catalog_pdf(_: dict = Depends(auth_dep)):
        """Generate a clean branded catalog PDF of all products & services.

        Intended for handing out to trusted clients — grouped by category,
        with SKU, name, description, unit and price. Service items get a
        small badge ; items priced at 0 show as "sur demande".
        """
        cursor = db.erp_products.find({}, {"_id": 0}).sort([("category", 1), ("name", 1)])
        products = [d async for d in cursor]
        pdf_bytes = await asyncio.to_thread(render_product_catalog_pdf, products)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    'inline; filename="catalogue-portech-produits-services.pdf"',
            },
        )

    @router.post("/products", response_model=Product, status_code=201)
    async def create_product(data: ProductIn, _: dict = Depends(auth_dep)):
        p = Product(**data.model_dump())
        await db.erp_products.insert_one(p.model_dump())
        return p

    @router.put("/products/{product_id}", response_model=Product)
    async def update_product(product_id: str, data: ProductIn, _: dict = Depends(auth_dep)):
        result = await db.erp_products.update_one(
            {"id": product_id}, {"$set": data.model_dump()}
        )
        if result.matched_count == 0:
            raise HTTPException(404, "Produit introuvable")
        doc = await db.erp_products.find_one({"id": product_id}, {"_id": 0})
        return Product(**doc)

    @router.delete("/products/{product_id}")
    async def delete_product(product_id: str, _: dict = Depends(auth_dep)):
        result = await db.erp_products.delete_one({"id": product_id})
        if result.deleted_count == 0:
            raise HTTPException(404, "Produit introuvable")
        return {"deleted": product_id}
