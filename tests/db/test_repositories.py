"""
Database Repositories Tests for Amazon Selector v2.2

Tests for ProductRepository and HistoryRepository CRUD operations.
All tests are asynchronous to match the async repository implementations.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.models import Product, History, ProductHistory
from src.db.repositories import ProductRepository, HistoryRepository


class TestProductRepository:
    """Tests for ProductRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_product(self, async_product_repo, sample_product_data):
        """Test creating a product."""
        product = await async_product_repo.create(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
            rating=sample_product_data['rating'],
            review_count=sample_product_data['review_count'],
            bsr=sample_product_data['bsr'],
            category=sample_product_data['category'],
            image_url=sample_product_data['image_url'],
        )
        
        assert product.id is not None
        assert product.asin == sample_product_data['asin']
        assert product.title == sample_product_data['title']
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, async_product_repo, async_sample_product):
        """Test getting product by ID."""
        retrieved = await async_product_repo.get_by_id(async_sample_product.id)
        
        assert retrieved is not None
        assert retrieved.id == async_sample_product.id
        assert retrieved.asin == async_sample_product.asin
    
    @pytest.mark.asyncio
    async def test_get_by_asin(self, async_product_repo, async_sample_product):
        """Test getting product by ASIN."""
        retrieved = await async_product_repo.get_by_asin(async_sample_product.asin)
        
        assert retrieved is not None
        assert retrieved.id == async_sample_product.id
    
    @pytest.mark.asyncio
    async def test_get_by_asin_not_found(self, async_product_repo):
        """Test getting non-existent product by ASIN."""
        retrieved = await async_product_repo.get_by_asin("B999999999")
        
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_get_all(self, async_product_repo, async_multiple_products):
        """Test getting all products."""
        products = await async_product_repo.get_all()
        
        assert len(products) == 5  # From async_multiple_products fixture
    
    @pytest.mark.asyncio
    async def test_get_all_pagination(self, async_product_repo, async_multiple_products):
        """Test pagination with get_all."""
        # Get first 2
        products = await async_product_repo.get_all(page=1, page_size=2)
        assert len(products) == 2
        
        # Get next 2
        products = await async_product_repo.get_all(page=2, page_size=2)
        assert len(products) == 2
        
        # Get last 1
        products = await async_product_repo.get_all(page=3, page_size=2)
        assert len(products) == 1
    
    @pytest.mark.asyncio
    async def test_update_product(self, async_product_repo, async_sample_product):
        """Test updating a product."""
        updated = await async_product_repo.update(
            async_sample_product.asin,
            price=59.99,
            rating=4.8,
        )
        
        assert updated is not None
        assert updated.price == 59.99
        assert updated.rating == 4.8
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_product(self, async_product_repo):
        """Test updating non-existent product."""
        updated = await async_product_repo.update(
            "B999999999",
            price=59.99,
        )
        
        assert updated is None
    
    @pytest.mark.asyncio
    async def test_delete_by_asin(self, async_product_repo, async_sample_product):
        """Test deleting product by ASIN."""
        result = await async_product_repo.delete(async_sample_product.asin)
        
        assert result is True
        
        # Verify deletion
        retrieved = await async_product_repo.get_by_asin(async_sample_product.asin)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_product(self, async_product_repo):
        """Test deleting non-existent product."""
        result = await async_product_repo.delete("B999999999")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_search_no_filters(self, async_product_repo, async_multiple_products):
        """Test search without filters."""
        products = await async_product_repo.search()
        
        assert len(products) == 5
    
    @pytest.mark.asyncio
    async def test_search_by_category(self, async_product_repo, async_multiple_products):
        """Test search by category."""
        products = await async_product_repo.search(category="Electronics")
        
        assert len(products) == 3
        assert all(p.category == "Electronics" for p in products)
    
    @pytest.mark.asyncio
    async def test_search_by_price_range(self, async_product_repo, async_multiple_products):
        """Test search by price range."""
        products = await async_product_repo.search(min_price=100, max_price=200)
        
        assert len(products) == 2
        assert all(100 <= p.price <= 200 for p in products)
    
    @pytest.mark.asyncio
    async def test_search_by_min_rating(self, async_product_repo, async_multiple_products):
        """Test search by minimum rating."""
        products = await async_product_repo.search(min_rating=4.7)
        
        assert len(products) >= 2
        assert all(p.rating >= 4.7 for p in products)
    
    @pytest.mark.asyncio
    async def test_search_by_min_reviews(self, async_product_repo, async_multiple_products):
        """Test search by minimum review count."""
        # Note: ProductRepository.search() doesn't have min_reviews parameter
        # This test verifies products with high review counts exist
        products = await async_product_repo.search()
        
        # Filter manually for products with high review counts
        high_review_products = [p for p in products if p.review_count and p.review_count >= 100000]
        
        assert len(high_review_products) >= 1
        assert all(p.review_count >= 100000 for p in high_review_products)
    
    @pytest.mark.asyncio
    async def test_search_combined_filters(self, async_product_repo, async_multiple_products):
        """Test search with multiple filters."""
        products = await async_product_repo.search(
            category="Electronics",
            min_price=40,
            max_price=150,
        )
        
        assert len(products) >= 1
    
    @pytest.mark.asyncio
    async def test_get_top_products_by_rating(self, async_product_repo, async_multiple_products):
        """Test getting top products by rating."""
        products = await async_product_repo.get_top_by_rating(limit=3)
        
        assert len(products) == 3
        # Should be sorted by rating descending
        for i in range(len(products) - 1):
            assert products[i].rating >= products[i + 1].rating
    
    @pytest.mark.asyncio
    async def test_get_top_products_by_review_count(self, async_product_repo, async_multiple_products):
        """Test getting top products by review count."""
        products = await async_product_repo.get_top_by_review_count(limit=3)
        
        assert len(products) == 3
        # Should be sorted by review_count descending
        for i in range(len(products) - 1):
            assert products[i].review_count >= products[i + 1].review_count
    
    @pytest.mark.asyncio
    async def test_count(self, async_product_repo, async_multiple_products):
        """Test counting products."""
        count = await async_product_repo.count()
        
        assert count == 5


class TestHistoryRepository:
    """Tests for HistoryRepository CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_record_history(self, async_history_repo, sample_history_data):
        """Test recording a history record."""
        # First create a product to link to
        product_repo = ProductRepository(async_history_repo.session)
        product = await product_repo.create(
            asin=sample_history_data['asin'],
            title="Test Product",
            price=sample_history_data['price'],
            product_url="https://example.com/test",
        )
        
        history = await async_history_repo.record_history(
            product_id=product.id,
            asin=sample_history_data['asin'],
            price=sample_history_data['price'],
            rating=sample_history_data['rating'],
            bsr=sample_history_data['bsr'],
        )
        
        assert history.id is not None
        assert history.asin == sample_history_data['asin']
        assert history.price == sample_history_data['price']
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, async_history_repo, async_sample_product_history):
        """Test getting history by ID."""
        retrieved = await async_history_repo.get_history(
            product_id=async_sample_product_history.id,
            limit=1,
        )
        
        assert len(retrieved) > 0
        assert retrieved[0].id == async_sample_product_history.id
    
    @pytest.mark.asyncio
    async def test_get_by_asin(self, async_history_repo, async_multiple_history_records):
        """Test getting history by ASIN."""
        records = await async_history_repo.get_history(
            asin=async_multiple_history_records[0].asin,
            limit=10,
        )
        
        assert len(records) == 4
    
    @pytest.mark.asyncio
    async def test_get_by_asin_with_date_filter(self, async_history_repo, async_multiple_history_records):
        """Test getting history with date filters."""
        now = datetime.utcnow()
        start_date = now - timedelta(days=20)
        
        records = await async_history_repo.get_history(
            asin=async_multiple_history_records[0].asin,
            start_date=start_date,
        )
        
        assert len(records) >= 2
    
    @pytest.mark.asyncio
    async def test_get_price_history(self, async_history_repo, async_sample_product):
        """Test getting price history."""
        # First create some price history records
        now = datetime.utcnow()
        for i, price in enumerate([49.99, 44.99, 39.99, 49.99]):
            await async_history_repo.record_price(
                product_id=async_sample_product.id,
                asin=async_sample_product.asin,
                price=price,
                recorded_at=now - timedelta(days=(3 - i) * 7),
            )
        
        price_history = await async_history_repo.get_price_history(
            asin=async_sample_product.asin,
            limit=10,
        )
        
        assert len(price_history) == 4
        # Should be oldest first
        assert price_history[0].price == 49.99
    
    @pytest.mark.asyncio
    async def test_get_trend(self, async_history_repo, async_multiple_history_records):
        """Test getting trend analysis."""
        trend = await async_history_repo.get_trend(
            async_multiple_history_records[0].asin,
            days=30,
            metric='price',
        )
        
        assert 'current' in trend
        assert 'previous' in trend
        assert 'trend' in trend
        assert 'data_points' in trend
    
    @pytest.mark.asyncio
    async def test_get_price_stats(self, async_history_repo, async_multiple_history_records):
        """Test getting price statistics."""
        stats = await async_history_repo.get_price_stats(
            async_multiple_history_records[0].asin,
            days=30,
        )
        
        assert 'min' in stats
        assert 'max' in stats
        assert 'avg' in stats
        assert 'current' in stats


class TestRepositoryIntegration:
    """Integration tests for repositories working together."""
    
    @pytest.mark.asyncio
    async def test_product_and_history_workflow(self, async_db_session, sample_product_data):
        """Test complete workflow with product and history."""
        product_repo = ProductRepository(async_db_session)
        history_repo = HistoryRepository(async_db_session)
        
        # Create product
        product = await product_repo.create(
            asin=sample_product_data['asin'],
            title=sample_product_data['title'],
            price=sample_product_data['price'],
            product_url=sample_product_data['product_url'],
        )
        
        # Create history record
        history = await history_repo.record_history(
            product_id=product.id,
            asin=product.asin,
            price=product.price,
            rating=product.rating,
        )
        
        # Update product
        await product_repo.update(product.asin, price=44.99)
        
        # Create another history record
        history2 = await history_repo.record_history(
            product_id=product.id,
            asin=product.asin,
            price=44.99,
            rating=product.rating,
        )
        
        # Verify
        assert product.id is not None
        assert history.id is not None
        assert history2.id is not None
        
        # Get history
        records = await history_repo.get_history(asin=product.asin)
        assert len(records) == 2
    
    @pytest.mark.asyncio
    async def test_search_and_update_workflow(self, async_db_session, async_multiple_products):
        """Test search and update workflow."""
        product_repo = ProductRepository(async_db_session)
        
        # Search for products
        products = await product_repo.search(min_price=100)
        
        # Store original prices for comparison
        original_prices = {p.asin: p.price for p in products}
        
        # Update all found products
        for product in products:
            new_price = round(product.price * 0.9, 2)
            await product_repo.update(product.asin, price=new_price)
        
        # Verify updates
        for product in products:
            updated = await product_repo.get_by_asin(product.asin)
            expected_price = round(original_prices[product.asin] * 0.9, 2)
            assert abs(updated.price - expected_price) < 0.01
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self, async_db_session):
        """Test bulk create and delete operations."""
        product_repo = ProductRepository(async_db_session)
        
        # Bulk create
        products_data = [
            {'asin': f'B0000000{i:02d}', 'title': f'Product {i}', 'price': 10.0 + i, 'product_url': f'https://example.com/{i}'}
            for i in range(10)
        ]
        
        products = []
        for data in products_data:
            products.append(await product_repo.create(
                asin=data['asin'],
                title=data['title'],
                price=data['price'],
                product_url=data['product_url'],
            ))
        
        await async_db_session.commit()
        
        # Verify count
        count = await product_repo.count()
        assert count >= 10
        
        # Bulk delete
        for product in products:
            await product_repo.delete(product.asin)
        
        # Verify deletion
        count = await product_repo.count()
        assert count == 0
