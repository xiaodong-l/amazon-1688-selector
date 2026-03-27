"""
Product Repository for Amazon Selector v2.2

Provides CRUD operations and search functionality for Product models.
"""
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models.product import Product, ProductImage, ProductFeature


def _soft_delete_filter(stmt, model):
    """
    Apply soft delete filter to query if model has is_deleted column.
    
    Args:
        stmt: SQLAlchemy select statement
        model: Model class to filter
        
    Returns:
        Statement with soft delete filter applied
    """
    if hasattr(model, 'is_deleted'):
        return stmt.where(model.is_deleted == False, model.deleted_at.is_(None))
    return stmt


class ProductRepository:
    """
    Repository for Product data access.
    
    Provides methods for creating, reading, updating, and deleting products,
    as well as search functionality.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
    
    async def create(
        self,
        asin: str,
        title: str,
        price: float,
        product_url: str,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        currency: Optional[str] = 'USD',
        rating: Optional[float] = None,
        review_count: Optional[int] = None,
        bsr: Optional[int] = None,
        bsr_category: Optional[str] = None,
        availability: Optional[bool] = True,
        prime_eligible: Optional[bool] = False,
        image_url: Optional[str] = None,
        images: Optional[List[Dict[str, Any]]] = None,
        features: Optional[List[str]] = None,
    ) -> Product:
        """
        Create a new product with optional images and features.
        
        Args:
            asin: Amazon Standard Identification Number
            title: Product title
            price: Current price
            product_url: URL to Amazon product page
            brand: Product brand (optional)
            category: Product category (optional)
            currency: Currency code (default: USD)
            rating: Average rating (optional)
            review_count: Number of reviews (optional)
            bsr: Best Sellers Rank (optional)
            bsr_category: BSR category (optional)
            availability: Whether product is available (default: True)
            prime_eligible: Whether Prime eligible (default: False)
            image_url: Main image URL (optional)
            images: List of image dicts with url, position, is_primary (optional)
            features: List of feature strings (optional)
            
        Returns:
            Created Product instance
        """
        product = Product(
            asin=asin,
            title=title,
            price=price,
            product_url=product_url,
            brand=brand,
            category=category,
            currency=currency,
            rating=rating,
            review_count=review_count,
            bsr=bsr,
            bsr_category=bsr_category,
            availability=availability,
            prime_eligible=prime_eligible,
            image_url=image_url,
        )
        
        self.session.add(product)
        await self.session.flush()  # Get the ID
        
        # Add images if provided
        if images:
            for idx, img_data in enumerate(images):
                image = ProductImage(
                    product_id=product.id,
                    image_url=img_data.get('url', ''),
                    position=img_data.get('position', idx),
                    is_primary=img_data.get('is_primary', False),
                )
                self.session.add(image)
        
        # Add features if provided
        if features:
            for idx, feature_text in enumerate(features):
                feature = ProductFeature(
                    product_id=product.id,
                    feature_text=feature_text,
                    position=idx,
                )
                self.session.add(feature)
        
        await self.session.commit()
        await self.session.refresh(product)
        
        return product
    
    async def get_by_asin(self, asin: str, load_relations: bool = False, include_deleted: bool = False) -> Optional[Product]:
        """
        Get product by ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            load_relations: Whether to load images and features (default: False)
            include_deleted: Include soft-deleted products (default: False)
            
        Returns:
            Product instance or None if not found
        """
        if load_relations:
            stmt = select(Product).where(Product.asin == asin).options(
                selectinload(Product.images),
                selectinload(Product.features),
            )
        else:
            stmt = select(Product).where(Product.asin == asin)
        
        if not include_deleted:
            stmt = _soft_delete_filter(stmt, Product)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, product_id: int, load_relations: bool = False, include_deleted: bool = False) -> Optional[Product]:
        """
        Get product by ID.
        
        Args:
            product_id: Product ID
            load_relations: Whether to load images and features (default: False)
            include_deleted: Include soft-deleted products (default: False)
            
        Returns:
            Product instance or None if not found
        """
        if load_relations:
            stmt = select(Product).where(Product.id == product_id).options(
                selectinload(Product.images),
                selectinload(Product.features),
            )
        else:
            stmt = select(Product).where(Product.id == product_id)
        
        if not include_deleted:
            stmt = _soft_delete_filter(stmt, Product)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        page: int = 1,
        page_size: int = 50,
        load_relations: bool = False,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Product]:
        """
        Get all products with pagination.
        
        Args:
            page: Page number (1-indexed, default: 1)
            page_size: Number of items per page (default: 50)
            load_relations: Whether to load images and features (default: False)
            include_deleted: Include soft-deleted products (default: False)
            limit: Direct limit override (optional)
            offset: Direct offset override (optional)
            
        Returns:
            List of Product instances
        """
        if limit is not None and offset is not None:
            pg_offset = offset
            pg_limit = limit
        else:
            pg_offset = (page - 1) * page_size
            pg_limit = page_size
        
        if load_relations:
            stmt = select(Product).options(
                selectinload(Product.images),
                selectinload(Product.features),
            ).offset(pg_offset).limit(pg_limit)
        else:
            stmt = select(Product).offset(pg_offset).limit(pg_limit)
        
        if not include_deleted:
            stmt = _soft_delete_filter(stmt, Product)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count(self, include_deleted: bool = False) -> int:
        """
        Get total count of products.
        
        Args:
            include_deleted: Include soft-deleted products (default: False)
            
        Returns:
            Total number of products
        """
        stmt = select(func.count()).select_from(Product)
        if not include_deleted:
            stmt = stmt.where(Product.is_deleted == False, Product.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar()
    
    async def get_categories(self) -> List[str]:
        """
        Get all unique product categories.
        
        Returns:
            List of unique category names
        """
        stmt = select(Product.category).where(
            Product.category.isnot(None),
            Product.is_deleted == False,
            Product.deleted_at.is_(None),
        ).distinct()
        result = await self.session.execute(stmt)
        return [cat for cat in result.scalars().all() if cat]
    
    async def update(
        self,
        asin: str,
        **kwargs,
    ) -> Optional[Product]:
        """
        Update product by ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            **kwargs: Fields to update
            
        Returns:
            Updated Product instance or None if not found
        """
        product = await self.get_by_asin(asin)
        
        if not product:
            return None
        
        # Update allowed fields
        allowed_fields = [
            'title', 'brand', 'category', 'price', 'currency',
            'rating', 'review_count', 'bsr', 'bsr_category',
            'availability', 'prime_eligible', 'image_url', 'product_url',
        ]
        
        for field in allowed_fields:
            if field in kwargs:
                setattr(product, field, kwargs[field])
        
        product.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(product)
        
        return product
    
    async def delete(self, asin: str) -> bool:
        """
        Soft delete product by ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            True if deleted, False if not found
        """
        # Use include_deleted=True to allow re-deleting already soft-deleted items
        product = await self.get_by_asin(asin, include_deleted=True)
        
        if not product:
            return False
        
        # Soft delete: mark as deleted instead of removing
        product.is_deleted = True
        product.deleted_at = datetime.utcnow()
        
        await self.session.commit()
        return True
    
    async def restore(self, asin: str) -> bool:
        """
        Restore a soft-deleted product by ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            True if restored, False if not found or not deleted
        """
        # Must include deleted items to find the one to restore
        product = await self.get_by_asin(asin, include_deleted=True)
        
        if not product:
            return False
        
        if not product.is_deleted:
            return False  # Not deleted, nothing to restore
        
        # Restore: clear delete flags
        product.is_deleted = False
        product.deleted_at = None
        
        await self.session.commit()
        return True
    
    async def hard_delete(self, asin: str) -> bool:
        """
        Permanently delete product by ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            True if deleted, False if not found
        """
        product = await self.get_by_asin(asin)
        
        if not product:
            return False
        
        await self.session.delete(product)
        await self.session.commit()
        return True
    
    async def get_top_products(
        self,
        by: str = 'rating',
        limit: int = 20,
        category: Optional[str] = None,
    ) -> List[Product]:
        """
        Get top products sorted by specified field.
        
        Args:
            by: Sort field (rating, review_count, price, created_at)
            limit: Number of results (default: 20)
            category: Filter by category (optional)
            
        Returns:
            List of top Product instances
        """
        # Map sort field to column
        sort_columns = {
            'rating': Product.rating,
            'review_count': Product.review_count,
            'price': Product.price,
            'created_at': Product.created_at,
        }
        
        sort_column = sort_columns.get(by, Product.rating)
        
        stmt = select(Product).where(
            Product.is_deleted == False,
            Product.deleted_at.is_(None),
        )
        
        if category:
            stmt = stmt.where(Product.category == category)
        
        stmt = stmt.order_by(sort_column.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def search(
        self,
        query: Optional[str] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        min_reviews: Optional[int] = None,
        min_bsr: Optional[int] = None,
        max_bsr: Optional[int] = None,
        prime_eligible: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Product]:
        """
        Search products with various filters.
        
        Args:
            query: Search query for title (optional)
            brand: Filter by brand (optional)
            category: Filter by category (optional)
            min_price: Minimum price filter (optional)
            max_price: Maximum price filter (optional)
            min_rating: Minimum rating filter (optional)
            min_reviews: Minimum review count filter (optional)
            min_bsr: Minimum BSR filter (optional)
            max_bsr: Maximum BSR filter (optional)
            prime_eligible: Filter by Prime eligibility (optional)
            page: Page number (1-indexed, default: 1)
            page_size: Number of items per page (default: 50)
            include_deleted: Include soft-deleted products (default: False)
            limit: Direct limit override (optional)
            offset: Direct offset override (optional)
            
        Returns:
            List of matching Product instances
        """
        conditions = []
        
        # Text search in title
        if query:
            conditions.append(Product.title.ilike(f"%{query}%"))
        
        # Brand filter
        if brand:
            conditions.append(Product.brand.ilike(f"%{brand}%"))
        
        # Category filter
        if category:
            conditions.append(Product.category.ilike(f"%{category}%"))
        
        # Price range
        if min_price is not None:
            conditions.append(Product.price >= min_price)
        if max_price is not None:
            conditions.append(Product.price <= max_price)
        
        # Rating filter
        if min_rating is not None:
            conditions.append(Product.rating >= min_rating)
        
        # Review count filter
        if min_reviews is not None:
            conditions.append(Product.review_count >= min_reviews)
        
        # BSR range
        if min_bsr is not None:
            conditions.append(Product.bsr >= min_bsr)
        if max_bsr is not None:
            conditions.append(Product.bsr <= max_bsr)
        
        # Prime eligibility
        if prime_eligible is not None:
            conditions.append(Product.prime_eligible == prime_eligible)
        
        # Soft delete filter (always apply unless explicitly included)
        if not include_deleted:
            conditions.append(Product.is_deleted == False)
            conditions.append(Product.deleted_at.is_(None))
        
        # Build query
        stmt = select(Product)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # Pagination
        if limit is not None and offset is not None:
            stmt = stmt.offset(offset).limit(limit)
        else:
            pg_offset = (page - 1) * page_size
            stmt = stmt.offset(pg_offset).limit(page_size)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_top_by_rating(self, limit: int = 10, include_deleted: bool = False) -> List[Product]:
        """
        Get top products by rating.
        
        Args:
            limit: Number of products to return (default: 10)
            include_deleted: Include soft-deleted products (default: False)
            
        Returns:
            List of Product instances sorted by rating
        """
        conditions = [Product.rating.isnot(None)]
        if not include_deleted:
            conditions.append(Product.is_deleted == False)
            conditions.append(Product.deleted_at.is_(None))
        
        stmt = select(Product).where(and_(*conditions)).order_by(Product.rating.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_top_by_review_count(self, limit: int = 10, include_deleted: bool = False) -> List[Product]:
        """
        Get top products by review count.
        
        Args:
            limit: Number of products to return (default: 10)
            include_deleted: Include soft-deleted products (default: False)
            
        Returns:
            List of Product instances sorted by review count
        """
        conditions = [Product.review_count.isnot(None)]
        if not include_deleted:
            conditions.append(Product.is_deleted == False)
            conditions.append(Product.deleted_at.is_(None))
        
        stmt = select(Product).where(and_(*conditions)).order_by(Product.review_count.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_lowest_bsr(self, limit: int = 10, include_deleted: bool = False) -> List[Product]:
        """
        Get products with lowest BSR (best ranking).
        
        Args:
            limit: Number of products to return (default: 10)
            include_deleted: Include soft-deleted products (default: False)
            
        Returns:
            List of Product instances sorted by BSR ascending
        """
        conditions = [Product.bsr.isnot(None)]
        if not include_deleted:
            conditions.append(Product.is_deleted == False)
            conditions.append(Product.deleted_at.is_(None))
        
        stmt = select(Product).where(and_(*conditions)).order_by(Product.bsr.asc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
