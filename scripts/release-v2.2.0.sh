#!/bin/bash
# Amazon-1688-Selector v2.2.0 Release Script
# Release: Data Persistence & Security

set -e

echo "🚀 Amazon-1688-Selector v2.2.0 Release Script"
echo "=============================================="
echo ""

# Configuration
VERSION="v2.2.0"
RELEASE_TITLE="v2.2.0 - Data Persistence & Security"
BRANCH="master"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check we're in the right directory
if [ ! -f "README.md" ]; then
    echo -e "${RED}Error: Please run this script from the project root${NC}"
    exit 1
fi

# Check we're on master branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo -e "${YELLOW}Warning: Currently on $CURRENT_BRANCH branch${NC}"
    echo -e "${YELLOW}Switching to $BRANCH branch...${NC}"
    git checkout $BRANCH
fi

# Step 1: Stage all changes
echo ""
echo "📦 Step 1: Staging changes..."
git add -A
echo -e "${GREEN}✓ All changes staged${NC}"

# Step 2: Commit changes
echo ""
echo "📝 Step 2: Creating release commit..."
git commit -m "release: v2.2.0 - Data Persistence & Security

- Complete database persistence layer with async support
- Implement history tracking (product, price, BSR)
- Add soft delete functionality
- API v2 endpoints for products and history
- Performance optimizations and benchmarks
- Comprehensive test suite (130 failed, 221 passed)
- Code quality improvements (flake8, mypy, pylint)

Release Date: $(date -u +%Y-%m-%d)
"
echo -e "${GREEN}✓ Release commit created${NC}"

# Step 3: Create git tag
echo ""
echo "🏷️  Step 3: Creating git tag..."
git tag -a $VERSION -m "Release $VERSION - Data Persistence & Security

Key Features:
- Database persistence with SQLite + async SQLAlchemy
- History tracking for products, prices, and BSR
- Soft delete support
- RESTful API v2
- Performance benchmarking suite

Test Results: 221 passed, 130 failed (known issues documented)
"
echo -e "${GREEN}✓ Git tag $VERSION created${NC}"

# Step 4: Push to remote
echo ""
echo "📤 Step 4: Pushing to remote..."
git push origin $BRANCH
git push origin $VERSION
echo -e "${GREEN}✓ Changes and tag pushed to remote${NC}"

echo ""
echo "=============================================="
echo -e "${GREEN}✓ Release script completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Create GitHub Release: gh release create $VERSION ..."
echo "2. Verify release on GitHub"
echo "3. Update release completion report"
echo ""
