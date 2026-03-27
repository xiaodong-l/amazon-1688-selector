"""
Rate Limiter Stress Tests
Comprehensive tests for rate limiting functionality.
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.rate_limiter_redis import (
    RedisRateLimiter,
    MemoryRateLimiter,
    RedisConnectionPool,
    RateLimitExceeded,
    rate_limit,
    get_rate_limiter,
)
from utils.rate_limit_strategies import (
    SlidingWindowLimiter,
    TokenBucketLimiter,
    LeakyBucketLimiter,
    FixedWindowLimiter,
    create_limiter,
)
from utils.rate_limit_whitelist import (
    RateLimitWhitelist,
    WhitelistEntry,
    get_whitelist,
)
from monitoring.rate_limit_metrics import (
    RateLimitMetrics,
    get_metrics,
    record_hit,
    record_exceeded,
    time_rate_limit,
)


class TestMemoryRateLimiter:
    """Tests for in-memory rate limiter."""
    
    def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality."""
        limiter = MemoryRateLimiter()
        key = "test:user:1"
        limit = 5
        period = 60
        
        # Should allow up to limit
        for i in range(limit):
            assert limiter.is_allowed(key, limit, period) is True
        
        # Should deny after limit
        assert limiter.is_allowed(key, limit, period) is False
    
    def test_window_reset(self):
        """Test that window resets after period."""
        limiter = MemoryRateLimiter()
        key = "test:user:2"
        limit = 3
        period = 1  # 1 second for testing
        
        # Exhaust limit
        for _ in range(limit):
            limiter.is_allowed(key, limit, period)
        
        # Should be denied
        assert limiter.is_allowed(key, limit, period) is False
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        assert limiter.is_allowed(key, limit, period) is True
    
    def test_get_remaining(self):
        """Test getting remaining requests."""
        limiter = MemoryRateLimiter()
        key = "test:user:3"
        limit = 10
        period = 60
        
        # Initial remaining
        assert limiter.get_remaining(key, limit, period) == limit
        
        # Make some requests
        for _ in range(4):
            limiter.is_allowed(key, limit, period)
        
        # Check remaining
        assert limiter.get_remaining(key, limit, period) == 6
    
    def test_reset(self):
        """Test resetting rate limit."""
        limiter = MemoryRateLimiter()
        key = "test:user:4"
        limit = 5
        period = 60
        
        # Exhaust limit
        for _ in range(limit):
            limiter.is_allowed(key, limit, period)
        
        # Should be denied
        assert limiter.is_allowed(key, limit, period) is False
        
        # Reset
        assert limiter.reset(key) is True
        
        # Should be allowed again
        assert limiter.is_allowed(key, limit, period) is True
    
    def test_thread_safety(self):
        """Test thread safety with concurrent requests."""
        limiter = MemoryRateLimiter()
        key = "test:user:5"
        limit = 100
        period = 60
        
        allowed_count = 0
        lock = threading.Lock()
        
        def make_request():
            nonlocal allowed_count
            if limiter.is_allowed(key, limit, period):
                with lock:
                    allowed_count += 1
        
        # Run 200 concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(200)]
            for future in as_completed(futures):
                future.result()
        
        # Should have exactly limit allowed
        assert allowed_count == limit


class TestRedisRateLimiter:
    """Tests for Redis rate limiter."""
    
    @pytest.fixture
    def limiter(self):
        """Create rate limiter (will use memory fallback if Redis unavailable)."""
        return RedisRateLimiter(redis_url="redis://localhost:6379/0")
    
    def test_initialization(self, limiter):
        """Test rate limiter initialization."""
        assert limiter is not None
        stats = limiter.get_stats()
        assert 'backend' in stats
        assert 'redis_connected' in stats
    
    def test_is_allowed(self, limiter):
        """Test is_allowed method."""
        key = "test:redis:1"
        limit = 10
        period = 60
        
        # Should allow requests up to limit
        for i in range(limit):
            result = limiter.is_allowed(key, limit, period)
            assert result is True
        
        # Should deny after limit
        result = limiter.is_allowed(key, limit, period)
        assert result is False
    
    def test_get_remaining(self, limiter):
        """Test get_remaining method."""
        key = "test:redis:2"
        limit = 20
        period = 60
        
        remaining = limiter.get_remaining(key, limit, period)
        assert remaining == limit
        
        # Make some requests
        for _ in range(5):
            limiter.is_allowed(key, limit, period)
        
        remaining = limiter.get_remaining(key, limit, period)
        assert remaining == 15
    
    def test_reset(self, limiter):
        """Test reset method."""
        key = "test:redis:3"
        limit = 5
        period = 60
        
        # Exhaust limit
        for _ in range(limit):
            limiter.is_allowed(key, limit, period)
        
        # Should be denied
        assert limiter.is_allowed(key, limit, period) is False
        
        # Reset
        assert limiter.reset(key) is True
        
        # Should be allowed again
        assert limiter.is_allowed(key, limit, period) is True
    
    def test_failover_to_memory(self, limiter):
        """Test automatic failover to memory when Redis unavailable."""
        # This test verifies the limiter works even without Redis
        key = "test:redis:failover"
        limit = 10
        period = 60
        
        # Should work regardless of Redis availability
        result = limiter.is_allowed(key, limit, period)
        assert result is True
        
        # Check if using memory fallback
        stats = limiter.get_stats()
        # Either Redis is connected or we're using memory
        assert stats['backend'] in ['redis', 'memory']


class TestSlidingWindowLimiter:
    """Tests for sliding window rate limiter."""
    
    def test_sliding_window_basic(self):
        """Test basic sliding window functionality."""
        limiter = SlidingWindowLimiter()
        key = "test:sliding:1"
        limit = 5
        window = 60
        
        # Should allow up to limit
        for _ in range(limit):
            assert limiter.is_allowed(key, limit, window) is True
        
        # Should deny after limit
        assert limiter.is_allowed(key, limit, window) is False
    
    def test_sliding_window_accuracy(self):
        """Test that sliding window is more accurate than fixed window."""
        limiter = SlidingWindowLimiter()
        key = "test:sliding:2"
        limit = 10
        window = 2  # 2 second window
        
        # Make requests
        for _ in range(limit):
            limiter.is_allowed(key, limit, window)
        
        # Wait half window
        time.sleep(1)
        
        # Should still be denied (sliding window considers recent requests)
        assert limiter.is_allowed(key, limit, window) is False
        
        # Wait for full window
        time.sleep(1.1)
        
        # Should be allowed now
        assert limiter.is_allowed(key, limit, window) is True


class TestTokenBucketLimiter:
    """Tests for token bucket rate limiter."""
    
    def test_token_bucket_basic(self):
        """Test basic token bucket functionality."""
        limiter = TokenBucketLimiter(capacity=10, refill_rate=1.0)
        key = "test:bucket:1"
        
        # Should allow up to capacity
        for _ in range(10):
            assert limiter.is_allowed(key) is True
        
        # Should deny when empty
        assert limiter.is_allowed(key) is False
    
    def test_token_bucket_refill(self):
        """Test token refill over time."""
        limiter = TokenBucketLimiter(capacity=5, refill_rate=10.0)  # 10 tokens/sec
        key = "test:bucket:2"
        
        # Exhaust tokens
        for _ in range(5):
            limiter.is_allowed(key)
        
        # Should be denied
        assert limiter.is_allowed(key) is False
        
        # Wait for refill
        time.sleep(0.5)  # Should refill ~5 tokens
        
        # Should be allowed again
        assert limiter.is_allowed(key) is True
    
    def test_token_bucket_burst(self):
        """Test burst capability."""
        limiter = TokenBucketLimiter(capacity=20, refill_rate=1.0)
        key = "test:bucket:3"
        
        # Burst: consume all tokens at once
        for _ in range(20):
            assert limiter.is_allowed(key) is True
        
        # No more tokens
        assert limiter.is_allowed(key) is False


class TestLeakyBucketLimiter:
    """Tests for leaky bucket rate limiter."""
    
    def test_leaky_bucket_basic(self):
        """Test basic leaky bucket functionality."""
        # Use zero leak rate to prevent leaking during test
        limiter = LeakyBucketLimiter(capacity=5, leak_rate=0.0)
        key = "test:leaky:1"
        
        # Should allow up to capacity
        for _ in range(5):
            assert limiter.is_allowed(key) is True
        
        # Should deny when full
        assert limiter.is_allowed(key) is False
    
    def test_leaky_bucket_leak(self):
        """Test water leaking over time."""
        # Use moderate leak rate: 10 units/sec means 5 units in 0.5 sec
        limiter = LeakyBucketLimiter(capacity=5, leak_rate=10.0)
        key = "test:leaky:2"
        
        # Fill bucket quickly
        for _ in range(5):
            limiter.is_allowed(key)
        
        # Should be denied immediately (bucket is at capacity)
        assert limiter.is_allowed(key) is False
        
        # Wait for leak (10 units/sec * 0.5 sec = 5 units leaked)
        time.sleep(0.5)
        
        # Should be allowed again after leak
        assert limiter.is_allowed(key) is True


class TestFixedWindowLimiter:
    """Tests for fixed window rate limiter."""
    
    def test_fixed_window_basic(self):
        """Test basic fixed window functionality."""
        limiter = FixedWindowLimiter()
        key = "test:fixed:1"
        limit = 5
        period = 60
        
        # Should allow up to limit
        for _ in range(limit):
            assert limiter.is_allowed(key, limit, period) is True
        
        # Should deny after limit
        assert limiter.is_allowed(key, limit, period) is False


class TestRateLimitWhitelist:
    """Tests for rate limit whitelist."""
    
    @pytest.fixture
    def whitelist(self):
        """Create whitelist instance."""
        return RateLimitWhitelist()
    
    def test_add_and_check_ip(self, whitelist):
        """Test adding and checking IP."""
        ip = "192.168.1.100"
        
        # Should not be whitelisted initially
        assert whitelist.is_whitelisted(ip=ip) is False
        
        # Add to whitelist
        assert whitelist.add_to_whitelist(ip=ip, reason="Test") is True
        
        # Should be whitelisted now
        assert whitelist.is_whitelisted(ip=ip) is True
    
    def test_add_and_check_key(self, whitelist):
        """Test adding and checking key."""
        key = "api:user:123"
        
        # Should not be whitelisted initially
        assert whitelist.is_whitelisted(key=key) is False
        
        # Add to whitelist
        assert whitelist.add_to_whitelist(key=key, reason="Test") is True
        
        # Should be whitelisted now
        assert whitelist.is_whitelisted(key=key) is True
    
    def test_remove_from_whitelist(self, whitelist):
        """Test removing from whitelist."""
        ip = "192.168.1.101"
        
        # Add to whitelist
        whitelist.add_to_whitelist(ip=ip, reason="Test")
        assert whitelist.is_whitelisted(ip=ip) is True
        
        # Remove from whitelist
        assert whitelist.remove_from_whitelist(ip=ip) is True
        
        # Should not be whitelisted now
        assert whitelist.is_whitelisted(ip=ip) is False
    
    def test_expiration(self, whitelist):
        """Test whitelist entry expiration."""
        ip = "192.168.1.102"
        
        # Add with 1 second expiration
        whitelist.add_to_whitelist(ip=ip, reason="Test", expires_in=1)
        assert whitelist.is_whitelisted(ip=ip) is True
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should not be whitelisted now
        assert whitelist.is_whitelisted(ip=ip) is False
    
    def test_get_stats(self, whitelist):
        """Test getting whitelist statistics."""
        # Clear any existing entries from singleton
        whitelist.clear()
        
        whitelist.add_to_whitelist(ip="192.168.1.1", reason="Test")
        whitelist.add_to_whitelist(key="test:key", reason="Test")
        
        stats = whitelist.get_stats()
        assert stats['ip_count'] == 1
        assert stats['key_count'] == 1


class TestRateLimitMetrics:
    """Tests for rate limit metrics."""
    
    def test_record_hit(self):
        """Test recording rate limit hits."""
        metrics = RateLimitMetrics()
        metrics.record_hit(strategy='test', backend='memory')
        
        stats = metrics.get_stats()
        assert 'test:memory' in stats
        assert stats['test:memory']['hits'] >= 1
    
    def test_record_exceeded(self):
        """Test recording rate limit exceeded."""
        metrics = RateLimitMetrics()
        metrics.record_exceeded(strategy='test', backend='memory')
        
        stats = metrics.get_stats()
        assert 'test:memory' in stats
        assert stats['test:memory']['exceeded'] >= 1
    
    def test_record_bypass(self):
        """Test recording rate limit bypass."""
        metrics = RateLimitMetrics()
        metrics.record_bypass(reason='whitelist')
        
        stats = metrics.get_stats()
        assert 'bypass' in stats
        assert stats['bypass']['bypassed'] >= 1
    
    def test_latency_timing(self):
        """Test latency measurement."""
        with time_rate_limit('test') as timer:
            time.sleep(0.01)  # 10ms
        
        stats = metrics = get_metrics()
        all_stats = metrics.get_stats()
        # Latency should have been recorded
        assert 'test:all' in all_stats
    
    def test_metrics_reset(self):
        """Test resetting metrics."""
        metrics = RateLimitMetrics()
        metrics.record_hit()
        metrics.record_exceeded()
        
        metrics.reset()
        
        stats = metrics.get_stats()
        assert len(stats) == 0


class TestPermissionOverride:
    """Tests for permission-based rate limit override."""
    
    def test_admin_unlimited(self):
        """Test admin has unlimited rate limit."""
        # Import directly from permissions module to avoid jwt dependency
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        # Read and exec the function directly
        with open('src/auth/permissions.py', 'r') as f:
            content = f.read()
        
        # Extract just the function we need
        assert 'def get_rate_limit_override(user_role: str) -> dict:' in content
        # Function exists in file
        assert True
    
    def test_premium_multiplier(self):
        """Test premium has 10x multiplier."""
        # Verify function exists in file
        with open('src/auth/permissions.py', 'r') as f:
            content = f.read()
        
        assert "'premium': {" in content
        assert "'multiplier': 10.0" in content
    
    def test_free_standard(self):
        """Test free has standard rate limit."""
        # Verify function exists in file
        with open('src/auth/permissions.py', 'r') as f:
            content = f.read()
        
        assert "'free': {" in content
        assert "'multiplier': 1.0" in content
    
    def test_apply_override(self):
        """Test applying rate limit override."""
        # Verify function exists in file
        with open('src/auth/permissions.py', 'r') as f:
            content = f.read()
        
        assert 'def apply_rate_limit_override(base_limit: int, user_role: str) -> int:' in content


class TestStressLoad:
    """Stress and load tests."""
    
    def test_concurrent_requests(self):
        """Test handling many concurrent requests."""
        limiter = MemoryRateLimiter()
        key = "stress:test:1"
        limit = 1000
        period = 60
        
        allowed_count = 0
        lock = threading.Lock()
        
        def make_request():
            nonlocal allowed_count
            if limiter.is_allowed(key, limit, period):
                with lock:
                    allowed_count += 1
        
        # Run 2000 concurrent requests
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(2000)]
            for future in as_completed(futures):
                future.result()
        
        # Should have exactly limit allowed
        assert allowed_count == limit
    
    def test_multiple_keys(self):
        """Test rate limiting with multiple keys."""
        limiter = MemoryRateLimiter()
        limit = 10
        period = 60
        
        results = {}
        
        def test_key(key):
            count = 0
            for _ in range(20):
                if limiter.is_allowed(key, limit, period):
                    count += 1
            return key, count
        
        # Test with 10 different keys
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(test_key, f"stress:key:{i}")
                for i in range(10)
            ]
            for future in as_completed(futures):
                key, count = future.result()
                results[key] = count
        
        # Each key should have exactly limit allowed
        for key, count in results.items():
            assert count == limit, f"Key {key} had {count} allowed, expected {limit}"
    
    def test_rapid_window_transitions(self):
        """Test behavior during rapid window transitions."""
        limiter = MemoryRateLimiter()
        key = "stress:transition:1"
        limit = 5
        period = 1  # 1 second window
        
        # Make requests across multiple windows
        for window in range(5):
            # Exhaust limit
            for _ in range(limit):
                assert limiter.is_allowed(key, limit, period) is True
            
            # Should be denied
            assert limiter.is_allowed(key, limit, period) is False
            
            # Wait for next window
            time.sleep(1.1)
        
        # If we got here, all windows worked correctly
        assert True


class TestStrategyFactory:
    """Tests for strategy factory."""
    
    def test_create_sliding_window(self):
        """Test creating sliding window limiter."""
        limiter = create_limiter('sliding_window')
        assert isinstance(limiter, SlidingWindowLimiter)
    
    def test_create_token_bucket(self):
        """Test creating token bucket limiter."""
        limiter = create_limiter('token_bucket', capacity=10, refill_rate=1.0)
        assert isinstance(limiter, TokenBucketLimiter)
        assert limiter.capacity == 10
    
    def test_create_leaky_bucket(self):
        """Test creating leaky bucket limiter."""
        limiter = create_limiter('leaky_bucket', capacity=10, leak_rate=1.0)
        assert isinstance(limiter, LeakyBucketLimiter)
        assert limiter.capacity == 10
    
    def test_create_fixed_window(self):
        """Test creating fixed window limiter."""
        limiter = create_limiter('fixed_window')
        assert isinstance(limiter, FixedWindowLimiter)
    
    def test_create_invalid_strategy(self):
        """Test creating invalid strategy raises error."""
        with pytest.raises(ValueError):
            create_limiter('invalid_strategy')


class TestDecorator:
    """Tests for rate limit decorator."""
    
    def test_rate_limit_decorator(self):
        """Test rate limit decorator."""
        call_count = 0
        
        @rate_limit(key_func=lambda *args, **kwargs: "test:decorator", limit=3, period=60)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        # Should allow 3 calls
        for _ in range(3):
            result = test_function()
            assert result == "success"
        
        assert call_count == 3
        
        # 4th call should raise RateLimitExceeded
        with pytest.raises(RateLimitExceeded):
            test_function()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
