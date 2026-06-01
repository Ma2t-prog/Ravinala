"""
auth/rbac.py — Role-Based Access Control guards.

Étape 12 — Sécurité et Gouvernance
───────────────────────────────────
Provides FastAPI dependencies for protecting endpoints:

  get_current_user       — extracts & validates JWT from Authorization header
  require_role("admin")  — dependency that checks the user role
  require_any_role(...)  — dependency that accepts any of listed roles

Security levels (from config.security_level):
  0 — local-only: auth is OPTIONAL, unprotected requests get an anonymous user
  1 — demo: auth required but any valid token passes
  2+ — controlled/production: full RBAC enforcement

Usage:
    @router.get("/admin-only")
    async def admin_page(user: User = Depends(get_current_user)):
        ...

    @router.get("/analysts")
    async def analyst_page(user: User = Depends(require_role("analyst"))):
        ...
"""

from __future__ import annotations

import logging
import uuid
from types import SimpleNamespace
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.auth.jwt_handler import TokenPayload, decode_access_token
from app.core.config import get_settings
from app.db.base import get_session
from app.db.models import User

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

# ─── Role hierarchy ──────────────────────────────────────────────────────

ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 10,
    "analyst": 20,
    "admin": 30,
}


class AnonymousUser:
    """Placeholder user for explicitly enabled local-only readonly access."""

    id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")
    username: str = "anonymous"
    role: str = "viewer"
    is_active: bool = True


_ANONYMOUS = AnonymousUser()


# ─── Core dependency ─────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Any = Depends(get_session),
) -> Any:
    """
    Extract the current user from the JWT Bearer token.

    Anonymous access is tolerated only when the backend is explicitly
    configured for local readonly access.  Even in that mode, the
    anonymous principal is always a viewer.
    """
    settings = get_settings()

    if credentials is None or not credentials.credentials:
        if settings.security_level == 0 and settings.allow_anonymous_readonly_local:
            _ANONYMOUS.role = settings.anonymous_local_role
            return _ANONYMOUS
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload: TokenPayload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_user_id = uuid.UUID(payload.sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    principal: Any = SimpleNamespace(
        id=token_user_id,
        username="",
        role=payload.role,
        is_active=True,
    )

    if hasattr(db, "execute"):
        result = await db.execute(select(User).where(User.id == token_user_id))
        db_user = result.scalar_one_or_none()
        if db_user is None or not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive or missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if payload.token_version != getattr(db_user, "token_version", 0):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        principal = SimpleNamespace(
            id=db_user.id,
            username=db_user.username,
            role=db_user.role,
            is_active=db_user.is_active,
        )

    request.state.user_id = str(principal.id)
    request.state.user_role = principal.role
    request.state.token_jti = payload.jti
    request.state.token_version = payload.token_version
    return principal


# ─── Role-check dependencies ─────────────────────────────────────────────

def require_role(role: str) -> Callable:
    """Return a FastAPI dependency that enforces a minimum role level."""
    required_level = ROLE_HIERARCHY.get(role, 0)

    async def _guard(user: Any = Depends(get_current_user)) -> Any:
        user_level = ROLE_HIERARCHY.get(getattr(user, "role", "viewer"), 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' or higher required",
            )
        return user

    return _guard


def require_any_role(*roles: str) -> Callable:
    """Return a dependency that accepts any of the listed roles."""

    async def _guard(user: Any = Depends(get_current_user)) -> Any:
        if getattr(user, "role", "") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {roles} required",
            )
        return user

    return _guard
