import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from backtesting import BacktestEngine, VaRBacktest, PerfDecayAnalysis

_render_page_header("BT", "Model Backtesting & Validation", "Validate pricing, hedging and risk models against realized paths", "Validation")

backtest_mode = st.radio("Backtesting Mode",
                        ["Model vs Realized", "Strategy P&L", "VaR Validation", "Greeks Accuracy"],
                        horizontal=True)

if backtest_mode == "Model vs Realized":
    st.markdown("### Pricing Model Accuracy Test")

    col1, col2 = st.columns(2)
    with col1:
        num_paths = st.slider("Historical Paths", 100, 1000, 252)
    with col2:
        test_days = st.slider("Test Period (days)", 30, 252, 60)

    # Run backtest - generate synthetic model and realized prices
    np.random.seed(42)
    model_prices = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, test_days)))
    realized_prices = 100 * np.exp(np.cumsum(np.random.normal(0.0003, 0.02, test_days)))
    backtest_results = BacktestEngine.compare_model_vs_realized(
        model_prices=model_prices, realized_prices=realized_prices
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("RMSE", f"{backtest_results.get('rmse', 0):.4f}")
    with col2:
        st.metric("MAE", f"€{backtest_results.get('mae', 0):.2f}")
    with col3:
        st.metric("R² Score", f"{backtest_results.get('r_squared', 0):.4f}")
    with col4:
        st.metric("Max Error", f"€{backtest_results.get('max_error', 0):.2f}")

    st.divider()

    # Generate comparison chart
    backtest_days = np.arange(test_days)
    simulated_prices = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, test_days)))
    realized_prices = 100 * np.exp(np.cumsum(np.random.normal(0.0003, 0.02, test_days)))

    fig_backtest = go.Figure()
    fig_backtest.add_trace(go.Scatter(x=backtest_days, y=realized_prices, name='Realized Path',
                                     line=dict(color='rgba(255, 107, 107, 0.8)', width=2)))
    fig_backtest.add_trace(go.Scatter(x=backtest_days, y=simulated_prices, name='Model Path',
                                     line=dict(color='rgba(69, 183, 209, 0.8)', width=2, dash='dash')))
    fig_backtest.update_layout(title="Model Pricing vs Realized Path", xaxis_title="Days",
                               yaxis_title="Price (€)", template="plotly_dark", height=400)
    st.plotly_chart(fig_backtest)

elif backtest_mode == "Strategy P&L":
    st.markdown("### Delta Hedging P&L Simulation")

    col1, col2 = st.columns(2)
    with col1:
        rehedge_freq = st.selectbox("Rehedge Frequency (days)", [1, 2, 5, 10, 20])
    with col2:
        bid_ask_spread = st.slider("Bid-Ask Spread (bps)", 1, 20, 5)

    st.info(f"Hedging every {rehedge_freq} day(s) | Spread: {bid_ask_spread} bps")

    # Synthetic hedging P&L
    np.random.seed(42)
    hedge_days = 60
    pnl_path = np.cumsum(np.random.normal(100, 500, hedge_days))
    cumulative_costs = np.cumsum(np.abs(np.random.normal(100, 200, hedge_days // rehedge_freq)))

    fig_pnl = go.Figure()
    fig_pnl.add_trace(go.Scatter(y=pnl_path, name='Hedge P&L', fill='tozeroy',
                                line=dict(color='rgba(69, 183, 209, 0.8)')))
    fig_pnl.add_trace(go.Scatter(y=-cumulative_costs.repeat(rehedge_freq)[:hedge_days],
                                name='Transaction Costs', line=dict(color='rgba(255, 107, 107, 0.8)')))
    fig_pnl.update_layout(title="Delta Hedge P&L with Costs", xaxis_title="Days",
                         yaxis_title="P&L (€)", template="plotly_dark", height=400)
    st.plotly_chart(fig_pnl)

elif backtest_mode == "VaR Validation":
    st.markdown("### VaR Model Validation (Kupiec POF Test)")

    confidence = st.slider("VaR Confidence Level", 0.90, 0.99, 0.95, 0.01)

    # Synthetic VaR breach data
    np.random.seed(42)
    num_observations = 252
    returns = np.random.normal(0.0005, 0.015, num_observations)
    var_threshold = np.percentile(returns, (1-confidence)*100)
    breaches = (returns < var_threshold).sum()

    expected_breaches = int(num_observations * (1 - confidence))
    kupiec_result = VaRBacktest.kupiec_pof_test(breaches, num_observations, confidence)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Days", num_observations)
    with col2:
        st.metric("VaR Breaches", breaches, f"Expected: {expected_breaches}")
    with col3:
        st.metric("Kupiec Test", "PASSED" if kupiec_result else "FAILED",
                 delta="Model Valid" if kupiec_result else "Model Invalid")

    st.divider()

    # Breach distribution
    days = np.arange(num_observations)
    breach_indicators = (returns < var_threshold).astype(int)

    fig_var = go.Figure()
    fig_var.add_trace(go.Scatter(x=days, y=returns, name='Daily Returns',
                                line=dict(color='rgba(69, 183, 209, 0.5)'), mode='lines'))
    fig_var.add_hline(y=var_threshold, line_dash="dash", line_color="red",
                     annotation_text=f"VaR {confidence:.0%}")
    fig_var.update_layout(title="VaR Breaches Over Time", xaxis_title="Days",
                         yaxis_title="Return", template="plotly_dark", height=400)
    st.plotly_chart(fig_var)

elif backtest_mode == "Greeks Accuracy":
    st.markdown("### Greeks Prediction vs Realized P&L")

    st.info("Comparing Greeks-predicted P&L with actual P&L from price moves")

    # Synthetic Greeks vs realized
    np.random.seed(42)
    spot_moves = np.random.normal(0, 1, 60)
    vol_moves = np.random.normal(0, 0.02, 60)

    delta_pnl = spot_moves * 100  # $100 delta per spot
    vega_pnl = vol_moves * 10000  # €10k vega per vol point
    gamma_pnl = (spot_moves**2) * 50  # Gamma cost
    theta_pnl = -np.linspace(0, 100, 60)  # Daily theta decay

    predicted_pnl = delta_pnl + gamma_pnl + vega_pnl + theta_pnl
    actual_pnl = predicted_pnl + np.random.normal(0, 50, 60)  # Add noise

    fig_greeks = go.Figure()
    fig_greeks.add_trace(go.Scatter(y=predicted_pnl, name='Greeks Predicted',
                                   line=dict(color='rgba(69, 183, 209, 0.8)')))
    fig_greeks.add_trace(go.Scatter(y=actual_pnl, name='Actual P&L',
                                   line=dict(color='rgba(255, 107, 107, 0.8)')))
    fig_greeks.update_layout(title="Greeks Prediction Accuracy", xaxis_title="Days",
                            yaxis_title="P&L (€)", template="plotly_dark", height=400)
    st.plotly_chart(fig_greeks)

    # Correlation
    correlation = np.corrcoef(predicted_pnl, actual_pnl)[0, 1]
    st.metric("Greeks vs Actual Correlation", f"{correlation:.4f}",
             delta="Strong" if correlation > 0.8 else "Weak")
