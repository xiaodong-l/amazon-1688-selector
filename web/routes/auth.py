"""
Authentication API Routes
Handles user login, logout, token management, and API key operations for v2.4.0
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from loguru import logger
import sys

from src.auth.jwt import create_access_token, create_refresh_token, verify_token, refresh_token, blacklist_token
from src.auth.password import verify_password, validate_password_strength
from src.auth.api_key import get_api_key_manager
from src.auth.permissions import get_permission_manager, PermissionManager, Role
from web.middleware.auth import require_auth, require_permission

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/v2/auth')

# In-memory user store (replace with database in production)
# Format: {user_id: {username, password_hash, email, role, created_at, ...}}
_users_db = {
    1: {
        'id': 1,
        'username': 'admin',
        'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MebAJu',  # 'admin123!@#'
        'email': 'admin@example.com',
        'role': 'admin',
        'created_at': datetime.utcnow(),
        'is_active': True,
    },
    2: {
        'id': 2,
        'username': 'user',
        'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MebAJu',  # 'user123!@#'
        'email': 'user@example.com',
        'role': 'user',
        'created_at': datetime.utcnow(),
        'is_active': True,
    },
}

# Token blacklist (in production, use Redis or database)
_token_blacklist = set()
_token_blacklist_lock = __import__('threading').Lock()


def _get_user_by_username(username: str):
    """Get user by username."""
    for user in _users_db.values():
        if user['username'] == username:
            return user
    return None


def _get_user_by_id(user_id: int):
    """Get user by ID."""
    return _users_db.get(user_id)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录，返回 JWT Token
    
    Request Body:
        {
            "username": "string",
            "password": "string",
            "remember_me": false  (optional, extends token expiry)
        }
    
    Response:
        {
            "success": true,
            "access_token": "eyJ...",
            "refresh_token": "eyJ...",
            "token_type": "Bearer",
            "expires_in": 1800,
            "user": {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin"
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        # Validate inputs
        if not username or not password:
            return jsonify({
                "success": False,
                "error": "用户名和密码不能为空",
            }), 400
        
        # Find user
        user = _get_user_by_username(username)
        
        if not user:
            logger.warning(f"登录失败：用户不存在 - {username}")
            return jsonify({
                "success": False,
                "error": "用户名或密码错误",
            }), 401
        
        # Check if user is active
        if not user.get('is_active', True):
            logger.warning(f"登录失败：账户已禁用 - {username}")
            return jsonify({
                "success": False,
                "error": "账户已被禁用，请联系管理员",
            }), 403
        
        # Verify password
        if not verify_password(password, user['password_hash']):
            logger.warning(f"登录失败：密码错误 - {username}")
            return jsonify({
                "success": False,
                "error": "用户名或密码错误",
            }), 401
        
        # Create tokens
        token_data = {
            'user_id': user['id'],
            'username': user['username'],
            'email': user.get('email'),
            'role': user.get('role', 'user'),
        }
        
        # Extended expiry for remember me
        if remember_me:
            access_expires = timedelta(days=7)
            refresh_expires = timedelta(days=30)
        else:
            access_expires = None  # Use default
            refresh_expires = None
        
        access_token = create_access_token(token_data, expires_delta=access_expires)
        refresh_token_str = create_refresh_token(token_data)
        
        logger.info(f"用户登录成功：{username} (ID: {user['id']})")
        
        return jsonify({
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "Bearer",
            "expires_in": 1800 if not remember_me else 604800,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user.get('email'),
                "role": user.get('role', 'user'),
            }
        }), 200
        
    except Exception as e:
        logger.error(f"登录异常：{e}")
        return jsonify({
            "success": False,
            "error": f"登录失败：{str(e)}",
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    用户登出，加入 Token 黑名单
    
    Requires: Bearer token in Authorization header
    
    Response:
        {
            "success": true,
            "message": "已成功登出"
        }
    """
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if token:
            # Blacklist the token
            blacklist_token(token)
            logger.info(f"用户登出：{request.current_user.get('username')}")
        
        return jsonify({
            "success": True,
            "message": "已成功登出",
        }), 200
        
    except Exception as e:
        logger.error(f"登出异常：{e}")
        return jsonify({
            "success": False,
            "error": f"登出失败：{str(e)}",
        }), 500


@auth_bp.route('/token/refresh', methods=['POST'])
def refresh_token_endpoint():
    """
    刷新 Token
    
    Request Body:
        {
            "refresh_token": "eyJ..."
        }
    
    Response:
        {
            "success": true,
            "access_token": "eyJ...",
            "refresh_token": "eyJ...",
            "token_type": "Bearer",
            "expires_in": 1800
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'refresh_token' not in data:
            return jsonify({
                "success": False,
                "error": "缺少 refresh_token",
            }), 400
        
        refresh_token_str = data['refresh_token']
        
        # Verify refresh token
        try:
            payload = verify_token(refresh_token_str)
            
            # Check token type
            if payload.get('type') != 'refresh':
                return jsonify({
                    "success": False,
                    "error": "无效的 token 类型",
                }), 400
            
            # Create new tokens
            token_data = {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'email': payload.get('email'),
                'role': payload.get('role'),
            }
            
            new_access_token = create_access_token(token_data)
            new_refresh_token = create_refresh_token(token_data)
            
            # Blacklist old refresh token
            blacklist_token(refresh_token_str)
            
            logger.info(f"Token 刷新成功：用户 {payload.get('username')}")
            
            return jsonify({
                "success": True,
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "Bearer",
                "expires_in": 1800,
            }), 200
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Token 验证失败：{str(e)}",
            }), 401
        
    except Exception as e:
        logger.error(f"Token 刷新异常：{e}")
        return jsonify({
            "success": False,
            "error": f"Token 刷新失败：{str(e)}",
        }), 500


@auth_bp.route('/token/revoke', methods=['POST'])
@require_auth
def revoke_token():
    """
    撤销 Token (使所有当前 token 失效)
    
    Requires: Bearer token in Authorization header
    
    Response:
        {
            "success": true,
            "message": "Token 已撤销"
        }
    """
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        current_user = request.current_user
        
        if token:
            blacklist_token(token)
        
        logger.info(f"Token 撤销：用户 {current_user.get('username')}")
        
        return jsonify({
            "success": True,
            "message": "Token 已撤销，请重新登录",
        }), 200
        
    except Exception as e:
        logger.error(f"Token 撤销异常：{e}")
        return jsonify({
            "success": False,
            "error": f"Token 撤销失败：{str(e)}",
        }), 500


@auth_bp.route('/api-keys', methods=['GET'])
@require_auth
@require_permission('api:read')
def list_api_keys():
    """
    获取 API Key 列表
    
    Requires: Bearer token with api:read permission
    
    Response:
        {
            "success": true,
            "count": 2,
            "keys": [
                {
                    "id": "abc123",
                    "name": "Production Key",
                    "permissions": ["api:read", "api:write"],
                    "created_at": "2024-01-01T00:00:00",
                    "expires_at": null,
                    "rate_limit": 1000,
                    "is_active": true,
                    "last_used": "2024-01-15T10:30:00",
                    "usage_count": 1500
                }
            ]
        }
    """
    try:
        current_user = request.current_user
        user_id = current_user.get('user_id')
        
        manager = get_api_key_manager()
        keys = manager.list_keys(user_id)
        
        return jsonify({
            "success": True,
            "count": len(keys),
            "keys": keys,
        }), 200
        
    except Exception as e:
        logger.error(f"获取 API Key 列表异常：{e}")
        return jsonify({
            "success": False,
            "error": f"获取 API Key 列表失败：{str(e)}",
        }), 500


@auth_bp.route('/api-keys', methods=['POST'])
@require_auth
@require_permission('api:write')
def create_api_key():
    """
    创建新 API Key
    
    Requires: Bearer token with api:write permission
    
    Request Body:
        {
            "name": "Production Key",
            "permissions": ["api:read", "api:write"],
            "expires_in_days": 365,
            "rate_limit": 1000
        }
    
    Response:
        {
            "success": true,
            "key": {
                "id": "abc123",
                "key": "sk_xxxxx...",  // Only shown once!
                "name": "Production Key",
                "permissions": ["api:read", "api:write"],
                "created_at": "2024-01-01T00:00:00",
                "expires_at": "2025-01-01T00:00:00",
                "rate_limit": 1000
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
            }), 400
        
        name = data.get('name')
        permissions = data.get('permissions', ['api:read'])
        expires_in_days = data.get('expires_in_days')
        rate_limit = data.get('rate_limit')
        
        if not name:
            return jsonify({
                "success": False,
                "error": "API Key 名称不能为空",
            }), 400
        
        current_user = request.current_user
        user_id = current_user.get('user_id')
        
        manager = get_api_key_manager()
        key_info = manager.generate_key(
            user_id=user_id,
            name=name,
            permissions=permissions,
            expires_in_days=expires_in_days,
            rate_limit=rate_limit,
        )
        
        logger.info(f"API Key 创建：用户 {current_user.get('username')} 创建了 {name}")
        
        return jsonify({
            "success": True,
            "key": key_info,
            "warning": "请安全保存此 API Key，它只会显示一次！",
        }), 201
        
    except Exception as e:
        logger.error(f"创建 API Key 异常：{e}")
        return jsonify({
            "success": False,
            "error": f"创建 API Key 失败：{str(e)}",
        }), 500


@auth_bp.route('/api-keys/<key_id>', methods=['PUT'])
@require_auth
@require_permission('api:write')
def rotate_api_key(key_id):
    """
    轮换 API Key (撤销旧 Key，创建新 Key)
    
    Requires: Bearer token with api:write permission
    
    Request Body (optional):
        {
            "name": "New Key Name"
        }
    
    Response:
        {
            "success": true,
            "key": {
                "id": "def456",
                "key": "sk_yyyyy...",  // New key, only shown once!
                "name": "New Key Name",
                ...
            },
            "old_key_id": "abc123"
        }
    """
    try:
        data = request.get_json() or {}
        new_name = data.get('name')
        
        current_user = request.current_user
        user_id = current_user.get('user_id')
        
        manager = get_api_key_manager()
        new_key = manager.rotate_key(user_id, key_id, new_name)
        
        if not new_key:
            return jsonify({
                "success": False,
                "error": "API Key 不存在或无权操作",
            }), 404
        
        logger.info(f"API Key 轮换：用户 {current_user.get('username')} 轮换了 Key {key_id}")
        
        return jsonify({
            "success": True,
            "key": new_key,
            "old_key_id": key_id,
            "warning": "旧 API Key 已撤销，请立即更新使用新 Key！",
        }), 200
        
    except Exception as e:
        logger.error(f"轮换 API Key 异常：{e}")
        return jsonify({
            "success": False,
            "error": f"轮换 API Key 失败：{str(e)}",
        }), 500


@auth_bp.route('/api-keys/<key_id>', methods=['DELETE'])
@require_auth
@require_permission('api:write')
def revoke_api_key(key_id):
    """
    撤销 API Key
    
    Requires: Bearer token with api:write permission
    
    Response:
        {
            "success": true,
            "message": "API Key 已撤销"
        }
    """
    try:
        current_user = request.current_user
        user_id = current_user.get('user_id')
        
        manager = get_api_key_manager()
        success = manager.revoke_key(user_id, key_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": "API Key 不存在或无权操作",
            }), 404
        
        logger.info(f"API Key 撤销：用户 {current_user.get('username')} 撤销了 Key {key_id}")
        
        return jsonify({
            "success": True,
            "message": "API Key 已撤销",
        }), 200
        
    except Exception as e:
        logger.error(f"撤销 API Key 异常：{e}")
        return jsonify({
            "success": False,
            "error": f"撤销 API Key 失败：{str(e)}",
        }), 500


@auth_bp.route('/api-keys/<key_id>/usage', methods=['GET'])
@require_auth
@require_permission('api:read')
def get_key_usage(key_id):
    """
    获取 Key 使用统计
    
    Requires: Bearer token with api:read permission
    
    Response:
        {
            "success": true,
            "usage": {
                "key_id": "abc123",
                "total_requests": 1500,
                "requests_last_hour": 50,
                "requests_last_day": 800,
                "requests_last_week": 1500,
                "success_rate": 100.0
            }
        }
    """
    try:
        current_user = request.current_user
        user_id = current_user.get('user_id')
        
        manager = get_api_key_manager()
        usage = manager.get_usage_stats(user_id, key_id)
        
        if 'error' in usage:
            return jsonify({
                "success": False,
                "error": usage['error'],
            }), 404
        
        return jsonify({
            "success": True,
            "usage": usage,
        }), 200
        
    except Exception as e:
        logger.error(f"获取 Key 使用统计异常：{e}")
        return jsonify({
            "success": False,
            "error": f"获取 Key 使用统计失败：{str(e)}",
        }), 500


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """
    获取当前用户信息
    
    Requires: Bearer token in Authorization header
    
    Response:
        {
            "success": true,
            "user": {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin",
                "permissions": ["user:read", "user:write", ...]
            }
        }
    """
    try:
        current_user = request.current_user
        user_id = current_user.get('user_id')
        
        # Get full user data
        user = _get_user_by_id(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "error": "用户不存在",
            }), 404
        
        # Get permissions
        perm_manager = get_permission_manager()
        permissions = perm_manager.get_user_permissions(user_id)
        
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user.get('email'),
                "role": user.get('role', 'user'),
                "permissions": permissions,
                "created_at": user.get('created_at').isoformat() if user.get('created_at') else None,
            }
        }), 200
        
    except Exception as e:
        logger.error(f"获取用户信息异常：{e}")
        return jsonify({
            "success": False,
            "error": f"获取用户信息失败：{str(e)}",
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    用户注册
    
    Request Body:
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123!"
        }
    
    Response:
        {
            "success": true,
            "message": "注册成功",
            "user": {
                "id": 3,
                "username": "newuser",
                "email": "newuser@example.com",
                "role": "user"
            }
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空",
            }), 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # Validate inputs
        if not username or not email or not password:
            return jsonify({
                "success": False,
                "error": "用户名、邮箱和密码不能为空",
            }), 400
        
        # Validate password strength
        is_valid, issues = validate_password_strength(password)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": "密码强度不足",
                "issues": issues,
            }), 400
        
        # Check if username exists
        if _get_user_by_username(username):
            return jsonify({
                "success": False,
                "error": "用户名已存在",
            }), 409
        
        # Generate new user ID
        new_user_id = max(_users_db.keys()) + 1
        
        # Hash password
        from src.auth.password import hash_password
        password_hash = hash_password(password)
        
        # Create user
        new_user = {
            'id': new_user_id,
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'role': 'user',
            'created_at': datetime.utcnow(),
            'is_active': True,
        }
        
        _users_db[new_user_id] = new_user
        
        logger.info(f"用户注册成功：{username} (ID: {new_user_id})")
        
        return jsonify({
            "success": True,
            "message": "注册成功",
            "user": {
                "id": new_user['id'],
                "username": new_user['username'],
                "email": new_user['email'],
                "role": new_user['role'],
            }
        }), 201
        
    except Exception as e:
        logger.error(f"用户注册异常：{e}")
        return jsonify({
            "success": False,
            "error": f"注册失败：{str(e)}",
        }), 500


@auth_bp.route('/health', methods=['GET'])
def health_check():
    """
    认证服务健康检查
    
    Response:
        {
            "success": true,
            "status": "healthy",
            "timestamp": "2024-01-15T10:30:00"
        }
    """
    return jsonify({
        "success": True,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }), 200
