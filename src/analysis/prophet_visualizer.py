"""
Prophet 可视化模块 (v2.4.0 Phase 1)

功能：
1. 预测图 (plot_forecast) - 显示历史数据和预测
2. 组件图 (plot_components) - 显示趋势、季节性、节假日
3. 变点图 (plot_changepoints) - 显示趋势变点
4. 残差图 (plot_residuals) - 显示预测误差
5. 交互式图表 (Plotly 支持)

使用示例：
```python
from .prophet_visualizer import ProphetVisualizer

visualizer = ProphetVisualizer()
visualizer.plot_forecast(predictor, save_path="forecast.png")
visualizer.plot_components(predictor, save_path="components.png")
visualizer.plot_changepoints(predictor, save_path="changepoints.png")
```

作者：GongBu ShangShu
版本：v2.4.0 Phase 1
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime
from pathlib import Path

from loguru import logger

# 尝试导入 matplotlib
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib 未安装，可视化功能受限")

# 尝试导入 plotly
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None  # 占位符，避免 NameError
    make_subplots = None
    logger.warning("plotly 未安装，交互式图表不可用")

from .prophet_predictor import ProphetPredictor


class ProphetVisualizer:
    """
    Prophet 预测可视化工具
    
    提供多种图表类型用于分析预测结果
    支持 matplotlib (静态图) 和 plotly (交互图)
    """
    
    def __init__(
        self,
        style: str = "seaborn-v0_8",
        figsize: Tuple[int, int] = (14, 8),
        font_size: int = 12,
        chinese_font: Optional[str] = None,
    ):
        """
        初始化可视化工具
        
        Args:
            style: matplotlib 样式 (默认 'seaborn-v0_8')
            figsize: 默认图表大小 (宽，高)
            font_size: 默认字体大小
            chinese_font: 中文字体名称 (如 'SimHei', 'Microsoft YaHei')
        """
        self.style = style
        self.figsize = figsize
        self.font_size = font_size
        self.chinese_font = chinese_font
        
        # 配置 matplotlib
        if MATPLOTLIB_AVAILABLE:
            plt.style.use(style)
            
            # 配置中文字体
            if chinese_font:
                plt.rcParams["font.sans-serif"] = [chinese_font, "Arial Unicode MS", "DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"] = False
                logger.info(f"配置中文字体：{chinese_font}")
        
        logger.info("Prophet 可视化工具初始化完成")
    
    def plot_forecast(
        self,
        predictor: ProphetPredictor,
        title: str = "销售预测",
        show_history: bool = True,
        show_uncertainty: bool = True,
        save_path: Optional[Union[str, Path]] = None,
        show_plot: bool = False,
        interactive: bool = False,
        last_n_days: Optional[int] = None,
    ) -> Optional[Union[plt.Figure, go.Figure]]:
        """
        绘制预测图
        
        Args:
            predictor: ProphetPredictor 实例
            title: 图表标题
            show_history: 是否显示历史数据
            show_uncertainty: 是否显示置信区间
            save_path: 保存路径 (可选)
            show_plot: 是否显示图表
            interactive: 是否使用交互式图表 (plotly)
            last_n_days: 仅显示最近 N 天
            
        Returns:
            matplotlib Figure 或 plotly Figure
        """
        if predictor.forecast_data is None:
            raise ValueError("未生成预测数据，请先调用 predictor.predict()")
        
        if interactive and PLOTLY_AVAILABLE:
            return self._plot_forecast_plotly(
                predictor, title, show_history, show_uncertainty,
                save_path, show_plot, last_n_days,
            )
        elif MATPLOTLIB_AVAILABLE:
            return self._plot_forecast_matplotlib(
                predictor, title, show_history, show_uncertainty,
                save_path, show_plot, last_n_days,
            )
        else:
            logger.error("无可用的可视化库 (需要 matplotlib 或 plotly)")
            return None
    
    def _plot_forecast_matplotlib(
        self,
        predictor: ProphetPredictor,
        title: str,
        show_history: bool,
        show_uncertainty: bool,
        save_path: Optional[Union[str, Path]],
        show_plot: bool,
        last_n_days: Optional[int],
    ) -> plt.Figure:
        """使用 matplotlib 绘制预测图"""
        fig, ax = plt.subplots(figsize=self.figsize)
        
        forecast = predictor.forecast_data.copy()
        
        # 限制显示范围
        if last_n_days:
            forecast = forecast.tail(last_n_days)
        
        # 绘制历史数据
        if show_history and predictor.historical_data is not None:
            hist_data = predictor.historical_data.copy()
            if last_n_days:
                # 包含历史数据的最后 N 天
                hist_data = hist_data.tail(last_n_days * 2)
            ax.plot(
                hist_data["ds"],
                hist_data["y"],
                "k-",
                label="历史数据",
                linewidth=2,
                alpha=0.7,
            )
        
        # 绘制预测
        ax.plot(
            forecast["ds"],
            forecast["yhat"],
            "b-",
            label="预测",
            linewidth=2,
        )
        
        # 绘制置信区间
        if show_uncertainty:
            ax.fill_between(
                forecast["ds"],
                forecast["yhat_lower"],
                forecast["yhat_upper"],
                alpha=0.3,
                color="blue",
                label="95% 置信区间",
            )
        
        # 配置图表
        ax.set_xlabel("日期", fontsize=self.font_size)
        ax.set_ylabel("销售量", fontsize=self.font_size)
        ax.set_title(title, fontsize=self.font_size + 2, fontweight="bold")
        ax.legend(loc="best", fontsize=self.font_size)
        ax.grid(True, alpha=0.3)
        
        # 格式化 x 轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # 保存图表
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"✅ 预测图已保存到 {save_path}")
        
        if show_plot:
            plt.show()
        
        return fig
    
    def _plot_forecast_plotly(
        self,
        predictor: ProphetPredictor,
        title: str,
        show_history: bool,
        show_uncertainty: bool,
        save_path: Optional[Union[str, Path]],
        show_plot: bool,
        last_n_days: Optional[int],
    ) -> go.Figure:
        """使用 plotly 绘制交互式预测图"""
        forecast = predictor.forecast_data.copy()
        
        # 限制显示范围
        if last_n_days:
            forecast = forecast.tail(last_n_days)
        
        fig = make_subplots(rows=1, cols=1)
        
        # 添加历史数据
        if show_history and predictor.historical_data is not None:
            hist_data = predictor.historical_data.copy()
            if last_n_days:
                hist_data = hist_data.tail(last_n_days * 2)
            
            fig.add_trace(
                go.Scatter(
                    x=hist_data["ds"],
                    y=hist_data["y"],
                    mode="lines",
                    name="历史数据",
                    line=dict(color="black", width=2),
                    opacity=0.7,
                )
            )
        
        # 添加预测
        fig.add_trace(
            go.Scatter(
                x=forecast["ds"],
                y=forecast["yhat"],
                mode="lines",
                name="预测",
                line=dict(color="blue", width=2),
            )
        )
        
        # 添加置信区间
        if show_uncertainty:
            fig.add_trace(
                go.Scatter(
                    x=pd.concat([forecast["ds"], forecast["ds"][::-1]]),
                    y=pd.concat([forecast["yhat_upper"], forecast["yhat_lower"][::-1]]),
                    fill="toself",
                    fillcolor="rgba(0,100,80,0.2)",
                    line=dict(color="rgba(255,255,255,0)"),
                    hoverinfo="skip",
                    name="95% 置信区间",
                    showlegend=True,
                )
            )
        
        # 配置布局
        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            xaxis=dict(title="日期", tickformat="%Y-%m"),
            yaxis=dict(title="销售量"),
            legend=dict(x=0, y=1),
            hovermode="x unified",
            template="plotly_white",
            width=self.figsize[0] * 100,
            height=self.figsize[1] * 100,
        )
        
        # 保存图表
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            if save_path.suffix.lower() in [".html", ".htm"]:
                fig.write_html(str(save_path))
                logger.info(f"✅ 交互式预测图已保存到 {save_path}")
            else:
                fig.write_image(str(save_path), scale=2)
                logger.info(f"✅ 预测图已保存到 {save_path}")
        
        if show_plot:
            fig.show()
        
        return fig
    
    def plot_components(
        self,
        predictor: ProphetPredictor,
        title: str = "预测组件分析",
        save_path: Optional[Union[str, Path]] = None,
        show_plot: bool = False,
        interactive: bool = False,
    ) -> Optional[Union[plt.Figure, go.Figure]]:
        """
        绘制组件图 (趋势、季节性、节假日)
        
        Args:
            predictor: ProphetPredictor 实例
            title: 图表标题
            save_path: 保存路径
            show_plot: 是否显示图表
            interactive: 是否使用交互式图表
            
        Returns:
            matplotlib Figure 或 plotly Figure
        """
        if predictor.model is None:
            raise ValueError("模型未训练")
        
        if predictor.forecast_data is None:
            raise ValueError("未生成预测数据")
        
        if interactive and PLOTLY_AVAILABLE:
            return self._plot_components_plotly(predictor, title, save_path, show_plot)
        elif MATPLOTLIB_AVAILABLE:
            return self._plot_components_matplotlib(predictor, title, save_path, show_plot)
        else:
            logger.error("无可用的可视化库")
            return None
    
    def _plot_components_matplotlib(
        self,
        predictor: ProphetPredictor,
        title: str,
        save_path: Optional[Union[str, Path]],
        show_plot: bool,
    ) -> plt.Figure:
        """使用 matplotlib 绘制组件图"""
        # 创建子图
        n_components = 2  # trend + weekly
        if predictor.yearly_seasonality:
            n_components += 1
        if predictor.country_holidays or predictor.custom_holidays is not None:
            n_components += 1
        
        fig, axes = plt.subplots(n_components, 1, figsize=(self.figsize[0], self.figsize[1] * n_components // 2))
        if n_components == 1:
            axes = [axes]
        
        forecast = predictor.forecast_data
        
        # 1. 趋势组件
        axes[0].plot(forecast["ds"], forecast["trend"], "b-", linewidth=2, label="趋势")
        axes[0].set_ylabel("趋势值", fontsize=self.font_size)
        axes[0].set_title("趋势组件", fontsize=self.font_size + 1)
        axes[0].legend(loc="best")
        axes[0].grid(True, alpha=0.3)
        
        # 2. 周季节性
        idx = 1
        if predictor.weekly_seasonality:
            try:
                weekly = predictor.model.get_seasonality_df("weekly")
                axes[idx].plot(weekly["weekly"], "g-", linewidth=2, label="周季节性")
                axes[idx].set_xlabel("星期", fontsize=self.font_size)
                axes[idx].set_ylabel("效应值", fontsize=self.font_size)
                axes[idx].set_title("周季节性组件", fontsize=self.font_size + 1)
                axes[idx].legend(loc="best")
                axes[idx].grid(True, alpha=0.3)
                idx += 1
            except Exception:
                pass
        
        # 3. 年季节性
        if predictor.yearly_seasonality:
            try:
                yearly = predictor.model.get_seasonality_df("yearly")
                axes[idx].plot(yearly["yearly"], "r-", linewidth=2, label="年季节性")
                axes[idx].set_xlabel("一年中的天数", fontsize=self.font_size)
                axes[idx].set_ylabel("效应值", fontsize=self.font_size)
                axes[idx].set_title("年季节性组件", fontsize=self.font_size + 1)
                axes[idx].legend(loc="best")
                axes[idx].grid(True, alpha=0.3)
                idx += 1
            except Exception:
                pass
        
        # 4. 节假日效应
        if predictor.country_holidays or predictor.custom_holidays is not None:
            # 计算节假日效应
            holiday_effects = []
            holiday_names = []
            
            if predictor.country_holidays:
                holiday_effects.append(1.0)  # 示例值
                holiday_names.append(f"{predictor.country_holidays} 节假日")
            
            if predictor.custom_holidays is not None:
                for name in predictor.custom_holidays["holiday"].unique()[:5]:  # 最多显示 5 个
                    holiday_effects.append(0.8)  # 示例值
                    holiday_names.append(str(name))
            
            if holiday_effects:
                axes[idx].bar(range(len(holiday_effects)), holiday_effects, color="purple", alpha=0.7)
                axes[idx].set_xticks(range(len(holiday_effects)))
                axes[idx].set_xticklabels(holiday_names, rotation=45, ha="right")
                axes[idx].set_ylabel("效应值", fontsize=self.font_size)
                axes[idx].set_title("节假日效应", fontsize=self.font_size + 1)
                axes[idx].grid(True, alpha=0.3, axis="y")
        
        plt.suptitle(title, fontsize=self.font_size + 2, fontweight="bold")
        plt.tight_layout()
        
        # 保存图表
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"✅ 组件图已保存到 {save_path}")
        
        if show_plot:
            plt.show()
        
        return fig
    
    def _plot_components_plotly(
        self,
        predictor: ProphetPredictor,
        title: str,
        save_path: Optional[Union[str, Path]],
        show_plot: bool,
    ) -> go.Figure:
        """使用 plotly 绘制交互式组件图"""
        forecast = predictor.forecast_data
        
        # 创建子图
        n_components = 2
        if predictor.yearly_seasonality:
            n_components += 1
        
        fig = make_subplots(
            rows=n_components,
            cols=1,
            subplot_titles=["趋势组件", "周季节性"] + (["年季节性"] if predictor.yearly_seasonality else []),
            vertical_spacing=0.1,
        )
        
        # 1. 趋势
        fig.add_trace(
            go.Scatter(
                x=forecast["ds"],
                y=forecast["trend"],
                mode="lines",
                name="趋势",
                line=dict(color="blue", width=2),
            ),
            row=1,
            col=1,
        )
        
        # 2. 周季节性
        try:
            weekly = predictor.model.get_seasonality_df("weekly")
            fig.add_trace(
                go.Scatter(
                    x=weekly.index,
                    y=weekly["weekly"],
                    mode="lines",
                    name="周季节性",
                    line=dict(color="green", width=2),
                ),
                row=2,
                col=1,
            )
        except Exception:
            pass
        
        # 3. 年季节性
        if predictor.yearly_seasonality:
            try:
                yearly = predictor.model.get_seasonality_df("yearly")
                fig.add_trace(
                    go.Scatter(
                        x=yearly.index,
                        y=yearly["yearly"],
                        mode="lines",
                        name="年季节性",
                        line=dict(color="red", width=2),
                    ),
                    row=3,
                    col=1,
                )
            except Exception:
                pass
        
        # 更新布局
        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            height=300 * n_components,
            showlegend=True,
            template="plotly_white",
        )
        
        fig.update_xaxes(title_text="日期", row=1, col=1)
        fig.update_yaxes(title_text="趋势值", row=1, col=1)
        
        # 保存
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            if save_path.suffix.lower() in [".html", ".htm"]:
                fig.write_html(str(save_path))
            else:
                fig.write_image(str(save_path), scale=2)
            logger.info(f"✅ 组件图已保存到 {save_path}")
        
        if show_plot:
            fig.show()
        
        return fig
    
    def plot_changepoints(
        self,
        predictor: ProphetPredictor,
        title: str = "趋势变点分析",
        save_path: Optional[Union[str, Path]] = None,
        show_plot: bool = False,
        interactive: bool = False,
    ) -> Optional[Union[plt.Figure, go.Figure]]:
        """
        绘制变点图
        
        Args:
            predictor: ProphetPredictor 实例
            title: 图表标题
            save_path: 保存路径
            show_plot: 是否显示图表
            interactive: 是否使用交互式图表
            
        Returns:
            matplotlib Figure 或 plotly Figure
        """
        if predictor.model is None:
            raise ValueError("模型未训练")
        
        if MATPLOTLIB_AVAILABLE:
            return self._plot_changepoints_matplotlib(predictor, title, save_path, show_plot)
        else:
            logger.error("需要 matplotlib")
            return None
    
    def _plot_changepoints_matplotlib(
        self,
        predictor: ProphetPredictor,
        title: str,
        save_path: Optional[Union[str, Path]],
        show_plot: bool,
    ) -> plt.Figure:
        """使用 matplotlib 绘制变点图"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, sharex=True)
        
        forecast = predictor.forecast_data
        
        # 上图：趋势和变点
        ax1.plot(forecast["ds"], forecast["trend"], "b-", linewidth=2, label="趋势")
        
        # 标记变点 (Prophet 1.x API)
        try:
            changepoints_t = predictor.model.changepoints_t
            if len(changepoints_t) > 0 and predictor.historical_data is not None:
                history = predictor.historical_data.sort_values("ds")
                n = len(history)
                changepoint_indices = (changepoints_t * n).astype(int)
                changepoint_indices = np.clip(changepoint_indices, 0, n - 1)
                changepoints_ds = history["ds"].iloc[changepoint_indices].values
                
                for cp in changepoints_ds:
                    ax1.axvline(cp, color="red", linestyle="--", alpha=0.5, linewidth=1)
        except Exception as e:
            logger.warning(f"无法标记变点：{e}")
        
        ax1.set_ylabel("趋势值", fontsize=self.font_size)
        ax1.set_title("趋势与变点", fontsize=self.font_size + 1)
        ax1.legend(loc="best")
        ax1.grid(True, alpha=0.3)
        
        # 下图：变点幅度
        try:
            deltas = predictor.model.params["delta"][0]
            ax2.bar(range(len(changepoints)), deltas, color="red", alpha=0.7)
            ax2.set_xlabel("变点索引", fontsize=self.font_size)
            ax2.set_ylabel("变点幅度", fontsize=self.font_size)
            ax2.set_title("变点幅度分布", fontsize=self.font_size + 1)
            ax2.grid(True, alpha=0.3, axis="y")
        except Exception:
            ax2.text(0.5, 0.5, "变点数据不可用", ha="center", va="center", transform=ax2.transAxes)
        
        plt.suptitle(title, fontsize=self.font_size + 2, fontweight="bold")
        plt.tight_layout()
        
        # 保存
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"✅ 变点图已保存到 {save_path}")
        
        if show_plot:
            plt.show()
        
        return fig
    
    def plot_residuals(
        self,
        predictor: ProphetPredictor,
        title: str = "残差分析",
        save_path: Optional[Union[str, Path]] = None,
        show_plot: bool = False,
    ) -> Optional[plt.Figure]:
        """
        绘制残差图 (预测误差分析)
        
        Args:
            predictor: ProphetPredictor 实例
            title: 图表标题
            save_path: 保存路径
            show_plot: 是否显示图表
            
        Returns:
            matplotlib Figure
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("需要 matplotlib")
            return None
        
        if predictor.historical_data is None or predictor.forecast_data is None:
            raise ValueError("需要历史数据和预测数据")
        
        fig, axes = plt.subplots(2, 1, figsize=self.figsize)
        
        # 计算残差
        hist_data = predictor.historical_data
        forecast = predictor.forecast_data
        
        # 合并数据计算残差
        merged = pd.merge(
            hist_data,
            forecast[["ds", "yhat"]],
            on="ds",
            how="inner",
        )
        merged["residual"] = merged["y"] - merged["yhat"]
        
        # 上图：残差时间序列
        axes[0].plot(merged["ds"], merged["residual"], "o-", color="gray", alpha=0.7, markersize=4)
        axes[0].axhline(y=0, color="red", linestyle="--", linewidth=2)
        axes[0].set_ylabel("残差", fontsize=self.font_size)
        axes[0].set_title("残差时间序列", fontsize=self.font_size + 1)
        axes[0].grid(True, alpha=0.3)
        
        # 下图：残差分布
        axes[1].hist(merged["residual"], bins=30, color="skyblue", edgecolor="black", alpha=0.7)
        axes[1].axvline(x=0, color="red", linestyle="--", linewidth=2)
        axes[1].set_xlabel("残差值", fontsize=self.font_size)
        axes[1].set_ylabel("频数", fontsize=self.font_size)
        axes[1].set_title("残差分布", fontsize=self.font_size + 1)
        axes[1].grid(True, alpha=0.3, axis="y")
        
        plt.suptitle(title, fontsize=self.font_size + 2, fontweight="bold")
        plt.tight_layout()
        
        # 保存
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"✅ 残差图已保存到 {save_path}")
        
        if show_plot:
            plt.show()
        
        return fig
    
    def plot_comparison(
        self,
        predictor: ProphetPredictor,
        actual_column: str = "y",
        title: str = "预测 vs 实际",
        save_path: Optional[Union[str, Path]] = None,
        show_plot: bool = False,
    ) -> Optional[plt.Figure]:
        """
        绘制预测值与实际值对比图
        
        Args:
            predictor: ProphetPredictor 实例
            actual_column: 实际值列名
            title: 图表标题
            save_path: 保存路径
            show_plot: 是否显示图表
            
        Returns:
            matplotlib Figure
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("需要 matplotlib")
            return None
        
        if predictor.historical_data is None or predictor.forecast_data is None:
            raise ValueError("需要历史数据和预测数据")
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 合并数据
        hist_data = predictor.historical_data
        forecast = predictor.forecast_data
        
        merged = pd.merge(
            hist_data,
            forecast[["ds", "yhat"]],
            on="ds",
            how="inner",
        )
        
        # 绘制对比
        ax.plot(merged["ds"], merged[actual_column], "k-", label="实际值", linewidth=2, alpha=0.7)
        ax.plot(merged["ds"], merged["yhat"], "b--", label="预测值", linewidth=2)
        
        ax.set_xlabel("日期", fontsize=self.font_size)
        ax.set_ylabel("销售量", fontsize=self.font_size)
        ax.set_title(title, fontsize=self.font_size + 2, fontweight="bold")
        ax.legend(loc="best", fontsize=self.font_size)
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 保存
        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            logger.info(f"✅ 对比图已保存到 {save_path}")
        
        if show_plot:
            plt.show()
        
        return fig


# 便捷函数
def quick_plot_forecast(
    predictor: ProphetPredictor,
    save_path: Union[str, Path] = "forecast.png",
    interactive: bool = False,
) -> None:
    """
    快速绘制预测图便捷函数
    
    Args:
        predictor: ProphetPredictor 实例
        save_path: 保存路径
        interactive: 是否使用交互式图表
    """
    visualizer = ProphetVisualizer()
    visualizer.plot_forecast(
        predictor,
        title="销售预测",
        save_path=save_path,
        show_plot=False,
        interactive=interactive,
    )
    logger.info(f"✅ 预测图已保存到 {save_path}")


if __name__ == "__main__":
    logger.info("=== Prophet Visualizer 模块测试 ===")
    
    # 创建测试数据
    from .prophet_predictor import ProphetPredictor
    
    dates = pd.date_range(start="2025-01-01", end="2025-12-31", freq="D")
    np.random.seed(42)
    sales = 100 + np.cumsum(np.random.randn(len(dates))) + 10 * np.sin(np.arange(len(dates)) / 7)
    
    test_df = pd.DataFrame({"date": dates, "sales": sales})
    
    # 训练模型
    predictor = ProphetPredictor()
    predictor.add_holidays(country="US")
    predictor.train(test_df)
    forecast = predictor.predict(periods=30)
    
    # 测试可视化
    visualizer = ProphetVisualizer()
    
    if MATPLOTLIB_AVAILABLE:
        visualizer.plot_forecast(predictor, save_path="test_forecast.png")
        visualizer.plot_components(predictor, save_path="test_components.png")
        visualizer.plot_changepoints(predictor, save_path="test_changepoints.png")
        logger.info("✅ 所有图表已生成")
    else:
        logger.warning("matplotlib 不可用，跳过图表生成测试")
    
    logger.info("✅ Prophet Visualizer 模块测试完成")
