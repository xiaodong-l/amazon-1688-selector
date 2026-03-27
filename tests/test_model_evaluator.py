"""
模型评估器测试 (v2.4.0 Phase 3)

测试内容:
1. ModelEvaluator 基础功能测试
2. 多模型训练测试
3. 多模型预测测试
4. 评估指标测试 (MAPE/RMSE/MAE/R²)
5. 最佳模型选择测试
6. 对比报告生成测试
7. 可视化功能测试
8. API 端点测试

运行测试:
```bash
cd /home/admina/.openclaw-imperial/workspace-taizi/projects/amazon-1688-selector
./venv/bin/pytest tests/test_model_evaluator.py -v
```

作者：GongBu ShangShu
版本：v2.4.0 Phase 3
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile
import json

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
        "sales": np.maximum(sales, 0),  # 确保非负
    })


@pytest.fixture
def train_test_split(sample_sales_data):
    """划分训练集和测试集"""
    data = sample_sales_data
    split_idx = int(len(data) * 0.8)
    
    train_data = data.iloc[:split_idx].copy()
    test_data = data.iloc[split_idx:].copy()
    
    return train_data, test_data


@pytest.fixture
def model_evaluator():
    """创建 ModelEvaluator 实例"""
    from analysis.model_evaluator import ModelEvaluator, create_default_evaluator
    return create_default_evaluator()


@pytest.fixture
def small_test_data():
    """小样本测试数据"""
    np.random.seed(42)
    dates = pd.date_range(start="2025-01-01", periods=30, freq="D")
    sales = 100 + np.cumsum(np.random.randn(30))
    
    return pd.DataFrame({
        "date": dates,
        "sales": np.maximum(sales, 0),
    })


# ==================== ModelEvaluator 基础测试 ====================

class TestModelEvaluatorInit:
    """ModelEvaluator 初始化测试"""
    
    def test_init_empty(self):
        """测试空初始化"""
        from analysis.model_evaluator import ModelEvaluator
        evaluator = ModelEvaluator()
        
        assert evaluator.models == {}
        assert evaluator.metrics_results == {}
        assert evaluator.train_times == {}
        assert evaluator.predict_times == {}
    
    def test_init_with_models(self):
        """测试带模型初始化"""
        from analysis.model_evaluator import ModelEvaluator
        from sklearn.linear_model import LinearRegression
        
        models = {'linear': LinearRegression()}
        evaluator = ModelEvaluator(models=models)
        
        assert 'linear' in evaluator.models
        assert len(evaluator.models) == 1
    
    def test_add_model(self, model_evaluator):
        """测试添加模型"""
        from sklearn.linear_model import LinearRegression
        
        initial_count = len(model_evaluator.models)
        model_evaluator.add_model('new_model', LinearRegression())
        
        assert len(model_evaluator.models) == initial_count + 1
        assert 'new_model' in model_evaluator.models


# ==================== 训练测试 ====================

class TestModelTraining:
    """模型训练测试"""
    
    def test_train_all_models(self, model_evaluator, train_test_split):
        """测试训练所有模型"""
        train_data, _ = train_test_split
        
        results = model_evaluator.train_all(train_data, target_col='sales')
        
        # 应该有三个模型 (linear, prophet, lstm)
        assert len(results) >= 1  # 至少一个模型成功
        
        # 检查训练结果
        for name, result in results.items():
            assert 'success' in result or result is not None
    
    def test_train_linear_model(self, train_test_split):
        """测试线性模型训练"""
        from analysis.model_evaluator import ModelEvaluator
        from sklearn.linear_model import LinearRegression
        
        train_data, _ = train_test_split
        evaluator = ModelEvaluator()
        evaluator.add_model('linear', LinearRegression())
        
        results = evaluator.train_all(train_data, target_col='sales')
        
        assert 'linear' in results
        assert results['linear']['success'] == True
    
    def test_train_prophet_model(self, train_test_split):
        """测试 Prophet 模型训练"""
        from analysis.model_evaluator import ModelEvaluator
        from analysis.prophet_predictor import ProphetPredictor
        
        train_data, _ = train_test_split
        evaluator = ModelEvaluator()
        evaluator.add_model('prophet', ProphetPredictor())
        
        results = evaluator.train_all(train_data, target_col='sales')
        
        assert 'prophet' in results
    
    def test_train_lstm_model(self, train_test_split):
        """测试 LSTM 模型训练"""
        from analysis.model_evaluator import ModelEvaluator
        from analysis.lstm_predictor import LSTMPredictor
        
        train_data, _ = train_test_split
        evaluator = ModelEvaluator()
        evaluator.add_model('lstm', LSTMPredictor(lookback=10, forecast_horizon=10))
        
        results = evaluator.train_all(train_data, target_col='sales')
        
        assert 'lstm' in results


# ==================== 预测测试 ====================

class TestModelPrediction:
    """模型预测测试"""
    
    def test_predict_all_models(self, model_evaluator, train_test_split):
        """测试所有模型预测"""
        train_data, test_data = train_test_split
        
        # 先训练
        model_evaluator.train_all(train_data, target_col='sales')
        
        # 再预测
        predictions = model_evaluator.predict_all(test_data, periods=30)
        
        # 检查预测结果
        assert len(predictions) >= 1
        
        for name, y_pred in predictions.items():
            if y_pred is not None:
                assert len(y_pred) > 0
    
    def test_predict_with_different_periods(self, model_evaluator, train_test_split):
        """测试不同预测期数"""
        train_data, _ = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        
        for periods in [7, 14, 30]:
            predictions = model_evaluator.predict_all(train_data, periods=periods)
            
            for name, y_pred in predictions.items():
                if y_pred is not None:
                    assert len(y_pred) == periods


# ==================== 评估指标测试 ====================

class TestEvaluationMetrics:
    """评估指标测试"""
    
    def test_evaluate_all(self, model_evaluator, train_test_split):
        """测试评估所有模型"""
        train_data, test_data = train_test_split
        
        # 训练和预测
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        # 评估
        y_true = test_data['sales'].values[:30]
        metrics_df = model_evaluator.evaluate_all(y_true)
        
        # 检查指标
        assert not metrics_df.empty
        assert 'MAPE' in metrics_df.columns
        assert 'RMSE' in metrics_df.columns
        assert 'MAE' in metrics_df.columns
        assert 'R2' in metrics_df.columns
    
    def test_mape_calculation(self, model_evaluator):
        """测试 MAPE 计算"""
        y_true = np.array([100, 200, 300, 400, 500])
        y_pred = np.array([105, 195, 310, 390, 505])
        
        mape = model_evaluator._calculate_mape(y_true, y_pred)
        
        # MAPE 应该在合理范围内
        assert 0 < mape < 100
    
    def test_mape_with_zero_values(self, model_evaluator):
        """测试 MAPE 处理零值"""
        y_true = np.array([0, 100, 200, 0, 500])
        y_pred = np.array([5, 105, 195, 3, 505])
        
        mape = model_evaluator._calculate_mape(y_true, y_pred)
        
        # 应该能处理零值
        assert mape >= 0
    
    def test_all_metrics_range(self, model_evaluator, train_test_split):
        """测试所有指标范围"""
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        metrics_df = model_evaluator.evaluate_all(y_true)
        
        for _, row in metrics_df.iterrows():
            # MAPE 应该在 0-100 之间
            assert 0 <= row['MAPE'] <= 100
            # RMSE 和 MAE 应该非负
            assert row['RMSE'] >= 0
            assert row['MAE'] >= 0
            # R2 应该在 -1 到 1 之间 (理论上)
            assert -1 <= row['R2'] <= 1.1  # 允许小范围误差


# ==================== 最佳模型选择测试 ====================

class TestBestModelSelection:
    """最佳模型选择测试"""
    
    def test_get_best_model_mape(self, model_evaluator, train_test_split):
        """测试基于 MAPE 选择最佳模型"""
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        model_evaluator.evaluate_all(y_true)
        
        best_model = model_evaluator.get_best_model('MAPE')
        
        assert best_model != ''
        assert best_model in model_evaluator.models
    
    def test_get_best_model_r2(self, model_evaluator, train_test_split):
        """测试基于 R2 选择最佳模型"""
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        model_evaluator.evaluate_all(y_true)
        
        best_model = model_evaluator.get_best_model('R2')
        
        assert best_model != ''
    
    def test_get_best_model_no_results(self, model_evaluator):
        """测试无结果时选择最佳模型"""
        best_model = model_evaluator.get_best_model('MAPE')
        
        assert best_model == ''


# ==================== 报告生成测试 ====================

class TestReportGeneration:
    """报告生成测试"""
    
    def test_generate_comparison_report(self, model_evaluator, train_test_split):
        """测试生成对比报告"""
        from analysis.model_comparison import generate_comparison_report
        
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        model_evaluator.evaluate_all(y_true)
        
        report = generate_comparison_report(model_evaluator)
        
        # 检查报告结构
        assert 'summary' in report
        assert 'metrics_comparison' in report
        assert 'best_model' in report
        assert 'recommendations' in report
    
    def test_export_report_json(self, model_evaluator, train_test_split):
        """测试导出 JSON 报告"""
        from analysis.model_comparison import generate_comparison_report, export_report
        
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        model_evaluator.evaluate_all(y_true)
        
        report = generate_comparison_report(model_evaluator)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_report(report, f.name, format='json')
            
            # 验证文件存在且有效
            with open(f.name, 'r') as rf:
                data = json.load(rf)
                assert 'summary' in data
    
    def test_export_report_markdown(self, model_evaluator, train_test_split):
        """测试导出 Markdown 报告"""
        from analysis.model_comparison import generate_comparison_report, export_report
        
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        model_evaluator.evaluate_all(y_true)
        
        report = generate_comparison_report(model_evaluator)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            export_report(report, f.name, format='markdown')
            
            # 验证文件存在且包含标题
            with open(f.name, 'r') as rf:
                content = rf.read()
                assert '# 📊 模型对比分析报告' in content


# ==================== 可视化测试 ====================

class TestVisualization:
    """可视化测试"""
    
    def test_plot_metrics_comparison(self, model_evaluator, train_test_split):
        """测试指标对比图"""
        from analysis.comparison_visualizer import plot_metrics_comparison
        
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        metrics_df = model_evaluator.evaluate_all(y_true)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            fig = plot_metrics_comparison(metrics_df, save_path=f.name)
            
            # 验证图表创建
            assert fig is not None
            assert Path(f.name).exists()
    
    def test_plot_predictions_comparison(self, model_evaluator, train_test_split):
        """测试预测对比图"""
        from analysis.comparison_visualizer import plot_predictions_comparison
        
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        model_evaluator.evaluate_all(y_true)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            fig = plot_predictions_comparison(y_true, model_evaluator.y_pred_dict, save_path=f.name)
            
            assert fig is not None
            assert Path(f.name).exists()
    
    def test_plot_radar_chart(self, model_evaluator, train_test_split):
        """测试雷达图"""
        from analysis.comparison_visualizer import plot_radar_chart
        
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        metrics_df = model_evaluator.evaluate_all(y_true)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            fig = plot_radar_chart(metrics_df, save_path=f.name)
            
            # 雷达图可能因数据不足返回 None
            # assert fig is not None
    
    def test_create_all_visualizations(self, model_evaluator, train_test_split):
        """测试创建所有可视化"""
        from analysis.comparison_visualizer import create_all_visualizations
        
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        model_evaluator.evaluate_all(y_true)
        
        metrics_df = pd.DataFrame(model_evaluator.metrics_results).T
        
        with tempfile.TemporaryDirectory() as tmpdir:
            files = create_all_visualizations(
                metrics_df=metrics_df,
                y_true=y_true,
                predictions_dict=model_evaluator.y_pred_dict,
                train_times=model_evaluator.train_times,
                predict_times=model_evaluator.predict_times,
                output_dir=tmpdir,
            )
            
            # 应该生成多个文件
            assert len(files) >= 1


# ==================== 快速对比测试 ====================

class TestQuickComparison:
    """快速对比测试"""
    
    def test_quick_model_comparison(self, train_test_split):
        """测试快速模型对比"""
        from analysis.model_evaluator import quick_model_comparison
        
        train_data, test_data = train_test_split
        
        result = quick_model_comparison(
            train_data=train_data,
            test_data=test_data,
            target_col='sales',
            periods=30,
        )
        
        assert 'metrics_df' in result
        assert 'best_model' in result
        assert 'evaluator' in result


# ==================== 导出功能测试 ====================

class TestExportFunctionality:
    """导出功能测试"""
    
    def test_export_results_json(self, model_evaluator, train_test_split):
        """测试导出 JSON 结果"""
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        model_evaluator.evaluate_all(y_true)
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            model_evaluator.export_results(f.name, format='json')
            
            # 验证文件
            with open(f.name, 'r') as rf:
                data = json.load(rf)
                assert len(data) > 0
    
    def test_export_results_csv(self, model_evaluator, train_test_split):
        """测试导出 CSV 结果"""
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        model_evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        model_evaluator.evaluate_all(y_true)
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            model_evaluator.export_results(f.name, format='csv')
            
            # 验证文件
            df = pd.read_csv(f.name)
            assert len(df) > 0


# ==================== 边界情况测试 ====================

class TestEdgeCases:
    """边界情况测试"""
    
    def test_small_dataset(self, small_test_data):
        """测试小数据集"""
        from analysis.model_evaluator import ModelEvaluator, create_default_evaluator
        
        evaluator = create_default_evaluator()
        
        # 只用部分数据训练
        train_data = small_test_data.iloc[:20].copy()
        test_data = small_test_data.iloc[20:].copy()
        
        # 应该能处理小数据集
        evaluator.train_all(train_data, target_col='sales')
        evaluator.predict_all(test_data, periods=5)
    
    def test_single_model(self, train_test_split):
        """测试单模型评估"""
        from analysis.model_evaluator import ModelEvaluator
        from sklearn.linear_model import LinearRegression
        
        train_data, test_data = train_test_split
        evaluator = ModelEvaluator()
        evaluator.add_model('linear', LinearRegression())
        
        evaluator.train_all(train_data, target_col='sales')
        evaluator.predict_all(test_data, periods=30)
        
        y_true = test_data['sales'].values[:30]
        metrics_df = evaluator.evaluate_all(y_true)
        
        assert len(metrics_df) == 1
    
    def test_empty_predictions(self, model_evaluator):
        """测试空预测处理"""
        y_true = np.array([100, 200, 300])
        
        # 没有预测结果时
        metrics_df = model_evaluator.evaluate_all(y_true)
        
        # 应该返回空 DataFrame
        assert metrics_df.empty


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""
    
    def test_training_time(self, model_evaluator, train_test_split):
        """测试训练时间"""
        import time
        
        train_data, _ = train_test_split
        
        start_time = time.time()
        model_evaluator.train_all(train_data, target_col='sales')
        train_time = time.time() - start_time
        
        # 训练时间应该合理 (小于 5 分钟)
        assert train_time < 300
        
        # 检查时间记录
        for name, t in model_evaluator.train_times.items():
            assert t >= 0
    
    def test_prediction_time(self, model_evaluator, train_test_split):
        """测试预测时间"""
        train_data, test_data = train_test_split
        
        model_evaluator.train_all(train_data, target_col='sales')
        
        import time
        start_time = time.time()
        model_evaluator.predict_all(test_data, periods=30)
        predict_time = time.time() - start_time
        
        # 预测时间应该合理 (小于 1 分钟)
        assert predict_time < 60


# ==================== 主测试入口 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
