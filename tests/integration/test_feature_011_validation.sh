#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$REPO_ROOT"

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

run_test() {
  local name="$1"
  local cmd="$2"

  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  echo ""
  echo "────────────────────────────────────────────"
  echo "Test $TOTAL_TESTS: $name"
  echo "────────────────────────────────────────────"

  if eval "$cmd" > /tmp/test_output.log 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    tail -10 /tmp/test_output.log
  else
    echo -e "${RED}✗ FAILED${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    tail -20 /tmp/test_output.log
  fi
}

echo "=============================================="
echo "Feature 011: Integration Test Suite"
echo "Constitution Packaging Safety and Redesign"
echo "=============================================="

if python3 -m build --help >/dev/null 2>&1; then
  echo "Building package..."
  python3 -m build
else
  echo -e "${YELLOW}SKIP: python -m build not available${NC}"
fi

run_test "Package Inspection (SC-001, SC-002)" \
  "python3 -m pytest tests/test_packaging_safety.py -v"

run_test "Upgrade Path 0.6.4->0.10.12 (SC-005, SC-008)" \
  "tests/integration/test_upgrade_path.sh"

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
  run_test "Windows Dashboard (SC-004)" \
    "pwsh tests/integration/test_dashboard_windows.ps1"
else
  echo ""
  echo "────────────────────────────────────────────"
  echo "Test: Windows Dashboard (SC-004)"
  echo "────────────────────────────────────────────"
  echo -e "${YELLOW}⊘ SKIPPED (not on Windows)${NC}"
fi

run_test "Constitution Minimal Path (SC-006)" \
  "tests/integration/test_constitution_minimal.sh"

run_test "Constitution Comprehensive Path (SC-007)" \
  "tests/integration/test_constitution_comprehensive.sh"

run_test "Commands Without Constitution (SC-003)" \
  "tests/integration/test_commands_without_constitution.sh"

run_test "Dogfooding Safety (SC-001)" \
  "tests/integration/test_dogfooding_safety.sh"

echo ""
echo "=============================================="
echo "INTEGRATION TEST RESULTS"
echo "=============================================="
echo ""
echo "Total Tests:  $TOTAL_TESTS"
echo -e "${GREEN}Passed:       $PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
  echo -e "${RED}Failed:       $FAILED_TESTS${NC}"
else
  echo "Failed:       $FAILED_TESTS"
fi

echo ""
if [ $FAILED_TESTS -eq 0 ]; then
  echo -e "${GREEN}✓ ALL AUTOMATED TESTS PASSED${NC}"
  echo ""
  echo "Manual tests still required:"
  echo "  - Windows dashboard (SC-004) on Windows 10/11"
  echo "  - Constitution timing (SC-006, SC-007) during manual testing"
  exit 0
else
  echo -e "${RED}✗ SOME TESTS FAILED${NC}"
  exit 1
fi
