from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import identity_service  # noqa: E402
from app.schemas.users import UserUpdate  # noqa: E402


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, results: list[object]):
        self._results = list(results)

    async def execute(self, stmt):
        if not self._results:
            raise AssertionError("Unexpected extra execute() call")
        return _ScalarResult(self._results.pop(0))


def test_auth_route_no_longer_owns_password_jwt_or_user_query_logic() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "auth.py").read_text(encoding="utf-8")
    assert "select(" not in source
    assert "hash_password(" not in source
    assert "verify_password(" not in source
    assert "create_access_token(" not in source
    assert "from app.services.identity_service import" in source


def test_users_route_no_longer_owns_direct_db_audit_or_settings_logic() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "users.py").read_text(encoding="utf-8")
    assert "select(" not in source
    assert "AuditEvent" not in source
    assert "fire_audit(" not in source
    assert "get_settings(" not in source
    assert "from app.services.identity_service import" in source


def test_security_status_route_is_admin_only() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "users.py").read_text(encoding="utf-8")
    assert '@router.get("/api/v1/security/status"' in source
    assert 'Depends(require_role("admin"))' in source


@pytest.mark.asyncio
async def test_non_admin_cannot_modify_role_or_activation_state() -> None:
    current_user = SimpleNamespace(id=uuid4(), role="viewer")

    with pytest.raises(HTTPException) as exc:
        await identity_service.update_managed_user(
            current_user.id,
            UserUpdate(role="admin"),
            current_user=current_user,
            db=_Session([]),
            ip_address="127.0.0.1",
        )

    assert exc.value.status_code == 403
    assert "Only admins" in exc.value.detail


@pytest.mark.asyncio
async def test_update_user_rejects_duplicate_email_before_db_constraint_failure() -> None:
    user_id = uuid4()
    current_user = SimpleNamespace(id=user_id, role="admin")
    existing_user = SimpleNamespace(
        id=user_id,
        username="alice",
        email="alice@example.com",
        role="viewer",
        is_active=True,
        created_at=SimpleNamespace(isoformat=lambda: "2026-03-23T12:00:00+00:00"),
        last_login=None,
    )

    session = _Session([existing_user, UUID("00000000-0000-0000-0000-000000000123")])

    with pytest.raises(HTTPException) as exc:
        await identity_service.update_managed_user(
            user_id,
            UserUpdate(email="bob@example.com"),
            current_user=current_user,
            db=session,
            ip_address="127.0.0.1",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Email already exists"
