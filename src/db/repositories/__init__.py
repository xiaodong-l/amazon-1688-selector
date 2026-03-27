"""
Database repositories for Amazon Selector v2.2

Provides data access layer for database operations.
"""
from .product_repo import ProductRepository
from .history_repo import HistoryRepository

__all__ = [
    'ProductRepository',
    'HistoryRepository',
]
