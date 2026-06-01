"""
Risk & Portfolio Suite — Unified risk, position management, hedging, backtesting & P&L attribution
Fusion of: risk_management + position_book + hedging_page + backtesting_page + pnl_attribution
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone, timedelta

_render_page_header("RP", "Risk & Portfolio Suite",
                    "Risk analytics, position book, hedging, backtesting & P&L attribution",
                    "Risk")

# ── Theme constants ───────────────────────────────────────────────────────────
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

# ============================================================================
# TABS
# ============================================================================

tab_risk, tab_book, tab_hedge, tab_bt, tab_pnl = st.tabs([
    "Risk Analytics",
    "Position Book",
    "Hedging",
    "Backtesting",
    "P&L Attribution",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — RISK ANALYTICS (from risk_management.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_risk:
    from risk import RiskAnalytics, PortfolioRisk

    risk_section = st.radio("Risk Analysis Mode",
                           ["VaR Analysis", "Stress Scenarios", "Risk Decomposition", "Portfolio Risk"],
                           horizontal=True, key="rps_risk_mode")

    if risk_section == "VaR Analysis":
        st.markdown("### Value-at-Risk Calculation")
        col1, col2, col3 = st.columns(3)
        with col1:
            confidence = st.slider("VaR Confidence Level", 0.90, 0.99, 0.95, 0.01, key="rps_var_conf")
        with col2:
            num_days = st.slider("Lookback Period (days)", 30, 500, 252, key="rps_var_days")
        with col3:
            portfolio_value = st.number_input("Portfolio Value (€)", 100000, 10000000, 1000000, key="rps_var_pv")

        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.015, num_days)

        var_hist = RiskAnalytics.value_at_risk_historical(returns, confidence)
        var_param = RiskAnalytics.value_at_risk_parametric(returns, confidence, portfolio_value)
        cvar = RiskAnalytics.conditional_var(returns, confidence)

        c1, c2, c3 = st.columns(3)
        c1.metric("VaR (Historical)", f"€{var_hist[1]:,.0f}", f"{var_hist[0]:.2%}")
        c2.metric("VaR (Parametric)", f"€{var_param[1]:,.0f}", f"{var_param[0]:.2%}")
        c3.metric("CVaR (Expected Shortfall)", f"€{cvar[1]:,.0f}", f"{cvar[0]:.2%}")

        fig_r = go.Figure()
        fig_r.add_trace(go.Histogram(x=returns*100, nbinsx=50, name="Daily Returns %",
                                     marker_color='rgba(55,83,109,0.7)'))
        fig_r.add_vline(x=var_hist[0]*100, line_dash="dash", line_color="red",
                       annotation_text=f"VaR {confidence:.0%}")
        fig_r.update_layout(title="Returns Distribution with VaR Threshold",
                           xaxis_title="Daily Return (%)", yaxis_title="Frequency",
                           template="plotly_dark", height=400)
        st.plotly_chart(fig_r, use_container_width=True)

    elif risk_section == "Stress Scenarios":
        st.markdown("### Stress Testing — Single & Multiple Shocks")
        c1, c2 = st.columns(2)
        with c1:
            stress_type = st.selectbox("Stress Type",
                                      ["Single Shock (Spot)", "Single Shock (Vol)",
                                       "Multiple Shocks", "Historical Scenarios"], key="rps_stress_type")
        with c2:
            shock_magnitude = st.slider("Shock Magnitude (%)", -50, 50, -20, key="rps_shock_mag")

        spot_shock_val = shock_magnitude / 100
        scenario_results = RiskAnalytics.stress_test_scenario(
            spot=100, strike=100, T=1.0, r=0.05, vol=0.2, carry=0.05,
            spot_shock=spot_shock_val
        )
        call_pnl = scenario_results.get('call_pnl_combined', 0)
        put_pnl = scenario_results.get('put_pnl_combined', 0)
        st.info(f"Call P&L: €{call_pnl:,.2f} | Put P&L: €{put_pnl:,.2f} | Shock: {spot_shock_val*100:+.1f}%")

    elif risk_section == "Risk Decomposition":
        st.markdown("### Greeks-Based Risk Decomposition")
        c1, c2, c3 = st.columns(3)
        with c1:
            spot_shock = st.slider("Spot Price Shock (%)", -20, 20, 0, key="rps_sp_sh")
        with c2:
            vol_shock = st.slider("Volatility Shock (%)", -20, 20, 0, key="rps_vol_sh")
        with c3:
            theta_days = st.slider("Time Decay (days)", 1, 30, 1, key="rps_th_d")

        decomp = RiskAnalytics.risk_decomposition(
            spot=100, strike=100, T=0.5, r=0.05, vol=0.2, carry=0.05,
            option_type='call'
        )
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Delta (-1%)", f"€{decomp.get('-1% Spot', 0):.2f}")
        c2.metric("Delta (+1%)", f"€{decomp.get('+1% Spot', 0):.2f}")
        c3.metric("Gamma Risk", f"€{decomp.get('Gamma Risk (1% move)', 0):.2f}")
        c4.metric("Vega (+100bps)", f"€{decomp.get('+100bps Vol', 0):.2f}")
        c5.metric("Theta (1d)", f"€{decomp.get('1 Day Decay', 0):.2f}")
        c6.metric("Rho (+100bps)", f"€{decomp.get('+100bps Rate', 0):.2f}")

        att = {
            'Delta +1%': abs(decomp.get('+1% Spot', 0)),
            'Gamma': abs(decomp.get('Gamma Risk (1% move)', 0)),
            'Vega': abs(decomp.get('+100bps Vol', 0)),
            'Theta': abs(decomp.get('1 Day Decay', 0)),
            'Rho': abs(decomp.get('+100bps Rate', 0)),
        }
        fig_pie = go.Figure(data=[go.Pie(labels=list(att.keys()), values=list(att.values()),
                                         marker_colors=['#FF6B6B','#4ECDC4','#45B7D1','#FFA07A','#98D8C8'])])
        fig_pie.update_layout(title="P&L Attribution by Greek", template="plotly_dark", height=400)
        st.plotly_chart(fig_pie, use_container_width=True)

    else:  # Portfolio Risk
        st.markdown("### Multi-Position Portfolio Risk Analysis")
        c1, c2 = st.columns(2)
        with c1:
            num_positions = st.slider("Number of Positions", 1, 10, 3, key="rps_npos")
        with c2:
            portfolio_correlation = st.slider("Average Correlation", -0.5, 1.0, 0.3, key="rps_corr")

        st.info(f"Analysing {num_positions} positions with avg correlation {portfolio_correlation:.2f}")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — POSITION BOOK (from position_book.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_book:
    from position_book import (
        Position, new_position, position_greeks,
        book_greeks, book_summary_df, hedge_suggestions,
        scenario_book
    )

    def _get_book():
        if "position_book" not in st.session_state:
            st.session_state["position_book"] = []
        return st.session_state["position_book"]

    def _save_book(book):
        st.session_state["position_book"] = book

    def _positions_from_state():
        return [Position.from_dict(d) for d in _get_book()]

    def _positions_to_state(positions):
        _save_book([p.to_dict() for p in positions])

    positions = _positions_from_state()

    # Book-level Greeks strip
    if positions:
        bg = book_greeks(positions)
        g_cols = st.columns(7)
        labels = {"delta": "Δ Delta", "gamma": "Γ Gamma", "vega": "ν Vega",
                   "theta": "Θ Theta", "rho": "ρ Rho", "vanna": "Vanna", "volga": "Volga"}
        for i, (gk, label) in enumerate(labels.items()):
            g_cols[i].metric(label, f"{bg[gk]:.4f}")
        st.divider()

    # Sub-tabs inside Position Book
    stab1, stab2, stab3, stab4, stab5 = st.tabs([
        "Book Manager", "Scenario Matrix", "Hedging",
        "Position Timeline", "Greeks Aggregation"
    ])

    # ── Book Manager ──────────────────────────────────────────────────────────
    with stab1:
        st.markdown("### Add Position")
        with st.form("add_position_form", clear_on_submit=True):
            fc1, fc2, fc3, fc4 = st.columns(4)
            name      = fc1.text_input("Name", value="AAPL Dec Call")
            direction = fc2.selectbox("Direction", ["long", "short"])
            otype     = fc3.selectbox("Type", ["call", "put", "stock"])
            qty       = fc4.number_input("Quantity", min_value=1, max_value=1000, value=1)

            fc5, fc6, fc7, fc8 = st.columns(4)
            strike      = fc5.number_input("Strike", min_value=0.01, value=100.0, step=1.0)
            expiry_days = fc6.number_input("Expiry (days)", min_value=1, max_value=3650, value=30)
            spot        = fc7.number_input("Spot", min_value=0.01, value=100.0, step=1.0)
            vol_pct     = fc8.number_input("Vol %", min_value=0.1, max_value=500.0, value=25.0, step=0.5)

            fc9, fc10, fc11 = st.columns(3)
            rate_pct    = fc9.number_input("Rate %", min_value=0.0, max_value=30.0, value=5.0, step=0.1)
            div_pct     = fc10.number_input("Div Yield %", min_value=0.0, max_value=30.0, value=0.0, step=0.1)
            entry_price = fc11.number_input("Entry Price (0=BS)", min_value=0.0, value=0.0, step=0.01)

            submitted = st.form_submit_button("Add Position")

        if submitted:
            pos = new_position(name, direction, otype, int(qty), strike, int(expiry_days),
                              spot, vol_pct/100, rate_pct/100, div_pct/100,
                              entry_price if entry_price > 0 else 0.0)
            if pos.entry_price == 0.0:
                pos.entry_price = pos.current_price()
            positions.append(pos)
            _positions_to_state(positions)
            st.success(f"Added: {name}")
            st.rerun()

        if positions:
            st.markdown("### Current Positions")
            df = book_summary_df(positions)
            if not df.empty:
                def _color_pnl(val):
                    try:
                        return f"color: {'#00FF9F' if float(val) >= 0 else '#FF4B4B'}"
                    except Exception:
                        return ""
                styled = df.style.applymap(_color_pnl, subset=["P&L"])
                st.dataframe(styled, use_container_width=True, hide_index=True)

            col_rm, col_exp = st.columns([3, 1])
            with col_rm:
                pos_names = [f"{i+1}. {p.name} ({p.id})" for i, p in enumerate(positions)]
                to_remove = st.selectbox("Remove position", pos_names, key="pb_remove_sel")
                if st.button("Remove Selected"):
                    idx = int(to_remove.split(".")[0]) - 1
                    positions.pop(idx)
                    _positions_to_state(positions)
                    st.rerun()
            with col_exp:
                if not df.empty:
                    csv = df.to_csv(index=False)
                    st.download_button("Export CSV", csv, "position_book.csv", "text/csv")

            if st.button("Clear All Positions", type="secondary"):
                _positions_to_state([])
                st.rerun()
        else:
            st.info("No positions yet. Add your first position above.")

    # ── Scenario Matrix ───────────────────────────────────────────────────────
    with stab2:
        if not positions:
            st.info("Add positions first.")
        else:
            sc1, sc2 = st.columns(2)
            spot_shock_pct = sc1.slider("Spot Shock Range ±%", 5, 50, 20, key="rps_sc_sp")
            vol_shock_pct  = sc2.slider("Vol Shock Range ±%", 10, 80, 30, key="rps_sc_vol")

            spot_shocks = np.linspace(-spot_shock_pct/100, spot_shock_pct/100, 9)
            vol_shocks  = np.linspace(-vol_shock_pct/100, vol_shock_pct/100, 7)
            matrix_df = scenario_book(positions, spot_shocks.tolist(), vol_shocks.tolist())

            if not matrix_df.empty:
                z = matrix_df.values.astype(float)
                fig_sm = go.Figure(go.Heatmap(
                    z=z, x=matrix_df.columns.tolist(), y=matrix_df.index.tolist(),
                    colorscale="RdYlGn", zmid=0,
                    text=[[f"${v:,.0f}" for v in row] for row in z],
                    texttemplate="%{text}", textfont=dict(size=10),
                    colorbar=dict(title="P&L ($)"),
                ))
                fig_sm.update_layout(**_LAYOUT, title="Book P&L — Spot × Vol Scenario Matrix",
                                     xaxis_title="Spot Shock", yaxis_title="Vol Shock", height=420)
                st.plotly_chart(fig_sm, use_container_width=True)

                with st.expander("Raw values"):
                    st.dataframe(matrix_df, use_container_width=True)

    # ── Hedging Suggestions ────────────────────────────────────────────────────
    with stab3:
        if not positions:
            st.info("Add positions first.")
        else:
            hc1, hc2, hc3 = st.columns(3)
            h_spot = hc1.number_input("Current Spot", value=positions[0].spot, step=1.0, key="rps_hs")
            h_vol  = hc2.number_input("Current Vol %", value=positions[0].vol*100, step=0.5, key="rps_hv") / 100
            h_rate = hc3.number_input("Current Rate %", value=positions[0].rate*100, step=0.1, key="rps_hr") / 100

            suggestions = hedge_suggestions(positions, h_spot, h_vol, h_rate)

            if suggestions:
                st.markdown("### Suggested Hedges")
                for sug in suggestions:
                    col_s, col_btn = st.columns([4, 1])
                    col_s.markdown(f"**{sug['greek']} Hedge** — {sug['suggestion']}")
                    if col_btn.button(f"Add Hedge", key=f"add_hedge_{sug['greek']}"):
                        hedge_pos = new_position(
                            name=f"Hedge ({sug['greek']})", direction=sug["direction"],
                            option_type=sug["option_type"], quantity=int(sug["quantity"]),
                            strike=sug["strike"], expiry_days=max(int(sug.get("expiry_days", 30)), 1),
                            spot=h_spot, vol=h_vol, rate=h_rate,
                        )
                        hedge_pos.entry_price = hedge_pos.current_price()
                        positions.append(hedge_pos)
                        _positions_to_state(positions)
                        st.success(f"Hedge added: {hedge_pos.name}")
                        st.rerun()

                st.divider()
                st.markdown("### Book Greeks Before Hedging")
                bg_now = book_greeks(positions)
                g_cols_h = st.columns(5)
                for i, gk in enumerate(["delta", "gamma", "vega", "theta", "rho"]):
                    g_cols_h[i].metric(gk.capitalize(), f"{bg_now[gk]:.4f}")
            else:
                st.success("Book is already well-hedged or no significant Greek exposure detected.")

    # ── Position Timeline ─────────────────────────────────────────────────────
    with stab4:
        if not positions:
            st.info("Add positions first.")
        else:
            today = datetime.now(timezone.utc)
            fig_tl = go.Figure()
            for i, pos in enumerate(positions):
                g = position_greeks(pos)
                pnl = pos.sign * pos.quantity * 100 * (pos.current_price() - pos.entry_price)
                color = _GREEN if pnl >= 0 else _RED
                fig_tl.add_trace(go.Bar(
                    x=[pos.expiry * 365], y=[i], orientation="h",
                    marker=dict(color=color, opacity=0.7), base=0, name=pos.name,
                    text=f"{pos.name} | Δ={g['delta']:.3f} | P&L=${pnl:,.0f}",
                    textposition="inside",
                    hovertemplate=(
                        f"<b>{pos.name}</b><br>Type: {pos.direction} {pos.option_type}<br>"
                        f"Strike: {pos.strike:.2f}<br>Expiry: {int(pos.expiry*365)}d<br>"
                        f"Delta: {g['delta']:.4f}<br>P&L: ${pnl:,.2f}<extra></extra>"
                    ),
                    showlegend=False,
                ))
            fig_tl.update_layout(
                **_LAYOUT, title="Position Timeline — Days to Expiry",
                xaxis_title="Days to Expiry",
                yaxis=dict(tickvals=list(range(len(positions))),
                           ticktext=[p.name for p in positions], gridcolor=_GRID),
                xaxis=dict(gridcolor=_GRID),
                height=max(300, 80 + len(positions) * 50), barmode="overlay",
            )
            st.plotly_chart(fig_tl, use_container_width=True)

    # ── Greeks Aggregation ────────────────────────────────────────────────────
    with stab5:
        if not positions:
            st.info("Add positions first.")
        else:
            names_agg = [f"{p.name} ({p.direction[0].upper()})" for p in positions]
            deltas_agg = [position_greeks(p)["delta"] for p in positions]
            vegas_agg  = [abs(position_greeks(p)["vega"]) for p in positions]

            col_d, col_v = st.columns(2)
            with col_d:
                fig_delta = go.Figure(go.Bar(
                    x=names_agg, y=deltas_agg,
                    marker_color=[_GREEN if d >= 0 else _RED for d in deltas_agg],
                    text=[f"{d:.3f}" for d in deltas_agg], textposition="outside",
                ))
                fig_delta.add_hline(y=0, line=dict(color="rgba(255,255,255,0.3)", width=1))
                fig_delta.update_layout(**_LAYOUT, title="Delta by Position",
                                        yaxis_title="Delta", yaxis=dict(gridcolor=_GRID), height=320)
                st.plotly_chart(fig_delta, use_container_width=True)

            with col_v:
                fig_vega = go.Figure(go.Pie(
                    labels=names_agg, values=vegas_agg, hole=0.4,
                    marker=dict(colors=[_CYAN,_GOLD,_PURPLE,_GREEN,_ORANGE,_RED,"#FFFFFF"][:len(positions)]),
                    textinfo="label+percent",
                ))
                fig_vega.update_layout(**_LAYOUT, title="|Vega| by Position", height=320)
                st.plotly_chart(fig_vega, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — HEDGING (from hedging_page.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_hedge:
    from hedging import HedgingAnalytics, PnLAttribution

    hedge_mode = st.radio("Hedging Analysis",
                         ["Delta Hedge Simulator", "Rehedge Optimization", "P&L Attribution", "Hedge Ratios"],
                         horizontal=True, key="rps_hedge_mode")

    if hedge_mode == "Delta Hedge Simulator":
        st.markdown("### Full Delta Hedging P&L with Transaction Costs")
        c1, c2, c3 = st.columns(3)
        with c1:
            hedge_spot = st.number_input("Initial Spot (€)", 50, 150, 100, key="rps_hs1")
        with c2:
            hedge_strike = st.number_input("Option Strike (€)", 50, 150, 100, key="rps_hk1")
        with c3:
            hedge_tte = st.slider("Time to Expiry (years)", 0.1, 2.0, 0.5, key="rps_htte")

        c1, c2, c3 = st.columns(3)
        with c1:
            hedge_rate = st.slider("Interest Rate (%)", 0, 10, 5, key="rps_hr1") / 100
        with c2:
            hedge_vol = st.slider("Volatility (%)", 5, 80, 20, key="rps_hvol1") / 100
        with c3:
            rehedge_frequency = st.selectbox("Rehedge Frequency", [1, 2, 5, 10, 20], key="rps_rf1")

        c1, c2 = st.columns(2)
        with c1:
            bid_ask = st.slider("Bid-Ask Spread (bps)", 1, 50, 5, key="rps_ba1")
        with c2:
            slippage = st.slider("Slippage (%)", 0.0, 2.0, 0.5, key="rps_sl1") / 100

        if st.button("Run Hedge Simulation", key="rps_run_hs"):
            np.random.seed(42)
            sim_days = 60
            dt = 1/252
            dW = np.random.normal(0, np.sqrt(dt), sim_days)
            spot_path = np.zeros(sim_days)
            spot_path[0] = hedge_spot
            for i in range(1, sim_days):
                spot_path[i] = spot_path[i-1] * np.exp((hedge_rate - 0.5*hedge_vol**2)*dt + hedge_vol*dW[i])

            pnl_path = np.cumsum(np.random.normal(100, 300, sim_days))
            cum_costs = np.cumsum(np.abs(np.random.normal(50, 100, sim_days // rehedge_frequency)) *
                                  (bid_ask/10000 + slippage))
            net_pnl = pnl_path - cum_costs.repeat(rehedge_frequency)[:sim_days]

            c1, c2, c3 = st.columns(3)
            c1.metric("Final P&L", f"€{net_pnl[-1]:,.0f}")
            c2.metric("Total Hedge Costs", f"€{cum_costs[-1]:,.0f}")
            c3.metric("Cost/Day", f"€{cum_costs[-1]/sim_days:,.0f}")

            fig_hg = go.Figure()
            fig_hg.add_trace(go.Scatter(y=spot_path, name='Spot Price', yaxis='y1',
                                        line=dict(color='rgba(69,183,209,0.8)')))
            fig_hg.add_trace(go.Scatter(y=net_pnl, name='Net Hedge P&L', yaxis='y2',
                                        line=dict(color='rgba(100,200,100,0.8)')))
            fig_hg.update_layout(title="Delta Hedge Simulation & P&L", xaxis_title="Days",
                                yaxis=dict(title="Spot Price (€)", side='left'),
                                yaxis2=dict(title="P&L (€)", overlaying='y', side='right'),
                                template="plotly_dark", height=400, hovermode='x unified')
            st.plotly_chart(fig_hg, use_container_width=True)

    elif hedge_mode == "Rehedge Optimization":
        st.markdown("### Find Optimal Rehedge Frequency")
        c1, c2 = st.columns(2)
        with c1:
            opt_bid_ask = st.slider("Bid-Ask Spread (bps)", 1, 20, 5, key="rps_oba")
        with c2:
            opt_slippage = st.slider("Slippage (%)", 0.0, 1.0, 0.2, key="rps_osl") / 100

        if st.button("Optimize Rehedge Frequency", key="rps_opt_rh"):
            frequencies = [1, 2, 5, 10, 20, 50]
            total_costs = []
            for freq in frequencies:
                num_rehedges = 252 // freq
                cost_per_rehedge = 100 * (opt_bid_ask/10000 + opt_slippage)
                total_costs.append(num_rehedges * cost_per_rehedge)

            st.success(f"Optimal frequency: Every {frequencies[np.argmin(total_costs)]} days")

            fig_opt = go.Figure()
            fig_opt.add_trace(go.Bar(x=[f"Every {f} days" for f in frequencies],
                                    y=total_costs, marker_color='rgba(69,183,209,0.8)'))
            fig_opt.update_layout(title="Annual Hedging Cost by Frequency",
                                 xaxis_title="Rehedge Frequency", yaxis_title="Total Cost (€)",
                                 template="plotly_dark", height=400)
            st.plotly_chart(fig_opt, use_container_width=True)

    elif hedge_mode == "P&L Attribution":
        st.markdown("### Daily P&L Attribution by Greeks")
        np.random.seed(42)
        days_h = 30
        spot_moves = np.random.normal(0, 1, days_h)
        vol_moves = np.random.normal(0, 0.02, days_h)

        delta_pnl_h = spot_moves * 100
        gamma_pnl_h = (spot_moves**2) * 50 - 50
        vega_pnl_h = vol_moves * 10000
        theta_pnl_h = -np.linspace(0, 100, days_h)
        rho_pnl_h = np.random.normal(-10, 5, days_h)

        fig_attr = go.Figure()
        fig_attr.add_trace(go.Scatter(x=np.arange(days_h), y=delta_pnl_h, name='Delta',
                                     fill='tozeroy', line=dict(color='rgba(69,183,209,0.8)')))
        fig_attr.add_trace(go.Scatter(x=np.arange(days_h), y=gamma_pnl_h, name='Gamma',
                                     fill='tonexty', line=dict(color='rgba(255,107,107,0.8)')))
        fig_attr.add_trace(go.Scatter(x=np.arange(days_h), y=vega_pnl_h, name='Vega',
                                     fill='tonexty', line=dict(color='rgba(100,200,100,0.8)')))
        fig_attr.add_trace(go.Scatter(x=np.arange(days_h), y=theta_pnl_h, name='Theta',
                                     fill='tonexty', line=dict(color='rgba(255,165,0,0.8)')))
        fig_attr.update_layout(title="Daily P&L Attribution by Greek", xaxis_title="Days",
                              yaxis_title="P&L (€)", template="plotly_dark", height=400)
        st.plotly_chart(fig_attr, use_container_width=True)

        attribution_df = pd.DataFrame({
            'Greek': ['Delta', 'Gamma', 'Vega', 'Theta', 'Rho'],
            'Total P&L': [delta_pnl_h.sum(), gamma_pnl_h.sum(), vega_pnl_h.sum(), theta_pnl_h.sum(), rho_pnl_h.sum()],
            'Avg Daily': [delta_pnl_h.mean(), gamma_pnl_h.mean(), vega_pnl_h.mean(), theta_pnl_h.mean(), rho_pnl_h.mean()],
            'Max Daily': [delta_pnl_h.max(), gamma_pnl_h.max(), vega_pnl_h.max(), theta_pnl_h.max(), rho_pnl_h.max()],
            'Min Daily': [delta_pnl_h.min(), gamma_pnl_h.min(), vega_pnl_h.min(), theta_pnl_h.min(), rho_pnl_h.min()],
        })
        st.dataframe(attribution_df, use_container_width=True, hide_index=True)

    else:  # Hedge Ratios
        st.markdown("### Optimal Hedge Ratios & Sensitivity")
        st.info("Configure position parameters to calculate optimal hedge ratios.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — BACKTESTING (from backtesting_page.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_bt:
    from backtesting import BacktestEngine, VaRBacktest

    backtest_mode = st.radio("Backtesting Mode",
                            ["Model vs Realized", "Strategy P&L", "VaR Validation", "Greeks Accuracy"],
                            horizontal=True, key="rps_bt_mode")

    if backtest_mode == "Model vs Realized":
        st.markdown("### Pricing Model Accuracy Test")
        c1, c2 = st.columns(2)
        with c1:
            num_paths = st.slider("Historical Paths", 100, 1000, 252, key="rps_bt_np")
        with c2:
            test_days = st.slider("Test Period (days)", 30, 252, 60, key="rps_bt_td")

        np.random.seed(42)
        model_prices = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, test_days)))
        realized_prices = 100 * np.exp(np.cumsum(np.random.normal(0.0003, 0.02, test_days)))
        bt_results = BacktestEngine.compare_model_vs_realized(
            model_prices=model_prices, realized_prices=realized_prices
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("RMSE", f"{bt_results.get('rmse', 0):.4f}")
        c2.metric("MAE", f"€{bt_results.get('mae', 0):.2f}")
        c3.metric("R² Score", f"{bt_results.get('r_squared', 0):.4f}")
        c4.metric("Max Error", f"€{bt_results.get('max_error', 0):.2f}")

        np.random.seed(42)
        sim_p = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, test_days)))
        real_p = 100 * np.exp(np.cumsum(np.random.normal(0.0003, 0.02, test_days)))

        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=np.arange(test_days), y=real_p, name='Realized',
                                   line=dict(color='rgba(255,107,107,0.8)', width=2)))
        fig_bt.add_trace(go.Scatter(x=np.arange(test_days), y=sim_p, name='Model',
                                   line=dict(color='rgba(69,183,209,0.8)', width=2, dash='dash')))
        fig_bt.update_layout(title="Model Pricing vs Realized", xaxis_title="Days",
                            yaxis_title="Price (€)", template="plotly_dark", height=400)
        st.plotly_chart(fig_bt, use_container_width=True)

    elif backtest_mode == "Strategy P&L":
        st.markdown("### Delta Hedging P&L Simulation")
        c1, c2 = st.columns(2)
        with c1:
            rehedge_freq = st.selectbox("Rehedge Frequency (days)", [1, 2, 5, 10, 20], key="rps_bt_rf")
        with c2:
            bid_ask_spread = st.slider("Bid-Ask Spread (bps)", 1, 20, 5, key="rps_bt_ba")

        np.random.seed(42)
        hedge_days = 60
        pnl_path = np.cumsum(np.random.normal(100, 500, hedge_days))
        cum_c = np.cumsum(np.abs(np.random.normal(100, 200, hedge_days // rehedge_freq)))

        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Scatter(y=pnl_path, name='Hedge P&L', fill='tozeroy',
                                    line=dict(color='rgba(69,183,209,0.8)')))
        fig_pnl.add_trace(go.Scatter(y=-cum_c.repeat(rehedge_freq)[:hedge_days],
                                    name='Transaction Costs', line=dict(color='rgba(255,107,107,0.8)')))
        fig_pnl.update_layout(title="Delta Hedge P&L with Costs", xaxis_title="Days",
                             yaxis_title="P&L (€)", template="plotly_dark", height=400)
        st.plotly_chart(fig_pnl, use_container_width=True)

    elif backtest_mode == "VaR Validation":
        st.markdown("### VaR Model Validation (Kupiec POF Test)")
        bt_confidence = st.slider("VaR Confidence Level", 0.90, 0.99, 0.95, 0.01, key="rps_bt_conf")

        np.random.seed(42)
        num_obs = 252
        bt_returns = np.random.normal(0.0005, 0.015, num_obs)
        var_thresh = np.percentile(bt_returns, (1 - bt_confidence) * 100)
        breaches = (bt_returns < var_thresh).sum()
        expected_breaches = int(num_obs * (1 - bt_confidence))
        kupiec_result = VaRBacktest.kupiec_pof_test(breaches, num_obs, bt_confidence)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Days", num_obs)
        c2.metric("VaR Breaches", breaches, f"Expected: {expected_breaches}")
        c3.metric("Kupiec Test", "PASSED" if kupiec_result else "FAILED",
                 delta="Model Valid" if kupiec_result else "Model Invalid")

        fig_var = go.Figure()
        fig_var.add_trace(go.Scatter(x=np.arange(num_obs), y=bt_returns, name='Daily Returns',
                                    line=dict(color='rgba(69,183,209,0.5)'), mode='lines'))
        fig_var.add_hline(y=var_thresh, line_dash="dash", line_color="red",
                         annotation_text=f"VaR {bt_confidence:.0%}")
        fig_var.update_layout(title="VaR Breaches Over Time", xaxis_title="Days",
                             yaxis_title="Return", template="plotly_dark", height=400)
        st.plotly_chart(fig_var, use_container_width=True)

    else:  # Greeks Accuracy
        st.markdown("### Greeks Accuracy Validation")
        st.info("Compare theoretical Greeks to implied Greeks from market movements.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — P&L ATTRIBUTION (from pnl_attribution.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_pnl:
    from pnl_attribution import (
        attribute_pnl, simulate_price_path,
        multi_day_attribution, sensitivity_attribution, AttributionResult
    )
    from engine import BlackScholesGreeks as BSG

    st.caption("Taylor decomposition: ΔP = Δ·ΔS + ½Γ·ΔS² + ν·Δσ + Θ·Δt + Vanna·ΔS·Δσ + ½Volga·Δσ² + ρ·Δr + ε")

    with st.expander("Position Parameters", expanded=True):
        st.markdown("**Initial State**")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        S0      = c1.number_input("Spot S₀", min_value=0.01, value=100.0, step=1.0, key="rps_S0")
        K_pa    = c2.number_input("Strike K", min_value=0.01, value=100.0, step=1.0, key="rps_K")
        T_days  = c3.number_input("Expiry T (days)", min_value=2, max_value=3650, value=30, key="rps_Td")
        sig0_pct= c4.number_input("Vol σ₀ %", min_value=0.1, max_value=500.0, value=25.0, step=0.5, key="rps_sig0")
        r_pct_pa= c5.number_input("Rate r %", min_value=0.0, max_value=30.0, value=5.0, step=0.1, key="rps_r")
        div_pct_pa = c6.number_input("Div Yield %", min_value=0.0, max_value=30.0, value=0.0, step=0.1, key="rps_div")

        otype_pa = st.radio("Option Type", ["call", "put"], horizontal=True, key="rps_otype")
        qty_pa   = st.number_input("Quantity (contracts)", min_value=1, max_value=1000, value=1, key="rps_qty")

        st.markdown("**Scenario (next day)**")
        d1, d2, d3, d4 = st.columns(4)
        S1      = d1.number_input("New Spot S₁", min_value=0.01, value=103.0, step=1.0, key="rps_S1")
        sig1_pct= d2.number_input("New Vol σ₁ %", min_value=0.1, max_value=500.0, value=26.0, step=0.5, key="rps_sig1")
        dr_pct  = d3.number_input("Rate Shock Δr %", min_value=-5.0, max_value=5.0, value=0.0, step=0.1, key="rps_dr")
        dt_days = d4.number_input("Time Elapsed (days)", min_value=1, max_value=365, value=1, key="rps_dt")

    T0_pa     = T_days / 365.0
    T1_pa     = max(T0_pa - dt_days / 365.0, 1e-4)
    sigma0_pa = sig0_pct / 100.0
    sigma1_pa = sig1_pct / 100.0
    r_pa      = r_pct_pa / 100.0
    div_pa    = div_pct_pa / 100.0
    dr_pa     = dr_pct / 100.0

    # Sub-tabs for P&L Attribution
    ptab1, ptab2, ptab3, ptab4 = st.tabs([
        "Single-Day Waterfall", "Multi-Day Path", "Formula Detail", "Sensitivity"
    ])

    with ptab1:
        result = attribute_pnl(S0, S1, sigma0_pa, sigma1_pa, T0_pa, T1_pa, r_pa, K_pa, otype_pa, qty_pa, div_pa, dr_pa)
        bd = result.breakdown

        ma, mb, mc = st.columns(3)
        ma.metric("Actual P&L", f"${result.total_actual:,.2f}", delta=f"{result.total_actual:.2f}")
        mb.metric("Theoretical P&L", f"${result.total_theoretical:,.2f}")
        mc.metric("Residual", f"${result.residual:,.2f}")

        terms = list(bd.keys())
        values = list(bd.values())
        fig_wf = go.Figure(go.Waterfall(
            name="P&L Attribution", orientation="v",
            measure=["relative"] * len(terms), x=terms, y=values,
            text=[f"${v:,.2f}" for v in values], textposition="outside",
            connector=dict(line=dict(color=_GRID, width=1)),
            increasing=dict(marker=dict(color=_GREEN)),
            decreasing=dict(marker=dict(color=_RED)),
            totals=dict(marker=dict(color=_CYAN)),
        ))
        fig_wf.update_layout(**_LAYOUT, title="Single-Day P&L Attribution Waterfall",
                            xaxis_title="Component", yaxis_title="P&L ($)",
                            yaxis=dict(gridcolor=_GRID, zeroline=True,
                                       zerolinecolor="rgba(255,255,255,0.3)"),
                            height=440)
        st.plotly_chart(fig_wf, use_container_width=True)

        rows_wf = []
        for term, val in bd.items():
            rows_wf.append({
                "Term": term,
                "P&L ($)": f"${val:,.4f}",
                "% of |Total|": f"{abs(val)/max(abs(result.total_actual), 1e-8)*100:.1f}%",
            })
        st.dataframe(pd.DataFrame(rows_wf), use_container_width=True, hide_index=True)

    with ptab2:
        pc1, pc2, pc3, pc4 = st.columns(4)
        n_days  = pc1.slider("Days", 5, 120, 30, key="rps_pnl_nd")
        n_paths = pc2.slider("Paths", 1, 10, 3, key="rps_pnl_np")
        vol_drift = pc3.slider("Vol Drift/Day (bps)", -50, 50, 0, key="rps_pnl_vd") / 10000.0
        seed    = pc4.number_input("Seed", min_value=0, max_value=9999, value=42, key="rps_pnl_sd")

        paths = simulate_price_path(S0, sigma0_pa, r_pa, div_pa, n_days, n_paths, int(seed))
        attr_df = multi_day_attribution(paths, K_pa, T0_pa, r_pa, sigma0_pa, otype_pa, qty_pa, div_pa, vol_drift)

        colors_path = [_CYAN, _GOLD, _GREEN, _ORANGE, _PURPLE, _RED, "#FFFFFF", "#FF69B4", "#00FF9F", "#98FB98"]
        fig_pp = go.Figure()
        for p in range(1, n_paths + 1):
            pdata = paths[p - 1]
            fig_pp.add_trace(go.Scatter(x=list(range(len(pdata))), y=pdata, mode="lines",
                                        name=f"Path {p}",
                                        line=dict(color=colors_path[(p-1) % len(colors_path)], width=1.5)))
        fig_pp.add_hline(y=K_pa, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"),
                        annotation_text=f"K={K_pa:.2f}")
        fig_pp.update_layout(**_LAYOUT, title="Simulated Price Paths (GBM)",
                            xaxis_title="Day", yaxis_title="Spot Price",
                            xaxis=dict(gridcolor=_GRID), yaxis=dict(gridcolor=_GRID),
                            height=320, legend=dict(orientation="h", y=1.06))
        st.plotly_chart(fig_pp, use_container_width=True)

        if not attr_df.empty:
            fig_cum = go.Figure()
            for p in range(1, n_paths + 1):
                pdata = attr_df[attr_df["path"] == p]
                fig_cum.add_trace(go.Scatter(x=pdata["day"], y=pdata["cumulative_pnl"],
                                             mode="lines", name=f"Path {p}",
                                             line=dict(color=colors_path[(p-1) % len(colors_path)], width=1.8)))
            fig_cum.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"))
            fig_cum.update_layout(**_LAYOUT, title="Cumulative P&L by Path",
                                 xaxis_title="Day", yaxis_title="Cumulative P&L ($)",
                                 xaxis=dict(gridcolor=_GRID),
                                 yaxis=dict(gridcolor=_GRID, zeroline=True,
                                            zerolinecolor="rgba(255,255,255,0.25)"),
                                 height=320, legend=dict(orientation="h", y=1.06))
            st.plotly_chart(fig_cum, use_container_width=True)

            p1 = attr_df[attr_df["path"] == 1].copy()
            components = ["delta_pnl", "gamma_pnl", "vega_pnl", "theta_pnl", "vanna_pnl", "volga_pnl", "residual"]
            comp_labels = ["Delta", "Gamma", "Vega", "Theta", "Vanna", "Volga", "Residual"]
            comp_colors = [_CYAN, _GOLD, _ORANGE, _RED, _PURPLE, "#FF69B4", "#888888"]

            fig_stack = go.Figure()
            for comp, label, color in zip(components, comp_labels, comp_colors):
                fig_stack.add_trace(go.Bar(x=p1["day"], y=p1[comp], name=label,
                                           marker_color=color, opacity=0.8))
            fig_stack.update_layout(**_LAYOUT, barmode="relative",
                                   title="Daily Attribution Components — Path 1",
                                   xaxis_title="Day", yaxis_title="Daily P&L ($)",
                                   xaxis=dict(gridcolor=_GRID),
                                   yaxis=dict(gridcolor=_GRID, zeroline=True,
                                              zerolinecolor="rgba(255,255,255,0.3)"),
                                   legend=dict(orientation="h", y=1.06), height=360)
            st.plotly_chart(fig_stack, use_container_width=True)

    with ptab3:
        st.markdown("### Taylor Expansion P&L Attribution")
        st.latex(r"""
        \Delta P \approx \Delta \cdot \Delta S
        + \frac{1}{2}\Gamma \cdot (\Delta S)^2
        + \nu \cdot \Delta\sigma
        + \Theta \cdot \Delta t
        + \text{Vanna} \cdot \Delta S \cdot \Delta\sigma
        + \frac{1}{2}\text{Volga} \cdot (\Delta\sigma)^2
        + \rho \cdot \Delta r
        + \varepsilon
        """)

        result2 = attribute_pnl(S0, S1, sigma0_pa, sigma1_pa, T0_pa, T1_pa, r_pa, K_pa, otype_pa, qty_pa, div_pa, dr_pa)
        dS_pa = S1 - S0
        dsigma_pa = sigma1_pa - sigma0_pa

        b0 = r_pa - div_pa
        delta_v  = BSG.delta(S0, K_pa, T0_pa, r_pa, b0, sigma0_pa, otype_pa)
        gamma_v  = BSG.gamma(S0, K_pa, T0_pa, r_pa, b0, sigma0_pa)
        vega_v   = BSG.vega(S0, K_pa, T0_pa, r_pa, b0, sigma0_pa) * 100.0
        theta_v  = BSG.theta(S0, K_pa, T0_pa, r_pa, b0, sigma0_pa, otype_pa)
        rho_v    = BSG.rho(S0, K_pa, T0_pa, r_pa, b0, sigma0_pa, otype_pa) * 100.0
        vanna_v  = BSG.vanna(S0, K_pa, T0_pa, r_pa, b0, sigma0_pa)
        volga_v  = BSG.volga(S0, K_pa, T0_pa, r_pa, b0, sigma0_pa)

        rows_fm = [
            {"Term": "Delta", "Formula": "Δ · ΔS", "Greek": f"Δ={delta_v:.5f}",
             "ΔInput": f"ΔS={dS_pa:+.3f}", "Value ($)": f"${result2.delta_pnl:,.4f}"},
            {"Term": "Gamma", "Formula": "½Γ · (ΔS)²", "Greek": f"Γ={gamma_v:.6f}",
             "ΔInput": f"(ΔS)²={dS_pa**2:.4f}", "Value ($)": f"${result2.gamma_pnl:,.4f}"},
            {"Term": "Vega", "Formula": "ν · Δσ", "Greek": f"ν={vega_v:.5f}",
             "ΔInput": f"Δσ={dsigma_pa:+.4f}", "Value ($)": f"${result2.vega_pnl:,.4f}"},
            {"Term": "Theta", "Formula": "Θ · Δt", "Greek": f"Θ={theta_v:.6f}/day",
             "ΔInput": f"Δt={dt_days:.2f}d", "Value ($)": f"${result2.theta_pnl:,.4f}"},
            {"Term": "Vanna", "Formula": "Vanna · ΔS · Δσ", "Greek": f"Vanna={vanna_v:.6f}",
             "ΔInput": f"ΔS·Δσ={dS_pa*dsigma_pa:.6f}", "Value ($)": f"${result2.vanna_pnl:,.4f}"},
            {"Term": "Volga", "Formula": "½Volga · (Δσ)²", "Greek": f"Volga={volga_v:.4f}",
             "ΔInput": f"(Δσ)²={dsigma_pa**2:.6f}", "Value ($)": f"${result2.volga_pnl:,.4f}"},
            {"Term": "Rho", "Formula": "ρ · Δr", "Greek": f"ρ={rho_v:.5f}",
             "ΔInput": f"Δr={dr_pa:+.4f}", "Value ($)": f"${result2.rho_pnl:,.4f}"},
            {"Term": "Residual", "Formula": "Actual − Theoretical", "Greek": "—",
             "ΔInput": "—", "Value ($)": f"${result2.residual:,.4f}"},
            {"Term": "TOTAL (Actual)", "Formula": "BS(S₁,σ₁,T₁) − BS(S₀,σ₀,T₀)", "Greek": "—",
             "ΔInput": "—", "Value ($)": f"${result2.total_actual:,.4f}"},
        ]
        st.dataframe(pd.DataFrame(rows_fm), use_container_width=True, hide_index=True)

    with ptab4:
        st.markdown("### Sensitivity Attribution")
        st.info("Analyse how P&L attribution changes when varying underlying parameters.")
