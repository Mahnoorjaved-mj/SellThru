"""Password hashing, JWT tokens, and validation helpers."""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from email_validator import EmailNotValidError, validate_email
from jose import JWTError, jwt
from app.core.config import settings

PASSWORD_MIN_LEN = 10
REFRESH_TOKEN_TTL_DAYS = 30


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def validate_password(pw: str) -> Optional[str]:
    """Return an error string if invalid, else None.

    Rules: min 10 chars, at least one letter and one digit.
    """
    if not pw or len(pw) < PASSWORD_MIN_LEN:
        return f"Password must be at least {PASSWORD_MIN_LEN} characters"
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain at least one letter and one digit"
    return None


def validate_email_address(em: str) -> Optional[str]:
    try:
        validate_email(em, check_deliverability=False)
        return None
    except EmailNotValidError as e:
        return str(e)


def create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Refresh tokens are opaque random strings, not JWTs — hash before storing
    so a database read alone can't be replayed as a valid session."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
