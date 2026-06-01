# 🚀 RAVINALA v3.0 — WEEK 3 QUICK REFERENCE


> [!WARNING]
> **Document status: needs verification**
> This guide reflects a specific historical rollout track.
> Endpoints, dependencies, and architecture assumptions may differ from current backend reality.
> Before implementation decisions, cross-check with:
> - `docs/PRIMARY_SOURCE_BASELINE_INDEX.md`
> - `docs/PRIMARY_SOURCE_DELTA_LEDGER.md`
> - `docs/PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md`

## 📍 DOCKER OPERATIONS

### Start Services
```bash
cd deployment
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Full Reset (Delete all data)
```bash
docker-compose down -v
docker volume prune
```

### View Logs
```bash
docker-compose logs postgres -f
docker-compose logs redis -f
```

### Health Check
```bash
docker-compose ps
```

---

## 🐍 PYTHON OPERATIONS

### Import Historical Data
```bash
python -c "
from src.data.importer import HistoricalDataImporter
importer = HistoricalDataImporter()
importer.import_indices()
importer.import_stocks()
importer.import_commodities()
importer.import_forex()
"
```

### Check Data Quality
```bash
python -c "
from src.data.quality_checks import DataQualityChecker
checker = DataQualityChecker()
results = checker.run_all_checks(['AAPL', 'MSFT', 'GOOGL'])
for symbol, checks in results.items():
    print(f'{symbol}: {checks}')
"
```

### Query Data with Caching
```bash
python -c "
from src.data.query_engine import query_engine
from datetime import datetime, timedelta

# Get latest price
price = query_engine.get_price_with_cache('AAPL')
print(f'AAPL: {price[\"price\"]}')

# Get OHLCV data
end = datetime.now()
start = end - timedelta(days=30)
df = query_engine.get_ohlcv_with_cache('AAPL', start, end)
print(f'Got {len(df)} days of data')

# Calculate correlation
symbols = ['AAPL', 'MSFT', 'GOOGL']
corr = query_engine.calculate_correlation_cached(symbols)
print(corr)
"
```

### Test Database Connection
```bash
python -c "
from src.db.connection import db_manager
health = db_manager.health_check()
print(f'Database: {\"OK\" if health else \"FAILED\"}')
"
```

### Test Redis Connection
```bash
python -c "
from src.cache.redis_manager import redis_cache
health = redis_cache.health_check()
print(f'Redis: {\"OK\" if health else \"FAILED\"}')
"
```

### Clear Cache
```bash
python -c "
from src.cache.redis_manager import redis_cache
redis_cache.flush_all()
print('✓ Cache cleared')
"
```

---

## 🔌 PSQL COMMANDS

### Connect to Database
```bash
psql -h localhost -U ravinala -d market_data
```

### Check Table Sizes
```psql
-- From psql prompt
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables 
WHERE schemaname != 'pg_catalog' 
ORDER BY pg_total_relation_size DESC;
```

### Count Records by Symbol
```psql
SELECT symbol, COUNT(*) as records 
FROM market_quotes 
GROUP BY symbol 
ORDER BY records DESC;
```

### Check Latest Data
```psql
SELECT symbol, MAX(ts) as latest_time 
FROM market_quotes 
GROUP BY symbol 
ORDER BY symbol;
```

### Get Price Range
```psql
SELECT 
  symbol,
  MIN(close) as min_price,
  MAX(close) as max_price,
  COUNT(*) as records
FROM market_quotes
WHERE symbol = 'AAPL'
GROUP BY symbol;
```

### Enable Compression
```psql
SELECT add_compression_policy('market_quotes', INTERVAL '1 week');
```

---

## ⚡ REDIS CLI COMMANDS

### Connect
```bash
redis-cli
```

### Check Memory
```bash
redis-cli info memory
```

### Check Keys
```bash
redis-cli KEYS "market:*"
redis-cli KEYS "analytics:*"
```

### Get Value
```bash
redis-cli GET "market:price:AAPL"
redis-cli GET "analytics:correlation:matrix"
```

### Check TTL
```bash
redis-cli TTL "market:price:AAPL"
```

### Flush All (⚠️ WARNING)
```bash
redis-cli FLUSHALL
```

---

## 📊 ARCHITECTURE FILES

| File | Purpose | Size |
|------|---------|------|
| `deployment/docker-compose.yml` | Docker services | 30 lines |
| `deployment/schema.sql` | Database schema | 100 lines |
| `src/db/models.py` | SQLAlchemy models | 85 lines |
| `src/db/connection.py` | DB manager | 150 lines |
| `src/cache/redis_manager.py` | Redis operations | 200 lines |
| `src/data/importer.py` | Data import | 250 lines |
| `src/data/quality_checks.py` | QA checks | 280 lines |
| `src/data/query_engine.py` | Query layer | 300 lines |

**Total Production Code**: ~1,400 lines

---

## 🔍 MONITORING

### Database Disk Usage
```bash
docker exec ravinala_postgres du -sh /var/lib/postgresql/data
```

### Redis Memory Usage
```bash
redis-cli info memory | grep used
```

### Query Performance (psql)
```psql
EXPLAIN ANALYZE
SELECT * FROM market_quotes 
WHERE symbol = 'AAPL' 
AND ts > NOW() - INTERVAL '30 days'
ORDER BY ts DESC;
```

---

## 🧼 MAINTENANCE

### Daily Update
```bash
python -c "
from src.data.importer import HistoricalDataImporter
importer = HistoricalDataImporter()
symbols = ['AAPL', 'MSFT', 'GOOGL', '^GSPC', 'GC=F']
importer.update_daily(symbols)
"
```

### Monthly Cleanup
```bash
python -c "
from src.data.quality_checks import DataQualityChecker
checker = DataQualityChecker()
# Remove duplicates
for symbol in ['AAPL', 'MSFT', 'GOOGL']:
    checker.clean_duplicates(symbol)
"
```

### Archive Old Data (5+ years)
```bash
python -c "
from src.db.connection import db_manager
deleted = db_manager.delete_old_data(older_than_days=1825)
print(f'✓ Deleted {deleted} old records')
"
```

---

## 🚨 TROUBLESHOOTING

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :5432
netstat -ano | findstr :6379

# Kill process
taskkill /PID <PID> /F
```

### Docker Won't Start
```bash
# Force remove containers
docker-compose down -v
docker system prune -a

# Retry
docker-compose up -d
```

### Database Connection Refused
```bash
# Check container is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Test manually
docker exec ravinala_postgres psql -U ravinala -d market_data -c "SELECT 1;"
```

### Redis Connection Refused
```bash
# Check container
docker-compose ps redis

# Test manually
docker exec ravinala_redis redis-cli ping
```

### Out of Memory
```bash
# Check usage
docker stats

# Reduce Redis max memory (docker-compose.yml)
# Reduce batch size (src/data/importer.py)
# Enable TimescaleDB compression earlier
```

---

## 📈 PERFORMANCE TUNING

### Increase DB Connection Pool
```python
# src/db/models.py
engine = create_engine(
    DATABASE_URL,
    pool_size=30,        # ← Increase from 20
    max_overflow=60,     # ← Increase from 40
)
```

### Increase Redis Memory
```yaml
# deployment/docker-compose.yml
command: redis-server --maxmemory 4gb  # ← Increase from 2gb
```

### Enable Query Caching
```python
# src/data/query_engine.py
# Reduce OHLCV TTL from 3600 to 7200 (2 hours)
self.TTL['ohlcv_1d'] = 7200
```

---

## ✅ WEEK 3 DEPLOYMENT CHECKLIST

- [ ] Docker containers running (`docker-compose ps`)
- [ ] PostgreSQL accessible (`psql -h localhost...`)
- [ ] TimescaleDB enabled (`\dx timescaledb`)
- [ ] Redis responding (`redis-cli ping`)
- [ ] Historical data imported (1000+ rows per symbol)
- [ ] Data quality checks pass (0 critical issues)
- [ ] Query engine works (< 500ms response)
- [ ] Cache layer works (< 5ms hits)
- [ ] WebSocket persists to DB
- [ ] App starts without DB errors
- [ ] Ready for Week 4 (charting)

---

**Last Updated**: March 16, 2026  
**Version**: 3.0  
**Status**: ✅ PRODUCTION READY
