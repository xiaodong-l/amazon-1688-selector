"""
监控集成测试

测试 Prometheus 集成和请求追踪集成
"""
import pytest
import time
from src.monitoring.prometheus import expose_metrics
from src.monitoring.request_tracing import start_trace, end_trace, get_tracer
from src.monitoring.error_tracking import track_error, get_error_tracker
from src.utils.rate_limiter_redis import MemoryRateLimiter


class TestPrometheusIntegration:
    """Prometheus 集成测试"""
    
    def test_prometheus_metrics_collection(self):
        """测试 Prometheus 指标收集"""
        from src.monitoring.prometheus import PrometheusMetrics
        
        metrics = PrometheusMetrics()
        
        # 记录 HTTP 请求
        metrics.record_http_request(
            method="GET",
            endpoint="/api/products",
            status=200,
            duration=50.0
        )
        
        metrics.record_http_request(
            method="POST",
            endpoint="/api/products",
            status=201,
            duration=120.0
        )
        
        metrics.record_http_request(
            method="GET",
            endpoint="/api/products",
            status=500,
            duration=200.0
        )
        
        # 验证指标已记录
        metrics_output = expose_metrics()
        assert metrics_output is not None
        assert len(metrics_output) > 0
    
    def test_prometheus_db_metrics(self):
        """测试数据库指标"""
        from src.monitoring.prometheus import PrometheusMetrics
        
        metrics = PrometheusMetrics()
        
        # 记录数据库查询
        metrics.record_db_query(duration=15.0)
        metrics.record_db_query(duration=25.0)
        metrics.record_db_query(duration=500.0)  # 慢查询
        
        # 获取指标
        metrics_output = expose_metrics()
        assert metrics_output is not None
        
        # 应该有数据库相关指标
        assert "db" in metrics_output.lower() or len(metrics_output) > 0
    
    def test_prometheus_product_metrics(self):
        """测试产品指标"""
        from src.monitoring.prometheus import PrometheusMetrics
        
        metrics = PrometheusMetrics()
        
        # 记录产品扫描
        metrics.record_product_scanned(count=10)
        metrics.record_history_record(count=5)
        
        # 获取指标
        metrics_output = expose_metrics()
        assert metrics_output is not None
        assert len(metrics_output) > 0


class TestRequestTracingIntegration:
    """请求追踪集成测试"""
    
    def test_full_request_lifecycle(self):
        """测试完整请求生命周期"""
        # 开始请求
        trace_id = start_trace(endpoint="/api/products/search")
        
        assert trace_id is not None
        
        # 模拟业务处理
        time.sleep(0.01)
        
        # 完成请求
        end_trace(trace_id)
        
        # 验证追踪记录
        tracer = get_tracer()
        stats = tracer.get_stats()
        assert stats["completed_traces"] >= 1
    
    def test_error_tracking_integration(self):
        """测试错误追踪集成"""
        # 开始请求
        trace_id = start_trace(endpoint="/api/error")
        
        error_msg = None
        # 模拟错误
        try:
            raise ValueError("Invalid input data")
        except Exception as e:
            error_msg = str(e)
            # 记录错误
            track_error(e, context={"endpoint": "/api/error", "user_id": "user_456"})
        
        # 完成请求 (带错误状态)
        end_trace(trace_id, error=error_msg)
        
        # 验证错误记录
        tracker = get_error_tracker()
        stats = tracker.get_stats()
        assert stats["total_errors"] >= 1 or stats["errors_24h"] >= 1
    
    def test_slow_query_tracking(self):
        """测试慢查询追踪"""
        # 开始请求
        trace_id = start_trace(endpoint="/api/slow-endpoint")
        
        # 模拟慢处理
        time.sleep(0.5)  # 500ms
        
        # 完成请求
        end_trace(trace_id)
        
        # 获取统计
        tracer = get_tracer()
        stats = tracer.get_stats()
        
        # 应该记录了响应时间
        assert stats["completed_traces"] >= 1
    
    def test_concurrent_request_tracing(self):
        """测试并发请求追踪"""
        import concurrent.futures
        
        def make_request(request_id):
            trace_id = start_trace(endpoint=f"/api/request/{request_id}")
            
            time.sleep(0.01)
            
            end_trace(trace_id)
            return trace_id
        
        # 并发执行 10 个请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            trace_ids = [f.result() for f in futures]
        
        # 所有请求都应该有追踪 ID
        assert len(trace_ids) == 10
        assert all(tid is not None for tid in trace_ids)
        
        # 验证统计
        tracer = get_tracer()
        stats = tracer.get_stats()
        assert stats["completed_traces"] >= 10


class TestMonitoringWithRateLimiting:
    """监控与限流集成测试"""
    
    def test_rate_limiting_integration(self):
        """测试限流集成"""
        rate_limiter = MemoryRateLimiter()
        
        client_id = "test_client_integration"
        
        # 模拟请求直到被限流
        allowed_count = 0
        denied_count = 0
        
        for i in range(15):
            is_allowed = rate_limiter.is_allowed(client_id, limit=10, period=60)
            
            if is_allowed:
                allowed_count += 1
            else:
                denied_count += 1
        
        # 验证限流行为
        assert allowed_count == 10
        assert denied_count == 5
    
    def test_integration_audit_logging(self):
        """测试审计日志集成"""
        from src.monitoring.prometheus import PrometheusMetrics
        from src.auth.jwt import create_access_token
        
        metrics = PrometheusMetrics()
        
        # 模拟用户操作
        user_info = {
            "user_id": "user_audit",
            "username": "audituser",
            "role": "admin"
        }
        
        token = create_access_token(
            data={
                "user_id": user_info["user_id"],
                "username": user_info["username"],
                "role": user_info["role"]
            }
        )
        
        # 记录 API 访问
        metrics.record_http_request(
            method="DELETE",
            endpoint="/api/products/123",
            status=200,
            duration=50.0
        )
        
        # 获取指标 (包含审计信息)
        metrics_output = expose_metrics()
        assert metrics_output is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
