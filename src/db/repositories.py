"""
Database Repositories for Amazon Selector v2.2

Implements repository pattern for Product and History data access.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .models import Product, History


class ProductRepository:
    """
    Repository for Product CRUD operations.
    
    Provides methods for creating, reading, updating, and deleting products,
    as well as complex queries.
    """
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session instance
        """
        self.session = session
    
    def create(self, product_data: Dict[str, Any]) -> Product:
        """
        Create a new product.
        
        Args:
            product_data: Dictionary with product fields
            
        Returns:
            Created Product instance
        """
        product = Product(**product_data)
        self.session.add(product)
        self.session.flush()  # Get ID without committing
        return product
    
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """
        Get product by ID.
        
        Args:
            product_id: Product primary key
            
        Returns:
            Product instance or None
        """
        return self.session.query(Product).filter(Product.id == product_id).first()
    
    def get_by_asin(self, asin: str) -> Optional[Product]:
        """
        Get product by ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            Product instance or None
        """
        return self.session.query(Product).filter(Product.asin == asin).first()
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """
        Get all products with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Product instances
        """
        return (
            self.session.query(Product)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def update(self, asin: str, update_data: Dict[str, Any]) -> Optional[Product]:
        """
        Update product by ASIN.
        
        Args:
            asin: Product ASIN
            update_data: Dictionary of fields to update
            
        Returns:
            Updated Product instance or None
        """
        product = self.get_by_asin(asin)
        if product:
            for key, value in update_data.items():
                if hasattr(product, key):
                    setattr(product, key, value)
            self.session.flush()
        return product
    
    def upsert(self, product_data: Dict[str, Any]) -> Product:
        """
        Update or insert product by ASIN.
        
        Args:
            product_data: Dictionary with product fields (must include asin)
            
        Returns:
            Product instance (new or updated)
        """
        asin = product_data.get('asin')
        if not asin:
            raise ValueError("ASIN is required for upsert")
        
        existing = self.get_by_asin(asin)
        if existing:
            return self.update(asin, product_data)
        else:
            return self.create(product_data)
    
    def delete(self, asin: str) -> bool:
        """
        Delete product by ASIN.
        
        Args:
            asin: Product ASIN
            
        Returns:
            True if deleted, False if not found
        """
        product = self.get_by_asin(asin)
        if product:
            self.session.delete(product)
            self.session.flush()
            return True
        return False
    
    def delete_by_id(self, product_id: int) -> bool:
        """
        Delete product by ID.
        
        Args:
            product_id: Product primary key
            
        Returns:
            True if deleted, False if not found
        """
        product = self.get_by_id(product_id)
        if product:
            self.session.delete(product)
            self.session.flush()
            return True
        return False
    
    def search(
        self,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        min_reviews: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Product]:
        """
        Search products with filters.
        
        Args:
            category: Filter by category
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_rating: Minimum rating filter
            min_reviews: Minimum review count filter
            limit: Maximum results
            offset: Results offset
            
        Returns:
            List of matching Product instances
        """
        query = self.session.query(Product)
        
        if category:
            query = query.filter(Product.category == category)
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        if min_rating is not None:
            query = query.filter(Product.rating >= min_rating)
        if min_reviews is not None:
            query = query.filter(Product.review_count >= min_reviews)
        
        return query.order_by(Product.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_top_products(
        self,
        by: str = 'rating',
        limit: int = 20,
        category: Optional[str] = None,
    ) -> List[Product]:
        """
        Get top products sorted by specified field.
        
        Args:
            by: Sort field ('rating', 'review_count', 'price', 'created_at')
            limit: Number of results
            category: Optional category filter
            
        Returns:
            List of top Product instances
        """
        query = self.session.query(Product)
        
        if category:
            query = query.filter(Product.category == category)
        
        sort_field = {
            'rating': Product.rating,
            'review_count': Product.review_count,
            'price': Product.price,
            'created_at': Product.created_at,
        }.get(by, Product.rating)
        
        return query.filter(sort_field.isnot(None)).order_by(desc(sort_field)).limit(limit).all()
    
    def count(self) -> int:
        """
        Get total product count.
        
        Returns:
            Number of products in database
        """
        return self.session.query(func.count(Product.id)).scalar()
    
    def get_categories(self) -> List[str]:
        """
        Get all unique categories.
        
        Returns:
            List of category names
        """
        results = self.session.query(Product.category).distinct().all()
        return [r[0] for r in results if r[0]]


class HistoryRepository:
    """
    Repository for History CRUD operations.
    
    Provides methods for recording and querying product history data.
    """
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session instance
        """
        self.session = session
    
    def create(self, history_data: Dict[str, Any]) -> History:
        """
        Create a new history record.
        
        Args:
            history_data: Dictionary with history fields
            
        Returns:
            Created History instance
        """
        # Set recorded_at to now if not provided
        if 'recorded_at' not in history_data:
            history_data['recorded_at'] = datetime.utcnow()
        
        history = History(**history_data)
        self.session.add(history)
        self.session.flush()
        return history
    
    def get_by_id(self, history_id: int) -> Optional[History]:
        """
        Get history record by ID.
        
        Args:
            history_id: History primary key
            
        Returns:
            History instance or None
        """
        return self.session.query(History).filter(History.id == history_id).first()
    
    def get_by_asin(
        self,
        asin: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[History]:
        """
        Get history records for a product ASIN.
        
        Args:
            asin: Product ASIN
            start_date: Filter records after this date
            end_date: Filter records before this date
            limit: Maximum results
            
        Returns:
            List of History instances
        """
        query = self.session.query(History).filter(History.asin == asin)
        
        if start_date:
            query = query.filter(History.recorded_at >= start_date)
        if end_date:
            query = query.filter(History.recorded_at <= end_date)
        
        return query.order_by(History.recorded_at.desc()).limit(limit).all()
    
    def get_latest(self, asin: str) -> Optional[History]:
        """
        Get most recent history record for a product.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Most recent History instance or None
        """
        return (
            self.session.query(History)
            .filter(History.asin == asin)
            .order_by(desc(History.recorded_at))
            .first()
        )
    
    def get_price_history(
        self,
        asin: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get price history for a product.
        
        Args:
            asin: Product ASIN
            days: Number of days of history
            
        Returns:
            List of dicts with date and price
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        records = self.get_by_asin(asin, start_date=start_date, limit=days)
        
        return [
            {
                'date': r.recorded_at.isoformat(),
                'price': r.price,
            }
            for r in reversed(records)  # Oldest first
            if r.price is not None
        ]
    
    def delete_by_asin(self, asin: str) -> int:
        """
        Delete all history records for an ASIN.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Number of records deleted
        """
        count = (
            self.session.query(History)
            .filter(History.asin == asin)
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return count
    
    def delete_old_records(self, days: int = 90) -> int:
        """
        Delete history records older than specified days.
        
        Args:
            days: Keep only records newer than this
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        count = (
            self.session.query(History)
            .filter(History.recorded_at < cutoff_date)
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return count
    
    def count_by_asin(self, asin: str) -> int:
        """
        Count history records for an ASIN.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Number of history records
        """
        return (
            self.session.query(func.count(History.id))
            .filter(History.asin == asin)
            .scalar()
        )
    
    def get_comparison(
        self,
        asin: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get comparison data for a product (current vs past).
        
        Args:
            asin: Product ASIN
            days: Days to compare against
            
        Returns:
            Dictionary with current and past values
        """
        current = self.get_latest(asin)
        past_date = datetime.utcnow() - timedelta(days=days)
        past_records = self.get_by_asin(asin, end_date=past_date, limit=1)
        past = past_records[0] if past_records else None
        
        return {
            'current': current.to_dict() if current else None,
            'past': past.to_dict() if past else None,
            'days_compared': days,
        }
