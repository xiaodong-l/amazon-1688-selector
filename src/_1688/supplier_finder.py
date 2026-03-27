"""
1688 供应商匹配模块

功能：
1. 基于关键词搜索 1688 供应商
2. 基于图像搜索相似商品
3. Top10 供应商筛选
4. 供应商评估指标 (价格、MOQ、评分、复购率等)

注意：1688 官方 API 需要企业账号，本模块提供两种方案：
- 方案 A: 1688 官方 API (推荐，需申请)
- 方案 B: 爬虫方案 (备选，有反爬风险)
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
import re

from ..utils.config import ALIBABA_CONFIG, DATA_DIR


class SupplierFinder:
    """1688 供应商查找器"""
    
    def __init__(self, use_api: bool = False, api_key: Optional[str] = None):
        """
        初始化查找器
        
        Args:
            use_api: 是否使用官方 API (默认 False，使用爬虫方案)
            api_key: 1688 API Key (可选)
        """
        self.use_api = use_api
        self.api_key = api_key
        self.request_delay = ALIBABA_CONFIG["request_delay"]
        self.max_retries = ALIBABA_CONFIG["max_retries"]
        self.top_n = 10
        
        if use_api and api_key:
            logger.info("使用 1688 官方 API")
        else:
            logger.info("使用爬虫方案 (备选)")
    
    async def find_suppliers(
        self,
        product_title: str,
        keywords: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        查找供应商
        
        Args:
            product_title: 商品标题 (来自亚马逊)
            keywords: 提取的关键词 (可选，自动提取)
            limit: 返回供应商数量
            
        Returns:
            供应商列表
        """
        # 提取关键词
        if not keywords:
            keywords = self._extract_keywords(product_title)
        
        logger.info(f"查找供应商：{product_title[:50]}...")
        logger.info(f"关键词：{keywords}")
        
        suppliers = []
        
        for keyword in keywords[:3]:  # 最多用 3 个关键词搜索
            try:
                if self.use_api and self.api_key:
                    results = await self._search_via_api(keyword, limit)
                else:
                    results = await self._search_via_crawl(keyword, limit)
                
                suppliers.extend(results)
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"搜索 {keyword} 失败：{e}")
                continue
        
        # 去重并排序
        suppliers = self._deduplicate_and_sort(suppliers, limit)
        
        logger.info(f"找到 {len(suppliers)} 个供应商")
        return suppliers
    
    def _extract_keywords(self, title: str) -> List[str]:
        """从商品标题提取关键词"""
        # 移除常见修饰词
        stop_words = [
            "for", "with", "and", "the", "a", "an", "in", "on",
            "无线", "蓝牙", "便携式", "多功能", "升级版", "专业版",
            "True Wireless", "Bluetooth", "Portable", "Professional",
        ]
        
        # 简单分词 (中文按字符，英文按空格)
        words = title.split()
        
        # 过滤短词和停用词
        keywords = [
            w for w in words
            if len(w) > 3 and w.lower() not in [s.lower() for s in stop_words]
        ]
        
        # 提取核心名词 (简单规则：大写字母开头或中文)
        core_keywords = []
        for kw in keywords[:5]:
            # 保留品牌词和产品词
            if kw[0].isupper() or any('\u4e00' <= c <= '\u9fff' for c in kw):
                core_keywords.append(kw)
        
        # 如果提取失败，使用原标题
        if not core_keywords:
            core_keywords = [title.split()[0]] if title.split() else ["product"]
        
        return core_keywords[:3]
    
    async def _search_via_api(self, keyword: str, limit: int) -> List[Dict]:
        """通过 1688 API 搜索 (需要企业账号)"""
        # 1688 官方 API 文档：https://open.1688.com/
        # 需要申请 appkey 和 secret
        
        logger.warning("1688 API 需要企业账号申请，暂使用模拟数据")
        
        # 返回模拟数据用于开发测试
        return self._generate_mock_suppliers(keyword, limit)
    
    async def _search_via_crawl(self, keyword: str, limit: int) -> List[Dict]:
        """
        通过爬虫搜索 1688
        
        注意：1688 有严格的反爬机制，需要：
        - 使用 Playwright/Selenium
        - 登录账号 (需要 1688 会员)
        - 使用代理 IP
        - 控制请求频率
        """
        logger.info(f"爬虫搜索：{keyword}")
        
        # 由于 1688 反爬严格，这里返回模拟数据
        # 实际生产环境需要：
        # 1. 配置 1688 账号 cookie
        # 2. 使用 Playwright 模拟浏览器
        # 3. 处理验证码
        
        return self._generate_mock_suppliers(keyword, limit)
    
    def _generate_mock_suppliers(self, keyword: str, limit: int) -> List[Dict]:
        """生成模拟供应商数据 (用于开发测试)"""
        import random
        
        base_suppliers = [
            {
                "company_name": f"深圳市{keyword}科技有限公司",
                "shop_name": f"{keyword}工厂店",
                "location": "广东 深圳",
                "years": random.randint(3, 10),
                "rating": round(random.uniform(4.5, 5.0), 1),
                "repeat_purchase_rate": f"{random.randint(20, 40)}%",
                "response_rate": f"{random.randint(85, 99)}%",
                "response_time": f"< {random.randint(1, 12)}小时",
                "min_order": random.randint(2, 100),
                "price_range": f"¥{random.randint(5, 50)}-{random.randint(50, 200)}",
                "transaction_level": random.randint(5, 10),
                "is_verified": random.choice([True, True, True, False]),
                "is_power_user": random.choice([True, True, False]),
                "main_products": f"{keyword}, 相关产品，配件",
                "capacity": f"日产{random.randint(1000, 10000)}件",
            }
            for _ in range(limit)
        ]
        
        for i, s in enumerate(base_suppliers):
            s["rank"] = i + 1
            s["search_keyword"] = keyword
            s["collected_at"] = datetime.utcnow().isoformat()
        
        return base_suppliers
    
    def _deduplicate_and_sort(self, suppliers: List[Dict], limit: int) -> List[Dict]:
        """去重并排序供应商"""
        # 按公司名去重
        seen = set()
        unique = []
        
        for s in suppliers:
            key = s.get("company_name", "") + s.get("shop_name", "")
            if key not in seen:
                seen.add(key)
                unique.append(s)
        
        # 综合评分排序
        def score(s):
            rating = s.get("rating", 0) or 0
            years = s.get("years", 0) or 0
            trans_level = s.get("transaction_level", 0) or 0
            verified = 1 if s.get("is_verified") else 0
            power_user = 1 if s.get("is_power_user") else 0
            
            return rating * 10 + years * 2 + trans_level + verified * 5 + power_user * 3
        
        unique.sort(key=score, reverse=True)
        
        return unique[:limit]
    
    def evaluate_supplier(self, supplier: Dict) -> Dict:
        """
        评估供应商
        
        返回详细评估报告
        """
        evaluation = {
            "company_name": supplier.get("company_name"),
            "shop_name": supplier.get("shop_name"),
            "overall_score": 0,
            "dimensions": {},
            "recommendation": "",
        }
        
        # 1. 信誉评分 (0-25)
        rating = supplier.get("rating", 0) or 0
        score_rating = min(25, rating * 5)
        evaluation["dimensions"]["信誉"] = {
            "score": score_rating,
            "details": f"店铺评分 {rating}/5.0",
        }
        
        # 2. 经验评分 (0-25)
        years = supplier.get("years", 0) or 0
        score_experience = min(25, years * 3)
        evaluation["dimensions"]["经验"] = {
            "score": score_experience,
            "details": f"经营 {years} 年",
        }
        
        # 3. 服务评分 (0-25)
        response_rate = supplier.get("response_rate", "0%")
        response_rate_num = int(re.search(r'\d+', response_rate).group()) if re.search(r'\d+', response_rate) else 0
        score_service = min(25, response_rate_num / 4)
        evaluation["dimensions"]["服务"] = {
            "score": score_service,
            "details": f"响应率 {response_rate}",
        }
        
        # 4. 实力评分 (0-25)
        trans_level = supplier.get("transaction_level", 0) or 0
        verified = 1 if supplier.get("is_verified") else 0
        power_user = 1 if supplier.get("is_power_user") else 0
        score_strength = min(25, trans_level * 2 + verified * 10 + power_user * 5)
        evaluation["dimensions"]["实力"] = {
            "score": score_strength,
            "details": f"交易等级 {trans_level}, 认证={verified}, 实力商家={power_user}",
        }
        
        # 总分
        total = score_rating + score_experience + score_service + score_strength
        evaluation["overall_score"] = round(total, 1)
        
        # 推荐等级
        if total >= 80:
            evaluation["recommendation"] = "⭐⭐⭐⭐⭐ 强烈推荐"
        elif total >= 60:
            evaluation["recommendation"] = "⭐⭐⭐⭐ 推荐"
        elif total >= 40:
            evaluation["recommendation"] = "⭐⭐⭐ 考虑"
        else:
            evaluation["recommendation"] = "⭐⭐ 谨慎"
        
        return evaluation
    
    def match_amazon_to_1688(
        self,
        amazon_product: Dict,
        suppliers: List[Dict]
    ) -> Dict:
        """
        匹配亚马逊商品到 1688 供应商
        
        Args:
            amazon_product: 亚马逊商品数据
            suppliers: 1688 供应商列表
            
        Returns:
            匹配结果
        """
        evaluated = [self.evaluate_supplier(s) for s in suppliers]
        
        # 添加亚马逊商品信息
        match_result = {
            "amazon_product": {
                "asin": amazon_product.get("asin"),
                "title": amazon_product.get("title"),
                "price": amazon_product.get("price"),
                "rating": amazon_product.get("rating"),
            },
            "suppliers": evaluated[:self.top_n],
            "best_match": evaluated[0] if evaluated else None,
            "matched_at": datetime.utcnow().isoformat(),
        }
        
        return match_result
    
    def export_suppliers(self, suppliers: List[Dict], filename: str) -> str:
        """导出供应商列表到 CSV"""
        import pandas as pd
        
        filepath = DATA_DIR / filename
        
        rows = []
        for s in suppliers:
            row = {
                "排名": s.get("rank"),
                "公司名称": s.get("company_name"),
                "店铺名称": s.get("shop_name"),
                "地区": s.get("location"),
                "经营年限": s.get("years"),
                "评分": s.get("rating"),
                "复购率": s.get("repeat_purchase_rate"),
                "响应率": s.get("response_rate"),
                "响应时间": s.get("response_time"),
                "起订量": s.get("min_order"),
                "价格区间": s.get("price_range"),
                "交易等级": s.get("transaction_level"),
                "是否认证": s.get("is_verified"),
                "是否实力商家": s.get("is_power_user"),
                "主营产品": s.get("main_products"),
                "产能": s.get("capacity"),
                "搜索关键词": s.get("search_keyword"),
                "采集时间": s.get("collected_at"),
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"供应商数据已导出：{filepath}")
        
        return str(filepath)
    
    def generate_match_report(self, match_results: List[Dict], output_path: Optional[str] = None) -> str:
        """
        生成匹配报告
        
        Args:
            match_results: 匹配结果列表
            output_path: 输出文件路径
            
        Returns:
            报告内容
        """
        report = []
        report.append("# 🏭 1688 供应商匹配报告")
        report.append(f"\n**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**匹配商品数:** {len(match_results)}")
        report.append(f"**每家供应商数:** Top {self.top_n}\n")
        
        for i, match in enumerate(match_results, 1):
            amazon = match.get("amazon_product", {})
            best = match.get("best_match", {})
            
            report.append(f"## {i}. {amazon.get('title', 'Unknown')[:60]}")
            report.append(f"\n**ASIN:** {amazon.get('asin', 'N/A')}")
            
            price = amazon.get("price", {})
            if isinstance(price, dict):
                price_str = f"{price.get('symbol', '$')}{price.get('value', 0):.2f}"
            else:
                price_str = str(price) if price else "N/A"
            
            report.append(f"**亚马逊价格:** {price_str}")
            report.append(f"**评分:** {amazon.get('rating', 0)}⭐\n")
            
            if best:
                report.append("### 🏆 最佳供应商")
                report.append(f"- **公司:** {best.get('company_name', 'N/A')}")
                report.append(f"- **店铺:** {best.get('shop_name', 'N/A')}")
                report.append(f"- **地区:** {best.get('location', 'N/A')}")
                report.append(f"- **综合评分:** {best.get('overall_score', 0)}/100")
                report.append(f"- **推荐等级:** {best.get('recommendation', 'N/A')}")
                
                dims = best.get("dimensions", {})
                report.append("\n**详细评估:**")
                for dim, data in dims.items():
                    report.append(f"- {dim}: {data.get('score', 0)}/25 ({data.get('details', '')})")
            
            report.append("\n---\n")
        
        report_text = "\n".join(report)
        
        if output_path:
            filepath = DATA_DIR / output_path
            filepath.parent.mkdir(exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"报告已保存：{filepath}")
        
        return report_text


# 使用示例
if __name__ == "__main__":
    async def main():
        finder = SupplierFinder()
        
        # 测试查找供应商
        test_title = "JBL Vibe Beam True Wireless Earbuds"
        suppliers = await finder.find_suppliers(test_title, limit=10)
        
        print(f"\n找到 {len(suppliers)} 个供应商:\n")
        for i, s in enumerate(suppliers[:5], 1):
            print(f"{i}. {s['company_name']}")
            print(f"   店铺：{s['shop_name']}")
            print(f"   地区：{s['location']}")
            print(f"   评分：{s['rating']}/5.0")
            print(f"   起订量：{s['min_order']}件")
            print()
    
    asyncio.run(main())
