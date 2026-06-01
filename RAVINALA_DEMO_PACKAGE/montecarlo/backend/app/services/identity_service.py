"""
services/identity_service.py - shared auth and user-management service.

Centralises security-sensitive user flows so routes stay as controllers and
do not own password, token, audit or DB mutation logic directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.audit import fire_audit
from app.auth.jwt_handler import create_access_token
from app.auth.password import hash_password, verify_password
from app.auth.rbac import ROLE_HIERARCHY
from app.core.config import get_settings
from app.db.models import AuditEvent, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.schemas.users import (
    AuditEventResponse,
    AuditTrailResponse,
    RoleInfo,
    RolesResponse,
    SecurityFeatures,
    SecurityStatusResponse,
    UserResponse,
    UserUpdate,
)

_ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"

_ROLE_DESCRIPTIONS = {
    "viewer": "Read-only access to dashboards and public data",
    "analyst": "Full read + execute backtests, ML models, risk computations",
    "admin": "Full access including user management, configuration, and audit trail",
}

_LEVEL_NAMES = {
    0: "local_only",
    1: "internal_demo",
    2: "controlled_testing",
    3: "production",
}

class _ThrottleStore:
    """
    Login failure tracking — Redis-backed when available, in-memory fallback.
    Redis ensures state survives restarts and is shared across workers.
    In-memory fallback maintains protection within a single process.
    """

    _REDIS_KEY_PREFIX = "login_fail:"

    def __init__(self) -> None:
        self._memory: dict[str, list[datetime]] = {}

    def _redis(self):
        """Return Redis client if available, else None."""
        try:
            from app.services.cache import get_cache  # deferred to avoid circular import
            cache = get_cache()
            return getattr(cache, "redis", None)
        except Exception:
            return None

    def get_recent(self, key: str, window_seconds: int) -> list[datetime]:
        r = self._redis()
        now = _utc_now()
        if r:
            raw = r.lrange(f"{self._REDIS_KEY_PREFIX}{key}", 0, -1)
            return [
                ts for raw_ts in raw
                if (ts := datetime.fromisoformat(raw_ts)) and (now - ts).total_seconds() < window_seconds
            ]
        recent = [
            ts for ts in self._memory.get(key, [])
            if (now - ts).total_seconds() < window_seconds
        ]
        if recent:
            self._memory[key] = recent
        else:
            self._memory.pop(key, None)
        return recent

    def record_failure(self, key: str, ts: datetime, window_seconds: int) -> None:
        r = self._redis()
        if r:
            redis_key = f"{self._REDIS_KEY_PREFIX}{key}"
            r.rpush(redis_key, ts.isoformat())
            r.expire(redis_key, window_seconds + 10)
        else:
            self._memory.setdefault(key, []).append(ts)

    def clear(self, key: str) -> None:
        r = self._redis()
        if r:
            r.delete(f"{self._REDIS_KEY_PREFIX}{key}")
        else:
            self._memory.pop(key, None)


_throttle_store = _ThrottleStore()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _login_throttle_key(username: str, ip_address: str) -> str:
    return f"{username.lower()}|{ip_address}"


def _check_login_throttle(username: str, ip_address: str) -> None:
    settings = get_settings()
    key = _login_throttle_key(username, ip_address)
    recent = _throttle_store.get_recent(key, settings.login_window_seconds)
    if len(recent) >= settings.login_max_attempts:
        fire_audit(
            action="LOGIN_THROTTLED",
            detail={"identifier": username, "attempts": len(recent)},
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )


def _record_login_failure(username: str, ip_address: str) -> None:
    settings = get_settings()
    key = _login_throttle_key(username, ip_address)
    _throttle_store.record_failure(key, _utc_now(), settings.login_window_seconds)


def _clear_login_failures(username: str, ip_address: str) -> None:
    _throttle_store.clear(_login_throttle_key(username, ip_address))


def client_ip_from_request(request: Any) -> str:
    settings = get_settings()
    forwarded = (
        request.headers.get("X-Forwarded-For")
        if request and settings.trust_x_forwarded_for
        else None
    )
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = getattr(request, "client", None)
    return client.host if client else "unknown"


def _invalidate_user_tokens(user: User) -> None:
    user.token_version = int(getattr(user, "token_version", 0)) + 1


def _user_info_from_user(user: User) -> UserInfo:
    return UserInfo(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


def _user_response_from_user(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


def _ensure_db(db: AsyncSession | None, detail: str) -> AsyncSession:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    return db


async def register_public_user(
    body: RegisterRequest,
    *,
    db: AsyncSession | None,
    ip_address: str,
) -> UserInfo:
    session = _ensure_db(db, "Database not configured — registration unavailable")
    settings = get_settings()

    if not settings.allow_public_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled",
        )

    if body.role != "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration can only create viewer accounts",
        )

    existing = await session.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        is_active=True,
    )
    session.add(user)
    await session.flush()

    fire_audit(
        action="CREATE",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        detail={"username": body.username, "role": body.role},
        ip_address=ip_address,
    )
    return _user_info_from_user(user)


async def authenticate_user(
    body: LoginRequest,
    *,
    db: AsyncSession | None,
    ip_address: str,
) -> TokenResponse:
    session = _ensure_db(db, "Database not configured — login unavailable")
    _check_login_throttle(body.email, ip_address)

    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if (
        user is None
        or not user.is_active
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        _record_login_failure(body.email, ip_address)
        fire_audit(
            action="LOGIN_FAILED",
            detail={"email": body.email},
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user.last_login = datetime.now(timezone.utc)
    _clear_login_failures(body.email, ip_address)
    settings = get_settings()
    token = create_access_token(
        user_id=user.id,
        role=user.role,
        token_version=user.token_version,
    )

    fire_audit(
        action="LOGIN",
        user_id=user.id,
        resource_type="session",
        detail={"username": user.username},
        ip_address=ip_address,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
        role=user.role,
    )


async def record_logout(
    user: Any,
    *,
    db: AsyncSession | None,
    ip_address: str,
) -> None:
    user_id = getattr(user, "id", None)
    if db is not None and user_id and str(user_id) != _ANONYMOUS_USER_ID:
        result = await db.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user is not None:
            _invalidate_user_tokens(db_user)

    fire_audit(
        action="LOGOUT",
        user_id=user_id,
        resource_type="session",
        ip_address=ip_address,
    )


async def get_current_user_info(user: Any, *, db: AsyncSession | None) -> UserInfo:
    user_id = getattr(user, "id", None)

    if db is not None and user_id and str(user_id) != _ANONYMOUS_USER_ID:
        result = await db.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user:
            return _user_info_from_user(db_user)

    return UserInfo(
        id=str(user_id) if user_id else "anonymous",
        username=getattr(user, "username", "anonymous"),
        email="",
        role=getattr(user, "role", "viewer"),
        is_active=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


async def list_registered_users(*, db: AsyncSession | None) -> list[UserResponse]:
    if db is None:
        return []

    result = await db.execute(select(User).order_by(User.created_at))
    return [_user_response_from_user(user) for user in result.scalars().all()]


async def get_visible_user(
    user_id: uuid.UUID,
    *,
    current_user: Any,
    db: AsyncSession | None,
) -> UserResponse:
    session = _ensure_db(db, "Database not configured")

    caller_role = getattr(current_user, "role", "viewer")
    caller_id = getattr(current_user, "id", None)
    if caller_role != "admin" and str(caller_id) != str(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_response_from_user(user)


async def update_managed_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    *,
    current_user: Any,
    db: AsyncSession | None,
    ip_address: str,
) -> UserResponse:
    session = _ensure_db(db, "Database not configured")

    caller_role = getattr(current_user, "role", "viewer")
    caller_id = getattr(current_user, "id", None)
    is_self = str(caller_id) == str(user_id)

    if not is_self and caller_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if caller_role != "admin" and (body.role is not None or body.is_active is not None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can modify role or activation state",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    changes: dict[str, Any] = {}

    if body.email is not None and body.email != user.email:
        existing = await session.execute(
            select(User.id).where((User.email == body.email) & (User.id != user_id))
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )
        user.email = body.email
        changes["email"] = body.email

    if body.role is not None and caller_role == "admin" and body.role != user.role:
        user.role = body.role
        changes["role"] = body.role

    if body.is_active is not None and caller_role == "admin" and body.is_active != user.is_active:
        user.is_active = body.is_active
        changes["is_active"] = body.is_active

    if "role" in changes or "is_active" in changes:
        _invalidate_user_tokens(user)

    if changes:
        fire_audit(
            action="UPDATE",
            user_id=caller_id,
            resource_type="user",
            resource_id=str(user_id),
            detail=changes,
            ip_address=ip_address,
        )

    return _user_response_from_user(user)


async def deactivate_user(
    user_id: uuid.UUID,
    *,
    admin_user: Any,
    db: AsyncSession | None,
    ip_address: str,
) -> None:
    session = _ensure_db(db, "Database not configured")

    if str(getattr(admin_user, "id", None)) == str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin self-deactivation is forbidden",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_active:
        user.is_active = False
        _invalidate_user_tokens(user)
    fire_audit(
        action="DELETE",
        user_id=getattr(admin_user, "id", None),
        resource_type="user",
        resource_id=str(user_id),
        detail={"username": user.username, "deactivated": True},
        ip_address=ip_address,
    )


def get_roles_catalog() -> RolesResponse:
    return RolesResponse(
        roles=[
            RoleInfo(name=name, level=level, description=_ROLE_DESCRIPTIONS.get(name, ""))
            for name, level in sorted(ROLE_HIERARCHY.items(), key=lambda item: item[1])
        ]
    )


async def fetch_audit_trail(
    *,
    limit: int,
    user_id: uuid.UUID | None,
    action: str | None,
    db: AsyncSession | None,
) -> AuditTrailResponse:
    if db is None:
        return AuditTrailResponse(events=[], total=0)

    query = select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit)
    if user_id is not None:
        query = query.where(AuditEvent.user_id == user_id)
    if action is not None:
        query = query.where(AuditEvent.action == action)

    result = await db.execute(query)
    events = result.scalars().all()
    return AuditTrailResponse(
        events=[
            AuditEventResponse(
                id=event.id,
                user_id=str(event.user_id) if event.user_id else None,
                action=event.action,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                detail=event.detail,
                ip_address=event.ip_address,
                created_at=event.created_at.isoformat(),
            )
            for event in events
        ],
        total=len(events),
    )


def get_security_status() -> SecurityStatusResponse:
    settings = get_settings()
    return SecurityStatusResponse(
        security_level=settings.security_level,
        level_name=_LEVEL_NAMES.get(settings.security_level, "unknown"),
        jwt_algorithm=settings.jwt_algorithm,
        jwt_expire_minutes=settings.jwt_expire_minutes,
        password_min_length=settings.password_min_length,
        login_max_attempts=settings.login_max_attempts,
        login_window_seconds=settings.login_window_seconds,
        secret_key_configured=settings.secret_key != "CHANGE-ME-IN-PRODUCTION",
        allow_anonymous_readonly_local=settings.allow_anonymous_readonly_local,
        anonymous_local_role=settings.anonymous_local_role,
        allow_public_registration=bool(settings.allow_public_registration),
        trust_x_forwarded_for=settings.trust_x_forwarded_for,
        features=SecurityFeatures(
            authentication=settings.security_level >= 1,
            rbac_enforced=settings.security_level >= 2,
            audit_trail=True,
            password_hashing="bcrypt",
        ),
    )
