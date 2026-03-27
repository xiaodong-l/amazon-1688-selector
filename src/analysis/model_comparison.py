"""
模型对比报告生成器 (v2.4.0 Phase 3)

功能：
1. 生成多模型对比报告
2. 指标对比分析
3. 训练/预测时间对比
4. 最佳模型推荐
5. 使用场景建议
6. 报告导出 (JSON/Markdown)

使用示例：
```python
from .model_comparison import generate_comparison_report, export_report

report = generate_comparison_report(evaluator)
export_report(report, 'reports/model_comparison.md')
```

作者：GongBu ShangShu
版本：v2.4.0 Phase 3
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json
from pathlib import Path

from loguru import logger

from .model_evaluator import ModelEvaluator


def generate_comparison_report(evaluator: ModelEvaluator) -> Dict[str, Any]:
    """
    生成模型对比报告
    
    Args:
        evaluator: ModelEvaluator 实例
        
    Returns:
        对比报告字典
    """
    logger.info("开始生成模型对比报告...")
    
    # 获取评估结果
    metrics = evaluator.metrics_results
    train_times = evaluator.train_times
    predict_times = evaluator.predict_times
    
    if not metrics:
        logger.warning("没有评估结果，无法生成报告")
        return {'error': 'No evaluation results'}
    
    # 创建指标对比表
    metrics_df = pd.DataFrame(metrics).T
    
    # 计算排名
    rankings = _calculate_rankings(metrics_df)
    
    # 确定最佳模型
    best_model = _determine_best_model(metrics_df, train_times, predict_times)
    
    # 生成使用场景建议
    recommendations = _generate_recommendations(metrics_df, train_times, predict_times)
    
    # 生成详细分析
    analysis = _generate_detailed_analysis(metrics_df, train_times, predict_times)
    
    # 构建报告
    report = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'models_evaluated': len(metrics),
            'model_names': list(metrics.keys()),
            'best_model_overall': best_model['overall'],
            'best_model_accuracy': best_model['accuracy'],
            'best_model_speed': best_model['speed'],
        },
        'metrics_comparison': metrics_df.to_dict('index'),
        'rankings': rankings,
        'time_comparison': {
            'train_times': train_times,
            'predict_times': predict_times,
            'total_times': {k: train_times.get(k, 0) + predict_times.get(k, 0) for k in metrics.keys()},
        },
        'best_model': best_model,
        'recommendations': recommendations,
        'detailed_analysis': analysis,
    }
    
    logger.info(f"模型对比报告生成完成，评估了 {len(metrics)} 个模型")
    
    return report


def _calculate_rankings(metrics_df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
    """
    计算各模型在各指标上的排名
    
    Args:
        metrics_df: 指标 DataFrame
        
    Returns:
        排名字典
    """
    rankings = {}
    
    # 误差类指标 (越小越好)
    error_metrics = ['MAPE', 'RMSE', 'MAE']
    # 正向指标 (越大越好)
    positive_metrics = ['R2']
    
    for metric in error_metrics + positive_metrics:
        if metric not in metrics_df.columns:
            continue
        
        is_error = metric in error_metrics
        
        # 排序
        if is_error:
            sorted_models = metrics_df[metric].sort_values().index.tolist()
        else:
            sorted_models = metrics_df[metric].sort_values(ascending=False).index.tolist()
        
        # 记录排名
        for rank, model in enumerate(sorted_models, 1):
            if model not in rankings:
                rankings[model] = {}
            rankings[model][metric] = rank
    
    return rankings


def _determine_best_model(
    metrics_df: pd.DataFrame,
    train_times: Dict[str, float],
    predict_times: Dict[str, float]
) -> Dict[str, Any]:
    """
    确定最佳模型
    
    Args:
        metrics_df: 指标 DataFrame
        train_times: 训练时间
        predict_times: 预测时间
        
    Returns:
        最佳模型信息
    """
    best = {
        'overall': '',
        'accuracy': '',
        'speed': '',
        'balanced': '',
        'reasoning': {},
    }
    
    # 最佳精度模型 (最低 MAPE)
    if 'MAPE' in metrics_df.columns:
        best['accuracy'] = metrics_df['MAPE'].idxmin()
        best['reasoning']['accuracy'] = f"最低 MAPE: {metrics_df.loc[best['accuracy'], 'MAPE']:.2f}%"
    
    # 最快速度模型 (最短总时间)
    total_times = {k: train_times.get(k, 0) + predict_times.get(k, 0) for k in metrics_df.index}
    if total_times:
        best['speed'] = min(total_times, key=total_times.get)
        best['reasoning']['speed'] = f"最短总时间：{total_times[best['speed']]:.4f}秒"
    
    # 综合最佳 (平衡精度和速度)
    # 使用加权评分：MAPE 权重 70%，时间权重 30%
    scores = {}
    for model in metrics_df.index:
        mape_score = metrics_df.loc[model, 'MAPE'] if 'MAPE' in metrics_df.columns else 0
        time_score = total_times.get(model, 0) * 100  # 放大时间影响
        
        # 归一化 (越低越好)
        scores[model] = mape_score * 0.7 + time_score * 0.3
    
    if scores:
        best['balanced'] = min(scores, key=scores.get)
        best['reasoning']['balanced'] = f"综合评分最低：{scores[best['balanced']]:.2f}"
    
    # 总体最佳 (默认使用综合最佳)
    best['overall'] = best['balanced'] or best['accuracy']
    
    return best


def _generate_recommendations(
    metrics_df: pd.DataFrame,
    train_times: Dict[str, float],
    predict_times: Dict[str, float]
) -> List[Dict[str, str]]:
    """
    生成使用场景建议
    
    Args:
        metrics_df: 指标 DataFrame
        train_times: 训练时间
        predict_times: 预测时间
        
    Returns:
        建议列表
    """
    recommendations = []
    
    # 分析每个模型的特点
    for model in metrics_df.index:
        scenario = _analyze_model_scenario(model, metrics_df, train_times, predict_times)
        if scenario:
            recommendations.append(scenario)
    
    # 添加通用建议
    recommendations.append({
        'scenario': '生产环境部署',
        'recommendation': '建议使用综合性能最佳的模型，并设置备用模型以应对异常情况',
        'models': '所有模型',
    })
    
    recommendations.append({
        'scenario': '模型更新策略',
        'recommendation': '建议定期 (每周/每月) 重新训练模型，并使用最新数据评估模型性能',
        'models': '所有模型',
    })
    
    return recommendations


def _analyze_model_scenario(
    model: str,
    metrics_df: pd.DataFrame,
    train_times: Dict[str, float],
    predict_times: Dict[str, float]
) -> Optional[Dict[str, str]]:
    """
    分析模型适用场景
    
    Args:
        model: 模型名称
        metrics_df: 指标 DataFrame
        train_times: 训练时间
        predict_times: 预测时间
        
    Returns:
        场景建议
    """
    mape = metrics_df.loc[model, 'MAPE'] if 'MAPE' in metrics_df.columns else None
    r2 = metrics_df.loc[model, 'R2'] if 'R2' in metrics_df.columns else None
    train_time = train_times.get(model, 0)
    predict_time = predict_times.get(model, 0)
    
    # 线性模型特点
    if model == 'linear':
        return {
            'scenario': '快速原型/基线对比',
            'recommendation': '线性模型训练速度快，适合作为基线模型或快速原型验证',
            'models': 'linear',
        }
    
    # Prophet 模型特点
    elif model == 'prophet':
        if mape and mape < 10:
            return {
                'scenario': '高精度预测需求',
                'recommendation': 'Prophet 模型在季节性数据上表现优异，适合销售预测等场景',
                'models': 'prophet',
            }
        else:
            return {
                'scenario': '含节假日效应的预测',
                'recommendation': 'Prophet 支持节假日调整，适合受节假日影响明显的销售数据',
                'models': 'prophet',
            }
    
    # LSTM 模型特点
    elif model == 'lstm':
        if train_time > 10:
            return {
                'scenario': '复杂模式识别',
                'recommendation': 'LSTM 能捕捉复杂时间依赖关系，适合长期趋势预测，但训练时间较长',
                'models': 'lstm',
            }
        else:
            return {
                'scenario': '实时预测应用',
                'recommendation': 'LSTM 预测速度快，适合需要频繁预测的实时应用场景',
                'models': 'lstm',
            }
    
    return None


def _generate_detailed_analysis(
    metrics_df: pd.DataFrame,
    train_times: Dict[str, float],
    predict_times: Dict[str, float]
) -> Dict[str, Any]:
    """
    生成详细分析
    
    Args:
        metrics_df: 指标 DataFrame
        train_times: 训练时间
        predict_times: 预测时间
        
    Returns:
        详细分析字典
    """
    analysis = {
        'accuracy_analysis': {},
        'speed_analysis': {},
        'stability_analysis': {},
        'trade_off_analysis': {},
    }
    
    # 精度分析
    if 'MAPE' in metrics_df.columns:
        mape_range = metrics_df['MAPE'].max() - metrics_df['MAPE'].min()
        analysis['accuracy_analysis'] = {
            'mape_range': float(mape_range),
            'mape_mean': float(metrics_df['MAPE'].mean()),
            'mape_std': float(metrics_df['MAPE'].std()) if len(metrics_df) > 1 else 0,
            'interpretation': _interpret_mape_range(mape_range),
        }
    
    # 速度分析
    total_times = {k: train_times.get(k, 0) + predict_times.get(k, 0) for k in metrics_df.index}
    if total_times:
        max_time = max(total_times.values())
        min_time = min(total_times.values())
        analysis['speed_analysis'] = {
            'fastest_model': min(total_times, key=total_times.get),
            'slowest_model': max(total_times, key=total_times.get),
            'speed_ratio': float(max_time / min_time) if min_time > 0 else 0,
            'interpretation': _interpret_speed_ratio(max_time / min_time) if min_time > 0 else '',
        }
    
    # 稳定性分析 (使用 R2 的标准差)
    if 'R2' in metrics_df.columns:
        analysis['stability_analysis'] = {
            'r2_variance': float(metrics_df['R2'].var()),
            'interpretation': 'R² 方差越小，模型表现越稳定' if len(metrics_df) > 1 else '单模型无法评估稳定性',
        }
    
    # 权衡分析
    analysis['trade_off_analysis'] = _analyze_trade_offs(metrics_df, total_times)
    
    return analysis


def _interpret_mape_range(mape_range: float) -> str:
    """解释 MAPE 范围"""
    if mape_range < 2:
        return "各模型精度差异很小，可优先选择速度更快的模型"
    elif mape_range < 5:
        return "各模型精度有中等差异，建议综合考虑精度和速度"
    else:
        return "各模型精度差异显著，建议优先选择精度最高的模型"


def _interpret_speed_ratio(speed_ratio: float) -> str:
    """解释速度比"""
    if speed_ratio < 2:
        return "各模型速度差异不大"
    elif speed_ratio < 10:
        return "各模型速度有中等差异"
    else:
        return "各模型速度差异显著，最快模型比最慢模型快很多"


def _analyze_trade_offs(
    metrics_df: pd.DataFrame,
    total_times: Dict[str, float]
) -> Dict[str, Any]:
    """
    分析精度 - 速度权衡
    
    Args:
        metrics_df: 指标 DataFrame
        total_times: 总时间
        
    Returns:
        权衡分析
    """
    trade_offs = {
        'pareto_frontier': [],
        'recommendations': [],
    }
    
    # 简单 Pareto 前沿分析
    models = list(metrics_df.index)
    
    for i, model1 in enumerate(models):
        is_pareto = True
        for model2 in models:
            if model1 == model2:
                continue
            
            mape1 = metrics_df.loc[model1, 'MAPE'] if 'MAPE' in metrics_df.columns else 0
            mape2 = metrics_df.loc[model2, 'MAPE'] if 'MAPE' in metrics_df.columns else 0
            time1 = total_times.get(model1, 0)
            time2 = total_times.get(model2, 0)
            
            # 如果 model2 在精度和速度上都优于 model1
            if mape2 <= mape1 and time2 <= time1 and (mape2 < mape1 or time2 < time1):
                is_pareto = False
                break
        
        if is_pareto:
            trade_offs['pareto_frontier'].append(model1)
    
    # 生成建议
    if trade_offs['pareto_frontier']:
        trade_offs['recommendations'].append(
            f"Pareto 最优模型：{', '.join(trade_offs['pareto_frontier'])}，这些模型在精度和速度之间达到了最佳平衡"
        )
    
    return trade_offs


def export_report(report: Dict[str, Any], path: str, format: str = 'json') -> None:
    """
    导出报告
    
    Args:
        report: 报告字典
        path: 保存路径
        format: 导出格式 ('json' 或 'markdown')
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"报告已导出为 JSON: {path}")
    
    elif format == 'markdown':
        markdown = _generate_markdown_report(report)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        logger.info(f"报告已导出为 Markdown: {path}")
    
    else:
        logger.error(f"不支持的导出格式：{format}")


def _generate_markdown_report(report: Dict[str, Any]) -> str:
    """
    生成 Markdown 格式报告
    
    Args:
        report: 报告字典
        
    Returns:
        Markdown 字符串
    """
    lines = []
    
    # 标题
    lines.append("# 📊 模型对比分析报告")
    lines.append("")
    lines.append(f"**生成时间**: {report.get('generated_at', 'N/A')}")
    lines.append("")
    
    # 摘要
    summary = report.get('summary', {})
    lines.append("## 📋 摘要")
    lines.append("")
    lines.append(f"- **评估模型数**: {summary.get('models_evaluated', 0)}")
    lines.append(f"- **模型列表**: {', '.join(summary.get('model_names', []))}")
    lines.append(f"- **最佳模型 (综合)**: {summary.get('best_model_overall', 'N/A')}")
    lines.append(f"- **最佳模型 (精度)**: {summary.get('best_model_accuracy', 'N/A')}")
    lines.append(f"- **最佳模型 (速度)**: {summary.get('best_model_speed', 'N/A')}")
    lines.append("")
    
    # 指标对比表
    lines.append("## 📈 指标对比")
    lines.append("")
    lines.append("| 模型 | MAPE (%) | RMSE | MAE | R² |")
    lines.append("|------|----------|------|-----|----|")
    
    metrics = report.get('metrics_comparison', {})
    for model, m in metrics.items():
        mape = f"{m.get('MAPE', 'N/A'):.2f}" if isinstance(m.get('MAPE'), (int, float)) else 'N/A'
        rmse = f"{m.get('RMSE', 'N/A'):.4f}" if isinstance(m.get('RMSE'), (int, float)) else 'N/A'
        mae = f"{m.get('MAE', 'N/A'):.4f}" if isinstance(m.get('MAE'), (int, float)) else 'N/A'
        r2 = f"{m.get('R2', 'N/A'):.4f}" if isinstance(m.get('R2'), (int, float)) else 'N/A'
        lines.append(f"| {model} | {mape} | {rmse} | {mae} | {r2} |")
    
    lines.append("")
    
    # 时间对比
    lines.append("## ⏱️ 时间对比")
    lines.append("")
    time_comp = report.get('time_comparison', {})
    
    lines.append("### 训练时间")
    lines.append("")
    for model, time in time_comp.get('train_times', {}).items():
        lines.append(f"- **{model}**: {time:.4f}秒")
    lines.append("")
    
    lines.append("### 预测时间")
    lines.append("")
    for model, time in time_comp.get('predict_times', {}).items():
        lines.append(f"- **{model}**: {time:.4f}秒")
    lines.append("")
    
    # 最佳模型
    lines.append("## 🏆 最佳模型")
    lines.append("")
    best = report.get('best_model', {})
    lines.append(f"- **总体最佳**: {best.get('overall', 'N/A')}")
    lines.append(f"- **精度最佳**: {best.get('accuracy', 'N/A')}")
    lines.append(f"- **速度最佳**: {best.get('speed', 'N/A')}")
    lines.append("")
    
    # 使用建议
    lines.append("## 💡 使用建议")
    lines.append("")
    recommendations = report.get('recommendations', [])
    for rec in recommendations:
        lines.append(f"### {rec.get('scenario', '场景')}")
        lines.append(f"- **推荐**: {rec.get('recommendation', '')}")
        lines.append(f"- **适用模型**: {rec.get('models', '')}")
        lines.append("")
    
    # 详细分析
    lines.append("## 🔍 详细分析")
    lines.append("")
    analysis = report.get('detailed_analysis', {})
    
    if 'accuracy_analysis' in analysis:
        acc = analysis['accuracy_analysis']
        lines.append("### 精度分析")
        lines.append(f"- MAPE 范围：{acc.get('mape_range', 0):.2f}%")
        lines.append(f"- MAPE 均值：{acc.get('mape_mean', 0):.2f}%")
        lines.append(f"- 分析：{acc.get('interpretation', '')}")
        lines.append("")
    
    if 'speed_analysis' in analysis:
        spd = analysis['speed_analysis']
        lines.append("### 速度分析")
        lines.append(f"- 最快模型：{spd.get('fastest_model', 'N/A')}")
        lines.append(f"- 最慢模型：{spd.get('slowest_model', 'N/A')}")
        lines.append(f"- 速度比：{spd.get('speed_ratio', 0):.2f}x")
        lines.append(f"- 分析：{spd.get('interpretation', '')}")
        lines.append("")
    
    lines.append("---")
    lines.append("*报告由 Model Comparison Generator 自动生成*")
    
    return '\n'.join(lines)


def generate_html_report(report: Dict[str, Any], template_path: Optional[str] = None) -> str:
    """
    生成 HTML 格式报告
    
    Args:
        report: 报告字典
        template_path: 模板路径 (可选)
        
    Returns:
        HTML 字符串
    """
    # 简化版 HTML 报告
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>模型对比分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .highlight {{ background-color: #fff3cd; }}
        .best {{ background-color: #d4edda; }}
    </style>
</head>
<body>
    <h1>📊 模型对比分析报告</h1>
    <p><strong>生成时间</strong>: {report.get('generated_at', 'N/A')}</p>
    
    <h2>📋 摘要</h2>
    <ul>
        <li><strong>评估模型数</strong>: {report.get('summary', {}).get('models_evaluated', 0)}</li>
        <li><strong>最佳模型 (综合)</strong>: {report.get('summary', {}).get('best_model_overall', 'N/A')}</li>
    </ul>
    
    <h2>📈 指标对比</h2>
    <table>
        <tr><th>模型</th><th>MAPE (%)</th><th>RMSE</th><th>MAE</th><th>R²</th></tr>
"""
    
    metrics = report.get('metrics_comparison', {})
    best_model = report.get('summary', {}).get('best_model_overall', '')
    
    for model, m in metrics.items():
        is_best = 'class="best"' if model == best_model else ''
        mape = f"{m.get('MAPE', 0):.2f}" if isinstance(m.get('MAPE'), (int, float)) else 'N/A'
        rmse = f"{m.get('RMSE', 0):.4f}" if isinstance(m.get('RMSE'), (int, float)) else 'N/A'
        mae = f"{m.get('MAE', 0):.4f}" if isinstance(m.get('MAE'), (int, float)) else 'N/A'
        r2 = f"{m.get('R2', 0):.4f}" if isinstance(m.get('R2'), (int, float)) else 'N/A'
        html += f'        <tr {is_best}><td>{model}</td><td>{mape}</td><td>{rmse}</td><td>{mae}</td><td>{r2}</td></tr>\n'
    
    html += """
    </table>
</body>
</html>
"""
    
    return html
