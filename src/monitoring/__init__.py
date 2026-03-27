"""
Monitoring module for Amazon Selector v2.3.0

Provides Prometheus metrics, request tracing, error tracking, and slow query logging.
"""

__version__ = "2.3.0"

from .prometheus import (
    # HTTP Metrics
    HTTP_REQUESTS,
    HTTP_DURATION,
    # DB Metrics
    DB_CONNECTIONS,
    DB_QUERY_DURATION,
    # Business Metrics
    PRODUCTS_SCANNED,
    HISTORY_RECORDS,
    # Functions
    expose_metrics,
    get_metrics_text,
    PrometheusMetrics,
    get_prometheus_metrics,
)

from .request_tracing import (
    RequestTracer,
    TraceSpan,
    TraceContext,
    start_trace,
    end_trace,
    add_span,
    get_trace,
    get_slow_traces,
)

from .error_tracking import (
    ErrorTracker,
    ErrorRecord,
    track_error,
    get_errors,
    get_error_rate,
    get_top_errors,
)

__all__ = [
    # Prometheus
    'HTTP_REQUESTS',
    'HTTP_DURATION',
    'DB_CONNECTIONS',
    'DB_QUERY_DURATION',
    'PRODUCTS_SCANNED',
    'HISTORY_RECORDS',
    'expose_metrics',
    'get_metrics_text',
    'PrometheusMetrics',
    'get_prometheus_metrics',
    # Request Tracing
    'RequestTracer',
    'TraceSpan',
    'TraceContext',
    'start_trace',
    'end_trace',
    'add_span',
    'get_trace',
    'get_slow_traces',
    # Error Tracking
    'ErrorTracker',
    'ErrorRecord',
    'track_error',
    'get_errors',
    'get_error_rate',
    'get_top_errors',
]
