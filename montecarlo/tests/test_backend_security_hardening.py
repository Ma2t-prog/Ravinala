from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.auth import rbac  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.routes.auth import RegisterRequest, register  # noqa: E402
from app.risk.persistence import _json_safe  # noqa: E402


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/",
            "scheme": "http",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "query_string": b"",
        }
    )


def _credentials(token: str = "token") -> SimpleNamespace:
    return SimpleNamespace(credentials=token)


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, *values):
        self._values = list(values)

    async def execute(self, stmt):
        if not self._values:
            raise AssertionError("Unexpected execute() call")
        return _ScalarResult(self._values.pop(0))


def test_settings_require_secret_when_security_level_is_enabled() -> None:
    with pytest.raises(ValidationError):
        Settings(
            security_level=1,
            secret_key="CHANGE-ME-IN-PRODUCTION",
        )


def test_controlled_security_defaults_public_registration_to_disabled() -> None:
    settings = Settings(
        security_level=2,
        secret_key="real-secret",
    )

    assert settings.allow_public_registration is False


@pytest.mark.asyncio
async def test_local_readonly_anonymous_user_is_viewer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        rbac,
        "get_settings",
        lambda: SimpleNamespace(
            security_level=0,
            allow_anonymous_readonly_local=True,
            anonymous_local_role="viewer",
        ),
    )

    user = await rbac.get_current_user(_request(), None)

    assert user.username == "anonymous"
    assert user.role == "viewer"


@pytest.mark.asyncio
async def test_anonymous_access_is_rejected_when_local_readonly_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rbac,
        "get_settings",
        lambda: SimpleNamespace(
            security_level=0,
            allow_anonymous_readonly_local=False,
            anonymous_local_role="viewer",
        ),
    )

    with pytest.raises(HTTPException) as exc:
        await rbac.get_current_user(_request(), None)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_uses_database_role_over_stale_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rbac,
        "decode_access_token",
        lambda token: SimpleNamespace(
            sub="00000000-0000-0000-0000-000000000111",
            role="viewer",
            token_version=2,
            jti="jti-1",
        ),
    )
    request = _request()
    db_user = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000111"),
        username="alice",
        role="admin",
        is_active=True,
        token_version=2,
    )

    user = await rbac.get_current_user(request, _credentials(), _Session(db_user))

    assert user.username == "alice"
    assert user.role == "admin"
    assert request.state.user_role == "admin"
    assert request.state.user_id == "00000000-0000-0000-0000-000000000111"


@pytest.mark.asyncio
async def test_get_current_user_rejects_revoked_token_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rbac,
        "decode_access_token",
        lambda token: SimpleNamespace(
            sub="00000000-0000-0000-0000-000000000111",
            role="admin",
            token_version=1,
            jti="jti-2",
        ),
    )
    db_user = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000111"),
        username="alice",
        role="admin",
        is_active=True,
        token_version=3,
    )

    with pytest.raises(HTTPException) as exc:
        await rbac.get_current_user(_request(), _credentials(), _Session(db_user))

    assert exc.value.status_code == 401
    assert "revoked" in exc.value.detail


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_database_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rbac,
        "decode_access_token",
        lambda token: SimpleNamespace(
            sub="00000000-0000-0000-0000-000000000111",
            role="viewer",
            token_version=0,
            jti="jti-3",
        ),
    )
    db_user = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000111"),
        username="alice",
        role="viewer",
        is_active=False,
        token_version=0,
    )

    with pytest.raises(HTTPException) as exc:
        await rbac.get_current_user(_request(), _credentials(), _Session(db_user))

    assert exc.value.status_code == 401
    assert "inactive or missing" in exc.value.detail


def test_public_registration_schema_allows_only_viewer_role() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            username="new_user",
            email="user@example.com",
            password="very-strong-password",
            role="admin",
        )


@pytest.mark.asyncio
async def test_public_registration_with_viewer_role_still_requires_database() -> None:
    body = RegisterRequest(
        username="new_user",
        email="user@example.com",
        password="very-strong-password",
    )

    with pytest.raises(HTTPException) as exc:
        await register(body, _request(), None)

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_public_registration_is_blocked_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = RegisterRequest(
        username="new_user",
        email="user@example.com",
        password="very-strong-password",
    )
    monkeypatch.setattr(
        rbac,
        "get_settings",
        lambda: SimpleNamespace(
            security_level=2,
            allow_anonymous_readonly_local=False,
            anonymous_local_role="viewer",
        ),
    )

    from app.services import identity_service  # noqa: WPS433

    monkeypatch.setattr(
        identity_service,
        "get_settings",
        lambda: SimpleNamespace(
            allow_public_registration=False,
            trust_x_forwarded_for=False,
        ),
    )

    with pytest.raises(HTTPException) as exc:
        await register(body, _request(), object())

    assert exc.value.status_code == 403
    assert "disabled" in exc.value.detail


def test_json_safe_normalizes_nested_values() -> None:
    now = datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)
    payload = {
        "ts": now,
        "amount": Decimal("1.25"),
        "identifier": UUID("00000000-0000-0000-0000-000000000001"),
        "nested": {"items": [Decimal("2.5"), now]},
    }

    result = _json_safe(payload)

    assert result == {
        "ts": now.isoformat(),
        "amount": 1.25,
        "identifier": "00000000-0000-0000-0000-000000000001",
        "nested": {"items": [2.5, now.isoformat()]},
    }
