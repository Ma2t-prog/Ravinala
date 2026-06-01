"""
auth/password.py — Bcrypt password hashing & verification.

Étape 12 — Sécurité et Gouvernance
───────────────────────────────────
Uses passlib with bcrypt backend.  Automatically handles:
  - Secure hash generation (salt embedded in hash)
  - Constant-time comparison (timing-attack safe)
  - Automatic rehash on scheme upgrade
"""

from __future__ import annotations

from passlib.context import CryptContext

from app.core.config import get_settings

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return bcrypt hash of *plain* password."""
    settings = get_settings()
    if len(plain) < settings.password_min_length:
        raise ValueError(
            f"Password must be at least {settings.password_min_length} characters"
        )
    return _ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time comparison of *plain* against *hashed*."""
    return _ctx.verify(plain, hashed)
