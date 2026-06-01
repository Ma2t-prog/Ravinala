# GENESIX Omega v2.1 — Professional Edition

## Implementation Plan (Phase 0+1, 4-6 weeks)

### 🎯 Vision

Transform Omega from a "toy allocator" (hardcoded tickers) to a **professional portfolio platform**:

- 60,000+ instrument universe (via OpenBB SDK)
- Multi-model optimization (MVO, Black-Litterman, Risk Parity ready)
- Institutional-grade risk analysis
- Real market data + live pricing
- Professional Streamlit UI (Quantum Dark design system)

---

## 📋 Module Breakdown

### MODULE 1: Universe Explorer

**Replaces "40 tickers hardcoded"**

#### 1.1 Data Infrastructure

- [ ] OpenBB SDK integration (ticker, ISIN, fundamentals, ESG)
- [ ] Local cache (SQLite) for universe metadata
- [ ] Price data pipeline (daily updates via OpenBB)
- [ ] Screener criteria database (P/E, P/B, dividend yield, volatility, etc.)

**Files to create:**

- `src/genesix/universe_explorer/data_pipeline.py` — OpenBB integration + caching
- `src/genesix/universe_explorer/screener_engine.py` — Filter logic
- `src/genesix/universe_explorer/cached_universe.db` — SQLite cache

#### 1.2 Instrument Search

- [ ] Global search bar (⌘K style in Streamlit sidebar)
- [ ] Auto-complete with preview (price, 30d sparkline)
- [ ] Search by: ticker, ISIN, name, sector, country

**File:**

- `src/pages/universe_search.py` — Streamlit page

#### 1.3 Screener

- [ ] Multi-criteria filter interface
- [ ] Pre-built screens (High Dividend, Growth, Value, Momentum, etc.)
- [ ] Custom screen builder (drag-and-drop style in Streamlit)
- [ ] Results: heatmap, filterable table, export CSV

**File:**

- `src/pages/universe_screener.py` — Streamlit page

#### 1.4 Instrument Detail

- [ ] Chart (candlestick + volume, TradingView Lightweight Charts via Streamlit-Lightweight-Charts)
- [ ] Fundamentals table (P/E, P/B, dividend yield, etc.)
- [ ] Risk metrics (volatility, max DD, beta)
- [ ] Peers comparison (same sector/industry)
- [ ] ESG score breakdown

**File:**

- `src/pages/instrument_detail.py` — Streamlit page with st.session_state for selected instrument

---

### MODULE 2: Portfolio Construction Engine

**Multi-model optimizer with real universe**

#### 2.1 Universe Selection

- [ ] Replace hardcoded tickers with dynamic universe selection
- [ ] User can search/screener → select N instruments (50-500 typical)
- [ ] Save selections as "sectors" or "custom universes"

#### 2.2 Optimization Models

Keep existing risk_matrix + scipy optimization, enhance:

- [ ] Mean-Variance (Markowitz) — Max Sharpe, Min Vol, Target Return
- [ ] Equal-Weight baseline
- [ ] Inverse Volatility (simple, robust)
- [ ] **Black-Litterman prep** (architecture ready, saisie views UI for Phase 2)

#### 2.3 Constraint Interface

- [ ] Min/max weights per instrument
- [ ] Sector constraints (max 25% Tech, etc.)
- [ ] Country constraints (min 30% Europe, etc.)
- [ ] Asset class constraints
- [ ] ESG floor (min ESG score)

**File:**

- Enhance `src/pages/genesix_home.py` with:
  - Universe selector (via Universe Explorer search)
  - Constraint builder (drag-drop style)
  - Multi-model selector
  - Output: efficient frontier + allocation table

#### 2.4 Outputs

- [ ] Allocation table (ticker, weight %, expected return, risk contribution)
- [ ] Efficient Frontier chart (with current portfolio marked)
- [ ] Comparison: Model A vs B vs equal-weight
- [ ] Export: CSV portfolio

---

### MODULE 3: Risk Engine

**Professional risk dashboard**

#### 3.1 Metrics Calculation

- [ ] Volatility (annualized + EWMA)
- [ ] Beta, correlation matrix
- [ ] VaR (parametric + historical)
- [ ] CVaR
- [ ] Max Drawdown + underwater chart
- [ ] Sharpe, Sortino, Calmar
- [ ] Factor decomposition (if data available)

**File:**

- `src/genesix/risk_engine/metrics.py` — Calculations
- Enhance `src/pages/genesix_risk_engine.py` — Dashboard

#### 3.2 Risk Dashboard

- [ ] Risk Summary bar (VaR, Max DD, Beta, Sharpe)
- [ ] Distribution chart (returns histogram + VaR lines)
- [ ] Underwater drawdown chart
- [ ] Correlation heatmap
- [ ] Stress test scenarios (2008, 2020 COVID, custom)

---

### MODULE 4: Performance & Analytics

**NAV tracking, backtesting stub**

#### 4.1 Performance Tracking

- [ ] Portfolio NAV calculation
- [ ] Buy-and-hold backtest (compare current allocation vs benchmark)
- [ ] Rolling returns (1m, 3m, 6m, 1y)
- [ ] Benchmark comparison

**File:**

- `src/genesix/performance_engine/tracker.py`
- Enhance `src/pages/genesix_portfolio_monitor.py`

#### 4.2 Backtesting Stub

- [ ] Load historical prices (past 5 years)
- [ ] Simulate portfolio from inception date
- [ ] Calculate Sharpe, max DD, rolling metrics
- [ ] Compare vs S&P 500, equal-weight

**File:**

- `src/pages/backtesting_page.py` (already exists, enhance)

---

## 🏗️ Architecture Changes

### Current State → Proposed

| Component        | Current                    | v2.1                                  |
| ---------------- | -------------------------- | ------------------------------------- |
| **Data Source**  | `risk_matrix.py` hardcoded | OpenBB SDK + SQLite cache             |
| **Universe**     | 40 tickers in code         | 60,000+ via OpenBB                    |
| **Optimization** | SciPy MVO only             | SciPy MVO + architecture for BL/RP    |
| **UI Theme**     | Gradients + emojis         | Quantum Dark (professional)           |
| **Navigation**   | Scattered pages            | Unified "GENESIX OMEGA" section       |
| **Data Models**  | Ad-hoc dicts               | Pydantic models (`genesix/models.py`) |

### Files to Create/Refactor

**New Modules:**

```
src/genesix/
├── universe_explorer/
│   ├── __init__.py
│   ├── data_pipeline.py      (OpenBB integration)
│   ├── screener_engine.py    (Filter logic)
│   └── models.py             (Instrument, Screen dataclasses)
├── portfolio_engine/
│   ├── __init__.py
│   ├── optimizer.py          (Enhanced MVO)
│   ├── constraints.py        (Constraint solver)
│   └── models.py             (Portfolio, Allocation dataclasses)
├── risk_engine/
│   ├── __init__.py
│   ├── metrics.py            (VaR, Sharpe, etc.)
│   ├── stress_tests.py       (Scenarios)
│   └── models.py
├── performance_engine/
│   ├── __init__.py
│   ├── tracker.py            (NAV, returns)
│   └── backtest.py           (Historical testing)
└── design_system/
    ├── __init__.py
    ├── themes.py             (Quantum Dark palette)
    └── components.py         (Streamlit custom widgets)
```

**New Pages:**

```
src/pages/
├── universe_search.py        (Instrument search)
├── universe_screener.py      (Multi-criteria filter)
├── instrument_detail.py      (Chart + fundamentals)
├── genesix_optimizer_new.py  (Enhanced v2.1 allocator)
└── [enhance existing]:
    ├── genesix_risk_engine.py
    ├── genesix_portfolio_monitor.py
    ├── backtesting_page.py
```

---

## 📊 Data Models (Pydantic)

```python
# src/genesix/models.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class Instrument(BaseModel):
    ticker: str
    isin: Optional[str]
    name: str
    asset_class: str  # 'equity', 'fixed_income', etc.
    sector: Optional[str]
    country: str
    exchange: str
    market_cap: Optional[float]
    price: float
    price_change_1d: float  # %
    dividend_yield: Optional[float]
    pe_ratio: Optional[float]
    volatility_1y: Optional[float]
    esg_score: Optional[float]
    beta: Optional[float]

class Portfolio(BaseModel):
    id: str
    name: str
    base_currency: str
    inception_date: datetime
    holdings: List['Holding']
    benchmark_id: Optional[str]

class Holding(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    weight: float  # %

class OptimizationResult(BaseModel):
    weights: dict  # ticker → weight
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    efficient_frontier: Optional[list]
    timestamp: datetime
```

---

## 🚀 Implementation Sequence

### Week 1: Foundation

- [ ] Install + test OpenBB SDK
- [ ] Create data_pipeline.py (fetch, cache universe)
- [ ] Create pydantic models
- [ ] Setup design system (Quantum Dark theme constants)

### Week 2: Universe Explorer

- [ ] Implement screener_engine.py
- [ ] Build universe_search.py page
- [ ] Build universe_screener.py page
- [ ] Build instrument_detail.py page

### Week 3-4: Enhanced Optimizer

- [ ] Refactor genesix_home.py to use dynamic universe
- [ ] Build constraint UI
- [ ] Enhance optimization (multi-model selector)
- [ ] Efficient Frontier chart

### Week 5: Risk Engine

- [ ] Implement risk_engine/metrics.py
- [ ] Enhance genesix_risk_engine.py dashboard
- [ ] Build stress test scenarios
- [ ] Correlation heatmap

### Week 6: Polish

- [ ] Performance tracker enhancements
- [ ] Navigation refactor (clean "GENESIX OMEGA" section)
- [ ] Professional design system applied consistently
- [ ] Testing + documentation

---

## 🎨 Design System: Quantum Dark (Streamlit)

```python
# src/genesix/design_system/themes.py

QUANTUM_DARK = {
    # Backgrounds
    "bg_0": "#08080C",     # Main background
    "bg_1": "#0E0E14",     # Cards/panels
    "bg_2": "#14141C",     # Elevated surfaces
    "bg_3": "#1A1A24",     # Hover/inputs

    # Text
    "text_0": "#F0F0F5",   # Primary text
    "text_1": "#B8B8C8",   # Secondary text
    "text_2": "#7878A0",   # Tertiary text

    # Accents
    "accent_positive": "#00E676",   # Green (gains)
    "accent_negative": "#FF5252",   # Red (losses)
    "accent_primary": "#448AFF",    # Blue (primary actions)
    "accent_warning": "#FFD740",    # Yellow (alerts)
    "accent_premium": "#D4AF37",    # Gold (GENESIX branding)

    # Semantic
    "border_subtle": "rgba(255, 255, 255, 0.06)",
    "surface_hover": "rgba(255, 255, 255, 0.05)",
}

# Apply in Streamlit config:
# streamlit run src/app.py --theme.primaryColor="#448AFF" --theme.backgroundColor="#08080C" ...
```

---

## 📈 Success Metrics (v2.1)

✅ **Universe Explorer works:** Search 60,000+ instruments, screener returns results in <2s
✅ **Real data:** Live AAPL, MSFT, SPY prices updated daily via OpenBB
✅ **Optimization:** Select custom universe (e.g., "Tech ETFs") → allocate (not hardcoded)
✅ **Risk dashboard:** VaR, correlation heatmap, stress tests render correctly
✅ **Professional feel:** Quantum Dark theme applied, no emojis, monospace for prices
✅ **Performance:** Dashboard loads in <3s even with 500-instrument universe

---

## 📝 Next Steps (Post-Implementation)

**Phase 1 features (not in v2.1):**

- Black-Litterman with views UI
- Risk Parity, HRP optimization
- Tax-Loss Harvesting integration
- Multi-portfolio management
- PDF reporting

**Eventual (Phases 2-4):**

- MongoDB for portfolio history
- WebSocket for live alerts
- Factor model integration
- Broker API connections (IB, Alpaca)
- Institutional compliance engine

---

## 🔗 Dependencies

```python
# requirements.txt additions
openbb              # Market data aggregator
pyportfolio-opt     # Portfolio optimization algorithms (prep for BL/RP)
yfinance            # Fallback for prices (OpenBB uses it too)
plotly              # Charts
streamlit           # UI framework
pydantic            # Data validation
pandas              # Tabular data
numpy               # Numerical computing
scipy               # Scientific computing
```

---

## 📊 Completion Checklist

By end of v2.1:

- [ ] Universe Explorer fully functional
- [ ] 60,000+ instrument universe searchable
- [ ] Portfolio optimizer works with dynamic universe
- [ ] Risk engine calculates all key metrics
- [ ] Streamlit app styled with Quantum Dark
- [ ] Performance benchmark (S&P 500) works
- [ ] All pages integrated, no broken imports
- [ ] Documentation: module README per component
- [ ] Example workflows documented
