from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_document_generator_uses_legacy_bridge_instead_of_direct_src_imports() -> None:
    source = (BACKEND_DIR / "app" / "services" / "document_generator.py").read_text(encoding="utf-8")

    assert "sys.path.insert" not in source
    assert "from src.engine" not in source
    assert "legacy_quant_bridge" in source


def test_legacy_quant_bridge_is_the_only_module_holding_src_import_logic() -> None:
    source = (BACKEND_DIR / "app" / "services" / "legacy_quant_bridge.py").read_text(encoding="utf-8")

    assert "ensure_src_on_path" in source
    assert "import_legacy_module" in source
    assert "get_legacy_attr" in source
    assert "sys.path.insert" in source
