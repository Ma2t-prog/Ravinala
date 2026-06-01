-- ==================== TIMESCALEDB SETUP ====================
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ==================== MARKET DATA TABLES ====================

-- Main quotes table (tick data, OHLCV)
CREATE TABLE IF NOT EXISTS market_quotes (
    id BIGSERIAL,
    symbol VARCHAR(20) NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    adj_close DOUBLE PRECISION,
    volume BIGINT,
    source VARCHAR(50) NOT NULL,
    interval VARCHAR(10) NOT NULL DEFAULT '1m',
    PRIMARY KEY (id, ts, symbol)
);

-- Convert to hypertable (TimescaleDB compression)
SELECT create_hypertable('market_quotes', 'ts', 'symbol', 4, if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_quotes_symbol_ts ON market_quotes (symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_ts ON market_quotes (ts DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_source ON market_quotes (source);

-- Enable compression
ALTER TABLE market_quotes SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('market_quotes', INTERVAL '1 week', if_not_exists => TRUE);

-- Data retention policy (5 years)
SELECT add_retention_policy('market_quotes', INTERVAL '5 years', if_not_exists => TRUE);

-- ==================== METADATA TABLES ====================

-- Asset metadata
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200),
    asset_type VARCHAR(50),
    sector VARCHAR(100),
    country VARCHAR(50),
    exchange VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_symbol ON assets (symbol);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets (asset_type);

-- Data quality log
CREATE TABLE IF NOT EXISTS data_quality_log (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    check_type VARCHAR(100),
    issue_count INT,
    ts_start TIMESTAMPTZ,
    ts_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Correlation snapshots
CREATE TABLE IF NOT EXISTS correlation_snapshots (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    symbol1 VARCHAR(20) NOT NULL,
    symbol2 VARCHAR(20) NOT NULL,
    correlation_pearson DOUBLE PRECISION,
    correlation_spearman DOUBLE PRECISION,
    lookback_days INT DEFAULT 252
);

CREATE INDEX IF NOT EXISTS idx_corr_ts ON correlation_snapshots (ts DESC);
CREATE INDEX IF NOT EXISTS idx_corr_symbols ON correlation_snapshots (symbol1, symbol2);

-- Risk metrics snapshots
CREATE TABLE IF NOT EXISTS risk_metrics (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    var_95 DOUBLE PRECISION,
    cvar_95 DOUBLE PRECISION,
    volatility DOUBLE PRECISION,
    sharpe_ratio DOUBLE PRECISION,
    lookback_days INT DEFAULT 252
);

CREATE INDEX IF NOT EXISTS idx_risk_ts ON risk_metrics (ts DESC);
CREATE INDEX IF NOT EXISTS idx_risk_symbol ON risk_metrics (symbol);

-- ==================== PERMISSIONS ====================

-- Create read-only user
CREATE USER ravinala_read_only WITH PASSWORD 'read_only_password_2026';
GRANT CONNECT ON DATABASE market_data TO ravinala_read_only;
GRANT USAGE ON SCHEMA public TO ravinala_read_only;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ravinala_read_only;
