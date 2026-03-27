"""
Base model and mixins for Amazon Selector v2.2

Provides common functionality for all database models.
"""
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime
from typing import Optional

# Declarative base for all models
Base = declarative_base()


class TimestampMixin:
    """
    Mixin for adding timestamp fields to models.
    
    Adds:
        - created_at: When the record was created
        - updated_at: When the record was last updated
    """
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    
    Adds:
        - is_deleted: Flag to mark records as deleted
        - deleted_at: When the record was deleted
    
    Usage:
        class MyModel(Base, SoftDeleteMixin):
            __tablename__ = 'my_table'
            id = Column(Integer, primary_key=True)
    """
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    def soft_delete(self):
        """Mark this record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
