"""
routes/auth.py — Authentication endpoints.

Étape 12 — Sécurité et Gouvernance
───────────────────────────────────
  POST /api/v1/auth/register  — create a new user account
  POST /api/v1/auth/login     — authenticate and get JWT token
  POST /api/v1/auth/logout    — revoke current user's active tokens
  GET  /api/v1/auth/me        — current user info from token
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import get_current_user
from app.db.base import get_session
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.services.identity_service import (
    authenticate_user,
    client_ip_from_request,
    get_current_user_info,
    record_logout,
    register_public_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: Optional[AsyncSession] = Depends(get_session),
) -> UserInfo:
    """Create a new user account."""
    return await register_public_user(
        body,
        db=db,
        ip_address=client_ip_from_request(request),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: Optional[AsyncSession] = Depends(get_session),
) -> TokenResponse:
    """Authenticate user and return a JWT access token."""
    return await authenticate_user(
        body,
        db=db,
        ip_address=client_ip_from_request(request),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout(
    request: Request,
    user: Any = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_session),
) -> None:
    """Log out and revoke active tokens for the current user."""
    await record_logout(
        user,
        db=db,
        ip_address=client_ip_from_request(request),
    )


@router.get("/me", response_model=UserInfo)
async def me(
    user: Any = Depends(get_current_user),
    db: Optional[AsyncSession] = Depends(get_session),
) -> UserInfo:
    """Return current user info from the JWT token."""
    return await get_current_user_info(user, db=db)
