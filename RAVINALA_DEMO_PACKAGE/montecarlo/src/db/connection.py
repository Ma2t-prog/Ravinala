"""
src/db/connection.py — Database connection manager
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from db.models import SessionLocal, engine
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = SessionLocal
    
    def get_session(self) -> Session:
        """Get a new database session"""
        return self.session_factory()
    
    def health_check(self) -> bool:
        """Check if database is healthy"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def insert_quotes_batch(self, quotes: List[Dict], batch_size: int = 1000) -> int:
        """
        Bulk insert quotes (efficient for large datasets).
        Returns count of inserted rows.
        """
        db = self.get_session()
        try:
            from db.models import MarketQuote
            
            total_inserted = 0
            for i in range(0, len(quotes), batch_size):
                batch = quotes[i:i+batch_size]
                db.bulk_insert_mappings(MarketQuote, batch)
                db.commit()
                total_inserted += len(batch)
                logger.debug(f"Inserted batch of {len(batch)} quotes")
            
            return total_inserted
                
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """Get the latest price for a symbol"""
        db = self.get_session()
        try:
            from db.models import MarketQuote
            
            quote = db.query(MarketQuote)\
                .filter(MarketQuote.symbol == symbol)\
                .order_by(MarketQuote.ts.desc())\
                .first()
            
            if quote:
                return {
                    'symbol': quote.symbol,
                    'price': quote.close,
                    'timestamp': quote.ts,
                    'open': quote.open,
                    'high': quote.high,
                    'low': quote.low,
                    'volume': quote.volume
                }
            return None
        finally:
            db.close()
    
    def get_ohlcv_range(self, symbol: str, start_ts: datetime, end_ts: datetime) -> List[Dict]:
        """Get OHLCV data for a symbol within a time range"""
        db = self.get_session()
        try:
            from db.models import MarketQuote
            
            quotes = db.query(MarketQuote)\
                .filter(
                    MarketQuote.symbol == symbol,
                    MarketQuote.ts >= start_ts,
                    MarketQuote.ts <= end_ts
                )\
                .order_by(MarketQuote.ts)\
                .all()
            
            return [{
                'symbol': q.symbol,
                'ts': q.ts,
                'open': q.open,
                'high': q.high,
                'low': q.low,
                'close': q.close,
                'adj_close': q.adj_close,
                'volume': q.volume
            } for q in quotes]
        finally:
            db.close()
    
    def get_price_history(self, symbol: str, days: int = 252) -> List[float]:
        """Get close price history for last N days"""
        db = self.get_session()
        try:
            from db.models import MarketQuote
            from datetime import timedelta
            
            start_ts = datetime.now() - timedelta(days=days)
            
            quotes = db.query(MarketQuote)\
                .filter(
                    MarketQuote.symbol == symbol,
                    MarketQuote.ts >= start_ts
                )\
                .order_by(MarketQuote.ts)\
                .all()
            
            return [q.close for q in quotes if q.close is not None]
        finally:
            db.close()
    
    def get_multiple_symbols(self, symbols: List[str], start_ts: datetime, end_ts: datetime) -> Dict[str, List[Dict]]:
        """Get OHLCV data for multiple symbols"""
        results = {}
        for symbol in symbols:
            results[symbol] = self.get_ohlcv_range(symbol, start_ts, end_ts)
        return results
    
    def delete_old_data(self, older_than_days: int = 1825) -> int:
        """Delete data older than N days (default 5 years)"""
        db = self.get_session()
        try:
            from db.models import MarketQuote
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            
            deleted = db.query(MarketQuote)\
                .filter(MarketQuote.ts < cutoff_date)\
                .delete()
            
            db.commit()
            logger.info(f"Deleted {deleted} rows older than {older_than_days} days")
            return deleted
        except Exception as e:
            logger.error(f"Delete old data failed: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

# Singleton instance
db_manager = DatabaseManager()
