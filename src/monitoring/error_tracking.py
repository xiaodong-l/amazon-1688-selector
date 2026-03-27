"""
Error Tracking for Amazon Selector

Provides error capture, statistics, and detailed error reporting.
"""

import time
import traceback
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ErrorRecord:
    """Represents a single error record."""
    error_id: str
    error_type: str
    error_message: str
    stack_trace: str
    timestamp: float
    endpoint: Optional[str] = None
    user_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    count: int = 1
    
    @property
    def timestamp_iso(self) -> str:
        """Get ISO format timestamp."""
        from datetime import datetime, timezone
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        return {
            'error_id': self.error_id,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'timestamp': self.timestamp,
            'timestamp_iso': self.timestamp_iso,
            'endpoint': self.endpoint,
            'user_id': self.user_id,
            'context': self.context,
            'count': self.count,
        }


class ErrorTracker:
    """
    Error tracker for capturing and analyzing errors.
    
    Provides error capture, aggregation, statistics, and reporting.
    """
    
    _instance: Optional['ErrorTracker'] = None
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
        
        # Error storage
        self._errors: List[ErrorRecord] = []
        self._error_groups: Dict[str, ErrorRecord] = {}  # Grouped by error signature
        self._total_errors = 0
        self._errors_by_type: Dict[str, int] = defaultdict(int)
        self._errors_by_endpoint: Dict[str, int] = defaultdict(int)
        
        # Configuration
        self._max_errors = 10000  # Maximum errors to keep in memory
        self._retention_hours = 24  # Default retention period
        self._lock = threading.RLock()
        self._initialized = True
    
    def _generate_error_id(self, error: Exception) -> str:
        """Generate a unique error ID."""
        return hashlib.md5(
            f"{type(error).__name__}:{str(error)}".encode()
        ).hexdigest()[:12]
    
    def _generate_error_signature(self, error: Exception) -> str:
        """Generate error signature for grouping similar errors."""
        # Group by error type and first line of message
        message_lines = str(error).split('\n')
        first_line = message_lines[0][:100] if message_lines else ""
        return f"{type(error).__name__}:{first_line}"
    
    def track_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                    endpoint: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Track an error.
        
        Args:
            error: The exception to track
            context: Optional context dictionary
            endpoint: Optional endpoint where error occurred
            user_id: Optional user ID
        
        Returns:
            The error ID
        """
        timestamp = time.time()
        error_id = self._generate_error_id(error)
        signature = self._generate_error_signature(error)
        
        # Get stack trace
        stack_trace = traceback.format_exc().strip()
        if not stack_trace:
            stack_trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        
        # Create error record
        error_record = ErrorRecord(
            error_id=error_id,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=stack_trace,
            timestamp=timestamp,
            endpoint=endpoint,
            user_id=user_id,
            context=context or {},
        )
        
        with self._lock:
            # Add to errors list
            self._errors.append(error_record)
            self._total_errors += 1
            
            # Update error groups
            if signature in self._error_groups:
                self._error_groups[signature].count += 1
            else:
                self._error_groups[signature] = error_record
            
            # Update statistics
            self._errors_by_type[type(error).__name__] += 1
            if endpoint:
                self._errors_by_endpoint[endpoint] += 1
            
            # Cleanup old errors
            self._cleanup_old_errors()
            
            # Limit total errors
            if len(self._errors) > self._max_errors:
                self._errors = self._errors[-self._max_errors:]
        
        logger.error(f"Error tracked: {type(error).__name__}: {error}")
        return error_id
    
    def _cleanup_old_errors(self) -> None:
        """Remove errors older than retention period."""
        cutoff = time.time() - (self._retention_hours * 3600)
        self._errors = [e for e in self._errors if e.timestamp >= cutoff]
        
        # Also cleanup error groups
        self._error_groups = {
            sig: err for sig, err in self._error_groups.items()
            if err.timestamp >= cutoff
        }
    
    def get_errors(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get errors from the last N hours.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            List of error dictionaries
        """
        cutoff = time.time() - (hours * 3600)
        
        with self._lock:
            errors = [e for e in self._errors if e.timestamp >= cutoff]
            # Sort by timestamp (newest first)
            errors.sort(key=lambda x: x.timestamp, reverse=True)
            return [e.to_dict() for e in errors]
    
    def get_error_rate(self, hours: int = 24) -> float:
        """
        Get error rate (errors per hour).
        
        Args:
            hours: Number of hours to calculate rate
        
        Returns:
            Errors per hour
        """
        errors = self.get_errors(hours)
        if hours <= 0:
            return 0.0
        return len(errors) / hours
    
    def get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top errors by occurrence count.
        
        Args:
            limit: Maximum number of errors to return
        
        Returns:
            List of error dictionaries sorted by count
        """
        with self._lock:
            # Sort error groups by count
            sorted_errors = sorted(
                self._error_groups.values(),
                key=lambda x: x.count,
                reverse=True
            )[:limit]
            return [e.to_dict() for e in sorted_errors]
    
    def get_errors_by_type(self, hours: int = 24) -> Dict[str, int]:
        """
        Get error counts grouped by error type.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            Dictionary of error type -> count
        """
        cutoff = time.time() - (hours * 3600)
        counts: Dict[str, int] = defaultdict(int)
        
        with self._lock:
            for error in self._errors:
                if error.timestamp >= cutoff:
                    counts[error.error_type] += 1
        
        return dict(counts)
    
    def get_errors_by_endpoint(self, hours: int = 24) -> Dict[str, int]:
        """
        Get error counts grouped by endpoint.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            Dictionary of endpoint -> count
        """
        cutoff = time.time() - (hours * 3600)
        counts: Dict[str, int] = defaultdict(int)
        
        with self._lock:
            for error in self._errors:
                if error.timestamp >= cutoff and error.endpoint:
                    counts[error.endpoint] += 1
        
        return dict(counts)
    
    def get_error_count(self, hours: int = 24) -> int:
        """
        Get total error count for the last N hours.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            Total error count
        """
        return len(self.get_errors(hours))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get error tracker statistics."""
        with self._lock:
            errors_24h = self.get_errors(24)
            errors_1h = self.get_errors(1)
            
            return {
                'total_errors': self._total_errors,
                'errors_24h': len(errors_24h),
                'errors_1h': len(errors_1h),
                'error_rate_per_hour': len(errors_24h) / 24 if errors_24h else 0,
                'unique_error_types': len(self._errors_by_type),
                'unique_error_groups': len(self._error_groups),
                'top_error_types': dict(sorted(
                    self._errors_by_type.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]),
            }
    
    def clear(self) -> None:
        """Clear all errors."""
        with self._lock:
            self._errors.clear()
            self._error_groups.clear()
            self._errors_by_type.clear()
            self._errors_by_endpoint.clear()
            self._total_errors = 0
        logger.info("Error tracker cleared")
    
    def set_retention(self, hours: int) -> None:
        """Set error retention period."""
        with self._lock:
            self._retention_hours = hours
            self._cleanup_old_errors()
        logger.info(f"Error retention set to {hours} hours")


# Module-level singleton
_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get or create error tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = ErrorTracker()
    return _tracker


# Convenience functions
def track_error(error: Exception, context: Optional[Dict[str, Any]] = None,
                endpoint: Optional[str] = None, user_id: Optional[str] = None) -> str:
    """Track an error."""
    return get_error_tracker().track_error(error, context, endpoint, user_id)


def get_errors(hours: int = 24) -> List[Dict[str, Any]]:
    """Get errors from last N hours."""
    return get_error_tracker().get_errors(hours)


def get_error_rate() -> float:
    """Get error rate (errors per hour)."""
    return get_error_tracker().get_error_rate()


def get_top_errors(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top errors by occurrence."""
    return get_error_tracker().get_top_errors(limit)


# Context manager for automatic error tracking
class ErrorTrackerContext:
    """Context manager for automatic error tracking."""
    
    def __init__(self, endpoint: Optional[str] = None, user_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None, swallow: bool = False):
        self.endpoint = endpoint
        self.user_id = user_id
        self.context = context or {}
        self.swallow = swallow  # Whether to suppress the exception
        self._tracker = get_error_tracker()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._tracker.track_error(
                exc_val,
                context=self.context,
                endpoint=self.endpoint,
                user_id=self.user_id,
            )
            return self.swallow  # Only suppress if swallow=True
        return False


def track_errors(endpoint: Optional[str] = None, user_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None) -> ErrorTrackerContext:
    """Create error tracking context manager."""
    return ErrorTrackerContext(endpoint, user_id, context)
