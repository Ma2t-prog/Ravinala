"""
UCITS ETF Explorer — full Streamlit page.
Called from app.py as: from etf_explorer import render_etf_explorer; render_etf_explorer()
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from etf_data_fetcher import fetch_etf_cached, ETFData
from etf_calculations import (
    fmt_pct, colour_pct, normalise_prices, rolling_drawdown,
)
from etf_isin_resolver import UCITS_ISIN_MAP
from etf_benchmark_db import BENCHMARK_DB

# ── Design tokens (match main app) ───────────────────────────────────────────
_BG      = "#0A0A0F"
_BG_S    = "#0D0D15"
_BG_CARD = "#13131E"
_ACCENT  = "#00D9A6"
_BLUE    = "#3B82F6"
_AMBER   = "#F59E0B"
_RED     = "#EF4444"
_BORDER  = "rgba(255,255,255,0.055)"
_TEXT    = "#E2E8F0"
_MUTED   = "#6B7280"

_CHART_LAYOUT = dict(
    paper_bgcolor=_BG,
    plot_bgcolor=_BG_S,
    font=dict(family="Inter, sans-serif", color=_TEXT, size=12),
    margin=dict(l=0, r=0, t=28, b=0),
    xaxis=dict(
        showgrid=True, gridcolor="rgba(255,255,255,0.04)",
        zeroline=False, showline=False,
    ),
    yaxis=dict(
        showgrid=True, gridcolor="rgba(255,255,255,0.04)",
        zeroline=False, showline=False,
    ),
)

# ── Quick-access chips ────────────────────────────────────────────────────────
_QUICK_CHIPS = [
    ("iShares MSCI World", "IE00B4L5Y983"),
    ("iShares Core S&P 500", "IE00B5BMR087"),
    ("Vanguard FTSE All-World", "IE00B3RBWM25"),
    ("iShares Core EM IMI", "IE00BKM4GZ66"),
    ("Amundi MSCI World", "LU1681043599"),
    ("iShares NASDAQ-100", "IE00B53SZB19"),
    ("iShares Global Agg Bond", "IE00B3F81409"),
    ("Xtrackers MSCI World", "LU0274208692"),
]

# ── CSS ───────────────────────────────────────────────────────────────────────
_CSS = f"""
<style>
/* ── ETF Explorer layout ─────────────────────────────────── */
.etf-search-wrap {{
    display: flex; gap: 12px; align-items: center; margin-bottom: 24px;
}}
.etf-chips {{
    display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 28px;
}}
.etf-chip {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 14px; border-radius: 20px; cursor: pointer;
    font-size: 0.78rem; font-weight: 500; letter-spacing: 0.01em;
    background: rgba(255,255,255,0.04);
    border: 1px solid {_BORDER};
    color: {_TEXT}; transition: all 0.18s ease;
}}
.etf-chip:hover {{
    background: rgba(0,217,166,0.10);
    border-color: rgba(0,217,166,0.30);
    color: {_ACCENT};
}}
/* ── Hero band ───────────────────────────────────────────── */
.etf-hero {{
    background: linear-gradient(135deg, #0F1628 0%, #0A0A0F 60%);
    border: 1px solid {_BORDER};
    border-radius: 14px; padding: 28px 32px; margin-bottom: 24px;
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: 24px;
}}
.etf-hero-name {{
    font-size: 1.45rem; font-weight: 700; color: {_TEXT}; line-height: 1.2;
}}
.etf-hero-ticker {{
    font-size: 0.82rem; font-family: "JetBrains Mono", monospace;
    color: {_ACCENT}; letter-spacing: 0.06em; margin-top: 4px;
}}
.etf-hero-meta {{
    display: flex; flex-wrap: wrap; gap: 18px; margin-top: 14px;
}}
.etf-meta-item {{
    display: flex; flex-direction: column; gap: 2px;
}}
.etf-meta-label {{
    font-size: 0.68rem; text-transform: uppercase;
    letter-spacing: 0.08em; color: {_MUTED};
}}
.etf-meta-value {{
    font-size: 0.9rem; font-weight: 600; color: {_TEXT};
}}
.etf-badge {{
    display: inline-flex; align-items: center;
    padding: 3px 10px; border-radius: 12px; font-size: 0.72rem;
    font-weight: 600; letter-spacing: 0.04em;
    background: rgba(0,217,166,0.12); color: {_ACCENT};
    border: 1px solid rgba(0,217,166,0.22);
}}
/* ── Performance grid ────────────────────────────────────── */
.perf-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 10px; margin-bottom: 24px;
}}
.perf-cell {{
    background: rgba(255,255,255,0.02); border: 1px solid {_BORDER};
    border-radius: 10px; padding: 12px 10px; text-align: center;
}}
.perf-label {{
    font-size: 0.68rem; text-transform: uppercase;
    letter-spacing: 0.07em; color: {_MUTED}; margin-bottom: 6px;
}}
.perf-value {{
    font-size: 1.05rem; font-weight: 700;
    font-family: "JetBrains Mono", monospace;
}}
/* ── Section headers ─────────────────────────────────────── */
.etf-section-header {{
    font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em;
    color: {_MUTED}; border-bottom: 1px solid {_BORDER};
    padding-bottom: 8px; margin: 28px 0 16px;
}}
/* ── Risk grid ───────────────────────────────────────────── */
.risk-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px; margin-bottom: 24px;
}}
.risk-card {{
    background: {_BG_CARD}; border: 1px solid {_BORDER};
    border-radius: 12px; padding: 14px 16px;
}}
.risk-card-label {{
    font-size: 0.7rem; text-transform: uppercase;
    letter-spacing: 0.07em; color: {_MUTED}; margin-bottom: 6px;
}}
.risk-card-value {{
    font-size: 1.1rem; font-weight: 700;
    font-family: "JetBrains Mono", monospace; color: {_TEXT};
}}
/* ── Holdings table ──────────────────────────────────────── */
.holding-row {{
    display: flex; align-items: center; gap: 10px;
    padding: 9px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
}}
.holding-rank {{
    width: 24px; font-size: 0.72rem; color: {_MUTED};
    font-family: "JetBrains Mono", monospace; text-align: right;
}}
.holding-name {{ flex: 1; font-size: 0.88rem; color: {_TEXT}; }}
.holding-bar-wrap {{ width: 100px; }}
.holding-bar-bg {{
    height: 5px; background: rgba(255,255,255,0.06);
    border-radius: 3px; overflow: hidden;
}}
.holding-bar-fill {{
    height: 100%; border-radius: 3px;
    background: linear-gradient(90deg, {_ACCENT}, {_BLUE});
}}
.holding-pct {{
    width: 52px; text-align: right;
    font-size: 0.82rem; font-weight: 600;
    font-family: "JetBrains Mono", monospace; color: {_TEXT};
}}
/* ── Error / warning ─────────────────────────────────────── */
.etf-error {{
    background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.22);
    border-radius: 12px; padding: 18px 22px; color: #FCA5A5;
    font-size: 0.9rem;
}}
</style>
"""

# ── Plotly helpers ────────────────────────────────────────────────────────────

def _price_chart(data: ETFData, period: str = "1Y") -> go.Figure:
    prices = data.prices
    bench = data.benchmark_prices

    period_map = {
        "1M": 21, "3M": 63, "6M": 126, "1Y": 252,
        "3Y": 756, "5Y": 1260, "MAX": len(prices),
    }
    n = period_map.get(period, 252)
    prices = prices.iloc[-n:] if len(prices) > n else prices
    if len(bench) > n:
        bench = bench.iloc[-n:]

    # Rebase to 100
    p_norm = normalise_prices(prices)
    fig = go.Figure()

    # ETF line
    fig.add_trace(go.Scatter(
        x=p_norm.index, y=p_norm.values,
        name=data.ticker,
        line=dict(color=_ACCENT, width=2),
        fill="tozeroy",
        fillcolor="rgba(0,217,166,0.04)",
        hovertemplate="%{x|%d %b %Y}<br><b>%{y:.1f}</b><extra></extra>",
    ))

    # Benchmark line
    if bench is not None and len(bench) >= 5:
        bm_common = bench[bench.index.isin(prices.index)]
        if len(bm_common) >= 5:
            bm_norm = normalise_prices(bm_common)
            fig.add_trace(go.Scatter(
                x=bm_norm.index, y=bm_norm.values,
                name=data.benchmark_name or "Benchmark",
                line=dict(color=_BLUE, width=1.5, dash="dot"),
                hovertemplate="%{x|%d %b %Y}<br>%{y:.1f}<extra></extra>",
            ))

    layout = {**_CHART_LAYOUT}
    layout["height"] = 320
    layout["legend"] = dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="right", x=1, font=dict(size=11),
    )
    layout["yaxis"]["tickformat"] = ".0f"
    fig.update_layout(**layout)
    return fig


def _drawdown_chart(data: ETFData, period: str = "1Y") -> go.Figure:
    prices = data.prices
    period_map = {
        "1M": 21, "3M": 63, "6M": 126, "1Y": 252,
        "3Y": 756, "5Y": 1260, "MAX": len(prices),
    }
    n = period_map.get(period, 252)
    prices = prices.iloc[-n:] if len(prices) > n else prices
    dd = rolling_drawdown(prices) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.values,
        fill="tozeroy",
        fillcolor="rgba(239,68,68,0.12)",
        line=dict(color=_RED, width=1.5),
        hovertemplate="%{x|%d %b %Y}<br>%{y:.2f} %<extra></extra>",
        name="Drawdown",
    ))
    layout = {**_CHART_LAYOUT}
    layout["height"] = 180
    layout["showlegend"] = False
    layout["yaxis"]["ticksuffix"] = " %"
    fig.update_layout(**layout)
    return fig


def _allocation_chart(weights: dict[str, float], title: str, max_items: int = 12) -> go.Figure:
    if not weights:
        return None
    sorted_items = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:max_items]
    labels = [x[0] for x in sorted_items]
    values = [x[1] * 100 for x in sorted_items]

    colors = px.colors.sequential.Teal[::-1]
    while len(colors) < len(labels):
        colors += colors

    fig = go.Figure(go.Bar(
        y=labels[::-1], x=values[::-1],
        orientation="h",
        marker=dict(color=colors[:len(labels)][::-1], opacity=0.85),
        hovertemplate="%{y}: <b>%{x:.1f} %</b><extra></extra>",
    ))
    layout = {**_CHART_LAYOUT}
    layout["height"] = max(200, 28 * len(labels) + 40)
    layout["xaxis"]["ticksuffix"] = " %"
    layout["showlegend"] = False
    layout["margin"] = dict(l=0, r=0, t=0, b=0)
    fig.update_layout(**layout)
    return fig


# ── Section renderers ─────────────────────────────────────────────────────────

def _render_hero(data: ETFData) -> None:
    aum_str = (
        f"${data.aum_usd:,.0f} M" if data.aum_usd else "—"
    )
    nav_str = (
        f"{data.nav:,.2f} {data.currency}" if data.nav else "—"
    )
    ter_str = f"{data.ter:.2f} %" if data.ter else "—"
    inception_str = data.inception_date[:10] if data.inception_date else "—"

    badge_html = ""
    if data.ucits:
        badge_html = '<span class="etf-badge">UCITS</span>'
    if data.distribution:
        badge_html += f'&nbsp;<span class="etf-badge" style="background:rgba(59,130,246,0.12);color:{_BLUE};border-color:rgba(59,130,246,0.22);">{data.distribution}</span>'

    st.markdown(f"""
<div class="etf-hero">
  <div style="flex:1;min-width:200px">
    <div class="etf-hero-name">{data.name or data.ticker}</div>
    <div class="etf-hero-ticker">{data.ticker} &nbsp;·&nbsp; {data.isin or "—"}</div>
    <div style="margin-top:10px">{badge_html}</div>
    <div class="etf-hero-meta">
      <div class="etf-meta-item">
        <span class="etf-meta-label">Issuer</span>
        <span class="etf-meta-value">{data.issuer or "—"}</span>
      </div>
      <div class="etf-meta-item">
        <span class="etf-meta-label">Asset Class</span>
        <span class="etf-meta-value">{data.asset_class or "—"}</span>
      </div>
      <div class="etf-meta-item">
        <span class="etf-meta-label">Region</span>
        <span class="etf-meta-value">{data.region or "—"}</span>
      </div>
      <div class="etf-meta-item">
        <span class="etf-meta-label">Currency</span>
        <span class="etf-meta-value">{data.currency or "—"}</span>
      </div>
      <div class="etf-meta-item">
        <span class="etf-meta-label">Domicile</span>
        <span class="etf-meta-value">{data.domicile or "IE / LU"}</span>
      </div>
    </div>
  </div>
  <div style="text-align:right;min-width:160px">
    <div style="font-size:1.6rem;font-weight:800;font-family:'JetBrains Mono',monospace;color:{_TEXT}">{nav_str}</div>
    <div style="font-size:0.72rem;color:{_MUTED};margin-top:2px">Latest NAV / Price</div>
    <div style="margin-top:14px;display:flex;flex-direction:column;gap:6px;align-items:flex-end">
      <div class="etf-meta-item" style="align-items:flex-end">
        <span class="etf-meta-label">AUM</span>
        <span class="etf-meta-value">{aum_str}</span>
      </div>
      <div class="etf-meta-item" style="align-items:flex-end">
        <span class="etf-meta-label">TER</span>
        <span class="etf-meta-value" style="color:{_AMBER}">{ter_str}</span>
      </div>
      <div class="etf-meta-item" style="align-items:flex-end">
        <span class="etf-meta-label">Inception</span>
        <span class="etf-meta-value">{inception_str}</span>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


def _render_performance(data: ETFData) -> None:
    p = data.performance
    periods = [
        ("1D", p.d1), ("1W", p.w1), ("1M", p.m1),
        ("3M", p.m3), ("6M", p.m6), ("YTD", p.ytd),
        ("1Y", p.y1), ("3Y", p.y3), ("5Y", p.y5),
    ]
    cells = ""
    for label, val in periods:
        colour = colour_pct(val)
        cells += f"""
<div class="perf-cell">
  <div class="perf-label">{label}</div>
  <div class="perf-value" style="color:{colour}">{fmt_pct(val, 2)}</div>
</div>"""
    st.markdown(f'<div class="perf-grid">{cells}</div>', unsafe_allow_html=True)


def _render_price_chart(data: ETFData) -> None:
    periods = ["1M", "3M", "6M", "1Y", "3Y", "5Y", "MAX"]
    sel = st.radio(
        "Period", periods, index=3,
        horizontal=True, key="etf_period",
        label_visibility="collapsed",
    )
    fig = _price_chart(data, sel)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # Drawdown sub-chart
    st.markdown(
        '<div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;'
        f'color:{_MUTED};margin-bottom:6px">Drawdown from Peak</div>',
        unsafe_allow_html=True,
    )
    fig_dd = _drawdown_chart(data, sel)
    st.plotly_chart(fig_dd, width="stretch", config={"displayModeBar": False})


def _render_risk(data: ETFData) -> None:
    r = data.risk
    t = data.tracking

    def _card(label: str, value: str, colour: str = _TEXT) -> str:
        return f"""
<div class="risk-card">
  <div class="risk-card-label">{label}</div>
  <div class="risk-card-value" style="color:{colour}">{value}</div>
</div>"""

    def _v(val, suffix="", decimals=2, pct=False):
        if val is None:
            return "—"
        if pct:
            return fmt_pct(val, decimals)
        return f"{val:.{decimals}f}{suffix}"

    vol_col = _AMBER if (r.volatility_1y or 0) > 0.15 else _TEXT
    dd_col = _RED if (r.max_drawdown or 0) < -0.20 else _AMBER

    cards_html = (
        _card("Volatility 1Y", _v(r.volatility_1y, " %", 1, pct=True), vol_col) +
        _card("Volatility 3Y", _v(r.volatility_3y, " %", 1, pct=True), vol_col) +
        _card("Sharpe 1Y", _v(r.sharpe_1y, "", 2)) +
        _card("Sharpe 3Y", _v(r.sharpe_3y, "", 2)) +
        _card("Max Drawdown", _v(r.max_drawdown, " %", 1, pct=True), dd_col) +
        _card("Beta", _v(r.beta, "", 2)) +
        _card("Correlation", _v(r.correlation, "", 2))
    )
    if data.benchmark_name:
        cards_html += (
            _card("Tracking Diff.", _v(t.tracking_difference, " %", 2, pct=True)) +
            _card("Tracking Error", _v(t.tracking_error, " %", 2, pct=True)) +
            _card("Info Ratio", _v(t.information_ratio, "", 2))
        )

    st.markdown(f'<div class="risk-grid">{cards_html}</div>', unsafe_allow_html=True)

    # Drawdown dates
    if r.max_drawdown_start and r.max_drawdown_end:
        st.markdown(
            f'<div style="font-size:0.78rem;color:{_MUTED}">Max drawdown: '
            f'<b style="color:{_TEXT}">{r.max_drawdown_start}</b> → '
            f'<b style="color:{_TEXT}">{r.max_drawdown_end}</b></div>',
            unsafe_allow_html=True,
        )


def _render_benchmark(data: ETFData) -> None:
    if not data.benchmark_name:
        st.markdown(
            f'<div style="color:{_MUTED};font-size:0.85rem">No benchmark mapped for this ETF.</div>',
            unsafe_allow_html=True,
        )
        return

    bm_info = BENCHMARK_DB.get(data.benchmark_name, {})

    cols = st.columns([2, 1])
    with cols[0]:
        st.markdown(f"""
<div style="background:{_BG_CARD};border:1px solid {_BORDER};border-radius:12px;padding:18px 20px">
  <div style="font-size:1.05rem;font-weight:700;color:{_TEXT};margin-bottom:6px">{data.benchmark_name}</div>
  <div style="font-size:0.83rem;color:{_MUTED};line-height:1.55">{bm_info.get('description','')}</div>
  <div style="display:flex;gap:20px;margin-top:14px;flex-wrap:wrap">
    <div><div style="font-size:0.67rem;text-transform:uppercase;letter-spacing:.07em;color:{_MUTED}">Asset Class</div>
         <div style="font-size:0.87rem;font-weight:600;color:{_TEXT}">{bm_info.get('asset_class','—')}</div></div>
    <div><div style="font-size:0.67rem;text-transform:uppercase;letter-spacing:.07em;color:{_MUTED}">Region</div>
         <div style="font-size:0.87rem;font-weight:600;color:{_TEXT}">{bm_info.get('region','—')}</div></div>
    <div><div style="font-size:0.67rem;text-transform:uppercase;letter-spacing:.07em;color:{_MUTED}">Constituents</div>
         <div style="font-size:0.87rem;font-weight:600;color:{_TEXT}">{bm_info.get('constituents','—'):,}</div></div>
    <div><div style="font-size:0.67rem;text-transform:uppercase;letter-spacing:.07em;color:{_MUTED}">Currency</div>
         <div style="font-size:0.87rem;font-weight:600;color:{_TEXT}">{bm_info.get('currency','—')}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

    with cols[1]:
        t = data.tracking
        if t.tracking_difference is not None:
            td_colour = _ACCENT if abs(t.tracking_difference) < 0.005 else _AMBER
            st.markdown(f"""
<div style="background:{_BG_CARD};border:1px solid {_BORDER};border-radius:12px;padding:18px 20px">
  <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;color:{_MUTED};margin-bottom:10px">Tracking vs Benchmark</div>
  <div style="display:flex;flex-direction:column;gap:10px">
    <div>
      <div style="font-size:0.68rem;color:{_MUTED}">Tracking Difference (ann.)</div>
      <div style="font-size:1.15rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:{td_colour}">{fmt_pct(t.tracking_difference)}</div>
    </div>
    <div>
      <div style="font-size:0.68rem;color:{_MUTED}">Tracking Error (ann.)</div>
      <div style="font-size:1.15rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:{_TEXT}">{fmt_pct(t.tracking_error)}</div>
    </div>
    <div>
      <div style="font-size:0.68rem;color:{_MUTED}">Information Ratio</div>
      <div style="font-size:1.15rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:{_TEXT}">{"—" if t.information_ratio is None else f"{t.information_ratio:.2f}"}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


def _render_holdings(data: ETFData) -> None:
    if not data.holdings:
        st.markdown(
            f'<div style="color:{_MUTED};font-size:0.85rem">Holdings data not available via free tier. '
            'Set FMP_API_KEY for detailed holdings.</div>',
            unsafe_allow_html=True,
        )
        return

    max_w = max((h.get("weight", 0) for h in data.holdings), default=1) or 1

    rows_html = ""
    for i, h in enumerate(data.holdings[:15], 1):
        name = h.get("name", "—")
        weight = h.get("weight", 0) or 0
        bar_pct = weight / max_w * 100
        rows_html += f"""
<div class="holding-row">
  <div class="holding-rank">{i}</div>
  <div class="holding-name">{name}</div>
  <div class="holding-bar-wrap">
    <div class="holding-bar-bg">
      <div class="holding-bar-fill" style="width:{bar_pct:.1f}%"></div>
    </div>
  </div>
  <div class="holding-pct">{weight:.2f} %</div>
</div>"""

    st.markdown(rows_html, unsafe_allow_html=True)


def _render_allocations(data: ETFData) -> None:
    has_sector = bool(data.sector_weights)
    has_country = bool(data.country_weights)

    if not has_sector and not has_country:
        st.markdown(
            f'<div style="color:{_MUTED};font-size:0.85rem">Allocation data not available '
            'for this ETF via free tier.</div>',
            unsafe_allow_html=True,
        )
        return

    cols = st.columns(2 if (has_sector and has_country) else 1)
    if has_sector:
        with cols[0]:
            st.markdown(
                f'<div style="font-size:0.8rem;font-weight:600;color:{_TEXT};margin-bottom:8px">Sector Allocation</div>',
                unsafe_allow_html=True,
            )
            fig = _allocation_chart(data.sector_weights, "Sectors")
            if fig:
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    if has_country:
        idx = 1 if has_sector else 0
        with cols[idx]:
            st.markdown(
                f'<div style="font-size:0.8rem;font-weight:600;color:{_TEXT};margin-bottom:8px">Country Allocation</div>',
                unsafe_allow_html=True,
            )
            fig = _allocation_chart(data.country_weights, "Countries")
            if fig:
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _render_fund_facts(data: ETFData) -> None:
    facts = {
        "Full Name": data.name,
        "ISIN": data.isin or "—",
        "Ticker (Yahoo)": data.ticker,
        "Issuer / Fund Family": data.issuer or "—",
        "Currency": data.currency,
        "Domicile": data.domicile or "Ireland (IE) / Luxembourg (LU)",
        "Inception Date": data.inception_date[:10] if data.inception_date else "—",
        "Replication": data.replication or "Physical / Optimised",
        "Distribution": data.distribution or "—",
        "Benchmark": data.benchmark_name or "—",
        "Total Expense Ratio": f"{data.ter:.2f} %" if data.ter else "—",
        "AUM": f"${data.aum_usd:,.0f} M" if data.aum_usd else "—",
        "UCITS Compliant": "Yes",
        "Data Source": data.source,
    }
    rows = ""
    for k, v in facts.items():
        rows += f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04)">
  <span style="font-size:0.82rem;color:{_MUTED}">{k}</span>
  <span style="font-size:0.85rem;font-weight:600;color:{_TEXT};text-align:right;max-width:60%">{v}</span>
</div>"""
    st.markdown(
        f'<div style="background:{_BG_CARD};border:1px solid {_BORDER};border-radius:12px;padding:16px 20px">'
        + rows + "</div>",
        unsafe_allow_html=True,
    )


# ── Skeleton loader ───────────────────────────────────────────────────────────

def _skeleton() -> None:
    st.markdown(f"""
<style>
@keyframes shimmer {{
  0%   {{ background-position: -200% 0; }}
  100% {{ background-position:  200% 0; }}
}}
.skel {{
    height: 18px; border-radius: 6px; margin-bottom: 10px;
    background: linear-gradient(90deg,
        rgba(255,255,255,0.04) 25%,
        rgba(255,255,255,0.08) 50%,
        rgba(255,255,255,0.04) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.4s infinite;
}}
</style>
<div class="skel" style="width:60%;height:32px"></div>
<div class="skel" style="width:40%"></div>
<div class="skel" style="width:100%;height:240px;margin-top:16px"></div>
<div style="display:flex;gap:12px;margin-top:16px">
  <div class="skel" style="flex:1;height:80px"></div>
  <div class="skel" style="flex:1;height:80px"></div>
  <div class="skel" style="flex:1;height:80px"></div>
  <div class="skel" style="flex:1;height:80px"></div>
</div>
""", unsafe_allow_html=True)


# ── Main page ─────────────────────────────────────────────────────────────────

def render_etf_explorer() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<h2 style="font-size:1.55rem;font-weight:700;color:{_TEXT};margin-bottom:4px">'
        f'<span style="color:{_ACCENT}">◈</span> UCITS ETF Explorer</h2>'
        f'<p style="font-size:0.85rem;color:{_MUTED};margin-bottom:24px">'
        'Search any UCITS ETF by ISIN or Yahoo Finance ticker for full analytics.</p>',
        unsafe_allow_html=True,
    )

    # ── Search bar ────────────────────────────────────────────────────────────
    col_inp, col_btn = st.columns([5, 1])
    with col_inp:
        query = st.text_input(
            "search",
            value=st.session_state.get("etf_query", ""),
            placeholder="Enter ISIN (e.g. IE00B4L5Y983) or ticker (e.g. IWDA.AS)",
            label_visibility="collapsed",
            key="etf_search_input",
        )
    with col_btn:
        search_clicked = st.button("Search", type="primary", width="stretch")

    # ── Quick-access chips ────────────────────────────────────────────────────
    st.markdown('<div class="etf-chips">', unsafe_allow_html=True)
    chip_cols = st.columns(len(_QUICK_CHIPS))
    for i, (label, isin) in enumerate(_QUICK_CHIPS):
        with chip_cols[i]:
            if st.button(label, key=f"chip_{isin}", width="stretch"):
                st.session_state["etf_query"] = isin
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Determine final query
    final_query = st.session_state.get("etf_query", "")
    if search_clicked and query:
        final_query = query
        st.session_state["etf_query"] = query

    if not final_query:
        # Landing state
        st.markdown(f"""
<div style="text-align:center;padding:60px 0;color:{_MUTED}">
  <div style="font-size:3rem;margin-bottom:12px">◈</div>
  <div style="font-size:1rem;font-weight:600;color:{_TEXT};margin-bottom:6px">Search for a UCITS ETF</div>
  <div style="font-size:0.85rem">Enter an ISIN or ticker above, or click a quick-access chip to get started.</div>
</div>
""", unsafe_allow_html=True)
        return

    # ── Fetch with spinner ────────────────────────────────────────────────────
    with st.spinner("Fetching ETF data…"):
        data = fetch_etf_cached(final_query)

    if data.error:
        st.markdown(
            f'<div class="etf-error">Warning: {data.error}</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Hero band ─────────────────────────────────────────────────────────────
    _render_hero(data)

    # ── Performance returns ───────────────────────────────────────────────────
    st.markdown('<div class="etf-section-header">Performance Returns</div>', unsafe_allow_html=True)
    _render_performance(data)

    # ── Price chart ───────────────────────────────────────────────────────────
    st.markdown('<div class="etf-section-header">Price History (Rebased to 100)</div>', unsafe_allow_html=True)
    _render_price_chart(data)

    # ── Risk & Tracking ───────────────────────────────────────────────────────
    st.markdown('<div class="etf-section-header">Risk Metrics</div>', unsafe_allow_html=True)
    _render_risk(data)

    # ── Benchmark ─────────────────────────────────────────────────────────────
    if data.benchmark_name:
        st.markdown('<div class="etf-section-header">Benchmark Details</div>', unsafe_allow_html=True)
        _render_benchmark(data)

    # ── Holdings ──────────────────────────────────────────────────────────────
    st.markdown('<div class="etf-section-header">Top Holdings</div>', unsafe_allow_html=True)
    _render_holdings(data)

    # ── Allocations ───────────────────────────────────────────────────────────
    if data.sector_weights or data.country_weights:
        st.markdown('<div class="etf-section-header">Allocations</div>', unsafe_allow_html=True)
        _render_allocations(data)

    # ── Fund facts ────────────────────────────────────────────────────────────
    st.markdown('<div class="etf-section-header">Fund Facts</div>', unsafe_allow_html=True)
    _render_fund_facts(data)
