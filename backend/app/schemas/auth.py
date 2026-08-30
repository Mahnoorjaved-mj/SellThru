"""Pydantic request/response schemas for auth + profile."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ---- Auth requests ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class TwoFAVerifyRequest(BaseModel):
    code: str


# ---- Profile update ----
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    notification_frequency: Optional[str] = None  # off | daily | weekly
