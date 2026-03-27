"""
User Repository for Amazon Selector v2.4

Provides CRUD operations for User models.
"""
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class UserRepository:
    """
    Repository for User data access.
    
    Provides methods for creating, reading, updating, and deleting users.
    Thread-safe and async-compatible design.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all users with pagination.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of user dictionaries
        """
        from src.db.models.user import User
        
        try:
            stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
            result = await self.session.execute(stmt)
            users = result.scalars().all()
            
            return [user.to_dict() for user in users]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            raise
    
    async def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User dictionary or None if not found
        """
        from src.db.models.user import User
        
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            return user.to_dict() if user else None
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            raise
    
    async def create(self, user_data: Dict[str, Any]) -> int:
        """
        Create a new user.
        
        Args:
            user_data: Dictionary with user data:
                - username: str (required)
                - email: str (required)
                - password_hash: str (required)
                - role: str (optional, default: 'user')
                - is_active: bool (optional, default: True)
                
        Returns:
            Created user ID
            
        Raises:
            ValueError: If username or email already exists
        """
        from src.db.models.user import User
        
        try:
            # Check if username exists
            existing_user = await self.get_by_username(user_data.get('username', ''))
            if existing_user:
                raise ValueError(f"Username '{user_data.get('username')}' already exists")
            
            # Create user
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data.get('role', 'user'),
                is_active=user_data.get('is_active', True),
            )
            
            self.session.add(user)
            await self.session.flush()  # Get the ID
            await self.session.commit()
            
            logger.info(f"User created: {user.username} (ID: {user.id})")
            return user.id
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating user: {e}")
            raise
    
    async def update(self, user_id: int, user_data: Dict[str, Any]) -> bool:
        """
        Update an existing user.
        
        Args:
            user_id: User ID to update
            user_data: Dictionary with fields to update:
                - username: str (optional)
                - email: str (optional)
                - role: str (optional)
                - is_active: bool (optional)
                
        Returns:
            True if successfully updated, False if user not found
        """
        from src.db.models.user import User
        
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Update fields
            if 'username' in user_data:
                user.username = user_data['username']
            if 'email' in user_data:
                user.email = user_data['email']
            if 'role' in user_data:
                user.role = user_data['role']
            if 'is_active' in user_data:
                user.is_active = user_data['is_active']
            if 'password_hash' in user_data:
                user.password_hash = user_data['password_hash']
            
            user.updated_at = datetime.utcnow()
            
            await self.session.commit()
            logger.info(f"User updated: {user.username} (ID: {user.id})")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating user {user_id}: {e}")
            raise
    
    async def delete(self, user_id: int) -> bool:
        """
        Delete a user (soft delete).
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if successfully deleted, False if user not found
        """
        from src.db.models.user import User
        
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Soft delete
            user.is_active = False
            user.deleted_at = datetime.utcnow()
            
            await self.session.commit()
            logger.info(f"User deleted: {user.username} (ID: {user.id})")
            return True
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise
    
    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User dictionary or None if not found
        """
        from src.db.models.user import User
        
        try:
            stmt = select(User).where(User.username == username)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            return user.to_dict() if user else None
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            raise
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email.
        
        Args:
            email: Email to search for
            
        Returns:
            User dictionary or None if not found
        """
        from src.db.models.user import User
        
        try:
            stmt = select(User).where(User.email == email)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            return user.to_dict() if user else None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise
    
    async def count(self) -> int:
        """
        Get total user count.
        
        Returns:
            Number of users
        """
        from src.db.models.user import User
        
        try:
            stmt = select(func.count(User.id))
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            raise
    
    async def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search users by username or email.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching user dictionaries
        """
        from src.db.models.user import User
        
        try:
            search_pattern = f"%{query}%"
            stmt = select(User).where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            ).order_by(User.username).limit(limit)
            
            result = await self.session.execute(stmt)
            users = result.scalars().all()
            
            return [user.to_dict() for user in users]
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            raise
    
    async def get_active_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all active users.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of active user dictionaries
        """
        from src.db.models.user import User
        
        try:
            stmt = select(User).where(
                and_(User.is_active == True, User.deleted_at.is_(None))
            ).order_by(User.username).limit(limit)
            
            result = await self.session.execute(stmt)
            users = result.scalars().all()
            
            return [user.to_dict() for user in users]
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            raise
