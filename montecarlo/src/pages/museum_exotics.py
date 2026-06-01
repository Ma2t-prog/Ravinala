import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header, get_sidebar_market_context

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from engine import MultiAssetPricer
from payoffs import PayoffLibrary
import utils

_render_page_header("MX", "Museum of Exotics", "Vintage structured products and path-dependent mechanics", "Exotics")

market = get_sidebar_market_context()

spot_price = market.spot
volatility = market.volatility
rate = market.rate
carry = market.carry
maturity = market.maturity
n_assets = market.n_assets
target_corr = market.target_corr
corr_matrix = utils.create_correlation_matrix(n_assets, target_corr)

museum_tabs = st.tabs(["Himalaya", "Everest", "Altiplano", "Napoleon"])

# Himalaya Tab
with museum_tabs[0]:
    st.markdown("### **The Himalaya: Best-of Past Performance**")
    st.markdown("""
    **History**: Popular in 2000s-2010s for multi-asset portfolios.

    **Mechanism**:
    - At each observation date, lock in the best-performing asset's return YTD.
    - Remove that asset and repeat.
    - Final payoff = sum of locked returns.

    **Risk**: Path-dependent correlation breakdowns, especially on consecutive low performers.
    """)

    col1, col2 = st.columns(2)
    with col1:
        himalaya_path_steps = st.slider("Path Steps for Himalaya", 4, 52, 12)
    with col2:
        himalaya_obs_freq = st.slider("Obs Frequency (per year)", 1, 12, 4)

    if st.button("Price Himalaya via MC", key="himalaya_mc"):
        with st.spinner("Simulating Himalaya..."):
            mc = MultiAssetPricer(n_simulations=5000)
            spots = np.array([spot_price] * 3)
            vols = np.array([volatility] * 3)
            carries = np.array([carry] * 3)

            paths = mc.simulate_paths(spots, carries, vols, maturity, himalaya_path_steps, corr_matrix)
            obs_idx = np.linspace(0, himalaya_path_steps, himalaya_obs_freq + 1).astype(int)[1:-1]

            payoffs_himalaya = [PayoffLibrary.himalaya(paths[i], obs_idx) for i in range(mc.n_sims)]
            price_himalaya = np.mean(payoffs_himalaya) * np.exp(-rate * maturity)

            st.metric("Himalaya Price", f"€{price_himalaya:.2f}")

            fig = go.Figure()
            fig.add_trace(go.Histogram(x=payoffs_himalaya, nbinsx=50, name='Himalaya Payoffs', marker_color='#fa8231'))
            fig.update_layout(title="Himalaya Payoff Distribution", template="plotly_dark", height=400)
            st.plotly_chart(fig)

# Everest Tab
with museum_tabs[1]:
    st.markdown("### **The Everest: Worst-of on Large Basket**")
    st.markdown("""
    **Concept**: Performance of the worst-performing asset in a large, uncorrelated basket.

    **Why at Risk**: Tail risk on a single underperformer can be severe. Correlation spikes amplify losses.

    **Modern Use**: Used sparingly; mostly for educational purposes on tail risk.
    """)

    if st.button("Price Everest via MC", key="everest_mc"):
        with st.spinner("Simulating Everest..."):
            mc = MultiAssetPricer(n_simulations=5000)
            n_everest = st.slider("Number of Assets in Basked", 5, 15, 8, key="everest_n")

            spots = np.array([spot_price] * n_everest)
            vols = np.array([volatility + np.random.uniform(-0.02, 0.02)] * n_everest)
            carries = np.array([carry] * n_everest)

            paths = mc.simulate_paths(spots, carries, vols, maturity, 252, corr_matrix)
            payoffs_everest = [PayoffLibrary.everest(paths[i, -1, :], spots) for i in range(mc.n_sims)]
            price_everest = np.mean(payoffs_everest) * np.exp(-rate * maturity)

            st.metric("Everest Price", f"€{price_everest:.2f}")

# Altiplano Tab
with museum_tabs[2]:
    st.markdown("### **The Altiplano: Digital Coupon & Barrier**")
    st.markdown("""
    **Feature**: Coupon paid ONLY if no barrier has been breached.

    **All-or-Nothing Logic**: Either full coupon or zero.

    **Vintage Risk**: Investors didn't fully appreciate path-dependent barrier risk.
    """)
    st.info("Altiplano pricing would follow similar MC logic to Himalaya.")

# Napoleon Tab
with museum_tabs[3]:
    st.markdown("### **The Napoleon: Worst Returns by Window**")
    st.markdown("Performance tracked over observation windows; payoff based on average worst-return.")
    st.info("Napoleon is a window-based exotic with historical importance in structured notes.")
