import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st

# ── Advanced Dashboard: Macro Analysis Complete ────────────────────────────────
try:
    from macro_dashboard import render_macro_dashboard
    MACRO_DASHBOARD_AVAILABLE = True
except ImportError:
    MACRO_DASHBOARD_AVAILABLE = False

_render_page_header("MA", "Macro Analysis", "Global cross-asset regime and economic dashboard", "Macro")

if MACRO_DASHBOARD_AVAILABLE:
    render_macro_dashboard()
else:
    st.error("Macro Dashboard is not available. Please ensure macro_dashboard module is installed.")
    st.info("Falling back to basic macro data view...")
    try:
        from macro_data import render_macro_tab
        render_macro_tab()
    except ImportError:
        st.warning("Basic macro view also unavailable.")
