"""Centralized caching layer for GenesiX.

Uses file-based Parquet cache for persistence + Streamlit caching for in-memory.
Cache hierarchy:
1. st.session_state (in-memory, per-session, instant)
2. st.cache_data / st.cache_resource (in-memory, cross-session)
3. Parquet files in data/cache/ (on-disk, persistent across restarts)

TTL policy:
- Realtime prices: 60 seconds
- Market OHLCV (daily): 1 hour during market hours, 12 hours after close
- Macro data: 24 hours (changes slowly)
- Alt data (sentiment, trends): 2 hours
- Feature matrices: 6 hours (expensive to compute)
- ML model weights: 24 hours (very expensive)
- Stress test results: 6 hours
- Correlation matrices: 2 hours
"""

import time
import hashlib
import json
import logging
from pathlib import Path
from functools import wraps
from typing import Any, Callable, Optional
import pandas as pd

logger = logging.getLogger('genesix.cache')

CACHE_DIR = Path("data/cache")

TTL_CONFIG = {
    'realtime': 60,           # 1 minute
    'ohlcv': 3600,            # 1 hour
    'macro': 86400,           # 24 hours
    'alt_data': 7200,         # 2 hours
    'features': 21600,        # 6 hours
    'ml_models': 86400,       # 24 hours
    'stress_tests': 21600,    # 6 hours
    'correlations': 7200,     # 2 hours
}


def cached(category: str, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results to Parquet.
    
    Usage:
        @cached('ohlcv')
        def fetch_equities(self, tickers, period):
            return ...
    
    Or with custom key function:
        @cached('features', key_func=lambda asset, lookback: f"{asset}_{lookback}")
        def build_feature_matrix(self, asset, lookback):
            return ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_func:
                # key_func receives all positional args except self
                cache_key = key_func(*args[1:], **kwargs)
            else:
                # Auto-generate: function_name + args + kwargs
                key_parts = [func.__name__]
                key_parts.extend(str(a) for a in args[1:])  # skip self
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_str = "_".join(key_parts)
                cache_key = hashlib.md5(key_str.encode()).hexdigest()[:12]
            
            cache_path = CACHE_DIR / category / f"{cache_key}.parquet"
            meta_path = CACHE_DIR / category / f"{cache_key}.meta.json"
            ttl = TTL_CONFIG.get(category, 3600)
            
            # Try to load from cache
            if cache_path.exists() and meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    age = time.time() - meta.get('timestamp', 0)
                    if age < ttl:
                        result = pd.read_parquet(cache_path)
                        logger.debug(f"Cache HIT for {func.__name__} ({cache_key}), age {age:.0f}s")
                        return result
                    else:
                        logger.debug(f"Cache expired for {func.__name__} ({cache_key}), age {age:.0f}s > TTL {ttl}s")
                except Exception as e:
                    logger.warning(f"Cache read failed for {cache_key}: {e}")
            
            # Compute
            logger.debug(f"Computing {func.__name__} ({cache_key})...")
            result = func(*args, **kwargs)
            
            # Save to cache
            if isinstance(result, pd.DataFrame):
                try:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    result.to_parquet(cache_path, compression='snappy')
                    meta_path.write_text(json.dumps({
                        'timestamp': time.time(),
                        'function': func.__name__,
                        'rows': len(result),
                        'columns': len(result.columns),
                        'cache_key': cache_key,
                    }))
                    logger.debug(f"Cached {func.__name__} to {cache_path}")
                except Exception as e:
                    logger.warning(f"Cache write failed for {cache_key}: {e}")
            
            return result
        return wrapper
    return decorator


def clear_cache(category: Optional[str] = None):
    """Clear cache files. None = clear all."""
    try:
        if category:
            cache_dir = CACHE_DIR / category
            if cache_dir.exists():
                for f in cache_dir.glob("*.parquet"):
                    f.unlink()
                for f in cache_dir.glob("*.meta.json"):
                    f.unlink()
            logger.info(f"Cleared cache for category: {category}")
        else:
            if CACHE_DIR.exists():
                import shutil
                shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            logger.info("Cleared all caches")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")


def cache_stats() -> dict:
    """
    Return cache statistics.
    
    Returns:
        {
            'total_size_mb': float,
            'num_files': int,
            'by_category': {
                'ohlcv': {
                    'n_files': 12,
                    'size_mb': 4.5,
                    'oldest_minutes': 2.3,
                    'newest_minutes': 0.1,
                },
                ...
            }
        }
    """
    if not CACHE_DIR.exists():
        return {'total_size_mb': 0, 'num_files': 0, 'by_category': {}}
    
    stats = {'by_category': {}, 'total_size_mb': 0, 'num_files': 0}
    now = time.time()
    
    for category_dir in CACHE_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        
        cat_name = category_dir.name
        cat_stats = {'n_files': 0, 'size_mb': 0, 'oldest_minutes': None, 'newest_minutes': None}
        
        parquet_files = list(category_dir.glob('*.parquet'))
        if not parquet_files:
            continue
        
        cat_stats['n_files'] = len(parquet_files)
        
        ages = []
        for f in parquet_files:
            size = f.stat().st_size
            cat_stats['size_mb'] += size
            
            meta_file = f.parent / f"{f.stem}.meta.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                    age_sec = now - meta.get('timestamp', now)
                    ages.append(age_sec)
                except:
                    pass
        
        cat_stats['size_mb'] /= 1024 * 1024  # Convert to MB
        
        if ages:
            cat_stats['oldest_minutes'] = max(ages) / 60
            cat_stats['newest_minutes'] = min(ages) / 60
        
        stats['by_category'][cat_name] = cat_stats
        stats['total_size_mb'] += cat_stats['size_mb']
        stats['num_files'] += cat_stats['n_files']
    
    return stats


def get_cache_info() -> str:
    """Return human-readable cache info for logging/display."""
    stats = cache_stats()
    if stats['num_files'] == 0:
        return "Cache: empty"
    
    lines = [f"Cache: {stats['num_files']} files, {stats['total_size_mb']:.1f} MB"]
    for cat, cat_stats in stats['by_category'].items():
        lines.append(
            f"  {cat}: {cat_stats['n_files']} files, "
            f"{cat_stats['size_mb']:.1f} MB, "
            f"age {cat_stats['newest_minutes']:.0f}-{cat_stats['oldest_minutes']:.0f}m"
        )
    
    return "\n".join(lines)
