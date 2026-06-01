"""
app.py — Point d'entrée principal de Ravinala.
Toute l'application est gatée derrière le système d'authentification.

Pour lancer : streamlit run app.py
"""

import sys
import os

# Ajouter src/ au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import streamlit as st
import streamlit.components.v1 as components

from auth import AuthManager
from auth_ui import render_login_page, render_logout_button
from protection import AppProtection
from admin_panel import AdminPanel
from auth_config import ALL_TABS, ADMIN_TAB
from tradebook_ui import render_tradebook_tab, render_save_to_book_button
from tradebook_models import PricingResult


# ═══════════════════════════════════════════════════════════════
# PAGE CONFIG — doit être le premier appel Streamlit
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Ravinala",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "**Ravinala** — The Cross-Asset Quantum Structuring Lab\n\n© 2026 TSIVAHINY Matthias"
    }
)


# ═══════════════════════════════════════════════════════════════
# INIT AUTH MANAGER (singleton via session_state)
# ═══════════════════════════════════════════════════════════════

if 'auth_manager' not in st.session_state:
    st.session_state.auth_manager = AuthManager(data_dir='data')

auth: AuthManager = st.session_state.auth_manager


# ═══════════════════════════════════════════════════════════════
# ─── GATE AUTH ─── Vérifier si l'utilisateur est connecté
# ═══════════════════════════════════════════════════════════════

is_authenticated = st.session_state.get('authenticated', False)
session_id = st.session_state.get('session_id')

if is_authenticated and session_id:
    # Valider la session à chaque rerun
    check = auth.validate_session(session_id)
    if not check['valid']:
        st.session_state.authenticated = False
        st.session_state.pop('session_id', None)
        st.session_state.pop('user', None)
        st.session_state.login_error = {
            'SESSION_EXPIRED': 'Your session has expired. Please log in again.',
            'SESSION_REVOKED': 'Your session was revoked. Please log in again.',
            'USER_DEACTIVATED': 'Your account has been disabled.',
        }.get(check['error'], 'Session invalid. Please log in again.')
        is_authenticated = False

# ─────────────────────────────────────────────────────────────
# NON AUTHENTIFIÉ → Page de login
# ─────────────────────────────────────────────────────────────

if not is_authenticated:
    credentials = render_login_page()

    if credentials:
        result = auth.authenticate(
            username=credentials['username'],
            password=credentials['password']
        )
        if result['success']:
            st.session_state.authenticated = True
            st.session_state.session_id = result['session_id']
            st.session_state.user = result['user']
            st.rerun()
        else:
            # Mapper les codes d'erreur → messages user-friendly
            error_messages = {
                'INVALID_CREDENTIALS': 'Invalid username or password.',
                'ACCOUNT_EXPIRED': 'Your access has expired. Contact the administrator.',
                'ACCOUNT_DISABLED': 'Your account has been disabled. Contact the administrator.',
                'TOO_MANY_SESSIONS': f"Only {result.get('user', {}).get('max_sessions', 1)} concurrent session(s) allowed. Log out from another device first.",
                'RATE_LIMITED': 'Too many failed attempts. Please wait 5 minutes.',
            }
            st.session_state.login_error = error_messages.get(
                result.get('error_code', ''), result.get('error', 'Authentication failed.')
            )
            st.rerun()

    st.stop()


# ═══════════════════════════════════════════════════════════════
# AUTHENTIFIÉ — Application principale
# ═══════════════════════════════════════════════════════════════

user = st.session_state.user

# ─── Injecter les protections anti-copie ───────────────────
protection_html = AppProtection.get_full_protection_html(user.get('username', 'user'))
components.html(protection_html, height=0)

# ─── Header global ─────────────────────────────────────────
render_logout_button(auth, user)

# Ligne décorative
st.markdown("""
    <div style="border-bottom: 1px solid rgba(52,211,153,0.15);
                margin: 0 0 16px 0;"></div>
""", unsafe_allow_html=True)


# ─── Construire la liste des tabs selon les permissions ────

user_allowed_tabs = user.get('allowed_tabs')  # None = tous
visible_tabs = []

TRADEBOOK_TAB = "📒 Trade Book"

ALL_TABS_WITH_TB = ALL_TABS + [TRADEBOOK_TAB]

for tab in ALL_TABS_WITH_TB:
    if user_allowed_tabs is None:
        visible_tabs.append(tab)
    elif any(allowed in tab for allowed in user_allowed_tabs):
        visible_tabs.append(tab)
    # Trade Book visible to all authenticated users
    elif tab == TRADEBOOK_TAB:
        visible_tabs.append(tab)

# Ajouter le tab Admin si admin
is_admin = (user.get('role') == 'admin')
if is_admin:
    visible_tabs.append(ADMIN_TAB)

if not visible_tabs:
    st.warning("⚠️ No tabs available for your account. Contact the administrator.")
    st.stop()


# ─── Tabs ──────────────────────────────────────────────────

tabs = st.tabs(visible_tabs)

# Index helper
def tab_index(name: str) -> int:
    try:
        return visible_tabs.index(name)
    except ValueError:
        return -1


# ─────────────────────────────────────────────────────────────
# ╔═══════════════════════════════════════════════════════════╗
# ║           CONTENU DES TABS — À REMPLIR                    ║
# ╚═══════════════════════════════════════════════════════════╝
# Remplacez les st.info() par le vrai contenu de chaque tab.
# ─────────────────────────────────────────────────────────────

# 🎯 Pricing
idx = tab_index("🎯 Pricing")
if idx >= 0:
    with tabs[idx]:
        st.header("🎯 Derivatives Pricing")
        st.info("**[PLACEHOLDER]** — Insert your pricing module here.")
        # Example: from src.pricing import render_pricing_tab; render_pricing_tab()

        # ── SAVE TO BOOK PATTERN ──────────────────────────────────────
        # When your pricing module produces a result, wrap it like this:
        #
        # if pricing_done and pricing_result is not None:
        #     render_save_to_book_button(
        #         product_type='vanilla_call',
        #         product_name=product_name,
        #         underlyings=[{'ticker': ticker, 'name': name,
        #                       'asset_class': 'equity_index',
        #                       'spot_at_inception': S, 'current_spot': S,
        #                       'currency': currency}],
        #         notional=notional,
        #         currency=currency,
        #         pricing_result=pricing_result,   # PricingResult object
        #         tenor_years=T,
        #         strike_pct=K_pct,
        #         direction='sell',
        #     )
        # ─────────────────────────────────────────────────────────────

# 🏗️ Sandbox
idx = tab_index("🏗️ Sandbox")
if idx >= 0:
    with tabs[idx]:
        st.header("🏗️ Sandbox")
        st.info("**[PLACEHOLDER]** — Insert your sandbox module here.")

# 🛠️ Custom
idx = tab_index("🛠️ Custom")
if idx >= 0:
    with tabs[idx]:
        st.header("🛠️ Custom Structures")
        st.info("**[PLACEHOLDER]** — Insert your custom structures module here.")

# 🏛️ Exotics
idx = tab_index("🏛️ Exotics")
if idx >= 0:
    with tabs[idx]:
        st.header("🏛️ Exotic Derivatives")
        st.info("**[PLACEHOLDER]** — Insert your exotics module here.")

# 📊 Macro
idx = tab_index("📊 Macro")
if idx >= 0:
    with tabs[idx]:
        st.header("📊 Macro Dashboard")
        st.info("**[PLACEHOLDER]** — Insert your macro module here.")

# ⚠️ Risk
idx = tab_index("⚠️ Risk")
if idx >= 0:
    with tabs[idx]:
        st.header("⚠️ Risk Management")
        st.info("**[PLACEHOLDER]** — Insert your risk module here.")

# 📈 Backtest
idx = tab_index("📈 Backtest")
if idx >= 0:
    with tabs[idx]:
        st.header("📈 Backtesting Engine")
        st.info("**[PLACEHOLDER]** — Insert your backtest module here.")

# 📉 Vol Cal
idx = tab_index("📉 Vol Cal")
if idx >= 0:
    with tabs[idx]:
        st.header("📉 Volatility Calibration")
        st.info("**[PLACEHOLDER]** — Insert your vol calibration module here.")

# 🤖 ML
idx = tab_index("🤖 ML")
if idx >= 0:
    with tabs[idx]:
        st.header("🤖 Machine Learning")
        st.info("**[PLACEHOLDER]** — Insert your ML module here.")

# 🛡️ Hedging
idx = tab_index("🛡️ Hedging")
if idx >= 0:
    with tabs[idx]:
        st.header("🛡️ Hedging Strategies")
        st.info("**[PLACEHOLDER]** — Insert your hedging module here.")

# ✨ Advanced
idx = tab_index("✨ Advanced")
if idx >= 0:
    with tabs[idx]:
        st.header("✨ Advanced Analytics")
        st.info("**[PLACEHOLDER]** — Insert your advanced analytics module here.")

# 📚 Learn
idx = tab_index("📚 Learn")
if idx >= 0:
    with tabs[idx]:
        st.header("📚 Learning Center")
        st.info("**[PLACEHOLDER]** — Insert your learning content here.")

# 📒 Trade Book
idx = tab_index(TRADEBOOK_TAB)
if idx >= 0:
    with tabs[idx]:
        render_tradebook_tab()

# 🔐 Admin (uniquement pour les admins)
if is_admin:
    idx = tab_index(ADMIN_TAB)
    if idx >= 0:
        with tabs[idx]:
            admin = AdminPanel()
            admin.render(auth, user)
