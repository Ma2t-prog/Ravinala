"""
Centralized configuration — single source of truth for backend settings.

Usage:
    from app.core.config import get_settings
    settings = get_settings()
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    db_user: str = "ravinala"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ravinala"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # API
    api_version: str = "v1"
    log_level: str = "WARNING"
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"

    # Authentication — Étape 12
    secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    password_min_length: int = 8

    # Security maturity level (0=local, 1=demo, 2=controlled, 3=production)
    security_level: int = 0
    allow_anonymous_readonly_local: bool = True
    anonymous_local_role: str = "viewer"
    allow_public_registration: bool | None = None
    trust_x_forwarded_for: bool = False
    login_max_attempts: int = 5
    login_window_seconds: int = 300

    # ML
    mlflow_tracking_uri: str = ""

    # External data providers
    fred_api_key: str = ""  # FRED API key for live bond + macro data (free at fred.stlouisfed.org)

    # Quant conventions (single source of truth for backend defaults)
    risk_free_rate: float = 0.043
    risk_free_rate_source: str = "US 10Y Treasury demo baseline"
    risk_free_rate_last_updated: str = "2026-03-23"
    trading_days_per_year: int = 252
    annualization_factor: float = 252.0  # arithmetic annualisation for return-like metrics

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.security_level not in {0, 1, 2, 3}:
            raise ValueError("security_level must be one of: 0, 1, 2, 3")
        if self.allow_public_registration is None:
            self.allow_public_registration = self.security_level <= 1
        if self.anonymous_local_role != "viewer":
            raise ValueError("anonymous_local_role is restricted to 'viewer'")
        if self.security_level >= 1 and self.secret_key == "CHANGE-ME-IN-PRODUCTION":
            raise ValueError(
                "SECRET_KEY or JWT_SECRET_KEY must be configured when security_level >= 1"
            )
        # S1.2 — trust_x_forwarded_for=True is only safe behind a trusted reverse-proxy
        # (security_level >= 2).  At lower levels, it enables IP spoofing.
        if self.trust_x_forwarded_for and self.security_level < 2:
            raise ValueError(
                "trust_x_forwarded_for=True requires security_level >= 2 "
                "(enables IP spoofing at lower security levels)"
            )
        # S2.4 — anonymous access is incompatible with controlled / production environments
        if self.security_level >= 2 and self.allow_anonymous_readonly_local:
            raise ValueError(
                "allow_anonymous_readonly_local must be False when security_level >= 2"
            )
        # S3.2 — CORS must not include localhost/127.0.0.1 in controlled environments
        if self.security_level >= 2:
            localhost_origins = [
                o for o in self.cors_allowed_origins_list
                if "localhost" in o.lower() or "127.0.0.1" in o
            ]
            if localhost_origins:
                raise ValueError(
                    "cors_allowed_origins must not include localhost/127.0.0.1 "
                    f"when security_level >= 2: {localhost_origins}"
                )
        if self.login_max_attempts <= 0:
            raise ValueError("login_max_attempts must be > 0")
        if self.login_window_seconds <= 0:
            raise ValueError("login_window_seconds must be > 0")
        if not 0 <= self.risk_free_rate <= 1:
            raise ValueError("risk_free_rate must be expressed as a decimal between 0 and 1")
        if self.trading_days_per_year <= 0:
            raise ValueError("trading_days_per_year must be > 0")
        if self.annualization_factor <= 0:
            raise ValueError("annualization_factor must be > 0")
        if not self.risk_free_rate_source.strip():
            raise ValueError("risk_free_rate_source must not be empty")
        if not self.risk_free_rate_last_updated.strip():
            raise ValueError("risk_free_rate_last_updated must not be empty")
        if not self.cors_allowed_origins.strip():
            raise ValueError("cors_allowed_origins must not be empty")
        return self

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
