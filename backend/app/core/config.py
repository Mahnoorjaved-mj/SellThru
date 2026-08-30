"""Application settings loaded from environment (.env), with fail-fast validation."""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_JWT_SECRET = "super-secret-key-change-in-production-123456"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Core ----
    APP_NAME: str = "Sellthru"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    APP_BASE_URL: str = "http://127.0.0.1:8000"
    FRONTEND_ORIGIN: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---- MongoDB ----
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "sales_forecasting"

    # ---- JWT auth ----
    JWT_SECRET: str = INSECURE_DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 4

    # ---- SMTP / email ----
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Sellthru Alerts"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.FRONTEND_ORIGIN.split(",") if o.strip()]

    def validate_for_boot(self) -> list[str]:
        """Return a list of fatal configuration problems (empty = OK to boot)."""
        problems: list[str] = []
        if not self.MONGO_URI:
            problems.append("MONGO_URI is not set")
        if not self.DEBUG and self.JWT_SECRET == INSECURE_DEFAULT_JWT_SECRET:
            problems.append(
                "JWT_SECRET is still the insecure default — set a real secret before running with DEBUG=False"
            )
        if not self.DEBUG and len(self.JWT_SECRET) < 32:
            problems.append("JWT_SECRET should be at least 32 characters in production")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
