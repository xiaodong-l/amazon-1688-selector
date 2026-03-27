"""
History models for Amazon Selector v2.2

Defines ProductHistory, PriceHistory, and BSRHistory models for tracking changes over time.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class ProductHistory(Base):
    """
    Product history model for storing snapshots of product data over time.
    
    Table: product_history
    
    Attributes:
        id: Primary key
        product_id: Foreign key to products
        asin: Product ASIN for easy querying
        title: Product title at this point in time
        price: Price at this point in time
        rating: Rating at this point in time
        review_count: Review count at this point in time
        bsr: BSR at this point in time
        recorded_at: When this data point was recorded
        created_at: Record creation timestamp
    """
    __tablename__ = 'product_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    asin = Column(String(20), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    price = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0, nullable=True)
    bsr = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="history")
    
    # Indexes for efficient time-series queries
    __table_args__ = (
        Index('idx_product_history_asin_recorded', 'asin', 'recorded_at'),
        Index('idx_product_history_product_recorded', 'product_id', 'recorded_at'),
        Index('idx_product_history_recorded', 'recorded_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'asin': self.asin,
            'title': self.title,
            'price': self.price,
            'rating': self.rating,
            'review_count': self.review_count,
            'bsr': self.bsr,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ProductHistory(asin='{self.asin}', recorded_at='{self.recorded_at}')>"


class PriceHistory(Base):
    """
    Price history model for tracking price changes specifically.
    
    Table: price_history
    
    Attributes:
        id: Primary key
        product_id: Foreign key to products
        asin: Product ASIN for easy querying
        price: Price at this point in time
        currency: Currency code
        recorded_at: When this price was recorded
        created_at: Record creation timestamp
    """
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    asin = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default='USD', nullable=True)
    recorded_at = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes for efficient time-series queries
    __table_args__ = (
        Index('idx_price_history_asin_recorded', 'asin', 'recorded_at'),
        Index('idx_price_history_recorded', 'recorded_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'asin': self.asin,
            'price': self.price,
            'currency': self.currency,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<PriceHistory(asin='{self.asin}', price={self.price}, recorded_at='{self.recorded_at}')>"


class BSRHistory(Base):
    """
    BSR (Best Sellers Rank) history model for tracking rank changes.
    
    Table: bsr_history
    
    Attributes:
        id: Primary key
        product_id: Foreign key to products
        asin: Product ASIN for easy querying
        bsr: Best Sellers Rank at this point in time
        bsr_category: Category for this BSR
        recorded_at: When this BSR was recorded
        created_at: Record creation timestamp
    """
    __tablename__ = 'bsr_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    asin = Column(String(20), nullable=False, index=True)
    bsr = Column(Integer, nullable=False)
    bsr_category = Column(String(300), nullable=True)
    recorded_at = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes for efficient time-series queries
    __table_args__ = (
        Index('idx_bsr_history_asin_recorded', 'asin', 'recorded_at'),
        Index('idx_bsr_history_recorded', 'recorded_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'asin': self.asin,
            'bsr': self.bsr,
            'bsr_category': self.bsr_category,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<BSRHistory(asin='{self.asin}', bsr={self.bsr}, recorded_at='{self.recorded_at}')>"
