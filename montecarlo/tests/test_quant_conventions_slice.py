from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import analytics.risk as risk_module
from analytics.risk import RiskEngine


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_default_is_name(
    source_path: Path,
    class_name: str,
    fn_name: str,
    arg_name: str,
    expected_name: str,
) -> None:
    tree = ast.parse(_read(source_path))
    class_node = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    fn_node = next(
        node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == fn_name
    )
    positional_args = [a.arg for a in fn_node.args.args]
    defaults = list(fn_node.args.defaults)
    first_default_idx = len(positional_args) - len(defaults)
    target_idx = positional_args.index(arg_name)
    target_default = defaults[target_idx - first_default_idx]
    assert isinstance(target_default, ast.Name)
    assert target_default.id == expected_name


def test_risk_free_defaults_are_bound_to_shared_conventions_names() -> None:
    _assert_default_is_name(
        SRC_DIR / "analysis" / "portfolio_analytics.py",
        class_name="PortfolioAnalytics",
        fn_name="markowitz_optimize",
        arg_name="risk_free",
        expected_name="RISK_FREE_RATE",
    )
    _assert_default_is_name(
        SRC_DIR / "analysis" / "portfolio_analytics.py",
        class_name="PortfolioAnalytics",
        fn_name="black_litterman_optimize",
        arg_name="risk_free",
        expected_name="RISK_FREE_RATE",
    )
    _assert_default_is_name(
        SRC_DIR / "analytics" / "risk.py",
        class_name="RiskEngine",
        fn_name="calculate_sharpe_ratio",
        arg_name="risk_free_rate",
        expected_name="RISK_FREE_RATE",
    )
    _assert_default_is_name(
        SRC_DIR / "genesix" / "risk" / "portfolio.py",
        class_name="PortfolioRiskAnalyzer",
        fn_name="efficient_frontier",
        arg_name="risk_free_rate",
        expected_name="RISK_FREE_RATE",
    )


def test_risk_engine_annualization_uses_shared_factors(monkeypatch) -> None:
    monkeypatch.setattr(risk_module, "ANNUALIZATION_FACTOR_RETURN", 260.0)
    monkeypatch.setattr(risk_module, "ANNUALIZATION_FACTOR_VOL", 17.0)

    engine = RiskEngine(confidence_level=0.95)
    prices = [100.0, 101.0, 102.0, 99.0, 100.0, 103.0]
    for price in prices:
        engine.add_price("TST", price)

    returns = np.diff(np.asarray(prices)) / np.asarray(prices[:-1])
    expected_vol = float(np.std(returns) * 17.0)
    expected_sharpe = float((np.mean(returns) * 260.0) / expected_vol)

    got_vol = engine.calculate_volatility("TST", annualize=True)
    got_sharpe = engine.calculate_sharpe_ratio("TST", risk_free_rate=0.0)

    assert math.isclose(got_vol, expected_vol, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(got_sharpe, expected_sharpe, rel_tol=1e-12, abs_tol=1e-12)


def test_slice_no_hardcoded_risk_free_literals_left() -> None:
    files = [
        SRC_DIR / "analysis" / "portfolio_analytics.py",
        SRC_DIR / "analytics" / "risk.py",
        SRC_DIR / "genesix" / "risk" / "portfolio.py",
    ]
    disallowed = (
        "risk_free: float = 0.05",
        "risk_free: float = 0.04",
        "risk_free_rate: float = 0.05",
        "risk_free_rate: float = 0.04",
    )

    for file in files:
        text = _read(file)
        for token in disallowed:
            assert token not in text
