# RAVINALA v3.0 QUICK REFERENCE GUIDE

> [!WARNING]
> **Document status: needs verification**
> Commands and examples here are retained for historical operations context.
> They are not guaranteed to match the current backend deployment path.
> Validate against:
> - `docs/PRIMARY_SOURCE_BASELINE_INDEX.md`
> - `docs/PRIMARY_SOURCE_DELTA_LEDGER.md`
> - `docs/PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md`

## ⚡ QUICK COMMANDS

### Start Real-Time Server

```bash
# Terminal 1: Start WebSocket server
cd montecarlo/src/real_time
python -m uvicorn websocket_server:app --host 0.0.0.0 --port 8000 --reload

# Server ready at http://localhost:8000
# WebSocket: ws://localhost:8000/ws/marketdata
# Swagger UI: http://localhost:8000/docs
```

### Test WebSocket Connection

```bash
# Terminal 2: Run test client
cd montecarlo/tests
python test_websocket_client.py

# Should show live market data:
# ✓ Connected...
# [0001] AAPL       $150.25 | finnhub
# [0002] BTCUSD     $45123  | kraken
```

### Run Analytics Tests

```bash
# Test all analytics modules
cd montecarlo
python -m pytest tests/analytics/test_analytics.py -v

# Test individual engines
python src/analytics/correlation.py   # Test correlation
python src/analytics/risk.py          # Test risk
python src/analytics/greeks.py        # Test Greeks
```

### Check Server Health

```bash
# Health check
curl http://localhost:8000/health

# Response:
# {"status": "healthy", "connected_clients": 3, "messages_broadcasted": 1245, ...}

# Get stats
curl http://localhost:8000/stats
```

---

## 📦 INSTALLATION QUICK CHECKLIST

- [ ] `pip install fastapi uvicorn websockets websocket-client`
- [ ] `pip install pandas numpy scipy scikit-learn`
- [ ] `pip install python-dotenv pydantic`
- [ ] `pip install pytest pytest-asyncio`
- [ ] Create `.env` with API keys
- [ ] `FINNHUB_API_KEY=your_token` (from https://finnhub.io)
- [ ] Ensure `ENABLE_FINNHUB=true` in `.env`
- [ ] Ensure `ENABLE_KRAKEN=true` in `.env`

Treat the rest of this sheet as historical operator guidance unless the primary-source docs confirm the same backend shape today.

---

## 🎯 TESTING QUICK CHECKLIST

### Week 1: Real-Time Data

**Server Startup**:

- [ ] No errors on startup
- [ ] See "🚀 RAVINALA Real-Time Server Starting"
- [ ] Health endpoint responds

**WebSocket Connection**:

- [ ] Test client connects successfully
- [ ] Sees "✓ Connected to market data server"
- [ ] Receives data from Finnhub
- [ ] Receives data from Kraken

**Data Validation**:

- [ ] AAPL, MSFT, GOOGL have prices
- [ ] BTC/USD, ETH/USD crypto data
- [ ] Multiple clients can subscribe
- [ ] Messages arrive < 500ms

### Week 2: Analytics

**Correlation**:

```python
from src.analytics.correlation import CorrelationEngine
engine = CorrelationEngine()
engine.add_price("A", 100)
engine.add_price("B", 100)
# ... add more prices
matrix = engine.calculate_matrix()
assert matrix is not None
```

**Risk**:

```python
from src.analytics.risk import RiskEngine
risk = RiskEngine(confidence_level=0.95)
risk.add_price("A", 100)
# ... add prices
var = risk.calculate_var_historical("A", 1_000_000)
assert var < 0  # Should be negative (loss)
```

**Greeks**:

```python
from src.analytics.greeks import GreeksCalculator
greeks = GreeksCalculator.get_all_greeks(150, 150, 0.05, 0.25, 0.1667, "call")
assert greeks['price'] > 0
assert 'delta' in greeks
assert 'gamma' in greeks
```

---

## 📊 DATA PROVIDERS QUICK REFERENCE

### Finnhub

| Asset Class | Symbols                | Latency | Note             |
| ----------- | ---------------------- | ------- | ---------------- |
| US Stocks   | AAPL, MSFT, GOOGL, ... | <100ms  | Real-time quotes |
| Forex       | EURUSD, GBPUSD, ...    | <100ms  | FX pairs         |
| Crypto      | BINANCE:BTCUSDT, ...   | ~500ms  | Via Finnhub      |

**API Key**: https://finnhub.io/register (free, 200 req/min)

### Kraken

| Asset Class | Symbols               | Latency   | Note            |
| ----------- | --------------------- | --------- | --------------- |
| Crypto      | BTC/USD, ETH/USD, ... | <100ms    | Direct exchange |
| Spreads     | Bid/Ask               | Real-time | Market quality  |

**API Key**: None required (public API)

### IEX Cloud

| Asset Class | Symbols      | Latency | Note                       |
| ----------- | ------------ | ------- | -------------------------- |
| US Stocks   | Any US stock | <50ms   | Deprecated (template only) |

**Note**: IEX Cloud API has changed. Template provided for alternative feeds.

---

## 🔧 COMMON OPERATIONS

### Subscribe to New Symbol (JavaScript)

```javascript
const client = new MarketDataClient();
client.subscribe("TSLA", (data) => {
  console.log(`TSLA: $${data.price}`);
});
```

### Add New Consumer (Python)

1. Create `src/real_time/data_sources/your_consumer.py`
2. Implement `YourConsumer` class with `on_message()`, `on_open()`, etc.
3. Import in `websocket_server.py`
4. Add to startup event: `asyncio.create_task(your_consumer())`

### Calculate Portfolio VaR

```python
from src.analytics.risk import RiskEngine
from src.analytics.correlation import CorrelationEngine

# Step 1: Build correlation matrix
corr = CorrelationEngine()
# ... add prices

corr_matrix = corr.calculate_matrix()

# Step 2: Calculate portfolio VaR
risk = RiskEngine(confidence_level=0.95)
# ... add prices

positions = {"AAPL": 500000, "MSFT": 500000}  # $1M portfolio
port_var = risk.calculate_portfolio_var(positions, corr_matrix)

print(f"Portfolio VaR (95%): ${abs(port_var):,.0f}")
```

---

## 🐛 QUICK TROUBLESHOOTING

| Issue                 | Solution                                             |
| --------------------- | ---------------------------------------------------- |
| Server won't start    | Check port 8000 not in use, check Python path        |
| No Finnhub data       | Verify API key in `.env`, check rate limit (200/min) |
| No Kraken data        | Ensure `ENABLE_KRAKEN=true`, check network           |
| WebSocket disconnects | Client reconnects auto after 3s, check server logs   |
| High CPU usage        | Increase `THROTTLE_INTERVAL`, reduce symbols         |
| Correlation NaN       | Need at least 2+ prices per symbol, 2+ symbols       |
| VaR always zero       | Need at least 2 prices to calculate returns          |

---

## 📈 PERFORMANCE TIPS

1. **Throttling**: Default 100 msgs/sec is optimal for UI updates
2. **Symbols**: Limit to 50-100 symbols per server instance
3. **Lookback**: Use 252 (1 year) for daily statistics
4. **Batch**: Calculate correlation/VaR once per minute, not every tick
5. **Redis**: Cache outputs in Phase 2 for 60-second TTL

---

## 💾 .ENV TEMPLATE

```env
# === API Keys ===
FINNHUB_API_KEY=your_finnhub_token_here
IEX_API_KEY=

# === Server ===
WS_HOST=0.0.0.0
WS_PORT=8000
WS_ENDPOINT=/ws/marketdata
MAX_MESSAGES_PER_SEC=100
THROTTLE_INTERVAL=0.01

# === Data ===
PRICE_HISTORY_LOOKBACK=252
VARIANCE_LOOKBACK=1260
VAR_CONFIDENCE_LEVEL=0.95
CVaR_CONFIDENCE_LEVEL=0.95

# === Logging ===
LOG_LEVEL=DEBUG
LOG_FILE=logs/real_time.log

# === Features ===
ENABLE_FINNHUB=true
ENABLE_KRAKEN=true
ENABLE_IEX=false
ENABLE_CORRELATION=true
ENABLE_RISK_CALC=true
```

---

## 📚 KEY FILES REFERENCE

| File                         | Purpose                    | Size       |
| ---------------------------- | -------------------------- | ---------- |
| `websocket_server.py`        | Main WebSocket server      | ~400 lines |
| `finnhub_consumer.py`        | Finnhub data stream        | ~180 lines |
| `kraken_consumer.py`         | Kraken crypto stream       | ~170 lines |
| `correlation.py`             | Correlation matrix engine  | ~250 lines |
| `risk.py`                    | Risk analytics (VaR, CVaR) | ~350 lines |
| `greeks.py`                  | Options Greeks calculator  | ~280 lines |
| `market_data_client.js`      | Frontend WebSocket client  | ~200 lines |
| `RAVINALA_v3_SETUP_GUIDE.md` | Complete setup guide       | ~500 lines |

**Total**: ~2,000 lines of production-ready code

---

## ✅ DEPLOYMENT CHECKLIST

- [ ] All files created and tested locally
- [ ] `.env` configured with valid API keys
- [ ] Server starts without errors
- [ ] WebSocket accepts connections
- [ ] Data streams from Finnhub
- [ ] Data streams from Kraken
- [ ] Analytics tests pass
- [ ] No hardcoded credentials
- [ ] Logging configured
- [ ] Throttling active
- [ ] Health check working
- [ ] Documentation complete

---

## 🚀 NEXT PHASE (WEEK 3)

Target: **PostgreSQL + Caching**

- [ ] PostgreSQL TimescaleDB setup
- [ ] Historical data importer (1-5 years)
- [ ] Redis caching layer
- [ ] Performance optimization
- [ ] Database indexing
- [ ] Data quality checks

---

_Quick Reference — RAVINALA v3.0 Real-Time Platform_
_Last updated: March 16, 2026_
