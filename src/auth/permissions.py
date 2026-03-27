"""
Permission Management Module
Role-based access control for v2.3.0
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from functools import wraps
import threading


class Role(Enum):
    """Standard user roles with permission levels."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class Permission(Enum):
    """Available permissions in the system."""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # System administration
    ADMIN_ACCESS = "admin:access"
    SYSTEM_CONFIG = "system:config"
    AUDIT_LOGS = "audit:logs"
    
    # API access
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_DELETE = "api:delete"
    
    # Data access
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_DELETE = "data:delete"


# Default role permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.ADMIN_ACCESS,
        Permission.SYSTEM_CONFIG,
        Permission.AUDIT_LOGS,
        Permission.API_READ,
        Permission.API_WRITE,
        Permission.API_DELETE,
        Permission.DATA_READ,
        Permission.DATA_WRITE,
        Permission.DATA_DELETE,
    },
    Role.USER: {
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.API_READ,
        Permission.API_WRITE,
        Permission.DATA_READ,
        Permission.DATA_WRITE,
    },
    Role.READONLY: {
        Permission.USER_READ,
        Permission.API_READ,
        Permission.DATA_READ,
    },
}


class PermissionManager:
    """
    Manages user permissions and role-based access control.
    Thread-safe implementation with in-memory storage.
    
    In production, replace with database-backed storage.
    """
    
    _instance: Optional['PermissionManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'PermissionManager':
        """Singleton pattern for permission manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._user_permissions: Dict[int, Set[Permission]] = {}
                    cls._instance._user_roles: Dict[int, Role] = {}
                    cls._instance._storage_lock = threading.RLock()
        return cls._instance
    
    def check_permission(self, user: dict, required: str) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user: User dictionary with 'id' and optionally 'role'
            required: Required permission string (e.g., "user:read")
            
        Returns:
            True if user has the permission
        """
        user_id = user.get("id")
        if user_id is None:
            return False
        
        try:
            required_perm = Permission(required)
        except ValueError:
            # Unknown permission, deny by default
            return False
        
        with self._storage_lock:
            # Check explicit user permissions first
            if user_id in self._user_permissions:
                if required_perm in self._user_permissions[user_id]:
                    return True
            
            # Check role-based permissions
            if user_id in self._user_roles:
                role = self._user_roles[user_id]
                if required_perm in ROLE_PERMISSIONS.get(role, set()):
                    return True
            
            # Fallback to user-provided role
            user_role = user.get("role")
            if user_role:
                try:
                    role = Role(user_role)
                    if required_perm in ROLE_PERMISSIONS.get(role, set()):
                        return True
                except ValueError:
                    pass
        
        return False
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of permission strings
        """
        with self._storage_lock:
            permissions = set()
            
            # Get explicit permissions
            if user_id in self._user_permissions:
                permissions.update(self._user_permissions[user_id])
            
            # Add role-based permissions
            if user_id in self._user_roles:
                role = self._user_roles[user_id]
                permissions.update(ROLE_PERMISSIONS.get(role, set()))
            
            return [perm.value for perm in permissions]
    
    def get_user_role(self, user_id: int) -> Optional[str]:
        """
        Get the role for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Role string or None
        """
        with self._storage_lock:
            role = self._user_roles.get(user_id)
            return role.value if role else None
    
    def assign_permission(self, user_id: int, permission: str) -> bool:
        """
        Assign a specific permission to a user.
        
        Args:
            user_id: User ID
            permission: Permission string to assign
            
        Returns:
            True if successfully assigned
        """
        try:
            perm = Permission(permission)
        except ValueError:
            return False
        
        with self._storage_lock:
            if user_id not in self._user_permissions:
                self._user_permissions[user_id] = set()
            self._user_permissions[user_id].add(perm)
            return True
    
    def revoke_permission(self, user_id: int, permission: str) -> bool:
        """
        Revoke a specific permission from a user.
        
        Args:
            user_id: User ID
            permission: Permission string to revoke
            
        Returns:
            True if successfully revoked
        """
        try:
            perm = Permission(permission)
        except ValueError:
            return False
        
        with self._storage_lock:
            if user_id in self._user_permissions:
                self._user_permissions[user_id].discard(perm)
                return True
            return False
    
    def assign_role(self, user_id: int, role: str) -> bool:
        """
        Assign a role to a user.
        
        Args:
            user_id: User ID
            role: Role string (admin/user/readonly)
            
        Returns:
            True if successfully assigned
        """
        try:
            role_enum = Role(role)
        except ValueError:
            return False
        
        with self._storage_lock:
            self._user_roles[user_id] = role_enum
            return True
    
    def revoke_role(self, user_id: int) -> bool:
        """
        Revoke a user's role (resets to default).
        
        Args:
            user_id: User ID
            
        Returns:
            True if role was revoked
        """
        with self._storage_lock:
            if user_id in self._user_roles:
                del self._user_roles[user_id]
                return True
            return False
    
    def has_role(self, user_id: int, role: str) -> bool:
        """
        Check if a user has a specific role.
        
        Args:
            user_id: User ID
            role: Role to check
            
        Returns:
            True if user has the role
        """
        with self._storage_lock:
            user_role = self._user_roles.get(user_id)
            if user_role:
                return user_role.value == role
            return False
    
    def clear_user(self, user_id: int) -> None:
        """
        Clear all permissions and roles for a user.
        
        Args:
            user_id: User ID
        """
        with self._storage_lock:
            self._user_permissions.pop(user_id, None)
            self._user_roles.pop(user_id, None)


# Module-level singleton
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get the singleton permission manager instance."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


# Decorator for permission checking
def require_permission(permission: str):
    """
    Decorator to require a specific permission for a function.
    
    Usage:
        @require_permission("user:read")
        def get_user(user_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(user: dict, *args, **kwargs):
            manager = get_permission_manager()
            if not manager.check_permission(user, permission):
                raise PermissionError(
                    f"User {user.get('id')} lacks required permission: {permission}"
                )
            return func(user, *args, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """
    Decorator to require a specific role for a function.
    
    Usage:
        @require_role("admin")
        def admin_function(user):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(user: dict, *args, **kwargs):
            manager = get_permission_manager()
            user_id = user.get("id")
            if not manager.has_role(user_id, role):
                raise PermissionError(
                    f"User {user_id} lacks required role: {role}"
                )
            return func(user, *args, **kwargs)
        return wrapper
    return decorator


def get_rate_limit_override(user_role: str) -> dict:
    """
    Get rate limit override settings based on user role.
    
    Args:
        user_role: User role string (admin/premium/free)
        
    Returns:
        Dictionary with rate limit settings:
        - 'unlimited': bool - If True, no rate limiting
        - 'multiplier': float - Rate limit multiplier (1.0 = standard)
        - 'burst_limit': int - Optional burst limit override
        
    Examples:
        >>> get_rate_limit_override("admin")
        {'unlimited': True, 'multiplier': None, 'burst_limit': None}
        >>> get_rate_limit_override("premium")
        {'unlimited': False, 'multiplier': 10.0, 'burst_limit': None}
        >>> get_rate_limit_override("free")
        {'unlimited': False, 'multiplier': 1.0, 'burst_limit': None}
    """
    role_overrides = {
        'admin': {
            'unlimited': True,
            'multiplier': None,
            'burst_limit': None,
            'description': 'Unlimited rate limit for administrators',
        },
        'premium': {
            'unlimited': False,
            'multiplier': 10.0,
            'burst_limit': None,
            'description': '10x rate limit for premium users',
        },
        'user': {
            'unlimited': False,
            'multiplier': 1.0,
            'burst_limit': None,
            'description': 'Standard rate limit for regular users',
        },
        'free': {
            'unlimited': False,
            'multiplier': 1.0,
            'burst_limit': None,
            'description': 'Standard rate limit for free users',
        },
        'readonly': {
            'unlimited': False,
            'multiplier': 0.5,
            'burst_limit': None,
            'description': '0.5x rate limit for read-only users',
        },
    }
    
    # Default to free tier if role not recognized
    return role_overrides.get(user_role.lower(), role_overrides['free'])


def apply_rate_limit_override(base_limit: int, user_role: str) -> int:
    """
    Apply rate limit override based on user role.
    
    Args:
        base_limit: Base rate limit
        user_role: User role string
        
    Returns:
        Adjusted rate limit (or -1 for unlimited)
    """
    override = get_rate_limit_override(user_role)
    
    if override['unlimited']:
        return -1  # Special value indicating unlimited
    
    multiplier = override.get('multiplier', 1.0)
    return int(base_limit * multiplier)
