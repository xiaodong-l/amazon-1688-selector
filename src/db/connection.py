"""
Database Connection Management for Amazon Selector v2.2

Handles database engine creation, session management, and connection pooling.
Supports both sync and async SQLAlchemy 2.0 APIs.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.pool import StaticPool, QueuePool, AsyncAdaptedQueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from typing import Optional, Generator, AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
import os
import logging

from .models import Base

# Configure logging for database operations
logger = logging.getLogger(__name__)

# Global engine and session factory (sync)
_engine = None
_SessionFactory = None
_Session = None

# Global async engine and session factory
_async_engine = None
_AsyncSessionFactory = None


def get_database_url(test_mode: bool = False, async_mode: bool = False) -> str:
    """
    Get database URL based on environment or test mode.
    
    Args:
        test_mode: If True, use SQLite in-memory database
        async_mode: If True, return async-compatible URL
        
    Returns:
        Database URL string
    """
    if test_mode:
        if async_mode:
            return "sqlite+aiosqlite:///:memory:"
        return "sqlite:///:memory:"
    
    # Check for environment variable
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Convert sync URL to async URL if needed
        if async_mode:
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("sqlite:///"):
                db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return db_url
    
    # Default to SQLite file-based database
    db_path = os.getenv("DB_FILE", "amazon_selector.db")
    if async_mode:
        return f"sqlite+aiosqlite:///{db_path}"
    return f"sqlite:///{db_path}"


# Sync Engine Functions

def get_engine(test_mode: bool = False, pool_size: int = 5, max_overflow: int = 10):
    """
    Get or create synchronous database engine.
    
    Args:
        test_mode: Use in-memory SQLite for testing
        pool_size: Number of connections to keep in pool
        max_overflow: Max connections beyond pool_size
        
    Returns:
        SQLAlchemy engine instance
    """
    global _engine
    
    if _engine is None:
        db_url = get_database_url(test_mode)
        
        if test_mode or db_url.startswith("sqlite:///:memory:"):
            # SQLite in-memory needs StaticPool and check_same_thread=False
            _engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
            )
        else:
            # PostgreSQL or other databases with connection pooling
            _engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
            )
    
    return _engine


def get_session_factory():
    """Get or create synchronous session factory."""
    global _SessionFactory
    
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    
    return _SessionFactory


def get_session() -> scoped_session:
    """
    Get a new synchronous database session.
    
    Returns:
        Scoped session instance
    """
    global _Session
    
    if _Session is None:
        factory = get_session_factory()
        _Session = scoped_session(factory)
    
    return _Session


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for synchronous database sessions.
    
    Yields:
        Session instance
        
    Example:
        with get_db_session() as session:
            products = session.query(Product).all()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for asynchronous database sessions.
    
    Yields:
        AsyncSession instance
        
    Example:
        async with get_async_db_session() as session:
            products = await session.execute(select(Product))
    """
    async_session = await get_async_session()
    try:
        yield async_session
        await async_session.commit()
    except Exception:
        await async_session.rollback()
        raise
    finally:
        await async_session.close()


# Async Engine Functions (SQLAlchemy 2.0)

def get_async_engine(test_mode: bool = False, pool_size: int = 5, max_overflow: int = 10):
    """
    Get or create asynchronous database engine.
    
    Args:
        test_mode: Use in-memory SQLite for testing
        pool_size: Number of connections to keep in pool
        max_overflow: Max connections beyond pool_size
        
    Returns:
        Async SQLAlchemy engine instance
    """
    global _async_engine
    
    if _async_engine is None:
        db_url = get_database_url(test_mode, async_mode=True)
        
        if test_mode or "memory" in db_url:
            # SQLite async needs specific configuration
            _async_engine = create_async_engine(
                db_url,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
            )
        else:
            # PostgreSQL with asyncpg or other async databases
            _async_engine = create_async_engine(
                db_url,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
            )
    
    return _async_engine


def get_async_session_factory():
    """Get or create asynchronous session factory."""
    global _AsyncSessionFactory
    
    if _AsyncSessionFactory is None:
        engine = get_async_engine()
        _AsyncSessionFactory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    return _AsyncSessionFactory


# Convenience for dependency injection
AsyncSessionLocal = get_async_session_factory


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for asynchronous database sessions.
    
    Yields:
        AsyncSession instance
        
    Example:
        async with get_async_session() as session:
            products = await session.execute(select(Product))
    """
    async_session_factory = get_async_session_factory()
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Database Initialization

def init_db(test_mode: bool = False):
    """
    Initialize database tables (synchronous).
    
    Args:
        test_mode: If True, use test database configuration
    """
    engine = get_engine(test_mode)
    Base.metadata.create_all(bind=engine)


async def init_db_async(test_mode: bool = False):
    """
    Initialize database tables (asynchronous).
    
    Args:
        test_mode: If True, use test database configuration
    """
    engine = get_async_engine(test_mode)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def drop_db(test_mode: bool = False):
    """
    Drop all database tables (synchronous).
    
    Args:
        test_mode: If True, use test database configuration
    """
    engine = get_engine(test_mode)
    Base.metadata.drop_all(bind=engine)


async def drop_db_async(test_mode: bool = False):
    """
    Drop all database tables (asynchronous).
    
    Args:
        test_mode: If True, use test database configuration
    """
    engine = get_async_engine(test_mode)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def reset_db(test_mode: bool = False):
    """
    Reset database by dropping and recreating all tables (synchronous).
    
    Args:
        test_mode: If True, use test database configuration
        
    Returns:
        True if successful, False if failed
        
    Raises:
        OperationalError: If database connection fails
        SQLAlchemyError: If database operation fails
    """
    global _engine, _SessionFactory, _Session
    
    try:
        logger.info("Starting database reset...")
        
        # Step 1: Drop all tables
        logger.info("Dropping existing tables...")
        drop_db(test_mode)
        logger.info("Tables dropped successfully")
        
        # Step 2: Reinitialize tables
        logger.info("Creating new tables...")
        init_db(test_mode)
        logger.info("Tables created successfully")
        
        # Step 3: Reset global connections to ensure fresh state
        logger.info("Resetting connection pool...")
        close_all()
        logger.info("Database reset completed successfully")
        
        return True
        
    except OperationalError as e:
        logger.error(f"Database connection error during reset: {str(e)}")
        # Attempt rollback by reinitializing
        try:
            logger.info("Attempting recovery...")
            _engine = None  # Force engine recreation
            init_db(test_mode)
            logger.info("Recovery successful")
        except Exception as recovery_error:
            logger.error(f"Recovery failed: {str(recovery_error)}")
            raise
        raise
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error during database reset: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database reset: {str(e)}")
        raise


async def reset_db_async(test_mode: bool = False):
    """
    Reset database by dropping and recreating all tables (asynchronous).
    
    Args:
        test_mode: If True, use test database configuration
        
    Returns:
        True if successful, False if failed
        
    Raises:
        OperationalError: If database connection fails
        SQLAlchemyError: If database operation fails
    """
    global _async_engine, _AsyncSessionFactory
    
    try:
        logger.info("Starting async database reset...")
        
        # Step 1: Drop all tables
        logger.info("Dropping existing tables...")
        await drop_db_async(test_mode)
        logger.info("Tables dropped successfully")
        
        # Step 2: Reinitialize tables
        logger.info("Creating new tables...")
        await init_db_async(test_mode)
        logger.info("Tables created successfully")
        
        # Step 3: Reset global connections to ensure fresh state
        logger.info("Resetting async connection pool...")
        await close_all_async()
        logger.info("Async database reset completed successfully")
        
        return True
        
    except OperationalError as e:
        logger.error(f"Database connection error during async reset: {str(e)}")
        # Attempt rollback by reinitializing
        try:
            logger.info("Attempting recovery...")
            _async_engine = None  # Force engine recreation
            await init_db_async(test_mode)
            logger.info("Recovery successful")
        except Exception as recovery_error:
            logger.error(f"Recovery failed: {str(recovery_error)}")
            raise
        raise
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error during async database reset: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during async database reset: {str(e)}")
        raise


def close_all():
    """Close all synchronous database connections and reset globals."""
    global _engine, _SessionFactory, _Session
    
    if _Session is not None:
        _Session.remove()
    
    if _engine is not None:
        _engine.dispose()
    
    _engine = None
    _SessionFactory = None
    _Session = None


async def close_all_async():
    """Close all asynchronous database connections and reset globals."""
    global _async_engine, _AsyncSessionFactory
    
    if _async_engine is not None:
        await _async_engine.dispose()
    
    _async_engine = None
    _AsyncSessionFactory = None
