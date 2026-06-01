# MEGA-PROMPT — LANGGRAPH AGENT MONITOR + 2D POKÉMON-STYLE DASHBOARD

> Copie-colle ce document entier dans Claude Code VS Code (ou tout autre agent IA) pour implémenter le système complet.
> Ce prompt est **100 % autonome** — il contient toute l'architecture, les specs, le design, les schémas de données et le plan d'exécution.

---

## TABLE DES MATIÈRES

1. [Contexte du projet](#1-contexte-du-projet)
2. [Architecture globale](#2-architecture-globale)
3. [Agents — Définitions complètes](#3-agents--définitions-complètes)
4. [LangGraph — Graph definition](#4-langgraph--graph-definition)
5. [WebSocket Bridge](#5-websocket-bridge)
6. [2D Pokémon-Style Visualization](#6-2d-pokémon-style-visualization)
7. [Frontend React Integration](#7-frontend-react-integration)
8. [Backend FastAPI Integration](#8-backend-fastapi-integration)
9. [Plan d'exécution pas-à-pas](#9-plan-dexécution-pas-à-pas)
10. [Tests & Validation](#10-tests--validation)

---

## 1. CONTEXTE DU PROJET

### Stack existante

| Couche | Tech | Détails |
|--------|------|---------|
| Frontend | React 19 + TypeScript 5.9 + Vite | `ravinala-web/` — React Router 7, TanStack Query 5, Tailwind 4, Recharts, Plotly |
| Backend | FastAPI (Python 3.13) | `montecarlo/backend/` — 58 endpoints, 14 route files |
| Calcul | Python modules in `montecarlo/src/` | Modules: `analysis/`, `genesix/`, `risk/`, `backtest/`, etc. |
| Design | Dark premium theme | BG #0A0E1A, Cyan #00D9FF, Gold #D4AF37, JetBrains Mono + Inter |

### Routes Backend existantes (14 fichiers)

```
montecarlo/backend/app/routes/
├── analysis.py    → POST /api/v1/analysis/company (FundamentalAnalyzer)
├── auth.py        → POST /api/v1/auth/register, login, logout | GET /me
├── backtest.py    → POST /api/v1/backtest/run | GET /runs, /strategies, /limitations
├── market.py      → GET /api/v1/snapshot, /indices, /bonds, /fx-pairs, /commodities, /macro
├── ml.py          → POST /api/v1/ml/train, /predict | GET /runs, /models
├── portfolio.py   → POST /api/v1/portfolio/optimize (PortfolioOptimizer)
├── risk.py        → POST /api/v1/risk/compute | GET /conventions, /metrics, ...
├── universe.py    → GET /api/v1/universe/...
└── ... (6 autres: users, monitoring, tradebook, compliance, admin, health)
```

### Frontend existant (ravinala-web/src/)

```
src/
├── api/          → 11 fichiers (client.ts, auth.ts, risk.ts, portfolio.ts, ml.ts, etc.)
├── hooks/        → 10 fichiers (useAuth.tsx, useRisk.ts, usePortfolio.ts, useML.ts, etc.)
├── pages/        → 35 pages routées dans App.tsx
├── components/   → Layout.tsx, Sidebar.tsx, ProtectedRoute.tsx, etc.
└── App.tsx       → 34 routes (32 app + 2 auth)
```

### Ce qu'on construit

Un **système d'orchestration d'agents IA** avec :
1. **LangGraph** (Python) — graphe de coordination multi-agents avec streaming temps réel
2. **WebSocket bridge** — FastAPI WS endpoint qui relaie les événements LangGraph vers le frontend
3. **Dashboard 2D Pokémon Silver** — Canvas React (PixiJS) avec sprites animés pour chaque agent, style rétro Game Boy Color

---

## 2. ARCHITECTURE GLOBALE

```
┌─────────────────────────────────────────────────────────────────┐
│                     REACT FRONTEND (ravinala-web)               │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              AgentMonitorPage.tsx (/agents/monitor)         │ │
│  │  ┌──────────────────────┐  ┌────────────────────────────┐ │ │
│  │  │   PixiJS Canvas      │  │    Control Panel            │ │ │
│  │  │   (Pokemon Silver    │  │    - Start/Stop mission     │ │ │
│  │  │    2D map with       │  │    - Agent status cards     │ │ │
│  │  │    agent sprites)    │  │    - Event log (scrollable) │ │ │
│  │  │                      │  │    - Progress bars          │ │ │
│  │  └──────────────────────┘  └────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│               │ useAgentMonitor() hook                          │
│               │ WebSocket connection                            │
│               ▼                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     FASTAPI BACKEND                             │
│                                                                 │
│  ┌─────────────────┐     ┌──────────────────────────────────┐  │
│  │  WS /api/v1/    │     │   REST /api/v1/agents/...        │  │
│  │  agents/stream   │◄───│   POST /missions/start           │  │
│  │  (broadcast)     │    │   GET  /missions/{id}/status     │  │
│  └────────┬────────┘     │   GET  /agents/list              │  │
│           │              │   POST /missions/{id}/cancel     │  │
│           │              └──────────────────────────────────┘  │
│           ▼                                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   LANGGRAPH ENGINE                           ││
│  │                                                              ││
│  │  StateGraph("AgentOrchestrator")                             ││
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐              ││
│  │  │Dispatcher│───►│ Market   │───►│ Analysis │──► ...       ││
│  │  │  (entry) │    │  Agent   │    │  Agent   │              ││
│  │  └──────────┘    └──────────┘    └──────────┘              ││
│  │       │               │               │                     ││
│  │       │          get_stream_writer() emits custom events    ││
│  │       │               │               │                     ││
│  │       ▼               ▼               ▼                     ││
│  │  ┌──────────────────────────────────────────┐               ││
│  │  │        Event Collector (async queue)      │               ││
│  │  │   → forwards to WebSocket broadcast       │               ││
│  │  └──────────────────────────────────────────┘               ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. AGENTS — DÉFINITIONS COMPLÈTES

### 3.1 Vue d'ensemble

| # | Agent | Rôle | Module Python wrappé | Sprite couleur |
|---|-------|------|---------------------|----------------|
| 0 | **OrchestratorAgent** | Dispatcher / superviseur | — | #D4AF37 Gold |
| 1 | **MarketAgent** | Données marchés temps réel | `app.services.data_fetcher` | #00D4FF Cyan |
| 2 | **AnalysisAgent** | Analyse fondamentale | `src.analysis.fundamentals` | #3B82F6 Blue |
| 3 | **RiskAgent** | Calcul de risque | `app.risk.engine` | #EF4444 Red |
| 4 | **PortfolioAgent** | Optimisation portfolio | `src.genesix.portfolio_optimizer` | #10B981 Green |
| 5 | **BacktestAgent** | Backtesting stratégies | `app.backtest.engine` | #F59E0B Amber |
| 6 | **MLAgent** | Machine Learning / prédictions | `app.providers.yfinance_adapter` + ML | #8B5CF6 Purple |
| 7 | **MonitoringAgent** | Health check / observabilité | `app.monitoring` | #6366F1 Indigo |
| 8 | **ErrorHandlerAgent** | Gestion d'erreurs globale | — (transversal) | #F43F5E Rose |
| 9 | **LoggerAgent** | Journalisation des événements | — (transversal) | #94A3B8 Slate |

### 3.2 Définition détaillée de chaque agent

#### Agent 0 : OrchestratorAgent (Supervisor)

```python
# Rôle : Point d'entrée du graphe. Reçoit une "mission" de l'utilisateur,
#         décompose en sous-tâches, les dispatche aux agents spécialisés,
#         agrège les résultats, gère les retry/fallback.
#
# Input :  { mission_type: str, params: dict, user_id: str }
# Output : { results: dict, agents_used: list, duration_ms: int, status: str }
#
# Timeout : 300s (5 min max par mission)
# Retry :  0 (l'orchestrateur ne retry pas lui-même, il retry les sous-agents)
#
# Événements custom émis via get_stream_writer() :
#   - "mission_start"     → { mission_id, mission_type, planned_agents }
#   - "agent_dispatched"  → { agent_name, task_id, task_type }
#   - "mission_complete"  → { mission_id, results_summary, duration_ms }
#   - "mission_failed"    → { mission_id, error, failed_agent }

MISSION_TYPES = {
    "full_analysis": ["MarketAgent", "AnalysisAgent", "RiskAgent", "PortfolioAgent"],
    "quick_scan": ["MarketAgent", "AnalysisAgent"],
    "risk_check": ["MarketAgent", "RiskAgent"],
    "backtest_run": ["MarketAgent", "BacktestAgent"],
    "ml_predict": ["MarketAgent", "MLAgent"],
    "portfolio_optimize": ["MarketAgent", "AnalysisAgent", "RiskAgent", "PortfolioAgent"],
    "health_check": ["MonitoringAgent"],
}
```

#### Agent 1 : MarketAgent

```python
# Rôle : Récupère les données de marché en temps réel (prix, indices, FX, commodities).
#         Premier agent appelé dans toute mission — fournit les données aux autres.
#
# Input :  { tickers: list[str], data_types: list[str], period: str }
#           data_types: ["price", "volume", "fundamentals", "options_chain"]
#           period: "1d", "1w", "1m", "3m", "1y", "5y"
#
# Output : { market_data: dict, timestamp: str, source: str, cache_hit: bool }
#
# Module wrappé : montecarlo/backend/app/services/data_fetcher.py
# Endpoint utilisé en interne : GET /api/v1/snapshot, /indices, etc.
#
# Timeout : 30s
# Retry :  2 (avec backoff exponentiel 1s, 3s)
#
# Événements custom :
#   - "market_fetch_start"   → { tickers, data_types }
#   - "market_data_partial"  → { ticker, price, change_pct }  (émis par ticker)
#   - "market_fetch_done"    → { nb_tickers, cache_hits, duration_ms }
#   - "market_fetch_error"   → { ticker, error }
```

#### Agent 2 : AnalysisAgent

```python
# Rôle : Analyse fondamentale d'une entreprise (financials, ratios, DCF, comparables).
#
# Input :  { ticker: str, analysis_type: str, market_data: dict }
#           analysis_type: "full", "dcf", "comparables", "ratios"
#
# Output : { analysis: dict, score: float, recommendation: str, confidence: float }
#
# Module wrappé : montecarlo/src/analysis/fundamentals.py → FundamentalAnalyzer
# Endpoint : POST /api/v1/analysis/company
#
# Timeout : 60s
# Retry :  1
#
# Événements custom :
#   - "analysis_start"       → { ticker, analysis_type }
#   - "analysis_phase"       → { phase: "financials"|"ratios"|"dcf"|"scoring", progress_pct }
#   - "analysis_complete"    → { ticker, score, recommendation }
#   - "analysis_error"       → { ticker, error, phase }
```

#### Agent 3 : RiskAgent

```python
# Rôle : Calcul des métriques de risque (VaR, CVaR, stress tests, Greeks, etc.)
#
# Input :  { portfolio: list[dict], risk_params: dict, market_data: dict }
#           risk_params: { confidence_level, horizon_days, method }
#           method: "historical", "parametric", "monte_carlo"
#
# Output : { var: float, cvar: float, sharpe: float, max_drawdown: float,
#            stress_results: dict, greeks: dict }
#
# Module wrappé : montecarlo/backend/app/risk/engine.py → compute_full_risk_report
# Endpoint : POST /api/v1/risk/compute
#
# Timeout : 90s
# Retry :  1
#
# Événements custom :
#   - "risk_start"           → { method, nb_positions, confidence }
#   - "risk_phase"           → { phase: "var"|"cvar"|"stress"|"greeks", progress_pct }
#   - "risk_complete"        → { var, cvar, sharpe, duration_ms }
#   - "risk_error"           → { error, phase }
```

#### Agent 4 : PortfolioAgent

```python
# Rôle : Optimisation de portefeuille (Markowitz, Black-Litterman, Risk Parity, etc.)
#
# Input :  { tickers: list[str], method: str, constraints: dict,
#            market_data: dict, risk_data: dict }
#           method: "markowitz", "black_litterman", "risk_parity", "min_variance", "max_sharpe"
#           constraints: { max_weight, min_weight, sector_limits, target_return }
#
# Output : { weights: dict, expected_return: float, expected_risk: float,
#            sharpe: float, efficient_frontier: list }
#
# Module wrappé : montecarlo/src/genesix/portfolio_optimizer.py → PortfolioOptimizer
# Endpoint : POST /api/v1/portfolio/optimize
#
# Timeout : 120s
# Retry :  1
#
# Événements custom :
#   - "portfolio_start"      → { method, nb_assets, constraints }
#   - "portfolio_phase"      → { phase: "covariance"|"optimization"|"frontier", progress_pct }
#   - "portfolio_complete"   → { sharpe, expected_return, duration_ms }
#   - "portfolio_error"      → { error, phase }
```

#### Agent 5 : BacktestAgent

```python
# Rôle : Backtesting de stratégies de trading sur données historiques.
#
# Input :  { strategy: str, tickers: list[str], start_date: str, end_date: str,
#            params: dict, market_data: dict }
#           strategy: "momentum", "mean_reversion", "pairs", "breakout", "custom"
#
# Output : { total_return: float, sharpe: float, max_drawdown: float,
#            trades: list, equity_curve: list, benchmark_comparison: dict }
#
# Module wrappé : montecarlo/backend/app/backtest/engine.py → run_with_baselines
# Endpoint : POST /api/v1/backtest/run
#
# Timeout : 180s
# Retry :  0
#
# Événements custom :
#   - "backtest_start"       → { strategy, period, nb_tickers }
#   - "backtest_year"        → { year, return_ytd, nb_trades }  (émis par année simulée)
#   - "backtest_complete"    → { total_return, sharpe, nb_trades, duration_ms }
#   - "backtest_error"       → { error }
```

#### Agent 6 : MLAgent

```python
# Rôle : Entraînement / prédiction via modèles ML (régression, classification, LSTM, etc.)
#
# Input :  { task: "train"|"predict", model_type: str, features: dict,
#            target: str, market_data: dict }
#           model_type: "random_forest", "xgboost", "lstm", "linear", "ensemble"
#
# Output : { predictions: list, accuracy: float, feature_importance: dict,
#            model_id: str, training_metrics: dict }
#
# Module wrappé : montecarlo/backend/app/providers/yfinance_adapter.py + ML models
# Endpoint : POST /api/v1/ml/train, /predict
#
# Timeout : 300s
# Retry :  0
#
# Événements custom :
#   - "ml_start"             → { task, model_type }
#   - "ml_epoch"             → { epoch, loss, val_loss, progress_pct }  (si train)
#   - "ml_complete"          → { accuracy, model_id, duration_ms }
#   - "ml_error"             → { error }
```

#### Agent 7 : MonitoringAgent

```python
# Rôle : Health check des services, monitoring de performance, alertes.
#
# Input :  { check_type: "health"|"performance"|"alerts" }
#
# Output : { services: dict[str, bool], latencies: dict[str, float],
#            alerts: list, uptime: float }
#
# Module wrappé : montecarlo/backend/app/monitoring/
# Endpoint : GET /api/v1/monitoring/health, /metrics
#
# Timeout : 15s
# Retry :  3
#
# Événements custom :
#   - "monitoring_start"     → { check_type }
#   - "service_checked"      → { service, healthy, latency_ms }
#   - "monitoring_complete"  → { all_healthy, nb_alerts }
#   - "monitoring_alert"     → { service, severity, message }
```

#### Agent 8 : ErrorHandlerAgent (transversal)

```python
# Rôle : Agent transversal. Intercepte les erreurs des autres agents,
#         décide retry/fallback/abort, notifie l'orchestrateur.
#
# Input :  { error: Exception, agent_name: str, task_id: str, attempt: int }
#
# Output : { action: "retry"|"fallback"|"abort", reason: str }
#
# Timeout : 5s
# Retry :  0
#
# Événements custom :
#   - "error_caught"         → { agent_name, error_type, message }
#   - "error_action"         → { agent_name, action, reason }
#   - "error_escalated"      → { agent_name, error, sent_to: "orchestrator" }
```

#### Agent 9 : LoggerAgent (transversal)

```python
# Rôle : Collecte et persiste tous les événements de tous les agents.
#         Écrit dans un fichier JSON + en DB pour l'historique des missions.
#
# Input :  { event: dict }  (reçoit tous les événements du graphe)
#
# Output : { logged: bool, log_id: str }
#
# Timeout : 2s
# Retry :  0
#
# Événements custom :
#   - "log_written"          → { log_id, event_type, agent_name }
```

---

## 4. LANGGRAPH — GRAPH DEFINITION

### 4.1 Installation

```bash
pip install langgraph langchain-core langchain-openai
```

### 4.2 State Schema

```python
# Fichier : montecarlo/backend/app/agents/state.py

from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages

class MissionState(TypedDict):
    """État partagé entre tous les agents du graphe."""
    
    # Mission metadata
    mission_id: str
    mission_type: str          # "full_analysis", "quick_scan", etc.
    user_id: str
    status: str                # "pending", "running", "completed", "failed", "cancelled"
    
    # Input params
    params: dict[str, Any]     # Paramètres de la mission (tickers, dates, etc.)
    
    # Data flowing between agents
    market_data: dict[str, Any]       # Output de MarketAgent
    analysis_data: dict[str, Any]     # Output de AnalysisAgent
    risk_data: dict[str, Any]         # Output de RiskAgent
    portfolio_data: dict[str, Any]    # Output de PortfolioAgent
    backtest_data: dict[str, Any]     # Output de BacktestAgent
    ml_data: dict[str, Any]           # Output de MLAgent
    monitoring_data: dict[str, Any]   # Output de MonitoringAgent
    
    # Tracking
    agents_completed: list[str]       # Agents qui ont terminé
    agents_failed: list[str]          # Agents en erreur
    errors: list[dict[str, Any]]      # Log des erreurs
    
    # Final result
    result: dict[str, Any]            # Résultat agrégé final
    duration_ms: int                  # Durée totale
    
    # Messages (LangGraph built-in pour chat history si besoin)
    messages: Annotated[list, add_messages]
```

### 4.3 Agent Node Implementation Pattern

```python
# Fichier : montecarlo/backend/app/agents/nodes/market_agent.py

import asyncio
import time
from langgraph.config import get_stream_writer
from app.agents.state import MissionState

async def market_agent_node(state: MissionState) -> dict:
    """
    Node LangGraph pour le MarketAgent.
    Utilise get_stream_writer() pour émettre des événements custom en streaming.
    """
    writer = get_stream_writer()
    start_time = time.time()
    
    tickers = state["params"].get("tickers", [])
    data_types = state["params"].get("data_types", ["price"])
    
    # Émettre événement de démarrage
    writer({
        "agent": "MarketAgent",
        "event": "market_fetch_start",
        "data": {"tickers": tickers, "data_types": data_types},
        "status": "running",
        "progress": 0.0,
        "timestamp": time.time()
    })
    
    market_data = {}
    
    for i, ticker in enumerate(tickers):
        try:
            # === APPEL AU MODULE EXISTANT ===
            # Ici on wrap le service existant de data_fetcher
            from app.services.data_fetcher import fetch_ticker_data
            data = await fetch_ticker_data(ticker, data_types)
            market_data[ticker] = data
            
            # Émettre progrès par ticker
            writer({
                "agent": "MarketAgent",
                "event": "market_data_partial",
                "data": {
                    "ticker": ticker,
                    "price": data.get("price"),
                    "change_pct": data.get("change_pct")
                },
                "status": "running",
                "progress": (i + 1) / len(tickers),
                "timestamp": time.time()
            })
            
        except Exception as e:
            writer({
                "agent": "MarketAgent",
                "event": "market_fetch_error",
                "data": {"ticker": ticker, "error": str(e)},
                "status": "running",
                "progress": (i + 1) / len(tickers),
                "timestamp": time.time()
            })
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Émettre événement de fin
    writer({
        "agent": "MarketAgent",
        "event": "market_fetch_done",
        "data": {
            "nb_tickers": len(tickers),
            "cache_hits": 0,
            "duration_ms": duration_ms
        },
        "status": "completed",
        "progress": 1.0,
        "timestamp": time.time()
    })
    
    return {
        "market_data": market_data,
        "agents_completed": ["MarketAgent"]
    }
```

### 4.4 Graph Construction

```python
# Fichier : montecarlo/backend/app/agents/graph.py

from langgraph.graph import StateGraph, START, END
from app.agents.state import MissionState
from app.agents.nodes.orchestrator import orchestrator_node, route_after_dispatch
from app.agents.nodes.market_agent import market_agent_node
from app.agents.nodes.analysis_agent import analysis_agent_node
from app.agents.nodes.risk_agent import risk_agent_node
from app.agents.nodes.portfolio_agent import portfolio_agent_node
from app.agents.nodes.backtest_agent import backtest_agent_node
from app.agents.nodes.ml_agent import ml_agent_node
from app.agents.nodes.monitoring_agent import monitoring_agent_node
from app.agents.nodes.error_handler import error_handler_node
from app.agents.nodes.aggregator import aggregator_node

MISSION_FLOWS = {
    "full_analysis":      ["market", "analysis", "risk", "portfolio"],
    "quick_scan":         ["market", "analysis"],
    "risk_check":         ["market", "risk"],
    "backtest_run":       ["market", "backtest"],
    "ml_predict":         ["market", "ml"],
    "portfolio_optimize": ["market", "analysis", "risk", "portfolio"],
    "health_check":       ["monitoring"],
}

def build_agent_graph() -> StateGraph:
    """Construit le graphe LangGraph complet."""
    
    graph = StateGraph(MissionState)
    
    # ── Ajouter tous les nodes ──
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("market", market_agent_node)
    graph.add_node("analysis", analysis_agent_node)
    graph.add_node("risk", risk_agent_node)
    graph.add_node("portfolio", portfolio_agent_node)
    graph.add_node("backtest", backtest_agent_node)
    graph.add_node("ml", ml_agent_node)
    graph.add_node("monitoring", monitoring_agent_node)
    graph.add_node("error_handler", error_handler_node)
    graph.add_node("aggregator", aggregator_node)
    
    # ── Entry point ──
    graph.add_edge(START, "orchestrator")
    
    # ── Orchestrator dispatche vers le premier agent de la mission ──
    graph.add_conditional_edges(
        "orchestrator",
        route_after_dispatch,
        {
            "market": "market",
            "analysis": "analysis",
            "risk": "risk",
            "portfolio": "portfolio",
            "backtest": "backtest",
            "ml": "ml",
            "monitoring": "monitoring",
            "done": "aggregator",
        }
    )
    
    # ── Chaînes séquentielles (chaque agent va au suivant dans le flow) ──
    # Ceci est géré dynamiquement par route_after_agent()
    
    for agent_name in ["market", "analysis", "risk", "portfolio", "backtest", "ml", "monitoring"]:
        graph.add_conditional_edges(
            agent_name,
            route_after_agent,
            {
                "market": "market",
                "analysis": "analysis",
                "risk": "risk",
                "portfolio": "portfolio",
                "backtest": "backtest",
                "ml": "ml",
                "monitoring": "monitoring",
                "aggregator": "aggregator",
                "error_handler": "error_handler",
            }
        )
    
    # ── Error handler retourne à l'orchestrateur ──
    graph.add_edge("error_handler", "orchestrator")
    
    # ── Aggregator → END ──
    graph.add_edge("aggregator", END)
    
    return graph.compile()


def route_after_agent(state: MissionState) -> str:
    """
    Détermine le prochain agent dans le flow de la mission.
    Si un agent a échoué → error_handler.
    Si tous les agents du flow sont complétés → aggregator.
    Sinon → prochain agent dans la séquence.
    """
    mission_type = state["mission_type"]
    flow = MISSION_FLOWS.get(mission_type, [])
    completed = set(state.get("agents_completed", []))
    failed = state.get("agents_failed", [])
    
    # Si le dernier agent a échoué, aller vers error_handler
    if failed and failed[-1] not in completed:
        return "error_handler"
    
    # Trouver le prochain agent non complété
    for agent_name in flow:
        agent_class = agent_name.capitalize() + "Agent"
        if agent_class not in completed:
            return agent_name
    
    # Tous complétés → agréger
    return "aggregator"
```

### 4.5 Orchestrator Node

```python
# Fichier : montecarlo/backend/app/agents/nodes/orchestrator.py

import uuid
import time
from langgraph.config import get_stream_writer
from app.agents.state import MissionState
from app.agents.graph import MISSION_FLOWS

async def orchestrator_node(state: MissionState) -> dict:
    """
    Point d'entrée. Planifie les agents à exécuter pour cette mission.
    """
    writer = get_stream_writer()
    
    mission_id = state.get("mission_id") or str(uuid.uuid4())
    mission_type = state["mission_type"]
    planned_agents = MISSION_FLOWS.get(mission_type, [])
    
    writer({
        "agent": "OrchestratorAgent",
        "event": "mission_start",
        "data": {
            "mission_id": mission_id,
            "mission_type": mission_type,
            "planned_agents": [a.capitalize() + "Agent" for a in planned_agents]
        },
        "status": "running",
        "progress": 0.0,
        "timestamp": time.time()
    })
    
    return {
        "mission_id": mission_id,
        "status": "running",
        "agents_completed": state.get("agents_completed", []),
        "agents_failed": state.get("agents_failed", []),
        "errors": state.get("errors", []),
    }


def route_after_dispatch(state: MissionState) -> str:
    """
    Après l'orchestrateur, route vers le premier agent non complété du flow.
    """
    mission_type = state["mission_type"]
    flow = MISSION_FLOWS.get(mission_type, [])
    completed = set(state.get("agents_completed", []))
    
    for agent_name in flow:
        agent_class = agent_name.capitalize() + "Agent"
        if agent_class not in completed:
            return agent_name
    
    return "done"
```

### 4.6 Aggregator Node

```python
# Fichier : montecarlo/backend/app/agents/nodes/aggregator.py

import time
from langgraph.config import get_stream_writer
from app.agents.state import MissionState

async def aggregator_node(state: MissionState) -> dict:
    """
    Agrège tous les résultats des agents en un résultat final.
    """
    writer = get_stream_writer()
    
    result = {
        "market": state.get("market_data", {}),
        "analysis": state.get("analysis_data", {}),
        "risk": state.get("risk_data", {}),
        "portfolio": state.get("portfolio_data", {}),
        "backtest": state.get("backtest_data", {}),
        "ml": state.get("ml_data", {}),
        "monitoring": state.get("monitoring_data", {}),
    }
    
    # Nettoyer les clés vides
    result = {k: v for k, v in result.items() if v}
    
    writer({
        "agent": "OrchestratorAgent",
        "event": "mission_complete",
        "data": {
            "mission_id": state["mission_id"],
            "results_summary": list(result.keys()),
            "agents_completed": state.get("agents_completed", []),
            "agents_failed": state.get("agents_failed", []),
        },
        "status": "completed",
        "progress": 1.0,
        "timestamp": time.time()
    })
    
    return {
        "result": result,
        "status": "completed"
    }
```

### 4.7 Streaming Execution

```python
# Fichier : montecarlo/backend/app/agents/runner.py

import asyncio
from app.agents.graph import build_agent_graph

# Compiler le graphe une seule fois au démarrage
agent_graph = build_agent_graph()

async def run_mission(mission_type: str, params: dict, user_id: str):
    """
    Lance une mission et yield les événements en streaming.
    Utilise le streaming API v2 de LangGraph.
    """
    
    initial_state = {
        "mission_id": "",
        "mission_type": mission_type,
        "user_id": user_id,
        "status": "pending",
        "params": params,
        "market_data": {},
        "analysis_data": {},
        "risk_data": {},
        "portfolio_data": {},
        "backtest_data": {},
        "ml_data": {},
        "monitoring_data": {},
        "agents_completed": [],
        "agents_failed": [],
        "errors": [],
        "result": {},
        "duration_ms": 0,
        "messages": [],
    }
    
    # stream_mode="custom" pour recevoir les événements de get_stream_writer()
    # subgraphs=True pour voir aussi les événements des sous-graphes si on en ajoute
    async for event in agent_graph.astream(
        initial_state,
        stream_mode=["custom", "updates"],
        config={"recursion_limit": 50}
    ):
        yield event
```

---

## 5. WEBSOCKET BRIDGE

### 5.1 Schéma d'événements WebSocket

Tous les événements transitant via le WebSocket suivent ce format JSON :

```typescript
// Type TypeScript pour le frontend
interface AgentEvent {
  agent: string;          // "MarketAgent", "RiskAgent", etc.
  event: string;          // "market_fetch_start", "risk_phase", etc.
  data: Record<string, any>;  // Payload spécifique à l'événement
  status: "idle" | "running" | "completed" | "error" | "waiting";
  progress: number;       // 0.0 à 1.0
  timestamp: number;      // Unix timestamp (seconds)
}

// Événements de contrôle (envoyés par le frontend)
interface MissionCommand {
  action: "start" | "cancel" | "pause";
  mission_type?: string;  // Requis pour "start"
  params?: Record<string, any>;
  mission_id?: string;    // Requis pour "cancel" / "pause"
}
```

### 5.2 FastAPI WebSocket Endpoint

```python
# Fichier : montecarlo/backend/app/routes/agents.py

import asyncio
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel
from app.agents.runner import run_mission

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# ── Store des missions actives ──
active_missions: dict[str, asyncio.Task] = {}
connected_clients: list[WebSocket] = []


class MissionRequest(BaseModel):
    mission_type: str
    params: dict = {}


class MissionResponse(BaseModel):
    mission_id: str
    status: str
    message: str


# ── REST endpoints ──

@router.get("/list")
async def list_agents():
    """Retourne la liste des agents disponibles."""
    return {
        "agents": [
            {"name": "OrchestratorAgent", "color": "#D4AF37", "role": "Supervisor"},
            {"name": "MarketAgent",       "color": "#00D4FF", "role": "Market Data"},
            {"name": "AnalysisAgent",     "color": "#3B82F6", "role": "Fundamentals"},
            {"name": "RiskAgent",         "color": "#EF4444", "role": "Risk Engine"},
            {"name": "PortfolioAgent",    "color": "#10B981", "role": "Optimization"},
            {"name": "BacktestAgent",     "color": "#F59E0B", "role": "Backtesting"},
            {"name": "MLAgent",           "color": "#8B5CF6", "role": "ML/Prediction"},
            {"name": "MonitoringAgent",   "color": "#6366F1", "role": "Health Check"},
            {"name": "ErrorHandlerAgent", "color": "#F43F5E", "role": "Error Handler"},
            {"name": "LoggerAgent",       "color": "#94A3B8", "role": "Logger"},
        ]
    }


@router.post("/missions/start", response_model=MissionResponse)
async def start_mission(req: MissionRequest):
    """Démarre une nouvelle mission."""
    mission_id = str(uuid.uuid4())
    
    async def mission_task():
        async for event in run_mission(req.mission_type, req.params, "system"):
            await broadcast_event(event)
    
    task = asyncio.create_task(mission_task())
    active_missions[mission_id] = task
    
    return MissionResponse(
        mission_id=mission_id,
        status="started",
        message=f"Mission {req.mission_type} started"
    )


@router.post("/missions/{mission_id}/cancel")
async def cancel_mission(mission_id: str):
    """Annule une mission en cours."""
    task = active_missions.get(mission_id)
    if not task:
        raise HTTPException(404, "Mission not found")
    task.cancel()
    del active_missions[mission_id]
    return {"status": "cancelled", "mission_id": mission_id}


@router.get("/missions/{mission_id}/status")
async def get_mission_status(mission_id: str):
    """Statut d'une mission."""
    task = active_missions.get(mission_id)
    if not task:
        return {"status": "not_found", "mission_id": mission_id}
    if task.done():
        return {"status": "completed", "mission_id": mission_id}
    return {"status": "running", "mission_id": mission_id}


# ── WebSocket endpoint ──

@router.websocket("/stream")
async def agent_stream(ws: WebSocket):
    """
    WebSocket endpoint pour le streaming d'événements agents.
    Le client se connecte ici et reçoit tous les événements en temps réel.
    Peut aussi envoyer des commandes (start/cancel).
    """
    await ws.accept()
    connected_clients.append(ws)
    
    try:
        # Envoyer un message de bienvenue
        await ws.send_json({
            "agent": "System",
            "event": "connected",
            "data": {"message": "Connected to agent stream"},
            "status": "idle",
            "progress": 0.0,
            "timestamp": __import__("time").time()
        })
        
        # Écouter les commandes du client
        while True:
            try:
                raw = await ws.receive_text()
                command = json.loads(raw)
                
                if command.get("action") == "start":
                    mission_type = command.get("mission_type", "quick_scan")
                    params = command.get("params", {})
                    mission_id = str(uuid.uuid4())
                    
                    async def mission_task(mt, p, mid):
                        try:
                            async for event in run_mission(mt, p, "ws_user"):
                                await broadcast_event(event)
                        except asyncio.CancelledError:
                            await broadcast_event({
                                "agent": "OrchestratorAgent",
                                "event": "mission_cancelled",
                                "data": {"mission_id": mid},
                                "status": "idle",
                                "progress": 0.0,
                                "timestamp": __import__("time").time()
                            })
                    
                    task = asyncio.create_task(
                        mission_task(mission_type, params, mission_id)
                    )
                    active_missions[mission_id] = task
                    
                    await ws.send_json({
                        "agent": "System",
                        "event": "mission_accepted",
                        "data": {"mission_id": mission_id, "mission_type": mission_type},
                        "status": "running",
                        "progress": 0.0,
                        "timestamp": __import__("time").time()
                    })
                    
                elif command.get("action") == "cancel":
                    mid = command.get("mission_id")
                    if mid and mid in active_missions:
                        active_missions[mid].cancel()
                        del active_missions[mid]
                        
            except WebSocketDisconnect:
                break
                
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)


async def broadcast_event(event: dict):
    """Broadcast un événement à tous les clients WebSocket connectés."""
    dead = []
    for client in connected_clients:
        try:
            if isinstance(event, tuple):
                # LangGraph stream retourne des tuples (stream_mode, data)
                mode, data = event
                if mode == "custom":
                    await client.send_json(data)
                elif mode == "updates":
                    await client.send_json({
                        "agent": "System",
                        "event": "state_update",
                        "data": data,
                        "status": "running",
                        "progress": 0.5,
                        "timestamp": __import__("time").time()
                    })
            elif isinstance(event, dict):
                await client.send_json(event)
        except Exception:
            dead.append(client)
    
    for client in dead:
        if client in connected_clients:
            connected_clients.remove(client)
```

### 5.3 Enregistrer la route dans le backend

```python
# Dans montecarlo/backend/app/main.py — ajouter :

from app.routes.agents import router as agents_router
app.include_router(agents_router)
```

---

## 6. 2D POKÉMON-STYLE VISUALIZATION

### 6.1 Concept visuel

**Style : Pokémon Silver (Game Boy Color, 1999)**

- Vue top-down isométrique simplifiée
- Grid 16×16 tiles
- Sprites pixel-art 32×32 pour chaque agent
- Palette réduite à 4-6 couleurs par sprite (style GBC)
- Fond de map : sol sombre (#0A0E1A), sentiers lumineux (#1A2332), zones colorées par domaine
- Animations frame-by-frame (2-4 frames par animation)

### 6.2 Palette de couleurs Pokémon Silver

```
┌──────────────────────────────────────────────────┐
│  POKÉMON SILVER × GENESIX                        │
│                                                  │
│  Map background:  #0A0E1A  (dark navy)           │
│  Tile grid:       #131823  (subtle grid lines)   │
│  Path tiles:      #1A2332  (walkable paths)      │
│  Active glow:     #00D9FF  (cyan pulse)          │
│  Gold accents:    #D4AF37  (labels, borders)     │
│  Silver accents:  #C0C0C0  (secondary text)      │
│  Text primary:    #F1F5F9  (white-ish)           │
│  Text secondary:  #94A3B8  (muted slate)         │
│  Error flash:     #EF4444  (red blink)           │
│  Success glow:    #10B981  (green pulse)         │
│                                                  │
│  Sprite palettes follow agent colors from §3.1   │
└──────────────────────────────────────────────────┘
```

### 6.3 Map Layout (Canvas 800×600)

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   ┌─────────┐                              ┌─────────┐        │
│   │ MARKET  │          ┌─────────┐         │  RISK   │        │
│   │  ZONE   │──path───►│ ORCH.   │◄──path──│  ZONE   │        │
│   │ (Cyan)  │          │ CENTER  │         │ (Red)   │        │
│   └─────────┘          │ (Gold)  │         └─────────┘        │
│       │                └────┬────┘              │              │
│       │                     │                   │              │
│   ┌───┴─────┐          ┌───┴─────┐         ┌───┴─────┐       │
│   │ANALYSIS │          │PORTFOLIO│         │BACKTEST │       │
│   │  ZONE   │          │  ZONE   │         │  ZONE   │       │
│   │ (Blue)  │          │ (Green) │         │ (Amber) │       │
│   └─────────┘          └─────────┘         └─────────┘       │
│       │                     │                   │              │
│       │                ┌────┴────┐              │              │
│   ┌───┴─────┐          │   ML    │         ┌───┴─────┐       │
│   │MONITOR  │          │  ZONE   │         │  LOG    │       │
│   │  ZONE   │          │(Purple) │         │  ZONE   │       │
│   │(Indigo) │          └─────────┘         │ (Slate) │       │
│   └─────────┘                              └─────────┘       │
│                                                                │
│   ┌──────────────────── STATUS BAR ──────────────────────┐    │
│   │  Mission: full_analysis  │  Status: running  │ 45%   │    │
│   └──────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

### 6.4 Sprites — Système d'animation

Chaque agent a un sprite sheet CSS/SVG avec les animations suivantes :

| État | Animation | Frames | Durée |
|------|-----------|--------|-------|
| `idle` | Respiration (scale 1.0↔1.05) | 2 frames | 1000ms loop |
| `running` | Marche (bob up/down + glow pulse) | 4 frames | 400ms loop |
| `completed` | Flash vert + particules | 6 frames | 600ms once |
| `error` | Flash rouge + shake | 4 frames | 300ms × 3 |
| `waiting` | Clignotement doux (opacity 0.6↔1.0) | 2 frames | 800ms loop |

### 6.5 Sprite Design (CSS Pixel Art)

```tsx
// Fichier : ravinala-web/src/components/agents/AgentSprite.tsx

import { useEffect, useRef } from 'react';
import * as PIXI from 'pixi.js';

interface AgentSpriteProps {
  name: string;
  color: string;
  status: 'idle' | 'running' | 'completed' | 'error' | 'waiting';
  x: number;
  y: number;
  progress: number;
}

// Positions des agents sur la map (en tiles, chaque tile = 48px)
export const AGENT_POSITIONS: Record<string, { x: number; y: number; zone: string }> = {
  OrchestratorAgent: { x: 400, y: 140, zone: 'center' },
  MarketAgent:       { x: 120, y: 100, zone: 'market' },
  AnalysisAgent:     { x: 120, y: 260, zone: 'analysis' },
  RiskAgent:         { x: 680, y: 100, zone: 'risk' },
  PortfolioAgent:    { x: 400, y: 280, zone: 'portfolio' },
  BacktestAgent:     { x: 680, y: 260, zone: 'backtest' },
  MLAgent:           { x: 400, y: 420, zone: 'ml' },
  MonitoringAgent:   { x: 120, y: 420, zone: 'monitoring' },
  ErrorHandlerAgent: { x: 540, y: 420, zone: 'error' },
  LoggerAgent:       { x: 680, y: 420, zone: 'logger' },
};

// Couleurs des agents
export const AGENT_COLORS: Record<string, string> = {
  OrchestratorAgent: '#D4AF37',
  MarketAgent:       '#00D4FF',
  AnalysisAgent:     '#3B82F6',
  RiskAgent:         '#EF4444',
  PortfolioAgent:    '#10B981',
  BacktestAgent:     '#F59E0B',
  MLAgent:           '#8B5CF6',
  MonitoringAgent:   '#6366F1',
  ErrorHandlerAgent: '#F43F5E',
  LoggerAgent:       '#94A3B8',
};
```

### 6.6 PixiJS Canvas Component

```tsx
// Fichier : ravinala-web/src/components/agents/AgentCanvas.tsx

import { useEffect, useRef, useCallback } from 'react';
import * as PIXI from 'pixi.js';
import { AGENT_POSITIONS, AGENT_COLORS } from './AgentSprite';
import { AgentEvent } from '../../hooks/useAgentMonitor';

interface AgentCanvasProps {
  events: AgentEvent[];
  agentStates: Record<string, {
    status: string;
    progress: number;
    lastEvent: string;
  }>;
}

const CANVAS_WIDTH = 800;
const CANVAS_HEIGHT = 600;
const BG_COLOR = 0x0A0E1A;
const GRID_COLOR = 0x131823;
const PATH_COLOR = 0x1A2332;

export function AgentCanvas({ events, agentStates }: AgentCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<PIXI.Application | null>(null);
  const spritesRef = useRef<Record<string, PIXI.Container>>({}); 

  useEffect(() => {
    if (!containerRef.current) return;
    
    const app = new PIXI.Application();
    
    (async () => {
      await app.init({
        width: CANVAS_WIDTH,
        height: CANVAS_HEIGHT,
        backgroundColor: BG_COLOR,
        antialias: false, // Pixel art look
        resolution: 1,
      });
      
      containerRef.current?.appendChild(app.canvas as HTMLCanvasElement);
      appRef.current = app;
      
      // ── Dessiner la grille ──
      drawGrid(app);
      
      // ── Dessiner les zones ──
      drawZones(app);
      
      // ── Dessiner les paths (connexions entre agents) ──
      drawPaths(app);
      
      // ── Créer les sprites agents ──
      for (const [name, pos] of Object.entries(AGENT_POSITIONS)) {
        const sprite = createAgentSprite(app, name, pos.x, pos.y);
        spritesRef.current[name] = sprite;
        app.stage.addChild(sprite);
      }
    })();
    
    return () => {
      app.destroy(true);
    };
  }, []);
  
  // ── Mise à jour des sprites en fonction des événements ──
  useEffect(() => {
    for (const [name, state] of Object.entries(agentStates)) {
      const sprite = spritesRef.current[name];
      if (!sprite) continue;
      
      updateSpriteState(sprite, state.status, state.progress);
    }
  }, [agentStates]);
  
  return (
    <div 
      ref={containerRef}
      className="rounded-lg overflow-hidden border border-[#1A2332]"
      style={{ width: CANVAS_WIDTH, height: CANVAS_HEIGHT }}
    />
  );
}


function drawGrid(app: PIXI.Application) {
  const g = new PIXI.Graphics();
  g.setStrokeStyle({ width: 1, color: GRID_COLOR, alpha: 0.3 });
  
  for (let x = 0; x < CANVAS_WIDTH; x += 48) {
    g.moveTo(x, 0).lineTo(x, CANVAS_HEIGHT);
  }
  for (let y = 0; y < CANVAS_HEIGHT; y += 48) {
    g.moveTo(0, y).lineTo(CANVAS_WIDTH, y);
  }
  g.stroke();
  app.stage.addChild(g);
}


function drawZones(app: PIXI.Application) {
  const zones = [
    { x: 60, y: 60, w: 140, h: 100, color: 0x00D4FF, label: 'MARKET' },
    { x: 60, y: 220, w: 140, h: 100, color: 0x3B82F6, label: 'ANALYSIS' },
    { x: 340, y: 60, w: 140, h: 100, color: 0xD4AF37, label: 'ORCHESTRATOR' },
    { x: 620, y: 60, w: 140, h: 100, color: 0xEF4444, label: 'RISK' },
    { x: 340, y: 220, w: 140, h: 100, color: 0x10B981, label: 'PORTFOLIO' },
    { x: 620, y: 220, w: 140, h: 100, color: 0xF59E0B, label: 'BACKTEST' },
    { x: 340, y: 380, w: 140, h: 100, color: 0x8B5CF6, label: 'ML' },
    { x: 60, y: 380, w: 140, h: 100, color: 0x6366F1, label: 'MONITOR' },
    { x: 620, y: 380, w: 140, h: 100, color: 0x94A3B8, label: 'LOGGER' },
  ];
  
  for (const zone of zones) {
    const g = new PIXI.Graphics();
    // Zone background (très subtil)
    g.roundRect(zone.x, zone.y, zone.w, zone.h, 8);
    g.fill({ color: zone.color, alpha: 0.05 });
    g.roundRect(zone.x, zone.y, zone.w, zone.h, 8);
    g.stroke({ color: zone.color, alpha: 0.2, width: 1 });
    
    // Label
    const label = new PIXI.Text({
      text: zone.label, 
      style: {
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 9,
        fill: zone.color,
        align: 'center',
      }
    });
    label.x = zone.x + zone.w / 2;
    label.y = zone.y + 8;
    label.anchor.set(0.5, 0);
    
    app.stage.addChild(g);
    app.stage.addChild(label);
  }
}


function drawPaths(app: PIXI.Application) {
  const g = new PIXI.Graphics();
  g.setStrokeStyle({ width: 2, color: PATH_COLOR, alpha: 0.5 });
  
  // Connexions entre agents (Orchestrator au centre)
  const orch = AGENT_POSITIONS.OrchestratorAgent;
  for (const [name, pos] of Object.entries(AGENT_POSITIONS)) {
    if (name === 'OrchestratorAgent') continue;
    g.moveTo(orch.x, orch.y).lineTo(pos.x, pos.y);
  }
  
  g.stroke();
  app.stage.addChild(g);
}


function createAgentSprite(
  app: PIXI.Application, 
  name: string, 
  x: number, 
  y: number
): PIXI.Container {
  const container = new PIXI.Container();
  container.x = x;
  container.y = y;
  
  const color = parseInt(AGENT_COLORS[name]?.replace('#', '0x') || '0xFFFFFF');
  
  // Corps du sprite (cercle pixel-art style)
  const body = new PIXI.Graphics();
  // Forme pixel-art simplifiée : rectangle arrondi 24×28
  body.roundRect(-12, -14, 24, 28, 4);
  body.fill({ color, alpha: 0.9 });
  body.roundRect(-12, -14, 24, 28, 4);
  body.stroke({ color: 0xFFFFFF, alpha: 0.3, width: 1 });
  container.addChild(body);
  
  // "Yeux" (2 pixels blancs)
  const eyes = new PIXI.Graphics();
  eyes.rect(-5, -8, 3, 3).fill(0xFFFFFF);
  eyes.rect(3, -8, 3, 3).fill(0xFFFFFF);
  container.addChild(eyes);
  
  // Nom sous le sprite
  const label = new PIXI.Text({
    text: name.replace('Agent', ''), 
    style: {
      fontFamily: 'JetBrains Mono, monospace',
      fontSize: 8,
      fill: 0xCBD5E1,
      align: 'center'
    }
  });
  label.anchor.set(0.5, 0);
  label.y = 20;
  container.addChild(label);
  
  // Progress bar sous le nom
  const progressBg = new PIXI.Graphics();
  progressBg.roundRect(-16, 32, 32, 3, 1);
  progressBg.fill({ color: 0x1A2332 });
  container.addChild(progressBg);
  
  const progressFill = new PIXI.Graphics();
  progressFill.roundRect(-16, 32, 0, 3, 1); // width 0 initially
  progressFill.fill({ color });
  progressFill.label = 'progressFill';
  container.addChild(progressFill);
  
  // Stocker des refs pour l'animation
  (container as any).__body = body;
  (container as any).__color = color;
  (container as any).__baseY = y;
  
  return container;
}


function updateSpriteState(
  container: PIXI.Container, 
  status: string, 
  progress: number
) {
  const body = (container as any).__body as PIXI.Graphics;
  const color = (container as any).__color as number;
  const baseY = (container as any).__baseY as number;
  
  // Trouver la progress bar
  const progressFill = container.children.find(
    c => c.label === 'progressFill'
  ) as PIXI.Graphics | undefined;
  
  // Mettre à jour la progress bar
  if (progressFill) {
    progressFill.clear();
    progressFill.roundRect(-16, 32, 32 * progress, 3, 1);
    progressFill.fill({ color });
  }
  
  // Animations par état
  switch (status) {
    case 'running':
      // Bob animation + glow
      container.y = baseY + Math.sin(Date.now() / 200) * 3;
      container.alpha = 1.0;
      body.tint = 0xFFFFFF; // Normal color 
      break;
      
    case 'completed':
      container.y = baseY;
      container.alpha = 1.0;
      // Flash vert
      body.tint = 0x10B981;
      break;
      
    case 'error':
      // Shake + flash rouge
      container.x += Math.sin(Date.now() / 50) * 2;
      body.tint = 0xEF4444;
      break;
      
    case 'waiting':
      container.y = baseY;
      container.alpha = 0.6 + Math.sin(Date.now() / 400) * 0.2;
      break;
      
    default: // idle
      container.y = baseY;
      container.alpha = 0.5;
      break;
  }
}
```

---

## 7. FRONTEND REACT INTEGRATION

### 7.1 Hook useAgentMonitor

```typescript
// Fichier : ravinala-web/src/hooks/useAgentMonitor.ts

import { useState, useEffect, useCallback, useRef } from 'react';

export interface AgentEvent {
  agent: string;
  event: string;
  data: Record<string, any>;
  status: 'idle' | 'running' | 'completed' | 'error' | 'waiting';
  progress: number;
  timestamp: number;
}

export interface AgentState {
  status: 'idle' | 'running' | 'completed' | 'error' | 'waiting';
  progress: number;
  lastEvent: string;
  lastData: Record<string, any>;
}

interface UseAgentMonitorReturn {
  connected: boolean;
  events: AgentEvent[];
  agentStates: Record<string, AgentState>;
  missionStatus: 'idle' | 'running' | 'completed' | 'failed';
  missionId: string | null;
  startMission: (missionType: string, params?: Record<string, any>) => void;
  cancelMission: () => void;
  clearEvents: () => void;
}

const WS_URL = `ws://${window.location.hostname}:8000/api/v1/agents/stream`;
const MAX_EVENTS = 500; // Limiter le nombre d'événements gardés en mémoire

const DEFAULT_AGENT_NAMES = [
  'OrchestratorAgent', 'MarketAgent', 'AnalysisAgent', 'RiskAgent',
  'PortfolioAgent', 'BacktestAgent', 'MLAgent', 'MonitoringAgent',
  'ErrorHandlerAgent', 'LoggerAgent',
];

export function useAgentMonitor(): UseAgentMonitorReturn {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [missionStatus, setMissionStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [missionId, setMissionId] = useState<string | null>(null);
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>(() => {
    const initial: Record<string, AgentState> = {};
    for (const name of DEFAULT_AGENT_NAMES) {
      initial[name] = { status: 'idle', progress: 0, lastEvent: '', lastData: {} };
    }
    return initial;
  });
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  
  // ── Connexion WebSocket ──
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    
    ws.onopen = () => {
      setConnected(true);
    };
    
    ws.onmessage = (msg) => {
      try {
        const event: AgentEvent = JSON.parse(msg.data);
        
        // Ajouter l'événement au log (avec limit)
        setEvents(prev => {
          const next = [...prev, event];
          return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
        });
        
        // Mettre à jour l'état de l'agent
        if (event.agent && event.agent !== 'System') {
          setAgentStates(prev => ({
            ...prev,
            [event.agent]: {
              status: event.status,
              progress: event.progress,
              lastEvent: event.event,
              lastData: event.data,
            }
          }));
        }
        
        // Tracker le statut de la mission
        if (event.event === 'mission_accepted') {
          setMissionStatus('running');
          setMissionId(event.data.mission_id);
        } else if (event.event === 'mission_complete') {
          setMissionStatus('completed');
        } else if (event.event === 'mission_failed') {
          setMissionStatus('failed');
        }
        
      } catch {
        // Ignorer les messages non-JSON
      }
    };
    
    ws.onclose = () => {
      setConnected(false);
      // Auto-reconnect après 3s
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };
    
    ws.onerror = () => {
      ws.close();
    };
  }, []);
  
  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);
  
  // ── Actions ──
  const startMission = useCallback((missionType: string, params: Record<string, any> = {}) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;
    
    // Reset tous les agents à idle
    setAgentStates(prev => {
      const reset: Record<string, AgentState> = {};
      for (const name of Object.keys(prev)) {
        reset[name] = { status: 'idle', progress: 0, lastEvent: '', lastData: {} };
      }
      return reset;
    });
    setEvents([]);
    setMissionStatus('idle');
    
    wsRef.current.send(JSON.stringify({
      action: 'start',
      mission_type: missionType,
      params,
    }));
  }, []);
  
  const cancelMission = useCallback(() => {
    if (!wsRef.current || !missionId) return;
    wsRef.current.send(JSON.stringify({
      action: 'cancel',
      mission_id: missionId,
    }));
    setMissionStatus('idle');
  }, [missionId]);
  
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);
  
  return {
    connected,
    events,
    agentStates,
    missionStatus,
    missionId,
    startMission,
    cancelMission,
    clearEvents,
  };
}
```

### 7.2 Agent Monitor Page

```tsx
// Fichier : ravinala-web/src/pages/AgentMonitorPage.tsx

import { useState } from 'react';
import { useAgentMonitor, AgentEvent } from '../hooks/useAgentMonitor';
import { AgentCanvas } from '../components/agents/AgentCanvas';
import { AGENT_COLORS } from '../components/agents/AgentSprite';

const MISSION_TYPES = [
  { value: 'full_analysis', label: 'Full Analysis', desc: 'Market → Analysis → Risk → Portfolio' },
  { value: 'quick_scan', label: 'Quick Scan', desc: 'Market → Analysis' },
  { value: 'risk_check', label: 'Risk Check', desc: 'Market → Risk' },
  { value: 'backtest_run', label: 'Backtest Run', desc: 'Market → Backtest' },
  { value: 'ml_predict', label: 'ML Predict', desc: 'Market → ML' },
  { value: 'portfolio_optimize', label: 'Portfolio Optimize', desc: 'Market → Analysis → Risk → Portfolio' },
  { value: 'health_check', label: 'Health Check', desc: 'Monitoring only' },
];

export default function AgentMonitorPage() {
  const {
    connected,
    events,
    agentStates,
    missionStatus,
    startMission,
    cancelMission,
    clearEvents,
  } = useAgentMonitor();
  
  const [selectedMission, setSelectedMission] = useState('full_analysis');
  const [tickerInput, setTickerInput] = useState('AAPL,MSFT,GOOGL');
  
  const handleStart = () => {
    const tickers = tickerInput.split(',').map(t => t.trim()).filter(Boolean);
    startMission(selectedMission, { tickers });
  };
  
  return (
    <div className="min-h-screen p-6 space-y-6" style={{ backgroundColor: '#0A0E1A' }}>
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#F1F5F9]" style={{ fontFamily: 'JetBrains Mono' }}>
            🎮 Agent Monitor
          </h1>
          <p className="text-sm text-[#94A3B8]">
            Pokémon Silver × GENESIX — Multi-Agent Orchestration
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono ${
            connected 
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
              : 'bg-red-500/10 text-red-400 border border-red-500/20'
          }`}>
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
      
      {/* Main layout: Canvas + Controls */}
      <div className="grid grid-cols-[1fr_360px] gap-6">
        
        {/* Left: Canvas */}
        <div>
          <AgentCanvas events={events} agentStates={agentStates} />
        </div>
        
        {/* Right: Control Panel */}
        <div className="space-y-4">
          
          {/* Mission Selector */}
          <div className="rounded-lg border border-[#1A2332] bg-[#131823] p-4 space-y-3">
            <h2 className="text-sm font-bold text-[#D4AF37] font-mono uppercase tracking-wider">
              Mission Control
            </h2>
            
            <div>
              <label className="block text-xs text-[#94A3B8] mb-1">Mission Type</label>
              <select
                value={selectedMission}
                onChange={(e) => setSelectedMission(e.target.value)}
                className="w-full bg-[#0A0E1A] border border-[#1A2332] rounded px-3 py-2 text-sm text-[#F1F5F9] font-mono"
              >
                {MISSION_TYPES.map(m => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
              <p className="text-xs text-[#64748B] mt-1">
                {MISSION_TYPES.find(m => m.value === selectedMission)?.desc}
              </p>
            </div>
            
            <div>
              <label className="block text-xs text-[#94A3B8] mb-1">Tickers</label>
              <input
                type="text"
                value={tickerInput}
                onChange={(e) => setTickerInput(e.target.value)}
                placeholder="AAPL,MSFT,GOOGL"
                className="w-full bg-[#0A0E1A] border border-[#1A2332] rounded px-3 py-2 text-sm text-[#F1F5F9] font-mono"
              />
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={handleStart}
                disabled={missionStatus === 'running' || !connected}
                className="flex-1 px-4 py-2 rounded font-mono text-sm font-bold
                  bg-[#D4AF37] text-[#0A0E1A] hover:bg-[#E5C04B]
                  disabled:opacity-40 disabled:cursor-not-allowed
                  transition-colors"
              >
                {missionStatus === 'running' ? '⏳ Running...' : '▶ Start Mission'}
              </button>
              
              {missionStatus === 'running' && (
                <button
                  onClick={cancelMission}
                  className="px-4 py-2 rounded font-mono text-sm
                    bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20
                    hover:bg-[#EF4444]/20 transition-colors"
                >
                  ✕ Cancel
                </button>
              )}
            </div>
          </div>
          
          {/* Agent Status Cards */}
          <div className="rounded-lg border border-[#1A2332] bg-[#131823] p-4 space-y-2">
            <h2 className="text-sm font-bold text-[#00D9FF] font-mono uppercase tracking-wider">
              Agent Status
            </h2>
            
            <div className="space-y-1.5 max-h-[240px] overflow-y-auto">
              {Object.entries(agentStates).map(([name, state]) => (
                <div
                  key={name}
                  className="flex items-center gap-2 px-2 py-1.5 rounded bg-[#0A0E1A]/50"
                >
                  <span
                    className="w-3 h-3 rounded-sm"
                    style={{ backgroundColor: AGENT_COLORS[name] || '#94A3B8' }}
                  />
                  <span className="text-xs font-mono text-[#CBD5E1] flex-1">
                    {name.replace('Agent', '')}
                  </span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    state.status === 'running'   ? 'bg-cyan-500/10 text-cyan-400' :
                    state.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                    state.status === 'error'     ? 'bg-red-500/10 text-red-400' :
                    state.status === 'waiting'   ? 'bg-amber-500/10 text-amber-400' :
                    'bg-slate-500/10 text-slate-500'
                  }`}>
                    {state.status}
                  </span>
                  {state.progress > 0 && state.progress < 1 && (
                    <span className="text-[10px] font-mono text-[#94A3B8]">
                      {Math.round(state.progress * 100)}%
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
          
          {/* Event Log */}
          <div className="rounded-lg border border-[#1A2332] bg-[#131823] p-4 space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-[#C0C0C0] font-mono uppercase tracking-wider">
                Event Log
              </h2>
              <button
                onClick={clearEvents}
                className="text-[10px] text-[#64748B] hover:text-[#94A3B8] font-mono"
              >
                Clear
              </button>
            </div>
            
            <div className="space-y-0.5 max-h-[200px] overflow-y-auto font-mono text-[10px]">
              {events.slice(-50).reverse().map((evt, i) => (
                <div key={i} className="flex gap-2 text-[#94A3B8]">
                  <span style={{ color: AGENT_COLORS[evt.agent] || '#94A3B8' }}>
                    [{evt.agent?.replace('Agent', '') || 'SYS'}]
                  </span>
                  <span className="text-[#CBD5E1]">{evt.event}</span>
                  {evt.data && Object.keys(evt.data).length > 0 && (
                    <span className="text-[#64748B] truncate max-w-[150px]">
                      {JSON.stringify(evt.data).slice(0, 60)}
                    </span>
                  )}
                </div>
              ))}
              {events.length === 0 && (
                <p className="text-[#475569] italic">No events yet. Start a mission.</p>
              )}
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
```

### 7.3 Route dans App.tsx

```tsx
// Ajouter dans ravinala-web/src/App.tsx (dans les routes protégées) :

import AgentMonitorPage from './pages/AgentMonitorPage';

// Dans le <Routes> :
<Route path="/agents/monitor" element={<AgentMonitorPage />} />
```

### 7.4 Entrée dans la Sidebar

```tsx
// Ajouter dans ravinala-web/src/components/Sidebar.tsx :
// Nouvelle section "AI Agents" avec couleur #D4AF37 (gold)

{
  title: 'AI Agents',
  icon: '🎮',
  color: '#D4AF37',
  items: [
    { label: 'Agent Monitor', path: '/agents/monitor', icon: '📡' },
  ]
}
```

---

## 8. BACKEND FASTAPI INTEGRATION

### 8.1 Structure des fichiers à créer

```
montecarlo/backend/app/
├── agents/                          ← NOUVEAU DOSSIER
│   ├── __init__.py
│   ├── state.py                     ← MissionState (§4.2)
│   ├── graph.py                     ← Build du graphe LangGraph (§4.4)
│   ├── runner.py                    ← run_mission() avec streaming (§4.7)
│   └── nodes/                       ← NOUVEAU SOUS-DOSSIER
│       ├── __init__.py
│       ├── orchestrator.py          ← OrchestratorAgent (§4.5)
│       ├── market_agent.py          ← MarketAgent (§4.3)
│       ├── analysis_agent.py        ← AnalysisAgent
│       ├── risk_agent.py            ← RiskAgent
│       ├── portfolio_agent.py       ← PortfolioAgent
│       ├── backtest_agent.py        ← BacktestAgent
│       ├── ml_agent.py              ← MLAgent
│       ├── monitoring_agent.py      ← MonitoringAgent
│       ├── error_handler.py         ← ErrorHandlerAgent
│       └── aggregator.py            ← Aggregator (§4.6)
├── routes/
│   └── agents.py                    ← WebSocket + REST endpoints (§5.2)
```

### 8.2 Structure des fichiers frontend à créer

```
ravinala-web/src/
├── components/
│   └── agents/                      ← NOUVEAU DOSSIER
│       ├── AgentSprite.tsx           ← Constantes + types (§6.5)
│       └── AgentCanvas.tsx           ← Canvas PixiJS (§6.6)
├── hooks/
│   └── useAgentMonitor.ts           ← Hook WebSocket (§7.1)
├── pages/
│   └── AgentMonitorPage.tsx         ← Page principale (§7.2)
```

### 8.3 Dépendances à installer

**Backend (Python) :**
```bash
cd montecarlo/backend
pip install langgraph langchain-core
```

Ajouter dans `montecarlo/backend/requirements.txt` :
```
langgraph>=0.4.0
langchain-core>=0.3.0
```

**Frontend (npm) :**
```bash
cd ravinala-web
npm install pixi.js@^8
```

### 8.4 Chaque agent node suit le même pattern

Voici le template pour créer chaque agent node. Il suffit d'adapter les imports et la logique métier :

```python
# Template : montecarlo/backend/app/agents/nodes/{agent_name}_agent.py

import time
from langgraph.config import get_stream_writer
from app.agents.state import MissionState

# Nom de l'agent (pour les événements)
AGENT_NAME = "XxxAgent"  # ← Remplacer

async def xxx_agent_node(state: MissionState) -> dict:
    """
    Node LangGraph pour {AGENT_NAME}.
    """
    writer = get_stream_writer()
    start_time = time.time()
    
    # ── 1. Émettre start ──
    writer({
        "agent": AGENT_NAME,
        "event": f"{AGENT_NAME.lower()}_start",
        "data": {},  # ← Remplir avec les params pertinents
        "status": "running",
        "progress": 0.0,
        "timestamp": time.time()
    })
    
    try:
        # ── 2. Logique métier ──
        # Importer et appeler le module existant ici
        # Ex: from src.analysis.fundamentals import FundamentalAnalyzer
        # result = await some_function(state["market_data"], state["params"])
        
        result = {}  # ← Remplacer par le vrai résultat
        
        # ── 3. Émettre progrès intermédiaire(s) si nécessaire ──
        writer({
            "agent": AGENT_NAME,
            "event": f"{AGENT_NAME.lower()}_phase",
            "data": {"phase": "processing", "progress_pct": 50},
            "status": "running",
            "progress": 0.5,
            "timestamp": time.time()
        })
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # ── 4. Émettre complete ──
        writer({
            "agent": AGENT_NAME,
            "event": f"{AGENT_NAME.lower()}_complete",
            "data": {"duration_ms": duration_ms},
            "status": "completed",
            "progress": 1.0,
            "timestamp": time.time()
        })
        
        # ── 5. Retourner le state update ──
        return {
            "xxx_data": result,  # ← Adapter la clé
            "agents_completed": [AGENT_NAME]
        }
        
    except Exception as e:
        writer({
            "agent": AGENT_NAME,
            "event": f"{AGENT_NAME.lower()}_error",
            "data": {"error": str(e)},
            "status": "error",
            "progress": 0.0,
            "timestamp": time.time()
        })
        
        return {
            "agents_failed": [AGENT_NAME],
            "errors": [{"agent": AGENT_NAME, "error": str(e), "timestamp": time.time()}]
        }
```

---

## 9. PLAN D'EXÉCUTION PAS-À-PAS

### Phase 1 : Backend — LangGraph Engine (7 fichiers)

| Step | Fichier | Action | Dépendance |
|------|---------|--------|------------|
| 1.1 | `pip install langgraph langchain-core` | Installer deps | — |
| 1.2 | `app/agents/__init__.py` | Créer (vide) | — |
| 1.3 | `app/agents/state.py` | Créer MissionState (§4.2) | — |
| 1.4 | `app/agents/nodes/__init__.py` | Créer (vide) | — |
| 1.5 | `app/agents/nodes/orchestrator.py` | Créer (§4.5) | 1.3 |
| 1.6 | `app/agents/nodes/market_agent.py` | Créer (§4.3) | 1.3 |
| 1.7 | `app/agents/nodes/analysis_agent.py` | Créer (template §8.4) | 1.3 |
| 1.8 | `app/agents/nodes/risk_agent.py` | Créer (template §8.4) | 1.3 |
| 1.9 | `app/agents/nodes/portfolio_agent.py` | Créer (template §8.4) | 1.3 |
| 1.10 | `app/agents/nodes/backtest_agent.py` | Créer (template §8.4) | 1.3 |
| 1.11 | `app/agents/nodes/ml_agent.py` | Créer (template §8.4) | 1.3 |
| 1.12 | `app/agents/nodes/monitoring_agent.py` | Créer (template §8.4) | 1.3 |
| 1.13 | `app/agents/nodes/error_handler.py` | Créer (§3.2 Agent 8) | 1.3 |
| 1.14 | `app/agents/nodes/aggregator.py` | Créer (§4.6) | 1.3 |
| 1.15 | `app/agents/graph.py` | Créer (§4.4) | 1.5–1.14 |
| 1.16 | `app/agents/runner.py` | Créer (§4.7) | 1.15 |

### Phase 2 : Backend — WebSocket & REST (2 fichiers)

| Step | Fichier | Action | Dépendance |
|------|---------|--------|------------|
| 2.1 | `app/routes/agents.py` | Créer (§5.2) | Phase 1 |
| 2.2 | `app/main.py` | Ajouter `include_router(agents_router)` | 2.1 |

### Phase 3 : Frontend — PixiJS + Hook + Page (5 fichiers)

| Step | Fichier | Action | Dépendance |
|------|---------|--------|------------|
| 3.1 | `npm install pixi.js@^8` | Installer dep | — |
| 3.2 | `src/components/agents/AgentSprite.tsx` | Créer (§6.5) | — |
| 3.3 | `src/components/agents/AgentCanvas.tsx` | Créer (§6.6) | 3.1, 3.2 |
| 3.4 | `src/hooks/useAgentMonitor.ts` | Créer (§7.1) | — |
| 3.5 | `src/pages/AgentMonitorPage.tsx` | Créer (§7.2) | 3.2, 3.3, 3.4 |

### Phase 4 : Intégration (2 éditions)

| Step | Fichier | Action | Dépendance |
|------|---------|--------|------------|
| 4.1 | `src/App.tsx` | Ajouter route `/agents/monitor` (§7.3) | 3.5 |
| 4.2 | `src/components/Sidebar.tsx` | Ajouter section "AI Agents" (§7.4) | 3.5 |

### Phase 5 : Validation

| Step | Action | Critère de succès |
|------|--------|-------------------|
| 5.1 | `cd ravinala-web && npm run build` | 0 erreurs TypeScript |
| 5.2 | `cd montecarlo/backend && python -c "from app.agents.graph import build_agent_graph; g = build_agent_graph(); print('OK')"` | Print "OK" |
| 5.3 | Lancer backend + frontend, ouvrir `/agents/monitor` | Page affiche canvas + panel |
| 5.4 | Cliquer "Start Mission" → observer les sprites s'animer | Sprites bougent, events dans le log |

---

## 10. TESTS & VALIDATION

### 10.1 Test unitaire du graphe

```python
# Fichier : montecarlo/backend/tests/test_agent_graph.py

import asyncio
import pytest
from app.agents.graph import build_agent_graph
from app.agents.state import MissionState

def test_graph_compiles():
    """Le graphe doit compiler sans erreur."""
    graph = build_agent_graph()
    assert graph is not None

@pytest.mark.asyncio
async def test_health_check_mission():
    """Une mission health_check doit passer par MonitoringAgent."""
    graph = build_agent_graph()
    
    initial = MissionState(
        mission_id="test-1",
        mission_type="health_check",
        user_id="test",
        status="pending",
        params={},
        market_data={},
        analysis_data={},
        risk_data={},
        portfolio_data={},
        backtest_data={},
        ml_data={},
        monitoring_data={},
        agents_completed=[],
        agents_failed=[],
        errors=[],
        result={},
        duration_ms=0,
        messages=[],
    )
    
    events = []
    async for event in graph.astream(initial, stream_mode=["custom", "updates"]):
        events.append(event)
    
    # Vérifier qu'on a bien des événements
    assert len(events) > 0

@pytest.mark.asyncio
async def test_quick_scan_mission():
    """Une mission quick_scan doit passer par MarketAgent puis AnalysisAgent."""
    graph = build_agent_graph()
    
    initial = MissionState(
        mission_id="test-2",
        mission_type="quick_scan",
        user_id="test",
        status="pending",
        params={"tickers": ["AAPL"]},
        market_data={},
        analysis_data={},
        risk_data={},
        portfolio_data={},
        backtest_data={},
        ml_data={},
        monitoring_data={},
        agents_completed=[],
        agents_failed=[],
        errors=[],
        result={},
        duration_ms=0,
        messages=[],
    )
    
    events = []
    async for event in graph.astream(initial, stream_mode=["custom", "updates"]):
        events.append(event)
    
    assert len(events) > 0
```

### 10.2 Test WebSocket

```python
# Fichier : montecarlo/backend/tests/test_agent_ws.py

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_list_agents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/agents/list")
        assert r.status_code == 200
        data = r.json()
        assert "agents" in data
        assert len(data["agents"]) == 10
```

### 10.3 Validation frontend

```bash
cd ravinala-web
npm run build
# Attendu: 0 erreurs, build success
```

---

## RÉCAPITULATIF

| Élément | Fichiers | Status |
|---------|----------|--------|
| LangGraph state + nodes | 12 fichiers Python | À créer |
| LangGraph graph + runner | 2 fichiers Python | À créer |
| WebSocket + REST route | 1 fichier Python + 1 edit | À créer |
| PixiJS canvas components | 2 fichiers TSX | À créer |
| WebSocket hook | 1 fichier TS | À créer |
| Monitor page | 1 fichier TSX | À créer |
| Route + Sidebar | 2 edits | À faire |
| Tests | 2 fichiers Python | À créer |
| **TOTAL** | **~21 fichiers** | — |

---

> **Ce prompt est prêt à être exécuté.** Copie-colle-le dans un agent IA et dis :
> *"Exécute ce prompt phase par phase. Commence par la Phase 1."*
