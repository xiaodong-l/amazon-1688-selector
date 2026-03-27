"""
Prometheus Metrics for Amazon Selector

Provides application metrics, business metrics, and metrics endpoint.
"""

import time
from typing import Dict, Optional, Any
import threading
import logging

logger = logging.getLogger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed, using in-memory metrics fallback")


# In-memory fallback classes
class InMemoryCounter:
    """In-memory counter fallback when Prometheus is not available."""
    
    def __init__(self, name: str, documentation: str, labelnames=None):
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames or []
        self._values: Dict[str, int] = {}
        self._lock = threading.Lock()
    
    def labels(self, **kwargs):
        label_key = tuple(sorted(kwargs.items()))
        return LabelledCounter(self, label_key)
    
    def inc(self, value: int = 1) -> None:
        with self._lock:
            key = str(tuple())
            self._values[key] = self._values.get(key, 0) + value
    
    def get(self, labels: tuple = ()) -> int:
        with self._lock:
            return self._values.get(str(labels), 0)


class LabelledCounter:
    """Labelled counter wrapper."""
    
    def __init__(self, counter: InMemoryCounter, label_key: tuple):
        self._counter = counter
        self._label_key = label_key
    
    def inc(self, value: int = 1) -> None:
        with self._counter._lock:
            key = str(self._label_key)
            self._counter._values[key] = self._counter._values.get(key, 0) + value


class InMemoryHistogram:
    """In-memory histogram fallback."""
    
    def __init__(self, name: str, documentation: str, labelnames=None, buckets=None):
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames or []
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._values: Dict[str, Dict] = {}
        self._lock = threading.Lock()
    
    def labels(self, **kwargs):
        label_key = tuple(sorted(kwargs.items()))
        return LabelledHistogram(self, label_key)
    
    def observe(self, value: float) -> None:
        with self._lock:
            key = str(tuple())
            if key not in self._values:
                self._values[key] = {'buckets': {b: 0 for b in self.buckets}, 'sum': 0, 'count': 0}
            data = self._values[key]
            data['count'] += 1
            data['sum'] += value
            for bucket in self.buckets:
                if value <= bucket:
                    data['buckets'][bucket] += 1
    
    def get(self) -> Dict[str, Any]:
        with self._lock:
            return self._values.get(str(tuple()), {'buckets': {}, 'sum': 0, 'count': 0})


class LabelledHistogram:
    """Labelled histogram wrapper."""
    
    def __init__(self, histogram: InMemoryHistogram, label_key: tuple):
        self._histogram = histogram
        self._label_key = label_key
    
    def observe(self, value: float) -> None:
        with self._histogram._lock:
            key = str(self._label_key)
            if key not in self._histogram._values:
                self._histogram._values[key] = {'buckets': {b: 0 for b in self._histogram.buckets}, 'sum': 0, 'count': 0}
            data = self._histogram._values[key]
            data['count'] += 1
            data['sum'] += value
            for bucket in self._histogram.buckets:
                if value <= bucket:
                    data['buckets'][bucket] += 1


class InMemoryGauge:
    """In-memory gauge fallback."""
    
    def __init__(self, name: str, documentation: str, labelnames=None):
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames or []
        self._values: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def labels(self, **kwargs):
        label_key = tuple(sorted(kwargs.items()))
        return LabelledGauge(self, label_key)
    
    def set(self, value: float) -> None:
        with self._lock:
            self._values[str(tuple())] = value
    
    def inc(self, value: float = 1) -> None:
        with self._lock:
            key = str(tuple())
            self._values[key] = self._values.get(key, 0) + value
    
    def dec(self, value: float = 1) -> None:
        with self._lock:
            key = str(tuple())
            self._values[key] = self._values.get(key, 0) - value
    
    def get(self) -> float:
        with self._lock:
            return self._values.get(str(tuple()), 0)


class LabelledGauge:
    """Labelled gauge wrapper."""
    
    def __init__(self, gauge: InMemoryGauge, label_key: tuple):
        self._gauge = gauge
        self._label_key = label_key
    
    def set(self, value: float) -> None:
        with self._gauge._lock:
            self._gauge._values[str(self._label_key)] = value
    
    def inc(self, value: float = 1) -> None:
        with self._gauge._lock:
            key = str(self._label_key)
            self._gauge._values[key] = self._gauge._values.get(key, 0) + value
    
    def dec(self, value: float = 1) -> None:
        with self._gauge._lock:
            key = str(self._label_key)
            self._gauge._values[key] = self._gauge._values.get(key, 0) - value


# Define Prometheus metrics
if PROMETHEUS_AVAILABLE:
    # HTTP Metrics
    HTTP_REQUESTS = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    HTTP_DURATION = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration in seconds',
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    
    # Database Metrics
    DB_CONNECTIONS = Gauge(
        'db_connections_active',
        'Number of active database connections'
    )
    
    DB_QUERY_DURATION = Histogram(
        'db_query_duration_seconds',
        'Database query duration in seconds',
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
    )
    
    # Business Metrics
    PRODUCTS_SCANNED = Counter(
        'products_scanned_total',
        'Total number of products scanned'
    )
    
    HISTORY_RECORDS = Counter(
        'history_records_total',
        'Total number of history records created'
    )
else:
    # Fallback to in-memory metrics
    HTTP_REQUESTS = InMemoryCounter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
    HTTP_DURATION = InMemoryHistogram('http_request_duration_seconds', 'HTTP request duration')
    DB_CONNECTIONS = InMemoryGauge('db_connections_active', 'Active DB connections')
    DB_QUERY_DURATION = InMemoryHistogram('db_query_duration_seconds', 'DB query duration')
    PRODUCTS_SCANNED = InMemoryCounter('products_scanned_total', 'Products scanned')
    HISTORY_RECORDS = InMemoryCounter('history_records_total', 'History records')


class PrometheusMetrics:
    """
    Prometheus metrics collector and reporter.
    
    Provides both Prometheus metrics and in-memory statistics.
    """
    
    _instance: Optional['PrometheusMetrics'] = None
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
        
        self._stats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._initialized = True
    
    def record_http_request(self, method: str, endpoint: str, status: int, duration: float) -> None:
        """Record an HTTP request."""
        if PROMETHEUS_AVAILABLE:
            HTTP_REQUESTS.labels(method=method, endpoint=endpoint, status=status).inc()
            HTTP_DURATION.observe(duration)
        
        with self._lock:
            key = f"{method}:{endpoint}:{status}"
            if key not in self._stats:
                self._stats[key] = {'count': 0, 'duration_total': 0.0}
            self._stats[key]['count'] += 1
            self._stats[key]['duration_total'] += duration
    
    def record_db_query(self, duration: float) -> None:
        """Record a database query."""
        if PROMETHEUS_AVAILABLE:
            DB_QUERY_DURATION.observe(duration)
    
    def set_db_connections(self, count: int) -> None:
        """Set active database connections count."""
        if PROMETHEUS_AVAILABLE:
            DB_CONNECTIONS.set(count)
    
    def record_product_scanned(self, count: int = 1) -> None:
        """Record products scanned."""
        if PROMETHEUS_AVAILABLE:
            PRODUCTS_SCANNED.inc(count)
    
    def record_history_record(self, count: int = 1) -> None:
        """Record history records created."""
        if PROMETHEUS_AVAILABLE:
            HISTORY_RECORDS.inc(count)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        with self._lock:
            stats = {}
            for key, data in self._stats.items():
                avg_duration = (
                    data['duration_total'] / data['count']
                    if data['count'] > 0 else 0
                )
                stats[key] = {
                    'count': data['count'],
                    'avg_duration_ms': avg_duration * 1000,
                    'total_duration_ms': data['duration_total'] * 1000,
                }
            return stats
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._stats.clear()
        logger.info("Prometheus metrics reset")


# Module-level singleton
_metrics: Optional[PrometheusMetrics] = None


def get_prometheus_metrics() -> PrometheusMetrics:
    """Get or create metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = PrometheusMetrics()
    return _metrics


def expose_metrics() -> str:
    """
    Expose Prometheus metrics in text format.
    
    Returns metrics in Prometheus exposition format.
    """
    if PROMETHEUS_AVAILABLE:
        return generate_latest().decode('utf-8')
    else:
        # Return simple text summary
        metrics = get_prometheus_metrics()
        stats = metrics.get_stats()
        lines = [
            "# Prometheus metrics (in-memory fallback)",
            "# prometheus_client not installed",
            ""
        ]
        for key, data in stats.items():
            lines.append(f"# {key}: count={data['count']}, avg_duration_ms={data['avg_duration_ms']:.2f}")
        return '\n'.join(lines)


def get_metrics_text() -> str:
    """Alias for expose_metrics()."""
    return expose_metrics()


# Context manager for timing HTTP requests
class HTTPRequestTimer:
    """Context manager for timing HTTP requests."""
    
    def __init__(self, method: str, endpoint: str):
        self.method = method
        self.endpoint = endpoint
        self.start_time = None
        self.status = 200
        self.metrics = get_prometheus_metrics()
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type is not None:
            self.status = 500
        self.metrics.record_http_request(self.method, self.endpoint, self.status, duration)
        return False


def time_request(method: str, endpoint: str) -> HTTPRequestTimer:
    """Get timer for HTTP request."""
    return HTTPRequestTimer(method, endpoint)
