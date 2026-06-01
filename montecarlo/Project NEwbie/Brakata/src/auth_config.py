"""
auth_config.py — Configuration centrale pour le système d'authentification Ravinala.
Modifie ces valeurs pour adapter le comportement du système.
"""

# ═══════════════════════════════════════════════════════════════
# SESSION
# ═══════════════════════════════════════════════════════════════

SESSION_TTL_HOURS = 24           # Durée de vie d'une session (heures)
MAX_SESSIONS_ADMIN = 5           # Sessions simultanées pour l'admin
MAX_SESSIONS_TESTER = 1          # Sessions simultanées pour les testeurs
MAX_SESSIONS_VIEWER = 1

# ═══════════════════════════════════════════════════════════════
# RATE LIMITING
# ═══════════════════════════════════════════════════════════════

MAX_LOGIN_ATTEMPTS = 5           # Tentatives avant lockout
RATE_LIMIT_WINDOW_SECONDS = 60  # Fenêtre de comptage (secondes)
LOCKOUT_DURATION_SECONDS = 300  # Durée du lockout (5 minutes)

# ═══════════════════════════════════════════════════════════════
# SÉCURITÉ
# ═══════════════════════════════════════════════════════════════

PBKDF2_ITERATIONS = 100_000      # Itérations PBKDF2 (NE PAS RÉDUIRE)
MIN_PASSWORD_LENGTH = 6
USERNAME_PATTERN = r'^[a-zA-Z0-9_]{3,20}$'

# ═══════════════════════════════════════════════════════════════
# COMPTES PAR DÉFAUT
# ═══════════════════════════════════════════════════════════════

DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'ravinala2026'  # À changer au premier login !
DEFAULT_ADMIN_DISPLAY_NAME = 'Administrator'

# ═══════════════════════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════════════════════

MAX_LOG_ENTRIES = 1000

# ═══════════════════════════════════════════════════════════════
# TABS DISPONIBLES
# ═══════════════════════════════════════════════════════════════

ALL_TABS = [
    "🎯 Pricing",
    "🏗️ Sandbox",
    "🛠️ Custom",
    "🏛️ Exotics",
    "📊 Macro",
    "⚠️ Risk",
    "📈 Backtest",
    "📉 Vol Cal",
    "🤖 ML",
    "🛡️ Hedging",
    "✨ Advanced",
    "📚 Learn",
]

ADMIN_TAB = "🔐 Admin"

# ═══════════════════════════════════════════════════════════════
# EXPIRATION PAR DÉFAUT
# ═══════════════════════════════════════════════════════════════

DEFAULT_TESTER_EXPIRY_DAYS = 30
DEFAULT_VIEWER_EXPIRY_DAYS = 7

# ═══════════════════════════════════════════════════════════════
# CHEMINS
# ═══════════════════════════════════════════════════════════════

DATA_DIR = 'data'
USERS_FILE = 'data/users.json'
SESSIONS_FILE = 'data/sessions.json'
LOG_FILE = 'data/access_log.json'

# ═══════════════════════════════════════════════════════════════
# WATERMARK
# ═══════════════════════════════════════════════════════════════

WATERMARK_OPACITY = 0.03         # Quasi invisible (0.03 = 3%)
WATERMARK_FONT_SIZE = 16         # px
WATERMARK_ANGLE = -30            # degrés
