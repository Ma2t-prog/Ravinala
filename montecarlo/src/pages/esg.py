import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import plotly.graph_objects as go

_render_page_header("ESG", "ESG & Green Finance Lab", "Carbon pricing, sustainability-linked structures and climate stress", "ESG")

try:
    from esg_module import GreeniumCalculator, CarbonPricer, ClimateStressTest, SustainabilityLinkedPayoff
    _esg_ok = True
except ImportError:
    _esg_ok = False
    st.warning("ESG module loading… restart app once build completes.")

if _esg_ok:
    esg_tabs = st.tabs(["Carbon Market", "Greenium", "SLB Payoff", "Climate Stress", "ESG Scores"])

    with esg_tabs[0]:
        st.markdown("### Carbon Allowance Market (EUA)")
        cp = CarbonPricer()
        if st.button("Fetch EUA Price", key="eua_btn"):
            with st.spinner("Fetching…"):
                st.session_state["carbon_data"] = cp.get_carbon_price()
        cd = st.session_state.get("carbon_data", {})
        if cd:
            if not cd.get("error"):
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("EUA Price (€/tCO₂)", f"€{cd.get('price',0):.2f}")
                with c2: st.metric("Daily Change", f"{cd.get('change_pct',0):+.2f}%")
                with c3: st.metric("Source", cd.get("source","yfinance"))
            else:
                st.warning(f"Live price unavailable: {cd['error']}. Using indicative €65/tCO₂")
        st.divider()
        st.markdown("#### Carbon Option Pricer")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1: eua_F = st.number_input("Forward (€)", value=65.0, min_value=1.0, max_value=300.0, key="eua_F")
        with col_c2: eua_K = st.number_input("Strike (€)", value=65.0, min_value=1.0, max_value=300.0, key="eua_K")
        with col_c3: eua_T = st.number_input("Maturity (yr)", value=0.5, min_value=0.1, max_value=3.0, step=0.1, key="eua_T")
        eua_sigma = st.slider("Carbon Vol (%)", 20, 100, 45, key="eua_vol") / 100
        eua_type  = st.selectbox("Type", ["call","put"], key="eua_type")
        if st.button("Price Carbon Option", key="eua_price_btn"):
            res_c = cp.price_carbon_option(eua_F, eua_K, eua_T, 0.039, eua_sigma, eua_type)
            if not res_c.get("error"):
                p1, p2, p3 = st.columns(3)
                with p1: st.metric("Price (€)", f"€{res_c.get('price',0):.4f}")
                with p2: st.metric("Delta", f"{res_c.get('delta',0):.4f}")
                with p3: st.metric("Vega", f"€{res_c.get('vega',0):.4f}")
        st.divider()
        st.markdown("#### Energy Spreads")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("**Dark Spread** (Coal → Power)")
            coal_p  = st.number_input("Coal (€/MWh)", value=120.0, key="coal_p")
            power_p = st.number_input("Power (€/MWh)", value=80.0, key="power_p")
            ds = cp.dark_spread(coal_p, power_p, cd.get("price", 65.0))
            clr = "#10b981" if ds > 0 else "#ef4444"
            st.markdown(f"<h3 style='color:{clr}'>€{ds:.2f}/MWh</h3>", unsafe_allow_html=True)
        with col_s2:
            st.markdown("**Spark Spread** (Gas → Power)")
            gas_p  = st.number_input("Gas (€/MWh)", value=40.0, key="gas_p")
            ss = cp.spark_spread(gas_p, power_p, cd.get("price", 65.0))
            clrs = "#10b981" if ss > 0 else "#ef4444"
            st.markdown(f"<h3 style='color:{clrs}'>€{ss:.2f}/MWh</h3>", unsafe_allow_html=True)

    with esg_tabs[1]:
        st.markdown("### Greenium Calculator")
        gc = GreeniumCalculator("BGRN", "LQD")
        if st.button("Calculate Greenium", key="green_btn"):
            with st.spinner("Fetching bond yields…"):
                st.session_state["greenium"] = gc.estimate_greenium()
        gr = st.session_state.get("greenium", {})
        if gr:
            g1, g2, g3 = st.columns(3)
            with g1: st.metric("Green Yield", f"{gr.get('green_yield',0)*100:.3f}%")
            with g2: st.metric("Conventional Yield", f"{gr.get('conv_yield',0)*100:.3f}%")
            with g3:
                bps = gr.get("greenium_bps", 0)
                st.metric("Greenium", f"{bps:.1f} bps",
                          "Green is cheaper" if bps < 0 else "Positive premium")

    with esg_tabs[2]:
        st.markdown("### Sustainability-Linked Autocall")
        c1, c2 = st.columns(2)
        with c1:
            sl_S = st.number_input("Spot", value=100.0, key="sl_s")
            sl_K = st.number_input("Strike", value=100.0, key="sl_k")
            sl_T = st.number_input("Maturity (yr)", value=3.0, min_value=1.0, max_value=10.0, step=1.0, key="sl_t")
            sl_sig = st.slider("Vol (%)", 10, 60, 20, key="sl_vol") / 100
        with c2:
            sl_coupon = st.slider("Base Coupon (%)", 2.0, 15.0, 5.0, 0.5, key="sl_c") / 100
            sl_bonus  = st.slider("ESG Bonus (%)", 0.0, 3.0, 0.5, 0.1, key="sl_b") / 100
            sl_esg_p  = st.slider("Prob ESG Target Met", 0.1, 1.0, 0.6, 0.05, key="sl_p")
            sl_bar    = st.slider("Protection Barrier (%)", 50, 95, 70, key="sl_bar") / 100
        if st.button("Price SLB Autocall", key="slb_btn"):
            slb = SustainabilityLinkedPayoff()
            with st.spinner("Monte Carlo…"):
                r_slb = slb.price_slb_autocall(sl_S, sl_K, sl_T, 0.039, sl_sig, 5000,
                                                sl_coupon, sl_bonus, sl_esg_p, sl_bar)
            if not r_slb.get("error"):
                s1, s2, s3, s4 = st.columns(4)
                with s1: st.metric("Fair Value (par=100)", f"{r_slb.get('price',0):.2f}")
                with s2: st.metric("Expected Coupon", f"{r_slb.get('expected_coupon',0)*100:.2f}%")
                with s3: st.metric("Autocall Prob", f"{r_slb.get('autocall_prob',0)*100:.1f}%")
                with s4: st.metric("ESG Uplift (bps)", f"{r_slb.get('esg_uplift',0)*10000:.0f}")

    with esg_tabs[3]:
        st.markdown("### Climate Risk Stress Test")
        port_tks_e = [x.strip().upper() for x in
                      st.text_input("Tickers", value="XOM,BP,VALE,JPM,AAPL", key="climate_port").split(",") if x.strip()]
        scenario_esg = st.selectbox("Scenario", {
            "carbon_tax_200": "Carbon Tax Shock (EUR200/tCO2)",
            "transition_2030": "Net-Zero Transition 2030",
            "physical_flood": "Physical Risk — Flooding"
        }.keys(), format_func=lambda x: {
            "carbon_tax_200": "Carbon Tax Shock (EUR200/tCO2)",
            "transition_2030": "Net-Zero Transition 2030",
            "physical_flood": "Physical Risk — Flooding"
        }.get(x, x), key="esg_sc")
        if st.button("Run Climate Stress", key="climate_btn"):
            cst = ClimateStressTest(port_tks_e, [1/len(port_tks_e)]*len(port_tks_e))
            cr  = cst.run_scenario(scenario_esg)
            st.session_state["climate_result"] = cr
        cr = st.session_state.get("climate_result", {})
        if cr:
            pnl = cr.get("portfolio_pnl_pct", 0)
            clr_cr = "#ef4444" if pnl < 0 else "#10b981"
            st.markdown(f"<h2 style='color:{clr_cr}'>Portfolio P&L: {pnl*100:+.1f}%</h2>", unsafe_allow_html=True)
            st.metric("VaR Increase", f"{cr.get('var_increase_pct',0):+.1f}%")
            bd = cr.get("sector_breakdown", {})
            if bd:
                fig_cl = go.Figure(go.Bar(
                    x=list(bd.keys()), y=[v*100 for v in bd.values()],
                    marker_color=["#10b981" if v >= 0 else "#ef4444" for v in bd.values()]
                ))
                fig_cl.update_layout(paper_bgcolor="#0A0A0F", plot_bgcolor="#0A0A0F",
                                     font=dict(color="#9ca3af"), height=300,
                                     yaxis=dict(title="Shock (%)", gridcolor="rgba(255,255,255,0.04)"),
                                     xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
                                     margin=dict(l=0,r=0,t=10,b=0))
                st.plotly_chart(fig_cl, width="stretch")

    with esg_tabs[4]:
        st.markdown("### ESG Scores")
        import yfinance as yf
        esg_t = st.text_input("Ticker", value="MSFT", key="esg_t")
        if st.button("Fetch ESG", key="esg_btn"):
            try:
                t_e2 = yf.Ticker(esg_t.upper().strip())
                sust = t_e2.sustainability
                if sust is not None and not sust.empty:
                    st.dataframe(sust, width="stretch")
                else:
                    info_e2 = t_e2.info
                    esg_fields = {k: v for k, v in info_e2.items() if "esg" in k.lower() or "governance" in k.lower()
                                  or "environment" in k.lower() or "social" in k.lower()}
                    if esg_fields:
                        st.json(esg_fields)
                    else:
                        st.info("No ESG data for this ticker. Try MSFT, AAPL, TSLA, AMZN.")
            except Exception as e:
                st.error(f"Error: {e}")
