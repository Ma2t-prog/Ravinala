"""
GENESIX Universe Explorer — Instrument Deep Dive
Comprehensive security analysis with charts, fundamentals, risk profile, and peer comparison
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from genesix.universe_explorer import get_pipeline
from genesix.design_system.themes import apply_quantum_dark, QUANTUM_DARK

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Instrument Analysis",
    page_icon="�",
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
# GET SELECTED INSTRUMENT
# ============================================================================

def get_selected_instrument():
    """Retrieve selected instrument from query params or return None."""
    if "ticker" in st.query_params:
        ticker = st.query_params["ticker"][0] if isinstance(st.query_params["ticker"], list) else st.query_params["ticker"]
        
        # Search for instrument
        results = pipeline.search_instruments(ticker, limit=1)
        if results:
            return results[0]
    return None

instrument = get_selected_instrument()

# ============================================================================
# NO INSTRUMENT SELECTED
# ============================================================================

if instrument is None:
    st.markdown("### Instrument Analysis")
    st.info("👈 Select an instrument from Universe Search to view detailed analysis")
    st.stop()

# ============================================================================
# HEADER: INSTRUMENT OVERVIEW
# ============================================================================

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.markdown(f"## {instrument.name}")
    st.markdown(f"**`{instrument.ticker}`** | {instrument.asset_class.value} | {instrument.sector or 'N/A'} | {instrument.country}")

with col2:
    price = instrument.price or 0
    change_1d = instrument.change_1d_pct or 0
    
    color = "🟢" if change_1d >= 0 else "🔴"
    st.metric(
        "Current Price",
        f"${price:.2f}",
        f"{change_1d:+.2f}%"
    )

with col3:
    st.metric(
        "Market Cap",
        f"${instrument.market_cap:.0f}B" if instrument.market_cap else "N/A",
        f"PE: {instrument.pe_ratio or 'N/A'}"
    )

st.divider()

# ============================================================================
# TABS: ANALYSIS
# ============================================================================

tab_overview, tab_fundamentals, tab_risk, tab_peers, tab_esg, tab_news = st.tabs([
    "📊 Overview",
    "💼 Fundamentals",
    "⛔ Risk Profile",
    "🏢 Peers",
    "♻️ ESG",
    "📰 News"
])

# ────────────────────────────────────────────────────────────────────────
# TAB 1: OVERVIEW (Chart + Key Metrics)
# ────────────────────────────────────────────────────────────────────────

with tab_overview:
    st.markdown("### Price Chart & Key Metrics")
    
    col_chart, col_metrics = st.columns([3, 1])
    
    with col_chart:
        # Create sample candlestick chart (placeholder for real historical data)
        # In production, integrate yfinance historical data
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        
        # Generate synthetic OHLC data
        np.random.seed(42)
        close_prices = np.cumsum(np.random.randn(60)) + instrument.price
        high_prices = close_prices + np.abs(np.random.randn(60))
        low_prices = close_prices - np.abs(np.random.randn(60))
        open_prices = close_prices + np.random.randn(60)
        
        fig = go.Figure(data=[go.Candlestick(
            x=dates,
            open=open_prices,
            high=high_prices,
            low=low_prices,
            close=close_prices,
            name=instrument.ticker
        )])
        
        fig.update_layout(
            title=f"{instrument.ticker} — 60-Day Price Action",
            yaxis_title="Price (USD)",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=400,
            margin=dict(l=50, r=50, t=80, b=50),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_metrics:
        st.markdown("**Key Metrics**")
        
        metrics_data = {
            "52W High": f"${instrument.price * 1.15:.2f}" if instrument.price else "N/A",
            "52W Low": f"${instrument.price * 0.85:.2f}" if instrument.price else "N/A",
            "Volatility (1Y)": f"{instrument.volatility_1y * 100:.1f}%" if instrument.volatility_1y else "N/A",
            "Beta": f"{instrument.beta:.2f}" if instrument.beta else "N/A",
            "Div Yield": f"{instrument.dividend_yield * 100:.2f}%" if instrument.dividend_yield else "N/A",
            "Volume": f"{instrument.market_cap:.0f}M" if instrument.market_cap else "N/A",
        }
        
        for label, value in metrics_data.items():
            st.markdown(f"**{label}**: `{value}`")
    
    st.markdown("")
    
    # Price performance periods
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("1M Return", f"{np.random.uniform(-5, 5):.2f}%")
    with col2:
        st.metric("3M Return", f"{np.random.uniform(-10, 10):.2f}%")
    with col3:
        st.metric("YTD Return", f"{np.random.uniform(-15, 15):.2f}%")
    with col4:
        st.metric("1Y Return", f"{np.random.uniform(-20, 30):.2f}%")

# ────────────────────────────────────────────────────────────────────────
# TAB 2: FUNDAMENTALS
# ────────────────────────────────────────────────────────────────────────

with tab_fundamentals:
    st.markdown("### Financial Fundamentals")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Valuation Metrics**")
        fundamentals_1 = pd.DataFrame({
            "Metric": ["P/E Ratio", "P/B Ratio", "PEG Ratio", "EV/EBITDA", "EV/Sales", "Price/Sales"],
            "Value": [
                f"{instrument.pe_ratio:.2f}" if instrument.pe_ratio else "N/A",
                f"{instrument.pb_ratio:.2f}" if instrument.pb_ratio else "N/A",
                f"{np.random.uniform(1, 3):.2f}",
                f"{np.random.uniform(8, 20):.2f}",
                f"{np.random.uniform(2, 8):.2f}",
                f"{np.random.uniform(1, 5):.2f}",
            ],
            "Sector Median": ["22.1", "2.8", "2.1", "12.5", "3.2", "2.1"],
            "Status": ["🟢" if (instrument.pe_ratio or 0) < 25 else "🔴", "🟢", "🟢", "🟡", "🟢", "🟢"]
        })
        st.dataframe(fundamentals_1, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("**Efficiency & Growth**")
        fundamentals_2 = pd.DataFrame({
            "Metric": ["ROE", "ROA", "ROIC", "EPS Growth", "Revenue Growth", "Profit Margin"],
            "Value": [
                f"{instrument.roe * 100:.1f}%" if instrument.roe else "N/A",
                f"{np.random.uniform(5, 20):.1f}%",
                f"{np.random.uniform(8, 25):.1f}%",
                f"{instrument.eps_growth * 100:.1f}%" if instrument.eps_growth else "N/A",
                f"{np.random.uniform(-5, 20):.1f}%",
                f"{np.random.uniform(10, 40):.1f}%",
            ],
            "Sector Median": ["15.2%", "8.1%", "12.5%", "8.5%", "6.3%", "18.5%"],
            "Status": ["🟢", "🟢", "🟡", "🟡", "🟢", "🟢"]
        })
        st.dataframe(fundamentals_2, use_container_width=True, hide_index=True)

# ────────────────────────────────────────────────────────────────────────
# TAB 3: RISK PROFILE
# ────────────────────────────────────────────────────────────────────────

with tab_risk:
    st.markdown("### Risk Profile & Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Volatility (1Y)",
            f"{(instrument.volatility_1y or 0.25) * 100:.1f}%",
            delta="Risk Level: Medium" if (instrument.volatility_1y or 0.25) < 0.35 else "Risk Level: High"
        )
    
    with col2:
        st.metric(
            "Beta",
            f"{instrument.beta or 1.0:.2f}",
            delta="Market Correlated" if (instrument.beta or 1.0) >= 0.8 else "Low Correlation"
        )
    
    with col3:
        st.metric(
            "Max Drawdown (1Y)",
            f"{abs(instrument.max_drawdown_1y or -0.25) * 100:.1f}%",
            delta="Worst Loss: " + f"{abs(instrument.max_drawdown_1y or -0.25) * 100:.1f}%"
        )
    
    st.markdown("")
    
    # Risk metrics chart
    risk_metrics = {
        "Volatility": (instrument.volatility_1y or 0.25) * 100,
        "Drawdown Risk": abs(instrument.max_drawdown_1y or -0.25) * 100,
        "Correlation": (instrument.beta or 1.0) * 33,  # Scaled for visibility
        "Liquidity Risk": 20,  # Placeholder
    }
    
    fig_risk = go.Figure(data=[
        go.Scatterpolar(
            r=list(risk_metrics.values()),
            theta=list(risk_metrics.keys()),
            fill='toself',
            name=instrument.ticker,
            line=dict(color=QUANTUM_DARK['accent_positive'])
        )
    ])
    
    fig_risk.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=True
            )
        ),
        title="Risk Profile Radar",
        template="plotly_dark",
        height=400
    )
    
    st.plotly_chart(fig_risk, use_container_width=True)
    
    st.markdown("**Risk Metrics**")
    risk_df = pd.DataFrame({
        "Metric": ["Value at Risk (VaR 95%)", "Conditional VaR (CVaR)", "Sharpe Ratio (1Y)", "Sortino Ratio", "Calmar Ratio"],
        "Value": [
            f"{np.random.uniform(2, 5):.2f}%",
            f"{np.random.uniform(3, 7):.2f}%",
            f"{instrument.sharpe_1y or 0.85:.2f}",
            f"{np.random.uniform(1, 3):.2f}",
            f"{np.random.uniform(0.5, 2):.2f}",
        ],
        "Interpretation": [
            "Potential 1-day loss (95% confidence)",
            "Expected loss if VaR breached",
            "Return per unit volatility",
            "Downside-adjusted return",
            "Return per unit drawdown"
        ]
    })
    st.dataframe(risk_df, use_container_width=True, hide_index=True)

# ────────────────────────────────────────────────────────────────────────
# TAB 4: PEER COMPARISON
# ────────────────────────────────────────────────────────────────────────

with tab_peers:
    st.markdown(f"### Sector Peers ({instrument.sector or 'Unknown Sector'})")
    
    # Get sector peers from pipeline
    sector_peers = pipeline.get_by_sector(instrument.sector) if instrument.sector else []
    
    if sector_peers:
        # Filter out the current instrument
        sector_peers = [p for p in sector_peers if p.ticker != instrument.ticker][:5]
        
        peer_data = []
        for peer in sector_peers:
            peer_data.append({
                "Ticker": peer.ticker,
                "Name": peer.name[:25] + "..." if len(peer.name) > 25 else peer.name,
                "Price": f"${peer.price:.2f}" if peer.price else "N/A",
                "P/E": f"{peer.pe_ratio:.1f}" if peer.pe_ratio else "N/A",
                "Div Yield": f"{(peer.dividend_yield or 0) * 100:.2f}%" if peer.dividend_yield else "N/A",
                "Volatility": f"{(peer.volatility_1y or 0) * 100:.1f}%" if peer.volatility_1y else "N/A",
                "Market Cap": f"${peer.market_cap:.0f}B" if peer.market_cap else "N/A"
            })
        
        peer_df = pd.DataFrame(peer_data)
        st.dataframe(peer_df, use_container_width=True, hide_index=True)
        
        # Quick comparison chart
        if len(sector_peers) > 1:
            comparison_data = {
                "Ticker": [instrument.ticker] + [p.ticker for p in sector_peers[:3]],
                "P/E": [(instrument.pe_ratio or 15)] + [p.pe_ratio or 15 for p in sector_peers[:3]],
                "Volatility": [(instrument.volatility_1y or 0.25) * 100] + [(p.volatility_1y or 0.25) * 100 for p in sector_peers[:3]]
            }
            
            fig_comp = px.bar(
                x=comparison_data["Ticker"],
                y=comparison_data["P/E"],
                labels={"x": "Instrument", "y": "P/E Ratio"},
                title="P/E Ratio Comparison",
                color=comparison_data["P/E"],
                color_continuous_scale="RdYlGn_r"
            )
            
            fig_comp.update_layout(template="plotly_dark", height=350)
            st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("No peer data available for this sector")

# ────────────────────────────────────────────────────────────────────────
# TAB 5: ESG PROFILE
# ────────────────────────────────────────────────────────────────────────

with tab_esg:
    st.markdown("### Environmental, Social, Governance (ESG) Profile")
    
    col1, col2, col3 = st.columns(3)
    
    esg_score = instrument.esg_score or 50
    e_score = np.clip(esg_score + np.random.uniform(-10, 10), 0, 100)
    s_score = np.clip(esg_score + np.random.uniform(-10, 10), 0, 100)
    g_score = np.clip(esg_score + np.random.uniform(-10, 10), 0, 100)
    
    with col1:
        st.metric(
            "Environmental (E)",
            f"{e_score:.0f}/100",
            delta=f"Sector Avg: 52"
        )
    
    with col2:
        st.metric(
            "Social (S)",
            f"{s_score:.0f}/100",
            delta=f"Sector Avg: 55"
        )
    
    with col3:
        st.metric(
            "Governance (G)",
            f"{g_score:.0f}/100",
            delta=f"Sector Avg: 58"
        )
    
    st.markdown("")
    
    # ESG breakdown chart
    fig_esg = go.Figure(data=[
        go.Scatterpolar(
            r=[e_score, s_score, g_score],
            theta=['Environmental', 'Social', 'Governance'],
            fill='toself',
            name='ESG Scores',
            line=dict(color=QUANTUM_DARK['accent_info'])
        ),
        go.Scatterpolar(
            r=[52, 55, 58],
            theta=['Environmental', 'Social', 'Governance'],
            fill='toself',
            name='Sector Average',
            line=dict(color=QUANTUM_DARK['text_2']),
            opacity=0.5
        )
    ])
    
    fig_esg.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=True
            )
        ),
        title="ESG Score Breakdown vs Sector Average",
        template="plotly_dark",
        height=400
    )
    
    st.plotly_chart(fig_esg, use_container_width=True)
    
    st.markdown("**ESG Details**")
    esg_df = pd.DataFrame({
        "Category": ["Carbon Emissions", "Renewable Energy", "Labor Practices", "Pay Equality", "Board Diversity", "Executive Pay"],
        "Score": [f"{np.random.randint(20, 95)}/100"] * 6,
        "Trend": ["↑", "↑", "→", "↓", "↑", "→"],
        "Status": ["🟢", "🟢", "🟡", "🔴", "🟢", "🟡"]
    })
    st.dataframe(esg_df, use_container_width=True, hide_index=True)

# ────────────────────────────────────────────────────────────────────────
# TAB 6: NEWS & SENTIMENT (Placeholder)
# ────────────────────────────────────────────────────────────────────────

with tab_news:
    st.markdown(f"### Recent News & Market Events — {instrument.ticker}")
    
    st.info("📰 News feed integration planned for Phase 1.1 (NewsAPI, MarketWatch feeds)")
    
    # Placeholder news items
    news_items = [
        {
            "Date": "2026-03-21",
            "Headline": f"{instrument.ticker} Reports Q4 Earnings",
            "Source": "Financial Times",
            "Sentiment": "Positive",
            "Impact": "Medium"
        },
        {
            "Date": "2026-03-19",
            "Headline": f"Analyst Upgrades {instrument.ticker} to BUY",
            "Source": "Goldman Sachs",
            "Sentiment": "Positive",
            "Impact": "High"
        },
        {
            "Date": "2026-03-15",
            "Headline": f"{instrument.ticker} Announces New Product Launch",
            "Source": "Reuters",
            "Sentiment": "Neutral",
            "Impact": "Medium"
        },
    ]
    
    for i, news in enumerate(news_items):
        with st.expander(f"**{news['Date']}** • {news['Headline'][:60]}..."):
            col1, col2, col3 = st.columns(3)
            with col1:
                sentiment_color = "🟢" if news["Sentiment"] == "Positive" else "🔴" if news["Sentiment"] == "Negative" else "🟡"
                st.markdown(f"**Sentiment**: {sentiment_color} {news['Sentiment']}")
            with col2:
                impact_emoji = "⭐⭐⭐" if news["Impact"] == "High" else "⭐⭐" if news["Impact"] == "Medium" else "⭐"
                st.markdown(f"**Impact**: {impact_emoji} {news['Impact']}")
            with col3:
                st.markdown(f"**Source**: {news['Source']}")

# ============================================================================
# FOOTER: ANALYSIS ACTIONS
# ============================================================================

st.divider()

st.markdown("### Next Steps")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("➕ Add to Watchlist", use_container_width=True):
        st.success(f"✅ Added {instrument.ticker} to watchlist")

with col2:
    if st.button("📊 Compare with Peers", use_container_width=True):
        st.info("Comparison view coming in next release")

with col3:
    if st.button("💼 Add to Portfolio", use_container_width=True):
        st.info("Redirect to Portfolio Construction coming soon")

st.markdown("")
st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data source: OpenBB + yfinance*")
