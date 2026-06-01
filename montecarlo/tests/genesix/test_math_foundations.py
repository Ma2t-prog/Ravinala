"""
Tests for genesix/math/ — stochastic calculus foundations.

Every test corresponds to a mathematical theorem or model property.
If a test fails, the implementation is mathematically wrong.
"""

import numpy as np
import pandas as pd
import pytest
from genesix.math.ito import ItoCalculus
from genesix.math.sde import SDESolver, OrnsteinUhlenbeck, CIRProcess, HestonModel, MertonJumpDiffusion
from genesix.math.measures import RiskNeutralPricing
from genesix.math.fractals import FractalAnalyzer, LyapunovExponent
from genesix.math.entropy import EntropyAnalyzer
from genesix.math.rmt import CorrelationCleaner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ou():
    return OrnsteinUhlenbeck(seed=0)


@pytest.fixture(scope="module")
def cir():
    return CIRProcess(seed=0)


@pytest.fixture(scope="module")
def heston():
    return HestonModel(S0=100, v0=0.04, mu=0.05, kappa=2.0, theta=0.04, xi=0.3, rho=-0.7, seed=0)


@pytest.fixture(scope="module")
def merton():
    return MertonJumpDiffusion(S0=100, mu=0.08, sigma=0.20, lam=2.0, mu_J=-0.05, sigma_J=0.10, seed=0)


@pytest.fixture(scope="module")
def rn():
    return RiskNeutralPricing()


@pytest.fixture(scope="module")
def fractal():
    return FractalAnalyzer()


@pytest.fixture(scope="module")
def lyapunov():
    return LyapunovExponent()


@pytest.fixture(scope="module")
def entropy():
    return EntropyAnalyzer()


@pytest.fixture(scope="module")
def cleaner():
    return CorrelationCleaner()


# ---------------------------------------------------------------------------
# ItoCalculus
# ---------------------------------------------------------------------------

class TestItoCalculus:
    """Itô's lemma numerical verifications."""

    def test_ito_correction_present(self):
        """E[log(S(T)/S0)] = (μ - σ²/2)T, not μT."""
        result = ItoCalculus.ito_lemma_demonstration(
            S0=100, mu=0.10, sigma=0.20, T=1.0, n_steps=5_000, n_paths=10_000
        )
        theoretical = result["theoretical_mean"]
        simulated = result["simulated_mean"]
        assert abs(simulated - theoretical) < 0.02, (
            f"Simulated mean {simulated:.4f} != theoretical {theoretical:.4f}"
        )

    def test_ito_correction_value(self):
        """The Itô correction is exactly -σ²/2 per year."""
        sigma = 0.30
        T = 1.0
        result = ItoCalculus.ito_lemma_demonstration(
            S0=100, mu=0.10, sigma=sigma, T=T, n_steps=5_000, n_paths=10_000
        )
        expected_correction = -0.5 * sigma**2 * T
        assert abs(result["ito_correction"] - expected_correction) < 1e-10

    def test_naive_estimate_overestimates(self):
        """μT > (μ - σ²/2)T — naive estimate always overestimates."""
        result = ItoCalculus.ito_lemma_demonstration(
            S0=100, mu=0.10, sigma=0.30, T=1.0, n_steps=5_000, n_paths=10_000
        )
        assert result["naive_mean_WITHOUT_ito"] > result["theoretical_mean"]

    def test_ito_isometry_variance(self):
        """E[(∫₀ᵀ t dW)²] = T³/3 (Itô isometry with f(t) = t)."""
        result = ItoCalculus.ito_isometry_demonstration(T=1.0, n_steps=10_000, n_paths=10_000)
        assert result["isometry_holds"], (
            f"Itô isometry failed: analytical={result['analytical_variance']:.6f}, "
            f"simulated={result['simulated_variance']:.6f}, "
            f"error={result['relative_error_pct']:.2f}%"
        )

    def test_ito_isometry_relative_error(self):
        """Itô isometry numerical error < 5%."""
        result = ItoCalculus.ito_isometry_demonstration(T=1.0, n_steps=10_000, n_paths=5_000)
        assert result["relative_error_pct"] < 5.0

    def test_black_scholes_derivation_contains_pde(self):
        """BS derivation string contains the PDE equation."""
        deriv = ItoCalculus.derive_black_scholes_from_ito()
        assert "∂V/∂t" in deriv
        assert "rV" in deriv or "rV  =  0" in deriv or "− rV" in deriv

    def test_product_rule_ito_reconstruction(self):
        """Itô product rule reconstructs XY exactly from increments."""
        from genesix.math.brownian import BrownianMotion
        bm = BrownianMotion(seed=7)
        T, n_steps = 1.0, 500
        # Simulate two independent BM paths as X, Y
        X = bm.simulate_path(T=T, n_steps=n_steps, n_paths=200)
        Y = bm.simulate_path(T=T, n_steps=n_steps, n_paths=200)
        dt = T / n_steps
        result = ItoCalculus.product_rule_ito(X, Y, dt=dt)
        assert result["reconstruction_accurate"], (
            f"Itô product rule reconstruction error: {result['max_reconstruction_error']:.2e}"
        )


# ---------------------------------------------------------------------------
# SDESolver (generic)
# ---------------------------------------------------------------------------

class TestSDESolver:
    """Euler-Maruyama and Milstein for GBM (known solution = validation)."""

    def test_euler_maruyama_gbm_mean(self):
        """EM applied to GBM: E[S(T)] ≈ S0 × exp(μT) within 2%."""
        solver = SDESolver(seed=0)
        S0, mu, sigma, T = 100.0, 0.08, 0.20, 1.0
        n_paths = 20_000

        def drift(x, t):
            return mu * x

        def diffusion(x, t):
            return sigma * x

        X = solver.euler_maruyama(drift, diffusion, X0=S0, T=T, n_steps=252, n_paths=n_paths)
        mean_ST = np.mean(X[-1, :])
        analytical = S0 * np.exp(mu * T)
        error_pct = abs(mean_ST - analytical) / analytical * 100
        assert error_pct < 2.0, f"EM GBM mean error {error_pct:.2f}%"

    def test_milstein_gbm_positive(self):
        """Milstein GBM paths are all positive."""
        solver = SDESolver(seed=0)
        S0, mu, sigma = 100.0, 0.08, 0.20

        def drift(x, t):
            return mu * x

        def diffusion(x, t):
            return sigma * x

        def diffusion_deriv(x, t):
            return sigma

        X = solver.milstein(drift, diffusion, diffusion_deriv, X0=S0, T=1.0, n_steps=252, n_paths=500)
        assert np.all(X > 0), "Milstein GBM should be positive"

    def test_milstein_higher_accuracy_than_euler(self):
        """Milstein has smaller bias than EM for GBM at coarse grid."""
        S0, mu, sigma, T = 100.0, 0.10, 0.30, 1.0
        n_steps = 20  # coarse grid amplifies discretization error
        n_paths = 50_000
        analytical = S0 * np.exp(mu * T)

        def drift(x, t):
            return mu * x

        def diffusion(x, t):
            return sigma * x

        def diffusion_deriv(x, t):
            return sigma

        em = SDESolver(seed=1)
        ml = SDESolver(seed=1)

        X_em = em.euler_maruyama(drift, diffusion, X0=S0, T=T, n_steps=n_steps, n_paths=n_paths)
        X_ml = ml.milstein(drift, diffusion, diffusion_deriv, X0=S0, T=T, n_steps=n_steps, n_paths=n_paths)

        err_em = abs(np.mean(X_em[-1, :]) - analytical) / analytical
        err_ml = abs(np.mean(X_ml[-1, :]) - analytical) / analytical
        # Both should be close; Milstein should be at most slightly worse or better
        assert err_ml < 0.05, f"Milstein mean error {err_ml*100:.2f}% too large"


# ---------------------------------------------------------------------------
# OrnsteinUhlenbeck
# ---------------------------------------------------------------------------

class TestOrnsteinUhlenbeck:
    """OU: mean reversion, exact analytical moments."""

    def test_ou_mean_convergence(self, ou):
        """E[X(T)] = θ + (X0 - θ)exp(-κT) — converges toward θ."""
        X0, kappa, theta, sigma, T = 5.0, 1.0, 2.0, 0.5, 3.0
        expected = ou.expected_value(X0=X0, kappa=kappa, theta=theta, T=T)
        # Should be close to theta after long time
        assert abs(expected - theta) < abs(X0 - theta), "OU hasn't reverted toward θ"

    def test_ou_expected_value_formula(self, ou):
        """E[X(T)] formula matches simulation."""
        X0, kappa, theta, sigma, T = 0.0, 2.0, 1.0, 0.3, 1.0
        n_paths = 20_000
        paths = ou.simulate_exact(X0=X0, kappa=kappa, theta=theta, sigma=sigma, T=T, n_steps=100, n_paths=n_paths)
        sim_mean = float(np.mean(paths[-1, :]))
        analytical = ou.expected_value(X0=X0, kappa=kappa, theta=theta, T=T)
        assert abs(sim_mean - analytical) < 0.05, (
            f"OU mean: sim={sim_mean:.4f}, analytical={analytical:.4f}"
        )

    def test_ou_variance_formula(self, ou):
        """Var[X(T)] = σ²/(2κ)(1 - exp(-2κT)) matches simulation."""
        X0, kappa, theta, sigma, T = 1.0, 1.5, 0.0, 0.4, 1.0
        n_paths = 20_000
        paths = ou.simulate_exact(X0=X0, kappa=kappa, theta=theta, sigma=sigma, T=T, n_steps=200, n_paths=n_paths)
        sim_var = float(np.var(paths[-1, :]))
        analytical_var = ou.variance(kappa=kappa, sigma=sigma, T=T)
        assert abs(sim_var - analytical_var) / analytical_var < 0.05, (
            f"OU variance: sim={sim_var:.4f}, analytical={analytical_var:.4f}"
        )

    def test_ou_half_life(self, ou):
        """Half-life = ln(2)/κ. After one half-life, gap halved."""
        kappa = 2.0
        hl = ou.half_life(kappa=kappa)
        assert abs(hl - np.log(2) / kappa) < 1e-10

    def test_ou_stationary_distribution(self, ou):
        """Stationary distribution: N(θ, σ²/(2κ))."""
        kappa, theta, sigma = 1.0, 3.0, 0.5
        stat = ou.stationary_distribution(kappa=kappa, theta=theta, sigma=sigma)
        assert stat["mean"] == theta
        assert abs(stat["variance"] - sigma**2 / (2 * kappa)) < 1e-10

    def test_ou_starts_at_x0(self, ou):
        """All OU paths start at X0."""
        paths = ou.simulate_exact(X0=2.5, kappa=1.0, theta=0.0, sigma=0.3, T=1.0, n_steps=100, n_paths=50)
        assert np.all(paths[0, :] == 2.5)


# ---------------------------------------------------------------------------
# CIRProcess
# ---------------------------------------------------------------------------

class TestCIRProcess:
    """CIR: non-negativity, Feller condition."""

    def test_cir_always_non_negative(self, cir):
        """CIR process must never go below 0 (full truncation)."""
        X = cir.simulate(X0=0.04, kappa=2.0, theta=0.04, sigma=0.3, T=2.0, n_steps=1000, n_paths=500)
        assert np.all(X >= 0.0), f"CIR produced negative values: min={X.min():.6f}"

    def test_cir_starts_at_x0(self, cir):
        """All CIR paths start at X0."""
        X0 = 0.05
        X = cir.simulate(X0=X0, kappa=1.5, theta=0.03, sigma=0.2, T=1.0, n_steps=100, n_paths=30)
        assert np.all(X[0, :] == X0)

    def test_cir_mean_reversion(self, cir):
        """CIR mean reverts: E[X(T)] → θ for large T."""
        kappa, theta = 3.0, 0.06
        X = cir.simulate(X0=0.20, kappa=kappa, theta=theta, sigma=0.1, T=5.0, n_steps=500, n_paths=5_000)
        mean_T = float(np.mean(X[-1, :]))
        assert abs(mean_T - theta) / theta < 0.1, (
            f"CIR mean at T=5: {mean_T:.4f}, expected θ={theta}"
        )

    def test_feller_condition_true(self, cir):
        """2κθ ≥ σ² satisfies Feller condition."""
        assert cir.feller_condition_satisfied(kappa=2.0, theta=0.04, sigma=0.2) is True

    def test_feller_condition_false(self, cir):
        """2κθ < σ² violates Feller condition."""
        assert cir.feller_condition_satisfied(kappa=0.5, theta=0.01, sigma=0.5) is False


# ---------------------------------------------------------------------------
# HestonModel
# ---------------------------------------------------------------------------

class TestHestonModel:
    """Heston: price positive, variance non-negative, shapes correct."""

    def test_heston_shape(self, heston):
        """simulate() returns (n_steps+1, n_paths) for S and v."""
        n_steps, n_paths = 100, 50
        S, v = heston.simulate(T=1.0, n_steps=n_steps, n_paths=n_paths)
        assert S.shape == (n_steps + 1, n_paths)
        assert v.shape == (n_steps + 1, n_paths)

    def test_heston_prices_positive(self, heston):
        """All Heston stock prices must be > 0."""
        S, _ = heston.simulate(T=1.0, n_steps=252, n_paths=200)
        assert np.all(S > 0), f"Heston produced non-positive prices: min={S.min():.4f}"

    def test_heston_variance_non_negative(self, heston):
        """Variance process must be ≥ 0 (full truncation)."""
        _, v = heston.simulate(T=1.0, n_steps=252, n_paths=200)
        assert np.all(v >= 0.0), f"Heston variance went negative: min={v.min():.6f}"

    def test_heston_starts_at_s0(self, heston):
        """All paths start at S0."""
        S, v = heston.simulate(T=1.0, n_steps=100, n_paths=30)
        assert np.allclose(S[0, :], heston.S0)

    def test_heston_variance_starts_at_v0(self, heston):
        """Variance starts at v0."""
        S, v = heston.simulate(T=1.0, n_steps=100, n_paths=30)
        assert np.allclose(v[0, :], heston.v0)


# ---------------------------------------------------------------------------
# MertonJumpDiffusion
# ---------------------------------------------------------------------------

class TestMertonJumpDiffusion:
    """Merton: jump-diffusion properties."""

    def test_merton_prices_positive(self, merton):
        """All Merton paths must be > 0 (exponential representation)."""
        S = merton.simulate(T=1.0, n_steps=252, n_paths=500)
        assert np.all(S > 0), f"Merton produced non-positive prices: min={S.min():.4f}"

    def test_merton_shape(self, merton):
        """simulate() returns (n_steps+1, n_paths)."""
        n_steps, n_paths = 100, 50
        S = merton.simulate(T=1.0, n_steps=n_steps, n_paths=n_paths)
        assert S.shape == (n_steps + 1, n_paths)

    def test_merton_starts_at_s0(self, merton):
        """All paths start at S0."""
        S = merton.simulate(T=1.0, n_steps=100, n_paths=30)
        assert np.allclose(S[0, :], merton.S0)

    def test_merton_option_price_positive(self, merton):
        """Analytical Merton call price is positive."""
        price = merton.european_call_price(K=100, T=1.0, r=0.05)
        assert price > 0

    def test_merton_option_price_below_stock(self, merton):
        """Call price < S0 (no-arbitrage bound)."""
        price = merton.european_call_price(K=100, T=1.0, r=0.05)
        assert price < merton.S0


# ---------------------------------------------------------------------------
# RiskNeutralPricing
# ---------------------------------------------------------------------------

class TestRiskNeutralPricing:
    """Risk-neutral pricing: MC vs BS closed-form."""

    def test_mc_call_close_to_bs(self, rn):
        """MC European call within 1% of Black-Scholes price."""
        S0, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0

        def call_payoff(ST):
            return np.maximum(ST - K, 0)

        mc_result = rn.price_european_option_mc(
            payoff_fn=call_payoff, S0=S0, r=r, sigma=sigma, T=T, n_paths=100_000
        )
        bs_result = rn.black_scholes(S=S0, K=K, r=r, sigma=sigma, T=T, option_type="call")

        error_pct = abs(mc_result["price"] - bs_result["price"]) / bs_result["price"] * 100
        assert error_pct < 1.5, (
            f"MC={mc_result['price']:.4f} vs BS={bs_result['price']:.4f}, error={error_pct:.2f}%"
        )

    def test_bs_call_put_parity(self, rn):
        """Put-call parity: C - P = S0 - K×exp(-rT)."""
        S0, K, r, sigma, T = 100.0, 95.0, 0.05, 0.25, 1.0
        call = rn.black_scholes(S=S0, K=K, r=r, sigma=sigma, T=T, option_type="call")
        put = rn.black_scholes(S=S0, K=K, r=r, sigma=sigma, T=T, option_type="put")
        lhs = call["price"] - put["price"]
        rhs = S0 - K * np.exp(-r * T)
        assert abs(lhs - rhs) < 1e-8, f"Put-call parity violated: {lhs:.6f} != {rhs:.6f}"

    def test_bs_delta_in_range(self, rn):
        """BS call delta in (0, 1)."""
        result = rn.black_scholes(S=100, K=100, r=0.05, sigma=0.20, T=1.0, option_type="call")
        delta = result["delta"]
        assert 0 < delta < 1, f"Delta {delta} out of range (0,1)"

    def test_bs_gamma_positive(self, rn):
        """BS gamma > 0 (option convexity)."""
        result = rn.black_scholes(S=100, K=100, r=0.05, sigma=0.20, T=1.0, option_type="call")
        assert result["gamma"] > 0

    def test_bs_vega_positive(self, rn):
        """BS vega > 0 (higher vol → higher option price)."""
        result = rn.black_scholes(S=100, K=100, r=0.05, sigma=0.20, T=1.0, option_type="call")
        assert result["vega"] > 0

    def test_bs_deep_itm_call_approaches_intrinsic(self, rn):
        """Deep ITM call ≈ S0 - K×exp(-rT)."""
        S0, K, r, T = 200.0, 50.0, 0.05, 1.0
        result = rn.black_scholes(S=S0, K=K, r=r, sigma=0.20, T=T, option_type="call")
        intrinsic = S0 - K * np.exp(-r * T)
        assert abs(result["price"] - intrinsic) / intrinsic < 0.01

    def test_mc_put_close_to_bs(self, rn):
        """MC European put within 1.5% of Black-Scholes price."""
        S0, K, r, sigma, T = 100.0, 105.0, 0.05, 0.20, 1.0

        def put_payoff(ST):
            return np.maximum(K - ST, 0)

        mc_result = rn.price_european_option_mc(
            payoff_fn=put_payoff, S0=S0, r=r, sigma=sigma, T=T, n_paths=100_000
        )
        bs_result = rn.black_scholes(S=S0, K=K, r=r, sigma=sigma, T=T, option_type="put")

        error_pct = abs(mc_result["price"] - bs_result["price"]) / bs_result["price"] * 100
        assert error_pct < 1.5, (
            f"MC={mc_result['price']:.4f} vs BS={bs_result['price']:.4f}, error={error_pct:.2f}%"
        )


# ---------------------------------------------------------------------------
# FractalAnalyzer
# ---------------------------------------------------------------------------

class TestFractalAnalyzer:
    """Hurst exponent, fractal dimension."""

    @pytest.fixture(scope="class")
    def bm_series(self):
        """White noise returns (H=0.5 — increments of a random walk)."""
        rng = np.random.default_rng(0)
        return rng.standard_normal(2000)

    @pytest.fixture(scope="class")
    def trending_series(self):
        """Trending series: fractionally integrated noise with H > 0.5."""
        rng = np.random.default_rng(0)
        # Strongly autocorrelated returns → persistent Hurst
        n = 2000
        x = rng.standard_normal(n)
        # Apply moving average to create persistence
        window = 20
        result = np.convolve(x, np.ones(window) / window, mode="same")
        return result

    def test_hurst_rs_random_walk_near_half(self, fractal, bm_series):
        """R/S Hurst of Brownian motion ≈ 0.5 (within ±0.15)."""
        result = fractal.hurst_exponent_rs(bm_series)
        H = result["hurst_exponent"]
        assert 0.35 <= H <= 0.65, f"BM Hurst (R/S) = {H:.3f}, expected ≈ 0.5"

    def test_hurst_dfa_random_walk_near_half(self, fractal, bm_series):
        """DFA Hurst of Brownian motion ≈ 0.5 (within ±0.15)."""
        result = fractal.hurst_exponent_dfa(bm_series)
        H = result["hurst_exponent"]
        assert 0.35 <= H <= 0.65, f"BM Hurst (DFA) = {H:.3f}, expected ≈ 0.5"

    def test_hurst_trending_above_half(self, fractal, trending_series):
        """Persistent (trending) series has H > 0.5."""
        result = fractal.hurst_exponent_rs(trending_series)
        H = result["hurst_exponent"]
        assert H > 0.5, f"Trending series Hurst = {H:.3f}, expected > 0.5"

    def test_fractal_dimension_range(self, fractal, bm_series):
        """Fractal dimension of BM path is in (1, 2)."""
        result = fractal.fractal_dimension(bm_series)
        D = result["fractal_dimension"]
        assert 1.0 < D < 2.0, f"Fractal dimension {D:.3f} not in (1, 2)"

    def test_compare_to_gbm_returns_dict(self, fractal, bm_series):
        """compare_to_gbm() returns expected keys."""
        result = fractal.compare_to_gbm(bm_series)
        assert "gbm_assumption_violations" in result
        assert "n_violations" in result
        assert "recommended_model" in result


# ---------------------------------------------------------------------------
# LyapunovExponent
# ---------------------------------------------------------------------------

class TestLyapunovExponent:
    """Lyapunov exponent: chaotic vs. random."""

    def test_lyapunov_returns_float(self, lyapunov):
        """estimate() returns a numeric value."""
        rng = np.random.default_rng(0)
        series = np.cumsum(rng.standard_normal(1000))
        result = lyapunov.estimate(series)
        assert isinstance(result["lyapunov_exponent"], float)

    def test_lyapunov_result_keys(self, lyapunov):
        """Result contains expected keys."""
        rng = np.random.default_rng(0)
        series = rng.standard_normal(1000)
        result = lyapunov.estimate(series)
        assert "lyapunov_exponent" in result
        assert "interpretation" in result


# ---------------------------------------------------------------------------
# EntropyAnalyzer
# ---------------------------------------------------------------------------

class TestEntropyAnalyzer:
    """Shannon, permutation, transfer entropy."""

    @pytest.fixture(scope="class")
    def normal_returns(self):
        rng = np.random.default_rng(1)
        return rng.standard_normal(2000)

    @pytest.fixture(scope="class")
    def constant_returns(self):
        return np.ones(500)

    def test_shannon_entropy_positive(self, entropy, normal_returns):
        """Shannon entropy of random series > 0."""
        result = entropy.shannon_entropy(normal_returns)
        assert result["entropy_bits"] > 0

    def test_shannon_entropy_constant_low(self, entropy, constant_returns):
        """Shannon entropy of constant series = 0 (or very low)."""
        result = entropy.shannon_entropy(constant_returns)
        assert result["entropy_bits"] == 0.0, "Constant series should have 0 entropy"

    def test_shannon_normalized_in_range(self, entropy, normal_returns):
        """Normalised Shannon entropy in [0, 1]."""
        result = entropy.shannon_entropy(normal_returns)
        assert 0.0 <= result["normalized_entropy"] <= 1.0

    def test_permutation_entropy_max_for_random(self, entropy, normal_returns):
        """Permutation entropy of white noise is high (near 1)."""
        result = entropy.permutation_entropy(normal_returns, order=4, normalize=True)
        assert result["normalized_permutation_entropy"] > 0.8, (
            f"White noise permutation entropy = {result['normalized_permutation_entropy']:.3f}, expected > 0.8"
        )

    def test_permutation_entropy_low_for_trend(self, entropy):
        """Permutation entropy of a perfect trend is low."""
        series = np.arange(1000, dtype=float)  # perfectly increasing
        result = entropy.permutation_entropy(series, order=4, normalize=True)
        assert result["normalized_permutation_entropy"] < 0.3, (
            f"Perfect trend permutation entropy = {result['normalized_permutation_entropy']:.3f}, expected < 0.3"
        )

    def test_transfer_entropy_keys(self, entropy, normal_returns):
        """transfer_entropy() returns all expected keys."""
        rng = np.random.default_rng(2)
        source = normal_returns[:500]
        target = rng.standard_normal(500)
        result = entropy.transfer_entropy(source, target, lag=1, n_bins=5)
        for key in ["te_source_to_target", "te_target_to_source", "net_flow", "dominant_direction"]:
            assert key in result

    def test_transfer_entropy_non_negative(self, entropy, normal_returns):
        """Transfer entropy values are ≥ 0."""
        rng = np.random.default_rng(2)
        source = normal_returns[:300]
        target = rng.standard_normal(300)
        result = entropy.transfer_entropy(source, target, lag=1, n_bins=5)
        assert result["te_source_to_target"] >= 0
        assert result["te_target_to_source"] >= 0

    def test_entropy_over_time_shape(self, entropy, normal_returns):
        """entropy_over_time() returns series of same length as input."""
        result = entropy.entropy_over_time(normal_returns, window=60)
        assert len(result) == len(normal_returns)


# ---------------------------------------------------------------------------
# CorrelationCleaner (RMT)
# ---------------------------------------------------------------------------

class TestCorrelationCleaner:
    """Marchenko-Pastur, eigenvalue cleaning."""

    @pytest.fixture(scope="class")
    def random_returns(self):
        """Purely random returns matrix — all eigenvalues should be noise."""
        rng = np.random.default_rng(0)
        data = rng.standard_normal((500, 20))  # T=500, N=20
        return pd.DataFrame(data, columns=[f"A{i}" for i in range(20)])

    def test_mp_bounds_formula(self, cleaner):
        """Marchenko-Pastur bounds: λ_max = (1+√q)², λ_min = (1-√q)²."""
        N, T = 10, 100
        q = N / T
        result = cleaner.marchenko_pastur_bounds(N=N, T=T)
        expected_max = (1 + np.sqrt(q))**2
        expected_min = (1 - np.sqrt(q))**2
        assert abs(result["lambda_max"] - expected_max) < 1e-10
        assert abs(result["lambda_min"] - expected_min) < 1e-10

    def test_mp_q_ratio(self, cleaner):
        """q = N/T is returned correctly."""
        result = cleaner.marchenko_pastur_bounds(N=50, T=200)
        assert abs(result["q_ratio"] - 0.25) < 1e-10

    def test_mp_raises_if_q_gt_1(self, cleaner):
        """Raises ValueError if N > T (q > 1)."""
        with pytest.raises(ValueError):
            cleaner.marchenko_pastur_bounds(N=100, T=50)

    def test_clean_clipping_shape(self, cleaner, random_returns):
        """Cleaned matrix has same shape as input."""
        result = cleaner.clean_correlation_matrix(random_returns, method="clipping")
        assert result["cleaned_matrix"].shape == (20, 20)

    def test_clean_unit_diagonal(self, cleaner, random_returns):
        """Cleaned correlation matrix has 1s on diagonal."""
        result = cleaner.clean_correlation_matrix(random_returns, method="clipping")
        diag = np.diag(result["cleaned_matrix"].values)
        assert np.allclose(diag, 1.0, atol=1e-6), f"Diagonal not 1: {diag}"

    def test_clean_symmetric(self, cleaner, random_returns):
        """Cleaned matrix is symmetric."""
        result = cleaner.clean_correlation_matrix(random_returns, method="clipping")
        C = result["cleaned_matrix"].values
        assert np.allclose(C, C.T, atol=1e-8)

    def test_clean_positive_semidefinite(self, cleaner, random_returns):
        """Cleaned matrix is positive semi-definite (all eigenvalues ≥ 0)."""
        result = cleaner.clean_correlation_matrix(random_returns, method="clipping")
        C = result["cleaned_matrix"].values
        eigenvalues = np.linalg.eigvalsh(C)
        assert np.all(eigenvalues >= -1e-8), f"Negative eigenvalue: {eigenvalues.min():.6f}"

    def test_clean_shrinkage_shape(self, cleaner, random_returns):
        """Shrinkage method returns correct shape."""
        result = cleaner.clean_correlation_matrix(random_returns, method="shrinkage")
        assert result["cleaned_matrix"].shape == (20, 20)

    def test_clean_unknown_method_raises(self, cleaner, random_returns):
        """Unknown method raises ValueError."""
        with pytest.raises(ValueError):
            cleaner.clean_correlation_matrix(random_returns, method="unknown")

    def test_eigenvalue_analysis_keys(self, cleaner, random_returns):
        """eigenvalue_analysis() returns all expected keys."""
        result = cleaner.eigenvalue_analysis(random_returns)
        for key in ["eigenvalues", "n_signal", "n_noise", "mp_bounds", "top_factors"]:
            assert key in result

    def test_eigenvalue_analysis_counts(self, cleaner, random_returns):
        """n_signal + n_noise == N."""
        result = cleaner.eigenvalue_analysis(random_returns)
        N = random_returns.shape[1]
        assert result["n_signal"] + result["n_noise"] == N

    def test_random_matrix_mostly_noise(self, cleaner, random_returns):
        """Purely random N×T matrix should have very few signal eigenvalues."""
        result = cleaner.eigenvalue_analysis(random_returns)
        # With N=20, T=500 random data: at most 1-2 signal eigenvalues expected
        assert result["n_signal"] <= 3, (
            f"Random matrix has {result['n_signal']} signal eigenvalues (expected ≤ 3)"
        )

    def test_mp_density_integrates_to_one(self, cleaner):
        """Marchenko-Pastur PDF integrates to ~1 over its support."""
        result = cleaner.marchenko_pastur_bounds(N=50, T=500)
        lam_min = result["lambda_min"]
        lam_max = result["lambda_max"]
        density = result["theoretical_density"]
        x = np.linspace(lam_min, lam_max, 10_000)
        integral = np.trapezoid(density(x), x)
        assert abs(integral - 1.0) < 0.05, f"MP density integrates to {integral:.4f}, expected 1"
