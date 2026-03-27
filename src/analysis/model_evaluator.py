"""
模型统一评估框架 (v2.4.0 Phase 3)

功能：
1. 统一评估多个预测模型 (线性/Prophet/LSTM)
2. 多指标评估 (MAPE/RMSE/MAE/R²)
3. 模型训练时间对比
4. 模型预测时间对比
5. 最佳模型自动推荐

使用示例：
```python
from .model_evaluator import ModelEvaluator

evaluator = ModelEvaluator({
    'linear': LinearModel(),
    'prophet': ProphetPredictor(),
    'lstm': LSTMPredictor(),
})

evaluator.train_all(train_data)
predictions = evaluator.predict_all(test_data)
metrics = evaluator.evaluate_all(y_true, y_pred)
best_model = evaluator.get_best_model('MAPE')
```

作者：GongBu ShangShu
版本：v2.4.0 Phase 3
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple, Union, Callable
from datetime import datetime
import logging
from pathlib import Path
import time
import json

from loguru import logger

# 导入现有模型
from .prophet_predictor import ProphetPredictor
from .lstm_predictor import LSTMPredictor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler


class ModelEvaluator:
    """
    多模型统一评估器
    
    提供统一的接口来训练、预测和评估多个时间序列模型
    支持 MAPE、RMSE、MAE、R² 等多种评估指标
    """
    
    def __init__(self, models: Optional[Dict[str, Any]] = None):
        """
        初始化模型评估器
        
        Args:
            models: 模型字典，键为模型名称，值为模型实例
                   如果为 None，将创建默认模型 (线性/Prophet/LSTM)
        """
        self.models: Dict[str, Any] = models or {}
        self.training_results: Dict[str, Dict[str, Any]] = {}
        self.prediction_results: Dict[str, np.ndarray] = {}
        self.metrics_results: Dict[str, Dict[str, float]] = {}
        self.y_true: Optional[np.ndarray] = None
        self.y_pred_dict: Dict[str, np.ndarray] = {}
        
        # 训练时间记录
        self.train_times: Dict[str, float] = {}
        # 预测时间记录
        self.predict_times: Dict[str, float] = {}
        
        logger.info("ModelEvaluator 初始化完成")
    
    def add_model(self, name: str, model: Any) -> None:
        """
        添加模型到评估器
        
        Args:
            name: 模型名称
            model: 模型实例
        """
        self.models[name] = model
        logger.info(f"添加模型：{name}")
    
    def train_all(self, train_data: pd.DataFrame, target_col: str = 'sales') -> Dict[str, Dict[str, Any]]:
        """
        训练所有模型
        
        Args:
            train_data: 训练数据 DataFrame
            target_col: 目标列名 (默认 'sales')
            
        Returns:
            训练结果字典
        """
        logger.info(f"开始训练 {len(self.models)} 个模型...")
        
        for name, model in self.models.items():
            logger.info(f"训练模型：{name}")
            start_time = time.time()
            
            try:
                result = self._train_single_model(name, model, train_data, target_col)
                self.training_results[name] = result
                self.train_times[name] = time.time() - start_time
                
                logger.info(f"模型 {name} 训练完成，耗时：{self.train_times[name]:.2f}秒")
                
            except Exception as e:
                logger.error(f"模型 {name} 训练失败：{e}")
                self.training_results[name] = {
                    'success': False,
                    'error': str(e),
                    'train_time': time.time() - start_time,
                }
        
        return self.training_results
    
    def _train_single_model(
        self, 
        name: str, 
        model: Any, 
        train_data: pd.DataFrame, 
        target_col: str
    ) -> Dict[str, Any]:
        """
        训练单个模型
        
        Args:
            name: 模型名称
            model: 模型实例
            train_data: 训练数据
            target_col: 目标列名
            
        Returns:
            训练结果
        """
        if name == 'linear':
            return self._train_linear_model(model, train_data, target_col)
        elif name == 'prophet':
            return self._train_prophet_model(model, train_data, target_col)
        elif name == 'lstm':
            return self._train_lstm_model(model, train_data, target_col)
        else:
            # 通用训练接口
            if hasattr(model, 'fit'):
                X = train_data.drop(columns=[target_col], errors='ignore')
                y = train_data[target_col]
                model.fit(X, y)
                return {'success': True, 'model_type': 'generic'}
            else:
                raise ValueError(f"未知模型类型：{name}")
    
    def _train_linear_model(
        self, 
        model: LinearRegression, 
        train_data: pd.DataFrame, 
        target_col: str
    ) -> Dict[str, Any]:
        """训练线性回归模型"""
        # 准备特征
        if 'date' in train_data.columns:
            train_data = train_data.copy()
            train_data['date_ordinal'] = pd.to_datetime(train_data['date']).map(pd.Timestamp.toordinal)
            X = train_data[['date_ordinal']]
        else:
            X = train_data.index.values.reshape(-1, 1)
        
        y = train_data[target_col].values
        
        model.fit(X, y)
        
        return {
            'success': True,
            'model_type': 'linear',
            'coefficients': model.coef_.tolist(),
            'intercept': float(model.intercept_),
            'n_samples': len(train_data),
        }
    
    def _train_prophet_model(
        self, 
        model: ProphetPredictor, 
        train_data: pd.DataFrame, 
        target_col: str
    ) -> Dict[str, Any]:
        """训练 Prophet 模型"""
        # 准备 Prophet 格式数据
        prophet_data = train_data.copy()
        if 'date' not in prophet_data.columns:
            prophet_data['date'] = pd.date_range(
                start='2025-01-01', 
                periods=len(prophet_data), 
                freq='D'
            )
        
        prophet_data = prophet_data.rename(columns={'date': 'ds', target_col: 'y'})
        prophet_data = prophet_data[['ds', 'y']]
        
        model.historical_data = prophet_data
        model.train(prophet_data)
        
        return {
            'success': True,
            'model_type': 'prophet',
            'n_samples': len(train_data),
        }
    
    def _train_lstm_model(
        self, 
        model: LSTMPredictor, 
        train_data: pd.DataFrame, 
        target_col: str
    ) -> Dict[str, Any]:
        """训练 LSTM 模型"""
        y = train_data[target_col].values
        
        # LSTM 需要序列数据
        model.fit(y)
        
        return {
            'success': True,
            'model_type': 'lstm',
            'n_samples': len(train_data),
        }
    
    def predict_all(self, test_data: pd.DataFrame, periods: int = 30) -> Dict[str, np.ndarray]:
        """
        所有模型进行预测
        
        Args:
            test_data: 测试数据 (用于 Prophet/LSTM)
            periods: 预测期数 (用于线性模型)
            
        Returns:
            预测结果字典
        """
        logger.info(f"开始 {len(self.models)} 个模型的预测...")
        
        for name, model in self.models.items():
            logger.info(f"模型 {name} 预测中...")
            start_time = time.time()
            
            try:
                predictions = self._predict_single_model(name, model, test_data, periods)
                self.prediction_results[name] = predictions
                self.predict_times[name] = time.time() - start_time
                
                logger.info(f"模型 {name} 预测完成，耗时：{self.predict_times[name]:.4f}秒")
                
            except Exception as e:
                logger.error(f"模型 {name} 预测失败：{e}")
                self.prediction_results[name] = None
                self.predict_times[name] = time.time() - start_time
        
        return self.prediction_results
    
    def _predict_single_model(
        self, 
        name: str, 
        model: Any, 
        test_data: pd.DataFrame, 
        periods: int
    ) -> np.ndarray:
        """预测单个模型"""
        if name == 'linear':
            return self._predict_linear_model(model, periods)
        elif name == 'prophet':
            return self._predict_prophet_model(model, periods)
        elif name == 'lstm':
            return self._predict_lstm_model(model, periods)
        else:
            raise ValueError(f"未知模型类型：{name}")
    
    def _predict_linear_model(self, model: LinearRegression, periods: int) -> np.ndarray:
        """线性模型预测"""
        # 创建未来日期
        last_idx = model.coef_.shape[0] if hasattr(model, 'coef_') else 1
        future_idx = np.arange(last_idx, last_idx + periods).reshape(-1, 1)
        return model.predict(future_idx)
    
    def _predict_prophet_model(self, model: ProphetPredictor, periods: int) -> np.ndarray:
        """Prophet 模型预测"""
        forecast = model.predict(periods=periods)
        return forecast['yhat'].values
    
    def _predict_lstm_model(self, model: LSTMPredictor, periods: int) -> np.ndarray:
        """LSTM 模型预测"""
        predictions = model.predict(periods=periods)
        return predictions
    
    def evaluate_all(
        self, 
        y_true: np.ndarray, 
        y_pred_dict: Optional[Dict[str, np.ndarray]] = None
    ) -> pd.DataFrame:
        """
        评估所有模型
        
        Args:
            y_true: 真实值
            y_pred_dict: 预测值字典 (如果为 None，使用已存储的预测结果)
            
        Returns:
            评估指标 DataFrame
        """
        self.y_true = y_true
        if y_pred_dict is not None:
            self.y_pred_dict = y_pred_dict
        else:
            self.y_pred_dict = self.prediction_results
        
        logger.info("开始评估所有模型...")
        
        metrics_list = []
        
        for name, y_pred in self.y_pred_dict.items():
            if y_pred is None:
                logger.warning(f"模型 {name} 无预测结果，跳过评估")
                continue
            
            try:
                metrics = self._calculate_metrics(y_true, y_pred)
                metrics['model_name'] = name
                metrics['train_time'] = self.train_times.get(name, 0.0)
                metrics['predict_time'] = self.predict_times.get(name, 0.0)
                metrics_list.append(metrics)
                
                logger.info(f"模型 {name} 评估完成：MAPE={metrics['MAPE']:.2f}%")
                
            except Exception as e:
                logger.error(f"模型 {name} 评估失败：{e}")
                self.metrics_results[name] = {'error': str(e)}
        
        self.metrics_results = {m['model_name']: m for m in metrics_list}
        
        # 创建 DataFrame
        if metrics_list:
            metrics_df = pd.DataFrame(metrics_list)
            # 设置模型名为索引
            metrics_df = metrics_df.set_index('model_name')
            return metrics_df
        else:
            return pd.DataFrame()
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """
        计算评估指标
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            指标字典
        """
        # 确保长度一致
        min_len = min(len(y_true), len(y_pred))
        y_true = y_true[:min_len]
        y_pred = y_pred[:min_len]
        
        # MAPE (平均绝对百分比误差)
        mape = self._calculate_mape(y_true, y_pred)
        
        # RMSE (均方根误差)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        
        # MAE (平均绝对误差)
        mae = mean_absolute_error(y_true, y_pred)
        
        # R² (决定系数)
        r2 = r2_score(y_true, y_pred)
        
        return {
            'MAPE': mape,
            'RMSE': rmse,
            'MAE': mae,
            'R2': r2,
        }
    
    def _calculate_mape(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        计算 MAPE (平均绝对百分比误差)
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            MAPE 值 (百分比)
        """
        # 避免除以零
        mask = y_true != 0
        if not np.any(mask):
            return 0.0
        
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        return mape
    
    def plot_comparison(self, save_path: Optional[str] = None) -> None:
        """
        绘制模型对比图
        
        Args:
            save_path: 保存路径 (如果为 None，则显示图表)
        """
        from .comparison_visualizer import (
            plot_metrics_comparison,
            plot_predictions_comparison,
            plot_residuals_comparison,
        )
        
        if not self.metrics_results:
            logger.warning("没有评估结果，无法绘制对比图")
            return
        
        # 创建指标对比 DataFrame
        metrics_df = pd.DataFrame(self.metrics_results).T
        
        # 绘制指标对比
        plot_metrics_comparison(metrics_df, save_path)
        
        # 绘制预测对比
        if self.y_true is not None and self.y_pred_dict:
            plot_predictions_comparison(self.y_true, self.y_pred_dict, save_path)
            plot_residuals_comparison(self.y_true, self.y_pred_dict, save_path)
        
        logger.info("模型对比图绘制完成")
    
    def get_best_model(self, metric: str = 'MAPE') -> str:
        """
        获取最佳模型
        
        Args:
            metric: 评估指标 (MAPE/RMSE/MAE/R2)
            
        Returns:
            最佳模型名称
        """
        if not self.metrics_results:
            logger.warning("没有评估结果，无法确定最佳模型")
            return ""
        
        # 对于误差类指标 (MAPE/RMSE/MAE)，值越小越好
        # 对于 R2，值越大越好
        error_metrics = ['MAPE', 'RMSE', 'MAE']
        
        best_model = None
        best_value = None
        
        for name, metrics in self.metrics_results.items():
            if metric not in metrics:
                continue
            
            value = metrics[metric]
            
            if best_value is None:
                best_value = value
                best_model = name
            else:
                if metric in error_metrics:
                    # 误差类指标，越小越好
                    if value < best_value:
                        best_value = value
                        best_model = name
                else:
                    # R2 等指标，越大越好
                    if value > best_value:
                        best_value = value
                        best_model = name
        
        if best_model:
            logger.info(f"最佳模型 ({metric}): {best_model} = {best_value:.4f}")
        
        return best_model or ""
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        获取评估摘要
        
        Returns:
            评估摘要字典
        """
        if not self.metrics_results:
            return {}
        
        metrics_df = pd.DataFrame(self.metrics_results).T
        
        summary = {
            'models_evaluated': list(self.metrics_results.keys()),
            'best_model_mape': self.get_best_model('MAPE'),
            'best_model_rmse': self.get_best_model('RMSE'),
            'best_model_mae': self.get_best_model('MAE'),
            'best_model_r2': self.get_best_model('R2'),
            'metrics': self.metrics_results,
            'train_times': self.train_times,
            'predict_times': self.predict_times,
        }
        
        return summary
    
    def export_results(self, path: str, format: str = 'json') -> None:
        """
        导出评估结果
        
        Args:
            path: 保存路径
            format: 导出格式 ('json' 或 'csv')
        """
        if format == 'json':
            # 转换 numpy 类型为 Python 原生类型
            export_data = {}
            for name, metrics in self.metrics_results.items():
                export_data[name] = {
                    k: (float(v) if isinstance(v, (np.floating, float)) else v)
                    for k, v in metrics.items()
                }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        elif format == 'csv':
            metrics_df = pd.DataFrame(self.metrics_results).T
            metrics_df.to_csv(path, encoding='utf-8-sig')
        
        logger.info(f"评估结果已导出到：{path}")


def create_default_evaluator() -> ModelEvaluator:
    """
    创建默认模型评估器 (包含线性/Prophet/LSTM 三个模型)
    
    Returns:
        ModelEvaluator 实例
    """
    evaluator = ModelEvaluator()
    
    # 添加线性回归模型
    evaluator.add_model('linear', LinearRegression())
    
    # 添加 Prophet 模型
    evaluator.add_model('prophet', ProphetPredictor())
    
    # 添加 LSTM 模型
    evaluator.add_model('lstm', LSTMPredictor())
    
    logger.info("默认模型评估器创建完成 (线性/Prophet/LSTM)")
    
    return evaluator


def quick_model_comparison(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    target_col: str = 'sales',
    periods: int = 30,
) -> Dict[str, Any]:
    """
    快速模型对比 (一键评估)
    
    Args:
        train_data: 训练数据
        test_data: 测试数据
        target_col: 目标列名
        periods: 预测期数
        
    Returns:
        对比结果字典
    """
    logger.info("开始快速模型对比...")
    
    # 创建评估器
    evaluator = create_default_evaluator()
    
    # 训练所有模型
    evaluator.train_all(train_data, target_col)
    
    # 预测
    evaluator.predict_all(test_data, periods)
    
    # 获取真实值
    y_true = test_data[target_col].values[:periods]
    
    # 评估
    metrics_df = evaluator.evaluate_all(y_true)
    
    # 获取最佳模型
    best_model = evaluator.get_best_model('MAPE')
    
    logger.info(f"快速模型对比完成，最佳模型：{best_model}")
    
    return {
        'metrics_df': metrics_df,
        'best_model': best_model,
        'evaluator': evaluator,
    }
