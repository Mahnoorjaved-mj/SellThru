"""Auth routes. Mounted at /auth (legacy) and /api/v1/auth (canonical)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.services import auth_service as ctrl
from app.schemas.common import serialize
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ProfileUpdate,
    RegisterRequest,
    ResetPasswordRequest,
    TwoFAVerifyRequest,
    VerifyOtpRequest,
)
from app.core.deps import get_current_user


class RefreshRequest(BaseModel):
    refresh_token: str

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest, request: Request):
    return await ctrl.register(body.email, body.password, body.name, request)


@router.post("/verify-otp")
async def verify_otp(body: VerifyOtpRequest, request: Request):
    return await ctrl.verify_otp(body.email, body.otp, request)


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    return await ctrl.login(body.email, body.password, request)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    return await ctrl.forgot_password(body.email, request)


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, request: Request):
    return await ctrl.reset_password(body.token, body.password, request)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    from app.repositories import twofa_repo

    safe = serialize(user) or {}
    safe.pop("password_hash", None)
    twofa_row = await twofa_repo.find_by_user(str(user["_id"]))
    safe["is_2fa_enabled"] = bool(twofa_row and twofa_row.get("enabled"))
    return {"status": "success", "user": safe}


@router.post("/logout")
async def logout(request: Request, user: dict = Depends(get_current_user)):
    from app.services.audit_service import log_event
    await log_event("logout", user_id=str(user["_id"]), org_id=user.get("org_id"), request=request)
    return {"status": "success"}


@router.post("/refresh")
async def refresh(body: RefreshRequest, request: Request):
    return await ctrl.refresh_access_token(body.refresh_token, request)


@router.get("/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    return await ctrl.list_sessions(str(user["_id"]))


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.revoke_session(str(user["_id"]), session_id, request)


@router.post("/logout-all")
async def logout_all(request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.logout_all(str(user["_id"]), request)


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.change_password(user, body.old_password, body.new_password, request)


@router.patch("/profile")
async def update_profile(body: ProfileUpdate, request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.update_profile(user, body.model_dump(exclude_none=True), request)


@router.post("/2fa/setup")
async def twofa_setup(request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.twofa_setup(user, request)


@router.post("/2fa/verify")
async def twofa_verify(
    body: TwoFAVerifyRequest, request: Request, user: dict = Depends(get_current_user)
):
    return await ctrl.twofa_verify(user, body.code, request)


@router.post("/2fa/disable")
async def twofa_disable(request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.twofa_disable(user, request)


@router.post("/2fa/recovery")
async def twofa_recovery(
    body: TwoFAVerifyRequest, request: Request, user: dict = Depends(get_current_user)
):
    return await ctrl.twofa_verify_recovery_code(user, body.code, request)
