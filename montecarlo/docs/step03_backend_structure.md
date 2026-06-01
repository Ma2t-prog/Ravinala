# Étape 3 — Structuration Backend (App Factory + Routes)

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

Historique de la structuration FastAPI, initialement décrite avec un pattern `create_app()` factory. Le code actuel expose un `app` module-level dans `backend/app/main.py`; garder cette page comme trace d'époque, pas comme preuve de structure actuelle.

---

## Structure Implémentée

```
backend/app/
├── main.py                       ← FastAPI app module (historical factory note)
├── models.py                     ← Pydantic models (BondsSnapshotModel, etc.)
├── routes/
│   ├── market.py                 ← GET /snapshot, /indices, /bonds, /fx-pairs, /commodities, /macro
│   ├── export.py                 ← POST /export/excel, /export/pdf
│   └── generate.py               ← POST /generate/termsheet, /scenariobook, /risksummary
├── services/
│   ├── data_fetcher.py           ← yfinance + static fetchers
│   ├── snapshot_service.py       ← Full dashboard builder async
│   └── cache.py                  ← Redis + in-memory (MAX_MEMORY_CACHE_SIZE=500)
└── providers/
    └── yfinance_adapter.py       ← Adapter isolant yfinance (R3 compliance)
```

## Routes Market (7 endpoints)

| Méthode | Path                  | Description                   | Cache  |
| ------- | --------------------- | ----------------------------- | ------ |
| GET     | `/api/v1/snapshot`    | Dashboard complet             | 15 min |
| GET     | `/api/v1/indices`     | 30 indices globaux            | 5 min  |
| GET     | `/api/v1/bonds`       | Rendements obligations        | 1 h    |
| GET     | `/api/v1/fx-pairs`    | 20 paires FX                  | 5 min  |
| GET     | `/api/v1/commodities` | Métaux, énergie, agro, crypto | 5 min  |
| GET     | `/api/v1/macro`       | CPI, PMI, GDP, chômage        | 1 j    |
| POST    | `/api/v1/refresh`     | Force-clear cache             | —      |

## Routes Export (2 endpoints)

| Méthode | Path                   | Description             |
| ------- | ---------------------- | ----------------------- |
| POST    | `/api/v1/export/excel` | Dashboard → .xlsx       |
| POST    | `/api/v1/export/pdf`   | Dashboard → PDF paysage |

## Routes Generate (3 endpoints)

| Méthode | Path                            | Description               | Timeout |
| ------- | ------------------------------- | ------------------------- | ------- |
| POST    | `/api/v1/generate/termsheet`    | Term sheet bancaire PDF   | 30s     |
| POST    | `/api/v1/generate/scenariobook` | Scenario book 10-15 pages | 60s     |
| POST    | `/api/v1/generate/risksummary`  | Résumé risk 1 page        | 20s     |

---

## Pattern Provider (R3)

Toute la data externe passe par `backend/app/providers/yfinance_adapter.py` :

```
Route → Service → Provider → API externe
```

Interdit : `yf.download()` directement dans services/ ou routes/.

---

## Cache Manager

- Redis (primaire) + dict in-memory (fallback)
- `MAX_MEMORY_CACHE_SIZE = 500` (éviction LRU si dépassé)
- TTL par section configurable
- `CacheManager.get_age()` pour les headers `X-Cache-Age`

---

## Validation

```bash
python scripts/audit_guard.py
# → 0 R3 violations dans le snapshot historique cité ici
```
