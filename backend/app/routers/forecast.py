"""Forecast router. Mounted at /api/forecast (legacy) and /api/v1/forecast (canonical)."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Request, Query

from app.services import forecast_service as ctrl
from app.core.deps import get_current_user

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/predictions")
async def get_predictions(
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    horizon_days: int = Query(30, ge=7, le=90),
    user: dict = Depends(get_current_user)
):
    return await ctrl.get_predictions(user["org_id"], store_id, product_id, horizon_days)


@router.post("/train")
async def train_model(request: Request, user: dict = Depends(get_current_user)):
    # Any authenticated user may trigger training for demo purposes.
    return await ctrl.train_model(user["org_id"], request)


@router.get("/models")
async def get_models(user: dict = Depends(get_current_user)):
    return await ctrl.get_models_list(user["org_id"])


@router.post("/models/{model_id}/promote")
async def promote_model(model_id: str, request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.promote_model(user["org_id"], model_id, request)
