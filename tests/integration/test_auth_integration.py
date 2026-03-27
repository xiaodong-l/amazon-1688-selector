"""
认证集成测试

测试完整的认证流程和认证 + 限流集成
"""
import pytest
import time
from datetime import timedelta
from src.auth.jwt import create_access_token, verify_token, blacklist_token, is_token_blacklisted
from src.auth.permissions import PermissionManager
from src.utils.rate_limiter_redis import MemoryRateLimiter
from src.monitoring.request_tracing import start_trace, end_trace, get_tracer
from src.monitoring.error_tracking import track_error, get_error_tracker


class TestAuthIntegration:
    """认证集成测试"""
    
    @pytest.fixture
    def permission_manager(self):
        """创建权限管理器"""
        return PermissionManager()
    
    @pytest.fixture
    def rate_limiter(self):
        """创建限流器 (使用内存模式)"""
        return MemoryRateLimiter()
    
    def test_complete_auth_flow(self, permission_manager):
        """测试完整认证流程：登录 -> 生成令牌 -> 验证 -> 登出"""
        # 1. 模拟用户登录并生成令牌
        user_id = "user_123"
        user_info = {
            "user_id": user_id,
            "username": "testuser",
            "role": "admin"
        }
        
        access_token = create_access_token(
            data={
                "user_id": user_info["user_id"],
                "username": user_info["username"],
                "role": user_info["role"]
            }
        )
        
        assert access_token is not None
        assert len(access_token) > 0
        
        # 2. 验证令牌有效性
        payload = verify_token(access_token)
        assert payload is not None
        assert payload["user_id"] == user_info["user_id"]
        assert payload["username"] == user_info["username"]
        
        # 3. 为用户分配角色
        permission_manager.assign_role(user_id, "admin")
        
        # 4. 检查权限 - admin 应该有 api:write 权限
        has_permission = permission_manager.check_permission(
            user={"id": user_id},
            required="api:write"
        )
        assert has_permission is True
        
        # 5. 模拟登出 - 将令牌加入黑名单
        blacklist_token(access_token)
        
        # 6. 验证令牌已被吊销
        is_blacklisted = is_token_blacklisted(access_token)
        assert is_blacklisted is True
    
    def test_auth_with_rate_limiting(self, rate_limiter):
        """测试认证 + 限流集成"""
        user_id = "user_456"
        user_info = {
            "user_id": user_id,
            "username": "ratelimituser",
            "role": "user"
        }
        
        # 生成令牌
        access_token = create_access_token(
            data={
                "user_id": user_info["user_id"],
                "username": user_info["username"],
                "role": user_info["role"]
            }
        )
        
        # 验证令牌
        payload = verify_token(access_token)
        assert payload is not None
        
        # 模拟多次请求，测试限流
        allowed_count = 0
        denied_count = 0
        client_id = f"client_{user_id}"
        
        for i in range(15):
            # 模拟 API 请求 (limit=10, period=60)
            is_allowed = rate_limiter.is_allowed(client_id, limit=10, period=60)
            
            if is_allowed:
                allowed_count += 1
            else:
                denied_count += 1
        
        # 前 10 个请求应该被允许，后 5 个被拒绝
        assert allowed_count == 10
        assert denied_count == 5
    
    def test_role_based_access_control(self, permission_manager):
        """测试基于角色的访问控制"""
        # 设置不同角色的用户
        permission_manager.assign_role("admin_1", "admin")
        permission_manager.assign_role("user_1", "user")
        permission_manager.assign_role("readonly_1", "readonly")
        
        # 测试 admin 角色 - 应该有 api 相关权限
        assert permission_manager.check_permission({"id": "admin_1"}, "api:write") is True
        assert permission_manager.check_permission({"id": "admin_1"}, "api:read") is True
        assert permission_manager.check_permission({"id": "admin_1"}, "data:write") is True
        
        # 测试 user 角色
        assert permission_manager.check_permission({"id": "user_1"}, "api:read") is True
        assert permission_manager.check_permission({"id": "user_1"}, "data:read") is True
        
        # 测试 readonly 角色 - 只有读权限
        assert permission_manager.check_permission({"id": "readonly_1"}, "api:read") is True
        assert permission_manager.check_permission({"id": "readonly_1"}, "data:read") is True
        # readonly 不应该有写权限
        assert permission_manager.check_permission({"id": "readonly_1"}, "api:write") is False
    
    def test_token_expiration(self):
        """测试令牌过期"""
        user_info = {
            "user_id": "user_789",
            "username": "expiryuser",
            "role": "user"
        }
        
        # 生成短期令牌 (1 秒)
        access_token = create_access_token(
            data={
                "user_id": user_info["user_id"],
                "username": user_info["username"],
                "role": user_info["role"]
            },
            expires_delta=timedelta(seconds=1)
        )
        
        # 立即验证应该成功
        payload = verify_token(access_token)
        assert payload is not None
        
        # 等待过期
        time.sleep(2)
        
        # 验证应该失败 (抛出异常)
        with pytest.raises(Exception):
            verify_token(access_token)


class TestMonitoringIntegration:
    """监控集成测试"""
    
    def test_request_tracing_with_auth(self):
        """测试请求追踪与认证集成"""
        # 开始追踪请求
        trace_id = start_trace(endpoint="/api/products")
        
        assert trace_id is not None
        
        # 模拟业务逻辑
        time.sleep(0.01)
        
        # 完成请求
        end_trace(trace_id)
        
        # 获取追踪统计
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
            raise ValueError("Test validation error")
        except Exception as e:
            error_msg = str(e)
            # 使用 track_error 函数记录
            track_error(e, context={"endpoint": "/api/error", "user_id": "user_error"})
        
        # 完成请求 (带错误状态)
        end_trace(trace_id, error=error_msg)
        
        # 验证错误记录
        tracker = get_error_tracker()
        stats = tracker.get_stats()
        assert stats["total_errors"] >= 1 or stats["errors_24h"] >= 1
    
    def test_slow_query_detection(self):
        """测试慢查询检测"""
        # 开始一个慢请求
        trace_id = start_trace(endpoint="/api/slow-query")
        
        # 模拟慢查询
        time.sleep(0.5)
        
        # 完成请求
        end_trace(trace_id)
        
        # 获取统计
        tracer = get_tracer()
        stats = tracer.get_stats()
        # 应该记录了响应时间
        assert stats["completed_traces"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
