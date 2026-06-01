from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_risk_route_no_longer_owns_snapshot_fallback_logic() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "risk.py").read_text(encoding="utf-8")
    assert "list_risk_snapshots(" not in source
    assert "list_fallback_snapshots(" not in source
    assert "list_risk_snapshots_with_fallback" in source


def test_risk_worker_still_delegates_to_shared_service() -> None:
    source = (BACKEND_DIR / "app" / "workers" / "tasks" / "risk_task.py").read_text(encoding="utf-8")
    assert "compute_risk_task_payload_sync" in source
    assert "_fetch_returns_sync" not in source
    assert "compute_full_risk_report" not in source
