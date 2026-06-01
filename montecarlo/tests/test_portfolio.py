"""
Tests for Portfolio Optimization Lab — portfolio.py
Run: pytest tests/test_portfolio.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Stub out streamlit before importing portfolio.py
from unittest.mock import MagicMock, patch
import sys

# Minimal streamlit mock so portfolio.py can be imported without a running server
st_mock = MagicMock()
st_mock.cache_data = lambda **kw: (lambda f: f)   # passthrough decorator
sys.modules['streamlit'] = st_mock

import pytest
import numpy as np
import pandas as pd

from portfolio import (
    MarketDataLoader,
    PortfolioOptimizer,
    PortfolioRiskAnalyzer,
    PortfolioBacktester,
    _max_drawdown,
    _sortino,
    _calmar,
    _cvar_from_returns,
    _nearest_psd,
)


# ─────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def rng():
    return np.random.default_rng(42)


@pytest.fixture(scope='module')
def sample_returns(rng):
    n, k = 500, 4
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    data = rng.multivariate_normal(
        mean=[0.0005] * k,
        cov=np.array([[0.0004, 0.0002, 0.0001, 0.0001],
                      [0.0002, 0.0004, 0.0001, 0.0001],
                      [0.0001, 0.0001, 0.0004, 0.0002],
                      [0.0001, 0.0001, 0.0002, 0.0004]]),
        size=n,
    )
    idx = pd.date_range('2020-01-02', periods=n, freq='B')
    return pd.DataFrame(data, columns=tickers, index=idx)


@pytest.fixture(scope='module')
def sample_prices(sample_returns):
    return (1 + sample_returns).cumprod() * 100


@pytest.fixture(scope='module')
def optimizer(sample_returns):
    return PortfolioOptimizer(sample_returns, risk_free_rate=0.035,
                              cov_method='sample', frequency='daily')


@pytest.fixture(scope='module')
def equal_w_result(optimizer):
    return optimizer.equal_weight()


# ─────────────────────────────────────────────────────────────────
# HELPER FUNCTION TESTS
# ─────────────────────────────────────────────────────────────────

class TestHelpers:
    def test_max_drawdown_is_negative(self):
        r = pd.Series([-0.10, 0.05, -0.20, 0.15])
        assert _max_drawdown(r) < 0

    def test_max_drawdown_all_positive(self):
        r = pd.Series([0.01, 0.02, 0.01, 0.03])
        assert _max_drawdown(r) == pytest.approx(0.0, abs=1e-6)

    def test_max_drawdown_accepts_ndarray(self):
        r = np.array([-0.05, 0.02, -0.10])
        assert _max_drawdown(r) < 0

    def test_sortino_positive_returns(self):
        # Mix of positive and negative returns with positive mean
        rng2 = np.random.default_rng(1)
        r = pd.Series(rng2.normal(0.002, 0.01, 500))
        result = _sortino(r, 0.035, 252)
        assert result > 0

    def test_sortino_no_downside(self):
        r = pd.Series([0.005] * 100)
        # No negative excess returns → sortino = 0
        result = _sortino(r, 0.0, 252)
        assert result >= 0

    def test_calmar_positive(self):
        r = pd.Series([0.005] * 300 + [-0.02] * 50)
        c = _calmar(r, 252)
        assert isinstance(c, float)

    def test_cvar_less_than_var(self):
        rng2 = np.random.default_rng(0)
        r = pd.Series(rng2.normal(0, 0.01, 1000))
        var = float(np.quantile(r, 0.05))
        cvar = _cvar_from_returns(r, 0.05)
        assert cvar <= var + 1e-9

    def test_nearest_psd_is_psd(self):
        A = np.array([[1.0, 2.0], [2.0, 1.0]])   # not PSD (det < 0)
        B = _nearest_psd(A)
        eigvals = np.linalg.eigvalsh(B)
        assert np.all(eigvals >= -1e-8)


# ─────────────────────────────────────────────────────────────────
# MarketDataLoader TESTS (no network)
# ─────────────────────────────────────────────────────────────────

class TestMarketDataLoader:
    def test_compute_returns_log_shape(self, sample_prices):
        loader = MarketDataLoader()
        rets = loader.compute_returns(sample_prices, method='log')
        assert rets.shape == (len(sample_prices) - 1, sample_prices.shape[1])

    def test_compute_returns_arithmetic_shape(self, sample_prices):
        loader = MarketDataLoader()
        rets = loader.compute_returns(sample_prices, method='arithmetic')
        assert rets.shape == (len(sample_prices) - 1, sample_prices.shape[1])

    def test_compute_returns_log_no_nan(self, sample_prices):
        loader = MarketDataLoader()
        rets = loader.compute_returns(sample_prices, method='log')
        assert not rets.isna().any().any()

    def test_compute_stats_index(self, sample_returns):
        loader = MarketDataLoader()
        stats = loader.compute_stats(sample_returns)
        assert list(stats.index) == list(sample_returns.columns)

    def test_compute_stats_columns(self, sample_returns):
        loader = MarketDataLoader()
        stats = loader.compute_stats(sample_returns)
        for col in ('CAGR', 'Vol', 'Sharpe', 'Sortino', 'MaxDD', 'Calmar',
                    'Skewness', 'Kurtosis'):
            assert col in stats.columns

    def test_compute_stats_values_finite(self, sample_returns):
        loader = MarketDataLoader()
        stats = loader.compute_stats(sample_returns)
        assert stats.apply(lambda c: np.isfinite(c)).all().all()


# ─────────────────────────────────────────────────────────────────
# PortfolioOptimizer TESTS
# ─────────────────────────────────────────────────────────────────

class TestPortfolioOptimizer:
    def test_equal_weight_sums_to_one(self, optimizer):
        w = optimizer.equal_weight()['weights']
        assert w.sum() == pytest.approx(1.0, abs=1e-6)

    def test_equal_weight_uniform(self, optimizer):
        w = optimizer.equal_weight()['weights']
        assert np.allclose(w, 0.25, atol=1e-6)

    def test_max_sharpe_weights_sum(self, optimizer):
        w = optimizer.max_sharpe({'long_only': True})['weights']
        assert w.sum() == pytest.approx(1.0, abs=1e-4)

    def test_max_sharpe_long_only(self, optimizer):
        res = optimizer.max_sharpe({'long_only': True})
        assert np.all(res['weights'] >= -1e-5)

    def test_max_sharpe_max_weight_constraint(self, optimizer):
        res = optimizer.max_sharpe({'long_only': True, 'max_weight': 0.40})
        assert np.all(res['weights'] <= 0.40 + 1e-4)

    def test_max_sharpe_min_weight_constraint(self, optimizer):
        res = optimizer.max_sharpe({'long_only': True, 'min_weight': 0.05})
        assert np.all(res['weights'] >= 0.05 - 1e-4)

    def test_min_variance_vol_le_equal_weight(self, optimizer):
        gmv = optimizer.min_variance({'long_only': True})
        ew  = optimizer.equal_weight()
        assert gmv['volatility'] <= ew['volatility'] * 1.01   # allow 1% tolerance

    def test_min_variance_weights_sum(self, optimizer):
        w = optimizer.min_variance()['weights']
        assert w.sum() == pytest.approx(1.0, abs=1e-4)

    def test_inverse_vol_weights_sum(self, optimizer):
        w = optimizer.inverse_vol()['weights']
        assert w.sum() == pytest.approx(1.0, abs=1e-6)

    def test_inverse_vol_lower_vol_gets_higher_weight(self, optimizer):
        res  = optimizer.inverse_vol()
        vols = np.sqrt(np.diag(optimizer.cov))
        low  = int(np.argmin(vols))
        high = int(np.argmax(vols))
        assert res['weights'][low] >= res['weights'][high] - 1e-5

    def test_risk_parity_weights_sum(self, optimizer):
        w = optimizer.risk_parity()['weights']
        assert w.sum() == pytest.approx(1.0, abs=1e-4)

    def test_risk_parity_approx_equal_rc(self, optimizer):
        res = optimizer.risk_parity()
        w   = res['weights']
        pv  = np.sqrt(w @ optimizer.cov @ w)
        rc  = w * (optimizer.cov @ w) / pv
        pct = rc / rc.sum()
        assert np.std(pct) < 0.05   # contributions within 5% std of equal

    def test_hrp_weights_sum(self, optimizer):
        w = optimizer.hierarchical_risk_parity()['weights']
        assert w.sum() == pytest.approx(1.0, abs=1e-6)

    def test_hrp_long_only(self, optimizer):
        w = optimizer.hierarchical_risk_parity()['weights']
        assert np.all(w >= -1e-8)

    def test_cvar_optimization_weights_sum(self, optimizer):
        res = optimizer.cvar_optimization(alpha=0.05)
        assert res['weights'].sum() == pytest.approx(1.0, abs=1e-3)

    def test_max_diversification_weights_sum(self, optimizer):
        res = optimizer.max_diversification({'long_only': True})
        assert res['weights'].sum() == pytest.approx(1.0, abs=1e-4)

    def test_metrics_keys_present(self, optimizer):
        res = optimizer.max_sharpe()
        for key in ('weights', 'expected_return', 'volatility', 'sharpe',
                    'sortino', 'max_drawdown', 'cvar_95', 'tickers'):
            assert key in res, f"Missing key: {key}"

    def test_black_litterman_valid_view(self, optimizer):
        views = {optimizer.tickers[0]: 0.15}
        res   = optimizer.black_litterman(views, tau=0.05)
        assert 'weights' in res
        assert res['weights'].sum() == pytest.approx(1.0, abs=1e-4)

    def test_black_litterman_unknown_ticker_fallback(self, optimizer):
        res = optimizer.black_litterman({'UNKNOWN_XYZ': 0.20})
        assert 'weights' in res
        assert res['weights'].sum() == pytest.approx(1.0, abs=1e-4)

    def test_efficient_frontier_not_empty(self, optimizer):
        ef = optimizer.efficient_frontier(n_points=10)
        assert isinstance(ef, pd.DataFrame)
        assert len(ef) > 0

    def test_efficient_frontier_return_increases(self, optimizer):
        ef = optimizer.efficient_frontier(n_points=10)
        if len(ef) > 2:
            diffs = np.diff(ef['return'].values)
            assert np.sum(diffs >= 0) >= len(diffs) * 0.7   # mostly increasing

    def test_single_asset(self):
        rng2 = np.random.default_rng(7)
        rets = pd.DataFrame({'A': rng2.normal(0.001, 0.02, 300)})
        opt  = PortfolioOptimizer(rets)
        res  = opt.equal_weight()
        assert res['weights'][0] == pytest.approx(1.0, abs=1e-9)

    def test_perfectly_correlated_assets(self):
        rng2 = np.random.default_rng(99)
        base = rng2.normal(0.001, 0.02, 400)
        rets = pd.DataFrame({'A': base, 'B': base + 1e-9, 'C': base + 2e-9})
        opt  = PortfolioOptimizer(rets)
        res  = opt.equal_weight()
        assert res['weights'].sum() == pytest.approx(1.0, abs=1e-6)

    def test_cov_positive_semi_definite(self, optimizer):
        eigvals = np.linalg.eigvalsh(optimizer.cov)
        assert np.all(eigvals >= -1e-8)


# ─────────────────────────────────────────────────────────────────
# PortfolioRiskAnalyzer TESTS
# ─────────────────────────────────────────────────────────────────

class TestPortfolioRiskAnalyzer:

    @pytest.fixture
    def analyzer(self, sample_returns):
        w = np.ones(4) / 4
        return PortfolioRiskAnalyzer(sample_returns, w, risk_free_rate=0.035,
                                     frequency='daily')

    def test_portfolio_returns_length(self, analyzer, sample_returns):
        assert len(analyzer.portfolio_returns()) == len(sample_returns)

    def test_portfolio_returns_is_series(self, analyzer):
        assert isinstance(analyzer.portfolio_returns(), pd.Series)

    def test_var_historical_var_negative(self, analyzer):
        v = analyzer.var_cvar(method='historical')
        assert v['var_95'] < 0

    def test_var_historical_cvar_le_var(self, analyzer):
        v = analyzer.var_cvar(method='historical')
        assert v['cvar_95'] <= v['var_95'] + 1e-9

    def test_var_parametric(self, analyzer):
        v = analyzer.var_cvar(method='parametric')
        assert 'var_95' in v and 'cvar_95' in v

    def test_var_cornish_fisher(self, analyzer):
        v = analyzer.var_cvar(method='cornish_fisher')
        assert 'var_95' in v

    def test_var_monte_carlo(self, analyzer):
        v = analyzer.var_cvar(method='monte_carlo')
        assert v['var_95'] < 0

    def test_drawdown_max_le_zero(self, analyzer):
        dd = analyzer.drawdown_analysis()
        assert dd['max_drawdown'] <= 0

    def test_drawdown_series_length(self, analyzer, sample_returns):
        dd = analyzer.drawdown_analysis()
        assert len(dd['drawdown_series']) == len(sample_returns)

    def test_risk_contribution_weights_sum(self, analyzer):
        rc = analyzer.risk_contribution()
        assert rc['Weight'].sum() == pytest.approx(1.0, abs=1e-6)

    def test_risk_contribution_has_all_assets(self, analyzer, sample_returns):
        rc = analyzer.risk_contribution()
        assert list(rc.index) == list(sample_returns.columns)

    def test_tail_analysis_keys(self, analyzer):
        ta = analyzer.tail_analysis()
        for k in ('skewness', 'kurtosis', 'jb_stat', 'jb_pvalue', 'is_normal',
                  'qq_theoretical', 'qq_empirical'):
            assert k in ta

    def test_regime_detection_returns_two_regimes(self, analyzer):
        reg = analyzer.regime_detection(n_regimes=2)
        assert 'regime_series' in reg
        assert 'stats' in reg
        assert 'rolling_vol' in reg

    def test_stress_test_returns_dataframe(self, analyzer):
        st_df = analyzer.stress_test()
        assert isinstance(st_df, pd.DataFrame)

    def test_stress_test_portfolio_return_column(self, analyzer):
        st_df = analyzer.stress_test()
        assert 'Portfolio Return' in st_df.columns

    def test_rolling_metrics_columns(self, analyzer):
        rm = analyzer.rolling_metrics(window=60)
        for col in ('rolling_return', 'rolling_vol', 'rolling_sharpe', 'rolling_drawdown'):
            assert col in rm.columns


# ─────────────────────────────────────────────────────────────────
# PortfolioBacktester TESTS
# ─────────────────────────────────────────────────────────────────

class TestPortfolioBacktester:

    @pytest.fixture
    def backtester(self, sample_prices):
        return PortfolioBacktester(sample_prices, risk_free_rate=0.035,
                                   frequency='daily')

    def test_equal_weight_backtest_keys(self, backtester):
        r = backtester.backtest('equal_weight', rebalance_freq='monthly',
                                lookback=60, initial_capital=100_000)
        for key in ('equity_curve', 'weights_history', 'turnover_history',
                    'transaction_costs', 'monthly_returns', 'metrics'):
            assert key in r

    def test_equity_curve_starts_near_capital(self, backtester):
        cap = 100_000.0
        r   = backtester.backtest('equal_weight', rebalance_freq='monthly',
                                   lookback=60, initial_capital=cap)
        # First value = cap * (1 + first_day_return); should be within 10% of cap
        assert r['equity_curve'].iloc[0] == pytest.approx(cap, rel=0.10)

    def test_equity_curve_all_positive(self, backtester):
        r = backtester.backtest('equal_weight', rebalance_freq='monthly', lookback=60)
        assert (r['equity_curve'] > 0).all()

    def test_backtest_metrics_finite(self, backtester):
        r = backtester.backtest('equal_weight', rebalance_freq='monthly', lookback=60)
        for k, v in r['metrics'].items():
            if isinstance(v, float):
                assert np.isfinite(v), f"Metric {k} is not finite: {v}"

    def test_inverse_vol_backtest(self, backtester):
        r = backtester.backtest('inverse_vol', rebalance_freq='monthly', lookback=60)
        assert 'equity_curve' in r

    def test_compare_strategies_returns_dataframe(self, backtester):
        df = backtester.compare_strategies(
            ['equal_weight', 'inverse_vol'],
            rebalance_freq='monthly', lookback=60,
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_compare_strategies_has_sharpe(self, backtester):
        df = backtester.compare_strategies(
            ['equal_weight'], rebalance_freq='monthly', lookback=60
        )
        assert 'sharpe' in df.columns

    def test_transaction_cost_reduces_value(self, backtester):
        r0 = backtester.backtest('equal_weight', rebalance_freq='monthly',
                                  lookback=60, transaction_cost_bps=0)
        r1 = backtester.backtest('equal_weight', rebalance_freq='monthly',
                                  lookback=60, transaction_cost_bps=50)
        # With costs, final value should be lower or equal
        assert r1['equity_curve'].iloc[-1] <= r0['equity_curve'].iloc[-1] * 1.001

    def test_quarterly_rebalance(self, backtester):
        r = backtester.backtest('equal_weight', rebalance_freq='quarterly', lookback=60)
        assert 'equity_curve' in r

    def test_monthly_returns_is_series(self, backtester):
        r = backtester.backtest('equal_weight', rebalance_freq='monthly', lookback=60)
        assert isinstance(r['monthly_returns'], pd.Series)


# ─────────────────────────────────────────────────────────────────
# EDGE CASES
# ─────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_missing_data_prices_dropna(self):
        rng2 = np.random.default_rng(5)
        prices = pd.DataFrame({
            'A': rng2.normal(100, 2, 200),
            'B': rng2.normal(50, 1, 200),
        }, index=pd.date_range('2020-01-01', periods=200, freq='B'))
        prices.iloc[10, 0] = np.nan
        prices = prices.dropna()
        bt = PortfolioBacktester(prices)
        r  = bt.backtest('equal_weight', rebalance_freq='monthly', lookback=30)
        assert r is not None and 'equity_curve' in r

    def test_two_asset_portfolio(self):
        rng2 = np.random.default_rng(11)
        rets = pd.DataFrame({
            'X': rng2.normal(0.001, 0.015, 300),
            'Y': rng2.normal(0.0005, 0.010, 300),
        }, index=pd.date_range('2021-01-01', periods=300, freq='B'))
        opt = PortfolioOptimizer(rets)
        for method in ('max_sharpe', 'min_variance', 'risk_parity',
                       'hierarchical_risk_parity', 'equal_weight', 'inverse_vol'):
            res = getattr(opt, method)()
            assert res['weights'].sum() == pytest.approx(1.0, abs=1e-4), \
                f"{method}: weights don't sum to 1"
            assert np.all(res['weights'] >= -1e-5), \
                f"{method}: negative weights in long-only"

    def test_high_correlation_hrp(self):
        rng2 = np.random.default_rng(13)
        base = rng2.normal(0.001, 0.02, 400)
        rets = pd.DataFrame({
            'A': base + rng2.normal(0, 0.001, 400),
            'B': base + rng2.normal(0, 0.001, 400),
            'C': rng2.normal(0.0005, 0.015, 400),
        }, index=pd.date_range('2019-01-01', periods=400, freq='B'))
        opt = PortfolioOptimizer(rets)
        res = opt.hierarchical_risk_parity()
        assert res['weights'].sum() == pytest.approx(1.0, abs=1e-6)

    def test_build_constraints_output(self):
        c = PortfolioOptimizer.build_constraints(5, long_only=True,
                                                  max_weight=0.4, min_weight=0.02)
        assert c['long_only'] is True
        assert c['max_weight'] == pytest.approx(0.4)
        assert c['min_weight'] == pytest.approx(0.02)
