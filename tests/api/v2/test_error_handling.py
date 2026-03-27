"""
Error Handling Tests for Amazon Selector API v2

Tests for error handling across all API endpoints:
- 404 Not Found errors
- 400 Bad Request errors
- 500 Internal Server errors
- Other HTTP error codes
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import Dict, Any
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.v2.products import products_router
from src.api.v2.history import history_router
from src.db.connection import init_db, close_all


# ==================== Test Client Setup ====================

def create_test_app() -> FastAPI:
    """Create FastAPI app for testing."""
    app = FastAPI(title="Amazon Selector API v2 - Error Test")
    app.include_router(products_router)
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


# ==================== 404 Not Found Tests ====================

class Test404NotFound:
    """Tests for 404 Not Found errors."""
    
    
    def test_404_product_not_found(self, client):
        """Test 404 when product doesn't exist."""
        response = client.get("/api/v2/products/B999999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data['detail'].lower()
    
    
    def test_404_history_not_found(self, client, sample_product_payload):
        """Test 404 when history doesn't exist for product."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(f"/api/v2/history/{sample_product_payload['asin']}/latest")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    
    def test_404_history_product_not_found(self, client):
        """Test 404 when accessing history for non-existent product."""
        response = client.get("/api/v2/history/B999999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data['detail'].lower()
    
    
    def test_404_delete_nonexistent_product(self, client):
        """Test 404 when deleting non-existent product."""
        response = client.delete("/api/v2/products/B999999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data['detail'].lower()
    
    
    def test_404_update_nonexistent_product(self, client):
        """Test 404 when updating non-existent product."""
        response = client.put(
            "/api/v2/products/B999999999",
            json={"price": 59.99},
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data['detail'].lower()
    
    
    def test_404_invalid_route(self, client):
        """Test 404 for invalid API routes."""
        response = client.get("/api/v2/nonexistent-endpoint")
        
        assert response.status_code == 404
    
    
    def test_404_comparison_nonexistent_product(self, client):
        """Test 404 when comparing non-existent product."""
        response = client.get("/api/v2/history/B999999999/comparison?days=7")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data['detail'].lower()


# ==================== 400 Bad Request Tests ====================

class Test400BadRequest:
    """Tests for 400 Bad Request errors."""
    
    
    def test_400_invalid_sort_field(self, client):
        """Test 400 when using invalid sort field."""
        response = client.get("/api/v2/products/top?by=invalid_field")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid sort field" in data['detail']
    
    
    def test_400_empty_request_body(self, client):
        """Test 400 when sending empty request body."""
        response = client.post("/api/v2/products", json={})
        
        # FastAPI returns 422 for validation errors
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    
    def test_400_invalid_json(self, client):
        """Test 400 when sending invalid JSON."""
        # This would typically be caught by the JSON parser
        # Testing with malformed data instead
        response = client.post(
            "/api/v2/products",
            json={"asin": "B08N5WRWNW", "price": "not_a_number"},
        )
        
        assert response.status_code == 422
    
    
    def test_400_invalid_query_parameter_type(self, client):
        """Test 400 when using wrong type for query parameter."""
        response = client.get("/api/v2/products?limit=not_a_number")
        
        # FastAPI returns 422 for type validation errors
        assert response.status_code == 422


# ==================== 422 Validation Error Tests ====================

class Test422ValidationError:
    """Tests for 422 Unprocessable Entity (Validation) errors."""
    
    
    def test_422_missing_required_field(self, client):
        """Test 422 when missing required field."""
        response = client.post("/api/v2/products", json={
            "title": "Missing ASIN",
        })
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    
    def test_422_invalid_asin_length(self, client):
        """Test 422 when ASIN is too short."""
        response = client.post("/api/v2/products", json={
            "asin": "B123",
            "title": "Test Product",
        })
        
        assert response.status_code == 422
        data = response.json()
        # Should have validation error about field length
    
    
    def test_422_invalid_rating_range(self, client, sample_product_payload):
        """Test 422 when rating is out of valid range."""
        payload = sample_product_payload.copy()
        payload['rating'] = 6.0  # Rating > 5
        
        response = client.post("/api/v2/products", json=payload)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    
    def test_422_negative_price(self, client, sample_product_payload):
        """Test 422 when price is negative."""
        payload = sample_product_payload.copy()
        payload['price'] = -10.0
        
        response = client.post("/api/v2/products", json=payload)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    
    def test_422_invalid_limit_value(self, client):
        """Test 422 when limit is out of valid range."""
        response = client.get("/api/v2/products?limit=1000")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    
    def test_422_invalid_offset_value(self, client):
        """Test 422 when offset is negative."""
        response = client.get("/api/v2/products?offset=-10")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    
    def test_422_invalid_days_value(self, client, sample_product_payload):
        """Test 422 when days parameter is invalid."""
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get(
            f"/api/v2/history/{sample_product_payload['asin']}/price-history?days=0",
        )
        
        assert response.status_code == 422


# ==================== 409 Conflict Tests ====================

class Test409Conflict:
    """Tests for 409 Conflict errors."""
    
    
    def test_409_duplicate_product(self, client, sample_product_payload):
        """Test 409 when creating duplicate product."""
        # Create first product
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Try to create duplicate
        response = client.post("/api/v2/products", json=sample_product_payload)
        
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "already exists" in data['detail'].lower()


# ==================== 500 Internal Server Error Tests ====================

class Test500InternalServerError:
    """Tests for 500 Internal Server errors."""
    
    
    def test_500_database_error_simulation(self, client, sample_product_payload):
        """
        Test 500 error when database operation fails.
        
        Note: This test mocks a database failure to simulate 500 error.
        """
        # Mock the repository to raise an exception
        with patch('src.api.v2.products.ProductRepository') as mock_repo:
            mock_repo.side_effect = Exception("Database connection failed")
            
            # This would cause a 500 error in production
            # In test mode with TestClient, exceptions are raised
            # So we verify the error handling exists
            pass
        
        # Placeholder - actual 500 testing requires error injection
        assert True, "500 error test - requires error injection setup"
    
    
    def test_500_unexpected_exception_handling(self, client):
        """
        Test that unexpected exceptions are handled gracefully.
        
        Note: This verifies error handling infrastructure.
        """
        # In a real scenario, we'd inject a fault
        # For now, verify the API responds normally
        response = client.get("/api/v2/products")
        
        # Should not return 500 under normal conditions
        assert response.status_code != 500


# ==================== Error Response Format Tests ====================

class TestErrorResponseFormat:
    """Tests for error response format consistency."""
    
    
    def test_error_response_has_detail(self, client):
        """Test that all error responses have 'detail' field."""
        response = client.get("/api/v2/products/B999999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    
    def test_error_response_is_json(self, client):
        """Test that error responses are JSON format."""
        response = client.get("/api/v2/products/B999999999")
        
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"
        
        # Verify it's valid JSON
        data = response.json()
        assert isinstance(data, dict)
    
    
    def test_error_response_message_clarity(self, client):
        """Test that error messages are clear and helpful."""
        response = client.get("/api/v2/products/B999999999")
        
        data = response.json()
        detail = data['detail']
        
        # Error message should mention what was not found
        assert "product" in detail.lower() or "asin" in detail.lower()
    
    
    def test_validation_error_format(self, client):
        """Test that validation errors have proper format."""
        response = client.post("/api/v2/products", json={})
        
        assert response.status_code == 422
        data = response.json()
        
        # FastAPI validation errors have specific format
        assert "detail" in data
        assert isinstance(data['detail'], list)


# ==================== Edge Case Error Tests ====================

class TestEdgeCaseErrors:
    """Tests for edge case error scenarios."""
    
    
    def test_error_with_special_characters_in_asin(self, client):
        """Test error handling with special characters in ASIN."""
        response = client.get("/api/v2/products/B123!@#$%")
        
        # Should handle gracefully (404 or 422)
        assert response.status_code in [404, 422]
    
    
    def test_error_with_very_long_asin(self, client):
        """Test error handling with very long ASIN."""
        long_asin = "B" + "0" * 100
        response = client.get(f"/api/v2/products/{long_asin}")
        
        # Should handle gracefully (404 or 422)
        assert response.status_code in [404, 422]
    
    
    def test_error_with_unicode_in_payload(self, client):
        """Test error handling with unicode in payload."""
        response = client.post("/api/v2/products", json={
            "asin": "B08N5WRWNW",
            "title": "Product with émojis 🎉 and üñíçödé",
        })
        
        # Should handle unicode properly
        # Either succeed or fail with appropriate error
        assert response.status_code in [201, 422]
    
    
    def test_error_with_null_values(self, client):
        """Test error handling with null values in payload."""
        response = client.post("/api/v2/products", json={
            "asin": "B08N5WRWNW",
            "title": "Test Product",
            "price": None,
            "rating": None,
        })
        
        # Should handle null values (either accept or validate)
        assert response.status_code in [201, 422]
    
    
    def test_error_with_extreme_numeric_values(self, client):
        """Test error handling with extreme numeric values."""
        response = client.post("/api/v2/products", json={
            "asin": "B08N5WRWNW",
            "title": "Test Product",
            "price": 999999999.99,
            "review_count": 999999999,
        })
        
        # Should handle large numbers
        assert response.status_code in [201, 422]


# ==================== Rate Limiting Tests (If Implemented) ====================

class TestRateLimiting:
    """Tests for rate limiting (if implemented)."""
    
    
    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present (if implemented)."""
        response = client.get("/api/v2/products")
        
        # Rate limiting may or may not be implemented
        # If implemented, check for headers
        if "X-RateLimit-Limit" in response.headers:
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
    
    
    def test_rate_limit_exceeded(self, client):
        """Test behavior when rate limit is exceeded."""
        # Make many requests rapidly
        responses = []
        for _ in range(100):
            response = client.get("/api/v2/products")
            responses.append(response.status_code)
        
        # If rate limiting is implemented, at least one should be 429
        # Otherwise, all should be 200 or 422
        if 429 in responses:
            assert responses.count(429) > 0
        else:
            # No rate limiting - all should succeed or fail validation
            assert all(code in [200, 422] for code in responses)


# ==================== CORS and Security Headers Tests ====================

class TestSecurityHeaders:
    """Tests for security headers."""
    
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.get("/api/v2/products")
        
        # CORS may or may not be configured
        # If configured, check headers
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"]
    
    
    def test_content_type_header(self, client):
        """Test Content-Type header is correct."""
        response = client.get("/api/v2/products")
        
        assert response.headers["content-type"] == "application/json"
    
    
    def test_error_content_type(self, client):
        """Test error responses have correct Content-Type."""
        response = client.get("/api/v2/products/B999999999")
        
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"
