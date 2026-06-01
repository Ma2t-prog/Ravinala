# Étape 1 — Honesty Flags & Data Quality Transparency


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

Établir un système de transparence sur la qualité des données retournées par l'API. Chaque réponse doit indiquer clairement si la donnée est **live** (temps réel), **demo_static** (valeur de référence codée en dur), **stale_cache** (cache périmé), ou **error**.

---

## Implémentation

### `backend/app/services/data_fetcher.py`

Chaque méthode de fetch ajoute un flag `data_quality` à son retour :

```python
# ÉTAPE 1 HONESTY FLAG: these are static reference values
result["data_quality"] = "demo_static"
```

| Méthode               | data_quality  | Raison                          |
| --------------------- | ------------- | ------------------------------- |
| `fetch_indices()`     | `live`        | yfinance en temps réel          |
| `fetch_fx_pairs()`    | `live`        | yfinance en temps réel          |
| `fetch_commodities()` | `live`        | yfinance en temps réel          |
| `fetch_bonds()`       | `demo_static` | Valeurs de référence hardcodées |
| `fetch_macro()`       | `demo_static` | Indicateurs macro statiques     |

### `backend/app/middleware/headers.py`

Le middleware HTTP propage le flag `data_quality` via le header `X-Data-Quality` sur chaque réponse :

```
X-Data-Quality: live
X-Data-Quality: demo_static
X-Data-Quality: mixed
```

### `backend/app/schemas/envelope.py`

Le type `DataQuality` est défini comme Literal :

```python
DataQuality = Literal["live", "demo_static", "stale_cache", "error", "mixed"]
```

---

## Fichiers Modifiés

| Fichier                                | Rôle                           |
| -------------------------------------- | ------------------------------ |
| `backend/app/services/data_fetcher.py` | Flags sur chaque fetch         |
| `backend/app/middleware/headers.py`    | Header X-Data-Quality          |
| `backend/app/schemas/envelope.py`      | Définition du type DataQuality |

---

## Validation

```bash
python scripts/audit_guard.py
# → 0 blockers, score 10/10
```

Les endpoints sont honnêtes sur l'origine des données. L'utilisateur sait toujours ce qu'il reçoit.
