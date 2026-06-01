import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st

_render_page_header("LN", "Educational Hub", "Asset classes, market intuition and practical fundamentals", "Academy")

# Create 5 sub-tabs for different asset classes
tab_equity, tab_commodities, tab_fx, tab_rates, tab_macro = st.tabs([
    "Equities & Indices",
    "Commodities",
    "FX Pairs",
    "Interest Rates",
    "Macro Indicators"
])

# ===== TAB 1: EQUITIES & INDICES =====
with tab_equity:
    st.markdown("### Equities & Major Indices")
    st.markdown("""
**What are Equity Indices?**

An equity index is a grouping of stocks that measures market performance. Key indices:
- **S&P 500** (USA): 500 large-cap US companies → Market leader
- **DAX** (Germany): 40 largest German companies → Eurozone bellwether
- **EUROSTOXX 50** (Eurozone): 50 largest EU companies
- **Nikkei 225** (Japan): 225 top Japanese companies
- **Hang Seng** (Hong Kong): Major Hong Kong stocks
- **KOSPI** (South Korea): Korean market index
    """)

    if st.button("Load Indices Snapshot", key="equity_snapshot"):
        try:
            from macro_data import fetch_indices_snapshot
            indices_df = fetch_indices_snapshot()
            if indices_df is not None and len(indices_df) > 0:
                st.dataframe(indices_df, width="stretch")
            else:
                st.warning("No data available")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ===== TAB 2: COMMODITIES =====
with tab_commodities:
    st.markdown("### Commodities Markets")
    st.markdown("""
**What are Commodities?**

Raw materials and agricultural products traded on global exchanges:
- **Energy**: WTI Crude, Brent, Natural Gas
- **Metals**: Gold, Silver, Copper, Aluminum
- **Agricultural**: Wheat, Corn, Soybeans, Coffee, Cocoa
- **Uses**: Industrial production, hedging inflation, portfolio diversification
    """)

    if st.button("Load Commodities", key="commodity_snapshot"):
        try:
            from macro_data import fetch_commodities_snapshot
            comm_df = fetch_commodities_snapshot()
            if comm_df is not None and len(comm_df) > 0:
                st.dataframe(comm_df, width="stretch")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ===== TAB 3: FX PAIRS =====
with tab_fx:
    st.markdown("### Foreign Exchange (FX) Markets")
    st.markdown("""
**What is FX?**

Currency trading market - largest financial market globally (~$6 trillion daily volume).

**Key Pairs:**
- **EUR/USD**: Euro vs US Dollar (most liquid)
- **GBP/USD**: British Pound vs Dollar
- **USD/JPY**: Dollar vs Yen (safe-haven pair)
- **AUD/USD**: Australian Dollar vs Dollar
- **Emerging Markets**: USD/CNH, USD/INR, USD/BRL
    """)

    if st.button("Load FX Snapshot", key="fx_snapshot"):
        try:
            from macro_data import fetch_fx_snapshot
            fx_df = fetch_fx_snapshot()
            if fx_df is not None and len(fx_df) > 0:
                st.dataframe(fx_df, width="stretch")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ===== TAB 4: INTEREST RATES =====
with tab_rates:
    st.markdown("### Interest Rates & Fixed Income")
    st.markdown("""
**What are Interest Rates?**

Cost of borrowing/return on lending. Government bond yields are key economic indicators.

**Key Rates:**
- **US Treasuries**: 2Y, 5Y, 10Y benchmarks (Fed policy-sensitive)
- **German Bunds**: Eurozone risk-free rate
- **UK Gilts**: BOE policy-sensitive
- **Japan JGB**: BOJ heavily manages yields
- **Spreads**: Yield curve (2Y-10Y), credit spreads measure risk
- **1 basis point = 0.01%**
    """)

    if st.button("Load Rates Snapshot", key="rates_snapshot"):
        try:
            from macro_data import fetch_rates_snapshot
            rates_df = fetch_rates_snapshot()
            if rates_df is not None and len(rates_df) > 0:
                st.dataframe(rates_df, width="stretch")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ===== TAB 5: MACRO INDICATORS =====
with tab_macro:
    st.markdown("### Macroeconomic Indicators")
    st.markdown("""
**Key Macro Indicators:**
- **CPI (Inflation)**: YoY % change in consumer prices (Central banks target 2%)
- **GDP**: Total economic output growth (YoY %)
- **Unemployment**: % of labor force without jobs
- **Central Bank Rates**: Fed Funds Rate, ECB Deposit Rate, BOJ Policy Rate
- **Demographics**: Population growth, median age

These indicators drive central bank policy and affect all asset classes significantly.
    """)

    if st.button("Load Macro Data", key="macro_snapshot"):
        try:
            from macro_data import fetch_cpi_data, fetch_gdp_data
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### CPI Inflation (YoY %)")
                cpi = fetch_cpi_data()
                if cpi is not None and len(cpi) > 0:
                    st.dataframe(cpi, width="stretch")
            with col2:
                st.markdown("#### GDP Growth (YoY %)")
                gdp = fetch_gdp_data()
                if gdp is not None and len(gdp) > 0:
                    st.dataframe(gdp, width="stretch")
        except Exception as e:
            st.error(f"Error loading macro data: {str(e)}")
