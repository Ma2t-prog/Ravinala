from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_backend_legacy_bridges_no_longer_mutate_sys_path_locally() -> None:
    service_files = [
        BACKEND_DIR / "app" / "services" / "company_analysis_service.py",
        BACKEND_DIR / "app" / "services" / "portfolio_optimization_service.py",
        BACKEND_DIR / "app" / "services" / "universe_service.py",
        BACKEND_DIR / "app" / "agents" / "nodes" / "analysis_agent.py",
    ]
    for file_path in service_files:
        source = file_path.read_text(encoding="utf-8")
        assert "sys.path.insert" not in source

    bridge_source = (
        BACKEND_DIR / "app" / "services" / "legacy_quant_bridge.py"
    ).read_text(encoding="utf-8")
    assert "ensure_src_on_path" in bridge_source
    assert "import_legacy_module" in bridge_source


def test_health_endpoint_uses_timezone_aware_timestamp() -> None:
    source = (BACKEND_DIR / "app" / "main.py").read_text(encoding="utf-8")
    assert "datetime.now(timezone.utc)" in source
    assert "datetime.utcnow()" not in source
