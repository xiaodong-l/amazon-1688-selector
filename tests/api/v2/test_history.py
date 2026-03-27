"""
History API v2 Tests for Amazon Selector

Tests for history API endpoints including CRUD operations and comparison.
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timedelta
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.v2.history import history_router
from src.db.connection import init_db, close_all


# ==================== Test Client Setup ====================

def create_test_app() -> FastAPI:
    """Create FastAPI app for testing."""
    app = FastAPI(title="Amazon Selector API v2 - Test")
    app.include_router(history_router)
    return app


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh database."""
    close_all()
    init_db(test_mode=True)
    
    app = create_test_app()
    
    with TestClient(app) as test_client:
        yield test_client
    
    close_all()


@pytest.fixture
def sample_product_payload() -> Dict[str, Any]:
    """Sample product creation payload."""
    return {
        "asin": "B08N5WRWNW",
        "title": "Echo Dot (4th Gen)",
        "price": 49.99,
        "rating": 4.7,
        "review_count": 254891,
        "category": "Electronics",
    }


@pytest.fixture
def sample_history_payload(sample_product_payload) -> Dict[str, Any]:
    """Sample history creation payload."""
    return {
        "asin": sample_product_payload['asin'],
        "price": 49.99,
        "rating": 4.7,
        "review_count": 254891,
        "bsr": 12,
    }


# ==================== Create History Tests ====================

class TestCreateHistory:
    """Tests for POST /api/v2/history."""
    
    def test_create_history_success(self, client, sample_product_payload, sample_history_payload):
        """Test creating a history record."""
        # Create product first
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history
        response = client.post("/api/v2/history", json=sample_history_payload)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data['asin'] == sample_history_payload['asin']
        assert data['price'] == sample_history_payload['price']
        assert 'id' in data
        assert 'recorded_at' in data
    
    def test_create_history_product_not_found(self, client, sample_history_payload):
        """Test creating history for non-existent product."""
        response = client.post("/api/v2/history", json=sample_history_payload)
        
        assert response.status_code == 404
        assert "not found" in response.json()['detail']
    
    def test_create_history_missing_asin(self, client):
        """Test creating history without ASIN."""
        payload = {"price": 49.99}
        
        response = client.post("/api/v2/history", json=payload)
        
        assert response.status_code == 422


# ==================== Get History Tests ====================

class TestGetHistory:
    """Tests for GET /api/v2/history/{asin}."""
    
    def test_get_history_success(self, client, sample_product_payload, sample_history_payload):
        """Test getting history for a product."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        client.post("/api/v2/history", json=sample_history_payload)
        
        # Get history
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['items']) == 1
        assert data['asin'] == sample_product_payload['asin']
    
    def test_get_history_empty(self, client, sample_product_payload):
        """Test getting history when none exists."""
        # Create product but no history
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['items'] == []
    
    def test_get_history_product_not_found(self, client):
        """Test getting history for non-existent product."""
        response = client.get("/api/v2/history/B999999999")
        
        assert response.status_code == 404
    
    def test_get_history_with_date_filter(self, client, sample_product_payload):
        """Test getting history with date filters."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create multiple history records
        now = datetime.utcnow()
        for i in range(5):
            payload = {
                "asin": sample_product_payload['asin'],
                "price": 50.0 - i,
                "recorded_at": (now - timedelta(days=i)).isoformat(),
            }
            client.post("/api/v2/history", json=payload)
        
        # Filter by date
        start_date = (now - timedelta(days=3)).isoformat()
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}?start_date={start_date}",
        )
        
        data = response.json()
        assert len(data['items']) <= 4  # Records within last 3 days


# ==================== Get Latest History Tests ====================

class TestGetLatestHistory:
    """Tests for GET /api/v2/history/{asin}/latest."""
    
    def test_get_latest_success(self, client, sample_product_payload):
        """Test getting latest history record."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create multiple history records
        for i in range(3):
            payload = {
                "asin": sample_product_payload['asin'],
                "price": 50.0 - i,
            }
            client.post("/api/v2/history", json=payload)
        
        # Get latest
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/latest")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['price'] == 50.0  # Most recent
    
    def test_get_latest_no_history(self, client, sample_product_payload):
        """Test getting latest when no history exists."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/latest")
        
        assert response.status_code == 404


# ==================== Price History Tests ====================

class TestGetPriceHistory:
    """Tests for GET /api/v2/history/{asin}/price-history."""
    
    def test_get_price_history_success(self, client, sample_product_payload):
        """Test getting price history."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history records
        for i in range(5):
            payload = {
                "asin": sample_product_payload['asin'],
                "price": 50.0 - i,
            }
            client.post("/api/v2/history", json=payload)
        
        # Get price history
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/price-history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 5
        assert all('date' in point and 'price' in point for point in data)
    
    def test_get_price_history_with_days_limit(self, client, sample_product_payload):
        """Test getting price history with days limit."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create 30 days of history
        now = datetime.utcnow()
        for i in range(30):
            payload = {
                "asin": sample_product_payload['asin'],
                "price": 50.0,
                "recorded_at": (now - timedelta(days=i)).isoformat(),
            }
            client.post("/api/v2/history", json=payload)
        
        # Get only last 7 days
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/price-history?days=7",
        )
        
        data = response.json()
        assert len(data) <= 7


# ==================== Comparison Tests ====================

class TestGetComparison:
    """Tests for GET /api/v2/history/{asin}/comparison."""
    
    def test_get_comparison_success(self, client, sample_product_payload):
        """Test getting comparison data."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history 7 days ago
        past_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 44.99,
            "rating": 4.6,
            "review_count": 250000,
            "recorded_at": past_date,
        })
        
        # Create current history
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
            "rating": 4.7,
            "review_count": 255000,
        })
        
        # Get comparison
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=7",
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['current'] is not None
        assert data['past'] is not None
        assert data['days_compared'] == 7
        assert data['price_change'] == 5.0
        assert data['price_change_percent'] > 0
        assert data['review_count_change'] == 5000
    
    def test_get_comparison_no_past_data(self, client, sample_product_payload):
        """Test comparison when no past data exists."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create only current history
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
        })
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=7",
        )
        
        data = response.json()
        assert data['current'] is not None
        assert data['past'] is None
        assert data['price_change'] is None


# ==================== Delete History Tests ====================

class TestDeleteHistory:
    """Tests for DELETE /api/v2/history/{asin}."""
    
    def test_delete_history_success(self, client, sample_product_payload):
        """Test deleting all history for a product."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history records
        for i in range(3):
            client.post("/api/v2/history", json={
                "asin": sample_product_payload['asin'],
                "price": 50.0 - i,
            })
        
        # Delete history
        response = client.delete(f"/api/v2/history/{sample_product_payload['asin']}")
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/api/v2/history/{sample_product_payload['asin']}")
        data = get_response.json()
        assert len(data['items']) == 0
    
    def test_delete_history_product_not_found(self, client):
        """Test deleting history for non-existent product."""
        response = client.delete("/api/v2/history/B999999999")
        
        assert response.status_code == 404


# ==================== Cleanup Tests ====================

class TestCleanupOldRecords:
    """Tests for POST /api/v2/history/cleanup."""
    
    def test_cleanup_old_records(self, client, sample_product_payload):
        """Test cleaning up old history records."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create old and new history
        now = datetime.utcnow()
        
        # Old record (100 days ago)
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 40.0,
            "recorded_at": (now - timedelta(days=100)).isoformat(),
        })
        
        # New record (5 days ago)
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 50.0,
            "recorded_at": (now - timedelta(days=5)).isoformat(),
        })
        
        # Cleanup records older than 30 days
        response = client.post("/api/v2/history/cleanup?days=30")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['deleted_count'] == 1
        assert data['days_kept'] == 30
    
    def test_cleanup_no_old_records(self, client, sample_product_payload):
        """Test cleanup when no old records exist."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create only recent history
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 50.0,
        })
        
        response = client.post("/api/v2/history/cleanup?days=30")
        
        data = response.json()
        assert data['deleted_count'] == 0


# ==================== History Count Tests ====================

class TestGetHistoryCount:
    """Tests for GET /api/v2/history/{asin}/count."""
    
    def test_get_count_success(self, client, sample_product_payload):
        """Test getting history count."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create multiple history records
        for i in range(5):
            client.post("/api/v2/history", json={
                "asin": sample_product_payload['asin'],
                "price": 50.0 - i,
            })
        
        # Get count
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/count")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['asin'] == sample_product_payload['asin']
        assert data['record_count'] == 5
    
    def test_get_count_zero(self, client, sample_product_payload):
        """Test getting count when no history exists."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/count")
        
        data = response.json()
        assert data['record_count'] == 0
    
    def test_get_count_product_not_found(self, client):
        """Test getting count for non-existent product."""
        response = client.get("/api/v2/history/B999999999/count")
        
        assert response.status_code == 404
