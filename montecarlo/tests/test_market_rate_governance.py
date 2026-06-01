from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

GENESIX_DIR = SRC_DIR / "genesix"
GENESIX_UTILS_DIR = GENESIX_DIR / "utils"

# Keep tests isolated from genesix/__init__.py side-effects.
if "genesix" not in sys.modules:
    genesix_pkg = types.ModuleType("genesix")
    genesix_pkg.__path__ = [str(GENESIX_DIR)]  # type: ignore[attr-defined]
    sys.modules["genesix"] = genesix_pkg

if "genesix.utils" not in sys.modules:
    genesix_utils_pkg = types.ModuleType("genesix.utils")
    genesix_utils_pkg.__path__ = [str(GENESIX_UTILS_DIR)]  # type: ignore[attr-defined]
    sys.modules["genesix.utils"] = genesix_utils_pkg

_quant_spec = importlib.util.spec_from_file_location(
    "genesix.utils.quant_conventions",
    GENESIX_UTILS_DIR / "quant_conventions.py",
)
assert _quant_spec is not None and _quant_spec.loader is not None
_quant_module = importlib.util.module_from_spec(_quant_spec)
sys.modules["genesix.utils.quant_conventions"] = _quant_module
_quant_spec.loader.exec_module(_quant_module)

RISK_FREE_RATE = _quant_module.RISK_FREE_RATE
RISK_FREE_RATE_SOURCE = _quant_module.RISK_FREE_RATE_SOURCE
RISK_FREE_RATE_LAST_UPDATED = _quant_module.RISK_FREE_RATE_LAST_UPDATED

_rate_policy_spec = importlib.util.spec_from_file_location(
    "genesix.utils.rate_policy",
    GENESIX_UTILS_DIR / "rate_policy.py",
)
assert _rate_policy_spec is not None and _rate_policy_spec.loader is not None
_rate_policy_module = importlib.util.module_from_spec(_rate_policy_spec)
sys.modules["genesix.utils.rate_policy"] = _rate_policy_module
_rate_policy_spec.loader.exec_module(_rate_policy_module)

from market import market_data
from genesix.utils import rate_policy


def test_fetch_risk_free_rate_keeps_legacy_tuple_contract() -> None:
    quote = market_data.fetch_risk_free_rate_quote("JPY")
    rate, label = market_data.fetch_risk_free_rate("JPY")

    assert isinstance(rate, float)
    assert isinstance(label, str)
    assert rate == quote.rate
    assert label == quote.source_label
    assert quote.mode == "static"
    assert "boj" in quote.source_label.lower()


def test_unknown_currency_uses_traceable_baseline_default() -> None:
    quote = market_data.fetch_risk_free_rate_quote("XYZ")

    assert quote.currency == "XYZ"
    assert quote.mode == "baseline_default"
    assert quote.rate == RISK_FREE_RATE
    assert RISK_FREE_RATE_SOURCE in quote.source_label
    assert "baseline" in quote.source_label.lower()
    assert quote.as_of_utc


def test_usd_fallback_mode_when_live_provider_unavailable(monkeypatch) -> None:
    class _BrokenTicker:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("provider unavailable")

    fake_yf = types.SimpleNamespace(Ticker=_BrokenTicker)
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    quote = market_data.fetch_risk_free_rate_quote("USD")
    assert quote.mode == "fallback"
    assert quote.rate == RISK_FREE_RATE
    assert "fallback" in quote.source_label.lower()
    assert "baseline" in quote.source_label.lower()


def test_policy_rate_quote_usd_baseline_is_traceable() -> None:
    quote = rate_policy.policy_rate_quote("USD")

    assert quote.currency == "USD"
    assert quote.rate == RISK_FREE_RATE
    assert quote.mode == "fallback"
    assert "baseline" in quote.source_label.lower()
    assert quote.as_of_utc == RISK_FREE_RATE_LAST_UPDATED


def test_policy_rate_quote_non_usd_and_unknown_modes_are_explicit() -> None:
    jpy_quote = rate_policy.policy_rate_quote("JPY")
    unknown_quote = rate_policy.policy_rate_quote("XYZ")

    assert jpy_quote.currency == "JPY"
    assert jpy_quote.mode == "static"
    assert "boj" in jpy_quote.source_label.lower()

    assert unknown_quote.currency == "XYZ"
    assert unknown_quote.mode == "baseline_default"
    assert unknown_quote.rate == RISK_FREE_RATE
    assert "baseline" in unknown_quote.source_label.lower()


def test_policy_live_quote_remains_serializable_and_legacy_compatible() -> None:
    quote = rate_policy.live_rate_quote("usd", 0.051, "Unit test provider")

    assert quote.currency == "USD"
    assert quote.mode == "live"
    assert quote.as_of_utc
    assert quote.to_legacy() == (0.051, "Unit test provider")
    assert quote.to_dict()["mode"] == "live"


def test_shared_sidebar_defaults_are_sourced_from_quant_baseline() -> None:
    shared_path = SRC_DIR / "_shared.py"
    text = shared_path.read_text(encoding="utf-8")

    assert "fetch_risk_free_rate_quote" in text
    assert 'st.session_state.setdefault("rate_sidebar", RISK_FREE_RATE)' in text
    assert 'rate_sidebar_source' in text
    assert "shared baseline" in text
    assert "Rate source:" in text
