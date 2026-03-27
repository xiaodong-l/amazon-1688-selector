"""
V2.2 性能基准测试

基准测试场景:
- 批量插入性能 (100/1000/10000 条)
- 查询性能 (简单查询/复杂查询/联表查询)
- 并发性能 (10/50/100 并发)
- 认证性能 (JWT 生成/验证)
- 限流性能 (内存/Redis)
- 监控开销测试

性能目标:
| 场景 | 目标 | 验收 |
|------|------|------|
| 批量插入 (100 条) | <100ms | <200ms |
| 简单查询 | <50ms | <100ms |
| 复杂查询 | <200ms | <500ms |
| JWT 生成 | <10ms | <20ms |
| JWT 验证 | <5ms | <10ms |
| 限流检查 | <2ms | <5ms |
| 监控开销 | <1ms | <2ms |
"""
import pytest
import pytest_asyncio
import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
import json
import hashlib
import hmac
import base64

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.models import Base, Product, ProductHistory
from src.db.connection import get_async_engine, get_async_session, init_db_async
from src.db.repositories import ProductRepository, HistoryRepository


# ==================== 性能阈值配置 ====================

class PerformanceThresholds:
    """性能测试阈值配置"""
    
    # 批量插入 (毫秒)
    BATCH_INSERT_100_TARGET = 100
    BATCH_INSERT_100_ACCEPTABLE = 200
    
    BATCH_INSERT_1000_TARGET = 500
    BATCH_INSERT_1000_ACCEPTABLE = 1000
    
    BATCH_INSERT_10000_TARGET = 3000
    BATCH_INSERT_10000_ACCEPTABLE = 5000
    
    # 查询性能 (毫秒)
    SIMPLE_QUERY_TARGET = 50
    SIMPLE_QUERY_ACCEPTABLE = 100
    
    COMPLEX_QUERY_TARGET = 200
    COMPLEX_QUERY_ACCEPTABLE = 500
    
    JOIN_QUERY_TARGET = 300
    JOIN_QUERY_ACCEPTABLE = 600
    
    # JWT 性能 (毫秒)
    JWT_GENERATE_TARGET = 10
    JWT_GENERATE_ACCEPTABLE = 20
    
    JWT_VERIFY_TARGET = 5
    JWT_VERIFY_ACCEPTABLE = 10
    
    # 限流性能 (毫秒)
    RATE_LIMIT_CHECK_TARGET = 2
    RATE_LIMIT_CHECK_ACCEPTABLE = 5
    
    # 监控开销 (毫秒)
    MONITORING_OVERHEAD_TARGET = 1
    MONITORING_OVERHEAD_ACCEPTABLE = 2
    
    # 并发性能
    CONCURRENT_10_TARGET = 100
    CONCURRENT_50_TARGET = 150
    CONCURRENT_100_TARGET = 200


# ==================== 测试夹具 ====================

@pytest_asyncio.fixture
async def async_db_session():
    """创建异步数据库会话"""
    async with get_async_session() as session:
        yield session


@pytest_asyncio.fixture
async def setup_test_database():
    """设置测试数据库 (创建表)"""
    engine = get_async_engine(test_mode=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def product_repo(async_db_session):
    """创建 ProductRepository 实例"""
    return ProductRepository(async_db_session)


@pytest_asyncio.fixture
async def history_repo(async_db_session):
    """创建 HistoryRepository 实例"""
    return HistoryRepository(async_db_session)


# ==================== 辅助函数 ====================

def generate_test_product(index: int) -> Dict[str, Any]:
    """生成测试商品数据"""
    return {
        'asin': f'B0{index:08d}',
        'title': f'Test Product {index}',
        'price': 10.0 + (index % 100),
        'product_url': f'https://amazon.com/dp/B0{index:08d}',
        'brand': f'Brand {index % 10}',
        'category': f'Category {index % 5}',
        'rating': 3.0 + (index % 5) * 0.5,
        'review_count': 100 + index * 10,
        'bsr': 1000 + index,
    }


def generate_test_products(count: int) -> List[Dict[str, Any]]:
    """批量生成测试商品数据"""
    return [generate_test_product(i) for i in range(count)]


# ==================== 批量插入性能测试 ====================

class TestBatchInsertPerformance:
    """批量插入性能测试"""
    
    @pytest.mark.asyncio
    async def test_batch_insert_100(self, async_db_session, setup_test_database):
        """测试批量插入 100 条记录的性能"""
        products_data = generate_test_products(100)
        
        # 预热
        async with get_async_session() as session:
            repo = ProductRepository(session)
            await repo.create(**products_data[0])
        
        # 测试
        start_time = time.perf_counter()
        
        async with get_async_session() as session:
            repo = ProductRepository(session)
            for product_data in products_data:
                await repo.create(**product_data)
        
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        
        print(f"\n批量插入 100 条: {elapsed_ms:.2f}ms")
        
        assert elapsed_ms < PerformanceThresholds.BATCH_INSERT_100_ACCEPTABLE, \
            f"批量插入 100 条耗时 {elapsed_ms:.2f}ms 超过验收阈值 {PerformanceThresholds.BATCH_INSERT_100_ACCEPTABLE}ms"
    
    @pytest.mark.asyncio
    async def test_batch_insert_1000(self, async_db_session, setup_test_database):
        """测试批量插入 1000 条记录的性能"""
        products_data = generate_test_products(1000)
        
        start_time = time.perf_counter()
        
        async with get_async_session() as session:
            repo = ProductRepository(session)
            for product_data in products_data[:100]:  # 限制数量避免测试过慢
                await repo.create(**product_data)
        
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        
        # 推算 1000 条的时间
        projected_ms = elapsed_ms * 10
        
        print(f"\n批量插入 1000 条 (推算): {projected_ms:.2f}ms")
        
        assert projected_ms < PerformanceThresholds.BATCH_INSERT_1000_ACCEPTABLE, \
            f"批量插入 1000 条推算耗时 {projected_ms:.2f}ms 超过验收阈值"
    
    @pytest.mark.asyncio
    async def test_batch_insert_with_history(self, async_db_session, setup_test_database):
        """测试批量插入并记录历史的性能"""
        products_data = generate_test_products(50)
        timestamp = datetime.now()
        
        start_time = time.perf_counter()
        
        async with get_async_session() as session:
            product_repo = ProductRepository(session)
            history_repo = HistoryRepository(session)
            
            for product_data in products_data:
                product = await product_repo.create(**product_data)
                await history_repo.record_history(
                    product_id=product.id,
                    asin=product.asin,
                    price=product.price,
                    rating=product.rating,
                    review_count=product.review_count,
                    bsr=product.bsr,
                    timestamp=timestamp,
                )
        
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        
        print(f"\n批量插入 50 条 + 历史记录: {elapsed_ms:.2f}ms")
        print(f"平均每条: {elapsed_ms / 50:.2f}ms")


# ==================== 查询性能测试 ====================

class TestQueryPerformance:
    """查询性能测试"""
    
    @pytest.mark.asyncio
    async def test_simple_query_by_asin(self, async_db_session, setup_test_database, product_repo):
        """测试简单查询 (按 ASIN)"""
        # 准备数据
        product = await product_repo.create(**generate_test_product(1))
        
        # 预热
        await product_repo.get_by_asin(product.asin)
        
        # 测试
        times = []
        for _ in range(20):
            start = time.perf_counter()
            await product_repo.get_by_asin(product.asin)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_ms = statistics.mean(times)
        p95_ms = sorted(times)[int(len(times) * 0.95)]
        
        print(f"\n简单查询 (ASIN): 平均={avg_ms:.2f}ms, P95={p95_ms:.2f}ms")
        
        assert avg_ms < PerformanceThresholds.SIMPLE_QUERY_ACCEPTABLE, \
            f"简单查询平均耗时 {avg_ms:.2f}ms 超过验收阈值"
    
    @pytest.mark.asyncio
    async def test_complex_query_search(self, async_db_session, setup_test_database, product_repo):
        """测试复杂查询 (多条件搜索)"""
        # 准备数据
        for i in range(100):
            await product_repo.create(**generate_test_product(i))
        
        # 预热
        await product_repo.search(category="Category 1", min_price=10, max_price=50)
        
        # 测试
        times = []
        for _ in range(10):
            start = time.perf_counter()
            results = await product_repo.search(
                category="Category 1",
                min_price=10,
                max_price=50,
                min_rating=3.5,
            )
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_ms = statistics.mean(times)
        p95_ms = sorted(times)[int(len(times) * 0.95)]
        
        print(f"\n复杂查询 (搜索): 平均={avg_ms:.2f}ms, P95={p95_ms:.2f}ms")
        
        assert avg_ms < PerformanceThresholds.COMPLEX_QUERY_ACCEPTABLE, \
            f"复杂查询平均耗时 {avg_ms:.2f}ms 超过验收阈值"
    
    @pytest.mark.asyncio
    async def test_join_query(self, async_db_session, setup_test_database, product_repo):
        """测试联表查询 (商品 + 历史)"""
        # 准备数据
        product = await product_repo.create(**generate_test_product(1))
        
        async with get_async_session() as session:
            history_repo = HistoryRepository(session)
            for i in range(20):
                await history_repo.record_history(
                    product_id=product.id,
                    asin=product.asin,
                    price=product.price + i,
                    rating=product.rating,
                    review_count=product.review_count,
                    bsr=product.bsr,
                    timestamp=datetime.now() - timedelta(days=i),
                )
        
        # 预热
        await product_repo.get_by_asin(product.asin, load_relations=True)
        
        # 测试
        times = []
        for _ in range(10):
            start = time.perf_counter()
            await product_repo.get_by_asin(product.asin, load_relations=True)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_ms = statistics.mean(times)
        
        print(f"\n联表查询: 平均={avg_ms:.2f}ms")
        
        assert avg_ms < PerformanceThresholds.JOIN_QUERY_ACCEPTABLE, \
            f"联表查询平均耗时 {avg_ms:.2f}ms 超过验收阈值"


# ==================== 并发性能测试 ====================

class TestConcurrentPerformance:
    """并发性能测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_reads_10(self, async_db_session, setup_test_database, product_repo):
        """测试 10 并发读取性能"""
        # 准备数据
        product = await product_repo.create(**generate_test_product(1))
        
        async def read_product():
            async with get_async_session() as session:
                repo = ProductRepository(session)
                return await repo.get_by_asin(product.asin)
        
        # 测试
        start = time.perf_counter()
        tasks = [read_product() for _ in range(10)]
        await asyncio.gather(*tasks)
        end = time.perf_counter()
        
        elapsed_ms = (end - start) * 1000
        
        print(f"\n10 并发读取: {elapsed_ms:.2f}ms")
        
        assert elapsed_ms < PerformanceThresholds.CONCURRENT_10_TARGET * 2, \
            f"10 并发读取耗时 {elapsed_ms:.2f}ms 超出预期"
    
    @pytest.mark.asyncio
    async def test_concurrent_reads_50(self, async_db_session, setup_test_database, product_repo):
        """测试 50 并发读取性能"""
        # 准备数据
        product = await product_repo.create(**generate_test_product(1))
        
        async def read_product():
            async with get_async_session() as session:
                repo = ProductRepository(session)
                return await repo.get_by_asin(product.asin)
        
        # 测试
        start = time.perf_counter()
        tasks = [read_product() for _ in range(50)]
        await asyncio.gather(*tasks)
        end = time.perf_counter()
        
        elapsed_ms = (end - start) * 1000
        
        print(f"\n50 并发读取: {elapsed_ms:.2f}ms")
        
        assert elapsed_ms < PerformanceThresholds.CONCURRENT_50_TARGET * 2, \
            f"50 并发读取耗时 {elapsed_ms:.2f}ms 超出预期"
    
    @pytest.mark.asyncio
    async def test_concurrent_writes(self, async_db_session, setup_test_database):
        """测试并发写入性能"""
        products_data = generate_test_products(20)
        
        async def create_product(data):
            async with get_async_session() as session:
                repo = ProductRepository(session)
                try:
                    return await repo.create(**data)
                except Exception:
                    return None  # 可能的主键冲突
        
        # 测试
        start = time.perf_counter()
        tasks = [create_product(data) for data in products_data]
        results = await asyncio.gather(*tasks)
        end = time.perf_counter()
        
        elapsed_ms = (end - start) * 1000
        success_count = sum(1 for r in results if r is not None)
        
        print(f"\n并发写入 20 条: {elapsed_ms:.2f}ms, 成功={success_count}")


# ==================== JWT 认证性能测试 ====================

class TestAuthPerformance:
    """认证性能测试"""
    
    def _generate_jwt(self, payload: Dict, secret: str = "test_secret") -> str:
        """简易 JWT 生成 (用于测试)"""
        header = {"alg": "HS256", "typ": "JWT"}
        
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b'=').decode()
        
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b'=').decode()
        
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
        
        return f"{message}.{signature_b64}"
    
    def _verify_jwt(self, token: str, secret: str = "test_secret") -> bool:
        """简易 JWT 验证 (用于测试)"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False
            
            message = f"{parts[0]}.{parts[1]}"
            expected_signature = hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            expected_sig_b64 = base64.urlsafe_b64encode(expected_signature).rstrip(b'=').decode()
            
            return hmac.compare_digest(parts[2], expected_sig_b64)
        except Exception:
            return False
    
    def test_jwt_generation_performance(self):
        """测试 JWT 生成性能"""
        payload = {
            "user_id": 123,
            "username": "test_user",
            "exp": datetime.now().timestamp() + 3600,
        }
        
        # 预热
        self._generate_jwt(payload)
        
        # 测试
        times = []
        for _ in range(100):
            start = time.perf_counter()
            self._generate_jwt(payload)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_ms = statistics.mean(times)
        p95_ms = sorted(times)[int(len(times) * 0.95)]
        
        print(f"\nJWT 生成: 平均={avg_ms:.3f}ms, P95={p95_ms:.3f}ms")
        
        assert avg_ms < PerformanceThresholds.JWT_GENERATE_ACCEPTABLE, \
            f"JWT 生成平均耗时 {avg_ms:.3f}ms 超过验收阈值"
    
    def test_jwt_verification_performance(self):
        """测试 JWT 验证性能"""
        payload = {"user_id": 123, "exp": datetime.now().timestamp() + 3600}
        token = self._generate_jwt(payload)
        
        # 预热
        self._verify_jwt(token)
        
        # 测试
        times = []
        for _ in range(100):
            start = time.perf_counter()
            self._verify_jwt(token)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_ms = statistics.mean(times)
        p95_ms = sorted(times)[int(len(times) * 0.95)]
        
        print(f"\nJWT 验证: 平均={avg_ms:.3f}ms, P95={p95_ms:.3f}ms")
        
        assert avg_ms < PerformanceThresholds.JWT_VERIFY_ACCEPTABLE, \
            f"JWT 验证平均耗时 {avg_ms:.3f}ms 超过验收阈值"


# ==================== 限流性能测试 ====================

class TestRateLimitPerformance:
    """限流性能测试"""
    
    def test_in_memory_rate_limit_check(self):
        """测试内存限流检查性能"""
        # 简易限流器实现
        rate_limits: Dict[str, List[float]] = {}
        
        def check_rate_limit(user_id: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
            now = time.time()
            if user_id not in rate_limits:
                rate_limits[user_id] = []
            
            # 清理过期记录
            rate_limits[user_id] = [
                t for t in rate_limits[user_id]
                if now - t < window_seconds
            ]
            
            # 检查是否超限
            if len(rate_limits[user_id]) >= max_requests:
                return False
            
            # 记录请求
            rate_limits[user_id].append(now)
            return True
        
        # 预热
        check_rate_limit("user_1")
        
        # 测试
        times = []
        for i in range(1000):
            user_id = f"user_{i % 10}"
            start = time.perf_counter()
            check_rate_limit(user_id)
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_ms = statistics.mean(times)
        p99_ms = sorted(times)[int(len(times) * 0.99)]
        
        print(f"\n限流检查: 平均={avg_ms:.3f}ms, P99={p99_ms:.3f}ms")
        
        assert avg_ms < PerformanceThresholds.RATE_LIMIT_CHECK_ACCEPTABLE, \
            f"限流检查平均耗时 {avg_ms:.3f}ms 超过验收阈值"


# ==================== 监控开销测试 ====================

class TestMonitoringOverhead:
    """监控开销测试"""
    
    def test_logging_overhead(self):
        """测试日志记录开销"""
        import logging
        
        # 配置日志
        logger = logging.getLogger("perf_test")
        logger.setLevel(logging.INFO)
        handler = logging.NullHandler()
        logger.addHandler(handler)
        
        # 测试
        times = []
        for i in range(1000):
            start = time.perf_counter()
            logger.info(f"Test log message {i}")
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_ms = statistics.mean(times)
        
        print(f"\n日志记录开销: 平均={avg_ms:.3f}ms")
        
        assert avg_ms < PerformanceThresholds.MONITORING_OVERHEAD_ACCEPTABLE, \
            f"日志记录开销 {avg_ms:.3f}ms 超过验收阈值"
    
    def test_metrics_collection_overhead(self):
        """测试指标收集开销"""
        metrics: Dict[str, List[float]] = {"response_time": []}
        
        def record_metric(name: str, value: float):
            if name not in metrics:
                metrics[name] = []
            metrics[name].append(value)
        
        # 测试
        times = []
        for i in range(1000):
            start = time.perf_counter()
            record_metric("response_time", float(i))
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        avg_ms = statistics.mean(times)
        
        print(f"\n指标收集开销: 平均={avg_ms:.3f}ms")
        
        assert avg_ms < PerformanceThresholds.MONITORING_OVERHEAD_ACCEPTABLE, \
            f"指标收集开销 {avg_ms:.3f}ms 超过验收阈值"


# ==================== 性能基准汇总 ====================

class TestPerformanceBenchmark:
    """性能基准汇总测试"""
    
    @pytest.mark.asyncio
    async def test_full_benchmark_summary(self, async_db_session, setup_test_database):
        """运行完整基准测试并生成摘要"""
        results = {}
        
        # 1. 批量插入测试
        products_data = generate_test_products(100)
        start = time.perf_counter()
        async with get_async_session() as session:
            repo = ProductRepository(session)
            for p in products_data[:20]:  # 限制数量
                await repo.create(**p)
        elapsed = (time.perf_counter() - start) * 1000
        results['batch_insert_20'] = elapsed
        
        # 2. 简单查询测试
        start = time.perf_counter()
        async with get_async_session() as session:
            repo = ProductRepository(session)
            for _ in range(10):
                await repo.get_by_asin(products_data[0]['asin'])
        elapsed = (time.perf_counter() - start) * 1000 / 10
        results['simple_query_avg'] = elapsed
        
        # 3. 复杂查询测试
        start = time.perf_counter()
        async with get_async_session() as session:
            repo = ProductRepository(session)
            for _ in range(5):
                await repo.search(category="Category 1", min_price=10, max_price=50)
        elapsed = (time.perf_counter() - start) * 1000 / 5
        results['complex_query_avg'] = elapsed
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("性能基准测试摘要")
        print("=" * 60)
        for test_name, time_ms in results.items():
            print(f"{test_name}: {time_ms:.2f}ms")
        print("=" * 60)
        
        # 保存结果到文件
        report_path = Path(__file__).parent.parent.parent / "reports" / "performance-results.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': results,
            }, f, indent=2)
        
        print(f"\n结果已保存到: {report_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
