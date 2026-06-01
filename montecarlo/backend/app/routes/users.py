"""
routes/users.py — User management and audit trail endpoints.

Étape 12 — Sécurité et Gouvernance
───────────────────────────────────
  GET    /api/v1/users               — list users (admin only)
  GET    /api/v1/users/{user_id}     — get user detail
  PUT    /api/v1/users/{user_id}     — update user (self or admin)
  DELETE /api/v1/users/{user_id}     — deactivate user (admin only)
  GET    /api/v1/roles               — list available roles
  GET    /api/v1/audit-trail         — recent audit events (admin only)
  GET    /api/v1/security/status     — security maturity & config
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import get_current_user, require_role
from app.db.base import get_session
from app.schemas.users import (
    AuditTrailResponse,
    RolesResponse,
    SecurityStatusResponse,
    UserResponse,
    UserUpdate,
)
from app.services.identity_service import (
    client_ip_from_request,
    deactivate_user,
    fetch_audit_trail,
    get_roles_catalog,
    get_security_status,
    get_visible_user,
    list_registered_users,
    update_managed_user,
)

router = APIRouter(tags=["users"])


@router.get("/api/v1/users", response_model=list[UserResponse])
async def list_users(
    admin: Any = Depends(require_role("admin")),
    db: Optional[AsyncSession] = Depends(get_session),
) -> list[UserResponse]:
    """List all users (admin only)."""
    return await list_registered_users(db=db)


@router.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: Any = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_session),
) -> UserResponse:
    """Get user detail. Viewers can only see their own profile."""
    return await get_visible_user(user_id, current_user=current_user, db=db)


@router.put("/api/v1/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    request: Request,
    current_user: Any = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_session),
) -> UserResponse:
    """Update user. Non-admins can only update their own email."""
    return await update_managed_user(
        user_id,
        body,
        current_user=current_user,
        db=db,
        ip_address=client_ip_from_request(request),
    )


@router.delete("/api/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    admin: Any = Depends(require_role("admin")),
    db: Optional[AsyncSession] = Depends(get_session),
) -> None:
    """Soft-delete (deactivate) a user. Admin only."""
    await deactivate_user(
        user_id,
        admin_user=admin,
        db=db,
        ip_address=client_ip_from_request(request),
    )


@router.get("/api/v1/roles", response_model=RolesResponse)
async def list_roles() -> RolesResponse:
    """List available roles and their hierarchy."""
    return get_roles_catalog()


@router.get("/api/v1/audit-trail", response_model=AuditTrailResponse)
async def audit_trail(
    limit: int = Query(default=100, ge=1, le=1000),
    user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    admin: Any = Depends(require_role("admin")),
    db: Optional[AsyncSession] = Depends(get_session),
) -> AuditTrailResponse:
    """Query audit trail. Admin only."""
    return await fetch_audit_trail(limit=limit, user_id=user_id, action=action, db=db)


@router.get("/api/v1/security/status", response_model=SecurityStatusResponse)
async def security_status(
    admin: Any = Depends(require_role("admin")),
) -> SecurityStatusResponse:
    """Current security maturity level and configuration. Admin only."""
    return get_security_status()
