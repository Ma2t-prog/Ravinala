# Étape 12 — Sécurité et Gouvernance


> [!WARNING]
> **Document status: superseded by primary source docs**
> This file is kept for project history and progress traceability.
> Do **not** treat it as current compliance proof or backend architecture evidence.
> For current source-based truth, use:
> - `docs/PRIMARY_SOURCE_BASELINE_INDEX.md`
> - `docs/PRIMARY_SOURCE_DELTA_LEDGER.md`
> - `docs/PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md`

> Date : 2026-03-23
> Statut : **historical**

---

## Objectif

Implémenter l'authentification JWT, le contrôle d'accès RBAC, la gestion des utilisateurs, et un journal d'audit complet pour toutes les actions sensibles.

---

## Endpoints Auth (`/api/v1/auth/`)

| Méthode | Path        | Auth | Description                    |
| ------- | ----------- | ---- | ------------------------------ |
| POST    | `/register` | —    | Créer un compte                |
| POST    | `/login`    | —    | Authentification → JWT token   |
| POST    | `/logout`   | JWT  | Invalider session (audit only) |
| GET     | `/me`       | JWT  | Info utilisateur courant       |

---

## Endpoints Users (`/api/v1/`)

| Méthode | Path               | Rôle       | Description                 |
| ------- | ------------------ | ---------- | --------------------------- |
| GET     | `/users`           | admin      | Liste des utilisateurs      |
| GET     | `/users/{id}`      | admin/self | Profil utilisateur          |
| PUT     | `/users/{id}`      | admin/self | Mettre à jour profil        |
| DELETE  | `/users/{id}`      | admin      | Désactiver (soft-delete)    |
| GET     | `/roles`           | any        | Liste des rôles disponibles |
| GET     | `/audit-trail`     | admin      | Journal d'audit             |
| GET     | `/security/status` | any        | Statut sécurité courant     |

---

## JWT Authentication

```python
# backend/app/auth/jwt_handler.py
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", ...)  # Jamais hardcodé (R6)
ALGORITHM = "HS256"
EXPIRE_MINUTES = settings.jwt_expire_minutes  # Configurable
```

**Flow :**

1. `POST /auth/login` → vérifie credentials → retourne `access_token`
2. Client inclut `Authorization: Bearer <token>` dans chaque requête
3. `get_current_user()` décode et valide le JWT

---

## RBAC (Role-Based Access Control)

Hiérarchie des rôles définie dans `backend/app/auth/rbac.py` :

```python
ROLE_HIERARCHY = {
    "viewer": 1,
    "analyst": 2,
    "trader": 3,
    "admin": 4,
}
```

Usage dans les routes :

```python
@router.get("/admin-only")
async def admin_endpoint(user = Depends(require_role("admin"))):
    ...
```

---

## Modes de Sécurité

`settings.security_level` (depuis `.env`) :

| Niveau | Nom          | Comportement                    |
| ------ | ------------ | ------------------------------- |
| 0      | `local-only` | Auth optionnelle (dev)          |
| 1      | `demo`       | Auth requise, tout token valide |
| 2+     | `production` | RBAC complet                    |

---

## Journal d'Audit

Chaque action sensible est journalisée via `fire_audit()` :

```python
fire_audit(
    action="LOGIN",
    user_id=user.id,
    resource_type="session",
    ip_address=_client_ip(request),
)
```

Actions journalisées : `LOGIN`, `LOGOUT`, `REGISTER`, `USER_UPDATE`, `USER_DELETE`, `ROLE_CHANGE`

---

## Règle R6 — Pas de Secrets en Dur

```python
# src/auth/auth.py — mot de passe admin par défaut
password = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'changeme')

# backend/app/auth/jwt_handler.py
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", ...)
```

Aucun mot de passe ou token ne doit être hardcodé dans le code.

---

## Passwords (Bcrypt)

```python
# backend/app/auth/password.py
hash_password(plain: str) → str     # bcrypt hash
verify_password(plain, hashed) → bool
```

Le modèle `User.password_hash` stocke uniquement le hash bcrypt (jamais le mot de passe en clair).

---

## Variables d'Environnement Requises

```env
JWT_SECRET_KEY=<secret-256-bits>
JWT_EXPIRE_MINUTES=480
ADMIN_DEFAULT_PASSWORD=<strong-password>
SECURITY_LEVEL=2
```
