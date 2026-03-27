# ❓ 常见问题 (FAQ)

**版本:** v2.1.0  
**最后更新:** 2026-03-27  
**状态:** ✅ 已完成

---

## 📋 目录

1. [安装问题](#安装问题)
2. [配置问题](#配置问题)
3. [数据采集](#数据采集)
4. [趋势分析](#趋势分析)
5. [Web 界面](#web 界面)
6. [API 使用](#api-使用)
7. [图表生成](#图表生成)
8. [性能优化](#性能优化)

---

## 安装问题

### Q1: pip 安装依赖失败

**错误信息:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**解决方案:**
```bash
# 1. 升级 pip
pip install --upgrade pip

# 2. 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 检查 Python 版本 (需要 3.10+)
python --version  # 应 >= 3.10
```

---

### Q2: 虚拟环境激活失败

**错误信息:**
```
bash: venv/bin/activate: No such file or directory
```

**解决方案:**
```bash
# 1. 删除并重新创建虚拟环境
rm -rf venv
python3 -m venv venv

# 2. 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 3. 验证激活
which python  # 应显示 venv 路径
```

---

### Q3: 权限错误

**错误信息:**
```
Permission denied: 'venv/bin/pip'
```

**解决方案:**
```bash
# 1. 修复权限
chmod -R u+w venv/

# 2. 或使用 --user 安装
pip install --user -r requirements.txt

# 3. 或使用 sudo (不推荐)
sudo pip install -r requirements.txt
```

---

### Q4: Python 版本不兼容

**错误信息:**
```
Python 3.8 is not supported. Please use Python 3.10+
```

**解决方案:**
```bash
# Ubuntu/Debian - 安装 Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev -y

# macOS - 使用 Homebrew
brew install python@3.12

# 创建新虚拟环境
python3.12 -m venv venv
source venv/bin/activate
```

---

## 配置问题

### Q5: API 密钥未配置

**错误信息:**
```
ValueError: RAINFOREST_API_KEY not configured
```

**解决方案:**
```bash
# 1. 检查 .env 文件是否存在
ls -la .env

# 2. 如果没有，复制模板
cp .env.example .env

# 3. 编辑 .env 文件，填入真实 API 密钥
vim .env

# 4. 确保格式正确 (无空格)
# 正确：RAINFOREST_API_KEY=abc123xyz
# 错误：RAINFOREST_API_KEY = abc123xyz

# 5. 获取 API 密钥：https://www.rainforestapi.com/
```

---

### Q6: 配置文件未生效

**症状:** 修改配置后无变化

**解决方案:**
```bash
# 1. 检查文件是否保存
cat .env | grep KEY

# 2. 重启 Web 服务
pkill -f "python.*app.py"
python web/app.py

# 3. 清除缓存
rm -rf .cache/

# 4. 验证配置加载
python -c "from utils import config; print(config.ANALYSIS_WEIGHTS)"
```

---

### Q7: 端口被占用

**错误信息:**
```
Address already in use: Port 5000 is in use
```

**解决方案:**
```bash
# 1. 查找占用端口的进程
lsof -i :5000

# 2. 杀死进程
kill -9 <PID>

# 3. 或更改端口
# 编辑 .env 文件
FLASK_PORT=8080

# 4. 重启服务
python web/app.py
```

---

## 数据采集

### Q8: 采集速度慢

**症状:** 采集 20 个商品需要很长时间

**解决方案:**
```bash
# 1. 检查网络连接
ping api.rainforestapi.com

# 2. 使用代理 (如果需要)
# 编辑 .env 文件
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080

# 3. 减少并发数
# 编辑 src/utils/config.py
MAX_CONCURRENT_REQUESTS = 5  # 降低并发

# 4. 使用缓存
# 编辑 .env 文件
CACHE_ENABLED=true
CACHE_TTL=3600
```

---

### Q9: API 配额超限

**错误信息:**
```
Rainforest API error: Monthly quota exceeded
```

**解决方案:**
```bash
# 1. 检查配额使用情况
# 登录 https://www.rainforestapi.com/ 查看

# 2. 等待下个月配额重置

# 3. 或升级 API 套餐

# 4. 使用缓存减少 API 调用
CACHE_ENABLED=true
CACHE_TTL=7200  # 延长缓存时间

# 5. 减少采集数量
python -m src.workflow --keywords "earbuds" --limit 10
```

---

### Q10: 采集数据为空

**症状:** 采集完成但无数据

**解决方案:**
```bash
# 1. 检查关键词是否有效
# 尝试更具体的关键词
python -m src.workflow --keywords "JBL wireless earbuds"

# 2. 检查 API 密钥是否有效
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.rainforestapi.com/request?api_key=YOUR_API_KEY&type=search&amazon_domain=amazon.com&search_term=test"

# 3. 查看详细日志
cat logs/app.log | grep ERROR

# 4. 尝试不同亚马逊站点
# 编辑 src/amazon/collector.py
amazon_domain = "amazon.com"  # 或 amazon.co.jp, amazon.co.uk
```

---

## 趋势分析

### Q11: 趋势评分异常

**症状:** 趋势评分过高或过低

**解决方案:**
```python
# 1. 检查权重配置
# 编辑 src/utils/config.py
ANALYSIS_WEIGHTS = {
    'sales_growth': 0.30,
    'review_growth': 0.20,
    'bsr_improvement': 0.15,
    'profit_margin': 0.15,
    'market_saturation': 0.10,
    'risk_score': 0.05
}

# 2. 检查阈值配置
ANALYSIS_THRESHOLDS = {
    'sales_growth': {
        'excellent': 20.0,
        'good': 10.0,
        ...
    }
}

# 3. 验证数据质量
python -c "
import pandas as pd
df = pd.read_csv('data/top20_*.csv')
print(df[['sales_growth', 'review_growth', 'bsr_rank']].describe())
"
```

---

### Q12: 预测不准确

**症状:** 30 天预测与实际不符

**解决方案:**
```python
# 1. 检查历史数据量
# 预测需要足够的历史数据 (建议 30 天+)

# 2. 调整季节性因子
# 编辑 src/utils/config.py
SEASONAL_FACTORS = {
    11: 1.30,  # 11 月 (黑色星期五)
    12: 1.40,  # 12 月 (圣诞季)
    ...
}

# 3. 使用更复杂的模型 (未来功能)
# Prophet 或 LSTM 模型

# 4. 降低预测置信度
# 编辑 src/analysis/trend_analyzer.py
confidence = 0.7  # 降低置信度
```

---

## Web 界面

### Q13: 页面无法访问

**症状:** 浏览器显示无法连接

**解决方案:**
```bash
# 1. 检查 Web 服务是否运行
ps aux | grep "python.*app.py"

# 2. 检查端口监听
netstat -tlnp | grep 5000

# 3. 检查防火墙
sudo ufw status
sudo ufw allow 5000

# 4. 尝试本地访问
curl http://localhost:5000

# 5. 查看 Web 服务日志
tail -f /tmp/amazon-web.log
```

---

### Q14: 页面显示空白

**症状:** 页面加载但无内容

**解决方案:**
```bash
# 1. 检查浏览器控制台 (F12)
# 查看 JavaScript 错误

# 2. 清除浏览器缓存
# Ctrl+Shift+Delete (Chrome)

# 3. 检查 API 是否正常
curl http://localhost:5000/api/products

# 4. 重启 Web 服务
pkill -f "python.*app.py"
python web/app.py

# 5. 检查模板文件
ls web/templates/
```

---

### Q15: 搜索功能无效

**症状:** 搜索框输入无反应

**解决方案:**
```javascript
// 1. 检查浏览器控制台 (F12)
// 查看 JavaScript 错误

// 2. 确保数据已加载
// 等待页面完全加载后再搜索

// 3. 尝试刷新页面
// Ctrl+R 或 F5

// 4. 检查网络请求
// F12 -> Network -> 查看搜索请求
```

---

## API 使用

### Q16: API 返回 404

**错误信息:**
```
404 Not Found
```

**解决方案:**
```bash
# 1. 检查端点 URL 是否正确
curl http://localhost:5000/api/products  # 正确
curl http://localhost:5000/products      # 错误 (缺少/api)

# 2. 检查 Web 服务是否运行
curl http://localhost:5000/api/health

# 3. 检查请求方法
curl -X GET http://localhost:5000/api/products   # 正确
curl -X POST http://localhost:5000/api/products  # 错误 (应为 GET)
```

---

### Q17: API 返回 500 错误

**错误信息:**
```
500 Internal Server Error
```

**解决方案:**
```bash
# 1. 查看详细错误日志
tail -f logs/app.log

# 2. 检查请求参数
curl -v http://localhost:5000/api/products?limit=-1  # 无效参数

# 3. 检查数据文件是否存在
ls data/top20_*.csv

# 4. 重启 Web 服务
pkill -f "python.*app.py"
python web/app.py
```

---

## 图表生成

### Q18: 图表无法生成

**错误信息:**
```
Kaleido requires Google Chrome or Chromium
```

**解决方案:**
```bash
# 1. 安装 Chrome/Chromium
# Ubuntu/Debian
sudo apt install chromium-browser -y

# macOS
brew install --cask google-chrome

# 2. 验证安装
which chromium-browser || which google-chrome

# 3. 使用 HTML 格式 (不需要 Chrome)
# 编辑 src/utils/config.py
VISUALIZATION_CONFIG = {
    'format': 'html',  # 改为 html
    ...
}

# 4. 或跳过 PNG 导出
# 图表仍会生成 HTML 版本
```

---

### Q19: 图表显示乱码

**症状:** 中文字符显示为方框

**解决方案:**
```python
# 1. 安装中文字体
# Ubuntu/Debian
sudo apt install fonts-wqy-zenhei -y

# macOS
# 系统已自带中文字体

# 2. 配置 Matplotlib 使用中文字体
# 编辑 src/utils/config.py
VISUALIZATION_CONFIG = {
    'chinese_font': 'SimHei',  # 或 'WenQuanYi Zen Hei'
    ...
}

# 3. 清除 Matplotlib 缓存
rm -rf ~/.matplotlib/

# 4. 重新生成图表
python -m src.workflow --keywords "earbuds"
```

---

### Q20: 图表质量差

**症状:** 图表模糊或分辨率低

**解决方案:**
```python
# 1. 提高 DPI 设置
# 编辑 src/utils/config.py
VISUALIZATION_CONFIG = {
    'dpi': 300,  # 从 150 提高到 300
    'width': 1920,
    'height': 1080,
    ...
}

# 2. 使用 SVG 格式 (矢量图)
# 编辑可视化代码
fig.savefig('chart.svg', format='svg')

# 3. 使用 HTML 交互式图表
# Plotly 默认生成 HTML 格式
```

---

## 性能优化

### Q21: 内存占用高

**症状:** 系统内存占用超过 1GB

**解决方案:**
```python
# 1. 减少采集数量
python -m src.workflow --keywords "earbuds" --limit 10

# 2. 启用数据分块处理
# 编辑 src/amazon/collector.py
BATCH_SIZE = 10  # 分批处理

# 3. 及时释放内存
# 编辑代码，添加
import gc
gc.collect()

# 4. 使用生成器而非列表
# 编辑数据处理代码
def process_products():
    for product in products:
        yield process(product)
```

---

### Q22: CPU 占用高

**症状:** CPU 持续 100%

**解决方案:**
```bash
# 1. 减少并发数
# 编辑 src/utils/config.py
MAX_CONCURRENT_REQUESTS = 3  # 降低并发

# 2. 添加请求延迟
# 编辑 src/amazon/collector.py
import time
time.sleep(1)  # 每个请求间隔 1 秒

# 3. 使用进程池限制
# 编辑分析代码
from multiprocessing import Pool
with Pool(processes=4) as pool:  # 限制为 4 进程
    results = pool.map(process, data)
```

---

### Q23: 磁盘空间不足

**错误信息:**
```
No space left on device
```

**解决方案:**
```bash
# 1. 清理旧数据
rm data/top20_*.csv.old
rm data/charts/*.png.old

# 2. 清理缓存
rm -rf .cache/

# 3. 清理日志
> logs/app.log

# 4. 限制数据保留天数
# 编辑清理脚本
find data/ -name "*.csv" -mtime +30 -delete

# 5. 压缩旧数据
gzip data/top20_*.csv
```

---

## 📚 其他资源

| 资源 | 链接 |
|------|------|
| [安装指南](./01-Getting-Started/installation.md) | 完整安装步骤 |
| [快速开始](./01-Getting-Started/quickstart.md) | 5 分钟上手 |
| [配置说明](./01-Getting-Started/configuration.md) | 详细配置 |
| [API 参考](./02-User-Guide/api-reference.md) | API 文档 |
| [GitHub Issues](https://github.com/xiaodong-l/amazon-1688-selector/issues) | 提交问题 |

---

## 💡 获取帮助

### 遇到问题？

1. **搜索 FAQ** - 本文档包含常见问题
2. **查看日志** - `logs/app.log` 包含详细错误信息
3. **搜索 Issue** - https://github.com/xiaodong-l/amazon-1688-selector/issues
4. **提交 Issue** - 提供错误信息和复现步骤
5. **讨论区** - https://github.com/xiaodong-l/amazon-1688-selector/discussions

### 提交 Issue 模板

```markdown
**问题描述:**
[简要描述问题]

**复现步骤:**
1. ...
2. ...
3. ...

**预期行为:**
[应该发生什么]

**实际行为:**
[实际发生了什么]

**环境信息:**
- OS: Ubuntu 22.04 / macOS 13 / Windows 11
- Python: 3.12.3
- 版本：v2.1.0

**日志:**
```
[粘贴相关日志]
```

**截图:**
[如有，添加截图]
```

---

**FAQ 版本:** v1.0  
**最后更新:** 2026-03-27  
**维护者:** @admina

---

<div align="center">

**❓ FAQ 完成!**

[安装指南](./01-Getting-Started/installation.md) | [快速开始](./01-Getting-Started/quickstart.md) | [提交 Issue](https://github.com/xiaodong-l/amazon-1688-selector/issues)

</div>
