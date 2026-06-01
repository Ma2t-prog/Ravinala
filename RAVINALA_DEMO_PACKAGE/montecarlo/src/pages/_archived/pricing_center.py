import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from engine import BlackScholesGreeks

_render_page_header("PC", "Vanilla Pricing & Greeks Dashboard", "Analyze European options with first/second-order risk sensitivities", "Pricing")

spot_price = st.session_state.get("spot_sidebar", 100.0)
volatility = st.session_state.get("vol_sidebar", 0.20)
rate = st.session_state.get("rate_sidebar", 0.05)
carry = st.session_state.get("carry_sidebar", 0.04)
CURRENCY_SYMBOL = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥"}.get(
    st.session_state.get("curr_sidebar", "USD"), "$"
)

col1, col2, col3 = st.columns(3)
with col1:
    strike = st.number_input("Strike Price (K)", value=100.0, step=0.1, min_value=0.1)
with col2:
    time_to_expiry = st.number_input("Time to Expiry (Years)", value=1.0, step=0.1, min_value=0.01, max_value=10.0)
with col3:
    option_type = st.radio("Option Type", ["Call", "Put"], horizontal=True)

# Dividend yield (carry for equity)
dividend_yield = st.slider("Dividend Yield (q)", 0.0, 0.10, 0.02)
carry = rate - dividend_yield  # b = r - q for stocks

# Compute Greeks
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

# Display Metrics
st.divider()
st.markdown("### **Option Valuation**")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Price", f"{CURRENCY_SYMBOL}{price:.2f}", f"{(price/strike - 1)*100:.1f}% of Strike")
with col2:
    st.metric("Intrinsic Value", f"{CURRENCY_SYMBOL}{max(spot_price - strike, 0):.2f}" if option_type == "Call" else f"{CURRENCY_SYMBOL}{max(strike - spot_price, 0):.2f}")
with col3:
    st.metric("Time Value", f"{CURRENCY_SYMBOL}{price - max(spot_price - strike, 0):.2f}" if option_type == "Call" else f"{CURRENCY_SYMBOL}{price - max(strike - spot_price, 0):.2f}")
with col4:
    st.metric("Moneyness", f"{(spot_price/strike):.2%}")

# Greeks Display
st.markdown("### **Risk Greeks**")
greek_cols = st.columns(4)
greek_data = [
    ("Delta (Δ)", delta, "Change in price per 1 unit spot move"),
    ("Gamma (Γ)", gamma, "Delta acceleration (convexity)"),
    ("Vega (ν)", vega, "Price change per 1% volatilit change"),
    ("Theta (Θ)", theta, "Daily time decay"),
]

for idx, (col, (label, value, tooltip)) in enumerate(zip(greek_cols, greek_data)):
    with col:
        st.metric(label, f"{value:.6f}", tooltip)

st.markdown("### **Advanced Greeks**")
adv_cols = st.columns(3)
adv_greek_data = [
    ("Rho (ρ)", rho, "Sensitivity to interest rates (per 1%)"),
    ("Vanna", vanna, "Spot-Vol correlation"),
    ("Volga", volga, "Vol-of-Vol sensitivity"),
]

for col, (label, value, tooltip) in zip(adv_cols, adv_greek_data):
    with col:
        st.metric(label, f"{value:.6f}", tooltip)

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
    z=heatmap_data,
    x=np.round(spot_range, 2),
    y=np.round(vol_range * 100, 1),
    colorscale='Viridis',
    colorbar=dict(title=f"{option_type} Price")
))

fig_heatmap.update_layout(
    title=f"{option_type} Price Sensitivity",
    xaxis_title="Spot Price",
    yaxis_title="Volatility (%)",
    height=500,
    template="plotly_dark"
)
st.plotly_chart(fig_heatmap)

# P&L Chart
st.markdown("### **Payoff Diagram at Expiry**")
spot_at_expiry = np.linspace(strike * 0.5, strike * 1.5, 100)
payoffs = []

for s in spot_at_expiry:
    if option_type == "Call":
        payoff = max(s - strike, 0)
    else:
        payoff = max(strike - s, 0)
    payoffs.append(payoff)

fig_payoff = go.Figure()
fig_payoff.add_trace(go.Scatter(
    x=spot_at_expiry,
    y=payoffs,
    mode='lines',
    name='Payoff',
    line=dict(color='#00d4ff', width=3)
))

fig_payoff.update_layout(
    title=f"{option_type} Payoff at Expiry",
    xaxis_title="Spot Price at Expiry",
    yaxis_title="Payoff",
    height=400,
    template="plotly_dark"
)
st.plotly_chart(fig_payoff)
