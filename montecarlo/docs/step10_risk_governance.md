# Étape 10 — Risk Engine Governance

> [!WARNING]
> **Document status: needs verification**
> Some references in this file may no longer match the current codebase exactly.
> Keep this file as historical context only, not as a proof of current backend state.
> For normative/current state, use:
> - `docs/PRIMARY_SOURCE_BASELINE_INDEX.md`
> - `docs/PRIMARY_SOURCE_DELTA_LEDGER.md`
> - `docs/PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md`

> Date : 2026-03-23
> Statut : **needs verification**

---

## Objectif

Structurer la gouvernance du moteur de risk : conventions quant documentées, spec sheets par métrique, niveaux de gouvernance, et inventaire des incohérences actuelles avec plan de correction.

---

## Endpoints (`/api/v1/risk/`)

| Méthode | Path                 | Description                         |
| ------- | -------------------- | ----------------------------------- |
| POST    | `/compute`           | Calcul rapport risk complet         |
| GET     | `/conventions`       | Conventions quant courantes         |
| GET     | `/metrics`           | Spec sheets de toutes les métriques |
| GET     | `/metrics/{name}`    | Spec sheet d'une métrique           |
| GET     | `/governance-levels` | Niveaux de gouvernance              |
| GET     | `/incoherences`      | Incohérences + plan de correction   |
| GET     | `/snapshots`         | Historique des snapshots risk       |

---

## Conventions Quant (`backend/app/risk/conventions.py`)

```python
CONVENTIONS.risk_free_rate = 0.043        # Current codebase value
CONVENTIONS.trading_days_per_year = 252    # Annualisation standard
```

Source de vérité actuelle — centralisée dans `conventions.py`. Si un autre fichier diverge, le considérer comme historique ou à corriger avant usage normatif.

---

## Métriques Implémentées

### VaR (Value at Risk)

- **Méthode 1 :** Historique (quantile empirique des P&L)
- **Méthode 2 :** Paramétrique (distribution normale)
- Niveau de confiance : 95% et 99%
- Convention : 1 jour, annualisé via √252

### CVaR (Expected Shortfall)

- Moyenne des pertes au-delà du VaR (Conditional VaR)
- Méthode : historique (Expected Shortfall sur queue)

### Métriques Performance

- Sharpe ratio (annualisé, CONVENTIONS.risk_free_rate=0.043)
- Max Drawdown (pic → creux)
- Volatilité (écart-type annualisé)
- Beta (vs benchmark)

---

## Niveaux de Gouvernance

Définis dans `backend/app/risk/conventions.py` :

| Niveau | Nom          | Description                          |
| ------ | ------------ | ------------------------------------ |
| 1      | `indicative` | Métrique exploratoire, usage interne |
| 2      | `research`   | Backtestée, pas encore validée prod  |
| 3      | `production` | Validée, utilisée en production      |
| 4      | `regulatory` | Conforme MiFID II / FRTB             |

---

## Incohérences Documentées

L'endpoint `GET /incoherences` expose :

```json
{
  "incoherences": [
    {
      "id": "INCO-01",
      "metric": "VaR",
      "description": "Paramétrique CVaR non implémenté",
      "what_to_defer": "Parametric CVaR → Étape 14",
      "correction": "Implémenter méthode paramétrique"
    },
    ...
  ],
  "correction_plan": {...}
}
```

---

## Persistance (Règle R5)

Les snapshots risk sont persistés en DB :

```python
class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"
    # asset, period, var_95, var_99, cvar_95, sharpe, max_dd, ...
```

Quand `DATABASE_URL` n'est pas configuré → in-memory seulement (fallback).

---

## Report Complet

`POST /api/v1/risk/compute` retourne :

```json
{
  "asset": "AAPL",
  "period": "5y",
  "var": {
    "method": "historical",
    "confidence_95": -0.023,
    "confidence_99": -0.038
  },
  "cvar": { "confidence_95": -0.031 },
  "performance": {
    "sharpe": 1.24,
    "max_drawdown": -0.31,
    "volatility_annual": 0.28
  },
  "governance_level": 2,
  "data_quality": "live"
}
```
