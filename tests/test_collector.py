"""
亚马逊采集模块测试脚本

使用方法：
1. 复制 .env.example 为 .env 并配置凭证
2. 运行：python -m tests.test_collector
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.amazon.collector import AmazonCollector
from src.utils.config import DATA_DIR
from loguru import logger
from datetime import datetime


async def test_sp_api_connection():
    """测试 SP-API 连接"""
    print("\n" + "="*60)
    print("🔌 测试 1: SP-API 连接测试")
    print("="*60)
    
    collector = AmazonCollector(use_sp_api=True)
    
    if collector.sp_api:
        print("✅ SP-API 初始化成功")
        return True
    else:
        print("❌ SP-API 未配置或初始化失败")
        print("\n请检查:")
        print("1. 是否已安装 sp-api-python: pip install sp-api-python")
        print("2. 是否已配置 .env 文件中的 AMAZON_SP_API_ID 和 AMAZON_SP_API_SECRET")
        return False


async def test_playwright_collection():
    """测试 Playwright 采集 (备选方案)"""
    print("\n" + "="*60)
    print("🎭 测试 2: Playwright 采集测试")
    print("="*60)
    
    collector = AmazonCollector(use_sp_api=False)
    
    test_keywords = ["wireless earbuds"]
    
    try:
        print(f"正在采集关键词：{test_keywords[0]}")
        products = await collector.collect_product_data(test_keywords, limit=5)
        
        if products:
            print(f"✅ 采集成功，获取 {len(products)} 个商品")
            print("\n示例数据:")
            for i, p in enumerate(products[:2], 1):
                print(f"  {i}. {p.get('title', 'N/A')[:50]}...")
                print(f"     ASIN: {p.get('asin', 'N/A')}")
                print(f"     价格：{p.get('price', 'N/A')}")
            return True
        else:
            print("⚠️ 采集结果为空，可能遇到反爬或网络问题")
            return False
            
    except Exception as e:
        print(f"❌ 采集失败：{e}")
        print("\n请检查:")
        print("1. 是否已安装 playwright: pip install playwright")
        print("2. 是否已安装浏览器：playwright install")
        print("3. 网络连接是否正常")
        return False


async def test_sp_api_collection():
    """测试 SP-API 采集"""
    print("\n" + "="*60)
    print("📦 测试 3: SP-API 采集测试")
    print("="*60)
    
    collector = AmazonCollector(use_sp_api=True)
    
    if not collector.sp_api:
        print("⏭️ 跳过 (SP-API 未配置)")
        return None
    
    test_keywords = ["phone case"]
    
    try:
        print(f"正在采集关键词：{test_keywords[0]}")
        products = await collector.collect_product_data(test_keywords, limit=5)
        
        if products:
            print(f"✅ 采集成功，获取 {len(products)} 个商品")
            return True
        else:
            print("⚠️ 采集结果为空")
            return False
            
    except Exception as e:
        print(f"❌ 采集失败：{e}")
        return False


async def test_data_export():
    """测试数据导出"""
    print("\n" + "="*60)
    print("💾 测试 4: 数据导出测试")
    print("="*60)
    
    collector = AmazonCollector(use_sp_api=False)
    
    # 生成测试数据
    test_products = [
        {
            "asin": "B08XYZ123",
            "title": "Test Wireless Earbuds",
            "price": "$29.99",
            "collected_at": datetime.utcnow().isoformat(),
            "source": "test"
        },
        {
            "asin": "B09ABC456",
            "title": "Test Phone Case",
            "price": "$15.99",
            "collected_at": datetime.utcnow().isoformat(),
            "source": "test"
        }
    ]
    
    try:
        filename = f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = collector.save_to_csv(test_products, filename)
        print(f"✅ 数据导出成功：{filepath}")
        return True
    except Exception as e:
        print(f"❌ 导出失败：{e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print("   亚马逊采集模块 - 测试套件")
    print("🚀"*30)
    
    results = {
        "sp_api_connection": None,
        "playwright_collection": None,
        "sp_api_collection": None,
        "data_export": None,
    }
    
    # 测试 1: SP-API 连接
    results["sp_api_connection"] = await test_sp_api_connection()
    
    # 测试 2: Playwright 采集
    results["playwright_collection"] = await test_playwright_collection()
    
    # 测试 3: SP-API 采集
    results["sp_api_collection"] = await test_sp_api_collection()
    
    # 测试 4: 数据导出
    results["data_export"] = await test_data_export()
    
    # 汇总报告
    print("\n" + "="*60)
    print("📊 测试汇总报告")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    print(f"\n通过：{passed} | 失败：{failed} | 跳过：{skipped}")
    print(f"总计：{len(results)} 项测试")
    
    if failed == 0 and passed > 0:
        print("\n✅ 所有测试通过！采集模块可以正常使用")
    elif failed > 0:
        print("\n⚠️ 部分测试失败，请根据上述提示进行配置")
    
    print("\n" + "="*60)
    
    return results


async def interactive_test():
    """交互式测试 - 采集指定关键词"""
    print("\n" + "="*60)
    print("🔍 交互式采集测试")
    print("="*60)
    
    collector = AmazonCollector(use_sp_api=False)  # 默认使用 Playwright
    
    keyword = input("\n请输入要采集的关键词 (英文): ").strip()
    if not keyword:
        keyword = "wireless earbuds"
        print(f"使用默认关键词：{keyword}")
    
    limit = input("请输入采集数量 (默认 10): ").strip()
    limit = int(limit) if limit.isdigit() else 10
    
    print(f"\n开始采集：{keyword} (限制：{limit} 个)")
    print("-"*60)
    
    try:
        products = await collector.collect_product_data([keyword], limit=limit)
        
        if products:
            print(f"\n✅ 采集成功！共 {len(products)} 个商品\n")
            
            # 显示前 5 个
            for i, p in enumerate(products[:5], 1):
                print(f"{i}. {p.get('title', 'N/A')}")
                print(f"   ASIN: {p.get('asin', 'N/A')}")
                print(f"   价格：{p.get('price', 'N/A')}")
                print()
            
            # 询问是否保存
            save = input("是否保存为 CSV? (y/n): ").strip().lower()
            if save == 'y':
                filename = f"amazon_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
                filepath = collector.save_to_csv(products, filename)
                print(f"已保存：{filepath}")
        else:
            print("\n⚠️ 未采集到数据")
            
    except Exception as e:
        print(f"\n❌ 采集失败：{e}")


async def main():
    """主函数"""
    print("\n请选择测试模式:")
    print("1. 运行全部自动化测试")
    print("2. 交互式采集测试")
    
    choice = input("\n请输入选项 (1/2): ").strip()
    
    if choice == "2":
        await interactive_test()
    else:
        await run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
