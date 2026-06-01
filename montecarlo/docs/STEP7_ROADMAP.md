# GenesiX Step 7: V2 Evolution — Implementation Roadmap

**Status**: In Progress

---

## Overview

Step 7 upgrades GenesiX from v1 (7 pages) to v2 (11 pages) with:

- **Part A**: Bloomberg-grade UI overhaul (DONE: theme_v2.py created)
- **Part B**: Portfolio Optimizer AI (IN PROGRESS)
- **Part C**: Visual Backtesting Engine (IN PROGRESS)
- **Part D**: Multi-Criteria Screener (IN PROGRESS)
- **Part E**: Social Trading & Leaderboard (TO DO)
- **Part F**: Navigation update (TO DO)

---

## File Creation Progress

### Part A: UI Overhaul ✅

- [x] `src/genesix/dashboard/theme_v2.py` — Comprehensive Bloomberg theme system
  - Color system (64 colors across 8 categories)
  - Global CSS with Streamlit overrides
  - HTML component builders (market_status_bar, metric_card, data_table, sparklines, alert_banner)
  - Plotly template with Bloomberg conventions

**Action**: Replace `theme.py` with `theme_v2.py` content in next commit.

---

### Part B: Portfolio Optimizer AI

**Files to Create**:

1. `src/genesix/optimizer/__init__.py` (exports)
2. `src/genesix/optimizer/optimizer.py` (500+ lines)
   - PortfolioOptimizer class
   - Methods: optimize(), optimize_with_views(), suggest_improvements()
   - Algorithms: max_sharpe, min_variance, max_return, risk_parity, black_litterman
   - Constraints: min/max weights, asset class bounds, target vol, max DD, no shorts
3. `src/genesix/dashboard/optimizer.py` (300+ lines)
   - Page layout: asset selector, constraints panel, objective picker
   - Visualizations: efficient frontier chart, weights table, comparison bar chart
   - Improvement suggestions display

**Key Classes**:

- `PortfolioOptimizer`: Core optimization engine
  - `optimize()` → optimized weights dict + metrics + efficient frontier
  - `optimize_with_views()` → Black-Litterman incorporation of user views
  - `suggest_improvements()` → AI recommendations for portfolio enhancement

---

### Part C: Visual Backtesting Engine

**Files to Create**:

1. `src/genesix/backtester/__init__.py` (exports)
2. `src/genesix/backtester/engine.py` (600+ lines)
   - BacktestEngine class
   - Methods: run_backtest(), run_dca_comparison(), run_strategy_backtest()
   - Strategies: buy_and_hold, rebalancing, DCA, momentum, mean_reversion, volatility_targeting
   - Realistic costs: transaction costs, slippage, fees, tax drag
3. `src/genesix/dashboard/backtester.py` (350+ lines)
   - Configuration panel: portfolio setup, date range, options
   - Equity curve chart (portfolio vs benchmark, log scale)
   - Key metrics cards: total return, annual return, sharpe, max DD, win rate, alpha
   - Monthly returns heatmap, drawdown underwater chart, rolling metrics

**Key Classes**:

- `BacktestEngine`: Backtesting simulation
  - `run_backtest()` → equity_curve, returns, metrics, trades_log
  - `run_dca_comparison()` → DCA vs lump sum comparison
  - `run_strategy_backtest()` → test systematic strategies

---

### Part D: Multi-Criteria Screener

**Files Created/To Create**:

1. [x] `src/genesix/screener/__init__.py` (exports)
2. [x] `src/genesix/screener/screener.py` (350+ lines) — AssetScreener class
   - Methods: screen(), prebuilt_screen(), rank_assets(), compare_assets()
   - Prebuilt screens: undervalued_momentum, safe_haven, high_conviction, income_generator, momentum, contrarian
   - Rating system: strong_buy → strong_sell
3. [ ] `src/genesix/dashboard/screener.py` (300+ lines)
   - Quick screen buttons, custom filter builder
   - Results table (sortable, color-coded, clickable)
   - Comparison mode (2-5 assets side by side)

**Key Classes**:

- `AssetScreener`: Multi-criteria screening engine
  - `screen()` → filtered/ranked DataFrame of assets
  - `prebuilt_screen()` → run named screens
  - `rank_assets()` → multi-factor ranking with composite scores
  - `compare_assets()` → side-by-side comparison

---

### Part E: Social Trading & Leaderboard

**Files to Create**:

1. `src/genesix/social/__init__.py` (exports)
2. `src/genesix/social/portfolio_sharing.py` (400+ lines)
   - PortfolioManager class
   - Methods: save_portfolio(), load_portfolio(), track_performance(), leaderboard()
   - Storage: local JSON/SQLite (v2), upgradeable to API backend
   - Privacyimpl: anonymous by default, public opt-in
3. `src/genesix/dashboard/social.py` (350+ lines)
   - Tab strip: My Portfolios | Leaderboard | Explore
   - My Portfolios: grid of cards with sparklines
   - Leaderboard: period selector, ranked table (top 3 highlighted)
   - Explore: filter by asset class/risk/return

**Key Classes**:

- `PortfolioManager`: Portfolio persistence + leaderboard
  - `save_portfolio()` → unique portfolio ID
  - `track_performance()` → historical real performance
  - `leaderboard()` → top performers by period
  - `clone_portfolio()` → reuse public portfolios

---

### Part F: Navigation Update

**File to Update**:

- `src/genesix/app.py` (main navigation/routing)

**New Navigation Tree**:

```
🧬 GenesiX — Risk Intelligence
├── 📊 Market Pulse
├── 🔍 Deep Analysis
├── 💰 Portfolio Simulator
├── 🎯 Optimizer AI          ← NEW
├── 📈 Backtester            ← NEW
├── 🔎 Screener              ← NEW
├── ⚡ Stress Lab
├── 🤖 ML Predictions
├── 🌐 Macro Radar
├── 🔔 Alert Center
└── 🏆 Social / Leaderboard  ← NEW
```

---

## Implementation Order

1. **✅ Part A: Theme** — Foundation for all UI
2. **🔄 Part D: Screener** — Quickest, immediate value
3. **⏳ Part C: Backtester** — Medium complexity
4. **⏳ Part B: Optimizer** — Complex algorithms
5. **⏳ Part E: Social** — Depends on everything being polished
6. **⏳ Part F: Navigation** — Last, integrate everything

---

## Code Style Requirements

All new code MUST follow these rules:

1. **Type hints everywhere** — `def screen(self, universe: list[str] | None = None) -> pd.DataFrame:`
2. **Docstrings** — Google-style with Args, Returns, Raises
3. **Error handling** — Try/except with logging, never silent failures
4. **Performance** — All operations < 60s (cached where needed)
5. **Testing** — Each new feature tested in `tests/genesix/`

---

## Testing Strategy

For each feature:

1. Unit tests for core algorithms (optimization, backtesting, screening)
2. Integration tests with real data
3. Dashboard page manual smoke test
4. Performance benchmarks (< 10s load time)

---

## Deployment Checklist

Before v2.0 release:

- [ ] All 4 features implemented and tested
- [ ] All 11 dashboard pages have market status bar + alert banner
- [ ] All numbers in monospace font
- [ ] All tables are Bloomberg-grid style
- [ ] All charts use genesix template
- [ ] Sparklines on all KPIs with history
- [ ] Loading states show skeleton shimmer
- [ ] Keyboard shortcuts documented (? to toggle help)
- [ ] README updated with v2 features
- [ ] Performance < 120s for full pipeline

---

## Token Budget Tracking

**Created so far**:

- theme_v2.py: ~800 lines
- screener.py: ~350 lines
- directories: screener/, backtester/, optimizer/

**Still to create** (estimate):

- backtester/engine.py: 600 lines
- optimizer/optimizer.py: 500 lines
- social/portfolio_sharing.py: 400 lines
- 6 dashboard pages: 1,800 lines
- **init**.py files: 100 lines
- tests: 800 lines
- **Total remaining**: ~5,000 lines

**Strategy**: Create core engines first, then dashboard pages, prioritizing by value to user.
