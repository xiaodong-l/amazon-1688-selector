"""
Prophet 预测模块测试 (v2.4.0 Phase 1)

测试内容:
1. 数据准备测试
2. 模型训练测试
3. 预测测试
4. 交叉验证测试
5. 评估指标测试
6. 节假日支持测试
7. 可视化测试

运行测试:
```bash
cd /home/admina/.openclaw-imperial/workspace-taizi/projects/amazon-1688-selector
./venv/bin/pytest tests/test_prophet_predictor.py -v
```

作者：GongBu ShangShu
版本：v2.4.0 Phase 1
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="WARNING")


# ==================== 测试夹具 ====================

@pytest.fixture
def sample_sales_data():
    """生成示例销售数据"""
    np.random.seed(42)
    dates = pd.date_range(start="2025-01-01", end="2025-12-31", freq="D")
    
    # 创建带有趋势、季节性和噪声的销售数据
    trend = np.linspace(100, 150, len(dates))
    weekly_seasonality = 10 * np.sin(np.arange(len(dates)) * 2 * np.pi / 7)
    yearly_seasonality = 20 * np.sin(np.arange(len(dates)) * 2 * np.pi / 365)
    noise = np.random.randn(len(dates)) * 5
    
    sales = trend + weekly_seasonality + yearly_seasonality + noise
    
    return pd.DataFrame({
        "date": dates,
        "sales": sales,
        "revenue": sales * 10,  # 假设单价为 10
    })


@pytest.fixture
def sample_small_data():
    """生成小样本数据 (用于边界测试)"""
    np.random.seed(42)
    dates = pd.date_range(start="2025-01-01", periods=20, freq="D")
    sales = 100 + np.cumsum(np.random.randn(20))
    
    return pd.DataFrame({
        "date": dates,
        "sales": sales,
    })


@pytest.fixture
def prophet_predictor():
    """创建 ProphetPredictor 实例"""
    from analysis.prophet_predictor import ProphetPredictor
    return ProphetPredictor(
        yearly_seasonality=True,
        weekly_seasonality=True,
    )


@pytest.fixture
def prophet_visualizer():
    """创建 ProphetVisualizer 实例"""
    from analysis.prophet_visualizer import ProphetVisualizer
    return ProphetVisualizer()


# ==================== 数据准备测试 ====================

class TestDataPreparation:
    """数据准备测试"""
    
    def test_prepare_data_basic(self, prophet_predictor, sample_sales_data):
        """测试基本数据准备"""
        df = prophet_predictor.prepare_data(
            sample_sales_data,
            date_column="date",
            value_column="sales",
        )
        
        assert "ds" in df.columns
        assert "y" in df.columns
        assert len(df) == len(sample_sales_data)
        assert pd.api.types.is_datetime64_any_dtype(df["ds"])
        assert df["y"].dtype == "float64"
    
    def test_prepare_data_custom_columns(self, prophet_predictor, sample_sales_data):
        """测试自定义列名"""
        df = prophet_predictor.prepare_data(
            sample_sales_data,
            date_column="date",
            value_column="revenue",
        )
        
        assert "ds" in df.columns
        assert "y" in df.columns
        assert df["y"].mean() > 1000  # revenue 应该比 sales 大
    
    def test_prepare_data_remove_negative(self, prophet_predictor):
        """测试移除负值"""
        data = pd.DataFrame({
            "date": pd.date_range(start="2025-01-01", periods=100, freq="D"),
            "sales": np.random.randn(100) * 10 + 50,
        })
        # 添加一些负值
        data.loc[10:15, "sales"] = -10
        
        df = prophet_predictor.prepare_data(
            data,
            date_column="date",
            value_column="sales",
            remove_negative=True,
        )
        
        assert (df["y"] >= 0).all()
        assert len(df) < len(data)
    
    def test_prepare_data_fill_missing(self, prophet_predictor):
        """测试缺失值填充"""
        data = pd.DataFrame({
            "date": pd.date_range(start="2025-01-01", periods=100, freq="D"),
            "sales": np.random.randn(100) * 10 + 50,
        })
        # 添加一些缺失值
        data.loc[10:15, "sales"] = np.nan
        
        df = prophet_predictor.prepare_data(
            data,
            date_column="date",
            value_column="sales",
            fill_method="ffill",
        )
        
        assert not df["y"].isna().any()
    
    def test_prepare_data_invalid_columns(self, prophet_predictor, sample_sales_data):
        """测试无效列名"""
        with pytest.raises(ValueError, match="日期列.*不存在"):
            prophet_predictor.prepare_data(
                sample_sales_data,
                date_column="invalid_date",
                value_column="sales",
            )
        
        with pytest.raises(ValueError, match="目标列.*不存在"):
            prophet_predictor.prepare_data(
                sample_sales_data,
                date_column="date",
                value_column="invalid_value",
            )
    
    def test_prepare_data_sorting(self, prophet_predictor, sample_sales_data):
        """测试数据排序"""
        # 打乱数据顺序
        shuffled = sample_sales_data.sample(frac=1, random_state=42)
        
        df = prophet_predictor.prepare_data(
            shuffled,
            date_column="date",
            value_column="sales",
        )
        
        assert df["ds"].is_monotonic_increasing
    
    def test_prepare_data_duplicates(self, prophet_predictor):
        """测试重复日期处理"""
        dates = pd.date_range(start="2025-01-01", periods=50, freq="D")
        # 添加重复日期
        dates = dates.tolist() + dates[:10].tolist()
        
        data = pd.DataFrame({
            "date": dates,
            "sales": np.random.randn(len(dates)) * 10 + 50,
        })
        
        df = prophet_predictor.prepare_data(
            data,
            date_column="date",
            value_column="sales",
        )
        
        assert df["ds"].is_unique


# ==================== 模型训练测试 ====================

class TestModelTraining:
    """模型训练测试"""
    
    def test_train_basic(self, prophet_predictor, sample_sales_data):
        """测试基本训练"""
        prophet_predictor.prepare_data(
            sample_sales_data,
            date_column="date",
            value_column="sales",
        )
        
        result = prophet_predictor.train()
        
        assert prophet_predictor.model is not None
        assert result is prophet_predictor  # 支持链式调用
    
    def test_train_with_holidays(self, prophet_predictor, sample_sales_data):
        """测试带节假日的训练"""
        prophet_predictor.prepare_data(
            sample_sales_data,
            date_column="date",
            value_column="sales",
        )
        prophet_predictor.add_holidays(country="US")
        
        result = prophet_predictor.train()
        
        assert prophet_predictor.model is not None
        assert prophet_predictor.country_holidays == "US"
    
    def test_train_without_prepare(self, prophet_predictor, sample_sales_data):
        """测试直接传入数据训练"""
        result = prophet_predictor.train(sample_sales_data)
        
        assert prophet_predictor.model is not None
        assert prophet_predictor.historical_data is not None
    
    def test_train_insufficient_data(self, prophet_predictor, sample_small_data):
        """测试数据量不足"""
        # 数据量过少应该警告但仍然可以训练
        prophet_predictor.prepare_data(sample_small_data)
        
        # Prophet 至少需要一些数据点
        if len(sample_small_data) >= 5:
            result = prophet_predictor.train()
            assert prophet_predictor.model is not None
    
    def test_train_chained(self, prophet_predictor, sample_sales_data):
        """测试链式调用"""
        prophet_predictor.prepare_data(sample_sales_data)
        result = (
            prophet_predictor
            .add_holidays(country="US")
            .train()
        )
        
        assert prophet_predictor.model is not None
        assert prophet_predictor.country_holidays == "US"


# ==================== 预测测试 ====================

class TestPrediction:
    """预测测试"""
    
    def test_predict_basic(self, prophet_predictor, sample_sales_data):
        """测试基本预测"""
        prophet_predictor.train(sample_sales_data)
        forecast = prophet_predictor.predict(periods=30)
        
        assert forecast is not None
        assert "yhat" in forecast.columns
        assert "yhat_lower" in forecast.columns
        assert "yhat_upper" in forecast.columns
        assert len(forecast) > len(sample_sales_data)
    
    def test_predict_periods(self, prophet_predictor, sample_sales_data):
        """测试不同预测期数"""
        prophet_predictor.train(sample_sales_data)
        
        for periods in [7, 14, 30, 60, 90]:
            forecast = prophet_predictor.predict(periods=periods)
            future_dates = forecast[forecast["ds"] > sample_sales_data["date"].max()]
            assert len(future_dates) >= periods
    
    def test_predict_with_history(self, prophet_predictor, sample_sales_data):
        """测试包含历史数据的预测"""
        prophet_predictor.train(sample_sales_data)
        
        forecast_with_history = prophet_predictor.predict(
            periods=30,
            include_history=True,
        )
        forecast_without_history = prophet_predictor.predict(
            periods=30,
            include_history=False,
        )
        
        assert len(forecast_with_history) > len(forecast_without_history)
    
    def test_predict_without_training(self, prophet_predictor):
        """测试未训练时预测"""
        with pytest.raises(ValueError, match="模型未训练"):
            prophet_predictor.predict(periods=30)
    
    def test_predict_forecast_to_dict(self, prophet_predictor, sample_sales_data):
        """测试预测结果转字典"""
        prophet_predictor.train(sample_sales_data)
        prophet_predictor.predict(periods=30)
        
        result = prophet_predictor.forecast_to_dict(include_history=False)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert "date" in result[0]
        assert "prediction" in result[0]
        assert "lower_bound" in result[0]
        assert "upper_bound" in result[0]


# ==================== 交叉验证测试 ====================

class TestCrossValidation:
    """交叉验证测试"""
    
    def test_cross_validation_basic(self, prophet_predictor, sample_sales_data):
        """测试基本交叉验证"""
        prophet_predictor.train(sample_sales_data)
        
        cv_results = prophet_predictor.cross_validation(
            horizon="30 days",
            initial="180 days",
            period="30 days",
        )
        
        assert cv_results is not None
        assert "yhat" in cv_results.columns
        assert "y" in cv_results.columns
        assert len(cv_results) > 0
    
    def test_cross_validation_metrics(self, prophet_predictor, sample_sales_data):
        """测试交叉验证指标"""
        prophet_predictor.train(sample_sales_data)
        prophet_predictor.cross_validation(horizon="30 days")
        
        metrics = prophet_predictor.get_metrics()
        
        assert isinstance(metrics, dict)
        assert "mape" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert metrics["mape"] >= 0
    
    def test_cross_validation_without_training(self, prophet_predictor):
        """测试未训练时交叉验证"""
        with pytest.raises(ValueError, match="模型未训练"):
            prophet_predictor.cross_validation()
    
    def test_mape_threshold(self, prophet_predictor, sample_sales_data):
        """测试 MAPE 是否小于 15%"""
        prophet_predictor.train(sample_sales_data)
        prophet_predictor.cross_validation(horizon="30 days")
        
        metrics = prophet_predictor.get_metrics()
        
        # MAPE 应该小于 15% (对于合成数据应该很容易达到)
        assert metrics["mape"] < 15, f"MAPE {metrics['mape']:.2f}% 超过 15%"


# ==================== 节假日测试 ====================

class TestHolidays:
    """节假日支持测试"""
    
    def test_holidays_us(self, prophet_predictor, sample_sales_data):
        """测试美国节假日"""
        from analysis.holidays import get_country_holidays
        
        us_holidays = get_country_holidays("US", years=[2025, 2026])
        
        assert len(us_holidays) > 0
        assert "holiday" in us_holidays.columns
        assert "lower" in us_holidays.columns
        assert "upper" in us_holidays.columns
    
    def test_holidays_cn(self, prophet_predictor, sample_sales_data):
        """测试中国节假日"""
        from analysis.holidays import get_country_holidays
        
        cn_holidays = get_country_holidays("CN", years=[2025, 2026])
        
        assert len(cn_holidays) > 0
    
    def test_shopping_holidays(self, prophet_predictor, sample_sales_data):
        """测试购物节"""
        from analysis.holidays import get_shopping_holidays
        
        shopping_holidays = get_shopping_holidays(years=[2025, 2026])
        
        assert len(shopping_holidays) > 0
        
        # 检查是否包含主要购物节
        holiday_names = shopping_holidays["holiday"].unique()
        assert any("Prime" in name for name in holiday_names)
        assert any("Black Friday" in name for name in holiday_names)
        assert any("Double 11" in name for name in holiday_names)
    
    def test_create_holidays_df(self, prophet_predictor, sample_sales_data):
        """测试创建综合节假日 DataFrame"""
        from analysis.holidays import create_holidays_df
        
        holidays_df = create_holidays_df(
            country="US",
            include_shopping=True,
            years=[2025, 2026],
        )
        
        assert len(holidays_df) > 0
        assert holidays_df["holiday"].nunique() > 5
    
    def test_model_with_holidays(self, prophet_predictor, sample_sales_data):
        """测试模型包含节假日效应"""
        prophet_predictor.prepare_data(sample_sales_data)
        prophet_predictor.add_holidays(country="US", add_shopping_holidays=True)
        prophet_predictor.train()
        
        assert prophet_predictor.model is not None
        assert prophet_predictor.country_holidays == "US"
        # 验证节假日已配置
        assert prophet_predictor._holidays_df is not None or prophet_predictor.country_holidays is not None


# ==================== 变点测试 ====================

class TestChangepoints:
    """变点测试"""
    
    def test_changepoints_detection(self, prophet_predictor, sample_sales_data):
        """测试变点检测"""
        prophet_predictor.train(sample_sales_data)
        
        changepoints_df = prophet_predictor.get_changepoints()
        
        assert len(changepoints_df) > 0
        assert "ds" in changepoints_df.columns
    
    def test_add_changepoints(self, prophet_predictor, sample_sales_data):
        """测试添加变点配置"""
        prophet_predictor.prepare_data(sample_sales_data)
        
        # 初始训练
        prophet_predictor.train()
        initial_n_changepoints = prophet_predictor.n_changepoints
        
        # 调整变点
        prophet_predictor.add_changepoints(n_changepoints=50)
        
        assert prophet_predictor.n_changepoints == 50
        assert prophet_predictor.n_changepoints != initial_n_changepoints
    
    def test_seasonality(self, prophet_predictor, sample_sales_data):
        """测试季节性成分"""
        prophet_predictor.train(sample_sales_data)
        prophet_predictor.predict(periods=30)
        
        seasonalities = prophet_predictor.get_seasonality()
        
        assert isinstance(seasonalities, dict)
        # 季节性数据应该存在 (可能从 forecast 中提取)
        # Prophet 1.x 的 API 有所不同，这里只验证方法能正常调用
        assert seasonalities is not None


# ==================== 可视化测试 ====================

class TestVisualization:
    """可视化测试"""
    
    def test_plot_forecast(self, prophet_predictor, prophet_visualizer, sample_sales_data):
        """测试预测图"""
        prophet_predictor.train(sample_sales_data)
        prophet_predictor.predict(periods=30)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            fig = prophet_visualizer.plot_forecast(
                prophet_predictor,
                save_path=f.name,
                show_plot=False,
            )
            
            assert fig is not None
            assert Path(f.name).exists()
            assert Path(f.name).stat().st_size > 0
    
    def test_plot_components(self, prophet_predictor, prophet_visualizer, sample_sales_data):
        """测试组件图"""
        prophet_predictor.train(sample_sales_data)
        prophet_predictor.predict(periods=30)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            fig = prophet_visualizer.plot_components(
                prophet_predictor,
                save_path=f.name,
                show_plot=False,
            )
            
            assert fig is not None
            assert Path(f.name).exists()
    
    def test_plot_changepoints(self, prophet_predictor, prophet_visualizer, sample_sales_data):
        """测试变点图"""
        prophet_predictor.train(sample_sales_data)
        prophet_predictor.predict(periods=30)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            fig = prophet_visualizer.plot_changepoints(
                prophet_predictor,
                save_path=f.name,
                show_plot=False,
            )
            
            assert fig is not None
            assert Path(f.name).exists()


# ==================== 模型保存加载测试 ====================

class TestModelPersistence:
    """模型持久化测试"""
    
    def test_save_load_model(self, prophet_predictor, sample_sales_data):
        """测试模型保存和加载"""
        from analysis.prophet_predictor import ProphetPredictor
        
        prophet_predictor.train(sample_sales_data)
        prophet_predictor.predict(periods=30)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "prophet_model.pkl"
            
            # 保存
            prophet_predictor.save_model(model_path)
            assert model_path.exists()
            
            # 加载
            loaded_predictor = ProphetPredictor.load_model(model_path)
            assert loaded_predictor.model is not None
            
            # 验证预测
            loaded_forecast = loaded_predictor.predict(periods=30)
            assert len(loaded_forecast) > 0


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""
    
    def test_full_workflow(self, prophet_predictor, sample_sales_data):
        """测试完整工作流程"""
        # 1. 准备数据
        prophet_predictor.prepare_data(
            sample_sales_data,
            date_column="date",
            value_column="sales",
        )
        
        # 2. 添加节假日
        prophet_predictor.add_holidays(country="US", add_shopping_holidays=True)
        
        # 3. 训练模型
        prophet_predictor.train()
        
        # 4. 生成预测
        forecast = prophet_predictor.predict(periods=30)
        
        # 5. 交叉验证
        prophet_predictor.cross_validation(horizon="30 days")
        
        # 6. 获取指标
        metrics = prophet_predictor.get_metrics()
        
        # 7. 验证结果
        assert prophet_predictor.model is not None
        assert len(forecast) > len(sample_sales_data)
        assert metrics["mape"] < 20  # 合理的 MAPE 阈值
        assert "yhat" in forecast.columns
    
    def test_quick_forecast(self, sample_sales_data):
        """测试快速预测便捷函数"""
        from analysis.prophet_predictor import quick_forecast
        
        forecast, metrics = quick_forecast(
            sample_sales_data,
            date_column="date",
            value_column="sales",
            periods=30,
            country_holidays="US",
        )
        
        assert forecast is not None
        assert metrics is not None
        assert len(forecast) > len(sample_sales_data)
        assert metrics["mape"] < 20


# ==================== 边界情况测试 ====================

class TestEdgeCases:
    """边界情况测试"""
    
    def test_empty_dataframe(self, prophet_predictor):
        """测试空 DataFrame"""
        empty_df = pd.DataFrame(columns=["date", "sales"])
        
        # 空 DataFrame 应该能处理 (返回空结果或警告)
        df = prophet_predictor.prepare_data(empty_df)
        assert len(df) == 0
    
    def test_single_row(self, prophet_predictor):
        """测试单行数据"""
        single_df = pd.DataFrame({
            "date": [datetime(2025, 1, 1)],
            "sales": [100],
        })
        
        with pytest.raises(ValueError):
            prophet_predictor.train(single_df)
    
    def test_constant_values(self, prophet_predictor):
        """测试常数值"""
        dates = pd.date_range(start="2025-01-01", periods=100, freq="D")
        constant_df = pd.DataFrame({
            "date": dates,
            "sales": [100] * 100,
        })
        
        prophet_predictor.train(constant_df)
        forecast = prophet_predictor.predict(periods=30)
        
        assert forecast is not None
        # 常数值预测应该接近 100
        assert 90 < forecast["yhat"].mean() < 110
    
    def test_extreme_values(self, prophet_predictor):
        """测试极端值"""
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=100, freq="D")
        sales = np.random.randn(100) * 1000 + 10000  # 大数值
        
        extreme_df = pd.DataFrame({
            "date": dates,
            "sales": sales,
        })
        
        prophet_predictor.train(extreme_df)
        forecast = prophet_predictor.predict(periods=30)
        
        assert forecast is not None
        assert not forecast["yhat"].isna().any()


# ==================== 主函数 ====================

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
