# GENESIX Ω — Quantitative Investment Intelligence Suite

> **Version 2.1** · React + TypeScript Frontend · FastAPI Backend  
> Enterprise-grade financial analytics platform with 13 integrated modules

---

## Architecture Overview

```
GENESIX Ω Suite
├─ Data Intelligence Layer
│  ├─ Universe Search ........... 80+ instruments, global coverage
│  ├─ Advanced Screener ......... Multi-criteria stock filtering
│  └─ Data Layer ................ Health monitoring, cache, quality metrics
│
├─ Analysis Engine
│  ├─ Instrument Analysis ....... Fundamentals, ESG, peer comparison
│  ├─ Advanced Analysis ......... Efficient frontier, Monte Carlo
│  └─ Market Intelligence ....... Signals, sentiment, health scores
│
├─ Risk & Portfolio Management
│  ├─ Portfolio Omega ........... Strategic allocation, Sharpe, VaR
│  ├─ Portfolio Monitor ......... Live positions, P&L, tax harvesting
│  └─ Risk Engine ............... VaR/CVaR, stress tests, factor decomposition
│
├─ Signal Generation & Prediction
│  ├─ Signal Intelligence ....... Buy/sell with confidence levels
│  ├─ ML Engine ................. RF, XGBoost, LSTM ensemble
│  └─ Backtesting ............... Historical strategy performance
│
└─ Advanced Physics Framework
   └─ Physics Lab ............... Seismology, LPPL, criticality, percolation
```

---

## Modules

### 1. Universe Search

**Route:** `/genesix/universe`  
**File:** `src/pages/genesix/UniverseSearch.tsx`

Global instrument universe spanning 80+ securities across US, EU, and Asia markets. Includes stocks, ETFs, and bonds with real-time pricing metrics, search, and filtering.

**Features:**

- Full-text search across tickers, names, sectors
- Region filters (US, EU, Asia)
- Asset class filters (Equity, ETF, Bond)
- Real-time price, change %, volume
- Sortable columns

---

### 2. Advanced Screener

**Route:** `/genesix/screener`  
**File:** `src/pages/genesix/AdvancedScreener.tsx`

Multi-criteria stock filtering engine for quantitative screening.

**Criteria:**

- Ticker / Name search
- Sector selection
- Market cap range
- P/E ratio range
- Dividend yield minimum
- Volatility range
- Beta range

---

### 3. Instrument Analysis

**Route:** `/genesix/instrument`  
**File:** `src/pages/genesix/InstrumentAnalysis.tsx`

Deep instrument profiles with fundamental analysis, risk metrics, ESG scoring, and peer comparison.

**Tabs:**

- **Overview** — Price chart, key metrics, analyst consensus
- **Fundamentals** — Income statement, balance sheet, cash flow
- **Risk Metrics** — Beta, volatility, drawdown, VaR
- **ESG Score** — Environmental, Social, Governance ratings
- **Peer Comparison** — Side-by-side with sector peers
- **Analyst Ratings** — Buy/hold/sell distribution, price targets

---

### 4. Portfolio Omega (Ω)

**Route:** `/genesix/portfolio`  
**File:** `src/pages/genesix/PortfolioOmega.tsx`

Strategic portfolio dashboard — the core allocator of the suite.

**Features:**

- Asset allocation across 6 classes (Equities, Bonds, Commodities, Real Estate, Crypto, Cash)
- Key metrics: VaR, Sharpe Ratio, Beta, Max Drawdown, Volatility, Sortino
- Allocation pie chart with interactive adjustments
- Performance vs benchmark comparison
- Correlation matrix

---

### 5. Risk Engine

**Route:** `/genesix/risk`  
**File:** `src/pages/genesix/RiskEngine.tsx`

Comprehensive risk analytics module.

**Tabs:**

- **VaR / CVaR** — Value-at-Risk and Conditional VaR at 95%/99% confidence
- **Drawdown Analysis** — Max drawdown tracking, recovery periods
- **Volatility Cone** — Forward-looking vol projections with confidence bands
- **Stress Tests** — 8 historical scenarios (2008 GFC, COVID crash, Dot-com, etc.)
- **Factor Decomposition** — Market, size, value, momentum factor exposures

---

### 6. Backtesting

**Route:** `/genesix/backtest`  
**File:** `src/pages/genesix/Backtesting.tsx`

Strategy backtesting with full performance attribution.

**Features:**

- Equity curve visualization
- Drawdown overlay
- Rolling returns (1M, 3M, 6M, 1Y)
- Attribution analysis (allocation vs selection effect)
- Risk metrics (Sharpe, Sortino, Calmar, Max DD)
- Monthly returns heatmap

---

### 7. ML Engine

**Route:** `/genesix/ml`  
**File:** `src/pages/genesix/MLEngine.tsx`

Machine learning prediction engine with ensemble models.

**Models:**

- **Random Forest** — Feature importance, OOB score
- **XGBoost** — Gradient boosting with hyperparameter tuning
- **LSTM** — Deep learning for sequence prediction

**Features:**

- Regime detection (Bull / Bear / Sideways)
- Anomaly detection with isolation forests
- Feature importance ranking
- Prediction accuracy tracking
- Model comparison dashboard

---

### 8. Advanced Analysis

**Route:** `/genesix/analysis`  
**File:** `src/pages/genesix/AdvancedAnalysis.tsx`

Quantitative analysis tools.

**Features:**

- **Efficient Frontier** — Mean-variance optimization, tangency portfolio
- **Monte Carlo** — 5,000 portfolio simulations
- **Factor Analysis** — Fama-French multi-factor regression
- **Statistical Tests** — Normality, stationarity, autocorrelation
- **Return Distribution** — Histogram, Q-Q plot, tail analysis

---

### 9. Market Intelligence

**Route:** `/genesix/intelligence`  
**File:** `src/pages/genesix/MarketIntelligence.tsx`

Real-time market health monitoring and signal generation.

**Health Scores (0-100):**

- Market Breadth — % stocks above moving averages
- Momentum — Rate of change aggregation
- Volatility — VIX regime classification
- Sentiment — Put/call ratio, CNN Fear & Greed proxy

**Features:**

- Market summary with key indices
- Alert system for regime changes
- Signal history log

---

### 10. Portfolio Monitor

**Route:** `/genesix/monitor`  
**File:** `src/pages/genesix/PortfolioMonitor.tsx`

Live position tracking and portfolio management.

**Features:**

- Holdings table with real-time P&L
- Allocation pie chart (by sector, asset class)
- Performance vs benchmark
- Rebalancing recommendations
- Tax-loss harvesting suggestions
- Dividend tracking

---

### 11. Signal Intelligence

**Route:** `/genesix/signals`  
**File:** `src/pages/genesix/SignalIntelligence.tsx`

Trading signal dashboard with actionable recommendations.

**Signal Properties:**

- Direction: Buy / Sell / Hold
- Confidence level (0-100%)
- Entry price, target price, stop-loss
- Strategy type (Momentum, Mean Reversion, Breakout, etc.)
- Timeframe (Intraday, Swing, Position)

---

### 12. Data Layer

**Route:** `/genesix/data`  
**File:** `src/pages/genesix/DataLayer.tsx`

Data infrastructure monitoring and management.

**Data Sources:**
| Source | Type | Latency | Status |
|--------|------|---------|--------|
| Bloomberg | Real-time | 12ms | Connected |
| Refinitiv | Fundamentals | 45ms | Connected |
| Quandl | Alt data | 120ms | Connected |
| Reuters | News/Sentiment | 350ms | Degraded |
| SEC EDGAR | Regulatory | 200ms | Connected |

**Features:**

- Cache statistics and hit rates
- Data quality metrics (completeness, accuracy, timeliness)
- Manual refresh by section
- Export dashboard (Excel / PDF)

---

### 13. Physics Lab

**Route:** `/genesix/physics`  
**File:** `src/pages/genesix/PhysicsLab.tsx`

Physics-inspired market analysis — unique to Genesix.

**Frameworks:**

- **Seismology** — Tail risk detection using earthquake magnitude analogies (Gutenberg-Richter law)
- **LPPL Bubbles** — Log-Periodic Power Law model for bubble/crash detection
- **Criticality Phases** — Phase transition detection (order parameter, susceptibility)
- **Percolation Contagion** — Network-based contagion spread model (epidemic simulation)
- **Scaling Laws** — Power-law distributions, Hurst exponent, fractal dimension

---

## Tech Stack

| Layer      | Technology                                              |
| ---------- | ------------------------------------------------------- |
| Frontend   | React 18 + TypeScript + Vite                            |
| Charts     | Recharts (Line, Bar, Scatter, Pie, Area)                |
| State      | React Query (TanStack) with staleTime / refetchInterval |
| API Client | Axios with base URL `http://localhost:8000`             |
| Backend    | FastAPI (Python) on port 8000                           |
| ML Backend | scikit-learn, XGBoost, TensorFlow/Keras (LSTM)          |
| Data       | yfinance, MarketDataFetcher, Redis cache                |

---

## Design System

| Token        | Value          | Usage                                |
| ------------ | -------------- | ------------------------------------ |
| Gold         | `#D4AF37`      | Genesix accent, sidebar, branding    |
| Cyan         | `#00D9FF`      | Active tabs, links, secondary accent |
| Green        | `#10B981`      | Positive values, success states      |
| Red          | `#EF4444`      | Negative values, alerts, losses      |
| Purple       | `#A855F7`      | Advanced features, ML indicators     |
| Amber        | `#F59E0B`      | Warnings, intermediate states        |
| Background   | `#0A0E18`      | Main page background                 |
| Card BG      | `#131823`      | Card/tooltip background              |
| Text         | `#F1F5F9`      | Primary text                         |
| Muted        | `#94A3B8`      | Secondary text                       |
| Font (mono)  | JetBrains Mono | Numbers, tickers, code               |
| Font (sans)  | Inter          | Body text, labels                    |
| Font (brand) | Orbitron       | Logo, headings                       |

---

## Data Flow

```
User Action → React Component → useHook (React Query)
                                    ↓
                              API Layer (axios)
                                    ↓
                         FastAPI Backend (port 8000)
                                    ↓
                    Data Services (yfinance, Redis cache)
                                    ↓
                         Response → Transform → Render
                                    ↓
                    Fallback to demo data if backend offline
```

**Hooks** (from `src/hooks/useMarketData.ts`):

| Hook               | Endpoint                  | Refresh |
| ------------------ | ------------------------- | ------- |
| `useSnapshot()`    | `GET /api/v1/snapshot`    | 60s     |
| `useIndices()`     | `GET /api/v1/indices`     | 5min    |
| `useBonds()`       | `GET /api/v1/bonds`       | 1hr     |
| `useFX()`          | `GET /api/v1/fx-pairs`    | 5min    |
| `useCommodities()` | `GET /api/v1/commodities` | 5min    |
| `useMacro()`       | `GET /api/v1/macro`       | 1day    |
| `useHealth()`      | `GET /health`             | 30s     |

---

## Sidebar Navigation

The Genesix section appears in the sidebar with **gold (#D4AF37)** accent color and the **Ω** symbol.

```
GENESIX Ω
├── 🔍 Universe Search        /genesix/universe
├── 🔬 Advanced Screener      /genesix/screener
├── 🔬 Instrument Analysis    /genesix/instrument
├── Ω  Portfolio Omega        /genesix/portfolio
├── 🛡 Risk Engine            /genesix/risk
├── 📊 Backtesting            /genesix/backtest
├── 🧠 ML Engine              /genesix/ml
├── 📈 Advanced Analysis      /genesix/analysis
├── 👁 Market Intelligence    /genesix/intelligence
├── 📡 Portfolio Monitor      /genesix/monitor
├── 📶 Signal Intelligence    /genesix/signals
├── ⚙️ Data Layer              /genesix/data
└── ⚛️ Physics Lab             /genesix/physics
```

---

## Running

```bash
# Backend
cd montecarlo && python backend/run.py

# Frontend
cd ravinala-web && npm run dev

# Or use the launcher
./launch.bat
```

Backend runs at `http://localhost:8000`, frontend at `http://localhost:5173`.

All Genesix pages gracefully degrade to seeded demo data when the backend is unreachable.
