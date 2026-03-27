"""
Pytest Configuration and Fixtures for Amazon Selector v2.2

Provides shared fixtures, test database configuration, and cleanup utilities.
Supports both synchronous and asynchronous test patterns.
"""
import pytest
import pytest_asyncio
import os
from typing import Generator, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.models import (
    Base,
    Product,
    ProductImage,
    ProductFeature,
    ProductHistory,
    PriceHistory,
    BSRHistory,
)
from src.db.repositories import ProductRepository, HistoryRepository


# ==================== Test Database Configuration ====================

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


# ==================== Async Database Fixtures ====================

@pytest_asyncio.fixture(scope="function")
async def async_test_engine():
    """
    Create in-memory SQLite async database engine for testing.
    
    Returns:
        Async SQLAlchemy engine instance
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_db_session(async_test_engine) -> Generator[AsyncSession, None, None]:
    """
    Create a new async database session for each test.
    
    Yields:
        Async SQLAlchemy session instance
        
    Example:
        async def test_example(async_db_session):
            repo = ProductRepository(async_db_session)
            product = await repo.create(...)
    """
    # Create async session factory
    async_session_factory = async_sessionmaker(
        bind=async_test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture
async def async_product_repo(async_db_session) -> ProductRepository:
    """
    Get ProductRepository with async test session.
    
    Returns:
        ProductRepository instance
    """
    return ProductRepository(async_db_session)


@pytest_asyncio.fixture
async def async_history_repo(async_db_session) -> HistoryRepository:
    """
    Get HistoryRepository with async test session.
    
    Returns:
        HistoryRepository instance
    """
    return HistoryRepository(async_db_session)


# Note: Sync database fixtures removed - all tests now use async fixtures
# TEST_SYNC_DATABASE_URL kept for backward compatibility if needed


# Note: Use async_product_repo and async_history_repo instead
# Sync repositories are not supported as all repository methods are async


# ==================== Test Data Fixtures ====================

@pytest.fixture
def sample_product_data() -> Dict[str, Any]:
    """
    Sample product data for testing.
    
    Returns:
        Dictionary with valid product data
    """
    return {
        "asin": "B08N5WRWNW",
        "title": "Echo Dot (4th Gen) | Smart speaker with Alexa | Charcoal",
        "price": 49.99,
        "rating": 4.7,
        "review_count": 254891,
        "bsr": 12,
        "category": "Electronics",
        "image_url": "https://example.com/images/echo-dot.jpg",
        "product_url": "https://amazon.com/dp/B08N5WRWNW",
    }


@pytest.fixture
def sample_history_data(sample_product_data) -> Dict[str, Any]:
    """
    Sample history data for testing (alias for sample_product_history_data).
    
    Returns:
        Dictionary with valid history data
    """
    return {
        "asin": sample_product_data["asin"],
        "price": 49.99,
        "rating": 4.7,
        "review_count": 254891,
        "bsr": 12,
        "recorded_at": datetime.utcnow(),
    }


# Alias for backward compatibility
sample_product_history_data = sample_history_data


@pytest_asyncio.fixture
async def async_sample_product(async_db_session, sample_product_data) -> Product:
    """
    Create and return a sample product in the database (async version).
    
    Returns:
        Product instance
    """
    repo = ProductRepository(async_db_session)
    return await repo.create(
        asin=sample_product_data["asin"],
        title=sample_product_data["title"],
        price=sample_product_data["price"],
        product_url=sample_product_data["product_url"],
        rating=sample_product_data["rating"],
        review_count=sample_product_data["review_count"],
        bsr=sample_product_data["bsr"],
        category=sample_product_data["category"],
        image_url=sample_product_data["image_url"],
    )


@pytest_asyncio.fixture
async def sample_product(async_db_session, sample_product_data) -> Product:
    """
    Create and return a sample product in the database.
    
    Returns:
        Product instance
    """
    repo = ProductRepository(async_db_session)
    return await repo.create(
        asin=sample_product_data["asin"],
        title=sample_product_data["title"],
        price=sample_product_data["price"],
        product_url=sample_product_data["product_url"],
        rating=sample_product_data["rating"],
        review_count=sample_product_data["review_count"],
        bsr=sample_product_data["bsr"],
        category=sample_product_data["category"],
        image_url=sample_product_data["image_url"],
    )


@pytest_asyncio.fixture
async def async_multiple_products(async_db_session) -> List[Product]:
    """Create multiple sample products in the database (async version)."""
    repo = ProductRepository(async_db_session)
    products_data = [
        {"asin": "B08N5WRWNW", "title": "Echo Dot (4th Gen)", "price": 49.99, "rating": 4.7, "review_count": 254891, "bsr": 12, "category": "Electronics", "product_url": "https://amazon.com/dp/B08N5WRWNW"},
        {"asin": "B07XJ8C8F5", "title": "Echo Show 8 (2nd Gen)", "price": 129.99, "rating": 4.6, "review_count": 89234, "bsr": 45, "category": "Electronics", "product_url": "https://amazon.com/dp/B07XJ8C8F5"},
        {"asin": "B09B8V1LZ3", "title": "Echo Show 15", "price": 249.99, "rating": 4.5, "review_count": 12456, "bsr": 156, "category": "Electronics", "product_url": "https://amazon.com/dp/B09B8V1LZ3"},
        {"asin": "B07HZLHPKP", "title": "Instant Pot Duo 7-in-1", "price": 89.99, "rating": 4.8, "review_count": 156789, "bsr": 3, "category": "Home & Kitchen", "product_url": "https://amazon.com/dp/B07HZLHPKP"},
        {"asin": "B08J6F1K3L", "title": "Ninja Air Fryer", "price": 119.99, "rating": 4.7, "review_count": 98234, "bsr": 8, "category": "Home & Kitchen", "product_url": "https://amazon.com/dp/B08J6F1K3L"},
    ]
    
    products = []
    for data in products_data:
        products.append(await repo.create(
            asin=data["asin"],
            title=data["title"],
            price=data["price"],
            product_url=data["product_url"],
            rating=data.get("rating"),
            review_count=data.get("review_count"),
            bsr=data.get("bsr"),
            category=data.get("category"),
        ))
    
    await async_db_session.commit()
    return products


@pytest_asyncio.fixture
async def multiple_products(async_db_session) -> List[Product]:
    """Create multiple sample products in the database."""
    repo = ProductRepository(async_db_session)
    products_data = [
        {"asin": "B08N5WRWNW", "title": "Echo Dot (4th Gen)", "price": 49.99, "rating": 4.7, "review_count": 254891, "bsr": 12, "category": "Electronics", "product_url": "https://amazon.com/dp/B08N5WRWNW"},
        {"asin": "B07XJ8C8F5", "title": "Echo Show 8 (2nd Gen)", "price": 129.99, "rating": 4.6, "review_count": 89234, "bsr": 45, "category": "Electronics", "product_url": "https://amazon.com/dp/B07XJ8C8F5"},
        {"asin": "B09B8V1LZ3", "title": "Echo Show 15", "price": 249.99, "rating": 4.5, "review_count": 12456, "bsr": 156, "category": "Electronics", "product_url": "https://amazon.com/dp/B09B8V1LZ3"},
        {"asin": "B07HZLHPKP", "title": "Instant Pot Duo 7-in-1", "price": 89.99, "rating": 4.8, "review_count": 156789, "bsr": 3, "category": "Home & Kitchen", "product_url": "https://amazon.com/dp/B07HZLHPKP"},
        {"asin": "B08J6F1K3L", "title": "Ninja Air Fryer", "price": 119.99, "rating": 4.7, "review_count": 98234, "bsr": 8, "category": "Home & Kitchen", "product_url": "https://amazon.com/dp/B08J6F1K3L"},
    ]
    
    products = []
    for data in products_data:
        products.append(await repo.create(
            asin=data["asin"],
            title=data["title"],
            price=data["price"],
            product_url=data["product_url"],
            rating=data.get("rating"),
            review_count=data.get("review_count"),
            bsr=data.get("bsr"),
            category=data.get("category"),
        ))
    
    await async_db_session.commit()
    return products


@pytest_asyncio.fixture
async def async_sample_product_history(async_db_session, async_sample_product) -> ProductHistory:
    """Create and return a sample history record (async version)."""
    repo = HistoryRepository(async_db_session)
    return await repo.record_history(
        product_id=async_sample_product.id,
        asin=async_sample_product.asin,
        price=async_sample_product.price,
        rating=async_sample_product.rating,
        bsr=async_sample_product.bsr,
    )


@pytest_asyncio.fixture
async def sample_product_history(async_db_session, sample_product) -> ProductHistory:
    """Create and return a sample history record."""
    repo = HistoryRepository(async_db_session)
    return await repo.record_history(
        product_id=sample_product.id,
        asin=sample_product.asin,
        price=sample_product.price,
        rating=sample_product.rating,
        bsr=sample_product.bsr,
    )


# Alias for backward compatibility
sample_history = sample_product_history


@pytest_asyncio.fixture
async def async_multiple_history_records(async_db_session, async_sample_product) -> List[ProductHistory]:
    """Create multiple history records for testing (async version)."""
    repo = HistoryRepository(async_db_session)
    now = datetime.utcnow()
    
    records = []
    for i, price in enumerate([49.99, 44.99, 39.99, 49.99]):
        record = await repo.record_history(
            product_id=async_sample_product.id,
            asin=async_sample_product.asin,
            price=price,
            rating=async_sample_product.rating,
            bsr=async_sample_product.bsr,
            recorded_at=now - timedelta(days=(3 - i) * 7),
        )
        records.append(record)
    
    return records


@pytest_asyncio.fixture
async def multiple_history_records(async_db_session, sample_product) -> List[ProductHistory]:
    """Create multiple history records for testing."""
    repo = HistoryRepository(async_db_session)
    now = datetime.utcnow()
    
    records = []
    for i, price in enumerate([49.99, 44.99, 39.99, 49.99]):
        record = await repo.record_history(
            product_id=sample_product.id,
            asin=sample_product.asin,
            price=price,
            rating=sample_product.rating,
            bsr=sample_product.bsr,
            recorded_at=now - timedelta(days=(3 - i) * 7),
        )
        records.append(record)
    
    return records


@pytest_asyncio.fixture
async def sample_price_history(async_db_session, sample_product) -> PriceHistory:
    """Create and return a sample price history record."""
    repo = HistoryRepository(async_db_session)
    return await repo.record_price(
        product_id=sample_product.id,
        asin=sample_product.asin,
        price=sample_product.price,
    )


@pytest_asyncio.fixture
async def sample_bsr_history(async_db_session, sample_product) -> BSRHistory:
    """Create and return a sample BSR history record."""
    repo = HistoryRepository(async_db_session)
    return await repo.record_bsr(
        product_id=sample_product.id,
        asin=sample_product.asin,
        bsr=sample_product.bsr,
    )


# ==================== Cleanup Fixtures ====================

@pytest_asyncio.fixture(autouse=True)
async def async_clean_database(async_db_session):
    """
    Automatically clean database after each async test.
    
    This fixture runs automatically for every async test to ensure isolation.
    """
    yield
    
    # Rollback any pending transactions
    await async_db_session.rollback()
    
    # Delete all records from all tables (in correct order due to FK)
    await async_db_session.execute(ProductHistory.__table__.delete())
    await async_db_session.execute(PriceHistory.__table__.delete())
    await async_db_session.execute(BSRHistory.__table__.delete())
    await async_db_session.execute(ProductFeature.__table__.delete())
    await async_db_session.execute(ProductImage.__table__.delete())
    await async_db_session.execute(Product.__table__.delete())
    await async_db_session.commit()


# Note: Only async_clean_database is used now since all fixtures are async
# The sync clean_database fixture has been removed as all tests use async fixtures


# ==================== Utility Fixtures ====================

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """
    Test configuration dictionary.
    
    Returns:
        Configuration for test environment
    """
    return {
        "database_url": TEST_SYNC_DATABASE_URL,
        "test_mode": True,
        "debug": True,
    }
