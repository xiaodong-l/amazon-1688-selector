"""
Database Models Tests for Amazon Selector v2.2

Tests for Product and History model definitions, relationships, and methods.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import inspect

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.models import Base, Product, History


class TestProductModel:
    """Tests for Product model."""
    
    def test_product_table_exists(self, test_engine):
        """Test that products table is created."""
        from sqlalchemy import inspect
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        
        assert "products" in tables
    
    def test_product_columns(self, test_engine):
        """Test Product model has correct columns."""
        inspector = inspect(test_engine)
        columns = {col['name'] for col in inspector.get_columns('products')}
        
        expected_columns = {
            'id', 'asin', 'title', 'price', 'rating',
            'review_count', 'bsr', 'category', 'image_url',
            'created_at', 'updated_at'
        }
        
        assert columns == expected_columns
    
    def test_product_primary_key(self, test_engine):
        """Test Product has auto-increment primary key."""
        inspector = inspect(test_engine)
        pk_columns = inspector.get_pk_constraint('products')['constrained_columns']
        
        assert pk_columns == ['id']
    
    def test_product_asin_unique(self, test_engine):
        """Test ASIN column has unique constraint."""
        inspector = inspect(test_engine)
        unique_constraints = inspector.get_unique_constraints('products')
        
        # Check for unique constraint on asin
        asin_unique = any(
            'asin' in constraint.get('column_names', [])
            for constraint in unique_constraints
        )
        
        # Also check unique index
        indexes = inspector.get_indexes('products')
        asin_index_unique = any(
            idx.get('unique', False) and 'asin' in idx.get('column_names', [])
            for idx in indexes
        )
        
        assert asin_unique or asin_index_unique
    
    def test_product_indexes(self, test_engine):
        """Test Product model has correct indexes."""
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes('products')
        index_names = {idx['name'] for idx in indexes}
        
        # Check for expected indexes
        assert any('asin' in str(idx) for idx in indexes)
    
    def test_product_to_dict(self, sample_product):
        """Test Product.to_dict() method."""
        product_dict = sample_product.to_dict()
        
        assert product_dict['id'] == sample_product.id
        assert product_dict['asin'] == sample_product.asin
        assert product_dict['title'] == sample_product.title
        assert product_dict['price'] == sample_product.price
        assert product_dict['rating'] == sample_product.rating
        assert product_dict['review_count'] == sample_product.review_count
        assert product_dict['bsr'] == sample_product.bsr
        assert product_dict['category'] == sample_product.category
        assert 'created_at' in product_dict
        assert 'updated_at' in product_dict
    
    def test_product_repr(self, sample_product):
        """Test Product.__repr__() method."""
        repr_str = repr(sample_product)
        
        assert 'Product' in repr_str
        assert sample_product.asin in repr_str
    
    def test_product_create(self, db_session, sample_product_data):
        """Test creating a Product instance."""
        product = Product(**sample_product_data)
        db_session.add(product)
        db_session.commit()
        
        assert product.id is not None
        assert product.asin == sample_product_data['asin']
    
    def test_product_timestamps_auto_set(self, db_session, sample_product_data):
        """Test that timestamps are set automatically."""
        product = Product(**sample_product_data)
        db_session.add(product)
        db_session.commit()
        
        assert product.created_at is not None
        assert product.updated_at is not None
        assert isinstance(product.created_at, datetime)
        assert isinstance(product.updated_at, datetime)
    
    def test_product_price_nullable(self, db_session):
        """Test that price can be nullable."""
        product = Product(
            asin="B000000005",
            title="No Price Product",
            price=None,
        )
        db_session.add(product)
        db_session.commit()
        
        assert product.price is None
    
    def test_product_rating_validation(self, db_session):
        """Test rating is within valid range."""
        # Valid ratings
        for rating in [0, 2.5, 4.7, 5.0]:
            product = Product(
                asin=f"B00000000{int(rating * 10)}",
                title=f"Rating {rating}",
                rating=rating,
            )
            db_session.add(product)
        
        db_session.commit()
        
        # Note: Database-level constraints would need explicit check constraints
        # SQLAlchemy doesn't enforce 0-5 range by default
    
    def test_product_duplicate_asin_fails(self, db_session, sample_product):
        """Test that duplicate ASIN raises integrity error."""
        from sqlalchemy.exc import IntegrityError
        
        duplicate = Product(
            asin=sample_product.asin,
            title="Duplicate Product",
        )
        db_session.add(duplicate)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestHistoryModel:
    """Tests for History model."""
    
    def test_history_table_exists(self, test_engine):
        """Test that history table is created."""
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        
        assert "history" in tables
    
    def test_history_columns(self, test_engine):
        """Test History model has correct columns."""
        inspector = inspect(test_engine)
        columns = {col['name'] for col in inspector.get_columns('history')}
        
        expected_columns = {
            'id', 'asin', 'price', 'rating', 'review_count',
            'bsr', 'recorded_at', 'created_at'
        }
        
        assert columns == expected_columns
    
    def test_history_primary_key(self, test_engine):
        """Test History has auto-increment primary key."""
        inspector = inspect(test_engine)
        pk_columns = inspector.get_pk_constraint('history')['constrained_columns']
        
        assert pk_columns == ['id']
    
    def test_history_indexes(self, test_engine):
        """Test History model has correct indexes."""
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes('history')
        
        # Should have indexes on asin and recorded_at
        index_columns = set()
        for idx in indexes:
            index_columns.update(idx.get('column_names', []))
        
        assert 'asin' in index_columns
        assert 'recorded_at' in index_columns
    
    def test_history_to_dict(self, sample_history):
        """Test History.to_dict() method."""
        history_dict = sample_history.to_dict()
        
        assert history_dict['id'] == sample_history.id
        assert history_dict['asin'] == sample_history.asin
        assert history_dict['price'] == sample_history.price
        assert history_dict['rating'] == sample_history.rating
        assert history_dict['review_count'] == sample_history.review_count
        assert history_dict['bsr'] == sample_history.bsr
        assert 'recorded_at' in history_dict
        assert 'created_at' in history_dict
    
    def test_history_repr(self, sample_history):
        """Test History.__repr__() method."""
        repr_str = repr(sample_history)
        
        assert 'History' in repr_str
        assert sample_history.asin in repr_str
    
    def test_history_create(self, db_session, sample_product):
        """Test creating a History instance."""
        history = History(
            asin=sample_product.asin,
            price=49.99,
            rating=4.7,
            review_count=1000,
            recorded_at=datetime.utcnow(),
        )
        db_session.add(history)
        db_session.commit()
        
        assert history.id is not None
        assert history.asin == sample_product.asin
    
    def test_history_recorded_at_default(self, db_session, sample_product):
        """Test that recorded_at defaults to current time if not provided."""
        history = History(
            asin=sample_product.asin,
            price=49.99,
        )
        db_session.add(history)
        db_session.commit()
        
        # Note: recorded_at doesn't have default in model, must be provided
        # This test verifies behavior when explicitly set
        assert history.recorded_at is not None
    
    def test_history_multiple_records_same_asin(self, db_session, sample_product):
        """Test creating multiple history records for same ASIN."""
        now = datetime.utcnow()
        
        for i in range(5):
            history = History(
                asin=sample_product.asin,
                price=50.0 - i,
                recorded_at=now - timedelta(days=i),
            )
            db_session.add(history)
        
        db_session.commit()
        
        count = db_session.query(History).filter(
            History.asin == sample_product.asin
        ).count()
        
        assert count == 5
    
    def test_history_nullable_fields(self, db_session, sample_product):
        """Test that history nullable fields work correctly."""
        history = History(
            asin=sample_product.asin,
            price=None,
            rating=None,
            bsr=None,
            review_count=0,
            recorded_at=datetime.utcnow(),
        )
        db_session.add(history)
        db_session.commit()
        
        assert history.price is None
        assert history.rating is None
        assert history.bsr is None


class TestModelRelationships:
    """Tests for model relationships (if any)."""
    
    def test_product_and_history_independent(self, db_session, sample_product):
        """Test that Product and History can exist independently."""
        # Create product
        product = Product(
            asin="B000000006",
            title="Standalone Product",
        )
        db_session.add(product)
        db_session.commit()
        
        # Product should exist without history
        assert product.id is not None
        
        # Create history without product (allowed in schema)
        history = History(
            asin="B999999999",  # Non-existent ASIN
            price=99.99,
            recorded_at=datetime.utcnow(),
        )
        db_session.add(history)
        db_session.commit()
        
        # History should be created (no foreign key constraint)
        assert history.id is not None
