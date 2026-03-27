"""
Rate Limiting Prometheus Metrics
Monitor rate limiting behavior and performance.
"""

from typing import Dict, Optional, Any
import threading
import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Try to import prometheus_client, provide fallback if not available
try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed, using in-memory metrics")


class InMemoryCounter:
    """In-memory counter fallback when Prometheus is not available."""
    
    def __init__(self, name: str, documentation: str):
        self.name = name
        self.documentation = documentation
        self._value = 0
        self._lock = threading.Lock()
    
    def inc(self, value: int = 1) -> None:
        with self._lock:
            self._value += value
    
    def get(self) -> int:
        with self._lock:
            return self._value


class InMemoryHistogram:
    """In-memory histogram fallback."""
    
    def __init__(self, name: str, documentation: str, buckets=None):
        self.name = name
        self.documentation = documentation
        self.buckets = buckets or [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._counts = defaultdict(int)
        self._sum = 0
        self._count = 0
        self._lock = threading.Lock()
    
    def observe(self, value: float) -> None:
        with self._lock:
            self._count += 1
            self._sum += value
            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[bucket] += 1
            self._counts[float('inf')] += 1
    
    def get(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'buckets': dict(self._counts),
                'sum': self._sum,
                'count': self._count,
            }


class InMemoryGauge:
    """In-memory gauge fallback."""
    
    def __init__(self, name: str, documentation: str):
        self.name = name
        self.documentation = documentation
        self._value = 0
        self._lock = threading.Lock()
    
    def set(self, value: float) -> None:
        with self._lock:
            self._value = value
    
    def inc(self, value: float = 1) -> None:
        with self._lock:
            self._value += value
    
    def dec(self, value: float = 1) -> None:
        with self._lock:
            self._value -= value
    
    def get(self) -> float:
        with self._lock:
            return self._value


# Define metrics
if PROMETHEUS_AVAILABLE:
    # Counters
    RATE_LIMIT_HITS = Counter(
        'rate_limit_hits_total',
        'Total number of rate limit checks',
        ['strategy', 'backend']
    )
    
    RATE_LIMIT_EXCEEDED = Counter(
        'rate_limit_exceeded_total',
        'Total number of rate limit exceeded events',
        ['strategy', 'backend', 'key_type']
    )
    
    RATE_LIMIT_BYPASS = Counter(
        'rate_limit_bypass_total',
        'Total number of rate limit bypasses (whitelist/permissions)',
        ['reason']
    )
    
    # Histograms
    RATE_LIMIT_LATENCY = Histogram(
        'rate_limit_latency_seconds',
        'Rate limit check latency',
        ['strategy'],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
    )
    
    RATE_LIMIT_REMAINING = Histogram(
        'rate_limit_remaining',
        'Remaining requests in rate limit window',
        ['strategy'],
        buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000]
    )
    
    # Gauges
    RATE_LIMIT_ACTIVE_KEYS = Gauge(
        'rate_limit_active_keys',
        'Number of active rate limit keys',
        ['strategy']
    )
    
    RATE_LIMIT_BACKEND_STATUS = Gauge(
        'rate_limit_backend_status',
        'Rate limit backend health (1=healthy, 0=unhealthy)',
        ['backend']
    )
    
    RATE_LIMIT_MEMORY_USAGE = Gauge(
        'rate_limit_memory_fallback_active',
        'Whether rate limiter is using memory fallback (1=yes, 0=no)',
    )
else:
    # Fallback to in-memory metrics
    RATE_LIMIT_HITS = InMemoryCounter('rate_limit_hits_total', 'Total rate limit checks')
    RATE_LIMIT_EXCEEDED = InMemoryCounter('rate_limit_exceeded_total', 'Rate limit exceeded')
    RATE_LIMIT_BYPASS = InMemoryCounter('rate_limit_bypass_total', 'Rate limit bypasses')
    RATE_LIMIT_LATENCY = InMemoryHistogram('rate_limit_latency_seconds', 'Rate limit latency')
    RATE_LIMIT_REMAINING = InMemoryHistogram('rate_limit_remaining', 'Remaining requests')
    RATE_LIMIT_ACTIVE_KEYS = InMemoryGauge('rate_limit_active_keys', 'Active keys')
    RATE_LIMIT_BACKEND_STATUS = InMemoryGauge('rate_limit_backend_status', 'Backend status')
    RATE_LIMIT_MEMORY_USAGE = InMemoryGauge('rate_limit_memory_fallback_active', 'Memory fallback')


class RateLimitMetrics:
    """
    Rate limit metrics collector and reporter.
    
    Provides both Prometheus metrics and in-memory statistics.
    """
    
    _instance: Optional['RateLimitMetrics'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'hits': 0,
            'exceeded': 0,
            'bypassed': 0,
            'latency_total': 0.0,
            'latency_count': 0,
        })
        self._lock = threading.RLock()
        self._initialized = True
    
    def record_hit(self, strategy: str = 'default', backend: str = 'memory') -> None:
        """Record a rate limit check."""
        if PROMETHEUS_AVAILABLE:
            RATE_LIMIT_HITS.labels(strategy=strategy, backend=backend).inc()
        
        with self._lock:
            key = f"{strategy}:{backend}"
            self._stats[key]['hits'] += 1
    
    def record_exceeded(self, strategy: str = 'default', backend: str = 'memory',
                       key_type: str = 'ip') -> None:
        """Record a rate limit exceeded event."""
        if PROMETHEUS_AVAILABLE:
            RATE_LIMIT_EXCEEDED.labels(
                strategy=strategy, backend=backend, key_type=key_type
            ).inc()
        
        with self._lock:
            key = f"{strategy}:{backend}"
            self._stats[key]['exceeded'] += 1
    
    def record_bypass(self, reason: str = 'whitelist') -> None:
        """Record a rate limit bypass."""
        if PROMETHEUS_AVAILABLE:
            RATE_LIMIT_BYPASS.labels(reason=reason).inc()
        
        with self._lock:
            self._stats['bypass']['bypassed'] += 1
    
    def record_latency(self, strategy: str, latency: float) -> None:
        """Record rate limit check latency."""
        if PROMETHEUS_AVAILABLE:
            RATE_LIMIT_LATENCY.labels(strategy=strategy).observe(latency)
        
        with self._lock:
            key = f"{strategy}:all"
            self._stats[key]['latency_total'] += latency
            self._stats[key]['latency_count'] += 1
    
    def record_remaining(self, strategy: str, remaining: int) -> None:
        """Record remaining requests."""
        if PROMETHEUS_AVAILABLE:
            RATE_LIMIT_REMAINING.labels(strategy=strategy).observe(remaining)
    
    def set_active_keys(self, strategy: str, count: int) -> None:
        """Set number of active rate limit keys."""
        if PROMETHEUS_AVAILABLE:
            RATE_LIMIT_ACTIVE_KEYS.labels(strategy=strategy).set(count)
    
    def set_backend_status(self, backend: str, healthy: bool) -> None:
        """Set backend health status."""
        if PROMETHEUS_AVAILABLE:
            RATE_LIMIT_BACKEND_STATUS.labels(backend=backend).set(1 if healthy else 0)
    
    def set_memory_fallback(self, active: bool) -> None:
        """Set memory fallback status."""
        if PROMETHEUS_AVAILABLE:
            RATE_LIMIT_MEMORY_USAGE.set(1 if active else 0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        with self._lock:
            stats = {}
            for key, data in self._stats.items():
                avg_latency = (
                    data['latency_total'] / data['latency_count']
                    if data['latency_count'] > 0 else 0
                )
                stats[key] = {
                    'hits': data['hits'],
                    'exceeded': data['exceeded'],
                    'bypassed': data.get('bypassed', 0),
                    'avg_latency_ms': avg_latency * 1000,
                    'exceed_rate': (
                        data['exceeded'] / data['hits'] * 100
                        if data['hits'] > 0 else 0
                    ),
                }
            return stats
    
    def get_metrics_text(self) -> str:
        """Get Prometheus metrics in text format."""
        if PROMETHEUS_AVAILABLE:
            return generate_latest().decode('utf-8')
        else:
            # Return simple text summary
            stats = self.get_stats()
            lines = ["# In-memory metrics (prometheus_client not installed)"]
            for key, data in stats.items():
                lines.append(f"# {key}: hits={data['hits']}, exceeded={data['exceeded']}")
            return '\n'.join(lines)
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._stats.clear()
        logger.info("Rate limit metrics reset")


# Context manager for timing rate limit checks
class RateLimitTimer:
    """Context manager for timing rate limit checks."""
    
    def __init__(self, strategy: str = 'default'):
        self.strategy = strategy
        self.start_time = None
        self.metrics = RateLimitMetrics()
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.time() - self.start_time
        self.metrics.record_latency(self.strategy, latency)
        return False


# Module-level singleton
_metrics: Optional[RateLimitMetrics] = None


def get_metrics() -> RateLimitMetrics:
    """Get or create metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = RateLimitMetrics()
    return _metrics


# Convenience functions
def record_hit(strategy: str = 'default', backend: str = 'memory') -> None:
    """Record a rate limit hit."""
    get_metrics().record_hit(strategy, backend)


def record_exceeded(strategy: str = 'default', backend: str = 'memory',
                   key_type: str = 'ip') -> None:
    """Record a rate limit exceeded."""
    get_metrics().record_exceeded(strategy, backend, key_type)


def record_bypass(reason: str = 'whitelist') -> None:
    """Record a rate limit bypass."""
    get_metrics().record_bypass(reason)


def time_rate_limit(strategy: str = 'default') -> RateLimitTimer:
    """Get timer for rate limit operation."""
    return RateLimitTimer(strategy)
