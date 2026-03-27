"""
Database models for Amazon Selector v2.2
"""
from .base import Base, TimestampMixin, SoftDeleteMixin
from .product import Product, ProductImage, ProductFeature
from .history import ProductHistory, PriceHistory, BSRHistory

# Alias for backwards compatibility
History = ProductHistory

__all__ = [
    'Base',
    'TimestampMixin',
    'SoftDeleteMixin',
    'Product',
    'ProductImage',
    'ProductFeature',
    'ProductHistory',
    'PriceHistory',
    'BSRHistory',
    'History',
]
