"""
API Key Management Module
Handles API key generation, validation, and usage tracking for v2.4.0
"""

import secrets
import hashlib
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path


class APIKeyManager:
    """
    Manages API keys for external access.
    Thread-safe implementation with file-based persistence.
    
    In production, replace with database-backed storage.
    """
    
    _instance: Optional['APIKeyManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, storage_path: Optional[str] = None) -> 'APIKeyManager':
        """Singleton pattern for API key manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._storage_path = storage_path
                    cls._instance._keys: Dict[str, dict] = {}
                    cls._instance._usage: Dict[str, List[dict]] = {}
                    cls._instance._storage_lock = threading.RLock()
                    cls._instance._load_keys()
        return cls._instance
    
    def _load_keys(self) -> None:
        """Load API keys from storage file."""
        if self._storage_path:
            path = Path(self._storage_path)
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._keys = data.get('keys', {})
                        self._usage = data.get('usage', {})
                except Exception:
                    self._keys = {}
                    self._usage = {}
    
    def _save_keys(self) -> None:
        """Save API keys to storage file."""
        if self._storage_path:
            path = Path(self._storage_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'keys': self._keys,
                        'usage': self._usage,
                    }, f, indent=2, default=str)
            except Exception:
                pass
    
    def generate_key(self, user_id: int, name: str, 
                     permissions: Optional[List[str]] = None,
                     expires_in_days: Optional[int] = None,
                     rate_limit: Optional[int] = None) -> dict:
        """
        Generate a new API key.
        
        Args:
            user_id: Owner user ID
            name: Human-readable name for the key
            permissions: List of permission strings
            expires_in_days: Days until expiration (None = never)
            rate_limit: Requests per hour (None = unlimited)
            
        Returns:
            Dictionary with key details (including raw key)
        """
        # Generate raw key
        raw_key = f"sk_{secrets.token_urlsafe(32)}"
        
        # Hash for storage
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        key_data = {
            'id': key_hash[:16],  # Short ID for reference
            'name': name,
            'user_id': user_id,
            'hash': key_hash,
            'permissions': permissions or [],
            'created_at': datetime.utcnow(),
            'expires_at': expires_at,
            'rate_limit': rate_limit,
            'is_active': True,
            'last_used': None,
            'usage_count': 0,
        }
        
        with self._storage_lock:
            self._keys[key_hash] = key_data
            self._usage[key_hash] = []
            self._save_keys()
        
        return {
            'id': key_data['id'],
            'key': raw_key,  # Only shown once
            'name': name,
            'permissions': key_data['permissions'],
            'created_at': key_data['created_at'].isoformat(),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'rate_limit': rate_limit,
        }
    
    def validate_key(self, raw_key: str) -> Optional[dict]:
        """
        Validate an API key and return key info if valid.
        
        Args:
            raw_key: Raw API key string
            
        Returns:
            Key info dict if valid, None if invalid
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        with self._storage_lock:
            key_data = self._keys.get(key_hash)
            
            if not key_data:
                return None
            
            if not key_data['is_active']:
                return None
            
            if key_data['expires_at'] and key_data['expires_at'] < datetime.utcnow():
                return None
            
            # Update last used
            key_data['last_used'] = datetime.utcnow()
            key_data['usage_count'] += 1
            
            # Track usage
            self._usage[key_hash].append({
                'timestamp': datetime.utcnow().isoformat(),
                'success': True,
            })
            
            # Keep only last 1000 usage records
            if len(self._usage[key_hash]) > 1000:
                self._usage[key_hash] = self._usage[key_hash][-1000:]
            
            self._save_keys()
            
            return {
                'id': key_data['id'],
                'user_id': key_data['user_id'],
                'permissions': key_data['permissions'],
                'name': key_data['name'],
            }
    
    def list_keys(self, user_id: int) -> List[dict]:
        """
        List all API keys for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of key info dicts (without hashes)
        """
        keys = []
        with self._storage_lock:
            for key_hash, key_data in self._keys.items():
                if key_data['user_id'] == user_id:
                    keys.append({
                        'id': key_data['id'],
                        'name': key_data['name'],
                        'permissions': key_data['permissions'],
                        'created_at': key_data['created_at'].isoformat(),
                        'expires_at': key_data['expires_at'].isoformat() if key_data['expires_at'] else None,
                        'rate_limit': key_data['rate_limit'],
                        'is_active': key_data['is_active'],
                        'last_used': key_data['last_used'].isoformat() if key_data['last_used'] else None,
                        'usage_count': key_data['usage_count'],
                    })
        return keys
    
    def revoke_key(self, user_id: int, key_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            user_id: User ID (for ownership check)
            key_id: Short key ID
            
        Returns:
            True if successfully revoked
        """
        with self._storage_lock:
            for key_hash, key_data in self._keys.items():
                if key_data['id'] == key_id and key_data['user_id'] == user_id:
                    key_data['is_active'] = False
                    self._save_keys()
                    return True
        return False
    
    def rotate_key(self, user_id: int, key_id: str, name: Optional[str] = None) -> Optional[dict]:
        """
        Rotate an API key (revoke old, create new).
        
        Args:
            user_id: User ID
            key_id: Short key ID of key to rotate
            name: New name (optional, keeps old if not provided)
            
        Returns:
            New key info dict if successful, None otherwise
        """
        with self._storage_lock:
            old_key_data = None
            for key_hash, key_data in self._keys.items():
                if key_data['id'] == key_id and key_data['user_id'] == user_id:
                    old_key_data = key_data.copy()
                    break
            
            if not old_key_data:
                return None
            
            # Revoke old key
            old_key_data['is_active'] = False
            
            # Create new key with same settings
            new_key = self.generate_key(
                user_id=user_id,
                name=name or old_key_data['name'],
                permissions=old_key_data['permissions'],
                expires_in_days=None,  # New key doesn't expire
                rate_limit=old_key_data['rate_limit'],
            )
            
            self._save_keys()
            return new_key
    
    def get_usage_stats(self, user_id: int, key_id: str) -> dict:
        """
        Get usage statistics for an API key.
        
        Args:
            user_id: User ID
            key_id: Short key ID
            
        Returns:
            Usage statistics dict
        """
        with self._storage_lock:
            key_hash = None
            for kh, key_data in self._keys.items():
                if key_data['id'] == key_id and key_data['user_id'] == user_id:
                    key_hash = kh
                    break
            
            if not key_hash:
                return {'error': 'Key not found'}
            
            usage_records = self._usage.get(key_hash, [])
            
            # Calculate stats
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            week_ago = now - timedelta(weeks=1)
            
            requests_last_hour = sum(
                1 for r in usage_records 
                if datetime.fromisoformat(r['timestamp']) > hour_ago
            )
            requests_last_day = sum(
                1 for r in usage_records 
                if datetime.fromisoformat(r['timestamp']) > day_ago
            )
            requests_last_week = sum(
                1 for r in usage_records 
                if datetime.fromisoformat(r['timestamp']) > week_ago
            )
            
            return {
                'key_id': key_id,
                'total_requests': len(usage_records),
                'requests_last_hour': requests_last_hour,
                'requests_last_day': requests_last_day,
                'requests_last_week': requests_last_week,
                'success_rate': 100.0,  # All tracked requests are successful
            }
    
    def check_rate_limit(self, raw_key: str) -> tuple[bool, Optional[int]]:
        """
        Check if a request is within rate limits.
        
        Args:
            raw_key: Raw API key
            
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        with self._storage_lock:
            key_data = self._keys.get(key_hash)
            
            if not key_data or not key_data['rate_limit']:
                return (True, None)
            
            # Count requests in last hour
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            usage_records = self._usage.get(key_hash, [])
            recent_count = sum(
                1 for r in usage_records 
                if datetime.fromisoformat(r['timestamp']) > hour_ago
            )
            
            if recent_count >= key_data['rate_limit']:
                # Calculate retry after
                oldest_recent = min(
                    (datetime.fromisoformat(r['timestamp']) for r in usage_records 
                     if datetime.fromisoformat(r['timestamp']) > hour_ago),
                    default=now
                )
                retry_after = int((oldest_recent + timedelta(hours=1) - now).total_seconds())
                return (False, max(1, retry_after))
            
            return (True, None)


# Module-level singleton
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager(storage_path: Optional[str] = None) -> APIKeyManager:
    """Get the singleton API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(storage_path)
    return _api_key_manager
