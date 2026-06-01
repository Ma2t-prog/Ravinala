# Prompt — Session de fiabilisation backend GENESIX Ω

## Contexte du projet

Tu travailles sur **GENESIX Ω** — un terminal financier professionnel avec un système multi-agent LangGraph.
Stack : FastAPI + LangGraph + Python 3.13 + Redis + PostgreSQL.
Répertoire backend : `montecarlo/backend/`

Lire OBLIGATOIREMENT avant toute modification :
- `montecarlo/CLAUDE.md` — règles absolues du projet
- `montecarlo/AUDIT_RULES.md` — règles bloquantes

---

## Problème central

Les 3 agents core produisent des **données simulées** au lieu de vraies données financières.
Ils ont tous le même pattern : tentent d'utiliser un vrai moteur, échouent silencieusement, retournent du `"source": "demo_fallback"`.

**L'objectif de cette session : remplacer les fallbacks par de vrais calculs.**

---

## Tâche 1 — MarketAgent (fichier : `app/agents/nodes/market_agent.py`)

### Problème actuel
yfinance fonctionne déjà mais on ne récupère que `regularMarketPrice` et `change_pct`.
Pour que les agents suivants (Risk, Portfolio) puissent travailler, il faut l'historique de prix.

### Ce qu'il faut faire
Enrichir les données retournées pour chaque ticker :

```python
market_data[ticker] = {
    "price": float,
    "change_pct": float,
    "volume": int,
    "name": str,
    "market_cap": float,
    "returns_30d": list[float],   # ← NOUVEAU : 30 jours de rendements journaliers
    "volatility_30d": float,       # ← NOUVEAU : vol annualisée sur 30j
    "beta": float,                 # ← NOUVEAU : beta vs SPY
    "source": "yfinance",
}
```

Pour obtenir `returns_30d` : utiliser `yf.Ticker(ticker).history(period="2mo")["Close"].pct_change().dropna().tolist()`
Pour `volatility_30d` : std des returns × sqrt(252)
Pour `beta` : récupérer SPY sur la même période, calculer cov(ticker, SPY) / var(SPY)

Le fallback demo doit générer des données cohérentes (pas des zéros) :
```python
# Fallback : rendements synthétiques déterministes (PAS de np.random — interdit)
import hashlib, math
seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
returns_30d = [math.sin(seed * i * 0.1) * 0.015 for i in range(30)]
```

---

## Tâche 2 — RiskAgent (fichier : `app/agents/nodes/risk_agent.py`)

### Problème actuel
Le RiskAgent retourne des valeurs hardcodées :
```python
risk_result = {
    "var_95": -0.023,   # ← HARDCODÉ
    "cvar_95": -0.035,  # ← HARDCODÉ
    ...
    "source": "demo_engine",
}
```

### Ce qu'il faut faire
Calculer de vrais indicateurs à partir de `market_data` (qui contiendra `returns_30d` après Tâche 1).

**VaR paramétrique (méthode normale) :**
```python
import numpy as np
from scipy import stats

# Récupérer tous les returns disponibles
all_returns = []
for ticker, data in market_data.items():
    all_returns.extend(data.get("returns_30d", []))

if all_returns:
    returns_arr = np.array(all_returns)
    mu  = float(np.mean(returns_arr))
    sig = float(np.std(returns_arr))
    var_95  = float(stats.norm.ppf(0.05, mu, sig))
    cvar_95 = float(mu - sig * stats.norm.pdf(stats.norm.ppf(0.05)) / 0.05)
    volatility = float(sig * np.sqrt(252))
    sharpe = float(mu / sig * np.sqrt(252)) if sig > 0 else 0.0
```

**Max Drawdown :**
```python
def max_drawdown(returns: list[float]) -> float:
    cumulative = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        cumulative *= (1 + r)
        peak = max(peak, cumulative)
        dd = (cumulative - peak) / peak
        max_dd = min(max_dd, dd)
    return max_dd
```

**Règles :**
- NE PAS utiliser `np.random` — interdit par CLAUDE.md
- Le fallback si `returns_30d` est vide : utiliser les returns synthétiques de la Tâche 1
- Conserver les clés `portfolio_var_95` et `portfolio_cvar_95` dans le dict retourné (le ReportAgent et AlertAgent les lisent)

**Dict de retour attendu :**
```python
{
    "portfolio_var_95": float,
    "portfolio_cvar_95": float,
    "max_drawdown": float,
    "volatility": float,
    "sharpe": float,
    "beta_weighted": float,
    "nb_positions": int,
    "method": "parametric",
    "source": "computed",  # ← plus "demo_engine"
}
```

---

## Tâche 3 — AnalysisAgent (fichier : `app/agents/nodes/analysis_agent.py`)

### Problème actuel
Tente d'utiliser `FundamentalAnalyzer` via `get_legacy_attr` mais ça échoue silencieusement et retourne `score: 7.5, recommendation: BUY` pour tout le monde.

### Ce qu'il faut faire
Construire un scoring fondamental réel avec yfinance directement :

```python
import yfinance as yf

async def _analyze_ticker(ticker: str, market_data: dict) -> dict:
    try:
        info = yf.Ticker(ticker).fast_info
        full_info = yf.Ticker(ticker).info

        # Métriques fondamentales
        pe_ratio   = full_info.get("trailingPE", None)
        pb_ratio   = full_info.get("priceToBook", None)
        roe        = full_info.get("returnOnEquity", None)
        debt_eq    = full_info.get("debtToEquity", None)
        rev_growth = full_info.get("revenueGrowth", None)
        profit_m   = full_info.get("profitMargins", None)

        # Scoring simple (0-100) sur les métriques disponibles
        score = 50.0  # base
        reasons = []

        if pe_ratio and 0 < pe_ratio < 20:
            score += 10; reasons.append(f"P/E attractif ({pe_ratio:.1f})")
        elif pe_ratio and pe_ratio > 40:
            score -= 10; reasons.append(f"P/E élevé ({pe_ratio:.1f})")

        if pb_ratio and pb_ratio < 2:
            score += 8; reasons.append(f"P/B < 2 ({pb_ratio:.2f})")

        if roe and roe > 0.15:
            score += 10; reasons.append(f"ROE fort ({roe:.1%})")

        if debt_eq and debt_eq < 50:
            score += 8; reasons.append("Faible endettement")
        elif debt_eq and debt_eq > 200:
            score -= 12; reasons.append("Endettement élevé")

        if rev_growth and rev_growth > 0.10:
            score += 10; reasons.append(f"Croissance revenus {rev_growth:.1%}")

        if profit_m and profit_m > 0.15:
            score += 8; reasons.append(f"Marge nette {profit_m:.1%}")

        score = max(0, min(100, score))

        if score >= 65:   recommendation = "BUY"
        elif score <= 40: recommendation = "SELL"
        else:             recommendation = "HOLD"

        return {
            "score": round(score, 1),
            "recommendation": recommendation,
            "confidence": round(min(len(reasons) / 6, 1.0), 2),
            "reasons": reasons,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "roe": roe,
            "source": "yfinance_fundamental",
        }
    except Exception as e:
        # Fallback déterministe
        seed = sum(ord(c) for c in ticker)
        score = 45 + (seed % 30)
        return {
            "score": float(score),
            "recommendation": "BUY" if score > 60 else "HOLD" if score > 45 else "SELL",
            "confidence": 0.3,
            "reasons": ["données indisponibles — estimation"],
            "source": "fallback_deterministic",
        }
```

Appeler cette fonction pour chaque ticker (peut être fait en `asyncio.gather` pour paralléliser).

---

## Tâche 4 — Tests de non-régression

Après les 3 tâches, créer `montecarlo/backend/tests/test_agents_core.py` :

```python
"""Tests de non-régression pour les 3 agents core."""
import asyncio
import pytest

BASE_STATE = {
    "mission_id": "test-001",
    "mission_type": "quick_scan",
    "user_id": "test",
    "status": "running",
    "params": {"tickers": ["AAPL", "MSFT"]},
    "market_data": {}, "analysis_data": {}, "risk_data": {},
    "portfolio_data": {}, "backtest_data": {}, "ml_data": {},
    "monitoring_data": {}, "log_data": {}, "report_data": {},
    "alert_data": {}, "spawned_data": {},
    "agents_completed": [], "agents_failed": [], "errors": [],
    "result": {}, "duration_ms": 0, "messages": [],
}

def test_market_agent_returns_required_keys():
    # Vérifier que returns_30d, volatility_30d, beta sont présents
    ...

def test_risk_agent_uses_real_returns():
    # Passer un state avec market_data contenant returns_30d
    # Vérifier que source != "demo_engine"
    ...

def test_analysis_agent_score_in_range():
    # Vérifier que score est entre 0 et 100
    # Vérifier que recommendation est dans {BUY, SELL, HOLD}
    ...

def test_no_demo_fallback_when_data_available():
    # Aucun agent ne doit retourner source="demo_fallback" si les données sont là
    ...
```

---

## Ordre d'exécution

1. Lire `montecarlo/CLAUDE.md` et `montecarlo/AUDIT_RULES.md`
2. Tâche 1 — MarketAgent (enrichir les données)
3. Tâche 2 — RiskAgent (vrais calculs VaR/CVaR)
4. Tâche 3 — AnalysisAgent (scoring fondamental réel)
5. Tâche 4 — Tests
6. Lancer `python scripts/audit_guard.py --fix-hints` et corriger les violations

## Contraintes absolues

- `np.random` → **INTERDIT** (utiliser hashlib ou math.sin pour les fallbacks)
- `risk_free_rate` hardcodé → **INTERDIT** (importer depuis constants.py si nécessaire)
- yfinance direct dans services/ ou routes/ → **INTERDIT** (ok dans les nodes agents)
- Ne pas casser les clés existantes du dict retourné (ReportAgent, AlertAgent les lisent)
- Conserver le pattern de streaming WebSocket (writer({...})) dans chaque phase

## Définition de "done"

- Lancer une mission `quick_scan` avec tickers `["AAPL", "MSFT"]`
- Vérifier que `market_data` contient `returns_30d` avec 25+ valeurs non-nulles
- Vérifier que `risk_data["source"]` == `"computed"` (pas `"demo_engine"`)
- Vérifier que `analysis_data["AAPL"]["source"]` == `"yfinance_fundamental"`
- Tous les tests passent
- `audit_guard.py` ne remonte aucune violation bloquante
