import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from risk import RiskAnalytics, PortfolioRisk

_render_page_header("RM", "Risk Analytics & Stress Testing", "VaR, stress testing, decomposition and portfolio risk", "Risk")

risk_section = st.radio("Risk Analysis Mode",
                       ["VaR Analysis", "Stress Scenarios", "Risk Decomposition", "Portfolio Risk"],
                       horizontal=True)

if risk_section == "VaR Analysis":
    st.markdown("### Value-at-Risk Calculation")

    col1, col2, col3 = st.columns(3)
    with col1:
        confidence = st.slider("VaR Confidence Level", 0.90, 0.99, 0.95, 0.01)
    with col2:
        num_days = st.slider("lookback Period (days)", 30, 500, 252)
    with col3:
        portfolio_value = st.number_input("Portfolio Value (€)", 100000, 10000000, 1000000)

    # Generate synthetic returns
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.015, num_days)

    # Calculate VaR
    var_hist = RiskAnalytics.value_at_risk_historical(returns, confidence)
    var_param = RiskAnalytics.value_at_risk_parametric(returns, confidence, portfolio_value)
    cvar = RiskAnalytics.conditional_var(returns, confidence)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("VaR (Historical)", f"€{var_hist[1]:,.0f}", f"{var_hist[0]:.2%}")
    with col2:
        st.metric("VaR (Parametric)", f"€{var_param[1]:,.0f}", f"{var_param[0]:.2%}")
    with col3:
        st.metric("CVaR (Expected Shortfall)", f"€{cvar[1]:,.0f}", f"{cvar[0]:.2%}")

    st.divider()

    # Visualize returns distribution
    fig_returns = go.Figure()
    fig_returns.add_trace(go.Histogram(x=returns*100, nbinsx=50, name="Daily Returns %",
                                       marker_color='rgba(55, 83, 109, 0.7)'))
    fig_returns.add_vline(x=var_hist[0]*100, line_dash="dash", line_color="red",
                         annotation_text=f"VaR {confidence:.0%}<br>({var_hist[0]:.2%})")
    fig_returns.update_layout(title="Returns Distribution with VaR Threshold",
                             xaxis_title="Daily Return (%)", yaxis_title="Frequency",
                             template="plotly_dark", height=400)
    st.plotly_chart(fig_returns)

elif risk_section == "Stress Scenarios":
    st.markdown("### Stress Testing - Single & Multiple Shocks")

    col1, col2 = st.columns(2)
    with col1:
        stress_type = st.selectbox("Stress Type",
                                  ["Single Shock (Spot)", "Single Shock (Vol)",
                                   "Multiple Shocks", "Historical Scenarios"])
    with col2:
        shock_magnitude = st.slider("Shock Magnitude (%)", -50, 50, -20)

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

    col1, col2, col3 = st.columns(3)
    with col1:
        spot_shock = st.slider("Spot Price Shock (%)", -20, 20, 0)
    with col2:
        vol_shock = st.slider("Volatility Shock (%)", -20, 20, 0)
    with col3:
        theta_days = st.slider("Time Decay (days)", 1, 30, 1)

    decomp = RiskAnalytics.risk_decomposition(
        spot=100, strike=100, T=0.5, r=0.05, vol=0.2, carry=0.05,
        option_type='call'
    )

    # Display attribution - decomp keys are scenario names like '-1% Spot', '+1% Spot', etc.
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Delta (-1%)", f"€{decomp.get('-1% Spot', 0):.2f}")
    with col2:
        st.metric("Delta (+1%)", f"€{decomp.get('+1% Spot', 0):.2f}")
    with col3:
        st.metric("Gamma Risk", f"€{decomp.get('Gamma Risk (1% move)', 0):.2f}")
    with col4:
        st.metric("Vega (+100bps)", f"€{decomp.get('+100bps Vol', 0):.2f}")
    with col5:
        st.metric("Theta (1d)", f"€{decomp.get('1 Day Decay', 0):.2f}")
    with col6:
        st.metric("Rho (+100bps)", f"€{decomp.get('+100bps Rate', 0):.2f}")

    # Pie chart of attribution
    attribution_data = {
        'Delta +1%': abs(decomp.get('+1% Spot', 0)),
        'Gamma': abs(decomp.get('Gamma Risk (1% move)', 0)),
        'Vega': abs(decomp.get('+100bps Vol', 0)),
        'Theta': abs(decomp.get('1 Day Decay', 0)),
        'Rho': abs(decomp.get('+100bps Rate', 0))
    }
    fig_pie = go.Figure(data=[go.Pie(labels=list(attribution_data.keys()),
                                     values=list(attribution_data.values()),
                                     marker_colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'])])
    fig_pie.update_layout(title="P&L Attribution by Greek", template="plotly_dark", height=400)
    st.plotly_chart(fig_pie)

elif risk_section == "Portfolio Risk":
    st.markdown("### Multi-Position Portfolio Risk Analysis")

    col1, col2 = st.columns(2)
    with col1:
        num_positions = st.slider("Number of Positions", 1, 10, 3)
    with col2:
        portfolio_correlation = st.slider("Average Correlation", -0.5, 1.0, 0.3)

    st.warning(f"Portfolio with {num_positions} positions | Avg Correlation: {portfolio_correlation:.2f}")

    # Synthetic portfolio Greeks
    portfolio_deltas = np.random.normal(0.5, 0.3, num_positions)
    portfolio_vegas = np.random.uniform(-100, 100, num_positions)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Aggregate Delta", f"{portfolio_deltas.sum():.3f}")
    with col2:
        st.metric("Aggregate Vega", f"€{portfolio_vegas.sum():.0f}/1%")
    with col3:
        st.metric("Marginal VaR @ 95%", f"€{np.std(portfolio_deltas) * 50000:.0f}")

    # Position heatmap
    st.subheader("Position Greeks Matrix")
    positions_df = pd.DataFrame({
        'Position': [f'Pos_{i+1}' for i in range(num_positions)],
        'Delta': portfolio_deltas,
        'Vega': portfolio_vegas,
        'Gamma': np.random.normal(0.1, 0.05, num_positions),
        'Theta': np.random.normal(-0.05, 0.02, num_positions)
    })
    st.dataframe(positions_df)
