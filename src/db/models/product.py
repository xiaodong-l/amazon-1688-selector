"""
Product models for Amazon Selector v2.2

Defines Product, ProductImage, and ProductFeature models.
"""
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin, SoftDeleteMixin


class Product(Base, TimestampMixin, SoftDeleteMixin):
    """
    Product model for storing Amazon product data.
    
    Table: products
    
    Attributes:
        id: Primary key
        asin: Amazon Standard Identification Number (unique)
        title: Product title
        brand: Product brand
        category: Product category
        price: Current price
        currency: Currency code (USD, EUR, etc.)
        rating: Average rating (0-5)
        review_count: Number of reviews
        bsr: Best Sellers Rank
        bsr_category: BSR category
        availability: Whether product is available
        prime_eligible: Whether product is Prime eligible
        image_url: URL to main product image
        product_url: URL to Amazon product page
    """
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    brand = Column(String(200), nullable=True, index=True)
    category = Column(String(300), nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default='USD', nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0, nullable=True)
    bsr = Column(Integer, nullable=True, index=True)
    bsr_category = Column(String(300), nullable=True)
    availability = Column(Boolean, default=True, nullable=True)
    prime_eligible = Column(Boolean, default=False, nullable=True)
    image_url = Column(String(500), nullable=True)
    product_url = Column(String(500), nullable=False)
    
    # Relationships
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    features = relationship("ProductFeature", back_populates="product", cascade="all, delete-orphan")
    history = relationship("ProductHistory", back_populates="product", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_products_price', 'price'),
        Index('idx_products_rating', 'rating'),
        Index('idx_products_created_at', 'created_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'asin': self.asin,
            'title': self.title,
            'brand': self.brand,
            'category': self.category,
            'price': self.price,
            'currency': self.currency,
            'rating': self.rating,
            'review_count': self.review_count,
            'bsr': self.bsr,
            'bsr_category': self.bsr_category,
            'availability': self.availability,
            'prime_eligible': self.prime_eligible,
            'image_url': self.image_url,
            'product_url': self.product_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<Product(asin='{self.asin}', title='{self.title[:50]}...')>"


class ProductImage(Base, TimestampMixin):
    """
    Product image model for storing multiple product images.
    
    Table: product_images
    
    Attributes:
        id: Primary key
        product_id: Foreign key to products
        image_url: URL to image
        position: Display order
        is_primary: Whether this is the main image
    """
    __tablename__ = 'product_images'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)
    position = Column(Integer, default=0, nullable=True)
    is_primary = Column(Boolean, default=False, nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="images")
    
    # Indexes
    __table_args__ = (
        Index('idx_product_images_position', 'product_id', 'position'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'image_url': self.image_url,
            'position': self.position,
            'is_primary': self.is_primary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ProductImage(product_id={self.product_id}, position={self.position})>"


class ProductFeature(Base, TimestampMixin):
    """
    Product feature model for storing product features/bullet points.
    
    Table: product_features
    
    Attributes:
        id: Primary key
        product_id: Foreign key to products
        feature_text: Feature description
        position: Display order
    """
    __tablename__ = 'product_features'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    feature_text = Column(Text, nullable=False)
    position = Column(Integer, default=0, nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="features")
    
    # Indexes
    __table_args__ = (
        Index('idx_product_features_position', 'product_id', 'position'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'feature_text': self.feature_text,
            'position': self.position,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ProductFeature(product_id={self.product_id}, position={self.position})>"
