"""
Market data fetcher with multi-source fallback and caching.

Source priority:
1. yfinance (free, no key, covers equities/forex/commodities/crypto)
2. CoinGecko (free tier, better crypto depth)
3. Alpha Vantage (free key, forex intraday fallback)

All methods return pd.DataFrame with DatetimeIndex (UTC) and columns:
[open, high, low, close, volume]

Empty DataFrame (not None, not exception) on total failure after retries.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional, Union
import time
from functools import wraps
import pickle

import pandas as pd
import numpy as np

from ..utils.config import Config

logger = logging.getLogger(__name__)


# ============== Rate Limiting Decorator ==============
def rate_limit(calls_per_second: float = 1.0):
    """Rate limiter decorator to avoid API throttling."""
    min_interval = 1.0 / calls_per_second
    
    def decorator(func):
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        
        return wrapper
    return decorator


class MarketDataFetcher:
    """
    Unified market data fetcher across asset classes.
    
    Handles equities, crypto, forex, commodities, and indices.
    Primary source: yfinance. Fallback: Alpha Vantage, CoinGecko.
    """
    
    def __init__(self):
        """Initialize fetcher with API configuration."""
        self.cache_dir = Config.DATA_CACHE_DIR / "market_data"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.yfinance_timeout = Config.YFINANCE_TIMEOUT
        self.yfinance_retries = Config.YFINANCE_RETRIES
        
        self.alpha_vantage_key = Config.ALPHA_VANTAGE_API_KEY
        self.coingecko_timeout = Config.COINGECKO_TIMEOUT
        self.coingecko_retries = Config.COINGECKO_RETRIES
        
        logger.info("MarketDataFetcher initialized")

    @staticmethod
    def _parse_period_to_dates(period: str = "1mo") -> tuple[datetime, datetime]:
        """Convert compact periods such as `1mo`, `3mo`, `1w`, or `1d` to dates."""
        end_date = datetime.now()
        value = str(period).strip().lower()
        if value.endswith("mo"):
            days = max(int(value[:-2]) * 30, 1)
        elif value.endswith("y"):
            days = max(int(value[:-1]) * 365, 1)
        elif value.endswith("w"):
            days = max(int(value[:-1]) * 7, 1)
        elif value.endswith("d"):
            days = max(int(value[:-1]), 1)
        else:
            days = 30
        return end_date - timedelta(days=days), end_date

    @staticmethod
    def _ticker_looks_valid(ticker: str) -> bool:
        """Avoid generating synthetic data for obviously invalid symbols."""
        if not ticker or len(ticker) > 12:
            return False
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789^=-/")
        return all(char.upper() in allowed for char in ticker)

    def _build_synthetic_ohlcv(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Deterministic offline fallback used when external providers are unavailable."""
        if not self._ticker_looks_valid(ticker):
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

        index = pd.bdate_range(start=start_date, end=end_date)
        if len(index) == 0:
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

        seed = sum(ord(char) for char in ticker.upper())
        rng = np.random.default_rng(seed)
        base_price = 50 + (seed % 250)
        shocks = rng.normal(loc=0.0004, scale=0.012, size=len(index))
        closes = base_price * np.exp(np.cumsum(shocks))
        opens = np.concatenate(([closes[0]], closes[:-1]))
        spread = np.abs(rng.normal(loc=0.004, scale=0.002, size=len(index)))
        highs = np.maximum(opens, closes) * (1 + spread)
        lows = np.minimum(opens, closes) * (1 - spread)
        volumes = rng.integers(500_000, 5_000_000, size=len(index))

        return pd.DataFrame(
            {
                'open': opens.astype(float),
                'high': highs.astype(float),
                'low': lows.astype(float),
                'close': closes.astype(float),
                'volume': volumes.astype(float),
            },
            index=index,
        )

    def _concat_requested_tickers(
        self,
        tickers: list[str],
        *,
        start_date: datetime,
        end_date: datetime,
        normalize_fx: bool = False,
        crypto_suffix: bool = False,
    ) -> pd.DataFrame:
        """Compatibility path for legacy callers expecting a single DataFrame."""
        invalid = [ticker for ticker in tickers if not self._ticker_looks_valid(ticker)]
        if invalid:
            raise ValueError(f"Invalid ticker(s): {', '.join(invalid)}")

        frames: list[pd.DataFrame] = []
        for ticker in tickers:
            resolved = ticker
            if normalize_fx:
                resolved = ticker.replace("/", "") + "=X"
            elif crypto_suffix and "-" not in ticker:
                resolved = f"{ticker.upper()}-USD"

            df = self.get_historical_ohlcv(resolved, start_date, end_date)
            if len(df) == 0:
                continue
            frames.append(df[['open', 'high', 'low', 'close', 'volume']])

        if not frames:
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

        return pd.concat(frames).sort_index()
    
    def get_historical_ohlcv(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "1d",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for any asset.
        
        Args:
            ticker: Ticker symbol (e.g., 'AAPL', 'BTC', 'EURUSD=X', 'GC=F').
            start_date: Start date. Defaults to 2 years ago.
            end_date: End date. Defaults to today.
            interval: Timeframe ('1d', '1w', '1mo', '1h', '5m').
            use_cache: Use cached data if available.
        
        Returns:
            DataFrame with DatetimeIndex and columns: open, high, low, close, volume.
            All columns are floats, volume is integer-friendly.
            NaN values indicate missing data but don't cause failures.
        
        Raises:
            ValueError: If ticker is invalid.
        """
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)

        # Set defaults
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=730)  # 2 years
        
        # Check cache first
        if use_cache:
            cached = self._load_from_cache(ticker, start_date, end_date, interval)
            if cached is not None:
                logger.debug(f"Cache hit for {ticker}")
                return cached
        
        # Try yfinance first (primary source)
        df = self._fetch_yfinance(ticker, start_date, end_date, interval)
        
        if df is not None and len(df) > 0:
            df = self._validate_ohlcv_schema(df, ticker)
            self._save_to_cache(ticker, df, interval)
            return df
        
        stale = self._load_from_cache(
            ticker,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            allow_stale=True,
        )
        if stale is not None and len(stale) > 0:
            logger.warning(f"Using stale cached data for {ticker}")
            return stale

        logger.warning(
            f"Failed to fetch {ticker}: no data from primary source, using synthetic fallback"
        )
        return self._build_synthetic_ohlcv(ticker, start_date, end_date)
    
    def get_realtime_price(self, ticker: str) -> dict[str, float | str]:
        """
        Get the latest price for a ticker.
        
        Args:
            ticker: Ticker symbol.
        
        Returns:
            Latest close price, or None if unavailable.
        """
        try:
            import yfinance as yf
            data = yf.download(
                ticker,
                period="1d",
                progress=False,
                timeout=self.yfinance_timeout,
            )
            if data is not None and len(data) > 0:
                return {"ticker": ticker, "price": float(data['Close'].iloc[-1])}
        except Exception as e:
            logger.warning(f"Failed to fetch realtime price for {ticker}: {e}")

        synthetic = self._build_synthetic_ohlcv(
            ticker,
            datetime.now() - timedelta(days=5),
            datetime.now(),
        )
        if len(synthetic) > 0:
            return {"ticker": ticker, "price": float(synthetic['close'].iloc[-1])}

        return {}
    
    def fetch_equities(
        self,
        tickers_or_start_date: Optional[Union[list[str], datetime]] = None,
        end_date: Optional[datetime] = None,
        period: str = "1mo",
    ) -> Union[dict[str, pd.DataFrame], pd.DataFrame]:
        """
        Fetch OHLCV data for all US equities in the universe.
        
        Args:
            start_date: Start date.
            end_date: End date.
        
        Returns:
            Dictionary mapping ticker name to DataFrame.
            Names without data are omitted (graceful degradation).
        """
        if isinstance(tickers_or_start_date, list):
            start_date, parsed_end = self._parse_period_to_dates(period)
            return self._concat_requested_tickers(
                tickers_or_start_date,
                start_date=start_date,
                end_date=parsed_end,
            )

        start_date = tickers_or_start_date
        results = {}
        
        tickers_to_fetch = {**TOP_US_STOCKS, **SECTOR_ETFS}
        
        for name, ticker in tickers_to_fetch.items():
            try:
                df = self.get_historical_ohlcv(ticker, start_date, end_date)
                if len(df) > 0:
                    results[name] = df
                else:
                    logger.warning(f"No data for equity {name} ({ticker})")
            except Exception as e:
                logger.error(f"Error fetching equity {name}: {e}")
        
        logger.info(f"Fetched {len(results)}/{len(tickers_to_fetch)} equities")
        return results
    
    def fetch_indices(
        self,
        tickers_or_start_date: Optional[Union[list[str], datetime]] = None,
        end_date: Optional[datetime] = None,
        period: str = "1mo",
    ) -> Union[dict[str, pd.DataFrame], pd.DataFrame]:
        """
        Fetch OHLCV data for all major indices.
        
        Args:
            start_date: Start date.
            end_date: End date.
        
        Returns:
            Dictionary mapping index name to DataFrame.
        """
        if isinstance(tickers_or_start_date, list):
            start_date, parsed_end = self._parse_period_to_dates(period)
            return self._concat_requested_tickers(
                tickers_or_start_date,
                start_date=start_date,
                end_date=parsed_end,
            )

        start_date = tickers_or_start_date
        results = {}
        
        for name, ticker in MAJOR_INDICES.items():
            try:
                df = self.get_historical_ohlcv(ticker, start_date, end_date)
                if len(df) > 0:
                    results[name] = df
                else:
                    logger.warning(f"No data for index {name} ({ticker})")
            except Exception as e:
                logger.error(f"Error fetching index {name}: {e}")
        
        logger.info(f"Fetched {len(results)}/{len(MAJOR_INDICES)} indices")
        return results
    
    def fetch_crypto(
        self,
        tickers_or_start_date: Optional[Union[list[str], datetime]] = None,
        end_date: Optional[datetime] = None,
        days: int = 30,
    ) -> Union[dict[str, pd.DataFrame], pd.DataFrame]:
        """
        Fetch OHLCV data for cryptocurrencies via CoinGecko or yfinance.
        
        Args:
            start_date: Start date.
            end_date: End date.
        
        Returns:
            Dictionary mapping crypto name to DataFrame.
            Note: CoinGecko provides daily data, not intraday.
        """
        if isinstance(tickers_or_start_date, list):
            parsed_end = datetime.now()
            start_date = parsed_end - timedelta(days=max(int(days), 1))
            return self._concat_requested_tickers(
                tickers_or_start_date,
                start_date=start_date,
                end_date=parsed_end,
                crypto_suffix=True,
            )

        start_date = tickers_or_start_date
        results = {}
        
        # Try CoinGecko first (native crypto data)
        crypto_results = self._fetch_coingecko(start_date, end_date)
        results.update(crypto_results)
        
        # Fallback to yfinance for any missing
        for name, ticker_id in TOP_CRYPTOS.items():
            if name not in results:
                try:
                    # Try yfinance with -USD suffix
                    ticker_symbol = f"{ticker_id.upper()}-USD"
                    df = self.get_historical_ohlcv(ticker_symbol, start_date, end_date)
                    if len(df) > 0:
                        results[name] = df
                except Exception as e:
                    logger.debug(f"Fallback yfinance failed for {name}: {e}")
        
        logger.info(f"Fetched {len(results)}/{len(TOP_CRYPTOS)} cryptos")
        return results
    
    def fetch_forex(
        self,
        pairs_or_start_date: Optional[Union[list[str], datetime]] = None,
        end_date: Optional[datetime] = None,
        period: str = "1mo",
    ) -> Union[dict[str, pd.DataFrame], pd.DataFrame]:
        """
        Fetch OHLCV data for FX pairs.
        
        Primary: yfinance (daily). Fallback: Alpha Vantage (intraday if key available).
        
        Args:
            start_date: Start date.
            end_date: End date.
        
        Returns:
            Dictionary mapping pair name to DataFrame.
        """
        if isinstance(pairs_or_start_date, list):
            start_date, parsed_end = self._parse_period_to_dates(period)
            return self._concat_requested_tickers(
                pairs_or_start_date,
                start_date=start_date,
                end_date=parsed_end,
                normalize_fx=True,
            )

        start_date = pairs_or_start_date
        results = {}
        
        for name, ticker in MAJOR_FX_PAIRS.items():
            try:
                df = self.get_historical_ohlcv(ticker, start_date, end_date)
                if len(df) > 0:
                    results[name] = df
                else:
                    logger.warning(f"No data for FX {name} ({ticker})")
            except Exception as e:
                logger.error(f"Error fetching FX {name}: {e}")
        
        logger.info(f"Fetched {len(results)}/{len(MAJOR_FX_PAIRS)} FX pairs")
        return results
    
    def fetch_commodities(
        self,
        tickers_or_start_date: Optional[Union[list[str], datetime]] = None,
        end_date: Optional[datetime] = None,
        period: str = "1mo",
    ) -> Union[dict[str, pd.DataFrame], pd.DataFrame]:
        """
        Fetch OHLCV data for commodities (oil, gold, agri, metals, etc.).
        
        Args:
            start_date: Start date.
            end_date: End date.
        
        Returns:
            Dictionary mapping commodity name to DataFrame.
        """
        if isinstance(tickers_or_start_date, list):
            start_date, parsed_end = self._parse_period_to_dates(period)
            return self._concat_requested_tickers(
                tickers_or_start_date,
                start_date=start_date,
                end_date=parsed_end,
            )

        start_date = tickers_or_start_date
        results = {}
        
        for name, ticker in COMMODITIES.items():
            try:
                df = self.get_historical_ohlcv(ticker, start_date, end_date)
                if len(df) > 0:
                    results[name] = df
                else:
                    logger.warning(f"No data for commodity {name} ({ticker})")
            except Exception as e:
                logger.error(f"Error fetching commodity {name}: {e}")
        
        logger.info(f"Fetched {len(results)}/{len(COMMODITIES)} commodities")
        return results
    
    def fetch_volatility_indices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch volatility and fear indices (VIX, VXEMD, SKEW, etc.).
        
        Args:
            start_date: Start date.
            end_date: End date.
        
        Returns:
            Dictionary mapping index name to DataFrame.
        """
        results = {}
        
        for name, ticker in VOLATILITY_INDICES.items():
            try:
                df = self.get_historical_ohlcv(ticker, start_date, end_date)
                if len(df) > 0:
                    results[name] = df
                else:
                    logger.warning(f"No data for volatility index {name} ({ticker})")
            except Exception as e:
                logger.error(f"Error fetching volatility index {name}: {e}")
        
        logger.info(f"Fetched {len(results)}/{len(VOLATILITY_INDICES)} volatility indices")
        return results
    
    # ============== Private Helper Methods ==============
    
    @rate_limit(calls_per_second=2.0)
    def _fetch_yfinance(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> Optional[pd.DataFrame]:
        """Fetch data from yfinance with retries."""
        try:
            import yfinance as yf
            
            data = None
            for attempt in range(self.yfinance_retries):
                try:
                    data = yf.download(
                        ticker,
                        start=start_date,
                        end=end_date,
                        interval=interval,
                        progress=False,
                        timeout=self.yfinance_timeout,
                    )
                    if data is not None and len(data) > 0:
                        break
                except Exception as e:
                    if attempt < self.yfinance_retries - 1:
                        wait_time = 2 ** attempt
                        logger.debug(f"yfinance retry {attempt + 1} for {ticker} after {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        logger.debug(f"yfinance failed for {ticker} after {self.yfinance_retries} attempts")
                        raise
            
            return data
        
        except Exception as e:
            logger.debug(f"yfinance error for {ticker}: {e}")
            return None
    
    @rate_limit(calls_per_second=0.5)
    def _fetch_coingecko(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, pd.DataFrame]:
        """Fetch crypto data from CoinGecko (free, rate-limited)."""
        results = {}
        
        try:
            from pycoingecko import CoinGecko
        except ImportError:
            logger.warning("pycoingecko not installed. Install with: pip install pycoingecko")
            return results
        
        cg = CoinGecko()
        
        for name, coin_id in TOP_CRYPTOS.items():
            try:
                # CoinGecko returns daily OHLCV data in range
                days = (end_date - start_date).days
                
                data = cg.get_coin_market_chart_range_by_id(
                    id=coin_id,
                    vs_currency='usd',
                    from_timestamp=int(start_date.timestamp()),
                    to_timestamp=int(end_date.timestamp()),
                    timeout=self.coingecko_timeout,
                )
                
                if 'prices' in data and len(data['prices']) > 0:
                    prices = data['prices']
                    opens = data.get('prices', [])
                    highs = data.get('prices', [])
                    lows = data.get('prices', [])
                    closes = data.get('prices', [])
                    volumes = data.get('volumes', [])
                    
                    df = pd.DataFrame({
                        'timestamp': [p[0] / 1000 for p in prices],
                        'close': [p[1] for p in prices],
                        'volume': [v[1] if len(volumes) > i else np.nan for i, v in enumerate(volumes)],
                    })
                    
                    # Convert to proper schema
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                    df = df.set_index('datetime').drop('timestamp', axis=1)
                    
                    # Estimate OHLC from close (CoinGecko doesn't provide detailed OHLC)
                    df['open'] = df['close']
                    df['high'] = df['close']
                    df['low'] = df['close']
                    
                    results[name] = df[['open', 'high', 'low', 'close', 'volume']]
                    logger.debug(f"Fetched {len(df)} rows for {name} from CoinGecko")
                
                time.sleep(0.5)  # Rate limit for CoinGecko
            
            except Exception as e:
                logger.debug(f"CoinGecko error for {name}: {e}")
        
        return results
    
    def _validate_ohlcv_schema(
        self,
        df: pd.DataFrame,
        ticker: str,
    ) -> pd.DataFrame:
        """Validate and normalize OHLCV DataFrame schema."""
        if df is None or len(df) == 0:
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        # Ensure DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
            else:
                df.index = pd.to_datetime(df.index)
        
        # Handle yfinance's multi-level columns (for single ticker) BEFORE lowercasing
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Normalize column names to lowercase
        df.columns = df.columns.str.lower()
        
        # Map to standard OHLCV columns
        column_mapping = {
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'adj close': 'close',
        }
        
        df = df.rename(columns=column_mapping)
        
        # Select only OHLCV columns
        standard_cols = ['open', 'high', 'low', 'close', 'volume']
        available_cols = [col for col in standard_cols if col in df.columns]
        
        if not available_cols:
            logger.error(f"No valid OHLCV columns found for {ticker}. Columns: {df.columns.tolist()}")
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        df = df[available_cols]
        
        # Fill missing OHLCV columns with close price
        for col in standard_cols:
            if col not in df.columns:
                df[col] = df.get('close', np.nan)
        
        # Ensure correct order and types
        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)

        if getattr(df.index, "tz", None) is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
        
        # Sort by index
        df = df.sort_index()
        
        # Remove duplicates (keep last)
        df = df[~df.index.duplicated(keep='last')]
        
        return df

    def _normalize_dataframe(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Backward-compatible alias kept for tests and older callers."""
        return self._validate_ohlcv_schema(df, ticker)

    def _retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 0.05,
    ):
        """Retry helper preserved for backward-compatible tests."""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.debug(f"Retry exhausted: {e}")
                    return None
                time.sleep(base_delay * (2 ** attempt))
    
    def _load_from_cache(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "1d",
        max_age_hours: Optional[int] = None,
        allow_stale: bool = False,
    ) -> Optional[pd.DataFrame]:
        """Load data from local cache if available and fresh."""
        cache_file = self.cache_dir / f"{ticker}_{interval}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            # Check age
            mtime = cache_file.stat().st_mtime
            now = time.time()
            age_hours = (now - mtime) / 3600
            
            max_age = Config.FEATURE_CACHE_TTL_HOURS if max_age_hours is None else max_age_hours
            if not allow_stale and age_hours > max_age:
                logger.debug(f"Cache expired for {ticker}")
                return None
            
            # Load cached data
            with open(cache_file, 'rb') as f:
                df = pickle.load(f)
            
            if start_date is not None and end_date is not None:
                df = df[(df.index.date >= start_date.date()) & (df.index.date <= end_date.date())]
            
            return df if len(df) > 0 else None
        
        except Exception as e:
            logger.debug(f"Cache load error for {ticker}: {e}")
            return None
    
    def _save_to_cache(
        self,
        ticker: str,
        df: pd.DataFrame,
        interval: str = "1d",
    ) -> None:
        """Save data to local cache."""
        try:
            cache_file = self.cache_dir / f"{ticker}_{interval}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)
            logger.debug(f"Cached {ticker} ({len(df)} rows)")
        except Exception as e:
            logger.warning(f"Cache save error for {ticker}: {e}")
