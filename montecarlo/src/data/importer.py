"""
src/data/importer.py — Historical data importer from yFinance
"""

import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from db.connection import db_manager

logger = logging.getLogger(__name__)

class HistoricalDataImporter:
    """Downloads and imports historical OHLCV data"""
    
    def __init__(self):
        self.db = db_manager
    
    def import_from_yfinance(
        self,
        symbols: List[str],
        start_date: str = None,
        end_date: str = None,
        interval: str = '1d'
    ) -> Dict[str, int]:
        """
        Import historical data from Yahoo Finance.
        
        Args:
            symbols: List of ticker symbols
            start_date: YYYY-MM-DD (default: 5 years ago)
            end_date: YYYY-MM-DD (default: today)
            interval: '1d', '1h', '5m', etc
        
        Returns:
            Dict with symbol -> count of inserted rows
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Importing from {start_date} to {end_date}")
        results = {}
        
        for symbol in symbols:
            try:
                logger.info(f"  Downloading {symbol}...")
                
                # Download data
                data = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    progress=False
                )
                
                if data.empty:
                    logger.warning(f"    No data for {symbol}")
                    results[symbol] = 0
                    continue
                
                # Prepare for insertion
                quotes = []
                for ts, row in data.iterrows():
                    quotes.append({
                        'symbol': symbol,
                        'ts': ts,
                        'open': float(row['Open']) if pd.notna(row['Open']) else None,
                        'high': float(row['High']) if pd.notna(row['High']) else None,
                        'low': float(row['Low']) if pd.notna(row['Low']) else None,
                        'close': float(row['Close']) if pd.notna(row['Close']) else None,
                        'adj_close': float(row['Adj Close']) if pd.notna(row['Adj Close']) else None,
                        'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                        'source': 'yfinance',
                        'interval': interval
                    })
                
                # Batch insert
                count = self.db.insert_quotes_batch(quotes)
                results[symbol] = count
                logger.info(f"    Imported {count} rows for {symbol}")
                
            except Exception as e:
                logger.error(f"    Failed to import {symbol}: {e}")
                results[symbol] = 0
        
        return results
    
    def import_indices(self) -> Dict[str, int]:
        """Import 30 global indices"""
        indices = [
            # US
            '^GSPC',   # S&P 500
            '^IXIC',   # NASDAQ
            '^DJI',    # Dow Jones
            '^IXRF',   # Russell 2000
            
            # Europe
            '^STOXX',  # EURO STOXX 50
            '^GDAXI',  # DAX (Germany)
            '^FCHI',   # CAC 40 (France)
            '^FTSE',   # FTSE 100 (UK)
            '^IBEX',   # IBEX 35 (Spain)
            '^FTIT',   # FTSE MIB (Italy)
            
            # Asia
            '^N225',   # Nikkei 225
            '^HSI',    # Hang Seng
            '000001.SS',  # Shanghai Composite
            '^AXJO',   # ASX 200
            
            # Volatility & Yields
            '^VIX',    # Volatility Index
            '^TNX',    # 10Y Treasury Yield
            '^FVX',    # 5Y Treasury Yield
        ]
        
        logger.info(f"Importing {len(indices)} indices...")
        results = self.import_from_yfinance(indices)
        
        count = sum(results.values())
        logger.info(f"Index import complete: {count} total rows")
        return results
    
    def import_commodities(self) -> Dict[str, int]:
        """Import commodities"""
        commodities = [
            'GC=F',     # Gold
            'SI=F',     # Silver
            'CL=F',     # WTI Oil
            'NG=F',     # Natural Gas
            'CT=F',     # Cotton
            'SB=F',     # Sugar
            'KC=F',     # Coffee
            'ZC=F',     # Corn
        ]
        
        logger.info(f"Importing {len(commodities)} commodities...")
        results = self.import_from_yfinance(commodities)
        
        count = sum(results.values())
        logger.info(f"Commodity import complete: {count} total rows")
        return results
    
    def import_stocks(self, symbols: List[str] = None) -> Dict[str, int]:
        """Import major stocks"""
        if not symbols:
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 
                      'META', 'JPM', 'BA', 'GS', 'CVX', 'XOM']
        
        logger.info(f"Importing {len(symbols)} stocks...")
        results = self.import_from_yfinance(symbols)
        
        count = sum(results.values())
        logger.info(f"Stock import complete: {count} total rows")
        return results
    
    def import_forex(self) -> Dict[str, int]:
        """Import forex pairs"""
        forex = [
            'EURUSD=X',
            'GBPUSD=X',
            'JPYUSD=X',
            'CHFUSD=X',
            'AUDUSD=X',
            'NZDUSD=X',
        ]
        
        logger.info(f"Importing {len(forex)} forex pairs...")
        results = self.import_from_yfinance(forex)
        
        count = sum(results.values())
        logger.info(f"Forex import complete: {count} total rows")
        return results
    
    def update_daily(self, symbols: List[str]) -> Dict[str, int]:
        """Efficient daily update: fetch only yesterday's data"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Daily update for {len(symbols)} symbols...")
        return self.import_from_yfinance(symbols, start_date=yesterday, end_date=today)

# Main execution
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    importer = HistoricalDataImporter()
    
    print("\n" + "="*60)
    print("RAVINALA v3.0 — Historical Data Importer")
    print("="*60)
    
    # Import indices
    print("\n1.  Importing global indices...")
    importer.import_indices()
    
    # Import stocks
    print("\n2.  Importing major stocks...")
    importer.import_stocks()
    
    # Import commodities
    print("\n3.  Importing commodities...")
    importer.import_commodities()
    
    # Import forex
    print("\n4.  Importing forex pairs...")
    importer.import_forex()
    
    print("\n" + "="*60)
    print("Historical data import COMPLETE!")
    print("="*60)
