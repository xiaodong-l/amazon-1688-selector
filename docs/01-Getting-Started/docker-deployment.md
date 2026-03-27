# 🐳 Docker 容器化部署指南

**版本:** v2.4.0  
**更新时间:** 2026-03-27 14:20 UTC

---

## 📋 前置要求

| 要求 | 版本 | 说明 |
|------|------|------|
| Docker | 20.10+ | 容器运行时 |
| Docker Compose | 2.0+ | 编排工具 |
| 内存 | 8GB+ | 推荐 16GB |
| 磁盘 | 10GB+ | 数据持久化 |

---

## 🚀 快速部署

### 1. 克隆代码

```bash
git clone https://github.com/xiaodong-l/amazon-1688-selector.git
cd amazon-1688-selector
```

### 2. 配置环境变量

```bash
# 复制环境配置模板
cp .env.example .env

# 编辑配置
vim .env
```

**必要配置:**
```bash
# 密钥配置
SECRET_KEY=your-super-secret-key-change-this

# 数据库配置
POSTGRES_DB=amazon
POSTGRES_USER=amazon
POSTGRES_PASSWORD=your-password

# Grafana 配置
GF_ADMIN_PASSWORD=your-grafana-password
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 检查服务状态
docker-compose ps
```

### 4. 初始化数据库

```bash
# 进入容器
docker-compose exec web bash

# 运行数据库迁移
python -m src.db.cli db upgrade

# 退出
exit
```

### 5. 验证部署

```bash
# 测试首页
curl http://localhost:5000/

# 测试健康检查
curl http://localhost:5000/api/v2/monitor/health

# 测试模型对比 API
curl http://localhost:5000/api/v2/analysis/compare-models
```

---

## 🌐 访问服务

| 服务 | URL | 默认账号 | 默认密码 |
|------|-----|---------|---------|
| **Web 应用** | http://localhost:5000 | - | - |
| **Grafana** | http://localhost:3000 | admin | admin123 |
| **Prometheus** | http://localhost:9090 | - | - |
| **Alertmanager** | http://localhost:9093 | - | - |
| **PostgreSQL** | localhost:5432 | amazon | amazon123 |
| **Redis** | localhost:6379 | - | - |

---

## 📊 Grafana 仪表板

### 配置数据源

1. 访问 http://localhost:3000
2. 登录 (admin/admin123)
3. 配置 → Data Sources
4. 添加 Prometheus 数据源
   - URL: `http://prometheus:9090`
   - 保存并测试

### 导入仪表板

**预配置仪表板:**
- `app-overview.json` - 应用概览
- `database-monitoring.json` - 数据库监控
- `rate-limiting.json` - 限流监控
- `auth-security.json` - 认证安全

**导入步骤:**
1. Dashboard → Import
2. 上传 JSON 文件
3. 选择 Prometheus 数据源
4. Import

---

## 🔧 常用命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 重启单个服务
docker-compose restart web

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f web
```

### 进入容器

```bash
# 进入 Web 容器
docker-compose exec web bash

# 进入数据库容器
docker-compose exec db psql -U amazon -d amazon

# 进入 Redis 容器
docker-compose exec redis redis-cli
```

### 数据库操作

```bash
# 数据库备份
docker-compose exec db pg_dump -U amazon amazon > backup.sql

# 数据库恢复
docker-compose exec -T db psql -U amazon amazon < backup.sql

# 运行迁移
docker-compose exec web python -m src.db.cli db upgrade

# 回滚迁移
docker-compose exec web python -m src.db.cli db downgrade -1
```

### 数据清理

```bash
# 清理所有数据卷 (谨慎！)
docker-compose down -v

# 清理构建缓存
docker-compose build --no-cache

# 清理停止的容器
docker-compose rm -f
```

---

## 🔐 生产环境配置

### 1. 修改默认密码

```bash
# .env 文件
POSTGRES_PASSWORD=<强密码>
SECRET_KEY=<随机密钥>
GF_ADMIN_PASSWORD=<强密码>
```

### 2. 启用 HTTPS

```bash
# 使用 Nginx 反向代理
# 或使用 Traefik 自动 HTTPS
```

### 3. 配置备份

```bash
# 创建备份脚本
cat > scripts/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T db pg_dump -U amazon amazon | gzip > backup_$DATE.sql.gz
echo "Backup completed: backup_$DATE.sql.gz"
EOF

chmod +x scripts/backup.sh

# 添加 Cron 任务
crontab -e
# 每天凌晨 2 点备份
0 2 * * * /path/to/scripts/backup.sh
```

### 4. 配置监控告警

```yaml
# monitoring/alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alerts@example.com'

route:
  receiver: 'email-notifications'

receivers:
  - name: 'email-notifications'
    email_configs:
      - to: 'admin@example.com'
```

---

## 📈 性能优化

### 1. 增加资源限制

```yaml
# docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 2. 启用 Redis 缓存

```python
# 配置中使用 Redis 缓存
REDIS_URL=redis://redis:6379
```

### 3. 数据库连接池

```yaml
# 调整 PostgreSQL 配置
# postgresql.conf
shared_buffers = 256MB
max_connections = 100
```

### 4. 水平扩展

```bash
# 扩展 Web 服务到 3 个实例
docker-compose up -d --scale web=3
```

---

## 🐛 故障排查

### 问题 1: 服务启动失败

```bash
# 查看日志
docker-compose logs web

# 检查依赖服务
docker-compose ps

# 重新构建
docker-compose build --no-cache
```

### 问题 2: 数据库连接失败

```bash
# 检查数据库状态
docker-compose exec db pg_isready

# 查看数据库日志
docker-compose logs db

# 重置数据库 (谨慎！)
docker-compose down -v
docker-compose up -d db
```

### 问题 3: 端口冲突

```bash
# 修改 docker-compose.yml 端口映射
ports:
  - "5001:5000"  # 改为 5001
```

### 问题 4: 磁盘空间不足

```bash
# 清理 Docker 资源
docker system prune -a

# 清理日志
docker-compose logs --tail=100
```

---

## 📊 监控指标

### Prometheus 指标

| 指标 | 说明 |
|------|------|
| `http_requests_total` | HTTP 请求总数 |
| `http_request_duration_seconds` | 请求延迟 |
| `db_connections_active` | 活跃数据库连接 |
| `rate_limit_hits_total` | 限流触发次数 |
| `products_scanned_total` | 商品采集数量 |

### Grafana 告警规则

```yaml
# 高错误率告警
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
  for: 5m
  annotations:
    summary: "高错误率告警"

# 慢查询告警
- alert: SlowQueries
  expr: rate(db_query_duration_seconds_count{quantile="0.99"}[5m]) > 1
  for: 5m
  annotations:
    summary: "慢查询告警"
```

---

## 🔗 相关文档

| 文档 | 位置 |
|------|------|
| API 路由图 | `docs/API-ROUTE-MAP.md` |
| 预测模型指南 | `docs/02-User-Guide/v2.4-prediction-guide.md` |
| 监控指南 | `docs/04-Technical-Docs/monitoring.md` |
| 部署测试报告 | `reports/DEPLOYMENT-SUMMARY-20260327.md` |

---

**Docker 部署配置完成!** 🐳✅
