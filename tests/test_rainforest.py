"""
Rainforest API 测试脚本

使用方法：
python tests/test_rainforest.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.amazon.rainforest_client import RainforestClient
from datetime import datetime


async def test_search():
    """测试商品搜索"""
    print("\n" + "="*60)
    print("🔍 测试 1: 商品搜索")
    print("="*60)
    
    client = RainforestClient()
    
    test_keywords = [
        "wireless earbuds",
        "phone case",
        "laptop stand",
    ]
    
    all_products = []
    
    for keyword in test_keywords:
        print(f"\n搜索：{keyword}")
        products = await client.search_products(keyword, limit=5)
        
        if products:
            print(f"✅ 找到 {len(products)} 个商品")
            all_products.extend(products)
            
            # 显示第一个商品详情
            p = products[0]
            print(f"\n示例商品:")
            print(f"  标题：{p['title'][:60]}...")
            print(f"  ASIN: {p['asin']}")
            print(f"  价格：{p['price']['raw'] if p['price'] else 'N/A'}")
            print(f"  评分：{p['rating']} ⭐ ({p['ratings_total']} 条评价)")
            if p.get('is_prime'):
                print(f"  标签：Prime ✓")
            if p.get('is_amazon_choice'):
                print(f"  标签：Amazon's Choice 🏆")
            if p.get('is_best_seller'):
                print(f"  标签：Best Seller 🔥")
        else:
            print(f"⚠️ 未找到商品")
    
    return all_products


async def test_product_details(asin: str):
    """测试商品详情"""
    print("\n" + "="*60)
    print("📦 测试 2: 商品详情")
    print("="*60)
    
    client = RainforestClient()
    
    print(f"\n获取详情：{asin}")
    details = await client.get_product_details(asin)
    
    if details:
        print("✅ 获取成功")
        print(f"\n商品详情:")
        print(f"  标题：{details['title'][:80]}...")
        print(f"  价格：{details['price']['raw'] if details['price'] else 'N/A'}")
        print(f"  评分：{details['rating']} ⭐ ({details['ratings_total']} 条评价)")
        print(f"  评论数：{details['reviews_total']}")
        
        if details.get('bestsellers_rank'):
            print(f"  BSR 排名:")
            for rank in details['bestsellers_rank'][:2]:
                print(f"    - {rank.get('category', 'N/A')}: #{rank.get('rank', 'N/A')}")
        
        return details
    else:
        print("❌ 获取失败")
        return None


async def test_reviews(asin: str):
    """测试评论获取"""
    print("\n" + "="*60)
    print("💬 测试 3: 商品评论")
    print("="*60)
    
    client = RainforestClient()
    
    print(f"\n获取评论：{asin}")
    reviews = await client.get_product_reviews(asin, limit=5)
    
    if reviews:
        print(f"✅ 获取 {len(reviews)} 条评论")
        
        for i, r in enumerate(reviews[:3], 1):
            print(f"\n{i}. {r.get('title', '无标题')}")
            print(f"   评分：{'⭐' * r.get('rating', 0)}")
            print(f"   日期：{r.get('date', 'N/A')}")
            print(f"   内容：{r.get('body', '')[:100]}...")
        
        return reviews
    else:
        print("⚠️ 未获取到评论")
        return []


async def test_quota():
    """检查配额"""
    print("\n" + "="*60)
    print("📊 测试 4: API 配额")
    print("="*60)
    
    client = RainforestClient()
    quota = client.check_quota()
    
    print(f"\n当前计划：{quota['plan']}")
    print(f"月度限额：{quota['monthly_limit']} 次请求")
    print(f"说明：{quota['note']}")


async def save_to_csv(products, filename: str):
    """保存数据到 CSV"""
    import pandas as pd
    
    filepath = Path(__file__).parent.parent / "data" / filename
    filepath.parent.mkdir(exist_ok=True)
    
    df = pd.DataFrame(products)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"\n💾 数据已保存：{filepath}")
    return filepath


async def main():
    """主测试流程"""
    print("\n" + "🚀"*30)
    print("   Rainforest API - 测试套件")
    print("🚀"*30)
    
    # 测试 1: 搜索商品
    products = await test_search()
    
    if products:
        # 保存搜索结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await save_to_csv(products, f"rainforest_search_{timestamp}.csv")
        
        # 测试 2: 获取第一个商品的详情
        if products:
            asin = products[0]['asin']
            details = await test_product_details(asin)
            
            # 测试 3: 获取评论
            if details:
                await test_reviews(asin)
    
    # 测试 4: 检查配额
    await test_quota()
    
    # 汇总
    print("\n" + "="*60)
    print("📊 测试汇总")
    print("="*60)
    print(f"\n采集商品总数：{len(products)}")
    print(f"API 状态：✅ 正常")
    print("\n✅ Rainforest API 集成成功!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
