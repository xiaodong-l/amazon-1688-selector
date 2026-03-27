"""
数据可视化模块 (增强版 v2.1)

功能：
1. 销量趋势对比图 (柱状图)
2. 价格分布图 (直方图)
3. 评分 - 销量关系图 (散点图)
4. 多维度雷达图
5. 指标相关性热力图
6. 趋势预测图 (带置信区间)

支持保存为 PNG 和 HTML 交互式图表

变更日志:
- v2.1: 添加缓存机制，使用工具函数，统一配置管理
"""
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from loguru import logger
from functools import lru_cache
import hashlib
import json

from ..utils.config import (
    DATA_DIR, 
    VISUALIZATION_CONFIG,
    CACHE_CONFIG,
)
from ..utils.helpers import (
    parse_price,
    truncate_text,
    calculate_data_hash,
)


# 配置中文字体
def setup_chinese_font():
    """设置中文字体支持"""
    # 尝试常见中文字体
    chinese_fonts = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC']
    
    for font in chinese_fonts:
        try:
            font_prop = FontProperties(family=font)
            plt.rcParams['font.sans-serif'] = [font]
            plt.rcParams['axes.unicode_minus'] = False
            logger.info(f"使用中文字体：{font}")
            return font_prop
        except Exception as e:
            logger.debug(f"加载字体 {font} 失败：{e}")
            continue
    
    # 如果都没有，使用默认字体 (英文)
    logger.warning("未找到中文字体，使用默认字体")
    plt.rcParams['font.sans-serif'] = ['Arial']
    plt.rcParams['axes.unicode_minus'] = False
    return None


class TrendVisualizer:
    """趋势可视化器 (增强版 v2.1)"""
    
    def __init__(self, output_dir: Optional[str] = None, cache_enabled: bool = True):
        """
        初始化可视化器
        
        Args:
            output_dir: 输出目录 (默认 data/charts/)
            cache_enabled: 是否启用缓存
        """
        self.output_dir = Path(output_dir) if output_dir else DATA_DIR / "charts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.font_prop = setup_chinese_font()
        
        # 缓存配置
        self.cache_enabled = cache_enabled and CACHE_CONFIG.get("enabled", True)
        self._chart_cache: Dict[str, Dict[str, str]] = {}
        
        # 可视化配置
        self.default_top_n = VISUALIZATION_CONFIG.get("default_top_n", 20)
        self.chart_dpi = VISUALIZATION_CONFIG.get("chart_dpi", 150)
        self.default_figsize = VISUALIZATION_CONFIG.get("default_figsize", (14, 8))
        
        logger.info("可视化器 (增强版) 初始化成功")
        logger.info(f"输出目录：{self.output_dir}")
        logger.info(f"缓存：{'启用' if self.cache_enabled else '禁用'}")
    
    def create_trend_bar_chart(self, products: List[Dict], top_n: int = 20, 
                                filename: Optional[str] = None) -> str:
        """
        创建趋势评分柱状图 (Top N 商品对比)
        
        Args:
            products: 商品列表 (已包含 trend_score)
            top_n: 显示前 N 个商品
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        logger.info(f"创建趋势评分柱状图 (Top {top_n})")
        
        # 准备数据
        df = pd.DataFrame(products[:top_n])
        df = df.sort_values('trend_score', ascending=True)  # 横向柱状图，从低到高
        
        # 创建图表
        fig, ax = plt.subplots(figsize=self.default_figsize)
        
        # 颜色映射 (根据趋势标签)
        colors = []
        for _, row in df.iterrows():
            label = row.get('trend_label', '')
            if '爆品' in label or '🔥' in label:
                colors.append('#FF4444')  # 红色
            elif '快速' in label or '📈' in label:
                colors.append('#FF8C00')  # 橙色
            elif '稳定' in label or '➡️' in label:
                colors.append('#32CD32')  # 绿色
            else:
                colors.append('#808080')  # 灰色
        
        # 绘制柱状图
        y_pos = np.arange(len(df))
        bars = ax.barh(y_pos, df['trend_score'], color=colors, alpha=0.8)
        
        # 添加数值标签
        for i, (idx, row) in enumerate(df.iterrows()):
            ax.text(row['trend_score'] + 1, i, f"{row['trend_score']:.1f}", 
                   va='center', fontsize=9, fontweight='bold')
        
        # 设置标签
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f"{title[:30]}..." if len(title) > 30 else title 
                           for title in df['title']], fontsize=9)
        ax.set_xlabel('趋势评分', fontsize=12, fontweight='bold')
        ax.set_title(f'🏆 Top {top_n} 潜力商品趋势评分对比\n{datetime.now().strftime("%Y-%m-%d %H:%M")}', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # 添加图例说明
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#FF4444', label='🔥 爆品潜力 (≥80)'),
            Patch(facecolor='#FF8C00', label='📈 快速增长 (60-79)'),
            Patch(facecolor='#32CD32', label='➡️ 稳定发展 (40-59)'),
            Patch(facecolor='#808080', label='⚠️ 增长放缓/衰退 (<40)'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=9)
        
        # 网格线
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存
        if filename is None:
            filename = f"trend_bar_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"柱状图已保存：{filepath}")
        return str(filepath)
    
    def create_price_distribution(self, products: List[Dict], 
                                   filename: Optional[str] = None) -> str:
        """
        创建价格分布直方图
        
        Args:
            products: 商品列表
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        logger.info("创建价格分布直方图")
        
        # 提取价格数据
        prices = []
        for p in products:
            price = p.get('price')
            if isinstance(price, dict):
                prices.append(price.get('value', 0))
            elif isinstance(price, (int, float)):
                prices.append(price)
        
        prices = [p for p in prices if p and p > 0]  # 过滤无效数据
        
        if not prices:
            logger.warning("无有效价格数据")
            return ""
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # 直方图
        n_bins = min(20, len(prices) // 3)
        counts, bins, patches = ax.hist(prices, bins=n_bins, color='steelblue', 
                                        alpha=0.7, edgecolor='black', linewidth=0.5)
        
        # 添加统计信息
        mean_price = np.mean(prices)
        median_price = np.median(prices)
        std_price = np.std(prices)
        
        ax.axvline(mean_price, color='red', linestyle='--', linewidth=2, 
                  label=f'平均价：${mean_price:.2f}')
        ax.axvline(median_price, color='green', linestyle='--', linewidth=2, 
                  label=f'中位价：${median_price:.2f}')
        
        # 添加文本框
        stats_text = f'样本数：{len(prices)}\n平均价：${mean_price:.2f}\n中位价：${median_price:.2f}\n标准差：${std_price:.2f}'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.98, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', horizontalalignment='right', bbox=props)
        
        # 设置标签
        ax.set_xlabel('价格 (USD)', fontsize=12, fontweight='bold')
        ax.set_ylabel('商品数量', fontsize=12, fontweight='bold')
        ax.set_title(f'💰 商品价格分布分析\n{datetime.now().strftime("%Y-%m-%d %H:%M")}', 
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        
        if filename is None:
            filename = f"price_distribution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"价格分布图已保存：{filepath}")
        return str(filepath)
    
    def create_rating_sales_scatter(self, products: List[Dict], 
                                     filename: Optional[str] = None) -> str:
        """
        创建评分 - 销量关系散点图
        
        Args:
            products: 商品列表
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        logger.info("创建评分 - 销量关系散点图")
        
        # 提取数据
        ratings = []
        sales = []
        trend_scores = []
        titles = []
        
        for p in products:
            rating = p.get('rating', 0) or 0
            rating_count = p.get('ratings_total', 0) or 0
            trend_score = p.get('trend_score', 0) or 0
            
            if rating > 0 and rating_count > 0:
                ratings.append(rating)
                sales.append(rating_count)
                trend_scores.append(trend_score)
                titles.append(p.get('title', '')[:20])
        
        if not ratings:
            logger.warning("无有效评分数据")
            return ""
        
        # 创建交互式散点图 (Plotly)
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=ratings,
            y=sales,
            mode='markers',
            marker=dict(
                size=[min(20, ts/3) for ts in trend_scores],  # 大小与趋势评分相关
                color=trend_scores,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='趋势评分'),
                line=dict(width=1, color='DarkSlateGrey'),
            ),
            text=[f"<b>{t}</b><br>评分：{r}<br>评论数：{s:,}<br>趋势分：{ts:.1f}" 
                  for t, r, s, ts in zip(titles, ratings, sales, trend_scores)],
            hovertemplate='%{text}<extra></extra>',
            name='商品'
        ))
        
        # 添加趋势线
        z = np.polyfit(ratings, np.log1p(sales), 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(ratings), max(ratings), 100)
        y_line = np.expm1(p(x_line))
        
        fig.add_trace(go.Scatter(
            x=x_line,
            y=y_line,
            mode='lines',
            line=dict(color='red', width=2, dash='dash'),
            name='趋势线',
            showlegend=True
        ))
        
        # 布局
        fig.update_layout(
            title=f'⭐ 评分 - 销量关系图 (颜色=趋势评分)<br><sup>{datetime.now().strftime("%Y-%m-%d %H:%M")}</sup>',
            xaxis_title='商品评分',
            yaxis_title='评论数量 (对数尺度)',
            height=600,
            showlegend=True,
            hovermode='closest'
        )
        
        fig.update_yaxes(type="log")
        
        # 保存
        if filename is None:
            filename = f"rating_sales_scatter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.output_dir / filename
        fig.write_html(filepath)
        logger.info(f"交互式散点图已保存：{filepath}")
        
        # 尝试保存静态 PNG (需要 Chrome/Kaleido)
        try:
            fig.write_image(filepath.with_suffix('.png'), width=1200, height=600)
            logger.info(f"静态 PNG 已保存：{filepath.with_suffix('.png')}")
        except Exception as e:
            logger.warning(f"无法保存 PNG (需要 Chrome): {e}")
        
        return str(filepath)
    
    def create_radar_chart(self, product: Dict, filename: Optional[str] = None) -> str:
        """
        创建单个商品的多维度雷达图
        
        Args:
            product: 单个商品数据 (包含 metrics)
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        logger.info(f"创建雷达图：{product.get('asin', 'Unknown')}")
        
        metrics = product.get('metrics', {})
        if not metrics:
            logger.warning("商品无指标数据")
            return ""
        
        # 指标数据
        categories = ['销量增长', '评论增速', 'BSR 排名']
        values = [
            metrics.get('sales_growth', 0),
            metrics.get('review_growth', 0),
            metrics.get('bsr_improvement', 0),
        ]
        
        # 闭合雷达图
        values += values[:1]
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
        
        # 绘制
        ax.plot(angles, values, 'o-', linewidth=2, color='#1f77b4', markersize=8)
        ax.fill(angles, values, alpha=0.25, color='#1f77b4')
        
        # 设置标签
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids(np.degrees(angles[:-1]), categories, fontsize=11, fontweight='bold')
        ax.set_rgrids([20, 40, 60, 80, 100], fontsize=10)
        ax.set_ylim(0, 100)
        
        # 标题
        title = product.get('title', 'Unknown')[:40]
        ax.set_title(f'📊 商品多维度分析\n{title}\n趋势评分：{product.get("trend_score", 0):.1f}', 
                    fontsize=12, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        if filename is None:
            asin = product.get('asin', 'unknown')
            filename = f"radar_{asin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"雷达图已保存：{filepath}")
        return str(filepath)
    
    def create_correlation_heatmap(self, products: List[Dict], 
                                    filename: Optional[str] = None) -> str:
        """
        创建指标相关性热力图
        
        Args:
            products: 商品列表
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        logger.info("创建相关性热力图")
        
        # 提取指标数据
        data = {
            '趋势评分': [],
            '销量增长': [],
            '评论增速': [],
            'BSR 排名': [],
            '价格': [],
            '评分': [],
            '评论数': [],
        }
        
        for p in products:
            metrics = p.get('metrics', {})
            data['趋势评分'].append(p.get('trend_score', 0) or 0)
            data['销量增长'].append(metrics.get('sales_growth', 0) or 0)
            data['评论增速'].append(metrics.get('review_growth', 0) or 0)
            data['BSR 排名'].append(metrics.get('bsr_improvement', 0) or 0)
            
            price = p.get('price')
            if isinstance(price, dict):
                data['价格'].append(price.get('value', 0) or 0)
            else:
                data['价格'].append(0)
            
            data['评分'].append(p.get('rating', 0) or 0)
            data['评论数'].append(p.get('ratings_total', 0) or 0)
        
        df = pd.DataFrame(data)
        
        # 计算相关系数
        corr_matrix = df.corr()
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # 热力图
        im = ax.imshow(corr_matrix, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)
        
        # 添加数值
        for i in range(len(corr_matrix)):
            for j in range(len(corr_matrix)):
                text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                              ha='center', va='center', color='black', fontsize=10,
                              fontweight='bold')
        
        # 设置标签
        ax.set_xticks(np.arange(len(corr_matrix.columns)))
        ax.set_yticks(np.arange(len(corr_matrix.columns)))
        ax.set_xticklabels(corr_matrix.columns, fontsize=10, rotation=45, ha='right')
        ax.set_yticklabels(corr_matrix.columns, fontsize=10)
        
        # 颜色条
        cbar = ax.figure.colorbar(im)
        cbar.ax.set_ylabel('相关系数', rotation=-90, va='bottom', fontsize=11)
        
        # 标题
        ax.set_title(f'🔗 商品指标相关性分析\n{datetime.now().strftime("%Y-%m-%d %H:%M")}', 
                    fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        if filename is None:
            filename = f"correlation_heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"热力图已保存：{filepath}")
        return str(filepath)
    
    def create_dashboard(self, products: List[Dict], top_n: int = 20,
                         filename: Optional[str] = None) -> str:
        """
        创建综合仪表板 (多图表组合)
        
        Args:
            products: 商品列表
            top_n: 显示前 N 个商品
            filename: 输出文件名
            
        Returns:
            输出文件路径
        """
        logger.info(f"创建综合仪表板 (Top {top_n})")
        
        # 创建交互式仪表板 (Plotly)
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('趋势评分 Top20', '价格分布', '评分 - 销量关系', '指标分布'),
            specs=[[{"type": "bar"}, {"type": "histogram"}],
                   [{"type": "scatter"}, {"type": "box"}]]
        )
        
        df = pd.DataFrame(products[:top_n])
        
        # 1. 趋势评分柱状图
        df_sorted = df.sort_values('trend_score', ascending=True)
        fig.add_trace(
            go.Bar(
                y=df_sorted['title'].apply(lambda x: x[:25] + '...' if len(x) > 25 else x),
                x=df_sorted['trend_score'],
                orientation='h',
                marker_color=df_sorted['trend_score'],
                marker_colorscale='Viridis',
                name='趋势评分'
            ),
            row=1, col=1
        )
        
        # 2. 价格分布
        prices = []
        for p in products:
            price = p.get('price')
            if isinstance(price, dict):
                prices.append(price.get('value', 0))
        fig.add_trace(
            go.Histogram(x=prices, nbinsx=20, name='价格', marker_color='steelblue'),
            row=1, col=2
        )
        
        # 3. 评分 - 销量散点图
        fig.add_trace(
            go.Scatter(
                x=df['rating'],
                y=df['ratings_total'],
                mode='markers',
                marker=dict(
                    size=df['trend_score'] / 3,
                    color=df['trend_score'],
                    colorscale='RdYlGn',
                    showscale=True
                ),
                name='商品',
                text=df['title']
            ),
            row=2, col=1
        )
        
        # 4. 指标箱线图
        metrics_data = []
        for p in products:
            m = p.get('metrics', {})
            metrics_data.extend([
                {'指标': '销量增长', '值': m.get('sales_growth', 0)},
                {'指标': '评论增速', '值': m.get('review_growth', 0)},
                {'指标': 'BSR 排名', '值': m.get('bsr_improvement', 0)},
            ])
        metrics_df = pd.DataFrame(metrics_data)
        
        for idx, metric in enumerate(['销量增长', '评论增速', 'BSR 排名']):
            metric_data = metrics_df[metrics_df['指标'] == metric]['值']
            fig.add_trace(
                go.Box(y=metric_data, name=metric, marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1'][idx]),
                row=2, col=2
            )
        
        # 更新布局
        fig.update_layout(
            height=900,
            showlegend=False,
            title_text=f'📊 亚马逊选品分析仪表板 - {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            title_font_size=16
        )
        
        fig.update_xaxes(title_text="趋势评分", row=1, col=1)
        fig.update_xaxes(title_text="价格 (USD)", row=1, col=2)
        fig.update_xaxes(title_text="评分", row=2, col=1)
        
        # 保存
        if filename is None:
            filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.output_dir / filename
        fig.write_html(filepath)
        logger.info(f"交互式仪表板已保存：{filepath}")
        
        return str(filepath)
    
    def _get_data_hash(self, data: List[Dict], suffix: str = "") -> str:
        """生成数据指纹用于缓存"""
        base_hash = calculate_data_hash(data[:self.default_top_n])
        return f"{base_hash}_{suffix}" if suffix else base_hash
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, str]]:
        """从缓存获取图表"""
        if self.cache_enabled and cache_key in self._chart_cache:
            logger.debug(f"缓存命中：{cache_key}")
            return self._chart_cache[cache_key]
        return None
    
    def _save_to_cache(self, cache_key: str, charts: Dict[str, str]):
        """保存到缓存"""
        if self.cache_enabled:
            self._chart_cache[cache_key] = charts
            logger.debug(f"缓存保存：{cache_key} ({len(charts)} 个图表)")
    
    def generate_all_charts(self, products: List[Dict], top_n: int = 20,
                           force_refresh: bool = False) -> Dict[str, str]:
        """
        生成所有图表 (带缓存)
        
        Args:
            products: 商品列表
            top_n: Top N 商品
            force_refresh: 强制刷新 (忽略缓存)
            
        Returns:
            图表文件路径字典
        """
        # 生成缓存键
        cache_key = self._get_data_hash(products, f"top{top_n}")
        
        # 检查缓存
        if not force_refresh:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.info(f"使用缓存的图表 (key: {cache_key})")
                return cached
        
        logger.info(f"生成全套可视化图表 (Top {top_n}, 缓存：{'跳过' if not force_refresh else '禁用'})")
        
        charts = {}
        
        # 1. 趋势柱状图
        charts['trend_bar'] = self.create_trend_bar_chart(products, top_n)
        
        # 2. 价格分布
        charts['price_dist'] = self.create_price_distribution(products)
        
        # 3. 评分 - 销量散点图
        charts['scatter'] = self.create_rating_sales_scatter(products)
        
        # 4. Top3 商品雷达图
        for i, product in enumerate(products[:3]):
            charts[f'radar_{i+1}'] = self.create_radar_chart(product)
        
        # 5. 相关性热力图
        charts['heatmap'] = self.create_correlation_heatmap(products)
        
        # 6. 综合仪表板
        charts['dashboard'] = self.create_dashboard(products, top_n)
        
        # 保存到缓存
        self._save_to_cache(cache_key, charts)
        
        logger.info(f"✅ 共生成 {len(charts)} 个图表")
        return charts
    
    def clear_cache(self):
        """清空缓存"""
        count = len(self._chart_cache)
        self._chart_cache.clear()
        logger.info(f"缓存已清空 ({count} 个条目)")


# 使用示例
if __name__ == "__main__":
    # 测试数据
    test_products = [
        {
            "asin": "B001",
            "title": "Wireless Earbuds Pro - Premium Sound Quality",
            "price": {"symbol": "$", "value": 29.99},
            "rating": 4.5,
            "ratings_total": 5000,
            "trend_score": 85.5,
            "trend_label": "🔥 爆品潜力",
            "metrics": {
                "sales_growth": 80,
                "review_growth": 85,
                "bsr_improvement": 90,
            }
        },
        {
            "asin": "B002",
            "title": "Phone Case Ultra - Shockproof Protection",
            "price": {"symbol": "$", "value": 15.99},
            "rating": 4.7,
            "ratings_total": 12000,
            "trend_score": 72.3,
            "trend_label": "📈 快速增长",
            "metrics": {
                "sales_growth": 65,
                "review_growth": 75,
                "bsr_improvement": 77,
            }
        },
        # ... 可以添加更多测试数据
    ]
    
    visualizer = TrendVisualizer()
    charts = visualizer.generate_all_charts(test_products, top_n=10)
    
    print("\n✅ 图表生成完成:")
    for name, path in charts.items():
        print(f"   {name}: {path}")
