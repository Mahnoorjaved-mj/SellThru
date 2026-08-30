"""FastAPI dependencies for auth: current user + admin guard."""
from __future__ import annotations

from bson.errors import InvalidId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.repositories import organizations_repo, users_repo
from app.repositories.base import users

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    payload = decode_token(creds.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    try:
        user = await users_repo.find_by_id(payload["sub"])
    except (InvalidId, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user.get("is_suspended"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been suspended")

    if not user.get("org_id"):
        # Defensive self-heal: every user should get org_id at creation/backfill time,
        # but never let a request proceed without a tenant scope.
        org_id = await organizations_repo.ensure_default()
        await users().update_one({"_id": user["_id"]}, {"$set": {"org_id": org_id}})
        user["org_id"] = org_id

    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
