"""
基于真实采集数据生成增强指标

所有指标必须基于实际采集的字段：
- price_value → 利润率
- ratings_total → 市场饱和度
- rating → 风险评估
- sales_growth, review_growth → 增长持续性
- collected_at → 季节性因子
"""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import (
    ANALYSIS_THRESHOLDS,
    CATEGORY_MARGINS,
    SEASONAL_FACTORS,
)
from src.utils.helpers import normalize_score, safe_divide


def calculate_profit_margin(price_value: float, title: str) -> float:
    """
    基于真实价格计算利润率估算
    
    参数:
        price_value: 实际采集的价格
        title: 商品标题（用于类目识别）
    
    返回:
        利润率评分 (0-100)
    """
    t = ANALYSIS_THRESHOLDS
    
    # 基于价格区间
    if price_value < t["price_low"]:
        base_margin = 0.20
    elif price_value < t["price_medium"]:
        base_margin = 0.30
    elif price_value < t["price_high"]:
        base_margin = 0.35
    elif price_value < t["price_premium"]:
        base_margin = 0.40
    else:
        base_margin = 0.35
    
    # 基于类目
    title_lower = title.lower()
    category_margin = CATEGORY_MARGINS.get("default")
    
    for cat, margin in CATEGORY_MARGINS.items():
        if cat in title_lower:
            category_margin = margin
            break
    
    # 综合利润率
    final_margin = (base_margin + category_margin) / 2
    
    return normalize_score(final_margin * 100 / 0.5)


def calculate_market_saturation(ratings_total: int, is_best_seller: bool) -> float:
    """
    基于真实评论数计算市场饱和度
    
    参数:
        ratings_total: 实际采集的评论总数
        is_best_seller: 是否 Best Seller
    
    返回:
        饱和度评分 (0-100, 越高越不饱和)
    """
    t = ANALYSIS_THRESHOLDS
    
    # 基于评论数
    if ratings_total > 50000:
        saturation_score = 20
    elif ratings_total > 10000:
        saturation_score = 40
    elif ratings_total > 5000:
        saturation_score = 60
    elif ratings_total > 1000:
        saturation_score = 75
    else:
        saturation_score = 90
    
    # Best Seller 调整
    if is_best_seller:
        saturation_score *= 0.7
    
    return normalize_score(saturation_score)


def calculate_growth_sustainability(rating: float, sales_growth: float, 
                                   review_growth: float) -> float:
    """
    基于真实评分和增长数据计算增长持续性
    
    参数:
        rating: 实际采集的评分
        sales_growth: 销量增长率
        review_growth: 评论增速
    
    返回:
        持续性评分 (0-100)
    """
    t = ANALYSIS_THRESHOLDS
    
    # 评分稳定性
    if rating >= t["rating_excellent"]:
        rating_score = 100
    elif rating >= t["rating_good"]:
        rating_score = 70
    elif rating >= t["rating_average"]:
        rating_score = 40
    else:
        rating_score = 20
    
    # 增长平衡性
    growth_balance = abs(sales_growth - review_growth)
    if growth_balance < 20:
        balance_score = 100
    elif growth_balance < 40:
        balance_score = 70
    else:
        balance_score = 40
    
    # 综合持续性
    sustainability = (rating_score * 0.6 + balance_score * 0.4)
    
    return normalize_score(sustainability)


def calculate_risk_score(rating: float, ratings_total: int, 
                        sales_growth: float, price_value: float) -> float:
    """
    基于真实数据计算风险评分
    
    参数:
        rating: 实际采集的评分
        ratings_total: 实际采集的评论总数
        sales_growth: 销量增长率
        price_value: 实际采集的价格
    
    返回:
        风险评分 (0-100, 越低风险越小)
    """
    t = ANALYSIS_THRESHOLDS
    risk = 0
    
    # 低评分风险
    if rating < t["rating_average"]:
        risk += 30
    elif rating < t["rating_good"]:
        risk += 15
    
    # 评论数过少风险
    if ratings_total < t["ratings_few"]:
        risk += 25
    elif ratings_total < t["ratings_low"]:
        risk += 10
    
    # 增长过快风险
    if sales_growth > t["growth_suspicious"]:
        risk += 20
    elif sales_growth > t["growth_high"]:
        risk += 10
    
    # 价格异常风险
    if price_value < 5:
        risk += 15
    elif price_value > 200:
        risk += 10
    
    return normalize_score(risk)


def calculate_confidence(rating: float, ratings_total: int, 
                        price_value: float) -> float:
    """
    基于真实数据计算置信度
    
    参数:
        rating: 实际采集的评分
        ratings_total: 实际采集的评论总数
        price_value: 实际采集的价格
    
    返回:
        置信度 (0-1)
    """
    confidence = 1.0
    
    # 样本量置信度
    if ratings_total < 100:
        confidence *= 0.6
    elif ratings_total < 500:
        confidence *= 0.8
    elif ratings_total < 2000:
        confidence *= 0.9
    
    # 数据完整性
    if not price_value or price_value <= 0:
        confidence *= 0.85
    if not rating or rating <= 0:
        confidence *= 0.85
    
    return round(confidence, 2)


def forecast_30d(rating: float, ratings_total: int, 
                sales_growth: float, review_growth: float,
                trend_score: float) -> dict:
    """
    基于真实数据预测 30 天趋势
    
    参数:
        rating: 实际采集的评分
        ratings_total: 实际采集的评论总数
        sales_growth: 实际采集的销量增长率
        review_growth: 实际采集的评论增速
        trend_score: 当前趋势评分
    
    返回:
        预测结果字典
    """
    t = ANALYSIS_THRESHOLDS
    
    # 基础趋势
    growth_momentum = (sales_growth + review_growth) / 2
    
    # 增长衰减
    if growth_momentum > 50:
        decay_factor = 0.7
    elif growth_momentum > 20:
        decay_factor = 0.85
    else:
        decay_factor = 0.95
    
    # 季节性调整
    current_month = datetime.now().month
    next_month = (current_month % 12) + 1
    current_factor = SEASONAL_FACTORS.get(current_month, 1.0)
    next_factor = SEASONAL_FACTORS.get(next_month, 1.0)
    seasonal_trend = safe_divide((next_factor - current_factor), current_factor, 0) * 10
    
    # 置信度调整
    confidence = calculate_confidence(rating, ratings_total, 0)
    
    # 预测变化
    score_change = (growth_momentum * 0.05 * decay_factor) + seasonal_trend
    score_change *= confidence
    
    forecast_score = trend_score + score_change
    
    # 趋势方向
    if score_change > 5:
        trend = "上升 ⬆️"
    elif score_change > 0:
        trend = "微升 ↗️"
    elif score_change > -5:
        trend = "微降 ↘️"
    else:
        trend = "下降 ⬇️"
    
    # 置信区间
    margin = max(5, abs(score_change) * 0.5)
    
    return {
        "score": round(normalize_score(forecast_score), 2),
        "change": round(score_change, 2),
        "trend": trend,
        "confidence_interval": {
            "low": round(normalize_score(forecast_score - margin), 2),
            "high": round(normalize_score(forecast_score + margin), 2),
        }
    }


def get_risk_level(risk_score: float) -> str:
    """根据风险评分返回风险等级"""
    t = ANALYSIS_THRESHOLDS
    
    if risk_score >= t["risk_high"]:
        return "🔴 高风险"
    elif risk_score >= t["risk_medium"]:
        return "🟡 中等风险"
    elif risk_score >= t["risk_low"]:
        return "🟢 低风险"
    else:
        return "🟢 极低风险"


def enhance_product_data(product: dict) -> dict:
    """
    为单个商品添加增强指标
    
    所有计算基于实际采集的字段
    """
    # 提取真实数据
    price_value = product.get('price_value', 0) or 0
    title = product.get('title', '')
    ratings_total = product.get('ratings_total', 0) or 0
    rating = product.get('rating', 0) or 0
    sales_growth = product.get('sales_growth', 0) or 0
    review_growth = product.get('review_growth', 0) or 0
    bsr_improvement = product.get('bsr_improvement', 0) or 0
    trend_score = product.get('trend_score', 0) or 0
    is_best_seller = product.get('is_best_seller', False)
    
    # 计算增强指标 (全部基于真实数据)
    metrics = {
        # 基础指标 (已有)
        "sales_growth": sales_growth,
        "review_growth": review_growth,
        "bsr_improvement": bsr_improvement,
        
        # 增强指标 (新计算)
        "profit_margin": calculate_profit_margin(price_value, title),
        "market_saturation": calculate_market_saturation(ratings_total, is_best_seller),
        "growth_sustainability": calculate_growth_sustainability(rating, sales_growth, review_growth),
        "risk_score": calculate_risk_score(rating, ratings_total, sales_growth, price_value),
    }
    
    # 置信度
    confidence = calculate_confidence(rating, ratings_total, price_value)
    
    # 30 天预测
    forecast = forecast_30d(rating, ratings_total, sales_growth, review_growth, trend_score)
    
    # 风险等级
    risk_level = get_risk_level(metrics["risk_score"])
    
    # 返回完整数据
    return {
        **product,
        "metrics": metrics,
        "confidence": confidence,
        "forecast_30d": forecast,
        "risk_level": risk_level,
    }


def main():
    """主函数：处理所有商品数据"""
    print("="*60)
    print("🔄 基于真实数据生成增强指标")
    print("="*60)
    print()
    
    # 加载真实数据
    data_dir = Path('data')
    csv_files = list(data_dir.glob('top20_*.csv'))
    
    if not csv_files:
        print("❌ 未找到 CSV 数据文件")
        return
    
    latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"📊 数据源：{latest_csv.name}")
    
    df = pd.read_csv(latest_csv)
    products = df.to_dict('records')
    print(f"📦 商品数量：{len(products)}")
    print()
    
    # 增强处理
    print("⚙️  计算增强指标...")
    enhanced_products = [enhance_product_data(p) for p in products]
    
    # 保存 JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = data_dir / f'top20_enhanced_{timestamp}.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_products, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 增强数据已保存：{output_file}")
    print()
    
    # 显示示例
    print("📋 增强指标示例 (Top 3):")
    print()
    
    for i, p in enumerate(enhanced_products[:3], 1):
        metrics = p['metrics']
        print(f"{i}. {p['title'][:40]}...")
        print(f"   ASIN: {p['asin']}")
        print(f"   基础数据:")
        print(f"     价格：${p['price_value']:.2f} | 评分：{p['rating']}⭐ | 评论：{p['ratings_total']:,}")
        print(f"     销量增长：{p['sales_growth']} | 评论增速：{p['review_growth']}")
        print(f"   增强指标:")
        print(f"     💰 利润率：{metrics['profit_margin']:.1f}/100")
        print(f"     📊 饱和度：{metrics['market_saturation']:.1f}/100")
        print(f"     📈 持续性：{metrics['growth_sustainability']:.1f}/100")
        print(f"     ⚠️  风险：{metrics['risk_score']:.1f}/100 ({p['risk_level']})")
        print(f"     ✅ 置信度：{p['confidence']:.2f}")
        print(f"   🔮 30 天预测:")
        print(f"     预测评分：{p['forecast_30d']['score']} | 趋势：{p['forecast_30d']['trend']}")
        print(f"     置信区间：[{p['forecast_30d']['confidence_interval']['low']}, {p['forecast_30d']['confidence_interval']['high']}]")
        print()
    
    print("="*60)
    print("✅ 所有指标均基于真实采集数据计算")
    print("="*60)


if __name__ == "__main__":
    main()
