"""
Rainforest API 客户端

Rainforest API 是亚马逊官方数据合作伙伴，提供稳定合规的数据采集服务
文档：https://www.rainforestapi.com/docs

免费额度：100 次请求/月
付费计划：$75/月起
"""
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from ..utils.config import AMAZON_CONFIG


class RainforestClient:
    """Rainforest API 客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            api_key: Rainforest API Key (如不提供则从配置读取)
        """
        self.api_key = api_key or AMAZON_CONFIG["rainforest_api_key"]
        self.base_url = AMAZON_CONFIG["rainforest_base_url"]
        self.max_retries = AMAZON_CONFIG["max_retries"]
        
        if not self.api_key:
            raise ValueError("Rainforest API Key 未配置")
        
        logger.info("Rainforest API 客户端初始化成功")
    
    async def search_products(
        self,
        keyword: str,
        marketplace: str = "amazon.com",
        limit: int = 20
    ) -> List[Dict]:
        """
        搜索商品
        
        Args:
            keyword: 搜索关键词
            marketplace: 亚马逊站点 (amazon.com, amazon.co.uk 等)
            limit: 返回数量限制
            
        Returns:
            商品列表
        """
        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": marketplace,
            "search_term": keyword,
            "sort_by": "featured",  # 按相关性排序
        }
        
        logger.info(f"搜索：{keyword} (marketplace: {marketplace})")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_search_results(data, limit)
                    else:
                        error_text = await response.text()
                        logger.error(f"API 请求失败：{response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"搜索失败：{e}")
            return []
    
    def _parse_search_results(self, data: Dict, limit: int) -> List[Dict]:
        """解析搜索结果"""
        products = []
        
        search_results = data.get("search_results", [])
        
        for item in search_results[:limit]:
            try:
                product = {
                    "asin": item.get("asin"),
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "price": {
                        "symbol": item.get("price", {}).get("symbol", "$"),
                        "value": item.get("price", {}).get("value"),
                        "raw": item.get("price", {}).get("raw"),
                    } if item.get("price") else None,
                    "rating": item.get("rating"),
                    "ratings_total": item.get("ratings_total"),
                    "is_prime": item.get("is_prime", False),
                    "is_amazon_choice": item.get("is_amazon_choice", False),
                    "is_best_seller": item.get("is_best_seller", False),
                    "position": item.get("position"),
                    "collected_at": datetime.utcnow().isoformat(),
                    "source": "rainforest_api",
                }
                products.append(product)
            except Exception as e:
                logger.warning(f"解析商品失败：{e}")
                continue
        
        logger.info(f"解析成功 {len(products)} 个商品")
        return products
    
    async def get_product_details(self, asin: str, marketplace: str = "amazon.com") -> Optional[Dict]:
        """
        获取商品详情
        
        Args:
            asin: 商品 ASIN
            marketplace: 亚马逊站点
            
        Returns:
            商品详情
        """
        params = {
            "api_key": self.api_key,
            "type": "product",
            "amazon_domain": marketplace,
            "asin": asin,
        }
        
        logger.info(f"获取商品详情：{asin}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_product_details(data)
                    else:
                        error_text = await response.text()
                        logger.error(f"API 请求失败：{response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"获取详情失败：{e}")
            return None
    
    def _parse_product_details(self, data: Dict) -> Dict:
        """解析商品详情"""
        product = data.get("product", {})
        
        return {
            "asin": product.get("asin"),
            "title": product.get("title"),
            "description": product.get("description"),
            "feature_bullets": product.get("feature_bullets"),
            "categories": product.get("categories"),
            "price": {
                "symbol": product.get("price", {}).get("symbol", "$"),
                "value": product.get("price", {}).get("value"),
                "raw": product.get("price", {}).get("raw"),
            } if product.get("price") else None,
            "rating": product.get("rating"),
            "ratings_total": product.get("ratings_total"),
            "reviews_total": product.get("reviews_total"),
            "bestsellers_rank": product.get("bestsellers_rank"),  # BSR 排名
            "main_image": product.get("main_image", {}).get("link"),
            "images": [img.get("link") for img in product.get("images", [])],
            "variants": product.get("variants"),
            "collected_at": datetime.utcnow().isoformat(),
            "source": "rainforest_api",
        }
    
    async def get_product_reviews(
        self,
        asin: str,
        marketplace: str = "amazon.com",
        limit: int = 10
    ) -> List[Dict]:
        """
        获取商品评论
        
        Args:
            asin: 商品 ASIN
            marketplace: 亚马逊站点
            limit: 评论数量限制
            
        Returns:
            评论列表
        """
        params = {
            "api_key": self.api_key,
            "type": "reviews",
            "amazon_domain": marketplace,
            "asin": asin,
            "sort_by": "recent",  # 按最新排序
        }
        
        logger.info(f"获取评论：{asin}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_reviews(data, limit)
                    else:
                        error_text = await response.text()
                        logger.error(f"API 请求失败：{response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"获取评论失败：{e}")
            return []
    
    def _parse_reviews(self, data: Dict, limit: int) -> List[Dict]:
        """解析评论数据"""
        reviews = []
        
        review_list = data.get("product", {}).get("reviews", [])
        
        for review in review_list[:limit]:
            try:
                reviews.append({
                    "id": review.get("id"),
                    "title": review.get("title"),
                    "body": review.get("body"),
                    "rating": review.get("rating"),
                    "date": review.get("date"),
                    "verified_purchase": review.get("verified_purchase", False),
                    "helpful_votes": review.get("helpful_votes"),
                    "author": review.get("profile", {}).get("name"),
                    "collected_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                logger.warning(f"解析评论失败：{e}")
                continue
        
        return reviews
    
    async def search_by_image(
        self,
        image_url: str,
        marketplace: str = "amazon.com",
        limit: int = 20
    ) -> List[Dict]:
        """
        以图搜图 (搜索相似商品)
        
        Args:
            image_url: 图片 URL
            marketplace: 亚马逊站点
            limit: 返回数量限制
            
        Returns:
            相似商品列表
        """
        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": marketplace,
            "search_term": image_url,
            "search_type": "image",
        }
        
        logger.info(f"以图搜图：{image_url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_search_results(data, limit)
                    else:
                        error_text = await response.text()
                        logger.error(f"API 请求失败：{response.status} - {error_text}")
                        return []
        except Exception as e:
            logger.error(f"以图搜图失败：{e}")
            return []
    
    def check_quota(self) -> Dict:
        """
        检查 API 配额
        
        Returns:
            配额信息
        """
        # Rainforest API 免费额度：100 次/月
        # 需要通过实际请求来检查剩余配额
        return {
            "plan": "free",
            "monthly_limit": 100,
            "note": "免费额度 100 次/月，超出需升级付费计划",
        }


# 使用示例
if __name__ == "__main__":
    async def main():
        # 初始化客户端
        client = RainforestClient()
        
        # 搜索商品
        products = await client.search_products("wireless earbuds", limit=5)
        
        print(f"\n找到 {len(products)} 个商品:\n")
        for i, p in enumerate(products, 1):
            print(f"{i}. {p['title']}")
            print(f"   ASIN: {p['asin']}")
            print(f"   价格：{p['price']['raw'] if p['price'] else 'N/A'}")
            print(f"   评分：{p['rating']} ({p['ratings_total']} 条评价)")
            print()
    
    asyncio.run(main())
