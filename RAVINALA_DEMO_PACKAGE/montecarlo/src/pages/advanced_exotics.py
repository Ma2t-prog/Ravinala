import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from exotics_advanced import CliquerProducts, VarianceSwaps, CreditLinkedNotes, ConvertibleBonds
from genesix.utils.constants import RISK_FREE_RATE

_render_page_header("AE", "Advanced Exotic Products & Structured Derivatives", "Cliquets, variance swaps, convertibles and credit-linked notes", "Exotics")

exotic_type = st.radio("Exotic Product Type",
                      ["Cliquet Options", "Variance Swaps", "Convertible Bonds",
                       "Credit-Linked Notes", "Range Accrual"],
                      horizontal=True)

if exotic_type == "Cliquet Options":
    st.markdown("### Cliquet / Ratchet Option Pricing")

    col1, col2, col3 = st.columns(3)
    with col1:
        cliquet_type = st.selectbox("Cliquet Type", ["European", "Memory", "Ratchet"])
    with col2:
        num_cliquets = st.slider("Number of Cliquet Dates", 2, 10, 4)
    with col3:
        maturity = st.slider("Maturity (years)", 1, 5, 2)

    col1, col2, col3 = st.columns(3)
    with col1:
        floor = st.slider("Coupon Floor (%)", 0, 5, 0) / 100
    with col2:
        cap = st.slider("Coupon Cap (%)", 5, 50, 50) / 100
    with col3:
        participation = st.slider("Participation Rate (%)", 50, 150, 100) / 100

    # Generate cliquet paths
    np.random.seed(42)
    num_paths = 10000
    reset_dates = np.linspace(0, maturity, num_cliquets + 1)[1:]

    paths = np.zeros((num_paths, len(reset_dates)))
    spot = 100

    for i, date in enumerate(reset_dates):
        returns = np.random.normal(0.02, 0.15, num_paths)
        paths[:, i] = np.maximum(np.minimum(returns * participation, cap), floor)

    # Calculate payoff
    if cliquet_type == "European":
        payoff = np.sum(paths, axis=1)
    elif cliquet_type == "Memory":
        payoff = np.sum(paths, axis=1) * 1.2  # Memory adds value
    else:  # Ratchet
        payoff = np.prod(1 + paths, axis=1) - 1

    cliquet_price = np.mean(payoff) * 100
    cliquet_std = np.std(payoff) * 100

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Cliquet Price", f"€{cliquet_price:.2f}")
    with col2:
        st.metric("Price Std Dev", f"€{cliquet_std:.2f}")
    with col3:
        st.metric("Expected Return", f"{np.mean(payoff)*100:.2f}%")

    # Payoff distribution
    fig_cliquet = go.Figure()
    fig_cliquet.add_trace(go.Histogram(x=payoff*100, nbinsx=50,
                                      marker_color='rgba(69, 183, 209, 0.7)',
                                      name='Cliquet Payoff'))
    fig_cliquet.update_layout(title=f"{cliquet_type} Cliquet Payoff Distribution",
                             xaxis_title="Payoff (%)", yaxis_title="Frequency",
                             template="plotly_dark", height=400)
    st.plotly_chart(fig_cliquet)

elif exotic_type == "Variance Swaps":
    st.markdown("### Variance Swap Pricing & Fair Strike Calculation")

    col1, col2, col3 = st.columns(3)
    with col1:
        var_maturity = st.slider("Variance Swap Maturity (years)", 0.25, 2.0, 1.0)
    with col2:
        var_strike = st.slider("Variance Strike (annualized %)", 10, 50, 20) / 100
    with col3:
        var_notional = st.number_input("Variance Notional (€)", 100000, 10000000, 1000000)

    # Simulate realized variance
    np.random.seed(42)
    daily_returns = np.random.normal(0.0005, 0.015, int(var_maturity * 252))
    realized_var = np.var(daily_returns) * 252
    realized_vol = np.sqrt(realized_var)

    # Variance swap payoff
    var_payoff = var_notional * (realized_var - var_strike**2)
    vol_swap_payoff = var_notional / (np.sqrt(var_strike)) * (realized_vol - var_strike)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Realized Variance", f"{realized_var*100:.4f}%")
    with col2:
        st.metric("Fair Strike Variance", f"{var_strike**2*100:.4f}%")
    with col3:
        st.metric("Variance Swap Payoff", f"€{var_payoff:,.0f}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Realized Vol", f"{realized_vol*100:.2f}%")
    with col2:
        st.metric("Vol Swap Payoff", f"€{vol_swap_payoff:,.0f}")

    # Realized vol path
    realized_vol_path = np.sqrt(np.var(daily_returns[:int(250)]) * 252)

    fig_var = go.Figure()
    fig_var.add_hline(y=var_strike*100, line_dash="dash", line_color="red",
                     annotation_text="Fair Strike")
    fig_var.add_hline(y=realized_vol*100, line_dash="solid", line_color="green",
                     annotation_text="Realized Vol")
    fig_var.add_trace(go.Scatter(y=np.cumsum(np.abs(daily_returns))*100/np.sqrt(np.arange(1, len(daily_returns)+1)),
                                name='Running Realized Vol',
                                line=dict(color='rgba(69, 183, 209, 0.8)')))
    fig_var.update_layout(title="Variance Swap: Realized vs Strike",
                         xaxis_title="Days", yaxis_title="Volatility (%)",
                         template="plotly_dark", height=400)
    st.plotly_chart(fig_var)

elif exotic_type == "Convertible Bonds":
    st.markdown("### Convertible Bond Valuation (Bond + Call Option)")

    col1, col2, col3 = st.columns(3)
    with col1:
        conv_face = st.number_input("Bond Face Value (€)", 100, 1000, 1000)
    with col2:
        conv_coupon = st.slider("Annual Coupon (%)", 1, 10, 5) / 100
    with col3:
        conv_maturity = st.slider("Maturity (years)", 2, 10, 5)

    col1, col2, col3 = st.columns(3)
    with col1:
        conv_spot = st.number_input("Current Stock Price (€)", 10, 100, 50)
    with col2:
        conv_ratio = st.number_input("Conversion Ratio (shares)", 1, 50, 10)
    with col3:
        credit_spread = st.slider("Credit Spread (bps)", 0, 500, 200) / 10000

    # Convertible bond pricing
    risk_free_rate = RISK_FREE_RATE
    discount_rate = risk_free_rate + credit_spread

    # Bond value (straight bond value)
    coupon_pmt = conv_coupon * conv_face
    bond_value = sum([coupon_pmt / (1 + discount_rate)**t for t in range(1, conv_maturity+1)])
    bond_value += conv_face / (1 + discount_rate)**conv_maturity

    # Conversion value
    conversion_value = conv_spot * conv_ratio

    # Embedded call option value (simplified)
    call_value = max(conversion_value - bond_value, 0) * 0.3  # Simplified

    # Convertible value
    convertible_value = bond_value + call_value

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Straight Bond Value", f"€{bond_value:.2f}")
    with col2:
        st.metric("Conversion Value", f"€{conversion_value:.2f}")
    with col3:
        st.metric("Call Option Value", f"€{call_value:.2f}")
    with col4:
        st.metric("Convertible Price", f"€{convertible_value:.2f}")

    st.divider()

    # Payoff diagram
    spot_range = np.linspace(10, 150, 50)
    conversion_payoff = spot_range * conv_ratio
    straight_bond_payoff = np.full_like(spot_range, bond_value)
    convertible_payoff = np.maximum(conversion_payoff, straight_bond_payoff)

    fig_conv = go.Figure()
    fig_conv.add_trace(go.Scatter(x=spot_range, y=convertible_payoff, name='Convertible',
                                 line=dict(color='rgba(69, 183, 209, 0.8)', width=3)))
    fig_conv.add_trace(go.Scatter(x=spot_range, y=conversion_payoff, name='If Converted',
                                 line=dict(color='rgba(100, 200, 100, 0.8)', dash='dash')))
    fig_conv.add_trace(go.Scatter(x=spot_range, y=straight_bond_payoff, name='Bond Floor',
                                 line=dict(color='rgba(255, 165, 0, 0.8)', dash='dot')))
    fig_conv.update_layout(title="Convertible Bond Payoff Profile",
                          xaxis_title="Stock Price (€)", yaxis_title="Value (€)",
                          template="plotly_dark", height=400)
    st.plotly_chart(fig_conv)

elif exotic_type == "Credit-Linked Notes":
    st.markdown("### Credit-Linked Note (CLN) Valuation")

    col1, col2, col3 = st.columns(3)
    with col1:
        cln_notional = st.number_input("CLN Notional (€)", 100000, 10000000, 1000000)
    with col2:
        cln_coupon = st.slider("Annual Coupon (%)", 1, 20, 5) / 100
    with col3:
        cln_maturity = st.slider("Maturity (years)", 1, 10, 5)

    col1, col2, col3 = st.columns(3)
    with col1:
        cln_spread = st.slider("Reference Spread (bps)", 0, 1000, 200) / 10000
    with col2:
        cln_recovery = st.slider("Recovery Rate (%)", 0, 100, 40) / 100
    with col3:
        default_prob = st.slider("Default Probability (%)", 0, 10, 2) / 100

    # CLN valuation
    risk_free_rate = RISK_FREE_RATE

    # Expected coupon and principal
    expected_coupon = cln_coupon * (1 - default_prob) * cln_notional
    expected_principal = (1 - default_prob) * cln_notional + default_prob * cln_recovery * cln_notional

    # Discount for credit risk
    discount_rate = risk_free_rate + cln_spread

    # Present value
    cln_pv_coupons = sum([expected_coupon / (1 + discount_rate)**t for t in range(1, cln_maturity+1)])
    cln_pv_principal = expected_principal / (1 + discount_rate)**cln_maturity

    cln_value = cln_pv_coupons + cln_pv_principal

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("CLN Par Value", f"€{cln_notional:,.0f}")
    with col2:
        st.metric("Fair Value", f"€{cln_value:,.0f}")
    with col3:
        st.metric("Recovery (if default)", f"€{cln_recovery * cln_notional:,.0f}")
    with col4:
        st.metric("OAS Spread", f"{cln_spread*10000:.0f} bps")

    st.divider()

    # Payoff scenarios
    scenarios = ['No Default', 'Early Default', 'Default at Maturity']
    scenario_payoffs = [
        cln_notional + cln_coupon * cln_notional * cln_maturity,
        cln_maturity/2 * cln_coupon * cln_notional + cln_recovery * cln_notional,
        cln_maturity * cln_coupon * cln_notional + cln_recovery * cln_notional
    ]

    fig_cln = go.Figure()
    fig_cln.add_trace(go.Bar(x=scenarios, y=scenario_payoffs,
                            marker_color=['rgba(100, 200, 100, 0.8)',
                                        'rgba(255, 165, 0, 0.8)',
                                        'rgba(255, 107, 107, 0.8)']))
    fig_cln.update_layout(title="CLN Payoff by Scenario",
                         xaxis_title="Scenario", yaxis_title="Total Payoff (€)",
                         template="plotly_dark", height=400)
    st.plotly_chart(fig_cln)

elif exotic_type == "Range Accrual":
    st.markdown("### Range Accrual: Corridor Coupon Structure")

    col1, col2, col3 = st.columns(3)
    with col1:
        range_floor = st.slider("Lower Barrier (% of spot)", 80, 100, 90)
    with col2:
        range_ceil = st.slider("Upper Barrier (% of spot)", 100, 120, 110)
    with col3:
        spot_price = st.number_input("Spot Price (€)", 50, 150, 100)

    col1, col2 = st.columns(2)
    with col1:
        daily_coupon = st.slider("Daily Coupon (bps)", 1, 100, 10) / 10000
    with col2:
        days_in_period = st.number_input("Period Length (days)", 30, 252, 90)

    # Simulate price path and coupon
    np.random.seed(42)
    price_path = spot_price + np.cumsum(np.random.normal(0, 1, days_in_period))

    # Check if price in range each day
    lower_bound = spot_price * range_floor / 100
    upper_bound = spot_price * range_ceil / 100
    in_range = (price_path >= lower_bound) & (price_path <= upper_bound)

    # Accumulate coupon
    coupon_accrued = np.cumsum(in_range) * daily_coupon
    total_coupon = coupon_accrued[-1]
    observation_days = np.sum(in_range)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Days in Range", int(observation_days), f"of {days_in_period}")
    with col2:
        st.metric("Total Coupon Accrued", f"{total_coupon*100:.2f}%")
    with col3:
        st.metric("Effective Yield", f"{total_coupon*365/days_in_period*100:.2f}%")

    st.divider()

    # Visualization
    fig_range = go.Figure()
    fig_range.add_hline(y=lower_bound, line_dash="dash", line_color="red",
                       annotation_text="Lower Barrier")
    fig_range.add_hline(y=upper_bound, line_dash="dash", line_color="red",
                       annotation_text="Upper Barrier")
    fig_range.add_trace(go.Scatter(y=price_path, name='Spot Price',
                                  line=dict(color='rgba(69, 183, 209, 0.8)', width=2)))
    fig_range.update_layout(title="Range Accrual: Spot vs Corridor",
                           xaxis_title="Days", yaxis_title="Price (€)",
                           template="plotly_dark", height=400)
    st.plotly_chart(fig_range)

    # Coupon accrual chart
    fig_coupon = go.Figure()
    fig_coupon.add_trace(go.Scatter(y=coupon_accrued*100, name='Coupon Accrued',
                                   fill='tozeroy', line=dict(color='rgba(100, 200, 100, 0.8)')))
    fig_coupon.update_layout(title="Coupon Accrual Over Time",
                            xaxis_title="Days", yaxis_title="Accrued Coupon (%)",
                            template="plotly_dark", height=300)
    st.plotly_chart(fig_coupon)
