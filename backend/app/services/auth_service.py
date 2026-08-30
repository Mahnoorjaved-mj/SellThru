"""Auth business logic — Mongo + JWT."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request

from app.repositories import otp_repo, organizations_repo, reset_tokens_repo, sessions_repo, twofa_repo, users_repo
from app.schemas.common import serialize
from app.services import email_service
from app.services.audit_service import log_event
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    validate_email_address,
    validate_password,
    verify_password,
)

OTP_TTL_MIN = 10
RESET_TOKEN_TTL_HOURS = 1


def _public_user(doc: dict) -> dict:
    """Strip secrets from a user doc before returning to the client."""
    safe = serialize(doc) or {}
    safe.pop("password_hash", None)
    return safe


def _client_meta(request: Request) -> dict:
    ip = None
    user_agent = None
    if request is not None:
        try:
            ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
            if ip and "," in ip:
                ip = ip.split(",")[0].strip()
            user_agent = (request.headers.get("user-agent") or "")[:256]
        except Exception:
            pass
    return {"ip": ip, "user_agent": user_agent}


async def _issue_tokens(user: dict, request: Request) -> dict:
    """Access token (short-lived JWT) + refresh token (opaque, rotated on use, stored hashed)."""
    access_token = create_access_token(str(user["_id"]), user["email"])
    refresh_token = generate_refresh_token()
    await sessions_repo.insert({
        "user_id": str(user["_id"]),
        "org_id": user.get("org_id"),
        "token_hash": hash_refresh_token(refresh_token),
        "expires_at": refresh_token_expiry(),
        **_client_meta(request),
    })
    return {"token": access_token, "refresh_token": refresh_token}


async def register(email: str, password: str, name: str | None, request: Request) -> dict:
    email = (email or "").strip().lower()
    err = validate_email_address(email) or validate_password(password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    if await users_repo.find_by_email(email):
        await log_event("register_email_taken", request=request, metadata={"email": email})
        raise HTTPException(status_code=409, detail="An account with that email already exists")

    # OTP rate-limit: max 3 attempts within the TTL window
    window_start = datetime.now(timezone.utc) - timedelta(minutes=OTP_TTL_MIN)
    recent = await otp_repo.count_recent(email, window_start)
    if recent >= 3:
        await log_event("register_otp_rate_limited", request=request, metadata={"email": email})
        raise HTTPException(
            status_code=429, detail="Too many verification attempts — try again in a few minutes"
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(timezone.utc)
    await otp_repo.delete_by_email(email)
    await otp_repo.insert(
        {
            "email": email,
            "otp": code,
            "password_hash": hash_password(password),
            "name": (name or "").strip() or None,
            "expires_at": now + timedelta(minutes=OTP_TTL_MIN),
            "created_at": now,
        }
    )
    email_service.send_otp(email, code)
    await log_event("register_otp_sent", request=request, metadata={"email": email})
    return {"status": "success", "message": "OTP sent to your email"}


async def verify_otp(email: str, code: str, request: Request) -> dict:
    email = (email or "").strip().lower()
    code = (code or "").strip()
    rec = await otp_repo.find_valid(email, code, datetime.now(timezone.utc))
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    now = datetime.now(timezone.utc)
    existing = await users_repo.find_by_email(email)
    if existing:
        user = existing
    else:
        # Determine if this user is the first user; if so, make them an Admin
        total_users = await users_repo.count_all()
        is_admin = total_users == 0
        org_id = await organizations_repo.ensure_default()

        doc = {
            "email": rec["email"],
            "password_hash": rec["password_hash"],
            "name": rec.get("name"),
            "is_admin": is_admin,
            "role": "admin" if is_admin else "user",
            "is_suspended": False,
            "org_id": org_id,
            "notification_frequency": "weekly",
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
        }
        user = await users_repo.insert_user(doc)

    await otp_repo.delete_by_email(email)
    email_service.send_welcome(email, rec.get("name"))
    await log_event("register_success", user_id=str(user["_id"]), org_id=user.get("org_id"), request=request)
    tokens = await _issue_tokens(user, request)
    return {"status": "success", **tokens, "user": _public_user(user)}


async def login(email: str, password: str, request: Request) -> dict:
    email = (email or "").strip().lower()
    user = await users_repo.find_by_email(email)
    if not user or not verify_password(password, user.get("password_hash", "")):
        await log_event("login_failed", request=request, metadata={"email": email})
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("is_suspended"):
        await log_event("login_blocked_suspended", user_id=str(user["_id"]), request=request)
        raise HTTPException(status_code=403, detail="This account has been suspended")

    await users_repo.update_last_login(str(user["_id"]))
    await log_event("login_success", user_id=str(user["_id"]), org_id=user.get("org_id"), request=request)
    tokens = await _issue_tokens(user, request)
    return {"status": "success", **tokens, "user": _public_user(user)}


async def refresh_access_token(refresh_token: str, request: Request) -> dict:
    """Rotate a refresh token: the presented token is consumed and a new pair issued.

    Reuse detection: if a token that's already been revoked (i.e. already
    rotated once before) is presented again, that's a signal the token was
    stolen and replayed — every session for that user is revoked so both the
    legitimate user and the attacker are logged out, forcing a fresh login.
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    token_hash = hash_refresh_token(refresh_token)
    session = await sessions_repo.find_by_token_hash(token_hash)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if session.get("revoked_at") is not None:
        await sessions_repo.revoke_all_for_user(session["user_id"])
        await log_event("refresh_token_reuse_detected", user_id=session["user_id"], request=request)
        raise HTTPException(status_code=401, detail="Session invalidated — please log in again")

    if session["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired — please log in again")

    user = await users_repo.find_by_id(session["user_id"])
    if not user or user.get("is_suspended"):
        raise HTTPException(status_code=401, detail="Account unavailable")

    await sessions_repo.revoke(str(session["_id"]))
    tokens = await _issue_tokens(user, request)
    return {"status": "success", **tokens, "user": _public_user(user)}


async def list_sessions(user_id: str) -> dict:
    docs = await sessions_repo.list_active_for_user(user_id)
    return {"status": "success", "sessions": [serialize(d) for d in docs]}


async def revoke_session(user_id: str, session_id: str, request: Request) -> dict:
    session = await sessions_repo.find_by_id_for_user(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await sessions_repo.revoke(session_id)
    await log_event("session_revoked", user_id=user_id, request=request)
    return {"status": "success", "message": "Session revoked"}


async def logout_all(user_id: str, request: Request) -> dict:
    await sessions_repo.revoke_all_for_user(user_id)
    await log_event("logout_all_sessions", user_id=user_id, request=request)
    return {"status": "success", "message": "All sessions signed out"}


async def forgot_password(email: str, request: Request) -> dict:
    email = (email or "").strip().lower()
    user = await users_repo.find_by_email(email)
    if user:
        token = secrets.token_urlsafe(32)
        await reset_tokens_repo.insert(
            {
                "user_id": str(user["_id"]),
                "token": token,
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS),
                "used": False,
                "created_at": datetime.now(timezone.utc),
            }
        )
        email_service.send_password_reset(email, token)
        await log_event("password_reset_requested", user_id=str(user["_id"]), request=request)
    return {"status": "success", "message": "If that email exists, a reset link has been sent"}


async def reset_password(token: str, new_password: str, request: Request) -> dict:
    token = (token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
    err = validate_password(new_password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    rec = await reset_tokens_repo.find_valid(token, datetime.now(timezone.utc))
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    await users_repo.update_password_hash(rec["user_id"], hash_password(new_password))
    await reset_tokens_repo.mark_used(rec["_id"])
    await log_event("password_reset_completed", user_id=rec["user_id"], request=request)
    return {"status": "success", "message": "Password updated"}


async def change_password(user: dict, old_password: str, new_password: str, request: Request) -> dict:
    if not verify_password(old_password, user.get("password_hash", "")):
        await log_event("change_password_failed", user_id=str(user["_id"]), request=request)
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    err = validate_password(new_password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    await users_repo.update_password_hash(str(user["_id"]), hash_password(new_password))
    await sessions_repo.revoke_all_for_user(str(user["_id"]))
    await log_event("change_password_success", user_id=str(user["_id"]), request=request)
    return {"status": "success", "message": "Password changed — all other sessions were signed out"}


async def update_profile(user: dict, fields: dict, request: Request) -> dict:
    if not fields:
        return {"status": "success", "user": _public_user(user)}
    await users_repo.update_fields(str(user["_id"]), fields)
    updated = await users_repo.find_by_id(str(user["_id"]))
    await log_event("profile_updated", user_id=str(user["_id"]), request=request, metadata={"fields": list(fields.keys())})
    return {"status": "success", "user": _public_user(updated)}


async def twofa_setup(user: dict, request: Request) -> dict:
    import hashlib
    import pyotp
    secret = pyotp.random_base32()
    recovery_codes = [secrets.token_hex(5) for _ in range(10)]
    hashes = [hashlib.sha256(c.encode("utf-8")).hexdigest() for c in recovery_codes]
    await twofa_repo.upsert_secret(str(user["_id"]), secret, hashes)
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user["email"], issuer_name="Sellthru")
    # Recovery codes are only ever shown here, in plaintext, once — the DB only has hashes.
    return {"status": "success", "secret": secret, "otpauth": uri, "recovery_codes": recovery_codes}


async def twofa_verify(user: dict, code: str, request: Request) -> dict:
    import pyotp
    code = (code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code required")
    row = await twofa_repo.find_by_user(str(user["_id"]))
    if not row:
        raise HTTPException(status_code=400, detail="Run 2FA setup first")
    if not pyotp.TOTP(row["secret"]).verify(code, valid_window=1):
        await log_event("2fa_verify_failed", user_id=str(user["_id"]), request=request)
        raise HTTPException(status_code=400, detail="Invalid code")
    await twofa_repo.mark_enabled(str(user["_id"]))
    await log_event("2fa_enabled", user_id=str(user["_id"]), request=request)
    return {"status": "success", "message": "2FA enabled"}


async def twofa_verify_recovery_code(user: dict, code: str, request: Request) -> dict:
    import hashlib
    code_hash = hashlib.sha256((code or "").strip().encode("utf-8")).hexdigest()
    consumed = await twofa_repo.consume_recovery_code(str(user["_id"]), code_hash)
    if not consumed:
        await log_event("2fa_recovery_failed", user_id=str(user["_id"]), request=request)
        raise HTTPException(status_code=400, detail="Invalid or already-used recovery code")
    await log_event("2fa_recovery_used", user_id=str(user["_id"]), request=request)
    return {"status": "success", "message": "Recovery code accepted — consider disabling and re-enabling 2FA to get a fresh code set"}


async def twofa_disable(user: dict, request: Request) -> dict:
    await twofa_repo.delete_by_user(str(user["_id"]))
    await log_event("2fa_disabled", user_id=str(user["_id"]), request=request)
    return {"status": "success", "message": "2FA disabled"}
