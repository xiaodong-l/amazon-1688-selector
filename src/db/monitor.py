"""
Database Query Monitoring for Amazon Selector

Provides slow query logging, query analysis, and performance monitoring.
"""

import time
import threading
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import hashlib

logger = logging.getLogger(__name__)

# Slow query threshold in seconds
SLOW_QUERY_THRESHOLD = 1.0  # 1 second


@dataclass
class SlowQueryRecord:
    """Represents a slow query record."""
    query_id: str
    query: str
    query_normalized: str
    duration: float
    timestamp: float
    params: Dict[str, Any] = field(default_factory=dict)
    endpoint: Optional[str] = None
    stack_trace: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds."""
        return self.duration * 1000
    
    @property
    def timestamp_iso(self) -> str:
        """Get ISO format timestamp."""
        from datetime import datetime, timezone
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query_id': self.query_id,
            'query': self.query,
            'query_normalized': self.query_normalized,
            'duration': self.duration,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp,
            'timestamp_iso': self.timestamp_iso,
            'params': self.params,
            'endpoint': self.endpoint,
        }


def _normalize_query(query: str) -> str:
    """
    Normalize a query for grouping similar queries.
    
    Replaces literal values with placeholders.
    """
    # Replace string literals
    normalized = re.sub(r"'[^']*'", "'?'", query)
    normalized = re.sub(r'"[^"]*"', "'?'", normalized)
    
    # Replace numeric literals
    normalized = re.sub(r'\b\d+\b', '?', normalized)
    
    # Replace IN clauses with multiple values
    normalized = re.sub(r'IN\s*\([^)]+\)', 'IN (?)', normalized, flags=re.IGNORECASE)
    
    # Normalize whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized


def _generate_query_id(query: str, timestamp: float) -> str:
    """Generate a unique query ID."""
    return hashlib.md5(
        f"{query}:{timestamp}".encode()
    ).hexdigest()[:12]


class QueryMonitor:
    """
    Database query monitor for tracking slow queries.
    
    Provides slow query logging, analysis, and statistics.
    """
    
    _instance: Optional['QueryMonitor'] = None
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
        
        # Query storage
        self._slow_queries: List[SlowQueryRecord] = []
        self._query_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0.0,
            'max_duration': 0.0,
            'min_duration': float('inf'),
        })
        
        # Configuration
        self._threshold = SLOW_QUERY_THRESHOLD
        self._max_queries = 1000  # Maximum slow queries to keep
        self._enabled = True
        self._lock = threading.RLock()
        self._initialized = True
    
    def log_slow_query(self, query: str, duration: float, params: Optional[Dict[str, Any]] = None,
                       endpoint: Optional[str] = None) -> Optional[SlowQueryRecord]:
        """
        Log a slow query.
        
        Args:
            query: The SQL query
            duration: Query duration in seconds
            params: Optional query parameters
            endpoint: Optional endpoint where query was executed
        
        Returns:
            The created record if query was slow, None otherwise
        """
        if not self._enabled:
            return None
        
        if duration < self._threshold:
            return None
        
        timestamp = time.time()
        query_id = _generate_query_id(query, timestamp)
        query_normalized = _normalize_query(query)
        
        # Get stack trace for debugging
        import traceback
        stack_trace = ''.join(traceback.format_stack()[:-2])
        
        record = SlowQueryRecord(
            query_id=query_id,
            query=query,
            query_normalized=query_normalized,
            duration=duration,
            timestamp=timestamp,
            params=params or {},
            endpoint=endpoint,
            stack_trace=stack_trace,
        )
        
        with self._lock:
            # Add to slow queries list
            self._slow_queries.append(record)
            
            # Update statistics
            stats = self._query_stats[query_normalized]
            stats['count'] += 1
            stats['total_duration'] += duration
            stats['max_duration'] = max(stats['max_duration'], duration)
            stats['min_duration'] = min(stats['min_duration'], duration)
            
            # Limit stored queries
            if len(self._slow_queries) > self._max_queries:
                self._slow_queries = self._slow_queries[-self._max_queries:]
        
        logger.warning(
            f"Slow query detected ({duration*1000:.2f}ms): {query[:100]}..."
        )
        
        return record
    
    def record_query(self, query: str, duration: float, params: Optional[Dict[str, Any]] = None,
                     endpoint: Optional[str] = None) -> None:
        """
        Record any query (logs if slow).
        
        This is a convenience method that always checks if query is slow.
        
        Args:
            query: The SQL query
            duration: Query duration in seconds
            params: Optional query parameters
            endpoint: Optional endpoint where query was executed
        """
        self.log_slow_query(query, duration, params, endpoint)
    
    def get_slow_queries(self, limit: int = 100, hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get slow queries.
        
        Args:
            limit: Maximum number of queries to return
            hours: Optional time filter (last N hours)
        
        Returns:
            List of slow query dictionaries
        """
        with self._lock:
            queries = self._slow_queries.copy()
        
        # Filter by time if specified
        if hours is not None:
            cutoff = time.time() - (hours * 3600)
            queries = [q for q in queries if q.timestamp >= cutoff]
        
        # Sort by duration (slowest first)
        queries.sort(key=lambda x: x.duration, reverse=True)
        
        # Limit results
        queries = queries[:limit]
        
        return [q.to_dict() for q in queries]
    
    def get_query_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get query statistics grouped by normalized query.
        
        Returns:
            Dictionary of normalized query -> statistics
        """
        with self._lock:
            stats = {}
            for query, data in self._query_stats.items():
                avg_duration = (
                    data['total_duration'] / data['count']
                    if data['count'] > 0 else 0
                )
                stats[query] = {
                    'count': data['count'],
                    'total_duration_ms': data['total_duration'] * 1000,
                    'avg_duration_ms': avg_duration * 1000,
                    'max_duration_ms': data['max_duration'] * 1000,
                    'min_duration_ms': (
                        data['min_duration'] * 1000
                        if data['min_duration'] != float('inf') else 0
                    ),
                }
            return stats
    
    def get_top_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top slow queries by total time spent.
        
        Args:
            limit: Maximum number of queries to return
        
        Returns:
            List of query statistics sorted by total duration
        """
        stats = self.get_query_stats()
        
        # Sort by total duration
        sorted_queries = sorted(
            stats.items(),
            key=lambda x: x[1]['total_duration_ms'],
            reverse=True
        )[:limit]
        
        return [
            {'query': query, **data}
            for query, data in sorted_queries
        ]
    
    def get_slow_query_count(self, hours: Optional[int] = None) -> int:
        """
        Get count of slow queries.
        
        Args:
            hours: Optional time filter (last N hours)
        
        Returns:
            Count of slow queries
        """
        with self._lock:
            queries = self._slow_queries
        
        if hours is not None:
            cutoff = time.time() - (hours * 3600)
            queries = [q for q in queries if q.timestamp >= cutoff]
        
        return len(queries)
    
    def set_threshold(self, threshold_seconds: float) -> None:
        """
        Set the slow query threshold.
        
        Args:
            threshold_seconds: Threshold in seconds
        """
        with self._lock:
            self._threshold = threshold_seconds
        logger.info(f"Slow query threshold set to {threshold_seconds}s")
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable query monitoring."""
        with self._lock:
            self._enabled = enabled
        logger.info(f"Query monitoring {'enabled' if enabled else 'disabled'}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        with self._lock:
            return {
                'slow_query_count': len(self._slow_queries),
                'unique_query_patterns': len(self._query_stats),
                'threshold_ms': self._threshold * 1000,
                'enabled': self._enabled,
                'max_queries': self._max_queries,
            }
    
    def clear(self) -> None:
        """Clear all slow query records."""
        with self._lock:
            self._slow_queries.clear()
            self._query_stats.clear()
        logger.info("Query monitor cleared")


# Module-level singleton
_monitor: Optional[QueryMonitor] = None


def get_query_monitor() -> QueryMonitor:
    """Get or create query monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = QueryMonitor()
    return _monitor


# Convenience functions
def log_slow_query(query: str, duration: float, params: Optional[Dict[str, Any]] = None,
                   endpoint: Optional[str] = None) -> Optional[SlowQueryRecord]:
    """Log a slow query."""
    return get_query_monitor().log_slow_query(query, duration, params, endpoint)


def get_slow_queries(limit: int = 100) -> List[Dict[str, Any]]:
    """Get slow queries."""
    return get_query_monitor().get_slow_queries(limit)


# Context manager for timing queries
class QueryTimer:
    """Context manager for timing database queries."""
    
    def __init__(self, query: str, params: Optional[Dict[str, Any]] = None,
                 endpoint: Optional[str] = None):
        self.query = query
        self.params = params or {}
        self.endpoint = endpoint
        self.start_time = None
        self._monitor = get_query_monitor()
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self._monitor.record_query(self.query, duration, self.params, self.endpoint)
        return False


def time_query(query: str, params: Optional[Dict[str, Any]] = None,
               endpoint: Optional[str] = None) -> QueryTimer:
    """Get timer for query execution."""
    return QueryTimer(query, params, endpoint)
