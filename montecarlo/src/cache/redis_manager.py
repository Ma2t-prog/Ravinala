"""
src/cache/redis_manager.py — Redis caching layer
"""

import redis
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis caching layer for market data"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            self.client.ping()
            logger.info(f"Redis connected to {host}:{port}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.client = None
        
        # TTL configs (seconds)
        self.TTL = {
            'price': 2,
            'orderbook': 1,
            'ohlcv_1d': 3600,
            'correlation': 3600,
            'risk_metrics': 600,
        }
    
    def set_price(self, symbol: str, price: float, volume: float = 0) -> bool:
        """Cache a real-time price (2s TTL)"""
        if not self.client:
            return False
        
        key = f"market:price:{symbol}"
        try:
            self.client.setex(
                key,
                self.TTL['price'],
                json.dumps({
                    'price': price,
                    'volume': volume,
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
            return True
        except Exception as e:
            logger.error(f"Redis set_price failed: {e}")
            return False
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """Get cached price"""
        if not self.client:
            return None
        
        key = f"market:price:{symbol}"
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get_price failed: {e}")
            return None
    
    def set_orderbook(self, symbol: str, orderbook: Dict) -> bool:
        """Cache order book"""
        if not self.client:
            return False
        
        key = f"market:orderbook:{symbol}"
        try:
            self.client.setex(
                key,
                self.TTL['orderbook'],
                json.dumps(orderbook)
            )
            return True
        except Exception as e:
            logger.error(f"Redis set_orderbook failed: {e}")
            return False
    
    def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """Get cached order book"""
        if not self.client:
            return None
        
        key = f"market:orderbook:{symbol}"
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get_orderbook failed: {e}")
            return None
    
    def set_correlation_matrix(self, symbols: list, corr_matrix: Dict) -> bool:
        """Cache correlation matrix (1h TTL)"""
        if not self.client:
            return False
        
        key = "analytics:correlation:matrix"
        try:
            self.client.setex(
                key,
                self.TTL['correlation'],
                json.dumps({
                    'symbols': symbols,
                    'matrix': corr_matrix,
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
            return True
        except Exception as e:
            logger.error(f"Redis set_correlation failed: {e}")
            return False
    
    def get_correlation_matrix(self) -> Optional[Dict]:
        """Get cached correlation matrix"""
        if not self.client:
            return None
        
        key = "analytics:correlation:matrix"
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get_correlation failed: {e}")
            return None
    
    def set_risk_metrics(self, symbol: str, metrics: Dict) -> bool:
        """Cache risk metrics (10min TTL)"""
        if not self.client:
            return False
        
        key = f"analytics:risk:{symbol}"
        try:
            self.client.setex(
                key,
                self.TTL['risk_metrics'],
                json.dumps(metrics)
            )
            return True
        except Exception as e:
            logger.error(f"Redis set_risk_metrics failed: {e}")
            return False
    
    def get_risk_metrics(self, symbol: str) -> Optional[Dict]:
        """Get cached risk metrics"""
        if not self.client:
            return None
        
        key = f"analytics:risk:{symbol}"
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get_risk_metrics failed: {e}")
            return None
    
    def health_check(self) -> bool:
        """Check Redis connectivity"""
        if not self.client:
            return False
        
        try:
            self.client.ping()
            logger.info("Redis health check passed")
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def flush_all(self):
        """Clear all cache (CAREFUL!)"""
        if not self.client:
            return False
        
        try:
            self.client.flushall()
            logger.warning("Redis flushed (all data cleared)")
            return True
        except Exception as e:
            logger.error(f"Redis flush failed: {e}")
            return False

# Singleton instance
redis_cache = RedisCache(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379))
)
