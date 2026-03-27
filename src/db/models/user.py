"""
User model for Amazon Selector v2.4

Defines User model for authentication and authorization.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    User model for storing user account data.
    
    Table: users
    
    Attributes:
        id: Primary key
        username: Unique username
        email: Unique email address
        password_hash: Hashed password
        role: User role (admin/user/readonly)
        is_active: Whether account is active
        last_login: Last login timestamp
        login_count: Total login count
        deleted_at: Soft delete timestamp
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'login_count': self.login_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_safe_dict(self) -> dict:
        """Convert model to dictionary without sensitive data."""
        data = self.to_dict()
        # Remove sensitive fields
        data.pop('password_hash', None)
        return data
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class APIKey(Base, TimestampMixin):
    """
    API Key model for storing user API keys.
    
    Table: api_keys
    
    Attributes:
        id: Primary key
        user_id: Foreign key to users
        name: Key name/description
        key_hash: Hashed API key
        prefix: Key prefix for identification (first 8 chars)
        scopes: JSON-encoded list of scopes
        expires_at: Expiration timestamp
        is_active: Whether key is active
        last_used: Last usage timestamp
    """
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False)
    prefix = Column(String(8), nullable=False)
    scopes = Column(Text, nullable=True)  # JSON-encoded list
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used = Column(DateTime, nullable=True)
    
    # Foreign key
    user_id = Column(Integer, nullable=False)
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'prefix': self.prefix,
            'scopes': self.scopes,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, prefix='{self.prefix}', name='{self.name}')>"
