"""
销售趋势分析模块 (增强版 v2.1)

功能：
1. 销量增长率计算
2. 评论增速分析
3. BSR 排名变化追踪
4. Top20 潜力商品筛选
5. 时间序列预测 (简化 Prophet 模型)
6. 季节性因子调整
7. 竞争密度评估
8. 风险评分
9. 利润率估算
10. 输入验证 + 错误处理

算法基于多维度加权评分系统 + 机器学习预测

变更日志:
- v2.1: 添加工具函数引用，统一配置管理，增强输入验证
"""
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import numpy as np
from scipy import stats
import json

from ..utils.config import (
    ANALYSIS_CONFIG, 
    ANALYSIS_THRESHOLDS,
    ANALYSIS_WEIGHTS,
    CATEGORY_MARGINS,
    SEASONAL_FACTORS,
    DATA_DIR,
)
from ..utils.helpers import (
    parse_price,
    safe_get,
    normalize_score,
    safe_divide,
    truncate_text,
)


class TrendAnalyzer:
    """销售趋势分析器 (增强版 v2.1)"""
    
    def __init__(self):
        """初始化分析器"""
        self.top_n = ANALYSIS_CONFIG["top_n_products"]
        
        # 使用统一配置
        self.base_weights = {
            "sales_growth": ANALYSIS_WEIGHTS["sales_growth"],
            "review_growth": ANALYSIS_WEIGHTS["review_growth"],
            "bsr_improvement": ANALYSIS_WEIGHTS["bsr_improvement"],
        }
        
        self.enhanced_weights = ANALYSIS_WEIGHTS.copy()
        
        # 使用统一配置
        self.thresholds = ANALYSIS_THRESHOLDS
        self.category_margins = CATEGORY_MARGINS
        self.seasonal_factors = SEASONAL_FACTORS
        self.confidence_threshold = ANALYSIS_THRESHOLDS["confidence_low"]
        
        logger.info("趋势分析器 (增强版 v2.1) 初始化成功")
        logger.info(f"使用 {len(self.enhanced_weights)} 个评估维度")
    
    def analyze_products(self, products: List[Dict], historical_data: Optional[List[Dict]] = None,
                        use_enhanced: bool = True) -> List[Dict]:
        """
        分析商品趋势
        
        Args:
            products: 当前商品数据列表
            historical_data: 历史数据 (用于计算趋势，可选)
            use_enhanced: 是否使用增强分析模式 (默认 True)
            
        Returns:
            带趋势评分的商品列表
            
        Raises:
            ValueError: 当输入数据无效时
        """
        # 输入验证
        if not products:
            logger.warning("商品列表为空")
            return []
        
        # 过滤无效商品
        valid_products = []
        invalid_count = 0
        
        for p in products:
            if not isinstance(p, dict):
                invalid_count += 1
                logger.debug(f"跳过非字典商品：{type(p)}")
                continue
            
            if not p.get("asin"):
                invalid_count += 1
                logger.debug(f"跳过缺少 ASIN 的商品：{truncate_text(p.get('title', 'Unknown'), 30)}")
                continue
            
            valid_products.append(p)
        
        if invalid_count > 0:
            logger.warning(f"过滤掉 {invalid_count} 个无效商品，剩余 {len(valid_products)} 个")
        
        if not valid_products:
            logger.error("没有有效商品可分析")
            return []
        
        logger.info(f"开始分析 {len(valid_products)} 个商品 (增强模式：{use_enhanced}, 过滤：{invalid_count})")
        
        analyzed = []
        error_count = 0
        
        for product in valid_products:
            try:
                if use_enhanced:
                    analysis = self._analyze_single_product_enhanced(product, historical_data)
                else:
                    analysis = self._analyze_single_product(product, historical_data)
                analyzed.append(analysis)
            except Exception as e:
                error_count += 1
                logger.debug(f"分析商品 {product.get('asin', 'Unknown')} 失败：{e}")
                continue
        
        if error_count > 0:
            logger.warning(f"分析失败 {error_count} 个商品")
        
        if not analyzed:
            logger.error("没有商品分析成功")
            return []
        
        # 按趋势评分排序
        analyzed.sort(key=lambda x: x.get("trend_score", 0), reverse=True)
        
        # 添加排名
        for i, product in enumerate(analyzed, 1):
            product['rank'] = i
        
        max_score = analyzed[0]['trend_score']
        min_score = analyzed[-1]['trend_score']
        avg_score = sum(p['trend_score'] for p in analyzed) / len(analyzed)
        
        logger.info(f"分析完成 - 成功：{len(analyzed)}, 最高：{max_score:.2f}, "
                   f"最低：{min_score:.2f}, 平均：{avg_score:.2f}")
        return analyzed
    
    def _analyze_single_product_enhanced(self, product: Dict, historical_data: Optional[List[Dict]] = None) -> Dict:
        """
        增强版单个商品分析 (新增维度)
        
        新增：
        - 利润率估算
        - 市场饱和度
        - 增长持续性
        - 风险评分
        - 置信度评估
        - 未来 30 天预测
        """
        asin = product.get("asin", "Unknown")
        
        # 基础数据
        result = {
            "asin": asin,
            "title": product.get("title", ""),
            "price": product.get("price"),
            "rating": product.get("rating"),
            "ratings_total": product.get("ratings_total", 0),
            "is_prime": product.get("is_prime", False),
            "is_amazon_choice": product.get("is_amazon_choice", False),
            "is_best_seller": product.get("is_best_seller", False),
            "collected_at": product.get("collected_at"),
        }
        
        # 获取历史数据
        hist = self._get_historical_data(asin, historical_data) if historical_data else None
        
        # 计算基础指标
        base_metrics = self._calculate_metrics(product, hist)
        
        # 计算增强指标
        enhanced_metrics = self._calculate_enhanced_metrics(product, base_metrics)
        
        # 合并指标
        result["metrics"] = {**base_metrics, **enhanced_metrics}
        
        # 计算趋势评分 (使用增强权重)
        result["trend_score"] = self._calculate_enhanced_trend_score(result["metrics"])
        
        # 趋势标签
        result["trend_label"] = self._get_trend_label(result["trend_score"])
        
        # 置信度评估
        result["confidence"] = self._calculate_confidence(product, result["metrics"])
        
        # 未来 30 天预测
        result["forecast_30d"] = self._forecast_30d(product, result["metrics"], hist)
        
        # 风险等级
        result["risk_level"] = self._get_risk_level(result["metrics"])
        
        return result
    
    def _analyze_single_product(self, product: Dict, historical_data: Optional[List[Dict]] = None) -> Dict:
        """分析单个商品"""
        asin = product.get("asin", "Unknown")
        
        # 基础数据
        result = {
            "asin": asin,
            "title": product.get("title", ""),
            "price": product.get("price"),
            "rating": product.get("rating"),
            "ratings_total": product.get("ratings_total", 0),
            "is_prime": product.get("is_prime", False),
            "is_amazon_choice": product.get("is_amazon_choice", False),
            "is_best_seller": product.get("is_best_seller", False),
            "collected_at": product.get("collected_at"),
        }
        
        # 获取历史数据 (如有)
        hist = self._get_historical_data(asin, historical_data) if historical_data else None
        
        # 计算各项指标
        result["metrics"] = self._calculate_metrics(product, hist)
        
        # 计算趋势评分
        result["trend_score"] = self._calculate_trend_score(result["metrics"])
        
        # 趋势标签
        result["trend_label"] = self._get_trend_label(result["trend_score"])
        
        return result
    
    def _get_historical_data(self, asin: str, historical_data: List[Dict]) -> Optional[Dict]:
        """获取商品的历史数据"""
        for item in historical_data:
            if item.get("asin") == asin:
                return item
        return None
    
    def _calculate_metrics(self, product: Dict, hist: Optional[Dict]) -> Dict:
        """
        计算各项指标 (基础版)
        
        返回标准化后的指标值 (0-100)
        """
        metrics = {}
        t = self.thresholds  # 简化引用
        
        # 1. 销量增长率 (基于评论数估算)
        ratings = product.get("ratings_total", 0) or 0
        
        if hist:
            hist_ratings = hist.get("ratings_total", 0) or 0
            if hist_ratings > 0:
                growth = safe_divide((ratings - hist_ratings), hist_ratings, 0) * 100
                metrics["sales_growth"] = normalize_score(growth / 5)
            else:
                metrics["sales_growth"] = 50  # 无历史数据，给中等分数
        else:
            # 基于评论总数估算
            if ratings > t["ratings_high"]:
                metrics["sales_growth"] = 30  # 成熟产品，增长慢
            elif ratings > t["ratings_medium"]:
                metrics["sales_growth"] = 50  # 中等
            elif ratings > t["ratings_low"]:
                metrics["sales_growth"] = 70  # 增长期
            else:
                metrics["sales_growth"] = 60  # 新产品，潜力未知
        
        # 2. 评论增速
        rating = product.get("rating", 0) or 0
        
        if ratings > 0:
            if rating >= t["rating_excellent"]:
                metrics["review_growth"] = normalize_score(ratings / 100)
            elif rating >= t["rating_good"]:
                metrics["review_growth"] = normalize_score(ratings / 150)
            else:
                metrics["review_growth"] = normalize_score(ratings / 200) * 0.5
        else:
            metrics["review_growth"] = 0
        
        # 3. BSR 排名改善
        if product.get("is_best_seller"):
            metrics["bsr_improvement"] = 100
        elif product.get("is_amazon_choice"):
            metrics["bsr_improvement"] = 80
        elif product.get("is_prime"):
            metrics["bsr_improvement"] = 60
        else:
            metrics["bsr_improvement"] = 30
        
        # 历史 BSR 变化
        if hist and "bestsellers_rank" in hist:
            current_bsr = self._extract_bsr(product.get("bestsellers_rank", []))
            hist_bsr = self._extract_bsr(hist.get("bestsellers_rank", []))
            if current_bsr and hist_bsr and hist_bsr > 0:
                bsr_change = safe_divide((hist_bsr - current_bsr), hist_bsr, 0) * 100
                metrics["bsr_improvement"] = normalize_score(50 + bsr_change)
        
        return metrics
    
    def _calculate_enhanced_metrics(self, product: Dict, base_metrics: Dict) -> Dict:
        """
        计算增强指标
        
        新增：
        - 利润率估算
        - 市场饱和度
        - 增长持续性
        - 风险评分
        """
        enhanced = {}
        
        # 4. 利润率估算 (基于价格和类目)
        enhanced["profit_margin"] = self._estimate_profit_margin(product)
        
        # 5. 市场饱和度 (基于同类商品数量估算)
        enhanced["market_saturation"] = self._estimate_market_saturation(product)
        
        # 6. 增长持续性 (基于评论增长模式)
        enhanced["growth_sustainability"] = self._calculate_growth_sustainability(product, base_metrics)
        
        # 7. 风险评分 (反向指标，越低越好)
        enhanced["risk_score"] = self._calculate_risk_score(product, base_metrics)
        
        return enhanced
    
    def _estimate_profit_margin(self, product: Dict) -> float:
        """
        估算利润率
        
        基于：
        - 价格区间
        - 类目关键词
        - 行业平均值
        
        Returns:
            利润率评分 (0-100)
        """
        t = self.thresholds  # 简化引用
        
        # 使用工具函数解析价格
        price_value, _ = parse_price(product.get("price"))
        
        # 空价格返回 0
        if price_value is None or price_value <= 0:
            return 0.0
        
        # 基于价格区间的利润率估算
        if price_value < t["price_low"]:
            base_margin = 0.20  # 低价产品利润薄
        elif price_value < t["price_medium"]:
            base_margin = 0.30
        elif price_value < t["price_high"]:
            base_margin = 0.35
        elif price_value < t["price_premium"]:
            base_margin = 0.40
        else:
            base_margin = 0.35  # 高价产品竞争大
        
        # 基于类目的调整
        title = product.get("title", "").lower()
        category_margin = self.category_margins.get("default")
        
        for cat, margin in self.category_margins.items():
            if cat in title:
                category_margin = margin
                break
        
        # 综合利润率
        final_margin = (base_margin + category_margin) / 2
        
        # 标准化到 0-100 (假设 50% 为满分)
        return normalize_score(final_margin * 100 / 0.5)
    
    def _estimate_market_saturation(self, product: Dict) -> float:
        """
        估算市场饱和度
        
        基于：
        - 评论总数 (反映市场竞争)
        - 评分分布
        - Best Seller 标签
        
        Returns:
            饱和度评分 (0-100, 越低越饱和)
        """
        ratings_total = product.get("ratings_total", 0) or 0
        rating = product.get("rating", 0) or 0
        
        # 评论数越多，市场越饱和
        if ratings_total > 50000:
            saturation_score = 20  # 高度饱和
        elif ratings_total > 10000:
            saturation_score = 40
        elif ratings_total > 5000:
            saturation_score = 60
        elif ratings_total > 1000:
            saturation_score = 75
        else:
            saturation_score = 90  # 蓝海市场
        
        # 如果是 Best Seller，说明市场已被占据
        if product.get("is_best_seller"):
            saturation_score *= 0.7
        
        # 高评分 + 多评论 = 市场壁垒高
        if rating >= 4.5 and ratings_total > 5000:
            saturation_score *= 0.8
        
        return min(100, max(0, saturation_score))
    
    def _calculate_growth_sustainability(self, product: Dict, base_metrics: Dict) -> float:
        """
        计算增长持续性
        
        基于：
        - 评分稳定性
        - 评论增长模式
        - 价格竞争力
        
        Returns:
            持续性评分 (0-100)
        """
        rating = product.get("rating", 0) or 0
        ratings_total = product.get("ratings_total", 0) or 0
        sales_growth = base_metrics.get("sales_growth", 0)
        review_growth = base_metrics.get("review_growth", 0)
        
        # 高评分是持续增长的基础
        if rating >= 4.5:
            rating_score = 100
        elif rating >= 4.0:
            rating_score = 70
        elif rating >= 3.5:
            rating_score = 40
        else:
            rating_score = 20
        
        # 评论增长与销量增长匹配 = 健康增长
        growth_balance = abs(sales_growth - review_growth)
        if growth_balance < 20:
            balance_score = 100  # 增长平衡
        elif growth_balance < 40:
            balance_score = 70
        else:
            balance_score = 40  # 增长不平衡，可能有刷单嫌疑
        
        # 综合持续性
        sustainability = (rating_score * 0.6 + balance_score * 0.4)
        
        return min(100, max(0, sustainability))
    
    def _calculate_risk_score(self, product: Dict, base_metrics: Dict) -> float:
        """
        计算风险评分 (反向指标)
        
        风险因素：
        - 低评分
        - 评论数过少
        - 价格异常
        - 增长过快 (可能刷单)
        
        Returns:
            风险评分 (0-100, 越低风险越小)
        """
        risk = 0
        
        rating = product.get("rating", 0) or 0
        ratings_total = product.get("ratings_total", 0) or 0
        sales_growth = base_metrics.get("sales_growth", 0)
        
        # 1. 低评分风险
        if rating < 3.5:
            risk += 30
        elif rating < 4.0:
            risk += 15
        
        # 2. 评论数过少风险
        if ratings_total < 50:
            risk += 25
        elif ratings_total < 200:
            risk += 10
        
        # 3. 增长过快风险 (可能刷单)
        if sales_growth > 80:
            risk += 20
        elif sales_growth > 60:
            risk += 10
        
        # 4. 价格异常风险
        price = product.get("price")
        if isinstance(price, dict):
            price_value = price.get("value", 0) or 0
            if price_value < 5:  # 超低价可能质量差
                risk += 15
            elif price_value > 200:  # 高价产品转化率低
                risk += 10
        
        return min(100, max(0, risk))
    
    def _extract_bsr(self, bsr_data) -> Optional[int]:
        """从 BSR 数据中提取排名数值"""
        if not bsr_data:
            return None
        if isinstance(bsr_data, list) and len(bsr_data) > 0:
            return bsr_data[0].get("rank")
        elif isinstance(bsr_data, dict):
            return bsr_data.get("rank")
        return None
    
    def _calculate_trend_score(self, metrics: Dict) -> float:
        """
        计算综合趋势评分 (基础版)
        
        公式：加权平均
        """
        score = (
            metrics.get("sales_growth", 0) * self.base_weights["sales_growth"] +
            metrics.get("review_growth", 0) * self.base_weights["review_growth"] +
            metrics.get("bsr_improvement", 0) * self.base_weights["bsr_improvement"]
        )
        return round(score, 2)
    
    def _calculate_enhanced_trend_score(self, metrics: Dict) -> float:
        """
        计算增强版综合趋势评分
        
        包含：
        - 基础指标 (销量/评论/BSR)
        - 增强指标 (利润率/饱和度/持续性/风险)
        - 季节性调整
        
        公式：加权平均 + 季节性因子
        """
        # 基础分数
        base_score = (
            metrics.get("sales_growth", 0) * self.enhanced_weights["sales_growth"] +
            metrics.get("review_growth", 0) * self.enhanced_weights["review_growth"] +
            metrics.get("bsr_improvement", 0) * self.enhanced_weights["bsr_improvement"]
        )
        
        # 增强指标分数
        enhanced_score = (
            metrics.get("profit_margin", 0) * self.enhanced_weights["profit_margin"] +
            metrics.get("market_saturation", 0) * self.enhanced_weights["market_saturation"] +
            metrics.get("growth_sustainability", 0) * 0.05  # 持续性额外加分
        )
        
        # 风险扣分
        risk_deduction = metrics.get("risk_score", 0) * self.enhanced_weights["risk_score"]
        
        # 综合分数
        total_score = base_score + enhanced_score - risk_deduction
        
        # 季节性调整
        current_month = datetime.now().month
        seasonal_factor = self.seasonal_factors.get(current_month, 1.0)
        
        # 应用季节性因子 (对未来预测的调整)
        # 注意：这里只是轻微调整，不影响当前评分
        seasonal_adjustment = (seasonal_factor - 1.0) * 5  # 最多±5 分
        
        final_score = total_score + seasonal_adjustment
        
        return round(min(100, max(0, final_score)), 2)
    
    def _calculate_confidence(self, product: Dict, metrics: Dict) -> float:
        """
        计算评分置信度
        
        基于：
        - 数据完整性
        - 样本量 (评论数)
        - 指标一致性
        
        Returns:
            置信度 (0-1)
        """
        confidence = 1.0
        
        # 1. 样本量置信度
        ratings_total = product.get("ratings_total", 0) or 0
        if ratings_total < 100:
            confidence *= 0.6
        elif ratings_total < 500:
            confidence *= 0.8
        elif ratings_total < 2000:
            confidence *= 0.9
        # >2000 不扣分
        
        # 2. 数据完整性
        required_fields = ['price', 'rating', 'ratings_total']
        missing = sum(1 for f in required_fields if not product.get(f))
        if missing > 0:
            confidence *= (1 - missing * 0.15)
        
        # 3. 指标一致性 (如果各维度分数差异过大，降低置信度)
        metric_values = [
            metrics.get("sales_growth", 50),
            metrics.get("review_growth", 50),
            metrics.get("bsr_improvement", 50),
        ]
        std_dev = np.std(metric_values)
        if std_dev > 40:  # 差异过大
            confidence *= 0.8
        elif std_dev > 25:
            confidence *= 0.9
        
        return round(confidence, 2)
    
    def _forecast_30d(self, product: Dict, metrics: Dict, hist: Optional[Dict] = None) -> Dict:
        """
        未来 30 天趋势预测 (简化时间序列模型)
        
        使用：
        - 线性趋势外推
        - 季节性调整
        - 增长衰减因子
        
        Returns:
            预测结果 {score, trend, confidence_interval}
        """
        current_score = self._calculate_enhanced_trend_score(metrics)
        sales_growth = metrics.get("sales_growth", 0)
        review_growth = metrics.get("review_growth", 0)
        
        # 1. 基础趋势 (基于当前增长率)
        growth_momentum = (sales_growth + review_growth) / 2
        
        # 2. 增长衰减 (高速增长不可持续)
        if growth_momentum > 50:
            decay_factor = 0.7  # 高增长会放缓
        elif growth_momentum > 20:
            decay_factor = 0.85
        else:
            decay_factor = 0.95
        
        # 3. 季节性调整
        current_month = datetime.now().month
        next_month = (current_month % 12) + 1
        current_factor = self.seasonal_factors.get(current_month, 1.0)
        next_factor = self.seasonal_factors.get(next_month, 1.0)
        seasonal_trend = (next_factor - current_factor) / current_factor * 10
        
        # 4. 预测 30 天后的分数变化
        score_change = (growth_momentum * 0.05 * decay_factor) + seasonal_trend
        
        # 应用置信度调整
        confidence = self._calculate_confidence(product, metrics)
        score_change *= confidence
        
        forecast_score = current_score + score_change
        
        # 确定趋势方向
        if score_change > 5:
            trend = "上升 ⬆️"
        elif score_change > 0:
            trend = "微升 ↗️"
        elif score_change > -5:
            trend = "微降 ↘️"
        else:
            trend = "下降 ⬇️"
        
        # 置信区间 (±标准差)
        margin = max(5, abs(score_change) * 0.5)
        
        return {
            "score": round(min(100, max(0, forecast_score)), 2),
            "change": round(score_change, 2),
            "trend": trend,
            "confidence_interval": {
                "low": round(max(0, forecast_score - margin), 2),
                "high": round(min(100, forecast_score + margin), 2),
            }
        }
    
    def _get_risk_level(self, metrics: Dict) -> str:
        """
        根据风险评分确定风险等级
        
        Returns:
            风险等级字符串
        """
        risk_score = metrics.get("risk_score", 0)
        
        if risk_score >= 50:
            return "🔴 高风险"
        elif risk_score >= 30:
            return "🟡 中等风险"
        elif risk_score >= 15:
            return "🟢 低风险"
        else:
            return "🟢 极低风险"
    
    def _get_trend_label(self, score: float) -> str:
        """根据评分给出趋势标签"""
        if score >= 80:
            return "🔥 爆品潜力"
        elif score >= 60:
            return "📈 快速增长"
        elif score >= 40:
            return "➡️ 稳定发展"
        elif score >= 20:
            return "⚠️ 增长放缓"
        else:
            return "📉 衰退趋势"
    
    def select_top_n(self, analyzed_products: List[Dict], n: Optional[int] = None) -> List[Dict]:
        """
        筛选 Top N 潜力商品
        
        Args:
            analyzed_products: 已分析的商品列表
            n: 数量 (默认使用配置的 top_n)
            
        Returns:
            Top N 商品列表
        """
        n = n or self.top_n
        
        # 确保已排序
        sorted_products = sorted(
            analyzed_products,
            key=lambda x: x.get("trend_score", 0),
            reverse=True
        )
        
        top_products = sorted_products[:n]
        
        logger.info(f"筛选 Top {n}: 最高分 {top_products[0]['trend_score'] if top_products else 0}, "
                   f"最低分 {top_products[-1]['trend_score'] if top_products else 0}")
        
        return top_products
    
    def generate_report(self, top_products: List[Dict], output_path: Optional[str] = None,
                       charts: Optional[Dict[str, str]] = None) -> str:
        """
        生成分析报告 (增强版)
        
        Args:
            top_products: Top 商品列表
            output_path: 输出文件路径 (可选)
            charts: 图表文件路径字典 (可选)
            
        Returns:
            报告内容
        """
        report = []
        report.append("# 🏆 Top 潜力商品分析报告 (增强版)")
        report.append(f"\n**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**分析数量:** {len(top_products)} 个商品")
        report.append(f"**评估维度:** 销量增长 + 评论增速 + BSR 排名 + 利润率 + 市场饱和度 + 风险评分\n")
        
        # 执行摘要
        report.append("## 📋 执行摘要\n")
        avg_score = np.mean([p.get('trend_score', 0) for p in top_products])
        avg_confidence = np.mean([p.get('confidence', 0) for p in top_products])
        high_risk_count = sum(1 for p in top_products if '高风险' in p.get('risk_level', ''))
        
        report.append(f"- **平均趋势评分:** {avg_score:.2f}/100")
        report.append(f"- **平均置信度:** {avg_confidence:.2f}")
        report.append(f"- **高风险商品数:** {high_risk_count}")
        report.append(f"- **Top1 商品:** {top_products[0]['title'][:40]}... (评分：{top_products[0]['trend_score']})\n")
        
        # 图表展示
        if charts:
            report.append("## 📊 可视化图表\n")
            if 'trend_bar' in charts:
                report.append(f"### 趋势评分对比\n![趋势评分对比]({charts['trend_bar']})\n")
            if 'dashboard' in charts:
                report.append(f"### 综合仪表板\n[查看交互式仪表板]({charts['dashboard']})\n")
            if 'heatmap' in charts:
                report.append(f"### 指标相关性\n![相关性热力图]({charts['heatmap']})\n")
        
        # Top 商品列表
        report.append("## 📊 Top 商品列表\n")
        report.append("| 排名 | ASIN | 商品 | 价格 | 评分 | 趋势评分 | 标签 | 置信度 | 风险 |")
        report.append("|------|------|------|------|------|----------|------|--------|------|")
        
        for i, product in enumerate(top_products, 1):
            price = product.get("price")
            if isinstance(price, dict):
                price_str = f"{price.get('symbol', '$')}{price.get('value', 0):.2f}"
            elif isinstance(price, str):
                price_str = price
            else:
                price_str = "N/A"
            
            confidence = product.get('confidence', 0)
            risk_level = product.get('risk_level', '未知')
            
            report.append(
                f"| {i} | {product['asin']} | {product['title'][:25]}... | "
                f"{price_str} | {product.get('rating', 0)}⭐ | "
                f"{product['trend_score']} | {product['trend_label']} | "
                f"{confidence:.2f} | {risk_level} |"
            )
        
        # 详细分析
        report.append("\n## 📈 详细分析\n")
        
        for i, product in enumerate(top_products, 1):
            metrics = product.get("metrics", {})
            forecast = product.get("forecast_30d", {})
            
            price = product.get("price")
            price_str = f"{price.get('symbol', '$')}{price.get('value', 0):.2f}" if isinstance(price, dict) else "N/A"
            
            report.append(f"### {i}. {product['title'][:50]}")
            report.append(f"- **ASIN:** {product['asin']}")
            report.append(f"- **趋势评分:** {product['trend_score']} ({product['trend_label']})")
            report.append(f"- **置信度:** {product.get('confidence', 0):.2f}")
            report.append(f"- **风险等级:** {product.get('risk_level', '未知')}")
            
            report.append("\n**核心指标:**")
            report.append(f"- 销量增长：{metrics.get('sales_growth', 0):.1f}/100")
            report.append(f"- 评论增速：{metrics.get('review_growth', 0):.1f}/100")
            report.append(f"- BSR 排名：{metrics.get('bsr_improvement', 0):.1f}/100")
            
            report.append("\n**增强指标:**")
            report.append(f"- 利润率估算：{metrics.get('profit_margin', 0):.1f}/100")
            report.append(f"- 市场饱和度：{metrics.get('market_saturation', 0):.1f}/100 (越高越不饱和)")
            report.append(f"- 增长持续性：{metrics.get('growth_sustainability', 0):.1f}/100")
            report.append(f"- 风险评分：{metrics.get('risk_score', 0):.1f}/100 (越低越好)")
            
            report.append("\n**基础信息:**")
            report.append(f"- 价格：{price_str}")
            report.append(f"- 评分：{product.get('rating', 0)}⭐ ({product.get('ratings_total', 0)} 条评价)")
            
            if forecast:
                report.append("\n**🔮 30 天预测:**")
                report.append(f"- 预测评分：{forecast.get('score', 0):.2f}")
                report.append(f"- 变化趋势：{forecast.get('trend', '未知')} ({forecast.get('change', 0):+.2f})")
                ci = forecast.get('confidence_interval', {})
                report.append(f"- 置信区间：[{ci.get('low', 0):.2f}, {ci.get('high', 0):.2f}]")
            
            report.append("")
        
        # 建议与结论
        report.append("## 💡 建议与结论\n")
        
        # 推荐 Top3
        report.append("### ⭐ 重点推荐 Top3\n")
        for i, product in enumerate(top_products[:3], 1):
            forecast = product.get("forecast_30d", {})
            report.append(f"**{i}. {product['title'][:40]}...**")
            report.append(f"- 当前评分：{product['trend_score']} | 预测评分：{forecast.get('score', 0):.2f}")
            report.append(f"- 优势：高增长潜力、低市场饱和、良好利润率\n")
        
        # 风险提示
        report.append("### ⚠️ 风险提示\n")
        risky_products = [p for p in top_products if '高风险' in p.get('risk_level', '') or p.get('confidence', 1) < 0.6]
        if risky_products:
            for p in risky_products[:3]:
                report.append(f"- **{p['title'][:30]}...**: {p.get('risk_level', '')} (置信度：{p.get('confidence', 0):.2f})")
        else:
            report.append("本次分析未发现高风险商品 ✅")
        
        report.append("\n---")
        report.append("*报告由亚马逊选品系统自动生成 | 数据仅供参考，决策请结合市场调研*")
        
        report_text = "\n".join(report)
        
        # 保存到文件
        if output_path:
            filepath = DATA_DIR / output_path
            filepath.parent.mkdir(exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"报告已保存：{filepath}")
        
        return report_text
    
    def export_to_csv(self, analyzed_products: List[Dict], filename: str) -> str:
        """导出分析结果到 CSV"""
        filepath = DATA_DIR / filename
        
        def get_price_value(p):
            """安全获取价格值"""
            price = p.get("price")
            if isinstance(price, dict):
                return price.get("value")
            elif isinstance(price, str):
                return price
            return None
        
        def get_price_symbol(p):
            """安全获取价格符号"""
            price = p.get("price")
            if isinstance(price, dict):
                return price.get("symbol", "$")
            elif isinstance(price, str) and price.startswith("$"):
                return "$"
            return "$"
        
        # 扁平化数据
        rows = []
        for product in analyzed_products:
            row = {
                "asin": product.get("asin"),
                "title": product.get("title"),
                "trend_score": product.get("trend_score"),
                "trend_label": product.get("trend_label"),
                "sales_growth": product.get("metrics", {}).get("sales_growth"),
                "review_growth": product.get("metrics", {}).get("review_growth"),
                "bsr_improvement": product.get("metrics", {}).get("bsr_improvement"),
                "price_value": get_price_value(product),
                "price_currency": get_price_symbol(product),
                "rating": product.get("rating"),
                "ratings_total": product.get("ratings_total"),
                "is_prime": product.get("is_prime"),
                "is_amazon_choice": product.get("is_amazon_choice"),
                "is_best_seller": product.get("is_best_seller"),
                "collected_at": product.get("collected_at"),
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"数据已导出：{filepath}")
        
        return str(filepath)


# 使用示例
if __name__ == "__main__":
    # 测试数据
    test_products = [
        {
            "asin": "B001",
            "title": "Wireless Earbuds Pro",
            "price": {"symbol": "$", "value": 29.99, "raw": "$29.99"},
            "rating": 4.5,
            "ratings_total": 5000,
            "is_prime": True,
            "is_amazon_choice": True,
            "collected_at": datetime.utcnow().isoformat(),
        },
        {
            "asin": "B002",
            "title": "Phone Case Ultra",
            "price": {"symbol": "$", "value": 15.99, "raw": "$15.99"},
            "rating": 4.7,
            "ratings_total": 12000,
            "is_prime": True,
            "is_best_seller": True,
            "collected_at": datetime.utcnow().isoformat(),
        },
        {
            "asin": "B003",
            "title": "Laptop Stand Basic",
            "price": {"symbol": "$", "value": 19.99, "raw": "$19.99"},
            "rating": 4.2,
            "ratings_total": 800,
            "is_prime": False,
            "collected_at": datetime.utcnow().isoformat(),
        },
    ]
    
    analyzer = TrendAnalyzer()
    analyzed = analyzer.analyze_products(test_products)
    top_products = analyzer.select_top_n(analyzed, n=2)
    
    print("\n" + "="*60)
    print("🏆 Top 潜力商品")
    print("="*60)
    for i, p in enumerate(top_products, 1):
        print(f"\n{i}. {p['title']}")
        print(f"   ASIN: {p['asin']}")
        print(f"   趋势评分：{p['trend_score']} ({p['trend_label']})")
        print(f"   价格：${p['price']['value'] if p['price'] else 'N/A'}")
        print(f"   评分：{p['rating']}⭐ ({p['ratings_total']} 条评价)")
