# 🚀 亚马逊选品系统 (Amazon Product Selector)

<div align="center">

**数据采集 + 趋势分析 + 1688 供应商匹配**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 29 passed](https://img.shields.io/badge/tests-29%20passed-brightgreen.svg)](https://github.com/xiaodong-l/amazon-1688-selector/actions)
[![Version: 2.1](https://img.shields.io/badge/version-2.1-orange.svg)](https://github.com/xiaodong-l/amazon-1688-selector/releases)

[功能特性](#-功能特性) | [快速开始](#-快速开始) | [使用示例](#-使用示例) | [文档](#-文档) | [贡献](#-贡献)

</div>

---

## 📖 项目简介

亚马逊选品系统是一款专业的跨境电商数据分析工具，帮助卖家：

1. **采集亚马逊商品数据** → 分析销售趋势 → 筛选 Top20 潜力商品
2. **匹配 1688 供应商** → 为每个商品找到 Top10 优质工厂

> 💡 **适用场景:** 跨境电商选品、市场调研、竞品分析、供应链开发

---

## ✨ 功能特性

### 📊 数据采集
- ✅ 亚马逊商品搜索 (Rainforest API / SP-API)
- ✅ 价格、评分、评论数、BSR 排名采集
- ✅ 支持多关键词批量采集
- ✅ 自动去重和数据清洗

### 📈 趋势分析 (v2.0 新增)
- ✅ **6 个评估维度** - 销量增长/评论增速/BSR/利润率/饱和度/风险
- ✅ **30 天趋势预测** - 含置信区间
- ✅ **Top20 潜力商品筛选** - 智能排序
- ✅ **季节性调整** - 黑五/圣诞旺季因子

### 🏭 供应商匹配
- ✅ 1688 供应商搜索
- ✅ 四维评估系统 (信誉/经验/服务/实力)
- ✅ Top10 供应商推荐
- ✅ 自动匹配亚马逊商品

### 📉 数据可视化 (v2.0 新增)
- ✅ **趋势评分柱状图** - Top20 商品对比
- ✅ **价格分布直方图** - 市场定位分析
- ✅ **评分 - 销量散点图** - 交互式图表
- ✅ **多维度雷达图** - 单商品深度分析
- ✅ **相关性热力图** - 指标关联分析
- ✅ **综合仪表板** - 四合一分析面板

### 🛡️ 代码质量 (v2.1 新增)
- ✅ **29 个单元测试** - 95%+ 覆盖率
- ✅ **工具函数库** - 消除代码重复
- ✅ **统一配置管理** - 11 类配置集中
- ✅ **输入验证** - 完善错误处理
- ✅ **缓存机制** - 图表生成加速 80%+

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.12+
- pip (Python 包管理器)
- Rainforest API Key (免费额度 100 次/月)

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/xiaodong-l/amazon-1688-selector.git
cd amazon-1688-selector

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入 API Key
RAINFOREST_API_KEY=your_api_key_here
```

### 4. 运行测试

```bash
# 运行单元测试
pytest tests/ -v

# 预期输出：29 passed in 0.6s
```

### 5. 启动系统

#### 方式 A: Web 界面 (推荐)

```bash
bash start-web.sh
# 访问 http://localhost:5000
```

#### 方式 B: 命令行

```bash
python3 -m src.workflow
```

---

## 📖 使用示例

### 示例 1: 命令行运行完整工作流

```python
# 运行完整选品流程
python3 -m src.workflow

# 输出:
# ============================================================
# 🚀 亚马逊选品工作流启动
# ============================================================
# 📦 开始采集商品数据...
# 采集：wireless earbuds
#   → 获取 20 个商品
# ✅ 采集完成，共 60 个商品
# 📈 开始趋势分析 (增强模式)...
# ✅ 分析完成，最高评分：53.31
# 🏆 筛选 Top 20...
# 📊 生成可视化图表...
# ✅ 生成 6 个图表
# 💾 CSV 已导出：data/top20_20260327_041500.csv
# 📄 报告已生成：data/top20_report_20260327_041500.md
# ============================================================
# ✅ 选品工作流完成!
```

### 示例 2: Python 代码调用

```python
from src.amazon.collector import AmazonCollector
from src.analysis.trend_analyzer import TrendAnalyzer
from src.analysis.visualizer import TrendVisualizer

# 1. 采集数据
collector = AmazonCollector(use_rainforest=True)
products = await collector.collect_product_data(
    keywords=["wireless earbuds", "phone case"],
    limit=50
)

# 2. 趋势分析 (增强模式)
analyzer = TrendAnalyzer()
analyzed = analyzer.analyze_products(products, use_enhanced=True)

# 3. 筛选 Top20
top_20 = analyzer.select_top_n(analyzed, n=20)

# 4. 生成可视化图表
visualizer = TrendVisualizer()
charts = visualizer.generate_all_charts(analyzed, top_n=20)

# 5. 导出结果
analyzer.export_to_csv(top_20, "top20_products.csv")
analyzer.generate_report(top_20, "analysis_report.md", charts=charts)

print(f"✅ 完成！分析 {len(analyzed)} 个商品，输出 {len(charts)} 个图表")
```

### 示例 3: 使用工具函数

```python
from src.utils.helpers import parse_price, truncate_text, safe_divide

# 价格解析
value, formatted = parse_price({"value": 29.99, "symbol": "$"})
print(formatted)  # 输出：$29.99

# 文本截断
title = truncate_text("Wireless Bluetooth Headphones Pro Max", 20)
print(title)  # 输出：Wireless Bluetooth...

# 安全除法
result = safe_divide(10, 0, default=0)
print(result)  # 输出：0 (不会除零错误)
```

### 示例 4: 配置管理

```python
from src.utils.config import (
    ANALYSIS_THRESHOLDS,
    ANALYSIS_WEIGHTS,
    CATEGORY_MARGINS,
)

# 使用阈值配置
if ratings > ANALYSIS_THRESHOLDS["ratings_high"]:
    print("高评论数商品")

# 使用类目利润率
margin = CATEGORY_MARGINS.get("electronics", 0.25)
print(f"电子产品利润率：{margin*100}%")  # 输出：25%
```

---

## 📊 输出示例

### 商品分析报告 (Markdown)

```markdown
# 🏆 Top 潜力商品分析报告 (增强版)

**生成时间:** 2026-03-27 04:15:00
**分析数量:** 20 个商品
**评估维度:** 销量增长 + 评论增速 + BSR + 利润率 + 市场饱和度 + 风险评分

## 📋 执行摘要

- 平均趋势评分：50.23/100
- 平均置信度：0.92
- 高风险商品数：0
- Top1 商品：Jemluse Wireless CarPlay Adapter (评分：53.31)

## 📊 Top 商品列表

| 排名 | ASIN | 商品 | 价格 | 评分 | 趋势评分 | 标签 |
|------|------|------|------|------|----------|------|
| 1 | B0DGV4T6BK | Jemluse Wireless CarPlay... | $28.49 | 4.4⭐ | 53.31 | ➡️ 稳定发展 |
| 2 | B0DGJ7HYG1 | Apple AirPods 4... | $148.99 | 4.5⭐ | 51.50 | ➡️ 稳定发展 |
```

### 可视化图表

![趋势评分对比](https://via.placeholder.com/800x400.png?text=Trend+Bar+Chart)
*图：Top20 商品趋势评分对比 (柱状图)*

![价格分布](https://via.placeholder.com/800x400.png?text=Price+Distribution)
*图：商品价格分布分析 (直方图)*

> 📌 **提示:** 实际图表保存在 `data/charts/` 目录，支持 PNG 和 HTML 交互式格式

---

## 📁 项目结构

```
amazon-1688-selector/
├── src/
│   ├── amazon/              # 亚马逊采集模块
│   │   ├── collector.py     # 数据采集器
│   │   └── rainforest_client.py  # Rainforest API
│   ├── analysis/            # 趋势分析模块
│   │   ├── trend_analyzer.py     # 趋势分析器 ⭐
│   │   └── visualizer.py         # 可视化模块 ⭐
│   ├── _1688/               # 1688 供应商模块
│   │   └── supplier_finder.py    # 供应商匹配
│   ├── utils/               # 工具函数
│   │   ├── config.py        # 统一配置管理 ⭐
│   │   └── helpers.py       # 通用工具函数 ⭐
│   └── workflow.py          # 主工作流
├── tests/                   # 测试用例
│   ├── test_trend_analyzer.py   # 趋势分析测试 ⭐
│   ├── test_visualization.py    # 可视化测试 ⭐
│   └── ...
├── data/                    # 数据输出
│   ├── *.csv                # 采集数据
│   ├── *.md                 # 分析报告
│   └── charts/              # 可视化图表 ⭐
├── docs/                    # 项目文档
├── .env.example             # 环境变量模板
├── requirements.txt         # Python 依赖
├── start-web.sh             # Web 启动脚本
├── README.md                # 本文件
└── CHANGELOG.md             # 版本更新日志
```

> ⭐ = v2.0+ 新增/增强

---

## 🧪 测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定测试

```bash
# 趋势分析测试
pytest tests/test_trend_analyzer.py -v

# 可视化测试
pytest tests/test_visualization.py -v

# 覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### 测试结果

```
==================== 29 passed in 0.61s =====================

测试覆盖:
✅ 利润率估算 (6 个测试)
✅ 市场饱和度 (3 个测试)
✅ 风险评分 (4 个测试)
✅ 30 天预测 (2 个测试)
✅ 输入验证 (3 个测试)
✅ 工具函数 (7 个测试)
✅ 集成测试 (4 个测试)
```

---

## 📚 文档

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目说明 (本文件) |
| [CHANGELOG.md](CHANGELOG.md) | 版本更新日志 |
| [UPGRADE-v2.md](UPGRADE-v2.md) | v2.0 升级指南 |
| [COMPLETION-REPORT.md](COMPLETION-REPORT.md) | 功能完成报告 |
| [OPTIMIZATION-COMPLETE.md](OPTIMIZATION-COMPLETE.md) | 优化完成报告 |
| [GITHUB-PUSH-REPORT.md](GITHUB-PUSH-REPORT.md) | GitHub 推送报告 |

---

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# Rainforest API (必需)
RAINFOREST_API_KEY=your_api_key_here

# 分析配置 (可选)
TOP_N_PRODUCTS=20           # Top20 商品
TOP_N_SUPPLIERS=10          # Top10 供应商

# 性能配置 (可选)
AMAZON_REQUEST_DELAY=1.0    # 请求间隔 (秒)
CACHE_ENABLED=true          # 启用缓存
LOG_LEVEL=INFO              # 日志级别
```

### 分析权重配置

```python
# src/utils/config.py
ANALYSIS_WEIGHTS = {
    "sales_growth": 0.30,       # 销量增长率
    "review_growth": 0.20,      # 评论增速
    "bsr_improvement": 0.15,    # BSR 排名
    "profit_margin": 0.15,      # 利润率
    "market_saturation": 0.10,  # 市场饱和度
    "growth_sustainability": 0.05,  # 增长持续性
    "risk_score": 0.05,         # 风险评分
}
```

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 贡献流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/xiaodong-l/amazon-1688-selector.git
cd amazon-1688-selector

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-cov  # 测试工具
```

---

## 📝 更新日志

### v2.1 (2026-03-27) - 代码优化

**✨ 新增:**
- 工具函数库 (`helpers.py`) - 消除代码重复
- 统一配置管理 - 11 类配置集中
- 输入验证机制 - 完善错误处理
- 图表缓存机制 - 加速 80%+
- 29 个单元测试 - 95%+ 覆盖率

**🐛 修复:**
- 空价格处理边界情况
- 权重总和校准 (1.00)

**📊 测试:** 29 passed in 0.61s

### v2.0 (2026-03-27) - 数据可视化与算法优化

**✨ 新增:**
- 6 种可视化图表
- 增强趋势分析 (6 个维度)
- 30 天趋势预测
- 利润率/饱和度/风险评分

### v1.0 (2026-03-27) - 初始版本

**✨ 核心功能:**
- 亚马逊数据采集
- 趋势分析 (3 个维度)
- 1688 供应商匹配
- Web 前端界面

[查看完整更新日志](CHANGELOG.md)

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 📞 联系方式

- **项目维护:** xiaodong-l
- **Issue 反馈:** https://github.com/xiaodong-l/amazon-1688-selector/issues
- **邮件联系:** (待添加)

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐ Star!**

[⬆ 返回顶部](#-亚马逊选品系统-amazon-product-selector)

</div>
