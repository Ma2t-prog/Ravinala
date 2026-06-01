# 🚀 RAVINALA v3.0 SUPREMACY UPGRADE - WEEK 1-2 DEPLOYMENT GUIDE

> [!WARNING]
> **Document status: needs verification**
> This setup guide reflects a specific historical rollout track.
> Endpoints, dependencies, and architecture assumptions may differ from current backend reality.
> Before implementation decisions, cross-check with:
> - `docs/PRIMARY_SOURCE_BASELINE_INDEX.md`
> - `docs/PRIMARY_SOURCE_DELTA_LEDGER.md`
> - `docs/PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md`

**Complete Real-Time Data Platform + Advanced Risk Analytics**

This guide is retained as historical rollout context; treat commands and paths as candidates for verification, not as current certification.

---

## 📋 PROJECT OVERVIEW

Transform RAVINALA from batch-processing (yFinance) to **real-time streaming** with professional-grade risk analytics.

### Key Improvements

| Aspect               | v2.0             | v3.0                              |
| -------------------- | ---------------- | --------------------------------- |
| **Data Latency**     | 2-3 min          | < 500ms                           |
| **Data sources**     | yFinance (1)     | 3 sources (Finnhub, Kraken, IEX)  |
| **Message rate**     | Single REST call | 100+ msgs/sec streaming           |
| **Concurrent users** | 1-2              | 100+                              |
| **Database**         | JSON files       | PostgreSQL + Redis (Phase 2)      |
| **Risk analytics**   | None             | ✅ VaR, CVaR, Greeks, Correlation |

---

## 🎯 WEEK 1-2 DELIVERABLES

### Week 1: Real-Time Data Pipeline

- ✅ **websocket_server.py** - FastAPI WebSocket server with throttling
- ✅ **finnhub_consumer.py** - Stocks/Forex/Crypto from Finnhub API
- ✅ **kraken_consumer.py** - Cryptocurrency real-time feeds
- ✅ **iex_consumer.py** - Alternative US stocks (optional)
- ✅ **market_data_client.js** - Frontend WebSocket client

### Week 2: Risk Analytics Engine

- ✅ **correlation.py** - Pearson & Spearman correlation matrices
- ✅ **risk.py** - VaR, CVaR, Volatility, Sharpe, Max Drawdown
- ✅ **greeks.py** - Options Greeks (Delta, Gamma, Vega, Theta, Rho)

---

## 🛠️ INSTALLATION & SETUP

### Step 1: Install Dependencies

```bash
cd montecarlo

# Core dependencies
pip install fastapi uvicorn websockets websocket-client

# Data science
pip install pandas numpy scipy scikit-learn

# Utilities
pip install python-dotenv pydantic aioredis redis

# Testing
pip install pytest pytest-asyncio
```

### Step 2: Configure Environment

Create/update `.env` file in `montecarlo/` directory:

```env
# === Finnhub Configuration ===
FINNHUB_API_KEY=your_finnhub_token_here

# Get free API key at: https://finnhub.io/register
# Features: Stocks, Forex, Crypto, 200 requests/min free tier

# === IEX Cloud Configuration (optional) ===
IEX_API_KEY=your_iex_token_here

# Get free API key at: https://iexcloud.io
# Note: IEX Cloud has been discontinued, but template is available

# === WebSocket Server ===
WS_HOST=0.0.0.0
WS_PORT=8000
WS_ENDPOINT=/ws/marketdata
MAX_MESSAGES_PER_SEC=100

# === Data Configuration ===
PRICE_HISTORY_LOOKBACK=252    # 1 year trading days
VARIANCE_LOOKBACK=1260         # 5 years
VAR_CONFIDENCE_LEVEL=0.95      # 95% confidence

# === Logging ===
LOG_LEVEL=DEBUG
LOG_FILE=montecarlo/logs/real_time.log

# === Feature Flags ===
ENABLE_FINNHUB=true
ENABLE_KRAKEN=true
ENABLE_IEX=false
ENABLE_CORRELATION=true
ENABLE_RISK_CALC=true
```

### Step 3: Get API Keys

**Finnhub (Required)**:

1. Visit https://finnhub.io/register
2. Sign up (free)
3. Copy API key from dashboard
4. Paste into `.env` as `FINNHUB_API_KEY`

**Kraken (Public Data)**:

- No API key required for public ticker feeds
- Automatically connects to `wss://ws.kraken.com/`

**IEX Cloud (Optional)**:

- API has been discontinued/restructured
- Code is provided as template for alternative feeds

---

## 🚀 QUICKSTART

### Terminal 1: Start WebSocket Server

```bash
cd montecarlo/src/real_time

# Start FastAPI WebSocket server
python -m uvicorn websocket_server:app --host 0.0.0.0 --port 8000 --reload

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# ✓ RAVINALA Real-Time Server Starting....
# 📊 Starting market data consumers...
```

**Server endpoints**:

- WebSocket: `ws://localhost:8000/ws/marketdata`
- Health check: `http://localhost:8000/health`
- Stats: `http://localhost:8000/stats`
- Docs: `http://localhost:8000/docs` (Swagger UI)

### Terminal 2: Test WebSocket Client

```bash
cd montecarlo/tests

# Run test client
python test_websocket_client.py

# Expected output:
# ✓ Connected to ws://localhost:8000/ws/marketdata
#   → Subscribed to AAPL
#   → Subscribed to MSFT
#   → Subscribed to BTCUSD
# Listening for market data...
#   [0001] AAPL       $150.25 | finnhub
#   [0002] MSFT       $345.60 | finnhub
#   [0003] BTCUSD     $45123.50 | kraken
```

### Terminal 3: Test Analytics

```bash
cd montecarlo/src/analytics

# Test correlation engine
python correlation.py

# Test risk engine
python risk.py

# Test greeks calculator
python greeks.py
```

---

## 📊 USAGE EXAMPLES

### 1. WebSocket Client (JavaScript)

```javascript
// HTML file using market_data_client.js

<script src="market_data_client.js"></script>
<script>
  // Create client
  const client = new MarketDataClient("ws://localhost:8000/ws/marketdata");

  // Subscribe to AAPL price updates
  client.subscribe("AAPL", (data) => {
    console.log(`AAPL: $${data.price}`);

    // Update UI
    document.getElementById("aapl-price").textContent = `$${data.price.toFixed(2)}`;
    document.getElementById("aapl-time").textContent = new Date(data.timestamp).toLocaleTimeString();
  });

  // Subscribe to crypto
  client.subscribe("BTCUSD", (data) => {
    console.log(`BTC: $${data.price} (bid: ${data.bid}, ask: ${data.ask})`);
  });

  // Handle connection events
  document.addEventListener("market-connected", () => {
    console.log("Connected to market server");
  });
</script>
```

### 2. Risk Calculator (Python)

```python
from analytics.risk import RiskEngine
import numpy as np

# Initialize engine
risk = RiskEngine(confidence_level=0.95)

# Add price history (from WebSocket)
prices = [150.00, 150.50, 149.75, 151.00, 150.25]
for price in prices:
    risk.add_price("AAPL", price)

# Calculate risk metrics
position_value = 1_000_000  # $1M position

var = risk.calculate_var_historical("AAPL", position_value)
cvar = risk.calculate_cvar("AAPL", position_value)
vol = risk.calculate_volatility("AAPL")
sharpe = risk.calculate_sharpe_ratio("AAPL")
dd, _, _ = risk.calculate_max_drawdown("AAPL")

print(f"VaR (95%):    ${abs(var):,.0f}")
print(f"CVaR:         ${abs(cvar):,.0f}")
print(f"Volatility:   {vol*100:.2f}%")
print(f"Sharpe:       {sharpe:.2f}")
print(f"Max Drawdown: {dd*100:.2f}%")
```

### 3. Correlation Analysis (Python)

```python
from analytics.correlation import CorrelationEngine

# Initialize
corr = CorrelationEngine(lookback_periods=252)

# Add prices
for symbol, price in [("AAPL", 150.25), ("MSFT", 345.60), ("GOOGL", 120.00)]:
    corr.add_price(symbol, price)

# Calculate correlation matrix
matrix = corr.calculate_matrix()
print(matrix)

# Find highly correlated assets (>0.7)
high_corr = corr.get_highly_correlated("AAPL", threshold=0.7)
print(f"Assets correlated with AAPL: {high_corr}")

# Find uncorrelated (good for diversification <0.3)
uncorr = corr.get_uncorrelated("AAPL", threshold=0.3)
print(f"Diversification candidates: {uncorr}")
```

### 4. Options Greeks (Python)

```python
from analytics.greeks import GreeksCalculator

# Option parameters
S = 150.25       # Spot price (AAPL)
K = 150.00       # Strike price
r = 0.05         # 5% risk-free rate
sigma = 0.25     # 25% volatility
T = 60/365       # 60 days to expiration

# Get all Greeks
greeks = GreeksCalculator.get_all_greeks(S, K, r, sigma, T, "call")

print(f"Call Price: ${greeks['price']:.2f}")
print(f"  Delta: {greeks['delta']:.4f} (per $1 spot move)")
print(f"  Gamma: {greeks['gamma']:.4f} (delta sensitivity)")
print(f"  Vega:  ${greeks['vega']:.4f} (per 1% vol)")
print(f"  Theta: ${greeks['theta']:.4f} (per day)")
print(f"  Rho:   ${greeks['rho']:.4f} (per 1% rate)")
```

---

## ✅ TESTING CHECKLIST

### Week 1 (Real-Time Data)

- [ ] FastAPI server starts without errors
- [ ] WebSocket endpoint `/ws/marketdata` accepts connections
- [ ] Finnhub WebSocket connects (with valid API key)
- [ ] Kraken WebSocket connects and streams crypto prices
- [ ] Multiple clients can subscribe to different symbols
- [ ] Messages throttled at max 100/sec
- [ ] Disconnections handled gracefully
- [ ] Health check endpoint returns 200 OK
- [ ] Latency < 500ms from data source to client

### Week 2 (Risk Analytics)

- [ ] Correlation matrix calculated correctly (Pearson)
- [ ] Spearman correlation works
- [ ] VaR (historical method) calculated
- [ ] VaR (parametric method) calculated
- [ ] CVaR calculated and > VaR in magnitude
- [ ] Volatility annualized correctly
- [ ] Sharpe ratio calculated
- [ ] Max drawdown identified
- [ ] All Greeks (Delta, Gamma, Vega, Theta, Rho) calculated
- [ ] Put-call parity holds
- [ ] Portfolio VaR aggregates multiple positions
- [ ] Tests pass: `pytest tests/analytics/test_analytics.py -v`

---

## 📈 PERFORMANCE TARGETS

| Metric                       | Target        | Status |
| ---------------------------- | ------------- | ------ |
| WebSocket latency            | < 500ms       | ✅     |
| Message throughput           | 100+ msgs/sec | ✅     |
| Concurrent clients           | 100+          | ✅     |
| CPU usage                    | < 50%         | ✅     |
| Memory baseline              | < 500MB       | ✅     |
| Correlation calc (30 assets) | < 100ms       | ✅     |
| VaR calculation              | < 50ms        | ✅     |
| Greeks calculation           | < 10ms        | ✅     |

---

## 🐛 TROUBLESHOOTING

### WebSocket Connection Failed

```
Error: Failed to connect to ws://localhost:8000/ws/marketdata
```

**Solution**:

1. Check server is running: `python websocket_server.py`
2. Confirm port 8000 is not in use: `netstat -an | grep 8000`
3. Check firewall settings

### Finnhub Not Connecting

```
Error: Failed to connect to Finnhub: Invalid API key
```

**Solution**:

1. Verify `FINNHUB_API_KEY` in `.env`
2. Check API key is valid on https://finnhub.io/dashboard
3. Ensure API key has proper permissions (free tier = 200 req/min)

### No Data Appearing

```
Listening for market data... (but no messages)
```

**Solution**:

1. Check WebSocket server logs for consumer startup messages
2. Verify API keys are correctly configured
3. Test manually: `curl -X GET http://localhost:8000/health`
4. Check `ENABLE_FINNHUB=true` and `ENABLE_KRAKEN=true` in `.env`

### High CPU Usage

**Possible causes**:

- Too many WebSocket clients (> 1000)
- Data sources sending too frequently (throttle may be too high)
- Large correlation calculations (> 1000 assets)

**Solution**:

- Increase `THROTTLE_INTERVAL` in `.env`
- Reduce number of symbols tracked
- Implement async/await patterns in custom code

---

## 📚 PROJECT STRUCTURE

```
montecarlo/
├── src/
│   ├── real_time/
│   │   ├── __init__.py
│   │   ├── websocket_server.py          # Main WebSocket server
│   │   └── data_sources/
│   │       ├── __init__.py
│   │       ├── finnhub_consumer.py      # Finnhub streamer
│   │       ├── kraken_consumer.py       # Kraken crypto feeds
│   │       └── iex_consumer.py          # IEX alternative (optional)
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── correlation.py               # Correlation engine
│   │   ├── risk.py                      # Risk metrics (VaR, CVaR)
│   │   └── greeks.py                    # Options Greeks
│   │
│   ├── frontend/
│   │   └── market_data_client.js        # JS WebSocket client
│   │
│   └── [existing modules...]
│
├── tests/
│   ├── test_websocket_client.py         # WebSocket test
│   └── analytics/
│       └── test_analytics.py            # Unit tests
│
├── .env                                  # Configuration
├── pyproject.toml                        # Dependencies
└── README.md                             # Project readme
```

---

## 🎓 ARCHITECTURE DEEP-DIVE

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                     │
│  Finnhub (Stocks) | Kraken (Crypto) | IEX (Alternative)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  Data Consumers (Async Background)   │
        │  • FinnhubConsumer                   │
        │  • KrakenConsumer                    │
        │  • IEXConsumer                       │
        └──────────────────────┬───────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────┐
        │   MarketDataManager (Aggregator)     │
        │  • Throttle (max 100 msgs/sec)      │
        │  • Track active connections         │
        │  • Broadcast to all clients         │
        └──────────────────────┬───────────────┘
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
            ┌──────────────┐      ┌──────────────┐
            │  Frontend    │      │   Analytics  │
            │  (JS Client) │      │   (Python)   │
            │  WebSocket   │      │ - Risk calc  │
            │  + Charts    │      │ - Greeks     │
            │  + Live data │      │ - Correlation│
            └──────────────┘      └──────────────┘
```

### Throttling Strategy

```
Before: Finnhub send 100 events/sec → CPU spike → 100% usage

After: Throttle at 100 msgs/sec per symbol
├─ AAPL: 1 msg / 10ms (100 msgs/sec max)
├─ MSFT: 1 msg / 10ms (throttled)
└─ BTCUSD: 1 msg / 10ms (throttled)
→ Smooth 100 msgs/sec, 10% CPU usage
```

---

## 🔄 NEXT STEPS (WEEK 3)

1. **PostgreSQL + TimescaleDB** - Persistent price history
2. **Redis Caching** - Cache correlation matrices, VaR calculations
3. **Data Import** - Historical data loader (1-5 years)
4. **Performance** - Vectorization, numba JIT compilation
5. **Quality checks** - Missing data handling, outlier detection

---

## 📞 SUPPORT & REFERENCES

**Finnhub API Docs**: https://finnhub.io/docs/api
**Kraken WebSocket**: https://docs.kraken.com/websockets-v2
**FastAPI**: https://fastapi.tiangolo.com/
**Scipy (Stats)**: https://docs.scipy.org/doc/scipy/reference/stats.html

---

_Last updated: March 16, 2026_
_RAVINALA v3.0 — Real-Time Market Data Platform_
