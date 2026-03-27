"""
1688 供应商匹配模块测试脚本

使用方法：
python tests/test_supplier_finder.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src._1688.supplier_finder import SupplierFinder
from datetime import datetime


async def test_find_suppliers():
    """测试供应商查找"""
    print("\n" + "="*60)
    print("🏭 测试 1: 查找供应商")
    print("="*60)
    
    finder = SupplierFinder()
    
    test_titles = [
        "JBL Vibe Beam True Wireless Earbuds",
        "OtterBox iPhone Case",
        "Adjustable Laptop Stand",
    ]
    
    all_suppliers = []
    
    for title in test_titles:
        print(f"\n搜索：{title[:40]}...")
        suppliers = await finder.find_suppliers(title, limit=5)
        
        if suppliers:
            print(f"✅ 找到 {len(suppliers)} 个供应商")
            all_suppliers.extend(suppliers)
            
            # 显示第一个供应商
            s = suppliers[0]
            print(f"\n最佳匹配:")
            print(f"  公司：{s.get('company_name', 'N/A')}")
            print(f"  店铺：{s.get('shop_name', 'N/A')}")
            print(f"  地区：{s.get('location', 'N/A')}")
            print(f"  评分：{s.get('rating', 0)}/5.0")
            print(f"  经营：{s.get('years', 0)}年")
            print(f"  起订量：{s.get('min_order', 0)}件")
        else:
            print("⚠️ 未找到供应商")
    
    return all_suppliers


async def test_evaluate_supplier():
    """测试供应商评估"""
    print("\n" + "="*60)
    print("📊 测试 2: 供应商评估")
    print("="*60)
    
    finder = SupplierFinder()
    
    # 测试供应商数据
    test_supplier = {
        "company_name": "深圳市科技有限公司",
        "shop_name": "科技工厂店",
        "location": "广东 深圳",
        "years": 8,
        "rating": 4.8,
        "repeat_purchase_rate": "35%",
        "response_rate": "95%",
        "response_time": "< 2 小时",
        "min_order": 50,
        "price_range": "¥20-100",
        "transaction_level": 8,
        "is_verified": True,
        "is_power_user": True,
    }
    
    print("\n评估供应商:")
    print(f"  公司：{test_supplier['company_name']}")
    print(f"  评分：{test_supplier['rating']}/5.0")
    print(f"  经营：{test_supplier['years']}年")
    
    evaluation = finder.evaluate_supplier(test_supplier)
    
    print(f"\n评估结果:")
    print(f"  综合评分：{evaluation['overall_score']}/100")
    print(f"  推荐等级：{evaluation['recommendation']}")
    
    print("\n详细维度:")
    for dim, data in evaluation['dimensions'].items():
        print(f"  {dim}: {data['score']}/25 - {data['details']}")
    
    return evaluation


async def test_match_amazon_to_1688():
    """测试亚马逊 -1688 匹配"""
    print("\n" + "="*60)
    print("🔗 测试 3: 亚马逊 -1688 匹配")
    print("="*60)
    
    finder = SupplierFinder()
    
    # 亚马逊商品
    amazon_product = {
        "asin": "B0BQPNMXQV",
        "title": "JBL Vibe Beam True Wireless Earbuds",
        "price": {"symbol": "$", "value": 29.94, "raw": "$29.94"},
        "rating": 4.3,
        "ratings_total": 36211,
    }
    
    # 查找供应商
    suppliers = await finder.find_suppliers(amazon_product["title"], limit=10)
    
    # 匹配
    match_result = finder.match_amazon_to_1688(amazon_product, suppliers)
    
    print(f"\n亚马逊商品：{amazon_product['title'][:50]}...")
    print(f"匹配供应商：{len(match_result['suppliers'])} 个")
    
    if match_result['best_match']:
        best = match_result['best_match']
        print(f"\n最佳供应商:")
        print(f"  公司：{best['company_name']}")
        print(f"  综合评分：{best['overall_score']}/100")
        print(f"  推荐：{best['recommendation']}")
    
    return match_result


async def test_export():
    """测试数据导出"""
    print("\n" + "="*60)
    print("💾 测试 4: 数据导出")
    print("="*60)
    
    finder = SupplierFinder()
    
    # 生成测试数据
    suppliers = await finder.find_suppliers("wireless earbuds", limit=10)
    
    # 导出 CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = finder.export_suppliers(suppliers, f"suppliers_{timestamp}.csv")
    print(f"✅ CSV 已导出：{csv_path}")
    
    return csv_path


async def test_full_workflow():
    """测试完整工作流"""
    print("\n" + "="*60)
    print("🚀 测试 5: 完整工作流")
    print("="*60)
    
    finder = SupplierFinder()
    
    # 模拟 Top5 亚马逊商品
    top_products = [
        {
            "asin": "B0CGCMS31N",
            "title": "OtterBox iPhone 16e 15 14 13 Commuter Series Case",
            "price": {"symbol": "$", "value": 24.97},
            "rating": 4.6,
            "trend_score": 54.34,
        },
        {
            "asin": "B0BQPNMXQV",
            "title": "JBL Vibe Beam True Wireless JBL Deep Bass Sound Earbuds",
            "price": {"symbol": "$", "value": 29.94},
            "rating": 4.3,
            "trend_score": 51.0,
        },
        {
            "asin": "B08BRCT4JH",
            "title": "BESIGN LS03 Aluminum Laptop Stand Ergonomic",
            "price": {"symbol": "$", "value": 14.99},
            "rating": 4.8,
            "trend_score": 51.0,
        },
    ]
    
    print(f"\n为 {len(top_products)} 个商品匹配供应商...\n")
    
    match_results = []
    
    for product in top_products:
        print(f"处理：{product['title'][:40]}...")
        
        suppliers = await finder.find_suppliers(product["title"], limit=5)
        match = finder.match_amazon_to_1688(product, suppliers)
        match_results.append(match)
        
        print(f"  → 匹配 {len(suppliers)} 个供应商")
    
    # 生成报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"supplier_match_report_{timestamp}.md"
    report = finder.generate_match_report(match_results, report_path)
    
    print(f"\n✅ 报告已生成：{report_path}")
    print(f"\n报告摘要:")
    print(report[:800] + "..." if len(report) > 800 else report)
    
    return match_results


async def main():
    """主函数"""
    print("\n" + "🏭"*30)
    print("   1688 供应商匹配模块 - 测试套件")
    print("🏭"*30)
    
    print("\n选择测试模式:")
    print("1. 快速测试 (查找 + 评估)")
    print("2. 完整工作流测试")
    
    choice = input("\n请输入选项 (1/2): ").strip()
    
    if choice == "2":
        await test_full_workflow()
    else:
        await test_find_suppliers()
        await test_evaluate_supplier()
        await test_match_amazon_to_1688()
        await test_export()
    
    print("\n" + "="*60)
    print("✅ 测试完成!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
