"""Alert rules & notifications router. Mounted at /api/alerts (legacy) and /api/v1/alerts (canonical)."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.services import alerts_service as ctrl
from app.core.deps import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


class RuleCreate(BaseModel):
    type: str
    store_id: Optional[str] = None
    product_id: Optional[str] = None
    threshold_pct: Optional[float] = None
    min_abs_z: Optional[float] = None


@router.get("/rules")
async def list_rules(user: dict = Depends(get_current_user)):
    return await ctrl.list_rules(user["org_id"])


@router.post("/rules")
async def create_rule(body: RuleCreate, user: dict = Depends(get_current_user)):
    params = body.model_dump(exclude={"type"}, exclude_none=True)
    return await ctrl.create_rule(user["org_id"], str(user["_id"]), body.type, params)


@router.post("/rules/{rule_id}/enable")
async def enable_rule(rule_id: str, user: dict = Depends(get_current_user)):
    return await ctrl.set_rule_enabled(user["org_id"], rule_id, True)


@router.post("/rules/{rule_id}/disable")
async def disable_rule(rule_id: str, user: dict = Depends(get_current_user)):
    return await ctrl.set_rule_enabled(user["org_id"], rule_id, False)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, user: dict = Depends(get_current_user)):
    return await ctrl.delete_rule(user["org_id"], rule_id)


@router.post("/evaluate")
async def evaluate_rules(user: dict = Depends(get_current_user)):
    """Run every enabled rule now. Also runs automatically on the weekly retraining schedule."""
    return await ctrl.evaluate_rules(user["org_id"])


@router.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    return await ctrl.list_notifications(user["org_id"])


@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id: str, user: dict = Depends(get_current_user)):
    return await ctrl.mark_notification_read(user["org_id"], notification_id)


@router.post("/notifications/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    return await ctrl.mark_all_read(user["org_id"])
