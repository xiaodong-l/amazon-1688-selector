"""
预测管道模块 (v2.4.0 Phase 4)

功能:
1. 完整预测流程自动化
2. 多模型预测与比较
3. 结果保存与可视化
4. 模型缓存与加载

使用场景:
- 批量预测多个 ASIN
- 自动化预测任务
- 生产环境部署

作者：GongBu ShangShu
版本：v2.4.0 Phase 4
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import pickle
import hashlib
from dataclasses import dataclass, asdict
import warnings
import time

from loguru import logger

# 配置日志
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO"
)

# 导入相关模块
from .prophet_predictor import ProphetPredictor
from .lstm_predictor import LSTMPredictor
from .ensemble_predictor import EnsemblePredictor
from .model_evaluator import ModelEvaluator
from .visualizer import TrendVisualizer
from .prophet_visualizer import ProphetVisualizer
from .lstm_visualizer import create_dashboard as lstm_create_dashboard


@dataclass
class PredictionConfig:
    """预测配置数据类"""
    # 数据配置
    data_dir: str = "data"
    cache_dir: str = "cache/models"
    results_dir: str = "results"
    
    # 模型配置
    models: List[str] = None  # ['prophet', 'lstm']
    ensemble_method: str = "weighted"  # 'weighted' or 'stacking'
    
    # Prophet 配置
    prophet_forecast_days: int = 30
    prophet_country_holidays: str = "US"
    prophet_seasonality_mode: str = "additive"
    
    # LSTM 配置
    lstm_lookback: int = 60
    lstm_forecast_days: int = 30
    lstm_units: List[int] = None  # [50, 25]
    lstm_dropout: float = 0.2
    lstm_epochs: int = 50
    lstm_batch_size: int = 32
    
    # 集成配置
    optimize_weights: bool = True
    validation_split: float = 0.2
    
    # 输出配置
    generate_charts: bool = True
    save_results: bool = True
    verbose: bool = True
    
    def __post_init__(self):
        if self.models is None:
            self.models = ['prophet', 'lstm']
        if self.lstm_units is None:
            self.lstm_units = [50, 25]
        
        # 创建目录
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.results_dir).mkdir(parents=True, exist_ok=True)


@dataclass
class PredictionResult:
    """预测结果数据类"""
    asin: str
    timestamp: str
    model_name: str
    forecast: List[float]
    forecast_dates: List[str]
    metrics: Dict[str, float]
    actual_values: Optional[List[float]] = None
    confidence_interval_lower: Optional[List[float]] = None
    confidence_interval_upper: Optional[List[float]] = None
    chart_paths: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self, path: str) -> None:
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


class PredictionPipeline:
    """
    预测管道 - 自动化完整预测流程
    
    流程:
    1. 加载历史数据
    2. 数据预处理
    3. 多模型预测
    4. 模型选择/集成
    5. 结果可视化
    6. 保存结果
    
    Attributes:
        config: 预测配置
        models: 已加载的模型字典
        results: 预测结果缓存
    """
    
    def __init__(self, config: Optional[PredictionConfig] = None):
        """
        初始化预测管道
        
        Args:
            config: 预测配置，如果为 None 则使用默认配置
        """
        self.config = config or PredictionConfig()
        self.models: Dict[str, Any] = {}
        self.results: Dict[str, PredictionResult] = {}
        self.data_cache: Dict[str, pd.DataFrame] = {}
        
        logger.info(f"预测管道初始化完成")
        logger.info(f"配置：{len(self.config.models)} 个模型，预测 {self.config.prophet_forecast_days} 天")
    
    def run(
        self,
        asin: str,
        models: Optional[List[str]] = None,
        historical_data: Optional[pd.DataFrame] = None,
        force_retrain: bool = False
    ) -> Dict[str, Any]:
        """
        运行完整预测流程
        
        Args:
            asin: 商品 ASIN
            models: 要使用的模型列表，如果为 None 则使用配置中的模型
            historical_data: 历史数据，如果为 None 则从文件加载
            force_retrain: 是否强制重新训练模型
        
        Returns:
            预测结果字典
        """
        start_time = time.time()
        models = models or self.config.models
        
        logger.info(f"\n{'='*60}")
        logger.info(f"启动预测管道 - ASIN: {asin}")
        logger.info(f"{'='*60}")
        logger.info(f"使用模型：{models}")
        
        # Step 1: 加载历史数据
        logger.info("\n[Step 1/6] 加载历史数据...")
        if historical_data is None:
            data = self._load_historical_data(asin)
        else:
            data = historical_data.copy()
        
        if data is None or len(data) == 0:
            logger.error(f"未找到 ASIN {asin} 的历史数据")
            return {'error': 'No historical data found'}
        
        logger.info(f"数据加载完成：{len(data)} 条记录")
        
        # Step 2: 数据预处理
        logger.info("\n[Step 2/6] 数据预处理...")
        data_processed = self._preprocess_data(data)
        logger.info(f"预处理完成：{len(data_processed)} 条记录")
        
        # Step 3: 多模型预测
        logger.info("\n[Step 3/6] 多模型预测...")
        model_predictions = {}
        
        for model_name in models:
            logger.info(f"\n  处理模型：{model_name}")
            try:
                if model_name == 'prophet':
                    pred_result = self._run_prophet(asin, data_processed, force_retrain)
                elif model_name == 'lstm':
                    pred_result = self._run_lstm(asin, data_processed, force_retrain)
                else:
                    logger.warning(f"未知模型：{model_name}")
                    continue
                
                if pred_result and 'error' not in pred_result:
                    model_predictions[model_name] = pred_result
                    logger.info(f"  ✓ {model_name} 预测完成 (MAPE: {pred_result['metrics'].get('mape', 'N/A'):.2f}%)")
            except Exception as e:
                logger.error(f"  ✗ {model_name} 预测失败：{str(e)}")
                model_predictions[model_name] = {'error': str(e)}
        
        if len(model_predictions) == 0:
            return {'error': 'All models failed'}
        
        # Step 4: 模型选择/集成
        logger.info("\n[Step 4/6] 模型集成...")
        if len(model_predictions) > 1 and self.config.ensemble_method:
            ensemble_result = self._run_ensemble(asin, data_processed, model_predictions)
            if ensemble_result and 'error' not in ensemble_result:
                model_predictions['ensemble'] = ensemble_result
                logger.info(f"  ✓ 集成预测完成 (MAPE: {ensemble_result['metrics'].get('mape', 'N/A'):.2f}%)")
        
        # Step 5: 结果可视化
        if self.config.generate_charts:
            logger.info("\n[Step 5/6] 生成可视化图表...")
            for model_name, pred_result in model_predictions.items():
                if 'error' not in pred_result:
                    self._generate_visualizations(asin, model_name, pred_result, data_processed)
        
        # Step 6: 保存结果
        if self.config.save_results:
            logger.info("\n[Step 6/6] 保存结果...")
            self._save_results(asin, model_predictions)
        
        elapsed_time = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"预测管道完成 - 总耗时：{elapsed_time:.2f} 秒")
        logger.info(f"{'='*60}")
        
        # 返回最佳结果
        best_model = self._select_best_model(model_predictions)
        return {
            'asin': asin,
            'predictions': model_predictions,
            'best_model': best_model,
            'elapsed_time': elapsed_time
        }
    
    def _load_historical_data(self, asin: str) -> Optional[pd.DataFrame]:
        """加载历史数据"""
        # 检查缓存
        cache_key = f"data_{asin}"
        if cache_key in self.data_cache:
            logger.debug(f"使用缓存数据：{asin}")
            return self.data_cache[cache_key]
        
        # 尝试从文件加载
        data_paths = [
            Path(self.config.data_dir) / f"{asin}_history.csv",
            Path(self.config.data_dir) / f"{asin}_sales.csv",
            Path("data") / f"{asin}_history.csv",
            Path("data") / f"products_{asin}.csv",
        ]
        
        for data_path in data_paths:
            if data_path.exists():
                logger.info(f"从文件加载数据：{data_path}")
                data = pd.read_csv(data_path)
                self.data_cache[cache_key] = data
                return data
        
        # 尝试从数据库加载 (如果有)
        try:
            from ..db import HistoryRepository, get_async_session
            import asyncio
            
            async def load_from_db():
                session = await get_async_session()
                repo = HistoryRepository(session)
                history = await repo.get_history_by_asin(asin)
                await session.close()
                return history
            
            data = asyncio.run(load_from_db())
            if data is not None and len(data) > 0:
                logger.info(f"从数据库加载数据：{len(data)} 条记录")
                df = pd.DataFrame([h.__dict__ for h in data if hasattr(h, '__dict__')])
                self.data_cache[cache_key] = df
                return df
        except Exception as e:
            logger.debug(f"数据库加载失败：{str(e)}")
        
        logger.warning(f"未找到 ASIN {asin} 的历史数据")
        return None
    
    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """数据预处理"""
        df = data.copy()
        
        # 标准化列名
        column_mapping = {
            'date': 'date',
            'Date': 'date',
            'DATE': 'date',
            'sales': 'sales',
            'Sales': 'sales',
            'SALES': 'sales',
            'revenue': 'revenue',
            'Revenue': 'revenue',
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        # 确保日期列是 datetime 类型
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
        
        # 处理缺失值
        if 'sales' in df.columns:
            df['sales'] = df['sales'].fillna(method='ffill').fillna(method='bfill')
        
        # 添加时间特征
        if 'date' in df.columns:
            df['day_of_week'] = df['date'].dt.dayofweek
            df['day_of_month'] = df['date'].dt.day
            df['month'] = df['date'].dt.month
            df['year'] = df['date'].dt.year
            df['week_of_year'] = df['date'].dt.isocalendar().week
        
        # 添加滞后特征 (用于 LSTM)
        if 'sales' in df.columns and len(df) > self.config.lstm_lookback:
            for lag in [1, 7, 14, 30]:
                df[f'sales_lag_{lag}'] = df['sales'].shift(lag)
            
            # 移动平均
            df['sales_ma_7'] = df['sales'].rolling(window=7).mean()
            df['sales_ma_30'] = df['sales'].rolling(window=30).mean()
        
        # 删除包含 NaN 的行
        df = df.dropna().reset_index(drop=True)
        
        return df
    
    def _run_prophet(
        self,
        asin: str,
        data: pd.DataFrame,
        force_retrain: bool = False
    ) -> Optional[Dict[str, Any]]:
        """运行 Prophet 预测"""
        # 检查缓存
        cache_path = Path(self.config.cache_dir) / f"prophet_{asin}.pkl"
        
        if not force_retrain and cache_path.exists():
            logger.info(f"  加载缓存的 Prophet 模型")
            with open(cache_path, 'rb') as f:
                predictor = pickle.load(f)
        else:
            # 创建并训练新模型
            logger.info(f"  训练 Prophet 模型...")
            predictor = ProphetPredictor(
                country_holidays=self.config.prophet_country_holidays,
                seasonality_mode=self.config.prophet_seasonality_mode
            )
            
            # 准备 Prophet 格式数据
            prophet_data = data[['date', 'sales']].copy()
            prophet_data.columns = ['ds', 'y']
            
            predictor.fit(prophet_data)
            
            # 缓存模型
            self._cache_model('prophet', asin, predictor)
        
        # 生成预测
        forecast_days = self.config.prophet_forecast_days
        forecast = predictor.predict_forecast(periods=forecast_days)
        
        if forecast is None:
            return {'error': 'Prophet prediction failed'}
        
        # 计算指标
        if 'y' in forecast.columns and 'yhat' in forecast.columns:
            # 如果有实际值，计算 MAPE
            mask = forecast['y'].notna()
            if mask.any():
                mape = np.mean(np.abs((forecast.loc[mask, 'y'] - forecast.loc[mask, 'yhat']) / 
                                      (forecast.loc[mask, 'y'] + 1e-8))) * 100
            else:
                mape = 0.0
        else:
            mape = 0.0
        
        # 准备结果
        result = {
            'model': 'prophet',
            'forecast': forecast['yhat'].tail(forecast_days).values.tolist(),
            'forecast_dates': forecast['ds'].tail(forecast_days).dt.strftime('%Y-%m-%d').tolist(),
            'metrics': {'mape': mape},
            'confidence_interval_lower': forecast.get('yhat_lower', forecast['yhat']).tail(forecast_days).values.tolist(),
            'confidence_interval_upper': forecast.get('yhat_upper', forecast['yhat']).tail(forecast_days).values.tolist(),
        }
        
        return result
    
    def _run_lstm(
        self,
        asin: str,
        data: pd.DataFrame,
        force_retrain: bool = False
    ) -> Optional[Dict[str, Any]]:
        """运行 LSTM 预测"""
        # 检查缓存
        cache_path = Path(self.config.cache_dir) / f"lstm_{asin}.pkl"
        
        if not force_retrain and cache_path.exists():
            logger.info(f"  加载缓存的 LSTM 模型")
            with open(cache_path, 'rb') as f:
                predictor = pickle.load(f)
        else:
            # 创建并训练新模型
            logger.info(f"  训练 LSTM 模型...")
            predictor = LSTMPredictor(
                lookback=self.config.lstm_lookback,
                forecast_days=self.config.lstm_forecast_days,
                units=self.config.lstm_units,
                dropout=self.config.lstm_dropout
            )
            
            # 准备 LSTM 特征
            if 'sales' not in data.columns:
                return {'error': 'No sales column in data'}
            
            feature_cols = ['sales']
            feature_data = data[feature_cols].values
            
            # 创建特征和目标
            from .lstm_features import create_features, create_target
            X, y = create_features(feature_data, self.config.lstm_lookback)
            
            # 划分训练集
            split_idx = int(len(X) * (1 - self.config.validation_split))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            # 训练模型
            predictor.fit(
                X_train, y_train,
                epochs=self.config.lstm_epochs,
                batch_size=self.config.lstm_batch_size,
                validation_data=(X_val, y_val) if len(X_val) > 0 else None
            )
            
            # 缓存模型
            self._cache_model('lstm', asin, predictor)
        
        # 生成预测
        try:
            forecast = predictor.predict(data)
            
            if forecast is None or len(forecast) == 0:
                return {'error': 'LSTM prediction failed'}
            
            # 计算指标
            mape = 0.0  # LSTM 预测通常没有实际值对比
            
            result = {
                'model': 'lstm',
                'forecast': forecast.tolist() if hasattr(forecast, 'tolist') else list(forecast),
                'forecast_dates': self._generate_future_dates(self.config.lstm_forecast_days),
                'metrics': {'mape': mape},
            }
            
            return result
        except Exception as e:
            logger.error(f"  LSTM 预测失败：{str(e)}")
            return {'error': str(e)}
    
    def _run_ensemble(
        self,
        asin: str,
        data: pd.DataFrame,
        model_predictions: Dict[str, Dict]
    ) -> Optional[Dict[str, Any]]:
        """运行集成预测"""
        # 过滤掉有错误的模型
        valid_models = {k: v for k, v in model_predictions.items() if 'error' not in v}
        
        if len(valid_models) < 2:
            logger.warning(f"  集成需要至少 2 个有效模型，当前只有 {len(valid_models)} 个")
            return {'error': 'Not enough valid models for ensemble'}
        
        # 创建集成预测器 (使用简化的方式)
        # 实际应用中应该训练真正的集成模型
        forecasts = []
        weights = []
        
        for model_name, pred in valid_models.items():
            forecasts.append(np.array(pred['forecast']))
            # 基于 MAPE 分配权重 (MAPE 越低权重越高)
            mape = pred['metrics'].get('mape', 10.0)
            weight = 1.0 / (mape + 1.0)  # 避免除以零
            weights.append(weight)
        
        # 归一化权重
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        # 加权平均
        ensemble_forecast = np.average(forecasts, axis=0, weights=weights)
        
        # 计算集成 MAPE (估计值)
        ensemble_mape = np.average(
            [valid_models[k]['metrics'].get('mape', 10.0) for k in valid_models.keys()],
            weights=weights
        )
        
        # 使用第一个模型的日期
        first_model = list(valid_models.keys())[0]
        forecast_dates = valid_models[first_model]['forecast_dates']
        
        result = {
            'model': 'ensemble',
            'forecast': ensemble_forecast.tolist(),
            'forecast_dates': forecast_dates,
            'metrics': {'mape': ensemble_mape},
            'weights': {k: float(w) for k, w in zip(valid_models.keys(), weights)},
        }
        
        return result
    
    def _generate_future_dates(self, days: int) -> List[str]:
        """生成未来日期列表"""
        dates = []
        today = datetime.now()
        for i in range(days):
            date = today + timedelta(days=i+1)
            dates.append(date.strftime('%Y-%m-%d'))
        return dates
    
    def _generate_visualizations(
        self,
        asin: str,
        model_name: str,
        pred_result: Dict,
        data: pd.DataFrame
    ) -> List[str]:
        """生成可视化图表"""
        chart_paths = []
        
        try:
            # 创建图表目录
            chart_dir = Path(self.config.results_dir) / "charts" / asin
            chart_dir.mkdir(parents=True, exist_ok=True)
            
            if model_name == 'prophet':
                # Prophet 可视化
                viz = ProphetVisualizer()
                
                # 预测图
                forecast_df = pd.DataFrame({
                    'ds': pred_result['forecast_dates'],
                    'yhat': pred_result['forecast']
                })
                
                chart_path = str(chart_dir / f"prophet_forecast_{asin}.png")
                viz.plot_forecast(forecast_df, output_path=chart_path)
                chart_paths.append(chart_path)
                
            elif model_name == 'lstm':
                # LSTM 可视化
                forecast_values = pred_result['forecast']
                dates = pred_result['forecast_dates']
                
                forecast_df = pd.DataFrame({
                    'date': pd.to_datetime(dates),
                    'forecast': forecast_values
                })
                
                # 使用通用可视化器
                viz = TrendVisualizer()
                chart_path = str(chart_dir / f"lstm_forecast_{asin}.png")
                
                # 简单折线图
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(forecast_df['date'], forecast_df['forecast'], label='LSTM Forecast')
                ax.set_xlabel('Date')
                ax.set_ylabel('Sales')
                ax.set_title(f'LSTM Sales Forecast - {asin}')
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(chart_path, dpi=150)
                plt.close()
                chart_paths.append(chart_path)
                
            elif model_name == 'ensemble':
                # 集成可视化
                forecast_values = pred_result['forecast']
                dates = pred_result['forecast_dates']
                weights = pred_result.get('weights', {})
                
                forecast_df = pd.DataFrame({
                    'date': pd.to_datetime(dates),
                    'forecast': forecast_values
                })
                
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(forecast_df['date'], forecast_df['forecast'], label='Ensemble Forecast', linewidth=2)
                
                # 显示权重
                weight_text = ', '.join([f"{k}: {v:.2f}" for k, v in weights.items()])
                ax.text(0.02, 0.98, f"Weights: {weight_text}", transform=ax.transAxes,
                       fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                
                ax.set_xlabel('Date')
                ax.set_ylabel('Sales')
                ax.set_title(f'Ensemble Sales Forecast - {asin}')
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(chart_path, dpi=150)
                plt.close()
                chart_paths.append(str(chart_dir / f"ensemble_forecast_{asin}.png"))
            
            logger.info(f"  生成图表：{len(chart_paths)} 个")
            
        except Exception as e:
            logger.warning(f"  可视化生成失败：{str(e)}")
        
        return chart_paths
    
    def _save_results(self, asin: str, predictions: Dict[str, Dict]) -> None:
        """保存预测结果"""
        results_dir = Path(self.config.results_dir) / asin
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存为 JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = results_dir / f"predictions_{timestamp}.json"
        
        results_data = {
            'asin': asin,
            'timestamp': datetime.now().isoformat(),
            'config': self.config.to_dict() if hasattr(self.config, 'to_dict') else asdict(self.config),
            'predictions': predictions
        }
        
        with open(json_path, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        logger.info(f"  结果已保存：{json_path}")
        
        # 保存为 CSV
        for model_name, pred in predictions.items():
            if 'error' not in pred:
                csv_df = pd.DataFrame({
                    'date': pred['forecast_dates'],
                    'forecast': pred['forecast'],
                    'model': model_name
                })
                
                if 'confidence_interval_lower' in pred:
                    csv_df['ci_lower'] = pred['confidence_interval_lower']
                    csv_df['ci_upper'] = pred['confidence_interval_upper']
                
                csv_path = results_dir / f"{model_name}_forecast_{timestamp}.csv"
                csv_df.to_csv(csv_path, index=False)
                logger.debug(f"  CSV 已保存：{csv_path}")
    
    def _cache_model(self, model_name: str, asin: str, model: Any) -> None:
        """缓存模型"""
        cache_path = Path(self.config.cache_dir) / f"{model_name}_{asin}.pkl"
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(model, f)
            logger.debug(f"  模型已缓存：{cache_path}")
        except Exception as e:
            logger.warning(f"  模型缓存失败：{str(e)}")
    
    def _select_best_model(self, predictions: Dict[str, Dict]) -> str:
        """选择最佳模型"""
        valid_predictions = {k: v for k, v in predictions.items() if 'error' not in v}
        
        if not valid_predictions:
            return 'none'
        
        # 按 MAPE 排序
        best_model = min(
            valid_predictions.keys(),
            key=lambda k: valid_predictions[k]['metrics'].get('mape', float('inf'))
        )
        
        return best_model
    
    def run_batch(
        self,
        asins: List[str],
        historical_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Dict[str, Dict]:
        """
        批量运行预测
        
        Args:
            asins: ASIN 列表
            historical_data: 历史数据字典 {asin: dataframe}
        
        Returns:
            预测结果字典
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"批量预测 - {len(asins)} 个 ASIN")
        logger.info(f"{'='*60}")
        
        results = {}
        for i, asin in enumerate(asins):
            logger.info(f"\n[{i+1}/{len(asins)}] 处理 ASIN: {asin}")
            
            data = historical_data.get(asin) if historical_data else None
            result = self.run(asin, historical_data=data)
            results[asin] = result
        
        logger.info(f"\n批量预测完成：{len(results)} 个 ASIN")
        return results
    
    def get_summary_report(self, results: Dict[str, Dict]) -> str:
        """生成摘要报告"""
        report_lines = [
            "# 预测管道摘要报告",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 概览",
            f"总 ASIN 数：{len(results)}",
            f"成功：{sum(1 for r in results.values() if 'error' not in r)}",
            f"失败：{sum(1 for r in results.values() if 'error' in r)}",
            "",
            "## 各 ASIN 结果",
            ""
        ]
        
        for asin, result in results.items():
            if 'error' in result:
                report_lines.append(f"### {asin}: ❌ 失败 - {result['error']}")
            else:
                best_model = result.get('best_model', 'N/A')
                best_mape = result['predictions'].get(best_model, {}).get('metrics', {}).get('mape', 'N/A')
                report_lines.append(f"### {asin}: ✅ 成功")
                report_lines.append(f"- 最佳模型：{best_model}")
                report_lines.append(f"- MAPE: {best_mape:.2f}%" if isinstance(best_mape, (int, float)) else f"- MAPE: {best_mape}")
                report_lines.append(f"- 耗时：{result.get('elapsed_time', 0):.2f} 秒")
            report_lines.append("")
        
        return "\n".join(report_lines)


def create_pipeline(config_dict: Optional[Dict] = None) -> PredictionPipeline:
    """
    创建预测管道的快捷函数
    
    Args:
        config_dict: 配置字典
    
    Returns:
        PredictionPipeline 实例
    """
    if config_dict:
        config = PredictionConfig(**config_dict)
    else:
        config = PredictionConfig()
    
    return PredictionPipeline(config)


if __name__ == "__main__":
    # 测试代码
    print("预测管道模块测试")
    print("=" * 60)
    
    # 创建示例数据
    np.random.seed(42)
    dates = pd.date_range(start="2025-01-01", periods=100, freq="D")
    sales = 100 + np.cumsum(np.random.randn(100)) + 10 * np.sin(np.arange(100) * 2 * np.pi / 7)
    
    test_data = pd.DataFrame({
        'date': dates,
        'sales': sales
    })
    
    # 创建管道
    config = PredictionConfig(
        models=['prophet'],
        prophet_forecast_days=7,
        generate_charts=False,
        save_results=False
    )
    
    pipeline = PredictionPipeline(config)
    
    # 运行预测
    result = pipeline.run(
        asin="TEST001",
        historical_data=test_data,
        force_retrain=True
    )
    
    print(f"\n预测结果:")
    if 'error' not in result:
        print(f"  最佳模型：{result['best_model']}")
        print(f"  耗时：{result['elapsed_time']:.2f} 秒")
    else:
        print(f"  错误：{result['error']}")
    
    print("\n✅ 预测管道模块测试完成!")
