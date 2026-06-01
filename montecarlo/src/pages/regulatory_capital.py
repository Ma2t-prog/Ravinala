import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st

_render_page_header("RC", "Regulatory Capital & FRTB", "Simplified Basel IV stack: SBM, SA-CCR, KVA and ROE solver", "Regulation")

try:
    from frtb_module import SBMCapitalCalculator, SACCRCalculator, KVACalculator, RegulatoryROESolver
    _frtb_ok = True
except ImportError:
    _frtb_ok = False
    st.warning("FRTB module loading…")

if _frtb_ok:
    frtb_tabs = st.tabs(["SBM Capital", "SA-CCR", "KVA", "ROE Solver"])

    with frtb_tabs[0]:
        st.markdown("### Sensitivities-Based Method (SBM)")
        n_sbm = int(st.number_input("Assets", min_value=1, max_value=8, value=3, step=1, key="sbm_n"))
        greeks_sbm = {}
        for i in range(n_sbm):
            with st.expander(f"Asset {i+1}", expanded=(i == 0)):
                c1, c2, c3, c4 = st.columns(4)
                with c1: tk_s = st.text_input("Ticker", value=["AAPL","MSFT","JPM"][i] if i < 3 else f"A{i}", key=f"sbm_tk_{i}")
                with c2: d_s  = st.number_input("Delta", value=0.5, min_value=-1.0, max_value=1.0, step=0.01, key=f"sbm_d_{i}")
                with c3: sp_s = st.number_input("Spot", value=150.0, min_value=1.0, step=1.0, key=f"sbm_s_{i}")
                with c4: n_s  = st.number_input("Notional", value=100000.0, step=10000.0, key=f"sbm_no_{i}")
                v_s = st.number_input("Vega", value=0.02, min_value=0.0, max_value=1.0, step=0.001, key=f"sbm_v_{i}")
                g_s = st.number_input("Gamma", value=0.01, min_value=0.0, max_value=1.0, step=0.001, key=f"sbm_g_{i}")
                greeks_sbm[tk_s] = {"delta": d_s, "spot": sp_s, "notional": n_s, "vega": v_s, "gamma": g_s}
        if st.button("Calculate FRTB Capital", key="sbm_btn"):
            try:
                calc = SBMCapitalCalculator()
                dr = calc.calculate_delta_charge(greeks_sbm)
                vr = calc.calculate_vega_charge({k: {"vega": v["vega"], "notional": v["notional"]} for k, v in greeks_sbm.items()})
                cr_frtb = calc.calculate_curvature_charge({k: {"delta": v["delta"], "spot": v["spot"], "gamma": v["gamma"]} for k, v in greeks_sbm.items()})
                total = dr.get("delta_charge",0) + vr.get("vega_charge",0) + cr_frtb.get("curvature_charge",0)
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("Delta Charge", f"${dr.get('delta_charge',0):,.0f}")
                with c2: st.metric("Vega Charge", f"${vr.get('vega_charge',0):,.0f}")
                with c3: st.metric("Curvature Charge", f"${cr_frtb.get('curvature_charge',0):,.0f}")
                with c4: st.metric("Total FRTB Capital", f"${total:,.0f}")
                st.latex(r"K = \sqrt{\sum_i S_i^2 + \sum_{i \neq j} \rho_{ij} S_i S_j}")
                st.caption("Aggregation formula — intra-bucket correlation ρ=0.75, cross-bucket γ=0.25")
            except Exception as e:
                st.error(f"Error: {e}")

    with frtb_tabs[1]:
        st.markdown("### SA-CCR — Standardised Approach for Counterparty Credit Risk")
        n_tr = int(st.number_input("Trades", min_value=1, max_value=5, value=2, step=1, key="saccr_n"))
        trades_s = []
        for i in range(n_tr):
            with st.expander(f"Trade {i+1}", expanded=(i == 0)):
                c1, c2, c3, c4 = st.columns(4)
                with c1: tr_n = st.number_input("Notional", value=1_000_000.0, step=100_000.0, key=f"tr_n_{i}")
                with c2: tr_m = st.number_input("MtM", value=50_000.0, step=1_000.0, key=f"tr_m_{i}")
                with c3: tr_d = st.number_input("Delta", value=0.5, min_value=-1.0, max_value=1.0, step=0.01, key=f"tr_d_{i}")
                with c4: tr_c = st.number_input("Collateral", value=0.0, step=1_000.0, key=f"tr_c_{i}")
                trades_s.append({"type":"option","notional":tr_n,"mtm":tr_m,"delta":tr_d,"collateral":tr_c,"asset_class":"equity"})
        if st.button("Calculate SA-CCR EAD", key="saccr_btn"):
            try:
                saccr = SACCRCalculator()
                ead_r = saccr.calculate_ead(trades_s)
                e1, e2, e3, e4 = st.columns(4)
                with e1: st.metric("EAD", f"${ead_r.get('ead',0):,.0f}")
                with e2: st.metric("Replacement Cost", f"${ead_r.get('rc',0):,.0f}")
                with e3: st.metric("PFE Add-On", f"${ead_r.get('addon',0):,.0f}")
                with e4: st.metric("Capital Charge (8%)", f"${ead_r.get('capital_charge',0):,.0f}")
                st.latex(r"EAD = 1.4 \times (RC + \text{Multiplier} \times \text{AddOn})")
            except Exception as e:
                st.error(f"Error: {e}")

    with frtb_tabs[2]:
        st.markdown("### KVA — Capital Valuation Adjustment")
        kva_coc = st.slider("Cost of Capital (%)", 6.0, 20.0, 10.0, 0.5, key="kva_coc") / 100
        tr_for_kva = trades_s if trades_s else [{"notional":1_000_000,"mtm":50_000,"delta":0.5,"collateral":0,"asset_class":"equity","type":"option"}]
        if st.button("Calculate KVA", key="kva_btn"):
            try:
                kva_c = KVACalculator()
                kr    = kva_c.calculate_kva(tr_for_kva, cost_of_capital=kva_coc)
                k1, k2, k3 = st.columns(3)
                with k1: st.metric("KVA", f"${kr.get('kva',0):,.0f}")
                with k2: st.metric("Cost of Capital", f"{kva_coc*100:.1f}%")
                with k3: st.metric("Regulatory ROE", f"{kr.get('regulatory_roe',0)*100:.1f}%")
                st.latex(r"KVA = CoC \times \int_0^T \mathbb{E}[EAD(t)]\, e^{-rt}\, dt")
            except Exception as e:
                st.error(f"Error: {e}")

    with frtb_tabs[3]:
        st.markdown("### ROE Solver — Minimum Spread")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: rs_n = st.number_input("Notional", value=10_000_000.0, step=1_000_000.0, key="rs_n")
        with c2: rs_m = st.number_input("Maturity (Y)", value=2.0, min_value=0.5, max_value=10.0, step=0.5, key="rs_m")
        with c3: rs_dc = st.number_input("Delta Cap.", value=50_000.0, step=5_000.0, key="rs_dc")
        with c4: rs_vc = st.number_input("Vega Cap.", value=20_000.0, step=5_000.0, key="rs_vc")
        with c5: rs_kv = st.number_input("KVA", value=30_000.0, step=5_000.0, key="rs_kv")
        rs_roe = st.slider("Target ROE (%)", 5.0, 25.0, 12.0, 1.0, key="rs_roe") / 100
        if st.button("Solve", key="rs_btn"):
            try:
                sol = RegulatoryROESolver().solve_minimum_spread(rs_n, rs_m, rs_dc, rs_vc, rs_kv, rs_roe)
                s1, s2, s3, s4 = st.columns(4)
                with s1: st.metric("Min Spread Required", f"{sol.get('min_spread_bps',0):.1f} bps")
                with s2: st.metric("Total Capital", f"${sol.get('total_capital',0):,.0f}")
                with s3: st.metric("Annual Cost", f"${sol.get('annual_cost',0):,.0f}")
                with s4:
                    if sol.get("viable"):
                        st.success("Viable Trade")
                    else:
                        st.error("Uneconomical")
            except Exception as e:
                st.error(f"Error: {e}")
