# Étape 14 — Modèles Risk Avancés (COMPLET)


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

Cette étape implémente les modèles de risk avancés qui ont été explicitement reportés depuis l'Étape 10. Ces modèles nécessitent plus de données historiques, une calibration plus complexe, et une validation quant rigoureuse.

---

## Métriques Reportées Depuis Étape 10

Toutes documentées dans `backend/app/risk/conventions.py` via `what_to_defer` :

### 1. VaR Cornish-Fisher

```python
"what_to_defer": "Cornish-Fisher and Monte Carlo VaR deferred to Étape 14"
```

- Ajustement d'asymétrie et d'aplatissement (skewness, kurtosis)
- Plus précis pour les distributions fat-tail

### 2. VaR Monte Carlo

- Simulation de scénarios (10,000+ paths)
- Dépendances copule pour le risque de portefeuille

### 3. VaR Paramétrique Avancée

```python
"what_to_defer": "Student-t and custom distributions → Étape 14"
```

- Distribution Student-t (mieux pour les queues épaisses)
- Distributions personnalisées (stable, skew-normal)

### 4. CVaR Paramétrique

- Extension de la méthode historique vers paramétrique

### 5. Modèles de Volatilité EWMA/GARCH

```python
"what_to_defer": "EWMA / GARCH volatility models → Étape 14"
```

- EWMA (Exponentially Weighted Moving Average)
- GARCH(1,1) pour la volatilité conditionnelle
- E-GARCH pour l'effet de levier

### 6. Métriques Performance Avancées

```python
"what_to_defer": "Rolling Sharpe, probabilistic Sharpe ratio → Étape 14"
"what_to_defer": "Rolling / conditional Sortino → Étape 14"
"what_to_defer": "Modified Calmar (rolling 3Y window) → Étape 14"
"what_to_defer": "Drawdown duration, conditional drawdown analysis → Étape 14"
```

### 7. Stress Tests Avancés

```python
"what_to_defer": "Multi-factor stress, reverse stress, conditional stress → Étape 14"
```

- Reverse stress testing (quelles conditions cassent le portfolio?)
- Conditional stress (stress conditionnel sur une variable macro)

---

## Prérequis Techniques

- Minimum 5 ans de données historiques par asset
- Implémentation `scipy.stats` pour distributions avancées
- `arch` library pour GARCH (pip install arch)
- Calibration et backtesting des modèles avancés

---

## Impact Attendu

- Précision VaR améliorée de ~30% pour les assets volatils
- Meilleures estimations de tail risk (CVaR, Cornish-Fisher)
- Alertes de régime volatilité via GARCH

---

## Fichiers à Créer

```
backend/app/risk/
├── models/
│   ├── var_cornish_fisher.py    ← VaR CF + Monte Carlo
│   ├── volatility_garch.py      ← EWMA + GARCH(1,1)
│   └── advanced_metrics.py     ← Rolling Sharpe, Sortino, Calmar
└── stress_testing/
    ├── reverse_stress.py        ← Reverse stress testing
    └── conditional_stress.py   ← Conditional scenarios
```
