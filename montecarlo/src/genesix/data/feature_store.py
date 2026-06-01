"""
Unified feature store for GenesiX.

Builds comprehensive feature matrices from:
- Price data (returns, volatility, momentum, technical indicators)
- Macroeconomic data (unemployment, inflation, yields)
- Alternative data (sentiment, weather, VIX, etc.)
- Cross-features (interactions)

Features are stored as Parquet for efficient access and caching.
Handles missing data gracefully (forward fill, interpolation).
"""

import logging
import pickle
from datetime import datetime, timedelta
from typing import Optional, Union
from pathlib import Path

import pandas as pd
import numpy as np
try:
    import ta  # Technical analysis library
except ImportError:  # pragma: no cover - optional dependency
    ta = None

from .market_fetcher import MarketDataFetcher
from .macro_fetcher import MacroDataFetcher
from .alt_data_fetcher import AltDataFetcher
from ..utils.config import Config
from ..utils.constants import FEATURE_DEFINITIONS

logger = logging.getLogger(__name__)


def _parse_lookback_to_days(lookback: str) -> int:
    """Parse flexible lookback values like `10y`, `6mo`, `30d`, or `2w`."""
    value = str(lookback).strip().lower()
    if not value:
        raise ValueError("lookback cannot be empty")

    units = {
        "years": 365,
        "year": 365,
        "yrs": 365,
        "yr": 365,
        "y": 365,
        "months": 30,
        "month": 30,
        "mo": 30,
        "weeks": 7,
        "week": 7,
        "wk": 7,
        "w": 7,
        "days": 1,
        "day": 1,
        "d": 1,
    }

    for suffix, multiplier in sorted(units.items(), key=lambda item: len(item[0]), reverse=True):
        if value.endswith(suffix):
            number = value[: -len(suffix)].strip()
            if number:
                return max(int(float(number) * multiplier), 1)

    if value.isdigit():
        return max(int(value), 1)

    raise ValueError(f"Unsupported lookback format: {lookback}")


def _compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Compute RSI, using the optional `ta` package when available."""
    if ta is not None:
        return ta.momentum.RSIIndicator(close=close, window=window).rsi() / 100

    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return (rsi / 100).clip(lower=0, upper=1)


def _compute_macd(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Compute MACD and its signal line with an internal fallback."""
    if ta is not None:
        macd = ta.trend.MACD(close=close)
        return macd.macd(), macd.macd_signal()

    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line


def _compute_bollinger(close: pd.Series, window: int = 20) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Compute Bollinger bands with an internal fallback."""
    if ta is not None:
        bb = ta.volatility.BollingerBands(close=close, window=window)
        return bb.bollinger_hband(), bb.bollinger_lband(), bb.bollinger_pband()

    rolling_mean = close.rolling(window).mean()
    rolling_std = close.rolling(window).std()
    upper = rolling_mean + (2 * rolling_std)
    lower = rolling_mean - (2 * rolling_std)
    width = (upper - lower).replace(0, np.nan)
    percent = ((close - lower) / width).clip(lower=0, upper=1)
    return upper, lower, percent


def _coerce_numeric_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all exported feature columns use numeric dtypes."""
    if df.empty:
        return df

    normalized = df.copy()
    for col in normalized.columns:
        series = normalized[col]
        if pd.api.types.is_bool_dtype(series.dtype):
            normalized[col] = series.astype(np.int8)
        else:
            normalized[col] = pd.to_numeric(series, errors='coerce')
    return normalized


class FeatureStore:
    """
    Unified feature matrix builder and storage.
    
    Combines market, macro, and alternative data into rich feature vectors
    suitable for ML prediction and risk analysis.
    
    Features are organized as:
    - Price features: returns, volatility, momentum, RSI, MACD, Bollinger Bands
    - Macro features: unemployment, CPI, GDP, yields, Fed rate
    - Alt features: sentiment, weather, VIX, put/call, seasonality
    - Cross features: interactions (VIX × sentiment, yield × momentum)
    """
    
    def __init__(self):
        """Initialize feature store."""
        self.cache_dir = Config.DATA_CACHE_DIR / "features"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.market_fetcher = MarketDataFetcher()
        self.macro_fetcher = MacroDataFetcher()
        self.alt_fetcher = AltDataFetcher()
        
        logger.info("FeatureStore initialized")
    
    def build_feature_matrix(
        self,
        asset: str,
        lookback: str = "2y",
        frequency: str = "1d",
    ) -> pd.DataFrame:
        """
        Build comprehensive feature matrix for an asset.
        
        Args:
            asset: Ticker symbol (e.g., 'AAPL', 'SPY', 'EURUSD=X', 'GC=F').
            lookback: Lookback period ('1y', '2y', '5y').
            frequency: Data frequency ('1d', '1w', '1mo').
        
        Returns:
            DataFrame with DatetimeIndex and columns:
            - Price features: return, volatility_20d, volatility_60d, momentum_10d, momentum_30d,
              rsi_14, macd, macd_signal, bb_upper, bb_lower, bb_percent
            - Macro features: unemployment, cpi_yoy, gdp_growth, yield_spread, fed_rate
            - Alt features: sentiment, vix_level, put_call_ratio, weather_score
            - Cross features: vix_x_sentiment, yield_x_momentum
            
            Missing data: forward fill + interpolation, with NaN indicator columns.
        """
        # Calculate date range
        end_date = datetime.now()
        lookback_days = _parse_lookback_to_days(lookback)
        start_date = end_date - timedelta(days=lookback_days)
        
        # Check cache first
        cached = self._load_from_cache(asset, lookback, frequency)
        if cached is not None:
            required_targets = {'forward_return_1d', 'forward_return_5d', 'forward_return_21d'}
            if required_targets.issubset(cached.columns):
                logger.info(f"Cache hit for {asset} features")
                return cached
            logger.info(f"Ignoring stale feature cache for {asset}: missing supervised targets")
        
        logger.info(f"Building feature matrix for {asset} (lookback: {lookback})")
        
        # Fetch price data
        price_data = self.market_fetcher.get_historical_ohlcv(
            asset, start_date, end_date, interval=frequency
        )
        
        if len(price_data) == 0:
            logger.error(f"No price data for {asset}")
            return pd.DataFrame()
        
        # Build feature matrix
        df = pd.DataFrame(index=price_data.index)
        
        # ============== Price Features ==============
        df = self._add_price_features(df, price_data)
        
        # ============== Macro Features ==============
        df = self._add_macro_features(df, start_date, end_date)
        
        # ============== Alternative Features ==============
        df = self._add_alt_features(df, start_date, end_date)
        
        # ============== Cross Features ==============
        df = self._add_cross_features(df)
        
        # ============== Handle Missing Data ==============
        df = self._handle_missing_data(df)
        df = _coerce_numeric_feature_frame(df)
        
        # Cache result
        self._save_to_cache(asset, df, lookback, frequency)
        
        logger.info(f"Built feature matrix: {df.shape[0]} rows × {df.shape[1]} columns")
        return df
    
    def get_correlation_matrix(
        self,
        assets: list[str],
        lookback: str = "2y",
        window: int = 60,
    ) -> pd.DataFrame:
        """
        Compute rolling correlation matrix across assets.
        
        Args:
            assets: List of ticker symbols.
            window: Rolling window in days (default 60).
        
        Returns:
            Correlation matrix across asset returns.
        """
        returns_df = pd.DataFrame()
        
        for asset in assets:
            try:
                df = self.build_feature_matrix(asset, lookback=lookback)
                if 'return' in df.columns and len(df) > 0:
                    returns_df[asset] = df['return']
            except Exception as e:
                logger.warning(f"Failed to get returns for {asset}: {e}")
        
        if len(returns_df) == 0:
            return pd.DataFrame()
        
        return returns_df.corr()

    def build_multi_asset_matrix(
        self,
        assets: list[str],
        lookback: str = "2y",
        frequency: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """Build feature matrices for multiple assets, keyed by ticker."""
        matrices: dict[str, pd.DataFrame] = {}
        for asset in assets:
            try:
                matrix = self.build_feature_matrix(asset, lookback=lookback, frequency=frequency)
            except Exception as e:
                logger.warning(f"Failed to build feature matrix for {asset}: {e}")
                continue
            if isinstance(matrix, pd.DataFrame) and len(matrix) > 0:
                matrices[asset] = matrix
        return matrices

    def get_feature_stats(
        self,
        asset: str,
        lookback: str = "2y",
        frequency: str = "1d",
    ) -> dict[str, dict[str, float]]:
        """Return summary statistics for the numeric feature columns of one asset."""
        matrix = self.build_feature_matrix(asset, lookback=lookback, frequency=frequency)
        if matrix.empty:
            return {}

        numeric = matrix.select_dtypes(include=[np.number])
        if numeric.empty:
            return {}

        return {
            "mean": numeric.mean().to_dict(),
            "std": numeric.std().to_dict(),
            "min": numeric.min().to_dict(),
            "max": numeric.max().to_dict(),
            "count": numeric.count().astype(float).to_dict(),
        }
    
    def refresh(
        self,
        sections: Optional[Union[str, list[str]]] = None,
    ) -> None:
        """
        Refresh feature caches (incremental update).
        
        Args:
            sections: Sections to refresh ('price', 'macro', 'alt').
                If None, refresh all.
        """
        if isinstance(sections, str):
            sections = [sections]

        if sections is None:
            sections = ['price', 'macro', 'alt']
        
        logger.info(f"Refreshing feature cache sections: {sections}")
        
        # Clear cache files
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
            except:
                pass
        
        logger.info("Feature cache cleared")
    
    # ============== Private Helper Methods ==============
    
    def _add_price_features(
        self,
        df: pd.DataFrame,
        price_data: pd.DataFrame,
    ) -> pd.DataFrame:
        """Compute and add price-based features."""
        # Log returns
        df['return'] = np.log(price_data['close'] / price_data['close'].shift(1))
        
        # Volatility (rolling std of returns)
        df['volatility_20d'] = price_data['close'].pct_change().rolling(20).std()
        df['volatility_60d'] = price_data['close'].pct_change().rolling(60).std()
        
        # Momentum (rate of change)
        df['momentum_10d'] = price_data['close'].pct_change(10)
        df['momentum_30d'] = price_data['close'].pct_change(30)

        # Forward returns used as supervised-learning targets.
        df['forward_return_1d'] = price_data['close'].shift(-1) / price_data['close'] - 1
        df['forward_return_5d'] = price_data['close'].shift(-5) / price_data['close'] - 1
        df['forward_return_21d'] = price_data['close'].shift(-21) / price_data['close'] - 1
        
        # RSI (Relative Strength Index)
        try:
            df['rsi_14'] = _compute_rsi(price_data['close'], window=14)
        except:
            logger.debug("RSI calculation failed")
            df['rsi_14'] = np.nan
        
        # MACD
        try:
            df['macd'], df['macd_signal'] = _compute_macd(price_data['close'])
        except:
            logger.debug("MACD calculation failed")
            df['macd'] = np.nan
            df['macd_signal'] = np.nan
        
        # Bollinger Bands
        try:
            df['bb_upper'], df['bb_lower'], df['bb_percent'] = _compute_bollinger(
                price_data['close'], window=20
            )
        except:
            logger.debug("Bollinger Bands calculation failed")
            df['bb_upper'] = np.nan
            df['bb_lower'] = np.nan
            df['bb_percent'] = np.nan
        
        return df
    
    def _add_macro_features(
        self,
        df: pd.DataFrame,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Fetch and add macroeconomic features."""
        # Unemployment rate
        try:
            unrate = self.macro_fetcher.get_indicator_timeseries(
                'UNRATE', start_date, end_date
            )
            if len(unrate) > 0:
                unrate.columns = ['unemployment_rate']
                df = df.join(unrate, how='left')
                # Forward fill for missing dates
                df['unemployment_rate'] = df['unemployment_rate'].ffill()
        except Exception as e:
            logger.debug(f"Unemployment data error: {e}")
        
        # CPI year-over-year
        try:
            cpi = self.macro_fetcher.get_indicator_timeseries(
                'CPIAUCSL', start_date, end_date
            )
            if len(cpi) > 0:
                cpi['cpi_yoy'] = cpi['value'].pct_change(12) * 100
                df = df.join(cpi[['cpi_yoy']], how='left')
                df['cpi_yoy'] = df['cpi_yoy'].ffill()
        except Exception as e:
            logger.debug(f"CPI data error: {e}")
        
        # GDP growth (quarterly, interpolate to daily)
        try:
            gdp = self.macro_fetcher.get_indicator_timeseries(
                'GDP', start_date, end_date
            )
            if len(gdp) > 0:
                gdp.columns = ['gdp_growth']
                df = df.join(gdp, how='left')
                df['gdp_growth'] = df['gdp_growth'].interpolate()
        except Exception as e:
            logger.debug(f"GDP data error: {e}")
        
        # Yield spread (10Y-2Y)
        try:
            spread = self.macro_fetcher.get_indicator_timeseries(
                'T10Y2Y', start_date, end_date
            )
            if len(spread) > 0:
                spread.columns = ['yield_spread']
                df = df.join(spread, how='left')
                df['yield_spread'] = df['yield_spread'].ffill()
        except Exception as e:
            logger.debug(f"Yield spread data error: {e}")
        
        # Fed Funds Rate
        try:
            fed = self.macro_fetcher.get_indicator_timeseries(
                'FEDFUNDS', start_date, end_date
            )
            if len(fed) > 0:
                fed.columns = ['fed_funds_rate']
                df = df.join(fed, how='left')
                df['fed_funds_rate'] = df['fed_funds_rate'].ffill()
        except Exception as e:
            logger.debug(f"Fed Funds data error: {e}")
        
        return df
    
    def _add_alt_features(
        self,
        df: pd.DataFrame,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Fetch and add alternative data features."""
        # VIX level
        try:
            vix_data = self.market_fetcher.get_historical_ohlcv(
                '^VIX', start_date, end_date
            )
            if len(vix_data) > 0:
                vix_df = pd.DataFrame({'vix_level': vix_data['close']})
                df = df.join(vix_df, how='left')
                df['vix_level'] = df['vix_level'].ffill()
        except Exception as e:
            logger.debug(f"VIX data error: {e}")
        
        # Sentiment (composite, updated daily)
        try:
            sentiment = self.alt_fetcher.get_sentiment_analysis()
            if 'composite' in sentiment:
                df['sentiment_composite'] = sentiment['composite']
        except Exception as e:
            logger.debug(f"Sentiment error: {e}")
        
        # Fear & Greed index
        try:
            fg = self.alt_fetcher.get_fear_and_greed_index()
            df['fear_greed_index'] = fg['index_value'] / 100  # Normalize to 0-1
        except Exception as e:
            logger.debug(f"Fear & Greed error: {e}")
        
        return df
    
    def _add_cross_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute interaction features."""
        # VIX × Sentiment
        if 'vix_level' in df.columns and 'sentiment_composite' in df.columns:
            df['vix_x_sentiment'] = (df['vix_level'] / 30) * ((df['sentiment_composite'] + 1) / 2)
        
        # Yield Spread × Momentum
        if 'yield_spread' in df.columns and 'momentum_30d' in df.columns:
            df['yield_x_momentum'] = df['yield_spread'] * df['momentum_30d']
        
        return df
    
    def _handle_missing_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values gracefully."""
        # Add NaN indicators before filling
        for col in df.columns:
            if df[col].isna().any():
                df[f'{col}_is_nan'] = df[col].isna().astype(np.int8)

        # Forward fill (for daily data that has values)
        df = df.ffill()
        
        # Linear interpolation for some columns
        interpolate_cols = [
            'gdp_growth', 'unemployment_rate', 'cpi_yoy',
            'vix_level', 'fed_funds_rate'
        ]
        for col in interpolate_cols:
            if col in df.columns:
                df[col] = df[col].interpolate(method='linear', limit_direction='both')
        
        # Fill remaining NaNs with median
        for col in df.columns:
            if df[col].isna().any() and not col.endswith('_is_nan'):
                non_null = df[col].dropna()
                if not non_null.empty:
                    median_value = non_null.median()
                    df[col] = df[col].fillna(median_value)
        
        # Final NaN fill with 0 for any remaining
        df = df.fillna(0)

        return _coerce_numeric_feature_frame(df)
    
    def _load_from_cache(
        self,
        asset: str,
        lookback: str,
        frequency: str,
    ) -> Optional[pd.DataFrame]:
        """Load features from cache if available and fresh."""
        cache_file = self.cache_dir / f"{asset}_{lookback}_{frequency}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            # Check age
            import time
            mtime = cache_file.stat().st_mtime
            now = time.time()
            age_hours = (now - mtime) / 3600
            
            if age_hours > Config.FEATURE_CACHE_TTL_HOURS:
                logger.debug(f"Feature cache expired for {asset}")
                return None
            
            # Load cache
            with open(cache_file, 'rb') as f:
                df = pickle.load(f)

            return _coerce_numeric_feature_frame(df)
        
        except Exception as e:
            logger.debug(f"Feature cache load error for {asset}: {e}")
            return None
    
    def _save_to_cache(
        self,
        asset: str,
        df: pd.DataFrame,
        lookback: str,
        frequency: str,
    ) -> None:
        """Save features to cache."""
        try:
            cache_file = self.cache_dir / f"{asset}_{lookback}_{frequency}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)
            logger.debug(f"Cached features for {asset}")
        except Exception as e:
            logger.warning(f"Feature cache save error for {asset}: {e}")
