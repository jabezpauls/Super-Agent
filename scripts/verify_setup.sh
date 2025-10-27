#!/bin/bash
# Verification script for browser_agent directory
# Run this to ensure everything is properly set up

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     Browser Agent - Setup Verification                          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success=0
failures=0

check_file() {
	if [ -f "$1" ]; then
		echo -e "${GREEN}✓${NC} Found: $1"
		((success++))
	else
		echo -e "${RED}✗${NC} Missing: $1"
		((failures++))
	fi
}

check_dir() {
	if [ -d "$1" ]; then
		echo -e "${GREEN}✓${NC} Found: $1/"
		((success++))
	else
		echo -e "${RED}✗${NC} Missing: $1/"
		((failures++))
	fi
}

echo "Checking core application files..."
check_file "browser_use_repl.py"
check_file "browser_use_interactive.py"
check_dir "browser_use"

echo ""
echo "Checking dependency files..."
check_file "pyproject.toml"
check_file "uv.lock"

echo ""
echo "Checking Docker files..."
check_file "Dockerfile.repl"
check_file "docker-compose.yml"
check_file "docker-quick-start.sh"

echo ""
echo "Checking documentation..."
check_file "README.md"
check_file "REPL_CLI_README.md"
check_file "REPL_QUICK_START.md"
check_file "REPL_TROUBLESHOOTING.md"
check_file "REPL_PROMPTING_TIPS.md"
check_file "UNDERSTANDING_AGENT_BEHAVIOR.md"
check_file "MODEL_RECOMMENDATIONS.md"
check_file "MODELS_QUICK_GUIDE.md"
check_file "DOCKER_SETUP.md"
check_file "DOCKER_README.md"

echo ""
echo "Checking helper scripts..."
check_file "setup_better_model.sh"
check_file "demo_repl.sh"

echo ""
echo "Checking executability..."
if [ -x "docker-quick-start.sh" ]; then
	echo -e "${GREEN}✓${NC} docker-quick-start.sh is executable"
	((success++))
else
	echo -e "${YELLOW}⚠${NC} docker-quick-start.sh is not executable (run: chmod +x docker-quick-start.sh)"
fi

if [ -x "setup_better_model.sh" ]; then
	echo -e "${GREEN}✓${NC} setup_better_model.sh is executable"
	((success++))
else
	echo -e "${YELLOW}⚠${NC} setup_better_model.sh is not executable (run: chmod +x setup_better_model.sh)"
fi

if [ -x "demo_repl.sh" ]; then
	echo -e "${GREEN}✓${NC} demo_repl.sh is executable"
	((success++))
else
	echo -e "${YELLOW}⚠${NC} demo_repl.sh is not executable (run: chmod +x demo_repl.sh)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Results:"
echo -e "  ${GREEN}✓ Success: $success${NC}"
if [ $failures -gt 0 ]; then
	echo -e "  ${RED}✗ Failures: $failures${NC}"
else
	echo -e "  ${GREEN}✗ Failures: 0${NC}"
fi

echo ""
if [ $failures -eq 0 ]; then
	echo -e "${GREEN}✅ All checks passed! Your browser_agent directory is ready.${NC}"
	echo ""
	echo "Next steps:"
	echo "  1. Read README.md for usage instructions"
	echo "  2. Run: cat README.md"
	echo "  3. Or start immediately: python browser_use_repl.py --help"
else
	echo -e "${RED}❌ Some files are missing. Please check the errors above.${NC}"
	exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                   Verification Complete                         ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
