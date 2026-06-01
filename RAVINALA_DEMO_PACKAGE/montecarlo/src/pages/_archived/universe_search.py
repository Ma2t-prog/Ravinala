"""
GENESIX Universe Explorer — Instrument Search
Find and analyze any of 35,000+ instruments globally
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from genesix.universe_explorer import get_pipeline
from genesix.design_system.themes import apply_quantum_dark

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Universe Explorer — Search",
    page_icon="🔍",
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

# ============================================================================
# HEADER
# ============================================================================

col1, col2 = st.columns([1, 3])
with col1:
    st.markdown("### 🔍 Universe Search")
with col2:
    stats = pipeline.get_stats()
    st.markdown(f"**{stats['total']}** instruments · "
                f"**{len(stats['by_sector'])}** sectors · "
                f"**{len(stats['by_country'])}** countries")

st.markdown("---")

# ============================================================================
# SEARCH INPUT
# ============================================================================

col_search, col_type = st.columns([3, 1])

with col_search:
    search_query = st.text_input(
        "Search by ticker, ISIN, or name",
        placeholder="e.g., AAPL, Apple, MSFT, BND...",
        key="search_input",
        help="Search across ticker symbols, company names, and ISIN codes"
    )

with col_type:
    search_limit = st.number_input(
        "Show top N results",
        min_value=5,
        max_value=100,
        value=20,
        step=5
    )

# ============================================================================
# SEARCH RESULTS
# ============================================================================

if search_query:
    st.markdown(f"### Search Results: **{search_query}**")
    
    # Execute search
    results = pipeline.search_instruments(search_query, limit=search_limit)
    
    if results:
        st.success(f"✓ Found **{len(results)}** instrument(s)")
        
        # Convert to DataFrame for display with clickable links
        data = []
        for inst in results:
            ticker_link = f"[{inst.ticker}](?ticker={inst.ticker})"
            data.append({
                "Ticker": ticker_link,
                "Name": inst.name,
                "Sector": inst.sector or "-",
                "Country": inst.country,
                "Price": f"${inst.price:.2f}",
                "1D Change": f"{inst.price_change_1d:+.2f}%",
                "Volatility": f"{inst.volatility_1y * 100:.1f}%" if inst.volatility_1y else "-",
                "Div Yield": f"{inst.dividend_yield * 100:.2f}%" if inst.dividend_yield else "-",
                "P/E": f"{inst.pe_ratio:.1f}" if inst.pe_ratio else "-",
                "Market Cap": f"${inst.market_cap:.0f}B" if inst.market_cap else "-",
            })
        
        df = pd.DataFrame(data)
        
        # Display table with sorting (use markdown mode for clickable links)
        st.markdown("**Results Table** — Click any ticker to view detailed analysis:")
        st.markdown(df.to_markdown(index=False), unsafe_allow_html=True)
        
        # Quick stats on top match
        if results:
            st.markdown("---")
            st.markdown("### Top Match Details")
            
            inst = results[0]
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
            
            with col1:
                st.metric("Price", f"${inst.price:.2f}", f"{inst.price_change_1d:+.2f}%")
            with col2:
                st.metric("Sector", inst.sector or "-")
            with col3:
                st.metric("Country", inst.country)
            with col4:
                st.metric("Exchange", inst.exchange)
            with col5:
                if st.button("View Analysis", key="top_match_detail"):
                    st.switch_page(f"pages/instrument_detail.py")
            
            col6, col7, col8, col9 = st.columns(4)
            
            with col6:
                if inst.pe_ratio:
                    st.metric("P/E Ratio", f"{inst.pe_ratio:.2f}")
                else:
                    st.metric("P/E Ratio", "-")
            
            with col7:
                if inst.dividend_yield:
                    st.metric("Dividend Yield", f"{inst.dividend_yield * 100:.2f}%")
                else:
                    st.metric("Dividend Yield", "-")
            
            with col8:
                if inst.volatility_1y:
                    st.metric("Volatility (1Y)", f"{inst.volatility_1y * 100:.2f}%")
                else:
                    st.metric("Volatility (1Y)", "-")
            
            with col9:
                if inst.beta:
                    st.metric("Beta", f"{inst.beta:.2f}")
                else:
                    st.metric("Beta", "-")
    
    else:
        st.warning(f"No instruments found matching **{search_query}**")
        st.info("Try searching by ticker (e.g., 'AAPL') or sector (e.g., 'Technology')")

else:
    # Show featured instruments
    st.markdown("### Featured Instruments")
    st.info("Start typing in the search box above to find any instrument globally")
    
    # Top performers
    col_top, col_volatile, col_div = st.columns(3)
    
    with col_top:
        st.markdown("#### Most Valuable")
        top = pipeline.get_all()[:3]
        for inst in top:
            st.write(f"**{inst.ticker}** — ${inst.price:.2f}")
    
    with col_volatile:
        st.markdown("#### Highest Volatility")
        volatile = sorted(
            [i for i in pipeline.get_all() if i.volatility_1y],
            key=lambda x: x.volatility_1y,
            reverse=True
        )[:3]
        for inst in volatile:
            st.write(f"**{inst.ticker}** — {inst.volatility_1y:.1f}%")
    
    with col_div:
        st.markdown("#### High Dividend")
        dividend = sorted(
            [i for i in pipeline.get_all() if i.dividend_yield],
            key=lambda x: x.dividend_yield,
            reverse=True
        )[:3]
        for inst in dividend:
            st.write(f"**{inst.ticker}** — {inst.dividend_yield:.2f}%")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption(f"Data updated daily via OpenBB SDK | Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
