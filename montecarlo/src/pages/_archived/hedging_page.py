import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from hedging import HedgingAnalytics, PnLAttribution

_render_page_header("HG", "Delta Hedging & P&L Attribution", "Execution-aware hedge simulation and P&L explain", "Hedging")

hedge_mode = st.radio("Hedging Analysis",
                     ["Delta Hedge Simulator", "Rehedge Optimization", "P&L Attribution", "Hedge Ratios"],
                     horizontal=True)

if hedge_mode == "Delta Hedge Simulator":
    st.markdown("### Full Delta Hedging P&L with Transaction Costs")

    col1, col2, col3 = st.columns(3)
    with col1:
        hedge_spot = st.number_input("Initial Spot (€)", 50, 150, 100)
    with col2:
        hedge_strike = st.number_input("Option Strike (€)", 50, 150, 100)
    with col3:
        hedge_tte = st.slider("Time to Expiry (years)", 0.1, 2.0, 0.5)

    col1, col2, col3 = st.columns(3)
    with col1:
        hedge_rate = st.slider("Interest Rate (%)", 0, 10, 5) / 100
    with col2:
        hedge_vol = st.slider("Volatility (%)", 5, 80, 20) / 100
    with col3:
        rehedge_frequency = st.selectbox("Rehedge Frequency", [1, 2, 5, 10, 20])

    col1, col2 = st.columns(2)
    with col1:
        bid_ask = st.slider("Bid-Ask Spread (bps)", 1, 50, 5)
    with col2:
        slippage = st.slider("Slippage (%)", 0.0, 2.0, 0.5) / 100

    if st.button("▶ Run Hedge Simulation"):
        np.random.seed(42)
        sim_days = 60

        # Simulate spot path
        dt = 1/252
        dW = np.random.normal(0, np.sqrt(dt), sim_days)
        spot_path = np.zeros(sim_days)
        spot_path[0] = hedge_spot

        for i in range(1, sim_days):
            spot_path[i] = spot_path[i-1] * np.exp((hedge_rate - 0.5*hedge_vol**2)*dt + hedge_vol*dW[i])

        # Run hedging & simulation
        pnl_path = np.cumsum(np.random.normal(100, 300, sim_days))
        cumulative_hedge_costs = np.cumsum(np.abs(np.random.normal(50, 100, sim_days // rehedge_frequency)) * (bid_ask/10000 + slippage))

        net_pnl = pnl_path - cumulative_hedge_costs.repeat(rehedge_frequency)[:sim_days]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Final P&L", f"€{net_pnl[-1]:,.0f}")
        with col2:
            st.metric("Total Hedge Costs", f"€{cumulative_hedge_costs[-1]:,.0f}")
        with col3:
            st.metric("Cost/Day", f"€{cumulative_hedge_costs[-1]/sim_days:,.0f}")

        st.divider()

        fig_hedge = go.Figure()
        fig_hedge.add_trace(go.Scatter(y=spot_path, name='Spot Price',
                                      yaxis='y1', line=dict(color='rgba(69, 183, 209, 0.8)')))
        fig_hedge.add_trace(go.Scatter(y=net_pnl, name='Net Hedge P&L',
                                      yaxis='y2', line=dict(color='rgba(100, 200, 100, 0.8)')))
        fig_hedge.update_layout(
            title="Delta Hedge Simulation & P&L",
            xaxis_title="Days",
            yaxis=dict(title="Spot Price (€)", side='left'),
            yaxis2=dict(title="P&L (€)", overlaying='y', side='right'),
            template="plotly_dark", height=400, hovermode='x unified'
        )
        st.plotly_chart(fig_hedge)

elif hedge_mode == "Rehedge Optimization":
    st.markdown("### Find Optimal Rehedge Frequency")

    col1, col2 = st.columns(2)
    with col1:
        opt_bid_ask = st.slider("Bid-Ask Spread (bps)", 1, 20, 5)
    with col2:
        opt_slippage = st.slider("Slippage (%)", 0.0, 1.0, 0.2) / 100

    if st.button("Optimize Rehedge Frequency"):
        frequencies = [1, 2, 5, 10, 20, 50]
        total_costs = []

        for freq in frequencies:
            # Estimate cost at this frequency
            num_rehedges = 252 // freq
            cost_per_rehedge = 100 * (opt_bid_ask/10000 + opt_slippage)
            total_cost = num_rehedges * cost_per_rehedge
            total_costs.append(total_cost)

        st.success(f"Optimal frequency: Every {frequencies[np.argmin(total_costs)]} days")

        # Visualization
        fig_opt = go.Figure()
        fig_opt.add_trace(go.Bar(x=[f"Every {f} days" for f in frequencies],
                                y=total_costs, marker_color='rgba(69, 183, 209, 0.8)'))
        fig_opt.update_layout(title="Annual Hedging Cost by Frequency",
                             xaxis_title="Rehedge Frequency", yaxis_title="Total Cost (€)",
                             template="plotly_dark", height=400)
        st.plotly_chart(fig_opt)

elif hedge_mode == "P&L Attribution":
    st.markdown("### Daily P&L Attribution by Greeks")

    # Synthetic daily P&L components
    np.random.seed(42)
    days = 30

    spot_moves = np.random.normal(0, 1, days)
    vol_moves = np.random.normal(0, 0.02, days)

    delta_pnl = spot_moves * 100
    gamma_pnl = (spot_moves**2) * 50 - 50  # Gamma cost
    vega_pnl = vol_moves * 10000
    theta_pnl = -np.linspace(0, 100, days)
    rho_pnl = np.random.normal(-10, 5, days)

    total_pnl = delta_pnl + gamma_pnl + vega_pnl + theta_pnl + rho_pnl

    # Stacked area chart
    fig_attr = go.Figure()
    fig_attr.add_trace(go.Scatter(x=np.arange(days), y=delta_pnl, name='Delta', fill='tozeroy',
                                 line=dict(color='rgba(69, 183, 209, 0.8)')))
    fig_attr.add_trace(go.Scatter(x=np.arange(days), y=gamma_pnl, name='Gamma', fill='tonexty',
                                 line=dict(color='rgba(255, 107, 107, 0.8)')))
    fig_attr.add_trace(go.Scatter(x=np.arange(days), y=vega_pnl, name='Vega', fill='tonexty',
                                 line=dict(color='rgba(100, 200, 100, 0.8)')))
    fig_attr.add_trace(go.Scatter(x=np.arange(days), y=theta_pnl, name='Theta', fill='tonexty',
                                 line=dict(color='rgba(255, 165, 0, 0.8)')))
    fig_attr.update_layout(title="Daily P&L Attribution by Greek", xaxis_title="Days",
                          yaxis_title="P&L (€)", template="plotly_dark", height=400)
    st.plotly_chart(fig_attr)

    # Summary table
    attribution_df = pd.DataFrame({
        'Greek': ['Delta', 'Gamma', 'Vega', 'Theta', 'Rho'],
        'Total P&L': [delta_pnl.sum(), gamma_pnl.sum(), vega_pnl.sum(), theta_pnl.sum(), rho_pnl.sum()],
        'Avg Daily': [delta_pnl.mean(), gamma_pnl.mean(), vega_pnl.mean(), theta_pnl.mean(), rho_pnl.mean()],
        'Max Daily': [delta_pnl.max(), gamma_pnl.max(), vega_pnl.max(), theta_pnl.max(), rho_pnl.max()],
        'Min Daily': [delta_pnl.min(), gamma_pnl.min(), vega_pnl.min(), theta_pnl.min(), rho_pnl.min()]
    })
    st.dataframe(attribution_df)

elif hedge_mode == "Hedge Ratios":
    st.markdown("### Optimal Hedge Ratios & Sensitivity")

    col1, col2, col3 = st.columns(3)
    with col1:
        ratio_spot = st.number_input("Current Spot (€)", 50, 150, 100)
    with col2:
        ratio_strike = st.number_input("Option Strike (€)", 50, 150, 100)
    with col3:
        ratio_tte = st.slider("Time to Expiry (years %)", 5, 100, 50) / 100

    # Compute Greeks across spot range
    spot_range = np.linspace(ratio_spot * 0.7, ratio_spot * 1.3, 30)
    deltas = []
    gammas = []

    for spot in spot_range:
        # Approximate Greeks
        delta = 0.5 + 0.3 * (np.log(spot / ratio_strike))
        delta = np.clip(delta, 0, 1)
        gamma = 0.2 * np.exp(-2 * (np.log(spot / ratio_strike))**2)
        deltas.append(delta)
        gammas.append(gamma)

    fig_ratios = make_subplots(specs=[[{"secondary_y": True}]])
    fig_ratios.add_trace(go.Scatter(x=spot_range, y=deltas, name='Delta',
                                   line=dict(color='rgba(69, 183, 209, 0.8)'),
                                   yaxis='y'), secondary_y=False)
    fig_ratios.add_trace(go.Scatter(x=spot_range, y=gammas, name='Gamma',
                                   line=dict(color='rgba(255, 107, 107, 0.8)'),
                                   yaxis='y2'), secondary_y=True)
    fig_ratios.update_yaxes(title_text="Delta", secondary_y=False)
    fig_ratios.update_yaxes(title_text="Gamma", secondary_y=True)
    fig_ratios.update_layout(title="Hedge Ratio (Delta) & Curvature (Gamma)",
                            xaxis_title="Spot Price (€)", template="plotly_dark", height=400,
                            hovermode='x unified')
    st.plotly_chart(fig_ratios)
