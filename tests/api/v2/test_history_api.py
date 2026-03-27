"""
History API v2 Comprehensive Tests for Amazon Selector

Tests for history API endpoints including:
- Product history retrieval
- Price history tracking
- BSR history tracking
- Statistics overview
- Invalid parameter handling
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


# ==================== Product History Tests ====================

class TestGetProductHistory:
    """Tests for GET /api/v2/history/{asin} - Product history retrieval."""
    
    
    def test_get_product_history_success(self, client, sample_product_payload, sample_history_payload):
        """Test getting complete product history."""
        # Setup: Create product and history
        client.post("/api/v2/products", json=sample_product_payload)
        client.post("/api/v2/history", json=sample_history_payload)
        
        # Get history
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['asin'] == sample_product_payload['asin']
        assert len(data['items']) == 1
        assert data['total'] == 1
        assert 'limit' in data
        
        # Verify history record structure
        record = data['items'][0]
        assert record['price'] == sample_history_payload['price']
        assert record['rating'] == sample_history_payload['rating']
        assert record['bsr'] == sample_history_payload['bsr']
        assert 'id' in record
        assert 'recorded_at' in record
    
    
    def test_get_product_history_multiple_records(self, client, sample_product_payload):
        """Test getting history with multiple records."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create multiple history records
        for i in range(5):
            client.post("/api/v2/history", json={
                "asin": sample_product_payload['asin'],
                "price": 50.0 - i,
                "rating": 4.7,
                "review_count": 254891 + i * 100,
                "bsr": 12 + i,
            })
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['items']) == 5
        assert data['total'] == 5
    
    
    def test_get_product_history_with_date_filter(self, client, sample_product_payload):
        """Test getting history with date range filters."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        now = datetime.utcnow()
        # Create history records on different dates
        for i in range(10):
            payload = {
                "asin": sample_product_payload['asin'],
                "price": 50.0 - i,
                "recorded_at": (now - timedelta(days=i)).isoformat(),
            }
            client.post("/api/v2/history", json=payload)
        
        # Filter by date range
        start_date = (now - timedelta(days=5)).isoformat()
        end_date = (now - timedelta(days=2)).isoformat()
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}?start_date={start_date}&end_date={end_date}",
        )
        
        data = response.json()
        assert response.status_code == 200
        # Should only include records within the date range
        assert len(data['items']) <= 4  # Days 2, 3, 4, 5
    
    
    def test_get_product_history_empty(self, client, sample_product_payload):
        """Test getting history when no records exist."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['items'] == []
        assert data['total'] == 0
        assert data['asin'] == sample_product_payload['asin']


# ==================== Price History Tests ====================

class TestGetPriceHistory:
    """Tests for GET /api/v2/history/{asin}/price-history - Price history tracking."""
    
    
    def test_get_price_history_success(self, client, sample_product_payload):
        """Test getting price history data."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create price history
        for i in range(10):
            client.post("/api/v2/history", json={
                "asin": sample_product_payload['asin'],
                "price": 50.0 - i,
            })
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/price-history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 10
        # Verify structure
        for point in data:
            assert 'date' in point
            assert 'price' in point
    
    
    def test_get_price_history_with_days_limit(self, client, sample_product_payload):
        """Test getting price history limited by days."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        now = datetime.utcnow()
        # Create 30 days of history
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
        assert response.status_code == 200
        assert len(data) <= 7
    
    
    def test_get_price_history_empty(self, client, sample_product_payload):
        """Test getting price history when no data exists."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/price-history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data == []
    
    
    def test_get_price_history_with_null_prices(self, client, sample_product_payload):
        """Test price history handles null prices gracefully."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history with some null prices
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 50.0,
        })
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": None,
        })
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 45.0,
        })
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/price-history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3


# ==================== BSR History Tests ====================

class TestGetBSRHistory:
    """Tests for BSR history retrieval."""
    
    
    def test_get_bsr_history_success(self, client, sample_product_payload):
        """Test getting BSR history from product history."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history with BSR data
        for i in range(5):
            client.post("/api/v2/history", json={
                "asin": sample_product_payload['asin'],
                "price": 50.0,
                "bsr": 10 + i,
            })
        
        # Get full history (includes BSR)
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['items']) == 5
        # Verify BSR is present in each record
        for item in data['items']:
            assert 'bsr' in item
            assert item['bsr'] is not None
    
    
    def test_get_bsr_history_with_null_values(self, client, sample_product_payload):
        """Test BSR history handles null BSR values."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history with mixed BSR values
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "bsr": 10,
        })
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "bsr": None,
        })
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['items']) == 2
        assert data['items'][0]['bsr'] == 10
        assert data['items'][1]['bsr'] is None
    
    
    def test_get_bsr_history_trend(self, client, sample_product_payload):
        """Test BSR history shows trend correctly."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create BSR history showing trend (lower is better)
        now = datetime.utcnow()
        for i, bsr in enumerate([100, 80, 60, 40, 20]):
            payload = {
                "asin": sample_product_payload['asin'],
                "bsr": bsr,
                "recorded_at": (now - timedelta(days=(4-i))).isoformat(),
            }
            client.post("/api/v2/history", json=payload)
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}")
        
        data = response.json()
        assert response.status_code == 200
        
        # Verify BSR trend (improving rank)
        bsr_values = [item['bsr'] for item in data['items']]
        assert bsr_values == [100, 80, 60, 40, 20]


# ==================== Stats Overview Tests ====================

class TestGetStatsOverview:
    """Tests for statistics overview endpoints."""
    
    
    def test_get_stats_overview_with_history(self, client, sample_product_payload):
        """Test getting statistics overview with history data."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create multiple history records
        for i in range(10):
            client.post("/api/v2/history", json={
                "asin": sample_product_payload['asin'],
                "price": 50.0 - i,
                "rating": 4.5 + (i * 0.02),
                "review_count": 254891 + i * 100,
                "bsr": 20 - i,
            })
        
        # Get latest record as stats
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/latest")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['asin'] == sample_product_payload['asin']
        assert data['price'] == 40.0  # Last recorded
        assert data['review_count'] == 254891 + 900
    
    
    def test_get_stats_overview_count(self, client, sample_product_payload):
        """Test getting record count as part of stats."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create 5 history records
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
    
    
    def test_get_stats_overview_comparison(self, client, sample_product_payload):
        """Test getting comparison stats."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create past history
        past_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 44.99,
            "rating": 4.6,
            "review_count": 250000,
            "bsr": 15,
            "recorded_at": past_date,
        })
        
        # Create current history
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
            "rating": 4.7,
            "review_count": 255000,
            "bsr": 12,
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


# ==================== Invalid ASIN Tests ====================

class TestHistoryWithInvalidASIN:
    """Tests for handling invalid ASIN parameters."""
    
    
    def test_history_with_invalid_asin_not_found(self, client):
        """Test history lookup with non-existent ASIN."""
        response = client.get("/api/v2/history/B999999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data['detail'].lower()
    
    
    def test_history_with_invalid_asin_too_short(self, client, sample_product_payload):
        """Test history creation with ASIN that's too short."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.post("/api/v2/history", json={
            "asin": "B123",  # Too short
            "price": 50.0,
        })
        
        assert response.status_code == 422  # Validation error
    
    
    def test_history_with_invalid_asin_empty(self, client):
        """Test history creation with empty ASIN."""
        response = client.post("/api/v2/history", json={
            "asin": "",
            "price": 50.0,
        })
        
        assert response.status_code == 422
    
    
    def test_history_with_invalid_asin_special_chars(self, client, sample_product_payload):
        """Test history lookup with ASIN containing special characters."""
        response = client.get("/api/v2/history/B123!@#$%")
        
        # Should either 404 or 422 depending on validation
        assert response.status_code in [404, 422]
    
    
    def test_history_create_without_asin(self, client):
        """Test history creation without ASIN field."""
        response = client.post("/api/v2/history", json={
            "price": 50.0,
        })
        
        assert response.status_code == 422


# ==================== Invalid Days Tests ====================

class TestHistoryWithInvalidDays:
    """Tests for handling invalid days parameters."""
    
    
    def test_history_with_invalid_days_zero(self, client, sample_product_payload):
        """Test price history with days=0."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/price-history?days=0",
        )
        
        assert response.status_code == 422  # Validation error (ge=1)
    
    
    def test_history_with_invalid_days_negative(self, client, sample_product_payload):
        """Test price history with negative days."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/price-history?days=-5",
        )
        
        assert response.status_code == 422
    
    
    def test_history_with_invalid_days_exceeds_max(self, client, sample_product_payload):
        """Test price history with days exceeding maximum."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/price-history?days=500",
        )
        
        assert response.status_code == 422  # Validation error (le=365)
    
    
    def test_history_with_invalid_days_non_integer(self, client, sample_product_payload):
        """Test price history with non-integer days value."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/price-history?days=abc",
        )
        
        assert response.status_code == 422  # Validation error
    
    
    def test_comparison_with_invalid_days(self, client, sample_product_payload):
        """Test comparison with invalid days parameter."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=200",
        )
        
        assert response.status_code == 422  # Validation error (le=90)


# ==================== Error Handling Tests ====================

class TestHistoryErrorHandling:
    """Tests for error handling in history API."""
    
    
    def test_404_not_found(self, client):
        """Test 404 error for non-existent resource."""
        response = client.get("/api/v2/history/B999999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    
    def test_400_bad_request(self, client, sample_product_payload):
        """Test 400 error for bad request."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Invalid sort parameter (if applicable)
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=invalid",
        )
        
        assert response.status_code == 422  # FastAPI returns 422 for validation errors
    
    
    def test_409_conflict_duplicate(self, client, sample_product_payload, sample_history_payload):
        """Test conflict handling (if applicable)."""
        # History doesn't have unique constraints like products,
        # but we test the pattern
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history multiple times (should be allowed)
        response1 = client.post("/api/v2/history", json=sample_history_payload)
        response2 = client.post("/api/v2/history", json=sample_history_payload)
        
        # Both should succeed (history can have duplicates)
        assert response1.status_code == 201
        assert response2.status_code == 201
