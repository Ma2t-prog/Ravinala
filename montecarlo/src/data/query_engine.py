"""
src/data/query_engine.py — Query layer with intelligent caching
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from db.connection import db_manager
from cache.redis_manager import redis_cache
import json

logger = logging.getLogger(__name__)

class QueryEngine:
    """Query layer with intelligent caching"""
    
    def __init__(self, db=db_manager, cache=redis_cache):
        self.db = db
        self.cache = cache
    
    def get_price_with_cache(self, symbol: str) -> Optional[Dict]:
        """
        Get latest price with Redis caching.
        TTL: 2 seconds for real-time data
        """
        # Try cache first
        cached = self.cache.get_price(symbol)
        if cached:
            logger.debug(f"Cache hit: {symbol} (price={cached.get('price')})")
            return cached
        
        # Query DB
        price_data = self.db.get_latest_price(symbol)
        
        if price_data:
            # Cache for future
            self.cache.set_price(symbol, price_data['price'])
            logger.debug(f"Cached: {symbol}")
            return price_data
        
        return None
    
    def get_ohlcv_with_cache(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get OHLCV data with caching.
        For daily data, cache for 1 hour.
        """
        # Cache key
        cache_key = f"ohlcv:{symbol}:{start_date.date()}:{end_date.date()}"
        
        # Try cache
        try:
            cached = self.cache.client.get(cache_key) if self.cache.client else None
            if cached:
                logger.debug(f"OHLCV cache hit: {symbol}")
                return pd.read_json(cached)
        except Exception as e:
            logger.debug(f"Cache read error (non-critical): {e}")
        
        # Query DB
        quotes = self.db.get_ohlcv_range(symbol, start_date, end_date)
        
        if quotes:
            df = pd.DataFrame(quotes)
            
            # Cache for 1 hour (3600s)
            try:
                if self.cache.client:
                    self.cache.client.setex(
                        cache_key,
                        3600,
                        df.to_json()
                    )
                    logger.debug(f"OHLCV cached: {symbol}")
            except Exception as e:
                logger.debug(f"Cache write error (non-critical): {e}")
            
            return df
        
        return pd.DataFrame()
    
    def get_multiple_ohlcv(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """Get OHLCV for multiple symbols efficiently"""
        results = {}
        
        logger.info(f"Fetching OHLCV for {len(symbols)} symbols...")
        for symbol in symbols:
            results[symbol] = self.get_ohlcv_with_cache(symbol, start_date, end_date)
        
        return results
    
    def calculate_correlation_cached(
        self,
        symbols: List[str],
        lookback_days: int = 252
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix with caching.
        TTL: 1 hour for average lookback
        """
        # Try cache
        cached = self.cache.get_correlation_matrix()
        if cached and cached.get('symbols') == symbols:
            logger.info(f"Correlation matrix cache hit ({len(symbols)} symbols)")
            data = cached.get('matrix', {})
            return pd.DataFrame(data, index=symbols, columns=symbols)
        
        # Recalculate
        logger.info(f"Calculating correlation for {len(symbols)} symbols ({lookback_days} days)...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Get data for all symbols
        data_dict = self.get_multiple_ohlcv(symbols, start_date, end_date)
        
        # Combine into single DataFrame
        df = pd.DataFrame()
        for symbol, symbol_df in data_dict.items():
            if not symbol_df.empty:
                df[symbol] = symbol_df['close']
        
        if df.empty:
            logger.warning("No data available for correlation calculation")
            return pd.DataFrame()
        
        # Calculate returns and correlation
        returns = df.pct_change().dropna()
        corr_matrix = returns.corr()
        
        # Cache result (1 hour)
        try:
            self.cache.set_correlation_matrix(
                symbols,
                corr_matrix.to_dict()
            )
            logger.info(f"Correlation matrix cached ({len(symbols)} symbols)")
        except Exception as e:
            logger.warning(f"Could not cache correlation matrix: {e}")
        
        return corr_matrix
    
    def get_price_series(
        self,
        symbol: str,
        days: int = 252
    ) -> pd.Series:
        """Get price series for analysis (returns, volatility, etc)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = self.get_ohlcv_with_cache(symbol, start_date, end_date)
        
        if df.empty:
            return pd.Series()
        
        return df['close']
    
    def get_price_returns(
        self,
        symbol: str,
        days: int = 252
    ) -> pd.Series:
        """Get daily log returns"""
        series = self.get_price_series(symbol, days)
        
        if series.empty:
            return pd.Series()
        
        return np.log(series / series.shift(1)).dropna()
    
    def health_check(self) -> Dict[str, bool]:
        """Check database and cache connectivity"""
        return {
            'database': self.db.health_check(),
            'cache': self.cache.health_check(),
            'timestamp': datetime.now().isoformat()
        }

# Import numpy for calculations
import numpy as np

# Singleton instance
query_engine = QueryEngine()

# Main execution
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("RAVINALA v3.0 — Query Engine Test")
    print("="*60)
    
    # Health check
    print("\nSystem health check...")
    health = query_engine.health_check()
    for service, status in health.items():
        if service != 'timestamp':
            symbol = "PASS" if status else "FAIL"
            print(f"  {symbol} {service}: {'OK' if status else 'FAILED'}")
    
    # Get latest price
    print("\nFetching latest prices...")
    for symbol in ['AAPL', 'MSFT', 'GOOGL']:
        price = query_engine.get_price_with_cache(symbol)
        if price:
            print(f"  {symbol}: ${price['price']:.2f}")
    
    # Get OHLCV
    print("\nFetching 30-day OHLCV...")
    end = datetime.now()
    start = end - timedelta(days=30)
    df = query_engine.get_ohlcv_with_cache('AAPL', start, end)
    print(f"  AAPL: {len(df)} days of data")
    
    # Calculate correlation
    print("\nCalculating correlation...")
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    corr = query_engine.calculate_correlation_cached(symbols)
    print(f"  Correlation matrix ({len(symbols)} symbols):")
    print(f"    AAPL-MSFT: {corr.loc['AAPL', 'MSFT']:.3f}")
    print(f"    MSFT-GOOGL: {corr.loc['MSFT', 'GOOGL']:.3f}")
    
    print("\n" + "="*60)
    print("Query engine test complete!")
    print("="*60)
