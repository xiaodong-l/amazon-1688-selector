"""
Bugfix Verification Tests for Major Issues

Tests to verify the 3 Major bugfixes:
1. Soft delete auto-filter
2. get_trend() null safety
3. reset_db() exception handling
"""
import pytest
import asyncio
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.connection import get_async_engine, get_async_session_factory, init_db_async, drop_db_async, reset_db_async, close_all_async
from src.db.models.product import Product
from src.db.models.history import PriceHistory
from src.db.repositories.product_repo import ProductRepository
from src.db.repositories.history_repo import HistoryRepository


@pytest.fixture
async def db_session():
    """Create async test session."""
    engine = get_async_engine(test_mode=True)
    await init_db_async(test_mode=True)
    
    factory = get_async_session_factory()
    async with factory() as session:
        yield session
    
    await close_all_async()


@pytest.fixture
def product_repo(db_session):
    """Create product repository."""
    return ProductRepository(db_session)


@pytest.fixture
def history_repo(db_session):
    """Create history repository."""
    return HistoryRepository(db_session)


class TestSoftDeleteFix:
    """Test soft delete auto-filter fix."""
    
    @pytest.mark.asyncio
    async def test_create_and_soft_delete(self, product_repo):
        """Test that soft delete sets deleted_at instead of removing."""
        # Create product
        product = await product_repo.create(
            asin='B000000001',
            title='Test Product',
            price=29.99,
            product_url='https://amazon.com/dp/B000000001',
        )
        
        assert product.id is not None
        assert product.is_deleted == False
        assert product.deleted_at is None
        
        # Soft delete
        result = await product_repo.delete('B000000001')
        assert result == True
        
        # Verify soft delete flags
        deleted_product = await product_repo.get_by_asin('B000000001', include_deleted=True)
        assert deleted_product is not None
        assert deleted_product.is_deleted == True
        assert deleted_product.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_soft_delete_auto_filter(self, product_repo):
        """Test that queries automatically filter soft-deleted items."""
        # Create and delete a product
        await product_repo.create(
            asin='B000000002',
            title='Deleted Product',
            price=19.99,
            product_url='https://amazon.com/dp/B000000002',
        )
        await product_repo.delete('B000000002')
        
        # Create another product (not deleted)
        await product_repo.create(
            asin='B000000003',
            title='Active Product',
            price=39.99,
            product_url='https://amazon.com/dp/B000000003',
        )
        
        # Get by ASIN should not find deleted product
        deleted = await product_repo.get_by_asin('B000000002')
        assert deleted is None
        
        # Get by ASIN with include_deleted should find it
        deleted_with_flag = await product_repo.get_by_asin('B000000002', include_deleted=True)
        assert deleted_with_flag is not None
        assert deleted_with_flag.is_deleted == True
        
        # Get all should not include deleted
        all_products = await product_repo.get_all()
        assert len(all_products) == 1
        assert all_products[0].asin == 'B000000003'
    
    @pytest.mark.asyncio
    async def test_restore_soft_deleted(self, product_repo):
        """Test restore() method for soft-deleted products."""
        # Create and delete
        await product_repo.create(
            asin='B000000004',
            title='To Restore',
            price=49.99,
            product_url='https://amazon.com/dp/B000000004',
        )
        await product_repo.delete('B000000004')
        
        # Verify deleted
        deleted = await product_repo.get_by_asin('B000000004')
        assert deleted is None
        
        # Restore
        result = await product_repo.restore('B000000004')
        assert result == True
        
        # Verify restored
        restored = await product_repo.get_by_asin('B000000004')
        assert restored is not None
        assert restored.is_deleted == False
        assert restored.deleted_at is None
    
    @pytest.mark.asyncio
    async def test_search_filters_deleted(self, product_repo):
        """Test that search automatically filters deleted products."""
        # Create products
        await product_repo.create(asin='B000000005', title='Active 1', price=10.0, product_url='http://a.com/5')
        await product_repo.create(asin='B000000006', title='Active 2', price=20.0, product_url='http://a.com/6')
        await product_repo.create(asin='B000000007', title='Deleted', price=30.0, product_url='http://a.com/7')
        await product_repo.delete('B000000007')
        
        # Search should not include deleted
        results = await product_repo.search()
        assert len(results) == 2
        assert all(p.asin != 'B000000007' for p in results)


class TestGetTrendNullSafety:
    """Test get_trend() null safety fix."""
    
    @pytest.mark.asyncio
    async def test_get_trend_no_data(self, history_repo):
        """Test get_trend with no data returns safe defaults."""
        result = await history_repo.get_trend('B999999999', days=30, metric='price')
        
        assert result['current'] is None
        assert result['previous'] is None
        assert result['change'] is None
        assert result['change_percent'] is None
        assert result['trend'] == 'unknown'
        assert result['data_points'] == []
        assert result['error'] is None
    
    @pytest.mark.asyncio
    async def test_get_trend_with_null_values(self, history_repo, db_session):
        """Test get_trend handles null values in records safely."""
        # Create price history with some null values
        from src.db.models.history import PriceHistory
        
        ph1 = PriceHistory(
            product_id=1,
            asin='B000000010',
            price=29.99,
            recorded_at=datetime.utcnow() - timedelta(days=10),
        )
        ph2 = PriceHistory(
            product_id=1,
            asin='B000000010',
            price=None,  # Null value
            recorded_at=datetime.utcnow() - timedelta(days=5),
        )
        ph3 = PriceHistory(
            product_id=1,
            asin='B000000010',
            price=39.99,
            recorded_at=datetime.utcnow(),
        )
        
        db_session.add_all([ph1, ph2, ph3])
        await db_session.commit()
        
        # Should handle null values gracefully
        result = await history_repo.get_trend('B000000010', days=30, metric='price')
        
        # Should have data points
        assert len(result['data_points']) > 0
        # Trend should be calculable or 'unknown' if nulls interfere
        assert result['trend'] in ['up', 'down', 'stable', 'unknown']
    
    @pytest.mark.asyncio
    async def test_get_trend_valid_data(self, history_repo, db_session):
        """Test get_trend with valid data calculates correctly."""
        from src.db.models.history import PriceHistory
        
        # Create price history
        for i, price in enumerate([10.0, 15.0, 20.0, 25.0]):
            ph = PriceHistory(
                product_id=1,
                asin='B000000011',
                price=price,
                recorded_at=datetime.utcnow() - timedelta(days=10 - i*2),
            )
            db_session.add(ph)
        
        await db_session.commit()
        
        result = await history_repo.get_trend('B000000011', days=30, metric='price')
        
        assert result['current'] == 25.0
        assert result['previous'] == 10.0
        assert result['change'] == 15.0
        assert result['change_percent'] == 150.0
        assert result['trend'] == 'up'
        assert len(result['data_points']) == 4


class TestResetDbExceptionHandling:
    """Test reset_db() exception handling fix."""
    
    def test_reset_db_exists_and_logged(self):
        """Test that reset_db has proper exception handling."""
        from src.db import connection
        import inspect
        
        # Get reset_db source
        source = inspect.getsource(connection.reset_db)
        
        # Check for exception handling
        assert 'try:' in source
        assert 'except' in source
        assert 'logger.error' in source or 'logger.info' in source
        assert 'OperationalError' in source or 'SQLAlchemyError' in source
    
    def test_reset_db_async_exists_and_logged(self):
        """Test that reset_db_async has proper exception handling."""
        from src.db import connection
        import inspect
        
        # Get reset_db_async source
        source = inspect.getsource(connection.reset_db_async)
        
        # Check for exception handling
        assert 'try:' in source
        assert 'except' in source
        assert 'logger.error' in source or 'logger.info' in source
    
    @pytest.mark.asyncio
    async def test_reset_db_works(self):
        """Test that reset_db completes successfully."""
        # Initialize
        await init_db_async(test_mode=True)
        
        # Reset should work without errors
        try:
            await reset_db_async(test_mode=True)
            success = True
        except Exception as e:
            success = False
            print(f"Reset failed: {e}")
        
        assert success == True
        
        await close_all_async()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
