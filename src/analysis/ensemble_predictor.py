"""
集成预测器模块 (v2.4.0 Phase 4)

功能:
1. 加权平均集成 (Weighted Average Ensemble)
2. Stacking 集成 (元学习器)
3. 权重优化
4. 模型评估

使用场景:
- 多模型预测结果融合
- 提升预测稳定性和准确性
- 降低单一模型风险

作者：GongBu ShangShu
版本：v2.4.0 Phase 4
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import warnings
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import json
from pathlib import Path

from loguru import logger

# 配置日志
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO"
)


class EnsemblePredictor:
    """
    集成预测器 - 融合多个模型的预测结果
    
    支持的集成方法:
    1. 加权平均 (Weighted Average): 简单但有效
    2. Stacking: 使用元学习器学习如何组合基模型
    
    Attributes:
        models: 基模型字典 {name: model}
        weights: 模型权重字典 {name: weight}
        meta_learner: Stacking 用的元学习器
        is_fitted: 是否已训练
    """
    
    def __init__(
        self,
        models: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
        meta_learner_type: str = "ridge",
        random_state: int = 42
    ):
        """
        初始化集成模型
        
        Args:
            models: 基模型字典，键为模型名称，值为模型对象
                   模型对象需要有 predict(X) 方法
            weights: 模型权重字典，用于加权平均
                    如果为 None，则使用等权重
            meta_learner_type: Stacking 元学习器类型
                              - "ridge": Ridge 回归 (默认，正则化防止过拟合)
                              - "linear": 线性回归
                              - "random_forest": 随机森林
                              - "gradient_boosting": 梯度提升
            random_state: 随机种子
        """
        if not models:
            raise ValueError("模型字典不能为空，请至少提供一个基模型")
        
        self.models = models
        self.model_names = list(models.keys())
        self.weights = weights or {name: 1.0 / len(models) for name in self.model_names}
        self.meta_learner_type = meta_learner_type
        self.random_state = random_state
        
        # 初始化元学习器
        self.meta_learner = self._create_meta_learner(meta_learner_type)
        
        # 状态标记
        self.is_fitted = False
        self.weights_optimized = False
        
        # 验证权重
        self._validate_weights()
        
        logger.info(f"集成预测器初始化完成：{len(self.models)} 个基模型")
        logger.info(f"模型列表：{self.model_names}")
        logger.info(f"初始权重：{self.weights}")
    
    def _create_meta_learner(self, learner_type: str) -> Any:
        """创建元学习器"""
        if learner_type == "ridge":
            return Ridge(alpha=1.0, random_state=self.random_state)
        elif learner_type == "linear":
            return LinearRegression()
        elif learner_type == "random_forest":
            return RandomForestRegressor(
                n_estimators=50,
                max_depth=5,
                random_state=self.random_state,
                n_jobs=-1
            )
        elif learner_type == "gradient_boosting":
            return GradientBoostingRegressor(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=self.random_state
            )
        else:
            logger.warning(f"未知的元学习器类型 '{learner_type}'，使用 Ridge 回归")
            return Ridge(alpha=1.0, random_state=self.random_state)
    
    def _validate_weights(self) -> None:
        """验证权重有效性"""
        if not self.weights:
            return
        
        # 检查权重是否为正
        for name, weight in self.weights.items():
            if weight < 0:
                raise ValueError(f"模型 '{name}' 的权重不能为负数：{weight}")
        
        # 检查权重和是否接近 1
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"权重和不为 1 ({total_weight:.4f})，将自动归一化")
            # 归一化权重
            self.weights = {k: v / total_weight for k, v in self.weights.items()}
    
    def predict_weighted(self, X: np.ndarray) -> np.ndarray:
        """
        加权平均预测
        
        Args:
            X: 输入特征数组，形状 (n_samples, n_features)
               或者每个模型的预测结果列表
        
        Returns:
            集成预测结果，形状 (n_samples,)
        """
        if len(self.models) == 0:
            raise ValueError("没有可用的基模型")
        
        # 收集所有模型的预测
        predictions = []
        for name in self.model_names:
            model = self.models[name]
            pred = model.predict(X)
            predictions.append(pred)
            logger.debug(f"模型 '{name}' 预测完成，形状：{pred.shape}")
        
        # 转换为数组
        predictions_array = np.array(predictions)  # (n_models, n_samples)
        
        # 加权平均
        weights_array = np.array([self.weights.get(name, 1.0 / len(self.model_names)) 
                                   for name in self.model_names])
        weights_array = weights_array / weights_array.sum()  # 确保归一化
        
        weighted_pred = np.average(predictions_array, axis=0, weights=weights_array)
        
        logger.info(f"加权平均预测完成：{len(weighted_pred)} 个样本")
        return weighted_pred
    
    def predict_stacking(self, X: np.ndarray) -> np.ndarray:
        """
        Stacking 集成预测 (使用元学习器)
        
        Args:
            X: 输入特征数组，形状 (n_samples, n_features)
        
        Returns:
            集成预测结果，形状 (n_samples,)
        """
        if not self.is_fitted:
            raise RuntimeError("Stacking 模型尚未训练，请先调用 fit_stacking()")
        
        # 收集所有模型的预测作为元学习器的输入
        meta_features = []
        for name in self.model_names:
            model = self.models[name]
            pred = model.predict(X)
            meta_features.append(pred.reshape(-1, 1))
            logger.debug(f"模型 '{name}' 预测完成，作为元特征")
        
        # 拼接所有预测
        meta_X = np.hstack(meta_features)  # (n_samples, n_models)
        logger.debug(f"元特征形状：{meta_X.shape}")
        
        # 使用元学习器预测
        stacked_pred = self.meta_learner.predict(meta_X)
        
        logger.info(f"Stacking 预测完成：{len(stacked_pred)} 个样本")
        return stacked_pred
    
    def fit_stacking(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        n_folds: int = 5,
        use_oof: bool = True
    ) -> 'EnsemblePredictor':
        """
        训练 Stacking 集成模型
        
        Args:
            X_train: 训练特征，形状 (n_samples, n_features)
            y_train: 训练标签，形状 (n_samples,)
            n_folds: 交叉验证折数
            use_oof: 是否使用 Out-of-Fold 预测 (推荐 True，防止过拟合)
        
        Returns:
            self
        """
        logger.info(f"开始训练 Stacking 集成模型 (n_folds={n_folds}, use_oof={use_oof})")
        
        n_samples = len(y_train)
        
        if use_oof:
            # Out-of-Fold 预测 (更稳健)
            logger.info("使用 Out-of-Fold 策略生成元特征")
            meta_train = np.zeros((n_samples, len(self.model_names)))
            
            kfold = KFold(n_splits=n_folds, shuffle=True, random_state=self.random_state)
            
            for fold_idx, (train_idx, val_idx) in enumerate(kfold.split(X_train)):
                logger.debug(f"处理折 {fold_idx + 1}/{n_folds}")
                
                X_tr, X_val = X_train[train_idx], X_train[val_idx]
                y_tr = y_train[train_idx]
                
                # 训练每个基模型并预测验证集
                for model_idx, name in enumerate(self.model_names):
                    model = self.models[name]
                    # 假设模型有 fit 方法
                    if hasattr(model, 'fit'):
                        model.fit(X_tr, y_tr)
                    
                    pred_val = model.predict(X_val)
                    meta_train[val_idx, model_idx] = pred_val
            
            logger.info(f"OOF 元特征生成完成，形状：{meta_train.shape}")
        else:
            # 简单策略：直接用全部数据训练
            logger.warning("未使用 OOF 策略，可能过拟合")
            meta_train = []
            for name in self.model_names:
                model = self.models[name]
                if hasattr(model, 'fit'):
                    model.fit(X_train, y_train)
                pred = model.predict(X_train)
                meta_train.append(pred.reshape(-1, 1))
            meta_train = np.hstack(meta_train)
        
        # 训练元学习器
        logger.info(f"训练元学习器：{self.meta_learner_type}")
        self.meta_learner.fit(meta_train, y_train)
        
        # 用全部数据重新训练基模型
        logger.info("用全部训练数据重新训练基模型")
        for name in self.model_names:
            model = self.models[name]
            if hasattr(model, 'fit'):
                model.fit(X_train, y_train)
        
        self.is_fitted = True
        logger.info("Stacking 集成模型训练完成")
        
        return self
    
    def get_optimal_weights(
        self,
        validation_data: pd.DataFrame,
        target_column: str = 'sales',
        feature_columns: Optional[List[str]] = None,
        method: str = "grid_search",
        n_iterations: int = 100
    ) -> Dict[str, float]:
        """
        优化模型权重
        
        Args:
            validation_data: 验证数据集
            target_column: 目标列名
            feature_columns: 特征列名列表，如果为 None 则自动推断
            method: 优化方法
                   - "grid_search": 网格搜索
                   - "optimization": 数值优化
            n_iterations: 迭代次数 (用于 optimization)
        
        Returns:
            最优权重的字典
        """
        logger.info(f"开始优化模型权重 (method={method})")
        
        # 准备数据
        if feature_columns is None:
            feature_columns = [col for col in validation_data.columns if col != target_column]
        
        X_val = validation_data[feature_columns].values
        y_val = validation_data[target_column].values
        
        # 获取各模型预测
        model_predictions = {}
        for name in self.model_names:
            model = self.models[name]
            pred = model.predict(X_val)
            model_predictions[name] = pred
            logger.debug(f"模型 '{name}' 验证集 MAPE: {self._calculate_mape(y_val, pred):.2f}%")
        
        if method == "grid_search":
            optimal_weights = self._grid_search_weights(
                y_val, model_predictions, resolution=0.05
            )
        elif method == "optimization":
            optimal_weights = self._optimize_weights_scipy(
                y_val, model_predictions, n_iterations=n_iterations
            )
        else:
            raise ValueError(f"未知的优化方法：{method}")
        
        # 更新权重
        self.weights = optimal_weights
        self.weights_optimized = True
        
        logger.info(f"权重优化完成：{optimal_weights}")
        
        # 验证优化效果
        old_pred = self._weighted_predict(model_predictions, 
                                          {name: 1.0/len(self.model_names) for name in self.model_names})
        new_pred = self._weighted_predict(model_predictions, optimal_weights)
        
        old_mape = self._calculate_mape(y_val, old_pred)
        new_mape = self._calculate_mape(y_val, new_pred)
        
        logger.info(f"优化效果：MAPE {old_mape:.2f}% → {new_mape:.2f}% (提升 {(old_mape-new_mape)/old_mape*100:.1f}%)")
        
        return optimal_weights
    
    def _weighted_predict(
        self,
        predictions: Dict[str, np.ndarray],
        weights: Dict[str, float]
    ) -> np.ndarray:
        """加权预测辅助函数"""
        pred_array = np.array([predictions[name] for name in self.model_names])
        weight_array = np.array([weights.get(name, 1.0/len(self.model_names)) 
                                  for name in self.model_names])
        weight_array = weight_array / weight_array.sum()
        return np.average(pred_array, axis=0, weights=weight_array)
    
    def _grid_search_weights(
        self,
        y_true: np.ndarray,
        predictions: Dict[str, np.ndarray],
        resolution: float = 0.05
    ) -> Dict[str, float]:
        """网格搜索最优权重"""
        from itertools import product
        
        n_models = len(self.model_names)
        steps = int(1.0 / resolution) + 1
        
        logger.debug(f"网格搜索：{n_models} 个模型，分辨率 {resolution}")
        
        best_weights = None
        best_score = float('inf')
        
        # 对于多模型，使用随机采样代替完全网格搜索
        if n_models > 2:
            # 随机采样 1000 种权重组合
            np.random.seed(self.random_state)
            for _ in range(1000):
                raw_weights = np.random.dirichlet(np.ones(n_models))
                weight_dict = {name: raw_weights[i] for i, name in enumerate(self.model_names)}
                
                pred = self._weighted_predict(predictions, weight_dict)
                score = self._calculate_mape(y_true, pred)
                
                if score < best_score:
                    best_score = score
                    best_weights = weight_dict
        else:
            # 两模型时可以完全搜索
            for w1 in np.linspace(0, 1, steps):
                w2 = 1.0 - w1
                weight_dict = {self.model_names[0]: w1, self.model_names[1]: w2}
                
                pred = self._weighted_predict(predictions, weight_dict)
                score = self._calculate_mape(y_true, pred)
                
                if score < best_score:
                    best_score = score
                    best_weights = weight_dict
        
        return best_weights or {name: 1.0/n_models for name in self.model_names}
    
    def _optimize_weights_scipy(
        self,
        y_true: np.ndarray,
        predictions: Dict[str, np.ndarray],
        n_iterations: int = 100
    ) -> Dict[str, float]:
        """使用 scipy 优化权重"""
        from scipy.optimize import minimize
        
        n_models = len(self.model_names)
        
        def objective(weights):
            weights = np.maximum(weights, 0)  # 确保非负
            weights = weights / weights.sum()  # 归一化
            weight_dict = {name: weights[i] for i, name in enumerate(self.model_names)}
            pred = self._weighted_predict(predictions, weight_dict)
            return self._calculate_mape(y_true, pred)
        
        # 初始权重：均匀分布
        x0 = np.ones(n_models) / n_models
        
        # 优化
        result = minimize(
            objective,
            x0,
            method='L-BFGS-B',
            bounds=[(0, 1)] * n_models,
            options={'maxiter': n_iterations}
        )
        
        optimal_weights = np.maximum(result.x, 0)
        optimal_weights = optimal_weights / optimal_weights.sum()
        
        return {name: optimal_weights[i] for i, name in enumerate(self.model_names)}
    
    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        method: str = "all"
    ) -> Dict[str, float]:
        """
        评估集成模型性能
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            method: 评估方法
                   - "all": 返回所有指标
                   - "mape": 只返回 MAPE
                   - "rmse": 只返回 RMSE
                   - "mae": 只返回 MAE
        
        Returns:
            评估指标字典
        """
        metrics = {}
        
        # MAPE (平均绝对百分比误差)
        metrics['mape'] = self._calculate_mape(y_true, y_pred)
        
        # RMSE (均方根误差)
        metrics['rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
        
        # MAE (平均绝对误差)
        metrics['mae'] = mean_absolute_error(y_true, y_pred)
        
        # R² (决定系数)
        from sklearn.metrics import r2_score
        metrics['r2'] = r2_score(y_true, y_pred)
        
        # MAPE 分量分析
        metrics['mape_median'] = np.median(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100
        metrics['mape_max'] = np.max(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100
        
        if method != "all":
            return {method: metrics.get(method, metrics['mape'])}
        
        logger.info(f"评估完成 - MAPE: {metrics['mape']:.2f}%, RMSE: {metrics['rmse']:.2f}, R²: {metrics['r2']:.4f}")
        return metrics
    
    def _calculate_mape(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """计算 MAPE"""
        # 避免除以零
        mask = np.abs(y_true) > 1e-8
        if not np.any(mask):
            return 0.0
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    
    def compare_methods(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, Dict[str, float]]:
        """
        比较不同集成方法的性能
        
        Args:
            X_test: 测试特征
            y_test: 测试标签
        
        Returns:
            各方法的评估结果
        """
        results = {}
        
        # 1. 单一模型性能
        logger.info("评估单一模型性能...")
        for name in self.model_names:
            model = self.models[name]
            pred = model.predict(X_test)
            results[f'single_{name}'] = self.evaluate(y_test, pred)
        
        # 2. 加权平均
        logger.info("评估加权平均集成...")
        weighted_pred = self.predict_weighted(X_test)
        results['weighted_average'] = self.evaluate(y_test, weighted_pred)
        
        # 3. Stacking (如果已训练)
        if self.is_fitted:
            logger.info("评估 Stacking 集成...")
            stacked_pred = self.predict_stacking(X_test)
            results['stacking'] = self.evaluate(y_test, stacked_pred)
        
        # 4. 等权重基线
        logger.info("评估等权重基线...")
        equal_weights = {name: 1.0/len(self.model_names) for name in self.model_names}
        old_weights = self.weights
        self.weights = equal_weights
        equal_pred = self.predict_weighted(X_test)
        results['equal_weights'] = self.evaluate(y_test, equal_pred)
        self.weights = old_weights
        
        # 找出最佳方法
        best_method = min(results.keys(), key=lambda k: results[k]['mape'])
        logger.info(f"最佳方法：{best_method} (MAPE: {results[best_method]['mape']:.2f}%)")
        
        return results
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        获取模型重要性 (基于权重)
        
        Returns:
            模型重要性的字典
        """
        if self.weights_optimized or self.is_fitted:
            return self.weights.copy()
        else:
            logger.warning("权重尚未优化，返回初始权重")
            return {name: 1.0/len(self.model_names) for name in self.model_names}
    
    def save_weights(self, path: str) -> None:
        """保存权重到文件"""
        weights_data = {
            'weights': self.weights,
            'model_names': self.model_names,
            'meta_learner_type': self.meta_learner_type,
            'is_fitted': self.is_fitted,
            'weights_optimized': self.weights_optimized,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(path, 'w') as f:
            json.dump(weights_data, f, indent=2)
        
        logger.info(f"权重已保存到：{path}")
    
    def load_weights(self, path: str) -> None:
        """从文件加载权重"""
        with open(path, 'r') as f:
            weights_data = json.load(f)
        
        self.weights = weights_data['weights']
        self.model_names = weights_data['model_names']
        self.is_fitted = weights_data.get('is_fitted', False)
        self.weights_optimized = weights_data.get('weights_optimized', False)
        
        logger.info(f"权重已从 {path} 加载")


def quick_ensemble_forecast(
    data: pd.DataFrame,
    models: Dict[str, Any],
    target_column: str = 'sales',
    forecast_days: int = 30,
    ensemble_method: str = 'weighted',
    optimize_weights: bool = True
) -> Dict[str, Any]:
    """
    快速集成预测快捷函数
    
    Args:
        data: 历史数据 DataFrame
        models: 已训练的模型字典
        target_column: 目标列名
        forecast_days: 预测天数
        ensemble_method: 集成方法 ('weighted' 或 'stacking')
        optimize_weights: 是否优化权重
    
    Returns:
        预测结果字典
    """
    logger.info(f"启动快速集成预测 (method={ensemble_method}, days={forecast_days})")
    
    # 创建集成预测器
    predictor = EnsemblePredictor(models=models)
    
    # 准备数据
    feature_columns = [col for col in data.columns if col != target_column]
    X = data[feature_columns].values
    y = data[target_column].values
    
    # 划分训练/验证集
    split_idx = int(len(data) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    
    # 优化权重
    if optimize_weights:
        val_df = pd.DataFrame(X_val, columns=feature_columns)
        val_df[target_column] = y_val
        predictor.get_optimal_weights(val_df, target_column)
    
    # 训练 Stacking (如果需要)
    if ensemble_method == 'stacking':
        predictor.fit_stacking(X_train, y_train)
    
    # 生成预测
    if ensemble_method == 'stacking':
        forecast = predictor.predict_stacking(X_val)
    else:
        forecast = predictor.predict_weighted(X_val)
    
    # 评估
    metrics = predictor.evaluate(y_val, forecast)
    
    logger.info(f"集成预测完成 - MAPE: {metrics['mape']:.2f}%")
    
    return {
        'forecast': forecast,
        'metrics': metrics,
        'weights': predictor.weights,
        'method': ensemble_method
    }


if __name__ == "__main__":
    # 测试代码
    print("集成预测器模块测试")
    print("=" * 60)
    
    # 创建示例数据
    np.random.seed(42)
    n_samples = 100
    X = np.random.randn(n_samples, 5)
    y = 2 * X[:, 0] + 3 * X[:, 1] + np.random.randn(n_samples) * 0.5
    
    # 创建简单模型
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    
    model1 = LinearRegression()
    model1.fit(X, y)
    
    model2 = RandomForestRegressor(n_estimators=10, random_state=42)
    model2.fit(X, y)
    
    models = {
        'linear': model1,
        'random_forest': model2
    }
    
    # 测试集成预测器
    predictor = EnsemblePredictor(models=models)
    
    # 测试加权预测
    weighted_pred = predictor.predict_weighted(X)
    print(f"加权预测形状：{weighted_pred.shape}")
    
    # 测试 Stacking
    predictor.fit_stacking(X, y)
    stacked_pred = predictor.predict_stacking(X)
    print(f"Stacking 预测形状：{stacked_pred.shape}")
    
    # 评估
    metrics = predictor.evaluate(y, stacked_pred)
    print(f"\n评估指标:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")
    
    print("\n✅ 集成预测器模块测试完成!")
