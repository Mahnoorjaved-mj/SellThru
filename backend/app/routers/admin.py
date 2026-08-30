"""Admin router (org-scoped). Mounted at /api/admin (legacy) and /api/v1/admin (canonical)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services import admin_service as ctrl
from app.core.deps import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleChange(BaseModel):
    role: str


@router.get("/overview")
async def get_overview(user: dict = Depends(require_admin)):
    return await ctrl.get_overview(user["org_id"])


@router.get("/users")
async def list_users(user: dict = Depends(require_admin)):
    return await ctrl.list_users(user["org_id"])


@router.post("/users/{target_user_id}/role")
async def change_role(target_user_id: str, body: RoleChange, user: dict = Depends(require_admin)):
    return await ctrl.change_user_role(user["org_id"], str(user["_id"]), target_user_id, body.role)


@router.post("/users/{target_user_id}/suspend")
async def suspend_user(target_user_id: str, user: dict = Depends(require_admin)):
    return await ctrl.set_user_suspended(user["org_id"], str(user["_id"]), target_user_id, True)


@router.post("/users/{target_user_id}/reactivate")
async def reactivate_user(target_user_id: str, user: dict = Depends(require_admin)):
    return await ctrl.set_user_suspended(user["org_id"], str(user["_id"]), target_user_id, False)


@router.get("/audit-log")
async def get_audit_log(user: dict = Depends(require_admin)):
    return await ctrl.get_audit_log(user["org_id"])


@router.get("/jobs")
async def get_jobs(user: dict = Depends(require_admin)):
    return await ctrl.get_jobs(user["org_id"])
