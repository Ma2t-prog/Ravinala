"""
Instrument Navigator — Unified instrument discovery, screening & exploration
Fusion of: universe_search + universe_screener + asset_explorer + etf_explorer
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import pandas as pd

from genesix.universe_explorer import get_pipeline, ScreenerEngine, ScreenerCriteria, AssetClass
from genesix.design_system.themes import apply_quantum_dark

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Instrument Navigator",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_quantum_dark()

_render_page_header("IN", "Instrument Navigator",
                    "Search, screen and explore 35,000+ instruments globally",
                    "Universe")

# ============================================================================
# INITIALIZATION
# ============================================================================

@st.cache_resource
def init_pipeline():
    pipeline = get_pipeline()
    pipeline.ensure_universe_loaded()
    return pipeline

@st.cache_resource
def init_screener():
    return ScreenerEngine(pipeline.get_all())

pipeline = init_pipeline()
screener = init_screener()

stats = pipeline.get_stats()
st.caption(f"**{stats['total']}** instruments · **{len(stats['by_sector'])}** sectors · **{len(stats['by_country'])}** countries")

# ============================================================================
# TABS
# ============================================================================

tab_search, tab_screener, tab_assets, tab_etf = st.tabs([
    "Search",
    "Screener",
    "Asset Classes",
    "ETF Focus",
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — SEARCH (from universe_search.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_search:
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
            min_value=5, max_value=100, value=20, step=5
        )

    if search_query:
        st.markdown(f"### Search Results: **{search_query}**")
        results = pipeline.search_instruments(search_query, limit=search_limit)

        if results:
            st.success(f"Found **{len(results)}** instrument(s)")

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
            st.markdown("**Results Table** — Click any ticker to view detailed analysis:")
            st.markdown(df.to_markdown(index=False), unsafe_allow_html=True)

            # Top match details
            st.markdown("---")
            st.markdown("### Top Match Details")
            inst = results[0]
            col1, col2, col3, col4, col5 = st.columns(5)
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
                    st.switch_page("pages/instrument_detail.py")

            col6, col7, col8, col9 = st.columns(4)
            with col6:
                st.metric("P/E Ratio", f"{inst.pe_ratio:.2f}" if inst.pe_ratio else "-")
            with col7:
                st.metric("Dividend Yield", f"{inst.dividend_yield * 100:.2f}%" if inst.dividend_yield else "-")
            with col8:
                st.metric("Volatility (1Y)", f"{inst.volatility_1y * 100:.2f}%" if inst.volatility_1y else "-")
            with col9:
                st.metric("Beta", f"{inst.beta:.2f}" if inst.beta else "-")
        else:
            st.warning(f"No instruments found matching **{search_query}**")
            st.info("Try searching by ticker (e.g., 'AAPL') or sector (e.g., 'Technology')")
    else:
        st.markdown("### Featured Instruments")
        st.info("Start typing in the search box above to find any instrument globally")

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
                key=lambda x: x.volatility_1y, reverse=True
            )[:3]
            for inst in volatile:
                st.write(f"**{inst.ticker}** — {inst.volatility_1y:.1f}%")
        with col_div:
            st.markdown("#### High Dividend")
            dividend = sorted(
                [i for i in pipeline.get_all() if i.dividend_yield],
                key=lambda x: x.dividend_yield, reverse=True
            )[:3]
            for inst in dividend:
                st.write(f"**{inst.ticker}** — {inst.dividend_yield:.2f}%")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — SCREENER (from universe_screener.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_screener:
    st.markdown("### Quick Screens")

    quick_col1, quick_col2, quick_col3 = st.columns(3)
    quick_screens = {
        "High Dividend": lambda: screener.screen_high_dividend(min_yield=3.0),
        "Growth Stocks": lambda: screener.screen_growth(),
        "Value Plays": lambda: screener.screen_value(),
    }
    for i, (name, func) in enumerate(quick_screens.items()):
        with [quick_col1, quick_col2, quick_col3][i]:
            if st.button(name, use_container_width=True, key=f"quick_{i}"):
                st.session_state.screener_result = func()

    quick_col4, quick_col5, quick_col6 = st.columns(3)
    more_screens = {
        "Large-Cap": lambda: screener.screen_large_cap(),
        "Momentum": lambda: screener.screen_momentum(),
        "Low Vol": lambda: screener.screen_low_volatility(),
    }
    for i, (name, func) in enumerate(more_screens.items()):
        with [quick_col4, quick_col5, quick_col6][i]:
            if st.button(name, use_container_width=True, key=f"quick_more_{i}"):
                st.session_state.screener_result = func()

    st.markdown("---")

    # Custom criteria builder
    st.markdown("### Custom Criteria")
    with st.expander("Build Custom Screen", expanded=True):
        stab1, stab2, stab3, stab4, stab5 = st.tabs([
            "Classification", "Fundamentals", "Risk & Performance", "Geographic", "ESG"
        ])

        with stab1:
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

        with stab2:
            st.markdown("**Valuation & Growth Metrics**")
            col_pe1, col_pe2 = st.columns(2)
            with col_pe1:
                pe_min = st.number_input("P/E Ratio (min)", value=0.0, key="screener_pe_min")
            with col_pe2:
                pe_max = st.number_input("P/E Ratio (max)", value=50.0, key="screener_pe_max")

            col_pb1, col_pb2 = st.columns(2)
            with col_pb1:
                pb_min = st.number_input("P/B Ratio (min)", value=0.0, key="screener_pb_min")
            with col_pb2:
                pb_max = st.number_input("P/B Ratio (max)", value=5.0, key="screener_pb_max")

            col_div1, col_div2 = st.columns(2)
            with col_div1:
                div_min = st.number_input("Dividend Yield % (min)", value=0.0, key="screener_div_min")
            with col_div2:
                div_max = st.number_input("Dividend Yield % (max)", value=20.0, key="screener_div_max")

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

        with stab3:
            st.markdown("**Risk Metrics**")
            col_vol1, col_vol2 = st.columns(2)
            with col_vol1:
                vol_max = st.number_input("Max Volatility (Annual %)", value=100.0, key="screener_vol_max")
            with col_vol2:
                st.info("Low vol: < 20% | Medium: 20-40% | High: > 40%")

            col_sharpe1, col_sharpe2 = st.columns(2)
            with col_sharpe1:
                sharpe_min = st.number_input("Min Sharpe Ratio (1Y)", value=0.0, step=0.1, key="screener_sharpe_min")
            with col_sharpe2:
                st.info("Sharpe > 1.0 is excellent")

            col_pc1, col_pc2 = st.columns(2)
            with col_pc1:
                pc_min = st.number_input("Price Change % (min)", value=-100.0, key="screener_pc_min")
            with col_pc2:
                pc_max = st.number_input("Price Change % (max)", value=100.0, key="screener_pc_max")

        with stab4:
            st.markdown("**Country & Exchange**")
            countries = st.multiselect(
                "Countries",
                options=pipeline.get_countries(),
                key="screener_countries",
                help="Leave empty to include all countries"
            )

        with stab5:
            st.markdown("**Environmental, Social, Governance**")
            col_esg1, col_esg2 = st.columns(2)
            with col_esg1:
                esg_min = st.number_input("Min ESG Score (0-100)", value=0.0,
                                          min_value=0.0, max_value=100.0, step=5.0,
                                          key="screener_esg_min")
            with col_esg2:
                st.info("Leaders: 70+ | Good: 50-70 | Low: < 50")

        st.markdown("---")

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

        if st.button("Run Screener", use_container_width=True, type="primary"):
            st.session_state.screener_result = screener.screen(criteria)

    st.markdown("---")

    # Results display
    if "screener_result" in st.session_state and st.session_state.screener_result:
        result = st.session_state.screener_result
        st.markdown(f"### Results: **{result.total_count}** instruments")
        st.caption(f"Execution time: {result.execution_time_ms:.1f}ms")

        if result.instruments:
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
            st.markdown(df.to_markdown(index=False), unsafe_allow_html=True)

            csv = df.to_csv(index=False)
            st.download_button("Export CSV", csv, "screener_results.csv", "text/csv")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — ASSET CLASSES (from asset_explorer.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_assets:
    from unified_asset_explorer import render_unified_asset_explorer
    render_unified_asset_explorer()

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — ETF FOCUS (from etf_explorer.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_etf:
    try:
        from etf_explorer import render_etf_explorer
        render_etf_explorer()
    except ImportError:
        st.info("ETF Explorer module not yet available. Coming soon.")
