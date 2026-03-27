"""
Database Connection Tests for Amazon Selector v2.2

Tests for database connection, pooling, and session management.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.connection import (
    get_database_url,
    get_engine,
    get_session,
    get_db_session,
    init_db,
    drop_db,
    reset_db,
    close_all,
)
from src.db.models import Base


class TestDatabaseURL:
    """Tests for database URL configuration."""
    
    def test_get_database_url_test_mode(self):
        """Test database URL in test mode."""
        url = get_database_url(test_mode=True)
        assert url == "sqlite:///:memory:"
    
    def test_get_database_url_default(self, monkeypatch):
        """Test default database URL."""
        # Remove DATABASE_URL if set
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("DB_FILE", "test_default.db")
        
        url = get_database_url(test_mode=False)
        assert url == "sqlite:///test_default.db"


class TestEngineCreation:
    """Tests for engine creation and configuration."""
    
    def test_get_engine_test_mode(self):
        """Test getting engine in test mode."""
        # Reset global state
        close_all()
        
        engine = get_engine(test_mode=True)
        
        assert engine is not None
        assert engine.url.database == ":memory:"
        
        close_all()
    
    def test_get_engine_returns_same_instance(self):
        """Test that get_engine returns cached instance."""
        close_all()
        
        engine1 = get_engine(test_mode=True)
        engine2 = get_engine(test_mode=True)
        
        assert engine1 is engine2
        
        close_all()
    
    def test_get_engine_with_pool_config(self):
        """Test engine creation with pool configuration."""
        close_all()
        
        engine = get_engine(
            test_mode=False,
            pool_size=10,
            max_overflow=20,
        )
        
        # Should create engine (might be file-based SQLite)
        assert engine is not None
        
        close_all()


class TestConnection:
    """Tests for database connections."""
    
    def test_can_connect_to_database(self):
        """Test basic database connectivity."""
        engine = create_engine("sqlite:///:memory:")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row[0] == 1
        
        engine.dispose()
    
    def test_connection_with_transaction(self):
        """Test connection with transaction handling."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("INSERT INTO products (asin, title) VALUES ('B000000001', 'Test')"))
        
        # Verify data was committed
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM products"))
            count = result.fetchone()[0]
            assert count == 1
        
        engine.dispose()


class TestSessionManagement:
    """Tests for session management."""
    
    def test_get_db_session_context_manager(self):
        """Test database session context manager."""
        close_all()
        init_db(test_mode=True)
        
        with get_db_session() as session:
            assert session is not None
            # Session should be active
            assert session.bind is not None
        
        close_all()
    
    def test_get_db_session_auto_commit(self):
        """Test that context manager auto-commits on success."""
        close_all()
        init_db(test_mode=True)
        
        with get_db_session() as session:
            from src.db.models import Product
            product = Product(
                asin="B000000002",
                title="Auto Commit Test",
            )
            session.add(product)
            # Should auto-commit on exit
        
        # Verify data was committed
        with get_db_session() as session:
            from src.db.models import Product
            count = session.query(Product).count()
            assert count >= 1
        
        close_all()
    
    def test_get_db_session_rollback_on_error(self):
        """Test that context manager rolls back on error."""
        close_all()
        init_db(test_mode=True)
        
        try:
            with get_db_session() as session:
                from src.db.models import Product
                product = Product(
                    asin="B000000003",
                    title="Should Rollback",
                )
                session.add(product)
                # Raise error to trigger rollback
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify data was rolled back (no new products)
        with get_db_session() as session:
            from src.db.models import Product
            # Should not have the failed insert
            product = session.query(Product).filter(
                Product.asin == "B000000003"
            ).first()
            assert product is None
        
        close_all()


class TestDatabaseInitialization:
    """Tests for database initialization."""
    
    def test_init_db_creates_tables(self):
        """Test that init_db creates all tables."""
        close_all()
        init_db(test_mode=True)
        
        engine = get_engine(test_mode=True)
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert "products" in tables
        assert "history" in tables
        
        close_all()
    
    def test_drop_db_removes_tables(self):
        """Test that drop_db removes all tables."""
        close_all()
        init_db(test_mode=True)
        drop_db(test_mode=True)
        
        engine = get_engine(test_mode=True)
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert len(tables) == 0
        
        close_all()
    
    def test_reset_db_drops_and_creates(self):
        """Test that reset_db drops and recreates tables."""
        close_all()
        init_db(test_mode=True)
        
        # Add some data
        with get_db_session() as session:
            from src.db.models import Product
            session.add(Product(asin="B000000004", title="Before Reset"))
        
        # Reset
        reset_db(test_mode=True)
        
        # Data should be gone, tables should exist
        with get_db_session() as session:
            from src.db.models import Product
            count = session.query(Product).count()
            assert count == 0
        
        close_all()


class TestConnectionPooling:
    """Tests for connection pooling."""
    
    def test_static_pool_for_sqlite(self):
        """Test StaticPool usage for SQLite."""
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        
        assert engine.pool is not None
        assert isinstance(engine.pool, StaticPool)
        
        engine.dispose()
    
    def test_queue_pool_for_postgresql(self):
        """Test QueuePool for PostgreSQL-style databases."""
        # Simulate PostgreSQL URL
        engine = create_engine(
            "postgresql://user:pass@localhost/db",
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
        )
        
        assert engine.pool is not None
        assert isinstance(engine.pool, QueuePool)
        
        engine.dispose()


class TestCleanup:
    """Tests for cleanup operations."""
    
    def test_close_all_disposes_engine(self):
        """Test that close_all disposes engine."""
        close_all()
        get_engine(test_mode=True)
        
        # Engine should be created
        from src.db.connection import _engine
        assert _engine is not None
        
        close_all()
        
        # Engine should be reset
        from src.db.connection import _engine as engine_after
        assert engine_after is None
    
    def test_multiple_close_all_calls(self):
        """Test that close_all can be called multiple times."""
        # Should not raise errors
        close_all()
        close_all()
        close_all()
        
        assert True
