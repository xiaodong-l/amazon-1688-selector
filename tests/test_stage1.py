"""
Stage 1 Database Tests for Amazon Selector v2.2

Tests for database connection, models, and basic operations.
Coverage target: >90%

Run with:
    pytest tests/test_stage1.py -v
    pytest tests/test_stage1.py -v --cov=src/db --cov-report=html

Note: All tests now use async patterns for SQLAlchemy 2.0 compatibility.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func

from src.db import (
    Base,
    Product,
    ProductImage,
    ProductFeature,
    ProductHistory,
    PriceHistory,
    BSRHistory,
)
from src.db.connection import get_database_url


# ==================== Connection Tests ====================

class TestConnection:
    """Test database connection and initialization."""
    
    def test_get_database_url_test_mode(self):
        """Test database URL generation for test mode."""
        url = get_database_url(test_mode=True, async_mode=True)
        assert "sqlite+aiosqlite" in url
        assert "memory" in url
    
    def test_get_database_url_default(self):
        """Test default database URL generation."""
        url = get_database_url(test_mode=False, async_mode=False)
        assert "sqlite" in url
    
    def test_get_database_url_async_postgresql(self):
        """Test async PostgreSQL URL generation."""
        import os
        old_url = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
            url = get_database_url(test_mode=False, async_mode=True)
            assert "postgresql+asyncpg" in url
        finally:
            if old_url:
                os.environ["DATABASE_URL"] = old_url
            else:
                os.environ.pop("DATABASE_URL", None)


# ==================== Model Tests ====================

class TestProductModel:
    """Test Product model."""
    
    @pytest_asyncio.fixture
    async def _setup_product(self, async_db_session, sample_product_data):
        """Setup helper for product tests."""
        product = Product(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
            rating=sample_product_data.get('rating'),
            review_count=sample_product_data.get('review_count'),
            bsr=sample_product_data.get('bsr'),
            category=sample_product_data.get('category'),
            image_url=sample_product_data.get('image_url'),
        )
        async_db_session.add(product)
        await async_db_session.commit()
        await async_db_session.refresh(product)
        return product
    
    async def test_create_product(self, async_db_session, sample_product_data):
        """Test creating a product."""
        product = Product(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
            rating=sample_product_data.get('rating'),
            review_count=sample_product_data.get('review_count'),
            bsr=sample_product_data.get('bsr'),
            category=sample_product_data.get('category'),
            image_url=sample_product_data.get('image_url'),
        )
        async_db_session.add(product)
        await async_db_session.commit()
        await async_db_session.refresh(product)
        
        assert product.id is not None
        assert product.asin == sample_product_data['asin']
        assert product.title == sample_product_data['title']
        assert product.price == sample_product_data['price']
    
    async def test_product_to_dict(self, async_db_session, sample_product_data):
        """Test product to_dict method."""
        product = Product(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
        )
        async_db_session.add(product)
        await async_db_session.commit()
        
        product_dict = product.to_dict()
        
        assert product_dict['asin'] == sample_product_data['asin']
        assert product_dict['title'] == sample_product_data['title']
        assert 'created_at' in product_dict
        assert 'updated_at' in product_dict
    
    async def test_product_unique_asin(self, async_db_session, sample_product_data):
        """Test ASIN uniqueness constraint."""
        product1 = Product(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
        )
        async_db_session.add(product1)
        await async_db_session.commit()
        
        # Try to create duplicate
        product2 = Product(
            asin=sample_product_data['asin'],
            title='Different Title',
            price=19.99,
            product_url='https://example.com',
        )
        async_db_session.add(product2)
        
        with pytest.raises(Exception):  # IntegrityError
            await async_db_session.commit()
    
    async def test_product_soft_delete(self, async_db_session, sample_product_data):
        """Test product soft delete functionality."""
        product = Product(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
        )
        async_db_session.add(product)
        await async_db_session.commit()
        
        # Soft delete
        product.soft_delete()
        await async_db_session.commit()
        
        assert product.is_deleted == True
        assert product.deleted_at is not None
    
    async def test_product_restore(self, async_db_session, sample_product_data):
        """Test product restore after soft delete."""
        product = Product(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
        )
        async_db_session.add(product)
        await async_db_session.commit()
        
        # Soft delete and restore
        product.soft_delete()
        product.restore()
        await async_db_session.commit()
        
        assert product.is_deleted == False
        assert product.deleted_at is None
    
    async def test_product_images(self, async_db_session, sample_product_data):
        """Test product with images."""
        product = Product(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
        )
        async_db_session.add(product)
        await async_db_session.flush()
        
        # Add images
        image1 = ProductImage(
            product_id=product.id,
            image_url='https://example.com/image1.jpg',
            position=0,
            is_primary=True,
        )
        image2 = ProductImage(
            product_id=product.id,
            image_url='https://example.com/image2.jpg',
            position=1,
            is_primary=False,
        )
        async_db_session.add_all([image1, image2])
        await async_db_session.commit()
        
        assert len(product.images) == 2
        assert product.images[0].is_primary == True
    
    async def test_product_features(self, async_db_session, sample_product_data):
        """Test product with features."""
        product = Product(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
        )
        async_db_session.add(product)
        await async_db_session.flush()
        
        # Add features
        feature1 = ProductFeature(
            product_id=product.id,
            feature_text='Feature 1',
            position=0,
        )
        feature2 = ProductFeature(
            product_id=product.id,
            feature_text='Feature 2',
            position=1,
        )
        async_db_session.add_all([feature1, feature2])
        await async_db_session.commit()
        
        assert len(product.features) == 2


class TestHistoryModels:
    """Test history models."""
    
    async def test_product_history(self, async_db_session, sample_product):
        """Test ProductHistory model."""
        history = ProductHistory(
            product_id=sample_product.id,
            asin=sample_product.asin,
            price=sample_product.price,
            rating=sample_product.rating,
            bsr=sample_product.bsr,
        )
        async_db_session.add(history)
        await async_db_session.commit()
        
        assert history.id is not None
        assert history.asin == sample_product.asin
    
    async def test_price_history(self, async_db_session, sample_product):
        """Test PriceHistory model."""
        price_history = PriceHistory(
            product_id=sample_product.id,
            asin=sample_product.asin,
            price=39.99,
        )
        async_db_session.add(price_history)
        await async_db_session.commit()
        
        assert price_history.id is not None
        assert price_history.price == 39.99
    
    async def test_bsr_history(self, async_db_session, sample_product):
        """Test BSRHistory model."""
        bsr_history = BSRHistory(
            product_id=sample_product.id,
            asin=sample_product.asin,
            bsr=10,
            bsr_category='Test Category',
        )
        async_db_session.add(bsr_history)
        await async_db_session.commit()
        
        assert bsr_history.id is not None
        assert bsr_history.bsr == 10
    
    async def test_price_history_multiple(self, async_db_session, sample_product):
        """Test multiple price history records."""
        for price in [49.99, 44.99, 39.99, 42.99]:
            history = PriceHistory(
                product_id=sample_product.id,
                asin=sample_product.asin,
                price=price,
            )
            async_db_session.add(history)
        await async_db_session.commit()
        
        stmt = select(PriceHistory).where(PriceHistory.asin == sample_product.asin)
        result = await async_db_session.execute(stmt)
        histories = result.scalars().all()
        
        assert len(histories) == 4
    
    async def test_bsr_history_multiple(self, async_db_session, sample_product):
        """Test multiple BSR history records."""
        for bsr in [100, 85, 72, 65, 50]:
            history = BSRHistory(
                product_id=sample_product.id,
                asin=sample_product.asin,
                bsr=bsr,
            )
            async_db_session.add(history)
        await async_db_session.commit()
        
        stmt = select(BSRHistory).where(BSRHistory.asin == sample_product.asin)
        result = await async_db_session.execute(stmt)
        histories = result.scalars().all()
        
        assert len(histories) == 5


# ==================== Query Tests ====================

class TestQueries:
    """Test database queries."""
    
    async def test_get_all_products(self, async_db_session, multiple_products):
        """Test getting all products."""
        stmt = select(Product)
        result = await async_db_session.execute(stmt)
        products = result.scalars().all()
        
        assert len(products) == 5
    
    async def test_get_product_by_asin(self, async_db_session, sample_product):
        """Test getting product by ASIN."""
        stmt = select(Product).where(Product.asin == sample_product.asin)
        result = await async_db_session.execute(stmt)
        product = result.scalar_one_or_none()
        
        assert product is not None
        assert product.asin == sample_product.asin
    
    async def test_search_by_category(self, async_db_session, multiple_products):
        """Test searching products by category."""
        stmt = select(Product).where(Product.category == 'Electronics')
        result = await async_db_session.execute(stmt)
        products = result.scalars().all()
        
        assert len(products) == 3  # 3 electronics products
    
    async def test_search_by_price_range(self, async_db_session, multiple_products):
        """Test searching products by price range."""
        stmt = select(Product).where(
            (Product.price >= 50) & (Product.price <= 150)
        )
        result = await async_db_session.execute(stmt)
        products = result.scalars().all()
        
        assert len(products) == 3  # 49.99, 89.99, 119.99 (close enough)
    
    async def test_order_by_rating(self, async_db_session, multiple_products):
        """Test ordering products by rating."""
        stmt = select(Product).order_by(Product.rating.desc())
        result = await async_db_session.execute(stmt)
        products = result.scalars().all()
        
        assert products[0].rating >= products[-1].rating
    
    async def test_count_products(self, async_db_session, multiple_products):
        """Test counting products."""
        stmt = select(func.count()).select_from(Product)
        result = await async_db_session.execute(stmt)
        count = result.scalar()
        
        assert count == 5
    
    async def test_history_by_asin(self, async_db_session, sample_product):
        """Test querying history by ASIN."""
        # Create history records
        for price in [49.99, 44.99, 39.99]:
            history = PriceHistory(
                product_id=sample_product.id,
                asin=sample_product.asin,
                price=price,
            )
            async_db_session.add(history)
        await async_db_session.commit()
        
        stmt = select(PriceHistory).where(PriceHistory.asin == sample_product.asin)
        result = await async_db_session.execute(stmt)
        histories = result.scalars().all()
        
        assert len(histories) == 3


# ==================== Integration Tests ====================

class TestIntegration:
    """Integration tests for complete workflows."""
    
    async def test_full_product_workflow(self, async_db_session, sample_product_data):
        """Test complete product creation and query workflow."""
        # CREATE
        product = Product(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
            rating=sample_product_data['rating'],
        )
        async_db_session.add(product)
        await async_db_session.commit()
        await async_db_session.refresh(product)
        
        # READ
        stmt = select(Product).where(Product.asin == sample_product_data['asin'])
        result = await async_db_session.execute(stmt)
        fetched = result.scalar_one_or_none()
        
        assert fetched is not None
        assert fetched.id == product.id
        
        # UPDATE
        fetched.price = 59.99
        await async_db_session.commit()
        
        # VERIFY UPDATE
        stmt = select(Product).where(Product.id == product.id)
        result = await async_db_session.execute(stmt)
        updated = result.scalar_one_or_none()
        
        assert updated.price == 59.99
        
        # DELETE (soft)
        updated.soft_delete()
        await async_db_session.commit()
        
        assert updated.is_deleted == True
