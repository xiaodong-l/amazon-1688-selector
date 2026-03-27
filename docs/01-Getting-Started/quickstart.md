# 🚀 快速开始指南

**版本:** v2.1.0  
**最后更新:** 2026-03-27  
**状态:** ✅ 已完成  
**预计时间:** 5-10 分钟

---

## 🎯 本指南适合

- ✅ 已完成 [安装](./installation.md) 的新用户
- ✅ 想快速了解系统功能
- ✅ 希望 5 分钟内看到运行效果

**⚠️ 注意:** 如未完成安装，请先查看 [安装指南](./installation.md)

---

## 📋 前置条件

- [x] Python 3.10+ 已安装
- [x] 项目已克隆
- [x] 虚拟环境已激活
- [x] 依赖已安装 (`pip install -r requirements.txt`)
- [x] `.env` 文件已配置 (含 API 密钥)

---

## ⚡ 5 分钟快速体验

### 步骤 1: 验证环境 (1 分钟)

```bash
# 进入项目目录
cd amazon-1688-selector

# 激活虚拟环境
source venv/bin/activate

# 验证 Python 和依赖
python --version  # 应显示 3.10+
python -c "import pandas, flask; print('✅ 依赖正常')"
```

**预期输出:**
```
Python 3.12.3
✅ 依赖正常
```

---

### 步骤 2: 运行数据采集 (2 分钟)

```bash
# 进入 src 目录
cd src

# 运行快速采集测试 (使用示例数据)
python -c "
from amazon.collector import AmazonCollector
import asyncio

async def test():
    collector = AmazonCollector()
    # 使用示例 ASIN 测试
    result = await collector.get_product_details('B0BQPNMXQV')
    print(f'✅ 采集成功：{result[\"title\"][:50]}...')

asyncio.run(test())
"
```

**预期输出:**
```
✅ 采集成功：JBL Vibe Beam True Wireless Earbuds - ...
```

---

### 步骤 3: 运行趋势分析 (2 分钟)

```bash
# 运行趋势分析
python -c "
from analysis.trend_analyzer import TrendAnalyzer
import pandas as pd

# 读取示例数据
df = pd.read_csv('../data/top20_*.csv')[0:5]
products = df.to_dict('records')

# 运行分析
analyzer = TrendAnalyzer()
results = analyzer.analyze_products(products)

print(f'✅ 分析完成：{len(results)} 个商品')
print(f'   Top 商品：{results[0][\"title\"][:40]}...')
print(f'   趋势评分：{results[0][\"trend_score\"]}')
"
```

**预期输出:**
```
✅ 分析完成：5 个商品
   Top 商品：JBL Vibe Beam True Wireless Earbuds...
   趋势评分：51.0
```

---

### 步骤 4: 启动 Web 界面 (1 分钟)

```bash
# 启动 Web 服务
cd ../web
python app.py
```

**预期输出:**
```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
 * Running on http://0.0.0.0:5000
```

**访问:** http://localhost:5000

---

## 🎨 Web 界面导览

### 首页功能

访问 http://localhost:5000

| 区域 | 功能 |
|------|------|
| 📊 统计卡片 | 商品数、Top 数、平均分 |
| 🔍 搜索框 | 搜索商品标题/ASIN |
| 📦 商品卡片 | 商品信息、趋势评分 |
| 📈 增强指标 | 利润率、饱和度等 |
| 🔮 30 天预测 | 趋势预测、置信区间 |

### 可视化页面

访问 http://localhost:5000/charts

| 图表 | 说明 |
|------|------|
| 📊 趋势评分柱状图 | Top20 商品对比 |
| 💰 价格分布图 | 价格区间统计 |
| ⭐ 评分 - 销量散点图 | 关系分析 |
| 🎯 雷达图 | 多维度对比 |
| 🔗 相关性热力图 | 指标关联 |
| 📱 综合仪表板 | 一站式总览 |

---

## 🧪 运行完整工作流

### 完整采集 + 分析

```bash
# 从项目根目录运行
cd /home/admina/.openclaw-imperial/workspace-taizi/projects/amazon-1688-selector

# 运行完整工作流
python -m src.workflow --keywords "wireless earbuds" --limit 20
```

**输出:**
```
🔍 开始采集：wireless earbuds
📊 采集完成：20 个商品
📈 开始分析...
✅ 分析完成
📊 生成图表：6 个
💾 保存数据：data/top20_*.csv
💾 保存增强数据：data/top20_enhanced_*.json
```

---

## 📊 查看结果

### 1. 查看采集数据

```bash
# 查看最新采集文件
ls -lt data/top20_*.csv | head -1

# 查看内容 (前 5 行)
head -5 data/top20_*.csv
```

### 2. 查看增强指标

```bash
# 查看增强数据
python -c "
import json
with open('data/top20_enhanced_*.json') as f:
    data = json.load(f)
    print(f'商品数：{len(data[\"products\"])}')
    print(f'平均趋势评分：{sum(p[\"trend_score\"] for p in data[\"products\"])/len(data[\"products\"]):.1f}')
"
```

### 3. 查看生成的图表

```bash
# 列出图表文件
ls -lh data/charts/
```

**输出:**
```
-rw-r--r--  admina  admina  150K  Mar 27 06:20  trend_bar_chart.png
-rw-r--r--  admina  admina   80K  Mar 27 06:20  price_distribution.png
-rw-r--r--  admina  admina  200K  Mar 27 06:20  rating_sales_scatter.html
...
```

---

## 🔧 常用命令速查

### 数据采集
```bash
# 快速采集 (单个关键词)
python -m src.workflow --keywords "wireless earbuds"

# 批量采集 (多个关键词)
python -m src.workflow --keywords "earbuds,headphones,speaker" --limit 50

# 指定输出文件
python -m src.workflow --keywords "earbuds" --output data/my_products.csv
```

### 趋势分析
```bash
# 分析现有数据
python -c "
from analysis.trend_analyzer import TrendAnalyzer
import pandas as pd
df = pd.read_csv('data/top20_*.csv')
analyzer = TrendAnalyzer()
results = analyzer.analyze_products(df.to_dict('records'))
"
```

### Web 服务
```bash
# 启动开发服务器
python web/app.py

# 指定端口
python web/app.py --port 8080

# 生产环境 (需要 gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 web.app:app
```

### 测试
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_trend_analyzer.py -v

# 生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 📚 下一步学习

完成快速开始后，建议继续:

1. **[配置说明](./configuration.md)** - 详细配置选项
2. **[用户指南](../02-User-Guide/)** - 功能详细说明
3. **[API 参考](../02-User-Guide/api-reference.md)** - API 接口文档
4. **[最佳实践](../02-User-Guide/best-practices.md)** - 使用技巧

---

## ❓ 常见问题

### Q1: 找不到 Python 命令
```bash
# 检查虚拟环境是否激活
which python

# 未激活则执行
source venv/bin/activate
```

### Q2: API 密钥错误
```bash
# 检查 .env 文件
cat .env | grep RAINFOREST_API_KEY

# 确保密钥有效 (从 https://www.rainforestapi.com/ 获取)
```

### Q3: Web 服务无法访问
```bash
# 检查端口是否被占用
lsof -i :5000

# 更换端口
python web/app.py --port 8080
```

### Q4: 图表无法生成
```bash
# 安装 Kaleido 依赖
pip install kaleido plotly

# 安装 Chrome/Chromium (PNG 导出需要)
sudo apt install chromium-browser -y
```

---

## 💡 提示

1. **首次运行** - 建议使用示例数据测试，确认系统正常
2. **API 配额** - 注意 Rainforest API 的调用限制
3. **数据保存** - 采集结果自动保存到 `data/` 目录
4. **图表缓存** - 生成的图表会缓存，避免重复生成
5. **日志查看** - 运行日志在 `logs/` 目录

---

## 🎉 恭喜完成！

你现在已经:
- ✅ 验证了环境配置
- ✅ 运行了数据采集
- ✅ 运行了趋势分析
- ✅ 启动了 Web 界面
- ✅ 查看了分析结果

**开始使用亚马逊选品系统吧！** 🚀

---

**快速开始指南版本:** v1.0  
**最后更新:** 2026-03-27  
**维护者:** @admina

---

<div align="center">

**🎉 快速开始完成!**

[安装指南](./installation.md) | [配置说明](./configuration.md) | [用户指南](../02-User-Guide/)

</div>
