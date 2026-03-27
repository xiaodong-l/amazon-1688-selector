"""
亚马逊数据采集模块

支持两种采集方式：
1. SP-API (官方推荐，合规)
2. Playwright 浏览器自动化 (备选)
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
from ..utils.config import AMAZON_CONFIG, DATA_DIR


class AmazonCollector:
    """亚马逊数据采集器"""
    
    def __init__(self, use_sp_api: bool = True, use_rainforest: bool = True):
        """
        初始化采集器
        
        Args:
            use_sp_api: 是否使用官方 SP-API (默认 True)
            use_rainforest: 是否使用 Rainforest API (默认 True，推荐)
        """
        self.use_sp_api = use_sp_api
        self.use_rainforest = use_rainforest
        self.request_delay = AMAZON_CONFIG["request_delay"]
        self.max_retries = AMAZON_CONFIG["max_retries"]
        
        if use_rainforest and AMAZON_CONFIG.get("rainforest_api_key"):
            logger.info("使用 Rainforest API 进行数据采集 (推荐)")
            self.rainforest_client = self._init_rainforest()
            self.sp_api = None
        elif use_sp_api:
            logger.info("使用亚马逊 SP-API 进行数据采集")
            self.sp_api = self._init_sp_api()
            self.rainforest_client = None
        else:
            logger.info("使用 Playwright 进行数据采集 (备选)")
            self.sp_api = None
            self.rainforest_client = None
            self.browser = None
    
    def _init_rainforest(self):
        """初始化 Rainforest API 客户端"""
        try:
            from .rainforest_client import RainforestClient
            client = RainforestClient()
            logger.info("Rainforest API 初始化成功")
            return client
        except Exception as e:
            logger.warning(f"Rainforest API 初始化失败：{e}")
            return None
    
    def _init_sp_api(self):
        """初始化 SP-API 客户端"""
        try:
            from sp_api.api import Products, Sales
            logger.info("SP-API 初始化成功")
            return {
                "products": Products(),
                "sales": Sales(),
            }
        except ImportError:
            logger.warning("SP-API 未安装，请运行：pip install sp-api-python")
            return None
    
    async def collect_product_data(
        self,
        keywords: List[str],
        categories: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        采集商品数据
        
        Args:
            keywords: 搜索关键词列表
            categories: 商品分类 (可选)
            limit: 每个关键词采集的商品数量
            
        Returns:
            商品数据列表
        """
        all_products = []
        
        for keyword in keywords:
            logger.info(f"采集关键词：{keyword}")
            
            try:
                if self.use_rainforest and self.rainforest_client:
                    products = await self._collect_via_rainforest(keyword, categories, limit)
                elif self.use_sp_api and self.sp_api:
                    products = await self._collect_via_sp_api(keyword, categories, limit)
                else:
                    products = await self._collect_via_playwright(keyword, categories, limit)
                
                all_products.extend(products)
                
                # 合规：控制请求频率
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"采集 {keyword} 失败：{e}")
                continue
        
        logger.info(f"采集完成，共 {len(all_products)} 个商品")
        return all_products
    
    async def _collect_via_rainforest(
        self,
        keyword: str,
        categories: Optional[List[str]],
        limit: int
    ) -> List[Dict]:
        """通过 Rainforest API 采集商品数据 (推荐)"""
        if not self.rainforest_client:
            logger.warning("Rainforest API 未初始化")
            return []
        
        products = await self.rainforest_client.search_products(
            keyword=keyword,
            marketplace="amazon.com",
            limit=limit
        )
        
        logger.info(f"Rainforest API 采集成功：{len(products)} 个商品")
        return products
    
    async def _collect_via_sp_api(
        self,
        keyword: str,
        categories: Optional[List[str]],
        limit: int
    ) -> List[Dict]:
        """通过 SP-API 采集商品数据"""
        products = []
        
        try:
            # 搜索商品
            search_results = self.sp_api["products"].search_catalog_items(
                keywords=keyword,
                marketplace_ids=["ATVPDKIKX0DER"],  # US marketplace
                item_count=limit
            )
            
            for item in search_results.get("items", []):
                product = {
                    "asin": item.get("asin"),
                    "title": item.get("item_name", {}).get("value"),
                    "brand": item.get("brand", {}).get("value"),
                    "category": item.get("product_classification", {}).get("product_category"),
                    "price": item.get("item_product_type"),
                    "collected_at": datetime.utcnow().isoformat(),
                    "source": "sp_api",
                }
                products.append(product)
                
        except Exception as e:
            logger.error(f"SP-API 采集失败：{e}")
        
        return products
    
    async def _collect_via_playwright(
        self,
        keyword: str,
        categories: Optional[List[str]],
        limit: int
    ) -> List[Dict]:
        """通过 Playwright 浏览器自动化采集 (备选方案)"""
        from playwright.async_api import async_playwright
        
        products = []
        
        # 随机 User-Agent 防止反爬
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        import random
        user_agent = random.choice(user_agents)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ]
            )
            
            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            
            # 添加反检测脚本
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            try:
                # 访问亚马逊搜索页面
                search_url = f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}"
                logger.info(f"访问：{search_url}")
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                
                # 等待页面加载
                await page.wait_for_timeout(3000)
                
                # 尝试多种选择器
                selectors = [
                    '[data-component-type="s-search-result"]',
                    '.s-result-item',
                    'li[class*="s-result-item"]',
                ]
                
                product_cards = []
                for selector in selectors:
                    try:
                        product_cards = await page.query_selector_all(selector)
                        if product_cards:
                            logger.info(f"使用选择器找到 {len(product_cards)} 个商品：{selector}")
                            break
                    except:
                        continue
                
                if not product_cards:
                    # 检查是否有验证码
                    captcha = await page.query_selector('form[action="/errors/validateCaptcha"]')
                    if captcha:
                        logger.warning("检测到验证码，需要人工干预")
                    else:
                        logger.warning("未找到商品列表，页面可能被阻止")
                    
                    # 保存页面快照用于调试
                    await page.screenshot(path="/tmp/amazon_debug.png")
                    logger.info("页面快照已保存：/tmp/amazon_debug.png")
                    return products
                
                for i, card in enumerate(product_cards[:limit]):
                    try:
                        asin = await card.get_attribute("data-asin")
                        if not asin:
                            continue
                            
                        title_elem = await card.query_selector("h2 a span, .a-size-medium, .a-text-normal")
                        title = await title_elem.inner_text() if title_elem else ""
                        
                        price_elem = await card.query_selector(".a-price .a-offscreen, .a-price span")
                        price = await price_elem.inner_text() if price_elem else ""
                        
                        product = {
                            "asin": asin,
                            "title": title.strip() if title else "",
                            "price": price.strip() if price else "",
                            "collected_at": datetime.utcnow().isoformat(),
                            "source": "playwright",
                        }
                        products.append(product)
                        
                    except Exception as e:
                        logger.warning(f"解析商品失败：{e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Playwright 采集失败：{e}")
            
            finally:
                await browser.close()
        
        return products
    
    async def collect_sales_data(self, asins: List[str]) -> List[Dict]:
        """
        采集销售数据 (BSR、评论等)
        
        Args:
            asins: ASIN 列表
            
        Returns:
            销售数据列表
        """
        sales_data = []
        
        for asin in asins:
            try:
                if self.use_sp_api and self.sp_api:
                    data = await self._get_sales_via_sp_api(asin)
                else:
                    data = await self._get_sales_via_playwright(asin)
                
                sales_data.append(data)
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"采集 {asin} 销售数据失败：{e}")
        
        return sales_data
    
    async def _get_sales_via_sp_api(self, asin: str) -> Dict:
        """通过 SP-API 获取销售数据"""
        try:
            # 获取商品详情
            product = self.sp_api["products"].get_catalog_item(
                asin=asin,
                marketplace_ids=["ATVPDKIKX0DER"]
            )
            
            return {
                "asin": asin,
                "bsr": product.get("sales_rank"),
                "reviews_count": product.get("customer_reviews", {}).get("count"),
                "rating": product.get("customer_reviews", {}).get("star_rating"),
                "collected_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"SP-API 获取销售数据失败：{e}")
            return {"asin": asin, "error": str(e)}
    
    async def _get_sales_via_playwright(self, asin: str) -> Dict:
        """通过 Playwright 获取销售数据"""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(f"https://www.amazon.com/dp/{asin}", wait_until="domcontentloaded")
                
                # 提取 BSR
                bsr_elem = await page.query_selector("#SalesRank")
                bsr = await bsr_elem.inner_text() if bsr_elem else ""
                
                # 提取评论数
                review_elem = await page.query_selector("#acrCustomerReviewText")
                reviews = await review_elem.inner_text() if review_elem else ""
                
                return {
                    "asin": asin,
                    "bsr": bsr,
                    "reviews_count": reviews,
                    "collected_at": datetime.utcnow().isoformat(),
                }
                
            finally:
                await browser.close()
    
    def save_to_csv(self, products: List[Dict], filename: str):
        """保存数据到 CSV"""
        import pandas as pd
        
        filepath = DATA_DIR / filename
        df = pd.DataFrame(products)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"数据已保存到：{filepath}")
        return filepath


# 使用示例
if __name__ == "__main__":
    async def main():
        collector = AmazonCollector(use_sp_api=True)
        
        keywords = ["wireless earbuds", "phone case", "laptop stand"]
        products = await collector.collect_product_data(keywords, limit=50)
        
        collector.save_to_csv(products, f"amazon_products_{datetime.now().strftime('%Y%m%d')}.csv")
    
    asyncio.run(main())
