#!/bin/bash
# Run the full CI test suite locally. Pass all tests before pushing.
#
# Usage: ./scripts/test_local.sh [--lint] [--coverage]
#
# Requires the package to be installed: pip install -e ".[dev]"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== tkgis local test suite ==="
echo "Project root: $PROJECT_ROOT"
echo "Python: $(python --version 2>&1)"
echo ""

# Lint (if requested)
if [[ "${1:-}" == "--lint" ]] || [[ "${2:-}" == "--lint" ]]; then
    echo "--- ruff lint ---"
    python -m ruff check src/ tests/
    echo "OK: ruff passed"
    echo ""
fi

# Determine coverage flags
COV_FLAGS=""
if [[ "${1:-}" == "--coverage" ]] || [[ "${2:-}" == "--coverage" ]]; then
    COV_FLAGS="--cov=tkgis --cov-report=term-missing"
fi

# Run tests
echo "--- pytest ---"
python -m pytest tests/ -x -q --tb=short $COV_FLAGS

echo ""
echo "=== ALL PASSED ==="
