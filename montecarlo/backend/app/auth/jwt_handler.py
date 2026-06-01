"""
auth/jwt_handler.py — JWT token generation & validation.

Étape 12 — Sécurité et Gouvernance
───────────────────────────────────
Tokens carry:
  sub  — user UUID
  role — user role (viewer / analyst / admin)
  ver  — per-user token version for revocation-on-logout/role-change
  exp  — expiration timestamp (UTC)
  iat  — issued-at timestamp
  jti  — unique token id (for revocation)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings


class TokenPayload:
    """Validated JWT payload."""

    __slots__ = ("sub", "role", "exp", "jti", "token_version")

    def __init__(self, sub: str, role: str, exp: datetime, jti: str, token_version: int):
        self.sub = sub
        self.role = role
        self.exp = exp
        self.jti = jti
        self.token_version = token_version


def create_access_token(
    user_id: str | uuid.UUID,
    role: str,
    token_version: int = 0,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "exp": now + expires_delta,
        "iat": now,
        "jti": uuid.uuid4().hex,
        "ver": token_version,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Raises ``JWTError`` on invalid / expired tokens.
    """
    settings = get_settings()
    try:
        data = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise
    return TokenPayload(
        sub=data["sub"],
        role=data.get("role", "viewer"),
        exp=datetime.fromtimestamp(data["exp"], tz=timezone.utc),
        jti=data.get("jti", ""),
        token_version=int(data.get("ver", 0)),
    )
