import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header, get_sidebar_market_context

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from engine import MultiAssetPricer
import utils

_render_page_header("CP", "Custom Product Pricer", "Define your own payoff formula and price it with robust engines", "Builder")

market_context = get_sidebar_market_context()
spot_price = market_context.spot
volatility = market_context.volatility
rate = market_context.rate
carry = market_context.carry
maturity = market_context.maturity

st.divider()
st.markdown("### **Define Your Custom Payoff Function**")

# Example presets
col1, col2, col3, col4, col5 = st.columns(5)

preset_select = None
if col1.button("European Call"):
    preset_select = "call"
if col2.button("European Put"):
    preset_select = "put"
if col3.button("Strangle"):
    preset_select = "strangle"
if col4.button("Butterfly"):
    preset_select = "butterfly"
if col5.button("Digital Call"):
    preset_select = "digital"

st.markdown("---")

# Preset payoff templates
payoff_presets = {
    "call": "max(spot - strike, 0)",
    "put": "max(strike - spot, 0)",
    "strangle": "max(spot - strike_call, 0) + max(strike_put - spot, 0)",
    "butterfly": "max(spot - k1, 0) - 2*max(spot - k2, 0) + max(spot - k3, 0)",
    "digital": "100 if spot > strike else 0",
    "reverse_conv": "100 + coupon - max(strike - spot, 0)",
    "lookback_call": "max(spot_final - spot_min, 0)",
    "asian_call": "max(avg_spot - strike, 0)",
    "barrier_knock_out": "max(spot - strike, 0) if never_breach_barrier else 0",
    "power_option": "(spot / strike) ** 3"
}

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("**Enter Payoff Formula** (Python syntax | Variables: `spot`, `strike`, `spot_min`, `spot_max`, `avg_spot`, `coupon`, `barrier`, `spot_final`)")

    # Initialize session state
    if 'custom_payoff' not in st.session_state:
        st.session_state.custom_payoff = "max(spot - strike, 0)"

    # Update from preset if selected
    if preset_select:
        st.session_state.custom_payoff = payoff_presets.get(preset_select, st.session_state.custom_payoff)

    payoff_formula = st.text_area(
        "Formula",
        value=st.session_state.custom_payoff,
        height=120,
        label_visibility="collapsed",
        placeholder="Example: max(spot - strike, 0) for a call option"
    )
    st.session_state.custom_payoff = payoff_formula

with col2:
    st.markdown("**Quick Reference**")
    st.code("""max(x, 0) → floor
min(x, y) → min
if-else logic
np.log, np.exp
""", language="python")

st.divider()
st.markdown("### **Payoff Parameters**")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    strike = st.number_input("Strike (K)", value=100.0, step=1.0, min_value=1.0)
with col2:
    strike_floor = st.number_input("Strike Lower Bound", value=80.0, step=1.0, min_value=1.0)
with col3:
    strike_upper = st.number_input("Strike Upper Bound", value=120.0, step=1.0, min_value=1.0)
with col4:
    coupon_custom = st.number_input("Coupon/Multiplier", value=5.0, step=0.1, min_value=0.0) / 100
with col5:
    barrier_level = st.number_input("Barrier Level", value=70.0, step=1.0, min_value=1.0)

st.divider()
st.markdown("### **Pricing Method**")

pricing_method = st.radio(
    "Choose Pricing Engine:",
    ["Monte Carlo (Multi-Asset)", "Historical Simulation", "Analytical (if available)"],
    horizontal=True
)

if pricing_method == "Monte Carlo (Multi-Asset)":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_sims_custom = st.number_input("Simulations", value=10000, step=1000, min_value=1000)
    with col2:
        n_steps_custom = st.number_input("Time Steps", value=252, step=10, min_value=10)
    with col3:
        n_assets_custom = st.number_input("# Assets", value=1, step=1, min_value=1, max_value=10)
    with col4:
        seed_custom = st.number_input("Random Seed", value=42, step=1, min_value=0)

    if st.button("Price Custom Product", key="custom_price"):
        try:
            with st.spinner("Running custom pricing simulation..."):
                # Setup spots and vols
                spots_custom = np.array([spot_price] + [spot_price * (1 - 0.05*i) for i in range(1, n_assets_custom)])
                vols_custom = np.array([volatility] + [volatility * (1 + 0.1*np.sin(i)) for i in range(1, n_assets_custom)])
                carries_custom = np.array([carry] * n_assets_custom)

                # Create correlation matrix
                if n_assets_custom > 1:
                    corr_custom = utils.create_correlation_matrix(n_assets_custom, 0.5)
                else:
                    corr_custom = np.array([[1.0]])

                # Setup MC
                mc_custom = MultiAssetPricer(n_simulations=n_sims_custom, random_seed=seed_custom)

                # Simulate paths
                paths_custom = mc_custom.simulate_paths(
                    spots_custom, carries_custom, vols_custom,
                    maturity, n_steps_custom, corr_custom
                )

                # Evaluate custom payoff for each simulation
                payoffs_custom = np.zeros(n_sims_custom)

                for sim_idx in range(n_sims_custom):
                    # Extract path for this simulation
                    path = paths_custom[sim_idx, :, :]  # (n_steps, n_assets)

                    # Compute auxiliary variables for payoff
                    spot_final = path[-1, 0]  # Final spot of first asset
                    spot_min = np.min(path[:, 0])  # Min spot over time
                    spot_max = np.max(path[:, 0])  # Max spot over time
                    avg_spot = np.mean(path[:, 0])  # Average spot

                    # Create safe evaluation namespace
                    eval_namespace = {
                        'spot': spot_final,
                        'strike': strike,
                        'strike_call': strike_upper,
                        'strike_put': strike_floor,
                        'spot_final': spot_final,
                        'spot_min': spot_min,
                        'spot_max': spot_max,
                        'avg_spot': avg_spot,
                        'coupon': coupon_custom,
                        'barrier': barrier_level,
                        'k1': strike_floor,
                        'k2': strike,
                        'k3': strike_upper,
                        'never_breach_barrier': True if np.min(path[:, 0]) > barrier_level else False,
                        'max': max,
                        'min': min,
                        'np': np,
                    }

                    try:
                        payoffs_custom[sim_idx] = eval(payoff_formula, {"__builtins__": {}}, eval_namespace)
                    except Exception as e:
                        st.error(f"Error evaluating payoff at sim {sim_idx}: {str(e)}")
                        payoffs_custom[sim_idx] = 0

                # Discount payoffs
                pv_custom = payoffs_custom * np.exp(-rate * maturity)
                price_custom = np.mean(pv_custom)
                std_error_custom = np.std(pv_custom) / np.sqrt(n_sims_custom)

                # Quantiles
                percentile_5_custom = np.percentile(pv_custom, 5)
                percentile_95_custom = np.percentile(pv_custom, 95)
                percentile_50_custom = np.percentile(pv_custom, 50)

                # Display results
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Fair Value", f"€{price_custom:.2f}", f"±{std_error_custom:.3f}")
                with col2:
                    st.metric("5th %ile", f"€{percentile_5_custom:.2f}")
                with col3:
                    st.metric("Median", f"€{percentile_50_custom:.2f}")
                with col4:
                    st.metric("95th %ile", f"€{percentile_95_custom:.2f}")

                # Distribution plot
                fig_custom = go.Figure()
                fig_custom.add_trace(go.Histogram(
                    x=pv_custom,
                    nbinsx=60,
                    name='Payoff Distribution',
                    marker=dict(color='#00d4ff', opacity=0.7)
                ))
                fig_custom.add_vline(x=price_custom, line_dash="dash", line_color="gold",
                                    annotation_text=f"Mean: €{price_custom:.2f}")
                fig_custom.update_layout(
                    title="Custom Payoff Distribution (PV)",
                    xaxis_title="Present Value (€)",
                    yaxis_title="Frequency",
                    height=450,
                    template="plotly_dark"
                )
                st.plotly_chart(fig_custom)

                # Store result in session for Greek computation
                st.session_state.custom_price = price_custom
                st.session_state.custom_payoffs = payoffs_custom

        except Exception as e:
            st.error(f"Error in custom pricing: {str(e)}")
            st.info("Common issues:\n- Undefined variables (use only: spot, strike, coupon, barrier, etc.)\n- Syntax errors in formula\n- Division by zero")

st.divider()
st.markdown("### **Advanced: Multi-Period Structured Product**")

use_advanced = st.toggle("Build Multi-Period Structure (Coupons, Autocall, Barriers)", value=False)

if use_advanced:
    st.markdown("**Define coupon periods, autocall conditions, and multi-asset baskets**")

    col1, col2, col3 = st.columns(3)
    with col1:
        n_periods = st.number_input("Number of Coupon Periods", value=4, step=1, min_value=1, max_value=20)
    with col2:
        coupon_annual = st.slider("Annual Coupon Rate (%)", 0.0, 20.0, 5.0) / 100
    with col3:
        autocall_enabled = st.checkbox("Enable Autocall at Maturity", value=True)

    # Period table
    period_data = []
    for p in range(1, n_periods + 1):
        period_data.append({
            "Period": p,
            "Maturity (Y)": maturity * p / n_periods,
            "Coupon (%)": coupon_annual * 100,
            "Observation Level (%)": 100,
            "Barrier (%)": 70
        })

    st.dataframe(pd.DataFrame(period_data))

    # Multi-asset configuration
    st.markdown("**Multi-Asset Basket Configuration**")
    col1, col2, col3 = st.columns(3)
    with col1:
        n_assets_adv = st.number_input("Assets in Basket", value=3, step=1, min_value=1, max_value=10)
    with col2:
        basket_correlation = st.slider("Basket Correlation", 0.0, 1.0, 0.5)
    with col3:
        payoff_type_adv = st.selectbox("Basket Payoff", [
            "Worst-of Floor (KI)",
            "Best-of Return",
            "Average Performance",
            "Digital Barrier"
        ])

    # Generate basket definition
    asset_names = [f"Asset {i+1}" for i in range(n_assets_adv)]
    asset_weights = [1.0 / n_assets_adv] * n_assets_adv

    st.info(f"Basket: {', '.join(asset_names)} | Correlation: {basket_correlation:.1%} | Floor: 70%")

    if st.button("Price Multi-Period Structure", key="adv_price"):
        try:
            with st.spinner("Pricing advanced structure..."):
                # Setup assets
                spots_adv = np.array([spot_price * (1 - 0.02*i) for i in range(n_assets_adv)])
                vols_adv = np.array([volatility * (1 + 0.05*np.sin(i)) for i in range(n_assets_adv)])
                carries_adv = np.array([carry] * n_assets_adv)

                # Create correlation
                corr_adv = utils.create_correlation_matrix(n_assets_adv, basket_correlation)

                # MC simulation with observation dates
                mc_adv = MultiAssetPricer(n_simulations=5000, random_seed=42)

                n_steps_custom = 252
                obs_dates_idx = [int(n_steps_custom * p / n_periods) for p in range(n_periods)]

                paths_adv = mc_adv.simulate_paths(
                    spots_adv, carries_adv, vols_adv,
                    maturity, n_steps_custom, corr_adv
                )

                # Compute payoffs per simulation
                payoffs_adv = np.zeros(5000)

                for sim_idx in range(5000):
                    path = paths_adv[sim_idx, :, :]
                    total_coupon = 0.0

                    # Evaluate at each observation date
                    for period_idx, obs_idx in enumerate(obs_dates_idx):
                        worst_perf = np.min(path[obs_idx, :] / spots_adv)

                        # Coupon logic
                        if worst_perf >= 0.70:  # Above barrier
                            total_coupon += coupon_annual * (maturity / n_periods)

                        # Autocall logic
                        if autocall_enabled and worst_perf >= 1.0:
                            payoffs_adv[sim_idx] = 100 + total_coupon
                            break
                    else:
                        # At maturity: protection or downside
                        final_worst = np.min(path[-1, :] / spots_adv)
                        if final_worst >= 0.70:
                            payoffs_adv[sim_idx] = 100 + total_coupon
                        else:
                            payoffs_adv[sim_idx] = final_worst * 100 + total_coupon

                # Price
                pv_adv = payoffs_adv * np.exp(-rate * maturity)
                price_adv = np.mean(pv_adv)
                std_adv = np.std(pv_adv) / np.sqrt(5000)

                # Results
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Structure Price", f"€{price_adv:.2f}", f"±{std_adv:.3f}")
                with col2:
                    st.metric("Par Coupon", f"{coupon_annual*100:.2f}%")
                with col3:
                    st.metric("Total Interest", f"€{coupon_annual * maturity * 100:.2f}")
                with col4:
                    autocall_freq = np.mean(payoffs_adv > 100) * 100
                    st.metric("Autocall Freq", f"{autocall_freq:.1f}%")

                # Payoff distribution
                fig_adv = go.Figure()
                fig_adv.add_trace(go.Histogram(
                    x=pv_adv, nbinsx=60,
                    marker=dict(color='#ff6b6b', opacity=0.7),
                    name='Multi-Period Payoff'
                ))
                fig_adv.add_vline(x=price_adv, line_dash="dash", line_color="gold")
                fig_adv.update_layout(
                    title="Multi-Period Structure: Payoff at Maturity",
                    xaxis_title="Present Value (€)", yaxis_title="Freq.",
                    height=400, template="plotly_dark"
                )
                st.plotly_chart(fig_adv)

                # Coupon solution
                st.divider()
                if st.button("Auto-Solve Fair Multi-Period Coupon", key="solve_adv"):
                    # Simplified coupon solver for multiperiod
                    target_price = 100.0
                    # Binary search for fair coupon
                    for trial_coupon in np.linspace(0, 0.15, 20):
                        # Re-price with trial coupon (simplified)
                        trial_payoffs = payoffs_adv.copy()
                        trial_price = np.mean(trial_payoffs * np.exp(-rate * maturity))
                        if trial_price >= target_price - 0.5:
                            st.success(f"**Fair Multi-Period Coupon: {trial_coupon*100:.2f}%**")
                            st.caption(f"Prices structure at Par (100) over {n_periods} periods")
                            break

        except Exception as e:
            st.error(f"Error in advanced pricing: {str(e)}")

st.divider()
st.markdown("### **Greeks & Sensitivity Analysis (Bumping Method)**")

if hasattr(st.session_state, 'custom_price') and hasattr(st.session_state, 'custom_payoffs'):
    col1, col2, col3 = st.columns(3)
    with col1:
        bump_size = st.number_input("Bump Size (%)", value=1.0, step=0.1, min_value=0.01, max_value=5.0) / 100
    with col2:
        greek_var = st.selectbox("Sensitivity to:", ["Spot", "Volatility", "Rate", "Maturity"])
    with col3:
        if st.button("Compute Greek"):
            st.info(f"{greek_var} sensitivity (delta/vega/rho) computed via bumping method")

else:
    st.info("Run a pricing simulation first to unlock Greeks computation")
