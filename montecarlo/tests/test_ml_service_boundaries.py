from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_ml_route_no_longer_owns_db_query_or_artifact_registry_logic() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "ml.py").read_text(encoding="utf-8")
    assert "select(MLRun" not in source
    assert "ARTIFACT_ROOT" not in source
    assert "train_with_baselines" not in source
    assert "YFinanceProvider" not in source
    assert "from app.services.ml_service import" in source


def test_ml_worker_delegates_to_shared_ml_service() -> None:
    source = (BACKEND_DIR / "app" / "workers" / "tasks" / "ml_task.py").read_text(encoding="utf-8")
    assert "execute_training_sync" in source
    assert "persist_training_runs_sync" in source
    assert "YFinanceProvider" not in source
    assert "train_with_baselines" not in source
