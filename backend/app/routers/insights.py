"""Insights router. Mounted at /api/insights (legacy) and /api/v1/insights (canonical)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.services import insights_service as ctrl
from app.core.deps import get_current_user

router = APIRouter(prefix="/insights", tags=["insights"])


class AcknowledgeRequest(BaseModel):
    store_id: str
    product_id: str
    date: str


@router.get("/anomalies")
async def get_anomalies(
    sensitivity: str = Query("medium", pattern="^(low|medium|high)$"),
    user: dict = Depends(get_current_user)
):
    return await ctrl.get_anomalies(user["org_id"], sensitivity)


@router.post("/anomalies/acknowledge")
async def acknowledge_anomaly(body: AcknowledgeRequest, user: dict = Depends(get_current_user)):
    return await ctrl.acknowledge_anomaly(user["org_id"], str(user["_id"]), body.store_id, body.product_id, body.date)


@router.get("/trends")
async def get_trends(user: dict = Depends(get_current_user)):
    return await ctrl.get_trends(user["org_id"])
