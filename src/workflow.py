"""
亚马逊选品主工作流程

流程：
1. 采集亚马逊商品数据
2. 分析销售趋势
3. 筛选 Top20 潜力商品
4. 导出报告
"""
import asyncio
from datetime import datetime
from pathlib import Path
import sys

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


class AmazonSelectorWorkflow:
    """亚马逊选品工作流 (增强版)"""
    
    def __init__(self, include_suppliers: bool = True, generate_charts: bool = True):
        """
        初始化工作流
        
        Args:
            include_suppliers: 是否包含 1688 供应商匹配
            generate_charts: 是否生成可视化图表
        """
        self.collector = AmazonCollector(use_rainforest=True)
        self.analyzer = TrendAnalyzer()
        self.visualizer = TrendVisualizer() if generate_charts else None
        self.supplier_finder = SupplierFinder() if include_suppliers else None
        self.top_n_products = ANALYSIS_CONFIG["top_n_products"]
        self.top_n_suppliers = ALIBABA_CONFIG["top_n_suppliers"]
        self.generate_charts = generate_charts
        
        logger.info("亚马逊选品工作流 (增强版) 初始化完成")
        if include_suppliers:
            logger.info("1688 供应商匹配已启用")
        if generate_charts:
            logger.info("可视化图表生成已启用")
    
    async def run(
        self,
        keywords: list = None,
        load_existing: bool = False,
        existing_file: str = None
    ):
        """
        运行完整选品流程
        
        Args:
            keywords: 搜索关键词列表
            load_existing: 是否加载已有数据 (不重新采集)
            existing_file: 已有数据文件路径
        """
        logger.info("="*60)
        logger.info("🚀 亚马逊选品工作流启动")
        logger.info("="*60)
        
        # 步骤 1: 获取商品数据
        if load_existing and existing_file:
            logger.info(f"📂 加载已有数据：{existing_file}")
            import pandas as pd
            filepath = DATA_DIR / existing_file
            if filepath.exists():
                df = pd.read_csv(filepath)
                products = df.to_dict('records')
                logger.info(f"✅ 加载 {len(products)} 个商品")
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
            
            all_products = []
            for keyword in keywords:
                logger.info(f"采集：{keyword}")
                products = await self.collector.collect_product_data(
                    [keyword],
                    limit=self.top_n_products
                )
                all_products.extend(products)
                logger.info(f"  → 获取 {len(products)} 个商品")
            
            products = all_products
            logger.info(f"✅ 采集完成，共 {len(products)} 个商品")
            
            # 保存原始数据
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_file = f"raw_products_{timestamp}.csv"
            self.collector.save_to_csv(products, raw_file)
            logger.info(f"💾 原始数据已保存：{raw_file}")
        
        if not products:
            logger.error("❌ 没有商品数据，无法继续分析")
            return None
        
        # 步骤 2: 趋势分析 (增强模式)
        logger.info("📈 开始趋势分析 (增强模式)...")
        analyzed_products = self.analyzer.analyze_products(products, use_enhanced=True)
        logger.info(f"✅ 分析完成")
        
        # 步骤 3: 筛选 Top20
        logger.info(f"🏆 筛选 Top {self.top_n_products}...")
        top_products = self.analyzer.select_top_n(analyzed_products, n=self.top_n_products)
        logger.info(f"✅ 筛选完成")
        
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
            
            supplier_csv = f"suppliers_{timestamp}.csv"
            supplier_path = self.supplier_finder.export_suppliers(all_suppliers, supplier_csv)
            logger.info(f"💾 供应商 CSV: {supplier_path}")
            
            # 生成匹配报告
            supplier_report = f"supplier_match_{timestamp}.md"
            self.supplier_finder.generate_match_report(supplier_results, supplier_report)
            logger.info(f"📄 供应商报告：{supplier_report}")
        
        # 步骤 5: 导出结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 导出 CSV
        csv_file = f"top{self.top_n_products}_{timestamp}.csv"
        csv_path = self.analyzer.export_to_csv(top_products, csv_file)
        logger.info(f"💾 CSV 已导出：{csv_path}")
        
        # 生成报告 (带图表)
        report_file = f"top{self.top_n_products}_report_{timestamp}.md"
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
        }


async def main():
    """主函数"""
    workflow = AmazonSelectorWorkflow()
    
    # 运行工作流
    # 选项 1: 使用已有测试数据
    # result = await workflow.run(
    #     load_existing=True,
    #     existing_file="rainforest_search_20260327_025530.csv"
    # )
    
    # 选项 2: 重新采集数据
    result = await workflow.run(keywords=[
        "wireless earbuds",
        "phone case",
        "laptop stand",
    ])
    
    if result:
        print(f"\n✅ 完成!")
        print(f"   总商品数：{result['total_products']}")
        print(f"   Top 商品数：{len(result['top_products'])}")
        print(f"   CSV 文件：{result['csv_file']}")
        print(f"   报告文件：{result['report_file']}")


if __name__ == "__main__":
    asyncio.run(main())
