"""
LSTM 超参数调优模块 (v2.4 Phase 2)

使用 Keras Tuner 进行自动化超参数搜索

功能:
- 自动搜索最优 LSTM 架构
- 学习率调优
- Dropout 率调优
- 层数和单元数调优

Author: OpenClaw Imperial - Gongbu Shangshu
Version: 2.4.0 Phase 2
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

try:
    import keras_tuner as kt
    TUNER_AVAILABLE = True
except ImportError:
    TUNER_AVAILABLE = False
    logging.warning("keras-tuner 未安装，超参数调优功能将不可用")

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

logger = logging.getLogger(__name__)


class LSTMHyperModel(kt.HyperModel if TUNER_AVAILABLE else object):
    """
    LSTM 超模型 (用于 Keras Tuner)
    
    自动搜索最优的:
    - LSTM 层数
    - 每层单元数
    - Dropout 率
    - 学习率
    - 全连接层配置
    """
    
    def __init__(
        self,
        lookback: int = 60,
        forecast_horizon: int = 30,
        max_layers: int = 3,
        max_units: int = 128,
        min_units: int = 16,
    ):
        """
        初始化超模型
        
        Args:
            lookback: 回溯窗口
            forecast_horizon: 预测范围
            max_layers: 最大 LSTM 层数
            max_units: 最大单元数
            min_units: 最小单元数
        """
        self.lookback = lookback
        self.forecast_horizon = forecast_horizon
        self.max_layers = max_layers
        self.max_units = max_units
        self.min_units = min_units
    
    def build(self, hp: kt.HyperParameters) -> keras.Model:
        """
        构建模型 (由 Keras Tuner 调用)
        
        Args:
            hp: 超参数对象
            
        Returns:
            编译好的 Keras 模型
        """
        model = keras.Sequential()
        
        # 输入层
        model.add(
            layers.Input(shape=(self.lookback, 1))
        )
        
        # LSTM 层 (可变层数)
        num_layers = hp.Int("num_lstm_layers", 1, self.max_layers, default=2)
        
        for i in range(num_layers):
            # 每层单元数
            units = hp.Int(
                f"lstm_units_{i}",
                self.min_units,
                self.max_units,
                step=16,
                default=64,
            )
            
            # 是否返回序列 (最后一层不返回)
            return_sequences = i < num_layers - 1
            
            model.add(
                layers.LSTM(
                    units,
                    return_sequences=return_sequences,
                    activation="tanh",
                    recurrent_activation="hard_sigmoid",
                )
            )
            
            # Dropout
            dropout = hp.Float(
                f"dropout_{i}",
                0.0,
                0.5,
                step=0.1,
                default=0.2,
            )
            model.add(layers.Dropout(dropout))
        
        # 全连接层
        dense_units = hp.Int(
            "dense_units",
            16,
            64,
            step=16,
            default=32,
        )
        model.add(layers.Dense(dense_units, activation="relu"))
        
        # 输出层 Dropout
        final_dropout = hp.Float(
            "final_dropout",
            0.0,
            0.3,
            step=0.1,
            default=0.1,
        )
        model.add(layers.Dropout(final_dropout))
        
        # 输出层
        model.add(layers.Dense(1, activation="linear"))
        
        # 学习率
        learning_rate = hp.Float(
            "learning_rate",
            1e-4,
            1e-2,
            sampling="log",
            default=0.001,
        )
        
        # 编译模型
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss="mse",
            metrics=["mae", "mape"],
        )
        
        return model


def tune_lstm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    lookback: int = 60,
    forecast_horizon: int = 30,
    max_trials: int = 20,
    epochs: int = 50,
    batch_size: int = 32,
    project_name: str = "lstm_tuning",
    directory: str = "./keras_tuner_dir",
    overwrite: bool = True,
    verbose: bool = True,
) -> Tuple[kt.HyperModel, Dict[str, Any]]:
    """
    执行超参数调优
    
    Args:
        X_train: 训练特征
        y_train: 训练目标
        X_val: 验证特征
        y_val: 验证目标
        lookback: 回溯窗口
        forecast_horizon: 预测范围
        max_trials: 最大试验次数
        epochs: 每轮训练 epoch 数
        batch_size: 批次大小
        project_name: 项目名称
        directory: 结果保存目录
        overwrite: 是否覆盖已有结果
        verbose: 是否打印日志
        
    Returns:
        最佳超模型和结果字典
    """
    if not TUNER_AVAILABLE:
        raise ImportError(
            "keras-tuner 未安装。请运行：pip install keras-tuner"
        )
    
    logger.info(f"开始超参数搜索：max_trials={max_trials}")
    
    # 创建超模型
    hypermodel = LSTMHyperModel(
        lookback=lookback,
        forecast_horizon=forecast_horizon,
    )
    
    # 创建 Tuner
    tuner = kt.BayesianOptimization(
        hypermodel,
        objective="val_loss",
        max_trials=max_trials,
        seed=42,
        directory=directory,
        project_name=project_name,
        overwrite=overwrite,
    )
    
    # 配置回调
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=10,
            restore_best_weights=True,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
        ),
    ]
    
    # 执行搜索
    search_summary = tuner.search_space_summary()
    
    tuner.search(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1 if verbose else 0,
    )
    
    # 获取最佳超参数
    best_hps = tuner.get_best_hyperparameters(num_trials=1)[0]
    
    # 构建最佳模型
    best_model = tuner.hypermodel.build(best_hps)
    
    # 结果摘要
    results = {
        "best_val_loss": tuner.get_best_models()[0].evaluate(X_val, y_val, verbose=0)[0],
        "best_hyperparameters": {
            "num_lstm_layers": best_hps.get("num_lstm_layers"),
            "learning_rate": best_hps.get("learning_rate"),
            "dense_units": best_hps.get("dense_units"),
        },
        "total_trials": max_trials,
        "search_summary": search_summary,
    }
    
    logger.info(f"✅ 超参数搜索完成")
    logger.info(f"最佳验证损失：{results['best_val_loss']:.4f}")
    
    return best_model, results


def get_best_hyperparameters(
    directory: str = "./keras_tuner_dir",
    project_name: str = "lstm_tuning",
) -> Dict[str, Any]:
    """
    从已有调优结果中获取最佳超参数
    
    Args:
        directory: 结果目录
        project_name: 项目名称
        
    Returns:
        最佳超参数字典
    """
    if not TUNER_AVAILABLE:
        raise ImportError("keras-tuner 未安装")
    
    tuner = kt.BayesianOptimization.load_tuner(
        directory=Path(directory) / project_name,
    )
    
    best_hps = tuner.get_best_hyperparameters(num_trials=1)[0]
    
    return {
        "num_lstm_layers": best_hps.get("num_lstm_layers"),
        "lstm_units_0": best_hps.get("lstm_units_0"),
        "lstm_units_1": best_hps.get("lstm_units_1") if best_hps.get("num_lstm_layers", 1) > 1 else None,
        "dropout_0": best_hps.get("dropout_0"),
        "dense_units": best_hps.get("dense_units"),
        "final_dropout": best_hps.get("final_dropout"),
        "learning_rate": best_hps.get("learning_rate"),
    }


def quick_tune(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    max_trials: int = 10,
    epochs: int = 30,
) -> Dict[str, Any]:
    """
    快速超参数调优 (简化版)
    
    Args:
        X_train: 训练特征
        y_train: 训练目标
        X_val: 验证特征
        y_val: 验证目标
        max_trials: 最大试验次数
        epochs: 训练轮数
        
    Returns:
        最佳超参数和性能指标
    """
    lookback = X_train.shape[1]
    
    best_model, results = tune_lstm(
        X_train, y_train,
        X_val, y_val,
        lookback=lookback,
        max_trials=max_trials,
        epochs=epochs,
        verbose=True,
    )
    
    return results


def manual_grid_search(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    param_grid: Dict[str, List[Any]],
    epochs: int = 50,
    batch_size: int = 32,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    手动网格搜索 (不依赖 Keras Tuner)
    
    Args:
        X_train: 训练特征
        y_train: 训练目标
        X_val: 验证特征
        y_val: 验证目标
        param_grid: 参数网格字典
        epochs: 训练轮数
        batch_size: 批次大小
        verbose: 是否打印日志
        
    Returns:
        最佳参数和结果
    """
    from itertools import product
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
    from tensorflow.keras.optimizers import Adam
    
    logger.info("开始手动网格搜索")
    
    best_val_loss = float("inf")
    best_params = {}
    best_model = None
    
    # 生成所有参数组合
    keys, values = zip(*param_grid.items())
    combinations = list(product(*values))
    
    total = len(combinations)
    logger.info(f"总组合数：{total}")
    
    for i, combo in enumerate(combinations):
        params = dict(zip(keys, combo))
        
        if verbose:
            logger.info(f"[{i+1}/{total}] 测试参数：{params}")
        
        # 构建模型
        model = Sequential()
        model.add(Input(shape=(X_train.shape[1], X_train.shape[2])))
        
        # LSTM 层
        lstm_units = params.get("lstm_units", [50])
        dropout = params.get("dropout", 0.2)
        
        for j, units in enumerate(lstm_units if isinstance(lstm_units, list) else [lstm_units]):
            model.add(LSTM(units, return_sequences=(j < len(lstm_units) - 1)))
            model.add(Dropout(dropout))
        
        # 全连接层
        dense_units = params.get("dense_units", 32)
        model.add(Dense(dense_units, activation="relu"))
        model.add(Dropout(dropout / 2))
        model.add(Dense(1))
        
        # 编译
        lr = params.get("learning_rate", 0.001)
        model.compile(
            optimizer=Adam(learning_rate=lr),
            loss="mse",
            metrics=["mae"],
        )
        
        # 训练
        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            verbose=0,
        )
        
        val_loss = min(history.history["val_loss"])
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_params = params
            best_model = model
        
        if verbose:
            logger.info(f"  验证损失：{val_loss:.4f}")
    
    logger.info(f"✅ 网格搜索完成")
    logger.info(f"最佳参数：{best_params}")
    logger.info(f"最佳验证损失：{best_val_loss:.4f}")
    
    return {
        "best_params": best_params,
        "best_val_loss": best_val_loss,
        "best_model": best_model,
        "total_combinations": total,
    }


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 生成模拟数据
    np.random.seed(42)
    n_samples = 1000
    lookback = 60
    
    X = np.random.randn(n_samples, lookback, 1)
    y = np.random.randn(n_samples)
    
    # 划分数据
    split = int(0.8 * n_samples)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    
    print("\n" + "=" * 50)
    print("超参数调优模块测试")
    print("=" * 50)
    
    if TUNER_AVAILABLE:
        print("Keras Tuner 可用 ✓")
        
        # 手动网格搜索测试
        param_grid = {
            "lstm_units": [[32], [64], [32, 16]],
            "dropout": [0.1, 0.2, 0.3],
            "learning_rate": [0.001, 0.01],
        }
        
        results = manual_grid_search(
            X_train, y_train,
            X_val, y_val,
            param_grid=param_grid,
            epochs=10,
            verbose=True,
        )
        
        print(f"\n最佳参数：{results['best_params']}")
        print(f"最佳验证损失：{results['best_val_loss']:.4f}")
    else:
        print("Keras Tuner 不可用，请安装：pip install keras-tuner")
    
    print("=" * 50)
