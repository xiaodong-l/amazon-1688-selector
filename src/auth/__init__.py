"""
Authentication Module for Amazon-1688-Selector v2.3.0

This module provides comprehensive authentication and authorization:
- JWT token management
- Password hashing with bcrypt
- Token blacklist management
- Role-based permissions
- Audit logging

Usage:
    from src.auth import jwt, password, permissions, audit_log
    from src.auth.jwt import create_access_token, verify_token
    from src.auth.password import hash_password, verify_password
    from src.auth.permissions import PermissionManager, require_permission
    from src.auth.audit_log import AuditLogger, log_login
"""

from .jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    refresh_token,
    blacklist_token,
    is_token_blacklisted,
    cleanup_blacklist,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

from .password import (
    hash_password,
    verify_password,
    needs_rehash,
    rehash_password,
    validate_password_strength,
)

from .token_blacklist import (
    TokenBlacklist,
    get_blacklist,
    blacklist_token as blacklist_token_func,
    is_token_blacklisted as is_blacklisted_func,
    cleanup_blacklist as cleanup_blacklist_func,
)

from .permissions import (
    PermissionManager,
    Role,
    Permission,
    ROLE_PERMISSIONS,
    get_permission_manager,
    require_permission,
    require_role,
)

from .audit_log import (
    AuditLogger,
    AuditEventType,
    get_audit_logger,
    log_login,
    log_api_key_usage,
    log_permission_change,
    get_logs,
)

__version__ = "2.3.0"
__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "refresh_token",
    "blacklist_token",
    "is_token_blacklisted",
    "cleanup_blacklist",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    # Password
    "hash_password",
    "verify_password",
    "needs_rehash",
    "rehash_password",
    "validate_password_strength",
    # Token Blacklist
    "TokenBlacklist",
    "get_blacklist",
    "blacklist_token_func",
    "is_blacklisted_func",
    "cleanup_blacklist_func",
    # Permissions
    "PermissionManager",
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    "get_permission_manager",
    "require_permission",
    "require_role",
    # Audit Log
    "AuditLogger",
    "AuditEventType",
    "get_audit_logger",
    "log_login",
    "log_api_key_usage",
    "log_permission_change",
    "get_logs",
]
