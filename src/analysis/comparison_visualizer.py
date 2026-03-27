"""
模型对比可视化工具 (v2.4.0 Phase 3)

功能：
1. 指标对比柱状图 (MAPE/RMSE/MAE/R²)
2. 多模型预测对比图
3. 多模型残差对比图
4. 雷达图 (多维度对比)
5. 热力图 (模型性能对比)
6. 支持中文显示

使用示例：
```python
from .comparison_visualizer import (
    plot_metrics_comparison,
    plot_predictions_comparison,
    plot_residuals_comparison,
    plot_radar_chart,
)

plot_metrics_comparison(metrics_df, save_path='metrics.png')
plot_predictions_comparison(y_true, predictions_dict, save_path='predictions.png')
```

作者：GongBu ShangShu
版本：v2.4.0 Phase 3
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
from pathlib import Path

from loguru import logger

# Matplotlib 配置 (支持中文)
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.dates as mdates

# 配置中文字体
def setup_chinese_font():
    """设置中文字体"""
    # 尝试多种中文字体
    chinese_fonts = [
        'SimHei',           # 黑体 (Windows)
        'Microsoft YaHei',  # 微软雅黑 (Windows)
        'WenQuanYi Micro Hei',  # 文泉驿 (Linux)
        'Noto Sans CJK SC', # Google Noto (跨平台)
        'Arial Unicode MS', # macOS
        'Heiti SC',         # macOS
    ]
    
    for font in chinese_fonts:
        try:
            font_manager.FontManager().findfont(font)
            plt.rcParams['font.sans-serif'] = [font] + plt.rcParams['font.sans-serif']
            logger.info(f"使用中文字体：{font}")
            return font
        except:
            continue
    
    # 如果都没有，使用默认字体
    logger.warning("未找到中文字体，使用默认字体")
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    return 'DejaVu Sans'


# 初始化中文字体
setup_chinese_font()
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


def plot_metrics_comparison(
    metrics_df: pd.DataFrame,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (12, 8),
    colors: Optional[List[str]] = None,
) -> plt.Figure:
    """
    绘制指标对比柱状图
    
    Args:
        metrics_df: 指标 DataFrame (索引为模型名，列为 MAPE/RMSE/MAE/R2)
        save_path: 保存路径 (如果为 None，则返回 Figure)
        figsize: 图像大小
        colors: 颜色列表
        
    Returns:
        Figure 对象
    """
    logger.info("绘制指标对比图...")
    
    # 创建图形
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    fig.suptitle('模型性能指标对比', fontsize=16, fontweight='bold')
    
    # 默认颜色
    if colors is None:
        colors = plt.cm.Set3(np.linspace(0, 1, len(metrics_df)))
    
    # 指标配置
    metrics_config = [
        ('MAPE', '平均绝对百分比误差 (%)', 'lower', 0),  # 名称，标签，越低越好，子图索引
        ('RMSE', '均方根误差', 'lower', 1),
        ('MAE', '平均绝对误差', 'lower', 2),
        ('R2', '决定系数 R²', 'higher', 3),
    ]
    
    for metric_name, metric_label, direction, ax_idx in metrics_config:
        if metric_name not in metrics_df.columns:
            continue
        
        ax = axes[ax_idx // 2, ax_idx % 2]
        models = metrics_df.index.tolist()
        values = metrics_df[metric_name].values
        
        # 创建柱状图
        bars = ax.bar(models, values, color=colors[:len(models)], alpha=0.8)
        
        # 设置标签
        ax.set_xlabel('模型', fontsize=12)
        ax.set_ylabel(metric_label, fontsize=12)
        ax.set_title(f'{metric_name} 对比', fontsize=14)
        
        # 添加数值标签
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.annotate(f'{value:.2f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom',
                       fontsize=10)
        
        # 标记最佳值
        if direction == 'lower':
            best_idx = np.argmin(values)
        else:
            best_idx = np.argmax(values)
        
        bars[best_idx].set_edgecolor('red')
        bars[best_idx].set_linewidth(3)
        
        # 添加网格
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    # 保存或返回
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        # 修改保存路径为指标对比图
        save_path = save_path.parent / f"metrics_comparison{save_path.suffix}"
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"指标对比图已保存：{save_path}")
    
    return fig


def plot_predictions_comparison(
    y_true: np.ndarray,
    predictions_dict: Dict[str, np.ndarray],
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (14, 8),
    show_legend: bool = True,
) -> plt.Figure:
    """
    绘制多模型预测对比图
    
    Args:
        y_true: 真实值
        predictions_dict: 预测值字典 {模型名：预测值}
        save_path: 保存路径
        figsize: 图像大小
        show_legend: 是否显示图例
        
    Returns:
        Figure 对象
    """
    logger.info("绘制预测对比图...")
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # 颜色映射
    colors = plt.cm.tab10(np.linspace(0, 1, len(predictions_dict) + 1))
    
    # 绘制真实值
    x = np.arange(len(y_true))
    ax.plot(x, y_true, 'k-', linewidth=2.5, label='真实值', marker='o', markersize=4)
    
    # 绘制各模型预测
    color_idx = 1
    for model_name, y_pred in predictions_dict.items():
        if y_pred is None:
            continue
        
        # 确保长度一致
        min_len = min(len(y_true), len(y_pred))
        ax.plot(x[:min_len], y_pred[:min_len], '--', 
               linewidth=2, label=model_name, color=colors[color_idx],
               marker='s', markersize=3, alpha=0.8)
        color_idx += 1
    
    # 设置标签
    ax.set_xlabel('时间步', fontsize=12)
    ax.set_ylabel('预测值', fontsize=12)
    ax.set_title('多模型预测对比', fontsize=14, fontweight='bold')
    
    if show_legend:
        ax.legend(loc='best', fontsize=10)
    
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    # 保存
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path = save_path.parent / f"predictions_comparison{save_path.suffix}"
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"预测对比图已保存：{save_path}")
    
    return fig


def plot_residuals_comparison(
    y_true: np.ndarray,
    predictions_dict: Dict[str, np.ndarray],
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (14, 10),
) -> plt.Figure:
    """
    绘制多模型残差对比图
    
    Args:
        y_true: 真实值
        predictions_dict: 预测值字典
        save_path: 保存路径
        figsize: 图像大小
        
    Returns:
        Figure 对象
    """
    logger.info("绘制残差对比图...")
    
    n_models = len(predictions_dict)
    fig, axes = plt.subplots(n_models + 1, 1, figsize=figsize)
    
    if n_models == 1:
        axes = [axes]
    
    colors = plt.cm.tab10(np.linspace(0, 1, n_models))
    
    # 计算残差
    residuals = {}
    for i, (model_name, y_pred) in enumerate(predictions_dict.items()):
        if y_pred is None:
            continue
        min_len = min(len(y_true), len(y_pred))
        residuals[model_name] = y_true[:min_len] - y_pred[:min_len]
    
    # 绘制真实值
    ax_idx = 0
    x = np.arange(len(y_true))
    axes[ax_idx].plot(x, y_true, 'k-', linewidth=2, label='真实值')
    axes[ax_idx].set_ylabel('真实值', fontsize=11)
    axes[ax_idx].set_title('真实值 vs 预测残差', fontsize=14, fontweight='bold')
    axes[ax_idx].grid(True, alpha=0.3)
    
    # 绘制各模型残差
    for i, (model_name, resid) in enumerate(residuals.items()):
        ax_idx = i + 1
        x_resid = np.arange(len(resid))
        
        # 残差图
        axes[ax_idx].bar(x_resid, resid, color=colors[i], alpha=0.6, label=model_name)
        axes[ax_idx].axhline(y=0, color='red', linestyle='-', linewidth=1)
        axes[ax_idx].set_ylabel('残差', fontsize=11)
        axes[ax_idx].set_title(f'{model_name} 残差分布', fontsize=12)
        axes[ax_idx].grid(True, alpha=0.3, axis='y')
        
        # 添加统计信息
        mean_resid = np.mean(resid)
        std_resid = np.std(resid)
        axes[ax_idx].text(0.02, 0.98, 
                         f'均值：{mean_resid:.4f}\n标准差：{std_resid:.4f}',
                         transform=axes[ax_idx].transAxes,
                         fontsize=9, verticalalignment='top',
                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.xlabel('时间步', fontsize=12)
    plt.tight_layout()
    
    # 保存
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path = save_path.parent / f"residuals_comparison{save_path.suffix}"
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"残差对比图已保存：{save_path}")
    
    return fig


def plot_radar_chart(
    metrics_df: pd.DataFrame,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 10),
    normalize: bool = True,
) -> plt.Figure:
    """
    绘制雷达图 (多维度对比)
    
    Args:
        metrics_df: 指标 DataFrame
        save_path: 保存路径
        figsize: 图像大小
        normalize: 是否归一化到 0-1 范围
        
    Returns:
        Figure 对象
    """
    logger.info("绘制雷达图...")
    
    # 选择要显示的指标
    metrics_to_show = ['MAPE', 'RMSE', 'MAE', 'R2']
    available_metrics = [m for m in metrics_to_show if m in metrics_df.columns]
    
    if len(available_metrics) < 3:
        logger.warning("指标不足，无法绘制雷达图")
        return None
    
    # 数据归一化
    if normalize:
        normalized_df = pd.DataFrame(index=metrics_df.index)
        for metric in available_metrics:
            if metric in ['MAPE', 'RMSE', 'MAE']:
                # 误差类指标，反转 (越小越好 -> 越大越好)
                min_val = metrics_df[metric].min()
                max_val = metrics_df[metric].max()
                if max_val - min_val > 0:
                    normalized_df[metric] = 1 - (metrics_df[metric] - min_val) / (max_val - min_val)
                else:
                    normalized_df[metric] = 1
            else:
                # R2 等正向指标
                min_val = metrics_df[metric].min()
                max_val = metrics_df[metric].max()
                if max_val - min_val > 0:
                    normalized_df[metric] = (metrics_df[metric] - min_val) / (max_val - min_val)
                else:
                    normalized_df[metric] = 1
    else:
        normalized_df = metrics_df[available_metrics]
    
    # 创建雷达图
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, polar=True)
    
    # 角度设置
    angles = np.linspace(0, 2 * np.pi, len(available_metrics), endpoint=False).tolist()
    angles += angles[:1]  # 闭合
    
    # 中文标签
    metric_labels = {
        'MAPE': 'MAPE\n(越低越好)',
        'RMSE': 'RMSE\n(越低越好)',
        'MAE': 'MAE\n(越低越好)',
        'R2': 'R²\n(越高越好)',
    }
    labels = [metric_labels.get(m, m) for m in available_metrics]
    labels += labels[:1]
    
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels, fontsize=11)
    
    # 绘制各模型
    colors = plt.cm.Set3(np.linspace(0, 1, len(normalized_df)))
    
    for idx, (model_name, row) in enumerate(normalized_df.iterrows()):
        values = row[available_metrics].values.tolist()
        values += values[:1]  # 闭合
        
        ax.plot(angles, values, 'o-', linewidth=2, label=model_name, color=colors[idx])
        ax.fill(angles, values, alpha=0.15, color=colors[idx])
    
    # 设置
    ax.set_ylim(0, 1.1 if normalize else None)
    ax.set_title('模型多维度对比雷达图', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
    ax.grid(True)
    
    plt.tight_layout()
    
    # 保存
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path = save_path.parent / f"radar_chart{save_path.suffix}"
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"雷达图已保存：{save_path}")
    
    return fig


def plot_heatmap_comparison(
    metrics_df: pd.DataFrame,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 8),
    cmap: str = 'RdYlGn_r',
) -> plt.Figure:
    """
    绘制热力图对比
    
    Args:
        metrics_df: 指标 DataFrame
        save_path: 保存路径
        figsize: 图像大小
        cmap: 颜色映射
        
    Returns:
        Figure 对象
    """
    logger.info("绘制热力图...")
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # 创建热力图数据
    # 对误差类指标取反，使得绿色表示好，红色表示差
    heatmap_data = metrics_df.copy()
    for col in ['MAPE', 'RMSE', 'MAE']:
        if col in heatmap_data.columns:
            # 归一化并取反
            min_val = heatmap_data[col].min()
            max_val = heatmap_data[col].max()
            if max_val - min_val > 0:
                heatmap_data[col] = 1 - (heatmap_data[col] - min_val) / (max_val - min_val)
    
    # 绘制热力图
    im = ax.imshow(heatmap_data.values, cmap=cmap, aspect='auto')
    
    # 设置标签
    ax.set_xticks(np.arange(len(heatmap_data.columns)))
    ax.set_yticks(np.arange(len(heatmap_data.index)))
    ax.set_xticklabels(heatmap_data.columns, fontsize=11)
    ax.set_yticklabels(heatmap_data.index, fontsize=11)
    
    # 旋转 x 轴标签
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # 添加数值
    for i in range(len(heatmap_data.index)):
        for j in range(len(heatmap_data.columns)):
            text = ax.text(j, i, f'{heatmap_data.values[i, j]:.3f}',
                          ha="center", va="center", color="black", fontsize=9)
    
    # 颜色条
    cbar = ax.figure.colorbar(im)
    cbar.ax.set_ylabel('归一化得分', rotation=-90, va="bottom", labelpad=20)
    
    ax.set_title('模型性能热力图 (绿色=好，红色=差)', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    # 保存
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path = save_path.parent / f"heatmap_comparison{save_path.suffix}"
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"热力图已保存：{save_path}")
    
    return fig


def plot_time_comparison(
    train_times: Dict[str, float],
    predict_times: Dict[str, float],
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (12, 6),
) -> plt.Figure:
    """
    绘制时间对比图 (训练时间 + 预测时间)
    
    Args:
        train_times: 训练时间字典
        predict_times: 预测时间字典
        save_path: 保存路径
        figsize: 图像大小
        
    Returns:
        Figure 对象
    """
    logger.info("绘制时间对比图...")
    
    models = list(set(list(train_times.keys()) + list(predict_times.keys())))
    
    fig, ax = plt.subplots(figsize=figsize)
    
    x = np.arange(len(models))
    width = 0.35
    
    train_vals = [train_times.get(m, 0) for m in models]
    predict_vals = [predict_times.get(m, 0) for m in models]
    
    # 堆叠柱状图
    bars1 = ax.bar(x - width/2, train_vals, width, label='训练时间', color='#4CAF50', alpha=0.8)
    bars2 = ax.bar(x + width/2, predict_vals, width, label='预测时间', color='#2196F3', alpha=0.8)
    
    # 设置标签
    ax.set_xlabel('模型', fontsize=12)
    ax.set_ylabel('时间 (秒)', fontsize=12)
    ax.set_title('模型训练与预测时间对比', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=11)
    ax.legend()
    
    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax.annotate(f'{height:.2f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=9)
    
    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax.annotate(f'{height:.4f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=9)
    
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    # 保存
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path = save_path.parent / f"time_comparison{save_path.suffix}"
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"时间对比图已保存：{save_path}")
    
    return fig


def create_all_visualizations(
    metrics_df: pd.DataFrame,
    y_true: np.ndarray,
    predictions_dict: Dict[str, np.ndarray],
    train_times: Dict[str, float],
    predict_times: Dict[str, float],
    output_dir: str,
) -> Dict[str, str]:
    """
    创建所有可视化图表
    
    Args:
        metrics_df: 指标 DataFrame
        y_true: 真实值
        predictions_dict: 预测值字典
        train_times: 训练时间
        predict_times: 预测时间
        output_dir: 输出目录
        
    Returns:
        生成的文件路径字典
    """
    logger.info(f"创建所有可视化图表，输出目录：{output_dir}")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    files = {}
    
    # 1. 指标对比图
    try:
        path = output_dir / "metrics_comparison.png"
        plot_metrics_comparison(metrics_df, save_path=str(path))
        files['metrics'] = str(path)
    except Exception as e:
        logger.error(f"指标对比图生成失败：{e}")
    
    # 2. 预测对比图
    try:
        path = output_dir / "predictions_comparison.png"
        plot_predictions_comparison(y_true, predictions_dict, save_path=str(path))
        files['predictions'] = str(path)
    except Exception as e:
        logger.error(f"预测对比图生成失败：{e}")
    
    # 3. 残差对比图
    try:
        path = output_dir / "residuals_comparison.png"
        plot_residuals_comparison(y_true, predictions_dict, save_path=str(path))
        files['residuals'] = str(path)
    except Exception as e:
        logger.error(f"残差对比图生成失败：{e}")
    
    # 4. 雷达图
    try:
        path = output_dir / "radar_chart.png"
        plot_radar_chart(metrics_df, save_path=str(path))
        files['radar'] = str(path)
    except Exception as e:
        logger.error(f"雷达图生成失败：{e}")
    
    # 5. 热力图
    try:
        path = output_dir / "heatmap_comparison.png"
        plot_heatmap_comparison(metrics_df, save_path=str(path))
        files['heatmap'] = str(path)
    except Exception as e:
        logger.error(f"热力图生成失败：{e}")
    
    # 6. 时间对比图
    try:
        path = output_dir / "time_comparison.png"
        plot_time_comparison(train_times, predict_times, save_path=str(path))
        files['time'] = str(path)
    except Exception as e:
        logger.error(f"时间对比图生成失败：{e}")
    
    logger.info(f"可视化图表生成完成，共生成 {len(files)} 个文件")
    
    return files
