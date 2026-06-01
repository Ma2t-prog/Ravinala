# Étape 9 — Backtesting Traçable


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

Implémenter un moteur de backtesting avec validation walk-forward, comparaison obligatoire aux baselines, kill switches, et persistance DB des résultats.

---

## Endpoints (`/api/v1/backtest/`)

| Méthode | Path             | Description                                |
| ------- | ---------------- | ------------------------------------------ |
| POST    | `/run`           | Lance un backtest + baselines obligatoires |
| GET     | `/runs`          | Liste des runs passés                      |
| GET     | `/runs/{run_id}` | Détail d'un run                            |
| GET     | `/strategies`    | Stratégies disponibles                     |
| GET     | `/limitations`   | Matrice de limitations par défaut          |

---

## Stratégies Disponibles

Définies dans `backend/app/backtest/engine.py` (`STRATEGY_MAP`) :

- `momentum` — Mean reversion sur retours glissants
- `mean_reversion` — Retour à la moyenne
- `equal_weight` — Poids équipondérés (baseline)
- `buy_hold` — Buy & hold simple (baseline)

---

## Baselines Obligatoires (Règle Q4)

Chaque `POST /run` lance automatiquement :

1. **La stratégie demandée**
2. **Buy & Hold** (benchmark naïf)
3. **Equal Weight** (benchmark équipondéré)

```python
result = await loop.run_in_executor(_executor, run_with_baselines, request)
```

---

## Paramètres Backtest

```python
class BacktestRunRequest(BaseModel):
    assets: list[str]           # Tickers (1-50)
    strategy: str = "momentum"  # Stratégie
    benchmark: str = "SPY"      # Benchmark de référence
    start_date: str             # YYYY-MM-DD
    end_date: str               # YYYY-MM-DD
    initial_capital: float = 100_000.0
    commission_bps: float = 10.0    # Points de base
    slippage_bps: float = 5.0       # Points de base
```

---

## Modèle DB (BacktestRun — 27 colonnes)

Persiste chaque run en DB quand `DATABASE_URL` est configuré :

- Métriques aggregées (Sharpe, Max DD, CAGR...)
- Métriques benchmark (pour comparaison)
- Matrice de limitations (survivorship bias, etc.)
- Lien vers ML run si entraîné avant

---

## Kill Switches

Implémentés dans le moteur :

- `max_drawdown_threshold` — Stop si DD > seuil
- `stop_loss` — Stop loss par position
- `take_profit` — Take profit par position

---

## Matrice de Limitations

```python
DEFAULT_LIMITATIONS = {
    "survivorship_bias": "Partiel — données yfinance incluent les survivants",
    "transaction_costs": "Commission + slippage modélisés (configurable)",
    "look_ahead_bias": "validate_no_lookahead() exécuté avant chaque run",
    "regime_changes": "Non modélisé dans cette version",
}
```

---

## DEPLOYMENT_POLICY

Politique de déploiement automatique basée sur les métriques :

```python
DEPLOYMENT_POLICY = {
    "min_sharpe": 0.5,
    "min_directional_accuracy": 0.52,
    "max_drawdown": -0.25,
    "min_backtest_months": 12,
}
```
