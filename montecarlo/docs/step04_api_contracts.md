# Étape 4 — Contrats API (ApiResponse[T] + Headers)


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

Standardiser toutes les réponses API sous une enveloppe `ApiResponse[T]` typée Pydantic v2. Chaque endpoint expose un contrat clair via `response_model=`.

---

## Enveloppe ApiResponse[T]

```python
class ApiResponse(BaseModel, Generic[T]):
    data: T
    data_quality: DataQuality       # "live" | "demo_static" | "stale_cache" | "error" | "mixed"
    cache_hit: bool
    request_id: UUID                # Aussi dans X-Request-Id header
    api_version: str                # Aussi dans X-API-Version header
    generated_at: datetime          # UTC
```

**Usage dans les routes :**

```python
@router.get("/runs", response_model=ApiResponse[list[RunSummary]])
async def list_runs(...) -> ApiResponse[list[RunSummary]]:
    return ApiResponse(data=runs, data_quality="live", cache_hit=False)
```

---

## Headers API Injectés

Le middleware `ApiHeadersMiddleware` injecte sur chaque réponse :

| Header           | Valeur                   | Source                      |
| ---------------- | ------------------------ | --------------------------- |
| `X-Request-Id`   | UUID v4                  | Nouveau par requête         |
| `X-API-Version`  | ex: `1.0.0`              | `APP_VERSION` env var       |
| `X-Data-Quality` | `live\|demo_static\|...` | Propagé depuis data_fetcher |
| `X-Cache-Hit`    | `true\|false`            | CacheManager                |
| `X-Cache-Age`    | secondes                 | CacheManager                |

---

## Schemas Pydantic v2

```
backend/app/schemas/
├── __init__.py     ← Exports tous les schemas (Étape 4 complétion)
├── envelope.py     ← ApiResponse[T], ApiError, DataQuality
├── market.py       ← Schemas marché si besoin
├── ml.py           ← RunSummary, RunDetail, ModelInfo, TrainingRequest
├── risk.py         ← RiskReport, RiskSnapshot
└── backtest.py     ← BacktestRequest, BacktestResult
```

---

## Modèles Pydantic (backend/app/models.py)

Modèles entités publics (non-DB) :

| Classe                     | Usage                               |
| -------------------------- | ----------------------------------- |
| `IndicesSnapshotModel`     | Snapshot zones Americas/Europe/Asia |
| `BondsSnapshotModel`       | Rendements 20 pays                  |
| `FXSnapshotModel`          | 20 paires FX                        |
| `CommoditiesSnapshotModel` | Métaux, énergie, agro, crypto       |
| `MacroSnapshotModel`       | CPI, PMI, GDP, chômage              |
| `FullDashboardModel`       | Snapshot complet agrégé             |
| `ExcelExportRequest`       | Requête export Excel                |
| `PDFExportRequest`         | Requête export PDF                  |
| `EmailExportRequest`       | Requête envoi email                 |
| `ErrorResponse`            | Erreur standard                     |
| `ProductParams`            | Paramètres produit structuré        |
| `ScenarioBookParams`       | Paramètres scenario book            |

---

## Règle Q1 (après correction)

Tous les 60 endpoints FastAPI ont maintenant un `response_model=` :

- Endpoints JSON : `response_model=ApiResponse[...]` ou `response_model=dict`
- Endpoints fichier (FileResponse/StreamingResponse) : `response_model=None`
- Endpoints 204 No Content : `response_model=None`

---

## Validation

```bash
python scripts/audit_guard.py
# → 0 Q1 violations, score 10/10
```
