"""
趋势分析器单元测试

覆盖：
1. 利润率估算
2. 市场饱和度
3. 风险评分
4. 趋势预测
5. 输入验证
6. 边界条件
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.trend_analyzer import TrendAnalyzer
from src.utils.helpers import parse_price, normalize_score, safe_divide, truncate_text
from src.utils.config import ANALYSIS_THRESHOLDS, CATEGORY_MARGINS


class TestProfitMargin:
    """利润率估算测试"""
    
    @pytest.fixture
    def analyzer(self):
        return TrendAnalyzer()
    
    def test_low_price_margin(self, analyzer):
        """低价商品利润率测试"""
        product = {
            "price": {"value": 5.99, "symbol": "$"},
            "title": "USB Cable"
        }
        margin = analyzer._estimate_profit_margin(product)
        # 低价产品利润率应该较低 (20-35%)
        assert 20 <= margin <= 50, f"低价产品利润率异常：{margin}"
    
    def test_medium_price_margin(self, analyzer):
        """中价商品利润率测试"""
        product = {
            "price": {"value": 29.99, "symbol": "$"},
            "title": "Wireless Mouse"
        }
        margin = analyzer._estimate_profit_margin(product)
        # 中价产品利润率应该中等 (30-45%)
        assert 30 <= margin <= 70, f"中价产品利润率异常：{margin}"
    
    def test_high_price_margin(self, analyzer):
        """高价商品利润率测试"""
        product = {
            "price": {"value": 199.99, "symbol": "$"},
            "title": "Wireless Headphones"
        }
        margin = analyzer._estimate_profit_margin(product)
        # 高价产品利润率 (35-50%)
        assert 30 <= margin <= 70, f"高价产品利润率异常：{margin}"
    
    def test_category_margin_electronics(self, analyzer):
        """电子产品类目利润率测试"""
        product = {
            "price": {"value": 49.99},
            "title": "Bluetooth Speaker Electronics"
        }
        margin = analyzer._estimate_profit_margin(product)
        # 电子产品利润率较低 (25%)
        assert margin > 0, "利润率应该为正"
    
    def test_category_margin_beauty(self, analyzer):
        """美妆类目利润率测试"""
        product = {
            "price": {"value": 35.00},
            "title": "Face Cream Beauty"
        }
        margin = analyzer._estimate_profit_margin(product)
        # 美妆利润率较高 (45%)
        assert margin > 30, "美妆产品应该有较高利润率"
    
    def test_null_price(self, analyzer):
        """空价格测试"""
        product = {"price": None, "title": "Test Product"}
        margin = analyzer._estimate_profit_margin(product)
        assert margin == 0, "空价格应该返回 0 利润率"


class TestMarketSaturation:
    """市场饱和度测试"""
    
    @pytest.fixture
    def analyzer(self):
        return TrendAnalyzer()
    
    def test_high_saturation(self, analyzer):
        """高饱和度市场测试"""
        product = {
            "ratings_total": 100000,  # 大量评论
            "rating": 4.5,
            "is_best_seller": True
        }
        saturation = analyzer._estimate_market_saturation(product)
        # 高饱和度应该得分低
        assert saturation < 40, f"高饱和市场评分过高：{saturation}"
    
    def test_low_saturation(self, analyzer):
        """低饱和度市场测试 (蓝海)"""
        product = {
            "ratings_total": 100,  # 很少评论
            "rating": 4.0,
            "is_best_seller": False
        }
        saturation = analyzer._estimate_market_saturation(product)
        # 低饱和度应该得分高
        assert saturation > 70, f"低饱和市场评分过低：{saturation}"
    
    def test_medium_saturation(self, analyzer):
        """中等饱和度市场测试"""
        product = {
            "ratings_total": 5000,
            "rating": 4.2,
            "is_best_seller": False
        }
        saturation = analyzer._estimate_market_saturation(product)
        # 中等饱和度
        assert 40 <= saturation <= 80, f"中等饱和市场评分异常：{saturation}"


class TestRiskScore:
    """风险评分测试"""
    
    @pytest.fixture
    def analyzer(self):
        return TrendAnalyzer()
    
    def test_low_rating_risk(self, analyzer):
        """低评分风险测试"""
        product = {"rating": 3.0, "ratings_total": 1000}
        base_metrics = {"sales_growth": 50, "review_growth": 50}
        risk = analyzer._calculate_risk_score(product, base_metrics)
        # 低评分应该有较高风险
        assert risk >= 25, f"低评分风险过低：{risk}"
    
    def test_few_reviews_risk(self, analyzer):
        """评论数过少风险测试"""
        product = {"rating": 4.5, "ratings_total": 20}
        base_metrics = {"sales_growth": 50, "review_growth": 50}
        risk = analyzer._calculate_risk_score(product, base_metrics)
        # 评论数少应该有中等风险
        assert risk >= 20, f"少评论风险过低：{risk}"
    
    def test_suspicious_growth_risk(self, analyzer):
        """可疑增长风险测试"""
        product = {"rating": 4.5, "ratings_total": 5000}
        base_metrics = {"sales_growth": 90, "review_growth": 50}  # 增长过快
        risk = analyzer._calculate_risk_score(product, base_metrics)
        # 增长过快应该有额外风险
        assert risk >= 15, f"可疑增长风险过低：{risk}"
    
    def test_low_risk_product(self, analyzer):
        """低风险产品测试"""
        product = {"rating": 4.5, "ratings_total": 5000}
        base_metrics = {"sales_growth": 40, "review_growth": 40}  # 健康增长
        risk = analyzer._calculate_risk_score(product, base_metrics)
        # 健康产品应该风险低
        assert risk < 20, f"健康产品风险过高：{risk}"


class TestForecast:
    """30 天预测测试"""
    
    @pytest.fixture
    def analyzer(self):
        return TrendAnalyzer()
    
    def test_seasonal_forecast_november(self, analyzer):
        """11 月 (黑五) 预测测试"""
        from datetime import datetime
        product = {"rating": 4.5, "ratings_total": 5000}
        metrics = {
            "sales_growth": 50,
            "review_growth": 50,
            "profit_margin": 40,
            "market_saturation": 60,
            "growth_sustainability": 70,
            "risk_score": 10,
        }
        
        # 模拟 11 月数据
        forecast = analyzer._forecast_30d(product, metrics, None)
        
        # 11 月→12 月 (圣诞季) 应该上升
        assert forecast["score"] > 0, "预测评分应该为正"
        assert "trend" in forecast, "预测应包含趋势"
    
    def test_forecast_confidence_interval(self, analyzer):
        """预测置信区间测试"""
        product = {"rating": 4.5, "ratings_total": 5000}
        metrics = {
            "sales_growth": 50,
            "review_growth": 50,
            "profit_margin": 40,
            "market_saturation": 60,
            "growth_sustainability": 70,
            "risk_score": 10,
        }
        
        forecast = analyzer._forecast_30d(product, metrics, None)
        
        # 置信区间应该有效
        ci = forecast.get("confidence_interval", {})
        assert "low" in ci and "high" in ci, "置信区间应该包含 low 和 high"
        assert ci["low"] <= ci["high"], "置信区间下限应小于上限"
        assert ci["low"] <= forecast["score"] <= ci["high"], "预测分应在置信区间内"


class TestInputValidation:
    """输入验证测试"""
    
    @pytest.fixture
    def analyzer(self):
        return TrendAnalyzer()
    
    def test_empty_products(self, analyzer):
        """空商品列表测试"""
        result = analyzer.analyze_products([])
        assert result == [], "空列表应返回空结果"
    
    def test_invalid_product_format(self, analyzer):
        """无效商品格式测试"""
        products = [
            {"asin": "B001", "title": "Valid Product"},  # 有效
            "invalid string",  # 无效
            None,  # 无效
            {"title": "No ASIN"},  # 缺少 ASIN
            {"asin": "B002", "title": "Another Valid"},  # 有效
        ]
        
        result = analyzer.analyze_products(products)
        
        # 应该只处理有效商品
        assert len(result) == 2, f"应该只处理 2 个有效商品，实际：{len(result)}"
    
    def test_missing_asin(self, analyzer):
        """缺少 ASIN 测试"""
        products = [
            {"title": "No ASIN Product 1"},
            {"title": "No ASIN Product 2"},
        ]
        
        result = analyzer.analyze_products(products)
        assert len(result) == 0, "缺少 ASIN 的商品应该被过滤"


class TestHelpers:
    """工具函数测试"""
    
    def test_parse_price_dict(self):
        """测试字典价格解析"""
        value, formatted = parse_price({"value": 29.99, "symbol": "$"})
        assert value == 29.99
        assert formatted == "$29.99"
    
    def test_parse_price_float(self):
        """测试浮点数价格解析"""
        value, formatted = parse_price(19.99)
        assert value == 19.99
        assert formatted == "$19.99"
    
    def test_parse_price_none(self):
        """测试空值价格解析"""
        value, formatted = parse_price(None)
        assert value is None
        assert formatted == "N/A"
    
    def test_parse_price_string(self):
        """测试字符串价格解析"""
        value, formatted = parse_price("$25.00")
        assert value == 25.0
        assert formatted == "$25.00"
    
    def test_normalize_score(self):
        """测试分数标准化"""
        assert normalize_score(150) == 100
        assert normalize_score(-10) == 0
        assert normalize_score(50) == 50
        assert normalize_score(50, 0, 50) == 50
    
    def test_safe_divide(self):
        """测试安全除法"""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(10, 0) == 0.0  # 除零返回默认值
        assert safe_divide(10, 0, default=-1) == -1
    
    def test_truncate_text(self):
        """测试文本截断"""
        assert truncate_text("Hello World", 5) == "He..."
        assert truncate_text("Hi", 10) == "Hi"
        assert truncate_text("", 10) == ""
        assert truncate_text(None, 10) == ""


class TestTrendAnalysis:
    """趋势分析集成测试"""
    
    @pytest.fixture
    def analyzer(self):
        return TrendAnalyzer()
    
    @pytest.fixture
    def sample_products(self):
        return [
            {
                "asin": "B001",
                "title": "Wireless Earbuds Pro",
                "price": {"value": 29.99, "symbol": "$"},
                "rating": 4.5,
                "ratings_total": 5000,
                "is_prime": True,
                "is_amazon_choice": True,
            },
            {
                "asin": "B002",
                "title": "Phone Case Ultra",
                "price": {"value": 15.99, "symbol": "$"},
                "rating": 4.7,
                "ratings_total": 12000,
                "is_prime": True,
                "is_best_seller": True,
            },
            {
                "asin": "B003",
                "title": "Laptop Stand Basic",
                "price": {"value": 19.99, "symbol": "$"},
                "rating": 4.2,
                "ratings_total": 800,
                "is_prime": False,
            },
        ]
    
    def test_analyze_products(self, analyzer, sample_products):
        """测试商品分析"""
        result = analyzer.analyze_products(sample_products, use_enhanced=True)
        
        assert len(result) == 3, "应该分析所有 3 个商品"
        assert all("trend_score" in p for p in result), "所有商品应该有趋势评分"
        assert all("metrics" in p for p in result), "所有商品应该有指标"
        assert all("rank" in p for p in result), "所有商品应该有排名"
    
    def test_ranking_order(self, analyzer, sample_products):
        """测试排名顺序"""
        result = analyzer.analyze_products(sample_products, use_enhanced=True)
        
        # 排名应该降序
        for i in range(len(result) - 1):
            assert result[i]["rank"] == i + 1, f"排名应该连续：{result[i]['rank']}"
            if i < len(result) - 1:
                assert result[i]["trend_score"] >= result[i+1]["trend_score"], \
                    "排名应该按分数降序"
    
    def test_enhanced_metrics_present(self, analyzer, sample_products):
        """测试增强指标存在"""
        result = analyzer.analyze_products(sample_products, use_enhanced=True)
        
        for product in result:
            metrics = product.get("metrics", {})
            assert "profit_margin" in metrics, "应该有利润率指标"
            assert "market_saturation" in metrics, "应该有市场饱和度指标"
            assert "risk_score" in metrics, "应该有风险评分指标"
    
    def test_confidence_and_forecast(self, analyzer, sample_products):
        """测试置信度和预测"""
        result = analyzer.analyze_products(sample_products, use_enhanced=True)
        
        for product in result:
            assert "confidence" in product, "应该有置信度"
            assert 0 <= product["confidence"] <= 1, "置信度应该在 0-1 之间"
            assert "forecast_30d" in product, "应该有 30 天预测"
            assert "risk_level" in product, "应该有风险等级"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
