import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st

try:
    from admin_panel import AdminPanel
    BRAKATA_AVAILABLE = True
except ImportError:
    BRAKATA_AVAILABLE = False

user = st.session_state.get("user", None)

if BRAKATA_AVAILABLE:
    if user and user.get("role") == "admin":
        try:
            admin = AdminPanel()
            admin.render()
        except TypeError:
            try:
                auth_mgr = st.session_state.get("auth_manager", None)
                admin = AdminPanel(auth_mgr)
                admin.render()
            except Exception as e:
                st.error(f"Admin Panel error: {e}")
        except Exception as e:
            st.error(f"Admin Panel error: {e}")
    else:
        st.error("Admin Panel is restricted to administrators only.")
else:
    st.error("Admin Panel module not available.")
