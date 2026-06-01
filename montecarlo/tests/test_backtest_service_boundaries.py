from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_backtest_route_no_longer_owns_execution_and_persistence_flow() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "backtest.py").read_text(encoding="utf-8")
    assert "YFinanceProvider" not in source
    assert "run_with_baselines" not in source
    assert "save_backtest_bundle" not in source
    assert "from app.services.backtest_service import" in source


def test_backtest_worker_delegates_to_shared_service() -> None:
    source = (BACKEND_DIR / "app" / "workers" / "tasks" / "backtest_task.py").read_text(encoding="utf-8")
    assert "execute_backtest_sync" in source
    assert "serialize_worker_summary" in source
    assert "YFinanceProvider" not in source
    assert "run_with_baselines" not in source
