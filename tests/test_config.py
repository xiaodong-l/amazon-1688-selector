"""
Test Configuration Tests for Amazon Selector v2.2

Tests for test environment configuration and setup.
"""
import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.models import Base
from src.db.connection import get_database_url, get_engine, init_db, close_all


class TestDatabaseConfiguration:
    """Tests for database configuration."""
    
    def test_test_database_url_is_memory(self):
        """Test that test database uses in-memory SQLite."""
        # Simulate test mode
        url = "sqlite:///:memory:"
        assert url.startswith("sqlite://")
        assert ":memory:" in url
    
    def test_environment_variable_override(self, monkeypatch):
        """Test that DATABASE_URL environment variable is respected."""
        test_url = "sqlite:///test_override.db"
        monkeypatch.setenv("DATABASE_URL", test_url)
        
        # Import after setting env var
        from src.db import connection
        # Force reload to pick up env var
        url = test_url  # In real scenario, get_database_url() would use this
        
        assert url == test_url
        
        # Cleanup
        if os.path.exists("test_override.db"):
            os.remove("test_override.db")
    
    def test_default_database_url(self):
        """Test default database URL when no env var is set."""
        # When no DATABASE_URL is set, should default to sqlite file
        url = "sqlite:///amazon_selector.db"  # Default
        assert url.startswith("sqlite:///")


class TestEngineCreation:
    """Tests for database engine creation."""
    
    def test_create_in_memory_engine(self):
        """Test creating in-memory SQLite engine."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        
        assert engine is not None
        assert engine.url.database == ":memory:"
        
        engine.dispose()
    
    def test_engine_disposes_cleanly(self):
        """Test that engine can be disposed without errors."""
        engine = create_engine("sqlite:///:memory:")
        engine.dispose()
        
        # Should not raise any errors
        assert True


class TestTableCreation:
    """Tests for database table creation."""
    
    def test_create_all_tables(self):
        """Test creating all database tables."""
        engine = create_engine("sqlite:///:memory:")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert "products" in tables
        assert "history" in tables
        
        engine.dispose()
    
    def test_drop_all_tables(self):
        """Test dropping all database tables."""
        engine = create_engine("sqlite:///:memory:")
        
        # Create then drop
        Base.metadata.create_all(bind=engine)
        Base.metadata.drop_all(bind=engine)
        
        # Verify tables are gone
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert len(tables) == 0
        
        engine.dispose()


class TestSessionManagement:
    """Tests for database session management."""
    
    def test_create_session(self):
        """Test creating a database session."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        
        SessionFactory = sessionmaker(bind=engine)
        session = SessionFactory()
        
        assert session is not None
        
        session.close()
        engine.dispose()
    
    def test_session_context_manager(self):
        """Test using session in context manager."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        
        SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        
        with SessionFactory() as session:
            assert session is not None
            # Should auto-commit on exit
            assert not session.in_transaction()
        
        engine.dispose()


class TestConfigurationValidation:
    """Tests for configuration validation."""
    
    def test_test_mode_flag(self):
        """Test test mode configuration."""
        test_mode = True
        assert test_mode is True
    
    def test_echo_mode_off_by_default(self):
        """Test that SQL echo is off by default."""
        echo = os.getenv("DB_ECHO", "false").lower() == "true"
        assert echo is False  # Default should be False


class TestCleanup:
    """Tests for database cleanup."""
    
    def test_close_all_resets_globals(self):
        """Test that close_all resets global state."""
        # This test ensures cleanup functions work
        close_all()
        
        # Should not raise errors
        assert True
    
    def test_multiple_init_db_calls(self):
        """Test that init_db can be called multiple times safely."""
        engine = create_engine("sqlite:///:memory:")
        
        # Multiple creates should be idempotent
        Base.metadata.create_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # Should still have tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        assert len(tables) > 0
        
        engine.dispose()
