"""
History Repository for Amazon Selector v2.2

Provides methods for recording and querying product history data.
"""
from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from ..models.history import ProductHistory, PriceHistory, BSRHistory
from ..models.product import Product


class HistoryRepository:
    """
    Repository for history data access.
    
    Provides methods for recording historical data points and
    querying trends over time.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
    
    async def create(self, data: Dict[str, Any]) -> ProductHistory:
        """
        Create a new history record from a data dictionary.
        
        This method provides a generic interface for creating history records
        from dictionary data, useful for API integrations and testing.
        
        Args:
            data: Dictionary containing history data with keys:
                - product_id: Product ID (required)
                - asin: Product ASIN (required)
                - price: Current price (optional)
                - rating: Current rating (optional)
                - review_count: Current review count (optional)
                - bsr: Current BSR (optional)
                - title: Product title (optional)
                - recorded_at: When this data was recorded (optional, defaults to now)
            
        Returns:
            Created ProductHistory instance
        """
        return await self.record_history(
            product_id=data.get('product_id'),
            asin=data.get('asin'),
            price=data.get('price'),
            rating=data.get('rating'),
            review_count=data.get('review_count'),
            bsr=data.get('bsr'),
            title=data.get('title'),
            recorded_at=data.get('recorded_at'),
        )
    
    async def bulk_create(self, records: List[Dict[str, Any]]) -> List[ProductHistory]:
        """
        Create multiple history records in a single transaction.
        
        Args:
            records: List of dictionaries containing history data
                (same format as create() method)
            
        Returns:
            List of created ProductHistory instances
        """
        created_records = []
        
        for data in records:
            record = await self.create(data)
            created_records.append(record)
        
        return created_records
    
    async def record_history(
        self,
        product_id: int,
        asin: str,
        price: Optional[float] = None,
        rating: Optional[float] = None,
        review_count: Optional[int] = None,
        bsr: Optional[int] = None,
        title: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
    ) -> ProductHistory:
        """
        Record a history snapshot for a product.
        
        Args:
            product_id: Product ID
            asin: Product ASIN
            price: Current price (optional)
            rating: Current rating (optional)
            review_count: Current review count (optional)
            bsr: Current BSR (optional)
            title: Product title (optional)
            recorded_at: When this data was recorded (default: now)
            
        Returns:
            Created ProductHistory instance
        """
        history = ProductHistory(
            product_id=product_id,
            asin=asin,
            price=price,
            rating=rating,
            review_count=review_count,
            bsr=bsr,
            title=title,
            recorded_at=recorded_at or datetime.utcnow(),
        )
        
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        
        return history
    
    async def record_price(
        self,
        product_id: int,
        asin: str,
        price: float,
        currency: str = 'USD',
        recorded_at: Optional[datetime] = None,
    ) -> PriceHistory:
        """
        Record a price history entry.
        
        Args:
            product_id: Product ID
            asin: Product ASIN
            price: Price value
            currency: Currency code (default: USD)
            recorded_at: When this price was recorded (default: now)
            
        Returns:
            Created PriceHistory instance
        """
        history = PriceHistory(
            product_id=product_id,
            asin=asin,
            price=price,
            currency=currency,
            recorded_at=recorded_at or datetime.utcnow(),
        )
        
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        
        return history
    
    async def record_bsr(
        self,
        product_id: int,
        asin: str,
        bsr: int,
        bsr_category: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
    ) -> BSRHistory:
        """
        Record a BSR history entry.
        
        Args:
            product_id: Product ID
            asin: Product ASIN
            bsr: BSR value
            bsr_category: BSR category (optional)
            recorded_at: When this BSR was recorded (default: now)
            
        Returns:
            Created BSRHistory instance
        """
        history = BSRHistory(
            product_id=product_id,
            asin=asin,
            bsr=bsr,
            bsr_category=bsr_category,
            recorded_at=recorded_at or datetime.utcnow(),
        )
        
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        
        return history
    
    async def get_history(
        self,
        asin: Optional[str] = None,
        product_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ProductHistory]:
        """
        Get product history entries.
        
        Args:
            asin: Filter by ASIN (optional)
            product_id: Filter by product ID (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum number of records (default: 100)
            
        Returns:
            List of ProductHistory instances
        """
        conditions = []
        
        if asin:
            conditions.append(ProductHistory.asin == asin)
        if product_id:
            conditions.append(ProductHistory.product_id == product_id)
        if start_date:
            conditions.append(ProductHistory.recorded_at >= start_date)
        if end_date:
            conditions.append(ProductHistory.recorded_at <= end_date)
        
        stmt = select(ProductHistory)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(desc(ProductHistory.recorded_at)).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_price_history(
        self,
        asin: Optional[str] = None,
        product_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[PriceHistory]:
        """
        Get price history entries.
        
        Args:
            asin: Filter by ASIN (optional)
            product_id: Filter by product ID (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum number of records (default: 100)
            
        Returns:
            List of PriceHistory instances
        """
        conditions = []
        
        if asin:
            conditions.append(PriceHistory.asin == asin)
        if product_id:
            conditions.append(PriceHistory.product_id == product_id)
        if start_date:
            conditions.append(PriceHistory.recorded_at >= start_date)
        if end_date:
            conditions.append(PriceHistory.recorded_at <= end_date)
        
        stmt = select(PriceHistory)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(asc(PriceHistory.recorded_at)).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_bsr_history(
        self,
        asin: Optional[str] = None,
        product_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BSRHistory]:
        """
        Get BSR history entries.
        
        Args:
            asin: Filter by ASIN (optional)
            product_id: Filter by product ID (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum number of records (default: 100)
            
        Returns:
            List of BSRHistory instances
        """
        conditions = []
        
        if asin:
            conditions.append(BSRHistory.asin == asin)
        if product_id:
            conditions.append(BSRHistory.product_id == product_id)
        if start_date:
            conditions.append(BSRHistory.recorded_at >= start_date)
        if end_date:
            conditions.append(BSRHistory.recorded_at <= end_date)
        
        stmt = select(BSRHistory)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(asc(BSRHistory.recorded_at)).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_trend(
        self,
        asin: str,
        days: int = 30,
        metric: str = 'price',
    ) -> Dict[str, Any]:
        """
        Get trend analysis for a product.
        
        Args:
            asin: Product ASIN
            days: Number of days to analyze (default: 30)
            metric: Metric to analyze: 'price', 'bsr', 'rating' (default: 'price')
            
        Returns:
            Dict with trend analysis:
                - current: Current value
                - previous: Value from start of period
                - change: Absolute change
                - change_percent: Percentage change
                - trend: 'up', 'down', or 'stable'
                - data_points: List of data points
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Validate metric and select appropriate model/column
        if metric == 'price':
            history_model = PriceHistory
            value_attr = 'price'
        elif metric == 'bsr':
            history_model = BSRHistory
            value_attr = 'bsr'
        elif metric == 'rating':
            history_model = ProductHistory
            value_attr = 'rating'
        else:
            # Default to price for unknown metrics
            history_model = PriceHistory
            value_attr = 'price'
        
        # Get historical data
        stmt = select(history_model).where(
            and_(
                history_model.asin == asin,
                history_model.recorded_at >= start_date,
            )
        ).order_by(asc(history_model.recorded_at))
        
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        
        if not records:
            return {
                'current': None,
                'previous': None,
                'change': None,
                'change_percent': None,
                'trend': 'unknown',
                'data_points': [],
                'error': None,
            }
        
        # Safely extract values with null checks
        def get_value(record, attr):
            """Safely get attribute value from record, handling None."""
            if record is None:
                return None
            value = getattr(record, attr, None)
            # Ensure value is not None and is a valid number
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        
        current_value = get_value(records[-1], value_attr)
        previous_value = get_value(records[0], value_attr)
        
        # Calculate trend with proper null handling
        if current_value is None or previous_value is None:
            trend = 'unknown'
            change = None
            change_percent = None
        else:
            change = current_value - previous_value
            
            if metric == 'bsr':
                # For BSR, lower is better
                if change < -0.001:  # Use small epsilon for float comparison
                    trend = 'up'  # BSR improved
                elif change > 0.001:
                    trend = 'down'  # BSR worsened
                else:
                    trend = 'stable'
            else:
                # For price/rating, higher is typically "up"
                if change > 0.001:
                    trend = 'up'
                elif change < -0.001:
                    trend = 'down'
                else:
                    trend = 'stable'
            
            if previous_value != 0:
                change_percent = round((change / previous_value) * 100, 2)
            else:
                change_percent = None
        
        # Format data points with safe value extraction
        data_points = []
        for record in records:
            value = get_value(record, value_attr)
            data_points.append({
                'recorded_at': record.recorded_at.isoformat() if record.recorded_at else None,
                'value': value,
            })
        
        return {
            'current': current_value,
            'previous': previous_value,
            'change': change,
            'change_percent': change_percent,
            'trend': trend,
            'data_points': data_points,
            'error': None,
        }
    
    async def get_price_stats(
        self,
        asin: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get price statistics for a product.
        
        Args:
            asin: Product ASIN
            days: Number of days to analyze (default: 30)
            
        Returns:
            Dict with statistics:
                - min: Minimum price
                - max: Maximum price
                - avg: Average price
                - current: Current/latest price
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(
            func.min(PriceHistory.price).label('min_price'),
            func.max(PriceHistory.price).label('max_price'),
            func.avg(PriceHistory.price).label('avg_price'),
        ).where(
            and_(
                PriceHistory.asin == asin,
                PriceHistory.recorded_at >= start_date,
            )
        )
        
        result = await self.session.execute(stmt)
        row = result.first()
        
        if not row or row.min_price is None:
            return {
                'min': None,
                'max': None,
                'avg': None,
                'current': None,
            }
        
        # Get current price
        current_stmt = select(PriceHistory).where(
            PriceHistory.asin == asin
        ).order_by(desc(PriceHistory.recorded_at)).limit(1)
        
        current_result = await self.session.execute(current_stmt)
        current_record = current_result.scalar_one_or_none()
        
        return {
            'min': row.min_price,
            'max': row.max_price,
            'avg': row.avg_price,
            'current': current_record.price if current_record else None,
        }
    
    async def get_bsr_stats(
        self,
        asin: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get BSR statistics for a product.
        
        Args:
            asin: Product ASIN
            days: Number of days to analyze (default: 30)
            
        Returns:
            Dict with statistics:
                - min: Best (lowest) BSR
                - max: Worst (highest) BSR
                - avg: Average BSR
                - current: Current/latest BSR
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(
            func.min(BSRHistory.bsr).label('min_bsr'),
            func.max(BSRHistory.bsr).label('max_bsr'),
            func.avg(BSRHistory.bsr).label('avg_bsr'),
        ).where(
            and_(
                BSRHistory.asin == asin,
                BSRHistory.recorded_at >= start_date,
            )
        )
        
        result = await self.session.execute(stmt)
        row = result.first()
        
        if not row or row.min_bsr is None:
            return {
                'min': None,
                'max': None,
                'avg': None,
                'current': None,
            }
        
        # Get current BSR
        current_stmt = select(BSRHistory).where(
            BSRHistory.asin == asin
        ).order_by(desc(BSRHistory.recorded_at)).limit(1)
        
        current_result = await self.session.execute(current_stmt)
        current_record = current_result.scalar_one_or_none()
        
        return {
            'min': row.min_bsr,
            'max': row.max_bsr,
            'avg': row.avg_bsr,
            'current': current_record.bsr if current_record else None,
        }
