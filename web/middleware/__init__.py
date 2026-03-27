"""
Web Middleware Package
"""

from web.middleware.auth import (
    require_auth,
    require_permission,
    require_role,
    optional_auth,
    get_current_user,
    is_authenticated,
    get_user_id,
    get_user_role,
    check_api_key,
    init_auth,
)

__all__ = [
    'require_auth',
    'require_permission',
    'require_role',
    'optional_auth',
    'get_current_user',
    'is_authenticated',
    'get_user_id',
    'get_user_role',
    'check_api_key',
    'init_auth',
]
