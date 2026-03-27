"""
Token Blacklist Module
Manages revoked/invalidated tokens for v2.3.0
"""

from datetime import datetime
from typing import Dict, Optional
import threading


class TokenBlacklist:
    """
    Thread-safe token blacklist management.
    
    In production, replace in-memory storage with Redis or database.
    """
    
    _instance: Optional['TokenBlacklist'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'TokenBlacklist':
        """Singleton pattern to ensure single blacklist instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._blacklist: Dict[str, datetime] = {}
                    cls._instance._storage_lock = threading.RLock()
        return cls._instance
    
    def add(self, token: str, expires_at: datetime) -> bool:
        """
        Add a token to the blacklist.
        
        Args:
            token: JWT token string to blacklist
            expires_at: When the blacklist entry should expire
            
        Returns:
            True if successfully added, False otherwise
        """
        if not token or not expires_at:
            return False
        
        with self._storage_lock:
            self._blacklist[token] = expires_at
            return True
    
    def is_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            token: JWT token string to check
            
        Returns:
            True if token is blacklisted and not expired, False otherwise
        """
        if not token:
            return False
        
        with self._storage_lock:
            if token in self._blacklist:
                expires_at = self._blacklist[token]
                if datetime.utcnow() < expires_at:
                    return True
                else:
                    # Auto-cleanup expired entry
                    del self._blacklist[token]
            return False
    
    def remove(self, token: str) -> bool:
        """
        Remove a token from the blacklist (e.g., for token reuse).
        
        Args:
            token: JWT token string to remove
            
        Returns:
            True if token was removed, False if not found
        """
        if not token:
            return False
        
        with self._storage_lock:
            if token in self._blacklist:
                del self._blacklist[token]
                return True
            return False
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the blacklist.
        
        Returns:
            Number of entries removed
        """
        removed_count = 0
        now = datetime.utcnow()
        
        with self._storage_lock:
            expired_tokens = [
                token for token, expires_at in self._blacklist.items()
                if now >= expires_at
            ]
            
            for token in expired_tokens:
                del self._blacklist[token]
                removed_count += 1
        
        return removed_count
    
    def get_blacklist_size(self) -> int:
        """
        Get the current number of blacklisted tokens.
        
        Returns:
            Number of tokens in blacklist
        """
        with self._storage_lock:
            return len(self._blacklist)
    
    def clear(self) -> None:
        """
        Clear all entries from the blacklist.
        Use with caution - typically only for testing.
        """
        with self._storage_lock:
            self._blacklist.clear()


# Module-level convenience functions
_blacklist_instance: Optional[TokenBlacklist] = None


def get_blacklist() -> TokenBlacklist:
    """Get the singleton blacklist instance."""
    global _blacklist_instance
    if _blacklist_instance is None:
        _blacklist_instance = TokenBlacklist()
    return _blacklist_instance


def blacklist_token(token: str, expires_at: Optional[datetime] = None) -> bool:
    """
    Convenience function to blacklist a token.
    
    Args:
        token: JWT token to blacklist
        expires_at: Optional expiration time (defaults to 7 days)
        
    Returns:
        True if successfully blacklisted
    """
    if expires_at is None:
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(days=7)
    
    return get_blacklist().add(token, expires_at)


def is_token_blacklisted(token: str) -> bool:
    """
    Convenience function to check if token is blacklisted.
    
    Args:
        token: JWT token to check
        
    Returns:
        True if blacklisted
    """
    return get_blacklist().is_blacklisted(token)


def cleanup_blacklist() -> int:
    """
    Convenience function to cleanup expired blacklist entries.
    
    Returns:
        Number of entries removed
    """
    return get_blacklist().cleanup_expired()
