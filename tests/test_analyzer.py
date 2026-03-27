"""
趋势分析模块测试脚本

使用方法：
python tests/test_analyzer.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.trend_analyzer import TrendAnalyzer
from datetime import datetime


def create_test_data():
    """创建测试数据"""
    return [
        {
            "asin": "B0BQPNMXQV",
            "title": "JBL Vibe Beam - True Wireless JBL Deep Bass Sound Earbuds",
            "price": {"symbol": "$", "value": 29.94, "raw": "$29.94"},
            "rating": 4.3,
            "ratings_total": 36211,
            "is_prime": True,
            "is_amazon_choice": False,
            "is_best_seller": False,
            "collected_at": datetime.utcnow().isoformat(),
        },
        {
            "asin": "B0CGCMS31N",
            "title": "OtterBox iPhone 16e, 15, 14, & 13 Commuter Series Case",
            "price": {"symbol": "$", "value": 24.97, "raw": "$24.97"},
            "rating": 4.6,
            "ratings_total": 8447,
            "is_prime": True,
            "is_amazon_choice": False,
            "is_best_seller": True,
            "collected_at": datetime.utcnow().isoformat(),
        },
        {
            "asin": "B0C7BKZ883",
            "title": "Adjustable Laptop Stand for Desk, Metal Foldable",
            "price": {"symbol": "$", "value": 14.99, "raw": "$14.99"},
            "rating": 4.6,
            "ratings_total": 3417,
            "is_prime": True,
            "is_amazon_choice": True,
            "is_best_seller": False,
            "collected_at": datetime.utcnow().isoformat(),
        },
        {
            "asin": "B09XYZ1234",
            "title": "USB C Cable 3-Pack 6ft Fast Charging Cord",
            "price": {"symbol": "$", "value": 9.99, "raw": "$9.99"},
            "rating": 4.5,
            "ratings_total": 15234,
            "is_prime": True,
            "is_amazon_choice": True,
            "is_best_seller": False,
            "collected_at": datetime.utcnow().isoformat(),
        },
        {
            "asin": "B08ABC5678",
            "title": "Portable Charger Power Bank 20000mAh",
            "price": {"symbol": "$", "value": 35.99, "raw": "$35.99"},
            "rating": 4.4,
            "ratings_total": 22156,
            "is_prime": True,
            "is_amazon_choice": False,
            "is_best_seller": True,
            "collected_at": datetime.utcnow().isoformat(),
        },
    ]


async def test_analyzer():
    """测试分析器"""
    print("\n" + "="*60)
    print("📈 趋势分析模块测试")
    print("="*60)
    
    # 创建测试数据
    products = create_test_data()
    print(f"\n测试数据：{len(products)} 个商品")
    
    # 初始化分析器
    analyzer = TrendAnalyzer()
    
    # 分析商品
    print("\n开始分析...")
    analyzed = analyzer.analyze_products(products)
    
    # 显示分析结果
    print("\n" + "-"*60)
    print("分析结果:")
    print("-"*60)
    
    for i, p in enumerate(analyzed, 1):
        print(f"\n{i}. {p['title'][:50]}...")
        print(f"   ASIN: {p['asin']}")
        print(f"   趋势评分：{p['trend_score']} ({p['trend_label']})")
        print(f"   指标详情:")
        metrics = p.get('metrics', {})
        print(f"     - 销量增长：{metrics.get('sales_growth', 0):.1f}/100")
        print(f"     - 评论增速：{metrics.get('review_growth', 0):.1f}/100")
        print(f"     - BSR 排名：{metrics.get('bsr_improvement', 0):.1f}/100")
    
    # 筛选 Top3
    print("\n" + "="*60)
    print("🏆 Top 3 潜力商品")
    print("="*60)
    
    top_3 = analyzer.select_top_n(analyzed, n=3)
    
    for i, p in enumerate(top_3, 1):
        price = p.get("price", {})
        price_str = f"${price.get('value', 0):.2f}" if price else "N/A"
        print(f"\n{i}🥇 {p['title'][:45]}...")
        print(f"   价格：{price_str} | 评分：{p['rating']}⭐ ({p['ratings_total']} 条)")
        print(f"   趋势评分：{p['trend_score']} - {p['trend_label']}")
    
    # 生成报告
    print("\n" + "="*60)
    print("📄 生成分析报告...")
    print("="*60)
    
    report = analyzer.generate_report(top_3)
    print(report[:1000] + "..." if len(report) > 1000 else report)
    
    # 导出 CSV
    from src.utils.config import DATA_DIR
    csv_path = analyzer.export_to_csv(analyzed, "test_analysis_result.csv")
    print(f"\n💾 CSV 已导出：{csv_path}")
    
    print("\n" + "="*60)
    print("✅ 测试完成!")
    print("="*60)
    
    return analyzed


async def test_with_real_data():
    """使用真实采集数据测试"""
    print("\n" + "="*60)
    print("📊 使用真实数据测试")
    print("="*60)
    
    import pandas as pd
    from src.utils.config import DATA_DIR
    
    # 查找最新的采集数据
    data_dir = DATA_DIR
    csv_files = list(data_dir.glob("rainforest_search_*.csv"))
    
    if not csv_files:
        print("⚠️ 未找到采集数据文件")
        print("请先运行：python tests/test_rainforest.py")
        return None
    
    # 使用最新文件
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"\n加载数据：{latest_file.name}")
    
    df = pd.read_csv(latest_file)
    products = df.to_dict('records')
    print(f"商品数量：{len(products)}")
    
    # 分析
    analyzer = TrendAnalyzer()
    analyzed = analyzer.analyze_products(products)
    
    # 筛选 Top20
    top_20 = analyzer.select_top_n(analyzed, n=20)
    
    print(f"\n🏆 Top 20 潜力商品:")
    print("-"*60)
    
    for i, p in enumerate(top_20, 1):
        price_val = p.get('price_value', 'N/A')
        if isinstance(price_val, (int, float)):
            price_str = f"${price_val:.2f}"
        else:
            price_str = str(price_val)
        
        print(f"{i:2}. {p['title'][:40]:40} | {price_str:8} | {p['rating']}⭐ | {p['trend_score']:5.1f} | {p['trend_label']}")
    
    # 导出
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = analyzer.export_to_csv(top_20, f"top20_{timestamp}.csv")
    report_path = f"top20_report_{timestamp}.md"
    analyzer.generate_report(top_20, report_path)
    
    print(f"\n✅ 分析完成!")
    print(f"   CSV: {csv_path}")
    print(f"   报告：{report_path}")
    
    return top_20


async def main():
    """主函数"""
    print("\n选择测试模式:")
    print("1. 使用模拟数据测试")
    print("2. 使用真实采集数据测试")
    
    choice = input("\n请输入选项 (1/2): ").strip()
    
    if choice == "2":
        await test_with_real_data()
    else:
        await test_analyzer()


if __name__ == "__main__":
    asyncio.run(main())
