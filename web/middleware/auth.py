"""
Authentication Middleware
Provides decorators and utilities for protecting routes with authentication and authorization.
"""

from functools import wraps
from flask import request, jsonify, g, current_app
from loguru import logger
from typing import Optional, Callable, Union

from src.auth.jwt import verify_token
from src.auth.permissions import get_permission_manager, PermissionManager


def require_auth(f: Callable) -> Callable:
    """
    需要认证的装饰器
    
    检查 Authorization header 中的 Bearer token，验证后将用户信息附加到 request.current_user
    
    Usage:
        @auth_bp.route('/protected')
        @require_auth
        def protected_route():
            user = request.current_user
            return jsonify({"user": user})
    
    Returns:
        401 if token is missing or invalid
        Original function result if authenticated
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logger.warning("认证失败：缺少 Authorization header")
            return jsonify({
                "success": False,
                "error": "缺少认证信息",
                "message": "请在 Authorization header 中提供 Bearer token",
            }), 401
        
        # Extract token
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            logger.warning("认证失败：无效的 Authorization header 格式")
            return jsonify({
                "success": False,
                "error": "无效的认证格式",
                "message": "请使用 Bearer <token> 格式",
            }), 401
        
        token = parts[1]
        
        try:
            # Verify token
            payload = verify_token(token)
            
            # Attach user info to request
            request.current_user = payload
            
            # Also store in g for template access
            g.current_user = payload
            
            logger.debug(f"认证成功：用户 {payload.get('username')} (ID: {payload.get('user_id')})")
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.warning(f"认证失败：{str(e)}")
            return jsonify({
                "success": False,
                "error": "认证失败",
                "message": str(e),
            }), 401
    
    return decorated


def require_permission(permission: str):
    """
    需要特定权限的装饰器
    
    检查用户是否具有指定的权限。必须在 @require_auth 之后使用。
    
    Usage:
        @auth_bp.route('/admin')
        @require_auth
        @require_permission('admin:access')
        def admin_route():
            return jsonify({"message": "Admin access granted"})
    
    Args:
        permission: Permission string (e.g., "user:read", "api:write")
    
    Returns:
        403 if user lacks permission
        Original function result if authorized
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            # Ensure user is authenticated
            if not hasattr(request, 'current_user') or not request.current_user:
                return jsonify({
                    "success": False,
                    "error": "未认证",
                    "message": "请先登录",
                }), 401
            
            user = request.current_user
            user_id = user.get('user_id')
            
            # Check permission
            manager = get_permission_manager()
            
            if not manager.check_permission(user, permission):
                logger.warning(f"权限拒绝：用户 {user.get('username')} 缺少权限 {permission}")
                return jsonify({
                    "success": False,
                    "error": "权限不足",
                    "message": f"您需要 {permission} 权限才能执行此操作",
                    "required_permission": permission,
                }), 403
            
            logger.debug(f"权限检查通过：用户 {user.get('username')} 拥有 {permission}")
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def require_role(role: str):
    """
    需要特定角色的装饰器
    
    检查用户是否具有指定的角色。必须在 @require_auth 之后使用。
    
    Usage:
        @auth_bp.route('/admin')
        @require_auth
        @require_role('admin')
        def admin_route():
            return jsonify({"message": "Admin access granted"})
    
    Args:
        role: Role string (e.g., "admin", "user", "readonly")
    
    Returns:
        403 if user lacks required role
        Original function result if authorized
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            # Ensure user is authenticated
            if not hasattr(request, 'current_user') or not request.current_user:
                return jsonify({
                    "success": False,
                    "error": "未认证",
                    "message": "请先登录",
                }), 401
            
            user = request.current_user
            user_id = user.get('user_id')
            user_role = user.get('role')
            
            # Check role
            manager = get_permission_manager()
            
            if not manager.has_role(user_id, role):
                logger.warning(f"角色拒绝：用户 {user.get('username')} ({user_role}) 需要角色 {role}")
                return jsonify({
                    "success": False,
                    "error": "权限不足",
                    "message": f"您需要 {role} 角色才能执行此操作",
                    "required_role": role,
                    "your_role": user_role,
                }), 403
            
            logger.debug(f"角色检查通过：用户 {user.get('username')} 拥有 {role} 角色")
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def optional_auth(f: Callable) -> Callable:
    """
    可选认证的装饰器
    
    如果提供了有效的 token，则认证用户；否则允许匿名访问。
    用户信息会附加到 request.current_user（如果认证成功）。
    
    Usage:
        @public_bp.route('/products')
        @optional_auth
        def get_products():
            if request.current_user:
                # Return personalized results
                ...
            else:
                # Return public results
                ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
                try:
                    payload = verify_token(token)
                    request.current_user = payload
                    g.current_user = payload
                    logger.debug(f"可选认证成功：用户 {payload.get('username')}")
                except Exception:
                    # Token invalid, but allow anonymous access
                    request.current_user = None
                    logger.debug("可选认证：无效 token，允许匿名访问")
        else:
            request.current_user = None
        
        return f(*args, **kwargs)
    
    return decorated


def get_current_user() -> Optional[dict]:
    """
    获取当前认证用户
    
    Returns:
        User dict if authenticated, None otherwise
    """
    return getattr(request, 'current_user', None)


def is_authenticated() -> bool:
    """
    检查当前请求是否已认证
    
    Returns:
        True if user is authenticated
    """
    return hasattr(request, 'current_user') and request.current_user is not None


def get_user_id() -> Optional[int]:
    """
    获取当前用户 ID
    
    Returns:
        User ID if authenticated, None otherwise
    """
    user = get_current_user()
    return user.get('user_id') if user else None


def get_user_role() -> Optional[str]:
    """
    获取当前用户角色
    
    Returns:
        User role if authenticated, None otherwise
    """
    user = get_current_user()
    return user.get('role') if user else None


def check_api_key():
    """
    检查 API Key 认证
    
    支持通过 X-API-Key header 进行 API Key 认证。
    如果验证成功，将用户信息附加到 request.current_user。
    
    Usage:
        @api_bp.route('/data')
        def get_data():
            user = check_api_key()
            if not user:
                return jsonify({"error": "Invalid API key"}), 401
            ...
    
    Returns:
        User dict if API key is valid, None otherwise
    """
    api_key = request.headers.get('X-API-Key')
    
    if not api_key:
        return None
    
    try:
        from src.auth.api_key import get_api_key_manager
        
        manager = get_api_key_manager()
        key_info = manager.validate_key(api_key)
        
        if key_info:
            # Create user context from API key
            request.current_user = {
                'user_id': key_info['user_id'],
                'username': f"api_key_{key_info['name']}",
                'auth_type': 'api_key',
                'permissions': key_info.get('permissions', []),
            }
            logger.debug(f"API Key 认证成功：{key_info['name']}")
            return request.current_user
        
    except Exception as e:
        logger.error(f"API Key 认证失败：{e}")
    
    return None


def auth_middleware():
    """
    Flask before_request handler for global authentication
    
    This can be registered with app.before_request(auth_middleware)
    to apply authentication to all routes (except those explicitly excluded).
    """
    # Skip for certain paths
    skip_paths = [
        '/api/v2/auth/login',
        '/api/v2/auth/register',
        '/api/v2/auth/health',
        '/api/v2/auth/token/refresh',
        '/static',
        '/',
        '/charts',
    ]
    
    if any(request.path.startswith(path) for path in skip_paths):
        return None
    
    # Try API key auth first
    if request.headers.get('X-API-Key'):
        user = check_api_key()
        if user:
            return None
    
    # For protected routes, require Bearer token
    # This is handled by @require_auth decorator on individual routes
    return None


def init_auth(app):
    """
    Initialize authentication for a Flask app
    
    Usage:
        from web.middleware.auth import init_auth
        app = Flask(__name__)
        init_auth(app)
    """
    app.before_request(auth_middleware)
    
    # Add user info to template context
    @app.context_processor
    def inject_user():
        return {
            'current_user': getattr(g, 'current_user', None),
            'is_authenticated': is_authenticated(),
        }
