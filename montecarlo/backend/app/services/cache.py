"""
Redis caching layer with TTL per section
"""

import copy
import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta, timezone
import hashlib

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)

class CacheManager:
    """Manage Redis cache with section-specific TTLs."""
    
    MAX_MEMORY_CACHE_SIZE = 500  # R5: prevent unbounded in-memory growth
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis connection."""
        self.redis = None
        self._memory_cache: dict[str, tuple[Any, datetime]] = {}
        try:
            import redis
            _r = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            _r.ping()
            self.redis = _r
            logger.info("✅ Redis connected")
        except Exception as e:
            self.redis = None
            logger.warning(f"⚠️ Redis unavailable: {e}. Running in-memory cache.")
    
    def get_ttl(self, section: str) -> int:
        """Get TTL in seconds for each section."""
        ttl_map = {
            "indices": 5 * 60,           # 5 min (volatile)
            "fx": 5 * 60,                # 5 min
            "commodities": 5 * 60,       # 5 min
            "bonds": 60 * 60,            # 1 hour (less volatile)
            "macro": 24 * 60 * 60,       # 1 day
            "correlations": 60 * 60,     # 1 hour
            "snapshot": 15 * 60,         # 15 min (full dashboard)
        }
        return ttl_map.get(section, 5 * 60)
    
    def set(self, key: str, value: Any, section: str = "default") -> bool:
        """Set cache with section-specific TTL."""
        ttl = self.get_ttl(section)
        try:
            if self.redis:
                serialized = json.dumps(value, default=str)
                self.redis.setex(key, ttl, serialized)
                logger.debug(f"💾 Cache set: {key} (TTL: {ttl}s)")
                return True
            else:
                # Evict expired entries, then enforce max size
                now = _utcnow()
                expired = [k for k, (_, exp) in self._memory_cache.items() if now >= exp]
                for k in expired:
                    del self._memory_cache[k]
                if len(self._memory_cache) >= self.MAX_MEMORY_CACHE_SIZE:
                    oldest_key = min(self._memory_cache, key=lambda k: self._memory_cache[k][1])
                    del self._memory_cache[oldest_key]
                self._memory_cache[key] = (copy.deepcopy(value), _utcnow() + timedelta(seconds=ttl))
                return True
        except Exception as e:
            logger.error(f"❌ Cache set failed: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get from cache."""
        try:
            if self.redis:
                data = self.redis.get(key)
                if data:
                    logger.debug(f"✅ Cache hit: {key}")
                    return json.loads(data)
            else:
                if key in self._memory_cache:
                    value, expiry = self._memory_cache[key]
                    if _utcnow() < expiry:
                        logger.debug(f"✅ In-memory cache hit: {key}")
                        return copy.deepcopy(value)
                    else:
                        del self._memory_cache[key]
            
            logger.debug(f"❌ Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"❌ Cache get failed: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete from cache."""
        try:
            if self.redis:
                self.redis.delete(key)
            elif key in self._memory_cache:
                del self._memory_cache[key]
            logger.debug(f"🗑️ Cache deleted: {key}")
            return True
        except Exception as e:
            logger.error(f"❌ Cache delete failed: {e}")
            return False
    
    def clear_section(self, section: str) -> int:
        """Clear all keys in a section (pattern: section:*)."""
        try:
            pattern = f"{section}:*"
            if self.redis:
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
                    logger.info(f"🗑️ Cleared {len(keys)} keys for section: {section}")
                    return len(keys)
            else:
                prefix = f"{section}:"
                keys = [key for key in list(self._memory_cache.keys()) if key.startswith(prefix)]
                for key in keys:
                    del self._memory_cache[key]
                if keys:
                    logger.info(f"🗑️ Cleared {len(keys)} in-memory keys for section: {section}")
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"❌ Clear section failed: {e}")
            return 0
    
    def health(self) -> bool:
        """Check if cache is healthy."""
        try:
            if self.redis:
                self.redis.ping()
                return True
            return True  # In-memory cache always healthy
        except Exception as e:
            logger.error(f"❌ Cache health check failed: {e}")
            return False
    
    def get_age(self, key: str) -> Optional[int]:
        """Get cache age in seconds (for staleness detection)."""
        try:
            if self.redis:
                ttl = self.redis.ttl(key)
                if ttl > 0:
                    section = key.split(":")[0]
                    max_ttl = self.get_ttl(section)
                    age = max_ttl - ttl
                    return age
            elif key in self._memory_cache:
                _, expiry = self._memory_cache[key]
                now = _utcnow()
                if now < expiry:
                    section = key.split(":")[0]
                    max_ttl = self.get_ttl(section)
                    remaining = max(0, int((expiry - now).total_seconds()))
                    return max_ttl - remaining
                del self._memory_cache[key]
            return None
        except Exception as e:
            logger.error(f"❌ Get age failed: {e}")
            return None
    
    @staticmethod
    def make_etag(data: dict) -> str:
        """Generate ETag from data hash."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()

# Singleton
_cache_manager = None

def get_cache() -> CacheManager:
    """Get or create cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
