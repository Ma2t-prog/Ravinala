import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st

try:
    from tradebook_ui import render_tradebook_tab
    BRAKATA_AVAILABLE = True
except ImportError:
    BRAKATA_AVAILABLE = False

if BRAKATA_AVAILABLE:
    try:
        render_tradebook_tab()
    except TypeError:
        try:
            user = st.session_state.get("user", {})
            render_tradebook_tab(user)
        except Exception as e:
            st.error(f"Trade Book module error: {e}")
    except Exception as e:
        st.error(f"Trade Book error: {e}")
else:
    st.error("Trade Book module not available.")
