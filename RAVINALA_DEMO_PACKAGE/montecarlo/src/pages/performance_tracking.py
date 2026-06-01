"""
GenesiX Performance Tracking — v2.1
NAV tracking, rolling returns, benchmark comparison, calendar heatmap, attribution.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

from genesix.design_system import QUANTUM_DARK
from genesix.design_system.themes import apply_quantum_dark

apply_quantum_dark()

# ============================================================================
# SIDEBAR — PORTFOLIO CONFIGURATION
# ============================================================================

st.sidebar.markdown("## Performance Tracker")

DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
    "JPM", "JNJ", "XOM", "PG", "V", "UNH", "HD", "BAC",
]

selected_tickers = st.sidebar.multiselect(
    "Portfolio Tickers",
    DEFAULT_UNIVERSE,
    default=["AAPL", "MSFT", "GOOGL", "AMZN"],
)

if not selected_tickers:
    st.warning("Select at least one ticker in the sidebar.")
    st.stop()

# Weight scheme
weight_mode = st.sidebar.radio(
    "Weight Scheme", ["Equal Weight", "Custom Weights"], horizontal=True
)

weights: dict[str, float] = {}
if weight_mode == "Equal Weight":
    w = 1.0 / len(selected_tickers)
    weights = {t: w for t in selected_tickers}
else:
    remaining = 100.0
    for i, t in enumerate(selected_tickers):
        default_w = round(remaining / (len(selected_tickers) - i), 1)
        val = st.sidebar.slider(
            f"{t} (%)", 0.0, 100.0, min(default_w, remaining), 0.5, key=f"w_{t}"
        )
        weights[t] = val / 100
        remaining = max(0, remaining - val)

    total = sum(weights.values())
    if abs(total - 1.0) > 0.02:
        st.sidebar.warning(f"Weights sum to {total*100:.1f}% — should be 100%")

# Period & benchmark
period = st.sidebar.selectbox(
    "Lookback Period", ["1y", "2y", "3y", "5y", "10y", "max"], index=3
)
benchmark = st.sidebar.selectbox(
    "Benchmark", ["SPY", "QQQ", "IWM", "EEM", "AGG", "TLT"], index=0
)
initial_nav = st.sidebar.number_input(
    "Initial Investment ($)", value=10_000, min_value=1_000, step=1_000
)

run_btn = st.sidebar.button("Run Analysis", use_container_width=True, type="primary")

# ============================================================================
# HEADER
# ============================================================================

st.markdown("# Performance Tracking")
st.markdown("Buy-and-hold NAV simulation, rolling returns, calendar heatmap and risk attribution.")

# ============================================================================
# RUN TRACKER
# ============================================================================

if run_btn:
    from genesix.performance_engine.tracker import PerformanceTracker

    with st.spinner("Fetching data and computing analytics ..."):
        tracker = PerformanceTracker(
            tickers=selected_tickers,
            weights=weights,
            benchmark=benchmark,
            period=period,
            initial_nav=initial_nav,
        )
        snap = tracker.run()

    if snap is None:
        st.error("Failed to fetch price data. Check tickers and try again.")
        st.stop()

    st.session_state["perf_snapshot"] = snap
    st.session_state["perf_tickers"] = selected_tickers
    st.session_state["perf_weights"] = weights
    st.session_state["perf_benchmark"] = benchmark

# ============================================================================
# DISPLAY RESULTS
# ============================================================================

if "perf_snapshot" not in st.session_state:
    st.info("Configure your portfolio in the sidebar and click **Run Analysis**.")
    st.stop()

snap = st.session_state["perf_snapshot"]
tickers_used = st.session_state["perf_tickers"]
weights_used = st.session_state["perf_weights"]

# ---- TOP METRICS BAR ----------------------------------------------------
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Annual Return", f"{snap.annual_return:+.2f}%")
c2.metric("Annual Vol", f"{snap.annual_volatility:.2f}%")
c3.metric("Sharpe", f"{snap.sharpe_ratio:.2f}")
c4.metric("Sortino", f"{snap.sortino_ratio:.2f}")
c5.metric("Max Drawdown", f"{snap.max_drawdown:.2f}%")
c6.metric("Alpha", f"{snap.alpha:+.2f}%")

st.divider()

# ---- TABS ----------------------------------------------------------------
tabs = st.tabs([
    "Equity Curve",
    "Rolling Returns",
    "Calendar Heatmap",
    "Drawdown",
    "Risk Metrics",
    "Attribution",
])

_PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    plot_bgcolor=QUANTUM_DARK["bg_1"],
    paper_bgcolor=QUANTUM_DARK["bg_1"],
    font=dict(color=QUANTUM_DARK["text_0"]),
    hovermode="x unified",
    margin=dict(l=40, r=20, t=40, b=30),
)

# ========== TAB 1: EQUITY CURVE ===========================================
with tabs[0]:
    # Normalise to 100 for comparison
    nav_norm = snap.nav / snap.nav.iloc[0] * 100
    bench_norm = snap.benchmark_nav / snap.benchmark_nav.iloc[0] * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nav_norm.index, y=nav_norm.values,
        name="Portfolio",
        line=dict(color=QUANTUM_DARK["accent_primary"], width=2),
    ))
    fig.add_trace(go.Scatter(
        x=bench_norm.index, y=bench_norm.values,
        name=st.session_state.get("perf_benchmark", "SPY"),
        line=dict(color=QUANTUM_DARK["accent_info"], width=2, dash="dash"),
    ))
    fig.update_layout(
        title="Portfolio vs Benchmark (Indexed to 100)",
        yaxis_title="Value",
        height=480,
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Final NAV cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Final NAV", f"${snap.nav.iloc[-1]:,.0f}")
    c2.metric("Total Return", f"{(snap.nav.iloc[-1]/snap.nav.iloc[0]-1)*100:+.2f}%")
    c3.metric("Beta", f"{snap.beta:.3f}")
    c4.metric("Win Rate", f"{snap.win_rate*100:.1f}%")

# ========== TAB 2: ROLLING RETURNS ========================================
with tabs[1]:
    fig = go.Figure()
    for name, series, color in [
        ("1M", snap.rolling_1m, QUANTUM_DARK["accent_primary"]),
        ("3M", snap.rolling_3m, QUANTUM_DARK["accent_info"]),
        ("6M", snap.rolling_6m, QUANTUM_DARK["accent_premium"]),
        ("1Y", snap.rolling_1y, QUANTUM_DARK["text_0"]),
    ]:
        valid = series.dropna()
        fig.add_trace(go.Scatter(
            x=valid.index, y=valid.values * 100,
            name=f"{name} Rolling",
            line=dict(color=color),
        ))

    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.2)")
    fig.update_layout(
        title="Rolling Annualised Returns",
        yaxis_title="Return (%)",
        height=480,
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Rolling Volatility
    vol_63 = snap.daily_returns.rolling(63).std() * np.sqrt(252) * 100
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=vol_63.index, y=vol_63.values,
        name="63-day Rolling Vol",
        fill="tozeroy",
        line=dict(color=QUANTUM_DARK["accent_primary"]),
    ))
    fig2.update_layout(
        title="Rolling Volatility (63-day)",
        yaxis_title="Volatility (%)",
        height=350,
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ========== TAB 3: CALENDAR HEATMAP =======================================
with tabs[2]:
    cal = snap.calendar_returns
    # Separate YTD from months for the heatmap
    month_cols = [c for c in cal.columns if c != "YTD"]
    heatmap_data = cal[month_cols]

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns.tolist(),
        y=[str(y) for y in heatmap_data.index],
        colorscale="RdYlGn",
        zmid=0,
        text=[[f"{v:.1f}%" if not pd.isna(v) else "" for v in row]
              for row in heatmap_data.values],
        texttemplate="%{text}",
        textfont=dict(size=11),
        colorbar=dict(title="Return (%)"),
    ))
    fig.update_layout(
        title="Monthly Returns by Year",
        height=max(250, 50 * len(heatmap_data)),
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

    # YTD summary
    if "YTD" in cal.columns:
        st.markdown("**Year-to-Date Returns**")
        ytd_df = cal[["YTD"]].rename(columns={"YTD": "YTD Return (%)"})
        st.dataframe(ytd_df.style.format("{:.2f}"), use_container_width=True)

# ========== TAB 4: DRAWDOWN ===============================================
with tabs[3]:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=snap.drawdown_series.index,
        y=snap.drawdown_series.values * 100,
        fill="tozeroy",
        line=dict(color=QUANTUM_DARK["accent_negative"], width=1),
        name="Drawdown",
    ))
    fig.update_layout(
        title="Underwater Chart (Peak-to-Trough Drawdown)",
        yaxis_title="Drawdown (%)",
        height=400,
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Max Drawdown", f"{snap.max_drawdown:.2f}%")
    c2.metric("Worst Day", f"{snap.worst_day:.2f}%")
    c3.metric("Best Day", f"{snap.best_day:+.2f}%")

# ========== TAB 5: RISK METRICS ==========================================
with tabs[4]:
    st.markdown("### Risk & Performance Summary")

    metrics_table = pd.DataFrame({
        "Metric": [
            "Annual Return", "Annual Volatility", "Sharpe Ratio",
            "Sortino Ratio", "Calmar Ratio", "Max Drawdown",
            "VaR (95%)", "CVaR (95%)", "Beta",
            "Alpha", "Tracking Error", "Information Ratio",
            "Skewness", "Excess Kurtosis", "Win Rate",
        ],
        "Value": [
            f"{snap.annual_return:+.2f}%",
            f"{snap.annual_volatility:.2f}%",
            f"{snap.sharpe_ratio:.3f}",
            f"{snap.sortino_ratio:.3f}",
            f"{snap.calmar_ratio:.3f}",
            f"{snap.max_drawdown:.2f}%",
            f"{snap.var_95:.3f}%",
            f"{snap.cvar_95:.3f}%",
            f"{snap.beta:.3f}",
            f"{snap.alpha:+.2f}%",
            f"{snap.tracking_error:.2f}%",
            f"{snap.information_ratio:.3f}",
            f"{snap.skewness:.3f}",
            f"{snap.kurtosis:.3f}",
            f"{snap.win_rate*100:.1f}%",
        ],
    })
    st.dataframe(metrics_table, use_container_width=True, hide_index=True)

    # Return distribution histogram
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=snap.daily_returns.values * 100,
        nbinsx=80,
        marker_color=QUANTUM_DARK["accent_primary"],
        opacity=0.7,
        name="Daily Returns",
    ))
    fig.add_vline(
        x=snap.var_95, line_dash="dash",
        line_color=QUANTUM_DARK["accent_negative"],
        annotation_text=f"VaR 95%: {snap.var_95:.2f}%",
    )
    fig.update_layout(
        title="Daily Returns Distribution",
        xaxis_title="Daily Return (%)",
        yaxis_title="Frequency",
        height=400,
        **_PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

# ========== TAB 6: ATTRIBUTION ===========================================
with tabs[5]:
    st.markdown("### Per-Instrument Attribution (Buy-and-Hold)")

    attr_rows = []
    for t in tickers_used:
        if t in snap.instrument_returns:
            attr_rows.append({
                "Ticker": t,
                "Weight": f"{weights_used.get(t, 0)*100:.1f}%",
                "Total Return": f"{snap.instrument_returns[t]:+.2f}%",
                "Contribution": f"{snap.instrument_contribution.get(t, 0):+.2f}%",
            })
    attr_df = pd.DataFrame(attr_rows)
    st.dataframe(attr_df, use_container_width=True, hide_index=True)

    # Bar chart
    if attr_rows:
        fig = go.Figure(data=[go.Bar(
            x=[r["Ticker"] for r in attr_rows],
            y=[snap.instrument_contribution.get(r["Ticker"], 0) for r in attr_rows],
            marker_color=[
                QUANTUM_DARK["accent_positive"]
                if snap.instrument_contribution.get(r["Ticker"], 0) >= 0
                else QUANTUM_DARK["accent_negative"]
                for r in attr_rows
            ],
        )])
        fig.update_layout(
            title="Weighted Return Contribution",
            yaxis_title="Contribution (%)",
            height=380,
            **_PLOTLY_LAYOUT,
        )
        st.plotly_chart(fig, use_container_width=True)
