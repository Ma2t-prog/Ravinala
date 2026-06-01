"""
auth.py — Backend authentification complet pour Ravinala.
Gère le hashing des mots de passe, les sessions, le rate limiting et les logs.
"""

import hashlib
import secrets
import json
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class User:
    """Représente un utilisateur."""
    username: str
    password_hash: str
    salt: str
    display_name: str
    role: str                        # 'admin' | 'tester' | 'viewer'
    created_at: str
    expires_at: Optional[str]        # None = pas d'expiration (admin)
    is_active: bool
    max_sessions: int
    last_login: Optional[str]
    login_count: int
    allowed_tabs: Optional[list]     # None = tous les tabs


@dataclass
class Session:
    """Représente une session active."""
    session_id: str
    username: str
    created_at: str
    expires_at: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_active: bool


# ═══════════════════════════════════════════════════════════════
# AUTH MANAGER
# ═══════════════════════════════════════════════════════════════

class AuthManager:
    """
    Gère toute l'authentification de Ravinala.
    Stockage JSON dans data/ — lecture/écriture atomique.
    """

    SESSION_TTL_HOURS = 24
    MAX_LOGIN_ATTEMPTS = 5
    RATE_LIMIT_WINDOW = 60        # secondes
    LOCKOUT_DURATION = 300        # 5 minutes
    MAX_LOG_ENTRIES = 1000
    PBKDF2_ITERATIONS = 100_000

    def __init__(self, data_dir: str = 'data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.users_file = self.data_dir / 'users.json'
        self.sessions_file = self.data_dir / 'sessions.json'
        self.log_file = self.data_dir / 'access_log.json'

        # Compteur de tentatives en mémoire {username: [timestamp, ...]}
        self._login_attempts: dict = {}

        self._init_files()

    # ─────────────────────────────────────────────────────────
    # INIT
    # ─────────────────────────────────────────────────────────

    def _init_files(self):
        """Crée les fichiers JSON s'ils n'existent pas, et le compte admin."""
        # users.json
        if not self.users_file.exists():
            self._write_json(self.users_file, {})

        # sessions.json
        if not self.sessions_file.exists():
            self._write_json(self.sessions_file, {})

        # access_log.json
        if not self.log_file.exists():
            self._write_json(self.log_file, [])

        # Créer admin par défaut si aucun user
        users = self._read_json(self.users_file)
        if not users:
            self._create_default_admin()

    def _create_default_admin(self):
        """Crée le compte admin par défaut au premier lancement."""
        self.create_user(
            username='admin',
            password='ravinala2026',
            display_name='Administrator',
            role='admin',
            expires_in_days=None,
            max_sessions=5,
            allowed_tabs=None
        )

    # ─────────────────────────────────────────────────────────
    # JSON HELPERS
    # ─────────────────────────────────────────────────────────

    def _read_json(self, path: Path) -> any:
        """Lecture JSON avec gestion de corruption."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {} if path != self.log_file else []

    def _write_json(self, path: Path, data: any) -> None:
        """Écriture JSON atomique (write to temp, then rename)."""
        tmp = path.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        tmp.replace(path)

    # ─────────────────────────────────────────────────────────
    # HASHING & SECURITY
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def generate_salt() -> str:
        return secrets.token_hex(32)

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        """PBKDF2-HMAC-SHA256 avec 100 000 itérations."""
        dk = hashlib.pbkdf2_hmac(
            hash_name='sha256',
            password=password.encode('utf-8'),
            salt=salt.encode('utf-8'),
            iterations=AuthManager.PBKDF2_ITERATIONS
        )
        return dk.hex()

    @staticmethod
    def generate_session_token() -> str:
        return secrets.token_urlsafe(64)

    def _verify_password(self, password: str, salt: str, stored_hash: str) -> bool:
        return secrets.compare_digest(
            self.hash_password(password, salt),
            stored_hash
        )

    # ─────────────────────────────────────────────────────────
    # USER MANAGEMENT
    # ─────────────────────────────────────────────────────────

    def create_user(self, username: str, password: str, display_name: str,
                    role: str = 'tester', expires_in_days: Optional[int] = 30,
                    max_sessions: int = 1, allowed_tabs: Optional[list] = None) -> bool:
        """Crée un nouvel utilisateur. Retourne True si créé."""
        # Validations
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return False
        if len(password) < 6:
            return False
        if role not in ('admin', 'tester', 'viewer'):
            return False

        users = self._read_json(self.users_file)
        if username in users:
            return False

        salt = self.generate_salt()
        pw_hash = self.hash_password(password, salt)
        now = datetime.utcnow().isoformat()

        if expires_in_days is not None:
            expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
        else:
            expires_at = None

        user = User(
            username=username,
            password_hash=pw_hash,
            salt=salt,
            display_name=display_name,
            role=role,
            created_at=now,
            expires_at=expires_at,
            is_active=True,
            max_sessions=max_sessions,
            last_login=None,
            login_count=0,
            allowed_tabs=allowed_tabs
        )

        users[username] = asdict(user)
        self._write_json(self.users_file, users)
        self.log_access('system', 'USER_CREATED', True, f'Created user: {username} ({role})')
        return True

    def delete_user(self, username: str) -> bool:
        users = self._read_json(self.users_file)
        if username not in users:
            return False
        del users[username]
        self._write_json(self.users_file, users)
        self.logout_all(username)
        self.log_access('system', 'USER_DELETED', True, f'Deleted user: {username}')
        return True

    def deactivate_user(self, username: str) -> bool:
        users = self._read_json(self.users_file)
        if username not in users:
            return False
        users[username]['is_active'] = False
        self._write_json(self.users_file, users)
        self.logout_all(username)
        return True

    def activate_user(self, username: str) -> bool:
        users = self._read_json(self.users_file)
        if username not in users:
            return False
        users[username]['is_active'] = True
        self._write_json(self.users_file, users)
        return True

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        users = self._read_json(self.users_file)
        if username not in users:
            return False
        u = users[username]
        if not self._verify_password(old_password, u['salt'], u['password_hash']):
            return False
        if len(new_password) < 6:
            return False
        salt = self.generate_salt()
        users[username]['salt'] = salt
        users[username]['password_hash'] = self.hash_password(new_password, salt)
        self._write_json(self.users_file, users)
        self.log_access(username, 'PASSWORD_CHANGED', True)
        return True

    def reset_password(self, username: str, new_password: str) -> bool:
        """Reset admin — pas besoin de l'ancien mot de passe."""
        users = self._read_json(self.users_file)
        if username not in users:
            return False
        if len(new_password) < 6:
            return False
        salt = self.generate_salt()
        users[username]['salt'] = salt
        users[username]['password_hash'] = self.hash_password(new_password, salt)
        self._write_json(self.users_file, users)
        self.log_access('admin', 'PASSWORD_RESET', True, f'Reset password for {username}')
        return True

    def extend_expiry(self, username: str, extra_days: int) -> bool:
        users = self._read_json(self.users_file)
        if username not in users:
            return False
        u = users[username]
        base = datetime.fromisoformat(u['expires_at']) if u.get('expires_at') else datetime.utcnow()
        new_expiry = (base + timedelta(days=extra_days)).isoformat()
        users[username]['expires_at'] = new_expiry
        self._write_json(self.users_file, users)
        return True

    def list_users(self) -> list:
        users = self._read_json(self.users_file)
        result = []
        for u in users.values():
            safe = {k: v for k, v in u.items() if k not in ('password_hash', 'salt')}
            result.append(safe)
        return result

    def get_user(self, username: str) -> Optional[User]:
        users = self._read_json(self.users_file)
        if username not in users:
            return None
        d = users[username]
        return User(**d)

    # ─────────────────────────────────────────────────────────
    # RATE LIMITING
    # ─────────────────────────────────────────────────────────

    def _is_rate_limited(self, username: str) -> bool:
        """Vérifie si l'utilisateur est en rate limit (5 tentatives/min)."""
        now = time.time()
        attempts = self._login_attempts.get(username, [])
        # Garder seulement les tentatives dans la fenêtre
        recent = [t for t in attempts if now - t < self.RATE_LIMIT_WINDOW]
        self._login_attempts[username] = recent
        return len(recent) >= self.MAX_LOGIN_ATTEMPTS

    def _is_locked_out(self, username: str) -> bool:
        """Vérifie si l'utilisateur est en lockout (5 min après 5 échecs)."""
        now = time.time()
        attempts = self._login_attempts.get(username, [])
        if len(attempts) < self.MAX_LOGIN_ATTEMPTS:
            return False
        # Dernier groupe de MAX tentatives
        last_attempts = sorted(attempts)[-self.MAX_LOGIN_ATTEMPTS:]
        earliest = last_attempts[0]
        return (now - earliest) < self.LOCKOUT_DURATION

    def _record_attempt(self, username: str):
        now = time.time()
        attempts = self._login_attempts.get(username, [])
        attempts.append(now)
        # Garder max 20 entrées
        self._login_attempts[username] = attempts[-20:]

    def _clear_attempts(self, username: str):
        self._login_attempts.pop(username, None)

    # ─────────────────────────────────────────────────────────
    # AUTHENTICATION
    # ─────────────────────────────────────────────────────────

    def authenticate(self, username: str, password: str,
                     ip_address: str = None, user_agent: str = None) -> dict:
        """
        Authentifie un utilisateur. Retourne un dict avec success/session_id/user/error.
        """
        # Rate limiting
        if self._is_locked_out(username):
            self.log_access(username, 'LOGIN_FAILED', False, 'Rate limited / locked out')
            return {
                'success': False, 'session_id': None, 'user': None,
                'error': 'Too many failed attempts. Please wait 5 minutes.',
                'error_code': 'RATE_LIMITED'
            }

        users = self._read_json(self.users_file)

        # 1. Utilisateur existe ?
        if username not in users:
            self._record_attempt(username)
            self.log_access(username, 'LOGIN_FAILED', False, 'User not found')
            return {
                'success': False, 'session_id': None, 'user': None,
                'error': 'Invalid username or password.',
                'error_code': 'INVALID_CREDENTIALS'
            }

        u = users[username]

        # 2. Compte actif ?
        if not u['is_active']:
            self.log_access(username, 'LOGIN_FAILED', False, 'Account disabled')
            return {
                'success': False, 'session_id': None, 'user': None,
                'error': 'Your account has been disabled. Contact the administrator.',
                'error_code': 'ACCOUNT_DISABLED'
            }

        # 3. Compte expiré ?
        if u.get('expires_at'):
            if datetime.utcnow() > datetime.fromisoformat(u['expires_at']):
                self.log_access(username, 'LOGIN_FAILED', False, 'Account expired')
                return {
                    'success': False, 'session_id': None, 'user': None,
                    'error': 'Your access has expired. Contact the administrator.',
                    'error_code': 'ACCOUNT_EXPIRED'
                }

        # 4. Mot de passe correct ?
        if not self._verify_password(password, u['salt'], u['password_hash']):
            self._record_attempt(username)
            self.log_access(username, 'LOGIN_FAILED', False, 'Wrong password')
            return {
                'success': False, 'session_id': None, 'user': None,
                'error': 'Invalid username or password.',
                'error_code': 'INVALID_CREDENTIALS'
            }

        # 5. Trop de sessions actives ?
        active_sessions = self._get_active_sessions(username)
        if len(active_sessions) >= u['max_sessions']:
            self.log_access(username, 'LOGIN_FAILED', False, 'Too many sessions')
            return {
                'success': False, 'session_id': None, 'user': None,
                'error': f'Maximum {u["max_sessions"]} concurrent session(s) allowed.',
                'error_code': 'TOO_MANY_SESSIONS'
            }

        # 6. Tout OK → Créer la session
        self._clear_attempts(username)
        session_id = self.generate_session_token()
        now = datetime.utcnow()
        expires_at = (now + timedelta(hours=self.SESSION_TTL_HOURS)).isoformat()

        session = Session(
            session_id=session_id,
            username=username,
            created_at=now.isoformat(),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True
        )

        sessions = self._read_json(self.sessions_file)
        sessions[session_id] = asdict(session)
        self._write_json(self.sessions_file, sessions)

        # Mettre à jour last_login et login_count
        users[username]['last_login'] = now.isoformat()
        users[username]['login_count'] = u.get('login_count', 0) + 1
        self._write_json(self.users_file, users)

        self.log_access(username, 'LOGIN_SUCCESS', True)
        self.cleanup_expired_sessions()

        safe_user = {k: v for k, v in u.items() if k not in ('password_hash', 'salt')}
        safe_user['last_login'] = now.isoformat()

        return {
            'success': True,
            'session_id': session_id,
            'user': safe_user,
            'error': None,
            'error_code': None
        }

    def validate_session(self, session_id: str) -> dict:
        """Vérifie qu'une session est toujours valide."""
        sessions = self._read_json(self.sessions_file)

        if session_id not in sessions:
            return {'valid': False, 'user': None, 'error': 'SESSION_REVOKED'}

        s = sessions[session_id]

        if not s['is_active']:
            return {'valid': False, 'user': None, 'error': 'SESSION_REVOKED'}

        if datetime.utcnow() > datetime.fromisoformat(s['expires_at']):
            # Marquer la session comme expirée
            sessions[session_id]['is_active'] = False
            self._write_json(self.sessions_file, sessions)
            return {'valid': False, 'user': None, 'error': 'SESSION_EXPIRED'}

        # Vérifier l'utilisateur
        users = self._read_json(self.users_file)
        username = s['username']

        if username not in users:
            return {'valid': False, 'user': None, 'error': 'SESSION_REVOKED'}

        u = users[username]

        if not u['is_active']:
            return {'valid': False, 'user': None, 'error': 'USER_DEACTIVATED'}

        if u.get('expires_at') and datetime.utcnow() > datetime.fromisoformat(u['expires_at']):
            return {'valid': False, 'user': None, 'error': 'SESSION_EXPIRED'}

        safe_user = {k: v for k, v in u.items() if k not in ('password_hash', 'salt')}
        return {'valid': True, 'user': safe_user, 'error': None}

    def logout(self, session_id: str) -> bool:
        sessions = self._read_json(self.sessions_file)
        if session_id not in sessions:
            return False
        username = sessions[session_id].get('username', 'unknown')
        sessions[session_id]['is_active'] = False
        self._write_json(self.sessions_file, sessions)
        self.log_access(username, 'LOGOUT', True)
        return True

    def logout_all(self, username: str) -> int:
        sessions = self._read_json(self.sessions_file)
        count = 0
        for sid, s in sessions.items():
            if s['username'] == username and s['is_active']:
                sessions[sid]['is_active'] = False
                count += 1
        if count:
            self._write_json(self.sessions_file, sessions)
        return count

    def _get_active_sessions(self, username: str) -> list:
        sessions = self._read_json(self.sessions_file)
        now = datetime.utcnow()
        return [
            s for s in sessions.values()
            if s['username'] == username
            and s['is_active']
            and datetime.fromisoformat(s['expires_at']) > now
        ]

    # ─────────────────────────────────────────────────────────
    # ACCESS LOGGING
    # ─────────────────────────────────────────────────────────

    def log_access(self, username: str, action: str, success: bool,
                   details: str = '') -> None:
        logs = self._read_json(self.log_file)
        if not isinstance(logs, list):
            logs = []

        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'username': username,
            'action': action,
            'success': success,
            'details': details
        }
        logs.append(entry)

        # Rotation : garder les 1000 dernières entrées
        if len(logs) > self.MAX_LOG_ENTRIES:
            logs = logs[-self.MAX_LOG_ENTRIES:]

        self._write_json(self.log_file, logs)

    def get_access_log(self, username: str = None, last_n: int = 100) -> list:
        logs = self._read_json(self.log_file)
        if not isinstance(logs, list):
            return []
        if username:
            logs = [l for l in logs if l.get('username') == username]
        return logs[-last_n:]

    # ─────────────────────────────────────────────────────────
    # SESSION CLEANUP
    # ─────────────────────────────────────────────────────────

    def cleanup_expired_sessions(self) -> int:
        sessions = self._read_json(self.sessions_file)
        now = datetime.utcnow()
        count = 0
        for sid, s in list(sessions.items()):
            if datetime.fromisoformat(s['expires_at']) < now:
                sessions[sid]['is_active'] = False
                count += 1
        if count:
            self._write_json(self.sessions_file, sessions)
        return count

    def get_active_session_count(self) -> int:
        sessions = self._read_json(self.sessions_file)
        now = datetime.utcnow()
        return sum(
            1 for s in sessions.values()
            if s['is_active'] and datetime.fromisoformat(s['expires_at']) > now
        )
