"""Ravinala by TSIVAHINY Matthias — ESG & Green Finance Module."""

import numpy as np
from scipy.stats import norm


class GreeniumCalculator:
    """Estimate the greenium (yield differential) between green and conventional bond ETFs."""

    GREEN_ETFS = ["BGRN", "BNGE"]
    CONV_ETFS = ["AGG", "LQD"]

    def __init__(self, green_ticker: str = "BGRN", conventional_ticker: str = "AGG"):
        self.green_ticker = green_ticker
        self.conventional_ticker = conventional_ticker

    def _get_yield(self, ticker: str) -> float:
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.info
            y = info.get("yield") or info.get("trailingAnnualDividendYield") or info.get("dividendYield")
            if y is not None:
                return float(y)
        except Exception:
            pass
        # Static fallbacks (approximate values as of 2024)
        fallbacks = {
            "BGRN": 0.0385,
            "BNGE": 0.0410,
            "AGG": 0.0430,
            "LQD": 0.0500,
        }
        return fallbacks.get(ticker, 0.0450)

    def estimate_greenium(self) -> dict:
        """
        Compare yield of green bond ETF vs conventional bond ETF.

        Returns dict with greenium_bps, green_yield, conv_yield, source.
        """
        green_yield = self._get_yield(self.green_ticker)
        conv_yield = self._get_yield(self.conventional_ticker)
        greenium_bps = (conv_yield - green_yield) * 10000

        source = "yfinance"
        try:
            import yfinance as yf  # noqa: F401
        except ImportError:
            source = "static_fallback"

        return {
            "greenium_bps": round(greenium_bps, 2),
            "green_yield": round(green_yield, 4),
            "conv_yield": round(conv_yield, 4),
            "source": source,
        }


class CarbonPricer:
    """Carbon allowance pricing using EUA futures and Black-Scholes on carbon derivatives."""

    CARBON_TICKERS = ["EUA=F", "CO2.DE"]

    def get_carbon_price(self) -> dict:
        """
        Fetch EUA carbon allowance price via yfinance.

        Returns dict with price, currency, change_pct, source.
        """
        for ticker in self.CARBON_TICKERS:
            try:
                import yfinance as yf
                t = yf.Ticker(ticker)
                hist = t.history(period="5d")
                if hist is not None and not hist.empty and len(hist) >= 2:
                    price = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    change_pct = (price - prev) / prev * 100
                    return {
                        "price": round(price, 2),
                        "currency": "EUR",
                        "change_pct": round(change_pct, 2),
                        "source": f"yfinance:{ticker}",
                    }
            except Exception:
                continue

        # Static fallback (approximate EUA price)
        return {
            "price": 65.00,
            "currency": "EUR",
            "change_pct": 0.0,
            "source": "static_fallback",
        }

    def price_carbon_option(
        self,
        F: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: str = "call",
    ) -> dict:
        """
        Black-Scholes pricing for a European option on carbon futures.

        Parameters
        ----------
        F : float
            Futures price (EUA per tonne).
        K : float
            Strike price.
        T : float
            Time to maturity in years.
        r : float
            Risk-free rate.
        sigma : float
            Implied volatility of carbon price.
        option_type : str
            "call" or "put".

        Returns dict with price, delta, vega.
        """
        try:
            if T <= 0 or sigma <= 0:
                raise ValueError("T and sigma must be positive.")

            d1 = (np.log(F / K) + 0.5 * sigma ** 2 * T) / (sigma * np.sqrt(T))
            d2 = d1 - sigma * np.sqrt(T)
            df = np.exp(-r * T)

            if option_type.lower() == "call":
                price = df * (F * norm.cdf(d1) - K * norm.cdf(d2))
                delta = df * norm.cdf(d1)
            else:
                price = df * (K * norm.cdf(-d2) - F * norm.cdf(-d1))
                delta = -df * norm.cdf(-d1)

            vega = F * df * norm.pdf(d1) * np.sqrt(T)

            return {
                "price": round(float(price), 4),
                "delta": round(float(delta), 4),
                "vega": round(float(vega), 4),
            }
        except Exception as e:
            return {"price": 0.0, "delta": 0.0, "vega": 0.0, "error": str(e)}

    def dark_spread(
        self,
        coal_price: float,
        power_price: float,
        carbon_price: float,
        efficiency: float = 0.35,
    ) -> float:
        """
        Dark spread: profit margin for coal-fired power generation.

        margin = power_price - coal_price/efficiency - carbon_price * 0.95

        Parameters
        ----------
        coal_price : float
            Coal price in EUR/MWh_thermal.
        power_price : float
            Power price in EUR/MWh_electric.
        carbon_price : float
            EUA price in EUR/tonne CO2.
        efficiency : float
            Plant thermal efficiency (default 0.35).

        Returns EUR/MWh.
        """
        return power_price - coal_price / efficiency - carbon_price * 0.95

    def spark_spread(
        self,
        gas_price: float,
        power_price: float,
        carbon_price: float,
        efficiency: float = 0.55,
    ) -> float:
        """
        Spark spread: profit margin for gas-fired power generation.

        margin = power_price - gas_price/efficiency - carbon_price * 0.35

        Parameters
        ----------
        gas_price : float
            Gas price in EUR/MWh_thermal.
        power_price : float
            Power price in EUR/MWh_electric.
        carbon_price : float
            EUA price in EUR/tonne CO2.
        efficiency : float
            Plant thermal efficiency (default 0.55).

        Returns EUR/MWh.
        """
        return power_price - gas_price / efficiency - carbon_price * 0.35


class ClimateStressTest:
    """
    Climate scenario stress-testing for equity portfolios.

    Applies sector-specific shocks under different transition and physical risk scenarios.
    """

    SECTOR_SHOCKS = {
        "carbon_tax_200": {
            "Energy": -0.30,
            "Utilities": -0.20,
            "Materials": -0.25,
            "Technology": -0.02,
            "Finance": -0.10,
            "Healthcare": -0.01,
            "Consumer": -0.10,
            "Other": -0.15,
        },
        "transition_2030": {
            "Energy": -0.45,
            "Auto": -0.35,
            "Steel": -0.40,
            "Technology": +0.05,
            "Utilities": -0.20,
            "Materials": -0.30,
            "Finance": -0.10,
            "Healthcare": -0.01,
            "Consumer": -0.15,
            "Other": -0.20,
        },
        "physical_flood": {
            "Real Estate": -0.25,
            "Insurance": -0.30,
            "Agriculture": -0.20,
            "Finance": -0.15,
            "Energy": -0.10,
            "Utilities": -0.10,
            "Technology": -0.05,
            "Healthcare": -0.02,
            "Consumer": -0.08,
            "Other": -0.10,
        },
    }

    def __init__(self, portfolio_tickers: list, weights: list):
        """
        Parameters
        ----------
        portfolio_tickers : list of str
            Ticker symbols.
        weights : list of float
            Portfolio weights (must sum to ~1).
        """
        if len(portfolio_tickers) != len(weights):
            raise ValueError("portfolio_tickers and weights must have the same length.")
        self.tickers = portfolio_tickers
        self.weights = weights

    def _get_sector(self, ticker: str) -> str:
        """Attempt to retrieve sector via yfinance, fallback to 'Other'."""
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            return info.get("sector", "Other")
        except Exception:
            return "Other"

    def _map_sector_to_shock(self, sector: str, shocks: dict) -> float:
        """Map yfinance sector name to the closest shock key."""
        sector_lower = sector.lower()
        for key in shocks:
            if key.lower() in sector_lower or sector_lower in key.lower():
                return shocks[key]
        return shocks.get("Other", -0.10)

    def run_scenario(self, scenario: str) -> dict:
        """
        Apply a named climate scenario to the portfolio.

        Parameters
        ----------
        scenario : str
            One of "carbon_tax_200", "transition_2030", "physical_flood".

        Returns dict with scenario, portfolio_pnl_pct, sector_breakdown, var_increase_pct.
        """
        if scenario not in self.SECTOR_SHOCKS:
            raise ValueError(
                f"Unknown scenario '{scenario}'. "
                f"Choose from: {list(self.SECTOR_SHOCKS.keys())}"
            )

        shocks = self.SECTOR_SHOCKS[scenario]
        sector_breakdown = {}
        portfolio_pnl = 0.0

        for ticker, weight in zip(self.tickers, self.weights):
            sector = self._get_sector(ticker)
            shock = self._map_sector_to_shock(sector, shocks)
            contribution = weight * shock
            portfolio_pnl += contribution
            sector_breakdown[ticker] = {
                "sector": sector,
                "shock_pct": round(shock * 100, 2),
                "contribution_pct": round(contribution * 100, 2),
            }

        # Approximate VaR increase: scenario loss amplifies tail risk
        base_var = 0.05  # 5% baseline daily VaR assumption
        var_increase_pct = abs(portfolio_pnl) / base_var * 100

        return {
            "scenario": scenario,
            "portfolio_pnl_pct": round(portfolio_pnl * 100, 2),
            "sector_breakdown": sector_breakdown,
            "var_increase_pct": round(var_increase_pct, 2),
        }

    def altman_esg_score(self, ticker: str) -> dict:
        """
        Compute an ESG-adjusted score for a ticker using yfinance ESG data.

        Uses `esgScores` if available; falls back to governance proxy metrics.

        Returns dict with score (0-100), rating (AAA–CCC), source.
        """
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.info

            # Try direct ESG scores
            esg = info.get("esgScores") or {}
            total_esg = esg.get("totalEsg") or info.get("esgScore")

            if total_esg is not None:
                score = float(total_esg)
                source = "yfinance:esgScores"
            else:
                # Proxy: combine governance metrics
                audit_risk = info.get("auditRisk", 5)
                board_risk = info.get("boardRisk", 5)
                shareholder_risk = info.get("shareholderRightsRisk", 5)
                compensation_risk = info.get("compensationRisk", 5)
                # Lower risk = better ESG; invert and scale to 0-100
                avg_risk = (audit_risk + board_risk + shareholder_risk + compensation_risk) / 4
                score = max(0.0, min(100.0, 100 - avg_risk * 10))
                source = "yfinance:governance_proxy"

            # Normalize to 0-100 if score looks like it's on a 0-10 scale
            if score <= 10:
                score = score * 10

            score = round(float(score), 1)

            # Rating scale
            if score >= 80:
                rating = "AAA"
            elif score >= 65:
                rating = "AA"
            elif score >= 50:
                rating = "A"
            elif score >= 40:
                rating = "BBB"
            elif score >= 30:
                rating = "BB"
            elif score >= 20:
                rating = "B"
            else:
                rating = "CCC"

            return {"score": score, "rating": rating, "source": source}

        except Exception as e:
            return {
                "score": 50.0,
                "rating": "BBB",
                "source": "static_fallback",
                "error": str(e),
            }


class SustainabilityLinkedPayoff:
    """Price Sustainability-Linked Bond (SLB) autocallable structures via Monte Carlo."""

    def price_slb_autocall(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        n_sims: int = 5000,
        base_coupon: float = 0.05,
        esg_bonus: float = 0.005,
        esg_improvement_prob: float = 0.6,
        barrier: float = 0.70,
    ) -> dict:
        """
        Monte Carlo pricing of an ESG-linked autocallable bond.

        At each annual observation:
          - If S_t > K: autocall triggered, investor receives par + coupon.
          - If S_t < barrier * K: knock-in event (capital at risk).
          - If ESG target met (Bernoulli): coupon += esg_bonus.

        Parameters
        ----------
        S : float
            Current spot price of the underlying.
        K : float
            Autocall/strike level.
        T : float
            Maturity in years.
        r : float
            Risk-free rate.
        sigma : float
            Volatility.
        n_sims : int
            Number of Monte Carlo paths.
        base_coupon : float
            Annual base coupon rate.
        esg_bonus : float
            Additional coupon if ESG target met.
        esg_improvement_prob : float
            Probability that ESG improvement target is achieved (Bernoulli).
        barrier : float
            Barrier as fraction of K (e.g. 0.70 means 70% of K).

        Returns dict with price, expected_coupon, autocall_prob, esg_uplift.
        """
        try:
            rng = np.random.default_rng(42)
            n_obs = int(T)
            if n_obs < 1:
                n_obs = 1
            dt = 1.0  # annual steps

            prices = np.zeros((n_sims, n_obs + 1))
            prices[:, 0] = S

            # Simulate GBM paths at annual observation dates
            for t in range(1, n_obs + 1):
                z = rng.standard_normal(n_sims)
                prices[:, t] = prices[:, t - 1] * np.exp(
                    (r - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z
                )

            # ESG improvement draws per year per simulation
            esg_hits = rng.binomial(1, esg_improvement_prob, size=(n_sims, n_obs))

            payoffs = np.zeros(n_sims)
            total_coupons = np.zeros(n_sims)
            autocalled = np.zeros(n_sims, dtype=bool)
            autocall_times = np.full(n_sims, n_obs)

            for obs in range(1, n_obs + 1):
                still_alive = ~autocalled
                triggered = still_alive & (prices[:, obs] >= K)

                for i in np.where(triggered)[0]:
                    coupon = base_coupon
                    if esg_hits[i, obs - 1]:
                        coupon += esg_bonus
                    total_coupons[i] += coupon * obs  # cumulative up to autocall
                    payoffs[i] = (1.0 + coupon) * np.exp(-r * obs)
                    autocalled[i] = True
                    autocall_times[i] = obs

            # Paths that never autocalled — final payoff at maturity
            never_called = ~autocalled
            for i in np.where(never_called)[0]:
                cumulative_coupon = 0.0
                for obs in range(1, n_obs + 1):
                    c = base_coupon + (esg_bonus if esg_hits[i, obs - 1] else 0.0)
                    cumulative_coupon += c * np.exp(-r * obs)

                # Check barrier breach at maturity
                final_price = prices[i, n_obs]
                if final_price < barrier * K:
                    # Capital loss proportional to price drop
                    loss = final_price / K
                    payoffs[i] = loss * np.exp(-r * n_obs) + cumulative_coupon
                else:
                    payoffs[i] = 1.0 * np.exp(-r * n_obs) + cumulative_coupon

                total_coupons[i] = cumulative_coupon

            price = float(np.mean(payoffs))
            expected_coupon = float(np.mean(total_coupons))
            autocall_prob = float(np.mean(autocalled))
            esg_uplift = float(np.mean(esg_hits) * esg_bonus * n_obs)

            return {
                "price": round(price, 4),
                "expected_coupon": round(expected_coupon, 4),
                "autocall_prob": round(autocall_prob, 4),
                "esg_uplift": round(esg_uplift, 6),
            }

        except Exception as e:
            return {
                "price": 1.0,
                "expected_coupon": base_coupon,
                "autocall_prob": 0.5,
                "esg_uplift": 0.0,
                "error": str(e),
            }
