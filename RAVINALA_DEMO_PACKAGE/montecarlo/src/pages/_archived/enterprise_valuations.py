import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd

from fundamental_analysis import (
    FinancialDataFetcher, DCFValuation, MonteCarloValuation,
    ValuationMultiples, AltmanZScore, PiotroskiFScore,
    AnalystConsensus, Ownership, SensitivityAnalysis
)

_render_page_header("EV", "Enterprise Valuations",
                    "DCF modelling, reverse DCF, financial trends, health scoring & peer benchmarking",
                    "Fundamentals")

# ── Session-state init ────────────────────────────────────────────────────────
_SS_KEYS = [
    'ev_ticker', 'ev_info', 'ev_fetcher', 'ev_spot',
    'ev_fcf_history', 'ev_multiples',
    'ev_dcf_result', 'ev_mc_result', 'ev_sensitivity_matrix',
]
for _k in _SS_KEYS:
    if _k not in st.session_state:
        st.session_state[_k] = None

st.divider()

# ── Ticker input ──────────────────────────────────────────────────────────────
col_in, col_btn = st.columns([4, 1])
with col_in:
    ticker_input = st.text_input(
        "Ticker", value=st.session_state.ev_ticker or "AAPL",
        placeholder="AAPL, MSFT, SAP, 0001.HK…",
        key="ev_ticker_input", label_visibility="collapsed"
    )
with col_btn:
    analyze_clicked = st.button("Analyze", key="ev_analyze_btn", use_container_width=True)

if analyze_clicked and ticker_input.strip():
    sym = ticker_input.upper().strip()
    with st.spinner(f"Fetching {sym}…"):
        try:
            fetcher = FinancialDataFetcher(sym)
            info = fetcher.get_info()
            if not info or not info.get('currentPrice'):
                st.error(f"No data found for **{sym}**. Check the ticker and try again.")
                st.stop()
            dcf_tmp = DCFValuation(sym, fetcher)
            fcf_hist = dcf_tmp.get_fcf_history(5)
            multiples_obj = ValuationMultiples(sym, fetcher)
            comp_mults = multiples_obj.get_multiples()

            st.session_state.ev_ticker = sym
            st.session_state.ev_info = info
            st.session_state.ev_fetcher = fetcher
            st.session_state.ev_spot = float(info.get('currentPrice') or 0)
            st.session_state.ev_fcf_history = fcf_hist
            st.session_state.ev_multiples = comp_mults
            # Clear stale calc results on new ticker
            st.session_state.ev_dcf_result = None
            st.session_state.ev_mc_result = None
            st.session_state.ev_sensitivity_matrix = None
        except Exception as e:
            st.error(f"Error loading {sym}: {e}")

# ── Main content (persists via session_state) ─────────────────────────────────
if not st.session_state.ev_ticker or not st.session_state.ev_info:
    st.info("Enter a ticker symbol above and click **Analyze** to begin.")
    st.stop()

# Shortcuts
ticker = st.session_state.ev_ticker
info = st.session_state.ev_info
fetcher = st.session_state.ev_fetcher
spot = st.session_state.ev_spot
fcf_hist = st.session_state.ev_fcf_history or []
comp_mults = st.session_state.ev_multiples or {}

company_name = info.get('longName', ticker)
market_cap = float(info.get('marketCap') or 0)
ev_market = float(info.get('enterpriseValue') or 0)
total_debt = float(info.get('totalDebt') or 0)
total_cash = float(info.get('totalCash') or 0)
net_debt = total_debt - total_cash
shares_out = float(info.get('sharesOutstanding') or 1)
ebitda_info = float(info.get('ebitda') or 0)
revenue_info = float(info.get('totalRevenue') or 0)
beta_val = float(info.get('beta') or 1.0)

st.divider()

# ── Company header ────────────────────────────────────────────────────────────
st.markdown(f"### {company_name} &nbsp; `{ticker}`")

h1, h2, h3, h4, h5, h6, h7 = st.columns(7)
with h1:
    st.metric("Price", f"${spot:.2f}")
with h2:
    st.metric("Market Cap", f"${market_cap/1e9:.1f}B")
with h3:
    st.metric("EV (Market)", f"${ev_market/1e9:.1f}B")
with h4:
    st.metric("Net Debt", f"${net_debt/1e9:.1f}B")
with h5:
    st.metric("Beta", f"{beta_val:.2f}")
with h6:
    w52_low = float(info.get('fiftyTwoWeekLow') or 0)
    w52_high = float(info.get('fiftyTwoWeekHigh') or 0)
    pos_pct = (spot - w52_low) / (w52_high - w52_low) * 100 if w52_high > w52_low else 0
    st.metric("52W Position", f"{pos_pct:.0f}%", f"${w52_low:.0f}–${w52_high:.0f}")
with h7:
    sector = info.get('sector', 'N/A')
    st.caption(f"**Sector**\n{sector}")

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "DCF", "Monte Carlo", "Multiples & Comps",
    "Reverse DCF", "Financial Trends", "Health & Risk",
    "Ownership & Consensus", "Sensitivity"
])


# ═══ TAB 1: DCF ══════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("2-Stage DCF Valuation")

    # ── WACC Builder ─────────────────────────────────────────────────────────
    with st.expander("WACC Builder (CAPM)", expanded=False):
        wc1, wc2, wc3, wc4, wc5 = st.columns(5)
        with wc1:
            rf = st.number_input("Risk-Free Rate (%)", value=4.2, step=0.1,
                                  min_value=0.0, max_value=10.0, key="wc_rf") / 100
        with wc2:
            beta_wc = st.number_input("Beta", value=round(beta_val, 2), step=0.05,
                                       min_value=0.1, max_value=4.0, key="wc_beta")
        with wc3:
            erp = st.number_input("Equity Risk Prem. (%)", value=5.5, step=0.1,
                                   min_value=2.0, max_value=10.0, key="wc_erp") / 100
        with wc4:
            cod = st.number_input("Cost of Debt (%)", value=3.5, step=0.1,
                                   min_value=0.5, max_value=15.0, key="wc_cod") / 100
        with wc5:
            tax_w = st.number_input("Tax Rate (%)", value=21.0, step=0.5,
                                     min_value=0.0, max_value=40.0, key="wc_tax") / 100

        ke_wc = rf + beta_wc * erp
        total_v_wc = market_cap + total_debt
        _wacc_computed = (market_cap / total_v_wc) * ke_wc + (total_debt / total_v_wc) * cod * (1 - tax_w) if total_v_wc > 0 else ke_wc
        st.session_state['_wacc_built'] = _wacc_computed
        st.info(
            f"**WACC = {_wacc_computed*100:.2f}%** | "
            f"Ke (CAPM) = {ke_wc*100:.2f}% | "
            f"E/V = {market_cap/total_v_wc*100:.0f}% | "
            f"D/V = {total_debt/total_v_wc*100:.0f}% | "
            f"After-tax Kd = {cod*(1-tax_w)*100:.2f}%"
        )

    wacc_built = st.session_state.get('_wacc_built', 0.08)

    # ── DCF Inputs ────────────────────────────────────────────────────────────
    dc1, dc2, dc3, dc4, dc5 = st.columns(5)
    with dc1:
        dcf_wacc = st.number_input("WACC (%)", min_value=2.0, max_value=25.0,
                                    value=round(wacc_built * 100, 1), step=0.1, key="dcf_wacc") / 100
    with dc2:
        stage1_g = st.number_input("Stage 1 Growth % (Yr 1–5)", min_value=-10.0, max_value=60.0,
                                    value=8.0, step=0.5, key="dcf_s1g") / 100
    with dc3:
        stage2_g = st.number_input("Stage 2 Growth % (Yr 6–10)", min_value=-10.0, max_value=40.0,
                                    value=4.0, step=0.5, key="dcf_s2g") / 100
    with dc4:
        dcf_tg = st.number_input("Terminal Growth (%)", min_value=0.0, max_value=5.0,
                                  value=2.5, step=0.1, key="dcf_tg") / 100
    with dc5:
        dcf_yrs = int(st.number_input("Projection Years", min_value=5, max_value=15,
                                       value=10, step=1, key="dcf_yrs"))

    if st.button("Calculate DCF", key="dcf_run_btn"):
        growth_schedule = [stage1_g] * 5 + [stage2_g] * max(0, dcf_yrs - 5)
        dcf_obj = DCFValuation(ticker, fetcher)
        res = dcf_obj.calculate_dcf_2stage(
            wacc=dcf_wacc, terminal_growth=dcf_tg,
            growth_rates=growth_schedule, projection_years=dcf_yrs
        )
        st.session_state.ev_dcf_result = res

    # ── DCF Results (persistent) ───────────────────────────────────────────
    if st.session_state.ev_dcf_result:
        res = st.session_state.ev_dcf_result
        if res.get('error'):
            st.error(f"DCF Error: {res['error']}")
        else:
            iv = res['per_share']
            upside = (iv / spot - 1) * 100 if spot > 0 else 0
            tv_pct = res.get('tv_pct_of_ev', 0)

            # Valuation label
            if upside > 15:
                st.success(f"UNDERVALUED — Intrinsic value {upside:+.1f}% above market price")
            elif upside < -15:
                st.error(f"OVERVALUED — Intrinsic value {upside:+.1f}% below market price")
            else:
                st.warning(f"FAIRLY VALUED — {upside:+.1f}% vs market price")

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            with m1:
                st.metric("Intrinsic Value/Share", f"${iv:.2f}",
                          f"{upside:+.1f}%",
                          delta_color="normal" if upside > 0 else "inverse")
            with m2:
                st.metric("Enterprise Value (DCF)", f"${res['enterprise_value']/1e9:.1f}B")
            with m3:
                st.metric("PV of FCFs", f"${res['pv_fcf']/1e9:.1f}B")
            with m4:
                st.metric("PV Terminal Value", f"${res['terminal_value']/1e9:.1f}B",
                          f"{tv_pct:.0f}% of EV")
            with m5:
                st.metric("Net Debt", f"${res.get('net_debt', 0)/1e9:.1f}B")
            with m6:
                st.metric("Base FCF", f"${res.get('base_fcf', 0)/1e9:.2f}B")

            st.markdown("---")
            col_l, col_r = st.columns(2)

            with col_l:
                # FCF projections bar chart
                proj = res.get('projected_fcf', [])
                if proj:
                    yr_labels = [f"Y{i+1}" for i in range(len(proj))]
                    colors = ['#00c896' if f >= 0 else '#ff4b4b' for f in proj]
                    fig_fcf = go.Figure(go.Bar(
                        x=yr_labels, y=[f / 1e9 for f in proj],
                        marker_color=colors,
                        text=[f"${f/1e9:.1f}B" for f in proj],
                        textposition='outside'
                    ))
                    # Stage divider
                    if dcf_yrs > 5:
                        fig_fcf.add_vline(x=4.5, line_dash="dot", line_color="#aaa",
                                          annotation_text="Stage 2",
                                          annotation_position="top right")
                    fig_fcf.update_layout(
                        title="Projected Free Cash Flow",
                        yaxis_title="FCF ($B)", height=340,
                        template="plotly_dark", showlegend=False
                    )
                    st.plotly_chart(fig_fcf, use_container_width=True)

            with col_r:
                # EV bridge waterfall
                pv_fcf_v = res['pv_fcf']
                pv_tv_v = res['terminal_value']
                ev_v = res['enterprise_value']
                nd_v = res.get('net_debt', 0)
                eq_v = res.get('equity_value', ev_v - nd_v)

                fig_wf = go.Figure(go.Waterfall(
                    orientation="v",
                    measure=["absolute", "relative", "total", "relative", "total"],
                    x=["PV(FCFs)", "PV(Terminal)", "Enterprise Value", "− Net Debt", "Equity Value"],
                    y=[pv_fcf_v / 1e9, pv_tv_v / 1e9, 0, -nd_v / 1e9, 0],
                    connector={"line": {"color": "rgba(120,120,120,0.5)"}},
                    increasing={"marker": {"color": "#00c896"}},
                    decreasing={"marker": {"color": "#ff4b4b"}},
                    totals={"marker": {"color": "#00d4ff"}},
                    texttemplate="%{y:.1f}B",
                    textposition="outside"
                ))
                fig_wf.update_layout(
                    title="DCF Bridge: EV → Equity Value",
                    yaxis_title="$B", height=340,
                    template="plotly_dark"
                )
                st.plotly_chart(fig_wf, use_container_width=True)

            # Historical vs Projected FCF
            if fcf_hist and proj:
                hist_labels = [f"H{i - len(fcf_hist) + 1}" if i < len(fcf_hist) - 1 else "H0 (LTM)"
                               for i in range(len(fcf_hist))]
                proj_labels = [f"Y{i+1}" for i in range(len(proj))]
                fig_comb = go.Figure()
                fig_comb.add_trace(go.Bar(
                    x=hist_labels, y=[f / 1e9 for f in fcf_hist],
                    name="Historical FCF", marker_color='#636efa'
                ))
                fig_comb.add_trace(go.Bar(
                    x=proj_labels, y=[f / 1e9 for f in proj],
                    name="Projected FCF", marker_color='#00d4ff', opacity=0.75
                ))
                fig_comb.update_layout(
                    title="Historical vs Projected FCF",
                    yaxis_title="$B", height=300,
                    template="plotly_dark", barmode='group'
                )
                st.plotly_chart(fig_comb, use_container_width=True)

            # DCF assumptions summary
            with st.expander("DCF Assumptions Summary"):
                assump = {
                    "WACC": f"{res.get('wacc', dcf_wacc)*100:.2f}%",
                    "Stage 1 Growth (Yr 1–5)": f"{stage1_g*100:.1f}%",
                    "Stage 2 Growth (Yr 6–10)": f"{stage2_g*100:.1f}%",
                    "Terminal Growth Rate": f"{dcf_tg*100:.1f}%",
                    "Projection Horizon": f"{dcf_yrs} years",
                    "Base FCF (LTM)": f"${res.get('base_fcf', 0)/1e9:.2f}B",
                    "Terminal Value % of EV": f"{tv_pct:.1f}%",
                    "Net Debt": f"${res.get('net_debt', 0)/1e9:.2f}B",
                    "Shares Outstanding": f"{res.get('shares_outstanding', 0)/1e9:.2f}B",
                }
                st.table(pd.DataFrame(list(assump.items()), columns=["Parameter", "Value"]))


# ═══ TAB 2: Monte Carlo ══════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Monte Carlo DCF Simulation")
    st.caption("Randomises WACC, FCF growth and terminal growth to build a distribution of intrinsic values.")

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1:
        mc_wacc = st.number_input("WACC Mean (%)", 2.0, 20.0, 8.0, 0.1, key="mc_wacc") / 100
    with mc2:
        mc_g = st.number_input("FCF Growth Mean (%)", 0.0, 30.0, 6.0, 0.5, key="mc_g") / 100
    with mc3:
        mc_tg = st.number_input("Terminal Growth Mean (%)", 0.1, 5.0, 2.5, 0.1, key="mc_tg") / 100
    with mc4:
        mc_n = int(st.number_input("Simulations", 1000, 20000, 5000, 1000, key="mc_n"))
    with mc5:
        mc_wacc_std = st.number_input("WACC Std Dev (%)", 0.1, 3.0, 1.0, 0.1, key="mc_ws") / 100

    if st.button("Run Monte Carlo", key="mc_run_btn"):
        with st.spinner(f"Running {mc_n:,} simulations…"):
            dcf_mc = DCFValuation(ticker, fetcher)
            mc_obj = MonteCarloValuation(dcf_mc)
            mc_res = mc_obj.run_monte_carlo(
                n_simulations=mc_n,
                wacc_mean=mc_wacc, wacc_std=mc_wacc_std,
                growth_mean=mc_g,
                terminal_growth_mean=mc_tg,
            )
            st.session_state.ev_mc_result = mc_res

    if st.session_state.ev_mc_result:
        mc_res = st.session_state.ev_mc_result
        dist = mc_res.get('distribution', np.array([]))
        p5 = mc_res.get('percentile_5', 0)
        p25 = mc_res.get('percentile_25', 0)
        p50 = mc_res.get('median', 0)
        p75 = mc_res.get('percentile_75', 0)
        p95 = mc_res.get('percentile_95', 0)
        mean_v = mc_res.get('mean', 0)

        prob_above = (np.sum(dist > spot) / len(dist) * 100) if len(dist) > 0 else 0

        sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
        with sc1: st.metric("P5 (Bear)", f"${p5:.2f}", f"{(p5/spot-1)*100:+.1f}%" if spot else "")
        with sc2: st.metric("P25", f"${p25:.2f}", f"{(p25/spot-1)*100:+.1f}%" if spot else "")
        with sc3: st.metric("Median (P50)", f"${p50:.2f}", f"{(p50/spot-1)*100:+.1f}%" if spot else "")
        with sc4: st.metric("P75", f"${p75:.2f}", f"{(p75/spot-1)*100:+.1f}%" if spot else "")
        with sc5: st.metric("P95 (Bull)", f"${p95:.2f}", f"{(p95/spot-1)*100:+.1f}%" if spot else "")
        with sc6: st.metric("P(Undervalued)", f"{prob_above:.1f}%",
                             delta_color="normal" if prob_above > 50 else "inverse")

        # Distribution histogram
        if len(dist) > 0:
            fig_mc = go.Figure()
            fig_mc.add_trace(go.Histogram(
                x=dist, nbinsx=80, name='Simulations',
                marker_color='#00d4ff', opacity=0.65
            ))
            for val, lbl, col in [
                (p5, "P5", "#ff6b6b"), (p25, "P25", "#ffa94d"),
                (p50, "P50", "#69db7c"), (p75, "P75", "#ffa94d"),
                (p95, "P95", "#ff6b6b"), (spot, "Market Price", "#ffffff"),
            ]:
                if val and val > 0:
                    fig_mc.add_vline(
                        x=val, line_dash="dash", line_color=col,
                        annotation_text=f" {lbl}: ${val:.0f}",
                        annotation_font_color=col
                    )
            fig_mc.update_layout(
                title=f"Intrinsic Value Distribution  ({len(dist):,} simulations)",
                xaxis_title="Fair Value per Share ($)",
                yaxis_title="Frequency", height=420,
                template="plotly_dark", showlegend=False
            )
            st.plotly_chart(fig_mc, use_container_width=True)

        # Scenario table
        rows = [
            ("Bear (P5)", p5), ("Conservative (P25)", p25), ("Base (P50)", p50),
            ("Optimistic (P75)", p75), ("Bull (P95)", p95), ("Mean", mean_v),
        ]
        table_data = [{
            "Scenario": lbl,
            "Fair Value": f"${v:.2f}",
            "Upside / Downside": f"{(v/spot-1)*100:+.1f}%" if spot > 0 else "N/A",
        } for lbl, v in rows]
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)


# ═══ TAB 3: Multiples & Comps ════════════════════════════════════════════════
with tabs[2]:
    st.subheader("Valuation Multiples & Football Field")

    col_mul, col_ff = st.columns([1, 1])

    with col_mul:
        st.markdown("**Current Trading Multiples**")
        mult_rows = [
            ("Trailing P/E", comp_mults.get('PE_Ratio', 0), "x", "15–25"),
            ("Forward P/E", comp_mults.get('Forward_PE', 0), "x", "12–20"),
            ("EV/EBITDA", comp_mults.get('EV_EBITDA', 0), "x", "10–15"),
            ("EV/Revenue", float(info.get('enterpriseToRevenue') or 0), "x", "2–5"),
            ("Price/Sales", comp_mults.get('PS_Ratio', 0), "x", "1–4"),
            ("Price/Book", comp_mults.get('PB_Ratio', 0), "x", "2–4"),
            ("ROE", comp_mults.get('ROE', 0) * 100, "%", ">15%"),
            ("ROA", comp_mults.get('ROA', 0) * 100, "%", ">5%"),
            ("Div Yield", comp_mults.get('Dividend_Yield', 0) * 100, "%", "2–4%"),
            ("Debt/Equity", comp_mults.get('Debt_to_Equity', 0), "x", "<1x"),
        ]
        mult_table = [
            {"Metric": n, "Value": f"{v:.2f}{u}", "Benchmark": b}
            for n, v, u, b in mult_rows if v and abs(v) > 0.001
        ]
        if mult_table:
            st.dataframe(pd.DataFrame(mult_table), use_container_width=True, hide_index=True)

    with col_ff:
        st.markdown("**Football Field Chart**")
        football = []

        if st.session_state.ev_dcf_result and not st.session_state.ev_dcf_result.get('error'):
            iv = st.session_state.ev_dcf_result['per_share']
            football.append(("DCF (±15%)", iv * 0.85, iv * 1.15, iv))

        if st.session_state.ev_mc_result:
            football.append(("Monte Carlo P25–P75",
                             st.session_state.ev_mc_result.get('percentile_25', 0),
                             st.session_state.ev_mc_result.get('percentile_75', 0),
                             st.session_state.ev_mc_result.get('median', 0)))

        if ebitda_info > 0:
            nd = total_debt - total_cash
            for lo_m, hi_m, lbl in [(8, 14, "EV/EBITDA 8–14x"), (12, 20, "EV/EBITDA 12–20x")]:
                pl = (ebitda_info * lo_m - nd) / shares_out
                ph = (ebitda_info * hi_m - nd) / shares_out
                if pl > 0:
                    football.append((lbl, pl, ph, (pl + ph) / 2))

        if revenue_info > 0:
            nd = total_debt - total_cash
            for lo_m, hi_m, lbl in [(2, 5, "EV/Rev 2–5x"), (5, 10, "EV/Rev 5–10x")]:
                pl = (revenue_info * lo_m - nd) / shares_out
                ph = (revenue_info * hi_m - nd) / shares_out
                if pl > 0:
                    football.append((lbl, pl, ph, (pl + ph) / 2))

        try:
            cons_tmp = AnalystConsensus(ticker).get_consensus()
            if not cons_tmp.get('error') and cons_tmp.get('low_target', 0) > 0:
                football.append(("Analyst Consensus",
                                  cons_tmp['low_target'], cons_tmp['high_target'],
                                  cons_tmp['target_price']))
        except Exception:
            pass

        if w52_low > 0:
            football.append(("52-Week Range", w52_low, w52_high, spot))

        if football:
            fig_ff = go.Figure()
            for label, lo, hi, mid in football:
                fig_ff.add_trace(go.Bar(
                    x=[hi - lo], base=[lo], y=[label], orientation='h',
                    marker_color='rgba(0,212,255,0.30)',
                    showlegend=False,
                    hovertemplate=f"{label}<br>Low: ${lo:.0f}<br>High: ${hi:.0f}<br>Mid: ${mid:.0f}<extra></extra>"
                ))
                fig_ff.add_trace(go.Scatter(
                    x=[mid], y=[label], mode='markers',
                    marker=dict(color='#00d4ff', size=10, symbol='diamond'),
                    showlegend=False
                ))
            fig_ff.add_vline(x=spot, line_color="white", line_width=2,
                              annotation_text=f" Current ${spot:.0f}")
            fig_ff.update_layout(
                title="Football Field — Valuation Ranges",
                xaxis_title="Price per Share ($)",
                height=max(300, len(football) * 55 + 100),
                template="plotly_dark", barmode='overlay'
            )
            st.plotly_chart(fig_ff, use_container_width=True)
        else:
            st.info("Run DCF & Monte Carlo first to populate the Football Field chart.")

    # ── Comps-Implied Prices ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**EV/EBITDA — Implied Price at Different Multiples**")
    if ebitda_info > 0:
        nd = total_debt - total_cash
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        for col, mult in zip([c1, c2, c3, c4, c5, c6], [8, 10, 12, 15, 18, 20]):
            implied = (ebitda_info * mult - nd) / shares_out
            delta = f"{(implied/spot-1)*100:+.1f}%" if spot > 0 else ""
            col.metric(f"EV/EBITDA {mult}x", f"${implied:.2f}", delta,
                       delta_color="normal" if implied > spot else "inverse")
    else:
        st.caption("EBITDA not available for this ticker.")

    st.markdown("**EV/Revenue — Implied Price at Different Multiples**")
    if revenue_info > 0:
        nd = total_debt - total_cash
        r1, r2, r3, r4, r5, r6 = st.columns(6)
        for col, mult in zip([r1, r2, r3, r4, r5, r6], [2, 3, 5, 8, 10, 15]):
            implied = (revenue_info * mult - nd) / shares_out
            delta = f"{(implied/spot-1)*100:+.1f}%" if spot > 0 else ""
            col.metric(f"EV/Rev {mult}x", f"${implied:.2f}", delta,
                       delta_color="normal" if implied > spot else "inverse")


# ═══ TAB 4: Reverse DCF ══════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("Reverse DCF — Market-Implied Growth Rate")
    st.caption("Solves for the FCF growth rate baked into the current share price via binary search.")

    rv1, rv2, rv3 = st.columns(3)
    with rv1:
        rv_wacc = st.number_input("WACC (%)", 2.0, 20.0, 8.0, 0.1, key="rv_wacc") / 100
    with rv2:
        rv_tg = st.number_input("Terminal Growth (%)", 0.1, 5.0, 2.5, 0.1, key="rv_tg") / 100
    with rv3:
        rv_yrs = int(st.number_input("Projection Years", 5, 15, 10, 1, key="rv_yrs"))

    if st.button("Find Implied Growth Rate", key="rv_run"):
        dcf_rv = DCFValuation(ticker, fetcher)
        implied_g = dcf_rv.get_implied_growth_rate(
            target_price=spot, wacc=rv_wacc,
            terminal_growth=rv_tg, projection_years=rv_yrs
        )
        if implied_g is not None:
            # Historical FCF CAGR
            hist_g = None
            if len(fcf_hist) >= 2 and fcf_hist[0] > 0 and fcf_hist[-1] > 0:
                hist_g = (fcf_hist[-1] / fcf_hist[0]) ** (1 / (len(fcf_hist) - 1)) - 1

            rv_c1, rv_c2, rv_c3 = st.columns(3)
            with rv_c1:
                st.metric("Implied FCF Growth (Mkt)", f"{implied_g*100:.1f}%")
            with rv_c2:
                if hist_g is not None:
                    st.metric("Historical FCF CAGR", f"{hist_g*100:.1f}%")
                else:
                    st.metric("Historical FCF CAGR", "N/A")
            with rv_c3:
                if hist_g is not None:
                    diff = implied_g - hist_g
                    verdict = "Demanding" if diff > 0.03 else ("Reasonable" if diff > -0.05 else "Conservative")
                    st.metric("Premium vs History", f"{diff*100:+.1f}%", verdict)

            # Sensitivity: growth → fair value
            g_range = np.linspace(max(-0.15, implied_g - 0.20), implied_g + 0.25, 25)
            dcf_sense = DCFValuation(ticker, fetcher)
            prices = []
            for g in g_range:
                r = dcf_sense.calculate_dcf_2stage(
                    wacc=rv_wacc, terminal_growth=rv_tg,
                    growth_rates=[g] * rv_yrs, projection_years=rv_yrs
                )
                prices.append(r.get('per_share', 0) if not r.get('error') else None)

            valid_pairs = [(g * 100, p) for g, p in zip(g_range, prices) if p and p > 0]
            if valid_pairs:
                xs, ys = zip(*valid_pairs)
                fig_rv = go.Figure()
                fig_rv.add_trace(go.Scatter(
                    x=list(xs), y=list(ys),
                    mode='lines', line=dict(color='#00d4ff', width=2),
                    name='Implied Fair Value'
                ))
                fig_rv.add_hline(y=spot, line_dash="dash", line_color="white",
                                  annotation_text=f" Market Price: ${spot:.2f}")
                fig_rv.add_vline(x=implied_g * 100, line_dash="dot", line_color="#69db7c",
                                  annotation_text=f" Implied: {implied_g*100:.1f}%",
                                  annotation_font_color="#69db7c")
                if hist_g is not None:
                    fig_rv.add_vline(x=hist_g * 100, line_dash="dot", line_color="#ffa94d",
                                      annotation_text=f" Historical: {hist_g*100:.1f}%",
                                      annotation_font_color="#ffa94d")
                fig_rv.update_layout(
                    title="FCF Growth Rate vs Implied Fair Value",
                    xaxis_title="FCF Growth Rate (%)",
                    yaxis_title="Fair Value / Share ($)",
                    height=420, template="plotly_dark"
                )
                st.plotly_chart(fig_rv, use_container_width=True)

            st.info(
                f"**Interpretation:** At WACC={rv_wacc*100:.1f}% and terminal growth={rv_tg*100:.1f}%, "
                f"the current share price of **${spot:.2f}** implies FCF growth of "
                f"**{implied_g*100:.1f}%/yr** over {rv_yrs} years."
                + (f" vs. historical CAGR of **{hist_g*100:.1f}%**." if hist_g is not None else "")
            )
        else:
            st.warning("Unable to compute implied growth — FCF data unavailable or negative.")


# ═══ TAB 5: Financial Trends ═════════════════════════════════════════════════
with tabs[4]:
    st.subheader("Financial History & Trends")

    try:
        income = fetcher.get_income_statement()
        balance = fetcher.get_balance_sheet()
        cf = fetcher.get_cash_flow()

        if income is None or income.empty:
            st.warning("Income statement data not available.")
        else:
            years_lbl = [str(c.year) for c in income.columns]

            def safe_row(df, label):
                if df is None or label not in df.index:
                    n = len(df.columns) if df is not None and not df.empty else 4
                    return [0.0] * n
                return [float(df.loc[label].iloc[i]) if pd.notna(df.loc[label].iloc[i]) else 0.0
                        for i in range(len(df.columns))]

            revenues = safe_row(income, 'Total Revenue')
            gross_profit = safe_row(income, 'Gross Profit')
            ebitda_h = safe_row(income, 'EBITDA')
            net_income_h = safe_row(income, 'Net Income')
            op_cf_h = safe_row(cf, 'Operating Cash Flow')
            capex_h = safe_row(cf, 'Capital Expenditure')
            capex_abs = [abs(v) for v in capex_h]
            fcf_h = [oc - cx for oc, cx in zip(op_cf_h, capex_abs)]

            def margins(vals, bases):
                return [v / b * 100 if b != 0 else 0 for v, b in zip(vals, bases)]

            yl = years_lbl[::-1]  # chronological
            rev_r = revenues[::-1]
            gp_r = gross_profit[::-1]
            ebitda_r = ebitda_h[::-1]
            ni_r = net_income_h[::-1]
            opcf_r = op_cf_h[::-1]
            capex_r = capex_abs[::-1]
            fcf_r = fcf_h[::-1]
            gm_r = margins(gp_r, rev_r)
            ebitdam_r = margins(ebitda_r, rev_r)
            fcfm_r = margins(fcf_r, rev_r)

            def dual_axis_chart(title, bars, bar_names, bar_colors, line, line_name, line_color, y_title="$B"):
                fig = go.Figure()
                for vals, name, color in zip(bars, bar_names, bar_colors):
                    fig.add_trace(go.Bar(x=yl, y=[v / 1e9 for v in vals], name=name, marker_color=color))
                if line:
                    fig.add_trace(go.Scatter(
                        x=yl, y=line, name=line_name, yaxis='y2',
                        line=dict(color=line_color, width=2), mode='lines+markers'
                    ))
                fig.update_layout(
                    title=title, yaxis_title=y_title,
                    yaxis2=dict(title="Margin %", overlaying='y', side='right', showgrid=False),
                    height=320, template="plotly_dark", barmode='group'
                )
                return fig

            t1, t2 = st.columns(2)
            with t1:
                st.plotly_chart(dual_axis_chart(
                    "Revenue & Gross Profit",
                    [rev_r, gp_r], ["Revenue", "Gross Profit"],
                    ['#636efa', '#00d4ff'], gm_r, "Gross Margin %", '#69db7c'
                ), use_container_width=True)
            with t2:
                st.plotly_chart(dual_axis_chart(
                    "EBITDA & Net Income",
                    [ebitda_r, ni_r], ["EBITDA", "Net Income"],
                    ['#4ecdc4', '#45b7d1'], ebitdam_r, "EBITDA Margin %", '#ff6b6b'
                ), use_container_width=True)

            t3, t4 = st.columns(2)
            with t3:
                st.plotly_chart(dual_axis_chart(
                    "Free Cash Flow & CapEx",
                    [fcf_r, capex_r], ["FCF", "CapEx"],
                    ['#00c896', '#ff7eb9'], fcfm_r, "FCF Margin %", '#ffd43b'
                ), use_container_width=True)
            with t4:
                if balance is not None and not balance.empty:
                    bal_yl = [str(c.year) for c in balance.columns][::-1]
                    fig_bal = go.Figure()
                    for label, color, name in [
                        ('Total Assets', '#636efa', 'Total Assets'),
                        ('Stockholders Equity', '#00c896', 'Equity'),
                        ('Long Term Debt', '#ff4b4b', 'LT Debt'),
                        ('Cash And Cash Equivalents', '#ffd43b', 'Cash'),
                    ]:
                        vals = safe_row(balance, label)[::-1]
                        fig_bal.add_trace(go.Scatter(
                            x=bal_yl, y=[v / 1e9 for v in vals],
                            name=name, line=dict(color=color), mode='lines+markers'
                        ))
                    fig_bal.update_layout(
                        title="Balance Sheet Trends", yaxis_title="$B",
                        height=320, template="plotly_dark"
                    )
                    st.plotly_chart(fig_bal, use_container_width=True)

            # ── Return Metrics ───────────────────────────────────────────────
            st.markdown("---")
            st.markdown("**Return & Profitability Metrics**")
            pm1, pm2, pm3, pm4, pm5, pm6 = st.columns(6)
            with pm1:
                st.metric("ROE", f"{comp_mults.get('ROE', 0)*100:.1f}%")
            with pm2:
                st.metric("ROA", f"{comp_mults.get('ROA', 0)*100:.1f}%")
            with pm3:
                op_mg = float(info.get('operatingMargins') or 0) * 100
                st.metric("Operating Margin", f"{op_mg:.1f}%")
            with pm4:
                fcf_mg = float(info.get('freeCashflow') or 0) / revenue_info * 100 if revenue_info > 0 else 0
                st.metric("FCF Margin", f"{fcf_mg:.1f}%")
            with pm5:
                try:
                    ebit_v = float(income.loc['EBIT'].iloc[0]) if 'EBIT' in income.index else 0
                    nopat = ebit_v * 0.79
                    ic = market_cap + total_debt
                    roic = nopat / ic * 100 if ic > 0 else 0
                    st.metric("ROIC (approx)", f"{roic:.1f}%")
                except Exception:
                    st.metric("ROIC", "N/A")
            with pm6:
                gross_mg = float(info.get('grossMargins') or 0) * 100
                st.metric("Gross Margin", f"{gross_mg:.1f}%")

    except Exception as e:
        st.error(f"Financial trends error: {e}")


# ═══ TAB 6: Health & Risk ════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("Financial Health & Risk Scoring")

    h_col1, h_col2 = st.columns(2)

    with h_col1:
        st.markdown("**Altman Z-Score — Bankruptcy Risk**")
        altman = AltmanZScore(fetcher).calculate()
        if not altman.get('error'):
            z = altman['z_score']
            fig_z = go.Figure(go.Indicator(
                mode="gauge+number",
                value=z,
                title={'text': "Altman Z-Score"},
                gauge={
                    'axis': {'range': [0, 6]},
                    'bar': {'color': "#00d4ff"},
                    'steps': [
                        {'range': [0, 1.81], 'color': '#ff4b4b'},
                        {'range': [1.81, 2.99], 'color': '#ffa94d'},
                        {'range': [2.99, 6], 'color': '#69db7c'},
                    ],
                    'threshold': {'line': {'color': 'white', 'width': 3}, 'thickness': 0.8, 'value': z}
                }
            ))
            fig_z.update_layout(height=260, template="plotly_dark")
            st.plotly_chart(fig_z, use_container_width=True)
            zclass = altman['risk_classification']
            zcolor = "green" if z > 2.99 else ("orange" if z > 1.81 else "red")
            st.markdown(f"**:{zcolor}[{zclass}]** (Z = {z:.2f})")
            comp_data = {
                'Component': ['X1 Working Capital/TA', 'X2 Retained Earn/TA',
                               'X3 EBIT/TA', 'X4 MktCap/TL', 'X5 Revenue/TA'],
                'Value': [altman.get('x1_working_cap', 0), altman.get('x2_retained_earn', 0),
                           altman.get('x3_ebit', 0), altman.get('x4_market_equity', 0),
                           altman.get('x5_asset_turnover', 0)],
                'Weight': [1.2, 1.4, 3.3, 0.6, 1.0],
            }
            df_z = pd.DataFrame(comp_data)
            df_z['Contribution'] = df_z['Value'] * df_z['Weight']
            st.dataframe(df_z.round(3), use_container_width=True, hide_index=True)
        else:
            st.error(altman['error'])

    with h_col2:
        st.markdown("**Piotroski F-Score — Earnings Quality**")
        piotroski = PiotroskiFScore(fetcher).calculate()
        if not piotroski.get('error'):
            f = piotroski['f_score']
            fig_f = go.Figure(go.Indicator(
                mode="gauge+number",
                value=f,
                title={'text': "F-Score (0–9)"},
                gauge={
                    'axis': {'range': [0, 9]},
                    'bar': {'color': "#00d4ff"},
                    'steps': [
                        {'range': [0, 3], 'color': '#ff4b4b'},
                        {'range': [3, 6], 'color': '#ffa94d'},
                        {'range': [6, 9], 'color': '#69db7c'},
                    ],
                }
            ))
            fig_f.update_layout(height=260, template="plotly_dark")
            st.plotly_chart(fig_f, use_container_width=True)
            rating = 'Excellent' if f >= 8 else ('Good' if f >= 5 else ('Average' if f >= 3 else 'Weak'))
            fcolor = "green" if f >= 7 else ("orange" if f >= 4 else "red")
            st.markdown(f"**:{fcolor}[{f}/9 — {rating}]**")
            # All 9 signals
            passed = piotroski.get('details', {})
            all_signals = [
                'Profitability', 'ROA Trend', 'Operating CF', 'Quality',
                'Liquidity', 'Share Dilution', 'Leverage', 'Asset Efficiency', 'Margin Quality'
            ]
            sig_df = pd.DataFrame([{
                'Signal': s,
                'Result': 'PASS' if s in passed else 'FAIL'
            } for s in all_signals])
            st.dataframe(sig_df, use_container_width=True, hide_index=True)
        else:
            st.error(piotroski['error'])

    # ── Capital Structure ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Capital Structure & Credit Metrics**")

    cs1, cs2, cs3, cs4, cs5, cs6 = st.columns(6)
    int_exp = abs(float(info.get('interestExpense') or 0))

    with cs1:
        nd_ebitda = net_debt / ebitda_info if ebitda_info > 0 else 0
        st.metric("Net Debt / EBITDA", f"{nd_ebitda:.1f}x",
                  delta_color="inverse" if nd_ebitda > 3 else "normal")
    with cs2:
        int_cov = ebitda_info / int_exp if int_exp > 0 else 999
        st.metric("Interest Coverage", f"{min(int_cov, 999):.1f}x",
                  delta_color="normal" if int_cov > 3 else "inverse")
    with cs3:
        de = float(info.get('debtToEquity') or 0) / 100
        st.metric("Debt / Equity", f"{de:.2f}x")
    with cs4:
        curr_r = float(info.get('currentRatio') or 0)
        st.metric("Current Ratio", f"{curr_r:.2f}x",
                  delta_color="normal" if curr_r > 1.5 else "inverse")
    with cs5:
        quick_r = float(info.get('quickRatio') or 0)
        st.metric("Quick Ratio", f"{quick_r:.2f}x")
    with cs6:
        net_d_cap = net_debt / (market_cap + net_debt) * 100 if (market_cap + net_debt) > 0 else 0
        st.metric("Net Debt / Total Capital", f"{net_d_cap:.1f}%")


# ═══ TAB 7: Ownership & Consensus ════════════════════════════════════════════
with tabs[6]:
    st.subheader("Analyst Consensus & Ownership")

    ow_col, cons_col = st.columns([1, 1])

    with cons_col:
        st.markdown("**Analyst Consensus**")
        try:
            con = AnalystConsensus(ticker).get_consensus()
            if not con.get('error'):
                target = con.get('target_price', 0)
                low_t = con.get('low_target', 0)
                high_t = con.get('high_target', 0)
                upside_c = (target / spot - 1) * 100 if spot > 0 and target > 0 else 0
                rec = con.get('recommendation', 'N/A').upper()

                cc1, cc2, cc3, cc4 = st.columns(4)
                with cc1: st.metric("Consensus Target", f"${target:.2f}", f"{upside_c:+.1f}%")
                with cc2: st.metric("Bull Target", f"${high_t:.2f}")
                with cc3: st.metric("Bear Target", f"${low_t:.2f}")
                with cc4: st.metric("# Analysts", int(con.get('recommendations_count', 0)))

                rec_col = "green" if "buy" in rec.lower() else ("red" if "sell" in rec.lower() else "orange")
                st.markdown(f"**Recommendation: :{rec_col}[{rec}]**")

                # Target range bar
                if low_t > 0 and high_t > 0:
                    fig_rng = go.Figure()
                    fig_rng.add_trace(go.Scatter(
                        x=[low_t, high_t], y=[1, 1], mode='lines',
                        line=dict(color='#00d4ff', width=10), name='Target Range'
                    ))
                    for val, sym_m, lbl, col in [
                        (low_t, 'triangle-right', f'Bear ${low_t:.0f}', '#ff6b6b'),
                        (target, 'diamond', f'Consensus ${target:.0f}', '#69db7c'),
                        (high_t, 'triangle-left', f'Bull ${high_t:.0f}', '#69db7c'),
                        (spot, 'circle', f'Current ${spot:.0f}', 'white'),
                    ]:
                        fig_rng.add_trace(go.Scatter(
                            x=[val], y=[1], mode='markers+text',
                            marker=dict(size=14, color=col, symbol=sym_m),
                            text=[lbl], textposition='top center',
                            textfont=dict(color=col, size=10),
                            showlegend=False
                        ))
                    fig_rng.update_layout(
                        height=160, template="plotly_dark", showlegend=False,
                        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                        xaxis_title="Price ($)", margin=dict(t=40, b=20)
                    )
                    st.plotly_chart(fig_rng, use_container_width=True)
            else:
                st.info("No analyst consensus data available.")
        except Exception as e:
            st.info(f"Analyst data unavailable: {e}")

    with ow_col:
        st.markdown("**Ownership Structure**")
        try:
            own_obj = Ownership(ticker)
            own = own_obj.get_ownership_stats()
            inst = own.get('institutional_ownership', 0) * 100
            insider_p = own.get('insider_ownership', 0) * 100
            public_p = max(0.0, 100 - inst - insider_p)

            if inst > 0 or insider_p > 0:
                fig_pie = go.Figure(go.Pie(
                    labels=['Institutional', 'Insider', 'Public Float'],
                    values=[inst, insider_p, public_p],
                    hole=0.42,
                    marker_colors=['#00d4ff', '#69db7c', '#636efa']
                ))
                fig_pie.update_layout(height=300, template="plotly_dark")
                st.plotly_chart(fig_pie, use_container_width=True)

                oc1, oc2, oc3 = st.columns(3)
                with oc1: st.metric("Institutional", f"{inst:.1f}%")
                with oc2: st.metric("Insider", f"{insider_p:.1f}%")
                with oc3: st.metric("Float", f"{own.get('shares_float', 0)/1e9:.2f}B sh")
            else:
                st.info("Ownership data not available.")
        except Exception as e:
            st.info(f"Ownership unavailable: {e}")

    # ── Short Interest ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Short Interest & Liquidity**")
    si1, si2, si3, si4, si5 = st.columns(5)
    with si1: st.metric("Short % of Float", f"{float(info.get('shortPercentOfFloat') or 0)*100:.1f}%")
    with si2: st.metric("Short Ratio (DTC)", f"{float(info.get('shortRatio') or 0):.1f}")
    with si3: st.metric("Shares Short", f"{float(info.get('sharesShort') or 0)/1e6:.0f}M")
    with si4: st.metric("Avg Volume (3M)", f"{float(info.get('averageVolume') or 0)/1e6:.1f}M")
    with si5: st.metric("Float", f"{float(info.get('floatShares') or 0)/1e9:.2f}B")


# ═══ TAB 8: Sensitivity ══════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("WACC × Terminal Growth — Sensitivity Matrix")

    ss1, ss2, ss3, ss4, ss5 = st.columns(5)
    with ss1: sens_wmin = st.number_input("WACC Min (%)", 2.0, 10.0, 5.0, 0.5, key="s_wmin") / 100
    with ss2: sens_wmax = st.number_input("WACC Max (%)", 5.0, 20.0, 13.0, 0.5, key="s_wmax") / 100
    with ss3: sens_gmin = st.number_input("Term. G Min (%)", 0.0, 5.0, 0.5, 0.5, key="s_gmin") / 100
    with ss4: sens_gmax = st.number_input("Term. G Max (%)", 0.5, 6.0, 4.0, 0.5, key="s_gmax") / 100
    with ss5: sens_steps = int(st.number_input("Steps", 5, 12, 8, 1, key="s_steps"))

    if st.button("Generate Matrix", key="sens_run"):
        with st.spinner("Calculating sensitivity matrix…"):
            dcf_s = DCFValuation(ticker, fetcher)
            matrix = SensitivityAnalysis.create_sensitivity_matrix(
                dcf_s,
                wacc_range=(sens_wmin, sens_wmax),
                growth_range=(sens_gmin, sens_gmax),
                steps=sens_steps
            )
            st.session_state.ev_sensitivity_matrix = matrix

    if st.session_state.ev_sensitivity_matrix is not None:
        matrix = st.session_state.ev_sensitivity_matrix

        # Add per-cell annotation: value + % vs market
        cell_text = []
        for i in range(len(matrix.index)):
            row_txt = []
            for j in range(len(matrix.columns)):
                v = matrix.iloc[i, j]
                if spot > 0 and v > 0:
                    pct = (v / spot - 1) * 100
                    row_txt.append(f"${v:.0f}<br>{pct:+.0f}%")
                else:
                    row_txt.append(f"${v:.0f}")
            cell_text.append(row_txt)

        fig_heat = go.Figure(data=go.Heatmap(
            z=matrix.values,
            x=list(matrix.columns),
            y=list(matrix.index),
            colorscale='RdYlGn',
            text=cell_text,
            texttemplate="%{text}",
            textfont={"size": 9},
            zmid=spot if spot > 0 else None,
        ))
        # Market-price contour
        if spot > 0:
            try:
                fig_heat.add_trace(go.Contour(
                    z=matrix.values,
                    x=list(matrix.columns),
                    y=list(matrix.index),
                    contours=dict(
                        coloring='none', showlines=True,
                        start=spot * 0.99, end=spot * 1.01, size=spot * 0.02
                    ),
                    line=dict(color='white', width=3),
                    showscale=False,
                    name=f'= Market ${spot:.0f}',
                    showlegend=True
                ))
            except Exception:
                pass

        fig_heat.update_layout(
            title=f"Fair Value/Share | White contour = Current Market Price ${spot:.0f}",
            xaxis_title="WACC", yaxis_title="Terminal Growth",
            height=520, template="plotly_dark"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # Styled table
        with st.expander("Raw Matrix (colour-coded vs market price)"):
            def _hl(v):
                if not spot or v == 0:
                    return ''
                pct = (v / spot - 1) * 100
                if pct > 15:
                    return 'background-color:#1a4d2e;color:white'
                if pct > 5:
                    return 'background-color:#2d6a3f;color:white'
                if pct < -15:
                    return 'background-color:#4d1a1a;color:white'
                if pct < -5:
                    return 'background-color:#6b2525;color:white'
                return 'background-color:#4d4a1a;color:white'

            try:
                st.dataframe(matrix.style.map(_hl).format("${:.2f}"),
                             use_container_width=True)
            except Exception:
                st.dataframe(matrix.style.applymap(_hl).format("${:.2f}"),
                             use_container_width=True)
