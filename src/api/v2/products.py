"""
Products API v2 Endpoints

RESTful API for product management.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.connection import get_async_db_session, init_db
from src.db.repositories import ProductRepository

products_router = APIRouter(prefix="/api/v2/products", tags=["products"])


# ==================== Pydantic Models ====================

class ProductCreate(BaseModel):
    """Schema for creating a product."""
    asin: str = Field(..., min_length=10, max_length=20, description="Amazon ASIN")
    title: str = Field(..., min_length=1, max_length=500, description="Product title")
    price: Optional[float] = Field(None, ge=0, description="Price in USD")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Average rating")
    review_count: int = Field(default=0, ge=0, description="Number of reviews")
    bsr: Optional[int] = Field(None, ge=1, description="Best Sellers Rank")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    image_url: Optional[str] = Field(None, max_length=1000, description="Image URL")
    product_url: str = Field(..., min_length=1, max_length=1000, description="Amazon product URL")


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    price: Optional[float] = Field(None, ge=0)
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: Optional[int] = Field(None, ge=0)
    bsr: Optional[int] = Field(None, ge=1)
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=1000)


from datetime import datetime

class ProductResponse(BaseModel):
    """Schema for product response."""
    id: int
    asin: str
    title: str
    price: Optional[float]
    rating: Optional[float]
    review_count: int
    bsr: Optional[int]
    category: Optional[str]
    image_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for paginated product list."""
    items: List[ProductResponse]
    total: int
    limit: int
    offset: int


# ==================== Helper Functions ====================

def get_repository():
    """Get product repository with session."""
    with get_db_session() as session:
        repo = ProductRepository(session)
        yield repo


# ==================== API Endpoints ====================

@products_router.get("", response_model=ProductListResponse)
async def list_products(
    limit: int = Query(default=100, ge=1, le=500, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Results offset"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    min_reviews: Optional[int] = Query(None, ge=0, description="Minimum reviews"),
):
    """
    List products with optional filters.
    
    Returns paginated list of products matching the specified criteria.
    """
    async with get_async_db_session() as session:
        repo = ProductRepository(session)
        
        if category or min_price is not None or max_price is not None or min_rating is not None or min_reviews is not None:
            products = await repo.search(
                category=category,
                min_price=min_price,
                max_price=max_price,
                min_rating=min_rating,
                min_reviews=min_reviews,
                limit=limit,
                offset=offset,
            )
        else:
            products = await repo.get_all(limit=limit, offset=offset)
        
        total = await repo.count()
        
        return ProductListResponse(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            limit=limit,
            offset=offset,
        )


@products_router.get("/top", response_model=List[ProductResponse])
async def get_top_products(
    by: str = Query(default="rating", description="Sort field"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of results"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """
    Get top products sorted by specified field.
    
    Sort options: rating, review_count, price, created_at
    """
    valid_sort_fields = ['rating', 'review_count', 'price', 'created_at']
    if by not in valid_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field. Must be one of: {valid_sort_fields}",
        )
    
    async with get_async_db_session() as session:
        repo = ProductRepository(session)
        products = await repo.get_top_products(by=by, limit=limit, category=category)
        return [ProductResponse.model_validate(p) for p in products]


@products_router.get("/categories", response_model=List[str])
async def get_categories():
    """
    Get all unique product categories.
    
    Returns list of categories present in the database.
    """
    async with get_async_db_session() as session:
        repo = ProductRepository(session)
        return await repo.get_categories()


@products_router.get("/stats/summary")
async def get_summary_stats():
    """
    Get summary statistics for products.
    
    Returns count and basic metrics.
    """
    async with get_async_db_session() as session:
        repo = ProductRepository(session)
        
        total = await repo.count()
        categories = await repo.get_categories()
        
        return {
            "total_products": total,
            "total_categories": len(categories),
            "categories": categories,
        }


@products_router.get("/{asin}", response_model=ProductResponse)
async def get_product(asin: str):
    """
    Get product by ASIN.
    
    Returns detailed information about a specific product.
    """
    async with get_async_db_session() as session:
        repo = ProductRepository(session)
        product = await repo.get_by_asin(asin)
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ASIN {asin} not found")
        
        return ProductResponse.model_validate(product)


@products_router.post("", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate):
    """
    Create a new product.
    
    Creates a new product record in the database.
    """
    async with get_async_db_session() as session:
        repo = ProductRepository(session)
        
        # Check if ASIN already exists
        existing = await repo.get_by_asin(product.asin)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Product with ASIN {product.asin} already exists",
            )
        
        created = await repo.create(**product.model_dump())
        return ProductResponse.model_validate(created)


@products_router.put("/{asin}", response_model=ProductResponse)
async def update_product(asin: str, product: ProductUpdate):
    """
    Update an existing product.
    
    Updates fields for the specified product.
    """
    async with get_async_db_session() as session:
        repo = ProductRepository(session)
        
        updated = await repo.update(asin, **product.model_dump(exclude_unset=True))
        
        if not updated:
            raise HTTPException(status_code=404, detail=f"Product with ASIN {asin} not found")
        
        return ProductResponse.model_validate(updated)


@products_router.delete("/{asin}", status_code=204)
async def delete_product(asin: str):
    """
    Delete a product.
    
    Removes the product from the database.
    """
    async with get_async_db_session() as session:
        repo = ProductRepository(session)
        
        if not await repo.delete(asin):
            raise HTTPException(status_code=404, detail=f"Product with ASIN {asin} not found")
        
        return None
