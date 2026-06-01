# Re-exports from auth submodules — keeps `from auth import AuthManager` etc. working
try:
    from auth.auth import *          # AuthManager
    from auth.auth_ui import *       # render_login_page
    from auth.admin_panel import *   # AdminPanel
    from auth.protection import *    # AppProtection
except Exception:
    pass
