"""
Products API v2 Tests for Amazon Selector

Tests for product API endpoints including CRUD operations and search.
All tests are asynchronous to match the async repository implementations.
"""
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.v2.products import products_router
from src.db.connection import init_db_async, close_all_async, get_db_session


# ==================== Test Client Setup ====================

def create_test_app() -> FastAPI:
    """Create FastAPI app for testing."""
    app = FastAPI(title="Amazon Selector API v2 - Test")
    app.include_router(products_router)
    return app


@pytest_asyncio.fixture(scope="function")
async def client():
    """Create test client with fresh database."""
    # Initialize test database (async for async endpoints)
    await close_all_async()
    await init_db_async(test_mode=True)
    
    app = create_test_app()
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    await close_all_async()


@pytest.fixture
def sample_product_payload() -> Dict[str, Any]:
    """Sample product creation payload."""
    return {
        "asin": "B08N5WRWNW",
        "title": "Echo Dot (4th Gen) | Smart speaker with Alexa",
        "price": 49.99,
        "rating": 4.7,
        "review_count": 254891,
        "bsr": 12,
        "category": "Electronics",
        "image_url": "https://example.com/image.jpg",
        "product_url": "https://amazon.com/dp/B08N5WRWNW",
    }


# ==================== Create Product Tests ====================

class TestCreateProduct:
    """Tests for POST /api/v2/products."""
    
    @pytest.mark.asyncio
    def test_create_product_success(self, client, sample_product_payload):
        """Test creating a product successfully."""
        response = client.post("/api/v2/products", json=sample_product_payload)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data['asin'] == sample_product_payload['asin']
        assert data['title'] == sample_product_payload['title']
        assert data['price'] == sample_product_payload['price']
        assert 'id' in data
        assert 'created_at' in data
    
    @pytest.mark.asyncio
    def test_create_product_duplicate_asin(self, client, sample_product_payload):
        """Test creating product with duplicate ASIN."""
        # Create first product
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Try to create duplicate
        response = client.post("/api/v2/products", json=sample_product_payload)
        
        assert response.status_code == 409
        assert "already exists" in response.json()['detail']
    
    @pytest.mark.asyncio
    def test_create_product_missing_required_fields(self, client):
        """Test creating product with missing required fields."""
        payload = {"title": "Missing ASIN"}
        
        response = client.post("/api/v2/products", json=payload)
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    def test_create_product_invalid_asin_length(self, client):
        """Test creating product with invalid ASIN length."""
        payload = {
            "asin": "B123",  # Too short
            "title": "Test Product",
        }
        
        response = client.post("/api/v2/products", json=payload)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    def test_create_product_invalid_rating(self, client, sample_product_payload):
        """Test creating product with invalid rating."""
        payload = sample_product_payload.copy()
        payload['rating'] = 6.0  # Rating > 5
        
        response = client.post("/api/v2/products", json=payload)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    def test_create_product_negative_price(self, client, sample_product_payload):
        """Test creating product with negative price."""
        payload = sample_product_payload.copy()
        payload['price'] = -10.0
        
        response = client.post("/api/v2/products", json=payload)
        
        assert response.status_code == 422


# ==================== Get Product Tests ====================

class TestGetProduct:
    """Tests for GET /api/v2/products/{asin}."""
    
    @pytest.mark.asyncio
    def test_get_product_success(self, client, sample_product_payload):
        """Test getting a product by ASIN."""
        # Create product first
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Get product
        response = client.get(f"/api/v2/products/{sample_product_payload['asin']}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['asin'] == sample_product_payload['asin']
        assert data['title'] == sample_product_payload['title']
    
    @pytest.mark.asyncio
    def test_get_product_not_found(self, client):
        """Test getting non-existent product."""
        response = client.get("/api/v2/products/B999999999")
        
        assert response.status_code == 404
        assert "not found" in response.json()['detail']


# ==================== List Products Tests ====================

class TestListProducts:
    """Tests for GET /api/v2/products."""
    
    @pytest.mark.asyncio
    def test_list_products_empty(self, client):
        """Test listing products when database is empty."""
        response = client.get("/api/v2/products")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['items'] == []
        assert data['total'] == 0
    
    @pytest.mark.asyncio
    def test_list_products_with_data(self, client, sample_product_payload):
        """Test listing products with data."""
        # Create product
        client.post("/api/v2/products", json=sample_product_payload)
        
        response = client.get("/api/v2/products")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['items']) == 1
        assert data['total'] >= 1
    
    @pytest.mark.asyncio
    def test_list_products_pagination(self, client):
        """Test product listing pagination."""
        # Create multiple products
        for i in range(5):
            payload = {
                "asin": f"B00000000{i}",
                "title": f"Product {i}",
                "price": 10.0 + i,
                "product_url": f"https://amazon.com/dp/B00000000{i}",
            }
            client.post("/api/v2/products", json=payload)
        
        # Get first page
        response = client.get("/api/v2/products?limit=2&offset=0")
        data = response.json()
        
        assert len(data['items']) == 2
        assert data['limit'] == 2
        assert data['offset'] == 0
        
        # Get second page
        response = client.get("/api/v2/products?limit=2&offset=2")
        data = response.json()
        
        assert len(data['items']) == 2
    
    @pytest.mark.asyncio
    def test_list_products_filter_by_category(self, client):
        """Test filtering products by category."""
        # Create products in different categories
        client.post("/api/v2/products", json={
            "asin": "B000000001",
            "title": "Electronic Product",
            "category": "Electronics",
        })
        client.post("/api/v2/products", json={
            "asin": "B000000002",
            "title": "Home Product",
            "category": "Home & Kitchen",
        })
        
        # Filter by Electronics
        response = client.get("/api/v2/products?category=Electronics")
        data = response.json()
        
        assert len(data['items']) == 1
        assert data['items'][0]['category'] == "Electronics"
    
    @pytest.mark.asyncio
    def test_list_products_filter_by_price_range(self, client):
        """Test filtering products by price range."""
        # Create products with different prices
        for i in range(5):
            client.post("/api/v2/products", json={
                "asin": f"B00000000{i}",
                "title": f"Product {i}",
                "price": 10.0 * (i + 1),
                "product_url": f"https://amazon.com/dp/B00000000{i}",
            })
        
        # Filter by price range
        response = client.get("/api/v2/products?min_price=20&max_price=40")
        data = response.json()
        
        assert len(data['items']) == 2
        assert all(20 <= p['price'] <= 40 for p in data['items'])
    
    @pytest.mark.asyncio
    def test_list_products_filter_by_rating(self, client):
        """Test filtering products by minimum rating."""
        # Create products with different ratings
        client.post("/api/v2/products", json={
            "asin": "B000000001",
            "title": "Low Rating",
            "rating": 3.0,
        })
        client.post("/api/v2/products", json={
            "asin": "B000000002",
            "title": "High Rating",
            "rating": 4.5,
        })
        
        # Filter by min rating
        response = client.get("/api/v2/products?min_rating=4.0")
        data = response.json()
        
        assert len(data['items']) == 1
        assert data['items'][0]['rating'] >= 4.0


# ==================== Top Products Tests ====================

class TestTopProducts:
    """Tests for GET /api/v2/products/top."""
    
    @pytest.mark.asyncio
    def test_get_top_products_by_rating(self, client):
        """Test getting top products by rating."""
        # Create products with different ratings
        products = [
            {"asin": "B000000001", "title": "Product 1", "rating": 3.5},
            {"asin": "B000000002", "title": "Product 2", "rating": 4.8},
            {"asin": "B000000003", "title": "Product 3", "rating": 4.2},
        ]
        
        for product in products:
            client.post("/api/v2/products", json=product)
        
        response = client.get("/api/v2/products/top?by=rating&limit=2")
        data = response.json()
        
        assert len(data) == 2
        # First should have highest rating
        assert data[0]['rating'] >= data[1]['rating']
    
    @pytest.mark.asyncio
    def test_get_top_products_invalid_sort_field(self, client):
        """Test getting top products with invalid sort field."""
        response = client.get("/api/v2/products/top?by=invalid_field")
        
        assert response.status_code == 400


# ==================== Update Product Tests ====================

class TestUpdateProduct:
    """Tests for PUT /api/v2/products/{asin}."""
    
    @pytest.mark.asyncio
    def test_update_product_success(self, client, sample_product_payload):
        """Test updating a product."""
        # Create product
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Update product
        update_data = {"price": 59.99, "rating": 4.8}
        response = client.put(
            f"/api/v2/products/{sample_product_payload['asin']}",
            json=update_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['price'] == 59.99
        assert data['rating'] == 4.8
    
    @pytest.mark.asyncio
    def test_update_nonexistent_product(self, client):
        """Test updating non-existent product."""
        response = client.put(
            "/api/v2/products/B999999999",
            json={"price": 59.99},
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    def test_update_partial_fields(self, client, sample_product_payload):
        """Test updating only some fields."""
        # Create product
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Update only price
        response = client.put(
            f"/api/v2/products/{sample_product_payload['asin']}",
            json={"price": 39.99},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['price'] == 39.99
        assert data['title'] == sample_product_payload['title']  # Unchanged


# ==================== Delete Product Tests ====================

class TestDeleteProduct:
    """Tests for DELETE /api/v2/products/{asin}."""
    
    @pytest.mark.asyncio
    def test_delete_product_success(self, client, sample_product_payload):
        """Test deleting a product."""
        # Create product
        client.post("/api/v2/products", json=sample_product_payload)
        
        # Delete product
        response = client.delete(
            f"/api/v2/products/{sample_product_payload['asin']}",
        )
        
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/api/v2/products/{sample_product_payload['asin']}")
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    def test_delete_nonexistent_product(self, client):
        """Test deleting non-existent product."""
        response = client.delete("/api/v2/products/B999999999")
        
        assert response.status_code == 404


# ==================== Categories Tests ====================

class TestGetCategories:
    """Tests for GET /api/v2/products/categories."""
    
    @pytest.mark.asyncio
    def test_get_categories_empty(self, client):
        """Test getting categories when database is empty."""
        response = client.get("/api/v2/products/categories")
        
        assert response.status_code == 200
        assert response.json() == []
    
    @pytest.mark.asyncio
    def test_get_categories_with_data(self, client):
        """Test getting categories with data."""
        # Create products in different categories
        client.post("/api/v2/products", json={
            "asin": "B000000001",
            "title": "Electronic Product",
            "category": "Electronics",
        })
        client.post("/api/v2/products", json={
            "asin": "B000000002",
            "title": "Home Product",
            "category": "Home & Kitchen",
        })
        client.post("/api/v2/products", json={
            "asin": "B000000003",
            "title": "Another Electronic",
            "category": "Electronics",
        })
        
        response = client.get("/api/v2/products/categories")
        data = response.json()
        
        assert len(data) == 2
        assert "Electronics" in data
        assert "Home & Kitchen" in data


# ==================== Stats Tests ====================

class TestGetSummaryStats:
    """Tests for GET /api/v2/products/stats/summary."""
    
    @pytest.mark.asyncio
    def test_get_summary_stats(self, client):
        """Test getting summary statistics."""
        response = client.get("/api/v2/products/stats/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_products" in data
        assert "total_categories" in data
        assert "categories" in data
