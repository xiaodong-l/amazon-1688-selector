"""
测试可视化模块和增强分析算法

使用已有数据测试：
1. 可视化图表生成
2. 增强版趋势分析
3. 30 天预测
"""
import asyncio
from datetime import datetime
from pathlib import Path
import pandas as pd
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.analysis.trend_analyzer import TrendAnalyzer
from src.analysis.visualizer import TrendVisualizer
from src.utils.config import DATA_DIR

logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")


def load_test_data():
    """加载测试数据"""
    # 查找最新的 CSV 文件
    csv_files = list(DATA_DIR.glob("top20_*.csv"))
    
    if not csv_files:
        logger.error("未找到测试数据文件")
        return None
    
    latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    logger.info(f"加载测试数据：{latest_file}")
    
    df = pd.read_csv(latest_file)
    products = df.to_dict('records')
    
    # 修复价格字段 (CSV 中可能是字符串)
    for p in products:
        if isinstance(p.get('price_value'), (int, float)):
            p['price'] = {
                'symbol': p.get('price_currency', '$'),
                'value': p['price_value'],
            }
    
    logger.info(f"加载 {len(products)} 个商品")
    return products


def test_enhanced_analysis(products):
    """测试增强版分析"""
    logger.info("="*60)
    logger.info("测试增强版趋势分析")
    logger.info("="*60)
    
    analyzer = TrendAnalyzer()
    
    # 使用增强模式分析
    analyzed = analyzer.analyze_products(products, use_enhanced=True)
    
    # 显示 Top5
    logger.info("\n🏆 Top 5 商品 (增强版):")
    for i, p in enumerate(analyzed[:5], 1):
        metrics = p.get('metrics', {})
        forecast = p.get('forecast_30d', {})
        logger.info(
            f"{i}. {p['title'][:35]}... | "
            f"评分：{p['trend_score']} | "
            f"置信度：{p.get('confidence', 0):.2f} | "
            f"风险：{p.get('risk_level', '未知')} | "
            f"30 天预测：{forecast.get('trend', 'N/A')}"
        )
    
    # 对比基础版和增强版
    logger.info("\n📊 基础版 vs 增强版 对比:")
    analyzed_base = analyzer.analyze_products(products, use_enhanced=False)
    
    for i in range(3):
        base_score = analyzed_base[i]['trend_score']
        enhanced_score = analyzed[i]['trend_score']
        diff = enhanced_score - base_score
        logger.info(
            f"{i+1}. {analyzed[i]['title'][:25]}... | "
            f"基础：{base_score:.2f} | "
            f"增强：{enhanced_score:.2f} | "
            f"差异：{diff:+.2f}"
        )
    
    return analyzed


def test_visualization(products):
    """测试可视化图表生成"""
    logger.info("="*60)
    logger.info("测试可视化图表生成")
    logger.info("="*60)
    
    visualizer = TrendVisualizer()
    
    # 生成所有图表
    charts = visualizer.generate_all_charts(products, top_n=20)
    
    logger.info(f"\n✅ 生成 {len(charts)} 个图表:")
    for name, path in charts.items():
        logger.info(f"   {name}: {path}")
    
    return charts


def test_individual_features(products):
    """测试单个功能"""
    logger.info("="*60)
    logger.info("测试单个功能")
    logger.info("="*60)
    
    analyzer = TrendAnalyzer()
    visualizer = TrendVisualizer()
    
    # 1. 测试利润率估算
    logger.info("\n💰 利润率估算测试:")
    for p in products[:3]:
        metrics = analyzer._calculate_enhanced_metrics(p, {})
        logger.info(f"   {p['title'][:30]}... | 利润率：{metrics['profit_margin']:.1f}/100")
    
    # 2. 测试市场饱和度
    logger.info("\n📊 市场饱和度测试:")
    for p in products[:3]:
        metrics = analyzer._calculate_enhanced_metrics(p, {})
        saturation = metrics['market_saturation']
        level = "🔴 高饱和" if saturation < 40 else "🟡 中等" if saturation < 70 else "🟢 低饱和"
        logger.info(f"   {p['title'][:30]}... | 饱和度：{saturation:.1f} ({level})")
    
    # 3. 测试风险评分
    logger.info("\n⚠️ 风险评分测试:")
    for p in products[:3]:
        metrics = analyzer._calculate_enhanced_metrics(p, {})
        risk = metrics['risk_score']
        level = "🔴 高风险" if risk >= 50 else "🟡 中风险" if risk >= 30 else "🟢 低风险"
        logger.info(f"   {p['title'][:30]}... | 风险：{risk:.1f} ({level})")
    
    # 4. 测试 30 天预测
    logger.info("\n🔮 30 天预测测试:")
    for p in products[:3]:
        base_metrics = analyzer._calculate_metrics(p, None)
        enhanced_metrics = analyzer._calculate_enhanced_metrics(p, base_metrics)
        all_metrics = {**base_metrics, **enhanced_metrics}
        forecast = analyzer._forecast_30d(p, all_metrics, None)
        logger.info(
            f"   {p['title'][:25]}... | "
            f"当前：{p['trend_score']} | "
            f"预测：{forecast['score']:.2f} ({forecast['trend']})"
        )
    
    # 5. 测试单个雷达图
    logger.info("\n📊 生成 Top1 商品雷达图:")
    radar_path = visualizer.create_radar_chart(products[0])
    logger.info(f"   雷达图：{radar_path}")


def main():
    """主测试函数"""
    logger.info("🚀 开始测试可视化与增强分析功能")
    logger.info("="*60)
    
    # 加载测试数据
    products = load_test_data()
    if not products:
        logger.error("无法加载测试数据，退出")
        return
    
    # 测试增强分析
    analyzed = test_enhanced_analysis(products)
    
    # 测试可视化
    charts = test_visualization(analyzed)
    
    # 测试单个功能
    test_individual_features(analyzed)
    
    # 生成完整报告
    logger.info("\n" + "="*60)
    logger.info("生成完整测试报告")
    logger.info("="*60)
    
    analyzer = TrendAnalyzer()
    report = analyzer.generate_report(
        analyzed[:10], 
        f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        charts=charts
    )
    
    logger.info(f"\n✅ 所有测试完成!")
    logger.info(f"   分析商品数：{len(products)}")
    logger.info(f"   生成图表数：{len(charts)}")
    logger.info(f"   图表目录：{visualizer.output_dir}")


if __name__ == "__main__":
    main()
