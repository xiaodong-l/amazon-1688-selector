"""
Monitoring API Routes for Amazon Selector

Provides endpoints for Prometheus metrics, request tracing, slow queries, and error tracking.
"""

from flask import Blueprint, jsonify, Response, request
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Create blueprint
monitor_bp = Blueprint('monitor', __name__, url_prefix='/api/v2/monitor')


@monitor_bp.route('/health', methods=['GET'])
def health_check() -> Response:
    """
    Health check endpoint.
    
    Returns:
        JSON response with service health status
    """
    return jsonify({
        'status': 'healthy',
        'service': 'amazon-1688-selector',
        'version': '2.3.0',
    })


@monitor_bp.route('/metrics/prometheus', methods=['GET'])
def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    
    Returns:
        Text response with Prometheus metrics
    """
    try:
        from src.monitoring import expose_metrics
        metrics_text = expose_metrics()
        return Response(
            metrics_text,
            mimetype='text/plain; charset=utf-8'
        )
    except Exception as e:
        logger.error(f"Error exposing metrics: {e}")
        return jsonify({
            'error': 'Failed to expose metrics',
            'message': str(e),
        }), 500


@monitor_bp.route('/metrics/summary', methods=['GET'])
def metrics_summary() -> Response:
    """
    Get metrics summary in JSON format.
    
    Returns:
        JSON response with metrics summary
    """
    try:
        from src.monitoring.prometheus import get_prometheus_metrics
        from src.monitoring.request_tracing import get_tracer
        from src.monitoring.error_tracking import get_error_tracker
        from src.db.monitor import get_query_monitor
        
        prometheus = get_prometheus_metrics()
        tracer = get_tracer()
        error_tracker = get_error_tracker()
        query_monitor = get_query_monitor()
        
        return jsonify({
            'http_metrics': prometheus.get_stats(),
            'tracing': tracer.get_stats(),
            'errors': error_tracker.get_stats(),
            'queries': query_monitor.get_stats(),
        })
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return jsonify({
            'error': 'Failed to get metrics summary',
            'message': str(e),
        }), 500


@monitor_bp.route('/traces', methods=['GET'])
def get_traces() -> Response:
    """
    Get request traces.
    
    Query parameters:
        - slow: Filter to only slow traces (default: false)
        - threshold: Slow threshold in ms (default: 1000)
        - limit: Maximum traces to return (default: 100)
        - trace_id: Get specific trace by ID
    
    Returns:
        JSON response with traces
    """
    try:
        from src.monitoring import get_trace, get_slow_traces, get_tracer
        
        trace_id = request.args.get('trace_id')
        slow_only = request.args.get('slow', 'false').lower() == 'true'
        threshold_ms = int(request.args.get('threshold', 1000))
        limit = int(request.args.get('limit', 100))
        
        # Get specific trace
        if trace_id:
            trace = get_trace(trace_id)
            if trace:
                return jsonify(trace)
            else:
                return jsonify({
                    'error': 'Trace not found',
                    'trace_id': trace_id,
                }), 404
        
        # Get slow traces
        if slow_only:
            traces = get_slow_traces(threshold_ms)
            return jsonify({
                'traces': traces[:limit],
                'count': len(traces),
                'threshold_ms': threshold_ms,
            })
        
        # Get all traces from tracer stats
        tracer = get_tracer()
        stats = tracer.get_stats()
        return jsonify({
            'stats': stats,
            'message': 'Use ?slow=true to get slow traces',
        })
    
    except Exception as e:
        logger.error(f"Error getting traces: {e}")
        return jsonify({
            'error': 'Failed to get traces',
            'message': str(e),
        }), 500


@monitor_bp.route('/slow-queries', methods=['GET'])
def get_slow_queries() -> Response:
    """
    Get slow database queries.
    
    Query parameters:
        - limit: Maximum queries to return (default: 100)
        - hours: Filter to last N hours (optional)
        - stats: Include query statistics (default: false)
    
    Returns:
        JSON response with slow queries
    """
    try:
        from src.db.monitor import get_slow_queries, get_query_monitor
        
        limit = int(request.args.get('limit', 100))
        hours = request.args.get('hours')
        include_stats = request.args.get('stats', 'false').lower() == 'true'
        
        # Get slow queries
        if hours:
            queries = get_slow_queries(limit, hours=int(hours))
        else:
            queries = get_slow_queries(limit)
        
        response = {
            'queries': queries,
            'count': len(queries),
        }
        
        # Include statistics if requested
        if include_stats:
            monitor = get_query_monitor()
            response['stats'] = monitor.get_query_stats()
            response['top_slow'] = monitor.get_top_slow_queries(10)
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error getting slow queries: {e}")
        return jsonify({
            'error': 'Failed to get slow queries',
            'message': str(e),
        }), 500


@monitor_bp.route('/errors', methods=['GET'])
def get_errors() -> Response:
    """
    Get error tracking data.
    
    Query parameters:
        - hours: Filter to last N hours (default: 24)
        - limit: Maximum errors to return (default: 100)
        - top: Get top errors by occurrence (default: false)
        - by_type: Group errors by type (default: false)
        - by_endpoint: Group errors by endpoint (default: false)
    
    Returns:
        JSON response with error data
    """
    try:
        from src.monitoring import get_errors, get_top_errors, get_error_rate, get_error_tracker
        
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 100))
        top_only = request.args.get('top', 'false').lower() == 'true'
        by_type = request.args.get('by_type', 'false').lower() == 'true'
        by_endpoint = request.args.get('by_endpoint', 'false').lower() == 'true'
        
        error_tracker = get_error_tracker()
        
        # Get top errors
        if top_only:
            errors = get_top_errors(limit)
            return jsonify({
                'errors': errors,
                'count': len(errors),
                'type': 'top_errors',
            })
        
        # Get errors by type
        if by_type:
            errors_by_type = error_tracker.get_errors_by_type(hours)
            return jsonify({
                'errors_by_type': errors_by_type,
                'hours': hours,
            })
        
        # Get errors by endpoint
        if by_endpoint:
            errors_by_endpoint = error_tracker.get_errors_by_endpoint(hours)
            return jsonify({
                'errors_by_endpoint': errors_by_endpoint,
                'hours': hours,
            })
        
        # Get all errors
        errors = get_errors(hours)
        return jsonify({
            'errors': errors[:limit],
            'count': len(errors),
            'error_rate_per_hour': get_error_rate(),
            'hours': hours,
        })
    
    except Exception as e:
        logger.error(f"Error getting errors: {e}")
        return jsonify({
            'error': 'Failed to get errors',
            'message': str(e),
        }), 500


@monitor_bp.route('/stats', methods=['GET'])
def get_monitoring_stats() -> Response:
    """
    Get comprehensive monitoring statistics.
    
    Returns:
        JSON response with all monitoring stats
    """
    try:
        from src.monitoring.prometheus import get_prometheus_metrics
        from src.monitoring.request_tracing import get_tracer
        from src.monitoring.error_tracking import get_error_tracker
        from src.db.monitor import get_query_monitor
        
        prometheus = get_prometheus_metrics()
        tracer = get_tracer()
        error_tracker = get_error_tracker()
        query_monitor = get_query_monitor()
        
        return jsonify({
            'prometheus': {
                'http_metrics': prometheus.get_stats(),
            },
            'tracing': tracer.get_stats(),
            'errors': error_tracker.get_stats(),
            'queries': query_monitor.get_stats(),
        })
    except Exception as e:
        logger.error(f"Error getting monitoring stats: {e}")
        return jsonify({
            'error': 'Failed to get monitoring stats',
            'message': str(e),
        }), 500


def init_monitor_routes(app) -> None:
    """
    Initialize monitoring routes with Flask app.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(monitor_bp)
    logger.info("Monitoring routes initialized")
