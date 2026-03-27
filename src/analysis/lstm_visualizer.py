"""
LSTM 可视化模块 (v2.4 Phase 2)

用于 LSTM 模型训练和预测结果的可视化

功能:
- 训练历史可视化
- 预测对比图
- 残差分析图
- 模型架构图
- 特征重要性图
- 预测区间图

Author: OpenClaw Imperial - Gongbu Shangshu
Version: 2.4.0 Phase 2
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

# matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure

# 设置中文字体支持
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

logger = logging.getLogger(__name__)


def plot_training_history(
    history: Dict[str, List[float]],
    figsize: Tuple[int, int] = (12, 6),
    save_path: Optional[str] = None,
    show: bool = True,
) -> Figure:
    """
    绘制训练历史 (loss/metrics)
    
    Args:
        history: 训练历史记录 (model.history.history)
        figsize: 图像大小
        save_path: 保存路径 (可选)
        show: 是否显示图像
        
    Returns:
        matplotlib Figure 对象
    """
    logger.info("绘制训练历史图")
    
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    
    # 1. Loss 曲线
    ax = axes[0]
    ax.plot(history["loss"], label="Train Loss", linewidth=2)
    if "val_loss" in history:
        ax.plot(history["val_loss"], label="Val Loss", linewidth=2)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss (MSE)")
    ax.set_title("训练损失")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. MAE 曲线
    ax = axes[1]
    ax.plot(history["mae"], label="Train MAE", linewidth=2)
    if "val_mae" in history:
        ax.plot(history["val_mae"], label="Val MAE", linewidth=2)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MAE")
    ax.set_title("平均绝对误差")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. MAPE 曲线
    ax = axes[2]
    if "mape" in history:
        ax.plot(history["mape"], label="Train MAPE", linewidth=2)
        if "val_mape" in history:
            ax.plot(history["val_mape"], label="Val MAPE", linewidth=2)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("MAPE (%)")
        ax.set_title("平均绝对百分比误差")
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图像
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"训练历史图已保存：{save_path}")
    
    if not show:
        plt.close(fig)
    
    return fig


def plot_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    dates: Optional[pd.DatetimeIndex] = None,
    figsize: Tuple[int, int] = (14, 7),
    save_path: Optional[str] = None,
    show: bool = True,
    title: str = "预测对比",
) -> Figure:
    """
    绘制预测对比图
    
    Args:
        y_true: 真实值
        y_pred: 预测值
        dates: 日期索引 (可选)
        figsize: 图像大小
        save_path: 保存路径 (可选)
        show: 是否显示图像
        title: 图表标题
        
    Returns:
        matplotlib Figure 对象
    """
    logger.info("绘制预测对比图")
    
    fig, axes = plt.subplots(2, 1, figsize=figsize)
    
    # 创建 x 轴
    if dates is not None:
        x = dates[:len(y_true)]
        x_pred = dates[:len(y_pred)]
    else:
        x = np.arange(len(y_true))
        x_pred = np.arange(len(y_pred))
    
    # 1. 时间序列对比
    ax = axes[0]
    ax.plot(x, y_true, label="真实值", linewidth=2, alpha=0.8)
    ax.plot(x_pred, y_pred, label="预测值", linewidth=2, alpha=0.8, linestyle="--")
    ax.set_xlabel("时间" if dates is not None else "样本")
    ax.set_ylabel("销量")
    ax.set_title(f"{title} - 时间序列对比")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    if dates is not None:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    # 2. 散点对比图 (真实值 vs 预测值)
    ax = axes[1]
    ax.scatter(y_true, y_pred, alpha=0.5, s=20)
    
    # 添加对角线
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    ax.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=2, label="完美预测")
    
    ax.set_xlabel("真实值")
    ax.set_ylabel("预测值")
    ax.set_title("真实值 vs 预测值")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 计算并显示 R²
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    ax.text(
        0.05, 0.95,
        f"R² = {r2:.4f}",
        transform=ax.transAxes,
        fontsize=12,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )
    
    plt.tight_layout()
    
    # 保存图像
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"预测对比图已保存：{save_path}")
    
    if not show:
        plt.close(fig)
    
    return fig


def plot_residuals(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    figsize: Tuple[int, int] = (14, 6),
    save_path: Optional[str] = None,
    show: bool = True,
) -> Figure:
    """
    绘制残差图
    
    Args:
        y_true: 真实值
        y_pred: 预测值
        figsize: 图像大小
        save_path: 保存路径 (可选)
        show: 是否显示图像
        
    Returns:
        matplotlib Figure 对象
    """
    logger.info("绘制残差图")
    
    residuals = y_true - y_pred
    
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    # 1. 残差分布直方图
    ax = axes[0]
    ax.hist(residuals, bins=50, edgecolor="black", alpha=0.7)
    ax.axvline(x=0, color="r", linestyle="--", linewidth=2, label="零残差")
    ax.set_xlabel("残差")
    ax.set_ylabel("频数")
    ax.set_title("残差分布")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 添加正态分布曲线
    from scipy import stats
    mu, sigma = np.mean(residuals), np.std(residuals)
    x = np.linspace(residuals.min(), residuals.max(), 100)
    ax.plot(x, stats.norm.pdf(x, mu, sigma) * len(residuals) * (residuals.max() - residuals.min()) / 50,
            "r-", linewidth=2, label="正态拟合")
    ax.legend()
    
    # 2. 残差 vs 预测值
    ax = axes[1]
    ax.scatter(y_pred, residuals, alpha=0.5, s=20)
    ax.axhline(y=0, color="r", linestyle="--", linewidth=2)
    ax.set_xlabel("预测值")
    ax.set_ylabel("残差")
    ax.set_title("残差 vs 预测值")
    ax.grid(True, alpha=0.3)
    
    # 添加 ±2σ 线
    ax.axhline(y=2 * sigma, color="orange", linestyle=":", alpha=0.7, label="±2σ")
    ax.axhline(y=-2 * sigma, color="orange", linestyle=":", alpha=0.7)
    ax.legend()
    
    plt.tight_layout()
    
    # 保存图像
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"残差图已保存：{save_path}")
    
    if not show:
        plt.close(fig)
    
    return fig


def plot_architecture(
    model: Any,
    figsize: Tuple[int, int] = (10, 8),
    save_path: Optional[str] = None,
    show: bool = True,
) -> Figure:
    """
    绘制模型架构图
    
    Args:
        model: Keras 模型
        figsize: 图像大小
        save_path: 保存路径 (可选)
        show: 是否显示图像
        
    Returns:
        matplotlib Figure 对象
    """
    logger.info("绘制模型架构图")
    
    try:
        from tensorflow.keras.utils import plot_model
        import tempfile
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
        
        plot_model(
            model,
            to_file=temp_path,
            show_shapes=True,
            show_layer_names=True,
            expand_nested=True,
            dpi=150,
        )
        
        # 读取并显示
        fig, ax = plt.subplots(figsize=figsize)
        img = plt.imread(temp_path)
        ax.imshow(img)
        ax.axis("off")
        ax.set_title("LSTM 模型架构")
        
        plt.tight_layout()
        
        # 保存
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"模型架构图已保存：{save_path}")
        
        # 清理临时文件
        Path(temp_path).unlink()
        
        if not show:
            plt.close(fig)
        
        return fig
        
    except Exception as e:
        logger.warning(f"无法绘制模型架构图：{e}")
        # 返回文本摘要
        print("\n模型架构摘要:")
        model.summary()
        return None


def plot_feature_importance(
    importance: np.ndarray,
    feature_names: Optional[List[str]] = None,
    top_n: int = 20,
    figsize: Tuple[int, int] = (10, 8),
    save_path: Optional[str] = None,
    show: bool = True,
) -> Figure:
    """
    绘制特征重要性图
    
    Args:
        importance: 特征重要性数组
        feature_names: 特征名称列表
        top_n: 显示前 N 个特征
        figsize: 图像大小
        save_path: 保存路径 (可选)
        show: 是否显示图像
        
    Returns:
        matplotlib Figure 对象
    """
    logger.info("绘制特征重要性图")
    
    # 创建特征名称 (如果未提供)
    if feature_names is None:
        feature_names = [f"Day {i}" for i in range(len(importance))]
    
    # 排序
    indices = np.argsort(importance)[::-1][:top_n]
    sorted_importance = importance[indices]
    sorted_names = [feature_names[i] for i in indices]
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # 水平条形图
    y_pos = np.arange(len(sorted_importance))
    bars = ax.barh(y_pos, sorted_importance, color=plt.cm.viridis(np.linspace(0.2, 0.8, len(sorted_importance))))
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sorted_names)
    ax.invert_yaxis()
    ax.set_xlabel("重要性")
    ax.set_title(f"Top {top_n} 特征重要性")
    
    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars, sorted_importance)):
        ax.text(
            bar.get_width() + 0.001,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.4f}",
            va="center",
            fontsize=9,
        )
    
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    
    # 保存图像
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"特征重要性图已保存：{save_path}")
    
    if not show:
        plt.close(fig)
    
    return fig


def plot_forecast_with_interval(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_pred_lower: Optional[np.ndarray] = None,
    y_pred_upper: Optional[np.ndarray] = None,
    dates: Optional[pd.DatetimeIndex] = None,
    confidence_level: float = 0.95,
    figsize: Tuple[int, int] = (14, 7),
    save_path: Optional[str] = None,
    show: bool = True,
) -> Figure:
    """
    绘制带预测区间的预测图
    
    Args:
        y_true: 真实值
        y_pred: 预测值
        y_pred_lower: 预测下界 (可选)
        y_pred_upper: 预测上界 (可选)
        dates: 日期索引
        confidence_level: 置信水平
        figsize: 图像大小
        save_path: 保存路径 (可选)
        show: 是否显示图像
        
    Returns:
        matplotlib Figure 对象
    """
    logger.info("绘制带预测区间的预测图")
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # 创建 x 轴
    if dates is not None:
        x_true = dates[:len(y_true)]
        x_pred = dates[:len(y_pred)]
    else:
        x_true = np.arange(len(y_true))
        x_pred = np.arange(len(y_pred))
    
    # 绘制真实值
    ax.plot(x_true, y_true, label="真实值", linewidth=2, color="blue", alpha=0.8)
    
    # 绘制预测值
    ax.plot(x_pred, y_pred, label="预测值", linewidth=2, color="red", linestyle="--")
    
    # 绘制预测区间
    if y_pred_lower is not None and y_pred_upper is not None:
        ax.fill_between(
            x_pred,
            y_pred_lower,
            y_pred_upper,
            alpha=0.3,
            color="red",
            label=f"{confidence_level*100:.0f}% 置信区间",
        )
    else:
        # 如果没有提供区间，使用标准差估算
        std = np.std(y_true - y_pred[:len(y_true)])
        z = 1.96  # 95% 置信水平
        lower = y_pred - z * std
        upper = y_pred + z * std
        ax.fill_between(
            x_pred,
            lower,
            upper,
            alpha=0.3,
            color="red",
            label=f"估算 {confidence_level*100:.0f}% 置信区间",
        )
    
    ax.set_xlabel("时间" if dates is not None else "样本")
    ax.set_ylabel("销量")
    ax.set_title("销售预测 (带置信区间)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    if dates is not None:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    
    # 保存图像
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"预测区间图已保存：{save_path}")
    
    if not show:
        plt.close(fig)
    
    return fig


def plot_comparison_all(
    y_true: np.ndarray,
    y_pred_lstm: np.ndarray,
    y_pred_prophet: Optional[np.ndarray] = None,
    dates: Optional[pd.DatetimeIndex] = None,
    figsize: Tuple[int, int] = (16, 10),
    save_path: Optional[str] = None,
    show: bool = True,
) -> Figure:
    """
    绘制多模型对比图
    
    Args:
        y_true: 真实值
        y_pred_lstm: LSTM 预测值
        y_pred_prophet: Prophet 预测值 (可选)
        dates: 日期索引
        figsize: 图像大小
        save_path: 保存路径 (可选)
        show: 是否显示图像
        
    Returns:
        matplotlib Figure 对象
    """
    logger.info("绘制多模型对比图")
    
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    
    # 创建 x 轴
    if dates is not None:
        x = dates[:len(y_true)]
    else:
        x = np.arange(len(y_true))
    
    # 1. 时间序列对比
    ax = axes[0, 0]
    ax.plot(x, y_true, label="真实值", linewidth=2, alpha=0.8)
    ax.plot(x, y_pred_lstm, label="LSTM 预测", linewidth=2, linestyle="--")
    if y_pred_prophet is not None:
        ax.plot(x, y_pred_prophet, label="Prophet 预测", linewidth=2, linestyle=":")
    ax.set_xlabel("时间")
    ax.set_ylabel("销量")
    ax.set_title("多模型预测对比")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. LSTM 散点对比
    ax = axes[0, 1]
    ax.scatter(y_true, y_pred_lstm, alpha=0.5, s=20, label="LSTM")
    min_val = min(y_true.min(), y_pred_lstm.min())
    max_val = max(y_true.max(), y_pred_lstm.max())
    ax.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=2)
    ax.set_xlabel("真实值")
    ax.set_ylabel("LSTM 预测值")
    ax.set_title("LSTM: 真实值 vs 预测值")
    ax.grid(True, alpha=0.3)
    
    # 3. Prophet 散点对比 (如果有)
    ax = axes[1, 0]
    if y_pred_prophet is not None:
        ax.scatter(y_true, y_pred_prophet, alpha=0.5, s=20, label="Prophet", color="green")
        ax.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=2)
        ax.set_xlabel("真实值")
        ax.set_ylabel("Prophet 预测值")
        ax.set_title("Prophet: 真实值 vs 预测值")
    else:
        ax.text(0.5, 0.5, "Prophet 预测\n不可用", ha="center", va="center", fontsize=16)
        ax.set_title("Prophet: 真实值 vs 预测值")
    ax.grid(True, alpha=0.3)
    
    # 4. 残差对比
    ax = axes[1, 1]
    residuals_lstm = y_true - y_pred_lstm
    ax.hist(residuals_lstm, bins=30, alpha=0.7, label="LSTM", edgecolor="black")
    if y_pred_prophet is not None:
        residuals_prophet = y_true - y_pred_prophet
        ax.hist(residuals_prophet, bins=30, alpha=0.7, label="Prophet", edgecolor="black")
    ax.set_xlabel("残差")
    ax.set_ylabel("频数")
    ax.set_title("残差分布对比")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图像
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"多模型对比图已保存：{save_path}")
    
    if not show:
        plt.close(fig)
    
    return fig


def create_dashboard(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    history: Dict[str, List[float]],
    metrics: Dict[str, float],
    dates: Optional[pd.DatetimeIndex] = None,
    save_path: Optional[str] = None,
    show: bool = True,
) -> Figure:
    """
    创建综合仪表板
    
    Args:
        y_true: 真实值
        y_pred: 预测值
        history: 训练历史
        metrics: 评估指标
        dates: 日期索引
        save_path: 保存路径 (可选)
        show: 是否显示图像
        
    Returns:
        matplotlib Figure 对象
    """
    logger.info("创建综合仪表板")
    
    fig = plt.figure(figsize=(20, 12))
    
    # 创建网格布局
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # 1. 预测对比 (左上，跨两列)
    ax1 = fig.add_subplot(gs[0, :2])
    if dates is not None:
        x = dates[:len(y_true)]
    else:
        x = np.arange(len(y_true))
    ax1.plot(x, y_true, label="真实值", linewidth=2, alpha=0.8)
    ax1.plot(x, y_pred, label="预测值", linewidth=2, linestyle="--")
    ax1.set_xlabel("时间")
    ax1.set_ylabel("销量")
    ax1.set_title("LSTM 销售预测")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 指标展示 (右上)
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.axis("off")
    metrics_text = "评估指标\n" + "=" * 30 + "\n"
    for key, value in metrics.items():
        if isinstance(value, float):
            metrics_text += f"{key}: {value:.4f}\n"
        else:
            metrics_text += f"{key}: {value}\n"
    ax2.text(0.1, 0.5, metrics_text, fontsize=12, family="monospace", verticalalignment="center")
    ax2.set_title("模型性能", fontsize=14, fontweight="bold")
    
    # 3. 训练 Loss (中左)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(history["loss"], label="Train", linewidth=2)
    if "val_loss" in history:
        ax3.plot(history["val_loss"], label="Val", linewidth=2)
    ax3.set_xlabel("Epoch")
    ax3.set_ylabel("Loss")
    ax3.set_title("训练损失")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 训练 MAPE (中中)
    ax4 = fig.add_subplot(gs[1, 1])
    if "mape" in history:
        ax4.plot(history["mape"], label="Train MAPE", linewidth=2)
        if "val_mape" in history:
            ax4.plot(history["val_mape"], label="Val MAPE", linewidth=2)
        ax4.set_xlabel("Epoch")
        ax4.set_ylabel("MAPE (%)")
        ax4.set_title("MAPE 趋势")
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    
    # 5. 散点对比 (中右)
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.scatter(y_true, y_pred, alpha=0.5, s=20)
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    ax5.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=2)
    ax5.set_xlabel("真实值")
    ax5.set_ylabel("预测值")
    ax5.set_title("预测准确性")
    ax5.grid(True, alpha=0.3)
    
    # 6. 残差分布 (下左)
    ax6 = fig.add_subplot(gs[2, 0])
    residuals = y_true - y_pred
    ax6.hist(residuals, bins=30, edgecolor="black", alpha=0.7)
    ax6.axvline(x=0, color="r", linestyle="--", linewidth=2)
    ax6.set_xlabel("残差")
    ax6.set_ylabel("频数")
    ax6.set_title("残差分布")
    ax6.grid(True, alpha=0.3)
    
    # 7. 残差 vs 预测 (下中)
    ax7 = fig.add_subplot(gs[2, 1])
    ax7.scatter(y_pred, residuals, alpha=0.5, s=20)
    ax7.axhline(y=0, color="r", linestyle="--", linewidth=2)
    ax7.set_xlabel("预测值")
    ax7.set_ylabel("残差")
    ax7.set_title("残差分析")
    ax7.grid(True, alpha=0.3)
    
    # 8. 预测误差趋势 (下右)
    ax8 = fig.add_subplot(gs[2, 2])
    abs_errors = np.abs(residuals)
    if dates is not None:
        x_err = dates[:len(abs_errors)]
    else:
        x_err = np.arange(len(abs_errors))
    ax8.plot(x_err, abs_errors, linewidth=1, alpha=0.7)
    ax8.axhline(y=np.mean(abs_errors), color="r", linestyle="--", label="平均误差")
    ax8.set_xlabel("时间")
    ax8.set_ylabel("绝对误差")
    ax8.set_title("预测误差趋势")
    ax8.legend()
    ax8.grid(True, alpha=0.3)
    
    # 添加总标题
    fig.suptitle("LSTM 深度学习预测 - 综合仪表板", fontsize=16, fontweight="bold", y=0.98)
    
    # 保存图像
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"综合仪表板已保存：{save_path}")
    
    if not show:
        plt.close(fig)
    
    return fig


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 生成模拟数据
    np.random.seed(42)
    n = 365
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    
    trend = np.linspace(100, 200, n)
    seasonality = 20 * np.sin(np.arange(n) * 2 * np.pi / 7)
    noise = np.random.randn(n) * 10
    y_true = trend + seasonality + noise
    y_pred = y_true + np.random.randn(n) * 5
    
    # 模拟训练历史
    history = {
        "loss": np.linspace(100, 10, 50),
        "val_loss": np.linspace(110, 15, 50),
        "mae": np.linspace(8, 2, 50),
        "val_mae": np.linspace(9, 3, 50),
        "mape": np.linspace(15, 5, 50),
        "val_mape": np.linspace(16, 6, 50),
    }
    
    # 模拟指标
    metrics = {
        "MAPE": 5.6,
        "RMSE": 8.2,
        "MAE": 6.1,
        "R2": 0.92,
    }
    
    print("\n" + "=" * 50)
    print("LSTM 可视化模块测试")
    print("=" * 50)
    
    # 测试各个可视化函数
    fig1 = plot_training_history(history, show=False)
    print("✓ 训练历史图生成成功")
    
    fig2 = plot_predictions(y_true, y_pred, dates=dates, show=False)
    print("✓ 预测对比图生成成功")
    
    fig3 = plot_residuals(y_true, y_pred, show=False)
    print("✓ 残差图生成成功")
    
    fig4 = create_dashboard(y_true, y_pred, history, metrics, dates=dates, show=False)
    print("✓ 综合仪表板生成成功")
    
    plt.close("all")
    print("\n✅ 所有可视化测试通过")
    print("=" * 50)
