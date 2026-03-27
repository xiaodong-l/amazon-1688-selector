"""
Analysis API Routes for Amazon Selector v2.4 Phase 3

Provides REST endpoints for model comparison and evaluation.
"""
from flask import Blueprint, request, jsonify, send_file, render_template
from typing import Dict, Any, Optional
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import json

from loguru import logger

# Import analysis modules
from src.analysis.model_evaluator import ModelEvaluator, create_default_evaluator, quick_model_comparison
from src.analysis.model_comparison import generate_comparison_report, export_report
from src.analysis.comparison_visualizer import create_all_visualizations
from src.analysis.prophet_predictor import ProphetPredictor
from src.analysis.lstm_predictor import LSTMPredictor
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)

# Create blueprint
analysis_bp = Blueprint('analysis', __name__, url_prefix='/api/v2/analysis')

# Global evaluator cache
_evaluator_cache: Optional[ModelEvaluator] = None
_comparison_cache: Dict[str, Any] = {}
_cache_timestamp: Optional[datetime] = None


def get_cached_evaluator() -> ModelEvaluator:
    """Get or create cached evaluator."""
    global _evaluator_cache
    if _evaluator_cache is None:
        _evaluator_cache = create_default_evaluator()
    return _evaluator_cache


def get_sample_data(periods: int = 90) -> pd.DataFrame:
    """
    Generate sample sales data for demonstration.
    
    Args:
        periods: Number of days
        
    Returns:
        DataFrame with date and sales columns
    """
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
    
    # Create realistic sales data with trend, seasonality, and noise
    trend = np.linspace(100, 150, periods)
    weekly_seasonality = 10 * np.sin(np.arange(periods) * 2 * np.pi / 7)
    yearly_seasonality = 20 * np.sin(np.arange(periods) * 2 * np.pi / 365)
    noise = np.random.randn(periods) * 5
    
    sales = trend + weekly_seasonality + yearly_seasonality + noise
    
    return pd.DataFrame({
        'date': dates,
        'sales': np.maximum(sales, 0),  # Ensure non-negative
    })


# ==================== Web Page Endpoint ====================

@analysis_bp.route('/model-comparison', methods=['GET'])
def model_comparison_page():
    """Serve the model comparison web page."""
    try:
        template_path = Path(__file__).parent.parent / 'templates' / 'analysis' / 'model_comparison.html'
        return send_file(template_path)
    except Exception as e:
        logger.error(f"Failed to serve model comparison page: {e}")
        return jsonify({'error': f'Failed to load page: {str(e)}'}), 500


# ==================== Model Comparison API Endpoints ====================

@analysis_bp.route('/compare-models', methods=['GET'])
def compare_models():
    """
    Compare multiple models (Linear/Prophet/LSTM).
    
    Query Parameters:
        days: Forecast horizon (default: 30)
        model: Specific model to focus on (optional)
        use_cache: Use cached results (default: true)
        
    Returns:
        JSON with comparison metrics
    """
    try:
        days = int(request.args.get('days', 30))
        model_filter = request.args.get('model', 'all')
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # Check cache
        cache_key = f"{days}_{model_filter}"
        if use_cache and cache_key in _comparison_cache:
            logger.info(f"Returning cached comparison for {cache_key}")
            return jsonify(_comparison_cache[cache_key])
        
        logger.info(f"Running model comparison: days={days}, model={model_filter}")
        
        # Generate sample data
        data = get_sample_data(periods=90)
        
        # Split into train/test
        train_data = data.iloc[:-days].copy()
        test_data = data.iloc[-days:].copy()
        
        # Create evaluator with default models
        evaluator = create_default_evaluator()
        
        # Filter models if requested
        if model_filter != 'all':
            evaluator.models = {
                k: v for k, v in evaluator.models.items() 
                if k == model_filter
            }
        
        # Train all models
        evaluator.train_all(train_data, target_col='sales')
        
        # Predict
        evaluator.predict_all(test_data, periods=days)
        
        # Evaluate
        y_true = test_data['sales'].values
        metrics_df = evaluator.evaluate_all(y_true)
        
        # Get predictions and residuals
        predictions = {}
        residuals = {}
        for name, y_pred in evaluator.y_pred_dict.items():
            if y_pred is not None:
                predictions[name] = y_pred.tolist()
                residuals[name] = (y_true[:len(y_pred)] - y_pred).tolist()
        
        # Build response
        response = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'days': days,
                'model_filter': model_filter,
                'models_evaluated': list(evaluator.models.keys()),
            },
            'metrics': {},
            'predictions': predictions,
            'residuals': residuals,
            'best_model': {},
            'recommendations': [],
        }
        
        # Add metrics
        for name, metrics in evaluator.metrics_results.items():
            response['metrics'][name] = {
                'MAPE': float(metrics.get('MAPE', 0)),
                'RMSE': float(metrics.get('RMSE', 0)),
                'MAE': float(metrics.get('MAE', 0)),
                'R2': float(metrics.get('R2', 0)),
                'train_time': float(evaluator.train_times.get(name, 0)),
                'predict_time': float(evaluator.predict_times.get(name, 0)),
            }
        
        # Add best model info
        response['best_model'] = {
            'overall': evaluator.get_best_model('MAPE'),
            'accuracy': evaluator.get_best_model('MAPE'),
            'speed': min(evaluator.train_times, key=evaluator.train_times.get) if evaluator.train_times else '',
            'stability': evaluator.get_best_model('R2'),
        }
        
        # Add recommendations
        response['recommendations'] = [
            {
                'scenario': '生产环境部署',
                'recommendation': f"建议使用 {response['best_model']['overall']} 模型进行生产预测",
            },
            {
                'scenario': '模型更新',
                'recommendation': '建议每周使用最新数据重新训练模型',
            },
        ]
        
        # Cache results
        _comparison_cache[cache_key] = response
        _cache_timestamp = datetime.now()
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Model comparison failed: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Model comparison failed',
        }), 500


@analysis_bp.route('/model-report', methods=['GET'])
def get_model_report():
    """
    Get detailed model comparison report.
    
    Query Parameters:
        format: Output format (json/markdown, default: json)
        days: Forecast horizon (default: 30)
        
    Returns:
        JSON report or Markdown file
    """
    try:
        output_format = request.args.get('format', 'json')
        days = int(request.args.get('days', 30))
        
        # Generate sample data
        data = get_sample_data(periods=90)
        train_data = data.iloc[:-days].copy()
        test_data = data.iloc[-days:].copy()
        
        # Create and run evaluator
        evaluator = create_default_evaluator()
        evaluator.train_all(train_data, target_col='sales')
        evaluator.predict_all(test_data, periods=days)
        y_true = test_data['sales'].values
        evaluator.evaluate_all(y_true)
        
        # Generate report
        report = generate_comparison_report(evaluator)
        
        if output_format == 'markdown':
            from src.analysis.model_comparison import _generate_markdown_report
            markdown = _generate_markdown_report(report)
            return markdown, 200, {'Content-Type': 'text/markdown'}
        else:
            return jsonify(report)
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Report generation failed',
        }), 500


@analysis_bp.route('/compare/predict', methods=['POST'])
def compare_predict():
    """
    Run multi-model prediction.
    
    Request Body:
        train_data: Training data (CSV or JSON)
        periods: Number of periods to predict
        models: List of models to use (optional)
        
    Returns:
        Predictions from all models
    """
    try:
        data = request.get_json()
        
        periods = int(data.get('periods', 30))
        models_to_use = data.get('models', ['linear', 'prophet', 'lstm'])
        
        # Get or generate training data
        if 'train_data' in data:
            train_df = pd.DataFrame(data['train_data'])
        else:
            train_df = get_sample_data(periods=90)
        
        # Create evaluator
        evaluator = ModelEvaluator()
        
        # Add requested models
        if 'linear' in models_to_use:
            evaluator.add_model('linear', LinearRegression())
        if 'prophet' in models_to_use:
            evaluator.add_model('prophet', ProphetPredictor())
        if 'lstm' in models_to_use:
            evaluator.add_model('lstm', LSTMPredictor())
        
        # Train
        evaluator.train_all(train_df, target_col='sales')
        
        # Predict
        evaluator.predict_all(train_df, periods=periods)
        
        # Build response
        response = {
            'timestamp': datetime.now().isoformat(),
            'predictions': {},
            'train_times': evaluator.train_times,
            'predict_times': evaluator.predict_times,
        }
        
        for name, y_pred in evaluator.prediction_results.items():
            if y_pred is not None:
                response['predictions'][name] = y_pred.tolist()
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Multi-model prediction failed: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Multi-model prediction failed',
        }), 500


@analysis_bp.route('/visualizations', methods=['GET'])
def get_visualizations():
    """
    Generate and return visualization images.
    
    Query Parameters:
        days: Forecast horizon (default: 30)
        type: Visualization type (metrics/predictions/residuals/radar/all)
        
    Returns:
        Image file(s) or paths
    """
    try:
        days = int(request.args.get('days', 30))
        viz_type = request.args.get('type', 'all')
        
        # Generate sample data
        data = get_sample_data(periods=90)
        train_data = data.iloc[:-days].copy()
        test_data = data.iloc[-days:].copy()
        
        # Create and run evaluator
        evaluator = create_default_evaluator()
        evaluator.train_all(train_data, target_col='sales')
        evaluator.predict_all(test_data, periods=days)
        y_true = test_data['sales'].values
        evaluator.evaluate_all(y_true)
        
        # Create output directory
        output_dir = Path('/tmp/model_visualizations')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate visualizations
        metrics_df = pd.DataFrame(evaluator.metrics_results).T
        files = create_all_visualizations(
            metrics_df=metrics_df,
            y_true=y_true,
            predictions_dict=evaluator.y_pred_dict,
            train_times=evaluator.train_times,
            predict_times=evaluator.predict_times,
            output_dir=str(output_dir),
        )
        
        # Return file paths
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'visualizations': files,
        })
        
    except Exception as e:
        logger.error(f"Visualization generation failed: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Visualization generation failed',
        }), 500


@analysis_bp.route('/best-model', methods=['GET'])
def get_best_model():
    """
    Get the best model recommendation.
    
    Query Parameters:
        metric: Metric to optimize (MAPE/RMSE/MAE/R2, default: MAPE)
        days: Forecast horizon (default: 30)
        
    Returns:
        Best model name and metrics
    """
    try:
        metric = request.args.get('metric', 'MAPE').upper()
        days = int(request.args.get('days', 30))
        
        # Generate sample data
        data = get_sample_data(periods=90)
        train_data = data.iloc[:-days].copy()
        test_data = data.iloc[-days:].copy()
        
        # Create and run evaluator
        evaluator = create_default_evaluator()
        evaluator.train_all(train_data, target_col='sales')
        evaluator.predict_all(test_data, periods=days)
        y_true = test_data['sales'].values
        evaluator.evaluate_all(y_true)
        
        # Get best model
        best_model = evaluator.get_best_model(metric)
        
        # Get metrics for best model
        best_metrics = evaluator.metrics_results.get(best_model, {})
        
        return jsonify({
            'best_model': best_model,
            'metric': metric,
            'value': best_metrics.get(metric, 0),
            'all_metrics': best_metrics,
            'train_time': evaluator.train_times.get(best_model, 0),
            'predict_time': evaluator.predict_times.get(best_model, 0),
        })
        
    except Exception as e:
        logger.error(f"Best model determination failed: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Best model determination failed',
        }), 500


@analysis_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the comparison cache."""
    global _comparison_cache, _cache_timestamp
    _comparison_cache = {}
    _cache_timestamp = None
    logger.info("Comparison cache cleared")
    return jsonify({'status': 'success', 'message': 'Cache cleared'})


@analysis_bp.route('/cache/status', methods=['GET'])
def cache_status():
    """Get cache status."""
    return jsonify({
        'cache_size': len(_comparison_cache),
        'cache_keys': list(_comparison_cache.keys()),
        'last_updated': _cache_timestamp.isoformat() if _cache_timestamp else None,
    })
