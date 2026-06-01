"""
Ravinala by TSIVAHINY Matthias | The Cross-Asset Quantum Structuring Lab
Entry point — sets up page config, auth, CSS, market header, sidebar and navigation.
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Ravinala · Cross-Asset Quantum Lab",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== AUTH (Brakata) ====================
try:
    from auth import AuthManager
    from auth_ui import render_login_page
    from tradebook_ui import render_tradebook_tab
    from admin_panel import AdminPanel
    from protection import AppProtection
    BRAKATA_AVAILABLE = True
except ImportError as e:
    print(f"Brakata import failed: {e}")
    BRAKATA_AVAILABLE = False

if BRAKATA_AVAILABLE:
    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = AuthManager(data_dir='data')
    user = {"username": "demo_user", "role": "admin"}
    st.session_state["user"] = user
    st.session_state["session_id"] = "demo_session_bypass"

# ==================== CSS + TOPBAR ====================
from _shared import inject_shared_css, _render_global_market_header, render_sidebar_market_data

inject_shared_css()

# ==================== MARKET HEADER ====================
_render_global_market_header()

# ==================== PAGES NAVIGATION ====================
_trading = []
if BRAKATA_AVAILABLE:
    _trading = [
        st.Page("pages/tradebook.py", title="Trade Book"),
        st.Page("pages/admin.py",     title="Admin Panel"),
    ]

pages = {
    "": [
        st.Page("pages/home.py", title="Home", default=True),
    ],
    # ── MARKET INTELLIGENCE ───────────────────────────────────────────────
    "MARKET INTEL": [
        st.Page("pages/live_market.py",           title="Live Market"),
        st.Page("pages/market_news.py",           title="Market News"),
        st.Page("pages/macro_analysis.py",        title="Macro Analysis"),
        st.Page("pages/alt_data.py",              title="Alt Data"),
        st.Page("pages/intelligence_center.py",   title="Intelligence"),
        st.Page("pages/financial_analysis.py",    title="Financial Analysis"),
    ],
    # ── DERIVATIVES STRUCTURING ───────────────────────────────────────────
    "DERIVATIVES": [
        st.Page("pages/pricing_center.py",        title="Pricing Center"),
        st.Page("pages/structuring.py",           title="Structuring Suite"),
        st.Page("pages/custom_product.py",        title="Custom Product"),
        st.Page("pages/advanced_exotics.py",      title="Advanced Exotics"),
        st.Page("pages/museum_exotics.py",        title="Museum of Exotics"),
        st.Page("pages/sandbox.py",               title="The Sandbox"),
    ],
    # ── RESEARCH & VALUATIONS ────────────────────────────────────────────
    "RESEARCH": [
        st.Page("pages/enterprise_valuations.py", title="Enterprise Val."),
        st.Page("pages/equity_research.py",       title="Equity Research"),
        st.Page("pages/fixed_income.py",          title="Fixed Income"),
        st.Page("pages/asset_explorer.py",        title="Asset Explorer"),
        st.Page("pages/company_analyzer.py",      title="Company Analyzer"),
        st.Page("pages/etf_explorer.py",          title="ETF Explorer"),
    ],
    # ── QUANTITATIVE RISK ─────────────────────────────────────────────────
    "RISK & QUANT": [
        st.Page("pages/risk_management.py",        title="Risk Management"),
        st.Page("pages/greeks_sensitivity_lab.py", title="Greeks & Sensitivity"),
        st.Page("pages/vol_calibration_page.py",   title="Vol Calibration"),
        st.Page("pages/backtesting_page.py",       title="Backtesting"),
        st.Page("pages/ml_pricing_page.py",        title="ML Pricing"),
        st.Page("pages/hedging_page.py",           title="Hedging"),
    ],
    # ── PORTFOLIO & TRADING DESK ──────────────────────────────────────────
    "PORTFOLIO DESK": [
        st.Page("pages/portfolio_optimizer.py",   title="Portfolio Optimizer"),
        st.Page("pages/strategy_lab.py",          title="Strategy Lab"),
        st.Page("pages/scenario_matrix.py",       title="Scenario Matrix"),
        st.Page("pages/pnl_attribution.py",       title="P&L Attribution"),
        st.Page("pages/position_book.py",         title="Position Book"),
    ],
    # ── TAX LAB Ω — GLOBAL TAX OPTIMIZATION ──────────────────────────────────
    "TAX LAB  Ω": [
        st.Page("pages/tax_lab.py", title="TAX LAB Ω — Full Suite"),
    ],
    # ── GENESIX Ω — INSTITUTIONAL RISK SUITE ─────────────────────────────
    "GENESIX  Ω": [
        # UNIVERSE EXPLORER (v2.1 NEW)
        st.Page("pages/universe_search.py",             title="Universe Search"),
        st.Page("pages/universe_screener.py",           title="Advanced Screener"),
        st.Page("pages/instrument_detail.py",           title="Instrument Analysis"),
        # PORTFOLIO MANAGEMENT
        st.Page("pages/genesix_home.py",                title="Ω Portfolio Omega"),
        st.Page("pages/risk_engine_dashboard.py",       title="Risk Engine"),
        st.Page("pages/performance_tracking.py",        title="Performance Tracking"),
        st.Page("pages/backtest_results.py",            title="Backtesting"),
        st.Page("pages/genesix_ml_engine.py",           title="ML Engine"),
        st.Page("pages/genesix_advanced_analysis.py",   title="Advanced Analysis"),
        st.Page("pages/genesix_market_intelligence.py", title="Market Intelligence"),
        st.Page("pages/genesix_portfolio_monitor.py",   title="Portfolio Monitor"),
        st.Page("pages/genesix_intelligence.py",        title="Signal Intelligence"),
        st.Page("pages/genesix_data_layer.py",          title="Data Layer"),
        # PHYSICS & EDUCATION
        st.Page("pages/physics_demo.py",                title="Physics Lab"),
    ],
    # ── COMPLIANCE & REPORTING ────────────────────────────────────────────
    "COMPLIANCE": [
        st.Page("pages/esg.py",                   title="ESG & Green Lab"),
        st.Page("pages/regulatory_capital.py",    title="Regulatory Capital"),
        st.Page("pages/documentation.py",         title="Report Generator"),
        st.Page("pages/legal.py",                 title="Legal & Compliance"),
    ],
    # ── LEARNING ──────────────────────────────────────────────────────────
    "LEARNING": [
        st.Page("pages/quantum_academy.py",        title="Quantum Academy"),
        st.Page("pages/probability_bible_page.py", title="Probability Bible"),
        st.Page("pages/learn.py",                  title="Learning Hub"),
    ],
}

if _trading:
    pages["TRADING DESK"] = _trading

pg = st.navigation(pages, position="sidebar", expanded=True)

# ==================== SIDEBAR MARKET DATA WIDGETS ====================
render_sidebar_market_data()

pg.run()
