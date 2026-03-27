"""
Rate Limit Whitelist Management
Manage IPs and keys that bypass rate limiting.
"""

from typing import Dict, Set, Optional, List, Any
import threading
import time
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class WhitelistEntry:
    """Represents a whitelist entry."""
    
    def __init__(self, value: str, reason: str, created_at: float,
                 expires_at: Optional[float] = None, created_by: str = "system"):
        self.value = value
        self.reason = reason
        self.created_at = created_at
        self.expires_at = expires_at
        self.created_by = created_by
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'value': self.value,
            'reason': self.reason,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'created_by': self.created_by,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WhitelistEntry':
        """Create from dictionary."""
        return cls(
            value=data['value'],
            reason=data['reason'],
            created_at=data['created_at'],
            expires_at=data.get('expires_at'),
            created_by=data.get('created_by', 'system'),
        )


class RateLimitWhitelist:
    """
    Manages rate limit whitelist.
    
    Features:
    - IP-based whitelisting
    - Key-based whitelisting
    - Expiration support
    - Persistence to file
    - Thread-safe operations
    """
    
    _instance: Optional['RateLimitWhitelist'] = None
    _lock = threading.Lock()
    
    def __new__(cls, persist_file: Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, persist_file: Optional[str] = None):
        if self._initialized:
            return
        
        self._persist_file = persist_file
        self._ip_whitelist: Dict[str, WhitelistEntry] = {}
        self._key_whitelist: Dict[str, WhitelistEntry] = {}
        self._lock = threading.RLock()
        self._initialized = True
        
        # Load persisted data if file exists
        if persist_file:
            self._load()
    
    def is_whitelisted(self, ip: Optional[str] = None, key: Optional[str] = None) -> bool:
        """
        Check if IP or key is whitelisted.
        
        Args:
            ip: IP address to check
            key: Rate limit key to check
            
        Returns:
            True if whitelisted
        """
        with self._lock:
            if ip and self._check_ip(ip):
                return True
            
            if key and self._check_key(key):
                return True
            
            return False
    
    def _check_ip(self, ip: str) -> bool:
        """Check if IP is whitelisted."""
        if ip in self._ip_whitelist:
            entry = self._ip_whitelist[ip]
            if entry.is_expired():
                # Remove expired entry
                del self._ip_whitelist[ip]
                logger.info(f"Whitelist entry expired for IP: {ip}")
                return False
            return True
        return False
    
    def _check_key(self, key: str) -> bool:
        """Check if key is whitelisted."""
        if key in self._key_whitelist:
            entry = self._key_whitelist[key]
            if entry.is_expired():
                del self._key_whitelist[key]
                logger.info(f"Whitelist entry expired for key: {key}")
                return False
            return True
        return False
    
    def add_to_whitelist(self, ip: Optional[str] = None, key: Optional[str] = None,
                        reason: str = "", expires_in: Optional[int] = None,
                        created_by: str = "system") -> bool:
        """
        Add IP or key to whitelist.
        
        Args:
            ip: IP address to whitelist
            key: Rate limit key to whitelist
            reason: Reason for whitelisting
            expires_in: Expiration time in seconds (None = never expires)
            created_by: Who added this entry
            
        Returns:
            True if successfully added
        """
        if not ip and not key:
            logger.warning("Whitelist add requires either ip or key")
            return False
        
        now = time.time()
        expires_at = None
        if expires_in is not None:
            expires_at = now + expires_in
        
        with self._lock:
            if ip:
                entry = WhitelistEntry(
                    value=ip,
                    reason=reason,
                    created_at=now,
                    expires_at=expires_at,
                    created_by=created_by,
                )
                self._ip_whitelist[ip] = entry
                logger.info(f"Added IP to whitelist: {ip} (reason: {reason})")
            
            if key:
                entry = WhitelistEntry(
                    value=key,
                    reason=reason,
                    created_at=now,
                    expires_at=expires_at,
                    created_by=created_by,
                )
                self._key_whitelist[key] = entry
                logger.info(f"Added key to whitelist: {key} (reason: {reason})")
            
            # Persist if configured
            if self._persist_file:
                self._save()
            
            return True
    
    def remove_from_whitelist(self, ip: Optional[str] = None,
                             key: Optional[str] = None) -> bool:
        """
        Remove IP or key from whitelist.
        
        Args:
            ip: IP address to remove
            key: Rate limit key to remove
            
        Returns:
            True if removed
        """
        if not ip and not key:
            logger.warning("Whitelist remove requires either ip or key")
            return False
        
        with self._lock:
            removed = False
            
            if ip and ip in self._ip_whitelist:
                del self._ip_whitelist[ip]
                removed = True
                logger.info(f"Removed IP from whitelist: {ip}")
            
            if key and key in self._key_whitelist:
                del self._key_whitelist[key]
                removed = True
                logger.info(f"Removed key from whitelist: {key}")
            
            # Persist if configured
            if self._persist_file and removed:
                self._save()
            
            return removed
    
    def get_whitelisted_ips(self) -> List[Dict[str, Any]]:
        """Get all whitelisted IPs."""
        with self._lock:
            return [entry.to_dict() for entry in self._ip_whitelist.values()]
    
    def get_whitelisted_keys(self) -> List[Dict[str, Any]]:
        """Get all whitelisted keys."""
        with self._lock:
            return [entry.to_dict() for entry in self._key_whitelist.values()]
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            removed = 0
            
            # Clean IP whitelist
            expired_ips = [
                ip for ip, entry in self._ip_whitelist.items()
                if entry.is_expired()
            ]
            for ip in expired_ips:
                del self._ip_whitelist[ip]
                removed += 1
            
            # Clean key whitelist
            expired_keys = [
                key for key, entry in self._key_whitelist.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._key_whitelist[key]
                removed += 1
            
            if removed > 0:
                logger.info(f"Cleaned up {removed} expired whitelist entries")
                
                # Persist if configured
                if self._persist_file:
                    self._save()
            
            return removed
    
    def _save(self) -> bool:
        """Persist whitelist to file."""
        if not self._persist_file:
            return False
        
        try:
            data = {
                'ip_whitelist': [e.to_dict() for e in self._ip_whitelist.values()],
                'key_whitelist': [e.to_dict() for e in self._key_whitelist.values()],
                'updated_at': time.time(),
            }
            
            # Ensure directory exists
            path = Path(self._persist_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save whitelist: {e}")
            return False
    
    def _load(self) -> bool:
        """Load whitelist from file."""
        if not self._persist_file:
            return False
        
        try:
            path = Path(self._persist_file)
            if not path.exists():
                return False
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            with self._lock:
                # Load IP whitelist
                for entry_data in data.get('ip_whitelist', []):
                    entry = WhitelistEntry.from_dict(entry_data)
                    if not entry.is_expired():
                        self._ip_whitelist[entry.value] = entry
                
                # Load key whitelist
                for entry_data in data.get('key_whitelist', []):
                    entry = WhitelistEntry.from_dict(entry_data)
                    if not entry.is_expired():
                        self._key_whitelist[entry.value] = entry
            
            logger.info(f"Loaded whitelist from {self._persist_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load whitelist: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get whitelist statistics."""
        with self._lock:
            return {
                'ip_count': len(self._ip_whitelist),
                'key_count': len(self._key_whitelist),
                'persist_file': self._persist_file,
            }
    
    def clear(self) -> None:
        """Clear all whitelist entries."""
        with self._lock:
            self._ip_whitelist.clear()
            self._key_whitelist.clear()
            
            if self._persist_file:
                self._save()
            
            logger.info("Whitelist cleared")


# Module-level singleton
_whitelist: Optional[RateLimitWhitelist] = None


def get_whitelist(persist_file: Optional[str] = None) -> RateLimitWhitelist:
    """
    Get or create whitelist instance.
    
    Args:
        persist_file: Optional file path for persistence
        
    Returns:
        Whitelist instance
    """
    global _whitelist
    if _whitelist is None:
        _whitelist = RateLimitWhitelist(persist_file)
    return _whitelist


# Decorator for whitelist bypass
def whitelist_bypass(ip_extractor=None, key_extractor=None):
    """
    Decorator to bypass rate limiting for whitelisted IPs/keys.
    
    Usage:
        @whitelist_bypass(ip_extractor=lambda req: req.client.host)
        def api_endpoint(request):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            whitelist = get_whitelist()
            
            # Extract IP
            ip = None
            if ip_extractor:
                ip = ip_extractor(*args, **kwargs)
            
            # Extract key
            key = None
            if key_extractor:
                key = key_extractor(*args, **kwargs)
            
            # Check whitelist
            if whitelist.is_whitelisted(ip=ip, key=key):
                logger.debug(f"Whitelist bypass for IP={ip}, key={key}")
                # Skip rate limiting
                return func(*args, **kwargs)
            
            # Continue with normal rate limiting
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
