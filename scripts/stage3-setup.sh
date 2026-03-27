#!/bin/bash
# =============================================================================
# 阶段 3 环境设置脚本
# =============================================================================
# 用途：安装阶段 3 (安全与监控) 所需依赖
# 创建时间：2026-03-27
# 使用方法：./scripts/stage3-setup.sh
# =============================================================================

set -e  # 遇到错误立即退出

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  阶段 3 (安全与监控) 环境设置"
echo "=========================================="
echo ""

# 进入项目目录
cd "$PROJECT_DIR"
echo "📁 项目目录：$PROJECT_DIR"
echo ""

# 检查 Python 版本
echo "🐍 检查 Python 版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python 版本：$PYTHON_VERSION"

# 检查是否为 Python 3.12+
REQUIRED_VERSION="3.12"
if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo "⚠️  警告：建议 Python 3.12+，当前版本：$PYTHON_VERSION"
else
    echo "✅ Python 版本符合要求"
fi
echo ""

# 激活虚拟环境 (如果存在)
if [ -d "venv" ]; then
    echo "🔄 激活虚拟环境..."
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
    echo ""
fi

# 安装阶段 3 依赖
echo "📦 安装阶段 3 依赖..."
if [ -f "requirements-stage3.txt" ]; then
    pip install -r requirements-stage3.txt
    echo "✅ 依赖安装完成"
else
    echo "❌ 错误：requirements-stage3.txt 不存在"
    exit 1
fi
echo ""

# 验证安装
echo "🔍 验证安装..."
echo ""

# 验证认证模块
echo "   验证认证模块..."
python3 -c "import jwt; print('   ✅ PyJWT OK')" 2>/dev/null || echo "   ❌ PyJWT 失败"
python3 -c "from jose import jwt; print('   ✅ python-jose OK')" 2>/dev/null || echo "   ❌ python-jose 失败"
python3 -c "import passlib; print('   ✅ passlib OK')" 2>/dev/null || echo "   ❌ passlib 失败"
python3 -c "import bcrypt; print('   ✅ bcrypt OK')" 2>/dev/null || echo "   ❌ bcrypt 失败"
echo ""

# 验证速率限制模块
echo "   验证速率限制模块..."
python3 -c "import flask_limiter; print('   ✅ Flask-Limiter OK')" 2>/dev/null || echo "   ❌ Flask-Limiter 失败"
python3 -c "import redis; print('   ✅ redis OK')" 2>/dev/null || echo "   ❌ redis 失败"
echo ""

# 验证监控模块
echo "   验证监控模块..."
python3 -c "import prometheus_client; print('   ✅ prometheus-client OK')" 2>/dev/null || echo "   ❌ prometheus-client 失败"
python3 -c "import grafana_api; print('   ✅ grafana-api OK')" 2>/dev/null || echo "   ❌ grafana-api 失败"
echo ""

# 验证测试模块
echo "   验证测试模块..."
python3 -c "import pytest_asyncio; print('   ✅ pytest-asyncio OK')" 2>/dev/null || echo "   ❌ pytest-asyncio 失败"
python3 -c "import pytest_cov; print('   ✅ pytest-cov OK')" 2>/dev/null || echo "   ❌ pytest-cov 失败"
echo ""

# 运行认证测试 (如果存在)
echo "🧪 运行认证测试..."
if [ -d "tests/auth" ]; then
    python3 -m pytest tests/auth/ -v --tb=short
    echo "✅ 认证测试完成"
else
    echo "ℹ️  跳过：tests/auth/ 目录不存在 (阶段 3 开发后创建)"
fi
echo ""

echo "=========================================="
echo "  ✅ 阶段 3 环境设置完成!"
echo "=========================================="
echo ""
echo "下一步:"
echo "  1. 阅读开发清单：docs/04-Technical-Docs/stage3-dev-checklist.md"
echo "  2. 阅读准备报告：reports/STAGE3-PREPARE-20260327.md"
echo "  3. 开始阶段 3 开发：2026-05-20"
echo ""
