"""
Request Tracing for Amazon Selector

Provides request链路追踪, span recording, and slow request detection.
"""

import time
import uuid
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """Represents a single span in a trace."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self) -> None:
        """Finish the span and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            'name': self.name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'duration_ms': (self.duration * 1000) if self.duration else None,
            'tags': self.tags,
        }


@dataclass
class TraceContext:
    """Represents a complete trace context."""
    trace_id: str
    endpoint: str
    start_time: float
    end_time: Optional[float] = None
    spans: List[TraceSpan] = field(default_factory=list)
    tags: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate total trace duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Get duration in milliseconds."""
        if self.duration:
            return self.duration * 1000
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary."""
        return {
            'trace_id': self.trace_id,
            'endpoint': self.endpoint,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'duration_ms': self.duration_ms,
            'spans': [span.to_dict() for span in self.spans],
            'tags': self.tags,
            'error': self.error,
        }


class RequestTracer:
    """
    Request tracer for distributed tracing.
    
    Tracks request lifecycle, records spans, and detects slow requests.
    """
    
    _instance: Optional['RequestTracer'] = None
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
        
        # Store active traces
        self._traces: OrderedDict[str, TraceContext] = OrderedDict()
        self._completed_traces: List[TraceContext] = []
        self._max_traces = 1000  # Maximum traces to keep in memory
        self._slow_threshold_ms = 1000  # Default slow threshold
        self._lock = threading.RLock()
        self._initialized = True
    
    def start_trace(self, request_id: Optional[str] = None, endpoint: str = "") -> str:
        """
        Start a new trace.
        
        Args:
            request_id: Optional request ID (generated if not provided)
            endpoint: The endpoint being called
        
        Returns:
            The trace ID
        """
        trace_id = request_id or str(uuid.uuid4())
        
        with self._lock:
            trace = TraceContext(
                trace_id=trace_id,
                endpoint=endpoint,
                start_time=time.time(),
            )
            self._traces[trace_id] = trace
            
            # Cleanup old traces if needed
            if len(self._traces) > self._max_traces:
                # Remove oldest trace
                self._traces.popitem(last=False)
        
        logger.debug(f"Started trace {trace_id} for {endpoint}")
        return trace_id
    
    def add_span(self, trace_id: str, span_name: str, duration: Optional[float] = None,
                 tags: Optional[Dict[str, Any]] = None) -> TraceSpan:
        """
        Add a span to an existing trace.
        
        Args:
            trace_id: The trace ID
            span_name: Name of the span
            duration: Optional duration (if not provided, creates a new span)
            tags: Optional tags for the span
        
        Returns:
            The created span
        """
        span = TraceSpan(
            name=span_name,
            start_time=time.time(),
            duration=duration,
            tags=tags or {},
        )
        
        if duration is not None:
            span.finish()
        
        with self._lock:
            if trace_id in self._traces:
                self._traces[trace_id].spans.append(span)
        
        return span
    
    def end_trace(self, trace_id: str, error: Optional[str] = None) -> Optional[TraceContext]:
        """
        End a trace.
        
        Args:
            trace_id: The trace ID
            error: Optional error message
        
        Returns:
            The completed trace context, or None if not found
        """
        with self._lock:
            if trace_id not in self._traces:
                logger.warning(f"Trace {trace_id} not found")
                return None
            
            trace = self._traces[trace_id]
            trace.end_time = time.time()
            trace.error = error
            
            # Move to completed traces
            del self._traces[trace_id]
            self._completed_traces.append(trace)
            
            # Limit completed traces
            if len(self._completed_traces) > self._max_traces:
                self._completed_traces = self._completed_traces[-self._max_traces:]
        
        # Check for slow trace
        if trace.duration_ms and trace.duration_ms > self._slow_threshold_ms:
            logger.warning(
                f"Slow request detected: {trace.endpoint} took {trace.duration_ms:.2f}ms"
            )
        
        logger.debug(f"Ended trace {trace_id} (duration: {trace.duration_ms:.2f}ms)")
        return trace
    
    def get_trace(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a trace by ID.
        
        Args:
            request_id: The trace ID
        
        Returns:
            Trace dictionary or None if not found
        """
        with self._lock:
            # Check active traces
            if request_id in self._traces:
                return self._traces[request_id].to_dict()
            
            # Check completed traces
            for trace in self._completed_traces:
                if trace.trace_id == request_id:
                    return trace.to_dict()
        
        return None
    
    def get_slow_traces(self, threshold_ms: int = 1000) -> List[Dict[str, Any]]:
        """
        Get all slow traces above threshold.
        
        Args:
            threshold_ms: Duration threshold in milliseconds
        
        Returns:
            List of slow trace dictionaries
        """
        slow_traces = []
        
        with self._lock:
            # Check completed traces
            for trace in self._completed_traces:
                if trace.duration_ms and trace.duration_ms > threshold_ms:
                    slow_traces.append(trace.to_dict())
            
            # Check active traces that might be slow
            current_time = time.time()
            for trace in self._traces.values():
                current_duration = (current_time - trace.start_time) * 1000
                if current_duration > threshold_ms:
                    slow_traces.append(trace.to_dict())
        
        # Sort by duration (slowest first)
        slow_traces.sort(key=lambda x: x.get('duration_ms', 0), reverse=True)
        return slow_traces
    
    def set_slow_threshold(self, threshold_ms: int) -> None:
        """Set the slow request threshold."""
        with self._lock:
            self._slow_threshold_ms = threshold_ms
        logger.info(f"Slow threshold set to {threshold_ms}ms")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracer statistics."""
        with self._lock:
            completed_count = len(self._completed_traces)
            active_count = len(self._traces)
            
            # Calculate average duration
            durations = [t.duration_ms for t in self._completed_traces if t.duration_ms]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Count slow traces
            slow_count = sum(1 for t in self._completed_traces 
                           if t.duration_ms and t.duration_ms > self._slow_threshold_ms)
            
            return {
                'active_traces': active_count,
                'completed_traces': completed_count,
                'avg_duration_ms': avg_duration,
                'slow_traces': slow_count,
                'slow_threshold_ms': self._slow_threshold_ms,
            }
    
    def clear(self) -> None:
        """Clear all traces."""
        with self._lock:
            self._traces.clear()
            self._completed_traces.clear()
        logger.info("Request tracer cleared")


# Module-level singleton
_tracer: Optional[RequestTracer] = None


def get_tracer() -> RequestTracer:
    """Get or create tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = RequestTracer()
    return _tracer


# Convenience functions
def start_trace(request_id: Optional[str] = None, endpoint: str = "") -> str:
    """Start a new trace."""
    return get_tracer().start_trace(request_id, endpoint)


def add_span(trace_id: str, span_name: str, duration: Optional[float] = None,
             tags: Optional[Dict[str, Any]] = None) -> TraceSpan:
    """Add a span to a trace."""
    return get_tracer().add_span(trace_id, span_name, duration, tags)


def end_trace(trace_id: str, error: Optional[str] = None) -> Optional[TraceContext]:
    """End a trace."""
    return get_tracer().end_trace(trace_id, error)


def get_trace(request_id: str) -> Optional[Dict[str, Any]]:
    """Get a trace by ID."""
    return get_tracer().get_trace(request_id)


def get_slow_traces(threshold_ms: int = 1000) -> List[Dict[str, Any]]:
    """Get slow traces."""
    return get_tracer().get_slow_traces(threshold_ms)


# Context manager for automatic tracing
class TraceContextManager:
    """Context manager for automatic request tracing."""
    
    def __init__(self, endpoint: str, request_id: Optional[str] = None):
        self.endpoint = endpoint
        self.request_id = request_id
        self.trace_id = None
        self.error = None
        self._tracer = get_tracer()
    
    def __enter__(self):
        self.trace_id = self._tracer.start_trace(self.request_id, self.endpoint)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = f"{exc_type.__name__}: {exc_val}"
        self._tracer.end_trace(self.trace_id, self.error)
        return False


def trace_request(endpoint: str, request_id: Optional[str] = None) -> TraceContextManager:
    """Create a trace context manager for a request."""
    return TraceContextManager(endpoint, request_id)
