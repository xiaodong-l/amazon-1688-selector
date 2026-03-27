"""
History API v2 Endpoints

RESTful API for product history tracking and comparison.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.connection import get_async_db_session
from src.db.repositories import HistoryRepository, ProductRepository
from src.db.models import History

history_router = APIRouter(prefix="/api/v2/history", tags=["history"])


# ==================== Pydantic Models ====================

class HistoryCreate(BaseModel):
    """Schema for creating a history record."""
    asin: str = Field(..., min_length=10, max_length=20, description="Product ASIN")
    price: Optional[float] = Field(None, ge=0, description="Price at time of recording")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Rating at time of recording")
    review_count: int = Field(default=0, ge=0, description="Review count at time of recording")
    bsr: Optional[int] = Field(None, ge=1, description="BSR at time of recording")
    recorded_at: Optional[datetime] = Field(None, description="Recording timestamp")


from datetime import datetime

class HistoryResponse(BaseModel):
    """Schema for history response."""
    id: int
    asin: str
    price: Optional[float]
    rating: Optional[float]
    review_count: int
    bsr: Optional[int]
    recorded_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class PricePoint(BaseModel):
    """Schema for price history point."""
    date: str
    price: Optional[float]


class HistoryComparison(BaseModel):
    """Schema for history comparison."""
    current: Optional[HistoryResponse]
    past: Optional[HistoryResponse]
    days_compared: int
    price_change: Optional[float] = None
    price_change_percent: Optional[float] = None
    rating_change: Optional[float] = None
    review_count_change: Optional[int] = None


class HistoryListResponse(BaseModel):
    """Schema for paginated history list."""
    items: List[HistoryResponse]
    asin: str
    total: int
    limit: int


# ==================== API Endpoints ====================

@history_router.post("", response_model=HistoryResponse, status_code=201)
async def create_history_record(history: HistoryCreate):
    """
    Create a new history record.
    
    Records current state of a product for historical tracking.
    """
    async with get_async_db_session() as session:
        repo = HistoryRepository(session)
        
        # Verify product exists
        product_repo = ProductRepository(session)
        product = await product_repo.get_by_asin(history.asin)
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with ASIN {history.asin} not found",
            )
        
        created = await repo.create(history.model_dump())
        return HistoryResponse.model_validate(created)


@history_router.get("/{asin}/latest", response_model=HistoryResponse)
async def get_latest_history(asin: str):
    """
    Get most recent history record for a product.
    
    Returns the latest recorded state.
    """
    async with get_async_db_session() as session:
        repo = HistoryRepository(session)
        
        # Verify product exists
        product_repo = ProductRepository(session)
        product = await product_repo.get_by_asin(asin)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ASIN {asin} not found")
        
        latest = await repo.get_latest(asin)
        
        if not latest:
            raise HTTPException(
                status_code=404,
                detail=f"No history records found for ASIN {asin}",
            )
        
        return HistoryResponse.model_validate(latest)


@history_router.get("/{asin}/price-history", response_model=List[PricePoint])
async def get_price_history(
    asin: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
):
    """
    Get price history for a product.
    
    Returns time-series price data for trend analysis.
    """
    async with get_async_db_session() as session:
        repo = HistoryRepository(session)
        
        # Verify product exists
        product_repo = ProductRepository(session)
        product = await product_repo.get_by_asin(asin)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ASIN {asin} not found")
        
        return await repo.get_price_history(asin=asin, days=days)


@history_router.get("/{asin}/comparison", response_model=HistoryComparison)
async def get_comparison(
    asin: str,
    days: int = Query(default=7, ge=1, le=90, description="Days to compare"),
):
    """
    Compare current vs past product data.
    
    Returns comparison between latest and historical data.
    """
    async with get_async_db_session() as session:
        repo = HistoryRepository(session)
        
        # Verify product exists
        product_repo = ProductRepository(session)
        product = await product_repo.get_by_asin(asin)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ASIN {asin} not found")
        
        comparison = await repo.get_comparison(asin=asin, days=days)
        
        # Calculate changes
        current = comparison.get('current')
        past = comparison.get('past')
        
        price_change = None
        price_change_percent = None
        rating_change = None
        review_count_change = None
        
        if current and past:
            if current.get('price') is not None and past.get('price') is not None:
                price_change = current['price'] - past['price']
                if past['price'] > 0:
                    price_change_percent = (price_change / past['price']) * 100
            
            if current.get('rating') is not None and past.get('rating') is not None:
                rating_change = current['rating'] - past['rating']
            
            review_count_change = current.get('review_count', 0) - past.get('review_count', 0)
        
        return HistoryComparison(
            current=HistoryResponse.model_validate(current) if current else None,
            past=HistoryResponse.model_validate(past) if past else None,
            days_compared=days,
            price_change=price_change,
            price_change_percent=price_change_percent,
            rating_change=rating_change,
            review_count_change=review_count_change,
        )


@history_router.delete("/{asin}", status_code=204)
async def delete_history(asin: str):
    """
    Delete all history records for a product.
    
    Removes historical data but keeps the product.
    """
    async with get_async_db_session() as session:
        repo = HistoryRepository(session)
        
        # Verify product exists
        product_repo = ProductRepository(session)
        product = await product_repo.get_by_asin(asin)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ASIN {asin} not found")
        
        await repo.delete_by_asin(asin)
        return None


@history_router.post("/cleanup", response_model=Dict[str, Any])
async def cleanup_old_records(
    days: int = Query(default=90, ge=1, le=365, description="Keep records newer than this"),
):
    """
    Clean up old history records.
    
    Removes records older than specified days.
    """
    async with get_async_db_session() as session:
        repo = HistoryRepository(session)
        
        deleted_count = await repo.delete_old_records(days=days)
        
        return {
            "deleted_count": deleted_count,
            "days_kept": days,
        }


@history_router.get("/{asin}/count")
async def get_history_count(asin: str):
    """
    Get count of history records for a product.
    
    Returns number of recorded data points.
    """
    async with get_async_db_session() as session:
        repo = HistoryRepository(session)
        
        # Verify product exists
        product_repo = ProductRepository(session)
        product = await product_repo.get_by_asin(asin)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ASIN {asin} not found")
        
        count = await repo.count_by_asin(asin)
        
        return {
            "asin": asin,
            "record_count": count,
        }


@history_router.get("/{asin}", response_model=HistoryListResponse)
async def get_history(
    asin: str,
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(default=100, ge=1, le=500, description="Max results"),
):
    """
    Get history records for a product.
    
    Returns historical data points for the specified ASIN.
    """
    async with get_async_db_session() as session:
        repo = HistoryRepository(session)
        
        # Verify product exists
        product_repo = ProductRepository(session)
        product = await product_repo.get_by_asin(asin)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ASIN {asin} not found")
        
        records = await repo.get_by_asin(
            asin=asin,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        
        return HistoryListResponse(
            items=[HistoryResponse.model_validate(r) for r in records],
            asin=asin,
            total=len(records),
            limit=limit,
        )
