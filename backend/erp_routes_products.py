"""Product catalogue CRUD routes."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from erp_models import Product, ProductIn


def register(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    @router.get("/products", response_model=List[Product])
    async def list_products(_: dict = Depends(auth_dep)):
        cur = db.erp_products.find({}, {"_id": 0}).sort("name", 1)
        return [Product(**d) async for d in cur]

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
