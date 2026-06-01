"""
Short rate models — stochastic models for the evolution of interest rates.

These models price bonds and interest rate derivatives analytically.
Each model captures different aspects of interest rate dynamics.

Vasicek (1977): simplest mean-reverting model (allows negative rates)
CIR (1985): mean-reverting, non-negative rates (√r diffusion)
Hull-White (1990): industry standard — fits market curve exactly via θ(t)
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from typing import Callable, Optional


class VasicekModel:
    """
    Vasicek (1977) model.

    dr = κ(θ - r) dt + σ dW

    Analytical zero-coupon bond price:
    P(0,T) = A(T) × exp(-B(T) × r₀)

    B(T) = (1 - e^{-κT}) / κ
    ln A(T) = (θ - σ²/(2κ²))(B(T) - T) - σ²B(T)²/(4κ)
    """

    def __init__(self, kappa: float, theta: float, sigma: float, r0: float):
        self.kappa = kappa
        self.theta = theta
        self.sigma = sigma
        self.r0 = r0
        self.rng = np.random.default_rng(42)

    def _B(self, T: float) -> float:
        return (1 - np.exp(-self.kappa * T)) / self.kappa

    def _ln_A(self, T: float) -> float:
        B = self._B(T)
        k, th, s = self.kappa, self.theta, self.sigma
        return (th - s**2 / (2 * k**2)) * (B - T) - s**2 * B**2 / (4 * k)

    def bond_price(self, T: float) -> float:
        """Analytical ZCB price P(0, T)."""
        B = self._B(T)
        lnA = self._ln_A(T)
        return float(np.exp(lnA - B * self.r0))

    def zero_rate(self, T: float) -> float:
        """Zero rate at maturity T: -ln(P(0,T))/T."""
        if T <= 0:
            return self.r0
        return float(-np.log(self.bond_price(T)) / T)

    def yield_curve(self, maturities: np.ndarray) -> np.ndarray:
        """Full yield curve from model parameters."""
        return np.array([self.zero_rate(T) for T in maturities])

    def bond_option_price(
        self,
        K: float,
        T_option: float,
        T_bond: float,
        option_type: str = "call",
    ) -> float:
        """
        Analytical European option on a ZCB (Jamshidian 1989).

        C = P(0,T_bond)×N(h) - K×P(0,T_option)×N(h - σ_P)
        h = (1/σ_P)×ln(P(0,T_bond)/(K×P(0,T_option))) + σ_P/2
        σ_P = σ×B(T_bond-T_option)×√((1-e^{-2κT_option})/(2κ))
        """
        P_Tb = self.bond_price(T_bond)
        P_To = self.bond_price(T_option)
        B_diff = self._B(T_bond - T_option)
        sigma_P = self.sigma * B_diff * np.sqrt((1 - np.exp(-2 * self.kappa * T_option)) / (2 * self.kappa))
        if sigma_P < 1e-10:
            intrinsic = max(P_Tb - K * P_To, 0)
            return intrinsic

        h = np.log(P_Tb / (K * P_To)) / sigma_P + sigma_P / 2
        if option_type == "call":
            return float(P_Tb * norm.cdf(h) - K * P_To * norm.cdf(h - sigma_P))
        else:
            return float(K * P_To * norm.cdf(-(h - sigma_P)) - P_Tb * norm.cdf(-h))

    def simulate_rates(
        self, T: float, n_steps: int, n_paths: int = 1
    ) -> np.ndarray:
        """Simulate short rate paths using exact OU transition density."""
        dt = T / n_steps
        kappa, theta, sigma = self.kappa, self.theta, self.sigma
        exp_k = np.exp(-kappa * dt)
        var_step = sigma**2 / (2 * kappa) * (1 - np.exp(-2 * kappa * dt))
        std_step = np.sqrt(var_step)

        r = np.zeros((n_steps + 1, n_paths))
        r[0] = self.r0
        for k in range(n_steps):
            mean_k = theta + (r[k] - theta) * exp_k
            r[k + 1] = mean_k + std_step * self.rng.standard_normal(n_paths)
        return r

    def calibrate(self, market_zero_rates: dict) -> dict:
        """
        Calibrate (κ, θ, σ) to market zero rates.

        market_zero_rates: {maturity: zero_rate}
        """
        tenors = np.array(list(market_zero_rates.keys()), dtype=float)
        rates = np.array(list(market_zero_rates.values()), dtype=float)

        def objective(params):
            k, th, s = params
            if k <= 0 or s <= 0:
                return 1e10
            model = VasicekModel(k, th, s, self.r0)
            fitted = model.yield_curve(tenors)
            return float(np.sum((fitted - rates) ** 2))

        x0 = [self.kappa, self.theta, self.sigma]
        bounds = [(0.001, 10), (0.001, 0.2), (0.001, 0.2)]
        result = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)
        k, th, s = result.x
        fitted = VasicekModel(k, th, s, self.r0).yield_curve(tenors)
        rmse = float(np.sqrt(np.mean((fitted - rates) ** 2)))
        return {"kappa": float(k), "theta": float(th), "sigma": float(s), "rmse": rmse}


class CIRModel:
    """
    Cox-Ingersoll-Ross (1985) model.

    dr = κ(θ - r) dt + σ√r dW

    Analytical ZCB price:
    P(0,T) = A(T)^{2κθ/σ²} × exp(-B(T) × r₀)

    γ = √(κ² + 2σ²)
    B(T) = 2(e^{γT}-1) / ((γ+κ)(e^{γT}-1) + 2γ)
    A(T) = 2γ e^{(κ+γ)T/2} / ((γ+κ)(e^{γT}-1) + 2γ)
    """

    def __init__(self, kappa: float, theta: float, sigma: float, r0: float):
        self.kappa = kappa
        self.theta = theta
        self.sigma = sigma
        self.r0 = r0
        self.rng = np.random.default_rng(42)

    def _AB(self, T: float):
        k, th, s = self.kappa, self.theta, self.sigma
        gamma = np.sqrt(k**2 + 2 * s**2)
        exp_gT = np.exp(gamma * T)
        denom = (gamma + k) * (exp_gT - 1) + 2 * gamma
        B = 2 * (exp_gT - 1) / denom
        A_num = 2 * gamma * np.exp((k + gamma) * T / 2)
        A = A_num / denom
        return float(A), float(B)

    def bond_price(self, T: float) -> float:
        """Analytical ZCB price P(0,T)."""
        k, th, s = self.kappa, self.theta, self.sigma
        A, B = self._AB(T)
        exp_pow = 2 * k * th / s**2
        return float(A**exp_pow * np.exp(-B * self.r0))

    def zero_rate(self, T: float) -> float:
        if T <= 0:
            return self.r0
        return float(-np.log(self.bond_price(T)) / T)

    def yield_curve(self, maturities: np.ndarray) -> np.ndarray:
        return np.array([self.zero_rate(T) for T in maturities])

    def feller_condition(self) -> bool:
        """2κθ ≥ σ² guarantees non-negative rates."""
        return 2 * self.kappa * self.theta >= self.sigma**2

    def simulate_rates(
        self, T: float, n_steps: int, n_paths: int = 1
    ) -> np.ndarray:
        """Simulate using Milstein scheme with full truncation."""
        dt = T / n_steps
        k, th, s = self.kappa, self.theta, self.sigma
        sqrt_dt = np.sqrt(dt)

        r = np.zeros((n_steps + 1, n_paths))
        r[0] = self.r0
        for step in range(n_steps):
            r_pos = np.maximum(r[step], 0.0)
            sqrt_r = np.sqrt(r_pos)
            dW = self.rng.standard_normal(n_paths) * sqrt_dt
            r[step + 1] = np.maximum(
                r[step]
                + k * (th - r_pos) * dt
                + s * sqrt_r * dW
                + 0.25 * s**2 * (dW**2 - dt),
                0.0,
            )
        return r

    def calibrate(self, market_zero_rates: dict) -> dict:
        tenors = np.array(list(market_zero_rates.keys()), dtype=float)
        rates = np.array(list(market_zero_rates.values()), dtype=float)

        def objective(params):
            k, th, s = params
            if k <= 0 or th <= 0 or s <= 0:
                return 1e10
            try:
                model = CIRModel(k, th, s, self.r0)
                fitted = model.yield_curve(tenors)
                return float(np.sum((fitted - rates) ** 2))
            except Exception:
                return 1e10

        x0 = [self.kappa, self.theta, self.sigma]
        bounds = [(0.001, 10), (0.001, 0.2), (0.001, 0.2)]
        result = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)
        k, th, s = result.x
        fitted = CIRModel(k, th, s, self.r0).yield_curve(tenors)
        rmse = float(np.sqrt(np.mean((fitted - rates) ** 2)))
        return {"kappa": float(k), "theta": float(th), "sigma": float(s), "rmse": rmse}


class HullWhiteModel:
    """
    Hull-White (1990) — industry standard.

    dr = [θ(t) - κr] dt + σ dW

    θ(t) is calibrated to exactly fit the market yield curve:
    θ(t) = ∂f^M(0,t)/∂t + κ×f^M(0,t) + σ²/(2κ)×(1-e^{-2κt})

    ZCB price at time t, given r(t):
    P(t,T,r) = P^M(0,T)/P^M(0,t) × exp(B(T-t)×f^M(0,t) - σ²/(4κ)×B(T-t)²×(1-e^{-2κt}) - B(T-t)×r(t))

    B(τ) = (1 - e^{-κτ}) / κ
    """

    def __init__(
        self,
        kappa: float,
        sigma: float,
        market_curve_fn: Callable,
    ):
        """
        Args:
            kappa: mean-reversion speed
            sigma: rate volatility
            market_curve_fn: callable(T) → market zero rate at T
        """
        self.kappa = kappa
        self.sigma = sigma
        self.market_curve_fn = market_curve_fn
        self.rng = np.random.default_rng(42)

    def _market_df(self, T: float) -> float:
        """Market discount factor."""
        r = float(self.market_curve_fn(T))
        return np.exp(-r * T)

    def _market_forward(self, T: float, h: float = 1e-5) -> float:
        """Instantaneous forward rate f^M(0,T) = -∂ln P^M(0,T)/∂T."""
        P_plus = self._market_df(T + h)
        P_minus = self._market_df(T - h) if T > h else self._market_df(1e-6)
        return float(-(np.log(P_plus) - np.log(P_minus)) / (2 * h))

    def _market_forward_deriv(self, T: float, h: float = 1e-5) -> float:
        """∂f^M(0,T)/∂T."""
        f_plus = self._market_forward(T + h)
        f_minus = self._market_forward(max(T - h, 1e-6))
        return float((f_plus - f_minus) / (2 * h))

    def _B(self, tau: float) -> float:
        return (1 - np.exp(-self.kappa * tau)) / self.kappa

    def theta_t(self, t: float) -> float:
        """
        Time-dependent drift that fits the market curve exactly.

        θ(t) = ∂f^M(0,t)/∂t + κ×f^M(0,t) + σ²/(2κ)×(1-e^{-2κt})
        """
        f_t = self._market_forward(t)
        df_dt = self._market_forward_deriv(t)
        correction = self.sigma**2 / (2 * self.kappa) * (1 - np.exp(-2 * self.kappa * t))
        return float(df_dt + self.kappa * f_t + correction)

    def bond_price(self, t: float, T: float, r_t: float) -> float:
        """
        ZCB price at time t given current short rate r(t).

        P(t,T,r) = A(t,T) × exp(-B(T-t) × r(t))

        ln A(t,T) = ln(P^M(0,T)/P^M(0,t)) + B(T-t)×f^M(0,t)
                    - σ²/(4κ) × B(T-t)² × (1 - e^{-2κt})
        """
        tau = T - t
        B = self._B(tau)
        P_T = self._market_df(T)
        P_t = self._market_df(t) if t > 0 else 1.0
        f_t = self._market_forward(t) if t > 0 else self._market_forward(1e-5)
        lnA = (
            np.log(P_T / P_t)
            + B * f_t
            - self.sigma**2 / (4 * self.kappa) * B**2 * (1 - np.exp(-2 * self.kappa * t))
        )
        return float(np.exp(lnA - B * r_t))

    def simulate_rates(
        self, T: float, n_steps: int, n_paths: int = 1
    ) -> np.ndarray:
        """
        Simulate rate paths consistent with the market curve.

        dr = [θ(t) - κr] dt + σ dW  (Euler-Maruyama)
        """
        dt = T / n_steps
        sqrt_dt = np.sqrt(dt)
        t_grid = np.linspace(0, T, n_steps + 1)
        r0 = self._market_forward(1e-5)

        r = np.zeros((n_steps + 1, n_paths))
        r[0] = r0
        for k in range(n_steps):
            t = t_grid[k]
            theta = self.theta_t(max(t, 1e-5))
            dW = self.rng.standard_normal(n_paths) * sqrt_dt
            r[k + 1] = r[k] + (theta - self.kappa * r[k]) * dt + self.sigma * dW
        return r

    def swaption_price(
        self,
        swap_start: float,
        swap_end: float,
        fixed_rate: float,
        notional: float = 1.0,
        option_type: str = "payer",
        n_periods_per_year: int = 2,
    ) -> float:
        """
        European swaption via Jamshidian decomposition.

        A swaption = portfolio of ZCB options.
        Strike short rate r* solves: Σ c_i × P(T_s, T_i, r*) = 1.
        Payer swaption = Σ c_i × Put(P(0, T_i), K_i, T_s)
        """
        from scipy.optimize import brentq as _brentq

        T_s = swap_start
        freq = n_periods_per_year
        n = int(round((swap_end - swap_start) * freq))
        payment_times = np.array([swap_start + (i + 1) / freq for i in range(n)])
        coupon = fixed_rate / freq
        c = np.full(n, coupon)
        c[-1] += 1.0  # final coupon + notional
        c *= notional

        # Find r* such that bond portfolio = notional × (1 - DF correction)
        # Actually: Σ c_i × P(T_s, T_i, r*) = notional (par condition)
        def _port_val(r_star):
            return sum(c[i] * self.bond_price(T_s, payment_times[i], r_star)
                       for i in range(n)) - notional

        try:
            r_star = _brentq(_port_val, -0.5, 2.0)
        except Exception:
            # Fallback: rough estimate
            r_star = float(self.market_curve_fn(T_s))

        K_i = np.array([self.bond_price(T_s, payment_times[i], r_star)
                         for i in range(n)])

        # Price each ZCB option
        total = 0.0
        for i in range(n):
            K = K_i[i]
            if option_type == "payer":
                # Payer swaption = sum of Put options on ZCBs (pay fixed = short bond)
                price = self._zcb_option(K, T_s, payment_times[i], "put")
            else:
                price = self._zcb_option(K, T_s, payment_times[i], "call")
            total += abs(c[i]) * price

        return float(total)

    def _zcb_option(self, K: float, T_option: float, T_bond: float, opt_type: str) -> float:
        """European option on ZCB under Hull-White (same as Vasicek formula)."""
        tau = T_bond - T_option
        B = self._B(tau)
        sigma_P = self.sigma * B * np.sqrt(
            (1 - np.exp(-2 * self.kappa * T_option)) / (2 * self.kappa)
        )
        P_Tb = self._market_df(T_bond)
        P_To = self._market_df(T_option)

        if sigma_P < 1e-10:
            intrinsic = max(P_Tb - K * P_To, 0)
            return intrinsic if opt_type == "call" else max(K * P_To - P_Tb, 0)

        h = np.log(P_Tb / (K * P_To)) / sigma_P + sigma_P / 2
        if opt_type == "call":
            return float(P_Tb * norm.cdf(h) - K * P_To * norm.cdf(h - sigma_P))
        else:
            return float(K * P_To * norm.cdf(-(h - sigma_P)) - P_Tb * norm.cdf(-h))

    def cap_floor_price(
        self,
        strike: float,
        maturity: float,
        tenor: float = 0.25,
        notional: float = 1.0,
        cap_or_floor: str = "cap",
    ) -> float:
        """
        Interest rate cap/floor = portfolio of caplets/floorlets.
        Each caplet: option on the forward rate for that period.
        Under Hull-White: equivalent to put/call on ZCB.
        """
        n = int(round(maturity / tenor))
        total = 0.0
        for i in range(n):
            T1 = (i + 1) * tenor
            T2 = T1 + tenor
            K_zcb = 1.0 / (1 + strike * tenor)
            if cap_or_floor == "cap":
                total += notional * (1 + strike * tenor) * self._zcb_option(
                    K_zcb, T1, T2, "put"
                )
            else:
                total += notional * (1 + strike * tenor) * self._zcb_option(
                    K_zcb, T1, T2, "call"
                )
        return float(total)

    def calibrate_to_swaptions(self, swaption_vols: dict) -> dict:
        """
        Calibrate (κ, σ) to market swaption ATM volatilities.

        swaption_vols: {(expiry, tenor): atm_vol}
        """
        pairs = list(swaption_vols.items())

        def objective(params):
            k, s = params
            if k <= 0 or s <= 0:
                return 1e10
            model = HullWhiteModel(k, s, self.market_curve_fn)
            total_sq_err = 0.0
            for (expiry, tenor), target_vol in pairs:
                swap_end = expiry + tenor
                try:
                    # ATM rate
                    from genesix.fixed_income.ir_derivatives import InterestRateSwap
                    freq = 2
                    n_pay = int(round(tenor * freq))
                    pay_times = [expiry + (i + 1) / freq for i in range(n_pay)]
                    dfs = [model._market_df(t) for t in pay_times]
                    day_fracs = [1.0 / freq] * n_pay
                    irs = InterestRateSwap()
                    atm = irs.swap_rate(pay_times, dfs, day_fracs)
                    price = model.swaption_price(expiry, swap_end, atm, 1.0, "payer")
                    # Convert to vol (approx)
                    from scipy.stats import norm as _norm
                    ann = sum(dfs[i] * day_fracs[i] for i in range(n_pay))
                    implied_vol = price / (ann * atm * np.sqrt(expiry)) if ann * atm > 0 else 0.01
                    total_sq_err += (implied_vol - target_vol) ** 2
                except Exception:
                    pass
            return total_sq_err

        x0 = [self.kappa, self.sigma]
        bounds = [(0.001, 5), (0.001, 0.1)]
        result = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)
        kappa, sigma = result.x
        return {
            "kappa": float(kappa),
            "sigma": float(sigma),
            "objective": float(result.fun),
        }
