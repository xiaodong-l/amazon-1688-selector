# 🗺️ API 路由与前端页面对照表

**生成时间:** 2026-03-27 13:52 UTC  
**版本:** v2.4.0

---

## 📊 总览

| 类别 | API 端点 | 前端页面 | 状态 |
|------|---------|---------|------|
| **核心页面** | - | 3 个 | ✅ |
| **产品 API** | 3 个 | - | ✅ |
| **分析 API** | 8 个 | 1 个 | ✅ |
| **监控 API** | 7 个 | 1 个 | ✅ |
| **用户 API** | 8 个 | ❌ 缺失 | ⚠️ |
| **认证 API** | ❌ 缺失 | ❌ 缺失 | ⚠️ |

---

## 🏠 核心页面

### 1. 首页 (`/`)

**模板:** `web/templates/index.html`

**功能:**
- 商品列表展示
- 增强指标面板
- 搜索/过滤

**关联 API:**
| API | 方法 | 说明 |
|-----|------|------|
| `/api/products` | GET | 获取商品列表 |
| `/api/config` | GET | 获取配置 |

---

### 2. 图表页 (`/charts`)

**模板:** `web/templates/charts.html`

**功能:**
- 6 种图表类型
- 趋势可视化
- 交互式图表

**关联 API:**
| API | 方法 | 说明 |
|-----|------|------|
| `/api/charts` | GET | 获取图表数据 |
| `/static/charts/<filename>` | GET | 获取图表图片 |

---

### 3. 模型对比页 (`/analysis/model-comparison`)

**模板:** `web/templates/analysis/model_comparison.html`

**功能:**
- 多模型对比 (线性/Prophet/LSTM)
- 指标对比表格
- 预测对比图表
- 最佳模型推荐
- 自动刷新 (30 秒)

**关联 API:**
| API | 方法 | 说明 |
|-----|------|------|
| `/api/v2/analysis/compare-models` | GET | 模型对比指标 |
| `/api/v2/analysis/model-report` | GET | 对比报告 |
| `/api/v2/analysis/compare/predict` | POST | 多模型预测 |
| `/api/v2/analysis/best-model` | GET | 最佳模型推荐 |
| `/api/v2/analysis/visualizations` | GET | 可视化图表 |

---

## 📈 监控页面

### 监控仪表板 (`/monitor`)

**模板:** `web/templates/monitor/dashboard.html`

**功能:**
- 系统健康状态
- Prometheus 指标可视化
- 请求追踪列表
- 错误统计图表
- 慢查询列表
- 自动刷新 (30 秒)

**关联 API:**
| API | 方法 | 说明 |
|-----|------|------|
| `/api/v2/monitor/health` | GET | 健康检查 |
| `/api/v2/monitor/metrics/prometheus` | GET | Prometheus 指标 |
| `/api/v2/monitor/metrics/summary` | GET | 指标摘要 |
| `/api/v2/monitor/traces` | GET | 请求追踪 |
| `/api/v2/monitor/slow-queries` | GET | 慢查询 |
| `/api/v2/monitor/errors` | GET | 错误列表 |
| `/api/v2/monitor/stats` | GET | 统计信息 |

---

## ⚠️ 缺失的前端页面

### 1. 用户管理页面

**API 已存在:**
| API | 方法 | 说明 |
|-----|------|------|
| `/api/v2/users` | GET | 用户列表 |
| `/api/v2/users` | POST | 创建用户 |
| `/api/v2/users/<id>` | GET | 用户详情 |
| `/api/v2/users/<id>` | PUT | 更新用户 |
| `/api/v2/users/<id>` | DELETE | 删除用户 |
| `/api/v2/users/<id>/password` | POST | 修改密码 |
| `/api/v2/users/<id>/permissions` | GET | 获取权限 |
| `/api/v2/users/<id>/permissions` | POST | 分配权限 |

**缺失页面:**
- ❌ 用户列表页
- ❌ 用户详情页
- ❌ 用户编辑页

**建议创建:**
- `web/templates/users/list.html`
- `web/templates/users/detail.html`
- `web/templates/users/edit.html`

---

### 2. 认证页面

**API 状态:** ❌ 缺失 (模块已存在 `src/auth/`，但未实现 API)

**缺失 API:**
- ❌ `/api/v2/auth/login` - 登录
- ❌ `/api/v2/auth/logout` - 登出
- ❌ `/api/v2/auth/token/refresh` - 刷新 Token
- ❌ `/api/v2/auth/api-keys` - API Key 管理

**缺失页面:**
- ❌ 登录页 (`web/templates/auth/login.html`) - 已创建但未集成
- ❌ API Key 管理页 (`web/templates/auth/api_keys.html`) - 已创建但未集成

---

## 🔧 建议的改进

### 优先级 1: 集成认证 UI

**任务:**
1. 实现认证 API (`web/routes/auth.py`)
2. 集成登录页面到主应用
3. 添加 JWT Token 管理

**文件:**
- `web/routes/auth.py` (新建)
- `web/templates/auth/login.html` (已存在，需集成)

---

### 优先级 2: 创建用户管理 UI

**任务:**
1. 创建用户列表页
2. 创建用户详情页
3. 创建用户编辑页
4. 集成到导航菜单

**文件:**
- `web/templates/users/list.html` (新建)
- `web/templates/users/detail.html` (新建)
- `web/templates/users/edit.html` (新建)

---

### 优先级 3: 添加导航菜单

**任务:**
1. 创建公共导航栏
2. 添加页面切换
3. 添加用户状态显示

**建议位置:**
- `web/templates/base.html` (新建基础模板)
- 或更新所有现有模板

---

## 📁 文件结构

```
web/
├── app.py                      # 主应用 ✅
├── routes/
│   ├── analysis.py             # 分析 API ✅
│   ├── monitor.py              # 监控 API ✅
│   ├── users.py                # 用户 API ✅
│   └── auth.py                 # 认证 API ❌ 缺失
└── templates/
    ├── index.html              # 首页 ✅
    ├── charts.html             # 图表页 ✅
    ├── analysis/
    │   └── model_comparison.html  # 模型对比 ✅
    ├── monitor/
    │   └── dashboard.html      # 监控仪表板 ✅
    ├── auth/
    │   ├── login.html          # 登录页 ✅ (未集成)
    │   └── api_keys.html       # API Key 管理 ✅ (未集成)
    └── users/
    │   ├── list.html           # 用户列表 ❌ 缺失
    │   ├── detail.html         # 用户详情 ❌ 缺失
    │   └── edit.html           # 用户编辑 ❌ 缺失
```

---

## 🎯 下一步行动

### 立即可做

1. **集成认证页面**
   - 创建 `web/routes/auth.py`
   - 集成登录页面
   - 添加导航菜单

2. **创建用户管理页面**
   - 用户列表页
   - 用户详情页
   - 用户编辑页

3. **添加导航系统**
   - 基础模板
   - 导航菜单
   - 页面切换

---

**文档将持续更新...**
