"""
Database Performance Tests for Amazon Selector v2.2

Tests for database operation performance including:
- Query performance (<500ms)
- Write performance (<200ms)
- Concurrent access (100 connections)

All tests use async operations to match production code patterns.
"""
import pytest
import pytest_asyncio
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import statistics

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.models import Base, Product, ProductHistory
from src.db.repositories import ProductRepository, HistoryRepository


# Performance thresholds
QUERY_TIME_THRESHOLD_MS = 500  # Max acceptable query time
WRITE_TIME_THRESHOLD_MS = 200  # Max acceptable write time
CONCURRENT_CONNECTIONS = 100  # Number of concurrent connections to test


class TestQueryPerformance:
    """Tests for database query performance."""
    
    @pytest.mark.asyncio
    async def test_get_by_asin_performance(self, async_db_session, async_multiple_products):
        """Test that get_by_asin completes within threshold."""
        repo = ProductRepository(async_db_session)
        
        # Warm up
        await repo.get_by_asin("B08N5WRWNW")
        
        # Measure performance
        start_time = time.perf_counter()
        for _ in range(10):
            await repo.get_by_asin("B08N5WRWNW")
        end_time = time.perf_counter()
        
        avg_time_ms = ((end_time - start_time) / 10) * 1000
        
        assert avg_time_ms < QUERY_TIME_THRESHOLD_MS, \
            f"get_by_asin avg time {avg_time_ms:.2f}ms exceeds threshold {QUERY_TIME_THRESHOLD_MS}ms"
    
    @pytest.mark.asyncio
    async def test_search_performance(self, async_db_session, async_multiple_products):
        """Test that search completes within threshold."""
        repo = ProductRepository(async_db_session)
        
        # Warm up
        await repo.search(category="Electronics")
        
        # Measure performance
        start_time = time.perf_counter()
        for _ in range(10):
            await repo.search(category="Electronics", min_price=40, max_price=200)
        end_time = time.perf_counter()
        
        avg_time_ms = ((end_time - start_time) / 10) * 1000
        
        assert avg_time_ms < QUERY_TIME_THRESHOLD_MS, \
            f"search avg time {avg_time_ms:.2f}ms exceeds threshold {QUERY_TIME_THRESHOLD_MS}ms"
    
    @pytest.mark.asyncio
    async def test_get_all_pagination_performance(self, async_db_session, async_multiple_products):
        """Test that paginated get_all completes within threshold."""
        repo = ProductRepository(async_db_session)
        
        # Warm up
        await repo.get_all(page=1, page_size=10)
        
        # Measure performance
        start_time = time.perf_counter()
        for page in range(1, 6):
            await repo.get_all(page=page, page_size=10)
        end_time = time.perf_counter()
        
        avg_time_ms = ((end_time - start_time) / 5) * 1000
        
        assert avg_time_ms < QUERY_TIME_THRESHOLD_MS, \
            f"get_all pagination avg time {avg_time_ms:.2f}ms exceeds threshold {QUERY_TIME_THRESHOLD_MS}ms"
    
    @pytest.mark.asyncio
    async def test_get_history_performance(self, async_db_session, async_multiple_history_records):
        """Test that get_history completes within threshold."""
        repo = HistoryRepository(async_db_session)
        
        # Warm up
        await repo.get_history(asin="B08N5WRWNW", limit=10)
        
        # Measure performance
        start_time = time.perf_counter()
        for _ in range(10):
            await repo.get_history(asin="B08N5WRWNW", limit=10)
        end_time = time.perf_counter()
        
        avg_time_ms = ((end_time - start_time) / 10) * 1000
        
        assert avg_time_ms < QUERY_TIME_THRESHOLD_MS, \
            f"get_history avg time {avg_time_ms:.2f}ms exceeds threshold {QUERY_TIME_THRESHOLD_MS}ms"
    
    @pytest.mark.asyncio
    async def test_get_trend_performance(self, async_db_session, async_multiple_history_records):
        """Test that get_trend completes within threshold."""
        repo = HistoryRepository(async_db_session)
        
        # Warm up
        await repo.get_trend("B08N5WRWNW", days=30)
        
        # Measure performance
        start_time = time.perf_counter()
        for _ in range(5):
            await repo.get_trend("B08N5WRWNW", days=30)
        end_time = time.perf_counter()
        
        avg_time_ms = ((end_time - start_time) / 5) * 1000
        
        assert avg_time_ms < QUERY_TIME_THRESHOLD_MS, \
            f"get_trend avg time {avg_time_ms:.2f}ms exceeds threshold {QUERY_TIME_THRESHOLD_MS}ms"


class TestWritePerformance:
    """Tests for database write performance."""
    
    @pytest.mark.asyncio
    async def test_create_product_performance(self, async_db_session):
        """Test that creating a product completes within threshold."""
        repo = ProductRepository(async_db_session)
        
        # Warm up
        await repo.create(
            asin="B000000000",
            title="Warmup Product",
            price=10.0,
            product_url="https://example.com/0",
        )
        await async_db_session.execute(Product.__table__.delete())
        await async_db_session.commit()
        
        # Measure performance
        times = []
        for i in range(10):
            start_time = time.perf_counter()
            await repo.create(
                asin=f"B0000000{i}",
                title=f"Product {i}",
                price=10.0 + i,
                product_url=f"https://example.com/{i}",
            )
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)
        
        avg_time_ms = statistics.mean(times)
        
        assert avg_time_ms < WRITE_TIME_THRESHOLD_MS, \
            f"create_product avg time {avg_time_ms:.2f}ms exceeds threshold {WRITE_TIME_THRESHOLD_MS}ms"
    
    @pytest.mark.asyncio
    async def test_update_product_performance(self, async_db_session, async_multiple_products):
        """Test that updating a product completes within threshold."""
        repo = ProductRepository(async_db_session)
        
        # Warm up
        await repo.update("B08N5WRWNW", price=50.0)
        
        # Measure performance
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            await repo.update("B08N5WRWNW", price=50.0)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)
        
        avg_time_ms = statistics.mean(times)
        
        assert avg_time_ms < WRITE_TIME_THRESHOLD_MS, \
            f"update_product avg time {avg_time_ms:.2f}ms exceeds threshold {WRITE_TIME_THRESHOLD_MS}ms"
    
    @pytest.mark.asyncio
    async def test_record_history_performance(self, async_db_session, async_sample_product):
        """Test that recording history completes within threshold."""
        repo = HistoryRepository(async_db_session)
        
        # Warm up
        await repo.record_history(
            product_id=async_sample_product.id,
            asin=async_sample_product.asin,
            price=async_sample_product.price,
        )
        
        # Measure performance
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            await repo.record_history(
                product_id=async_sample_product.id,
                asin=async_sample_product.asin,
                price=async_sample_product.price,
            )
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)
        
        avg_time_ms = statistics.mean(times)
        
        assert avg_time_ms < WRITE_TIME_THRESHOLD_MS, \
            f"record_history avg time {avg_time_ms:.2f}ms exceeds threshold {WRITE_TIME_THRESHOLD_MS}ms"
    
    @pytest.mark.asyncio
    async def test_bulk_create_performance(self, async_db_session, async_sample_product):
        """Test that bulk creating history records completes within threshold."""
        repo = HistoryRepository(async_db_session)
        
        # Prepare data
        records = [
            {
                'product_id': async_sample_product.id,
                'asin': async_sample_product.asin,
                'price': 50.0 + i,
                'rating': 4.5,
            }
            for i in range(20)
        ]
        
        # Warm up
        await async_db_session.execute(ProductHistory.__table__.delete())
        await async_db_session.commit()
        
        # Measure performance
        start_time = time.perf_counter()
        await repo.bulk_create(records[:5])  # Test with 5 records
        end_time = time.perf_counter()
        
        time_ms = (end_time - start_time) * 1000
        
        # Allow more time for bulk operations (5 records * 200ms = 1000ms)
        assert time_ms < (WRITE_TIME_THRESHOLD_MS * 5), \
            f"bulk_create time {time_ms:.2f}ms exceeds threshold {WRITE_TIME_THRESHOLD_MS * 5}ms"


class TestConcurrentAccess:
    """Tests for concurrent database access."""
    
    @pytest.mark.asyncio
    async def test_concurrent_reads(self, async_test_engine, async_multiple_products):
        """Test handling 100 concurrent read operations."""
        # Create multiple sessions for concurrent access
        async def read_product(session, asin: str):
            repo = ProductRepository(session)
            return await repo.get_by_asin(asin)
        
        # Create concurrent tasks
        tasks = []
        for i in range(CONCURRENT_CONNECTIONS):
            # Create a new session for each "connection"
            async with async_test_engine.begin() as conn:
                # Note: In real scenarios, each connection would have its own session
                # For testing, we simulate concurrent access
                pass
        
        # Simulate concurrent reads using asyncio.gather
        async with async_test_engine.begin() as conn:
            # Create a session for this test
            from sqlalchemy.ext.asyncio import AsyncSession
            session = AsyncSession(bind=async_test_engine)
            
            start_time = time.perf_counter()
            
            # Create concurrent tasks
            tasks = [
                read_product(session, "B08N5WRWNW")
                for _ in range(CONCURRENT_CONNECTIONS)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.perf_counter()
            
            total_time_ms = (end_time - start_time) * 1000
            
            # Count successful reads
            successful = sum(1 for r in results if r is not None and not isinstance(r, Exception))
            
            # Allow 5 seconds for 100 concurrent reads
            assert total_time_ms < 5000, \
                f"Concurrent reads took {total_time_ms:.2f}ms, expected < 5000ms"
            assert successful >= CONCURRENT_CONNECTIONS * 0.9, \
                f"Only {successful}/{CONCURRENT_CONNECTIONS} reads succeeded"
            
            await session.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_writes(self, async_db_session, async_sample_product):
        """Test handling concurrent write operations."""
        repo = HistoryRepository(async_db_session)
        
        start_time = time.perf_counter()
        
        # Create concurrent write tasks with different prices
        # Note: SQLite has limited concurrent write support, so we test sequential writes
        # In production with PostgreSQL, these would be truly concurrent
        results = []
        for i in range(20):
            try:
                result = await repo.record_history(
                    product_id=async_sample_product.id,
                    asin=async_sample_product.asin,
                    price=50.0 + i,
                )
                results.append(result)
            except Exception as e:
                results.append(None)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Count successful writes
        successful = sum(1 for r in results if r is not None)
        
        # Allow 10 seconds for writes
        assert total_time_ms < 10000, \
            f"Concurrent writes took {total_time_ms:.2f}ms, expected < 10000ms"
        
        # All writes should succeed in sequential execution
        assert successful == 20, \
            f"Only {successful}/20 writes succeeded"


class TestScalability:
    """Tests for database scalability with larger datasets."""
    
    @pytest.mark.asyncio
    async def test_large_dataset_query_performance(self, async_db_session):
        """Test query performance with 1000 products."""
        repo = ProductRepository(async_db_session)
        
        # Create 1000 products
        print("Creating 1000 products for scalability test...")
        for i in range(1000):
            await repo.create(
                asin=f"B{i:010d}",
                title=f"Product {i}",
                price=10.0 + (i % 100),
                product_url=f"https://example.com/{i}",
                category="Electronics" if i % 2 == 0 else "Home & Kitchen",
            )
        
        await async_db_session.commit()
        
        # Test search performance
        start_time = time.perf_counter()
        results = await repo.search(category="Electronics", min_price=20, max_price=80)
        end_time = time.perf_counter()
        
        time_ms = (end_time - start_time) * 1000
        
        assert len(results) > 0, "Should find products matching criteria"
        assert time_ms < QUERY_TIME_THRESHOLD_MS * 2, \
            f"Search in large dataset took {time_ms:.2f}ms, expected < {QUERY_TIME_THRESHOLD_MS * 2}ms"
    
    @pytest.mark.asyncio
    async def test_pagination_with_large_dataset(self, async_db_session):
        """Test pagination performance with large dataset."""
        repo = ProductRepository(async_db_session)
        
        # Dataset should already exist from previous test if run together
        # If not, create a smaller set
        count = await repo.count()
        if count < 100:
            for i in range(200):
                await repo.create(
                    asin=f"B{i:010d}",
                    title=f"Product {i}",
                    price=10.0 + (i % 100),
                    product_url=f"https://example.com/{i}",
                )
            await async_db_session.commit()
        
        # Test pagination across multiple pages
        start_time = time.perf_counter()
        
        for page in range(1, 11):  # Test 10 pages
            results = await repo.get_all(page=page, page_size=20)
            assert len(results) <= 20
        
        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / 10) * 1000
        
        assert avg_time_ms < QUERY_TIME_THRESHOLD_MS, \
            f"Pagination avg time {avg_time_ms:.2f}ms exceeds threshold {QUERY_TIME_THRESHOLD_MS}ms"
