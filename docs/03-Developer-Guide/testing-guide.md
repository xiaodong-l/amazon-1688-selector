# 采集模块测试指南

## 快速开始

### 步骤 1: 配置环境

```bash
cd /home/admina/.openclaw-imperial/workspace-taizi/projects/amazon-1688-selector

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件 (可选，SP-API 需要配置)
nano .env
```

### 步骤 2: 安装依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 步骤 3: 运行测试

```bash
# 运行自动化测试套件
python -m tests.test_collector

# 或直接运行
python tests/test_collector.py
```

---

## 测试模式说明

### 模式 1: 自动化测试
运行全部 4 项测试：
- SP-API 连接测试
- Playwright 采集测试
- SP-API 采集测试
- 数据导出测试

### 模式 2: 交互式测试
手动输入关键词进行采集测试，可保存结果到 CSV

---

## 预期输出

```
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀
   亚马逊采集模块 - 测试套件
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀

============================================================
🔌 测试 1: SP-API 连接测试
============================================================
✅ SP-API 初始化成功

============================================================
🎭 测试 2: Playwright 采集测试
============================================================
正在采集关键词：wireless earbuds
✅ 采集成功，获取 5 个商品

示例数据:
  1. Wireless Earbuds Bluetooth 5.0 Headphones...
     ASIN: B08XYZ123
     价格：$29.99
  2. True Wireless Earbuds with Charging Case...
     ASIN: B09ABC456
     价格：$24.99

...

============================================================
📊 测试汇总报告
============================================================

通过：4 | 失败：0 | 跳过：0
总计：4 项测试

✅ 所有测试通过！采集模块可以正常使用
```

---

## 常见问题

### Q1: SP-API 初始化失败
**原因:** 未配置 API 凭证或未安装 SDK

**解决:**
```bash
pip install sp-api-python
# 编辑 .env 填入 AMAZON_SP_API_ID 和 AMAZON_SP_API_SECRET
```

### Q2: Playwright 采集失败
**原因:** 浏览器未安装

**解决:**
```bash
playwright install chromium
```

### Q3: 采集结果为空
**原因:** 网络问题或反爬限制

**解决:**
1. 检查网络连接
2. 使用代理 IP
3. 增加请求延迟 (.env 中 AMAZON_REQUEST_DELAY)

---

## 下一步

测试通过后，继续开发：
- W2: 销售趋势分析模块
- W3: 1688 供应商匹配模块
- W4: 系统集成测试

---

**有问题？汇报给尚书省或直接向皇帝请示。**
