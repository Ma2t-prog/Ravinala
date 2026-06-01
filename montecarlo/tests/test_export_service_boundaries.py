from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_export_route_no_longer_owns_rendering_and_tmp_policy() -> None:
    source = (BACKEND_DIR / "app" / "routes" / "export.py").read_text(encoding="utf-8")
    assert "openpyxl" not in source
    assert "reportlab" not in source
    assert '"/tmp"' not in source
    assert "datetime.utcnow" not in source
    assert "app.services.export_service" in source
