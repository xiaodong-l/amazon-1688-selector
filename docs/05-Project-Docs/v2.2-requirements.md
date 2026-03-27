# 📊 v2.2 版本需求设计文档

**版本:** v2.2.0  
**制定时间:** 2026-03-27  
**预计发布:** 2026-05-31  
**优先级:** 🔴 高  
**工作量:** ~40 小时  
**状态:** 📋 需求设计中

---

## 🎯 版本概述

### 版本名称
**数据持久化与历史追踪 (Data Persistence & Historical Tracking)**

### 版本目标
建立完整的数据存储和历史追踪能力，解决 v2.1 中"历史数据缺失，无法趋势对比"的核心问题。

### 核心价值
1. **数据持久化** - 从 CSV 文件升级为数据库存储
2. **历史追踪** - 记录商品数据变化历史
3. **趋势对比** - 支持周/月/季度数据对比分析
4. **查询优化** - 支持复杂查询和数据导出

---

## 📋 功能需求

### FR-001: 数据库集成

| 属性 | 说明 |
|------|------|
| **优先级** | P0 (必需) |
| **工作量** | 12 小时 |
| **依赖** | 无 |

#### 需求描述
将数据存储从 CSV 文件升级为关系型数据库，支持高效查询和数据管理。

#### 功能点

**FR-001-1: 数据库选型**
- [ ] 支持 SQLite (默认，零配置)
- [ ] 支持 PostgreSQL (生产环境)
- [ ] 通过配置切换数据库类型
- [ ] 数据库连接池管理

**FR-001-2: ORM 集成**
- [ ] 使用 SQLAlchemy 作为 ORM
- [ ] 定义数据模型类
- [ ] 支持异步操作 (asyncpg)
- [ ] 数据库迁移工具 (Alembic)

**FR-001-3: 配置管理**
- [ ] 数据库连接配置 (.env)
- [ ] 连接池参数配置
- [ ] 超时和重试配置

#### 验收标准
- [ ] SQLite 和 PostgreSQL 均可正常连接
- [ ] 数据库连接池工作正常
- [ ] 配置切换无需修改代码

---

### FR-002: 商品数据表设计

| 属性 | 说明 |
|------|------|
| **优先级** | P0 (必需) |
| **工作量** | 6 小时 |
| **依赖** | FR-001 |

#### 需求描述
设计商品数据存储结构，支持商品基本信息和实时数据。

#### 数据模型

**products 表 (商品主表)**
```sql
CREATE TABLE products (
    -- 主键
    id SERIAL PRIMARY KEY,
    
    -- 商品标识
    asin VARCHAR(20) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    
    -- 价格信息
    price_value DECIMAL(10,2),
    price_currency VARCHAR(3) DEFAULT 'USD',
    price_original DECIMAL(10,2),  -- 原价
    price_discount_percent INTEGER, -- 折扣百分比
    
    -- 评分信息
    rating DECIMAL(3,2),
    ratings_total INTEGER,
    ratings_breakdown JSONB,  -- 评分分布 {5: 100, 4: 50, ...}
    
    -- 排名信息
    bsr_rank INTEGER,
    bsr_category VARCHAR(100),
    
    -- 商品状态
    is_prime BOOLEAN DEFAULT FALSE,
    is_best_seller BOOLEAN DEFAULT FALSE,
    is_amazon_choice BOOLEAN DEFAULT FALSE,
    availability VARCHAR(50),  -- 'In Stock', 'Out of Stock'
    
    -- 分类信息
    category VARCHAR(100),
    keywords JSONB,  -- 关联关键词
    
    -- 时间戳
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_asin (asin),
    INDEX idx_category (category),
    INDEX idx_rating (rating),
    INDEX idx_bsr (bsr_rank),
    INDEX idx_updated (last_updated_at)
);
```

**product_images 表 (商品图片)**
```sql
CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    image_type VARCHAR(20),  -- 'main', 'thumbnail', 'gallery'
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**product_features 表 (商品特性)**
```sql
CREATE TABLE product_features (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    feature_text TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 验收标准
- [ ] 商品数据可正确插入和查询
- [ ] 唯一约束防止重复 ASIN
- [ ] 外键约束保证数据完整性
- [ ] 索引优化查询性能

---

### FR-003: 历史记录表设计

| 属性 | 说明 |
|------|------|
| **优先级** | P0 (必需) |
| **工作量** | 8 小时 |
| **依赖** | FR-002 |

#### 需求描述
记录商品数据的历史变化，支持趋势分析和对比。

#### 数据模型

**product_history 表 (商品历史)**
```sql
CREATE TABLE product_history (
    -- 主键
    id SERIAL PRIMARY KEY,
    
    -- 外键
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    asin VARCHAR(20) NOT NULL,
    
    -- 快照数据
    price_value DECIMAL(10,2),
    rating DECIMAL(3,2),
    ratings_total INTEGER,
    bsr_rank INTEGER,
    
    -- 分析数据
    trend_score DECIMAL(5,2),
    trend_label VARCHAR(20),
    profit_margin DECIMAL(5,2),
    market_saturation DECIMAL(5,2),
    
    -- 时间信息
    collected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_asin_time (asin, collected_at),
    INDEX idx_product_time (product_id, collected_at),
    INDEX idx_collected_at (collected_at)
);

-- 分区表 (按月分区，优化大数据量查询)
-- product_history_2026_03
-- product_history_2026_04
-- ...
```

**price_history 表 (价格历史)**
```sql
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    asin VARCHAR(20) NOT NULL,
    
    price_value DECIMAL(10,2) NOT NULL,
    price_type VARCHAR(20),  -- 'current', 'original', 'deal'
    
    collected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_asin_time (asin, collected_at),
    INDEX idx_product_time (product_id, collected_at)
);
```

**bsr_history 表 (BSR 排名历史)**
```sql
CREATE TABLE bsr_history (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    asin VARCHAR(20) NOT NULL,
    
    bsr_rank INTEGER NOT NULL,
    bsr_category VARCHAR(100),
    
    collected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_asin_time (asin, collected_at),
    INDEX idx_rank (bsr_rank)
);
```

#### 验收标准
- [ ] 每次采集自动记录历史数据
- [ ] 历史数据可按时段查询
- [ ] 支持 30 天以上历史数据
- [ ] 分区表正常工作 (PostgreSQL)

---

### FR-004: 定时采集任务

| 属性 | 说明 |
|------|------|
| **优先级** | P1 (重要) |
| **工作量** | 6 小时 |
| **依赖** | FR-002, FR-003 |

#### 需求描述
实现定时采集任务，自动更新商品数据。

#### 功能点

**FR-004-1: Cron 调度**
- [ ] 支持 Cron 表达式配置
- [ ] 默认每天采集一次
- [ ] 支持自定义采集频率
- [ ] 采集任务队列管理

**FR-004-2: 增量采集**
- [ ] 仅采集已存在的商品 (更新历史)
- [ ] 智能识别新商品
- [ ] 采集失败重试机制

**FR-004-3: 任务监控**
- [ ] 采集任务状态追踪
- [ ] 采集日志记录
- [ ] 失败告警通知

#### 配置示例
```yaml
# config/scheduler.yaml
schedules:
  - name: "daily_product_update"
    cron: "0 2 * * *"  # 每天凌晨 2 点
    action: "update_existing"
    limit: 100
    
  - name: "hourly_trending"
    cron: "0 * * * *"  # 每小时
    action: "collect_trending"
    keywords: ["wireless earbuds"]
    limit: 20
```

#### 验收标准
- [ ] 定时任务按配置执行
- [ ] 采集数据正确保存到数据库
- [ ] 失败任务有重试机制
- [ ] 任务日志可查询

---

### FR-005: 数据对比功能

| 属性 | 说明 |
|------|------|
| **优先级** | P1 (重要) |
| **工作量** | 6 小时 |
| **依赖** | FR-003 |

#### 需求描述
提供数据对比分析功能，支持周/月/季度对比。

#### 功能点

**FR-005-1: 时间对比**
- [ ] 周对比 (本周 vs 上周)
- [ ] 月对比 (本月 vs 上月)
- [ ] 季度对比 (本季度 vs 上季度)
- [ ] 自定义时间范围对比

**FR-005-2: 指标对比**
- [ ] 价格变化对比
- [ ] 评分变化对比
- [ ] 评论数变化对比
- [ ] BSR 排名变化对比
- [ ] 趋势评分变化对比

**FR-005-3: 竞品对比**
- [ ] 多商品对比 (最多 5 个)
- [ ] 对比图表展示
- [ ] 对比报告导出

#### API 设计
```python
# GET /api/v2/compare/time
# 时间对比
params:
  - asin: B0BQPNMXQV
  - period: week|month|quarter
  - metric: price|rating|reviews|bsr|trend

# GET /api/v2/compare/products
# 多商品对比
params:
  - asins: B0BQPNMXQV,B0ABCD1234,B0EFGH5678
  - metric: all|price|rating|bsr

# GET /api/v2/history/trend
# 历史趋势
params:
  - asin: B0BQPNMXQV
  - days: 30|60|90
  - metrics: price,rating,bsr
```

#### 响应示例
```json
{
  "success": true,
  "asin": "B0BQPNMXQV",
  "period": "week",
  "comparison": {
    "price": {
      "current": 29.94,
      "previous": 32.99,
      "change": -3.05,
      "change_percent": -9.24
    },
    "rating": {
      "current": 4.3,
      "previous": 4.2,
      "change": 0.1,
      "change_percent": 2.38
    },
    "ratings_total": {
      "current": 36211,
      "previous": 35800,
      "change": 411,
      "change_percent": 1.15
    },
    "bsr_rank": {
      "current": 1250,
      "previous": 1580,
      "change": -330,
      "change_percent": -20.89
    },
    "trend_score": {
      "current": 51.0,
      "previous": 48.5,
      "change": 2.5,
      "change_percent": 5.15
    }
  },
  "summary": "价格下降 9.24%，BSR 排名提升 20.89%，趋势向好"
}
```

#### 验收标准
- [ ] 时间对比数据准确
- [ ] 多商品对比图表正常
- [ ] 对比报告可导出 (PDF/CSV)

---

### FR-006: 数据查询 API

| 属性 | 说明 |
|------|------|
| **优先级** | P1 (重要) |
| **工作量** | 4 小时 |
| **依赖** | FR-002, FR-003 |

#### 需求描述
提供丰富的数据查询接口。

#### API 端点

```python
# 商品查询
GET /api/v2/products
  - keyword: 搜索关键词
  - category: 分类过滤
  - min_rating: 最低评分
  - max_price: 最高价格
  - sort: rating|price|bsr|trend
  - order: asc|desc
  - page: 页码
  - limit: 每页数量

# 商品详情
GET /api/v2/products/{asin}
  - 包含完整商品信息
  - 包含历史数据摘要

# 历史数据
GET /api/v2/products/{asin}/history
  - days: 天数 (7|30|60|90)
  - metrics: 指标 (price|rating|bsr|trend)

# 价格历史
GET /api/v2/products/{asin}/price-history
  - days: 天数

# BSR 历史
GET /api/v2/products/{asin}/bsr-history
  - days: 天数

# 数据统计
GET /api/v2/stats/overview
  - 总商品数
  - 今日更新数
  - 平均评分
  - 平均价格

# 数据导出
GET /api/v2/export
  - format: csv|json|xlsx
  - asins: 商品列表
  - fields: 字段选择
```

#### 验收标准
- [ ] 查询响应时间 <500ms
- [ ] 分页功能正常
- [ ] 数据导出格式正确

---

### FR-007: 数据管理功能

| 属性 | 说明 |
|------|------|
| **优先级** | P2 (可选) |
| **工作量** | 4 小时 |
| **依赖** | FR-002 |

#### 需求描述
提供数据管理功能，支持数据清理和维护。

#### 功能点

**FR-007-1: 数据清理**
- [ ] 清理过期数据 (可配置保留天数)
- [ ] 清理重复数据
- [ ] 清理无效商品 (下架商品)

**FR-007-2: 数据备份**
- [ ] 数据库备份命令
- [ ] 自动备份计划
- [ ] 备份恢复功能

**FR-007-3: 数据导入**
- [ ] CSV 导入功能
- [ ] JSON 导入功能
- [ ] 导入数据验证

#### 命令行工具
```bash
# 数据清理
python -m src.db.cleanup --days 90 --dry-run

# 数据备份
python -m src.db.backup --output /backup/

# 数据恢复
python -m src.db.restore --input /backup/db_20260327.sql

# 数据导入
python -m src.db.import --file data.csv --format csv
```

#### 验收标准
- [ ] 数据清理安全 (有确认步骤)
- [ ] 备份文件可正常恢复
- [ ] 导入数据验证正确

---

## 🗄️ 技术设计

### 技术栈选择

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| **数据库** | SQLite / PostgreSQL | SQLite 默认，PostgreSQL 生产 |
| **ORM** | SQLAlchemy 2.0 | 支持异步操作 |
| **迁移** | Alembic | 数据库版本管理 |
| **连接池** | SQLAlchemy Pool | 内置连接池 |
| **调度** | APScheduler | Python 定时任务 |
| **缓存** | SQLAlchemy Cache | 查询结果缓存 |

### 目录结构

```
src/
├── db/                      # 新增：数据库模块
│   ├── __init__.py
│   ├── connection.py        # 数据库连接
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── product.py       # Product 模型
│   │   ├── history.py       # History 模型
│   │   └── base.py          # 基础模型
│   ├── repositories/        # 数据访问层
│   │   ├── __init__.py
│   │   ├── product_repo.py
│   │   └── history_repo.py
│   ├── migrations/          # 数据库迁移
│   │   ├── versions/
│   │   └── env.py
│   ├── scheduler.py         # 定时任务调度
│   └── cli.py               # 数据库 CLI 工具
├── analysis/
│   ├── trend_analyzer.py    # 修改：支持数据库输入
│   └── visualizer.py        # 修改：支持数据库输入
├── workflow.py              # 修改：集成数据库
└── utils/
    ├── config.py            # 修改：添加数据库配置
    └── helpers.py
```

### 数据库配置

```python
# src/utils/config.py

DATABASE_CONFIG = {
    # 数据库类型
    'type': 'sqlite',  # sqlite | postgresql
    
    # SQLite 配置
    'sqlite': {
        'path': 'data/amazon_selector.db',
        'echo': False,  # SQL 日志
    },
    
    # PostgreSQL 配置
    'postgresql': {
        'host': 'localhost',
        'port': 5432,
        'database': 'amazon_selector',
        'user': 'admin',
        'password': '',
        'ssl_mode': 'prefer',
    },
    
    # 连接池配置
    'pool': {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 3600,
    },
    
    # 缓存配置
    'cache': {
        'enabled': True,
        'ttl': 300,  # 5 分钟
    }
}
```

---

## 📅 实施计划

### 阶段 1: 数据库基础 (12 小时)

| 任务 | 工时 | 依赖 | 交付物 |
|------|------|------|--------|
| 数据库连接模块 | 3h | - | `db/connection.py` |
| 数据模型定义 | 4h | - | `db/models/*.py` |
| 数据访问层 | 3h | 数据模型 | `db/repositories/*.py` |
| 数据库迁移 | 2h | 数据模型 | `db/migrations/` |

**里程碑:** 数据库可正常读写

---

### 阶段 2: 历史追踪 (14 小时)

| 任务 | 工时 | 依赖 | 交付物 |
|------|------|------|--------|
| 历史记录表 | 3h | 阶段 1 | `product_history` 表 |
| 采集集成 | 4h | 历史记录表 | 自动记录历史 |
| 定时任务 | 4h | 采集集成 | `scheduler.py` |
| 历史查询 API | 3h | 历史记录表 | `/api/v2/history/*` |

**里程碑:** 历史数据自动采集和查询

---

### 阶段 3: 数据对比 (8 小时)

| 任务 | 工时 | 依赖 | 交付物 |
|------|------|------|--------|
| 对比算法 | 3h | 历史数据 | 对比计算逻辑 |
| 对比 API | 3h | 对比算法 | `/api/v2/compare/*` |
| 对比图表 | 2h | 对比 API | 可视化图表 |

**里程碑:** 数据对比功能可用

---

### 阶段 4: 数据管理 (6 小时)

| 任务 | 工时 | 依赖 | 交付物 |
|------|------|------|--------|
| 数据清理 | 2h | - | `cleanup.py` |
| 数据备份 | 2h | - | `backup.py` |
| 数据导入 | 2h | - | `import.py` |

**里程碑:** 数据管理工具完整

---

### 总计

| 阶段 | 工时 | 百分比 |
|------|------|--------|
| 阶段 1 | 12h | 30% |
| 阶段 2 | 14h | 35% |
| 阶段 3 | 8h | 20% |
| 阶段 4 | 6h | 15% |
| **总计** | **40h** | **100%** |

---

## ✅ 验收标准

### 功能验收

| 功能 | 验收标准 | 状态 |
|------|---------|------|
| 数据库集成 | SQLite/PostgreSQL 正常连接 | 📋 |
| 商品存储 | 商品数据正确存储和查询 | 📋 |
| 历史追踪 | 每次采集自动记录历史 | 📋 |
| 定时采集 | 按配置自动执行采集 | 📋 |
| 数据对比 | 周/月/季度对比准确 | 📋 |
| 查询 API | 响应时间 <500ms | 📋 |
| 数据管理 | 清理/备份/导入正常 | 📋 |

### 性能验收

| 指标 | 目标值 | 测试方法 |
|------|--------|---------|
| 查询响应时间 | <500ms | 1000 次查询平均 |
| 写入响应时间 | <200ms | 单次插入 |
| 并发连接 | 100 连接 | 压力测试 |
| 历史数据量 | 30 天+ | 数据量验证 |
| 数据库大小 | <1GB (30 天) | 磁盘占用 |

### 质量验收

| 指标 | 目标值 |
|------|--------|
| 单元测试覆盖率 | >90% |
| 集成测试通过率 | 100% |
| 文档完整度 | 100% |
| 代码审查通过 | 2 人批准 |

---

## 📊 风险评估

### 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 数据库迁移失败 | 高 | 低 | 充分测试，备份数据 |
| 性能不达标 | 中 | 中 | 索引优化，查询优化 |
| 数据丢失 | 高 | 低 | 事务处理，备份机制 |

### 进度风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 工作量低估 | 中 | 中 | 分阶段交付，优先核心功能 |
| 依赖延迟 | 低 | 低 | 提前准备依赖，预留缓冲 |

---

## 📚 交付物清单

### 代码
- [ ] `src/db/connection.py` - 数据库连接
- [ ] `src/db/models/*.py` - 数据模型 (3 个文件)
- [ ] `src/db/repositories/*.py` - 数据访问层 (2 个文件)
- [ ] `src/db/migrations/` - 数据库迁移
- [ ] `src/db/scheduler.py` - 定时调度
- [ ] `src/db/cli.py` - 命令行工具
- [ ] `src/db/backup.py` - 数据备份
- [ ] `src/db/cleanup.py` - 数据清理

### API
- [ ] `GET /api/v2/products` - 商品查询
- [ ] `GET /api/v2/products/{asin}` - 商品详情
- [ ] `GET /api/v2/products/{asin}/history` - 历史数据
- [ ] `GET /api/v2/compare/time` - 时间对比
- [ ] `GET /api/v2/compare/products` - 多商品对比
- [ ] `GET /api/v2/stats/overview` - 数据统计
- [ ] `GET /api/v2/export` - 数据导出

### 文档
- [ ] `docs/05-Project-Docs/v2.2-release-notes.md` - 发布说明
- [ ] `docs/04-Technical-Docs/database-schema.md` - 数据库设计
- [ ] `docs/04-Technical-Docs/migration-guide.md` - 迁移指南
- [ ] `docs/02-User-Guide/data-management.md` - 数据管理指南

### 测试
- [ ] `tests/test_db_connection.py` - 连接测试
- [ ] `tests/test_db_models.py` - 模型测试
- [ ] `tests/test_db_repositories.py` - 仓库测试
- [ ] `tests/test_db_scheduler.py` - 调度测试
- [ ] `tests/test_api_v2.py` - API 测试

---

## 🔗 相关文档

| 文档 | 链接 |
|------|------|
| 项目路线图 | `docs/05-Project-Docs/roadmap.md` |
| 执行计划 | `context/plans/active/DOC-2026-001.md` |
| 数据库设计 | `docs/04-Technical-Docs/database-schema.md` (待创建) |
| 迁移指南 | `docs/04-Technical-Docs/migration-guide.md` (待创建) |

---

**需求设计版本:** v1.0  
**制定时间:** 2026-03-27  
**状态:** 📋 待评审  
**评审人:** @admina

---

<div align="center">

**📊 v2.2 需求设计完成!**

[项目路线图](docs/05-Project-Docs/roadmap.md) | [执行计划](context/plans/active/DOC-2026-001.md)

</div>
