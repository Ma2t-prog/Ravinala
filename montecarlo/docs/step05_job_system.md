# Étape 5 — Job System (Celery + Polling)


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

Déporter les opérations longues (>5s) vers des tâches Celery asynchrones. Les clients reçoivent un `job_id` et peuvent poller le statut via `/api/v1/jobs/{job_id}`.

---

## Architecture

```
Client → POST /api/v1/backtest/run → Celery task_id (job_id)
                                        ↓
                               Celery Worker (Redis broker)
                                        ↓
Client → GET /api/v1/jobs/{job_id} → status: PENDING/STARTED/SUCCESS/FAILURE
```

---

## `backend/app/workers/celery_app.py`

```python
celery_app = Celery(
    "ravinala",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.workers.tasks.fetch_task",
        "app.workers.tasks.backtest_task",
        "app.workers.tasks.ml_task",
        "app.workers.tasks.risk_task",
    ]
)
```

Beat schedule (auto-refresh) :

- `refresh-snapshot-every-5min` → `fetch_task` toutes les 5 minutes

---

## 4 Tâches Celery

| Tâche                             | soft_time_limit | time_limit | Usage                  |
| --------------------------------- | --------------- | ---------- | ---------------------- |
| `fetch_task.run_snapshot_refresh` | 120s            | 180s       | Refresh cache marché   |
| `backtest_task.run_backtest`      | 300s            | 360s       | Backtest stratégie     |
| `ml_task.run_ml_training`         | 600s            | 700s       | Entraînement modèle ML |
| `risk_task.compute_risk_report`   | 120s            | 180s       | Calcul rapport risk    |

Toutes les tâches respectent la règle **R3** : accès data via `YFinanceProvider`, jamais `yf.download()` direct.

---

## `backend/app/routes/jobs.py`

```python
@router.get("/{job_id}", response_model=ApiResponse[JobStatus])
async def get_job_status(job_id: str) -> ApiResponse[JobStatus]:
    res = AsyncResult(job_id, app=celery_app)
    return ApiResponse(
        data=JobStatus(job_id=job_id, status=res.status, result=res.result),
        data_quality="live",
        cache_hit=False,
    )
```

Statuts possibles : `PENDING | STARTED | SUCCESS | FAILURE | RETRY | REVOKED`

---

## Lancement Worker

```bash
# Worker
celery -A app.workers.celery_app worker --loglevel=info

# Beat (scheduler)
celery -A app.workers.celery_app beat --loglevel=info

# Dev (combined)
celery -A app.workers.celery_app worker --beat --loglevel=info
```

---

## Variables d'Environnement

```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0  # override optionnel
```

---

## Validation (Q2)

```bash
python scripts/audit_guard.py
# → 0 Q2 violations (toutes les tâches ont soft_time_limit)
```
