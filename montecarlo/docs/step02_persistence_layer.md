# Étape 2 — Persistance Minimale (SQLAlchemy Async)


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

Ajouter une couche de persistance async (PostgreSQL via TimescaleDB) avec dégradation gracieuse : si `DATABASE_URL` n'est pas configuré, le backend démarre quand même sans base de données.

---

## Implémentation

### `backend/app/db/base.py`

Engine SQLAlchemy async. Connexion optionnelle :

```python
# Graceful degradation: si DATABASE_URL absent → backend sans DB
if DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, ...)
    AsyncSessionLocal = async_sessionmaker(engine)
else:
    engine = None
    AsyncSessionLocal = None
```

Fonctions exportées :

- `init_db()` — crée les tables (lifespan FastAPI)
- `close_db()` — ferme les connexions proprement
- `get_session()` — dépendance FastAPI → `AsyncSession | None`
- `engine_status()` — `"connected"` | `"not_configured"`

### `backend/app/db/models.py`

9 entités DB async (style `Mapped`) :

| Modèle             | Table                 | Usage                              |
| ------------------ | --------------------- | ---------------------------------- |
| `User`             | `users`               | Authentification JWT               |
| `BacktestRun`      | `backtest_runs`       | Résultats backtests (27 colonnes)  |
| `BacktestTrade`    | `backtest_trades`     | Trades individuels (13 colonnes)   |
| `MLTrainingRun`    | `ml_training_runs`    | Historique entraînements ML        |
| `RiskSnapshot`     | `risk_snapshots`      | Snapshots risk (VaR, CVaR, Sharpe) |
| `CeleryTaskResult` | `celery_task_results` | Cache résultats tâches async       |
| `PriceFetchLog`    | `price_fetch_log`     | Traçabilité des fetches data       |
| `AuditEvent`       | `audit_events`        | Journal sécurité                   |
| `ApiEvent`         | `api_events`          | Logs d'appels API                  |

### `deployment/docker-compose.yml`

```yaml
services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: ravinala
      POSTGRES_USER: ravinala
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

---

## Configuration

```env
DATABASE_URL=postgresql+asyncpg://ravinala:password@localhost:5432/ravinala
```

---

## Schéma DB Sync

**Règle R4** : `src/db/models.py` (Column style, sync) doit toujours être en sync avec `backend/app/db/models.py` (Mapped style, async). Les colonnes de `BacktestRun` et `BacktestTrade` sont identiques dans les deux fichiers.

---

## Dégradation Gracieuse

Sans `DATABASE_URL` :

- Toutes les routes DB-dépendantes retournent `503 Service Unavailable`
- Le backend démarre normalement
- Le cache Redis reste fonctionnel
- Les endpoints market (yfinance) fonctionnent

---

## Validation

```bash
python scripts/audit_guard.py
# → 0 R4 violations
```
