"""
Limits to Arbitrage — why mispricings persist.

Standard finance: "arbitrage is riskless; mispricings are instantly corrected."
Reality: arbitrage is costly, risky, and limited.

Key limits:
1. Fundamental risk: arbitrageur's long/short may diverge before converging
   (Keynes: "market can stay irrational longer than you can stay solvent")

2. Noise trader risk: mispricing can worsen before improving
   (DeLong, Shleifer, Summers & Waldmann 1990)

3. Synchronization risk: each arbitrageur waits for others to act first
   (Abreu & Brunnermeier 2002)

4. Implementation costs: short-selling costs, margin requirements, capital limits

5. Model risk: what if the "fundamental value" estimate is wrong?

Reference: Shleifer & Vishny (1997), Gromb & Vayanos (2010)
"""

from __future__ import annotations

import numpy as np
from typing import Optional


class LimitsToArbitrage:
    """Quantify and simulate limits to arbitrage."""

    # ------------------------------------------------------------------ #
    # Convergence risk                                                    #
    # ------------------------------------------------------------------ #

    def convergence_risk(
        self,
        initial_mispricing: float,
        fundamental_vol: float,
        noise_trader_vol: float,
        horizon: int = 252,
        seed: int = 42,
        n_paths: int = 10_000,
    ) -> dict:
        """
        Simulate mispricing path: will it converge before the arbitrageur blows up?

        Model (simplified DSSW):
        - Mispricing follows mean-reverting process + noise trader shock
        - Arbitrageur has finite horizon (margin call if loss > threshold)

        dz_t = -κ × z_t × dt + σ_fund × dW₁ + σ_noise × dW₂

        where z_t = mispricing (price - fundamental value)

        Returns probability that:
        a) Mispricing converges to zero before horizon
        b) Mispricing worsens by >50% before improving (noise trader risk)
        """
        rng = np.random.default_rng(seed)
        kappa = 0.05  # mean reversion speed
        dt = 1 / 252

        z = np.full(n_paths, initial_mispricing)
        converged = np.zeros(n_paths, dtype=bool)
        worsened_50pct = np.zeros(n_paths, dtype=bool)

        max_mispricing = np.abs(z.copy())

        for t in range(horizon):
            dW1 = rng.standard_normal(n_paths)
            dW2 = rng.standard_normal(n_paths)

            dz = (-kappa * z * dt
                  + fundamental_vol * np.sqrt(dt) * dW1
                  + noise_trader_vol * np.sqrt(dt) * dW2)
            z = z + dz
            max_mispricing = np.maximum(max_mispricing, np.abs(z))

            converged = converged | (np.abs(z) < initial_mispricing * 0.1)

        worsened_50pct = max_mispricing > np.abs(initial_mispricing) * 1.5

        p_converge = float(np.mean(converged))
        p_worsen = float(np.mean(worsened_50pct))
        p_survive = float(np.mean(~worsened_50pct & converged))

        final_z = z

        return {
            "initial_mispricing": float(initial_mispricing),
            "p_converge_by_horizon": p_converge,
            "p_worsen_50pct_first": p_worsen,
            "p_profitable_convergence": p_survive,
            "mean_final_mispricing": float(np.mean(final_z)),
            "std_final_mispricing": float(np.std(final_z)),
            "horizon_days": horizon,
            "interpretation": (
                f"P(converge) = {p_converge:.1%}, "
                f"P(worsen 50% first) = {p_worsen:.1%}. "
                f"Noise trader risk is {noise_trader_vol/fundamental_vol:.1f}× fundamental risk. "
                f"Profitable convergence probability = {p_survive:.1%}."
            ),
        }

    # ------------------------------------------------------------------ #
    # Short-selling costs and constraints                                 #
    # ------------------------------------------------------------------ #

    def short_selling_cost(
        self,
        borrow_fee_annual: float,
        overvaluation_pct: float,
        expected_convergence_years: float,
        volatility: float,
        risk_free_rate: float = 0.05,
    ) -> dict:
        """
        Analyze whether shorting an overvalued asset is profitable.

        Profit = Overvaluation - Borrow costs - Funding costs
               - Risk premium for noise trader risk

        Short-seller's break-even: overvaluation must exceed total costs.

        Historical borrow fees:
        - Easy-to-borrow: 0.25% - 0.5% pa
        - Hard-to-borrow (hot stocks): 50% - 100% pa
        - Squeeze situations: 300%+ pa

        Duffie, Garleanu & Pedersen (2002): high borrow costs → smaller short
        interest → larger persistent mispricings.
        """
        # Expected gross profit from convergence
        gross_pnl = overvaluation_pct / 100.0

        # Costs
        borrow_cost = borrow_fee_annual * expected_convergence_years
        opportunity_cost = risk_free_rate * expected_convergence_years

        # Risk premium: require Sharpe ≥ 1 on the trade
        vol_total = volatility * np.sqrt(expected_convergence_years)
        required_risk_premium = vol_total * 1.0  # Sharpe=1 threshold

        total_cost = borrow_cost + opportunity_cost
        net_pnl = gross_pnl - total_cost
        is_viable = net_pnl > required_risk_premium

        # Break-even overvaluation
        breakeven_overval = (total_cost + required_risk_premium) * 100

        return {
            "gross_profit_pct": float(gross_pnl * 100),
            "borrow_cost_pct": float(borrow_cost * 100),
            "opportunity_cost_pct": float(opportunity_cost * 100),
            "total_cost_pct": float(total_cost * 100),
            "risk_premium_required_pct": float(required_risk_premium * 100),
            "net_pnl_pct": float(net_pnl * 100),
            "trade_viable": bool(is_viable),
            "breakeven_overvaluation_pct": float(breakeven_overval),
            "interpretation": (
                f"Net P&L = {net_pnl*100:.2f}%. "
                + ("Trade viable." if is_viable
                   else f"Not viable: need {breakeven_overval:.1f}% overvaluation "
                        f"to break even (current: {overvaluation_pct:.1f}%).")
            ),
        }

    # ------------------------------------------------------------------ #
    # Capital constraints and fire sales                                  #
    # ------------------------------------------------------------------ #

    def margin_spiral(
        self,
        initial_equity: float,
        leverage: float,
        asset_value: float,
        margin_requirement: float = 0.10,
        price_drop_pct: float = 0.05,
        n_rounds: int = 10,
    ) -> dict:
        """
        Simulate margin call spiral (Brunnermeier & Pedersen 2009).

        When asset prices fall:
        1. Losses reduce equity → margin requirements force deleveraging
        2. Forced selling → further price declines
        3. New margin calls → more forced selling

        This feedback loop amplifies volatility and explains liquidity crises.

        Returns sequence of equity, leverage, and fire-sale amounts.
        """
        equity_history = [initial_equity]
        leverage_history = [leverage]
        assets_history = [asset_value]
        fire_sale_history = [0.0]

        total_assets = initial_equity * leverage
        debt = total_assets - initial_equity

        for round_ in range(n_rounds):
            current_assets = assets_history[-1]
            current_equity = equity_history[-1]

            # Price drop → equity loss
            loss = current_assets * price_drop_pct
            new_equity = current_equity - loss
            new_assets = current_assets * (1 - price_drop_pct)

            if new_equity <= 0:
                equity_history.append(0.0)
                leverage_history.append(float("inf"))
                assets_history.append(0.0)
                fire_sale_history.append(new_assets)
                break

            current_lev = new_assets / new_equity
            max_leverage = 1.0 / margin_requirement

            if current_lev > max_leverage:
                # Must delever: sell assets to bring leverage down
                # new_assets - sold = max_lev × new_equity
                # But debt = (new_assets - sold) - new_equity... simplified:
                target_assets = max_leverage * new_equity
                fire_sale = max(0.0, new_assets - target_assets)
                # Fire sale depresses price further by price_drop_pct × fire_sale/current_assets
                extra_drop_pct = 0.01 * (fire_sale / (current_assets + 1e-10))
                new_assets = target_assets - target_assets * extra_drop_pct
                new_equity = new_equity - target_assets * extra_drop_pct
                new_lev = new_assets / new_equity if new_equity > 0 else float("inf")
            else:
                fire_sale = 0.0
                new_lev = current_lev

            equity_history.append(float(new_equity))
            leverage_history.append(float(new_lev))
            assets_history.append(float(new_assets))
            fire_sale_history.append(float(fire_sale))

            # Stop if leverage normalized
            if new_lev <= max_leverage * 1.01:
                break

        total_loss = initial_equity - equity_history[-1]
        total_fire_sale = sum(fire_sale_history)

        return {
            "equity_path": equity_history,
            "leverage_path": leverage_history,
            "asset_path": assets_history,
            "fire_sale_path": fire_sale_history,
            "initial_equity": float(initial_equity),
            "final_equity": float(equity_history[-1]),
            "total_loss": float(total_loss),
            "total_fire_sale": float(total_fire_sale),
            "n_margin_call_rounds": len([x for x in fire_sale_history if x > 0]),
            "interpretation": (
                f"Initial equity {initial_equity:.0f} → final {equity_history[-1]:.0f} "
                f"({total_loss/initial_equity*100:.1f}% loss). "
                f"Total fire sales: {total_fire_sale:.0f}. "
                f"Spiral amplified initial {price_drop_pct:.1%} drop."
            ),
        }

    # ------------------------------------------------------------------ #
    # Arbitrage opportunity metrics                                       #
    # ------------------------------------------------------------------ #

    def stat_arb_signal(
        self,
        spread: np.ndarray,
        lookback: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
    ) -> dict:
        """
        Statistical arbitrage signal from mean-reverting spread.

        Classic pairs trade:
        1. Compute z-score of spread vs rolling mean/std
        2. Enter when |z| > entry_z (spread is "far" from equilibrium)
        3. Exit when |z| < exit_z (convergence)

        Measures half-life of mean reversion (AR(1) coefficient).

        Half-life = -ln(2) / ln(|ρ|)
        """
        spread = np.asarray(spread, dtype=float)
        n = len(spread)

        # Rolling z-score
        z_scores = np.zeros(n)
        for i in range(lookback, n):
            window = spread[i - lookback:i]
            mu = window.mean()
            sigma = window.std()
            z_scores[i] = (spread[i] - mu) / (sigma + 1e-10)

        # AR(1) fit for half-life
        y = spread[1:]
        x = spread[:-1]
        rho = float(np.corrcoef(x, y)[0, 1])
        if abs(rho) < 0.9999 and rho < 0:
            half_life = -np.log(2) / np.log(abs(rho))
        elif 0 < rho < 0.9999:
            half_life = -np.log(2) / np.log(rho)
        else:
            half_life = float("inf")

        # Backtest signals
        positions = np.zeros(n)
        pnl = np.zeros(n)
        in_trade = False
        entry_side = 0

        for i in range(lookback, n - 1):
            if not in_trade:
                if z_scores[i] > entry_z:
                    in_trade = True
                    entry_side = -1  # short the spread
                elif z_scores[i] < -entry_z:
                    in_trade = True
                    entry_side = 1  # long the spread
            else:
                positions[i] = entry_side
                pnl[i] = entry_side * -(spread[i] - spread[i - 1])
                if abs(z_scores[i]) < exit_z:
                    in_trade = False
                    entry_side = 0

        n_trades = int(np.sum(np.diff(positions.astype(float)) != 0)) // 2
        total_pnl = float(np.sum(pnl))
        sharpe = float(np.mean(pnl[lookback:]) / (np.std(pnl[lookback:]) + 1e-10) * np.sqrt(252))

        return {
            "z_scores": z_scores[lookback:].tolist(),
            "ar1_rho": float(rho),
            "half_life_days": float(half_life),
            "n_trades": n_trades,
            "total_pnl": total_pnl,
            "sharpe_ratio": sharpe,
            "pct_time_in_trade": float(np.mean(positions[lookback:] != 0)),
            "interpretation": (
                f"Half-life = {half_life:.1f} days, "
                f"AR(1) ρ = {rho:.3f}. "
                f"Sharpe = {sharpe:.2f} from {n_trades} trades."
            ),
        }

    def mispricing_persistence(
        self,
        mispricings: np.ndarray,
        factor_name: str = "anomaly",
    ) -> dict:
        """
        Test whether a mispricing (anomaly return) persists or decays.

        Efficient market hypothesis: mispricings revert quickly.
        Limits to arbitrage: mispricings can persist for months/years.

        Tests:
        - Fama-MacBeth style autocorrelation
        - Half-life of return predictability
        - Whether returns are significant after 1, 3, 6, 12 months
        """
        mispricings = np.asarray(mispricings, dtype=float)
        n = len(mispricings)

        # Autocorrelations at lags 1, 5, 21, 63, 126, 252
        lags = [1, 5, 21, 63, 126, 252]
        autocorrs = {}
        for lag in lags:
            if lag < n:
                x = mispricings[:-lag]
                y = mispricings[lag:]
                autocorrs[f"lag_{lag}"] = float(np.corrcoef(x, y)[0, 1])

        # AR(1) half-life
        if len(mispricings) > 2:
            rho = float(np.corrcoef(mispricings[:-1], mispricings[1:])[0, 1])
            if 0 < rho < 0.9999:
                hl = -np.log(2) / np.log(rho)
            elif rho <= 0:
                hl = 1.0  # rapid reversion
            else:
                hl = float("inf")
        else:
            rho = 0.0
            hl = float("inf")

        return {
            "factor": factor_name,
            "ar1_rho": float(rho),
            "half_life_periods": float(hl),
            "autocorrelations": autocorrs,
            "persistent": bool(hl > 21),  # > 1 month = persistent
            "interpretation": (
                f"'{factor_name}' mispricing half-life = {hl:.1f} periods "
                f"(AR1 ρ={rho:.3f}). "
                + ("Persistent anomaly — limits to arbitrage likely operating."
                   if hl > 21 else "Rapidly mean-reverting — easily arbitraged.")
            ),
        }
