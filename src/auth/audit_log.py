"""
Audit Logging Module
Security audit trail for authentication events in v2.3.0
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import threading
import json


class AuditEventType(Enum):
    """Types of audit events."""
    LOGIN_SUCCESS = "login.success"
    LOGIN_FAILURE = "login.failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token.refresh"
    TOKEN_REVOKED = "token.revoked"
    API_KEY_CREATED = "apikey.created"
    API_KEY_USED = "apikey.used"
    API_KEY_REVOKED = "apikey.revoked"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_REVOKED = "permission.revoked"
    ROLE_CHANGED = "role.changed"
    PASSWORD_CHANGED = "password.changed"
    ACCOUNT_LOCKED = "account.locked"
    ACCOUNT_UNLOCKED = "account.unlocked"


class AuditLogger:
    """
    Thread-safe audit logging system.
    
    In production, replace with database-backed storage with retention policies.
    """
    
    _instance: Optional['AuditLogger'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'AuditLogger':
        """Singleton pattern for audit logger."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._logs: List[Dict[str, Any]] = []
                    cls._instance._storage_lock = threading.RLock()
                    cls._instance._max_logs = 10000  # Memory limit
        return cls._instance
    
    def _create_log_entry(
        self,
        event_type: AuditEventType,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a standardized log entry."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
        }
    
    def log_login(self, user_id: int, success: bool, ip: str, 
                  user_agent: Optional[str] = None,
                  reason: Optional[str] = None) -> None:
        """
        Log a login attempt.
        
        Args:
            user_id: User ID attempting to log in
            success: Whether login was successful
            ip: IP address of the attempt
            user_agent: Optional user agent string
            reason: Optional failure reason
        """
        event_type = AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE
        
        details = {}
        if reason:
            details["reason"] = reason
        
        entry = self._create_log_entry(
            event_type=event_type,
            user_id=user_id,
            details=details,
            ip_address=ip,
            user_agent=user_agent,
        )
        
        with self._storage_lock:
            self._logs.append(entry)
            self._cleanup_if_needed()
    
    def log_api_key_usage(self, key_id: int, endpoint: str,
                          user_id: Optional[int] = None,
                          ip_address: Optional[str] = None,
                          response_code: Optional[int] = None) -> None:
        """
        Log API key usage.
        
        Args:
            key_id: API Key ID
            endpoint: API endpoint accessed
            user_id: Optional associated user ID
            ip_address: Optional IP address
            response_code: Optional HTTP response code
        """
        details = {
            "key_id": key_id,
            "endpoint": endpoint,
        }
        
        if response_code:
            details["response_code"] = response_code
        
        entry = self._create_log_entry(
            event_type=AuditEventType.API_KEY_USED,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
        )
        
        with self._storage_lock:
            self._logs.append(entry)
            self._cleanup_if_needed()
    
    def log_permission_change(self, user_id: int, action: str,
                              target_user_id: Optional[int] = None,
                              permission: Optional[str] = None,
                              actor_id: Optional[int] = None,
                              ip_address: Optional[str] = None) -> None:
        """
        Log permission changes.
        
        Args:
            user_id: User whose permissions changed
            action: Action type (grant/revoke/change)
            target_user_id: Optional target user (if different)
            permission: Permission that was changed
            actor_id: User who made the change
            ip_address: IP address of the change
        """
        if action.lower() in ["grant", "assign"]:
            event_type = AuditEventType.PERMISSION_GRANTED
        elif action.lower() in ["revoke", "remove"]:
            event_type = AuditEventType.PERMISSION_REVOKED
        else:
            event_type = AuditEventType.PERMISSION_GRANTED  # Default
        
        details = {
            "action": action,
            "permission": permission,
        }
        
        if target_user_id and target_user_id != user_id:
            details["target_user_id"] = target_user_id
        
        if actor_id:
            details["actor_id"] = actor_id
        
        entry = self._create_log_entry(
            event_type=event_type,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
        )
        
        with self._storage_lock:
            self._logs.append(entry)
            self._cleanup_if_needed()
    
    def log_api_key_created(self, key_id: int, user_id: int,
                            key_name: Optional[str] = None,
                            ip_address: Optional[str] = None) -> None:
        """Log API key creation."""
        details = {"key_id": key_id}
        if key_name:
            details["key_name"] = key_name
        
        entry = self._create_log_entry(
            event_type=AuditEventType.API_KEY_CREATED,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
        )
        
        with self._storage_lock:
            self._logs.append(entry)
            self._cleanup_if_needed()
    
    def log_api_key_revoked(self, key_id: int, user_id: int,
                            reason: Optional[str] = None,
                            ip_address: Optional[str] = None) -> None:
        """Log API key revocation."""
        details = {"key_id": key_id}
        if reason:
            details["reason"] = reason
        
        entry = self._create_log_entry(
            event_type=AuditEventType.API_KEY_REVOKED,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
        )
        
        with self._storage_lock:
            self._logs.append(entry)
            self._cleanup_if_needed()
    
    def log_token_refresh(self, user_id: int, ip_address: Optional[str] = None) -> None:
        """Log token refresh event."""
        entry = self._create_log_entry(
            event_type=AuditEventType.TOKEN_REFRESH,
            user_id=user_id,
            ip_address=ip_address,
        )
        
        with self._storage_lock:
            self._logs.append(entry)
            self._cleanup_if_needed()
    
    def log_password_change(self, user_id: int, ip_address: Optional[str] = None) -> None:
        """Log password change event."""
        entry = self._create_log_entry(
            event_type=AuditEventType.PASSWORD_CHANGED,
            user_id=user_id,
            ip_address=ip_address,
        )
        
        with self._storage_lock:
            self._logs.append(entry)
            self._cleanup_if_needed()
    
    def get_logs(self, user_id: Optional[int] = None,
                 days: int = 30,
                 event_type: Optional[str] = None,
                 limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with filtering.
        
        Args:
            user_id: Filter by user ID (optional)
            days: Number of days to look back (default: 30)
            event_type: Filter by event type (optional)
            limit: Maximum number of logs to return (default: 100)
            
        Returns:
            List of log entries matching criteria
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        results = []
        
        with self._storage_lock:
            for log in reversed(self._logs):  # Most recent first
                if len(results) >= limit:
                    break
                
                # Filter by user
                if user_id is not None and log.get("user_id") != user_id:
                    continue
                
                # Filter by date
                try:
                    log_time = datetime.fromisoformat(log["timestamp"])
                    if log_time < cutoff:
                        continue
                except (KeyError, ValueError):
                    continue
                
                # Filter by event type
                if event_type and log.get("event_type") != event_type:
                    continue
                
                results.append(log.copy())
        
        return results
    
    def get_logs_by_user(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get all logs for a specific user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of log entries
        """
        return self.get_logs(user_id=user_id, days=days, limit=1000)
    
    def get_recent_logins(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent login attempts for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of entries
            
        Returns:
            List of login log entries
        """
        with self._storage_lock:
            results = []
            for log in reversed(self._logs):
                if len(results) >= limit:
                    break
                if (log.get("user_id") == user_id and 
                    log.get("event_type") in [AuditEventType.LOGIN_SUCCESS.value, 
                                               AuditEventType.LOGIN_FAILURE.value]):
                    results.append(log.copy())
            return results
    
    def _cleanup_if_needed(self) -> None:
        """Remove old logs if storage limit exceeded."""
        if len(self._logs) > self._max_logs:
            # Keep only the most recent logs
            self._logs = self._logs[-self._max_logs:]
    
    def get_log_count(self) -> int:
        """Get total number of logs."""
        with self._storage_lock:
            return len(self._logs)
    
    def clear_logs(self) -> None:
        """Clear all logs. Use with caution."""
        with self._storage_lock:
            self._logs.clear()
    
    def export_logs(self, format: str = "json") -> str:
        """
        Export logs to a string format.
        
        Args:
            format: Export format (json, csv)
            
        Returns:
            Formatted log data
        """
        with self._storage_lock:
            if format == "json":
                return json.dumps(self._logs, indent=2)
            elif format == "csv":
                if not self._logs:
                    return ""
                
                headers = ["timestamp", "event_type", "user_id", "ip_address", "details"]
                lines = [",".join(headers)]
                
                for log in self._logs:
                    row = [
                        log.get("timestamp", ""),
                        log.get("event_type", ""),
                        str(log.get("user_id", "")),
                        log.get("ip_address", ""),
                        json.dumps(log.get("details", {})),
                    ]
                    lines.append(",".join(f'"{field}"' for field in row))
                
                return "\n".join(lines)
            else:
                raise ValueError(f"Unsupported format: {format}")


# Module-level singleton
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the singleton audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience functions
def log_login(user_id: int, success: bool, ip: str, **kwargs) -> None:
    """Convenience function to log login."""
    get_audit_logger().log_login(user_id, success, ip, **kwargs)


def log_api_key_usage(key_id: int, endpoint: str, **kwargs) -> None:
    """Convenience function to log API key usage."""
    get_audit_logger().log_api_key_usage(key_id, endpoint, **kwargs)


def log_permission_change(user_id: int, action: str, **kwargs) -> None:
    """Convenience function to log permission changes."""
    get_audit_logger().log_permission_change(user_id, action, **kwargs)


def get_logs(user_id: Optional[int] = None, days: int = 30, **kwargs) -> List[Dict[str, Any]]:
    """Convenience function to get logs."""
    return get_audit_logger().get_logs(user_id=user_id, days=days, **kwargs)
