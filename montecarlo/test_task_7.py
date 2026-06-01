"""
GenesiX Task 7: Backtesting Engine & Performance Tracking — Validation Tests
Tests for backtesting_engine.py and backtest_results.py
"""

import sys
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'montecarlo'))

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def print_test(num, name):
    print(f"  ✓ TEST {num}: {name}")

def print_result(passed, failed):
    print(f"\n{'='*70}")
    if failed == 0:
        print(f"  ✅ ALL {passed} TESTS PASSED")
    else:
        print(f"  ⚠️  {passed} PASSED, {failed} FAILED")
    print(f"{'='*70}\n")

# ============================================================================
# TEST 1: MODULE IMPORTS
# ============================================================================

test_num = 1
passed = 0
failed = 0

print_header("TEST 1: Module Imports")

try:
    from src.genesix.backtesting_engine import (
        BacktestingEngine,
        BacktestConfig,
        BacktestResult,
        create_backtest_config
    )
    print_test(test_num, "backtesting_engine imports")
    passed += 1
except Exception as e:
    print(f"  ✗ backtesting_engine import failed: {e}")
    failed += 1

# ============================================================================
# TEST 2: BACKTEST CONFIG CREATION
# ============================================================================

test_num += 1
print_header("TEST 2: BacktestConfig Creation")

try:
    config = BacktestConfig(
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=100_000,
        rebalance_frequency="monthly",
        benchmark_ticker="SPY"
    )
    
    assert config.initial_capital == 100_000
    assert config.benchmark_ticker == "SPY"
    assert config.rebalance_frequency == "monthly"
    
    print_test(test_num, "BacktestConfig instantiation")
    print(f"    - Start: {config.start_date.date()}")
    print(f"    - End: {config.end_date.date()}")
    print(f"    - Initial Capital: ${config.initial_capital:,.0f}")
    print(f"    - Rebalance: {config.rebalance_frequency}")
    passed += 1
except Exception as e:
    print(f"  ✗ BacktestConfig creation failed: {e}")
    failed += 1

# ============================================================================
# TEST 3: BACKTESTING ENGINE INSTANTIATION
# ============================================================================

test_num += 1
print_header("TEST 3: BacktestingEngine Instantiation")

try:
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    weights = {t: 0.2 for t in tickers}
    config = BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=100_000
    )
    
    engine = BacktestingEngine(
        tickers=tickers,
        weights=weights,
        config=config
    )
    
    assert engine.tickers == tickers
    assert engine.config.initial_capital == 100_000
    
    print_test(test_num, "BacktestingEngine instantiation")
    print(f"    - Tickers: {', '.join(tickers)}")
    print(f"    - Initial Capital: ${config.initial_capital:,.0f}")
    print(f"    - Optimization Period: {config.start_date.date()} to {config.end_date.date()}")
    passed += 1
except Exception as e:
    print(f"  ✗ BacktestingEngine instantiation failed: {e}")
    failed += 1

# ============================================================================
# TEST 4: WEIGHT VALIDATION
# ============================================================================

test_num += 1
print_header("TEST 4: Weight Validation (Sum to 1.0)")

try:
    # Valid weights
    valid_weights = {"AAPL": 0.3, "MSFT": 0.4, "GOOGL": 0.3}
    config = BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31)
    )
    
    engine = BacktestingEngine(
        tickers=list(valid_weights.keys()),
        weights=valid_weights,
        config=config
    )
    
    print_test(test_num, "Valid weights (sum to 1.0)")
    print(f"    - Weights: {valid_weights}")
    print(f"    - Sum: {sum(valid_weights.values()):.4f}")
    passed += 1
    
    # Invalid weights should raise error
    try:
        invalid_weights = {"AAPL": 0.3, "MSFT": 0.4}  # Sum = 0.7
        engine2 = BacktestingEngine(
            tickers=list(invalid_weights.keys()),
            weights=invalid_weights,
            config=config
        )
        print(f"  ✗ Invalid weights should have raised ValueError")
        failed += 1
    except ValueError as e:
        print(f"    - Correctly rejected invalid weights (sum=0.7)")
        passed += 1
except Exception as e:
    print(f"  ✗ Weight validation test failed: {e}")
    failed += 1

# ============================================================================
# TEST 5: BACKTEST EXECUTION (PRODUCTION RUN)
# ============================================================================

test_num += 1
print_header("TEST 5: Backtest Execution (Live Data)")

try:
    # Use recent data and major tickers
    tickers = ["AAPL", "MSFT", "NVDA"]
    weights = {t: 1.0/3 for t in tickers}
    
    # 1-year lookback
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100_000,
        rebalance_frequency="monthly"
    )
    
    engine = BacktestingEngine(
        tickers=tickers,
        weights=weights,
        config=config
    )
    
    print(f"    Running backtest: {tickers}")
    print(f"    Period: {start_date.date()} to {end_date.date()}")
    
    result = engine.run()
    
    assert result is not None, "Backtest returned None"
    assert len(result.portfolio_value) > 0, "No portfolio values calculated"
    assert len(result.daily_returns) > 0, "No daily returns calculated"
    assert result.sharpe_ratio != 0, "Sharpe ratio not calculated"
    
    print_test(test_num, "Backtest execution")
    print(f"    ✓ Portfolio values: {len(result.portfolio_value)} days")
    print(f"    ✓ Daily returns: {len(result.daily_returns)} days")
    print(f"    ✓ Total return: {result.total_return:.2f}%")
    print(f"    ✓ Annual return: {result.annual_return:.2f}%")
    print(f"    ✓ Annual volatility: {result.annual_volatility:.2f}%")
    print(f"    ✓ Sharpe ratio: {result.sharpe_ratio:.2f}")
    print(f"    ✓ Max drawdown: {result.max_drawdown:.2f}%")
    print(f"    ✓ Beta: {result.beta:.3f}")
    print(f"    ✓ Alpha: {result.alpha:.2f}%")
    
    passed += 1
except Exception as e:
    print(f"  ✗ Backtest execution failed: {e}")
    import traceback
    traceback.print_exc()
    failed += 1

# ============================================================================
# TEST 6: PERFORMANCE METRICS CALCULATION
# ============================================================================

test_num += 1
print_header("TEST 6: Performance Metrics Validation")

try:
    assert result is not None, "Result not available from Test 5"
    
    # Validate metric ranges
    assert -100 <= result.total_return <= 500, f"Total return {result.total_return} out of range"
    assert 0 <= result.annual_volatility <= 200, f"Annual vol {result.annual_volatility} out of range"
    assert -100 <= result.max_drawdown <= 0, f"Max DD {result.max_drawdown} should be between -100 and 0"
    assert result.annual_volatility >= 0, "Volatility should be positive"
    assert result.sharpe_ratio > -10, "Sharpe ratio too negative"
    assert 0 <= result.beta <= 2, f"Beta {result.beta} out of expected range"
    
    # Validate risk metrics
    assert result.var_95 <= 0, "VaR should be negative or zero"
    assert result.cvar_95 <= result.var_95, "CVaR should be <= VaR"
    assert 0 <= result.win_loss_ratio <= 5, f"Win/loss ratio {result.win_loss_ratio} invalid"
    
    print_test(test_num, "Performance metrics validation")
    print(f"    ✓ Total return: {result.total_return:.2f}% (valid range)")
    print(f"    ✓ Annual volatility: {result.annual_volatility:.2f}% (valid range)")
    print(f"    ✓ Sharpe ratio: {result.sharpe_ratio:.2f} (valid)")
    print(f"    ✓ Max drawdown: {result.max_drawdown:.2f}% (valid negative)")
    print(f"    ✓ Beta: {result.beta:.3f} (valid range)")
    print(f"    ✓ VaR(95%): {result.var_95:.2f}% (valid negative)")
    print(f"    ✓ CVaR(95%): {result.cvar_95:.2f}% (valid)")
    print(f"    ✓ Win/loss ratio: {result.win_loss_ratio:.2f}")
    
    passed += 1
except Exception as e:
    print(f"  ✗ Performance metrics validation failed: {e}")
    failed += 1

# ============================================================================
# TEST 7: ATTRIBUTION ANALYSIS
# ============================================================================

test_num += 1
print_header("TEST 7: Attribution Analysis")

try:
    assert result is not None, "Result not available"
    
    # Check that all tickers have attribution data
    for ticker in tickers:
        assert ticker in result.instrument_returns, f"Missing returns for {ticker}"
        assert ticker in result.instrument_pnl, f"Missing P&L for {ticker}"
    
    total_attribution = sum(result.instrument_pnl.values())
    
    print_test(test_num, "Attribution analysis")
    print(f"    ✓ Attribution calculated for {len(result.instrument_returns)} instruments")
    print(f"    Attribution breakdown:")
    for ticker in tickers:
        ret = result.instrument_returns[ticker]
        pnl = result.instrument_pnl[ticker]
        print(f"      - {ticker}: {ret:+.2f}% return, {pnl:+.2f}% contribution")
    
    passed += 1
except Exception as e:
    print(f"  ✗ Attribution analysis failed: {e}")
    failed += 1

# ============================================================================
# TEST 8: BENCHMARK COMPARISON
# ============================================================================

test_num += 1
print_header("TEST 8: Benchmark Comparison (vs SPY)")

try:
    assert result is not None, "Result not available"
    
    # Validate benchmark data
    assert len(result.benchmark_returns) > 0, "No benchmark returns"
    assert len(result.benchmark_value) > 0, "No benchmark values"
    assert len(result.excess_returns) > 0, "No excess returns"
    
    # Validate benchmark metrics
    assert isinstance(result.beta, float), "Beta should be float"
    assert isinstance(result.alpha, float), "Alpha should be float"
    assert isinstance(result.tracking_error, float), "Tracking error should be float"
    assert isinstance(result.information_ratio, float), "Info ratio should be float"
    
    outperformance = result.total_return - ((result.benchmark_value.iloc[-1] / 100_000 - 1) * 100)
    
    print_test(test_num, "Benchmark comparison")
    print(f"    ✓ Portfolio return: {result.total_return:.2f}%")
    print(f"    ✓ Beta: {result.beta:.3f}")
    print(f"    ✓ Alpha: {result.alpha:.2f}%")
    print(f"    ✓ Tracking error: {result.tracking_error:.2f}%")
    print(f"    ✓ Information ratio: {result.information_ratio:.2f}")
    print(f"    ✓ Excess returns calculated")
    
    passed += 1
except Exception as e:
    print(f"  ✗ Benchmark comparison failed: {e}")
    failed += 1

# ============================================================================
# TEST 9: BACKTEST PAGE SYNTAX
# ============================================================================

test_num += 1
print_header("TEST 9: Backtest Results Page Syntax")

try:
    import ast
    
    page_path = os.path.join(os.path.dirname(__file__), "src", "pages", "backtest_results.py")
    
    with open(page_path, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()
    
    # Parse to check syntax
    ast.parse(code)
    
    # Check key imports
    assert "import streamlit" in code
    assert "from src.genesix.backtesting_engine" in code
    assert "BacktestingEngine" in code
    
    # Check basic structure
    assert "st.set_page_config" in code or "streamlit" in code, "No streamlit config found"
    
    file_size = len(code)
    line_count = len(code.split('\n'))
    
    print_test(test_num, "Backtest results page syntax")
    print(f"    ✓ Syntax valid (parsed successfully)")
    print(f"    ✓ File size: {file_size:,} bytes")
    print(f"    ✓ Line count: {line_count} lines")
    print(f"    ✓ Required imports present")
    
    passed += 1
except SyntaxError as e:
    print(f"  ✗ Syntax error in backtest_results.py: {e}")
    failed += 1
except Exception as e:
    print(f"  ✗ Page syntax validation failed: {e}")
    failed += 1

# ============================================================================
# TEST 10: CREATE_BACKTEST_CONFIG HELPER
# ============================================================================

test_num += 1
print_header("TEST 10: Backtest Config Helper Function")

try:
    config_helper = create_backtest_config(
        start_date="2023-01-01",
        end_date="2023-12-31",
        initial_capital=250_000
    )
    
    assert config_helper.initial_capital == 250_000
    assert config_helper.start_date.year == 2023
    assert config_helper.start_date.month == 1
    assert config_helper.end_date.year == 2023
    assert config_helper.end_date.month == 12
    
    print_test(test_num, "Config helper function")
    print(f"    ✓ Created config from date strings")
    print(f"    ✓ Period: {config_helper.start_date.date()} to {config_helper.end_date.date()}")
    print(f"    ✓ Initial capital: ${config_helper.initial_capital:,.0f}")
    
    passed += 1
except Exception as e:
    print(f"  ✗ Config helper test failed: {e}")
    failed += 1

# ============================================================================
# FINAL RESULTS
# ============================================================================

total_tests = passed + failed
print_result(passed, failed)

# Exit with appropriate code
sys.exit(0 if failed == 0 else 1)
