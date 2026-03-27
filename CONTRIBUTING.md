# 🤝 贡献指南

感谢你对本项目的关注！欢迎以任何形式贡献代码、报告问题或提出建议。

## 📋 目录

- [代码贡献](#代码贡献)
- [报告问题](#报告问题)
- [提出建议](#提出建议)
- [开发环境](#开发环境)
- [提交规范](#提交规范)

---

## 💻 代码贡献

### 1. Fork 仓库

点击 GitHub 页面右上角的 "Fork" 按钮

### 2. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/amazon-1688-selector.git
cd amazon-1688-selector
```

### 3. 创建分支

```bash
# 功能开发
git checkout -b feature/your-feature-name

# Bug 修复
git checkout -b fix/issue-number

# 文档更新
git checkout -b docs/update-readme
```

### 4. 开发并测试

```bash
# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-cov flake8

# 运行测试
pytest tests/ -v

# 代码检查
flake8 src/ --max-line-length=127
```

### 5. 提交更改

```bash
git add .
git commit -m "feat: add your feature description"
```

### 6. 推送并创建 PR

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request

---

## 🐛 报告问题

### 创建 Issue 时请包含：

1. **问题描述** - 清晰描述遇到的问题
2. **复现步骤** - 如何重现这个问题
3. **期望行为** - 你认为正确的行为应该是什么
4. **实际行为** - 实际发生了什么
5. **环境信息** - Python 版本、操作系统等
6. **错误日志** - 完整的错误信息

### Issue 模板示例：

```markdown
### 问题描述
简要描述问题

### 复现步骤
1. 运行 '...'
2. 点击 '...'
3. 看到错误 '...'

### 期望行为
应该发生什么

### 实际行为
实际发生了什么

### 环境信息
- Python: 3.12.0
- OS: Ubuntu 22.04
- 版本：v2.1

### 错误日志
```
[粘贴完整错误日志]
```
```

---

## 💡 提出建议

### 功能建议请包含：

1. **功能描述** - 你想要什么功能
2. **使用场景** - 为什么需要这个功能
3. **实现建议** - 如何实现 (可选)
4. **替代方案** - 考虑过哪些其他方案

---

## 🛠️ 开发环境

### 系统要求

- Python 3.10+
- pip
- git

### 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/xiaodong-l/amazon-1688-selector.git
cd amazon-1688-selector

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装开发工具
pip install pytest pytest-cov flake8 black isort
```

### 代码规范

我们遵循 PEP 8 代码规范：

- 行宽限制：127 字符
- 缩进：4 个空格
- 导入排序：标准库 → 第三方 → 本地模块

### 运行代码检查

```bash
# 代码风格检查
flake8 src/ tests/

# 自动格式化 (可选)
black src/ tests/
isort src/ tests/
```

---

## 📝 提交规范

我们使用 [约定式提交](https://www.conventionalcommits.org/) 规范：

### 提交类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式 (不影响代码运行)
- `refactor`: 代码重构 (既不是新功能也不是 Bug 修复)
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具变动

### 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 提交示例

```bash
# 新功能
git commit -m "feat(analysis): 添加 30 天趋势预测功能"

# Bug 修复
git commit -m "fix(price): 修复空价格解析错误"

# 文档更新
git commit -m "docs(readme): 更新使用示例"

# 代码优化
git commit -m "refactor(utils): 提取价格为解析工具函数"

# 测试
git commit -m "test(analyzer): 添加利润率估算单元测试"
```

---

## 📚 相关资源

- [项目文档](README.md)
- [更新日志](CHANGELOG.md)
- [优化报告](OPTIMIZATION-COMPLETE.md)

---

## 🙏 致谢

感谢所有为本项目做出贡献的开发者！

<a href="https://github.com/xiaodong-l/amazon-1688-selector/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=xiaodong-l/amazon-1688-selector" />
</a>

---

<div align="center">

**再次感谢你的贡献！** 🎉

</div>
