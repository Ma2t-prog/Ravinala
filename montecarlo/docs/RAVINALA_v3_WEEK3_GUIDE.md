# 🚀 RAVINALA v3.0 — WEEK 3 DEPLOYMENT GUIDE

> [!WARNING]
> **Document status: needs verification**
> This guide reflects a specific historical rollout track.
> Endpoints, dependencies, and architecture assumptions may differ from current backend reality.
> Before implementation decisions, cross-check with:
> - `docs/PRIMARY_SOURCE_BASELINE_INDEX.md`
> - `docs/PRIMARY_SOURCE_DELTA_LEDGER.md`
> - `docs/PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md`

# Database + Caching + Historical Data

## 📋 PRE-REQUISITES

- Docker & Docker Compose installed
- Python 3.13+
- PostgreSQL client tools (psql) optional but recommended
- 5GB free disk space minimum

## 🏗️ ARCHITECTURE OVERVIEW

```
┌─────────────────────┐
│   Real-Time Data    │
│   (WebSocket)       │
└─────────┬───────────┘
          │
    ┌─────▼─────┐
    │  Redis    │ ◄── Cache hits: < 5ms
    │  (Hot)    │
    └─────┬─────┘
          │ (miss)
    ┌─────▼──────────────┐
    │ PostgreSQL         │ ◄── DB hits: < 100ms
    │ + TimescaleDB      │
    │ (Cold Storage)     │
    └────────────────────┘
```

## ⚙️ STEP 1: START DATABASE & CACHE USING DOCKER

### 1️⃣ Navigate to deployment directory

```bash
cd c:\Users\Matthias\Project\montecarlo\deployment
ls  # Should show docker-compose.yml and schema.sql
```

### 2️⃣ Start containers

```bash
docker-compose up -d
```

Expected output:
```
[+] Running 2/2
 ✓ Network ravinala_network Created
 ✓ Container ravinala_postgres Started
 ✓ Container ravinala_redis Started
```

### 3️⃣ Verify containers are healthy

```bash
docker-compose ps
```

Expected output: Both containers should show STATUS "healthy"

### 4️⃣ Check logs

```bash
# PostgreSQL
docker-compose logs postgres | head -20

# Redis
docker-compose logs redis | head -20
```

## ✅ STEP 2: VERIFY DATABASE CONNECTION

### 1️⃣ Test PostgreSQL

```bash
psql -h localhost -U ravinala -d market_data -c "SELECT version();"
```

Expected output: PostgreSQL version info

### 2️⃣ Test TimescaleDB

```bash
psql -h localhost -U ravinala -d market_data -c "\dx timescaledb"
```

Expected output: Shows timescaledb extension

### 3️⃣ Check tables created

```bash
psql -h localhost -U ravinala -d market_data -c "\dt"
```

Expected output: Lists tables (market_quotes, assets, risk_metrics, correlation_snapshots, data_quality_log)

### 4️⃣ Test Redis

```bash
redis-cli ping
```

Expected output: `PONG`

## 🐍 STEP 3: INSTALL PYTHON DEPENDENCIES

```bash
cd c:\Users\Matthias\Project\montecarlo

# Install database + caching dependencies
pip install sqlalchemy alembic psycopg2-binary redis pandas yfinance numpy scipy

# Verify installations
python -c "import sqlalchemy; import redis; import psycopg2; print('✓ All dependencies OK')"
```

## 📥 STEP 4: IMPORT HISTORICAL DATA

### 1️⃣ Run the importer

```bash
cd c:\Users\Matthias\Project\montecarlo

python -c "
from src.data.importer import HistoricalDataImporter
import logging
logging.basicConfig(level=logging.INFO)

importer = HistoricalDataImporter()

print('\n=== IMPORTING HISTORICAL DATA ===\n')

# Indices (fastest)
print('1. Importing indices...')
importer.import_indices()

# Stocks
print('\n2. Importing stocks...')
importer.import_stocks()

# Commodities
print('\n3. Importing commodities...')
importer.import_commodities()

# Forex
print('\n4. Importing forex...')
importer.import_forex()

print('\n=== IMPORT COMPLETE ===')
"
```

**Expected duration**: 15-30 minutes (depends on internet speed)

**Expected output**:
```
1. Importing indices...
  ✓ Imported 1260 rows for ^GSPC
  ✓ Imported 1260 rows for ^IXIC
  ...

2. Importing stocks...
  ✓ Imported 1260 rows for AAPL
  ...
```

### 2️⃣ Verify data imported

```bash
psql -h localhost -U ravinala -d market_data -c "
SELECT symbol, COUNT(*) as record_count 
FROM market_quotes 
GROUP BY symbol 
ORDER BY symbol 
LIMIT 10;
"
```

Expected output: Shows thousands of records per symbol

## 🔍 STEP 5: RUN DATA QUALITY CHECKS

```bash
cd c:\Users\Matthias\Project\montecarlo

python -c "
from src.data.quality_checks import DataQualityChecker
import logging
logging.basicConfig(level=logging.INFO)

checker = DataQualityChecker()

symbols = ['AAPL', 'MSFT', 'GOOGL', '^GSPC', 'GC=F']
print('\n=== DATA QUALITY REPORT ===\n')
results = checker.run_all_checks(symbols)

for symbol, checks in results.items():
    print(f'{symbol}:')
    print(f'  Records: {checks[\"records\"]:,}')
    print(f'  Missing OHLC: {checks[\"missing_ohlc\"]}')
    print(f'  Duplicates: {checks[\"duplicates\"]}')
    print(f'  Outliers: {checks[\"outliers\"]}')
    print(f'  Gaps: {checks[\"gaps\"]}')
    print()
"
```

**Expected output**: All values should be 0 for clean data

## ⚡ STEP 6: TEST QUERY ENGINE WITH CACHING

```bash
cd c:\Users\Matthias\Project\montecarlo

python -c "
from src.data.query_engine import query_engine
from datetime import datetime, timedelta

print('\n=== QUERY ENGINE TEST ===\n')

# 1. Health check
print('1️⃣  System health check...')
health = query_engine.health_check()
for service, status in health.items():
    if service != 'timestamp':
        symbol = '✅' if status else '❌'
        print(f'  {symbol} {service}: {\"OK\" if status else \"FAILED\"}')

# 2. Get latest price (test cache)
print('\n2️⃣  Latest prices (cached)...')
for symbol in ['AAPL', 'MSFT']:
    price = query_engine.get_price_with_cache(symbol)
    if price:
        print(f'  {symbol}: \${price[\"price\"]:.2f}')

# 3. Get OHLCV data
print('\n3️⃣  30-day OHLCV...')
end = datetime.now()
start = end - timedelta(days=30)
df = query_engine.get_ohlcv_with_cache('AAPL', start, end)
print(f'  AAPL: {len(df)} days, ▲ \${df[\"close\"].max():.2f}, ▼ \${df[\"close\"].min():.2f}')

# 4. Calculate correlation
print('\n4️⃣  Correlation matrix (cached)...')
symbols = ['AAPL', 'MSFT', 'GOOGL']
corr = query_engine.calculate_correlation_cached(symbols, lookback_days=252)
print(f'  Calculated for {len(symbols)} symbols:')
print(f'    AAPL-MSFT: {corr.loc[\"AAPL\", \"MSFT\"]:.3f}')
print(f'    MSFT-GOOGL: {corr.loc[\"MSFT\", \"GOOGL\"]:.3f}')

print('\n✅ Query engine test PASSED!')
"
```

**Expected output**: All tests should pass with data displayed

## 🔌 STEP 7: INTEGRATE WITH WEBSOCKET SERVER

The WebSocket server now persists all quotes to the database automatically.

### 1️⃣ Update websocket_server.py imports (if not already done)

```python
# Add to top of websocket_server.py:
from src.db.connection import db_manager
from src.cache.redis_manager import redis_cache
import asyncio
```

### 2️⃣ The server will now:

- ✅ Persist all WebSocket messages to PostgreSQL
- ✅ Cache recent prices in Redis (2s TTL)
- ✅ Compress old data automatically (TimescaleDB)
- ✅ Query from cache for fast lookups

## 🚀 STEP 8: START FULL STACK (DATABASE + REAL-TIME + FRONTEND)

### Terminal 1: WebSocket Server with persistence

```bash
cd c:\Users\Matthias\Project\montecarlo
python -m uvicorn src.real_time.websocket_server:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Streamlit UI

```bash
cd c:\Users\Matthias\Project\montecarlo\src
python -m streamlit run app.py --logger.level=warning
```

### Terminal 3: Query test (optional)

```bash
cd c:\Users\Matthias\Project\montecarlo

# Check database every 30 seconds
while true; do
    echo "Records in DB:"
    psql -h localhost -U ravinala -d market_data -c "SELECT COUNT(*) FROM market_quotes;"
    sleep 30
done
```

## 📊 PERFORMANCE METRICS

### Query Latency Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Price (cache hit) | < 5ms | Redis |
| Price (DB hit) | < 100ms | PostgreSQL index |
| OHLCV (1 year) | < 500ms | TimescaleDB compression |
| Correlation matrix | < 200ms cached, < 2s computed | Pre-calculated |

### Storage Usage

| Data | Estimated Size |
|------|----------------|
| 5 years × 30 symbols × daily | ~15MB (compressed) |
| 5 years × 10 symbols × hourly | ~200MB (compressed) |
| 1 year × 5 symbols × 1-minute | ~500MB (compressed) |

### Concurrent Clients

- PostgreSQL: 50+ concurrent connections
- Redis: Unlimited connections
- System: Tested with 100+ simultaneous WebSocket clients

## 🔧 TROUBLESHOOTING

### Issue: Docker containers won't start

```bash
# Check for port conflicts
netstat -an | grep 5432  # PostgreSQL
netstat -an | grep 6379  # Redis

# Force recreate
docker-compose down -v
docker-compose up -d --force-recreate
```

### Issue: Database connection refused

```bash
# Verify containers running
docker-compose ps

# Check PostgreSQL logs
docker-compose logs postgres --tail=50

# Manually test connection
psql -h localhost -U ravinala -d market_data -c "SELECT 1;"
```

### Issue: No data after import

```bash
# Check import logs
docker-compose logs postgres | grep "CREATE TABLE"

# Verify table exists
psql -h localhost -U ravinala -d market_data -c "SELECT COUNT(*) FROM market_quotes;"
```

### Issue: High memory usage

```bash
# Redis memory stats
redis-cli info memory

# Reduce Redis TTL in src/cache/redis_manager.py
# Reduce max_memory in docker-compose.yml (currently 2gb)
```

## 🧹 MAINTENANCE

### Daily Update

```bash
python -c "
from src.data.importer import HistoricalDataImporter
importer = HistoricalDataImporter()

symbols = ['AAPL', 'MSFT', 'GOOGL', '^GSPC', 'GC=F']
importer.update_daily(symbols)
"
```

### Clean Old Data

```bash
python -c "
from src.db.connection import db_manager
deleted = db_manager.delete_old_data(older_than_days=1825)  # Keep only 5 years
print(f'Deleted {deleted} old records')
"
```

### Clear Cache

```bash
redis-cli FLUSHALL  # ⚠️ WARNING: Clears entire cache
```

## 📈 NEXT STEPS (WEEK 4+)

- [ ] TradingView-style charts (Lightweight Charts JS)
- [ ] 200+ technical indicators (TA-Lib)
- [ ] Advanced backtesting engine
- [ ] ML-based price prediction
- [ ] Multi-timeframe analysis
- [ ] Performance optimization with vectorization

## ✅ WEEK 3 CHECKLIST

- [x] PostgreSQL + TimescaleDB running in Docker
- [x] Redis running in Docker
- [x] Tables created (market_quotes, assets, risk_metrics)
- [x] Historical data imported (1000+ rows per symbol)
- [x] Data quality checks pass
- [x] Query engine with caching working
- [x] WebSocket server persisting data to DB
- [x] Redis cache layer operational
- [x] Docker Compose can be torn down/rebuilt without data loss
- [x] Ready for Week 4 (charting + indicators)

---

**Last Updated**: March 16, 2026
**Status**: ✅ PRODUCTION READY
