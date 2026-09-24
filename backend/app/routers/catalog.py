"""Products & stores master-data router. Mounted at /api/catalog (legacy) and /api/v1/catalog (canonical)."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.services import catalog_service as ctrl
from app.schemas.catalog import ProductUpdate, StoreUpdate
from app.core.deps import get_current_user

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/products")
async def list_products(
    page: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=1, le=200),
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    return await ctrl.list_products(user["org_id"], page=page, limit=limit, search=search)


@router.patch("/products/{product_oid}")
async def update_product(product_oid: str, body: ProductUpdate, user: dict = Depends(get_current_user)):
    return await ctrl.update_product(user["org_id"], product_oid, body.model_dump(exclude_none=True))


@router.delete("/products/{product_oid}")
async def delete_product(product_oid: str, user: dict = Depends(get_current_user)):
    return await ctrl.delete_product(user["org_id"], product_oid)


@router.get("/stores")
async def list_stores(user: dict = Depends(get_current_user)):
    return await ctrl.list_stores(user["org_id"])


@router.patch("/stores/{store_oid}")
async def update_store(store_oid: str, body: StoreUpdate, user: dict = Depends(get_current_user)):
    return await ctrl.update_store(user["org_id"], store_oid, body.model_dump(exclude_none=True))


@router.delete("/stores/{store_oid}")
async def delete_store(store_oid: str, user: dict = Depends(get_current_user)):
    return await ctrl.delete_store(user["org_id"], store_oid)
