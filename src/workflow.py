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
from .analysis.prophet_predictor import ProphetPredictor, quick_forecast
from .analysis.prophet_visualizer import ProphetVisualizer, quick_plot_forecast
from .analysis.lstm_predictor import LSTMPredictor, quick_lstm_forecast
from .analysis.lstm_features import create_features, create_target
from .analysis.lstm_visualizer import create_dashboard as lstm_create_dashboard
from .analysis.holidays import create_holidays_df
from .analysis.model_evaluator import create_default_evaluator, quick_model_comparison
from .analysis.model_comparison import generate_comparison_report, export_report
from ._1688.supplier_finder import SupplierFinder
from .utils.config import DATA_DIR, ANALYSIS_CONFIG, ALIBABA_CONFIG
from .db import (
    get_async_session,
    ProductRepository,
    HistoryRepository,
    init_db_async,
)


class AmazonSelectorWorkflow:
    """亚马逊选品工作流 (v2.4 Phase 2 - LSTM 深度学习预测集成版)"""
    
    def __init__(
        self,
        include_suppliers: bool = True,
        generate_charts: bool = True,
        use_database: bool = True,
        use_prophet: bool = False,
        prophet_forecast_days: int = 30,
        prophet_country_holidays: str = "US",
        use_lstm: bool = False,
        lstm_lookback: int = 60,
        lstm_forecast_days: int = 30,
        lstm_units: list = None,
    ):
        """
        初始化工作流
        
        Args:
            include_suppliers: 是否包含 1688 供应商匹配
            generate_charts: 是否生成可视化图表
            use_database: 是否使用数据库存储 (默认 True)
            use_prophet: 是否使用 Prophet 时间序列预测 (v2.4 新功能)
            prophet_forecast_days: Prophet 预测天数 (默认 30)
            prophet_country_holidays: Prophet 国家节假日代码 (默认 US)
            use_lstm: 是否使用 LSTM 深度学习预测 (v2.4 Phase 2 新功能)
            lstm_lookback: LSTM 回溯窗口 (默认 60 天)
            lstm_forecast_days: LSTM 预测天数 (默认 30 天)
            lstm_units: LSTM 每层单元数列表 (默认 [50, 25])
        """
        self.use_database = use_database
        self.use_prophet = use_prophet
        self.prophet_forecast_days = prophet_forecast_days
        self.prophet_country_holidays = prophet_country_holidays
        self.use_lstm = use_lstm
        self.lstm_lookback = lstm_lookback
        self.lstm_forecast_days = lstm_forecast_days
        self.lstm_units = lstm_units or [50, 25]
        
        self.collector = AmazonCollector(
            use_rainforest=True,
            use_database=use_database,
        )
        self.analyzer = TrendAnalyzer()
        self.visualizer = TrendVisualizer() if generate_charts else None
        self.prophet_predictor = ProphetPredictor() if use_prophet else None
        self.prophet_visualizer = ProphetVisualizer() if (use_prophet and generate_charts) else None
        self.lstm_predictor = LSTMPredictor(
            lookback=lstm_lookback,
            forecast_horizon=lstm_forecast_days,
            lstm_units=self.lstm_units,
        ) if use_lstm else None
        self.lstm_visualizer = lstm_create_dashboard if (use_lstm and generate_charts) else None
        self.supplier_finder = SupplierFinder() if include_suppliers else None
        self.top_n_products = ANALYSIS_CONFIG["top_n_products"]
        self.top_n_suppliers = ALIBABA_CONFIG["top_n_suppliers"]
        self.generate_charts = generate_charts
        
        logger.info("亚马逊选品工作流 (v2.4 Phase 2 - LSTM 深度学习预测集成版) 初始化完成")
        if include_suppliers:
            logger.info("1688 供应商匹配已启用")
        if generate_charts:
            logger.info("可视化图表生成已启用")
        if use_database:
            logger.info("📊 数据库存储已启用")
        if use_prophet:
            logger.info("🔮 Prophet 时间序列预测已启用")
            logger.info(f"   预测天数：{prophet_forecast_days}")
            logger.info(f"   节假日：{prophet_country_holidays}")
        if use_lstm:
            logger.info("🧠 LSTM 深度学习预测已启用")
            logger.info(f"   回溯窗口：{lstm_lookback}天")
            logger.info(f"   预测天数：{lstm_forecast_days}天")
            logger.info(f"   LSTM 单元：{self.lstm_units}")
    
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
    
    def _prepare_prophet_data(
        self,
        products: List[Dict[str, Any]],
        timestamp: datetime,
        days_history: int = 90,
    ) -> pd.DataFrame:
        """
        为 Prophet 准备历史数据
        
        Args:
            products: 商品数据列表
            timestamp: 当前时间戳
            days_history: 历史天数
            
        Returns:
            Prophet 格式 DataFrame (ds, y)
        """
        import pandas as pd
        import numpy as np
        
        # 从产品数据生成模拟历史数据
        # 实际使用时应该从数据库加载真实历史数据
        dates = pd.date_range(
            end=timestamp,
            periods=days_history,
            freq="D",
        )
        
        # 使用当前产品的 review_count 和 rating 估算销售
        # 这是一个简化的模拟，实际应该使用真实历史销售数据
        base_sales = np.mean([
            p.get("review_count", 100) * 0.1  # 假设评论数的 10% 作为日销量估算
            for p in products
            if isinstance(p.get("review_count"), (int, float))
        ])
        
        # 添加趋势和季节性
        trend = np.linspace(base_sales * 0.8, base_sales * 1.2, days_history)
        weekly_seasonality = 10 * np.sin(np.arange(days_history) * 2 * np.pi / 7)
        noise = np.random.randn(days_history) * 5
        
        sales = trend + weekly_seasonality + noise
        sales = np.maximum(sales, 0)  # 确保非负
        
        df = pd.DataFrame({
            "date": dates,
            "sales": sales,
        })
        
        logger.info(f"准备 Prophet 数据：{len(df)} 天，平均销量 {sales.mean():.1f}")
        return df
    
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
        
        # 步骤 3.5: Prophet 时间序列预测 (v2.4 新功能)
        prophet_results = None
        if self.use_prophet and self.prophet_predictor:
            logger.info("🔮 开始 Prophet 时间序列预测...")
            try:
                # 准备历史数据 (从 analyzed_products 提取)
                historical_df = self._prepare_prophet_data(analyzed_products, timestamp)
                
                if len(historical_df) > 10:
                    # 配置节假日
                    self.prophet_predictor.add_holidays(
                        country=self.prophet_country_holidays,
                        add_shopping_holidays=True,
                    )
                    
                    # 训练模型
                    self.prophet_predictor.train(historical_df)
                    
                    # 生成预测
                    forecast = self.prophet_predictor.predict(periods=self.prophet_forecast_days)
                    
                    # 获取评估指标
                    metrics = self.prophet_predictor.get_metrics()
                    
                    # 生成预测图
                    if self.prophet_visualizer:
                        forecast_plot = f"prophet_forecast_{timestamp_str}.png"
                        self.prophet_visualizer.plot_forecast(
                            self.prophet_predictor,
                            title="销售预测 (Prophet)",
                            save_path=forecast_plot,
                            show_plot=False,
                        )
                        charts["prophet_forecast"] = forecast_plot
                    
                    # 生成组件图
                    components_plot = f"prophet_components_{timestamp_str}.png"
                    self.prophet_visualizer.plot_components(
                        self.prophet_predictor,
                        title="预测组件分析",
                        save_path=components_plot,
                        show_plot=False,
                    )
                    charts["prophet_components"] = components_plot
                    
                    prophet_results = {
                        "forecast": forecast,
                        "metrics": metrics,
                        "forecast_days": self.prophet_forecast_days,
                        "mape": metrics.get("mape", 0),
                    }
                    
                    logger.info(f"✅ Prophet 预测完成 (MAPE: {metrics.get('mape', 0):.2f}%)")
                else:
                    logger.warning("⚠️ 历史数据不足，跳过 Prophet 预测")
            except Exception as e:
                logger.warning(f"⚠️ Prophet 预测失败：{e}")
                prophet_results = None
        
        # 步骤 3.5b: LSTM 深度学习预测 (v2.4 Phase 2 新功能)
        lstm_results = None
        if self.use_lstm and self.lstm_predictor:
            logger.info("🧠 开始 LSTM 深度学习预测...")
            try:
                # 准备历史数据
                historical_df = self._prepare_prophet_data(analyzed_products, timestamp)
                
                if len(historical_df) > self.lstm_lookback:
                    # 创建特征
                    features_df = create_features(
                        historical_df,
                        target_col="sales",
                        date_col="date",
                    )
                    
                    # 准备 LSTM 数据
                    sales_data = features_df["sales"].values
                    
                    # 快速 LSTM 预测
                    predictions, metrics = quick_lstm_forecast(
                        sales_data,
                        forecast_days=self.lstm_forecast_days,
                        lookback=self.lstm_lookback,
                        verbose=True,
                    )
                    
                    # 生成预测日期
                    forecast_dates = pd.date_range(
                        start=timestamp + pd.Timedelta(days=1),
                        periods=self.lstm_forecast_days,
                        freq="D",
                    )
                    
                    # 生成预测 DataFrame
                    lstm_forecast = pd.DataFrame({
                        "date": forecast_dates,
                        "predicted_sales": predictions,
                    })
                    
                    # 生成可视化
                    if self.lstm_visualizer:
                        # 创建仪表板
                        dashboard_path = f"lstm_dashboard_{timestamp_str}.png"
                        history_dict = self.lstm_predictor.history.history if self.lstm_predictor.history else {}
                        
                        fig = self.lstm_visualizer(
                            y_true=sales_data[-len(predictions):],
                            y_pred=predictions,
                            history=history_dict,
                            metrics=metrics,
                            dates=forecast_dates,
                            save_path=dashboard_path,
                            show=False,
                        )
                        import matplotlib.pyplot as plt
                        plt.close(fig)
                        charts["lstm_dashboard"] = dashboard_path
                    
                    lstm_results = {
                        "forecast": lstm_forecast,
                        "metrics": metrics,
                        "forecast_days": self.lstm_forecast_days,
                        "mape": metrics.get("MAPE", 0),
                    }
                    
                    logger.info(f"✅ LSTM 预测完成 (MAPE: {metrics.get('MAPE', 0):.2f}%)")
                else:
                    logger.warning(
                        f"⚠️ 历史数据不足 (需要>{self.lstm_lookback}天，实际{len(historical_df)}天)，跳过 LSTM 预测"
                    )
            except Exception as e:
                logger.warning(f"⚠️ LSTM 预测失败：{e}")
                import traceback
                logger.debug(traceback.format_exc())
                lstm_results = None
        
        # 步骤 3.6: 生成可视化图表
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
            "prophet_enabled": self.use_prophet,
            "prophet_results": prophet_results,
            "lstm_enabled": self.use_lstm,
            "lstm_results": lstm_results,
            "timestamp": timestamp.isoformat(),
        }
    
    def run_model_comparison(self, days: int = 30, export_path: str = None) -> Dict[str, Any]:
        """
        运行多模型对比分析 (v2.4 Phase 3 新功能)
        
        Args:
            days: 预测天数
            export_path: 报告导出路径 (可选)
            
        Returns:
            对比结果字典
        """
        logger.info("="*60)
        logger.info("🔬 开始多模型对比分析 (v2.4 Phase 3)")
        logger.info("="*60)
        
        try:
            # 生成样本数据用于对比
            import numpy as np
            np.random.seed(42)
            
            dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
            trend = np.linspace(100, 150, 90)
            weekly = 10 * np.sin(np.arange(90) * 2 * np.pi / 7)
            yearly = 20 * np.sin(np.arange(90) * 2 * np.pi / 365)
            noise = np.random.randn(90) * 5
            sales = trend + weekly + yearly + noise
            
            data = pd.DataFrame({
                'date': dates,
                'sales': np.maximum(sales, 0),
            })
            
            # 划分训练/测试集
            train_data = data.iloc[:-days].copy()
            test_data = data.iloc[-days:].copy()
            
            # 创建评估器
            logger.info("创建模型评估器 (线性/Prophet/LSTM)...")
            evaluator = create_default_evaluator()
            
            # 训练所有模型
            logger.info("训练所有模型...")
            evaluator.train_all(train_data, target_col='sales')
            
            # 预测
            logger.info(f"预测未来 {days} 天...")
            evaluator.predict_all(test_data, periods=days)
            
            # 评估
            y_true = test_data['sales'].values
            metrics_df = evaluator.evaluate_all(y_true)
            
            # 显示结果
            logger.info("="*60)
            logger.info("📊 模型对比结果")
            logger.info("="*60)
            print(metrics_df.to_string())
            
            # 最佳模型
            best_model = evaluator.get_best_model('MAPE')
            logger.info(f"🏆 最佳模型 (MAPE): {best_model}")
            
            # 生成报告
            result = {
                'metrics_df': metrics_df,
                'best_model': best_model,
                'evaluator': evaluator,
                'metrics': evaluator.metrics_results,
                'train_times': evaluator.train_times,
                'predict_times': evaluator.predict_times,
            }
            
            # 导出报告
            if export_path:
                logger.info(f"导出报告到：{export_path}")
                report = generate_comparison_report(evaluator)
                
                if export_path.endswith('.md'):
                    export_report(report, export_path, format='markdown')
                else:
                    export_report(report, export_path, format='json')
                
                logger.info(f"✅ 报告已导出：{export_path}")
            
            # 生成可视化
            if self.generate_charts:
                from analysis.comparison_visualizer import create_all_visualizations
                import tempfile
                
                output_dir = Path(tempfile.gettempdir()) / 'model_comparison'
                output_dir.mkdir(parents=True, exist_ok=True)
                
                metrics_df_for_viz = pd.DataFrame(evaluator.metrics_results).T
                files = create_all_visualizations(
                    metrics_df=metrics_df_for_viz,
                    y_true=y_true,
                    predictions_dict=evaluator.y_pred_dict,
                    train_times=evaluator.train_times,
                    predict_times=evaluator.predict_times,
                    output_dir=str(output_dir),
                )
                
                logger.info(f"📈 可视化图表已生成：{len(files)} 个")
                result['visualization_files'] = files
            
            logger.info("="*60)
            logger.info("✅ 多模型对比分析完成!")
            logger.info("="*60)
            
            return result
            
        except Exception as e:
            logger.error(f"模型对比失败：{e}", exc_info=True)
            return {'error': str(e)}


async def main():
    """主函数 - 支持命令行参数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="亚马逊选品工作流 (v2.4 - Prophet 预测)")
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
    parser.add_argument(
        "--use-prophet",
        action="store_true",
        default=False,
        help="启用 Prophet 时间序列预测 (v2.4 新功能)"
    )
    parser.add_argument(
        "--prophet-days",
        type=int,
        default=30,
        help="Prophet 预测天数 (默认：30)"
    )
    parser.add_argument(
        "--prophet-country",
        type=str,
        default="US",
        help="Prophet 国家节假日代码 (默认：US)"
    )
    parser.add_argument(
        "--use-lstm",
        action="store_true",
        default=False,
        help="启用 LSTM 深度学习预测 (v2.4 Phase 2 新功能)"
    )
    parser.add_argument(
        "--lstm-lookback",
        type=int,
        default=60,
        help="LSTM 回溯窗口天数 (默认：60)"
    )
    parser.add_argument(
        "--lstm-days",
        type=int,
        default=30,
        help="LSTM 预测天数 (默认：30)"
    )
    parser.add_argument(
        "--compare-models",
        action="store_true",
        default=False,
        help="启用多模型对比分析 (v2.4 Phase 3 新功能)"
    )
    parser.add_argument(
        "--compare-days",
        type=int,
        default=30,
        help="模型对比预测天数 (默认：30)"
    )
    parser.add_argument(
        "--export-report",
        type=str,
        default=None,
        help="导出对比报告路径 (JSON/Markdown)"
    )
    parser.add_argument(
        "--ensemble",
        action="store_true",
        default=False,
        help="启用集成预测 (v2.4 Phase 4 新功能)"
    )
    parser.add_argument(
        "--ensemble-method",
        type=str,
        default="weighted",
        choices=["weighted", "stacking"],
        help="集成方法：weighted (加权平均) 或 stacking (元学习器)"
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        default=False,
        help="使用预测管道 (v2.4 Phase 4 新功能)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/",
        help="预测结果输出目录 (默认：results/)"
    )
    parser.add_argument(
        "--optimize-weights",
        action="store_true",
        default=True,
        help="优化集成模型权重"
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
        use_prophet=args.use_prophet,
        prophet_forecast_days=args.prophet_days,
        prophet_country_holidays=args.prophet_country,
        use_lstm=args.use_lstm,
        lstm_lookback=args.lstm_lookback,
        lstm_forecast_days=args.lstm_days,
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
    
    # 模型对比分析 (v2.4 Phase 3)
    if args.compare_models:
        logger.info("\n" + "="*60)
        logger.info("🔬 启动多模型对比分析 (Phase 3)")
        logger.info("="*60)
        
        compare_result = workflow.run_model_comparison(
            days=args.compare_days,
            export_path=args.export_report,
        )
        
        if compare_result and 'error' not in compare_result:
            print("\n🏆 模型对比结果:")
            print(f"   最佳模型：{compare_result.get('best_model', 'N/A')}")
            print(f"   评估模型数：{len(compare_result.get('metrics', {}))}")
            if compare_result.get('visualization_files'):
                print(f"   可视化图表：{len(compare_result['visualization_files'])} 个")
    
    # 集成预测 (v2.4 Phase 4)
    if args.ensemble:
        logger.info("\n" + "="*60)
        logger.info("🔧 启动集成预测 (Phase 4)")
        logger.info("="*60)
        
        try:
            from analysis.ensemble_predictor import EnsemblePredictor, quick_ensemble_forecast
            
            # 准备数据
            logger.info("准备集成预测数据...")
            
            # 从数据库或文件加载数据
            from db import HistoryRepository, get_async_session
            import asyncio
            
            async def load_data_for_ensemble():
                session = await get_async_session()
                repo = HistoryRepository(session)
                history = await repo.get_all_history(limit=500)
                await session.close()
                return history
            
            history_data = asyncio.run(load_data_for_ensemble())
            
            if history_data and len(history_data) > 0:
                # 转换为 DataFrame
                df = pd.DataFrame([{
                    'date': h.date,
                    'sales': h.sales,
                    'asin': h.asin
                } for h in history_data if hasattr(h, '__dict__')])
                
                if len(df) > 100:
                    logger.info(f"加载历史数据：{len(df)} 条记录")
                    
                    # 按 ASIN 分组预测
                    unique_asins = df['asin'].unique()[:5]  # 限制为前 5 个 ASIN
                    
                    for asin in unique_asins:
                        asin_data = df[df['asin'] == asin].copy()
                        asin_data = asin_data.sort_values('date')
                        
                        # 添加滞后特征
                        asin_data['lag_1'] = asin_data['sales'].shift(1)
                        asin_data['lag_7'] = asin_data['sales'].shift(7)
                        asin_data = asin_data.dropna()
                        
                        if len(asin_data) < 50:
                            continue
                        
                        logger.info(f"\n  处理 ASIN: {asin}")
                        
                        # 创建简单模型进行集成
                        from sklearn.linear_model import LinearRegression
                        from sklearn.ensemble import RandomForestRegressor
                        
                        X = asin_data[['lag_1', 'lag_7']].values
                        y = asin_data['sales'].values
                        
                        split_idx = int(len(X) * 0.8)
                        X_train, X_val = X[:split_idx], X[split_idx:]
                        y_train, y_val = y[:split_idx], y[split_idx:]
                        
                        # 训练基模型
                        model1 = LinearRegression()
                        model1.fit(X_train, y_train)
                        
                        model2 = RandomForestRegressor(n_estimators=20, max_depth=5, random_state=42)
                        model2.fit(X_train, y_train)
                        
                        models = {
                            'linear': model1,
                            'random_forest': model2
                        }
                        
                        # 创建集成预测器
                        predictor = EnsemblePredictor(models=models)
                        
                        # 优化权重
                        if args.optimize_weights:
                            val_df = asin_data.iloc[split_idx:].copy()
                            predictor.get_optimal_weights(val_df, target_column='sales')
                        
                        # 训练 Stacking (如果需要)
                        if args.ensemble_method == 'stacking':
                            predictor.fit_stacking(X_train, y_train, n_folds=3)
                        
                        # 预测
                        if args.ensemble_method == 'stacking':
                            forecast = predictor.predict_stacking(X_val)
                        else:
                            forecast = predictor.predict_weighted(X_val)
                        
                        # 评估
                        metrics = predictor.evaluate(y_val, forecast)
                        
                        logger.info(f"  ✓ {asin} - MAPE: {metrics['mape']:.2f}%")
                        logger.info(f"    权重：{predictor.weights}")
                else:
                    logger.warning("数据量不足，跳过集成预测")
            else:
                logger.warning("未找到历史数据，跳过集成预测")
        
        except Exception as e:
            logger.error(f"集成预测失败：{e}", exc_info=True)
    
    # 预测管道 (v2.4 Phase 4)
    if args.pipeline:
        logger.info("\n" + "="*60)
        logger.info("📦 启动预测管道 (Phase 4)")
        logger.info("="*60)
        
        try:
            from analysis.predict_pipeline import PredictionPipeline, PredictionConfig
            
            # 创建配置
            config = PredictionConfig(
                models=['prophet', 'lstm'] if args.use_lstm else ['prophet'],
                ensemble_method=args.ensemble_method,
                prophet_forecast_days=args.prophet_days,
                lstm_forecast_days=args.lstm_days,
                optimize_weights=args.optimize_weights,
                results_dir=args.output,
                generate_charts=True,
                save_results=True
            )
            
            # 创建管道
            pipeline = PredictionPipeline(config)
            
            # 从数据库加载 ASIN 列表
            from db import ProductRepository, get_async_session
            import asyncio
            
            async def get_asins():
                session = await get_async_session()
                repo = ProductRepository(session)
                products = await repo.get_all_products(limit=10)
                await session.close()
                return [p.asin for p in products if hasattr(p, 'asin')]
            
            asins = asyncio.run(get_asins())
            
            if asins:
                logger.info(f"找到 {len(asins)} 个 ASIN")
                
                # 运行批量预测
                results = pipeline.run_batch(asins[:3])  # 限制为前 3 个
                
                # 生成摘要报告
                report = pipeline.get_summary_report(results)
                
                # 保存报告
                report_path = Path(args.output) / "pipeline_summary.md"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(report_path, 'w') as f:
                    f.write(report)
                
                logger.info(f"\n✅ 预测管道完成")
                logger.info(f"   报告已保存：{report_path}")
                logger.info(f"   结果目录：{args.output}")
            else:
                logger.warning("未找到 ASIN，跳过预测管道")
        
        except Exception as e:
            logger.error(f"预测管道失败：{e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
