"""
Tests for Monitoring Module

Tests for Prometheus metrics, request tracing, error tracking, and slow query logging.
"""

import pytest
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.monitoring.prometheus import (
    PrometheusMetrics,
    get_prometheus_metrics,
    expose_metrics,
    HTTP_REQUESTS,
    HTTP_DURATION,
)

from src.monitoring.request_tracing import (
    RequestTracer,
    get_tracer,
    start_trace,
    end_trace,
    add_span,
    get_trace,
    get_slow_traces,
    trace_request,
)

from src.monitoring.error_tracking import (
    ErrorTracker,
    get_error_tracker,
    track_error,
    get_errors,
    get_error_rate,
    get_top_errors,
)

from src.db.monitor import (
    QueryMonitor,
    get_query_monitor,
    log_slow_query,
    get_slow_queries,
    SLOW_QUERY_THRESHOLD,
)


class TestPrometheusMetrics:
    """Tests for Prometheus metrics."""
    
    def test_singleton_instance(self):
        """Test that PrometheusMetrics is a singleton."""
        metrics1 = get_prometheus_metrics()
        metrics2 = get_prometheus_metrics()
        assert metrics1 is metrics2
    
    def test_record_http_request(self):
        """Test recording HTTP requests."""
        metrics = get_prometheus_metrics()
        metrics.reset()  # Start fresh
        
        # Record some requests
        metrics.record_http_request('GET', '/api/products', 200, 0.05)
        metrics.record_http_request('GET', '/api/products', 200, 0.03)
        metrics.record_http_request('POST', '/api/products', 201, 0.1)
        
        stats = metrics.get_stats()
        
        assert 'GET:/api/products:200' in stats
        assert stats['GET:/api/products:200']['count'] == 2
        
        assert 'POST:/api/products:201' in stats
        assert stats['POST:/api/products:201']['count'] == 1
    
    def test_record_db_query(self):
        """Test recording database queries."""
        metrics = get_prometheus_metrics()
        
        # Should not raise
        metrics.record_db_query(0.05)
        metrics.record_db_query(0.1)
    
    def test_set_db_connections(self):
        """Test setting database connections count."""
        metrics = get_prometheus_metrics()
        
        # Should not raise
        metrics.set_db_connections(5)
        metrics.set_db_connections(10)
    
    def test_record_product_scanned(self):
        """Test recording products scanned."""
        metrics = get_prometheus_metrics()
        
        # Should not raise
        metrics.record_product_scanned(1)
        metrics.record_product_scanned(5)
    
    def test_record_history_record(self):
        """Test recording history records."""
        metrics = get_prometheus_metrics()
        
        # Should not raise
        metrics.record_history_record(1)
        metrics.record_history_record(10)
    
    def test_expose_metrics(self):
        """Test exposing metrics."""
        metrics_text = expose_metrics()
        
        assert isinstance(metrics_text, str)
        assert len(metrics_text) > 0
    
    def test_http_request_timer(self):
        """Test HTTP request timer context manager."""
        from src.monitoring.prometheus import HTTPRequestTimer, time_request
        
        metrics = get_prometheus_metrics()
        metrics.reset()
        
        with HTTPRequestTimer('GET', '/api/test') as timer:
            time.sleep(0.01)  # Small delay
            timer.status = 200
        
        stats = metrics.get_stats()
        assert 'GET:/api/test:200' in stats
    
    def test_reset_metrics(self):
        """Test resetting metrics."""
        metrics = get_prometheus_metrics()
        
        # Record some data
        metrics.record_http_request('GET', '/test', 200, 0.1)
        
        # Reset
        metrics.reset()
        
        stats = metrics.get_stats()
        assert len(stats) == 0


class TestRequestTracing:
    """Tests for request tracing."""
    
    def test_singleton_instance(self):
        """Test that RequestTracer is a singleton."""
        tracer1 = get_tracer()
        tracer2 = get_tracer()
        assert tracer1 is tracer2
    
    def test_start_trace(self):
        """Test starting a trace."""
        tracer = get_tracer()
        tracer.clear()  # Start fresh
        
        trace_id = tracer.start_trace(endpoint='/api/test')
        
        assert trace_id is not None
        assert len(trace_id) > 0
    
    def test_add_span(self):
        """Test adding spans to a trace."""
        tracer = get_tracer()
        tracer.clear()
        
        trace_id = tracer.start_trace(endpoint='/api/test')
        
        # Add spans
        span1 = tracer.add_span(trace_id, 'db_query', duration=0.05)
        span2 = tracer.add_span(trace_id, 'cache_lookup', duration=0.01)
        
        assert span1 is not None
        assert span2 is not None
        assert span1.name == 'db_query'
        assert span2.name == 'cache_lookup'
    
    def test_end_trace(self):
        """Test ending a trace."""
        tracer = get_tracer()
        tracer.clear()
        
        trace_id = tracer.start_trace(endpoint='/api/test')
        tracer.add_span(trace_id, 'test_span', duration=0.05)
        
        trace = tracer.end_trace(trace_id)
        
        assert trace is not None
        assert trace.trace_id == trace_id
        assert trace.endpoint == '/api/test'
        assert trace.duration is not None
    
    def test_get_trace(self):
        """Test getting a trace by ID."""
        tracer = get_tracer()
        tracer.clear()
        
        trace_id = tracer.start_trace(endpoint='/api/test')
        tracer.add_span(trace_id, 'test_span', duration=0.05)
        tracer.end_trace(trace_id)
        
        trace = tracer.get_trace(trace_id)
        
        assert trace is not None
        assert trace['trace_id'] == trace_id
        assert trace['endpoint'] == '/api/test'
        assert len(trace['spans']) == 1
    
    def test_get_slow_traces(self):
        """Test getting slow traces."""
        tracer = get_tracer()
        tracer.clear()
        tracer.set_slow_threshold(10)  # 10ms threshold
        
        # Create a slow trace
        trace_id = tracer.start_trace(endpoint='/api/slow')
        time.sleep(0.02)  # 20ms - should be slow
        tracer.end_trace(trace_id)
        
        slow_traces = tracer.get_slow_traces(threshold_ms=10)
        
        assert len(slow_traces) >= 1
        assert slow_traces[0]['endpoint'] == '/api/slow'
    
    def test_trace_context_manager(self):
        """Test trace context manager."""
        tracer = get_tracer()
        tracer.clear()
        
        with trace_request('/api/context') as ctx:
            assert ctx.trace_id is not None
            time.sleep(0.01)
        
        # Trace should be completed
        trace = tracer.get_trace(ctx.trace_id)
        assert trace is not None
        assert trace['endpoint'] == '/api/context'
    
    def test_get_tracer_stats(self):
        """Test getting tracer statistics."""
        tracer = get_tracer()
        tracer.clear()
        
        # Create some traces
        for i in range(5):
            trace_id = tracer.start_trace(endpoint=f'/api/test/{i}')
            tracer.add_span(trace_id, 'span', duration=0.01)
            tracer.end_trace(trace_id)
        
        stats = tracer.get_stats()
        
        assert 'completed_traces' in stats
        assert stats['completed_traces'] == 5


class TestErrorTracking:
    """Tests for error tracking."""
    
    def test_singleton_instance(self):
        """Test that ErrorTracker is a singleton."""
        tracker1 = get_error_tracker()
        tracker2 = get_error_tracker()
        assert tracker1 is tracker2
    
    def test_track_error(self):
        """Test tracking an error."""
        tracker = get_error_tracker()
        tracker.clear()  # Start fresh
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            error_id = tracker.track_error(e, context={'test': 'data'})
        
        assert error_id is not None
        assert len(error_id) > 0
    
    def test_get_errors(self):
        """Test getting errors."""
        tracker = get_error_tracker()
        tracker.clear()
        
        # Track some errors
        for i in range(3):
            try:
                raise ValueError(f"Error {i}")
            except ValueError as e:
                tracker.track_error(e)
        
        errors = tracker.get_errors(hours=24)
        
        assert len(errors) == 3
    
    def test_get_error_rate(self):
        """Test getting error rate."""
        tracker = get_error_tracker()
        tracker.clear()
        
        # Track some errors
        try:
            raise ValueError("Test error")
        except ValueError as e:
            tracker.track_error(e)
        
        rate = tracker.get_error_rate(hours=24)
        
        # Should have some rate (errors / hours)
        assert rate >= 0
    
    def test_get_top_errors(self):
        """Test getting top errors."""
        tracker = get_error_tracker()
        tracker.clear()
        
        # Track same error multiple times
        for i in range(5):
            try:
                raise ValueError("Repeated error")
            except ValueError as e:
                tracker.track_error(e)
        
        top_errors = tracker.get_top_errors(limit=10)
        
        assert len(top_errors) >= 1
        assert top_errors[0]['count'] == 5
    
    def test_get_errors_by_type(self):
        """Test getting errors grouped by type."""
        tracker = get_error_tracker()
        tracker.clear()
        
        # Track different error types
        for i in range(3):
            try:
                raise ValueError(f"Value error {i}")
            except ValueError as e:
                tracker.track_error(e)
        
        for i in range(2):
            try:
                raise KeyError(f"Key error {i}")
            except KeyError as e:
                tracker.track_error(e)
        
        errors_by_type = tracker.get_errors_by_type(hours=24)
        
        assert 'ValueError' in errors_by_type
        assert 'KeyError' in errors_by_type
        assert errors_by_type['ValueError'] == 3
        assert errors_by_type['KeyError'] == 2
    
    def test_error_tracker_context(self):
        """Test error tracker context manager."""
        from src.monitoring.error_tracking import track_errors
        
        tracker = get_error_tracker()
        tracker.clear()
        
        try:
            with track_errors(endpoint='/api/test'):
                raise ValueError("Context error")
        except ValueError:
            pass  # Expected
        
        errors = tracker.get_errors(hours=1)
        assert len(errors) == 1
        assert errors[0]['endpoint'] == '/api/test'
    
    def test_get_stats(self):
        """Test getting error tracker statistics."""
        tracker = get_error_tracker()
        tracker.clear()
        
        # Track some errors
        try:
            raise ValueError("Test")
        except ValueError as e:
            tracker.track_error(e)
        
        stats = tracker.get_stats()
        
        assert 'total_errors' in stats
        assert 'errors_24h' in stats
        assert 'error_rate_per_hour' in stats


class TestSlowQueryLogging:
    """Tests for slow query logging."""
    
    def test_singleton_instance(self):
        """Test that QueryMonitor is a singleton."""
        monitor1 = get_query_monitor()
        monitor2 = get_query_monitor()
        assert monitor1 is monitor2
    
    def test_log_slow_query(self):
        """Test logging a slow query."""
        monitor = get_query_monitor()
        monitor.clear()  # Start fresh
        
        # Log a slow query (2 seconds > 1 second threshold)
        record = monitor.log_slow_query(
            query="SELECT * FROM products WHERE id = 1",
            duration=2.0,
            params={'id': 1}
        )
        
        assert record is not None
        assert record.duration == 2.0
    
    def test_skip_fast_query(self):
        """Test that fast queries are not logged."""
        monitor = get_query_monitor()
        monitor.clear()
        
        # Log a fast query (0.1 seconds < 1 second threshold)
        record = monitor.log_slow_query(
            query="SELECT * FROM products",
            duration=0.1
        )
        
        assert record is None
    
    def test_get_slow_queries(self):
        """Test getting slow queries."""
        monitor = get_query_monitor()
        monitor.clear()
        
        # Log some slow queries
        for i in range(5):
            monitor.log_slow_query(
                query=f"SELECT * FROM products WHERE id = {i}",
                duration=1.5 + (i * 0.1)
            )
        
        queries = monitor.get_slow_queries(limit=10)
        
        assert len(queries) == 5
        # Should be sorted by duration (slowest first)
        assert queries[0]['duration'] >= queries[-1]['duration']
    
    def test_query_normalization(self):
        """Test query normalization for grouping."""
        from src.db.monitor import _normalize_query
        
        query1 = "SELECT * FROM products WHERE id = 1"
        query2 = "SELECT * FROM products WHERE id = 2"
        query3 = "SELECT * FROM products WHERE id = 100"
        
        normalized1 = _normalize_query(query1)
        normalized2 = _normalize_query(query2)
        normalized3 = _normalize_query(query3)
        
        # All should normalize to the same pattern
        assert normalized1 == normalized2
        assert normalized2 == normalized3
    
    def test_get_query_stats(self):
        """Test getting query statistics."""
        monitor = get_query_monitor()
        monitor.clear()
        
        # Log same query pattern multiple times
        for i in range(3):
            monitor.log_slow_query(
                query=f"SELECT * FROM products WHERE id = {i}",
                duration=1.5
            )
        
        stats = monitor.get_query_stats()
        
        # Should have one normalized query pattern
        assert len(stats) >= 1
    
    def test_get_top_slow_queries(self):
        """Test getting top slow queries."""
        monitor = get_query_monitor()
        monitor.clear()
        
        # Log queries with different durations
        monitor.log_slow_query("SELECT slow", duration=5.0)
        monitor.log_slow_query("SELECT medium", duration=3.0)
        monitor.log_slow_query("SELECT fast", duration=1.5)
        
        top = monitor.get_top_slow_queries(limit=10)
        
        assert len(top) >= 1
        # Should be sorted by total duration
        assert top[0]['query'] == 'SELECT slow'
    
    def test_set_threshold(self):
        """Test setting slow query threshold."""
        monitor = get_query_monitor()
        
        monitor.set_threshold(0.5)  # 500ms
        
        stats = monitor.get_stats()
        assert stats['threshold_ms'] == 500
    
    def test_query_timer_context(self):
        """Test query timer context manager."""
        from src.db.monitor import time_query
        
        monitor = get_query_monitor()
        monitor.clear()
        
        with time_query("SELECT * FROM test", endpoint='/api/test'):
            time.sleep(0.01)
        
        # Query was fast, so no record
        queries = monitor.get_slow_queries()
        assert len(queries) == 0
    
    def test_get_stats(self):
        """Test getting monitor statistics."""
        monitor = get_query_monitor()
        monitor.clear()
        
        stats = monitor.get_stats()
        
        assert 'slow_query_count' in stats
        assert 'threshold_ms' in stats
        assert 'enabled' in stats


class TestMonitoringIntegration:
    """Integration tests for monitoring module."""
    
    def test_full_request_lifecycle(self):
        """Test full request lifecycle with monitoring."""
        # Clear all monitors
        get_prometheus_metrics().reset()
        get_tracer().clear()
        get_error_tracker().clear()
        get_query_monitor().clear()
        
        # Simulate a request
        tracer = get_tracer()
        metrics = get_prometheus_metrics()
        
        trace_id = tracer.start_trace(endpoint='/api/products')
        
        # Simulate DB query
        query_monitor = get_query_monitor()
        query_monitor.log_slow_query(
            "SELECT * FROM products",
            duration=1.5
        )
        
        # Simulate some work
        time.sleep(0.01)
        
        # Add span
        tracer.add_span(trace_id, 'db_query', duration=1.5)
        
        # End trace
        tracer.end_trace(trace_id)
        
        # Record metrics
        metrics.record_http_request('GET', '/api/products', 200, 1.51)
        metrics.record_product_scanned(10)
        
        # Verify everything was recorded
        trace = tracer.get_trace(trace_id)
        assert trace is not None
        assert len(trace['spans']) == 1
        
        stats = metrics.get_stats()
        assert 'GET:/api/products:200' in stats
        
        slow_queries = get_slow_queries()
        assert len(slow_queries) >= 1
    
    def test_error_during_request(self):
        """Test error tracking during request."""
        get_error_tracker().clear()
        get_tracer().clear()
        
        with trace_request('/api/error') as ctx:
            try:
                raise RuntimeError("Request failed")
            except RuntimeError as e:
                track_error(e, endpoint='/api/error')
        
        errors = get_error_tracker().get_errors(hours=1)
        assert len(errors) == 1
        assert errors[0]['error_type'] == 'RuntimeError'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
