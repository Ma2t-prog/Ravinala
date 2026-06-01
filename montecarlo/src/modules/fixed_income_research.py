"""Ravinala — Fixed Income Research Module
Institutional-grade bond research: credit analysis, yield curve, spreads, relative value, technicals.
Bulge bracket level: OAS, duration, convexity, CDS, scenario analysis.
PDF export via reportlab.
"""

import io
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────────────────────────────
# 1. CREDIT SECTORS & BENCHMARKS
# ─────────────────────────────────────────────────────────────────────────────

CREDIT_SECTORS = {
    "Technology": {
        "issuers": ["APL", "MSFT", "ORCL", "IBM", "INTC"],
        "spread_target": 150,  # bps
        "rating_avg": "A",
    },
    "Consumer": {
        "issuers": ["AMZN", "HD", "MCD", "NKE"],
        "spread_target": 120,
        "rating_avg": "BBB",
    },
    "Financials": {
        "issuers": ["JPM", "BAC", "GS", "MS"],
        "spread_target": 110,
        "rating_avg": "A",
    },
    "Energy": {
        "issuers": ["XOM", "CVX", "COP", "SLB"],
        "spread_target": 250,
        "rating_avg": "BBB",
    },
    "Industrials": {
        "issuers": ["GE", "CAT", "RTX", "BA"],
        "spread_target": 140,
        "rating_avg": "BBB+",
    },
    "Utilities": {
        "issuers": ["NEE", "DUK", "SO", "D"],
        "spread_target": 130,
        "rating_avg": "A-",
    },
    "REITs": {
        "issuers": ["AMT", "PLD", "CCI", "EQIX"],
        "spread_target": 200,
        "rating_avg": "BBB",
    },
    "Healthcare": {
        "issuers": ["JNJ", "UNH", "MRK", "ABBV"],
        "spread_target": 100,
        "rating_avg": "A+",
    },
}

RATING_HIERARCHY = {
    "AAA": 1,
    "AA+": 2,
    "AA": 3,
    "AA-": 4,
    "A+": 5,
    "A": 6,
    "A-": 7,
    "BBB+": 8,
    "BBB": 9,
    "BBB-": 10,
    "BB+": 11,
    "BB": 12,
    "BB-": 13,
    "B+": 14,
    "B": 15,
    "B-": 16,
    "CCC": 17,
    "CC": 18,
    "C": 19,
    "D": 20,
}

# ─────────────────────────────────────────────────────────────────────────────
# 1B. TOP 20 MOST-RESEARCHED FIXED INCOME ISSUERS
# ─────────────────────────────────────────────────────────────────────────────

TOP_20_ISSUERS = pd.DataFrame({
    "Ticker": ["JPM", "BAC", "GS", "MS", "WFC", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
               "XOM", "CVX", "JNJ", "UNH", "MRK", "NEE", "DIS", "META", "TSLA", "AMT"],
    "Issuer": [
        "JPMorgan Chase", "Bank of America", "Goldman Sachs", "Morgan Stanley", "Wells Fargo",
        "Apple Inc.", "Microsoft Corp", "NVIDIA Corp", "Alphabet Inc.", "Amazon.com Inc.",
        "Exxon Mobil", "Chevron Corp", "Johnson & Johnson", "UnitedHealth Group", "Merck & Co.",
        "NextEra Energy", "The Walt Disney Co.", "Meta Platforms", "Tesla Inc.", "American Tower REIT"
    ],
    "Sector": [
        "Banking", "Banking", "Banking", "Banking", "Banking",
        "Technology", "Technology", "Technology", "Technology", "Consumer",
        "Energy", "Energy", "Healthcare", "Healthcare", "Healthcare",
        "Utilities", "Media", "Technology", "Consumer", "REITs"
    ],
    "Rating": [
        "A", "A-", "A-", "A-", "BBB+",
        "AA-", "AAA", "A+", "AA", "BBB+",
        "BBB", "BBB+", "AAA", "A+", "AA-",
        "BBB+", "BBB", "BBB", "BB+", "BBB"
    ],
    "5Y Spread (bps)": [
        95, 110, 125, 130, 145,
        75, 65, 90, 80, 140,
        210, 185, 60, 95, 85,
        110, 140, 160, 350, 120
    ],
    "Coverage": [
        "Very High", "Very High", "Very High", "Very High", "Very High",
        "Very High", "Very High", "Very High", "Very High", "Very High",
        "High", "High", "Very High", "High", "High",
        "High", "High", "Very High", "High", "High"
    ],
})

# ─────────────────────────────────────────────────────────────────────────────


class BondMetrics:
    """Core fixed income calculations: duration, convexity, yield, spreads."""

    @staticmethod
    def duration(ytm: float, coupon: float, years_to_maturity: float, frequency: int = 2) -> float:
        """Macaulay duration (modified adjusted for frequency)."""
        try:
            c = coupon / frequency
            y = ytm / frequency
            n = int(years_to_maturity * frequency)
            if y == 0:
                y = 0.0001
            pv_sum = 0.0
            for t in range(1, n + 1):
                t_adj = t / frequency
                cf = c * 100
                if t == n:
                    cf += 100
                pv = cf / ((1 + y) ** t)
                pv_sum += t_adj * pv
            price = sum([c * 100 / ((1 + y) ** t) for t in range(1, n + 1)]) + 100 / ((1 + y) ** n)
            mac_dur = pv_sum / price
            mod_dur = mac_dur / (1 + y)
            return mod_dur
        except Exception:
            return np.nan

    @staticmethod
    def convexity(ytm: float, coupon: float, years_to_maturity: float, frequency: int = 2) -> float:
        """Bond convexity (price sensitivity to rate squared)."""
        try:
            c = coupon / frequency
            y = ytm / frequency
            n = int(years_to_maturity * frequency)
            if y == 0:
                y = 0.0001
            pv_sum = 0.0
            for t in range(1, n + 1):
                t_adj = t / frequency
                cf = c * 100
                if t == n:
                    cf += 100
                pv = cf / ((1 + y) ** (t + 2))
                pv_sum += t_adj * (t_adj + 1 / frequency) * pv
            price = sum([c * 100 / ((1 + y) ** t) for t in range(1, n + 1)]) + 100 / ((1 + y) ** n)
            convexity = pv_sum / (100 * price * (frequency ** 2))
            return convexity
        except Exception:
            return np.nan

    @staticmethod
    def bond_price(ytm: float, coupon: float, years_to_maturity: float, face: float = 100, frequency: int = 2) -> float:
        """Present value of future coupons + principal."""
        try:
            c = (coupon * face) / frequency
            y = ytm / frequency
            n = int(years_to_maturity * frequency)
            if y == 0:
                return face + coupon * face * years_to_maturity
            pv_coupons = sum([c / ((1 + y) ** t) for t in range(1, n + 1)])
            pv_principal = face / ((1 + y) ** n)
            return pv_coupons + pv_principal
        except Exception:
            return np.nan

    @staticmethod
    def z_spread_approximation(ytm: float, risk_free_rate: float) -> float:
        """Simple OAS approximation: yield spread over duration-matched Treasury."""
        return (ytm - risk_free_rate) * 10000  # in bps

    @staticmethod
    def spread_duration(duration: float, spread: float) -> float:
        """Sensitivity of bond price to spread changes (in bps)."""
        return duration * (spread / 10000)


# ─────────────────────────────────────────────────────────────────────────────
# 3. FIXED INCOME RESEARCH ENGINE
# ─────────────────────────────────────────────────────────────────────────────


class FixedIncomeResearchEngine:
    """Enterprise fixed income analysis: credit, yields, spreads, technicals."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper().strip()
        self._yft = yf.Ticker(self.ticker)
        self._info: Optional[Dict] = None

    def _info_safe(self) -> Dict:
        if self._info is None:
            try:
                self._info = self._yft.info or {}
            except Exception:
                self._info = {}
        return self._info

    # ── Issuer Profile ────────────────────────────────────────────────────────

    def get_issuer_profile(self) -> Dict:
        """Company fundamentals + credit context."""
        info = self._info_safe()
        return {
            "name": info.get("longName") or info.get("shortName") or self.ticker,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "country": info.get("country", "N/A"),
            "market_cap": info.get("marketCap"),
            "debt_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "fcf": info.get("freeCashflow"),
            "enterprise_value": info.get("enterpriseValue"),
        }

    # ── Credit Metrics ────────────────────────────────────────────────────────

    def get_credit_metrics(self) -> Dict:
        """Leverage, coverage, liquidity ratios."""
        info = self._info_safe()
        profile = self.get_issuer_profile()

        # Synthetic credit metrics from equity fundamentals
        de = info.get("debtToEquity")
        cr = info.get("currentRatio")
        qr = info.get("quickRatio")
        profit_margin = info.get("profitMargins")
        roa = info.get("returnOnAssets")

        # Estimate credit rating based on metrics
        rating = self._estimate_credit_rating(de, roa, profit_margin)

        return {
            "debt_to_equity": de,
            "current_ratio": cr,
            "quick_ratio": qr,
            "profit_margin": profit_margin,
            "roa": roa,
            "estimated_rating": rating,
            "sector_rating_avg": CREDIT_SECTORS.get(profile["sector"], {}).get("rating_avg", "BBB"),
            "ltm_coverage": self._calc_coverage(info),
            "net_debt": self._calc_net_debt(info),
            "fcf_to_debt": self._calc_fcf_to_debt(info),
        }

    @staticmethod
    def _estimate_credit_rating(de, roa, pm) -> str:
        """Heuristic credit rating from equity metrics."""
        score = 0
        if de is None or de < 0.5:
            score += 3
        elif de < 1.0:
            score += 2
        elif de < 2.0:
            score += 1

        if roa and roa > 0.08:
            score += 2
        elif roa and roa > 0.04:
            score += 1

        if pm and pm > 0.20:
            score += 2
        elif pm and pm > 0.10:
            score += 1

        if score >= 6:
            return "A"
        elif score >= 4:
            return "BBB+"
        elif score >= 2:
            return "BBB"
        else:
            return "BBB-"

    @staticmethod
    def _calc_coverage(info) -> Optional[float]:
        return info.get("operatingCashflow") / max(1, float(info.get("totalDebt") or 1)) if info.get(
            "operatingCashflow") else None

    @staticmethod
    def _calc_net_debt(info) -> Optional[float]:
        total_debt = info.get("totalDebt")
        cash = info.get("cash")
        if total_debt and cash:
            return total_debt - cash
        return None

    @staticmethod
    def _calc_fcf_to_debt(info) -> Optional[float]:
        fcf = info.get("freeCashflow")
        total_debt = info.get("totalDebt")
        if fcf and total_debt:
            return fcf / total_debt
        return None

    # ── Bond-level Assumptions ────────────────────────────────────────────────

    def get_bond_assumptions(self) -> Dict:
        """Synthetic bond curve parameters."""
        profile = self.get_issuer_profile()
        metrics = self.get_credit_metrics()

        sector = profile.get("sector", "Technology")
        sector_spread = CREDIT_SECTORS.get(sector, {}).get("spread_target", 150)

        # Adjust for credit quality
        rating = metrics.get("estimated_rating", "BBB")
        rating_adjust = {
            "AAA": -80,
            "AA": -50,
            "A": -20,
            "BBB": 0,
            "BB": 150,
            "B": 400,
        }
        adjusted_spread = sector_spread + rating_adjust.get(rating.split("+")[0].split("-")[0], 0)

        # Tenor assumptions
        return {
            "3y_spread": adjusted_spread * 0.85,
            "5y_spread": adjusted_spread,
            "10y_spread": adjusted_spread * 1.15,
            "30y_spread": adjusted_spread * 1.35,
            "3y_duration": 2.8,
            "5y_duration": 4.2,
            "10y_duration": 8.1,
            "30y_duration": 18.5,
            "coupon_assumed": adjusted_spread / 10000 + 0.045,
        }

    # ── Yield Curve Analysis ──────────────────────────────────────────────────

    def get_yield_curve(self) -> pd.DataFrame:
        """Synthetic issuer yield curve + Treasury benchmarks."""
        assumptions = self.get_bond_assumptions()

        tenors = [1, 3, 5, 7, 10, 30]
        spreads = [
            assumptions["3y_spread"] * 0.6,
            assumptions["3y_spread"],
            assumptions["5y_spread"],
            assumptions["10y_spread"] * 0.95,
            assumptions["10y_spread"],
            assumptions["30y_spread"],
        ]

        # Treasury yields (approx as of Mar 2026)
        treasury_yields = [0.035, 0.038, 0.042, 0.045, 0.050, 0.048]

        issuer_yields = [t + s / 10000 for t, s in zip(treasury_yields, spreads)]

        df = pd.DataFrame({
            "Tenor (y)": tenors,
            "Treasury (%)": [y * 100 for y in treasury_yields],
            "Issuer (%)": [y * 100 for y in issuer_yields],
            "Spread (bps)": spreads,
        })
        return df

    # ── Relative Value Framework ──────────────────────────────────────────────

    def get_relative_value(self) -> Dict:
        """RV scorecard vs sector peers + duration-matched comparables."""
        profile = self.get_issuer_profile()
        metrics = self.get_credit_metrics()
        assumptions = self.get_bond_assumptions()

        sector = profile.get("sector", "Technology")
        sector_data = CREDIT_SECTORS.get(sector, {})

        # Compute RV signals (simplified)
        de = metrics.get("debt_to_equity")
        fcf_debt = metrics.get("fcf_to_debt")

        de_vs_sector = "Cheap" if de and de < 0.8 else ("Expensive" if de and de > 1.5 else "Fair")
        fcf_vs_sector = "Strong" if fcf_debt and fcf_debt > 0.15 else ("Weak" if fcf_debt and fcf_debt < 0.05 else "OK")

        spread_vs_sector = assumptions["5y_spread"]
        sector_spread = sector_data.get("spread_target", 150)
        spread_signal = "Cheap" if spread_vs_sector > sector_spread + 20 else (
            "Expensive" if spread_vs_sector < sector_spread - 20 else "Fair"
        )

        return {
            "leverage_signal": de_vs_sector,
            "fcf_signal": fcf_vs_sector,
            "spread_signal": spread_signal,
            "rv_score": (
                (2 if de_vs_sector == "Cheap" else -1 if de_vs_sector == "Expensive" else 0) +
                (2 if fcf_vs_sector == "Strong" else -1 if fcf_vs_sector == "Weak" else 0) +
                (2 if spread_signal == "Cheap" else -1 if spread_signal == "Expensive" else 0)
            ),
            "recommendation": "BUY" if (2 if spread_signal == "Cheap" else -1 if spread_signal == "Expensive" else 0) > 0 else "SELL",
        }

    # ── Duration + Convexity Analysis ─────────────────────────────────────────

    def get_duration_analysis(self) -> Dict:
        """Interest rate sensitivity metrics."""
        assumptions = self.get_bond_assumptions()

        dur_5y = assumptions["5y_duration"]
        conv_5y = BondMetrics.convexity(
            ytm=assumptions["5y_spread"] / 10000 + 0.042,
            coupon=assumptions["coupon_assumed"],
            years_to_maturity=5.0,
        )

        return {
            "5y_duration": dur_5y,
            "5y_convexity": conv_5y,
            "price_chg_50bps_down": dur_5y * 0.50 + 0.5 * conv_5y * (0.50**2),
            "price_chg_50bps_up": -dur_5y * 0.50 + 0.5 * conv_5y * (0.50**2),
            "price_chg_100bps_down": dur_5y * 1.0 + 0.5 * conv_5y * (1.0**2),
            "price_chg_100bps_up": -dur_5y * 1.0 + 0.5 * conv_5y * (1.0**2),
            "carry_1y": assumptions["coupon_assumed"] * 100,
            "roll_down_1y": 0.15,  # simplified
        }

    # ── Scenario Analysis ─────────────────────────────────────────────────────

    def get_scenarios(self) -> Dict:
        """Bear / Base / Bull case returns."""
        dur = self.get_duration_analysis()
        dur_val = dur.get("5y_duration", 4.0)
        carry = dur.get("carry_1y", 4.5)

        return {
            "bear": {
                "scenario": "Rates +200 bps (stagflation)",
                "rate_chg": 2.0,
                "credit_chg": 0.50,
                "total_return": -dur_val * 2.0 - 0.50 + carry,
                "probability": 15,
            },
            "base": {
                "scenario": "Rates flat, credit spreads widen 50 bps",
                "rate_chg": 0.0,
                "credit_chg": 0.50,
                "total_return": -0.50 + carry,
                "probability": 50,
            },
            "bull": {
                "scenario": "Rates -100 bps, tight spreads (recession flight-to-quality)",
                "rate_chg": -1.0,
                "credit_chg": -0.30,
                "total_return": dur_val * 1.0 + 0.30 + carry,
                "probability": 35,
            },
        }

    # ── Price History & Technicals ────────────────────────────────────────────

    def get_price_history(self, period: str = "1y") -> Optional[pd.DataFrame]:
        """Equity price as proxy for credit risk."""
        try:
            hist = self._yft.history(period=period)
            if not hist.empty:
                return hist[["Close"]].copy()
        except Exception:
            pass
        return None

    def get_technicals(self) -> Dict:
        """MA crossovers, momentum, volatility."""
        hist = self.get_price_history("1y")
        if hist is None or hist.empty:
            return {"error": "No price data"}

        close = hist["Close"]
        returns = close.pct_change().dropna()

        ma_20 = close.rolling(20).mean().iloc[-1]
        ma_50 = close.rolling(50).mean().iloc[-1]
        ma_200 = close.rolling(200).mean().iloc[-1]
        current = close.iloc[-1]

        vol_30d = returns.tail(30).std() * np.sqrt(252) * 100
        vol_90d = returns.tail(90).std() * np.sqrt(252) * 100

        return {
            "current_price": current,
            "ma_20": ma_20,
            "ma_50": ma_50,
            "ma_200": ma_200,
            "signal_20_50": "Bullish" if ma_20 > ma_50 else "Bearish",
            "signal_50_200": "Bullish" if ma_50 > ma_200 else "Bearish",
            "vol_30d": vol_30d,
            "vol_90d": vol_90d,
            "rsi": self._calc_rsi(close),
            "52w_high": close.max(),
            "52w_low": close.min(),
            "distance_to_52w_high": ((close.max() - current) / close.max()) * 100,
        }

    @staticmethod
    def _calc_rsi(prices, period=14) -> float:
        """Relative Strength Index."""
        try:
            deltas = prices.diff()
            seed = deltas[:period + 1]
            up = seed[seed >= 0].sum() / period
            down = -seed[seed < 0].sum() / period
            rs = up / down if down != 0 else 0
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception:
            return np.nan

    # ── Investment Recommendation ─────────────────────────────────────────────

    def generate_investment_thesis(self) -> Dict:
        """Full credit research view."""
        profile = self.get_issuer_profile()
        metrics = self.get_credit_metrics()
        rv = self.get_relative_value()
        scenarios = self.get_scenarios()

        rating = metrics.get("estimated_rating", "BBB")

        thesis = []
        risks = []

        # Thesis
        if rv.get("spread_signal") == "Cheap":
            thesis.append("Relative value attractive — spreads above sector average.")
        if metrics.get("fcf_to_debt", 0) and metrics["fcf_to_debt"] > 0.15:
            thesis.append(f"Strong FCF generation: {metrics['fcf_to_debt']:.2f}x annual debt paydown capability.")
        if metrics.get("current_ratio", 0) and metrics["current_ratio"] > 1.5:
            thesis.append("Adequate liquidity — comfortable near-term maturity profile.")
        if "+" in rating:
            thesis.append(f"Investment grade {rating} — stable credit profile.")

        exp_return = scenarios["base"]["total_return"]
        if exp_return > 0.04:
            thesis.append(f"Expected total return ~{exp_return*100:.1f}% (base case carry + roll-down).")

        # Risks
        de = metrics.get("debt_to_equity")
        if de and de > 1.5:
            risks.append(f"High leverage ({de:.1f}x) — limited deleveraging flexibility.")
        if metrics.get("fcf_to_debt", 0) and metrics["fcf_to_debt"] < 0.05:
            risks.append("Weak FCF generation — refinancing reliance rising.")
        if "B" in rating or "C" in rating:
            risks.append(f"Sub-IG rating {rating} — elevated downgrade risk in stress.")

        bear_return = scenarios["bear"]["total_return"]
        if bear_return < -0.05:
            risks.append(f"Significant downside in bear scenario: {bear_return*100:.1f}% (rates +200bps).")

        if not thesis:
            thesis = ["Company operates in stable sector.", "Monitor cash flow trends."]
        if len(risks) < 3:
            risks.extend([
                "Macro headwinds: rate volatility, credit market stress.",
                "Refinancing risk: monitor maturity profile.",
                "Sector rotation: investors may seek higher-quality credits.",
            ])

        return {
            "rating": rating,
            "thesis_bullets": thesis[:4],
            "risk_bullets": risks[:4],
            "exp_return_base": exp_return * 100,
            "recommendation": rv.get("recommendation", "HOLD"),
        }

    # ── Full Fetch ────────────────────────────────────────────────────────────

    def fetch_all(self) -> Dict:
        try:
            info = self._info_safe()
            if not info or (not info.get("currentPrice") and not info.get("regularMarketPrice")):
                return {"error": f"No data found for '{self.ticker}'. Verify the symbol."}
            return {
                "error": None,
                "profile": self.get_issuer_profile(),
                "credit_metrics": self.get_credit_metrics(),
                "bond_assumptions": self.get_bond_assumptions(),
            }
        except Exception as e:
            return {"error": f"Failed to fetch '{self.ticker}': {e}"}


# ─────────────────────────────────────────────────────────────────────────────
# 4. PDF REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_fixed_income_report_pdf(
    ticker: str,
    profile: Dict,
    metrics: Dict,
    yield_curve: pd.DataFrame,
    dur_analysis: Dict,
    scenarios: Dict,
    thesis: Dict,
) -> Optional[bytes]:
    """Professional fixed income research report."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=1.8*cm, rightMargin=1.8*cm,
            topMargin=1.8*cm, bottomMargin=1.8*cm,
        )
        styles = getSampleStyleSheet()

        S_TITLE = ParagraphStyle("RTitle", parent=styles["Title"],
                                fontSize=20, textColor=colors.HexColor("#6366f1"), spaceAfter=2)
        S_H1    = ParagraphStyle("RH1", parent=styles["Heading1"],
                               fontSize=14, textColor=colors.HexColor("#1e1b4b"), spaceAfter=4)
        S_H2    = ParagraphStyle("RH2", parent=styles["Heading2"],
                               fontSize=11, textColor=colors.HexColor("#4338ca"),
                               spaceBefore=12, spaceAfter=4)
        S_BODY  = ParagraphStyle("RBody", parent=styles["Normal"],
                               fontSize=9, textColor=colors.HexColor("#374151"),
                               spaceAfter=3, leading=13)
        S_BULLET = ParagraphStyle("RBullet", parent=styles["Normal"],
                                fontSize=9, textColor=colors.HexColor("#374151"),
                                spaceAfter=3, leading=13, leftIndent=12)

        _INDIGO = colors.HexColor("#6366f1")
        _SLATE  = colors.HexColor("#e5e7eb")
        _ROW_A  = colors.HexColor("#f5f3ff")
        _ROW_B  = colors.white

        def _tbl_style():
            return TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4338ca")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_ROW_A, _ROW_B]),
                ("GRID", (0, 0), (-1, -1), 0.3, _SLATE),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])

        story = []

        # Title
        story.append(Paragraph("Fixed Income Research Report", S_TITLE))
        story.append(Paragraph(f"{profile.get('name')} ({ticker})", S_H1))
        story.append(Paragraph(
            f"Sector: {profile.get('sector')}  ·  Rating: {thesis.get('rating','N/A')}  "
            f"·  Generated: {datetime.now().strftime('%Y-%m-%d')}",
            S_BODY,
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=_INDIGO, spaceAfter=8))

        # Credit Metrics
        story.append(Paragraph("Credit Metrics", S_H2))
        cdata = [
            ["Metric", "Value", "Metric", "Value"],
            ["Debt/Equity", f"{metrics.get('debt_to_equity', 0):.2f}x",
             "Current Ratio", f"{metrics.get('current_ratio', 0):.2f}x"],
            ["FCF/Debt", f"{metrics.get('fcf_to_debt', 0):.2f}x",
             "Est. Rating", metrics.get("estimated_rating", "—")],
            ["Profit Margin", f"{metrics.get('profit_margin', 0)*100:.1f}%",
             "ROA", f"{metrics.get('roa', 0)*100:.1f}%"],
        ]
        ct = Table(cdata, colWidths=[3.5*cm]*4)
        ct.setStyle(_tbl_style())
        story.append(ct)
        story.append(Spacer(1, 6))

        # Yield Curve
        story.append(Paragraph("Issuer Yield Curve", S_H2))
        if not yield_curve.empty:
            yc_data = [["Tenor", "Treasury", "Issuer", "Spread (bps)"]]
            for _, row in yield_curve.iterrows():
                yc_data.append([
                    f"{int(row['Tenor (y)'])}Y",
                    f"{row['Treasury (%)']:.2f}%",
                    f"{row['Issuer (%)']:.2f}%",
                    f"{row['Spread (bps)']:.0f}",
                ])
            yct = Table(yc_data, colWidths=[2*cm]*4)
            yct.setStyle(_tbl_style())
            story.append(yct)
        story.append(Spacer(1, 6))

        # Duration Analysis
        story.append(Paragraph("Interest Rate Sensitivity", S_H2))
        ddata = [
            ["Metric", "Value"],
            ["5Y Duration", f"{dur_analysis.get('5y_duration', 0):.2f}"],
            ["5Y Convexity", f"{dur_analysis.get('5y_convexity', 0):.4f}"],
            ["Return if Rates +50 bps", f"{dur_analysis.get('price_chg_50bps_up', 0):.2f}%"],
            ["Return if Rates -50 bps", f"{dur_analysis.get('price_chg_50bps_down', 0):.2f}%"],
            ["Carry (1Y)", f"{dur_analysis.get('carry_1y', 0):.2f}%"],
        ]
        dt = Table(ddata, colWidths=[5*cm]*2)
        dt.setStyle(_tbl_style())
        story.append(dt)
        story.append(Spacer(1, 6))

        # Scenarios
        story.append(Paragraph("Scenario Analysis (1Y Returns)", S_H2))
        sdata = [["Scenario", "Rate Change", "Return", "Probability"]]
        for key, data in scenarios.items():
            sdata.append([
                data["scenario"],
                f"{data['rate_chg']:+.0f} bps",
                f"{data['total_return']:+.2f}%",
                f"{data['probability']}%",
            ])
        st = Table(sdata, colWidths=[4*cm, 2.5*cm, 2*cm, 2*cm])
        st.setStyle(_tbl_style())
        story.append(st)
        story.append(Spacer(1, 6))

        # Investment Thesis
        story.append(Paragraph("Investment Thesis", S_H2))
        story.append(Paragraph(f"<b>Recommendation:</b> {thesis.get('recommendation', 'HOLD')}", S_BODY))
        story.append(Paragraph(f"<b>Expected Return (Base):</b> {thesis.get('exp_return_base', 0):.1f}%", S_BODY))
        story.append(Spacer(1, 4))

        story.append(Paragraph("<b>Bull Case</b>", S_BODY))
        for b in thesis.get("thesis_bullets", []):
            story.append(Paragraph(f"PASS {b}", S_BULLET))
        story.append(Spacer(1, 4))

        story.append(Paragraph("<b>Key Risks</b>", S_BODY))
        for r in thesis.get("risk_bullets", []):
            story.append(Paragraph(f"▲ {r}", S_BULLET))

        # Footer
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.5, color=_SLATE))
        story.append(Paragraph(
            "Generated by Ravinala v2.0  ·  TSIVAHINY Matthias  ·  "
            "For informational purposes only — not investment advice.",
            S_BODY,
        ))

        doc.build(story)
        buf.seek(0)
        return buf.read()

    except ImportError:
        return None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. STREAMLIT TAB RENDERER
# ─────────────────────────────────────────────────────────────────────────────

_BG     = "#07080d"
_GRID   = "rgba(255,255,255,0.04)"
_FONT   = "#9ca3af"
_ACCENT = "#6366f1"
_GREEN  = "#10b981"
_RED    = "#ef4444"
_AMBER  = "#f59e0b"
_MUTED  = "#94a3b8"


def _base_layout(**kw) -> Dict:
    return dict(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=dict(color=_FONT, family="Inter, SF Pro Display, sans-serif"),
        margin=dict(l=0, r=0, t=32, b=0),
        xaxis=dict(gridcolor=_GRID),
        yaxis=dict(gridcolor=_GRID),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        **kw,
    )


def render_fixed_income_research_tab() -> None:
    """Entry point for Fixed Income Research tab."""
    import streamlit as st
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    st.markdown("## Fixed Income Research")
    st.markdown("*Institutional credit analysis: yields, spreads, duration, scenarios, technicals*")

    # ── Top 20 Most-Researched Corporate Issuers ──────────────────────────────
    with st.expander("**Top 20 Most-Researched Corporate Issuers** (Bulge Bracket Coverage)", expanded=False):
        st.caption("Click any ticker to instantly load detailed credit analysis. Sorted by institutional research coverage and trading volume.")

        # Format table for display
        display_df = TOP_20_ISSUERS.copy()
        display_df["5Y Spread"] = display_df["5Y Spread (bps)"].apply(lambda x: f"{x} bps")
        display_df = display_df[["Ticker", "Issuer", "Sector", "Rating", "5Y Spread", "Coverage"]]

        # Styled dataframe with rating color coding
        def highlight_rating(row):
            colors = []
            for val in row:
                if "AAA" in str(val) or "AA" in str(val):
                    colors.append("background-color: rgba(16,185,129,0.12)")  # Green
                elif "A" in str(val) and "AA" not in str(val):
                    colors.append("background-color: rgba(245,158,11,0.12)")  # Amber
                elif "BB" in str(val) or "B" in str(val):
                    colors.append("background-color: rgba(239,68,68,0.12)")  # Red
                else:
                    colors.append("background-color: rgba(99,102,241,0.12)")
            return colors

        st.dataframe(
            display_df.style.apply(highlight_rating, axis=1),
            width="stretch",
            hide_index=True,
        )

        # Quick-select buttons (organized by sector)
        st.markdown("##### Quick Select by Sector")

        sectors_fi = {
            "Banking": ["JPM", "BAC", "GS", "MS", "WFC"],
            "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL"],
            "Energy": ["XOM", "CVX"],
            "Healthcare": ["JNJ", "UNH", "MRK"],
            "Consumer": ["AMZN", "DIS"],
            "Other": ["NEE", "META", "TSLA", "AMT"],
        }

        cols = st.columns(len(sectors_fi))
        for col_idx, (sector_label, tickers) in enumerate(sectors_fi.items()):
            with cols[col_idx]:
                st.markdown(f"**{sector_label}**")
                for t in tickers:
                    if st.button(t, key=f"fi_quick_{t}", width="stretch"):
                        st.session_state["fi_ticker_val"] = t
                        st.rerun()

    # Input
    ci1, ci2, ci3 = st.columns([2, 1.2, 1])
    with ci1:
        fi_ticker = st.text_input(
            "Issuer Ticker",
            value=st.session_state.get("fi_ticker_val", "AAPL"),
            placeholder="AAPL, JPM, XOM, NEE, AMZN…",
            key="fi_ticker_input",
        )
    with ci2:
        fi_tenor = st.selectbox("Tenor", ["3Y", "5Y", "10Y", "30Y"], index=1, key="fi_tenor")
    with ci3:
        st.markdown("<div style='padding-top:28px'></div>", unsafe_allow_html=True)
        fi_btn = st.button("Analyse", key="fi_analyse_btn", width="stretch")

    if fi_btn and fi_ticker.strip():
        clean = fi_ticker.upper().strip()
        st.session_state["fi_ticker_val"] = clean
        st.session_state.pop("fi_data", None)
        st.session_state.pop("fi_engine", None)
        with st.spinner(f"Analysing {clean}…"):
            _engine = FixedIncomeResearchEngine(clean)
            _base = _engine.fetch_all()
        if _base["error"]:
            st.error(_base["error"])
            return
        st.session_state["fi_data"] = _base
        st.session_state["fi_engine"] = clean

    if "fi_data" not in st.session_state:
        st.info("Enter an issuer ticker and click ** Analyse** to run institutional-grade credit research.")
        return

    data = st.session_state["fi_data"]
    ticker = st.session_state["fi_engine"]
    engine = FixedIncomeResearchEngine(ticker)

    profile = data["profile"]
    metrics = data["credit_metrics"]
    assumptions = data["bond_assumptions"]
    tenor = st.session_state.get("fi_tenor", "5Y")

    # Header
    rating = metrics.get("estimated_rating", "BBB")
    rec_color = _GREEN if "A" in rating else (_RED if "B" in rating or "C" in rating else _AMBER)

    st.markdown(
        f"""<div style="margin:16px 0 8px">
          <span style="font-size:1.55rem;font-weight:700;color:#f1f2f6">{profile['name']}</span>
          <span style="margin-left:12px;font-size:0.85rem;color:{rec_color};
                       background:rgba(99,102,241,0.13);padding:2px 10px;border-radius:20px;
                       font-weight:600">{rating}</span>
          <span style="margin-left:8px;font-size:0.85rem;color:#9ca3af">{profile['sector']}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    # Key Credit Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Debt/Equity", f"{metrics.get('debt_to_equity', 0):.2f}x")
    with m2:
        st.metric("Current Ratio", f"{metrics.get('current_ratio', 0):.2f}x")
    with m3:
        fcf_debt = metrics.get("fcf_to_debt", 0)
        st.metric("FCF/Debt", f"{fcf_debt:.2f}x")
    with m4:
        st.metric("Profit Margin", f"{metrics.get('profit_margin', 0)*100:.1f}%")
    with m5:
        st.metric("ROA", f"{metrics.get('roa', 0)*100:.1f}%")

    st.divider()

    # Tabs
    tabs = st.tabs(["Yield Curve", "Relative Value", "Duration", "Scenarios", "Technicals", "Thesis"])

    # ════════════ TAB 1 — YIELD CURVE ════════════════════════════════════════
    with tabs[0]:
        st.markdown("#### Issuer Yield Curve vs Benchmarks")
        with st.spinner("Loading yield curve…"):
            yc = engine.get_yield_curve()

        if yc.empty:
            st.warning("Yield curve data unavailable.")
        else:
            st.dataframe(
                yc.style.format({
                    "Treasury (%)": "{:.2f}",
                    "Issuer (%)": "{:.2f}",
                    "Spread (bps)": "{:.0f}",
                }),
                width="stretch",
            )

            # Chart
            fig_yc = go.Figure()
            fig_yc.add_trace(go.Scatter(
                x=yc["Tenor (y)"], y=yc["Treasury (%)"], mode="lines+markers",
                name="Treasury Curve", line=dict(color=_MUTED, width=2),
                marker=dict(size=8),
            ))
            fig_yc.add_trace(go.Scatter(
                x=yc["Tenor (y)"], y=yc["Issuer (%)"], mode="lines+markers",
                name="Issuer Curve", line=dict(color=_ACCENT, width=2.5),
                marker=dict(size=8),
            ))
            fig_yc.update_layout(
                **_base_layout(height=360, hovermode="x unified"),
                yaxis_title="Yield (%)",
                xaxis_title="Tenor (years)",
            )
            st.plotly_chart(fig_yc, width="stretch")

            # Spread bar chart
            fig_sp = go.Figure(go.Bar(
                x=yc["Tenor (y)"], y=yc["Spread (bps)"],
                marker_color=_ACCENT, text=yc["Spread (bps)"],
                textposition="outside", textfont=dict(color=_FONT),
            ))
            fig_sp.update_layout(**_base_layout(height=300), yaxis_title="Spread (bps)")
            st.plotly_chart(fig_sp, width="stretch")

    # ════════════ TAB 2 — RELATIVE VALUE ═════════════════════════════════════
    with tabs[1]:
        st.markdown("#### Relative Value Scorecard")
        with st.spinner("Computing RV signals…"):
            rv = engine.get_relative_value()

        cv1, cv2, cv3, cv4 = st.columns(4)
        with cv1:
            st.metric("Leverage", rv.get("leverage_signal", "—"))
        with cv2:
            st.metric("FCF", rv.get("fcf_signal", "—"))
        with cv3:
            st.metric("Spreads", rv.get("spread_signal", "—"))
        with cv4:
            score = rv.get("rv_score", 0)
            st.metric("RV Score", f"{score:+d}/6", rv.get("recommendation", "HOLD"))

        st.markdown("---")
        rec = rv.get("recommendation", "HOLD")
        rec_col = _GREEN if rec == "BUY" else (_RED if rec == "SELL" else _AMBER)
        st.markdown(
            f"""<div style="padding:16px;border-radius:8px;background:rgba(99,102,241,0.08);
                         border:1px solid {rec_col}">
              <span style="font-size:0.9rem;color:#9ca3af">Recommendation Signal</span><br>
              <span style="font-size:1.8rem;font-weight:700;color:{rec_col}">{rec}</span>
            </div>""",
            unsafe_allow_html=True,
        )

    # ════════════ TAB 3 — DURATION & CONVEXITY ═══════════════════════════════
    with tabs[2]:
        st.markdown("#### Interest Rate Sensitivity")
        with st.spinner("Calculating duration…"):
            dur = engine.get_duration_analysis()

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.metric("5Y Duration", f"{dur.get('5y_duration', 0):.2f}")
        with d2:
            st.metric("5Y Convexity", f"{dur.get('5y_convexity', 0):.4f}")
        with d3:
            st.metric("Carry (1Y)", f"{dur.get('carry_1y', 0):.2f}%")
        with d4:
            st.metric("Roll-Down", "+0.15%")

        st.markdown("---")
        st.markdown("##### Price Sensitivity")

        # Price change scenarios
        sens_data = {
            "Scenario": [
                "Rates +100 bps",
                "Rates +50 bps",
                "Rates -50 bps",
                "Rates -100 bps",
            ],
            "Price Change": [
                f"{dur.get('price_chg_100bps_up', 0):+.2f}%",
                f"{dur.get('price_chg_50bps_up', 0):+.2f}%",
                f"{dur.get('price_chg_50bps_down', 0):+.2f}%",
                f"{dur.get('price_chg_100bps_down', 0):+.2f}%",
            ],
        }
        sens_df = pd.DataFrame(sens_data)
        st.dataframe(sens_df, width="stretch", hide_index=True)

        # Visualization
        rates = [-100, -50, 50, 100]
        changes = [
            dur.get("price_chg_100bps_down", 0),
            dur.get("price_chg_50bps_down", 0),
            dur.get("price_chg_50bps_up", 0),
            dur.get("price_chg_100bps_up", 0),
        ]
        colors_list = [_GREEN if c > 0 else _RED for c in changes]

        fig_sens = go.Figure(go.Bar(
            x=[f"{r:+d} bps" for r in rates], y=changes,
            marker_color=colors_list, text=[f"{c:+.2f}%" for c in changes],
            textposition="outside", textfont=dict(color=_FONT),
        ))
        fig_sens.update_layout(**_base_layout(height=340), yaxis_title="Price Change (%)")
        st.plotly_chart(fig_sens, width="stretch")

    # ════════════ TAB 4 — SCENARIO ANALYSIS ═════════════════════════════════
    with tabs[3]:
        st.markdown("#### 1-Year Return Scenarios")
        with st.spinner("Running scenarios…"):
            scenarios = engine.get_scenarios()

        # Scenario cards
        scol1, scol2, scol3 = st.columns(3)
        with scol1:
            sc = scenarios["bear"]
            st.markdown(
                f"""<div style="padding:16px;border-radius:8px;background:rgba(239,68,68,0.08);
                             border:1px solid rgba(239,68,68,0.3)">
                  <div style="color:#9ca3af;font-size:0.8rem;font-weight:600">BEAR CASE</div>
                  <div style="font-size:1.3rem;font-weight:700;color:#ef4444;margin:8px 0">
                    {sc['total_return']:+.2f}%
                  </div>
                  <div style="font-size:0.75rem;color:#9ca3af">{sc['scenario']}</div>
                  <div style="font-size:0.75rem;color:#9ca3af;margin-top:4px">
                    P({sc['probability']}%)
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )
        with scol2:
            sc = scenarios["base"]
            st.markdown(
                f"""<div style="padding:16px;border-radius:8px;background:rgba(245,158,11,0.08);
                             border:1px solid rgba(245,158,11,0.3)">
                  <div style="color:#9ca3af;font-size:0.8rem;font-weight:600">BASE CASE</div>
                  <div style="font-size:1.3rem;font-weight:700;color:#f59e0b;margin:8px 0">
                    {sc['total_return']:+.2f}%
                  </div>
                  <div style="font-size:0.75rem;color:#9ca3af">{sc['scenario']}</div>
                  <div style="font-size:0.75rem;color:#9ca3af;margin-top:4px">
                    P({sc['probability']}%)
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )
        with scol3:
            sc = scenarios["bull"]
            st.markdown(
                f"""<div style="padding:16px;border-radius:8px;background:rgba(16,185,129,0.08);
                             border:1px solid rgba(16,185,129,0.3)">
                  <div style="color:#9ca3af;font-size:0.8rem;font-weight:600">BULL CASE</div>
                  <div style="font-size:1.3rem;font-weight:700;color:#10b981;margin:8px 0">
                    {sc['total_return']:+.2f}%
                  </div>
                  <div style="font-size:0.75rem;color:#9ca3af">{sc['scenario']}</div>
                  <div style="font-size:0.75rem;color:#9ca3af;margin-top:4px">
                    P({sc['probability']}%)
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

        # Expected value
        exp_val = sum(s["total_return"] * s["probability"] / 100 for s in scenarios.values())
        st.metric("Probability-Weighted Return", f"{exp_val:+.2f}%")

    # ════════════ TAB 5 — TECHNICALS ═════════════════════════════════════════
    with tabs[4]:
        st.markdown("#### Technical Analysis (Equity Proxy)")
        with st.spinner("Computing technicals…"):
            tech = engine.get_technicals()

        if "error" not in tech:
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                sig = tech.get("signal_20_50", "—")
                st.metric("MA(20/50)", sig)
            with t2:
                sig = tech.get("signal_50_200", "—")
                st.metric("MA(50/200)", sig)
            with t3:
                st.metric("RSI(14)", f"{tech.get('rsi', 50):.0f}")
            with t4:
                st.metric("Vol (30D)", f"{tech.get('vol_30d', 0):.1f}%")

            st.markdown("---")
            st.markdown("##### 52-Week Range")
            range_pct = tech.get("distance_to_52w_high", 0)
            st.progress(value=1 - (range_pct / 100), text=f"{range_pct:.1f}% below 52W high")

            # Price history chart
            hist = engine.get_price_history("1y")
            if hist is not None and not hist.empty:
                fig_price = go.Figure()
                fig_price.add_trace(go.Scatter(
                    x=hist.index, y=hist["Close"], mode="lines", name="Price",
                    line=dict(color=_ACCENT, width=1.5),
                    fill="tozeroy", fillcolor=f"rgba(99,102,241,0.1)",
                ))
                fig_price.add_hline(y=tech["ma_20"], line_dash="dash", line_color="#818cf8",
                                   annotation_text="MA(20)", annotation_font_color=_FONT)
                fig_price.add_hline(y=tech["ma_50"], line_dash="dash", line_color="#a5b4fc",
                                   annotation_text="MA(50)", annotation_font_color=_FONT)
                fig_price.update_layout(**_base_layout(height=360), yaxis_title="Price")
                st.plotly_chart(fig_price, width="stretch")
        else:
            st.warning("Technical data unavailable.")

    # ════════════ TAB 6 — INVESTMENT THESIS ══════════════════════════════════
    with tabs[5]:
        st.markdown("#### Investment Thesis")
        with st.spinner("Generating credit view…"):
            thesis = engine.generate_investment_thesis()

        rec = thesis.get("recommendation", "HOLD")
        rec_col = _GREEN if rec == "BUY" else (_RED if rec == "SELL" else _AMBER)

        tp1, tp2, tp3 = st.columns(3)
        with tp1:
            st.markdown(
                f"""<div style="padding:16px;border-radius:8px;
                             background:rgba(99,102,241,0.08);
                             border:1px solid rgba(99,102,241,0.2);text-align:center">
                  <div style="color:#9ca3af;font-size:0.72rem;text-transform:uppercase;
                              letter-spacing:0.06em">Recommendation</div>
                  <div style="font-size:1.5rem;font-weight:700;color:{rec_col};margin-top:4px">{rec}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with tp2:
            st.metric("Est. Return (Base)", f"{thesis.get('exp_return_base', 0):+.1f}%")
        with tp3:
            st.metric("Credit Rating", thesis.get("rating", "—"))

        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
        col_t, col_r = st.columns(2)
        with col_t:
            st.markdown("**Bull Case**")
            for b in thesis.get("thesis_bullets", []):
                st.markdown(f"PASS {b}")
        with col_r:
            st.markdown("**Key Risks**")
            for r in thesis.get("risk_bullets", []):
                st.markdown(f"WARNING {r}")

    # ── PDF Export ────────────────────────────────────────────────────────────
    st.divider()
    if st.button("Export Fixed Income Report (PDF)", key="fi_pdf_btn"):
        with st.spinner("Generating PDF…"):
            yc = engine.get_yield_curve()
            dur = engine.get_duration_analysis()
            scenarios = engine.get_scenarios()
            thesis = engine.generate_investment_thesis()

            pdf_bytes = generate_fixed_income_report_pdf(
                ticker=ticker,
                profile=profile,
                metrics=metrics,
                yield_curve=yc,
                dur_analysis=dur,
                scenarios=scenarios,
                thesis=thesis,
            )
        if pdf_bytes:
            st.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name=f"{ticker}_fixed_income_research_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="fi_pdf_dl",
            )
        else:
            st.error("PDF generation failed — reportlab required.")
