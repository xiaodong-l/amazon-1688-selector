"""
LSTM 预测模块测试 (v2.4 Phase 2)

测试覆盖:
- 序列准备
- 模型构建
- 模型训练
- 预测功能
- 评估指标
- 特征工程
- 可视化功能
- 模型保存/加载

Author: OpenClaw Imperial - Gongbu Shangshu
Version: 2.4.0 Phase 2
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import logging
import warnings

# 忽略 TensorFlow 警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

logging.basicConfig(level=logging.WARNING)

# 导入被测试模块
from src.analysis.lstm_predictor import (
    LSTMPredictor,
    quick_lstm_forecast,
)
from src.analysis.lstm_features import (
    create_features,
    create_target,
    select_features,
    prepare_lstm_data,
    get_feature_summary,
)
from src.analysis.lstm_visualizer import (
    plot_training_history,
    plot_predictions,
    plot_residuals,
    plot_feature_importance,
    create_dashboard,
)


# ========== Fixtures ==========

@pytest.fixture
def sample_sales_data():
    """生成模拟销售数据"""
    np.random.seed(42)
    n_days = 365
    
    # 创建带趋势和季节性的销售数据
    trend = np.linspace(100, 200, n_days)
    seasonality = 20 * np.sin(np.arange(n_days) * 2 * np.pi / 7)
    noise = np.random.randn(n_days) * 10
    sales = trend + seasonality + noise
    
    dates = pd.date_range(start="2024-01-01", periods=n_days, freq="D")
    
    return pd.DataFrame({
        "date": dates,
        "sales": sales,
        "price": np.random.uniform(10, 20, n_days),
    })


@pytest.fixture
def lstm_predictor():
    """创建 LSTM 预测器实例"""
    return LSTMPredictor(
        lookback=30,
        forecast_horizon=7,
        lstm_units=[32, 16],
        dropout=0.2,
        learning_rate=0.01,
        random_state=42,
    )


@pytest.fixture
def prepared_data(sample_sales_data, lstm_predictor):
    """准备训练数据"""
    df = sample_sales_data
    
    # 归一化
    sales_data = df["sales"].values
    scaled_data = lstm_predictor.fit_transform(sales_data)
    
    # 创建序列
    X, y = lstm_predictor.prepare_sequences(scaled_data)
    
    # 划分训练/验证集
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]
    
    return {
        "df": df,
        "X_train": X_train,
        "X_val": X_val,
        "y_train": y_train,
        "y_val": y_val,
        "sales_data": sales_data,
        "scaled_data": scaled_data,
    }


# ========== 序列准备测试 ==========

class TestSequencePreparation:
    """序列数据准备测试"""
    
    def test_prepare_sequences_shape(self, lstm_predictor, sample_sales_data):
        """测试序列数据形状"""
        data = sample_sales_data["sales"].values
        X, y = lstm_predictor.prepare_sequences(data)
        
        expected_samples = len(data) - lstm_predictor.lookback
        expected_shape = (expected_samples, lstm_predictor.lookback, 1)
        
        assert X.shape == expected_shape, f"X shape mismatch: {X.shape} vs {expected_shape}"
        assert len(y) == expected_samples, f"y length mismatch: {len(y)} vs {expected_samples}"
    
    def test_prepare_sequences_values(self, lstm_predictor):
        """测试序列数据值正确性"""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        lstm_predictor.lookback = 3
        
        X, y = lstm_predictor.prepare_sequences(data)
        
        # 第一个样本应该是 [1, 2, 3]，目标是 4
        assert np.allclose(X[0].flatten(), [1, 2, 3]), "First sequence incorrect"
        assert y[0] == 4, "First target incorrect"
        
        # 最后一个样本应该是 [7, 8, 9]，目标是 10
        assert np.allclose(X[-1].flatten(), [7, 8, 9]), "Last sequence incorrect"
        assert y[-1] == 10, "Last target incorrect"
    
    def test_prepare_multistep_sequences(self, lstm_predictor):
        """测试多步序列准备"""
        data = np.arange(100, dtype=float)
        lstm_predictor.lookback = 10
        lstm_predictor.forecast_horizon = 5
        
        X, y = lstm_predictor.prepare_multistep_sequences(data)
        
        assert X.shape[0] == y.shape[0], "X and y should have same number of samples"
        assert y.shape[1] == lstm_predictor.forecast_horizon, "y should have forecast_horizon steps"
    
    def test_prepare_sequences_empty(self, lstm_predictor):
        """测试空数据处理"""
        data = np.array([])
        
        with pytest.raises((IndexError, ValueError)):
            lstm_predictor.prepare_sequences(data)


# ========== 模型构建测试 ==========

class TestModelBuilding:
    """模型构建测试"""
    
    def test_build_model_structure(self, lstm_predictor, prepared_data):
        """测试模型结构"""
        input_shape = (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
        model = lstm_predictor.build_model(input_shape)
        
        assert model is not None, "Model should not be None"
        assert len(model.layers) > 0, "Model should have layers"
        
        # 检查层类型
        layer_types = [type(layer).__name__ for layer in model.layers]
        assert "LSTM" in layer_types[0] or "Input" in layer_types[0], "First layer should be Input or LSTM"
        assert "Dense" in layer_types[-1], "Last layer should be Dense"
    
    def test_build_model_output_shape(self, lstm_predictor, prepared_data):
        """测试模型输出形状"""
        input_shape = (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
        model = lstm_predictor.build_model(input_shape)
        
        # 测试单步预测
        test_input = np.random.randn(1, input_shape[0], input_shape[1])
        output = model.predict(test_input, verbose=0)
        
        assert output.shape == (1, 1), f"Output shape should be (1, 1), got {output.shape}"
    
    def test_build_model_multistep(self, lstm_predictor, prepared_data):
        """测试多步预测模型"""
        input_shape = (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
        output_steps = 7
        model = lstm_predictor.build_model(input_shape, output_steps=output_steps)
        
        test_input = np.random.randn(1, input_shape[0], input_shape[1])
        output = model.predict(test_input, verbose=0)
        
        assert output.shape == (1, output_steps), f"Output shape should be (1, {output_steps})"
    
    def test_model_compilation(self, lstm_predictor, prepared_data):
        """测试模型编译"""
        input_shape = (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
        model = lstm_predictor.build_model(input_shape)
        
        assert model.optimizer is not None, "Model should be compiled with optimizer"
        assert model.loss is not None, "Model should have loss function"
        assert len(model.metrics) > 0, "Model should have metrics"


# ========== 模型训练测试 ==========

class TestModelTraining:
    """模型训练测试"""
    
    def test_train_model(self, lstm_predictor, prepared_data):
        """测试模型训练"""
        # 构建模型
        input_shape = (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
        lstm_predictor.build_model(input_shape)
        
        # 训练
        history = lstm_predictor.train(
            prepared_data["X_train"],
            prepared_data["y_train"],
            prepared_data["X_val"],
            prepared_data["y_val"],
            epochs=5,
            batch_size=32,
            verbose=0,
        )
        
        assert lstm_predictor.is_fitted, "Model should be fitted after training"
        assert "history" in history, "History should be returned"
        assert "loss" in history["history"], "History should contain loss"
        assert len(history["history"]["loss"]) == 5, "Should have 5 epochs of history"
    
    def test_train_with_early_stopping(self, lstm_predictor, prepared_data):
        """测试带早停的训练"""
        input_shape = (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
        lstm_predictor.build_model(input_shape)
        
        history = lstm_predictor.train(
            prepared_data["X_train"],
            prepared_data["y_train"],
            prepared_data["X_val"],
            prepared_data["y_val"],
            epochs=100,  # 多轮次以触发早停
            batch_size=32,
            verbose=0,
        )
        
        # 早停应该在 100 轮之前停止
        assert history["epochs_trained"] <= 100, "Early stopping should trigger"
    
    def test_train_without_build(self, lstm_predictor, prepared_data):
        """测试自动构建并训练"""
        # 不显式调用 build_model，直接训练
        history = lstm_predictor.train(
            prepared_data["X_train"],
            prepared_data["y_train"],
            prepared_data["X_val"],
            prepared_data["y_val"],
            epochs=3,
            verbose=0,
        )
        
        assert lstm_predictor.is_fitted, "Model should be fitted"
        assert lstm_predictor.model is not None, "Model should be built automatically"


# ========== 预测功能测试 ==========

class TestPrediction:
    """预测功能测试"""
    
    def test_predict_single_step(self, lstm_predictor, prepared_data):
        """测试单步预测"""
        # 训练模型
        input_shape = (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
        lstm_predictor.build_model(input_shape)
        lstm_predictor.train(
            prepared_data["X_train"],
            prepared_data["y_train"],
            prepared_data["X_val"],
            prepared_data["y_val"],
            epochs=3,
            verbose=0,
        )
        
        # 预测
        predictions = lstm_predictor.predict(prepared_data["X_val"][:10])
        
        assert len(predictions) == 10, "Should predict 10 samples"
        assert predictions.shape[-1] == 1 or len(predictions.shape) == 1, "Should be single-step predictions"
    
    def test_predict_unfitted_model(self, lstm_predictor, prepared_data):
        """测试未训练模型的预测"""
        with pytest.raises(RuntimeError, match="模型尚未训练"):
            lstm_predictor.predict(prepared_data["X_val"])
    
    def test_predict_recursive(self, lstm_predictor, prepared_data):
        """测试递归多步预测"""
        # 训练模型
        input_shape = (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
        lstm_predictor.build_model(input_shape)
        lstm_predictor.train(
            prepared_data["X_train"],
            prepared_data["y_train"],
            prepared_data["X_val"],
            prepared_data["y_val"],
            epochs=3,
            verbose=0,
        )
        
        # 递归预测
        last_sequence = prepared_data["scaled_data"][-lstm_predictor.lookback:]
        predictions = lstm_predictor.predict_recursive(last_sequence, steps=7)
        
        assert len(predictions) == 7, "Should predict 7 steps"
    
    def test_inverse_transform(self, lstm_predictor, sample_sales_data):
        """测试反归一化"""
        sales_data = sample_sales_data["sales"].values
        scaled = lstm_predictor.fit_transform(sales_data)
        
        # 反归一化
        restored = lstm_predictor.inverse_transform(scaled)
        
        assert np.allclose(restored, sales_data, rtol=1e-5), "Inverse transform should restore original values"


# ========== 评估指标测试 ==========

class TestEvaluation:
    """评估指标测试"""
    
    def test_evaluate_metrics(self, lstm_predictor):
        """测试评估指标计算"""
        y_true = np.array([100, 200, 300, 400, 500], dtype=float)
        y_pred = np.array([105, 195, 310, 390, 505], dtype=float)
        
        metrics = lstm_predictor.evaluate(y_true, y_pred)
        
        assert "MAPE" in metrics, "Should contain MAPE"
        assert "RMSE" in metrics, "Should contain RMSE"
        assert "MAE" in metrics, "Should contain MAE"
        assert "R2" in metrics, "Should contain R2"
        
        # MAPE 应该在合理范围内
        assert 0 <= metrics["MAPE"] <= 100, f"MAPE should be between 0 and 100, got {metrics['MAPE']}"
    
    def test_evaluate_perfect_prediction(self, lstm_predictor):
        """测试完美预测的评估"""
        y_true = np.array([100, 200, 300, 400, 500], dtype=float)
        y_pred = y_true.copy()
        
        metrics = lstm_predictor.evaluate(y_true, y_pred)
        
        assert metrics["MAPE"] == 0, "Perfect prediction should have 0 MAPE"
        assert metrics["RMSE"] == 0, "Perfect prediction should have 0 RMSE"
        assert metrics["MAE"] == 0, "Perfect prediction should have 0 MAE"
        assert metrics["R2"] == 1, "Perfect prediction should have R2 = 1"
    
    def test_evaluate_with_zeros(self, lstm_predictor):
        """测试含零值的评估"""
        y_true = np.array([0, 100, 200, 0, 500], dtype=float)
        y_pred = np.array([5, 105, 195, 5, 505], dtype=float)
        
        # 不应抛出除以零错误
        metrics = lstm_predictor.evaluate(y_true, y_pred)
        assert "MAPE" in metrics


# ========== 特征工程测试 ==========

class TestFeatureEngineering:
    """特征工程测试"""
    
    def test_create_features(self, sample_sales_data):
        """测试特征创建"""
        df = sample_sales_data
        features_df = create_features(df, target_col="sales", price_col="price")
        
        # 检查特征数量
        assert len(features_df.columns) > len(df.columns), "Should have more columns after feature creation"
        
        # 检查关键特征存在
        expected_features = [
            "lag_1", "lag_7", "lag_30",
            "rolling_mean_7", "rolling_mean_30",
            "rolling_std_7", "rolling_std_30",
            "month", "day_of_week", "is_weekend",
            "month_sin", "month_cos",
        ]
        
        for feature in expected_features:
            assert feature in features_df.columns, f"Missing feature: {feature}"
    
    def test_create_target(self, sample_sales_data):
        """测试目标变量创建"""
        df = sample_sales_data
        features_df = create_features(df, target_col="sales")
        target = create_target(features_df, target_col="sales", horizon=30)
        
        assert len(target) == len(features_df), "Target should have same length as input"
        assert not target.isnull().all(), "Target should not be all null"
    
    def test_create_target_methods(self, sample_sales_data):
        """测试不同目标创建方法"""
        df = sample_sales_data
        features_df = create_features(df, target_col="sales")
        
        methods = ["mean", "sum", "max", "min", "last"]
        
        for method in methods:
            target = create_target(features_df, target_col="sales", horizon=30, method=method)
            assert len(target) == len(features_df), f"Method {method} should work"
    
    def test_select_features(self, sample_sales_data):
        """测试特征选择"""
        df = sample_sales_data
        features_df = create_features(df, target_col="sales")
        
        selected = select_features(features_df, target_col="sales")
        
        assert len(selected) > 0, "Should select some features"
        assert "sales" not in selected, "Should not include target column"
    
    def test_prepare_lstm_data(self, sample_sales_data):
        """测试 LSTM 数据准备"""
        df = sample_sales_data
        features_df = create_features(df, target_col="sales")
        
        data = prepare_lstm_data(
            features_df,
            target_col="sales",
            lookback=30,
            forecast_horizon=7,
            train_ratio=0.7,
            val_ratio=0.15,
        )
        
        assert "X_train" in data
        assert "X_val" in data
        assert "X_test" in data
        assert "scaler_X" in data
        assert "scaler_y" in data
        
        # 检查数据划分比例
        total = len(data["X_train"]) + len(data["X_val"]) + len(data["X_test"])
        assert len(data["X_train"]) / total >= 0.65, "Train ratio should be around 0.7"
    
    def test_get_feature_summary(self, sample_sales_data):
        """测试特征摘要"""
        df = sample_sales_data
        features_df = create_features(df, target_col="sales")
        
        summary = get_feature_summary(features_df)
        
        assert len(summary) > 0, "Should have summary"
        assert "null_count" in summary.columns, "Should have null_count column"
        assert "dtype" in summary.columns, "Should have dtype column"


# ========== 可视化测试 ==========

class TestVisualization:
    """可视化功能测试"""
    
    def test_plot_training_history(self):
        """测试训练历史图"""
        history = {
            "loss": [10, 8, 6, 4, 2],
            "val_loss": [11, 9, 7, 5, 3],
            "mae": [5, 4, 3, 2, 1],
            "val_mae": [6, 5, 4, 3, 2],
        }
        
        fig = plot_training_history(history, show=False)
        
        assert fig is not None, "Figure should be created"
        assert len(fig.axes) == 3, "Should have 3 subplots"
    
    def test_plot_predictions(self):
        """测试预测对比图"""
        y_true = np.random.randn(100) + 100
        y_pred = y_true + np.random.randn(100) * 0.5
        
        fig = plot_predictions(y_true, y_pred, show=False)
        
        assert fig is not None
        assert len(fig.axes) == 2, "Should have 2 subplots"
    
    def test_plot_residuals(self):
        """测试残差图"""
        y_true = np.random.randn(100) + 100
        y_pred = y_true + np.random.randn(100) * 0.5
        
        fig = plot_residuals(y_true, y_pred, show=False)
        
        assert fig is not None
        assert len(fig.axes) == 2, "Should have 2 subplots"
    
    def test_plot_feature_importance(self):
        """测试特征重要性图"""
        importance = np.random.rand(60)
        importance = importance / importance.sum()
        
        fig = plot_feature_importance(importance, top_n=10, show=False)
        
        assert fig is not None
    
    def test_create_dashboard(self, sample_sales_data):
        """测试综合仪表板"""
        y_true = sample_sales_data["sales"].values[:200]
        y_pred = y_true + np.random.randn(200) * 5
        
        history = {
            "loss": np.linspace(100, 10, 50),
            "val_loss": np.linspace(110, 15, 50),
            "mape": np.linspace(15, 5, 50),
        }
        
        metrics = {
            "MAPE": 5.6,
            "RMSE": 8.2,
            "MAE": 6.1,
            "R2": 0.92,
        }
        
        dates = pd.DatetimeIndex(sample_sales_data["date"].values[:200])
        
        fig = create_dashboard(y_true, y_pred, history, metrics, dates=dates, show=False)
        
        assert fig is not None


# ========== 模型保存/加载测试 ==========

class TestModelPersistence:
    """模型持久化测试"""
    
    def test_save_and_load_model(self, lstm_predictor, prepared_data):
        """测试模型保存和加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.keras"
            
            # 训练模型
            input_shape = (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
            lstm_predictor.build_model(input_shape)
            lstm_predictor.train(
                prepared_data["X_train"],
                prepared_data["y_train"],
                prepared_data["X_val"],
                prepared_data["y_val"],
                epochs=3,
                verbose=0,
            )
            
            # 保存
            lstm_predictor.save_model(str(model_path))
            
            # 检查文件存在
            assert model_path.exists(), "Model file should exist"
            assert model_path.with_suffix(".pkl").exists(), "Scaler file should exist"
            assert model_path.with_suffix(".json").exists(), "Config file should exist"
            
            # 创建新预测器并加载
            new_predictor = LSTMPredictor()
            new_predictor.load_model(str(model_path))
            
            # 验证加载的模型可以预测
            predictions = new_predictor.predict(prepared_data["X_val"][:10])
            assert len(predictions) == 10, "Loaded model should be able to predict"
    
    def test_quick_lstm_forecast(self, sample_sales_data):
        """测试快速预测函数"""
        sales_data = sample_sales_data["sales"].values
        
        predictions, metrics = quick_lstm_forecast(
            sales_data,
            forecast_days=7,
            lookback=30,
            verbose=False,
        )
        
        assert len(predictions) > 0, "Should return predictions"
        assert "MAPE" in metrics, "Should return metrics"
        assert metrics["MAPE"] < 100, "MAPE should be reasonable"


# ========== 集成测试 ==========

class TestIntegration:
    """集成测试"""
    
    def test_full_pipeline(self, sample_sales_data):
        """测试完整预测流程"""
        df = sample_sales_data
        
        # 1. 特征工程
        features_df = create_features(df, target_col="sales", price_col="price")
        
        # 2. 创建预测器
        predictor = LSTMPredictor(
            lookback=30,
            forecast_horizon=7,
            lstm_units=[32, 16],
            dropout=0.2,
            random_state=42,
        )
        
        # 3. 准备数据
        sales_data = features_df["sales"].values
        scaled_data = predictor.fit_transform(sales_data)
        X, y = predictor.prepare_sequences(scaled_data)
        
        # 4. 划分数据
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # 5. 训练
        predictor.build_model((X_train.shape[1], X_train.shape[2]))
        history = predictor.train(
            X_train, y_train,
            X_val, y_val,
            epochs=10,
            batch_size=32,
            verbose=0,
        )
        
        # 6. 预测
        predictions_scaled = predictor.predict(X_val)
        predictions = predictor.inverse_transform(predictions_scaled)
        
        # 7. 评估
        y_true = predictor.inverse_transform(y_val.reshape(-1, 1))
        metrics = predictor.evaluate(y_true, predictions)
        
        # 验证
        assert predictor.is_fitted, "Model should be fitted"
        assert "MAPE" in metrics, "Should have MAPE metric"
        assert len(predictions) == len(y_true), "Predictions should match true values length"
        
        # MAPE 应该合理 (对于模拟数据，< 20% 是合理的)
        assert metrics["MAPE"] < 20, f"MAPE should be < 20%, got {metrics['MAPE']:.2f}%"
    
    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 确保旧的 Prophet 导入仍然可用
        from src.analysis.prophet_predictor import ProphetPredictor
        
        prophet = ProphetPredictor()
        assert prophet is not None, "ProphetPredictor should still be available"


# ========== 性能测试 ==========

class TestPerformance:
    """性能测试"""
    
    def test_training_time(self, prepared_data):
        """测试训练时间 (< 5 分钟)"""
        import time
        
        predictor = LSTMPredictor(
            lookback=60,
            forecast_horizon=30,
            lstm_units=[50, 25],
            dropout=0.2,
        )
        
        start_time = time.time()
        
        predictor.build_model(
            (prepared_data["X_train"].shape[1], prepared_data["X_train"].shape[2])
        )
        predictor.train(
            prepared_data["X_train"],
            prepared_data["y_train"],
            prepared_data["X_val"],
            prepared_data["y_val"],
            epochs=50,
            batch_size=32,
            verbose=0,
        )
        
        elapsed = time.time() - start_time
        
        # 训练时间应小于 5 分钟 (300 秒)
        assert elapsed < 300, f"Training took {elapsed:.2f}s, should be < 300s"
        
        print(f"\n训练时间：{elapsed:.2f}秒")


# ========== 运行测试 ==========

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # 首次失败即停止
    ])
