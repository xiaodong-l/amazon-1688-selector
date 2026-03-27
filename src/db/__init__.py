"""
Database module for Amazon Selector v2.2

Provides models, repositories, and connection management.
"""
from .models import (
    Base,
    Product,
    ProductImage,
    ProductFeature,
    ProductHistory,
    PriceHistory,
    BSRHistory,
)
from .repositories import ProductRepository, HistoryRepository
from .connection import (
    get_engine,
    get_async_engine,
    get_session,
    get_async_session,
    init_db,
    init_db_async,
    drop_db,
    drop_db_async,
    reset_db,
    reset_db_async,
    close_all,
    close_all_async,
    AsyncSessionLocal,
)

__all__ = [
    # Models
    'Base',
    'Product',
    'ProductImage',
    'ProductFeature',
    'ProductHistory',
    'PriceHistory',
    'BSRHistory',
    # Repositories
    'ProductRepository',
    'HistoryRepository',
    # Connection
    'get_engine',
    'get_async_engine',
    'get_session',
    'get_async_session',
    'init_db',
    'AsyncSessionLocal',
]
