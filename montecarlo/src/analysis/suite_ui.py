"""
suite_ui.py — Complete Streamlit UI for the Financial Analysis Suite.

Entry point: call render_financial_analysis_suite() from a Streamlit page.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st
from genesix.utils.quant_conventions import RISK_FREE_RATE, periods_per_year_for_timeframe

from .alerts_engine import Alert, AlertCondition, AlertsEngine, CONDITION_TYPES
from .backtesting import Backtester, PRESET_STRATEGIES
from .charting import ChartEngine
from .core import DataFetcher, DARK_THEME
from .export import ReportExporter
from .fundamentals import FundamentalAnalyzer
from .heatmap import MarketHeatmap
from .intermarket import IntermarketAnalyzer, MarketBreadth
from .journal import JournalEntry, TradeJournal
from .options_chain import OptionsChainViewer
from .patterns import PatternDetector
from .portfolio_analytics import PortfolioAnalytics
from .relative_strength import RelativeStrength
from .screener import StockScreener, PRESET_SCREENS
from .seasonality import SeasonalityAnalyzer
from .sector_rotation import SectorRotation
from .technical import TechnicalIndicators
from .volume_profile import VolumeProfile

_C = DARK_THEME

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
.fa-metric-card {
    background: #1a1a2e;
    border: 1px solid #2a2a3e;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 4px 0;
}
.fa-metric-label { color: #94a3b8; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
.fa-metric-value { color: #e2e8f0; font-size: 22px; font-weight: 700; margin-top: 2px; }
.fa-metric-change { font-size: 13px; margin-top: 2px; }
.fa-green { color: #22c55e; }
.fa-red { color: #ef4444; }
.fa-yellow { color: #f59e0b; }
.fa-tag {
    display: inline-block;
    background: #2a2a3e;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    color: #94a3b8;
    margin: 2px;
}
.fa-section-title {
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 12px 0 6px;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# INIT STATE
# ─────────────────────────────────────────────────────────────────────────────

_WATCHLIST_DEFAULT = ["AAPL", "MSFT", "SPY", "EURUSD=X", "GC=F", "^GSPC", "^VIX", "^TNX"]

def _init_state() -> None:
    st.session_state.setdefault("fa_symbol", "AAPL")
    st.session_state.setdefault("fa_timeframe", "1d")
    st.session_state.setdefault("fa_watchlist", _WATCHLIST_DEFAULT.copy())
    st.session_state.setdefault("fa_chart_type", "candlestick")
    st.session_state.setdefault("fa_overlays", ["ema_20", "ema_50"])
    st.session_state.setdefault("fa_sub_panels", ["volume", "rsi"])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _metric_card(label: str, value: str, change: Optional[str] = None,
                  change_positive: Optional[bool] = None) -> str:
    change_html = ""
    if change:
        color = "fa-green" if change_positive else ("fa-red" if change_positive is False else "")
        change_html = f'<div class="fa-metric-change {color}">{change}</div>'
    return f"""
    <div class="fa-metric-card">
        <div class="fa-metric-label">{label}</div>
        <div class="fa-metric-value">{value}</div>
        {change_html}
    </div>
    """


def _fmt_val(v, suffix: str = "", prefix: str = "", decimals: int = 2) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{prefix}{v:.{decimals}f}{suffix}"


def _large_num(v) -> str:
    if v is None:
        return "N/A"
    if abs(v) >= 1e12:
        return f"${v/1e12:.2f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.2f}M"
    return f"${v:.0f}"


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def _render_sidebar() -> None:
    """Render the global sidebar: symbol picker, quick stats, watchlist, market pulse."""
    with st.sidebar:
        st.markdown(_CSS, unsafe_allow_html=True)

        # ── Symbol selector ────────────────────────────────────────────────
        symbol = st.text_input(
            "Symbol",
            value=st.session_state.fa_symbol,
            key="_fa_symbol_input",
            placeholder="AAPL, MSFT, EURUSD=X…",
        ).strip().upper()
        if symbol and symbol != st.session_state.fa_symbol:
            st.session_state.fa_symbol = symbol
            st.rerun()

        # ── Quick stats ───────────────────────────────────────────────────
        snap = DataFetcher.snapshot(st.session_state.fa_symbol)
        if snap:
            price = snap.get("price", 0)
            chg_pct = snap.get("change_pct", 0)
            color = "fa-green" if chg_pct >= 0 else "fa-red"
            sign = "+" if chg_pct >= 0 else ""
            st.markdown(f"""
            <div style="background:#12121a;border:1px solid #2a2a3e;border-radius:10px;padding:14px 16px;margin-bottom:12px">
                <div style="font-size:15px;font-weight:700;color:#e2e8f0">{snap.get('name', symbol)}</div>
                <div style="font-size:24px;font-weight:800;color:#e2e8f0;margin:6px 0">${price:.2f}</div>
                <div class="{color}" style="font-size:13px">{sign}{chg_pct:.2f}%</div>
                <hr style="border-color:#2a2a3e;margin:10px 0">
                <div style="font-size:11px;color:#94a3b8">
                    <b>Mkt Cap</b> {_large_num(snap.get('market_cap'))}<br>
                    <b>52W</b> ${snap.get('week_52_low', 0):.2f} – ${snap.get('week_52_high', 0):.2f}<br>
                    <b>P/E</b> {_fmt_val(snap.get('pe_ratio'))}<br>
                    <b>Vol</b> {snap.get('volume', 0):,.0f}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Timeframe ─────────────────────────────────────────────────────
        tf = st.selectbox(
            "Timeframe",
            ["5m", "15m", "1h", "4h", "1d", "1w", "1M"],
            index=["5m", "15m", "1h", "4h", "1d", "1w", "1M"].index(
                st.session_state.fa_timeframe
            ),
        )
        st.session_state.fa_timeframe = tf

        # ── Watchlist ─────────────────────────────────────────────────────
        st.markdown('<div class="fa-section-title">Watchlist</div>', unsafe_allow_html=True)
        watchlist = st.session_state.fa_watchlist

        for sym in watchlist:
            ws = DataFetcher.snapshot(sym)
            if ws:
                p = ws.get("price", 0)
                c = ws.get("change_pct", 0)
                color = "#22c55e" if c >= 0 else "#ef4444"
                arrow = "▲" if c >= 0 else "▼"
                clicked = st.button(
                    f"{sym}  ${p:.2f}  {arrow}{abs(c):.1f}%",
                    key=f"wl_{sym}",
                    help=f"Switch to {sym}",
                    use_container_width=True,
                )
                if clicked:
                    st.session_state.fa_symbol = sym
                    st.rerun()

        # Add to watchlist
        with st.expander("+ Add to Watchlist"):
            new_sym = st.text_input("Ticker", key="wl_add").strip().upper()
            if st.button("Add", key="wl_add_btn") and new_sym:
                if new_sym not in watchlist:
                    st.session_state.fa_watchlist = watchlist + [new_sym]
                    st.rerun()

        # ── Market Pulse ──────────────────────────────────────────────────
        st.markdown('<div class="fa-section-title">Market Pulse</div>', unsafe_allow_html=True)
        pulse_tickers = {"S&P": "^GSPC", "VIX": "^VIX", "10Y": "^TNX", "DXY": "DX-Y.NYB", "Gold": "GC=F"}
        for label, ticker in pulse_tickers.items():
            ps = DataFetcher.snapshot(ticker)
            if ps:
                c = ps.get("change_pct", 0)
                color = "#22c55e" if c >= 0 else "#ef4444"
                sign = "+" if c >= 0 else ""
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;font-size:12px;padding:2px 0">'
                    f'<span style="color:#94a3b8">{label}</span>'
                    f'<span style="color:{color}">{sign}{c:.2f}%</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# TAB: CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def _tab_charts(symbol: str, timeframe: str) -> None:
    engine = ChartEngine()
    detector = PatternDetector()

    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        chart_type = st.selectbox(
            "Chart Type",
            ["candlestick", "heikin_ashi", "ohlc", "line", "area"],
            index=0,
        )
    with col2:
        log_scale = st.checkbox("Log Scale", value=False)
    with col3:
        multi_tf = st.checkbox("Multi-Timeframe View", value=False)

    # Overlays
    with st.expander("Overlays & Indicators", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("**Moving Averages**")
            show_ema20  = st.checkbox("EMA 20",  True)
            show_ema50  = st.checkbox("EMA 50",  True)
            show_sma200 = st.checkbox("SMA 200", False)
            show_hull   = st.checkbox("Hull MA (20)", False)
            show_bbands = st.checkbox("Bollinger Bands", False)
            show_keltner = st.checkbox("Keltner Channels", False)
        with c2:
            st.markdown("**Trend**")
            show_ichimoku   = st.checkbox("Ichimoku Cloud", False)
            show_supertrend = st.checkbox("SuperTrend", False)
            show_psar       = st.checkbox("Parabolic SAR", False)
            show_vwap       = st.checkbox("VWAP", False)
        with c3:
            st.markdown("**Sub-Panels**")
            show_volume = st.checkbox("Volume", True)
            show_rsi    = st.checkbox("RSI (14)", True)
            show_macd   = st.checkbox("MACD", False)
            show_stoch  = st.checkbox("Stochastic", False)
            show_obv    = st.checkbox("OBV", False)
        with c4:
            st.markdown("**Levels**")
            show_sr     = st.checkbox("Auto S/R", False)
            show_fib    = st.checkbox("Fibonacci", False)
            show_pivots = st.checkbox("Pivot Points", False)
            pivot_method = st.selectbox("Pivot Method", ["standard", "fibonacci", "camarilla", "woodie"], index=0)

    # Build config
    overlays = []
    if show_ema20:   overlays.append({"type": "ema", "period": 20, "color": "#22c55e"})
    if show_ema50:   overlays.append({"type": "ema", "period": 50, "color": "#f59e0b"})
    if show_sma200:  overlays.append({"type": "sma", "period": 200, "color": "#94a3b8"})
    if show_hull:    overlays.append({"type": "hull", "period": 20, "color": "#a855f7"})
    if show_bbands:  overlays.append({"type": "bollinger", "period": 20, "std": 2.0})
    if show_keltner: overlays.append({"type": "keltner", "period": 20})
    if show_ichimoku:   overlays.append({"type": "ichimoku"})
    if show_supertrend: overlays.append({"type": "supertrend"})
    if show_psar:       overlays.append({"type": "parabolic_sar"})
    if show_vwap:       overlays.append({"type": "vwap"})

    sub_panels = []
    if show_volume: sub_panels.append({"type": "volume", "height_ratio": 0.15})
    if show_rsi:    sub_panels.append({"type": "rsi",    "height_ratio": 0.12})
    if show_macd:   sub_panels.append({"type": "macd",   "height_ratio": 0.12})
    if show_stoch:  sub_panels.append({"type": "stochastic", "height_ratio": 0.12})
    if show_obv:    sub_panels.append({"type": "obv",    "height_ratio": 0.12})

    levels = []
    if show_sr:     levels.append({"type": "support_resistance", "auto": True})
    if show_fib:    levels.append({"type": "fibonacci"})
    if show_pivots: levels.append({"type": "pivot_points", "method": pivot_method})

    config = {
        "chart_type": chart_type,
        "log_scale":  log_scale,
        "overlays":   overlays,
        "sub_panels": sub_panels if sub_panels else [{"type": "volume", "height_ratio": 0.15}],
        "levels":     levels,
    }

    df = DataFetcher.ohlcv(symbol, timeframe)

    if multi_tf:
        tfs = st.multiselect("Select Timeframes", ["5m", "15m", "1h", "4h", "1d", "1w"],
                              default=["1h", "4h", "1d", "1w"])
        inds = st.multiselect("Indicators on each TF", ["ema_20", "ema_50", "sma_200"],
                               default=["ema_20", "ema_50"])
        fig = engine.render_multi_timeframe(symbol, tfs, inds)
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = engine.render_pro_chart(df, symbol, config)
        st.plotly_chart(fig, use_container_width=True)

    # Export
    col_exp1, col_exp2 = st.columns([1, 5])
    with col_exp1:
        ReportExporter.download_button_chart(fig, f"{symbol}_chart.png", "PNG")

    # Pattern detection
    with st.expander("Pattern Scanner", expanded=False):
        if not df.empty:
            patterns = detector.detect_all_with_chart(df, lookback=80)
            if patterns:
                for p in patterns[:10]:
                    bias_color = "fa-green" if p.bias == "Bullish" else ("fa-red" if p.bias == "Bearish" else "fa-yellow")
                    st.markdown(
                        f'<div style="padding:8px;margin:4px 0;background:#1a1a2e;border-radius:8px;border-left:3px solid {"#22c55e" if p.bias=="Bullish" else "#ef4444" if p.bias=="Bearish" else "#f59e0b"}">'
                        f'<b>{p.pattern}</b> <span class="fa-tag">{p.category}</span> '
                        f'<span class="{bias_color}">{p.bias}</span> '
                        f'<span style="color:#94a3b8;font-size:11px">conf: {p.confidence:.0%} · {p.strength}</span><br>'
                        f'<span style="color:#94a3b8;font-size:11px">{p.description}</span>'
                        f'{"<br><span style=color:#f59e0b;font-size:11px>Target: $" + str(p.target) + "</span>" if p.target else ""}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No significant patterns detected in the last 80 bars.")
        else:
            st.warning(f"No data available for {symbol}.")

    # Comparison chart
    with st.expander("Compare Assets", expanded=False):
        compare_input = st.text_input("Add symbols to compare (comma-separated)",
                                       placeholder="AAPL, MSFT, GOOGL")
        if compare_input:
            syms = [s.strip().upper() for s in compare_input.split(",") if s.strip()]
            syms = [symbol] + syms
            normalize = st.checkbox("Normalize to base 100", True)
            fig_cmp = engine.render_comparison_chart(syms, timeframe, normalize=normalize)
            st.plotly_chart(fig_cmp, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: SCREENER
# ─────────────────────────────────────────────────────────────────────────────

def _tab_screener() -> None:
    screener = StockScreener()

    col1, col2 = st.columns([1, 3])
    with col1:
        universe_name = st.selectbox(
            "Universe", ["nasdaq100", "sp500", "cac40", "eurostoxx50"],
        )
        mode = st.radio("Mode", ["Preset Screens", "Custom Filters"])

    with col2:
        if mode == "Preset Screens":
            preset_cols = st.columns(len(PRESET_SCREENS))
            selected_preset = None
            for i, (key, cfg) in enumerate(PRESET_SCREENS.items()):
                with preset_cols[i % len(preset_cols)]:
                    if st.button(f"{cfg['icon']} {key.replace('_', ' ').title()}", key=f"preset_{key}"):
                        selected_preset = key

            if selected_preset:
                st.info(f"**{PRESET_SCREENS[selected_preset]['description']}**")
                with st.spinner(f"Scanning {universe_name}… (this may take 20-40s)"):
                    results = screener.run_preset(selected_preset, universe_name)
                if not results.empty:
                    _render_screener_results(results)
                else:
                    st.warning("No stocks match this screen right now.")

        else:  # Custom filters
            st.markdown("**Technical Filters**")
            c1, c2, c3 = st.columns(3)
            filters: Dict = {}
            with c1:
                rsi_min = st.number_input("RSI min", 0, 100, 0, key="scr_rsi_min")
                rsi_max = st.number_input("RSI max", 0, 100, 100, key="scr_rsi_max")
                if rsi_min > 0 or rsi_max < 100:
                    filters["rsi_14"] = {}
                    if rsi_min > 0: filters["rsi_14"]["min"] = rsi_min
                    if rsi_max < 100: filters["rsi_14"]["max"] = rsi_max
                above_200 = st.checkbox("Above SMA 200", key="scr_sma200")
                if above_200: filters["price_above_sma200"] = True
            with c2:
                pe_max = st.number_input("P/E max", 0, 500, 0, key="scr_pe_max")
                if pe_max > 0: filters["pe_ratio"] = {"max": pe_max}
                mktcap_min = st.number_input("Min Market Cap ($B)", 0.0, 10000.0, 0.0, key="scr_mc")
                if mktcap_min > 0: filters["market_cap"] = {"min": mktcap_min * 1e9}
            with c3:
                div_min = st.number_input("Min Div Yield (%)", 0.0, 20.0, 0.0, key="scr_div")
                if div_min > 0: filters["dividend_yield"] = {"min": div_min / 100}
                margin_min = st.number_input("Min Net Margin (%)", -100.0, 100.0, 0.0, key="scr_margin")
                if margin_min > 0: filters["net_margin"] = {"min": margin_min / 100}

            if st.button("Run Screen", key="scr_run") and filters:
                with st.spinner(f"Scanning {universe_name}…"):
                    results = screener.screen(universe_name, filters, limit=50)
                if not results.empty:
                    _render_screener_results(results)
                else:
                    st.info("No stocks match your filters.")


def _render_screener_results(df: pd.DataFrame) -> None:
    """Display screener results table."""
    st.success(f"Found {len(df)} matching stocks")

    display_cols = [
        "symbol", "name", "price", "pct_change_1d", "pct_change_1m",
        "rsi_14", "pe_ratio", "market_cap", "net_margin",
    ]
    show_cols = [c for c in display_cols if c in df.columns]
    show_df = df[show_cols].copy()

    # Format
    if "pct_change_1d" in show_df.columns:
        show_df["pct_change_1d"] = show_df["pct_change_1d"].apply(
            lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
        )
    if "pct_change_1m" in show_df.columns:
        show_df["pct_change_1m"] = show_df["pct_change_1m"].apply(
            lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
        )
    if "market_cap" in show_df.columns:
        show_df["market_cap"] = show_df["market_cap"].apply(
            lambda x: f"${x/1e9:.1f}B" if pd.notna(x) and x else "N/A"
        )
    if "net_margin" in show_df.columns:
        show_df["net_margin"] = show_df["net_margin"].apply(
            lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
        )
    if "rsi_14" in show_df.columns:
        show_df["rsi_14"] = show_df["rsi_14"].apply(
            lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
        )
    if "price" in show_df.columns:
        show_df["price"] = show_df["price"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
        )
    if "pe_ratio" in show_df.columns:
        show_df["pe_ratio"] = show_df["pe_ratio"].apply(
            lambda x: f"{x:.1f}x" if pd.notna(x) else "N/A"
        )

    show_df.columns = [c.replace("_", " ").title() for c in show_df.columns]
    st.dataframe(show_df, use_container_width=True, height=500)
    ReportExporter.download_button_csv(show_df, "screener_results.csv", "Download CSV")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: FUNDAMENTALS
# ─────────────────────────────────────────────────────────────────────────────

def _tab_fundamentals(symbol: str) -> None:
    analyzer = FundamentalAnalyzer()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Overview", "Financials", "Valuation & DCF", "Earnings", "Peer Comparison"
    ])

    with tab1:
        profile = analyzer.get_company_profile(symbol)
        if profile:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"""
                <div style="background:#1a1a2e;border-radius:10px;padding:16px">
                    <div style="font-size:18px;font-weight:700;color:#e2e8f0">{profile.get('name', symbol)}</div>
                    <div style="color:#94a3b8;margin-top:4px">{profile.get('sector', '')} · {profile.get('industry', '')}</div>
                    <hr style="border-color:#2a2a3e">
                    <table style="font-size:12px;width:100%">
                    <tr><td style="color:#94a3b8">Exchange</td><td style="color:#e2e8f0">{profile.get('exchange', 'N/A')}</td></tr>
                    <tr><td style="color:#94a3b8">Country</td><td style="color:#e2e8f0">{profile.get('country', 'N/A')}</td></tr>
                    <tr><td style="color:#94a3b8">Employees</td><td style="color:#e2e8f0">{profile.get('employees', 'N/A'):,}</td></tr>
                    <tr><td style="color:#94a3b8">Mkt Cap</td><td style="color:#e2e8f0">{_large_num(profile.get('market_cap'))}</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                desc = profile.get("description", "")
                if desc:
                    st.markdown(f'<div style="color:#94a3b8;font-size:13px;line-height:1.6">{desc[:600]}{"…" if len(desc)>600 else ""}</div>', unsafe_allow_html=True)

        # Profitability + health in metrics
        prof = analyzer.get_profitability_metrics(symbol)
        health = analyzer.get_financial_health(symbol)

        col_metrics = st.columns(4)
        metrics_data = [
            ("Gross Margin", f"{prof.get('gross_margin', 0)*100:.1f}%" if prof.get('gross_margin') else "N/A"),
            ("Net Margin",   f"{prof.get('net_margin', 0)*100:.1f}%"   if prof.get('net_margin')   else "N/A"),
            ("ROE",          f"{prof.get('roe', 0)*100:.1f}%"          if prof.get('roe')          else "N/A"),
            ("D/E Ratio",    f"{health.get('debt_equity', 'N/A')}"),
            ("Current Ratio", f"{health.get('current_ratio', 'N/A')}"),
            ("Altman Z",     str(health.get("altman_z", "N/A"))),
            ("Piotroski F",  f"{health.get('piotroski_f', 'N/A')}/9"),
            ("FCF",          _large_num(health.get("free_cashflow"))),
        ]
        for i, (label, val) in enumerate(metrics_data):
            with col_metrics[i % 4]:
                st.markdown(_metric_card(label, val), unsafe_allow_html=True)

    with tab2:
        statements = analyzer.get_financial_statements(symbol)
        sub = st.radio("Statement", ["Income Statement", "Balance Sheet", "Cash Flow"], horizontal=True)
        key_map = {"Income Statement": "income", "Balance Sheet": "balance", "Cash Flow": "cashflow"}
        df_stmt = statements.get(key_map[sub], pd.DataFrame())
        if not df_stmt.empty:
            st.dataframe(df_stmt.style.format("{:,.0f}", na_rep="N/A"), use_container_width=True)
            ReportExporter.download_button_csv(df_stmt, f"{symbol}_{key_map[sub]}.csv")
        else:
            st.info(f"No {sub} data available for {symbol}.")

    with tab3:
        ratios = analyzer.get_valuation_ratios(symbol)
        if ratios:
            c1, c2, c3, c4 = st.columns(4)
            val_metrics = [
                ("P/E (TTM)",    _fmt_val(ratios.get("pe_trailing"), "x")),
                ("P/E (Fwd)",    _fmt_val(ratios.get("pe_forward"),  "x")),
                ("PEG",          _fmt_val(ratios.get("peg_ratio"),   "x")),
                ("EV/EBITDA",    _fmt_val(ratios.get("ev_ebitda"),   "x")),
                ("P/S",          _fmt_val(ratios.get("ps_ratio"),    "x")),
                ("P/B",          _fmt_val(ratios.get("pb_ratio"),    "x")),
                ("Div Yield",    f"{ratios.get('dividend_yield', 0)*100:.2f}%" if ratios.get("dividend_yield") else "N/A"),
                ("Payout Ratio", f"{ratios.get('payout_ratio', 0)*100:.1f}%" if ratios.get("payout_ratio") else "N/A"),
            ]
            for i, (label, val) in enumerate(val_metrics):
                with [c1, c2, c3, c4][i % 4]:
                    st.markdown(_metric_card(label, val), unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("DCF Valuation")
        c1, c2, c3 = st.columns(3)
        with c1:
            growth = st.slider("Revenue Growth Rate (%)", -20, 60, 10) / 100
        with c2:
            discount = st.slider("Discount Rate (%)", 5, 20, 10) / 100
        with c3:
            terminal = st.slider("Terminal Growth (%)", 1, 5, 2) / 100

        if st.button("Run DCF"):
            with st.spinner("Computing DCF…"):
                dcf = analyzer.simple_dcf(symbol, growth, terminal, discount)
            if dcf:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(_metric_card("Intrinsic Value", f"${dcf['intrinsic_value']:.2f}"), unsafe_allow_html=True)
                with c2:
                    st.markdown(_metric_card("Current Price", f"${dcf['current_price']:.2f}"), unsafe_allow_html=True)
                with c3:
                    upside = dcf["upside_pct"]
                    st.markdown(_metric_card("Upside", f"{upside:+.1f}%",
                                change_positive=upside > 0), unsafe_allow_html=True)
                with c4:
                    mos = dcf.get("margin_of_safety")
                    st.markdown(_metric_card("Margin of Safety", f"{mos:.1f}%" if mos else "N/A"), unsafe_allow_html=True)

                st.markdown("**Sensitivity Table** (Intrinsic Value by Growth Rate × Discount Rate)")
                sens = dcf.get("sensitivity_table")
                if sens is not None and not sens.empty:
                    st.dataframe(
                        sens.style.background_gradient(cmap="RdYlGn", axis=None),
                        use_container_width=True,
                    )
            else:
                st.warning("Insufficient data to compute DCF for this ticker.")

    with tab4:
        earnings = analyzer.earnings_analysis(symbol)
        if earnings:
            c1, c2, c3 = st.columns(3)
            with c1:
                br = earnings.get("beat_rate")
                st.markdown(_metric_card("Beat Rate", f"{br*100:.0f}%" if br else "N/A"), unsafe_allow_html=True)
            with c2:
                ag = earnings.get("avg_surprise")
                st.markdown(_metric_card("Avg Surprise", f"{ag:.1f}%" if ag else "N/A",
                            change_positive=ag > 0 if ag else None), unsafe_allow_html=True)
            with c3:
                st.markdown(_metric_card("Next Earnings", str(earnings.get("next_earnings", "N/A"))), unsafe_allow_html=True)

            if earnings.get("pattern_text"):
                st.info(earnings["pattern_text"])

            hist = earnings.get("history")
            if hist is not None and not hist.empty:
                st.dataframe(hist.head(12), use_container_width=True)

    with tab5:
        peers_input = st.text_input("Peers (optional, comma-separated)", placeholder="Auto-detect if empty")
        peers = [s.strip().upper() for s in peers_input.split(",") if s.strip()] or None
        with st.spinner("Fetching peer data…"):
            peers_df = analyzer.peer_comparison(symbol, peers)
        if not peers_df.empty:
            st.dataframe(peers_df, use_container_width=True)
            ReportExporter.download_button_csv(peers_df, f"{symbol}_peers.csv")
        else:
            st.warning("Peer data unavailable.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: MARKET HEATMAP
# ─────────────────────────────────────────────────────────────────────────────

def _tab_heatmap() -> None:
    hm = MarketHeatmap()
    c1, c2, c3 = st.columns(3)
    with c1:
        color_by = st.selectbox("Color By", ["change_1d", "mkt_cap"], index=0)
    with c2:
        size_by = st.selectbox("Size By", ["mkt_cap", "volume"], index=0)
    with c3:
        max_per_sector = st.slider("Stocks per Sector", 5, 20, 10)

    with st.spinner("Loading market heatmap…"):
        fig = hm.generate_heatmap(color_by=color_by, size_by=size_by,
                                   max_tickers_per_sector=max_per_sector)
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: OPTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _tab_options(symbol: str) -> None:
    viewer = OptionsChainViewer()
    expirations = viewer.get_expirations(symbol)

    if not expirations:
        st.warning(f"No options data for {symbol}.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        expiry = st.selectbox("Expiration", expirations[:12])
    with col2:
        view_mode = st.radio("View", ["Chain", "IV Smile", "Term Structure", "Unusual Activity", "Max Pain / PCR"])

    if view_mode == "Chain":
        with st.spinner("Loading options chain…"):
            chain = viewer.get_chain(symbol, expiry)
        if not chain.empty:
            calls = chain[chain["Type"] == "CALL"]
            puts  = chain[chain["Type"] == "PUT"]
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Calls**")
                st.dataframe(calls.drop("Type", axis=1).set_index("Strike"), use_container_width=True)
            with c2:
                st.markdown("**Puts**")
                st.dataframe(puts.drop("Type", axis=1).set_index("Strike"), use_container_width=True)

    elif view_mode == "IV Smile":
        fig = viewer.iv_smile(symbol, expiry)
        st.plotly_chart(fig, use_container_width=True)

    elif view_mode == "Term Structure":
        fig = viewer.iv_term_structure(symbol)
        st.plotly_chart(fig, use_container_width=True)

    elif view_mode == "Unusual Activity":
        with st.spinner("Scanning for unusual activity…"):
            unusual = viewer.unusual_activity(symbol)
        if not unusual.empty:
            st.dataframe(unusual, use_container_width=True)
        else:
            st.info("No unusual options activity detected.")

    else:  # Max Pain / PCR
        c1, c2 = st.columns(2)
        with c1:
            mp = viewer.max_pain(symbol, expiry)
            st.markdown(_metric_card("Max Pain", f"${mp:.2f}" if mp else "N/A"), unsafe_allow_html=True)
        with c2:
            pcr = viewer.put_call_ratio(symbol)
            if pcr:
                st.markdown(_metric_card(
                    "Put/Call Ratio",
                    f"{pcr.get('pcr_volume', 0):.3f}",
                    pcr.get("sentiment", ""),
                    change_positive=pcr.get("sentiment") == "Bullish",
                ), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: SECTOR ROTATION
# ─────────────────────────────────────────────────────────────────────────────

def _tab_sector_rotation() -> None:
    sr = SectorRotation()
    tab1, tab2 = st.tabs(["RRG Chart", "Sector Performance Table"])

    with tab1:
        benchmark = st.selectbox("Benchmark", ["SPY", "QQQ", "IWM", "EFA"], index=0)
        tail_len = st.slider("Tail Length (weeks)", 2, 8, 4)
        with st.spinner("Building RRG…"):
            fig = sr.rrg_chart(benchmark, tail_length=tail_len)
        st.plotly_chart(fig, use_container_width=True)

        # Legend
        from .sector_rotation import _QUADRANT_DESCS
        cols = st.columns(4)
        for i, (q, desc) in enumerate(_QUADRANT_DESCS.items()):
            from .sector_rotation import _QUADRANT_COLORS
            with cols[i]:
                st.markdown(
                    f'<div style="background:#1a1a2e;border-left:3px solid {_QUADRANT_COLORS[q]};'
                    f'padding:8px;border-radius:4px"><b style="color:{_QUADRANT_COLORS[q]}">{q}</b>'
                    f'<br><span style="color:#94a3b8;font-size:11px">{desc}</span></div>',
                    unsafe_allow_html=True,
                )

    with tab2:
        with st.spinner("Fetching sector performance…"):
            perf_df = sr.sector_performance_table()
        if not perf_df.empty:
            st.dataframe(perf_df, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: INTERMARKET
# ─────────────────────────────────────────────────────────────────────────────

def _tab_intermarket() -> None:
    ia = IntermarketAnalyzer()
    mb = MarketBreadth()

    tab1, tab2, tab3 = st.tabs(["Cross-Asset Correlations", "Regime Detection", "Market Breadth"])

    with tab1:
        with st.spinner("Computing cross-asset correlations…"):
            dashboard = ia.cross_asset_dashboard()

        for label, entry in dashboard.items():
            if entry.get("error"):
                continue
            c_val = entry["current"]
            z = entry["zscore"]
            flag = entry.get("flag", "")
            color = "#22c55e" if c_val >= 0 else "#ef4444"
            col1, col2 = st.columns([2, 3])
            with col1:
                st.markdown(
                    f'<div style="background:#1a1a2e;border-radius:8px;padding:12px;margin:4px 0">'
                    f'<div style="font-size:13px;font-weight:600;color:#e2e8f0">{label}</div>'
                    f'<div style="font-size:12px;color:#94a3b8">{entry["description"]}</div>'
                    f'<div style="font-size:18px;font-weight:700;color:{color};margin-top:6px">'
                    f'r = {c_val:.3f}</div>'
                    f'<div style="font-size:11px;color:#94a3b8">Z-score: {z:.2f} | '
                    f'Percentile: {entry["pct_rank"]:.0f}th</div>'
                    f'{"<div style=color:#f59e0b;font-size:11px>" + flag + "</div>" if flag else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                fig = ia.render_cross_asset_chart(label, dashboard)
                if fig.data:
                    st.plotly_chart(fig, use_container_width=True)

    with tab2:
        ticker_input = st.text_input("Index for Regime", "^GSPC")
        with st.spinner("Detecting market regime…"):
            regime = ia.regime_detection(ticker_input)
        if regime:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f'<div style="background:#1a1a2e;border-left:4px solid {regime["color"]};'
                    f'border-radius:8px;padding:16px">'
                    f'<div style="font-size:11px;color:#94a3b8">Current Regime</div>'
                    f'<div style="font-size:20px;font-weight:700;color:{regime["color"]}">'
                    f'{regime["regime"]}</div>'
                    f'<div style="font-size:12px;color:#94a3b8;margin-top:6px">{regime["description"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(_metric_card("Realized Vol (ann.)", f"{regime['vol_current']:.1f}%",
                            f"Median: {regime['vol_median']:.1f}%"), unsafe_allow_html=True)
            with col3:
                trend_3m = regime["trend_3m"]
                st.markdown(_metric_card("3M Trend", f"{trend_3m:+.1f}%",
                            change_positive=trend_3m > 0), unsafe_allow_html=True)

            fig = ia.render_regime_chart(ticker_input)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        with st.spinner("Computing market breadth…"):
            breadth = mb.compute_breadth()
        if breadth:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(_metric_card("Advances", str(breadth["advances"])), unsafe_allow_html=True)
            with c2:
                st.markdown(_metric_card("Declines", str(breadth["declines"])), unsafe_allow_html=True)
            with c3:
                st.markdown(_metric_card("A/D Ratio", f"{breadth['ad_ratio']:.2f}",
                            breadth["sentiment"],
                            change_positive=breadth["ad_ratio"] > 1), unsafe_allow_html=True)
            with c4:
                st.markdown(_metric_card("% Above SMA200", f"{breadth['pct_above_200']:.1f}%"), unsafe_allow_html=True)

            c5, c6 = st.columns(2)
            with c5:
                st.markdown(_metric_card("52W Highs", str(breadth["new_highs"])), unsafe_allow_html=True)
            with c6:
                st.markdown(_metric_card("52W Lows", str(breadth["new_lows"])), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: SEASONALITY
# ─────────────────────────────────────────────────────────────────────────────

def _tab_seasonality(symbol: str) -> None:
    sa = SeasonalityAnalyzer()
    tab1, tab2, tab3 = st.tabs(["Monthly Heatmap", "Day-of-Week", "Pre/Post Earnings"])

    with tab1:
        years = st.slider("Years of history", 3, 20, 10, key="seas_years")
        with st.spinner("Computing seasonality…"):
            fig = sa.render_monthly_heatmap(symbol, years)
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("Raw Data"):
            data = sa.monthly_returns_heatmap(symbol, years)
            if not data.empty:
                st.dataframe(data.style.background_gradient(cmap="RdYlGn", axis=None), use_container_width=True)

    with tab2:
        with st.spinner("Analyzing day-of-week patterns…"):
            dow_df = sa.day_of_week_analysis(symbol)
        if not dow_df.empty:
            st.dataframe(dow_df, use_container_width=True)
            import plotly.express as px
            fig_dow = px.bar(
                dow_df, x="Day", y="Avg Return %",
                color="Avg Return %",
                color_continuous_scale=["#ef4444", "#374151", "#22c55e"],
                color_continuous_midpoint=0,
            )
            fig_dow.update_layout(paper_bgcolor=_C["bg"], plot_bgcolor=_C["panel"],
                                   font=dict(color=_C["text"]), showlegend=False)
            st.plotly_chart(fig_dow, use_container_width=True)

    with tab3:
        with st.spinner("Analyzing pre/post earnings patterns…"):
            events = sa.pre_post_event_analysis(symbol)
        if events and events.get("note"):
            st.info(events["note"])
            c1, c2 = st.columns(2)
            with c1:
                pre = events.get("pre_avg", 0) or 0
                st.markdown(_metric_card("Avg Return (5d PRE)", f"{pre:+.2f}%",
                            change_positive=pre > 0), unsafe_allow_html=True)
            with c2:
                post = events.get("post_avg", 0) or 0
                st.markdown(_metric_card("Avg Return (5d POST)", f"{post:+.2f}%",
                            change_positive=post > 0), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: BACKTEST LAB
# ─────────────────────────────────────────────────────────────────────────────

def _tab_backtest(symbol: str, timeframe: str) -> None:
    bt = Backtester(
        risk_free_rate=float(st.session_state.get("rate_sidebar", RISK_FREE_RATE)),
        periods_per_year=periods_per_year_for_timeframe(timeframe),
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        strategy_name = st.selectbox("Strategy", list(PRESET_STRATEGIES.keys()))
    with c2:
        capital = st.number_input("Initial Capital ($)", 1000, 1_000_000, 10_000, step=1000)
        bt.initial_capital = float(capital)
    with c3:
        allow_short = st.checkbox("Allow Short", True)
        bt.allow_short = allow_short

    if st.button("Run Backtest"):
        df = DataFetcher.ohlcv(symbol, timeframe)
        if df.empty:
            st.error(f"No data for {symbol}.")
            return

        signal_fn = PRESET_STRATEGIES[strategy_name]
        with st.spinner("Running backtest…"):
            result = bt.run(df, signal_fn, strategy_name)

        m = result.metrics
        if not m:
            st.error("Insufficient data for backtest.")
            return

        # Metrics row
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(_metric_card("Total Return", f"{m.get('total_return', 0):+.1f}%",
                        f"vs Benchmark: {m.get('alpha', 0):+.1f}%",
                        change_positive=m.get('total_return', 0) > 0), unsafe_allow_html=True)
        with c2:
            st.markdown(_metric_card("Sharpe Ratio", f"{m.get('sharpe', 0):.2f}",
                        f"Sortino: {m.get('sortino', 0):.2f}"), unsafe_allow_html=True)
        with c3:
            st.markdown(_metric_card("Max Drawdown", f"{m.get('max_drawdown', 0):.1f}%"), unsafe_allow_html=True)
        with c4:
            st.markdown(_metric_card("Win Rate", f"{m.get('win_rate', 0):.0f}%",
                        f"{m.get('n_trades', 0)} trades"), unsafe_allow_html=True)

        fig = bt.render_result(result)
        st.plotly_chart(fig, use_container_width=True)

        # Trades table
        if result.trades:
            trade_rows = [
                {
                    "Entry": t.entry_date.strftime("%Y-%m-%d"),
                    "Exit": t.exit_date.strftime("%Y-%m-%d") if t.exit_date else "Open",
                    "Dir": t.direction,
                    "Entry $": f"${t.entry_price:.2f}",
                    "Exit $": f"${t.exit_price:.2f}" if t.exit_price else "—",
                    "P&L": f"${t.pnl:+.2f}",
                    "P&L %": f"{t.pnl_pct:+.1f}%",
                }
                for t in result.trades
            ]
            with st.expander(f"Trade Log ({len(result.trades)} trades)"):
                st.dataframe(pd.DataFrame(trade_rows), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: PORTFOLIO
# ─────────────────────────────────────────────────────────────────────────────

def _tab_portfolio() -> None:
    pa = PortfolioAnalytics()

    symbols_input = st.text_input("Portfolio symbols (comma-separated)",
                                   "AAPL, MSFT, GOOGL, AMZN, JPM")
    symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

    method = st.radio("Optimization Method", ["Markowitz", "Black-Litterman"], horizontal=True)
    target = st.selectbox("Objective", ["max_sharpe", "min_vol", "max_return"],
                           index=0) if method == "Markowitz" else None

    views_input = {}
    if method == "Black-Litterman":
        st.markdown("**Your Views** (expected return per ticker)")
        for sym in symbols[:6]:
            v = st.number_input(f"{sym} expected return (%)", -50.0, 200.0, 0.0,
                                 key=f"bl_view_{sym}")
            if v != 0:
                views_input[sym] = v

    if st.button("Optimize Portfolio") and len(symbols) >= 2:
        with st.spinner("Optimizing…"):
            if method == "Markowitz":
                result = pa.markowitz_optimize(symbols, target=target)
            else:
                result = pa.black_litterman_optimize(symbols, views=views_input or None)

        if not result:
            st.error("Insufficient data to optimize.")
            return

        # Weights pie
        import plotly.express as px
        weights = result["weights"]
        fig_pie = px.pie(
            names=list(weights.keys()),
            values=list(weights.values()),
            title="Optimal Allocation",
            color_discrete_sequence=["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#ef4444", "#14b8a6"],
        )
        fig_pie.update_layout(paper_bgcolor=_C["bg"], font=dict(color=_C["text"]))

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(_metric_card("Expected Return", f"{result['exp_return']:.1f}%"), unsafe_allow_html=True)
        with c2:
            st.markdown(_metric_card("Expected Volatility", f"{result['exp_vol']:.1f}%"), unsafe_allow_html=True)
        with c3:
            st.markdown(_metric_card("Sharpe Ratio", f"{result['sharpe']:.2f}"), unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            fig_ef = pa.render_efficient_frontier(result, symbols)
            st.plotly_chart(fig_ef, use_container_width=True)

        # Risk metrics
        returns_df = pa.get_returns(symbols)
        if not returns_df.empty:
            risk = pa.portfolio_metrics(weights, returns_df)
            if risk:
                st.subheader("Risk Analysis")
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(_metric_card("VaR 95%", f"{risk['var_95']:.2f}%"), unsafe_allow_html=True)
                with c2: st.markdown(_metric_card("CVaR 95%", f"{risk['cvar_95']:.2f}%"), unsafe_allow_html=True)
                with c3: st.markdown(_metric_card("Max Drawdown", f"{risk['max_drawdown']:.1f}%"), unsafe_allow_html=True)
                with c4: st.markdown(_metric_card("Ann. Volatility", f"{risk['total_vol_ann']:.1f}%"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB: JOURNAL
# ─────────────────────────────────────────────────────────────────────────────

def _tab_journal() -> None:
    journal = TradeJournal()

    sub1, sub2 = st.tabs(["Add Trade", "Journal & Analytics"])

    with sub1:
        c1, c2, c3 = st.columns(3)
        with c1:
            j_sym = st.text_input("Symbol", "AAPL", key="jnl_sym").upper()
            j_dir = st.selectbox("Direction", ["Long", "Short"], key="jnl_dir")
            j_strategy = st.text_input("Strategy", key="jnl_strat")
        with c2:
            j_entry_date = st.date_input("Entry Date", key="jnl_entry_date")
            j_entry_price = st.number_input("Entry Price", 0.0, 100000.0, 0.0, key="jnl_ep")
            j_shares = st.number_input("Shares", 0.0, 100000.0, 0.0, key="jnl_shares")
        with c3:
            j_exit_date = st.date_input("Exit Date (optional)", key="jnl_exit_date", value=None)
            j_exit_price = st.number_input("Exit Price (0 = still open)", 0.0, 100000.0, 0.0, key="jnl_xp")
            j_rating = st.slider("Process Rating (1-5)", 1, 5, 3, key="jnl_rating")

        j_setup = st.selectbox("Setup Type", ["Breakout", "Pullback", "Mean Reversion", "Trend Follow",
                                               "Earnings Play", "Gap Fill", "Other"], key="jnl_setup")
        j_emotion = st.selectbox("Emotional State", ["Confident", "Neutral", "Fearful", "FOMO", "Greedy"], key="jnl_emo")
        j_tf = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d", "1w"], index=5, key="jnl_tf")
        j_notes = st.text_area("Notes / Thesis", key="jnl_notes", height=80)
        j_tags = st.text_input("Tags (comma-separated)", key="jnl_tags")

        if st.button("Add Journal Entry"):
            if j_entry_price > 0 and j_shares > 0:
                entry = JournalEntry(
                    entry_id=str(uuid.uuid4())[:8],
                    symbol=j_sym,
                    direction=j_dir,
                    entry_date=str(j_entry_date),
                    entry_price=j_entry_price,
                    exit_date=str(j_exit_date) if j_exit_date else None,
                    exit_price=j_exit_price if j_exit_price > 0 else None,
                    shares=j_shares,
                    strategy=j_strategy,
                    setup=j_setup,
                    timeframe=j_tf,
                    emotion=j_emotion,
                    rating=j_rating,
                    notes=j_notes,
                    tags=[t.strip() for t in j_tags.split(",") if t.strip()],
                )
                journal.add_entry(entry)
                st.success(f"Added journal entry for {j_sym}.")

    with sub2:
        df_j = journal.to_dataframe()
        if not df_j.empty:
            analytics = journal.get_analytics()
            if analytics:
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(_metric_card("Total P&L", f"${analytics['total_pnl']:+.2f}",
                            change_positive=analytics["total_pnl"] > 0), unsafe_allow_html=True)
                with c2: st.markdown(_metric_card("Win Rate", f"{analytics['win_rate']:.1f}%"), unsafe_allow_html=True)
                with c3: st.markdown(_metric_card("Profit Factor", f"{analytics['profit_factor']:.2f}"), unsafe_allow_html=True)
                with c4: st.markdown(_metric_card("Expectancy", f"${analytics['expectancy']:.2f}/trade",
                            change_positive=analytics["expectancy"] > 0), unsafe_allow_html=True)

                fig_j = journal.render_analytics_chart()
                st.plotly_chart(fig_j, use_container_width=True)

            st.dataframe(df_j, use_container_width=True)
            ReportExporter.download_button_csv(df_j, "trade_journal.csv")
        else:
            st.info("No journal entries yet. Add your first trade above.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: ALERTS
# ─────────────────────────────────────────────────────────────────────────────

def _tab_alerts(symbol: str) -> None:
    ae = AlertsEngine()

    sub1, sub2 = st.tabs(["Active Alerts", "Create Alert"])

    with sub2:
        c1, c2, c3 = st.columns(3)
        with c1:
            al_sym = st.text_input("Symbol", symbol, key="al_sym").upper()
            al_name = st.text_input("Alert Name", key="al_name")
        with c2:
            al_condition = st.selectbox("Condition Type", CONDITION_TYPES, key="al_cond")
            al_threshold = st.number_input("Threshold (price/level)", 0.0, key="al_thresh")
        with c3:
            al_period = st.number_input("Period (MA/RSI)", 1, 200, 14, key="al_period")
            al_logic = st.radio("Logic", ["ALL", "ANY"], horizontal=True, key="al_logic")

        if st.button("Create Alert") and al_sym:
            new_alert = AlertsEngine.build_simple_alert(
                al_sym, al_condition,
                threshold=al_threshold if al_threshold > 0 else None,
                period=int(al_period) if al_period > 0 else None,
                name=al_name or None,
            )
            new_alert.logic = al_logic
            ae.add_alert(new_alert)
            st.success(f"Alert created for {al_sym}.")

    with sub1:
        alerts = ae.alerts
        if not alerts:
            st.info("No alerts configured. Create one in the 'Create Alert' tab.")
            return

        if st.button("Check All Alerts Now"):
            with st.spinner("Checking alerts…"):
                triggered = ae.check_alerts()
            if triggered:
                for t in triggered:
                    st.warning(
                        f" **{t['name']}** triggered! {t['symbol']} @ ${t.get('price', 0):.2f} "
                        f"({t.get('change_pct', 0):+.2f}%)"
                    )
            else:
                st.success("No alerts triggered.")

        for alert in alerts:
            status_color = "#22c55e" if alert.get("active") else "#475569"
            conds = ", ".join(c.get("condition_type", "") for c in alert.get("conditions", []))
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(
                    f'<div style="background:#1a1a2e;border-left:3px solid {status_color};'
                    f'padding:10px;border-radius:6px;margin:4px 0">'
                    f'<b>{alert["name"]}</b> <span class="fa-tag">{alert["symbol"]}</span><br>'
                    f'<span style="color:#94a3b8;font-size:11px">{conds}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("Toggle", key=f"al_tog_{alert['alert_id']}"):
                    ae.toggle_alert(alert["alert_id"])
                    st.rerun()
            with col3:
                if st.button("Delete", key=f"al_del_{alert['alert_id']}"):
                    ae.remove_alert(alert["alert_id"])
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: WATCHLIST
# ─────────────────────────────────────────────────────────────────────────────

def _tab_watchlist() -> None:
    watchlist = st.session_state.fa_watchlist
    engine = ChartEngine()

    st.subheader(f"Watchlist ({len(watchlist)} symbols)")
    cols = st.columns(4)

    for i, sym in enumerate(watchlist):
        with cols[i % 4]:
            snap = DataFetcher.snapshot(sym)
            if snap:
                price = snap.get("price", 0)
                chg = snap.get("change_pct", 0)
                color = "#22c55e" if chg >= 0 else "#ef4444"
                sign = "+" if chg >= 0 else ""
                st.markdown(
                    f'<div style="background:#1a1a2e;border-radius:10px;padding:12px;margin:4px 0;'
                    f'border-top:2px solid {color}">'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<b style="color:#e2e8f0">{sym}</b>'
                    f'<span style="color:{color}">{sign}{chg:.2f}%</span>'
                    f'</div>'
                    f'<div style="font-size:20px;font-weight:700;color:#e2e8f0">${price:.2f}</div>'
                    f'<div style="font-size:11px;color:#94a3b8">{snap.get("name", sym)}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                df = DataFetcher.ohlcv(sym, "1d")
                if not df.empty:
                    mini = engine.mini_chart(df.iloc[-30:], color)
                    st.plotly_chart(mini, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────────────
# VOLUME PROFILE TAB
# ─────────────────────────────────────────────────────────────────────────────

def _tab_volume_profile(symbol: str, timeframe: str) -> None:
    vp = VolumeProfile()
    df = DataFetcher.ohlcv(symbol, timeframe)

    n_bins = st.slider("Profile Bins", 20, 80, 40)
    fig = vp.render_with_profile(df, symbol, n_bins)
    st.plotly_chart(fig, use_container_width=True)

    if not df.empty:
        profile = vp.compute_profile(df, n_bins)
        if profile:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(_metric_card("Point of Control (POC)", f"${profile['poc']:.2f}"), unsafe_allow_html=True)
            with c2:
                st.markdown(_metric_card("Value Area High", f"${profile['value_area_high']:.2f}"), unsafe_allow_html=True)
            with c3:
                st.markdown(_metric_card("Value Area Low", f"${profile['value_area_low']:.2f}"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render_financial_analysis_suite() -> None:
    """Main entry point — renders the complete Financial Analysis Suite UI."""
    _init_state()
    st.markdown(_CSS, unsafe_allow_html=True)
    _render_sidebar()

    symbol = st.session_state.fa_symbol
    timeframe = st.session_state.fa_timeframe

    st.markdown(f"## Financial Analysis Suite")

    tabs = st.tabs([
        "Charts",
        "Screener",
        "Fundamentals",
        "Market Heatmap",
        "Options Flow",
        "Sector Rotation",
        "Intermarket",
        "Seasonality",
        "Volume Profile",
        "Backtest Lab",
        "Portfolio",
        "Journal",
        "Alerts",
        "Watchlist",
    ])

    with tabs[0]:  _tab_charts(symbol, timeframe)
    with tabs[1]:  _tab_screener()
    with tabs[2]:  _tab_fundamentals(symbol)
    with tabs[3]:  _tab_heatmap()
    with tabs[4]:  _tab_options(symbol)
    with tabs[5]:  _tab_sector_rotation()
    with tabs[6]:  _tab_intermarket()
    with tabs[7]:  _tab_seasonality(symbol)
    with tabs[8]:  _tab_volume_profile(symbol, timeframe)
    with tabs[9]:  _tab_backtest(symbol, timeframe)
    with tabs[10]: _tab_portfolio()
    with tabs[11]: _tab_journal()
    with tabs[12]: _tab_alerts(symbol)
    with tabs[13]: _tab_watchlist()
