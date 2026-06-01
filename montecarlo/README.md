# Ravinala — Cross-Asset Quantum Structuring Lab

**Professional-Grade Platform for Pricing, Structuring & Risk Management of Derivatives**

Version 2.0 | Built by TSIVAHINY Matthias | © 2026

---

## Overview

**Ravinala** is a full-stack derivatives platform combining a **Streamlit dashboard** (frontend) and a **FastAPI backend** with real-time market data, caching, and export capabilities.

| Layer    | Technology                   | Purpose                              |
| -------- | ---------------------------- | ------------------------------------ |
| Frontend | Streamlit + Plotly           | Interactive pricing & risk dashboard |
| Backend  | FastAPI + Redis              | Real-time data API with caching      |
| Engine   | NumPy / SciPy / scikit-learn | Pricing, Greeks, ML, calibration     |

---

## Features

### Pricing & Structuring

- European & Exotic Options — Black-Scholes and Monte Carlo
- Complex Derivatives — Autocalls, Coupons, Barriers, Multi-Asset Baskets
- Exotic Payoffs — Himalaya, Phoenix, Athena, Cliquet, Variance Swaps, Convertible Bonds, CLNs

### Risk & Analytics

- Greeks (Delta, Gamma, Vega, Theta, Rho, Vanna, Volga)
- VaR (Historical & Parametric), CVaR, Stress Testing, Greeks Decomposition
- Backtesting — Model Validation, Strategy P&L, VaR Testing, Greeks Accuracy

### Calibration & ML

- Implied Vol Smile, SABR Model, Term Structure, EWMA/GARCH Forecasting
- ML Pricing — Gradient Boosting, Batch Pricing, Anomaly Detection, Model Comparison

### Hedging

- Delta Hedging Simulator, Rehedge Optimization, P&L Attribution

### Backend API

- REST endpoints for real-time market data (indices, FX, bonds, commodities, macro)
- Redis caching with section-specific TTLs
- Multi-source data fetching (yfinance, FRED, CoinGecko, World Bank)
- Excel/PDF export, health checks & monitoring

---

## Installation

### Quick Start (Windows)

```batch
git clone https://github.com/zetaxelor/ravinala.git
cd ravinala
install.bat
ravinala
```

### Quick Start (macOS & Linux)

```bash
git clone https://github.com/zetaxelor/ravinala.git
cd ravinala
chmod +x install.sh && ./install.sh
./ravinala_run.sh
```

### Manual Installation

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# or
.venv\Scripts\activate.ps1       # Windows PowerShell

pip install -e .
ravinala
```

### System Requirements

- **Python**: 3.10+
- **Memory**: 4GB minimum (8GB recommended)
- **Disk**: 500MB
- **OS**: Windows 10+, macOS 10.14+, Ubuntu 20.04+

---

## Usage

### Launch the Dashboard

```bash
ravinala                          # After installation
python -m ravinala                # Python module
streamlit run src/app.py          # Dev mode
```

Opens at `http://localhost:8501`

### Dashboard Tabs

| Tab                   | Description                                       |
| --------------------- | ------------------------------------------------- |
| Pricing Center        | Vanilla options & Greeks                          |
| The Sandbox           | Multi-asset structures with Monte Carlo           |
| Custom Product Pricer | Build your own payoffs                            |
| Museum of Exotics     | Himalaya, Everest, and more                       |
| Macro Analysis        | Rate shocks & scenario analysis                   |
| Risk Management       | VaR, stress testing, Greeks decomposition         |
| Backtesting           | Model validation, strategy P&L, Greeks accuracy   |
| Vol Calibration       | Smile fitting, SABR, term structure, forecasting  |
| ML Pricing            | Training, batch prediction, anomaly detection     |
| Hedging               | Delta hedging simulator, rehedge optimization     |
| Advanced Exotics      | Cliquets, Variance Swaps, Convertible Bonds, CLNs |
| Learn & Legal         | Educational content, disclaimers, mathematics     |
| **GenesiX**           | **Risk Intelligence Engine (see below)**          |

---

## GenesiX — Risk Intelligence Engine

GenesiX is an integrated AI-powered risk module that combines alternative data, machine learning, and quantitative finance to provide portfolio risk analysis and predictions. It answers: **"If I invest €100 today, what can I expect?"**

### GenesiX Features

**7 Dashboard Pages:**

1. **Market Pulse** — Global market overview
   - Fear & Greed Index (VIX, breadth, sentiment)
   - Real-time correlation heatmap
   - Top movers & sector rotation
   - News sentiment by asset class

2. **Portfolio Simulator** — Interactive portfolio analysis
   - Enter assets and weights
   - See 5 probability-weighted scenarios (Crash/Bear/Base/Bull/Extreme)
   - Risk metrics: VaR, CVaR, volatility, Sharpe ratio
   - Investment cones (confidence interval bands)

3. **Deep Analysis** — Single-asset dive
   - Technical & macro sensitivity
   - Drawdown history & recovery time
   - Peer comparison (correlation, beta)
   - Event impact analysis

4. **Stress Lab** — Custom stress testing
   - 8 historical scenarios (COVID, 2008 GFC, dot-com, ++
   - Custom shock parameters (equity -%, bonds +bps, vol Δ)
   - Impact tables: portfolio P&L, sector breakdown

5. **ML Predictions** — Ensemble forecast
   - 3-model ensemble: XGBoost, LightGBM, Random Forest
   - Walk-forward backtesting (no lookahead bias)
   - SHAP explainability (top drivers)
   - Confidence scores & directional accuracy

6. **Macro Radar** — Economic tracking
   - US yield curve (real-time)
   - Economic calendar alerts
   - Inflation, unemployment, growth
   - Global PMI & macro surprises

7. **Alert Center** — Anomaly system
   - Composite alert level: GREEN → BLACK
   - Volatility regime, trend, liquidity, correlation
   - Actionable alerts with context

### Data Sources & Coverage

| Source        | Data                                        | No API Key? |
| ------------- | ------------------------------------------- | ----------- |
| yfinance      | Equities, Crypto, FX, Commodities (delayed) | ✓           |
| FRED          | US macro (rates, CPI, unemployment)         | Free key    |
| World Bank    | Global macro, development indicators        | ✓           |
| Open-Meteo    | 7-day weather (agricultural impact)         | ✓           |
| Google Trends | Search interest (momentum)                  | ✓           |
| CoinGecko     | Crypto ecosystem data                       | ✓           |
| Yahoo Finance | News headlines (no key)                     | ✓           |
| Alpha Vantage | FX intraday (optional)                      | Free tier   |
| News API      | News sentiment (optional)                   | Free tier   |

### Risk Methodologies

**VaR (Value at Risk):**

- Historical simulation
- Parametric (normal distribution)
- Cornish-Fisher expansion (skew/kurtosis)
- Monte Carlo simulation

**Anomaly Detection:**

- Volatility regimes (EWMA clustering)
- Trend detection (momentum + MA)
- Bubble scoring (Shiller P/E equivalent)
- Correlation breakdown alerts

**ML Predictions:**

- 3-model ensemble with inverse MSE weighting
- A/B tested walk-forward validation
- Bootstrap confidence intervals
- 48-58% directional accuracy on test set

### Quick Start with GenesiX

```bash
# Install GenesiX dependencies
pip install -e ".[genesix]"

# Launch Ravinala
ravinala

# Navigate to GenesiX tab in sidebar
# Portfolio Simulator → Add SPY + TLT + GC=F → Click Analyze
```

For full ML capabilities (LSTM):

```bash
pip install -e ".[genesix-full]"
```

### Configuration

Optional: Set environment variables in `.env`:

```env
FRED_API_KEY=your_fred_key
ALPHA_VANTAGE_KEY=your_alpha_vantage_key
NEWSAPI_KEY=your_news_api_key
```

GenesiX works without these keys — it falls back to free sources (yfinance, World Bank, Open-Meteo, Google Trends).

### Performance & Caching

| Operation                    | Time  | Cache TTL |
| ---------------------------- | ----- | --------- |
| Fetch market data            | <5s   | 5 min     |
| Build feature matrix         | <30s  | 6 hours   |
| Risk analytics (VaR, stress) | <5s   | 6 hours   |
| ML ensemble training         | <120s | 24 hours  |
| ML prediction                | <3s   | 2 hours   |
| Anomaly detection            | <2s   | 1 hour    |
| PDF export                   | <10s  | —         |
| Excel export                 | <5s   | —         |

All results cached intelligently — cold starts fast, warm starts instant.

### Exports & Reporting

**PDF Report:**

- Cover page with alert level
- Executive summary (key metrics, concerns)
- Portfolio composition (weighted table)
- Risk analysis (VaR, CVaR, drawdown)
- Scenario analysis (5 outcomes)
- Recommendations (6 actionable items)
- Methodology & disclaimer

**Excel Workbook (Multi-sheet):**

- Summary (key metrics)
- Scenarios (probability × outcomes)
- Risk Metrics (VaR/CVaR by horizon)
- Portfolio (weights & amounts)
- Raw Data (JSON export)

Downloads available directly from Portfolio Simulator page.

---

### Launch the Backend API

```bash
cd backend

# Optional: start Redis for persistent caching
docker run -d -p 6379:6379 redis:alpine   # or skip — falls back to in-memory cache

# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend available at:

- **API**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`
- **Health**: `http://localhost:8000/health`

---

## Backend API

### Endpoints

```bash
# Full snapshot
GET /api/v1/snapshot
GET /api/v1/snapshot?sections=indices,bonds,fx

# By section
GET /api/v1/indices?zones=americas,asia&limit=30
GET /api/v1/bonds?countries=USA,EUR,JPY&maturities=2Y,5Y,10Y
GET /api/v1/fx-pairs?base=USD&limit=20
GET /api/v1/commodities?categories=metals,energy,crypto
GET /api/v1/macro?countries=USA,China

# Exports
POST /api/v1/export/excel
POST /api/v1/export/pdf

# Cache control
POST /api/v1/refresh?section=indices
POST /api/v1/refresh

# Health
GET /health
```

### Caching Strategy

| Section       | TTL    | Volatility |
| ------------- | ------ | ---------- |
| Indices       | 5 min  | High       |
| FX            | 5 min  | High       |
| Commodities   | 5 min  | High       |
| Bonds         | 1 hour | Medium     |
| Macro         | 1 day  | Low        |
| Full Snapshot | 15 min | Medium     |

### Data Sources

- **Real-time** — yfinance (indices, FX, commodities), CoinGecko (crypto)
- **EOD** — World Bank API, FRED API (macro)

### Frontend Integration

```python
import httpx

async def fetch_dashboard_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/v1/snapshot")
        return response.json()
```

### Backend Configuration

Create a `.env` file in `backend/`:

```env
REDIS_URL=redis://localhost:6379/0
FRED_API_KEY=your_key_here
ALPHA_VANTAGE_KEY=your_key_here
NEWSAPI_KEY=your_key_here
```

---

## Python API

```python
from ravinala.engine import BlackScholesGreeks, MultiAssetPricer, ZeroCouponBond
from ravinala.payoffs import PayoffLibrary
import numpy as np

# Black-Scholes pricing & Greeks
bs = BlackScholesGreeks()
price = bs.call_price(S=100, K=105, T=1.0, r=0.05, b=0.05, sigma=0.2)
delta = bs.delta(S=100, K=105, T=1.0, r=0.05, b=0.05, sigma=0.2, option_type='call')
gamma = bs.gamma(S=100, K=105, T=1.0, r=0.05, b=0.05, sigma=0.2)
vega  = bs.vega(S=100, K=105, T=1.0, r=0.05, b=0.05, sigma=0.2)

# Multi-asset Monte Carlo
mc = MultiAssetPricer(n_simulations=10000, random_seed=42)
spots = np.array([100, 95, 105])
vols  = np.array([0.20, 0.22, 0.18])
corr  = np.array([[1.0, 0.5, 0.3],
                  [0.5, 1.0, 0.4],
                  [0.3, 0.4, 1.0]])

paths = mc.simulate_paths(spots, np.full(3, 0.05), vols, T=2.0,
                          n_steps=252, correlation_matrix=corr)

# Zero-Coupon Bond pricing
zcb_price = ZeroCouponBond.price(notional=100, maturity=2.0, rate=0.05, credit_spread=0.01)
option_budget = 100 - zcb_price
```

---

## Project Structure

```
ravinala/
├── src/
│   ├── app.py                # Main Streamlit application
│   ├── engine.py             # Black-Scholes, MC, Greeks, ZCB pricing
│   ├── payoffs.py            # Exotic payoff library & builder
│   ├── risk.py               # VaR, stress testing, Greeks decomposition
│   ├── backtesting.py        # Model validation, strategy P&L
│   ├── calibration.py        # Vol surfaces, SABR, EWMA/GARCH
│   ├── ml_pricing.py         # ML predictor, anomaly detection
│   ├── hedging.py            # Delta hedging, P&L attribution
│   ├── exotics_advanced.py   # Cliquet, Variance Swaps, CLNs, etc.
│   ├── options.py            # Call & Put option classes
│   ├── pricing.py            # BlackScholes & MonteCarlo classes
│   ├── utils.py              # Utility functions
│   ├── cli.py                # Command-line launcher
│   └── __main__.py           # CLI entry point
├── backend/
│   └── app/
│       ├── main.py           # FastAPI app + endpoints
│       ├── models.py         # Pydantic models
│       └── services/
│           ├── cache.py      # Redis caching layer
│           └── data_fetcher.py  # Data collection service
├── tests/
│   └── test_pricing.py       # 13+ unit tests
├── install.bat               # Windows installer
├── install.sh                # Linux/macOS installer
├── pyproject.toml            # Package configuration
└── README.md
```

---

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html
```

**Status**: 13/13 tests passing

---

## Performance

| Operation                          | Time    |
| ---------------------------------- | ------- |
| Black-Scholes pricing              | < 1ms   |
| Greeks calculation                 | < 1ms   |
| Monte Carlo (10k paths, 252 steps) | ~250ms  |
| API response (cache hit)           | < 100ms |
| API response (cache miss)          | < 500ms |
| PDF generation                     | < 3s    |
| App startup                        | ~3-5s   |

---

## Troubleshooting

**`ravinala` command not found**

```bash
pip install -e .
python -m ravinala
```

**Port 8501 already in use**

```bash
streamlit run src/app.py --server.port 8502
```

**Module import errors**

```bash
pip install -e . --force-reinstall
```

**Backend: Redis not connecting**
The backend falls back to in-memory cache automatically — Redis is optional.

---

## Legal

> This application is **for educational and research purposes only**. It is NOT financial advice.
> See the **Learn & Legal** tab in the app for full disclaimers.

**Ravinala** is proprietary software. © 2026 TSIVAHINY Matthias. All Rights Reserved.

---

## Contact

- **Email**: info@ravinala.io
- **Website**: https://ravinala.io
- **Repository**: https://github.com/zetaxelor/ravinala

---

_Built with Python · Streamlit · FastAPI · NumPy · SciPy · Redis_
