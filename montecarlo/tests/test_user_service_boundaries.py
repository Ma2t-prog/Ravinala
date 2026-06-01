from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_users_route_no_longer_owns_user_queries_or_audit_serialization() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "users.py").read_text(encoding="utf-8")
    assert "select(User)" not in source
    assert "select(AuditEvent)" not in source
    assert "fire_audit(" not in source
    assert "app.services.identity_service" in source
