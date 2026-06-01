"""
Equity Research Workbench — Unified company analysis & enterprise valuations
Fusion of: enterprise_valuations + company_analyzer
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime

_render_page_header("ER", "Equity Research Workbench",
                    "Company intelligence, DCF valuation, multiples, health scoring & ownership",
                    "Research")

# ── Theme ─────────────────────────────────────────────────────────────────────
_BG = "#0A0E1A"
_GRID = "rgba(255,255,255,0.05)"
_CYAN = "#00D9FF"
_GREEN = "#10B981"
_RED = "#EF4444"
_GOLD = "#F59E0B"
_PURPLE = "#A78BFA"
_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(family="Inter, sans-serif", size=12, color="#E8ECF3"),
    margin=dict(l=40, r=20, t=40, b=40),
)

CURRENCY_SYMBOL = st.session_state.get("CURRENCY_SYMBOL", "$")

# ── Helpers ───────────────────────────────────────────────────────────────────
def _safe_val(info, *keys, default=None):
    for k in keys:
        v = info.get(k)
        if v is not None and v != "N/A":
            return v
    return default

def _fmt_large(val, symbol=CURRENCY_SYMBOL):
    if val is None:
        return "N/A"
    abs_v = abs(val)
    if abs_v >= 1e12:
        return f"{symbol}{val/1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{symbol}{val/1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{symbol}{val/1e6:.2f}M"
    return f"{symbol}{val:,.0f}"

def _dcf_single(fcf_base, g1, g2, g_t, wacc, shares, net_debt):
    fcfs = []
    cf = fcf_base
    for yr in range(1, 11):
        g = g1 if yr <= 5 else g2
        cf = cf * (1 + g)
        fcfs.append(cf)
    tv = fcfs[-1] * (1 + g_t) / max(wacc - g_t, 0.001)
    pv_fcfs = sum(f / (1 + wacc) ** (i + 1) for i, f in enumerate(fcfs))
    pv_tv = tv / (1 + wacc) ** 10
    ev = pv_fcfs + pv_tv
    eq_val = ev - net_debt
    ivps = eq_val / shares if shares and shares > 0 else 0
    return fcfs, pv_fcfs, pv_tv, ev, eq_val, ivps

# ── Session state ─────────────────────────────────────────────────────────────
for _k in ['erw_ticker', 'erw_info', 'erw_fetcher', 'erw_spot',
           'erw_income', 'erw_balance', 'erw_cashflow', 'erw_hist',
           'erw_inst_holders', 'erw_insider_tx', 'erw_rec_summary',
           'erw_fcf_history', 'erw_multiples']:
    if _k not in st.session_state:
        st.session_state[_k] = None

# ── Shared ticker input ──────────────────────────────────────────────────────
col_in, col_btn = st.columns([4, 1])
with col_in:
    ticker_input = st.text_input(
        "Ticker", value=st.session_state.erw_ticker or "AAPL",
        placeholder="AAPL, MSFT, TSLA, SAP…",
        key="erw_ticker_input", label_visibility="collapsed"
    )
with col_btn:
    analyze_clicked = st.button("Analyze", key="erw_btn", use_container_width=True)

if analyze_clicked and ticker_input.strip():
    sym = ticker_input.upper().strip()
    with st.spinner(f"Fetching {sym}…"):
        try:
            t = yf.Ticker(sym)
            info = t.info
            if not info or not info.get('currentPrice'):
                st.error(f"No data found for **{sym}**.")
                st.stop()

            # Fetch all data
            try:
                income_stmt = t.income_stmt
            except Exception:
                income_stmt = pd.DataFrame()
            try:
                balance_sheet = t.balance_sheet
            except Exception:
                balance_sheet = pd.DataFrame()
            try:
                cashflow = t.cashflow
            except Exception:
                cashflow = pd.DataFrame()
            try:
                hist_1y = t.history(period="1y")
            except Exception:
                hist_1y = pd.DataFrame()
            try:
                inst_holders = t.institutional_holders
            except Exception:
                inst_holders = pd.DataFrame()
            try:
                insider_tx = t.insider_transactions
            except Exception:
                insider_tx = pd.DataFrame()
            try:
                rec_summary = t.recommendations_summary
            except Exception:
                rec_summary = pd.DataFrame()

            # Try to load fundamental_analysis module for advanced valuations
            fetcher = None
            fcf_hist = []
            comp_mults = {}
            try:
                from fundamental_analysis import (
                    FinancialDataFetcher, DCFValuation, ValuationMultiples
                )
                fetcher = FinancialDataFetcher(sym)
                dcf_tmp = DCFValuation(sym, fetcher)
                fcf_hist = dcf_tmp.get_fcf_history(5)
                mult_obj = ValuationMultiples(sym, fetcher)
                comp_mults = mult_obj.get_multiples()
            except Exception:
                pass

            st.session_state.erw_ticker = sym
            st.session_state.erw_info = info
            st.session_state.erw_fetcher = fetcher
            st.session_state.erw_spot = float(info.get('currentPrice') or 0)
            st.session_state.erw_income = income_stmt
            st.session_state.erw_balance = balance_sheet
            st.session_state.erw_cashflow = cashflow
            st.session_state.erw_hist = hist_1y
            st.session_state.erw_inst_holders = inst_holders
            st.session_state.erw_insider_tx = insider_tx
            st.session_state.erw_rec_summary = rec_summary
            st.session_state.erw_fcf_history = fcf_hist
            st.session_state.erw_multiples = comp_mults
        except Exception as e:
            st.error(f"Error: {e}")

if not st.session_state.erw_ticker or not st.session_state.erw_info:
    st.info("Enter a ticker symbol above and click **Analyze** to begin.")
    st.stop()

# Shortcuts
ticker = st.session_state.erw_ticker
info = st.session_state.erw_info
spot = st.session_state.erw_spot
income_stmt = st.session_state.erw_income
balance_sheet = st.session_state.erw_balance
cashflow = st.session_state.erw_cashflow
hist_1y = st.session_state.erw_hist
inst_holders = st.session_state.erw_inst_holders
insider_tx = st.session_state.erw_insider_tx
rec_summary = st.session_state.erw_rec_summary
fcf_hist = st.session_state.erw_fcf_history or []
comp_mults = st.session_state.erw_multiples or {}

company_name = info.get('longName', ticker)
market_cap = float(info.get('marketCap') or 0)
ev_market = float(info.get('enterpriseValue') or 0)
total_debt = float(info.get('totalDebt') or 0)
total_cash = float(info.get('totalCash') or 0)
net_debt = total_debt - total_cash
shares_out = float(info.get('sharesOutstanding') or 1)
beta_val = float(info.get('beta') or 1.0)

# ── Company Header ────────────────────────────────────────────────────────────
st.markdown(f"### {company_name} &nbsp; `{ticker}`")
h1, h2, h3, h4, h5, h6 = st.columns(6)
h1.metric("Price", f"${spot:.2f}")
h2.metric("Market Cap", _fmt_large(market_cap))
h3.metric("EV", _fmt_large(ev_market))
h4.metric("Net Debt", _fmt_large(net_debt))
h5.metric("Beta", f"{beta_val:.2f}")
w52l = float(info.get('fiftyTwoWeekLow') or 0)
w52h = float(info.get('fiftyTwoWeekHigh') or 0)
pos_pct = (spot - w52l) / (w52h - w52l) * 100 if w52h > w52l else 0
h6.metric("52W Position", f"{pos_pct:.0f}%", f"${w52l:.0f}–${w52h:.0f}")
st.divider()


# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "Overview", "DCF Valuation", "Monte Carlo DCF",
    "Multiples", "Financials", "Health & Risk",
    "Ownership", "Sensitivity"
])


# ═══ TAB 1: OVERVIEW ═════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("Key Metrics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("P/E (Trailing)", f"{_safe_val(info, 'trailingPE', default=0):.2f}")
    m2.metric("P/E (Forward)", f"{_safe_val(info, 'forwardPE', default=0):.2f}")
    m3.metric("EV/EBITDA", f"{_safe_val(info, 'enterpriseToEbitda', default=0):.2f}")
    m4.metric("Profit Margin", f"{(_safe_val(info, 'profitMargins', default=0) or 0)*100:.1f}%")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Revenue", _fmt_large(_safe_val(info, 'totalRevenue', default=0)))
    m6.metric("EBITDA", _fmt_large(_safe_val(info, 'ebitda', default=0)))
    m7.metric("Dividend Yield", f"{(_safe_val(info, 'dividendYield', default=0) or 0)*100:.2f}%")
    m8.metric("Sector", info.get('sector', 'N/A'))

    # Price chart
    if hist_1y is not None and not hist_1y.empty:
        st.subheader("Price Chart (1 Year)")
        fig_pc = go.Figure()
        fig_pc.add_trace(go.Scatter(x=hist_1y.index, y=hist_1y['Close'],
                                    mode='lines', name='Close', line=dict(color=_CYAN, width=2)))
        fig_pc.update_layout(**_LAYOUT, height=350)
        st.plotly_chart(fig_pc, use_container_width=True)

    # Analyst consensus
    if rec_summary is not None and not rec_summary.empty:
        st.subheader("Analyst Consensus")
        st.dataframe(rec_summary, use_container_width=True, hide_index=True)


# ═══ TAB 2: DCF VALUATION ════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("2-Stage DCF Valuation")

    with st.expander("WACC Builder (CAPM)", expanded=False):
        wc1, wc2, wc3, wc4, wc5 = st.columns(5)
        rf = wc1.number_input("Risk-Free (%)", value=4.2, step=0.1, min_value=0.0, max_value=10.0, key="erw_rf") / 100
        beta_wc = wc2.number_input("Beta", value=round(beta_val, 2), step=0.05, min_value=0.1, max_value=4.0, key="erw_beta")
        erp = wc3.number_input("Equity RP (%)", value=5.5, step=0.1, min_value=2.0, max_value=10.0, key="erw_erp") / 100
        cod = wc4.number_input("Cost of Debt (%)", value=3.5, step=0.1, min_value=0.5, max_value=15.0, key="erw_cod") / 100
        tax_rate = wc5.number_input("Tax Rate (%)", value=21.0, step=1.0, min_value=0.0, max_value=50.0, key="erw_tax") / 100

        ke = rf + beta_wc * erp
        debt_weight = total_debt / max(ev_market, 1)
        equity_weight = 1 - debt_weight
        wacc = equity_weight * ke + debt_weight * cod * (1 - tax_rate)
        st.info(f"Ke = {ke*100:.2f}% | WACC = {wacc*100:.2f}%")

    # FCF-based DCF
    fcf_base_val = 0
    if fcf_hist:
        fcf_base_val = fcf_hist[-1] if isinstance(fcf_hist[-1], (int, float)) else 0
    elif cashflow is not None and not cashflow.empty:
        try:
            op_cf = cashflow.loc['Total Cash From Operating Activities'] if 'Total Cash From Operating Activities' in cashflow.index else cashflow.iloc[0]
            capex = cashflow.loc['Capital Expenditures'] if 'Capital Expenditures' in cashflow.index else pd.Series([0])
            fcf_base_val = float(op_cf.iloc[0] or 0) + float(capex.iloc[0] or 0)
        except Exception:
            fcf_base_val = 0

    dc1, dc2, dc3, dc4 = st.columns(4)
    fcf_input = dc1.number_input("Base FCF", value=float(fcf_base_val), step=1e6, format="%.0f", key="erw_fcf")
    g1 = dc2.slider("Growth Stage 1 (%)", -10, 30, 8, key="erw_g1") / 100
    g2 = dc3.slider("Growth Stage 2 (%)", -5, 15, 3, key="erw_g2") / 100
    g_t = dc4.slider("Terminal Growth (%)", 0, 5, 2, key="erw_gt") / 100

    if fcf_input and fcf_input > 0:
        fcfs, pv_fcfs, pv_tv, ev_dcf, eq_val, ivps = _dcf_single(
            fcf_input, g1, g2, g_t, wacc, shares_out, net_debt
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Enterprise Value", _fmt_large(ev_dcf))
        c2.metric("Equity Value", _fmt_large(eq_val))
        c3.metric("Intrinsic /Share", f"${ivps:.2f}")
        upside = (ivps - spot) / spot * 100 if spot > 0 else 0
        c4.metric("Upside", f"{upside:+.1f}%",
                 delta="Undervalued" if upside > 0 else "Overvalued")

        # FCF projection chart
        fig_dcf = go.Figure()
        fig_dcf.add_trace(go.Bar(x=[f"Y{i+1}" for i in range(10)], y=fcfs,
                                 marker_color=[_CYAN]*5 + [_GOLD]*5, name="Projected FCF"))
        fig_dcf.update_layout(**_LAYOUT, title="Projected Free Cash Flows", height=350,
                             xaxis_title="Year", yaxis_title="FCF ($)")
        st.plotly_chart(fig_dcf, use_container_width=True)

        c1, c2 = st.columns(2)
        c1.metric("PV of FCFs", _fmt_large(pv_fcfs))
        c2.metric("PV of Terminal Value", _fmt_large(pv_tv))
        tv_pct = pv_tv / max(ev_dcf, 1) * 100
        st.progress(min(tv_pct / 100, 1.0), text=f"Terminal Value = {tv_pct:.1f}% of EV")
    else:
        st.warning("No FCF data available. Enter a base FCF manually.")


# ═══ TAB 3: MONTE CARLO DCF ═════════════════════════════════════════════════
with tabs[2]:
    st.subheader("Monte Carlo DCF Simulation")

    mc1, mc2, mc3 = st.columns(3)
    n_sims = mc1.slider("Simulations", 1000, 50000, 10000, step=1000, key="erw_nsims")
    growth_std = mc2.slider("Growth σ (%)", 1, 20, 5, key="erw_gstd") / 100
    wacc_std = mc3.slider("WACC σ (%)", 0.5, 5.0, 1.0, step=0.5, key="erw_wstd") / 100

    fcf_mc = fcf_input if 'fcf_input' in dir() and fcf_input > 0 else 1e9
    wacc_mc = wacc if 'wacc' in dir() else 0.10
    g1_mc = g1 if 'g1' in dir() else 0.08
    g_t_mc = g_t if 'g_t' in dir() else 0.02

    if st.button("Run Monte Carlo", key="erw_mc_run"):
        np.random.seed(42)
        ivps_dist = []
        for _ in range(n_sims):
            sim_g = np.random.normal(g1_mc, growth_std)
            sim_wacc = max(np.random.normal(wacc_mc, wacc_std), 0.02)
            sim_gt = max(min(np.random.normal(g_t_mc, 0.005), sim_wacc - 0.005), 0.0)
            _, _, _, _, eq, iv = _dcf_single(fcf_mc, sim_g, sim_g * 0.5, sim_gt, sim_wacc, shares_out, net_debt)
            ivps_dist.append(iv)

        ivps_arr = np.array(ivps_dist)
        p10, p50, p90 = np.percentile(ivps_arr, [10, 50, 90])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Median IV/Share", f"${p50:.2f}")
        c2.metric("P10 (Bear)", f"${p10:.2f}")
        c3.metric("P90 (Bull)", f"${p90:.2f}")
        upside_mc = (p50 - spot) / spot * 100 if spot > 0 else 0
        c4.metric("Upside (Median)", f"{upside_mc:+.1f}%")

        fig_mc = go.Figure()
        fig_mc.add_trace(go.Histogram(x=ivps_arr, nbinsx=80, marker_color=_CYAN, opacity=0.7, name="IV/Share"))
        fig_mc.add_vline(x=spot, line_dash="dash", line_color=_RED, annotation_text=f"Market ${spot:.2f}")
        fig_mc.add_vline(x=p50, line_dash="dash", line_color=_GREEN, annotation_text=f"Median ${p50:.2f}")
        fig_mc.update_layout(**_LAYOUT, title="Monte Carlo Intrinsic Value Distribution",
                            xaxis_title="Intrinsic Value / Share ($)", yaxis_title="Frequency", height=400)
        st.plotly_chart(fig_mc, use_container_width=True)


# ═══ TAB 4: MULTIPLES ═══════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("Valuation Multiples")

    pe_t = _safe_val(info, 'trailingPE', default=0) or 0
    pe_f = _safe_val(info, 'forwardPE', default=0) or 0
    ev_ebitda = _safe_val(info, 'enterpriseToEbitda', default=0) or 0
    ev_rev = _safe_val(info, 'enterpriseToRevenue', default=0) or 0
    pb = _safe_val(info, 'priceToBook', default=0) or 0
    ps = _safe_val(info, 'priceToSalesTrailing12Months', default=0) or 0

    multiples_data = {
        'Metric': ['P/E (Trailing)', 'P/E (Forward)', 'EV/EBITDA', 'EV/Revenue', 'P/B', 'P/S'],
        'Value': [f"{pe_t:.2f}", f"{pe_f:.2f}", f"{ev_ebitda:.2f}", f"{ev_rev:.2f}", f"{pb:.2f}", f"{ps:.2f}"],
    }
    st.dataframe(pd.DataFrame(multiples_data), use_container_width=True, hide_index=True)

    if comp_mults:
        st.markdown("### Peer Comparison")
        st.dataframe(pd.DataFrame(comp_mults), use_container_width=True, hide_index=True)


# ═══ TAB 5: FINANCIALS ══════════════════════════════════════════════════════
with tabs[4]:
    fs1, fs2, fs3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])

    with fs1:
        if income_stmt is not None and not income_stmt.empty:
            st.dataframe(income_stmt, use_container_width=True)
        else:
            st.info("No income statement data available.")

    with fs2:
        if balance_sheet is not None and not balance_sheet.empty:
            st.dataframe(balance_sheet, use_container_width=True)
        else:
            st.info("No balance sheet data available.")

    with fs3:
        if cashflow is not None and not cashflow.empty:
            st.dataframe(cashflow, use_container_width=True)
        else:
            st.info("No cash flow data available.")


# ═══ TAB 6: HEALTH & RISK ═══════════════════════════════════════════════════
with tabs[5]:
    # Altman Z-Score
    st.subheader("Altman Z-Score")
    try:
        from fundamental_analysis import AltmanZScore, PiotroskiFScore
        fetcher_h = st.session_state.erw_fetcher
        if fetcher_h:
            altman = AltmanZScore(ticker, fetcher_h)
            z_result = altman.calculate()
            if z_result:
                z_val = z_result.get('z_score', 0)
                c1, c2 = st.columns(2)
                c1.metric("Z-Score", f"{z_val:.2f}")
                zone = "Safe Zone" if z_val > 2.99 else ("Grey Zone" if z_val > 1.81 else "Distress Zone")
                c2.metric("Zone", zone)

                if z_result.get('components'):
                    st.dataframe(pd.DataFrame(list(z_result['components'].items()),
                                             columns=["Component", "Value"]),
                                use_container_width=True, hide_index=True)

            # Piotroski F-Score
            st.divider()
            st.subheader("Piotroski F-Score")
            piotroski = PiotroskiFScore(ticker, fetcher_h)
            f_result = piotroski.calculate()
            if f_result:
                f_val = f_result.get('f_score', 0)
                c1, c2 = st.columns(2)
                c1.metric("F-Score", f"{f_val}/9")
                strength = "Strong" if f_val >= 7 else ("Moderate" if f_val >= 4 else "Weak")
                c2.metric("Assessment", strength)

                if f_result.get('details'):
                    st.dataframe(pd.DataFrame(list(f_result['details'].items()),
                                             columns=["Criterion", "Pass/Fail"]),
                                use_container_width=True, hide_index=True)
        else:
            st.info("Fundamental analysis module not available. Basic ratios shown below.")
    except ImportError:
        st.info("Fundamental analysis module not available.")

    # Key Financial Ratios (from yfinance directly)
    st.divider()
    st.subheader("Key Financial Ratios")
    ratios = {
        'Current Ratio': _safe_val(info, 'currentRatio', default='N/A'),
        'Quick Ratio': _safe_val(info, 'quickRatio', default='N/A'),
        'Debt/Equity': _safe_val(info, 'debtToEquity', default='N/A'),
        'ROE': f"{(_safe_val(info, 'returnOnEquity', default=0) or 0)*100:.1f}%",
        'ROA': f"{(_safe_val(info, 'returnOnAssets', default=0) or 0)*100:.1f}%",
        'Gross Margin': f"{(_safe_val(info, 'grossMargins', default=0) or 0)*100:.1f}%",
        'Operating Margin': f"{(_safe_val(info, 'operatingMargins', default=0) or 0)*100:.1f}%",
        'Profit Margin': f"{(_safe_val(info, 'profitMargins', default=0) or 0)*100:.1f}%",
    }
    st.dataframe(pd.DataFrame(list(ratios.items()), columns=["Ratio", "Value"]),
                use_container_width=True, hide_index=True)


# ═══ TAB 7: OWNERSHIP ═══════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("Institutional Holders")
    if inst_holders is not None and not inst_holders.empty:
        st.dataframe(inst_holders.head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No institutional holder data available.")

    st.divider()
    st.subheader("Major Holders")
    holders_info = {
        'Insider Hold': f"{(_safe_val(info, 'heldPercentInsiders', default=0) or 0)*100:.2f}%",
        'Institutions Hold': f"{(_safe_val(info, 'heldPercentInstitutions', default=0) or 0)*100:.2f}%",
    }
    st.dataframe(pd.DataFrame(list(holders_info.items()), columns=["Type", "Percentage"]),
                use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Insider Transactions")
    if insider_tx is not None and not insider_tx.empty:
        st.dataframe(insider_tx.head(15), use_container_width=True, hide_index=True)
    else:
        st.info("No insider transaction data available.")


# ═══ TAB 8: SENSITIVITY ═════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("WACC × Terminal Growth Sensitivity Matrix")

    wacc_base = wacc if 'wacc' in dir() else 0.10
    g_t_base = g_t if 'g_t' in dir() else 0.02
    fcf_sens = fcf_input if 'fcf_input' in dir() and fcf_input > 0 else 1e9

    wacc_range = np.arange(max(wacc_base - 0.03, 0.04), wacc_base + 0.04, 0.01)
    gt_range = np.arange(max(g_t_base - 0.015, 0.005), g_t_base + 0.02, 0.005)

    matrix = np.zeros((len(gt_range), len(wacc_range)))
    for i, gt_s in enumerate(gt_range):
        for j, w_s in enumerate(wacc_range):
            if w_s > gt_s + 0.005:
                _, _, _, _, _, iv = _dcf_single(fcf_sens, g1 if 'g1' in dir() else 0.08,
                                                 g2 if 'g2' in dir() else 0.03,
                                                 gt_s, w_s, shares_out, net_debt)
                matrix[i, j] = iv
            else:
                matrix[i, j] = np.nan

    fig_sens = go.Figure(go.Heatmap(
        z=matrix,
        x=[f"{w*100:.1f}%" for w in wacc_range],
        y=[f"{g*100:.1f}%" for g in gt_range],
        colorscale="RdYlGn", zmid=spot,
        text=[[f"${v:.0f}" if not np.isnan(v) else "—" for v in row] for row in matrix],
        texttemplate="%{text}", textfont=dict(size=10),
        colorbar=dict(title="IV/Share"),
    ))
    fig_sens.update_layout(**_LAYOUT, title="Intrinsic Value / Share — WACC × Terminal Growth",
                          xaxis_title="WACC", yaxis_title="Terminal Growth Rate", height=450)
    st.plotly_chart(fig_sens, use_container_width=True)
