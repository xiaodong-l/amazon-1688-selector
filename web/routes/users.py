"""
User Management API Routes for Amazon Selector v2.4

Provides REST endpoints for user CRUD operations and permission management.
"""
from flask import Blueprint, request, jsonify, Response
from typing import Dict, Any, Optional
import logging
from functools import wraps

from src.auth.jwt import verify_token
from src.auth.permissions import PermissionManager, get_permission_manager

logger = logging.getLogger(__name__)

# Create blueprint
users_bp = Blueprint('users', __name__, url_prefix='/api/v2/users')


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'Authorization header required',
            }), 401
        
        try:
            # Extract token from "Bearer <token>"
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return jsonify({
                    'error': 'Invalid authorization header format',
                }), 401
            
            token = parts[1]
            payload = verify_token(token)
            
            # Attach user info to request
            request.current_user = {
                'id': payload.get('user_id'),
                'username': payload.get('username'),
                'role': payload.get('role', 'user'),
            }
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return jsonify({
                'error': 'Invalid or expired token',
                'message': str(e),
            }), 401
        
        return f(*args, **kwargs)
    return decorated


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            user = request.current_user
            manager = get_permission_manager()
            
            if not manager.check_permission(user, permission):
                return jsonify({
                    'error': 'Permission denied',
                    'message': f"User lacks required permission: {permission}",
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator


# ==================== User CRUD Endpoints ====================

@users_bp.route('', methods=['GET'])
@require_permission('user:read')
def list_users() -> Response:
    """
    Get list of all users.
    
    Query parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - search: Search by username or email
        - role: Filter by role
        - status: Filter by status (active/inactive)
    
    Returns:
        JSON response with users list and pagination info
    """
    try:
        from src.db.connection import get_async_session
        from src.db.repositories.user_repo import UserRepository
        
        # Parse query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        search = request.args.get('search')
        role = request.args.get('role')
        status = request.args.get('status')
        
        offset = (page - 1) * per_page
        
        async def fetch_users():
            async with get_async_session() as session:
                repo = UserRepository(session)
                
                # Search
                if search:
                    users = await repo.search(search, limit=per_page)
                    total = len(users)
                else:
                    # Get all with pagination
                    users = await repo.get_all(limit=per_page, offset=offset)
                    total = await repo.count()
                
                # Filter by role
                if role and not search:
                    users = [u for u in users if u.get('role') == role]
                    total = len(users)
                
                # Filter by status
                if status and not search:
                    is_active = status.lower() == 'active'
                    users = [u for u in users if u.get('is_active') == is_active]
                    total = len(users)
                
                return users, total
        
        import asyncio
        users, total = asyncio.run(fetch_users())
        
        return jsonify({
            'users': users,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
            },
        })
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({
            'error': 'Failed to list users',
            'message': str(e),
        }), 500


@users_bp.route('', methods=['POST'])
@require_permission('user:create')
def create_user() -> Response:
    """
    Create a new user.
    
    Request body:
        - username: str (required)
        - email: str (required)
        - password: str (required)
        - role: str (optional, default: 'user')
        - is_active: bool (optional, default: True)
    
    Returns:
        JSON response with created user
    """
    try:
        from src.db.connection import get_async_session
        from src.db.repositories.user_repo import UserRepository
        from src.auth.password import hash_password
        
        data = request.get_json()
        
        # Validate required fields
        required = ['username', 'email', 'password']
        for field in required:
            if not data.get(field):
                return jsonify({
                    'error': f'Missing required field: {field}',
                }), 400
        
        # Validate email format
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, data.get('email', '')):
            return jsonify({
                'error': 'Invalid email format',
            }), 400
        
        # Validate password strength
        password = data.get('password', '')
        if len(password) < 8:
            return jsonify({
                'error': 'Password must be at least 8 characters',
            }), 400
        
        # Hash password
        password_hash = hash_password(password)
        
        # Prepare user data
        user_data = {
            'username': data['username'],
            'email': data['email'],
            'password_hash': password_hash,
            'role': data.get('role', 'user'),
            'is_active': data.get('is_active', True),
        }
        
        async def create():
            async with get_async_session() as session:
                repo = UserRepository(session)
                user_id = await repo.create(user_data)
                
                # Get created user
                user = await repo.get_by_id(user_id)
                return user
        
        import asyncio
        user = asyncio.run(create())
        
        # Remove sensitive data
        user.pop('password_hash', None)
        
        logger.info(f"User created: {user['username']} by {request.current_user['username']}")
        
        return jsonify({
            'user': user,
            'message': 'User created successfully',
        }), 201
        
    except ValueError as e:
        return jsonify({
            'error': str(e),
        }), 400
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({
            'error': 'Failed to create user',
            'message': str(e),
        }), 500


@users_bp.route('/<int:user_id>', methods=['GET'])
@require_permission('user:read')
def get_user(user_id: int) -> Response:
    """
    Get user details by ID.
    
    Args:
        user_id: User ID
        
    Returns:
        JSON response with user details
    """
    try:
        from src.db.connection import get_async_session
        from src.db.repositories.user_repo import UserRepository
        
        async def fetch():
            async with get_async_session() as session:
                repo = UserRepository(session)
                user = await repo.get_by_id(user_id)
                return user
        
        import asyncio
        user = asyncio.run(fetch())
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'user_id': user_id,
            }), 404
        
        # Remove sensitive data
        user.pop('password_hash', None)
        
        return jsonify({
            'user': user,
        })
        
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to get user',
            'message': str(e),
        }), 500


@users_bp.route('/<int:user_id>', methods=['PUT'])
@require_permission('user:update')
def update_user(user_id: int) -> Response:
    """
    Update user information.
    
    Args:
        user_id: User ID
        
    Request body (all optional):
        - username: str
        - email: str
        - role: str
        - is_active: bool
    
    Returns:
        JSON response with updated user
    """
    try:
        from src.db.connection import get_async_session
        from src.db.repositories.user_repo import UserRepository
        
        data = request.get_json()
        
        # Validate email if provided
        if 'email' in data:
            import re
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, data['email']):
                return jsonify({
                    'error': 'Invalid email format',
                }), 400
        
        # Validate role if provided
        if 'role' in data:
            valid_roles = ['admin', 'user', 'readonly']
            if data['role'] not in valid_roles:
                return jsonify({
                    'error': f'Invalid role. Must be one of: {valid_roles}',
                }), 400
        
        async def update():
            async with get_async_session() as session:
                repo = UserRepository(session)
                success = await repo.update(user_id, data)
                
                if success:
                    user = await repo.get_by_id(user_id)
                    return user
                return None
        
        import asyncio
        user = asyncio.run(update())
        
        if not user:
            return jsonify({
                'error': 'User not found',
                'user_id': user_id,
            }), 404
        
        # Remove sensitive data
        user.pop('password_hash', None)
        
        logger.info(f"User updated: {user['username']} by {request.current_user['username']}")
        
        return jsonify({
            'user': user,
            'message': 'User updated successfully',
        })
        
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to update user',
            'message': str(e),
        }), 500


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@require_permission('user:delete')
def delete_user(user_id: int) -> Response:
    """
    Delete a user (soft delete).
    
    Args:
        user_id: User ID
        
    Returns:
        JSON response with success message
    """
    try:
        from src.db.connection import get_async_session
        from src.db.repositories.user_repo import UserRepository
        
        # Prevent self-deletion
        if user_id == request.current_user['id']:
            return jsonify({
                'error': 'Cannot delete your own account',
            }), 400
        
        async def delete():
            async with get_async_session() as session:
                repo = UserRepository(session)
                return await repo.delete(user_id)
        
        import asyncio
        success = asyncio.run(delete())
        
        if not success:
            return jsonify({
                'error': 'User not found',
                'user_id': user_id,
            }), 404
        
        logger.info(f"User deleted: ID {user_id} by {request.current_user['username']}")
        
        return jsonify({
            'message': 'User deleted successfully',
            'user_id': user_id,
        })
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to delete user',
            'message': str(e),
        }), 500


# ==================== Password Management ====================

@users_bp.route('/<int:user_id>/password', methods=['POST'])
@require_permission('user:update')
def change_password(user_id: int) -> Response:
    """
    Change user password.
    
    Args:
        user_id: User ID
        
    Request body:
        - current_password: str (required for non-admin)
        - new_password: str (required)
    
    Returns:
        JSON response with success message
    """
    try:
        from src.db.connection import get_async_session
        from src.db.repositories.user_repo import UserRepository
        from src.auth.password import hash_password, verify_password
        
        data = request.get_json()
        
        # Validate new password
        new_password = data.get('new_password')
        if not new_password or len(new_password) < 8:
            return jsonify({
                'error': 'New password must be at least 8 characters',
            }), 400
        
        async def change():
            async with get_async_session() as session:
                repo = UserRepository(session)
                user = await repo.get_by_id(user_id)
                
                if not user:
                    return None, 'User not found'
                
                # Non-admin users must provide current password
                if request.current_user['role'] != 'admin':
                    current_password = data.get('current_password')
                    if not current_password:
                        return None, 'Current password required'
                    
                    # Verify current password (need to check against stored hash)
                    # This requires accessing the raw user model
                    from src.db.models.user import User
                    from sqlalchemy import select
                    stmt = select(User).where(User.id == user_id)
                    result = await session.execute(stmt)
                    db_user = result.scalar_one_or_none()
                    
                    if not db_user or not verify_password(current_password, db_user.password_hash):
                        return None, 'Current password is incorrect'
                
                # Hash new password
                password_hash = hash_password(new_password)
                
                # Update
                success = await repo.update(user_id, {'password_hash': password_hash})
                
                if success:
                    updated_user = await repo.get_by_id(user_id)
                    return updated_user, None
                return None, 'Failed to update password'
        
        import asyncio
        user, error = asyncio.run(change())
        
        if error:
            if error == 'User not found':
                return jsonify({'error': error}), 404
            return jsonify({'error': error}), 400
        
        logger.info(f"Password changed for user {user['username']} by {request.current_user['username']}")
        
        return jsonify({
            'message': 'Password changed successfully',
        })
        
    except Exception as e:
        logger.error(f"Error changing password for user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to change password',
            'message': str(e),
        }), 500


# ==================== Permission Management ====================

@users_bp.route('/<int:user_id>/permissions', methods=['GET'])
@require_permission('user:read')
def get_permissions(user_id: int) -> Response:
    """
    Get user permissions.
    
    Args:
        user_id: User ID
        
    Returns:
        JSON response with permissions list
    """
    try:
        manager = get_permission_manager()
        permissions = manager.get_user_permissions(user_id)
        role = manager.get_user_role(user_id)
        
        return jsonify({
            'user_id': user_id,
            'role': role,
            'permissions': permissions,
        })
        
    except Exception as e:
        logger.error(f"Error getting permissions for user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to get permissions',
            'message': str(e),
        }), 500


@users_bp.route('/<int:user_id>/permissions', methods=['POST'])
@require_permission('user:update')
def assign_permission(user_id: int) -> Response:
    """
    Assign permission or role to user.
    
    Args:
        user_id: User ID
        
    Request body:
        - permission: str (optional) - Permission to assign
        - role: str (optional) - Role to assign
        
    Returns:
        JSON response with updated permissions
    """
    try:
        from src.db.connection import get_async_session
        from src.db.repositories.user_repo import UserRepository
        
        data = request.get_json()
        manager = get_permission_manager()
        
        # Assign role
        if 'role' in data:
            role = data['role']
            valid_roles = ['admin', 'user', 'readonly']
            
            if role not in valid_roles:
                return jsonify({
                    'error': f'Invalid role. Must be one of: {valid_roles}',
                }), 400
            
            # Update in database
            async def update_role():
                async with get_async_session() as session:
                    repo = UserRepository(session)
                    success = await repo.update(user_id, {'role': role})
                    return success
            
            import asyncio
            asyncio.run(update_role())
            
            # Update in permission manager
            manager.assign_role(user_id, role)
        
        # Assign specific permission
        if 'permission' in data:
            permission = data['permission']
            manager.assign_permission(user_id, permission)
        
        # Get updated permissions
        permissions = manager.get_user_permissions(user_id)
        role = manager.get_user_role(user_id)
        
        logger.info(f"Permissions updated for user {user_id} by {request.current_user['username']}")
        
        return jsonify({
            'user_id': user_id,
            'role': role,
            'permissions': permissions,
            'message': 'Permissions updated successfully',
        })
        
    except Exception as e:
        logger.error(f"Error assigning permission to user {user_id}: {e}")
        return jsonify({
            'error': 'Failed to assign permission',
            'message': str(e),
        }), 500


def init_user_routes(app) -> None:
    """
    Initialize user routes with Flask app.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(users_bp)
    logger.info("User routes initialized")
