#!/usr/bin/env python3
"""
Bugfix Verification Script for Major Issues

Standalone script to verify the 3 Major bugfixes without pytest.
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.connection import (
    get_async_engine, 
    get_async_session_factory, 
    init_db_async, 
    drop_db_async, 
    reset_db_async, 
    close_all_async
)
from src.db.repositories.product_repo import ProductRepository
from src.db.repositories.history_repo import HistoryRepository
from src.db.models.history import PriceHistory


async def test_soft_delete_fix():
    """Test soft delete auto-filter fix."""
    print("\n" + "="*60)
    print("TEST 1: Soft Delete Auto-Filter Fix")
    print("="*60)
    
    engine = get_async_engine(test_mode=True)
    await init_db_async(test_mode=True)
    
    factory = get_async_session_factory()
    async with factory() as session:
        repo = ProductRepository(session)
        
        # Test 1a: Create and soft delete
        print("\n[1a] Creating product and testing soft delete...")
        product = await repo.create(
            asin='B000000001',
            title='Test Product',
            price=29.99,
            product_url='https://amazon.com/dp/B000000001',
        )
        assert product.id is not None, "Product should have ID"
        assert product.is_deleted == False, "New product should not be deleted"
        print(f"  ✓ Created product: {product.asin}")
        
        # Soft delete
        result = await repo.delete('B000000001')
        assert result == True, "Delete should succeed"
        print(f"  ✓ Soft delete returned True")
        
        # Verify soft delete flags
        deleted_product = await repo.get_by_asin('B000000001', include_deleted=True)
        assert deleted_product is not None, "Should find product with include_deleted=True"
        assert deleted_product.is_deleted == True, "Product should be marked as deleted"
        assert deleted_product.deleted_at is not None, "deleted_at should be set"
        print(f"  ✓ Product soft-deleted (is_deleted={deleted_product.is_deleted}, deleted_at={deleted_product.deleted_at})")
        
        # Test 1b: Auto-filter in queries
        print("\n[1b] Testing auto-filter in queries...")
        
        # Create another product
        await repo.create(
            asin='B000000002',
            title='Active Product',
            price=39.99,
            product_url='https://amazon.com/dp/B000000002',
        )
        
        # Get by ASIN should not find deleted product
        deleted = await repo.get_by_asin('B000000001')
        assert deleted is None, "Should not find deleted product by default"
        print(f"  ✓ get_by_asin() correctly filters deleted products")
        
        # Get all should not include deleted
        all_products = await repo.get_all()
        assert len(all_products) == 1, f"Should have 1 active product, got {len(all_products)}"
        assert all_products[0].asin == 'B000000002', "Should only return active product"
        print(f"  ✓ get_all() correctly filters deleted products (count={len(all_products)})")
        
        # Test 1c: Restore
        print("\n[1c] Testing restore() method...")
        result = await repo.restore('B000000001')
        assert result == True, "Restore should succeed"
        
        restored = await repo.get_by_asin('B000000001')
        assert restored is not None, "Should find restored product"
        assert restored.is_deleted == False, "Restored product should not be deleted"
        assert restored.deleted_at is None, "Restored product deleted_at should be None"
        print(f"  ✓ Product restored successfully")
        
        # Test 1d: Search filters deleted
        print("\n[1d] Testing search auto-filter...")
        await repo.delete('B000000001')  # Delete again
        results = await repo.search()
        assert len(results) == 1, f"Search should return 1 active product, got {len(results)}"
        print(f"  ✓ search() correctly filters deleted products")
    
    await close_all_async()
    print("\n✅ Soft Delete Fix: ALL TESTS PASSED")
    return True


async def test_get_trend_null_safety():
    """Test get_trend() null safety fix."""
    print("\n" + "="*60)
    print("TEST 2: get_trend() Null Safety Fix")
    print("="*60)
    
    engine = get_async_engine(test_mode=True)
    await init_db_async(test_mode=True)
    
    factory = get_async_session_factory()
    async with factory() as session:
        repo = HistoryRepository(session)
        
        # Test 2a: No data returns safe defaults
        print("\n[2a] Testing get_trend with no data...")
        result = await repo.get_trend('B999999999', days=30, metric='price')
        
        assert result['current'] is None, "current should be None"
        assert result['previous'] is None, "previous should be None"
        assert result['change'] is None, "change should be None"
        assert result['change_percent'] is None, "change_percent should be None"
        assert result['trend'] == 'unknown', "trend should be 'unknown'"
        assert result['data_points'] == [], "data_points should be empty"
        assert result['error'] is None, "error should be None"
        print(f"  ✓ Returns safe defaults for missing data")
        
        # Test 2b: Valid data calculates correctly
        print("\n[2b] Testing get_trend with valid data...")
        
        # Create price history
        for i, price in enumerate([10.0, 15.0, 20.0, 25.0]):
            ph = PriceHistory(
                product_id=1,
                asin='B000000011',
                price=price,
                recorded_at=datetime.utcnow() - timedelta(days=10 - i*2),
            )
            session.add(ph)
        
        await session.commit()
        
        result = await repo.get_trend('B000000011', days=30, metric='price')
        
        assert result['current'] == 25.0, f"current should be 25.0, got {result['current']}"
        assert result['previous'] == 10.0, f"previous should be 10.0, got {result['previous']}"
        assert result['change'] == 15.0, f"change should be 15.0, got {result['change']}"
        assert result['change_percent'] == 150.0, f"change_percent should be 150.0, got {result['change_percent']}"
        assert result['trend'] == 'up', f"trend should be 'up', got {result['trend']}"
        assert len(result['data_points']) == 4, f"should have 4 data points, got {len(result['data_points'])}"
        print(f"  ✓ Correctly calculates trend: {result['trend']} (+{result['change_percent']}%)")
        
        # Test 2c: Null values in records (using ProductHistory which allows null rating)
        print("\n[2c] Testing get_trend with null values...")
        
        from src.db.models.history import ProductHistory
        
        # Create history with null rating (ProductHistory allows null rating)
        ph1 = ProductHistory(
            product_id=1,
            asin='B000000012',
            price=10.0,
            rating=4.5,
            recorded_at=datetime.utcnow() - timedelta(days=10),
        )
        ph2 = ProductHistory(
            product_id=1,
            asin='B000000012',
            price=15.0,
            rating=None,  # Null rating
            recorded_at=datetime.utcnow() - timedelta(days=5),
        )
        ph3 = ProductHistory(
            product_id=1,
            asin='B000000012',
            price=20.0,
            rating=4.8,
            recorded_at=datetime.utcnow(),
        )
        session.add_all([ph1, ph2, ph3])
        await session.commit()
        
        # Should handle gracefully without crashing when accessing rating
        result = await repo.get_trend('B000000012', days=30, metric='rating')
        assert 'trend' in result, "Should return result even with null values"
        print(f"  ✓ Handles null values gracefully (trend={result['trend']})")
    
    await close_all_async()
    print("\n✅ get_trend() Null Safety: ALL TESTS PASSED")
    return True


async def test_reset_db_exception_handling():
    """Test reset_db() exception handling fix."""
    print("\n" + "="*60)
    print("TEST 3: reset_db() Exception Handling Fix")
    print("="*60)
    
    import inspect
    from src.db import connection
    
    # Test 3a: Check source code has exception handling
    print("\n[3a] Checking reset_db() source code...")
    source = inspect.getsource(connection.reset_db)
    
    checks = [
        ('try:', 'try block'),
        ('except', 'except block'),
        ('logger.', 'logging'),
    ]
    
    for check, desc in checks:
        assert check in source, f"reset_db() should have {desc}"
        print(f"  ✓ Has {desc}")
    
    # Test 3b: Check reset_db_async has exception handling
    print("\n[3b] Checking reset_db_async() source code...")
    source_async = inspect.getsource(connection.reset_db_async)
    
    for check, desc in checks:
        assert check in source_async, f"reset_db_async() should have {desc}"
        print(f"  ✓ Has {desc}")
    
    # Test 3c: Actually run reset_db
    print("\n[3c] Testing reset_db_async() execution...")
    
    # Initialize first
    await init_db_async(test_mode=True)
    print(f"  ✓ Initialized database")
    
    # Reset should work without errors
    try:
        result = await reset_db_async(test_mode=True)
        assert result == True, "reset_db_async should return True"
        print(f"  ✓ reset_db_async() completed successfully (returned {result})")
    except Exception as e:
        print(f"  ✗ reset_db_async() failed: {e}")
        raise
    
    await close_all_async()
    print("\n✅ reset_db() Exception Handling: ALL TESTS PASSED")
    return True


async def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("BUGFIX VERIFICATION - MAJOR ISSUES")
    print("="*60)
    print("\nVerifying 3 Major bugfixes:")
    print("  1. Soft Delete Auto-Filter")
    print("  2. get_trend() Null Safety")
    print("  3. reset_db() Exception Handling")
    
    results = []
    
    try:
        results.append(await test_soft_delete_fix())
    except Exception as e:
        print(f"\n❌ Soft Delete Fix FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    try:
        results.append(await test_get_trend_null_safety())
    except Exception as e:
        print(f"\n❌ get_trend() Null Safety FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    try:
        results.append(await test_reset_db_exception_handling())
    except Exception as e:
        print(f"\n❌ reset_db() Exception Handling FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(False)
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"\n  Passed: {passed}/{total}")
    
    if all(results):
        print("\n  ✅ ALL MAJOR BUGFIXES VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print("\n  ❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
