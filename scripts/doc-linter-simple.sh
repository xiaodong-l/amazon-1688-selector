#!/bin/bash
# 📋 文档 Linter 脚本 - 简化版
# 用途：验证文档结构、命名、新鲜度

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="$PROJECT_ROOT/docs"

echo "📋 文档 Linter v1.0"
echo "===================="
echo ""

TOTAL=0
PASSED=0
FAILED=0

# 检查 1: 文件命名 (kebab-case)
echo "检查 1: 文件命名规范"
for file in $(find "$DOCS_DIR" -name "*.md" -type f 2>/dev/null); do
    filename=$(basename "$file")
    if [[ "$filename" =~ ^[a-z0-9]+(-[a-z0-9]+)*\.md$ ]]; then
        echo "  ✓ $filename"
        ((PASSED++))
    else
        echo "  ✗ $filename (不符合 kebab-case)"
        ((FAILED++))
    fi
    ((TOTAL++))
done

# 检查 2: 目录结构
echo ""
echo "检查 2: 目录结构"
for dir in docs/01-Getting-Started docs/02-User-Guide docs/03-Developer-Guide docs/04-Technical-Docs docs/05-Project-Docs docs/06-Internal-Docs; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        echo "  ✓ $dir"
        ((PASSED++))
    else
        echo "  ✗ $dir (不存在)"
        ((FAILED++))
    fi
    ((TOTAL++))
done

# 检查 3: README 存在性
echo ""
echo "检查 3: README 存在性"
if [ -f "$DOCS_DIR/README.md" ]; then
    echo "  ✓ docs/README.md"
    ((PASSED++))
else
    echo "  ✗ docs/README.md (不存在)"
    ((FAILED++))
fi
((TOTAL++))

if [ -f "$PROJECT_ROOT/README.md" ]; then
    echo "  ✓ 根目录 README.md"
    ((PASSED++))
else
    echo "  ✗ 根目录 README.md (不存在)"
    ((FAILED++))
fi
((TOTAL++))

# 摘要
echo ""
echo "===================="
echo "总计：$TOTAL | 通过：$PASSED | 失败：$FAILED"

if [ $FAILED -gt 0 ]; then
    echo "❌ 检查未通过"
    exit 1
else
    echo "✅ 检查全部通过!"
    exit 0
fi
