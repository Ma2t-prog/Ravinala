"""
options_chain.py — Options chain viewer with Greeks, IV smile, unusual activity.

Leverages Ravinala's existing Black-Scholes engine (src/engine.py) for Greeks
and IV calculation via Newton-Raphson.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from .core import DARK_THEME

_C = DARK_THEME


# ─────────────────────────────────────────────────────────────────────────────
# BLACK-SCHOLES HELPERS (standalone so no circular import)
# ─────────────────────────────────────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    from math import erfc, sqrt
    return 0.5 * erfc(-x / sqrt(2))


def _bs_price(S: float, K: float, T: float, r: float, sigma: float,
               option_type: str = "call") -> float:
    """Black-Scholes option price."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(0.0, (S - K) if option_type == "call" else (K - S))
    import math
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "call":
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def _bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
                option_type: str = "call") -> Dict[str, float]:
    """Compute Delta, Gamma, Vega, Theta for a European option."""
    if T <= 0 or sigma <= 0:
        return {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    import math
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    pdf_d1 = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)

    delta = _norm_cdf(d1) if option_type == "call" else _norm_cdf(d1) - 1
    gamma = pdf_d1 / (S * sigma * math.sqrt(T))
    vega  = S * pdf_d1 * math.sqrt(T) / 100  # per 1% change in vol
    theta = (
        -(S * pdf_d1 * sigma) / (2 * math.sqrt(T))
        - r * K * math.exp(-r * T) * (_norm_cdf(d2) if option_type == "call" else _norm_cdf(-d2))
    ) / 365  # daily theta

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "vega":  round(vega, 4),
        "theta": round(theta, 4),
    }


def _implied_vol(market_price: float, S: float, K: float, T: float, r: float,
                  option_type: str = "call", tol: float = 1e-6,
                  max_iter: int = 100) -> Optional[float]:
    """Newton-Raphson implied volatility solver."""
    if market_price <= 0 or T <= 0:
        return None
    import math
    sigma = 0.3  # initial guess
    for _ in range(max_iter):
        price = _bs_price(S, K, T, r, sigma, option_type)
        diff = price - market_price
        if abs(diff) < tol:
            return sigma

        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        vega = S * math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi) * math.sqrt(T)
        if vega < 1e-10:
            break
        sigma -= diff / vega
        sigma = max(1e-6, min(sigma, 10.0))

    return sigma if 0 < sigma < 10 else None


# ─────────────────────────────────────────────────────────────────────────────
# OPTIONS CHAIN VIEWER
# ─────────────────────────────────────────────────────────────────────────────

class OptionsChainViewer:
    """Display options chains with Greeks, IV smile, and unusual activity detection."""

    @staticmethod
    @st.cache_data(ttl=120)
    def get_chain(ticker: str,
                   expiry: Optional[str] = None) -> pd.DataFrame:
        """Fetch and enrich the options chain.

        Args:
            ticker: Ticker symbol.
            expiry: Expiration date string (YYYY-MM-DD). If None, uses nearest expiry.

        Returns:
            DataFrame with strike, type, bid, ask, last, volume, OI, IV,
            delta, gamma, theta, vega columns.
        """
        try:
            t = yf.Ticker(ticker)
            expirations = t.options
        except Exception:
            return pd.DataFrame()

        if not expirations:
            return pd.DataFrame()

        if expiry is None:
            expiry = expirations[0]
        elif expiry not in expirations:
            # Find closest
            exp_dates = pd.to_datetime(expirations)
            target = pd.Timestamp(expiry)
            closest = min(exp_dates, key=lambda d: abs(d - target))
            expiry = closest.strftime("%Y-%m-%d")

        try:
            chain = t.option_chain(expiry)
            spot = float(t.history(period="1d", auto_adjust=True)["Close"].iloc[-1])
        except Exception:
            return pd.DataFrame()

        r = 0.05  # risk-free rate

        exp_dt = pd.Timestamp(expiry)
        T = max((exp_dt - pd.Timestamp.now()).days / 365.0, 1 / 365)

        rows = []
        for opt_type, df_opts in [("call", chain.calls), ("put", chain.puts)]:
            if df_opts is None or df_opts.empty:
                continue
            for _, row in df_opts.iterrows():
                K = float(row.get("strike", 0))
                bid = float(row.get("bid", 0) or 0)
                ask = float(row.get("ask", 0) or 0)
                last = float(row.get("lastPrice", 0) or 0)
                vol = int(row.get("volume", 0) or 0)
                oi = int(row.get("openInterest", 0) or 0)
                iv_yf = float(row.get("impliedVolatility", 0) or 0)

                mid = (bid + ask) / 2 if ask > 0 else last
                iv = _implied_vol(mid, spot, K, T, r, opt_type) if mid > 0.01 else iv_yf
                if iv is None:
                    iv = iv_yf

                greeks = _bs_greeks(spot, K, T, r, iv, opt_type) if iv > 0 else {}

                rows.append({
                    "Strike":   K,
                    "Type":     opt_type.upper(),
                    "Bid":      bid,
                    "Ask":      ask,
                    "Last":     last,
                    "Volume":   vol,
                    "OI":       oi,
                    "IV":       round(iv * 100, 1) if iv else None,
                    "Delta":    greeks.get("delta"),
                    "Gamma":    greeks.get("gamma"),
                    "Theta":    greeks.get("theta"),
                    "Vega":     greeks.get("vega"),
                    "ITM":      (K < spot if opt_type == "call" else K > spot),
                    "Moneyness": round((spot - K) / K * 100, 1) if opt_type == "call" else round((K - spot) / K * 100, 1),
                })

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame(rows)
        result = result.sort_values("Strike").reset_index(drop=True)
        return result

    @staticmethod
    @st.cache_data(ttl=120)
    def get_expirations(ticker: str) -> List[str]:
        """Return available expiration dates for a ticker."""
        try:
            return list(yf.Ticker(ticker).options)
        except Exception:
            return []

    def iv_smile(self, ticker: str, expiry: Optional[str] = None) -> go.Figure:
        """Plot implied volatility smile (IV vs Strike).

        Args:
            ticker: Ticker symbol.
            expiry: Expiration date.

        Returns:
            Plotly Figure.
        """
        chain = self.get_chain(ticker, expiry)
        if chain.empty:
            return go.Figure()

        try:
            spot = float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
        except Exception:
            spot = None

        fig = go.Figure()

        for opt_type, color in [("CALL", _C["green"]), ("PUT", _C["red"])]:
            subset = chain[chain["Type"] == opt_type].dropna(subset=["IV"])
            if subset.empty:
                continue
            fig.add_trace(go.Scatter(
                x=subset["Strike"],
                y=subset["IV"],
                name=opt_type,
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=5),
                hovertemplate=f"{opt_type}<br>Strike: %{{x:.0f}}<br>IV: %{{y:.1f}}%<extra></extra>",
            ))

        if spot:
            fig.add_vline(
                x=spot,
                line=dict(color=_C["yellow"], width=1.5, dash="dash"),
                annotation_text=f"Spot: ${spot:.2f}",
                annotation_font=dict(color=_C["yellow"]),
            )

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title=f"<b>{ticker}</b> — IV Smile (expiry: {expiry or 'nearest'})",
            xaxis_title="Strike",
            yaxis_title="Implied Volatility (%)",
            xaxis=dict(gridcolor=_C["border"]),
            yaxis=dict(gridcolor=_C["border"]),
            height=450,
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        return fig

    def iv_term_structure(self, ticker: str) -> go.Figure:
        """Plot ATM implied volatility term structure across all expirations."""
        expirations = self.get_expirations(ticker)
        if not expirations:
            return go.Figure()

        try:
            spot = float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
        except Exception:
            return go.Figure()

        atm_ivs = []
        for exp in expirations[:12]:  # limit to 12 expirations for speed
            try:
                chain = self.get_chain(ticker, exp)
                if chain.empty:
                    continue
                # Find ATM strike
                calls = chain[chain["Type"] == "CALL"].dropna(subset=["IV"])
                if calls.empty:
                    continue
                atm_row = calls.iloc[(calls["Strike"] - spot).abs().argsort()[:1]]
                iv_atm = float(atm_row["IV"].iloc[0])
                dte = max((pd.Timestamp(exp) - pd.Timestamp.now()).days, 0)
                atm_ivs.append({"expiry": exp, "dte": dte, "iv_atm": iv_atm})
            except Exception:
                continue

        if not atm_ivs:
            return go.Figure()

        df_ts = pd.DataFrame(atm_ivs).sort_values("dte")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_ts["dte"],
            y=df_ts["iv_atm"],
            mode="lines+markers",
            line=dict(color=_C["blue"], width=2.5),
            marker=dict(size=8, color=_C["blue"]),
            hovertemplate="DTE: %{x}d<br>ATM IV: %{y:.1f}%<extra></extra>",
        ))
        for _, r in df_ts.iterrows():
            fig.add_annotation(
                x=r["dte"], y=r["iv_atm"],
                text=r["expiry"], showarrow=False,
                font=dict(size=8, color=_C["text_muted"]),
                yshift=12,
            )

        fig.update_layout(
            paper_bgcolor=_C["bg"],
            plot_bgcolor=_C["panel"],
            font=dict(color=_C["text"]),
            title=f"<b>{ticker}</b> — IV Term Structure (ATM)",
            xaxis_title="Days to Expiry",
            yaxis_title="Implied Volatility (%)",
            xaxis=dict(gridcolor=_C["border"]),
            yaxis=dict(gridcolor=_C["border"]),
            height=400,
        )
        return fig

    @staticmethod
    def unusual_activity(ticker: str,
                          vol_oi_threshold: float = 3.0) -> pd.DataFrame:
        """Detect unusual options activity.

        Criteria:
        - Volume / OI > threshold (new position being opened)
        - Volume > 500

        Args:
            ticker: Ticker symbol.
            vol_oi_threshold: Minimum Vol/OI ratio.

        Returns:
            DataFrame of unusual contracts sorted by Vol/OI desc.
        """
        exps = OptionsChainViewer.get_expirations(ticker)
        if not exps:
            return pd.DataFrame()

        rows = []
        for exp in exps[:3]:  # scan nearest 3 expirations
            try:
                chain = OptionsChainViewer.get_chain(ticker, exp)
                if chain.empty:
                    continue
                chain["Expiry"] = exp
                rows.append(chain)
            except Exception:
                continue

        if not rows:
            return pd.DataFrame()

        all_chain = pd.concat(rows)
        all_chain = all_chain[all_chain["OI"] > 0].copy()
        all_chain["Vol/OI"] = all_chain["Volume"] / all_chain["OI"]

        unusual = all_chain[
            (all_chain["Vol/OI"] >= vol_oi_threshold)
            & (all_chain["Volume"] >= 500)
        ].copy()

        return unusual.sort_values("Vol/OI", ascending=False).reset_index(drop=True)

    @staticmethod
    def max_pain(ticker: str, expiry: Optional[str] = None) -> Optional[float]:
        """Compute the Max Pain price for an expiration.

        Max Pain = strike price where total options pain (to option buyers) is maximized.

        Args:
            ticker: Ticker symbol.
            expiry: Expiration date.

        Returns:
            Max pain price as float or None.
        """
        chain = OptionsChainViewer.get_chain(ticker, expiry)
        if chain.empty:
            return None

        strikes = sorted(chain["Strike"].unique())
        if not strikes:
            return None

        try:
            spot = float(yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1])
        except Exception:
            return None

        calls = chain[chain["Type"] == "CALL"].set_index("Strike")
        puts  = chain[chain["Type"] == "PUT"].set_index("Strike")

        pain_by_strike = {}
        for test_price in strikes:
            call_pain = 0.0
            put_pain  = 0.0
            for s in strikes:
                c_oi = float(calls.loc[s, "OI"]) if s in calls.index else 0
                p_oi = float(puts.loc[s, "OI"])  if s in puts.index  else 0
                call_pain += max(test_price - s, 0) * c_oi
                put_pain  += max(s - test_price, 0) * p_oi
            pain_by_strike[test_price] = call_pain + put_pain

        # Max pain = strike where pain to buyers is maximized
        max_pain_price = max(pain_by_strike, key=pain_by_strike.get)
        return float(max_pain_price)

    @staticmethod
    def put_call_ratio(ticker: str) -> Dict:
        """Compute Put/Call ratio by volume and by OI.

        Returns:
            Dict with pcr_volume, pcr_oi, sentiment.
        """
        exps = OptionsChainViewer.get_expirations(ticker)
        if not exps:
            return {}

        total_call_vol, total_put_vol = 0, 0
        total_call_oi,  total_put_oi  = 0, 0

        for exp in exps[:4]:
            try:
                chain = OptionsChainViewer.get_chain(ticker, exp)
                if chain.empty:
                    continue
                calls = chain[chain["Type"] == "CALL"]
                puts  = chain[chain["Type"] == "PUT"]
                total_call_vol += int(calls["Volume"].sum())
                total_put_vol  += int(puts["Volume"].sum())
                total_call_oi  += int(calls["OI"].sum())
                total_put_oi   += int(puts["OI"].sum())
            except Exception:
                continue

        pcr_vol = total_put_vol / max(total_call_vol, 1)
        pcr_oi  = total_put_oi  / max(total_call_oi, 1)

        if pcr_vol > 1.2:
            sentiment = "Bearish"
        elif pcr_vol < 0.7:
            sentiment = "Bullish"
        else:
            sentiment = "Neutral"

        return {
            "pcr_volume":      round(pcr_vol, 3),
            "pcr_oi":          round(pcr_oi, 3),
            "sentiment":       sentiment,
            "call_volume":     total_call_vol,
            "put_volume":      total_put_vol,
            "call_oi":         total_call_oi,
            "put_oi":          total_put_oi,
        }
