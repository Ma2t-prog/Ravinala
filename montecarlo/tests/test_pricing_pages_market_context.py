from __future__ import annotations

from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
ACTIVE_PRICING_PAGES = (
    Path("pages/options_analytics.py"),
    Path("pages/custom_product.py"),
    Path("pages/museum_exotics.py"),
    Path("pages/sandbox.py"),
)


def _read(relative_path: Path | str) -> str:
    return (SRC_DIR / relative_path).read_text(encoding="utf-8")


def test_shared_sidebar_market_context_helper_exists() -> None:
    text = _read("_shared.py")

    assert "class SidebarMarketContext" in text
    assert "def _ensure_market_sidebar_defaults()" in text
    assert "def get_sidebar_market_context()" in text
    assert 'st.session_state.setdefault("rate_sidebar", RISK_FREE_RATE)' in text
    assert 'st.session_state.setdefault("carry_sidebar", default_rate_sidebar)' in text


def test_active_pricing_pages_use_shared_market_context() -> None:
    for relative_path in ACTIVE_PRICING_PAGES:
        text = _read(relative_path)
        assert "get_sidebar_market_context" in text, f"{relative_path} must use the shared helper"
        assert 'st.session_state.get("rate_sidebar", 0.05)' not in text
        assert 'st.session_state.get("carry_sidebar", 0.04)' not in text

