"""
Rate Limiting Strategies
Multiple algorithms for different use cases.
"""

from typing import Dict, Any, Optional, List
import time
import threading
from collections import deque
import logging

logger = logging.getLogger(__name__)


class SlidingWindowLimiter:
    """
    Sliding window rate limiter.
    More accurate than fixed window, prevents boundary attacks.
    
    Uses Redis sorted sets for distributed rate limiting.
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize sliding window limiter.
        
        Args:
            redis_client: Optional Redis client instance
        """
        self._redis = redis_client
        self._memory_store: Dict[str, deque] = {}
        self._lock = threading.RLock()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed using sliding window.
        
        Args:
            key: Rate limit key
            limit: Maximum requests per window
            window: Window size in seconds
            
        Returns:
            True if allowed
        """
        now = time.time()
        window_start = now - window
        
        if self._redis:
            return self._redis_sliding_window(key, limit, window, now, window_start)
        else:
            return self._memory_sliding_window(key, limit, window, now, window_start)
    
    def _redis_sliding_window(self, key: str, limit: int, window: int, 
                              now: float, window_start: float) -> bool:
        """Redis-based sliding window."""
        try:
            redis_key = f"sliding:{key}"
            
            # Use Redis pipeline for atomic operations
            pipe = self._redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current entries
            pipe.zcard(redis_key)
            
            # Add new entry
            pipe.zadd(redis_key, {f"{now}": now})
            
            # Set expiry
            pipe.expire(redis_key, window)
            
            results = pipe.execute()
            current_count = results[1]
            
            if current_count >= limit:
                # Remove the entry we just added since we're over limit
                self._redis.zrem(redis_key, f"{now}")
                logger.debug(f"Sliding window limit exceeded for {key}: {current_count}/{limit}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Redis sliding window failed: {e}")
            # Fallback to memory
            return self._memory_sliding_window(key, limit, window, now, window_start)
    
    def _memory_sliding_window(self, key: str, limit: int, window: int,
                               now: float, window_start: float) -> bool:
        """In-memory sliding window."""
        with self._lock:
            if key not in self._memory_store:
                self._memory_store[key] = deque()
            
            timestamps = self._memory_store[key]
            
            # Remove old entries
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()
            
            # Check limit
            if len(timestamps) >= limit:
                logger.debug(f"Sliding window limit exceeded for {key}: {len(timestamps)}/{limit}")
                return False
            
            # Add new entry
            timestamps.append(now)
            return True
    
    def get_remaining(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - window
        
        with self._lock:
            if key not in self._memory_store:
                return limit
            
            timestamps = self._memory_store[key]
            
            # Remove old entries
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()
            
            return max(0, limit - len(timestamps))
    
    def reset(self, key: str) -> bool:
        """Reset sliding window for key."""
        with self._lock:
            if key in self._memory_store:
                del self._memory_store[key]
            
            if self._redis:
                try:
                    self._redis.delete(f"sliding:{key}")
                except Exception as e:
                    logger.error(f"Redis reset failed: {e}")
            
            return True


class TokenBucketLimiter:
    """
    Token bucket rate limiter.
    Allows bursting while maintaining average rate.
    
    Good for APIs that want to allow occasional bursts.
    """
    
    def __init__(self, capacity: int, refill_rate: float, redis_client=None):
        """
        Initialize token bucket limiter.
        
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
            redis_client: Optional Redis client
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._redis = redis_client
        self._memory_buckets: Dict[str, Dict[str, float]] = {}
        self._lock = threading.RLock()
    
    def is_allowed(self, key: str, tokens: int = 1) -> bool:
        """
        Check if request is allowed (consumes tokens).
        
        Args:
            key: Rate limit key
            tokens: Number of tokens to consume
            
        Returns:
            True if allowed
        """
        now = time.time()
        
        if self._redis:
            return self._redis_token_bucket(key, tokens, now)
        else:
            return self._memory_token_bucket(key, tokens, now)
    
    def _redis_token_bucket(self, key: str, tokens: int, now: float) -> bool:
        """Redis-based token bucket."""
        try:
            redis_key = f"bucket:{key}"
            
            # Use Lua script for atomic token bucket operation
            lua_script = """
            local key = KEYS[1]
            local capacity = tonumber(ARGV[1])
            local refill_rate = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local tokens = tonumber(ARGV[4])
            
            local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
            local current_tokens = tonumber(bucket[1])
            local last_update = tonumber(bucket[2])
            
            if current_tokens == nil then
                current_tokens = capacity
                last_update = now
            end
            
            -- Refill tokens based on time elapsed
            local elapsed = now - last_update
            local refilled = elapsed * refill_rate
            current_tokens = math.min(capacity, current_tokens + refilled)
            
            if current_tokens >= tokens then
                current_tokens = current_tokens - tokens
                redis.call('HMSET', key, 'tokens', current_tokens, 'last_update', now)
                redis.call('EXPIRE', key, 3600)
                return 1
            else
                return 0
            end
            """
            
            result = self._redis.eval(
                lua_script, 1, redis_key,
                self.capacity, self.refill_rate, now, tokens
            )
            
            return result == 1
            
        except Exception as e:
            logger.error(f"Redis token bucket failed: {e}")
            return self._memory_token_bucket(key, tokens, now)
    
    def _memory_token_bucket(self, key: str, tokens: int, now: float) -> bool:
        """In-memory token bucket."""
        with self._lock:
            if key not in self._memory_buckets:
                self._memory_buckets[key] = {
                    'tokens': self.capacity,
                    'last_update': now,
                }
            
            bucket = self._memory_buckets[key]
            
            # Refill tokens
            elapsed = now - bucket['last_update']
            bucket['tokens'] = min(
                self.capacity,
                bucket['tokens'] + elapsed * self.refill_rate
            )
            bucket['last_update'] = now
            
            # Check if enough tokens
            if bucket['tokens'] >= tokens:
                bucket['tokens'] -= tokens
                return True
            
            logger.debug(f"Token bucket empty for {key}: {bucket['tokens']:.2f}/{tokens}")
            return False
    
    def get_tokens(self, key: str) -> float:
        """Get current token count for key."""
        now = time.time()
        
        with self._lock:
            if key not in self._memory_buckets:
                return self.capacity
            
            bucket = self._memory_buckets[key]
            elapsed = now - bucket['last_update']
            
            return min(
                self.capacity,
                bucket['tokens'] + elapsed * self.refill_rate
            )
    
    def reset(self, key: str) -> bool:
        """Reset token bucket for key."""
        with self._lock:
            if key in self._memory_buckets:
                del self._memory_buckets[key]
            
            if self._redis:
                try:
                    self._redis.delete(f"bucket:{key}")
                except Exception as e:
                    logger.error(f"Redis reset failed: {e}")
            
            return True


class LeakyBucketLimiter:
    """
    Leaky bucket rate limiter.
    Enforces strict rate limiting with queue behavior.
    
    Good for preventing bursts and ensuring smooth traffic.
    """
    
    def __init__(self, capacity: int, leak_rate: float, redis_client=None):
        """
        Initialize leaky bucket limiter.
        
        Args:
            capacity: Maximum queue size
            leak_rate: Requests processed per second
            redis_client: Optional Redis client
        """
        self.capacity = capacity
        self.leak_rate = leak_rate
        self._redis = redis_client
        self._memory_buckets: Dict[str, Dict[str, float]] = {}
        self._lock = threading.RLock()
    
    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed.
        
        Args:
            key: Rate limit key
            
        Returns:
            True if allowed (added to queue)
        """
        now = time.time()
        
        if self._redis:
            return self._redis_leaky_bucket(key, now)
        else:
            return self._memory_leaky_bucket(key, now)
    
    def _redis_leaky_bucket(self, key: str, now: float) -> bool:
        """Redis-based leaky bucket."""
        try:
            redis_key = f"leaky:{key}"
            
            # Use Lua script for atomic leaky bucket operation
            lua_script = """
            local key = KEYS[1]
            local capacity = tonumber(ARGV[1])
            local leak_rate = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            
            local bucket = redis.call('HMGET', key, 'water', 'last_leak')
            local water = tonumber(bucket[1])
            local last_leak = tonumber(bucket[2])
            
            if water == nil then
                water = 0
                last_leak = now
            end
            
            -- Leak water based on time elapsed
            local elapsed = now - last_leak
            local leaked = elapsed * leak_rate
            water = math.max(0, water - leaked)
            
            if water + 1 <= capacity then
                water = water + 1
                redis.call('HMSET', key, 'water', water, 'last_leak', now)
                redis.call('EXPIRE', key, 3600)
                return 1
            else
                return 0
            end
            """
            
            result = self._redis.eval(
                lua_script, 1, redis_key,
                self.capacity, self.leak_rate, now
            )
            
            return result == 1
            
        except Exception as e:
            logger.error(f"Redis leaky bucket failed: {e}")
            return self._memory_leaky_bucket(key, now)
    
    def _memory_leaky_bucket(self, key: str, now: float) -> bool:
        """In-memory leaky bucket."""
        with self._lock:
            if key not in self._memory_buckets:
                self._memory_buckets[key] = {
                    'water': 0,
                    'last_leak': now,
                }
            
            bucket = self._memory_buckets[key]
            
            # Leak water
            elapsed = now - bucket['last_leak']
            bucket['water'] = max(0, bucket['water'] - elapsed * self.leak_rate)
            bucket['last_leak'] = now
            
            # Check if adding water would overflow
            if bucket['water'] + 1 > self.capacity:
                logger.debug(f"Leaky bucket full for {key}: {bucket['water']:.2f}/{self.capacity}")
                return False
            
            # Add water (request)
            bucket['water'] += 1
            return True
    
    def get_level(self, key: str) -> float:
        """Get current water level for key."""
        now = time.time()
        
        with self._lock:
            if key not in self._memory_buckets:
                return 0
            
            bucket = self._memory_buckets[key]
            elapsed = now - bucket['last_leak']
            
            return max(0, bucket['water'] - elapsed * self.leak_rate)
    
    def reset(self, key: str) -> bool:
        """Reset leaky bucket for key."""
        with self._lock:
            if key in self._memory_buckets:
                del self._memory_buckets[key]
            
            if self._redis:
                try:
                    self._redis.delete(f"leaky:{key}")
                except Exception as e:
                    logger.error(f"Redis reset failed: {e}")
            
            return True


class FixedWindowLimiter:
    """
    Fixed window rate limiter.
    Simple and efficient, but allows boundary attacks.
    
    Good for basic rate limiting needs.
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize fixed window limiter.
        
        Args:
            redis_client: Optional Redis client
        """
        self._redis = redis_client
        self._memory_counters: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def is_allowed(self, key: str, limit: int, period: int) -> bool:
        """
        Check if request is allowed using fixed window.
        
        Args:
            key: Rate limit key
            limit: Maximum requests per period
            period: Time period in seconds
            
        Returns:
            True if allowed
        """
        now = time.time()
        window_start = int(now / period) * period
        
        if self._redis:
            return self._redis_fixed_window(key, limit, period, window_start)
        else:
            return self._memory_fixed_window(key, limit, period, window_start)
    
    def _redis_fixed_window(self, key: str, limit: int, period: int,
                           window_start: float) -> bool:
        """Redis-based fixed window."""
        try:
            redis_key = f"fixed:{key}:{int(window_start)}"
            
            # Atomic increment
            current = self._redis.incr(redis_key)
            
            # Set expiry on first request
            if current == 1:
                self._redis.expire(redis_key, period)
            
            if current > limit:
                logger.debug(f"Fixed window limit exceeded for {key}: {current}/{limit}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Redis fixed window failed: {e}")
            return self._memory_fixed_window(key, limit, period, window_start)
    
    def _memory_fixed_window(self, key: str, limit: int, period: int,
                            window_start: float) -> bool:
        """In-memory fixed window."""
        with self._lock:
            if key not in self._memory_counters:
                self._memory_counters[key] = {
                    'count': 0,
                    'window': window_start,
                }
            
            counter = self._memory_counters[key]
            
            # Reset if window expired
            if counter['window'] != window_start:
                counter['count'] = 0
                counter['window'] = window_start
            
            counter['count'] += 1
            
            if counter['count'] > limit:
                logger.debug(f"Fixed window limit exceeded for {key}: {counter['count']}/{limit}")
                return False
            
            return True
    
    def get_remaining(self, key: str, limit: int, period: int) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = int(now / period) * period
        
        with self._lock:
            if key not in self._memory_counters:
                return limit
            
            counter = self._memory_counters[key]
            
            if counter['window'] != window_start:
                return limit
            
            return max(0, limit - counter['count'])
    
    def reset(self, key: str) -> bool:
        """Reset fixed window for key."""
        with self._lock:
            if key in self._memory_counters:
                del self._memory_counters[key]
            
            if self._redis:
                try:
                    # Delete all fixed window keys for this key (pattern match)
                    keys = self._redis.keys(f"fixed:{key}:*")
                    if keys:
                        self._redis.delete(*keys)
                except Exception as e:
                    logger.error(f"Redis reset failed: {e}")
            
            return True


# Strategy factory
def create_limiter(strategy: str, **kwargs):
    """
    Create a rate limiter with specified strategy.
    
    Args:
        strategy: Strategy name ('sliding_window', 'token_bucket', 'leaky_bucket', 'fixed_window')
        **kwargs: Strategy-specific parameters
        
    Returns:
        Rate limiter instance
        
    Example:
        limiter = create_limiter('token_bucket', capacity=100, refill_rate=10)
    """
    strategies = {
        'sliding_window': SlidingWindowLimiter,
        'token_bucket': TokenBucketLimiter,
        'leaky_bucket': LeakyBucketLimiter,
        'fixed_window': FixedWindowLimiter,
    }
    
    if strategy not in strategies:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    return strategies[strategy](**kwargs)
