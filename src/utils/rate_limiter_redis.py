"""
Redis-based Rate Limiter with Failover
Production-ready rate limiting with Redis backend and memory fallback.
"""

from typing import Optional, Dict, Any
import threading
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class RedisConnectionPool:
    """
    Manages Redis connection pool with automatic reconnection.
    """
    
    _instance: Optional['RedisConnectionPool'] = None
    _lock = threading.Lock()
    
    def __new__(cls, redis_url: Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, redis_url: Optional[str] = None):
        if self._initialized:
            return
        
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self._pool = None
        self._client = None
        self._connected = False
        self._lock = threading.RLock()
        self._initialized = True
    
    def connect(self) -> bool:
        """
        Establish Redis connection.
        
        Returns:
            True if connected successfully
        """
        with self._lock:
            try:
                from redis import Redis, ConnectionPool
                
                # Create connection pool
                self._pool = ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=20,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
                
                self._client = Redis(connection_pool=self._pool)
                
                # Test connection
                self._client.ping()
                self._connected = True
                
                logger.info("Redis connection established")
                return True
                
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._connected = False
                return False
    
    def get_client(self) -> Optional[Any]:
        """
        Get Redis client instance.
        
        Returns:
            Redis client or None if not connected
        """
        if not self._connected:
            if not self.connect():
                return None
        return self._client
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected
    
    def disconnect(self) -> None:
        """Close Redis connection."""
        with self._lock:
            if self._pool:
                self._pool.disconnect()
                self._pool = None
            self._client = None
            self._connected = False
            logger.info("Redis connection closed")


class MemoryRateLimiter:
    """
    In-memory rate limiter for failover when Redis is unavailable.
    Thread-safe implementation.
    """
    
    def __init__(self):
        self._counters: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def is_allowed(self, key: str, limit: int, period: int) -> bool:
        """
        Check if request is allowed using fixed window algorithm.
        
        Args:
            key: Rate limit key
            limit: Maximum requests per period
            period: Time period in seconds
            
        Returns:
            True if allowed
        """
        with self._lock:
            now = time.time()
            window_start = int(now / period) * period
            
            if key not in self._counters:
                self._counters[key] = {
                    'count': 0,
                    'window': window_start,
                    'timestamp': now,
                }
            
            counter = self._counters[key]
            
            # Reset if window expired
            if counter['window'] != window_start:
                counter['count'] = 0
                counter['window'] = window_start
            
            # Check limit
            if counter['count'] >= limit:
                return False
            
            counter['count'] += 1
            counter['timestamp'] = now
            return True
    
    def get_remaining(self, key: str, limit: int, period: int) -> int:
        """Get remaining requests for key."""
        with self._lock:
            if key not in self._counters:
                return limit
            
            now = time.time()
            window_start = int(now / period) * period
            counter = self._counters[key]
            
            if counter['window'] != window_start:
                return limit
            
            return max(0, limit - counter['count'])
    
    def reset(self, key: str) -> bool:
        """Reset counter for key."""
        with self._lock:
            if key in self._counters:
                del self._counters[key]
            return True
    
    def cleanup(self, max_age: int = 3600) -> int:
        """
        Remove stale entries.
        
        Args:
            max_age: Maximum age in seconds
            
        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            to_remove = []
            
            for key, counter in self._counters.items():
                if now - counter['timestamp'] > max_age:
                    to_remove.append(key)
            
            for key in to_remove:
                del self._counters[key]
            
            return len(to_remove)


class RedisRateLimiter:
    """
    Redis-based rate limiter with automatic failover to memory.
    
    Features:
    - Redis storage backend
    - Connection pool management
    - Automatic failover to memory on Redis failure
    - Fixed window rate limiting
    - Thread-safe operations
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_url: Redis connection URL (default: redis://localhost:6379/0)
        """
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self._pool = RedisConnectionPool(redis_url=self.redis_url)
        self._memory_limiter = MemoryRateLimiter()
        self._use_memory = False
        self._lock = threading.RLock()
    
    def _get_client(self) -> Optional[Any]:
        """Get Redis client or mark as unavailable."""
        if self._use_memory:
            return None
        
        client = self._pool.get_client()
        if client is None:
            self._use_memory = True
            logger.warning("Rate limiter switched to memory fallback")
        return client
    
    def is_allowed(self, key: str, limit: int, period: int) -> bool:
        """
        Check if request is allowed.
        
        Args:
            key: Rate limit key (e.g., "user:123", "ip:192.168.1.1")
            limit: Maximum requests per period
            period: Time period in seconds
            
        Returns:
            True if request is allowed
        """
        client = self._get_client()
        
        if client is None:
            # Use memory fallback
            return self._memory_limiter.is_allowed(key, limit, period)
        
        try:
            # Use Redis fixed window algorithm
            now = time.time()
            window_start = int(now / period) * period
            redis_key = f"ratelimit:{key}:{window_start}"
            
            # Increment counter atomically
            current = client.incr(redis_key)
            
            # Set expiry on first request
            if current == 1:
                client.expire(redis_key, period)
            
            allowed = current <= limit
            
            if not allowed:
                logger.debug(f"Rate limit exceeded for {key}: {current}/{limit}")
            
            return allowed
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Failover to memory
            self._use_memory = True
            return self._memory_limiter.is_allowed(key, limit, period)
    
    def get_remaining(self, key: str, limit: int, period: int) -> int:
        """
        Get remaining requests for a key.
        
        Args:
            key: Rate limit key
            limit: Maximum requests per period
            period: Time period in seconds
            
        Returns:
            Number of remaining requests
        """
        client = self._get_client()
        
        if client is None:
            return self._memory_limiter.get_remaining(key, limit, period)
        
        try:
            now = time.time()
            window_start = int(now / period) * period
            redis_key = f"ratelimit:{key}:{window_start}"
            
            current = client.get(redis_key)
            if current is None:
                return limit
            
            return max(0, limit - int(current))
            
        except Exception as e:
            logger.error(f"Redis get_remaining failed: {e}")
            return self._memory_limiter.get_remaining(key, limit, period)
    
    def reset(self, key: str, period: int = 60) -> bool:
        """
        Reset rate limit counter for a key.
        
        Args:
            key: Rate limit key
            period: Time period in seconds (default: 60)
            
        Returns:
            True if reset successful
        """
        client = self._get_client()
        
        if client is None:
            return self._memory_limiter.reset(key)
        
        try:
            # Delete all rate limit keys for this key
            now = time.time()
            # Current window
            window_start = int(now / period) * period
            redis_key = f"ratelimit:{key}:{window_start}"
            client.delete(redis_key)
            
            return True
            
        except Exception as e:
            logger.error(f"Redis reset failed: {e}")
            return self._memory_limiter.reset(key)
    
    def restore_redis(self) -> bool:
        """
        Attempt to restore Redis connection.
        
        Returns:
            True if Redis is available again
        """
        if not self._use_memory:
            return True
        
        with self._lock:
            self._use_memory = False
            client = self._pool.get_client()
            
            if client:
                logger.info("Rate limiter restored to Redis")
                return True
            else:
                self._use_memory = True
                return False
    
    def is_using_memory(self) -> bool:
        """Check if using memory fallback."""
        return self._use_memory
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            'backend': 'memory' if self._use_memory else 'redis',
            'redis_connected': self._pool.is_connected(),
            'redis_url': self.redis_url,
        }


# Decorator for rate limiting
def rate_limit(key_func=None, limit: int = 100, period: int = 60):
    """
    Decorator to apply rate limiting to a function.
    
    Args:
        key_func: Function to extract rate limit key from args/kwargs
        limit: Maximum requests per period
        period: Time period in seconds
        
    Usage:
        @rate_limit(key_func=lambda user, **kw: f"user:{user.id}", limit=10, period=60)
        def get_user_data(user, **kwargs):
            ...
    """
    _limiter: Optional[RedisRateLimiter] = None
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal _limiter
            if _limiter is None:
                _limiter = RedisRateLimiter()
            
            # Extract key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"func:{func.__name__}"
            
            # Check rate limit
            if not _limiter.is_allowed(key, limit, period):
                raise RateLimitExceeded(
                    f"Rate limit exceeded: {limit} requests per {period}s"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


# Module-level singleton
_rate_limiter: Optional[RedisRateLimiter] = None


def get_rate_limiter(redis_url: Optional[str] = None) -> RedisRateLimiter:
    """
    Get or create rate limiter instance.
    
    Args:
        redis_url: Optional Redis URL
        
    Returns:
        Rate limiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter(redis_url)
    return _rate_limiter
