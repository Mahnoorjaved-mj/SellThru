"""Admin panel service: org-scoped overview, user management, audit log, jobs view.

Everything here is scoped to the caller's own org_id — there is no
cross-org browsing yet (that needs the organizations/membership model from
Section 6.3, which isn't built). This is "admin of my own organization",
not a superadmin console across tenants.
"""
from __future__ import annotations

from fastapi import HTTPException

from app.repositories import (
    audit_repo, imports_repo, models_repo, products_repo,
    sales_repo, stores_repo, users_repo,
)
from app.schemas.common import serialize

VALID_ROLES = {"user", "analyst", "manager", "admin"}


async def get_overview(org_id: str) -> dict:
    users_count = await users_repo.count_by_org(org_id)
    stores_count = len(await stores_repo.list_all(org_id))
    products_count = len(await products_repo.list_all(org_id))
    transactions_count = await sales_repo.count(org_id)
    imports = await imports_repo.list_recent(org_id, limit=10)
    models = await models_repo.list_recent(org_id, limit=5)
    active_model = await models_repo.find_active(org_id)

    return {
        "status": "success",
        "stats": {
            "users": users_count,
            "stores": stores_count,
            "products": products_count,
            "transactions": transactions_count,
            "models_trained": len(await models_repo.list_recent(org_id, limit=1000)),
            "active_model_version": active_model.get("version") if active_model else None,
        },
        "recent_imports": [serialize(d) for d in imports],
        "recent_models": [serialize(d) for d in models],
    }


async def list_users(org_id: str) -> dict:
    docs = await users_repo.list_by_org(org_id)
    safe = []
    for d in docs:
        s = serialize(d) or {}
        s.pop("password_hash", None)
        safe.append(s)
    return {"status": "success", "users": safe}


async def change_user_role(org_id: str, actor_id: str, target_user_id: str, role: str) -> dict:
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role '{role}'")
    target = await users_repo.find_by_id(target_user_id)
    if not target or str(target.get("org_id")) != org_id:
        raise HTTPException(status_code=404, detail="User not found in this organization")
    if str(target["_id"]) == actor_id and role != "admin":
        raise HTTPException(status_code=400, detail="You can't demote your own account")
    await users_repo.set_role(target_user_id, role, is_admin=(role == "admin"))
    return {"status": "success", "message": f"Role updated to {role}"}


async def set_user_suspended(org_id: str, actor_id: str, target_user_id: str, suspended: bool) -> dict:
    target = await users_repo.find_by_id(target_user_id)
    if not target or str(target.get("org_id")) != org_id:
        raise HTTPException(status_code=404, detail="User not found in this organization")
    if str(target["_id"]) == actor_id:
        raise HTTPException(status_code=400, detail="You can't suspend your own account")
    await users_repo.set_suspended(target_user_id, suspended)
    return {"status": "success", "message": "User suspended" if suspended else "User reactivated"}


async def get_audit_log(org_id: str, limit: int = 200) -> dict:
    docs = await audit_repo.list_by_org(org_id, limit)
    return {"status": "success", "events": [serialize(d) for d in docs]}


async def get_jobs(org_id: str) -> dict:
    """Unified view of background-ish work: CSV imports + model training runs."""
    imports = await imports_repo.list_recent(org_id, limit=50)
    models = await models_repo.list_recent(org_id, limit=50)

    jobs = []
    for d in imports:
        jobs.append({
            "type": "import",
            "id": str(d["_id"]),
            "label": d.get("filename"),
            "status": d.get("status"),
            "detail": f"{d.get('rows_imported', 0)} imported, {d.get('rows_failed', 0)} failed",
            "created_at": d.get("created_at"),
        })
    for d in models:
        jobs.append({
            "type": "model_training",
            "id": str(d["_id"]),
            "label": d.get("version"),
            "status": d.get("status"),
            "detail": f"WAPE {d.get('metrics', {}).get('wape', '—')}%",
            "created_at": d.get("trained_at"),
        })

    from datetime import datetime, timezone

    jobs.sort(key=lambda j: j["created_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    for j in jobs:
        j["created_at"] = j["created_at"].isoformat() if j["created_at"] else None
    return {"status": "success", "jobs": jobs[:50]}
