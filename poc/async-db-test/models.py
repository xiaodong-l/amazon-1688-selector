"""
SQLAlchemy 2.0 Async ORM Models for POC Testing
验证异步模型定义语法和兼容性
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Product(Base):
    """
    Product 异步模型 - 使用 SQLAlchemy 2.0 异步 ORM
    验证模型定义语法
    """
    __tablename__ = 'products'

    # SQLAlchemy 2.0 风格映射
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default='USD')
    category: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=True)
    sku: Mapped[str] = mapped_column(String(50), nullable=True, unique=True, index=True)
    
    # 库存相关
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"

    def to_dict(self):
        """转换为字典，便于 JSON 序列化"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'currency': self.currency,
            'category': self.category,
            'brand': self.brand,
            'sku': self.sku,
            'stock_quantity': self.stock_quantity,
            'is_available': self.is_available,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
