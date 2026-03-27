# 📡 API 参考文档

**版本:** v2.1.0  
**最后更新:** 2026-03-27  
**状态:** ✅ 已完成  
**基础 URL:** `http://localhost:5000/api`

---

## 📋 API 概览

| 端点 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/health` | GET | 健康检查 | ❌ |
| `/products` | GET | 获取商品列表 | ❌ |
| `/charts` | GET | 获取图表列表 | ❌ |
| `/config` | GET | 获取配置信息 | ❌ |
| `/results` | GET | 获取分析报告 | ❌ |
| `/run` | POST | 运行工作流 | ❌ |
| `/suppliers` | POST | 供应商匹配 | ❌ |

---

## 🔍 健康检查

### `GET /api/health`

检查 API 服务状态。

**请求:**
```bash
curl http://localhost:5000/api/health
```

**响应:**
```json
{
  "status": "ok",
  "version": "v2.1.0",
  "timestamp": "2026-03-27T06:22:00Z"
}
```

**状态码:**
- `200` - 服务正常
- `500` - 服务异常

---

## 📦 商品列表

### `GET /api/products`

获取采集的商品列表 (包含增强指标)。

**请求:**
```bash
curl http://localhost:5000/api/products
```

**查询参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | 20 | 返回数量限制 |
| `offset` | int | 0 | 偏移量 |
| `min_rating` | float | 0 | 最低评分 |
| `min_reviews` | int | 0 | 最低评论数 |
| `trend_label` | string | - | 趋势标签过滤 |

**请求示例:**
```bash
curl "http://localhost:5000/api/products?limit=10&min_rating=4.0"
```

**响应:**
```json
{
  "success": true,
  "count": 10,
  "data_source": "enhanced",
  "products": [
    {
      "asin": "B0BQPNMXQV",
      "title": "JBL Vibe Beam True Wireless Earbuds",
      "price_value": 29.94,
      "rating": 4.3,
      "ratings_total": 36211,
      "trend_score": 51.0,
      "trend_label": "➡️ 稳定发展",
      "metrics": {
        "profit_margin": 65.0,
        "market_saturation": 40.0,
        "growth_sustainability": 58.0,
        "risk_score": 0.0
      },
      "confidence": 1.0,
      "forecast_30d": {
        "score": 53.38,
        "trend": "微升 ↗️",
        "confidence_interval": {
          "low": 48.38,
          "high": 58.38
        }
      },
      "risk_level": "🟢 极低风险",
      "link": "https://www.amazon.com/dp/B0BQPNMXQV"
    }
  ]
}
```

**状态码:**
- `200` - 成功
- `400` - 参数错误
- `500` - 服务器错误

---

## 📊 图表列表

### `GET /api/charts`

获取生成的图表列表。

**请求:**
```bash
curl http://localhost:5000/api/charts
```

**响应:**
```json
{
  "success": true,
  "charts": [
    {
      "type": "trend_bar",
      "name": "趋势评分柱状图",
      "url": "/static/charts/trend_bar_chart.png",
      "created_at": "2026-03-27T06:20:00Z"
    },
    {
      "type": "price_dist",
      "name": "价格分布图",
      "url": "/static/charts/price_distribution.png",
      "created_at": "2026-03-27T06:20:00Z"
    },
    {
      "type": "scatter",
      "name": "评分 - 销量散点图",
      "url": "/static/charts/rating_sales_scatter.html",
      "created_at": "2026-03-27T06:20:00Z"
    }
  ],
  "product_count": 16,
  "last_update": "2026-03-27T06:20:00Z"
}
```

**状态码:**
- `200` - 成功
- `404` - 无图表数据

---

## ⚙️ 配置信息

### `GET /api/config`

获取系统配置信息。

**请求:**
```bash
curl http://localhost:5000/api/config
```

**响应:**
```json
{
  "success": true,
  "config": {
    "analysis_weights": {
      "sales_growth": 0.30,
      "review_growth": 0.20,
      "bsr_improvement": 0.15,
      "profit_margin": 0.15,
      "market_saturation": 0.10,
      "risk_score": 0.05
    },
    "analysis_thresholds": {
      "sales_growth": {
        "excellent": 20.0,
        "good": 10.0,
        "moderate": 5.0,
        "slow": 0.0
      }
    },
    "seasonal_factors": {
      "11": 1.30,
      "12": 1.40
    },
    "version": "v2.1.0"
  }
}
```

**状态码:**
- `200` - 成功

---

## 📄 分析报告

### `GET /api/results`

获取最新分析报告。

**请求:**
```bash
curl http://localhost:5000/api/results
```

**响应:**
```json
{
  "success": true,
  "report": {
    "generated_at": "2026-03-27T06:20:00Z",
    "product_count": 16,
    "top_products": [...],
    "charts": [...],
    "summary": {
      "avg_trend_score": 45.2,
      "avg_rating": 4.3,
      "avg_price": 35.5
    }
  }
}
```

**状态码:**
- `200` - 成功
- `404` - 无报告数据

---

## 🚀 运行工作流

### `POST /api/run`

运行完整的数据采集和分析工作流。

**请求:**
```bash
curl -X POST http://localhost:5000/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "wireless earbuds",
    "limit": 20,
    "use_enhanced": true
  }'
```

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `keywords` | string | ✅ | 搜索关键词 |
| `limit` | int | ❌ | 采集数量 (默认 20) |
| `use_enhanced` | bool | ❌ | 启用增强分析 (默认 true) |

**响应:**
```json
{
  "success": true,
  "message": "工作流运行成功",
  "data": {
    "products_collected": 20,
    "charts_generated": 6,
    "output_file": "data/top20_20260327_062200.csv",
    "enhanced_file": "data/top20_enhanced_20260327_062200.json"
  }
}
```

**状态码:**
- `200` - 成功
- `400` - 参数错误
- `500` - 运行失败

---

## 🏭 供应商匹配

### `POST /api/suppliers`

匹配 1688 供应商。

**请求:**
```bash
curl -X POST http://localhost:5000/api/suppliers \
  -H "Content-Type: application/json" \
  -d '{
    "asin": "B0BQPNMXQV",
    "title": "JBL Vibe Beam Earbuds",
    "price_range": [20, 40]
  }'
```

**请求体:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `asin` | string | ✅ | 亚马逊 ASIN |
| `title` | string | ✅ | 商品标题 |
| `price_range` | array | ❌ | 价格范围 [min, max] |

**响应:**
```json
{
  "success": true,
  "suppliers": [
    {
      "name": "深圳市 XX 电子厂",
      "price": 15.5,
      "moq": 100,
      "rating": 4.8,
      "url": "https://detail.1688.com/offer/xxx.html"
    }
  ]
}
```

**状态码:**
- `200` - 成功
- `400` - 参数错误
- `500` - 匹配失败

---

## 📥 静态文件

### `GET /static/charts/<filename>`

获取生成的图表文件。

**请求:**
```bash
curl http://localhost:5000/static/charts/trend_bar_chart.png -o chart.png
```

**响应:**
- 图片文件 (PNG 或 HTML)

**状态码:**
- `200` - 成功
- `404` - 文件不存在

---

## 🔧 Python SDK 示例

### 安装依赖

```bash
pip install requests
```

### 获取商品列表

```python
import requests

BASE_URL = "http://localhost:5000/api"

def get_products(limit=20, min_rating=4.0):
    """获取商品列表"""
    response = requests.get(
        f"{BASE_URL}/products",
        params={"limit": limit, "min_rating": min_rating}
    )
    data = response.json()
    if data["success"]:
        return data["products"]
    return []

# 使用
products = get_products(limit=10)
for p in products:
    print(f"{p['title']}: ${p['price_value']} ({p['trend_score']}分)")
```

### 运行工作流

```python
def run_workflow(keywords, limit=20):
    """运行采集工作流"""
    response = requests.post(
        f"{BASE_URL}/run",
        json={
            "keywords": keywords,
            "limit": limit,
            "use_enhanced": True
        }
    )
    return response.json()

# 使用
result = run_workflow("wireless earbuds", limit=20)
print(f"采集完成：{result['data']['products_collected']} 个商品")
```

### 获取图表

```python
def get_charts():
    """获取图表列表"""
    response = requests.get(f"{BASE_URL}/charts")
    return response.json()

def download_chart(url):
    """下载图表"""
    response = requests.get(f"{BASE_URL}{url}")
    with open("chart.png", "wb") as f:
        f.write(response.content)

# 使用
charts = get_charts()
for chart in charts["charts"]:
    print(f"{chart['name']}: {chart['url']}")
    if chart['url'].endswith('.png'):
        download_chart(chart['url'])
```

---

## 🌐 cURL 命令集合

### 健康检查
```bash
curl http://localhost:5000/api/health
```

### 获取商品
```bash
curl "http://localhost:5000/api/products?limit=10"
```

### 获取图表
```bash
curl http://localhost:5000/api/charts
```

### 运行工作流
```bash
curl -X POST http://localhost:5000/api/run \
  -H "Content-Type: application/json" \
  -d '{"keywords": "earbuds", "limit": 20}'
```

### 获取配置
```bash
curl http://localhost:5000/api/config | jq
```

---

## ⚠️ 错误处理

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "参数错误：limit 必须为正整数",
    "details": {
      "field": "limit",
      "value": -1
    }
  }
}
```

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|---------|
| `INVALID_PARAMETER` | 参数错误 | 检查参数类型和范围 |
| `DATA_NOT_FOUND` | 数据不存在 | 确认数据文件存在 |
| `API_ERROR` | API 调用失败 | 检查 API 密钥和网络 |
| `INTERNAL_ERROR` | 内部错误 | 查看日志文件 |

---

## 📊 速率限制

| 端点 | 限制 | 说明 |
|------|------|------|
| `/api/health` | 无 | - |
| `/api/products` | 60 次/分钟 | 读操作 |
| `/api/charts` | 60 次/分钟 | 读操作 |
| `/api/run` | 5 次/分钟 | 写操作 (采集) |
| `/api/suppliers` | 10 次/分钟 | 写操作 |

---

## 📚 相关文档

| 文档 | 链接 |
|------|------|
| [快速开始](./quickstart.md) | 快速体验 |
| [配置说明](./configuration.md) | API 配置 |
| [用户指南](../02-User-Guide/) | 功能说明 |
| [部署指南](../04-Technical-Docs/deployment.md) | 生产部署 |

---

**API 参考版本:** v1.0  
**最后更新:** 2026-03-27  
**维护者:** @admina

---

<div align="center">

**📡 API 参考完成!**

[快速开始](./quickstart.md) | [配置说明](./configuration.md) | [用户指南](../02-User-Guide/)

</div>
