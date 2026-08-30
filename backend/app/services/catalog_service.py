"""Products and stores master-data CRUD."""
from __future__ import annotations

from fastapi import HTTPException

from app.repositories import products_repo, stores_repo
from app.schemas.common import serialize


async def list_products(org_id: str) -> dict:
    docs = await products_repo.list_all(org_id)
    return {"status": "success", "products": [serialize(d) for d in docs]}


async def update_product(org_id: str, product_oid: str, fields: dict) -> dict:
    existing = await products_repo.find_by_id(org_id, product_oid)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    await products_repo.update_fields(org_id, product_oid, fields)
    updated = await products_repo.find_by_id(org_id, product_oid)
    return {"status": "success", "product": serialize(updated)}


async def delete_product(org_id: str, product_oid: str) -> dict:
    existing = await products_repo.find_by_id(org_id, product_oid)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    await products_repo.delete(org_id, product_oid)
    return {"status": "success", "message": "Product deleted"}


async def list_stores(org_id: str) -> dict:
    docs = await stores_repo.list_all(org_id)
    return {"status": "success", "stores": [serialize(d) for d in docs]}


async def update_store(org_id: str, store_oid: str, fields: dict) -> dict:
    existing = await stores_repo.find_by_id(org_id, store_oid)
    if not existing:
        raise HTTPException(status_code=404, detail="Store not found")
    await stores_repo.update_fields(org_id, store_oid, fields)
    updated = await stores_repo.find_by_id(org_id, store_oid)
    return {"status": "success", "store": serialize(updated)}


async def delete_store(org_id: str, store_oid: str) -> dict:
    existing = await stores_repo.find_by_id(org_id, store_oid)
    if not existing:
        raise HTTPException(status_code=404, detail="Store not found")
    await stores_repo.delete(org_id, store_oid)
    return {"status": "success", "message": "Store deleted"}
