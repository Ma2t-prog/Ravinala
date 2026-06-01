"""
GENESIX Universe Explorer — Advanced Screener
Professional multi-criteria instrument screening
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from genesix.universe_explorer import get_pipeline, ScreenerEngine, ScreenerCriteria, AssetClass
from genesix.design_system.themes import apply_quantum_dark

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Universe Explorer — Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_quantum_dark()

# ============================================================================
# INITIALIZATION
# ============================================================================

@st.cache_resource
def init_pipeline():
    """Initialize universe pipeline (cached)."""
    pipeline = get_pipeline()
    pipeline.ensure_universe_loaded()
    return pipeline

pipeline = init_pipeline()

@st.cache_resource
def init_screener():
    """Initialize screener (cached)."""
    return ScreenerEngine(pipeline.get_all())

screener = init_screener()

# ============================================================================
# HEADER
# ============================================================================

col1, col2 = st.columns([1, 3])
with col1:
    st.markdown("### Advanced Screener")
with col2:
    stats = pipeline.get_stats()
    st.markdown(f"Scan **{stats['total']}** instruments with **10+** criteria")

st.markdown("---")

# ============================================================================
# QUICK SCREENS (PRE-BUILT STRATEGIES)
# ============================================================================

st.markdown("### Quick Screens")

quick_col1, quick_col2, quick_col3 = st.columns(3)

quick_screens = {
    "High Dividend": (None, lambda: screener.screen_high_dividend(min_yield=3.0)),
    "Growth Stocks": (None, lambda: screener.screen_growth()),
    "Value Plays": (None, lambda: screener.screen_value()),
}

for i, (name, (emoji, func)) in enumerate(quick_screens.items()):
    cols = [quick_col1, quick_col2, quick_col3]
    with cols[i]:
        if st.button(f"{name}", use_container_width=True, key=f"quick_{i}"):
            st.session_state.screener_result = func()
            st.session_state.active_tab = "results"

quick_col4, quick_col5, quick_col6 = st.columns(3)

more_screens = {
    "Large-Cap": (None, lambda: screener.screen_large_cap()),
    "Momentum": (None, lambda: screener.screen_momentum()),
    "Low Vol": (None, lambda: screener.screen_low_volatility()),
}

for i, (name, (emoji, func)) in enumerate(more_screens.items()):
    cols = [quick_col4, quick_col5, quick_col6]
    with cols[i]:
        if st.button(f"{name}", use_container_width=True, key=f"quick_more_{i}"):
            st.session_state.screener_result = func()
            st.session_state.active_tab = "results"

st.markdown("---")

# ============================================================================
# CUSTOM SCREENER
# ============================================================================

st.markdown("### Custom Criteria")

with st.expander("📋 Build Custom Screen", expanded=True):
    
    # TAB STRUCTURE for criteria categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Classification",
        "Fundamentals",
        "Risk & Performance",
        "Geographic",
        "ESG"
    ])
    
    # ====== TAB 1: Classification ======
    with tab1:
        st.markdown("**Asset Class & Sector**")
        
        col_asset, col_sector = st.columns(2)
        
        with col_asset:
            asset_classes = st.multiselect(
                "Asset Classes",
                options=[ac.value for ac in AssetClass],
                default=["equity"],
                key="screener_asset_class"
            )
        
        with col_sector:
            sectors = st.multiselect(
                "Sectors",
                options=pipeline.get_sectors(),
                key="screener_sectors",
                help="Leave empty to include all sectors"
            )
    
    # ====== TAB 2: Fundamentals ======
    with tab2:
        st.markdown("**Valuation & Growth Metrics**")
        
        # P/E Ratio
        col_pe1, col_pe2 = st.columns(2)
        with col_pe1:
            pe_min = st.number_input("P/E Ratio (min)", value=0.0, key="screener_pe_min")
        with col_pe2:
            pe_max = st.number_input("P/E Ratio (max)", value=50.0, key="screener_pe_max")
        
        # P/B Ratio
        col_pb1, col_pb2 = st.columns(2)
        with col_pb1:
            pb_min = st.number_input("P/B Ratio (min)", value=0.0, key="screener_pb_min")
        with col_pb2:
            pb_max = st.number_input("P/B Ratio (max)", value=5.0, key="screener_pb_max")
        
        # Dividend Yield
        col_div1, col_div2 = st.columns(2)
        with col_div1:
            div_min = st.number_input("Dividend Yield % (min)", value=0.0, key="screener_div_min")
        with col_div2:
            div_max = st.number_input("Dividend Yield % (max)", value=20.0, key="screener_div_max")
        
        # Market Cap
        st.markdown("**Market Capitalization**")
        market_cap_options = [
            ("Any", (0, None)),
            ("Mega (> $200B)", (200_000_000_000, None)),
            ("Large (> $10B)", (10_000_000_000, None)),
            ("Mid ($2-10B)", (2_000_000_000, 10_000_000_000)),
            ("Small (< $2B)", (0, 2_000_000_000)),
        ]
        market_cap_choice = st.radio(
            "Market Cap Range",
            options=[opt[0] for opt in market_cap_options],
            horizontal=True,
            key="screener_market_cap"
        )
        selected_cap = dict(market_cap_options)[market_cap_choice]
        mc_min, mc_max = selected_cap
    
    # ====== TAB 3: Risk & Performance ======
    with tab3:
        st.markdown("**Risk Metrics**")
        
        col_vol1, col_vol2 = st.columns(2)
        with col_vol1:
            vol_max = st.number_input(
                "Max Volatility (Annual %)",
                value=100.0,
                key="screener_vol_max",
                help="Estimated annual volatility"
            )
        with col_vol2:
            st.info("Low vol: < 20% | Medium: 20-40% | High: > 40%")
        
        # Sharpe Ratio (1-year)
        col_sharpe1, col_sharpe2 = st.columns(2)
        with col_sharpe1:
            sharpe_min = st.number_input(
                "Min Sharpe Ratio (1Y)",
                value=0.0,
                step=0.1,
                key="screener_sharpe_min"
            )
        with col_sharpe2:
            st.info("💡 Sharpe > 1.0 is excellent")
        
        # Price momentum
        col_pc1, col_pc2 = st.columns(2)
        with col_pc1:
            pc_min = st.number_input(
                "Price Change % (min, last day)",
                value=-100.0,
                key="screener_pc_min"
            )
        with col_pc2:
            pc_max = st.number_input(
                "Price Change % (max, last day)",
                value=100.0,
                key="screener_pc_max"
            )
    
    # ====== TAB 4: Geographic ======
    with tab4:
        st.markdown("**Country & Exchange**")
        
        countries = st.multiselect(
            "Countries",
            options=pipeline.get_countries(),
            key="screener_countries",
            help="Leave empty to include all countries"
        )
    
    # ====== TAB 5: ESG ======
    with tab5:
        st.markdown("**Environmental, Social, Governance**")
        
        col_esg1, col_esg2 = st.columns(2)
        with col_esg1:
            esg_min = st.number_input(
                "Min ESG Score (0-100)",
                value=0.0,
                min_value=0.0,
                max_value=100.0,
                step=5.0,
                key="screener_esg_min"
            )
        with col_esg2:
            st.info("💡 Leaders: 70+ | Good: 50-70 | Low: < 50")
    
    # ====== RUN SCREENER ====== 
    st.markdown("---")
    
    # Build criteria from form inputs
    criteria = ScreenerCriteria(
        asset_classes=[AssetClass(ac) for ac in asset_classes] if asset_classes else None,
        sectors=sectors if sectors else None,
        pe_min=pe_min if pe_min > 0 else None,
        pe_max=pe_max if pe_max > 0 else None,
        pb_min=pb_min if pb_min > 0 else None,
        pb_max=pb_max if pb_max > 0 else None,
        dividend_yield_min=div_min if div_min > 0 else None,
        dividend_yield_max=div_max if div_max > 0 else None,
        market_cap_min=mc_min if mc_min > 0 else None,
        market_cap_max=mc_max,
        volatility_max=vol_max if vol_max < 100 else None,
        sharpe_min=sharpe_min if sharpe_min > 0 else None,
        price_change_min=pc_min if pc_min > -100 else None,
        price_change_max=pc_max if pc_max < 100 else None,
        esg_score_min=esg_min if esg_min > 0 else None,
        countries=countries if countries else None,
    )
    
    if st.button("🔍 Run Screener", use_container_width=True, type="primary"):
        st.session_state.screener_result = screener.screen(criteria)
        st.session_state.active_tab = "results"

st.markdown("---")

# ============================================================================
# RESULTS
# ============================================================================

if "screener_result" in st.session_state and st.session_state.screener_result:
    result = st.session_state.screener_result
    
    st.markdown(f"### 📊 Results: **{result.total_count}** instruments")
    st.caption(f"Execution time: {result.execution_time_ms:.1f}ms")
    
    if result.instruments:
        # Convert to DataFrame with clickable links
        data = []
        for inst in result.instruments:
            ticker_link = f"[{inst.ticker}](?ticker={inst.ticker})"
            data.append({
                "Ticker": ticker_link,
                "Name": inst.name,
                "Sector": inst.sector or "-",
                "Country": inst.country,
                "Price": f"${inst.price:.2f}",
                "1D Chg": f"{inst.price_change_1d:+.2f}%",
                "Vol%": f"{inst.volatility_1y * 100:.1f}%" if inst.volatility_1y else "-",
                "P/E": f"{inst.pe_ratio:.1f}" if inst.pe_ratio else "-",
                "Div%": f"{inst.dividend_yield * 100:.2f}%" if inst.dividend_yield else "-",
                "Mkt Cap": f"${inst.market_cap:.0f}B" if inst.market_cap else "-",
            })
        
        df = pd.DataFrame(data)
        
        st.markdown("**Results Table** — Click any ticker to view detailed analysis:")
        st.markdown(df.to_markdown(index=False), unsafe_allow_html=True)
        
        # Export button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"screener_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    
    else:
        st.warning("❌ No instruments match your criteria. Try adjusting filters.")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption(f"Data updated daily via OpenBB SDK | Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
