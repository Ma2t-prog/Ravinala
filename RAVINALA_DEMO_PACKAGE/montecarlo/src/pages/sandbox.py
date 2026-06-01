import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header, get_sidebar_market_context

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from engine import MultiAssetPricer, ZeroCouponBond, CouponSolver
from payoffs import StructuredProductBuilder
import utils

_render_page_header("SB", "The Structurer's Sandbox", "Build and test structured payoffs with Monte Carlo", "Structuring")

market = get_sidebar_market_context()

spot_price = market.spot
volatility = market.volatility
rate = market.rate
carry = market.carry
credit_spread = market.credit_spread
maturity = market.maturity
n_assets = market.n_assets
target_corr = market.target_corr
corr_matrix = utils.create_correlation_matrix(n_assets, target_corr)

st.divider()
st.markdown("### **Step 1: Define Your Funding**")

col1, col2, col3 = st.columns(3)
with col1:
    notional = st.number_input("Notional (Par = 100)", value=100.0, step=1.0, min_value=10.0)
with col2:
    st.metric("Issuer Spread", f"{credit_spread*10000:.0f} bps")
with col3:
    zcb_price = ZeroCouponBond.price(notional, maturity, rate, credit_spread)
    st.metric("ZCB Price", f"€{zcb_price:.2f}")

budget = notional - zcb_price
st.info(f"**Option Budget Available: €{budget:.2f}** (Par - ZCB Price)")

st.divider()
st.markdown("### **Step 2: Choose Your Structure**")

col1, col2, col3 = st.columns(3)
with col1:
    product_category = st.selectbox(
        "Product Category",
        ["Modern", "Vintage", "Hybrid"]
    )
with col2:
    available_products = StructuredProductBuilder.list_products(product_category)
    selected_product = st.selectbox("Product Type", available_products)
with col3:
    st.metric("Budget Needed", f"Estimate → Run MC")

st.divider()
st.markdown("### **Step 3: Configure Parameters**")

if selected_product == "athena":
    col1, col2, col3 = st.columns(3)
    with col1:
        coupon = st.slider("Annual Coupon (%)", 1, 15, 5) / 100
    with col2:
        barrier = st.slider("Barrier Level (%)", 40, 100, 70) / 100
    with col3:
        autocall_level = st.slider("Autocall Level (%)", 100, 150, 120) / 100

elif selected_product == "phoenix":
    col1, col2 = st.columns(2)
    with col1:
        coupon = st.slider("Annual Coupon (%)", 1, 15, 6) / 100
    with col2:
        barrier = st.slider("Barrier Level (%)", 40, 100, 60) / 100

elif selected_product == "himalaya":
    col1, col2 = st.columns(2)
    with col1:
        n_obs_dates = st.slider("Observation Dates", 2, 12, 4)
    with col2:
        st.caption(f"Path-dependent on best performers")

else:
    st.info(f"Configure {selected_product} with default basket")

st.divider()
st.markdown("### **Step 4: Run Monte Carlo Simulation**")

if st.button("Price Structure (10k simulations)", key="mc_price"):
    with st.spinner("Running Monte Carlo..."):
        # Setup MC
        mc = MultiAssetPricer(n_simulations=10000, random_seed=42)

        # Multi-asset setup
        spots = np.array([spot_price, spot_price * 0.95, spot_price * 1.05])
        vols = np.array([volatility, volatility * 1.1, volatility * 0.9])
        carries = np.array([carry, carry - 0.01, carry + 0.01])

        # Simulate worst-of basket
        def worst_of_payoff(final_spots):
            worst_perf = np.min(final_spots / spots)
            return max(worst_perf, 0.5) * 100  # With floor

        try:
            mc_result = mc.payoff_distribution(
                worst_of_payoff,
                spots, carries, vols,
                T=maturity,
                r=rate,
                n_steps=252,
                correlation_matrix=corr_matrix
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Fair Value", f"€{mc_result['price']:.2f}")
            with col2:
                st.metric("Std Error", f"±€{mc_result['std_error']:.2f}")
            with col3:
                st.metric("5th Percentile", f"€{mc_result['percentile_5']:.2f}")
            with col4:
                st.metric("95th Percentile", f"€{mc_result['percentile_95']:.2f}")

            # Histogram of outcomes
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=mc_result['pv'],
                nbinsx=50,
                name='PV Distribution',
                marker=dict(color='#00d4ff')
            ))
            fig_hist.add_vline(x=mc_result['price'], line_dash="dash", line_color="red", annotation_text="Mean")
            fig_hist.update_layout(
                title="Monte Carlo Payoff Distribution",
                xaxis_title="Present Value (€)",
                yaxis_title="Frequency",
                height=400,
                template="plotly_dark"
            )
            st.plotly_chart(fig_hist)

            # Solve for Coupon
            st.divider()
            st.markdown("### **The Solver: Find Fair Coupon @ Par**")

            if st.button("Solve for Fair Coupon", key="solve_coupon"):
                with st.spinner("Optimizing..."):
                    coupon_dates = np.array([maturity/n for n in range(1, int(maturity*4)+1)])
                    option_value = mc_result['price'] - zcb_price  # Remaining budget
                    fair_coupon = CouponSolver.solve_coupon(coupon_dates, 0.7, option_value, rate)

                    st.success(f"**Fair Annual Coupon: {fair_coupon*100:.2f}%**")
                    st.caption("This coupon ensures the product prices at Par (100) with your credit spread")

        except Exception as e:
            st.error(f"Error in MC simulation: {str(e)}")
