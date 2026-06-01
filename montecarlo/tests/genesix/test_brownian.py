"""
Tests for brownian.py — verifying fundamental Brownian motion properties.

Every test corresponds to a mathematical theorem. If a test fails,
the simulation is mathematically wrong.
"""

import numpy as np
import pytest
from genesix.math.brownian import BrownianMotion, GeometricBrownianMotion


@pytest.fixture
def bm():
    return BrownianMotion(seed=0)


@pytest.fixture
def gbm():
    return GeometricBrownianMotion(seed=0)


class TestBrownianMotionProperties:
    """W(0) = 0, E[W(T)] = 0, Var[W(T)] = T, [W]_T ≈ T."""

    def test_bm_starts_at_zero(self, bm):
        """W(0) = 0 for all paths."""
        W = bm.simulate_path(T=1.0, n_steps=100, n_paths=50)
        assert np.all(W[0, :] == 0.0), "All paths must start at 0"

    def test_bm_mean_zero(self, bm):
        """E[W(T)] ≈ 0 (within 3σ of Monte Carlo sampling error)."""
        n_paths = 10_000
        W = bm.simulate_path(T=1.0, n_steps=252, n_paths=n_paths)
        WT = W[-1, :]
        mean = np.mean(WT)
        # 3σ bound: σ = 1/√n_paths
        assert abs(mean) < 3 / np.sqrt(n_paths), f"E[W(T)] = {mean:.4f}, should be ≈ 0"

    def test_bm_variance_equals_T(self, bm):
        """Var[W(T)] ≈ T (within 5%)."""
        T = 2.0
        n_paths = 20_000
        W = bm.simulate_path(T=T, n_steps=500, n_paths=n_paths)
        var = np.var(W[-1, :])
        assert abs(var - T) / T < 0.05, f"Var[W(T)] = {var:.4f}, expected {T}"

    def test_bm_variance_scales_linearly(self, bm):
        """Var[W(T)] proportional to T."""
        n_paths = 10_000
        n_steps = 252
        for T in [0.5, 1.0, 2.0]:
            W = bm.simulate_path(T=T, n_steps=n_steps, n_paths=n_paths)
            var = np.var(W[-1, :])
            assert abs(var - T) / T < 0.06, f"Var failed for T={T}"

    def test_bm_quadratic_variation_equals_T(self, bm):
        """[W]_T ≈ T (within 10% on average over many paths)."""
        T = 1.0
        n_steps = 10_000
        n_paths = 100
        W = bm.simulate_path(T=T, n_steps=n_steps, n_paths=n_paths)
        qvs = [bm.quadratic_variation(W[:, i:i+1], T) for i in range(n_paths)]
        mean_qv = np.mean(qvs)
        assert abs(mean_qv - T) / T < 0.10, f"Mean QV = {mean_qv:.4f}, expected {T}"

    def test_bm_increments_independent(self, bm):
        """Non-overlapping increments have |correlation| < 0.05."""
        n_paths = 5_000
        W = bm.simulate_path(T=1.0, n_steps=300, n_paths=n_paths)
        inc1 = W[100, :] - W[0, :]
        inc2 = W[300, :] - W[200, :]
        corr = np.corrcoef(inc1, inc2)[0, 1]
        assert abs(corr) < 0.05, f"Increment correlation = {corr:.4f}, should be ≈ 0"

    def test_bm_increments_normal(self, bm):
        """Increments are normally distributed (Jarque-Bera p > 0.01)."""
        from scipy.stats import jarque_bera
        n_paths = 5_000
        W = bm.simulate_path(T=1.0, n_steps=100, n_paths=n_paths)
        increments = W[50, :] - W[49, :]
        _, p_value = jarque_bera(increments)
        assert p_value > 0.01, f"JB p-value = {p_value:.6f}, increments not normal"

    def test_correlated_paths_shape(self, bm):
        """Correlated paths have correct shape."""
        rho = np.array([[1.0, 0.7], [0.7, 1.0]])
        W = bm.simulate_correlated_paths(T=1.0, n_steps=100, n_assets=2, correlation_matrix=rho, n_paths=10)
        assert W.shape == (101, 2, 10)

    def test_correlated_paths_start_at_zero(self, bm):
        """All correlated paths start at zero."""
        rho = np.array([[1.0, 0.5], [0.5, 1.0]])
        W = bm.simulate_correlated_paths(T=1.0, n_steps=50, n_assets=2, correlation_matrix=rho, n_paths=20)
        assert np.all(W[0, :, :] == 0.0)

    def test_correlated_paths_preserve_correlation(self, bm):
        """Simulated correlation between two assets ≈ input correlation (within 0.1)."""
        rho_target = 0.8
        rho_mat = np.array([[1.0, rho_target], [rho_target, 1.0]])
        n_paths = 20_000
        W = bm.simulate_correlated_paths(T=1.0, n_steps=1, n_assets=2, correlation_matrix=rho_mat, n_paths=n_paths)
        w1 = W[1, 0, :]
        w2 = W[1, 1, :]
        rho_sim = np.corrcoef(w1, w2)[0, 1]
        assert abs(rho_sim - rho_target) < 0.1, f"Simulated ρ = {rho_sim:.4f}, expected {rho_target}"

    def test_verify_properties_all_pass(self, bm):
        """verify_properties() returns results consistent with BM axioms."""
        result = bm.verify_properties(T=1.0, n_steps=5000, n_paths=5000)
        assert abs(result["mean_WT"]) < 0.05, "E[W(T)] deviates from 0"
        assert abs(result["var_WT"] - 1.0) < 0.05, "Var[W(T)] deviates from T=1"
        assert abs(result["mean_quadratic_variation"] - 1.0) < 0.15, "QV deviates from T"
        assert abs(result["independent_increments_correlation"]) < 0.05, "Increments not independent"


class TestGeometricBrownianMotion:
    """Tests for GBM: positivity, Itô correction, moments."""

    def test_gbm_always_positive(self, gbm):
        """All GBM prices are > 0 (prices can't go negative)."""
        S = gbm.simulate(S0=100, mu=0.10, sigma=0.30, T=2.0, n_steps=500, n_paths=1000)
        assert np.all(S > 0), "GBM produced non-positive values"

    def test_gbm_starts_at_S0(self, gbm):
        """All paths start at S0."""
        S0 = 150.0
        S = gbm.simulate(S0=S0, mu=0.05, sigma=0.20, T=1.0, n_steps=100, n_paths=20)
        assert np.allclose(S[0, :], S0), "GBM paths don't start at S0"

    def test_gbm_mean_matches_analytical(self, gbm):
        """Simulated E[S(T)] within 2% of S0×exp(μT)."""
        S0, mu, sigma, T = 100, 0.10, 0.20, 1.0
        n_paths = 50_000
        S = gbm.simulate(S0=S0, mu=mu, sigma=sigma, T=T, n_steps=252, n_paths=n_paths)
        ST = S[-1, :]
        analytical_mean = S0 * np.exp(mu * T)
        error_pct = abs(np.mean(ST) - analytical_mean) / analytical_mean * 100
        assert error_pct < 2.0, f"Mean error {error_pct:.2f}% > 2%"

    def test_gbm_ito_correction(self, gbm):
        """
        Median < Mean for GBM — this IS the Itô correction.

        E[S(T)] = S0 exp(μT)  (mean driven by arithmetic drift)
        Median   = S0 exp((μ - σ²/2)T)  (median driven by log drift)

        For σ > 0: median < mean. Forgetting the Itô correction
        overestimates expected log returns.
        """
        S0, mu, sigma, T = 100, 0.10, 0.30, 1.0
        n_paths = 50_000
        S = gbm.simulate(S0=S0, mu=mu, sigma=sigma, T=T, n_steps=252, n_paths=n_paths)
        ST = S[-1, :]
        assert np.median(ST) < np.mean(ST), (
            f"Median ({np.median(ST):.2f}) should be < Mean ({np.mean(ST):.2f}) — "
            "Itô correction not present"
        )

    def test_gbm_log_returns_normal(self, gbm):
        """Log returns of GBM are normally distributed (Jarque-Bera p > 0.01)."""
        from scipy.stats import jarque_bera
        n_paths = 10_000
        S = gbm.simulate(S0=100, mu=0.08, sigma=0.20, T=1.0, n_steps=1, n_paths=n_paths)
        log_returns = np.log(S[-1, :] / 100)
        _, p_value = jarque_bera(log_returns)
        assert p_value > 0.01, f"JB p-value = {p_value:.6f}, log returns not normal"

    def test_gbm_log_return_mean_ito(self, gbm):
        """
        E[log(S(T)/S0)] ≈ (μ - σ²/2)T, NOT μT.

        This is the Itô correction. The naive estimate μT overestimates
        by σ²T/2. For σ=50% crypto vol, that's 12.5% per year!
        """
        mu, sigma, T = 0.10, 0.30, 1.0
        n_paths = 50_000
        S = gbm.simulate(S0=100, mu=mu, sigma=sigma, T=T, n_steps=252, n_paths=n_paths)
        log_ret = np.log(S[-1, :] / 100)
        expected = (mu - 0.5 * sigma**2) * T
        error = abs(np.mean(log_ret) - expected)
        assert error < 0.02, f"Log return mean error {error:.4f}, expected ≈ {expected:.4f}"

    def test_gbm_analytical_moments(self, gbm):
        """Analytical moments: expected_price = S0 exp(μT), median < mean."""
        S0, mu, sigma, T = 100, 0.12, 0.25, 1.0
        moments = gbm.analytical_moments(S0=S0, mu=mu, sigma=sigma, T=T)
        assert abs(moments["expected_price"] - S0 * np.exp(mu * T)) < 1e-6
        assert moments["median_price"] < moments["expected_price"]

    def test_gbm_verify_against_analytical(self, gbm):
        """verify_against_analytical() returns mean_error_pct < 2%."""
        result = gbm.verify_against_analytical(n_paths=30_000)
        assert result["mean_error_pct"] < 2.0, f"Mean error {result['mean_error_pct']:.2f}%"

    def test_gbm_multi_asset_shape(self, gbm):
        """Multi-asset GBM returns correct shape."""
        S0 = np.array([100, 200, 150])
        mu = np.array([0.10, 0.08, 0.12])
        sigma = np.array([0.20, 0.25, 0.18])
        corr = np.array([[1.0, 0.6, 0.4], [0.6, 1.0, 0.5], [0.4, 0.5, 1.0]])
        S = gbm.simulate_multi_asset(S0=S0, mu=mu, sigma=sigma, correlation=corr,
                                      T=1.0, n_steps=100, n_paths=50)
        assert S.shape == (101, 3, 50), f"Shape {S.shape} != (101, 3, 50)"

    def test_gbm_multi_asset_positive(self, gbm):
        """Multi-asset GBM prices are always positive."""
        S0 = np.array([100, 50])
        mu = np.array([0.05, 0.08])
        sigma = np.array([0.30, 0.40])
        corr = np.array([[1.0, -0.5], [-0.5, 1.0]])
        S = gbm.simulate_multi_asset(S0=S0, mu=mu, sigma=sigma, correlation=corr,
                                      T=2.0, n_steps=500, n_paths=200)
        assert np.all(S > 0), "Multi-asset GBM produced non-positive prices"
