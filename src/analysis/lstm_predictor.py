"""
LSTM 深度学习预测模块 (v2.4 Phase 2)

基于 TensorFlow/Keras 的 LSTM 神经网络时间序列预测
用于亚马逊销售数据预测，目标 MAPE < 12%

功能:
- 序列数据准备
- LSTM 模型构建
- 模型训练与验证
- 预测与评估
- 模型保存/加载

Author: OpenClaw Imperial - Gongbu Shangshu
Version: 2.4.0 Phase 2
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
import logging

# TensorFlow imports
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam

# Scikit-learn imports
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

# 配置日志
logger = logging.getLogger(__name__)


class LSTMPredictor:
    """
    LSTM 时间序列预测器
    
    使用多层 LSTM 网络进行销售数据预测
    支持自定义回溯窗口和预测范围
    """
    
    def __init__(
        self,
        lookback: int = 60,
        forecast_horizon: int = 30,
        lstm_units: List[int] = [50, 25],
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        random_state: int = 42,
    ):
        """
        初始化 LSTM 预测器
        
        Args:
            lookback: 回溯窗口大小 (使用过去 N 天数据预测)
            forecast_horizon: 预测范围 (预测未来 N 天)
            lstm_units: 每层 LSTM 单元数列表
            dropout: Dropout 比率 (防止过拟合)
            learning_rate: 学习率
            random_state: 随机种子 (确保可重复性)
        """
        self.lookback = lookback
        self.forecast_horizon = forecast_horizon
        self.lstm_units = lstm_units
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.random_state = random_state
        
        # 设置随机种子
        np.random.seed(random_state)
        tf.random.set_seed(random_state)
        
        # 初始化模型和 scaler
        self.model: Optional[tf.keras.Model] = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.is_fitted = False
        
        # 训练历史
        self.history = None
        
        logger.info(
            f"LSTMPredictor 初始化完成：lookback={lookback}, "
            f"horizon={forecast_horizon}, lstm_units={lstm_units}"
        )
    
    def prepare_sequences(
        self,
        data: np.ndarray,
        target: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        准备序列数据 (X, y)
        
        将时间序列数据转换为监督学习格式
        
        Args:
            data: 输入数据 (一维数组)
            target: 目标变量 (可选，如果为 None 则使用 data 自身)
            
        Returns:
            X: 特征矩阵 (samples, lookback, features)
            y: 目标向量 (samples,)
        """
        if target is None:
            target = data
        
        X, y = [], []
        
        for i in range(len(data) - self.lookback):
            X.append(data[i:i + self.lookback])
            y.append(target[i + self.lookback])
        
        X = np.array(X)
        y = np.array(y)
        
        # 重塑 X 为 (samples, lookback, features)
        if len(X.shape) == 2:
            X = X.reshape((X.shape[0], X.shape[1], 1))
        
        logger.info(f"序列数据准备完成：X shape={X.shape}, y shape={y.shape}")
        return X, y
    
    def prepare_multistep_sequences(
        self,
        data: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备多步预测序列数据
        
        Args:
            data: 输入数据 (一维数组)
            
        Returns:
            X: 特征矩阵 (samples, lookback, features)
            y: 目标矩阵 (samples, forecast_horizon)
        """
        X, y = [], []
        
        for i in range(len(data) - self.lookback - self.forecast_horizon + 1):
            X.append(data[i:i + self.lookback])
            y.append(data[i + self.lookback:i + self.lookback + self.forecast_horizon])
        
        X = np.array(X)
        y = np.array(y)
        
        # 重塑 X 为 (samples, lookback, features)
        if len(X.shape) == 2:
            X = X.reshape((X.shape[0], X.shape[1], 1))
        
        logger.info(
            f"多步序列数据准备完成：X shape={X.shape}, y shape={y.shape}"
        )
        return X, y
    
    def build_model(
        self,
        input_shape: Tuple[int, int],
        output_steps: int = 1,
    ) -> tf.keras.Model:
        """
        构建 LSTM 模型
        
        Args:
            input_shape: 输入形状 (lookback, features)
            output_steps: 输出步数 (1=单步预测，>1=多步预测)
            
        Returns:
            编译好的 Keras 模型
        """
        model = Sequential(name="LSTM_Sales_Predictor")
        
        # 输入层
        model.add(
            Input(shape=input_shape, name="input_layer")
        )
        
        # LSTM 层
        for i, units in enumerate(self.lstm_units):
            return_sequences = i < len(self.lstm_units) - 1
            model.add(
                LSTM(
                    units,
                    return_sequences=return_sequences,
                    name=f"lstm_layer_{i}",
                    activation="tanh",
                    recurrent_activation="hard_sigmoid",
                )
            )
            model.add(Dropout(self.dropout, name=f"dropout_{i}"))
        
        # 全连接层
        model.add(
            Dense(
                32,
                activation="relu",
                name="dense_layer_1",
            )
        )
        model.add(Dropout(self.dropout / 2, name="dropout_final"))
        
        # 输出层
        if output_steps == 1:
            model.add(
                Dense(1, activation="linear", name="output_layer")
            )
        else:
            model.add(
                Dense(output_steps, activation="linear", name="output_layer")
            )
        
        # 编译模型
        optimizer = Adam(learning_rate=self.learning_rate)
        model.compile(
            optimizer=optimizer,
            loss="mse",
            metrics=["mae", "mape"],
        )
        
        # 打印模型摘要
        model.summary()
        
        self.model = model
        logger.info(f"LSTM 模型构建完成，参数量：{model.count_params():,}")
        return model
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        verbose: int = 1,
        model_save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        训练模型
        
        Args:
            X_train: 训练特征
            y_train: 训练目标
            X_val: 验证特征
            y_val: 验证目标
            epochs: 训练轮数
            batch_size: 批次大小
            verbose: 日志详细程度 (0=静默，1=进度条，2=每轮)
            model_save_path: 模型保存路径
            
        Returns:
            训练历史记录
        """
        if self.model is None:
            # 自动推断输入形状
            input_shape = (X_train.shape[1], X_train.shape[2])
            output_steps = y_train.shape[1] if len(y_train.shape) > 1 else 1
            self.build_model(input_shape, output_steps)
        
        # 配置回调函数
        callbacks = [
            EarlyStopping(
                monitor="val_loss",
                patience=15,
                restore_best_weights=True,
                verbose=1,
            ),
            ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=7,
                min_lr=1e-6,
                verbose=1,
            ),
        ]
        
        if model_save_path:
            callbacks.append(
                ModelCheckpoint(
                    filepath=model_save_path,
                    monitor="val_loss",
                    save_best_only=True,
                    verbose=1,
                )
            )
        
        # 训练模型
        logger.info(
            f"开始训练：epochs={epochs}, batch_size={batch_size}, "
            f"train_samples={len(X_train)}, val_samples={len(X_val)}"
        )
        
        self.history = self.model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=verbose,
        )
        
        self.is_fitted = True
        logger.info("✅ 模型训练完成")
        
        return {
            "history": self.history.history,
            "epochs_trained": len(self.history.history["loss"]),
            "best_val_loss": min(self.history.history["val_loss"]),
        }
    
    def predict(
        self,
        X: np.ndarray,
        scaled: bool = False,
    ) -> np.ndarray:
        """
        预测
        
        Args:
            X: 输入特征 (samples, lookback, features)
            scaled: 输入是否已归一化
            
        Returns:
            预测值
        """
        if not self.is_fitted:
            raise RuntimeError("模型尚未训练，请先调用 train() 方法")
        
        predictions = self.model.predict(X, verbose=0)
        
        # 如果输入未归一化且输出是单步预测，反归一化
        if not scaled and predictions.shape[-1] == 1:
            predictions = self.inverse_transform(predictions)
        
        return predictions
    
    def predict_recursive(
        self,
        last_sequence: np.ndarray,
        steps: int,
    ) -> np.ndarray:
        """
        递归多步预测
        
        使用滚动预测方式预测未来多步
        
        Args:
            last_sequence: 最后一个序列 (lookback, features)
            steps: 预测步数
            
        Returns:
            预测值数组 (steps,)
        """
        if not self.is_fitted:
            raise RuntimeError("模型尚未训练，请先调用 train() 方法")
        
        predictions = []
        current_sequence = last_sequence.copy()
        
        for _ in range(steps):
            # 重塑为 (1, lookback, features)
            X = current_sequence.reshape(1, self.lookback, -1)
            
            # 预测下一步
            pred = self.model.predict(X, verbose=0)[0, 0]
            predictions.append(pred)
            
            # 更新序列 (移除最早的值，添加预测值)
            current_sequence = np.roll(current_sequence, -1, axis=0)
            current_sequence[-1] = pred
        
        return np.array(predictions)
    
    def inverse_transform(
        self,
        predictions: np.ndarray,
    ) -> np.ndarray:
        """
        反归一化预测值
        
        Args:
            predictions: 归一化的预测值
            
        Returns:
            原始尺度的预测值
        """
        # 确保是二维数组
        if len(predictions.shape) == 1:
            predictions = predictions.reshape(-1, 1)
        
        return self.scaler.inverse_transform(predictions).flatten()
    
    def fit_transform(
        self,
        data: np.ndarray,
    ) -> np.ndarray:
        """
        拟合并转换数据 (归一化)
        
        Args:
            data: 原始数据
            
        Returns:
            归一化后的数据
        """
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)
        
        scaled = self.scaler.fit_transform(data)
        logger.info(f"数据归一化完成：范围 [{scaled.min():.3f}, {scaled.max():.3f}]")
        return scaled.flatten()
    
    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> Dict[str, float]:
        """
        评估预测性能
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            评估指标字典 (MAPE, RMSE, MAE, MAPE_daily)
        """
        # 确保是一维数组
        y_true = y_true.flatten()
        y_pred = y_pred.flatten()
        
        # MAPE (平均绝对百分比误差)
        # 避免除以零
        mask = y_true != 0
        if mask.sum() > 0:
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        else:
            mape = 0.0
        
        # 每日 MAPE (更细粒度)
        mape_daily = []
        for true, pred in zip(y_true, y_pred):
            if true != 0:
                mape_daily.append(abs((true - pred) / true) * 100)
        mape_daily_avg = np.mean(mape_daily) if mape_daily else 0.0
        
        # RMSE (均方根误差)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        
        # MAE (平均绝对误差)
        mae = mean_absolute_error(y_true, y_pred)
        
        # R² (决定系数)
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        metrics = {
            "MAPE": mape,
            "MAPE_daily_avg": mape_daily_avg,
            "RMSE": rmse,
            "MAE": mae,
            "R2": r2,
        }
        
        logger.info(
            f"评估结果：MAPE={mape:.2f}%, RMSE={rmse:.2f}, "
            f"MAE={mae:.2f}, R²={r2:.4f}"
        )
        
        return metrics
    
    def save_model(self, path: str) -> None:
        """
        保存模型
        
        Args:
            path: 保存路径 (.keras 或 .h5)
        """
        if not self.is_fitted:
            raise RuntimeError("模型尚未训练，无法保存")
        
        # 确保目录存在
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        # 保存模型
        self.model.save(path)
        
        # 保存 scaler
        import pickle
        scaler_path = str(Path(path).with_suffix(".pkl"))
        with open(scaler_path, "wb") as f:
            pickle.dump(self.scaler, f)
        
        # 保存配置
        config = {
            "lookback": self.lookback,
            "forecast_horizon": self.forecast_horizon,
            "lstm_units": self.lstm_units,
            "dropout": self.dropout,
            "learning_rate": self.learning_rate,
            "random_state": self.random_state,
        }
        config_path = str(Path(path).with_suffix(".json"))
        import json
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"✅ 模型已保存：{path}")
    
    def load_model(self, path: str) -> None:
        """
        加载模型
        
        Args:
            path: 模型路径 (.keras 或 .h5)
        """
        # 加载模型
        self.model = load_model(path)
        
        # 加载 scaler
        import pickle
        scaler_path = str(Path(path).with_suffix(".pkl"))
        with open(scaler_path, "rb") as f:
            self.scaler = pickle.load(f)
        
        # 加载配置
        config_path = str(Path(path).with_suffix(".json"))
        import json
        with open(config_path, "r") as f:
            config = json.load(f)
        
        self.lookback = config["lookback"]
        self.forecast_horizon = config["forecast_horizon"]
        self.lstm_units = config["lstm_units"]
        self.dropout = config["dropout"]
        self.learning_rate = config["learning_rate"]
        self.random_state = config["random_state"]
        
        self.is_fitted = True
        logger.info(f"✅ 模型已加载：{path}")
    
    def get_feature_importance(
        self,
        X: np.ndarray,
        method: str = "permutation",
    ) -> np.ndarray:
        """
        计算特征重要性 (实验性)
        
        Args:
            X: 输入数据
            method: 计算方法 (permutation)
            
        Returns:
            特征重要性数组
        """
        if not self.is_fitted:
            raise RuntimeError("模型尚未训练")
        
        # 基线预测
        baseline_pred = self.model.predict(X, verbose=0)
        baseline_mse = np.mean((baseline_pred - self.model.predict(X, verbose=0)) ** 2)
        
        importance = np.zeros(self.lookback)
        
        # 对每个时间步进行扰动
        for t in range(self.lookback):
            X_perturbed = X.copy()
            # 打乱第 t 个时间步
            np.random.shuffle(X_perturbed[:, t, :])
            
            perturbed_pred = self.model.predict(X_perturbed, verbose=0)
            perturbed_mse = np.mean((perturbed_pred - self.model.predict(X, verbose=0)) ** 2)
            
            importance[t] = perturbed_mse - baseline_mse
        
        # 归一化
        if importance.sum() > 0:
            importance = importance / importance.sum()
        
        return importance


def quick_lstm_forecast(
    sales_data: np.ndarray,
    forecast_days: int = 30,
    lookback: int = 60,
    verbose: bool = True,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    快速 LSTM 预测快捷函数
    
    Args:
        sales_data: 历史销售数据
        forecast_days: 预测天数
        lookback: 回溯窗口
        verbose: 是否打印日志
        
    Returns:
        predictions: 预测值
        metrics: 评估指标
    """
    if verbose:
        logger.info(f"开始快速 LSTM 预测：{len(sales_data)} 天历史数据")
    
    # 创建预测器
    predictor = LSTMPredictor(
        lookback=lookback,
        forecast_horizon=forecast_days,
        lstm_units=[50, 25],
        dropout=0.2,
    )
    
    # 归一化数据
    scaled_data = predictor.fit_transform(sales_data)
    
    # 准备序列
    X, y = predictor.prepare_sequences(scaled_data)
    
    # 划分训练/验证集 (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    
    # 构建并训练模型
    predictor.build_model((lookback, 1))
    predictor.train(
        X_train, y_train,
        X_val, y_val,
        epochs=50,
        batch_size=32,
        verbose=1 if verbose else 0,
    )
    
    # 预测
    predictions_scaled = predictor.predict(X_val)
    predictions = predictor.inverse_transform(predictions_scaled)
    
    # 评估
    y_true = predictor.inverse_transform(y_val.reshape(-1, 1))
    metrics = predictor.evaluate(y_true, predictions)
    
    if verbose:
        logger.info(f"✅ 快速 LSTM 预测完成：MAPE={metrics['MAPE']:.2f}%")
    
    return predictions, metrics


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 生成模拟数据
    np.random.seed(42)
    days = 365
    trend = np.linspace(100, 200, days)
    seasonality = 20 * np.sin(np.arange(days) * 2 * np.pi / 7)
    noise = np.random.randn(days) * 10
    sales = trend + seasonality + noise
    
    # 快速预测测试
    predictions, metrics = quick_lstm_forecast(
        sales,
        forecast_days=30,
        lookback=60,
        verbose=True,
    )
    
    print("\n" + "=" * 50)
    print("LSTM 预测测试结果")
    print("=" * 50)
    print(f"MAPE: {metrics['MAPE']:.2f}%")
    print(f"RMSE: {metrics['RMSE']:.2f}")
    print(f"MAE: {metrics['MAE']:.2f}")
    print(f"R²: {metrics['R2']:.4f}")
    print("=" * 50)
