"""
src/data/quality_checks.py — Data quality validation
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from db.connection import db_manager
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DataQualityChecker:
    """Validates and cleans market data"""
    
    def __init__(self, db=db_manager):
        self.db = db
    
    def check_missing_ohlc(self, symbol: str) -> int:
        """Check for missing OHLC values"""
        db_session = self.db.get_session()
        try:
            from db.models import MarketQuote
            
            missing = db_session.query(MarketQuote).filter(
                MarketQuote.symbol == symbol,
                ((MarketQuote.open == None) | 
                 (MarketQuote.high == None) | 
                 (MarketQuote.low == None) | 
                 (MarketQuote.close == None))
            ).count()
            
            if missing > 0:
                logger.warning(f"  {symbol}: {missing} rows with missing OHLC")
            
            return missing
        finally:
            db_session.close()
    
    def check_duplicates(self, symbol: str) -> int:
        """Check for duplicate timestamps"""
        db_session = self.db.get_session()
        try:
            from db.models import MarketQuote
            
            # Find duplicates
            duplicates = db_session.query(
                MarketQuote.symbol,
                MarketQuote.ts
            ).filter(
                MarketQuote.symbol == symbol
            ).group_by(
                MarketQuote.symbol,
                MarketQuote.ts
            ).having(
                text('COUNT(*) > 1')
            ).count()
            
            if duplicates > 0:
                logger.warning(f"  {symbol}: {duplicates} duplicate timestamps")
            
            return duplicates
        finally:
            db_session.close()
    
    def check_outliers(self, symbol: str, std_dev_threshold: float = 5.0) -> int:
        """Check for outlier prices (> N standard deviations)"""
        db_session = self.db.get_session()
        try:
            from db.models import MarketQuote
            
            # Get last 252 trading days
            quotes = db_session.query(MarketQuote).filter(
                MarketQuote.symbol == symbol
            ).order_by(
                MarketQuote.ts.desc()
            ).limit(252).all()
            
            if len(quotes) < 20:
                return 0
            
            closes = np.array([q.close for q in quotes if q.close])
            
            if len(closes) < 2:
                return 0
            
            # Calculate returns
            returns = np.diff(np.log(closes)) * 100
            
            mean = np.mean(returns)
            std = np.std(returns)
            
            # Find outliers
            if std > 0:
                outliers = np.where(np.abs(returns - mean) > std_dev_threshold * std)[0]
            else:
                outliers = []
            
            if len(outliers) > 0:
                logger.warning(f"  {symbol}: {len(outliers)} outlier moves detected")
            
            return len(outliers)
        finally:
            db_session.close()
    
    def check_data_gaps(self, symbol: str) -> int:
        """Check for gaps in time series"""
        db_session = self.db.get_session()
        try:
            from db.models import MarketQuote
            
            quotes = db_session.query(MarketQuote).filter(
                MarketQuote.symbol == symbol
            ).order_by(
                MarketQuote.ts
            ).all()
            
            if len(quotes) < 2:
                return 0
            
            gaps = 0
            for i in range(1, len(quotes)):
                time_diff = (quotes[i].ts - quotes[i-1].ts).days
                
                # More than 5 days is suspicious
                if time_diff > 5:
                    gaps += 1
            
            if gaps > 0:
                logger.warning(f"  {symbol}: {gaps} suspicious time gaps detected")
            
            return gaps
        finally:
            db_session.close()
    
    def get_record_count(self, symbol: str) -> int:
        """Get total records for a symbol"""
        db_session = self.db.get_session()
        try:
            from db.models import MarketQuote
            return db_session.query(MarketQuote).filter(
                MarketQuote.symbol == symbol
            ).count()
        finally:
            db_session.close()
    
    def run_all_checks(self, symbols: List[str]) -> Dict[str, Dict]:
        """Run all quality checks on symbols"""
        results = {}
        
        for symbol in symbols:
            logger.info(f"Running quality checks on {symbol}...")
            
            results[symbol] = {
                'records': self.get_record_count(symbol),
                'missing_ohlc': self.check_missing_ohlc(symbol),
                'duplicates': self.check_duplicates(symbol),
                'outliers': self.check_outliers(symbol),
                'gaps': self.check_data_gaps(symbol),
                'timestamp': datetime.now().isoformat()
            }
        
        return results
    
    def clean_duplicates(self, symbol: str, keep='first') -> int:
        """Remove duplicate timestamps"""
        db_session = self.db.get_session()
        try:
            from db.models import MarketQuote
            
            # Get duplicates
            duplicates = db_session.query(
                MarketQuote.symbol,
                MarketQuote.ts
            ).filter(
                MarketQuote.symbol == symbol
            ).group_by(
                MarketQuote.symbol,
                MarketQuote.ts
            ).having(
                text('COUNT(*) > 1')
            ).all()
            
            deleted = 0
            for dup_symbol, dup_ts in duplicates:
                # Get all rows for this timestamp
                rows = db_session.query(MarketQuote).filter(
                    MarketQuote.symbol == dup_symbol,
                    MarketQuote.ts == dup_ts
                ).order_by(
                    MarketQuote.id
                ).all()
                
                # Delete all but first
                if keep == 'first':
                    for row in rows[1:]:
                        db_session.delete(row)
                        deleted += 1
            
            db_session.commit()
            logger.info(f"Cleaned {deleted} duplicate rows for {symbol}")
            return deleted
            
        except Exception as e:
            logger.error(f"Clean duplicates failed: {e}")
            db_session.rollback()
            return 0
        finally:
            db_session.close()

# Main execution
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    checker = DataQualityChecker()
    
    print("\n" + "="*60)
    print("RAVINALA v3.0 — Data Quality Check")
    print("="*60)
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', '^GSPC', 'GC=F']
    results = checker.run_all_checks(symbols)
    
    print("\n=== DATA QUALITY REPORT ===\n")
    for symbol, checks in results.items():
        print(f"{symbol}:")
        print(f"  Records: {checks.get('records', 0):,}")
        print(f"  Missing OHLC: {checks.get('missing_ohlc', 0)}")
        print(f"  Duplicates: {checks.get('duplicates', 0)}")
        print(f"  Outliers: {checks.get('outliers', 0)}")
        print(f"  Gaps: {checks.get('gaps', 0)}")
        print()
    
    print("="*60)
    print("Quality check complete!")
    print("="*60)
