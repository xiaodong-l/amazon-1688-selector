"""
Comparison API v2 Tests for Amazon Selector

Tests for comparison API endpoints including:
- Time-based comparisons
- Multi-product comparisons
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


# ==================== Time Comparison Tests ====================

class TestCompareTime:
    """Tests for time-based comparisons."""
    
    
    def test_compare_time_7_days(self, client, sample_product_payload):
        """Test 7-day time comparison."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history 7 days ago
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
        
        # Get 7-day comparison
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
        assert data['rating_change'] == 0.1
        assert data['review_count_change'] == 5000
    
    
    def test_compare_time_30_days(self, client, sample_product_payload):
        """Test 30-day time comparison."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history 30 days ago
        past_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 39.99,
            "rating": 4.5,
            "review_count": 200000,
            "recorded_at": past_date,
        })
        
        # Create current history
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
            "rating": 4.7,
            "review_count": 255000,
        })
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=30",
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['days_compared'] == 30
        assert data['price_change'] == 10.0
        assert data['review_count_change'] == 55000
    
    
    def test_compare_time_no_past_data(self, client, sample_product_payload):
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
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['current'] is not None
        assert data['past'] is None
        assert data['price_change'] is None
        assert data['price_change_percent'] is None
    
    
    def test_compare_time_price_decrease(self, client, sample_product_payload):
        """Test comparison showing price decrease."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create past history with higher price
        past_date = (datetime.utcnow() - timedelta(days=14)).isoformat()
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 59.99,
            "recorded_at": past_date,
        })
        
        # Create current history with lower price
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
        })
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=14",
        )
        
        data = response.json()
        assert response.status_code == 200
        
        assert data['price_change'] == -10.0
        assert data['price_change_percent'] < 0
    
    
    def test_compare_time_no_change(self, client, sample_product_payload):
        """Test comparison when no change occurred."""
        # Setup
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create identical history records
        past_date = (datetime.utcnow() - timedelta(days=5)).isoformat()
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
            "rating": 4.7,
            "recorded_at": past_date,
        })
        
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
            "rating": 4.7,
        })
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=5",
        )
        
        data = response.json()
        assert response.status_code == 200
        
        assert data['price_change'] == 0.0
        assert data['rating_change'] == 0.0


# ==================== Multi-Product Comparison Tests ====================

class TestCompareProducts:
    """Tests for multi-product comparisons."""
    
    
    def test_compare_products_multiple_asins(self, client):
        """Test comparing multiple products."""
        # Create multiple products
        products = [
            {"asin": "B000000001", "title": "Product 1", "price": 49.99, "rating": 4.5},
            {"asin": "B000000002", "title": "Product 2", "price": 59.99, "rating": 4.7},
            {"asin": "B000000003", "title": "Product 3", "price": 39.99, "rating": 4.3},
        ]
        
        for product in products:
            client.post("/api/v2/products", json=product)
            client.post("/api/v2/history", json={
                "asin": product['asin'],
                "price": product['price'],
                "rating": product['rating'],
            })
        
        # Get history for each product (simulating comparison)
        comparisons = []
        for product in products:
            response = client.get(f"/api/v2/history/{product['asin']}/latest")
            if response.status_code == 200:
                comparisons.append(response.json())
        
        assert len(comparisons) == 3
        
        # Verify we can compare prices
        prices = [c['price'] for c in comparisons]
        assert min(prices) == 39.99
        assert max(prices) == 59.99
    
    
    def test_compare_products_same_category(self, client):
        """Test comparing products in same category."""
        # Create products in same category
        category = "Electronics"
        products = [
            {"asin": "B000000001", "title": "Echo Dot", "price": 49.99, "rating": 4.7, "category": category},
            {"asin": "B000000002", "title": "Echo Show", "price": 129.99, "rating": 4.6, "category": category},
        ]
        
        for product in products:
            client.post("/api/v2/products", json=product)
            client.post("/api/v2/history", json={
                "asin": product['asin'],
                "price": product['price'],
                "rating": product['rating'],
                "bsr": 10 if product['asin'] == "B000000001" else 20,
            })
        
        # Get latest for comparison
        response1 = client.get("/api/v2/history/B000000001/latest")
        response2 = client.get("/api/v2/history/B000000002/latest")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Compare BSR (lower is better)
        assert data1['bsr'] < data2['bsr']  # Product 1 has better rank
    
    
    def test_compare_products_price_performance(self, client):
        """Test price-performance comparison across products."""
        # Create products with different price-performance ratios
        products = [
            {"asin": "B000000001", "title": "Budget Option", "price": 29.99, "rating": 4.0},
            {"asin": "B000000002", "title": "Mid Range", "price": 49.99, "rating": 4.5},
            {"asin": "B000000003", "title": "Premium", "price": 99.99, "rating": 4.8},
        ]
        
        for product in products:
            client.post("/api/v2/products", json=product)
            client.post("/api/v2/history", json={
                "asin": product['asin'],
                "price": product['price'],
                "rating": product['rating'],
            })
        
        # Calculate price-performance ratio
        ratios = []
        for product in products:
            response = client.get(f"/api/v2/history/{product['asin']}/latest")
            if response.status_code == 200:
                data = response.json()
                ratio = data['price'] / data['rating']
                ratios.append((product['asin'], ratio))
        
        # Best value should have lowest price/rating ratio
        best_value = min(ratios, key=lambda x: x[1])
        assert best_value[0] == "B000000001"  # Budget option


# ==================== Invalid Parameters Tests ====================

class TestCompareWithInvalidParams:
    """Tests for invalid parameter handling in comparison API."""
    
    
    def test_compare_with_invalid_params_missing_asin(self, client):
        """Test comparison with missing ASIN."""
        response = client.get("/api/v2/history//comparison?days=7")
        
        # Should be 404 (path not found) or 422 (validation)
        assert response.status_code in [404, 422]
    
    
    def test_compare_with_invalid_params_days_zero(self, client, sample_product_payload):
        """Test comparison with days=0."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=0",
        )
        
        assert response.status_code == 422
    
    
    def test_compare_with_invalid_params_days_negative(self, client, sample_product_payload):
        """Test comparison with negative days."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=-10",
        )
        
        assert response.status_code == 422
    
    
    def test_compare_with_invalid_params_days_exceeds_max(self, client, sample_product_payload):
        """Test comparison with days exceeding maximum (90)."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=100",
        )
        
        assert response.status_code == 422
    
    
    def test_compare_with_invalid_params_non_existent_product(self, client):
        """Test comparison for non-existent product."""
        response = client.get("/api/v2/history/B999999999/comparison?days=7")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data['detail'].lower()
    
    
    def test_compare_with_invalid_params_string_days(self, client, sample_product_payload):
        """Test comparison with non-numeric days value."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=abc",
        )
        
        assert response.status_code == 422
    
    
    def test_compare_with_invalid_params_float_days(self, client, sample_product_payload):
        """Test comparison with float days value."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=7.5",
        )
        
        # FastAPI may coerce or reject floats for int fields
        assert response.status_code in [200, 422]


# ==================== Edge Cases ====================

class TestCompareEdgeCases:
    """Tests for edge cases in comparison API."""
    
    
    def test_compare_single_history_record(self, client, sample_product_payload):
        """Test comparison when only one history record exists."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create only one history record
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
        })
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=7",
        )
        
        data = response.json()
        assert response.status_code == 200
        
        assert data['current'] is not None
        assert data['past'] is None
        assert data['price_change'] is None
    
    
    def test_compare_with_null_values(self, client, sample_product_payload):
        """Test comparison with null field values."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create past history with null rating
        past_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 44.99,
            "rating": None,
            "recorded_at": past_date,
        })
        
        # Create current history
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
            "rating": 4.7,
        })
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=7",
        )
        
        data = response.json()
        assert response.status_code == 200
        
        assert data['price_change'] == 5.0
        assert data['rating_change'] is None  # Can't calculate with null
    
    
    def test_compare_exact_boundary(self, client, sample_product_payload):
        """Test comparison at exact day boundary."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Create history exactly 7 days ago
        exact_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 44.99,
            "recorded_at": exact_date,
        })
        
        client.post("/api/v2/history", json={
            "asin": sample_product_payload['asin'],
            "price": 49.99,
        })
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/comparison?days=7",
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['past'] is not None
        assert data['days_compared'] == 7
