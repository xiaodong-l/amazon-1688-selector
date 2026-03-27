# ⚙️ 配置说明

**版本:** v2.1.0  
**最后更新:** 2026-03-27  
**状态:** ✅ 已完成  
**预计时间:** 10-15 分钟

---

## 📋 配置文件概览

| 文件 | 位置 | 用途 | 必需 |
|------|------|------|------|
| `.env` | 根目录 | 环境变量配置 | ✅ |
| `config.py` | `src/utils/` | 系统配置 | ✅ |
| `.project-meta.json` | 根目录 | 项目元数据 | ❌ |

---

## 🔐 环境变量配置 (.env)

### 创建配置文件

```bash
# 复制模板
cp .env.example .env

# 编辑配置
vim .env
```

### 完整配置示例

```bash
# ═══════════════════════════════════════════════════
# 亚马逊选品系统 - 环境配置
# ═══════════════════════════════════════════════════

# ───────────────────────────────────────────────────
# Rainforest API 配置
# ───────────────────────────────────────────────────
RAINFOREST_API_KEY=your_api_key_here
RAINFOREST_API_URL=https://api.rainforestapi.com/request
RAINFOREST_API_TIMEOUT=30

# ───────────────────────────────────────────────────
# 项目路径配置
# ───────────────────────────────────────────────────
PROJECT_ROOT=/home/admina/.openclaw-imperial/workspace-taizi/projects/amazon-1688-selector
DATA_DIR=data
LOGS_DIR=logs
CHARTS_DIR=data/charts

# ───────────────────────────────────────────────────
# Web 服务配置
# ───────────────────────────────────────────────────
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_PORT=5000
FLASK_HOST=0.0.0.0

# ───────────────────────────────────────────────────
# 日志配置
# ───────────────────────────────────────────────────
LOG_LEVEL=INFO
LOG_FORMAT=detailed
LOG_FILE=logs/app.log

# ───────────────────────────────────────────────────
# 分析配置
# ───────────────────────────────────────────────────
ANALYSIS_TOP_N=20
ANALYSIS_MIN_RATING=3.5
ANALYSIS_MIN_REVIEWS=100

# ───────────────────────────────────────────────────
# 缓存配置
# ───────────────────────────────────────────────────
CACHE_ENABLED=true
CACHE_TTL=3600
CACHE_DIR=.cache

# ───────────────────────────────────────────────────
# 数据库配置 (可选)
# ───────────────────────────────────────────────────
# DATABASE_URL=sqlite:///data/products.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/amazon_selector

# ───────────────────────────────────────────────────
# Redis 配置 (可选，用于异步任务)
# ───────────────────────────────────────────────────
# REDIS_URL=redis://localhost:6379/0
# CELERY_BROKER=redis://localhost:6379/0
```

---

## 📊 系统配置 (config.py)

### 位置
`src/utils/config.py`

### 配置类别

#### 1. 分析阈值 (ANALYSIS_THRESHOLDS)

```python
ANALYSIS_THRESHOLDS = {
    'sales_growth': {
        'excellent': 20.0,    # 优秀：>20%
        'good': 10.0,         # 良好：>10%
        'moderate': 5.0,      # 中等：>5%
        'slow': 0.0           # 缓慢：>0%
    },
    'review_growth': {
        'excellent': 15.0,
        'good': 8.0,
        'moderate': 4.0,
        'slow': 0.0
    },
    'bsr_rank': {
        'excellent': 1000,    # 优秀：<1000
        'good': 5000,         # 良好：<5000
        'moderate': 10000,    # 中等：<10000
        'slow': float('inf')  # 缓慢：>10000
    }
}
```

#### 2. 分析权重 (ANALYSIS_WEIGHTS)

```python
ANALYSIS_WEIGHTS = {
    'sales_growth': 0.30,      # 销量增长 30%
    'review_growth': 0.20,     # 评论增速 20%
    'bsr_improvement': 0.15,   # BSR 排名 15%
    'profit_margin': 0.15,     # 利润率 15%
    'market_saturation': 0.10, # 市场饱和度 10%
    'risk_score': 0.05         # 风险评分 5%
}
```

#### 3. 类别利润率 (CATEGORY_MARGINS)

```python
CATEGORY_MARGINS = {
    'Electronics': 0.25,       # 电子产品 25%
    'Home & Kitchen': 0.30,    # 家居厨房 30%
    'Sports & Outdoors': 0.28, # 运动户外 28%
    'Beauty & Personal Care': 0.35,  # 美容护理 35%
    'Toys & Games': 0.32,      # 玩具游戏 32%
    'default': 0.30            # 默认 30%
}
```

#### 4. 季节性因子 (SEASONAL_FACTORS)

```python
SEASONAL_FACTORS = {
    1: 1.10,   # 1 月 (新年促销)
    2: 1.05,   # 2 月
    3: 1.00,   # 3 月
    4: 1.00,   # 4 月
    5: 1.05,   # 5 月
    6: 1.00,   # 6 月
    7: 1.00,   # 7 月
    8: 1.05,   # 8 月 (返校季)
    9: 1.00,   # 9 月
    10: 1.10,  # 10 月
    11: 1.30,  # 11 月 (黑色星期五)
    12: 1.40   # 12 月 (圣诞季)
}
```

#### 5. 缓存配置 (CACHE_CONFIG)

```python
CACHE_CONFIG = {
    'enabled': True,
    'ttl': 3600,          # 缓存有效期 (秒)
    'max_size': 1000,     # 最大缓存条目
    'cache_dir': '.cache'
}
```

#### 6. 可视化配置 (VISUALIZATION_CONFIG)

```python
VISUALIZATION_CONFIG = {
    'width': 1200,
    'height': 600,
    'dpi': 150,
    'format': 'png',      # png 或 html
    'theme': 'purple',    # purple 或 blue
    'font_size': 12,
    'chinese_font': 'SimHei'  # 中文字体
}
```

---

## 🔧 配置修改方法

### 方法 1: 修改 .env 文件

```bash
# 编辑 .env 文件
vim .env

# 修改后重启服务
# Web 服务会自动重新加载 (开发模式)
```

### 方法 2: 修改 config.py

```bash
# 编辑配置文件
vim src/utils/config.py

# 修改后重新导入
python -c "from utils import config; print(config.ANALYSIS_WEIGHTS)"
```

### 方法 3: 命令行覆盖

```bash
# 通过环境变量覆盖
export ANALYSIS_TOP_N=50
python -m src.workflow --keywords "earbuds"
```

---

## 📝 配置验证

### 验证脚本

```bash
# 创建验证脚本
cat > scripts/verify-config.sh << 'EOF'
#!/bin/bash
echo "🔍 验证配置..."

# 检查 .env 文件
if [ -f ".env" ]; then
    echo "✅ .env 文件存在"
    
    # 检查 API 密钥
    if grep -q "RAINFOREST_API_KEY=your_api_key_here" .env; then
        echo "⚠️  请替换 API 密钥"
    else
        echo "✅ API 密钥已配置"
    fi
else
    echo "❌ .env 文件不存在"
    exit 1
fi

# 检查 config.py
if [ -f "src/utils/config.py" ]; then
    echo "✅ config.py 存在"
else
    echo "❌ config.py 不存在"
    exit 1
fi

echo "✅ 配置验证通过"
EOF

chmod +x scripts/verify-config.sh
./scripts/verify-config.sh
```

### Python 验证

```python
# 验证配置加载
python -c "
from utils.config import (
    ANALYSIS_THRESHOLDS,
    ANALYSIS_WEIGHTS,
    SEASONAL_FACTORS
)

print('✅ 配置加载成功')
print(f'   分析权重：{ANALYSIS_WEIGHTS}')
print(f'   季节性因子：{SEASONAL_FACTORS[11]}x (11 月)')
"
```

---

## 🎯 常用配置场景

### 场景 1: 调整分析阈值

**需求:** 只分析高评分商品

```python
# 修改 src/utils/config.py
ANALYSIS_THRESHOLDS = {
    ...
    'min_rating': 4.0,  # 从 3.5 提高到 4.0
    'min_reviews': 500, # 从 100 提高到 500
}
```

### 场景 2: 调整权重

**需求:** 更看重利润率

```python
# 修改 ANALYSIS_WEIGHTS
ANALYSIS_WEIGHTS = {
    'sales_growth': 0.25,      # 降低 5%
    'review_growth': 0.15,     # 降低 5%
    'bsr_improvement': 0.15,
    'profit_margin': 0.25,     # 提高 10%
    'market_saturation': 0.10,
    'risk_score': 0.10         # 提高 5%
}
```

### 场景 3: 修改缓存策略

**需求:** 延长缓存时间

```bash
# 修改 .env
CACHE_TTL=7200  # 从 3600 改为 7200 (2 小时)
```

### 场景 4: 更改 Web 端口

**需求:** 使用 8080 端口

```bash
# 修改 .env
FLASK_PORT=8080
```

---

## ⚠️ 配置注意事项

### 1. API 密钥安全

**❌ 错误:**
```bash
# 不要提交 .env 到 Git
git add .env  # 禁止！
```

**✅ 正确:**
```bash
# .env 已在 .gitignore 中
cat .gitignore | grep .env  # 应显示 .env
```

### 2. 配置文件备份

```bash
# 修改前备份
cp .env .env.backup.$(date +%Y%m%d)
cp src/utils/config.py src/utils/config.py.backup.$(date +%Y%m%d)
```

### 3. 配置验证

```bash
# 每次修改后验证
python -c "from utils import config; print('✅ 配置正常')"
```

---

## 🐛 配置问题排查

### 问题 1: 配置未生效

**症状:** 修改配置后无变化

**解决:**
```bash
# 1. 检查文件是否保存
cat .env | grep KEY

# 2. 重启服务
pkill -f "python.*app.py"
python web/app.py

# 3. 清除缓存
rm -rf .cache/
```

### 问题 2: API 密钥错误

**症状:** `ValueError: API key not configured`

**解决:**
```bash
# 检查 .env 文件
cat .env | grep RAINFOREST_API_KEY

# 确保没有多余空格
# 正确：RAINFOREST_API_KEY=abc123
# 错误：RAINFOREST_API_KEY = abc123
```

### 问题 3: 端口被占用

**症状:** `Address already in use`

**解决:**
```bash
# 查找占用端口的进程
lsof -i :5000

# 杀死进程
kill -9 <PID>

# 或更改端口
FLASK_PORT=8080
```

---

## 📚 相关文档

| 文档 | 链接 |
|------|------|
| [安装指南](./installation.md) | 环境配置 |
| [快速开始](./quickstart.md) | 快速体验 |
| [API 参考](../02-User-Guide/api-reference.md) | API 配置 |
| [部署指南](../04-Technical-Docs/deployment.md) | 生产配置 |

---

**配置说明版本:** v1.0  
**最后更新:** 2026-03-27  
**维护者:** @admina

---

<div align="center">

**⚙️ 配置完成!**

[快速开始](./quickstart.md) | [API 参考](../02-User-Guide/api-reference.md) | [用户指南](../02-User-Guide/)

</div>
