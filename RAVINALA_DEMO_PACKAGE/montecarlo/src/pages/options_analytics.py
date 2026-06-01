"""
Options Analytics — Unified options pricing, strategy, Greeks & scenario analysis
Fusion of: pricing_center + strategy_lab + greeks_sensitivity_lab + scenario_matrix
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header, get_sidebar_market_context

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from engine import BlackScholesGreeks

BSG = BlackScholesGreeks

# ── Theme ─────────────────────────────────────────────────────────────────────
_BG = "#0A0E1A"
_GRID = "rgba(255,255,255,0.05)"
_CYAN = "#00D9FF"
_GREEN = "#00FF9F"
_RED = "#FF4B4B"
_GOLD = "#FFD700"
_PURPLE = "#B44FFF"
_ORANGE = "#FF8C42"

_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(family="Inter, sans-serif", size=12, color="#E8ECF3"),
    margin=dict(l=60, r=20, t=50, b=50),
)

_render_page_header("OA", "Options Analytics",
                    "Pricing, strategy building, Greeks sensitivity & scenario matrices",
                    "Derivatives")

# ============================================================================
# TABS
# ============================================================================

tab_pricing, tab_strategy, tab_greeks, tab_scenario = st.tabs([
    "Pricing Center",
    "Strategy Lab",
    "Greeks & Sensitivity",
    "Scenario Matrix",
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — PRICING CENTER (from pricing_center.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_pricing:
    market_context = get_sidebar_market_context()
    spot_price = market_context.spot
    volatility = market_context.volatility
    rate = market_context.rate
    CURRENCY_SYMBOL = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥"}.get(
        market_context.currency, "$"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        strike = st.number_input("Strike Price (K)", value=100.0, step=0.1, min_value=0.1, key="pc_strike")
    with col2:
        time_to_expiry = st.number_input("Time to Expiry (Years)", value=1.0, step=0.1,
                                          min_value=0.01, max_value=10.0, key="pc_tte")
    with col3:
        option_type = st.radio("Option Type", ["Call", "Put"], horizontal=True, key="pc_otype")

    dividend_yield = st.slider("Dividend Yield (q)", 0.0, 0.10, 0.02, key="pc_div")
    carry = rate - dividend_yield

    bs = BlackScholesGreeks()

    if option_type == "Call":
        price = bs.call_price(spot_price, strike, time_to_expiry, rate, carry, volatility)
        delta = bs.delta(spot_price, strike, time_to_expiry, rate, carry, volatility, 'call')
        theta = bs.theta(spot_price, strike, time_to_expiry, rate, carry, volatility, 'call')
        rho = bs.rho(spot_price, strike, time_to_expiry, rate, carry, volatility, 'call')
    else:
        price = bs.put_price(spot_price, strike, time_to_expiry, rate, carry, volatility)
        delta = bs.delta(spot_price, strike, time_to_expiry, rate, carry, volatility, 'put')
        theta = bs.theta(spot_price, strike, time_to_expiry, rate, carry, volatility, 'put')
        rho = bs.rho(spot_price, strike, time_to_expiry, rate, carry, volatility, 'put')

    gamma = bs.gamma(spot_price, strike, time_to_expiry, rate, carry, volatility)
    vega = bs.vega(spot_price, strike, time_to_expiry, rate, carry, volatility)
    vanna = bs.vanna(spot_price, strike, time_to_expiry, rate, carry, volatility)
    volga = bs.volga(spot_price, strike, time_to_expiry, rate, carry, volatility)

    st.divider()
    st.markdown("### **Option Valuation**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Price", f"{CURRENCY_SYMBOL}{price:.2f}", f"{(price/strike - 1)*100:.1f}% of Strike")
    with col2:
        iv = max(spot_price - strike, 0) if option_type == "Call" else max(strike - spot_price, 0)
        st.metric("Intrinsic Value", f"{CURRENCY_SYMBOL}{iv:.2f}")
    with col3:
        st.metric("Time Value", f"{CURRENCY_SYMBOL}{price - iv:.2f}")
    with col4:
        st.metric("Moneyness", f"{(spot_price/strike):.2%}")

    st.markdown("### **Risk Greeks**")
    greek_cols = st.columns(4)
    greek_data = [
        ("Delta", delta), ("Gamma", gamma), ("Vega", vega), ("Theta", theta),
    ]
    for col, (label, value) in zip(greek_cols, greek_data):
        with col:
            st.metric(label, f"{value:.6f}")

    st.markdown("### **Advanced Greeks**")
    adv_cols = st.columns(3)
    for col, (label, value) in zip(adv_cols, [("Rho", rho), ("Vanna", vanna), ("Volga", volga)]):
        with col:
            st.metric(label, f"{value:.6f}")

    st.divider()

    # Heatmap: Spot vs Vol
    st.markdown("### **Risk Heatmap: Price Sensitivity (Spot vs Volatility)**")
    spot_range = np.linspace(spot_price * 0.7, spot_price * 1.3, 15)
    vol_range = np.linspace(max(0.05, volatility * 0.5), volatility * 2, 15)
    heatmap_data = np.zeros((len(vol_range), len(spot_range)))

    for i, vol in enumerate(vol_range):
        for j, spot in enumerate(spot_range):
            if option_type == "Call":
                heatmap_data[i, j] = bs.call_price(spot, strike, time_to_expiry, rate, carry, vol)
            else:
                heatmap_data[i, j] = bs.put_price(spot, strike, time_to_expiry, rate, carry, vol)

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data, x=np.round(spot_range, 2), y=np.round(vol_range * 100, 1),
        colorscale='Viridis', colorbar=dict(title=f"{option_type} Price")
    ))
    fig_heatmap.update_layout(
        title=f"{option_type} Price Sensitivity",
        xaxis_title="Spot Price", yaxis_title="Volatility (%)",
        height=500, template="plotly_dark"
    )
    st.plotly_chart(fig_heatmap)

    # Payoff diagram
    st.markdown("### **Payoff Diagram at Expiry**")
    spot_at_expiry = np.linspace(strike * 0.5, strike * 1.5, 100)
    if option_type == "Call":
        payoffs = [max(s - strike, 0) - price for s in spot_at_expiry]
    else:
        payoffs = [max(strike - s, 0) - price for s in spot_at_expiry]

    fig_payoff = go.Figure()
    fig_payoff.add_trace(go.Scatter(x=spot_at_expiry, y=payoffs, mode='lines',
                                     name='P&L at Expiry', line=dict(color=_CYAN, width=2)))
    fig_payoff.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    fig_payoff.update_layout(**_LAYOUT, height=400, xaxis_title="Spot at Expiry", yaxis_title="P&L")
    st.plotly_chart(fig_payoff, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — STRATEGY LAB (from strategy_lab.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_strategy:
    from strategy_lab import (
        Leg, fill_premiums, leg_greeks, net_greeks,
        payoff_at_expiry, payoff_today, breakevens,
        max_profit_loss, recognize_strategy
    )

    def _make_spots(legs, n=300):
        if not legs:
            return np.linspace(50, 200, n)
        ref = legs[0].spot
        lo = min(l.strike for l in legs) * 0.55
        hi = max(l.strike for l in legs) * 1.45
        lo = min(lo, ref * 0.60)
        hi = max(hi, ref * 1.40)
        return np.linspace(lo, hi, n)

    def _render_leg_table(legs):
        if not legs:
            return
        fill_premiums(legs)
        rows = []
        for i, leg in enumerate(legs):
            g = leg_greeks(leg)
            rows.append({
                "#": i + 1, "Dir": leg.direction.upper(), "Type": leg.option_type.capitalize(),
                "Qty": leg.quantity, "Strike": f"{leg.strike:.2f}",
                "Expiry (d)": int(leg.expiry * 365), "Vol %": f"{leg.vol*100:.1f}%",
                "Premium": f"{leg.premium:.4f}", "Delta": f"{g['delta']:.3f}",
                "Gamma": f"{g['gamma']:.5f}", "Vega": f"{g['vega']:.3f}", "Theta": f"{g['theta']:.4f}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    def _payoff_chart(legs, label=""):
        spots = _make_spots(legs)
        pnl_expiry = payoff_at_expiry(legs, spots)
        pnl_today = payoff_today(legs, spots, legs[0].expiry if legs else 0.25)
        be = breakevens(legs)
        mp, ml = max_profit_loss(legs, spots)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=spots, y=pnl_expiry, mode="lines", name="At Expiry",
                                  line=dict(color=_CYAN, width=2.5)))
        fig.add_trace(go.Scatter(x=spots, y=pnl_today, mode="lines", name="Today",
                                  line=dict(color=_GOLD, width=1.8, dash="dash")))
        fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.25)", width=1, dash="dot"))
        if legs:
            fig.add_vline(x=legs[0].spot, line=dict(color=_PURPLE, width=1.2, dash="dot"),
                          annotation_text="Spot", annotation_position="top")
        for be_val in be:
            fig.add_vline(x=be_val, line=dict(color=_GREEN, width=1, dash="dashdot"),
                          annotation_text=f"BE {be_val:.2f}", annotation_position="bottom right",
                          annotation_font_size=10)
        fig.add_trace(go.Scatter(x=spots, y=np.maximum(pnl_expiry, 0), fill="tozeroy",
                                  fillcolor="rgba(0,255,159,0.07)", line=dict(width=0),
                                  showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=spots, y=np.minimum(pnl_expiry, 0), fill="tozeroy",
                                  fillcolor="rgba(255,75,75,0.07)", line=dict(width=0),
                                  showlegend=False, hoverinfo="skip"))
        fig.update_layout(**_LAYOUT, title=f"Payoff Diagram{' — ' + label if label else ''}",
                          xaxis_title="Spot Price", yaxis_title="P&L ($)",
                          xaxis=dict(gridcolor=_GRID), yaxis=dict(gridcolor=_GRID),
                          legend=dict(orientation="h", y=1.06), height=420)
        if mp != float("inf") and mp > 0:
            fig.add_annotation(text=f"Max Profit: ${mp:,.0f}", xref="paper", yref="paper",
                               x=0.01, y=0.97, showarrow=False, font=dict(color=_GREEN, size=12))
        if ml != float("-inf") and ml < 0:
            fig.add_annotation(text=f"Max Loss: ${ml:,.0f}", xref="paper", yref="paper",
                               x=0.01, y=0.90, showarrow=False, font=dict(color=_RED, size=12))
        return fig

    def _greeks_chart(legs):
        if not legs:
            return go.Figure()
        fill_premiums(legs)
        names = [f"Leg {i+1} ({l.direction[0].upper()}{l.option_type[0].upper()} K={l.strike:.0f})"
                 for i, l in enumerate(legs)]
        deltas = [leg_greeks(l)["delta"] for l in legs]
        colors = [_GREEN if d >= 0 else _RED for d in deltas]
        fig = go.Figure(go.Bar(x=names, y=deltas, marker_color=colors,
                                text=[f"{d:.3f}" for d in deltas], textposition="outside"))
        fig.update_layout(**_LAYOUT, title="Delta by Leg", yaxis_title="Delta",
                          yaxis=dict(gridcolor=_GRID, zeroline=True, zerolinecolor="rgba(255,255,255,0.3)"),
                          height=320)
        return fig

    def _scenario_chart(legs, days_forward):
        spots = _make_spots(legs)
        if not legs:
            return go.Figure()
        T_max = legs[0].expiry
        times = [T_max, T_max * 0.75, T_max * 0.5, T_max * 0.25, 1.0 / 252.0]
        labels = ["At entry", "75% time", "50% time", "25% time", "At expiry"]
        palette = [_CYAN, _GOLD, _PURPLE, "#FF8C42", _GREEN]

        fig = go.Figure()
        for T_rem, label, color in zip(times, labels, palette):
            pnl = payoff_at_expiry(legs, spots) if T_rem == 1.0 / 252.0 else payoff_today(legs, spots, T_rem)
            fig.add_trace(go.Scatter(x=spots, y=pnl, mode="lines", name=label,
                                      line=dict(color=color, width=1.8)))
        T_sel = max(T_max - days_forward / 365.0, 1e-4)
        pnl_sel = payoff_today(legs, spots, T_sel)
        fig.add_trace(go.Scatter(x=spots, y=pnl_sel, mode="lines", name=f"Day +{days_forward}",
                                  line=dict(color="#FFFFFF", width=2.5)))
        fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"))
        if legs:
            fig.add_vline(x=legs[0].spot, line=dict(color=_PURPLE, width=1, dash="dot"))
        fig.update_layout(**_LAYOUT, title="Payoff Evolution Over Time",
                          xaxis_title="Spot Price", yaxis_title="P&L ($)",
                          xaxis=dict(gridcolor=_GRID), yaxis=dict(gridcolor=_GRID),
                          legend=dict(orientation="h", y=1.06), height=420)
        return fig

    def _init_legs_state(key):
        if key not in st.session_state:
            st.session_state[key] = []

    def _add_leg_form(key, spot_default, rate_default, vol_default, div_default):
        with st.expander("+ Add Leg", expanded=len(st.session_state[key]) == 0):
            c1, c2, c3, c4 = st.columns(4)
            direction = c1.selectbox("Direction", ["long", "short"], key=f"{key}_dir")
            otype = c2.selectbox("Type", ["call", "put", "stock"], key=f"{key}_type")
            qty = c3.number_input("Qty", min_value=1, max_value=100, value=1, key=f"{key}_qty")
            strike_l = c4.number_input("Strike", min_value=0.01, value=float(spot_default),
                                        step=1.0, key=f"{key}_K")
            c5, c6, c7, c8 = st.columns(4)
            expiry_days = c5.number_input("Expiry (days)", min_value=1, max_value=3650,
                                           value=30, key=f"{key}_exp")
            vol_override = c6.number_input("Vol %", min_value=0.1, max_value=500.0,
                                            value=vol_default * 100, step=0.5, key=f"{key}_vol")
            premium_override = c7.number_input("Premium (0=BS)", min_value=0.0, value=0.0,
                                                step=0.01, key=f"{key}_prem")
            if st.button("Add Leg", key=f"{key}_add_btn"):
                leg = Leg(direction=direction, option_type=otype, quantity=qty,
                          strike=strike_l, expiry=expiry_days / 365.0, spot=spot_default,
                          vol=vol_override / 100.0, rate=rate_default, div_yield=div_default,
                          premium=premium_override if premium_override > 0 else None)
                st.session_state[key].append(leg)
                st.rerun()

    def _render_strategy_block(key, spot, rate_s, vol, div):
        _init_legs_state(key)
        for leg in st.session_state[key]:
            leg.spot = spot
            leg.rate = rate_s
            leg.div_yield = div

        legs = st.session_state[key]
        name = recognize_strategy(legs)
        if legs:
            fill_premiums(legs)
            st.info(f"**Strategy recognised:** {name} | {len(legs)} leg(s)")

        _render_leg_table(legs)

        if legs:
            col_del, col_clr = st.columns([3, 1])
            idx_del = col_del.number_input("Remove leg #", min_value=1, max_value=len(legs),
                                            value=1, step=1, key=f"{key}_del_idx")
            if col_del.button("Remove", key=f"{key}_del_btn"):
                st.session_state[key].pop(idx_del - 1)
                st.rerun()
            if col_clr.button("Clear All", key=f"{key}_clr_btn"):
                st.session_state[key] = []
                st.rerun()

        _add_leg_form(key, spot, rate_s, vol, div)

    # Strategy Lab main UI
    st.markdown("### Global Parameters")
    gc1, gc2, gc3, gc4 = st.columns(4)
    spot_g = gc1.number_input("Spot Price", min_value=0.01, value=100.0, step=1.0, key="slab_spot")
    rate_g = gc2.number_input("Risk-free Rate %", min_value=0.0, max_value=30.0, value=5.0,
                               step=0.1, key="slab_rate") / 100.0
    vol_g = gc3.number_input("Implied Vol %", min_value=0.1, max_value=500.0, value=25.0,
                              step=0.5, key="slab_vol") / 100.0
    div_g = gc4.number_input("Div Yield %", min_value=0.0, max_value=30.0, value=0.0,
                              step=0.1, key="slab_div") / 100.0

    st.divider()

    mode = st.radio("Mode", ["Single Strategy", "Compare A vs B"], horizontal=True, key="slab_mode")

    if mode == "Single Strategy":
        _render_strategy_block("slab_legs", spot_g, rate_g, vol_g, div_g)
        legs = st.session_state.get("slab_legs", [])

        if not legs:
            st.info("Add at least one leg to see the payoff diagram.")
        else:
            stab1, stab2, stab3 = st.tabs(["Payoff Diagram", "Greeks Dashboard", "Scenario"])
            with stab1:
                st.plotly_chart(_payoff_chart(legs), use_container_width=True)
                be = breakevens(legs)
                mp, ml = max_profit_loss(legs, _make_spots(legs))
                m1, m2, m3 = st.columns(3)
                m1.metric("Breakeven(s)", ", ".join(f"{b:.2f}" for b in be) if be else "None")
                m2.metric("Max Profit", f"${mp:,.2f}" if mp < 1e8 else "Unlimited")
                m3.metric("Max Loss", f"${ml:,.2f}" if ml > -1e8 else "Unlimited")

            with stab2:
                fill_premiums(legs)
                ng = net_greeks(legs)
                cols_g = st.columns(6)
                cols_g[0].metric("Net Delta", f"{ng['delta']:.4f}")
                cols_g[1].metric("Net Gamma", f"{ng['gamma']:.6f}")
                cols_g[2].metric("Net Vega", f"{ng['vega']:.4f}")
                cols_g[3].metric("Net Theta", f"{ng['theta']:.4f}")
                cols_g[4].metric("Net Rho", f"{ng['rho']:.4f}")
                cols_g[5].metric("Vanna", f"{ng['vanna']:.5f}")
                st.plotly_chart(_greeks_chart(legs), use_container_width=True)

                rows = []
                for i, leg in enumerate(legs):
                    g = leg_greeks(leg)
                    rows.append({"Leg": f"#{i+1} {leg.direction.upper()} {leg.option_type.capitalize()} K={leg.strike:.2f}",
                                  **{k: round(v, 6) for k, v in g.items() if k != "price"}})
                rows.append({"Leg": "NET", **{k: round(v, 6) for k, v in ng.items()}})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            with stab3:
                days_fwd = st.slider("Days Forward", min_value=1,
                                      max_value=max(int(legs[0].expiry * 365), 2),
                                      value=max(int(legs[0].expiry * 365 // 2), 1),
                                      key="slab_days_fwd")
                st.plotly_chart(_scenario_chart(legs, days_fwd), use_container_width=True)

    else:  # Compare A vs B
        colA, colB = st.columns(2)
        with colA:
            st.markdown("#### Strategy A")
            _render_strategy_block("slab_legs_A", spot_g, rate_g, vol_g, div_g)
        with colB:
            st.markdown("#### Strategy B")
            _render_strategy_block("slab_legs_B", spot_g, rate_g, vol_g, div_g)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — GREEKS & SENSITIVITY (from greeks_sensitivity_lab.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_greeks:
    with st.expander("Position Parameters", expanded=True):
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        S = c1.number_input("Spot (S)", min_value=0.01, value=100.0, step=1.0, key="gl_S")
        K_g = c2.number_input("Strike (K)", min_value=0.01, value=100.0, step=1.0, key="gl_K")
        T_days = c3.number_input("Expiry (days)", min_value=1, value=90, step=1, key="gl_Td")
        r_pct = c4.number_input("Rate %", min_value=0.0, value=5.0, step=0.1, key="gl_r")
        sig_pct = c5.number_input("Vol %", min_value=0.1, value=25.0, step=0.5, key="gl_sig")
        div_pct_g = c6.number_input("Div Yield %", min_value=0.0, value=0.0, step=0.1, key="gl_div")
        otype_g = c7.radio("Type", ["call", "put"], key="gl_otype")

    T = max(T_days / 365.0, 1e-6)
    r_val = r_pct / 100.0
    sigma_val = sig_pct / 100.0
    div_val = div_pct_g / 100.0
    b_val = r_val - div_val

    p_g = BSG.call_price(S, K_g, T, r_val, b_val, sigma_val) if otype_g == "call" else BSG.put_price(S, K_g, T, r_val, b_val, sigma_val)
    d_g = BSG.delta(S, K_g, T, r_val, b_val, sigma_val, option_type=otype_g)
    g_g = BSG.gamma(S, K_g, T, r_val, b_val, sigma_val)
    v_g = BSG.vega(S, K_g, T, r_val, b_val, sigma_val)
    t_g = BSG.theta(S, K_g, T, r_val, b_val, sigma_val, option_type=otype_g)
    rho_g = BSG.rho(S, K_g, T, r_val, b_val, sigma_val, option_type=otype_g)
    vanna_g = BSG.vanna(S, K_g, T, r_val, b_val, sigma_val)
    volga_g = BSG.volga(S, K_g, T, r_val, b_val, sigma_val)

    st.divider()

    gtab1, gtab2, gtab3, gtab4 = st.tabs(["Greeks Dashboard", "Sensitivity Profiles", "Heatmaps", "P&L Attribution"])

    with gtab1:
        m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
        m1.metric("Price", f"{p_g:.4f}")
        m2.metric("Delta", f"{d_g:.4f}")
        m3.metric("Gamma", f"{g_g:.6f}")
        m4.metric("Vega", f"{v_g:.4f}")
        m5.metric("Theta", f"{t_g:.4f}")
        m6.metric("Rho", f"{rho_g:.4f}")
        m7.metric("Vanna", f"{vanna_g:.5f}")

        st.divider()

        spot_range_g = np.linspace(S * 0.5, S * 1.5, 200)
        d_arr = np.array([BSG.delta(float(s), K_g, T, r_val, b_val, sigma_val, option_type=otype_g) for s in spot_range_g])
        g_arr = np.array([BSG.gamma(float(s), K_g, T, r_val, b_val, sigma_val) for s in spot_range_g])
        v_arr = np.array([BSG.vega(float(s), K_g, T, r_val, b_val, sigma_val) for s in spot_range_g])
        th_arr = np.array([BSG.theta(float(s), K_g, T, r_val, b_val, sigma_val, option_type=otype_g) for s in spot_range_g])
        p_arr = np.array([BSG.call_price(float(s), K_g, T, r_val, b_val, sigma_val) if otype_g == "call"
                          else BSG.put_price(float(s), K_g, T, r_val, b_val, sigma_val) for s in spot_range_g])

        fig_gr = make_subplots(rows=2, cols=3, shared_xaxes=False, vertical_spacing=0.12,
                                horizontal_spacing=0.08,
                                subplot_titles=["Price", "Delta", "Gamma", "Vega", "Theta", "Vanna"])

        SERIES = [
            (p_arr, _CYAN, 1, 1), (d_arr, _GREEN, 1, 2), (g_arr, _GOLD, 1, 3),
            (v_arr, _PURPLE, 2, 1), (th_arr, _RED, 2, 2),
            (np.array([BSG.vanna(float(s), K_g, T, r_val, b_val, sigma_val) for s in spot_range_g]), _ORANGE, 2, 3),
        ]
        for arr, color, row, col in SERIES:
            fig_gr.add_trace(go.Scatter(x=spot_range_g, y=arr, mode="lines",
                                         line=dict(color=color, width=2), showlegend=False), row=row, col=col)
            fig_gr.add_vline(x=S, line=dict(color="#475569", width=1, dash="dot"), row=row, col=col)
            fig_gr.add_vline(x=K_g, line=dict(color="#334155", width=1, dash="dash"), row=row, col=col)

        fig_gr.update_layout(**_LAYOUT, height=520,
                              title=dict(text=f"All Greeks vs Spot — {otype_g.upper()} K={K_g} T={T_days}d"))
        st.plotly_chart(fig_gr, use_container_width=True)

        tbl = pd.DataFrame({
            "Greek": ["Price", "Delta", "Gamma", "Vega", "Theta", "Rho", "Vanna", "Volga"],
            "Value": [f"{x:.6f}" for x in [p_g, d_g, g_g, v_g, t_g, rho_g, vanna_g, volga_g]],
        })
        st.dataframe(tbl, use_container_width=True, hide_index=True)
        csv_g = tbl.to_csv(index=False)
        st.download_button("Download Greeks (CSV)", csv_g,
                           file_name=f"greeks_{otype_g}_K{K_g}_T{T_days}.csv", mime="text/csv")

    with gtab2:
        def _compute_greek(greek, S_, K_, T_, r_, b_, sig_):
            sig_ = max(sig_, 1e-6)
            T_ = max(T_, 1e-6)
            funcs = {
                "Price": lambda: BSG.call_price(S_, K_, T_, r_, b_, sig_) if otype_g == "call" else BSG.put_price(S_, K_, T_, r_, b_, sig_),
                "Delta": lambda: BSG.delta(S_, K_, T_, r_, b_, sig_, option_type=otype_g),
                "Gamma": lambda: BSG.gamma(S_, K_, T_, r_, b_, sig_),
                "Vega": lambda: BSG.vega(S_, K_, T_, r_, b_, sig_),
                "Theta": lambda: BSG.theta(S_, K_, T_, r_, b_, sig_, option_type=otype_g),
                "Rho": lambda: BSG.rho(S_, K_, T_, r_, b_, sig_, option_type=otype_g),
                "Vanna": lambda: BSG.vanna(S_, K_, T_, r_, b_, sig_),
                "Volga": lambda: BSG.volga(S_, K_, T_, r_, b_, sig_),
            }
            return funcs.get(greek, lambda: 0.0)()

        profile_axis = st.radio("Vary", ["Spot", "Volatility", "Time to Expiry", "Rate"],
                                horizontal=True, key="gl_profile_axis")
        greek_sel = st.selectbox("Greek to display",
                                 ["Price", "Delta", "Gamma", "Vega", "Theta", "Rho", "Vanna", "Volga"],
                                 key="gl_greek_sel")

        if profile_axis == "Spot":
            x_range = np.linspace(S * 0.4, S * 1.6, 200)
            y_vals = np.array([_compute_greek(greek_sel, float(x), K_g, T, r_val, b_val, sigma_val) for x in x_range])
            x_label, ref_val = "Spot Price", S
        elif profile_axis == "Volatility":
            x_range = np.linspace(0.01, 1.5, 200)
            y_vals = np.array([_compute_greek(greek_sel, S, K_g, T, r_val, r_val - div_val, float(x)) for x in x_range])
            x_label, ref_val = "Volatility", sigma_val
        elif profile_axis == "Time to Expiry":
            x_range = np.linspace(0.01, max(T * 3, 2.0), 200)
            y_vals = np.array([_compute_greek(greek_sel, S, K_g, float(x), r_val, b_val, sigma_val) for x in x_range])
            x_label, ref_val = "Time to Expiry (years)", T
        else:
            x_range = np.linspace(0.0, 0.15, 200)
            y_vals = np.array([_compute_greek(greek_sel, S, K_g, T, float(x), float(x) - div_val, sigma_val) for x in x_range])
            x_label, ref_val = "Risk-free Rate", r_val

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=x_range, y=y_vals, mode="lines",
                                   line=dict(color=_CYAN, width=2.5), name=greek_sel,
                                   fill="tozeroy", fillcolor="rgba(0,217,255,0.06)"))
        fig2.add_vline(x=ref_val, line=dict(color="#94A3B8", width=1, dash="dot"),
                       annotation_text=f"Current ({ref_val:.3g})")
        fig2.update_layout(**_LAYOUT, height=440, xaxis=dict(title=x_label, gridcolor=_GRID),
                           yaxis=dict(title=greek_sel, gridcolor=_GRID),
                           title=dict(text=f"{greek_sel} vs {profile_axis} — {otype_g.upper()} K={K_g}"))
        st.plotly_chart(fig2, use_container_width=True)

    with gtab3:
        metric_h = st.selectbox("Metric", ["Price", "Delta", "Gamma", "Vega", "Theta", "Rho"],
                                 key="gl_hm_metric")
        hc1, hc2, hc3, hc4 = st.columns(4)
        n_sp = hc1.slider("Spot points", 7, 21, 13, step=2, key="gl_nsp")
        sp_rng = hc2.slider("Spot range +/-%", 10, 50, 30, step=5, key="gl_sprng")
        n_vl = hc3.slider("Vol points", 5, 15, 11, step=2, key="gl_nvl")
        vl_rng = hc4.slider("Vol range +/-%", 20, 100, 50, step=10, key="gl_vlrng")

        spot_moves = np.linspace(-sp_rng / 100, sp_rng / 100, n_sp)
        vol_moves = np.linspace(-vl_rng / 100, vl_rng / 100, n_vl)

        matrix = np.empty((len(spot_moves), len(vol_moves)), dtype=float)
        for i, ds in enumerate(spot_moves):
            S_new = S * (1.0 + ds)
            for j, dv in enumerate(vol_moves):
                sig_new = max(sigma_val * (1.0 + dv), 1e-6)
                matrix[i, j] = _compute_greek(metric_h, S_new, K_g, T, r_val, b_val, sig_new)

        x_lbl = [f"{v*100:+.0f}%" for v in vol_moves]
        y_lbl = [f"{v*100:+.0f}%" for v in spot_moves]

        fig4 = go.Figure(go.Heatmap(
            z=matrix, x=x_lbl, y=y_lbl, colorscale="Viridis",
            text=[[f"{matrix[i,j]:+.4f}" if abs(matrix[i,j]) < 100 else f"{matrix[i,j]:+.2f}"
                   for j in range(len(vol_moves))] for i in range(len(spot_moves))],
            texttemplate="%{text}",
            colorbar=dict(thickness=12, tickfont=dict(color="#94A3B8", size=10)),
        ))
        fig4.update_layout(**_LAYOUT, height=500, xaxis=dict(title="Vol change"),
                           yaxis=dict(title="Spot change"),
                           title=dict(text=f"{metric_h} — Spot x Vol scenario matrix | {otype_g.upper()} K={K_g} T={T_days}d"))
        st.plotly_chart(fig4, use_container_width=True)

    with gtab4:
        st.markdown("Taylor decomposition: dP = d*dS + 1/2*G*dS^2 + v*dsig + Th*dt + Vanna*dS*dsig + 1/2*Volga*dsig^2 + residual")
        ac1, ac2, ac3 = st.columns(3)
        S_prev = ac1.number_input("Previous Spot", value=S * 0.98, step=0.5, key="gl_Sprev")
        sig_prev = ac2.number_input("Previous Vol %", value=sig_pct - 1.0, step=0.5, key="gl_sigprev") / 100.0
        dt_days_a = ac3.number_input("Days elapsed", value=1, min_value=1, step=1, key="gl_dt")

        sig_prev = max(sig_prev, 1e-6)
        T_prev = T + dt_days_a / 365.0

        p0 = BSG.call_price(S_prev, K_g, T_prev, r_val, b_val, sig_prev) if otype_g == "call" else BSG.put_price(S_prev, K_g, T_prev, r_val, b_val, sig_prev)
        dS = S - S_prev
        dsigma = sigma_val - sig_prev

        d0 = BSG.delta(S_prev, K_g, T_prev, r_val, b_val, sig_prev, option_type=otype_g)
        g0 = BSG.gamma(S_prev, K_g, T_prev, r_val, b_val, sig_prev)
        v0 = BSG.vega(S_prev, K_g, T_prev, r_val, b_val, sig_prev)
        t0 = BSG.theta(S_prev, K_g, T_prev, r_val, b_val, sig_prev, option_type=otype_g)
        va0 = BSG.vanna(S_prev, K_g, T_prev, r_val, b_val, sig_prev)
        vg0 = BSG.volga(S_prev, K_g, T_prev, r_val, b_val, sig_prev)

        delta_pnl_a = d0 * dS
        gamma_pnl_a = 0.5 * g0 * dS ** 2
        vega_pnl_a = v0 * dsigma * 100.0
        theta_pnl_a = t0 * dt_days_a
        vanna_pnl_a = va0 * dS * dsigma * 100.0
        volga_pnl_a = 0.5 * vg0 * (dsigma * 100.0) ** 2
        actual_pnl_a = p_g - p0
        total_taylor = delta_pnl_a + gamma_pnl_a + vega_pnl_a + theta_pnl_a + vanna_pnl_a + volga_pnl_a
        residual_a = actual_pnl_a - total_taylor

        labels_a = ["Start", "Delta", "Gamma", "Vega", "Theta", "Vanna", "Volga", "Residual", "End"]
        values_a = [p0, delta_pnl_a, gamma_pnl_a, vega_pnl_a, theta_pnl_a, vanna_pnl_a, volga_pnl_a, residual_a, p_g]
        measures_a = ["absolute"] + ["relative"] * 6 + ["relative", "total"]

        fig_wf = go.Figure(go.Waterfall(
            x=labels_a, y=values_a, measure=measures_a,
            increasing=dict(marker=dict(color=_GREEN)),
            decreasing=dict(marker=dict(color=_RED)),
            totals=dict(marker=dict(color=_CYAN)),
            connector=dict(line=dict(color=_GRID)),
            text=[f"${v:,.4f}" for v in values_a], textposition="outside",
        ))
        fig_wf.update_layout(**_LAYOUT, height=420, title="P&L Attribution Waterfall",
                              yaxis=dict(gridcolor=_GRID))
        st.plotly_chart(fig_wf, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — SCENARIO MATRIX (from scenario_matrix.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_scenario:
    from scenario_matrix import (
        build_scenario_matrix, greeks_vs_spot,
        greeks_surface_3d, vol_surface_3d, term_structure
    )

    with st.expander("Position Parameters", expanded=True):
        c1s, c2s, c3s, c4s, c5s, c6s = st.columns(6)
        S_s = c1s.number_input("Spot (S)", min_value=0.01, value=100.0, step=1.0, key="sm_S")
        K_s = c2s.number_input("Strike (K)", min_value=0.01, value=100.0, step=1.0, key="sm_K")
        T_days_s = c3s.number_input("Expiry (days)", min_value=1, max_value=3650, value=30, key="sm_Td")
        r_pct_s = c4s.number_input("Rate %", min_value=0.0, max_value=30.0, value=5.0, step=0.1, key="sm_r")
        sig_pct_s = c5s.number_input("Vol %", min_value=0.1, max_value=500.0, value=25.0, step=0.5, key="sm_sig")
        div_pct_s = c6s.number_input("Div Yield %", min_value=0.0, max_value=30.0, value=0.0, step=0.1, key="sm_div")
        otype_s = st.radio("Option Type", ["call", "put"], horizontal=True, key="sm_otype")

    T_s = T_days_s / 365.0
    r_s = r_pct_s / 100.0
    sigma_s = sig_pct_s / 100.0
    div_s = div_pct_s / 100.0

    st.divider()

    smtab1, smtab2, smtab3, smtab4, smtab5 = st.tabs([
        "2D Heatmap", "3D Greeks Surface", "Vol x Spot Surface", "Greeks vs Spot", "Term Structure"
    ])

    with smtab1:
        col_m, col_sr, col_vr, col_ns, col_nv = st.columns(5)
        metric_sm = col_m.selectbox("Metric", ["price","delta","gamma","vega","theta","rho","vanna","volga"], key="sm_metric")
        sp_range_sm = col_sr.slider("Spot Range +/-%", 5, 50, 30, key="sm_spr")
        vl_range_sm = col_vr.slider("Vol Range +/-%", 10, 80, 40, key="sm_vlr")
        n_sp_sm = col_ns.slider("# Spot pts", 8, 25, 12, key="sm_nsp")
        n_vl_sm = col_nv.slider("# Vol pts", 8, 25, 12, key="sm_nvl")

        matrix_df, spots_arr, vols_arr = build_scenario_matrix(
            S_s, K_s, T_s, r_s, sigma_s, otype_s, div_s,
            spot_range_pct=sp_range_sm/100, vol_range_pct=vl_range_sm/100,
            n_spots=n_sp_sm, n_vols=n_vl_sm, metric=metric_sm
        )

        z = matrix_df.values.astype(float)
        fig_hm = go.Figure(go.Heatmap(
            z=z, x=matrix_df.columns.tolist(), y=matrix_df.index.tolist(),
            colorscale="RdYlGn", zmid=0 if metric_sm not in ["price","gamma","vega"] else None,
            text=[[f"{v:.4f}" for v in row] for row in z], texttemplate="%{text}",
            textfont=dict(size=9), colorbar=dict(title=metric_sm.capitalize()),
        ))
        fig_hm.update_layout(**_LAYOUT, title=f"{metric_sm.capitalize()} — Spot x Vol Scenario Matrix",
                              xaxis_title="Spot Price", yaxis_title="Implied Vol", height=500)
        st.plotly_chart(fig_hm, use_container_width=True)

        with st.expander("Raw matrix table"):
            st.dataframe(matrix_df.style.background_gradient(cmap="RdYlGn", axis=None), use_container_width=True)

    with smtab2:
        c_g, c_sr2, c_t = st.columns(3)
        greek3d = c_g.selectbox("Greek", ["delta","gamma","vega","theta","rho","price","vanna","volga"], key="g3d")
        sp_r2 = c_sr2.slider("Spot Range +/-%", 5, 50, 25, key="sr3d")
        t_max = c_t.slider("Max Expiry (years)", 0.1, 3.0, 1.0, step=0.1, key="sm_tmax")

        spots3d, times3d, surf3d = greeks_surface_3d(
            S_s, K_s, r_s, sigma_s, otype_s, div_s, greek3d,
            spot_range_pct=sp_r2/100, n_spots=35, n_times=25, T_max=t_max
        )

        fig_3d = go.Figure(go.Surface(
            x=spots3d, y=times3d, z=surf3d.T, colorscale="Plasma",
            colorbar=dict(title=greek3d.capitalize()),
            contours=dict(z=dict(show=True, usecolormap=True, highlightcolor="#00D9FF", project_z=True)),
        ))
        fig_3d.update_layout(**_LAYOUT, title=f"{greek3d.capitalize()} Surface — Spot x Time to Expiry",
                              scene=dict(
                                  xaxis=dict(title="Spot", backgroundcolor=_BG, gridcolor=_GRID),
                                  yaxis=dict(title="Time (yrs)", backgroundcolor=_BG, gridcolor=_GRID),
                                  zaxis=dict(title=greek3d.capitalize(), backgroundcolor=_BG, gridcolor=_GRID),
                                  bgcolor=_BG,
                              ), height=560)
        st.plotly_chart(fig_3d, use_container_width=True)

    with smtab3:
        c_gv, c_srv, c_vrv = st.columns(3)
        greek_vs = c_gv.selectbox("Metric", ["price","delta","gamma","vega","theta","rho"], key="gvs")
        sp_rv = c_srv.slider("Spot Range +/-%", 5, 50, 25, key="sprvs")
        vl_rv = c_vrv.slider("Vol Range +/-%", 10, 80, 40, key="vlrvs")

        spots_vs, vols_vs, surf_vs = vol_surface_3d(
            S_s, K_s, r_s, otype_s, div_s, greek_vs,
            spot_range_pct=sp_rv/100, vol_range_pct=vl_rv/100,
            sigma_center=sigma_s, n_spots=30, n_vols=25, T=T_s
        )

        fig_vs = go.Figure(go.Surface(
            x=spots_vs, y=vols_vs, z=surf_vs.T, colorscale="Viridis",
            colorbar=dict(title=greek_vs.capitalize()),
        ))
        fig_vs.update_layout(**_LAYOUT, title=f"{greek_vs.capitalize()} — Spot x Vol",
                              scene=dict(
                                  xaxis=dict(title="Spot", backgroundcolor=_BG, gridcolor=_GRID),
                                  yaxis=dict(title="Vol", backgroundcolor=_BG, gridcolor=_GRID),
                                  zaxis=dict(title=greek_vs.capitalize(), backgroundcolor=_BG, gridcolor=_GRID),
                                  bgcolor=_BG,
                              ), height=520)
        st.plotly_chart(fig_vs, use_container_width=True)

    with smtab4:
        gvs_df = greeks_vs_spot(S_s, K_s, T_s, r_s, sigma_s, otype_s, div_s, n_spots=150)

        fig_gvs = make_subplots(specs=[[{"secondary_y": True}]])
        colors_map = {"delta": _CYAN, "gamma": _GOLD, "vega": _ORANGE, "theta": _PURPLE, "rho": _GREEN}

        for greek_name, color in colors_map.items():
            fig_gvs.add_trace(
                go.Scatter(x=gvs_df["spot"], y=gvs_df[greek_name],
                           name=greek_name.capitalize(), line=dict(color=color, width=1.8)),
                secondary_y=False,
            )

        fig_gvs.add_trace(
            go.Scatter(x=gvs_df["spot"], y=gvs_df["price"],
                       name="Price", line=dict(color="#FFFFFF", width=2, dash="dash")),
            secondary_y=True,
        )
        fig_gvs.add_vline(x=S_s, line=dict(color=_PURPLE, width=1.5, dash="dot"),
                          annotation_text="Spot", annotation_position="top")
        fig_gvs.add_vline(x=K_s, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"),
                          annotation_text="K", annotation_position="bottom")

        fig_gvs.update_layout(**_LAYOUT, title="All Greeks vs Spot Price",
                               xaxis_title="Spot", height=460, legend=dict(orientation="h", y=1.08))
        fig_gvs.update_yaxes(title_text="Greek Value", secondary_y=False, gridcolor=_GRID)
        fig_gvs.update_yaxes(title_text="Option Price", secondary_y=True, gridcolor=_GRID)
        st.plotly_chart(fig_gvs, use_container_width=True)

    with smtab5:
        ts_data = term_structure(S_s, K_s, r_s, sigma_s, otype_s, div_s)
        if ts_data is not None and not ts_data.empty:
            fig_ts = go.Figure()
            for col_name in [c for c in ts_data.columns if c != "expiry"]:
                fig_ts.add_trace(go.Scatter(x=ts_data["expiry"], y=ts_data[col_name],
                                             mode="lines", name=col_name.capitalize()))
            fig_ts.update_layout(**_LAYOUT, title="Greeks Term Structure",
                                  xaxis_title="Expiry (years)", height=400)
            st.plotly_chart(fig_ts, use_container_width=True)
        else:
            st.info("Term structure data not available.")
