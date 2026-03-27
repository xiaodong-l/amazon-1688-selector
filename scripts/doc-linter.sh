#!/bin/bash
# 📋 文档 Linter 脚本
# 用途：验证文档结构、命名、新鲜度、黄金原则合规
# 版本：v1.0
# 最后更新：2026-03-27

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 统计
TOTAL=0
PASSED=0
FAILED=0
WARNINGS=0

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="$PROJECT_ROOT/docs"
REPORTS_DIR="$PROJECT_ROOT/reports"

# 打印函数
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}\n"
}

print_check() {
    echo -e "  ${YELLOW}CHECK${NC} $1"
}

print_pass() {
    echo -e "  ${GREEN}✓ PASS${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "  ${RED}✗ FAIL${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "  ${YELLOW}⚠ WARN${NC} $1"
    ((WARNINGS++))
}

print_info() {
    echo -e "  ${BLUE}ℹ INFO${NC} $1"
}

# 检查 1: 文件命名规范 (GP-007)
check_naming_convention() {
    print_header "检查 1: 文件命名规范 (GP-007)"
    
    local files=$(find "$DOCS_DIR" "$REPORTS_DIR" -name "*.md" -type f 2>/dev/null)
    
    for file in $files; do
        ((TOTAL++))
        local filename=$(basename "$file")
        
        # 检查 kebab-case
        if [[ ! "$filename" =~ ^[a-z0-9]+(-[a-z0-9]+)*\.md$ ]]; then
            print_fail "$file - 命名不符合 kebab-case"
        else
            print_pass "$filename"
        fi
    done
}

# 检查 2: 目录结构完整性
check_directory_structure() {
    print_header "检查 2: 目录结构完整性"
    
    local dirs=(
        "docs/01-Getting-Started"
        "docs/02-User-Guide"
        "docs/03-Developer-Guide"
        "docs/04-Technical-Docs"
        "docs/05-Project-Docs"
        "docs/06-Internal-Docs"
        "reports/development"
        "reports/deployment"
        "reports/optimization"
        "context/plans/active"
    )
    
    for dir in "${dirs[@]}"; do
        ((TOTAL++))
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            print_pass "$dir"
        else
            print_fail "$dir - 目录不存在"
        fi
    done
}

# 检查 3: 文档元数据 (GP-006)
check_doc_metadata() {
    print_header "检查 3: 文档元数据 (GP-006)"
    
    local files=$(find "$DOCS_DIR" -name "*.md" -type f 2>/dev/null | head -20)
    
    for file in $files; do
        ((TOTAL++))
        local filename=$(basename "$file")
        
        # 检查是否包含最后更新日期
        if grep -q "\*\*最后更新\*\*:" "$file" 2>/dev/null; then
            print_pass "$filename - 包含更新日期"
        else
            print_warn "$filename - 缺少更新日期"
        fi
        
        # 检查是否包含版本
        if grep -q "\*\*版本\*\*:" "$file" 2>/dev/null; then
            : # 静默通过
        else
            print_warn "$filename - 缺少版本信息"
        fi
    done
}

# 检查 4: 文档新鲜度 (GP-006)
check_doc_freshness() {
    print_header "检查 4: 文档新鲜度 (GP-006)"
    
    local current_date=$(date +%s)
    local thirty_days_ago=$((current_date - 30*24*60*60))
    local ninety_days_ago=$((current_date - 90*24*60*60))
    
    local files=$(find "$DOCS_DIR" "$REPORTS_DIR" -name "*.md" -type f 2>/dev/null)
    
    for file in $files; do
        ((TOTAL++))
        local filename=$(basename "$file")
        local file_date=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null)
        local days_old=$(( (current_date - file_date) / 86400 ))
        
        if [ $days_old -gt 90 ]; then
            print_warn "$filename - 文档已过期 ($days_old 天)"
        elif [ $days_old -gt 30 ]; then
            print_info "$filename - 文档较旧 ($days_old 天)"
        else
            print_pass "$filename - 文档新鲜 ($days_old 天)"
        fi
    done
}

# 检查 5: 链接有效性
check_links() {
    print_header "检查 5: 链接有效性"
    
    local files=$(find "$DOCS_DIR" -name "*.md" -type f 2>/dev/null | head -10)
    
    for file in $files; do
        ((TOTAL++))
        local filename=$(basename "$file")
        
        # 提取相对链接
        local links=$(grep -oE '\]\(\./[^)]+\)' "$file" 2>/dev/null | sed 's/](/ /g' | sed 's/)//g')
        
        for link in $links; do
            local target_file="$(dirname "$file")/$link"
            if [ -f "$target_file" ]; then
                : # 静默通过
            else
                print_warn "$filename - 链接不存在：$link"
            fi
        done
    done
    
    print_info "链接检查完成 (仅检查相对链接)"
}

# 检查 6: 执行计划存在性 (GP-004)
check_exec_plans() {
    print_header "检查 6: 执行计划存在性 (GP-004)"
    
    ((TOTAL++))
    if [ -d "$PROJECT_ROOT/context/plans/active" ]; then
        local plans=$(ls -1 "$PROJECT_ROOT/context/plans/active"/*.md 2>/dev/null | wc -l)
        if [ $plans -gt 0 ]; then
            print_pass "发现 $plans 个活跃执行计划"
        else
            print_warn "无活跃执行计划"
        fi
    else
        print_fail "context/plans/active 目录不存在"
    fi
}

# 检查 7: README 存在性
check_readme_exists() {
    print_header "检查 7: README 存在性"
    
    ((TOTAL++))
    if [ -f "$DOCS_DIR/README.md" ]; then
        print_pass "docs/README.md 存在"
    else
        print_fail "docs/README.md 不存在"
    fi
    
    ((TOTAL++))
    if [ -f "$PROJECT_ROOT/README.md" ]; then
        print_pass "根目录 README.md 存在"
    else
        print_fail "根目录 README.md 不存在"
    fi
}

# 打印摘要
print_summary() {
    print_header "检查摘要"
    
    echo -e "  总检查数：${BLUE}$TOTAL${NC}"
    echo -e "  通过：${GREEN}$PASSED${NC}"
    echo -e "  失败：${RED}$FAILED${NC}"
    echo -e "  警告：${YELLOW}$WARNINGS${NC}"
    echo ""
    
    local pass_rate=0
    if [ $TOTAL -gt 0 ]; then
        pass_rate=$((PASSED * 100 / TOTAL))
    fi
    
    echo -e "  通过率：${BLUE}${pass_rate}%${NC}"
    echo ""
    
    if [ $FAILED -gt 0 ]; then
        echo -e "  ${RED}❌ 检查未通过 - 存在 $FAILED 个失败项${NC}"
        exit 1
    elif [ $WARNINGS -gt 0 ]; then
        echo -e "  ${YELLOW}⚠️  检查通过 - 存在 $WARNINGS 个警告${NC}"
        exit 0
    else
        echo -e "  ${GREEN}✅ 检查全部通过!${NC}"
        exit 0
    fi
}

# 主函数
main() {
    print_header "📋 文档 Linter v1.0"
    print_info "项目根目录：$PROJECT_ROOT"
    print_info "文档目录：$DOCS_DIR"
    print_info "报告目录：$REPORTS_DIR"
    
    check_naming_convention
    check_directory_structure
    check_doc_metadata
    check_doc_freshness
    check_links
    check_exec_plans
    check_readme_exists
    
    print_summary
}

# 运行
main "$@"
