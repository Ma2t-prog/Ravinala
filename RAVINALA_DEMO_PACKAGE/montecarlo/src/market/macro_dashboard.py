"""MACRO DASHBOARD — Comprehensive Global Macro Intelligence
Uses Ravinala Backend API for real-time equities, FX, bonds, commodities, and macro data
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import inspect
import warnings
import json
import logging

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 10

# ═══════════════════════════════════════════════════════════════════════════
# API INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════

def make_etag(data: dict) -> str:
    """Generate ETag from data hash."""
    import hashlib
    data_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(data_str.encode()).hexdigest()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_snapshot_from_api() -> Optional[dict]:
    """Fetch full dashboard snapshot from Ravinala Backend API."""
    try:
        import httpx
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(f"{API_BASE_URL}/api/v1/snapshot")
            if response.status_code == 200:
                logger.info("API snapshot fetched")
                return response.json()
            else:
                logger.warning(f"API returned {response.status_code}")
                return None
    except Exception as e:
        logger.warning(f"API fetch failed: {e}. Using fallback data.")
        return None

def get_api_data() -> dict:
    """Get data from API, with fallback to mock data."""
    snapshot = fetch_snapshot_from_api()
    
    if snapshot and "indices" in snapshot:
        logger.info("Using API data")
        return snapshot
    else:
        logger.warning("Using fallback mock data")
        return get_fallback_snapshot()

def get_fallback_snapshot() -> dict:
    """Return mock snapshot when API unavailable."""
    return {
        "indices": {
            "americas": [{"symbol": "^GSPC", "name": "S&P 500", "price": 5900, "change": {"percent": 1.2}, "region": "Americas", "timestamp": datetime.utcnow().isoformat(), "is_stale": True}],
            "europe": [],
            "asia_pacific": [],
            "middle_east_other": [],
            "last_updated": datetime.utcnow().isoformat(),
            "cache_age_seconds": 0,
        },
        "bonds": {"bonds": [], "benchmark_country": "Germany", "last_updated": datetime.utcnow().isoformat()},
        "fx": {"usd_base": [], "crosses": [], "last_updated": datetime.utcnow().isoformat()},
        "commodities": {"metals": [], "energy": [], "agriculture": [], "crypto": [], "last_updated": datetime.utcnow().isoformat()},
        "macro": {"indicators": [], "last_updated": datetime.utcnow().isoformat()},
    }

# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def format_price_change(value: float, is_rate: bool = False) -> Tuple[str, str]:
    """Format price/rate change with color indicator."""
    if pd.isna(value):
        return "–", "neutral"
    
    if value > 0:
        return f"▲ {abs(value):.2f}%", ""
    elif value < 0:
        return f"▼ {abs(value):.2f}%", ""
    else:
        return "→ 0.00%", ""

def create_metric_card(label: str, value: str, change: str, color: str, currency: str = "") -> str:
    """Create HTML metric card."""
    return f"""
    <div style="
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(52,211,153,0.2);
        border-radius: 8px;
        padding: 12px;
        margin: 4px;
        flex: 1;
        min-width: 140px;
        text-align: center;
    ">
        <div style="font-size: 11px; color: rgba(255,255,255,0.6); margin-bottom: 4px;">{label}</div>
        <div style="font-size: 18px; font-weight: bold; color: #34D399;">{currency}{value}</div>
        <div style="font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 4px;">{color} {change}</div>
    </div>
    """

def _stretch_kwargs(func) -> dict:
    """Return Streamlit kwargs to stretch component to container width.

    Streamlit is deprecating `use_container_width` in favor of `width="stretch"`.
    This helper keeps compatibility across versions.
    """
    try:
        params = inspect.signature(func).parameters
    except Exception:
        return {}
    if "width" in params:
        return {"width": "stretch"}
    if "use_container_width" in params:
        return {"use_container_width": True}
    return {}

def ui_button(label: str, *, key: str | None = None, **kwargs) -> bool:
    if key is not None:
        kwargs["key"] = key
    kwargs.update(_stretch_kwargs(st.button))
    return st.button(label, **kwargs)

def ui_dataframe(df, **kwargs):
    kwargs.update(_stretch_kwargs(st.dataframe))
    return st.dataframe(df, **kwargs)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD RENDER
# ═══════════════════════════════════════════════════════════════════════════

def render_macro_dashboard():
    """Render complete global macro dashboard using API data."""

    st.markdown(
        """
        <div class="rvn-ph">
          <div class="rvn-ph-icon"></div>
          <div>
            <div class="rvn-ph-title">Global Macro Dashboard</div>
            <p class="rvn-ph-sub">Real-time equities, FX, rates, commodities & macro indicators</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONTROLS & TIMESTAMP
    # ─────────────────────────────────────────────────────────────────────────
    
    col_refresh, col_export, col_time = st.columns([1, 2, 2])
    
    with col_refresh:
        if ui_button("Refresh", key="macro_refresh_btn"):
            st.cache_data.clear()
            st.rerun()
    
    with col_export:
        col_pdf, col_excel, col_email = st.columns(3)
        with col_pdf:
            if ui_button("PDF", key="macro_pdf_btn"):
                st.info("PDF export coming soon")
        with col_excel:
            if ui_button("Excel", key="macro_excel_btn"):
                st.info("Excel export coming soon")
        with col_email:
            if ui_button("Email", key="macro_email_btn"):
                st.info("Email export coming soon")
    
    with col_time:
        st.metric("Last Update", datetime.now().strftime("%H:%M UTC"), "LIVE")
    
    st.divider()
    
    # Fetch data from API
    snapshot = get_api_data()
    
    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 1: GLOBAL INDICES
    # ─────────────────────────────────────────────────────────────────────────
    
    st.header("Global Equity Indices")
    
    indices_data = snapshot.get("indices", {})
    regions_order = ["americas", "europe", "asia_pacific", "middle_east_other"]
    regions_labels = {
        "americas": "US AMERICAS",
        "europe": "EU EUROPE",
        "asia_pacific": "ASIA-PACIFIC",
        "middle_east_other": "MIDDLE EAST & OTHER",
    }
    
    for region_key in regions_order:
        region_indices = indices_data.get(region_key, [])
        
        if region_indices:
            with st.expander(f"{regions_labels.get(region_key, region_key)} ({len(region_indices)} indices)", expanded=True):
                cols = st.columns(5)
                
                for idx, index_item in enumerate(region_indices):
                    with cols[idx % 5]:
                        price = index_item.get("price", 0)
                        change_pct = index_item.get("change", {}).get("percent", 0)
                        name = index_item.get("name", "Unknown")
                        
                        st.metric(
                            label=name,
                            value=f"{price:,.0f}",
                            delta=f"{change_pct:+.2f}%",
                            delta_color="normal" if change_pct >= 0 else "inverse"
                        )
    
    st.divider()
    
    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 2: FIXED INCOME
    # ─────────────────────────────────────────────────────────────────────────
    
    st.header("Fixed Income - Government Bonds")
    st.markdown("*Yield Curves: 2Y, 5Y, 10Y*")
    
    bonds_data = snapshot.get("bonds", {}).get("bonds", [])
    
    if bonds_data:
        bond_records = []
        for bond in bonds_data:
            bond_records.append({
                "Country": bond.get("country", "Unknown"),
                "2Y Yield": f"{bond.get('yield_2y', 0):.2f}%",
                "5Y Yield": f"{bond.get('yield_5y', 0):.2f}%",
                "10Y Yield": f"{bond.get('yield_10y', 0):.2f}%",
                "Spread vs Bund": f"{bond.get('spread_vs_bund', 0):.0f}bp",
            })
        
        ui_dataframe(pd.DataFrame(bond_records), hide_index=True)
    else:
        st.info("Bonds data unavailable")
    
    st.divider()
    
    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 3: FOREIGN EXCHANGE
    # ─────────────────────────────────────────────────────────────────────────
    
    st.header("Foreign Exchange")
    
    fx_data = snapshot.get("fx", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("USD Base Pairs")
        usd_base = fx_data.get("usd_base", [])
        
        if usd_base:
            fx_records = []
            for pair in usd_base:
                fx_records.append({
                    "Pair": pair.get("symbol", "Unknown"),
                    "Price": f"{pair.get('price', 0):.4f}",
                    "Change": f"{pair.get('change', {}).get('percent', 0):+.2f}%",
                })
            
            ui_dataframe(pd.DataFrame(fx_records), hide_index=True)
        else:
            st.info("No data available")
    
    with col2:
        st.subheader("Cross Pairs")
        crosses = fx_data.get("crosses", [])
        
        if crosses:
            fx_records = []
            for pair in crosses:
                fx_records.append({
                    "Pair": pair.get("symbol", "Unknown"),
                    "Price": f"{pair.get('price', 0):.4f}",
                    "Change": f"{pair.get('change', {}).get('percent', 0):+.2f}%",
                })
            
            ui_dataframe(pd.DataFrame(fx_records), hide_index=True)
        else:
            st.info("No data available")
    
    st.divider()
    
    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 4: COMMODITIES
    # ─────────────────────────────────────────────────────────────────────────
    
    st.header("Commodities Markets")
    
    commodities = snapshot.get("commodities", {})
    categories = {
        "Metals": "metals",
        "Energy": "energy",
        "Agriculture": "agriculture",
        "Crypto": "crypto",
    }
    
    for cat_label, cat_key in categories.items():
        cat_data = commodities.get(cat_key, [])
        
        if cat_data:
            with st.expander(f"{cat_label} ({len(cat_data)} commodities)", expanded=True):
                cols = st.columns(4)
                
                for idx, commodity in enumerate(cat_data):
                    with cols[idx % 4]:
                        price = commodity.get("price", 0)
                        change_pct = commodity.get("change", {}).get("percent", 0)
                        name = commodity.get("name", "Unknown")
                        
                        st.metric(
                            label=name,
                            value=f"${price:.2f}",
                            delta=f"{change_pct:+.2f}%",
                            delta_color="normal" if change_pct >= 0 else "inverse"
                        )
    
    st.divider()
    
    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 5: KEY MACRO INDICATORS
    # ─────────────────────────────────────────────────────────────────────────
    
    st.header("Key Macro Indicators Summary")
    
    macro_data = snapshot.get("macro", {}).get("indicators", [])
    
    if macro_data:
        macro_records = []
        for indicator in macro_data:
            macro_records.append({
                "Indicator": indicator.get("name", "Unknown"),
                "Region": indicator.get("region", "Unknown"),
                "Value": f"{indicator.get('value', '–')}",
                "Previous": f"{indicator.get('previous', '–')}",
                "Change": f"{indicator.get('change', '–')}",
            })
        
        ui_dataframe(pd.DataFrame(macro_records), hide_index=True)
    else:
        st.info("Macro indicators unavailable")
    
    st.divider()
    
    # ─────────────────────────────────────────────────────────────────────────
    # FOOTER
    # ─────────────────────────────────────────────────────────────────────────
    
    st.markdown("---")
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    
    with footer_col1:
        st.caption(f"Data: Ravinala Backend API")
    
    with footer_col2:
        last_updated = snapshot.get("indices", {}).get("last_updated", datetime.now().isoformat())
        st.caption(f"Last Updated: {last_updated}")
    
    with footer_col3:
        st.caption("**Ravinala Macro Dashboard v2.0 (API-driven)**")

# Entry point
if __name__ == "__main__":
    render_macro_dashboard()
