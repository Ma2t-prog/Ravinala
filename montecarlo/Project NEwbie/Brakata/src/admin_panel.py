"""
admin_panel.py — Panel d'administration Ravinala.
Accessible uniquement aux utilisateurs avec role='admin'.
Gestion complète des utilisateurs, sessions, logs et sécurité.
"""

import streamlit as st
import secrets
import string
from datetime import datetime
import pandas as pd

from auth import AuthManager
from auth_config import ALL_TABS, DEFAULT_TESTER_EXPIRY_DAYS


class AdminPanel:
    """
    Panel d'administration accessible uniquement par les admins.
    """

    # ─────────────────────────────────────────────────────────
    # RENDER PRINCIPAL
    # ─────────────────────────────────────────────────────────

    def render(self, auth_manager: AuthManager, current_user: dict):
        """Affiche le panel admin complet."""
        if current_user.get('role') != 'admin':
            st.error("⛔ Access denied — Admin role required.")
            return

        st.markdown("""
            <style>
            .admin-header {
                font-family: 'Orbitron', sans-serif;
                font-size: 13px;
                letter-spacing: 3px;
                color: #34D399;
                text-transform: uppercase;
                margin-bottom: 4px;
            }
            .metric-card {
                background: rgba(15,23,42,0.6);
                border: 1px solid rgba(52,211,153,0.2);
                border-radius: 12px;
                padding: 16px 20px;
                text-align: center;
            }
            .metric-value {
                font-family: 'Orbitron', sans-serif;
                font-size: 28px;
                color: #34D399;
                font-weight: 700;
            }
            .metric-label {
                font-size: 11px;
                color: #64748B;
                letter-spacing: 2px;
                text-transform: uppercase;
                margin-top: 4px;
            }
            </style>
        """, unsafe_allow_html=True)

        st.markdown('<p class="admin-header">🔐 Administration Panel</p>', unsafe_allow_html=True)
        st.markdown("---")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Dashboard",
            "👥 Users",
            "📋 Access Log",
            "🔒 Security",
            "✉️ Quick Invite"
        ])

        with tab1:
            self._render_dashboard(auth_manager)
        with tab2:
            self._render_user_management(auth_manager)
        with tab3:
            self._render_access_log(auth_manager)
        with tab4:
            self._render_security(auth_manager, current_user)
        with tab5:
            self._render_quick_invite(auth_manager)

    # ─────────────────────────────────────────────────────────
    # 1. DASHBOARD
    # ─────────────────────────────────────────────────────────

    def _render_dashboard(self, auth: AuthManager):
        st.subheader("Overview")

        users = auth.list_users()
        active_users = [u for u in users if u['is_active']]
        active_sessions = auth.get_active_session_count()

        # Comptes expirant bientôt (7 jours)
        now = datetime.utcnow()
        expiring_soon = []
        for u in users:
            if u.get('expires_at'):
                try:
                    exp = datetime.fromisoformat(u['expires_at'])
                    days_left = (exp - now).days
                    if 0 <= days_left <= 7:
                        expiring_soon.append({**u, 'days_left': days_left})
                except Exception:
                    pass

        # Métriques
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", len(users))
        with col2:
            st.metric("Active Users", len(active_users))
        with col3:
            st.metric("Live Sessions", active_sessions)
        with col4:
            st.metric("Expiring Soon", len(expiring_soon), delta=None,
                      delta_color="inverse" if expiring_soon else "normal")

        st.markdown("---")

        # Dernières connexions
        st.subheader("Recent Activity")
        logs = auth.get_access_log(last_n=20)
        if logs:
            log_data = []
            for entry in reversed(logs):
                ts = entry.get('timestamp', '')
                try:
                    ts = datetime.fromisoformat(ts).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass
                log_data.append({
                    'Time': ts,
                    'User': entry.get('username', '-'),
                    'Action': entry.get('action', '-'),
                    'Status': '✅' if entry.get('success') else '❌',
                    'Details': entry.get('details', '')
                })
            st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)
        else:
            st.info("No activity logged yet.")

        # Alertes expiration
        if expiring_soon:
            st.markdown("---")
            st.warning(f"⚠️ **{len(expiring_soon)} account(s) expiring within 7 days:**")
            for u in expiring_soon:
                st.write(f"- **{u['display_name']}** (`{u['username']}`) — "
                         f"{u['days_left']} day(s) left")

    # ─────────────────────────────────────────────────────────
    # 2. USER MANAGEMENT
    # ─────────────────────────────────────────────────────────

    def _render_user_management(self, auth: AuthManager):
        st.subheader("User List")

        users = auth.list_users()
        now = datetime.utcnow()

        if not users:
            st.info("No users found.")
        else:
            # Tableau principal
            for u in users:
                with st.expander(
                    f"{'🟢' if u['is_active'] else '🔴'}  "
                    f"**{u['display_name']}** — `{u['username']}` — {u['role'].upper()}"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Role:** {u['role']}")
                        st.write(f"**Status:** {'Active ✅' if u['is_active'] else 'Disabled ❌'}")
                        st.write(f"**Created:** {u.get('created_at', '-')[:10]}")
                        st.write(f"**Last Login:** {u.get('last_login', 'Never')}")
                        st.write(f"**Login Count:** {u.get('login_count', 0)}")
                    with col2:
                        if u.get('expires_at'):
                            exp = datetime.fromisoformat(u['expires_at'])
                            days_left = (exp - now).days
                            color = "🔴" if days_left < 3 else ("🟡" if days_left < 7 else "🟢")
                            st.write(f"**Expires:** {u['expires_at'][:10]} {color} ({days_left}d)")
                        else:
                            st.write("**Expires:** Never (admin)")
                        st.write(f"**Max Sessions:** {u.get('max_sessions', 1)}")
                        tabs_allowed = u.get('allowed_tabs')
                        st.write(f"**Tabs:** {'All' if tabs_allowed is None else ', '.join(tabs_allowed)}")

                    st.markdown("---")
                    uid = u['username']
                    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)

                    with btn_col1:
                        if u['is_active']:
                            if st.button("🚫 Disable", key=f"dis_{uid}"):
                                auth.deactivate_user(uid)
                                st.success(f"User {uid} disabled.")
                                st.rerun()
                        else:
                            if st.button("✅ Enable", key=f"ena_{uid}"):
                                auth.activate_user(uid)
                                st.success(f"User {uid} enabled.")
                                st.rerun()

                    with btn_col2:
                        if st.button("🔑 Reset pwd", key=f"rpwd_{uid}"):
                            st.session_state[f'reset_pwd_{uid}'] = True

                    with btn_col3:
                        if st.button("📅 +30 days", key=f"ext_{uid}"):
                            auth.extend_expiry(uid, 30)
                            st.success(f"Extended {uid} by 30 days.")
                            st.rerun()

                    with btn_col4:
                        if st.button("🚪 Logout all", key=f"loa_{uid}"):
                            n = auth.logout_all(uid)
                            st.success(f"Revoked {n} session(s).")
                            st.rerun()

                    with btn_col5:
                        if st.button("🗑️ Delete", key=f"del_{uid}",
                                     type="primary" if False else "secondary"):
                            if uid != 'admin':
                                auth.delete_user(uid)
                                st.success(f"User {uid} deleted.")
                                st.rerun()
                            else:
                                st.error("Cannot delete the admin account.")

                    # Formulaire reset password
                    if st.session_state.get(f'reset_pwd_{uid}'):
                        new_pwd = st.text_input(f"New password for {uid}",
                                                type="password",
                                                key=f"npwd_{uid}")
                        if st.button("Confirm Reset", key=f"crst_{uid}"):
                            if auth.reset_password(uid, new_pwd):
                                st.success(f"Password reset for {uid}.")
                                del st.session_state[f'reset_pwd_{uid}']
                                st.rerun()
                            else:
                                st.error("Password too short (min 6 chars).")

        st.markdown("---")
        st.subheader("➕ Create New User")
        self._render_create_user_form(auth)

    def _render_create_user_form(self, auth: AuthManager):
        with st.form("create_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username *",
                                             placeholder="john_doe",
                                             help="3-20 chars, letters/digits/underscore")
                new_display = st.text_input("Display Name *",
                                            placeholder="John Doe")
            with col2:
                new_password = st.text_input("Password *",
                                             type="password",
                                             placeholder="min 6 chars")
                new_role = st.selectbox("Role", ['tester', 'viewer', 'admin'])

            col3, col4 = st.columns(2)
            with col3:
                expiry_days = st.slider("Expiry (days)", 1, 365,
                                        DEFAULT_TESTER_EXPIRY_DAYS,
                                        help="0 = no expiry (admin only)")
            with col4:
                max_sess = st.slider("Max concurrent sessions", 1, 5, 1)

            allowed_tabs = st.multiselect(
                "Allowed tabs (empty = all)",
                ALL_TABS,
                default=[]
            )

            submitted = st.form_submit_button("✅ Create User", use_container_width=True)
            if submitted:
                if not new_username or not new_password or not new_display:
                    st.error("Username, Display Name and Password are required.")
                else:
                    tabs = allowed_tabs if allowed_tabs else None
                    exp = expiry_days if new_role != 'admin' else None
                    success = auth.create_user(
                        username=new_username,
                        password=new_password,
                        display_name=new_display,
                        role=new_role,
                        expires_in_days=exp,
                        max_sessions=max_sess,
                        allowed_tabs=tabs
                    )
                    if success:
                        st.success(f"✅ User **{new_username}** created successfully!")
                    else:
                        st.error("Failed to create user. Username may already exist or be invalid.")

    # ─────────────────────────────────────────────────────────
    # 3. ACCESS LOG
    # ─────────────────────────────────────────────────────────

    def _render_access_log(self, auth: AuthManager):
        st.subheader("Access Log")

        col1, col2 = st.columns(2)
        with col1:
            filter_user = st.text_input("Filter by username", placeholder="Leave empty for all")
        with col2:
            filter_n = st.slider("Show last N entries", 10, 500, 100)

        logs = auth.get_access_log(
            username=filter_user.strip() if filter_user.strip() else None,
            last_n=filter_n
        )

        if not logs:
            st.info("No log entries found.")
            return

        log_data = []
        for entry in reversed(logs):
            ts = entry.get('timestamp', '')
            try:
                ts = datetime.fromisoformat(ts).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
            log_data.append({
                'Timestamp': ts,
                'Username': entry.get('username', '-'),
                'Action': entry.get('action', '-'),
                'Success': '✅' if entry.get('success') else '❌',
                'Details': entry.get('details', '')
            })

        df = pd.DataFrame(log_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Export CSV
        csv = df.to_csv(index=False)
        st.download_button(
            "⬇️ Export CSV",
            data=csv,
            file_name=f"ravinala_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    # ─────────────────────────────────────────────────────────
    # 4. SECURITY
    # ─────────────────────────────────────────────────────────

    def _render_security(self, auth: AuthManager, current_user: dict):
        st.subheader("Security Controls")

        st.warning("""
        ⚠️ **Nuclear Options** — These actions affect ALL users immediately.
        """)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔴 Logout ALL users", use_container_width=True,
                         help="Revokes every active session across all users"):
                users = auth.list_users()
                total = 0
                for u in users:
                    total += auth.logout_all(u['username'])
                st.success(f"✅ Revoked {total} total sessions.")
                st.rerun()

        with col2:
            st.info("Use 'Logout ALL' to force everyone to re-authenticate.")

        st.markdown("---")
        st.subheader("Change Admin Password")

        with st.form("change_admin_pwd"):
            old_pwd = st.text_input("Current password", type="password")
            new_pwd = st.text_input("New password", type="password")
            new_pwd2 = st.text_input("Confirm new password", type="password")
            submitted = st.form_submit_button("Update Password", use_container_width=True)
            if submitted:
                if new_pwd != new_pwd2:
                    st.error("New passwords do not match.")
                elif len(new_pwd) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    if auth.change_password(current_user['username'], old_pwd, new_pwd):
                        st.success("✅ Password changed. You'll be logged out shortly.")
                        auth.logout_all(current_user['username'])
                        st.session_state.authenticated = False
                        st.session_state.pop('session_id', None)
                        st.session_state.pop('user', None)
                        st.rerun()
                    else:
                        st.error("Incorrect current password.")

        st.markdown("---")
        st.subheader("📋 Protection Notes")
        from protection import AppProtection
        st.code(AppProtection.add_source_obfuscation_note(), language=None)

    # ─────────────────────────────────────────────────────────
    # 5. QUICK INVITE
    # ─────────────────────────────────────────────────────────

    def _render_quick_invite(self, auth: AuthManager):
        st.subheader("Quick Invite — Generate Tester Account")
        st.markdown(
            "Quickly create a tester account and copy-paste credentials to share."
        )

        with st.form("quick_invite_form", clear_on_submit=False):
            name_input = st.text_input(
                "Tester name or email",
                placeholder="e.g. John Doe  or  john@example.com"
            )
            invite_days = st.slider("Access duration (days)", 7, 90, 30)
            submitted = st.form_submit_button("🚀 Generate Account", use_container_width=True)

            if submitted and name_input.strip():
                username, password, display = self._generate_credentials(name_input.strip())
                success = auth.create_user(
                    username=username,
                    password=password,
                    display_name=display,
                    role='tester',
                    expires_in_days=invite_days,
                    max_sessions=1,
                    allowed_tabs=None
                )

                if success:
                    st.session_state['last_invite'] = {
                        'username': username,
                        'password': password,
                        'display': display,
                        'days': invite_days
                    }
                else:
                    # Essayer avec un suffix
                    suffix = secrets.token_hex(2)
                    username = f"{username}_{suffix}"
                    success = auth.create_user(
                        username=username, password=password,
                        display_name=display, role='tester',
                        expires_in_days=invite_days, max_sessions=1
                    )
                    if success:
                        st.session_state['last_invite'] = {
                            'username': username,
                            'password': password,
                            'display': display,
                            'days': invite_days
                        }
                    else:
                        st.error("Failed to generate account. Try again.")

        # Afficher les credentials générés
        invite = st.session_state.get('last_invite')
        if invite:
            st.markdown("---")
            st.success("✅ Account created! Share these credentials:")
            st.code(
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  RAVINALA — Access Credentials\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  Username : {invite['username']}\n"
                f"  Password : {invite['password']}\n"
                f"  Valid for: {invite['days']} days\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                language=None
            )
            if st.button("🗑️ Clear credentials", key="clear_invite"):
                del st.session_state['last_invite']
                st.rerun()

    @staticmethod
    def _generate_credentials(name_input: str) -> tuple[str, str, str]:
        """Génère un username et un password aléatoire à partir d'un nom."""
        # Nettoyer le nom
        import re
        # Extraire la partie avant @
        clean = name_input.split('@')[0].strip()
        # Remplacer les espaces et caractères spéciaux
        clean = re.sub(r'[^a-zA-Z0-9 ]', '', clean)
        parts = clean.lower().split()

        if len(parts) >= 2:
            username = f"{parts[0]}.{parts[1]}"[:18]
        elif parts:
            username = parts[0][:18]
        else:
            username = f"user_{secrets.token_hex(3)}"

        # Supprimer les points en trop
        username = re.sub(r'\.{2,}', '.', username).strip('.')

        # Password aléatoire lisible (format: Word + digits + symbol)
        words = ['Alpha', 'Beta', 'Delta', 'Sigma', 'Nova', 'Orbit', 'Vega', 'Lyra']
        pw = (
            secrets.choice(words)
            + str(secrets.randbelow(90) + 10)
            + secrets.choice(['!', '#', '@', '$'])
        )

        display = name_input.split('@')[0].strip().title()
        return username, pw, display
