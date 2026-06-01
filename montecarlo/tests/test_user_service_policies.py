from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.users import UserUpdate
from app.services import identity_service


def _user(**overrides):
    base = {
        "id": UUID("00000000-0000-0000-0000-000000000111"),
        "username": "alice",
        "email": "alice@example.com",
        "role": "viewer",
        "is_active": True,
        "created_at": datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc),
        "last_login": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_update_user_profile_rejects_non_admin_role_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _user()

    class _Result:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _Session:
        async def execute(self, stmt):
            return _Result(target)

    monkeypatch.setattr(identity_service, "fire_audit", lambda **kwargs: None)

    with pytest.raises(HTTPException) as exc:
        await identity_service.update_managed_user(
            target.id,
            UserUpdate(role="admin"),
            current_user=SimpleNamespace(id=target.id, role="viewer"),
            ip_address="127.0.0.1",
            db=_Session(),
        )

    assert exc.value.status_code == 403
    assert "Only admins can modify role or activation state" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_update_user_profile_rejects_duplicate_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _user()

    class _Result:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _Session:
        def __init__(self):
            self.calls = 0

        async def execute(self, stmt):
            self.calls += 1
            if self.calls == 1:
                return _Result(target)
            return _Result(UUID("00000000-0000-0000-0000-000000000222"))

    monkeypatch.setattr(identity_service, "fire_audit", lambda **kwargs: None)

    with pytest.raises(HTTPException) as exc:
        await identity_service.update_managed_user(
            target.id,
            UserUpdate(email="duplicate@example.com"),
            current_user=SimpleNamespace(id=target.id, role="viewer"),
            ip_address="127.0.0.1",
            db=_Session(),
        )

    assert exc.value.status_code == 409
    assert "Email already exists" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_deactivate_user_forbids_admin_self_deactivation() -> None:
    admin_id = UUID("00000000-0000-0000-0000-000000000999")

    with pytest.raises(HTTPException) as exc:
        await identity_service.deactivate_user(
            admin_id,
            admin_user=SimpleNamespace(id=admin_id, role="admin"),
            ip_address="127.0.0.1",
            db=object(),
        )

    assert exc.value.status_code == 403
    assert "self-deactivation" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_role_change_increments_token_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _user(token_version=4)

    class _Result:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _Session:
        async def execute(self, stmt):
            return _Result(target)

    monkeypatch.setattr(identity_service, "fire_audit", lambda **kwargs: None)

    await identity_service.update_managed_user(
        target.id,
        UserUpdate(role="analyst"),
        current_user=SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000999"), role="admin"),
        ip_address="127.0.0.1",
        db=_Session(),
    )

    assert target.role == "analyst"
    assert target.token_version == 5


@pytest.mark.asyncio
async def test_email_only_update_does_not_revoke_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _user(token_version=7)

    class _Result:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _Session:
        def __init__(self):
            self.calls = 0

        async def execute(self, stmt):
            self.calls += 1
            if self.calls == 1:
                return _Result(target)
            return _Result(None)

    monkeypatch.setattr(identity_service, "fire_audit", lambda **kwargs: None)

    await identity_service.update_managed_user(
        target.id,
        UserUpdate(email="new@example.com"),
        current_user=SimpleNamespace(id=target.id, role="viewer"),
        ip_address="127.0.0.1",
        db=_Session(),
    )

    assert target.email == "new@example.com"
    assert target.token_version == 7


@pytest.mark.asyncio
async def test_logout_revokes_current_user_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _user(token_version=1)

    class _Result:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _Session:
        async def execute(self, stmt):
            return _Result(target)

    monkeypatch.setattr(identity_service, "fire_audit", lambda **kwargs: None)

    await identity_service.record_logout(
        SimpleNamespace(id=target.id, role=target.role),
        db=_Session(),
        ip_address="127.0.0.1",
    )

    assert target.token_version == 2


def test_client_ip_ignores_forwarded_header_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = SimpleNamespace(
        headers={"X-Forwarded-For": "203.0.113.10"},
        client=SimpleNamespace(host="127.0.0.1"),
    )
    monkeypatch.setattr(
        identity_service,
        "get_settings",
        lambda: SimpleNamespace(trust_x_forwarded_for=False),
    )

    assert identity_service.client_ip_from_request(request) == "127.0.0.1"


def test_client_ip_honors_forwarded_header_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = SimpleNamespace(
        headers={"X-Forwarded-For": "203.0.113.10, 10.0.0.2"},
        client=SimpleNamespace(host="127.0.0.1"),
    )
    monkeypatch.setattr(
        identity_service,
        "get_settings",
        lambda: SimpleNamespace(trust_x_forwarded_for=True),
    )

    assert identity_service.client_ip_from_request(request) == "203.0.113.10"


@pytest.mark.asyncio
async def test_register_public_user_rejects_when_public_registration_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        identity_service,
        "get_settings",
        lambda: SimpleNamespace(
            allow_public_registration=False,
            trust_x_forwarded_for=False,
            login_max_attempts=5,
            login_window_seconds=300,
        ),
    )

    with pytest.raises(HTTPException) as exc:
        await identity_service.register_public_user(
            SimpleNamespace(
                username="alice",
                email="alice@example.com",
                password="strong-password",
                role="viewer",
            ),
            db=object(),
            ip_address="127.0.0.1",
        )

    assert exc.value.status_code == 403
    assert "disabled" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_authenticate_user_throttles_after_repeated_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _user(password_hash="hashed-password")

    class _Result:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _Session:
        async def execute(self, stmt):
            return _Result(target)

    identity_service._LOGIN_FAILURES.clear()
    monkeypatch.setattr(identity_service, "verify_password", lambda raw, hashed: False)
    monkeypatch.setattr(identity_service, "fire_audit", lambda **kwargs: None)
    monkeypatch.setattr(
        identity_service,
        "get_settings",
        lambda: SimpleNamespace(
            jwt_expire_minutes=30,
            trust_x_forwarded_for=False,
            allow_public_registration=True,
            login_max_attempts=2,
            login_window_seconds=300,
        ),
    )

    with pytest.raises(HTTPException) as first_exc:
        await identity_service.authenticate_user(
            SimpleNamespace(username="alice", password="bad-password"),
            db=_Session(),
            ip_address="127.0.0.1",
        )
    with pytest.raises(HTTPException) as second_exc:
        await identity_service.authenticate_user(
            SimpleNamespace(username="alice", password="bad-password"),
            db=_Session(),
            ip_address="127.0.0.1",
        )
    with pytest.raises(HTTPException) as throttled_exc:
        await identity_service.authenticate_user(
            SimpleNamespace(username="alice", password="bad-password"),
            db=_Session(),
            ip_address="127.0.0.1",
        )

    assert first_exc.value.status_code == 401
    assert second_exc.value.status_code == 401
    assert throttled_exc.value.status_code == 429
