"""
fundamentals.py — Complete fundamental analysis: ratios, DCF, earnings, peers.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _safe(d: Dict, key: str, default=None):
    val = d.get(key, default)
    return default if val is None or (isinstance(val, float) and np.isnan(val)) else val


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def _fmt(value: Optional[float], decimals: int = 2, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}{suffix}"


def _millions(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1e12:
        return f"${value / 1e12:.2f}T"
    if abs(value) >= 1e9:
        return f"${value / 1e9:.2f}B"
    if abs(value) >= 1e6:
        return f"${value / 1e6:.2f}M"
    return f"${value:.0f}"


class FundamentalAnalyzer:
    """Full fundamental analysis for a single equity ticker.

    Uses yFinance as the data source.  All public methods return plain Python
    dicts or DataFrames so they can be used outside Streamlit.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # PROFILE
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=600)
    def get_company_profile(ticker: str) -> Dict:
        """Fetch company profile.

        Args:
            ticker: Ticker symbol (e.g., 'AAPL').

        Returns:
            Dict with profile fields or empty dict on failure.
        """
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            return {}

        return {
            "name":        _safe(info, "longName", ticker),
            "description": _safe(info, "longBusinessSummary", ""),
            "sector":      _safe(info, "sector", "N/A"),
            "industry":    _safe(info, "industry", "N/A"),
            "country":     _safe(info, "country", "N/A"),
            "exchange":    _safe(info, "exchange", "N/A"),
            "currency":    _safe(info, "currency", "USD"),
            "website":     _safe(info, "website", ""),
            "employees":   _safe(info, "fullTimeEmployees"),
            "market_cap":  _safe(info, "marketCap"),
            "shares_out":  _safe(info, "sharesOutstanding"),
            "float_shares": _safe(info, "floatShares"),
            "ipo_date":    _safe(info, "ipoExpectedDate"),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # FINANCIAL STATEMENTS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=600)
    def get_financial_statements(ticker: str) -> Dict[str, pd.DataFrame]:
        """Fetch the three financial statements (annual, last 4 years).

        Returns:
            Dict with keys 'income', 'balance', 'cashflow' → DataFrames.
        """
        try:
            t = yf.Ticker(ticker)
            income = t.financials
            balance = t.balance_sheet
            cashflow = t.cashflow
        except Exception:
            return {"income": pd.DataFrame(), "balance": pd.DataFrame(), "cashflow": pd.DataFrame()}

        return {
            "income": income if income is not None else pd.DataFrame(),
            "balance": balance if balance is not None else pd.DataFrame(),
            "cashflow": cashflow if cashflow is not None else pd.DataFrame(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # VALUATION RATIOS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=300)
    def get_valuation_ratios(ticker: str) -> Dict:
        """Fetch key valuation multiples.

        Returns:
            Dict with ratio names → values (float or None).
        """
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            return {}

        return {
            "pe_trailing":      _safe(info, "trailingPE"),
            "pe_forward":       _safe(info, "forwardPE"),
            "peg_ratio":        _safe(info, "pegRatio"),
            "ps_ratio":         _safe(info, "priceToSalesTrailing12Months"),
            "pb_ratio":         _safe(info, "priceToBook"),
            "ev_ebitda":        _safe(info, "enterpriseToEbitda"),
            "ev_revenue":       _safe(info, "enterpriseToRevenue"),
            "enterprise_value": _safe(info, "enterpriseValue"),
            "market_cap":       _safe(info, "marketCap"),
            "dividend_yield":   _safe(info, "dividendYield"),
            "payout_ratio":     _safe(info, "payoutRatio"),
            "fcf_per_share":    _safe(info, "freeCashflow"),
            "book_value":       _safe(info, "bookValue"),
            "price":            _safe(info, "currentPrice") or _safe(info, "regularMarketPrice"),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PROFITABILITY
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=300)
    def get_profitability_metrics(ticker: str) -> Dict:
        """Fetch profitability and growth metrics.

        Returns:
            Dict with metric names → values.
        """
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            return {}

        return {
            "gross_margin":      _safe(info, "grossMargins"),
            "operating_margin":  _safe(info, "operatingMargins"),
            "net_margin":        _safe(info, "profitMargins"),
            "ebitda_margin":     _safe(info, "ebitdaMargins"),
            "roe":               _safe(info, "returnOnEquity"),
            "roa":               _safe(info, "returnOnAssets"),
            "revenue":           _safe(info, "totalRevenue"),
            "revenue_growth":    _safe(info, "revenueGrowth"),
            "earnings_growth":   _safe(info, "earningsGrowth"),
            "eps_ttm":           _safe(info, "trailingEps"),
            "eps_forward":       _safe(info, "forwardEps"),
            "ebitda":            _safe(info, "ebitda"),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # FINANCIAL HEALTH
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=300)
    def get_financial_health(ticker: str) -> Dict:
        """Compute financial health metrics including Altman Z-Score and Piotroski F-Score.

        Returns:
            Dict with health metrics.
        """
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            bs = t.balance_sheet
            fin = t.financials
            cf = t.cashflow
        except Exception:
            return {}

        result: Dict = {
            "debt_equity":        _safe(info, "debtToEquity"),
            "current_ratio":      _safe(info, "currentRatio"),
            "quick_ratio":        _safe(info, "quickRatio"),
            "total_debt":         _safe(info, "totalDebt"),
            "cash":               _safe(info, "totalCash"),
            "free_cashflow":      _safe(info, "freeCashflow"),
            "interest_coverage":  None,
            "net_debt_ebitda":    None,
            "altman_z":           None,
            "piotroski_f":        None,
        }

        # Net Debt / EBITDA
        total_debt = _safe(info, "totalDebt", 0) or 0
        cash = _safe(info, "totalCash", 0) or 0
        ebitda = _safe(info, "ebitda", 0) or 0
        if ebitda and ebitda != 0:
            result["net_debt_ebitda"] = (total_debt - cash) / ebitda

        # Interest Coverage (EBIT / Interest Expense)
        try:
            if fin is not None and not fin.empty:
                ebit_row = [r for r in fin.index if "EBIT" in str(r).upper() or "Operating Income" in str(r)]
                int_row  = [r for r in fin.index if "Interest Expense" in str(r)]
                if ebit_row and int_row:
                    ebit_val = float(fin.loc[ebit_row[0]].iloc[0])
                    int_val  = abs(float(fin.loc[int_row[0]].iloc[0]))
                    if int_val > 0:
                        result["interest_coverage"] = ebit_val / int_val
        except Exception:
            pass

        # Simplified Altman Z-Score
        try:
            if bs is not None and not bs.empty and fin is not None and not fin.empty:
                mkt_cap = _safe(info, "marketCap", 0) or 0
                total_assets_row = [r for r in bs.index if "Total Assets" in str(r)]
                total_liab_row   = [r for r in bs.index if "Total Liab" in str(r) or "Total Liabilities" in str(r)]
                re_row           = [r for r in bs.index if "Retained Earnings" in str(r)]
                ca_row           = [r for r in bs.index if "Current Assets" in str(r) and "Total" not in str(r)]
                cl_row           = [r for r in bs.index if "Current Liabilities" in str(r)]
                rev_row          = [r for r in fin.index if "Total Revenue" in str(r)]
                ebit_r           = [r for r in fin.index if "EBIT" in str(r).upper() or "Operating Income" in str(r)]

                ta = float(bs.loc[total_assets_row[0]].iloc[0]) if total_assets_row else 0
                tl = float(bs.loc[total_liab_row[0]].iloc[0]) if total_liab_row else 0
                re = float(bs.loc[re_row[0]].iloc[0]) if re_row else 0
                ca = float(bs.loc[ca_row[0]].iloc[0]) if ca_row else 0
                cl = float(bs.loc[cl_row[0]].iloc[0]) if cl_row else 0
                rev = float(fin.loc[rev_row[0]].iloc[0]) if rev_row else 0
                ebit_v = float(fin.loc[ebit_r[0]].iloc[0]) if ebit_r else 0

                if ta > 0:
                    wc = ca - cl
                    z = (
                        1.2 * (wc / ta)
                        + 1.4 * (re / ta)
                        + 3.3 * (ebit_v / ta)
                        + 0.6 * (mkt_cap / max(tl, 1))
                        + 1.0 * (rev / ta)
                    )
                    result["altman_z"] = round(z, 2)
        except Exception:
            pass

        # Piotroski F-Score (simplified, 9 criteria)
        try:
            f_score = 0
            roa = _safe(info, "returnOnAssets", 0) or 0
            if roa > 0:
                f_score += 1      # ROA positive
            fcf = _safe(info, "freeCashflow", 0) or 0
            if fcf > 0:
                f_score += 1      # Positive FCF
            op_margin = _safe(info, "operatingMargins", 0) or 0
            if op_margin > 0:
                f_score += 1      # Positive operating margin
            de = _safe(info, "debtToEquity")
            if de is not None and de < 1:
                f_score += 1      # Low leverage
            cr = _safe(info, "currentRatio")
            if cr is not None and cr > 1:
                f_score += 1      # Adequate liquidity
            rev_growth = _safe(info, "revenueGrowth", 0) or 0
            if rev_growth > 0:
                f_score += 1      # Revenue growing
            earn_growth = _safe(info, "earningsGrowth", 0) or 0
            if earn_growth > 0:
                f_score += 1      # Earnings growing
            gross_margin = _safe(info, "grossMargins", 0) or 0
            if gross_margin > 0.3:
                f_score += 1      # Good gross margins
            if fcf > 0 and roa > 0 and fcf > roa:
                f_score += 1      # FCF > ROA (accruals)

            result["piotroski_f"] = f_score
        except Exception:
            pass

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # SIMPLE DCF
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def simple_dcf(
        ticker: str,
        growth_rate: Optional[float] = None,
        terminal_growth: float = 0.025,
        discount_rate: float = 0.10,
        projection_years: int = 5,
    ) -> Dict:
        """Discounted Cash Flow valuation.

        Algorithm:
        1. Get TTM Free Cash Flow.
        2. Project FCF for N years at growth_rate (or historical avg if None).
        3. Compute terminal value via Gordon Growth.
        4. Discount all cash flows at discount_rate.
        5. Subtract net debt, divide by shares outstanding.

        Returns:
            Dict with intrinsic_value, current_price, upside_pct,
            margin_of_safety, sensitivity_table.
        """
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            return {}

        fcf = _safe(info, "freeCashflow")
        shares = _safe(info, "sharesOutstanding")
        price = _safe(info, "currentPrice") or _safe(info, "regularMarketPrice")
        total_debt = _safe(info, "totalDebt", 0) or 0
        cash = _safe(info, "totalCash", 0) or 0
        net_debt = total_debt - cash

        if not fcf or not shares or not price or shares == 0:
            return {}

        if growth_rate is None:
            growth_rate = _safe(info, "earningsGrowth", 0.08) or 0.08
            growth_rate = min(max(growth_rate, -0.20), 0.50)

        # Project FCF
        projected_fcf = []
        cf = fcf
        for _ in range(projection_years):
            cf *= (1 + growth_rate)
            projected_fcf.append(cf)

        # Terminal value
        terminal_value = projected_fcf[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)

        # Discount all
        pv_fcfs = sum(
            v / (1 + discount_rate) ** (i + 1)
            for i, v in enumerate(projected_fcf)
        )
        pv_terminal = terminal_value / (1 + discount_rate) ** projection_years
        equity_value = pv_fcfs + pv_terminal - net_debt
        intrinsic = equity_value / shares

        upside = (intrinsic - price) / price * 100
        margin_of_safety = (1 - price / intrinsic) * 100 if intrinsic > 0 else None

        # Sensitivity table (growth × discount)
        growth_range = [growth_rate * 0.5, growth_rate * 0.75, growth_rate,
                        growth_rate * 1.25, growth_rate * 1.5]
        discount_range = [discount_rate - 0.02, discount_rate - 0.01, discount_rate,
                          discount_rate + 0.01, discount_rate + 0.02]
        growth_range = [max(-0.20, min(0.60, g)) for g in growth_range]
        discount_range = [max(0.03, min(0.25, d)) for d in discount_range]

        table_data = {}
        for g in growth_range:
            row = {}
            for d in discount_range:
                if d <= terminal_growth:
                    row[f"{d:.1%}"] = np.nan
                    continue
                cf_g = fcf
                pv = 0.0
                for yr in range(1, projection_years + 1):
                    cf_g *= (1 + g)
                    pv += cf_g / (1 + d) ** yr
                tv = cf_g * (1 + terminal_growth) / (d - terminal_growth)
                pv_tv = tv / (1 + d) ** projection_years
                eq = pv + pv_tv - net_debt
                val = eq / shares
                row[f"{d:.1%}"] = round(val, 2)
            table_data[f"{g:.1%}"] = row

        sensitivity = pd.DataFrame(table_data).T
        sensitivity.index.name = "Growth / Discount"

        return {
            "intrinsic_value":    round(intrinsic, 2),
            "current_price":      round(price, 2),
            "upside_pct":         round(upside, 1),
            "margin_of_safety":   round(margin_of_safety, 1) if margin_of_safety else None,
            "pv_fcfs":            round(pv_fcfs, 0),
            "pv_terminal":        round(pv_terminal, 0),
            "terminal_value":     round(terminal_value, 0),
            "net_debt":           round(net_debt, 0),
            "equity_value":       round(equity_value, 0),
            "growth_rate_used":   growth_rate,
            "discount_rate_used": discount_rate,
            "sensitivity_table":  sensitivity,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # EARNINGS ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=600)
    def earnings_analysis(ticker: str) -> Dict:
        """Analyze earnings history and detect patterns.

        Returns:
            Dict with history DataFrame, beat_rate, avg_surprise, next_earnings.
        """
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            eps_hist = t.earnings_history
            info = t.info or {}
        except Exception:
            return {}

        next_earnings = None
        if cal is not None:
            try:
                if isinstance(cal, dict):
                    next_earnings = cal.get("Earnings Date")
                elif hasattr(cal, "iloc"):
                    next_earnings = str(cal.iloc[0].get("Earnings Date", ""))
            except Exception:
                pass

        history_df = pd.DataFrame()
        beat_rate = None
        avg_surprise = None
        drop_after_beat = None

        if eps_hist is not None and not eps_hist.empty:
            try:
                df = eps_hist.copy()
                if "epsEstimate" in df.columns and "epsActual" in df.columns:
                    df["surprise"] = df["epsActual"] - df["epsEstimate"]
                    df["surprise_pct"] = df["surprise"] / df["epsEstimate"].abs().replace(0, np.nan) * 100
                    df["beat"] = df["surprise"] > 0
                    beat_rate = float(df["beat"].mean()) if len(df) > 0 else None
                    avg_surprise = float(df["surprise_pct"].mean()) if len(df) > 0 else None
                    history_df = df
            except Exception:
                pass

        # Reaction pattern text
        pattern_text = ""
        if beat_rate is not None and len(history_df) >= 4:
            pattern_text = (
                f"Beat earnings {beat_rate * 100:.0f}% of the last {len(history_df)} quarters "
                f"with average surprise of {avg_surprise:.1f}%."
                if avg_surprise is not None else ""
            )

        return {
            "history":       history_df,
            "beat_rate":     beat_rate,
            "avg_surprise":  avg_surprise,
            "next_earnings": next_earnings,
            "pattern_text":  pattern_text,
            "eps_ttm":       _safe(info, "trailingEps"),
            "eps_forward":   _safe(info, "forwardEps"),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PEER COMPARISON
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    @st.cache_data(ttl=600)
    def peer_comparison(ticker: str,
                         peers: Optional[List[str]] = None) -> pd.DataFrame:
        """Compare ticker vs peer group on key metrics.

        Args:
            ticker: Target ticker.
            peers: Peer tickers. If None, attempts auto-detection from same sector.

        Returns:
            DataFrame: Ticker | MktCap | P/E | EV/EBITDA | Net Margin | Rev Growth | ROE | D/E
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if peers is None:
            # Minimal auto-detection by sector via known ETF constituents
            sector_peers: Dict[str, List[str]] = {
                "Technology":    ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMZN"],
                "Financials":    ["JPM", "BAC", "WFC", "GS", "MS", "C"],
                "Healthcare":    ["JNJ", "PFE", "MRK", "ABT", "LLY", "UNH"],
                "Energy":        ["XOM", "CVX", "COP", "OXY", "SLB", "EOG"],
                "Industrials":   ["GE", "HON", "MMM", "CAT", "DE", "LMT"],
            }
            try:
                info = yf.Ticker(ticker).info or {}
                sector = _safe(info, "sector", "")
                peers = [s for s in sector_peers.get(sector, []) if s != ticker][:5]
            except Exception:
                peers = []

        all_tickers = [ticker] + (peers or [])

        def _fetch(sym: str) -> Dict:
            try:
                info = yf.Ticker(sym).info or {}
                return {
                    "Ticker":     sym,
                    "Name":       _safe(info, "shortName", sym),
                    "MktCap":     _safe(info, "marketCap"),
                    "P/E":        _safe(info, "trailingPE"),
                    "EV/EBITDA":  _safe(info, "enterpriseToEbitda"),
                    "Net Margin": _safe(info, "profitMargins"),
                    "Rev Growth": _safe(info, "revenueGrowth"),
                    "ROE":        _safe(info, "returnOnEquity"),
                    "D/E":        _safe(info, "debtToEquity"),
                    "Div Yield":  _safe(info, "dividendYield"),
                }
            except Exception:
                return {"Ticker": sym}

        rows = []
        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = {ex.submit(_fetch, s): s for s in all_tickers}
            for f in futures:
                rows.append(f.result())

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # Format percentages
        for col in ["Net Margin", "Rev Growth", "ROE", "Div Yield"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{x * 100:.1f}%" if isinstance(x, float) else "N/A")

        # Sort: target ticker first
        target_mask = df["Ticker"] == ticker
        df = pd.concat([df[target_mask], df[~target_mask]]).reset_index(drop=True)

        return df
