"""
亚马逊选品主工作流程 (v2.3 - 数据库集成版)

流程：
1. 采集亚马逊商品数据 (自动保存到数据库)
2. 记录历史数据 (自动)
3. 存储到数据库 (同时保留 CSV 导出 - 向后兼容)
4. 分析销售趋势
5. 筛选 Top20 潜力商品
6. 导出报告

v2.3 更新:
- 使用 collector 内置数据库保存
- 自动记录历史数据
- 添加 --use-db 命令行参数
"""
import asyncio
from datetime import datetime
from pathlib import Path
import sys
import argparse
from typing import Optional, Dict, Any, List

from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO"
)

from .amazon.collector import AmazonCollector
from .analysis.trend_analyzer import TrendAnalyzer
from .analysis.visualizer import TrendVisualizer
from ._1688.supplier_finder import SupplierFinder
from .utils.config import DATA_DIR, ANALYSIS_CONFIG, ALIBABA_CONFIG
from .db import (
    get_async_session,
    ProductRepository,
    HistoryRepository,
    init_db_async,
)


class AmazonSelectorWorkflow:
    """亚马逊选品工作流 (v2.3 - 数据库集成版)"""
    
    def __init__(
        self,
        include_suppliers: bool = True,
        generate_charts: bool = True,
        use_database: bool = True,
    ):
        """
        初始化工作流
        
        Args:
            include_suppliers: 是否包含 1688 供应商匹配
            generate_charts: 是否生成可视化图表
            use_database: 是否使用数据库存储 (默认 True)
        """
        self.use_database = use_database
        self.collector = AmazonCollector(
            use_rainforest=True,
            use_database=use_database,
        )
        self.analyzer = TrendAnalyzer()
        self.visualizer = TrendVisualizer() if generate_charts else None
        self.supplier_finder = SupplierFinder() if include_suppliers else None
        self.top_n_products = ANALYSIS_CONFIG["top_n_products"]
        self.top_n_suppliers = ALIBABA_CONFIG["top_n_suppliers"]
        self.generate_charts = generate_charts
        
        logger.info("亚马逊选品工作流 (v2.3 - 数据库集成版) 初始化完成")
        if include_suppliers:
            logger.info("1688 供应商匹配已启用")
        if generate_charts:
            logger.info("可视化图表生成已启用")
        if use_database:
            logger.info("📊 数据库存储已启用")
    
    async def _ensure_db_initialized(self):
        """确保数据库已初始化"""
        if self.use_database:
            try:
                await init_db_async()
                logger.info("✅ 数据库已就绪")
            except Exception as e:
                logger.warning(f"⚠️ 数据库初始化失败：{e}")
                logger.warning("将使用 CSV 模式运行")
                self.use_database = False
    
    @staticmethod
    def _extract_price(price_data: Any) -> float:
        """
        提取价格值 (处理多种格式)
        
        Args:
            price_data: 价格数据 (dict, str, float, int)
            
        Returns:
            价格浮点数值
        """
        if isinstance(price_data, dict):
            return float(price_data.get('value', 0.0))
        elif isinstance(price_data, str):
            if price_data.startswith('{'):
                import json
                try:
                    price_dict = json.loads(price_data.replace("'", '"'))
                    return float(price_dict.get('value', 0.0))
                except Exception as e:
                    logger.warning(f"解析价格字典失败：{e}")
                    return 0.0
            else:
                try:
                    return float(price_data.replace('$', '').replace(',', '').strip())
                except Exception as e:
                    logger.warning(f"解析价格字符串失败：{e}")
                    return 0.0
        elif isinstance(price_data, (int, float)):
            return float(price_data)
        return 0.0
    
    async def _save_to_database(
        self,
        products: List[Dict[str, Any]],
        timestamp: datetime,
    ) -> int:
        """
        保存商品数据到数据库
        
        Args:
            products: 商品数据列表
            timestamp: 时间戳
            
        Returns:
            保存的商品数量
        """
        if not self.use_database:
            return 0
        
        saved_count = 0
        try:
            async with get_async_session() as session:
                product_repo = ProductRepository(session)
                history_repo = HistoryRepository(session)
                
                for product in products:
                    try:
                        # 检查是否已存在
                        existing = await product_repo.get_by_asin(product.get('asin', ''))
                        
                        if existing:
                            # 提取价格
                            price_value = self._extract_price(product.get('price', 0.0))
                            
                            # 更新现有商品
                            await product_repo.update(
                                product.get('asin', ''),
                                price=price_value,
                                rating=product.get('rating'),
                                review_count=product.get('review_count'),
                                bsr=product.get('bsr'),
                                category=product.get('category'),
                            )
                            
                            # 记录历史
                            if product.get('asin'):
                                await history_repo.record_history(
                                    product_id=existing.id,
                                    asin=product.get('asin', ''),
                                    price=price_value,
                                    rating=product.get('rating'),
                                    review_count=product.get('review_count'),
                                    bsr=product.get('bsr'),
                                    title=product.get('title'),
                                    recorded_at=timestamp,
                                )
                        else:
                            # 创建新商品
                            price_value = self._extract_price(product.get('price', 0.0))
                            
                            await product_repo.create(
                                asin=product.get('asin', ''),
                                title=product.get('title', ''),
                                price=price_value or 0.0,
                                product_url=product.get('product_url', ''),
                                brand=product.get('brand'),
                                category=product.get('category'),
                                currency=product.get('currency', 'USD'),
                                rating=product.get('rating'),
                                review_count=product.get('review_count'),
                                bsr=product.get('bsr'),
                                image_url=product.get('image_url'),
                            )
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.warning(f"⚠️ 保存商品 {product.get('asin', 'unknown')} 失败：{e}")
                        continue
                
                logger.info(f"✅ 数据库保存完成：{saved_count} 个商品")
                
        except Exception as e:
            logger.error(f"❌ 数据库保存失败：{e}")
            logger.warning("将继续使用 CSV 模式")
        
        return saved_count
    
    async def run(
        self,
        keywords: list = None,
        load_existing: bool = False,
        existing_file: str = None,
        save_to_db: Optional[bool] = None,
    ):
        """
        运行完整选品流程
        
        Args:
            keywords: 搜索关键词列表
            load_existing: 是否加载已有数据 (不重新采集)
            existing_file: 已有数据文件路径
            save_to_db: 是否保存到数据库 (覆盖默认设置)
            
        Returns:
            工作流结果字典
        """
        # 允许覆盖数据库设置
        if save_to_db is not None:
            self.use_database = save_to_db
        
        # 确保数据库初始化
        if self.use_database:
            await self._ensure_db_initialized()
        
        logger.info("="*60)
        logger.info("🚀 亚马逊选品工作流启动 (v2.3)")
        if self.use_database:
            logger.info("📊 数据库存储：已启用 (自动保存 + 历史记录)")
        else:
            logger.info("📊 数据库存储：已禁用 (CSV 模式)")
        logger.info("="*60)
        
        timestamp = datetime.now()
        
        # 步骤 1: 获取商品数据
        if load_existing and existing_file:
            logger.info(f"📂 加载已有数据：{existing_file}")
            import pandas as pd
            filepath = DATA_DIR / existing_file
            if filepath.exists():
                df = pd.read_csv(filepath)
                products = df.to_dict('records')
                logger.info(f"✅ 加载 {len(products)} 个商品")
                
                # 如果启用数据库，保存到数据库
                if self.use_database:
                    await self.collector._save_products_to_db(products, timestamp)
            else:
                logger.error(f"文件不存在：{filepath}")
                return None
        else:
            logger.info("📦 开始采集商品数据...")
            keywords = keywords or [
                "wireless earbuds",
                "phone case",
                "laptop stand",
                "usb c cable",
                "screen protector",
                "phone charger",
                "bluetooth speaker",
                "car phone mount",
                "portable charger",
                "airpods case",
            ]
            
            # 使用 collector 的数据库集成 (自动保存 + 历史记录)
            logger.info(f"采集关键词：{', '.join(keywords)}")
            products = await self.collector.collect_product_data(
                keywords,
                limit=self.top_n_products,
                save_to_db=self.use_database,
            )
            logger.info(f"✅ 采集完成，共 {len(products)} 个商品")
            
            # 保存原始数据 (CSV - 向后兼容)
            if products:
                raw_file = f"raw_products_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
                self.collector.save_to_csv(products, raw_file)
                logger.info(f"💾 原始数据已保存：{raw_file}")
        
        if not products:
            logger.error("❌ 没有商品数据，无法继续分析")
            return None
        
        # 步骤 2: 趋势分析 (增强模式)
        logger.info("📈 开始趋势分析 (增强模式)...")
        analyzed_products = self.analyzer.analyze_products(products, use_enhanced=True)
        logger.info("✅ 分析完成")
        
        # 步骤 3: 筛选 Top20
        logger.info(f"🏆 筛选 Top {self.top_n_products}...")
        top_products = self.analyzer.select_top_n(analyzed_products, n=self.top_n_products)
        logger.info("✅ 筛选完成")
        
        # 步骤 3.5: 生成可视化图表
        charts = {}
        if self.visualizer and self.generate_charts:
            logger.info("📊 生成可视化图表...")
            charts = self.visualizer.generate_all_charts(analyzed_products, top_n=self.top_n_products)
            logger.info(f"✅ 生成 {len(charts)} 个图表")
        
        # 步骤 4: 1688 供应商匹配 (可选)
        supplier_results = None
        if self.supplier_finder:
            logger.info("🏭 开始 1688 供应商匹配...")
            supplier_results = []
            
            for product in top_products:
                suppliers = await self.supplier_finder.find_suppliers(
                    product["title"],
                    limit=self.top_n_suppliers
                )
                match = self.supplier_finder.match_amazon_to_1688(product, suppliers)
                supplier_results.append(match)
                logger.info(f"  → {product['asin']}: 匹配 {len(suppliers)} 个供应商")
            
            # 导出供应商数据
            all_suppliers = []
            for match in supplier_results:
                all_suppliers.extend(match.get("suppliers", []))
            
            supplier_csv = f"suppliers_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
            supplier_path = self.supplier_finder.export_suppliers(all_suppliers, supplier_csv)
            logger.info(f"💾 供应商 CSV: {supplier_path}")
            
            # 生成匹配报告
            supplier_report = f"supplier_match_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
            self.supplier_finder.generate_match_report(supplier_results, supplier_report)
            logger.info(f"📄 供应商报告：{supplier_report}")
        
        # 步骤 5: 导出结果
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # 导出 CSV (向后兼容)
        csv_file = f"top{self.top_n_products}_{timestamp_str}.csv"
        csv_path = self.analyzer.export_to_csv(top_products, csv_file)
        logger.info(f"💾 CSV 已导出：{csv_path}")
        
        # 生成报告 (带图表)
        report_file = f"top{self.top_n_products}_report_{timestamp_str}.md"
        report = self.analyzer.generate_report(top_products, report_file, charts=charts)
        logger.info(f"📄 报告已生成：{report_file}")
        
        # 步骤 6: 显示摘要
        logger.info("="*60)
        logger.info("🏆 Top 潜力商品摘要")
        logger.info("="*60)
        
        for i, p in enumerate(top_products[:5], 1):
            price = p.get("price", {})
            price_str = f"{price.get('symbol', '$')}{price.get('value', 0):.2f}" if price else "N/A"
            logger.info(
                f"{i}. {p['title'][:40]}... | {price_str} | "
                f"{p['rating']}⭐ | 评分：{p['trend_score']} | {p['trend_label']}"
            )
        
        logger.info("="*60)
        logger.info("✅ 选品工作流完成!")
        logger.info("="*60)
        
        return {
            "total_products": len(products),
            "top_products": top_products,
            "csv_file": csv_path,
            "report_file": report_file,
            "supplier_results": supplier_results,
            "charts": charts,
            "visualizer_enabled": self.visualizer is not None,
            "database_enabled": self.use_database,
            "timestamp": timestamp.isoformat(),
        }


async def main():
    """主函数 - 支持命令行参数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="亚马逊选品工作流 (v2.3)")
    parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        help="搜索关键词 (逗号分隔，例如：'wireless earbuds,phone case')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="每个关键词采集的商品数量 (默认：20)"
    )
    parser.add_argument(
        "--use-db",
        action="store_true",
        default=True,
        help="使用数据库存储 (默认：启用)"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="禁用数据库存储 (仅 CSV 模式)"
    )
    parser.add_argument(
        "--load-existing",
        type=str,
        default=None,
        help="加载已有 CSV 文件 (不重新采集)"
    )
    
    args = parser.parse_args()
    
    # 确定数据库设置
    use_database = not args.no_db and args.use_db
    
    # 解析关键词
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]
    
    # 创建工作流
    workflow = AmazonSelectorWorkflow(
        use_database=use_database,
        include_suppliers=True,
        generate_charts=True,
    )
    
    # 运行工作流
    if args.load_existing:
        logger.info(f"使用已有数据：{args.load_existing}")
        result = await workflow.run(
            load_existing=True,
            existing_file=args.load_existing,
            save_to_db=use_database,
        )
    else:
        # 更新 top_n_products 为命令行指定的 limit
        workflow.top_n_products = args.limit
        result = await workflow.run(
            keywords=keywords,
            save_to_db=use_database,
        )
    
    if result:
        print("\n✅ 完成!")
        print(f"   总商品数：{result['total_products']}")
        print(f"   Top 商品数：{len(result['top_products'])}")
        print(f"   CSV 文件：{result['csv_file']}")
        print(f"   报告文件：{result['report_file']}")
        if result.get('database_enabled'):
            print("   数据库存储：已启用")


if __name__ == "__main__":
    asyncio.run(main())
