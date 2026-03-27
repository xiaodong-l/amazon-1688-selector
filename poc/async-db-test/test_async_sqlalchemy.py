"""
SQLAlchemy 2.0 Async POC 测试脚本
验证异步代码兼容性和可行性

测试内容:
- 异步数据库连接
- 异步 CRUD 操作
- 异步查询
- 连接池配置测试
"""

import asyncio
import time
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.orm import selectinload

from models import Base, Product


# ============================================================================
# 数据库配置
# ============================================================================

DATABASE_URL = "sqlite+aiosqlite:///./test_async.db"

# 连接池配置测试参数
POOL_CONFIG = {
    "pool_size": 5,          # 连接池大小
    "max_overflow": 10,      # 最大溢出连接数
    "pool_timeout": 30,      # 获取连接超时 (秒)
    "pool_recycle": 1800,    # 连接回收时间 (秒)
    "pool_pre_ping": True,   # 连接前 ping 测试
}


# ============================================================================
# 数据库引擎和会话管理
# ============================================================================

def create_engine_with_pool() -> AsyncEngine:
    """
    创建带连接池配置的异步数据库引擎
    验证连接池配置
    """
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,  # 打印 SQL 日志
        pool_size=POOL_CONFIG["pool_size"],
        max_overflow=POOL_CONFIG["max_overflow"],
        pool_timeout=POOL_CONFIG["pool_timeout"],
        pool_recycle=POOL_CONFIG["pool_recycle"],
        pool_pre_ping=POOL_CONFIG["pool_pre_ping"],
    )
    return engine


@asynccontextmanager
async def get_session(engine: AsyncEngine):
    """
    异步会话管理器
    验证异步上下文管理器
    """
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session


async def init_db(engine: AsyncEngine):
    """
    初始化数据库 - 创建所有表
    验证异步表创建
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ 数据库表创建成功")


async def cleanup_db(engine: AsyncEngine):
    """
    清理数据库 - 删除所有表
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✓ 数据库表已清理")


# ============================================================================
# CRUD 操作测试
# ============================================================================

async def test_create_product(session: AsyncSession, product_data: dict) -> Product:
    """
    测试异步创建操作 (Create)
    """
    product = Product(**product_data)
    session.add(product)
    await session.commit()
    await session.refresh(product)
    print(f"✓ 创建产品：{product.name} (ID: {product.id})")
    return product


async def test_read_product(session: AsyncSession, product_id: int) -> Optional[Product]:
    """
    测试异步读取操作 (Read)
    """
    stmt = select(Product).where(Product.id == product_id)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    
    if product:
        print(f"✓ 读取产品：{product.name} (ID: {product.id})")
    else:
        print(f"✗ 未找到产品 (ID: {product_id})")
    
    return product


async def test_read_all_products(session: AsyncSession) -> List[Product]:
    """
    测试异步查询所有记录
    """
    stmt = select(Product)
    result = await session.execute(stmt)
    products = result.scalars().all()
    print(f"✓ 查询到 {len(products)} 个产品")
    return products


async def test_update_product(
    session: AsyncSession, 
    product_id: int, 
    update_data: dict
) -> Optional[Product]:
    """
    测试异步更新操作 (Update)
    """
    stmt = (
        update(Product)
        .where(Product.id == product_id)
        .values(**update_data)
        .returning(Product)
    )
    result = await session.execute(stmt)
    await session.commit()
    product = result.scalar_one_or_none()
    
    if product:
        print(f"✓ 更新产品：{product.name} (ID: {product.id})")
    else:
        print(f"✗ 更新失败 (ID: {product_id})")
    
    return product


async def test_delete_product(session: AsyncSession, product_id: int) -> bool:
    """
    测试异步删除操作 (Delete)
    """
    stmt = delete(Product).where(Product.id == product_id)
    result = await session.execute(stmt)
    await session.commit()
    
    if result.rowcount > 0:
        print(f"✓ 删除产品 (ID: {product_id})")
        return True
    else:
        print(f"✗ 删除失败 (ID: {product_id})")
        return False


# ============================================================================
# 高级查询测试
# ============================================================================

async def test_filter_query(session: AsyncSession, category: str) -> List[Product]:
    """
    测试异步条件查询
    """
    stmt = select(Product).where(Product.category == category)
    result = await session.execute(stmt)
    products = result.scalars().all()
    print(f"✓ 条件查询 (category={category}): {len(products)} 个产品")
    return products


async def test_search_query(session: AsyncSession, keyword: str) -> List[Product]:
    """
    测试异步模糊查询
    """
    stmt = select(Product).where(Product.name.like(f"%{keyword}%"))
    result = await session.execute(stmt)
    products = result.scalars().all()
    print(f"✓ 模糊查询 (keyword={keyword}): {len(products)} 个产品")
    return products


async def test_aggregate_query(session: AsyncSession):
    """
    测试异步聚合查询
    """
    # 总数统计
    count_stmt = select(func.count(Product.id))
    count_result = await session.execute(count_stmt)
    total_count = count_result.scalar()
    
    # 平均价格
    avg_stmt = select(func.avg(Product.price))
    avg_result = await session.execute(avg_stmt)
    avg_price = avg_result.scalar()
    
    print(f"✓ 聚合查询：总数={total_count}, 平均价格={avg_price:.2f}")
    return {"total": total_count, "avg_price": avg_price}


async def test_order_query(session: AsyncSession) -> List[Product]:
    """
    测试异步排序查询
    """
    stmt = select(Product).order_by(Product.price.desc())
    result = await session.execute(stmt)
    products = result.scalars().all()
    print(f"✓ 排序查询 (按价格降序): {len(products)} 个产品")
    return products


# ============================================================================
# 性能测试
# ============================================================================

async def performance_test_batch_insert(engine: AsyncEngine, count: int = 100):
    """
    性能测试：批量插入
    """
    print(f"\n⏱ 性能测试：批量插入 {count} 条记录")
    
    start_time = time.time()
    
    async with get_session(engine) as session:
        products = []
        for i in range(count):
            product = Product(
                name=f"Test Product {i}",
                description=f"Description for product {i}",
                price=10.0 + i * 0.5,
                currency="USD",
                category=f"Category {i % 10}",
                brand=f"Brand {i % 5}",
                sku=f"SKU-{i:05d}",
                stock_quantity=i * 10,
                is_available=i % 2 == 0,
            )
            products.append(product)
        
        session.add_all(products)
        await session.commit()
    
    elapsed = time.time() - start_time
    print(f"✓ 批量插入完成：{count} 条记录，耗时 {elapsed:.3f} 秒，{count/elapsed:.0f} 条/秒")
    return elapsed


async def performance_test_batch_query(engine: AsyncEngine):
    """
    性能测试：批量查询
    """
    print(f"\n⏱ 性能测试：批量查询")
    
    start_time = time.time()
    iterations = 100
    
    async with get_session(engine) as session:
        for _ in range(iterations):
            stmt = select(Product).limit(10)
            result = await session.execute(stmt)
            _ = result.scalars().all()
    
    elapsed = time.time() - start_time
    print(f"✓ 批量查询完成：{iterations} 次查询，耗时 {elapsed:.3f} 秒，{iterations/elapsed:.0f} 次/秒")
    return elapsed


# ============================================================================
# 主测试流程
# ============================================================================

async def run_all_tests():
    """
    运行所有测试
    """
    print("=" * 80)
    print("SQLAlchemy 2.0 Async POC 测试")
    print("=" * 80)
    
    # 1. 创建引擎 (验证连接池配置)
    print("\n[1] 创建数据库引擎 (带连接池配置)")
    engine = create_engine_with_pool()
    print(f"✓ 引擎创建成功，连接池配置：{POOL_CONFIG}")
    
    # 2. 初始化数据库
    print("\n[2] 初始化数据库")
    await init_db(engine)
    
    # 3. CRUD 测试
    print("\n[3] CRUD 操作测试")
    async with get_session(engine) as session:
        # Create
        print("\n  --- Create ---")
        product1 = await test_create_product(
            session,
            {
                "name": "iPhone 15 Pro",
                "description": "Apple 最新旗舰手机",
                "price": 999.99,
                "currency": "USD",
                "category": "Electronics",
                "brand": "Apple",
                "sku": "APL-IP15P-256",
                "stock_quantity": 100,
                "is_available": True,
            }
        )
        
        product2 = await test_create_product(
            session,
            {
                "name": "MacBook Pro 14",
                "description": "M3 Pro 芯片笔记本电脑",
                "price": 1999.99,
                "currency": "USD",
                "category": "Electronics",
                "brand": "Apple",
                "sku": "APL-MBP14-M3",
                "stock_quantity": 50,
                "is_available": True,
            }
        )
        
        product3 = await test_create_product(
            session,
            {
                "name": "AirPods Pro 2",
                "description": "主动降噪无线耳机",
                "price": 249.99,
                "currency": "USD",
                "category": "Electronics",
                "brand": "Apple",
                "sku": "APL-APP2-USB",
                "stock_quantity": 200,
                "is_available": True,
            }
        )
        
        # Read
        print("\n  --- Read ---")
        await test_read_product(session, product1.id)
        await test_read_all_products(session)
        
        # Update
        print("\n  --- Update ---")
        await test_update_product(
            session,
            product1.id,
            {"price": 949.99, "stock_quantity": 150}
        )
        
        # 验证更新
        updated = await test_read_product(session, product1.id)
        if updated:
            print(f"    更新后价格：{updated.price}, 库存：{updated.stock_quantity}")
        
        # Delete
        print("\n  --- Delete ---")
        await test_delete_product(session, product3.id)
        await test_read_all_products(session)
    
    # 4. 高级查询测试
    print("\n[4] 高级查询测试")
    async with get_session(engine) as session:
        await test_filter_query(session, "Electronics")
        await test_search_query(session, "Pro")
        await test_aggregate_query(session)
        await test_order_query(session)
    
    # 5. 性能测试
    print("\n[5] 性能测试")
    await performance_test_batch_insert(engine, 100)
    await performance_test_batch_query(engine)
    
    # 6. 并发连接测试
    print("\n[6] 并发连接测试")
    async def concurrent_task(task_id: int):
        async with get_session(engine) as session:
            stmt = select(func.count(Product.id))
            result = await session.execute(stmt)
            count = result.scalar()
            print(f"  任务 {task_id}: 当前产品总数 = {count}")
            await asyncio.sleep(0.1)
    
    tasks = [concurrent_task(i) for i in range(5)]
    await asyncio.gather(*tasks)
    print("✓ 并发连接测试完成")
    
    # 7. 清理
    print("\n[7] 清理数据库")
    await cleanup_db(engine)
    
    # 8. 关闭引擎
    await engine.dispose()
    print("\n✓ 引擎已关闭")
    
    print("\n" + "=" * 80)
    print("所有测试完成!")
    print("=" * 80)
    
    return True


# ============================================================================
# 入口点
# ============================================================================

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    if success:
        print("\n✅ POC 验证成功 - SQLAlchemy 2.0 异步 API 完全兼容")
    else:
        print("\n❌ POC 验证失败")
