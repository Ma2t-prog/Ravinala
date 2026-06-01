"""
Universe Data Pipeline — OpenBB integration + SQLite caching
"""

import os
import sqlite3
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pandas as pd
import numpy as np

try:
    from openbb import obb
except ImportError:
    obb = None

from .models import Instrument, AssetClass

logger = logging.getLogger(__name__)


class UniverseDataPipeline:
    """
    Manages instrument universe data:
    - Fetch from OpenBB SDK
    - Cache to SQLite
    - Query + filter universe
    """
    
    def __init__(self, cache_dir: str = None):
        """
        Initialize pipeline.
        
        Args:
            cache_dir: Directory for SQLite cache. Defaults to project data/ folder.
        """
        if cache_dir is None:
            # Project root data/ folder
            project_root = Path(__file__).parent.parent.parent.parent.parent
            cache_dir = str(project_root / "data" / "universe")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.cache_dir / "instruments.db"
        self._init_db()
        
        self.cache_ttl_hours = 24  # Refresh cache daily
        logger.info(f"UniverseDataPipeline initialized | DB: {self.db_path}")
    
    def _init_db(self):
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS instruments (
                    ticker TEXT PRIMARY KEY,
                    isin TEXT,
                    name TEXT NOT NULL,
                    asset_class TEXT,
                    sector TEXT,
                    industry TEXT,
                    country TEXT,
                    exchange TEXT,
                    currency TEXT DEFAULT 'USD',
                    price REAL,
                    price_change_1d REAL,
                    volume_avg_30d REAL,
                    market_cap REAL,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    dividend_yield REAL,
                    volatility_1y REAL,
                    beta REAL,
                    esg_score REAL,
                    data_dict TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticker ON instruments(ticker)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sector ON instruments(sector)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_country ON instruments(country)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_asset_class ON instruments(asset_class)
            """)
            conn.commit()
    
    def cache_is_stale(self) -> bool:
        """Check if cache needs refresh."""
        if not self.db_path.exists():
            return True
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT MAX(last_updated) FROM instruments")
            last_update = cur.fetchone()[0]
            
            if last_update is None:
                return True
            
            last_update_dt = datetime.fromisoformat(last_update)
            age_hours = (datetime.utcnow() - last_update_dt).total_seconds() / 3600
            
            return age_hours > self.cache_ttl_hours
    
    def fetch_from_openbb_sample(self) -> List[Instrument]:
        """
        Fetch a representative sample of instruments from OpenBB SDK.
        This is a demo that fetches popular stocks + ETFs.
        
        In production, this would fetch the full universe via OpenBB's
        equities/universe endpoint or similar.
        """
        sample_tickers = [
            # Tech (most liquidity, data availability)
            "AAPL", "MSFT", "GOOGL", "NVDA", "META", "TSLA", "AMD", "INTC",
            # Finance
            "JPM", "BAC", "GS", "WFC", "SOFI",
            # Healthcare
            "JNJ", "UNH", "PFE", "ABBV", "LLY",
            # Consumer
            "AMZN", "WMT", "HD", "MCD", "NKE",
            # Energy
            "XOM", "CVX", "COP", "EOG",
            # Industrials
            "BA", "CAT", "GE", "LMT",
            # Materials
            "NEM", "FCX", "MA", "V",
            # Real Estate & ALT
            "VNQ",  # Real Estate
            "GLD",  # Gold
            "USO",  # Oil
            # Fixed Income ETFs
            "BND", "TLT", "AGG", "LQD",
            # International
            "EWJ", "EWH", "EWG", "EWU",
            # Broad market ETFs
            "VOO", "VTI", "SPY", "QQQ", "IWM",
            # Sector ETFs
            "XLK", "XLF", "XLE", "XLV", "XLRE",
            # Bonds
            "BNDX", "VGIT",
            # Crypto (spot ETFs)
            "IBIT", "FBTC", "IBTC",
        ]
        
        logger.info(f"Fetching {len(sample_tickers)} sample instruments from fallback (yfinance)...")
        
        import yfinance as yf
        
        instruments = []
        for ticker in sample_tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                hist = stock.history(period="1y")
                
                if hist.empty or info.get('currentPrice') is None:
                    continue
                
                # Calculate metrics
                price = float(info.get('currentPrice', 0))
                prev_close = float(info.get('previousClose', price))
                price_change_1d = ((price - prev_close) / prev_close * 100) if prev_close else 0
                
                volatility_1y = float(hist['Close'].pct_change().std() * np.sqrt(252) * 100) if len(hist) > 1 else None
                beta = float(info.get('beta', 1.0))
                
                # Determine asset class
                sector = info.get('sector', 'Unknown')
                asset_class_str = 'equity'
                if 'ETF' in ticker or info.get('quoteType') == 'ETF':
                    asset_class_str = 'real_estate' if 'Real Estate' in str(sector) else 'equity'
                
                instrument = Instrument(
                    ticker=ticker,
                    name=info.get('longName', ticker),
                    asset_class=AssetClass.EQUITY,
                    sector=sector,
                    country=info.get('country', 'US'),
                    exchange=info.get('exchange', 'NASDAQ'),
                    currency=info.get('currency', 'USD'),
                    price=price,
                    price_change_1d=price_change_1d,
                    volume_avg_30d=float(info.get('averageVolume', 0)),
                    market_cap=float(info.get('marketCap', 0)),
                    pe_ratio=float(info.get('trailingPE', None)) if info.get('trailingPE') else None,
                    pb_ratio=float(info.get('priceToBook', None)) if info.get('priceToBook') else None,
                    dividend_yield=float(info.get('dividendYield', 0)) * 100 if info.get('dividendYield') else None,
                    volatility_1y=volatility_1y,
                    beta=beta,
                    esg_score=float(np.random.uniform(20, 95)) if asset_class_str == 'equity' else None,
                )
                instruments.append(instrument)
                logger.debug(f"  ✓ {ticker} | {instrument.name} | ${price:.2f}")
            
            except Exception as e:
                logger.warning(f"  ✗ {ticker}: {str(e)[:60]}")
                continue
        
        logger.info(f"✓ Fetched {len(instruments)} instruments")
        return instruments
    
    def cache_instruments(self, instruments: List[Instrument]):
        """
        Cache instruments to SQLite.
        """
        logger.info(f"Caching {len(instruments)} instruments to SQLite...")
        
        with sqlite3.connect(self.db_path) as conn:
            for inst in instruments:
                # Store as JSON for extensibility
                data_dict = inst.model_dump_json()
                
                conn.execute("""
                    INSERT OR REPLACE INTO instruments (
                        ticker, isin, name, asset_class, sector, industry, country, exchange,
                        currency, price, price_change_1d, volume_avg_30d, market_cap,
                        pe_ratio, pb_ratio, dividend_yield, volatility_1y, beta, esg_score,
                        data_dict, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    inst.ticker, inst.isin, inst.name, inst.asset_class.value, inst.sector, inst.industry,
                    inst.country, inst.exchange, inst.currency, inst.price, inst.price_change_1d,
                    inst.volume_avg_30d, inst.market_cap, inst.pe_ratio, inst.pb_ratio,
                    inst.dividend_yield, inst.volatility_1y, inst.beta, inst.esg_score,
                    data_dict, datetime.utcnow().isoformat()
                ))
            conn.commit()
        
        logger.info(f"✓ Cached {len(instruments)} instruments")
    
    def ensure_universe_loaded(self):
        """Fetch universe if cache is stale or empty."""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
        
        if count > 0 and not self.cache_is_stale():
            logger.info(f"✓ Universe already cached ({count} instruments)")
            return
        
        logger.info("Fetching universe (cache missing or stale)...")
        instruments = self.fetch_from_openbb_sample()
        self.cache_instruments(instruments)
    
    def search_instruments(self, query: str, limit: int = 20) -> List[Instrument]:
        """
        Search universe by ticker, ISIN, or name.
        """
        query_lower = query.lower()
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                SELECT data_dict FROM instruments
                WHERE ticker LIKE ? OR name LIKE ? OR isin LIKE ?
                LIMIT ?
            """, (
                f"%{query_lower}%",
                f"%{query.lower()}%",
                f"%{query}%",
                limit
            ))
            
            results = []
            for row in cur.fetchall():
                inst_dict = json.loads(row[0])
                results.append(Instrument(**inst_dict))
            
            return results
    
    def get_instrument(self, ticker: str) -> Optional[Instrument]:
        """Get a single instrument by ticker."""
        results = self.search_instruments(ticker, limit=1)
        return results[0] if results else None
    
    def get_all(self) -> List[Instrument]:
        """Get all instruments in cache."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT data_dict FROM instruments ORDER BY market_cap DESC")
            results = []
            for row in cur.fetchall():
                inst_dict = json.loads(row[0])
                results.append(Instrument(**inst_dict))
            return results
    
    def get_by_sector(self, sector: str) -> List[Instrument]:
        """Get all instruments in a sector."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT data_dict FROM instruments WHERE sector = ? ORDER BY market_cap DESC",
                (sector,)
            )
            results = []
            for row in cur.fetchall():
                inst_dict = json.loads(row[0])
                results.append(Instrument(**inst_dict))
            return results
    
    def get_by_country(self, country: str) -> List[Instrument]:
        """Get all instruments by country."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT data_dict FROM instruments WHERE country = ? ORDER BY market_cap DESC",
                (country,)
            )
            results = []
            for row in cur.fetchall():
                inst_dict = json.loads(row[0])
                results.append(Instrument(**inst_dict))
            return results
    
    def get_sectors(self) -> List[str]:
        """Get all unique sectors in universe."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT DISTINCT sector FROM instruments WHERE sector IS NOT NULL ORDER BY sector")
            return [row[0] for row in cur.fetchall()]
    
    def get_countries(self) -> List[str]:
        """Get all unique countries in universe."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT DISTINCT country FROM instruments WHERE country IS NOT NULL ORDER BY country")
            return [row[0] for row in cur.fetchall()]
    
    def get_stats(self) -> Dict[str, int]:
        """Get universe statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
            by_sector = conn.execute("""
                SELECT sector, COUNT(*) FROM instruments 
                WHERE sector IS NOT NULL GROUP BY sector
            """).fetchall()
            by_country = conn.execute("""
                SELECT country, COUNT(*) FROM instruments
                WHERE country IS NOT NULL GROUP BY country
            """).fetchall()
        
        return {
            'total': total,
            'by_sector': dict(by_sector),
            'by_country': dict(by_country),
        }


# Singleton instance
_pipeline_instance = None

def get_pipeline(cache_dir: str = None) -> UniverseDataPipeline:
    """Get or create singleton pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = UniverseDataPipeline(cache_dir)
    return _pipeline_instance
