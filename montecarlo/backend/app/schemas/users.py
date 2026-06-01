"""Schemas for user management and security-governance endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: str | None = Field(default=None, pattern=r"^(viewer|analyst|admin)$")
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str
    last_login: str | None = None


class RoleInfo(BaseModel):
    name: str
    level: int
    description: str


class RolesResponse(BaseModel):
    roles: list[RoleInfo]


class AuditEventResponse(BaseModel):
    id: int
    user_id: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    detail: dict[str, Any] | None = None
    ip_address: str | None = None
    created_at: str


class AuditTrailResponse(BaseModel):
    events: list[AuditEventResponse]
    total: int


class SecurityFeatures(BaseModel):
    authentication: bool
    rbac_enforced: bool
    audit_trail: bool
    password_hashing: str


class SecurityStatusResponse(BaseModel):
    security_level: int
    level_name: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    password_min_length: int
    login_max_attempts: int
    login_window_seconds: int
    secret_key_configured: bool
    allow_anonymous_readonly_local: bool
    anonymous_local_role: str
    allow_public_registration: bool
    trust_x_forwarded_for: bool
    features: SecurityFeatures
