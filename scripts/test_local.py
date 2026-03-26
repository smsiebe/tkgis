#!/usr/bin/env python
"""Run the same test suite locally that CI runs on push.

Usage:
    python scripts/test_local.py [--lint] [--coverage]

Options:
    --lint       Run ruff lint check before tests.
    --coverage   Enable pytest-cov coverage reporting.
"""
from __future__ import annotations

import argparse
import importlib
import subprocess
import sys


MIN_PYTHON = (3, 11)

REQUIRED_PACKAGES = [
    "tkinter",
    "customtkinter",
    "ttkbootstrap",
    "geopandas",
    "pyproj",
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
    "pydantic",
    "yaml",
    "shapely",
    "PIL",
]

OPTIONAL_PACKAGES = [
    "grdl",
    "grdl_rt",
    "rasterio",
    "pyogrio",
]


def check_python_version() -> bool:
    """Return True if the running Python meets the minimum version."""
    if sys.version_info[:2] < MIN_PYTHON:
        print(
            f"FAIL: Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} required, "
            f"got {sys.version_info[0]}.{sys.version_info[1]}"
        )
        return False
    print(f"OK: Python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")
    return True


def check_imports() -> bool:
    """Verify that required packages are importable."""
    ok = True
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            print(f"  OK: {pkg}")
        except ImportError:
            print(f"  MISSING: {pkg}")
            ok = False

    for pkg in OPTIONAL_PACKAGES:
        try:
            importlib.import_module(pkg)
            print(f"  OK: {pkg}")
        except ImportError:
            print(f"  WARN (optional): {pkg}")

    return ok


def run_lint() -> int:
    """Run ruff lint check and return the exit code."""
    print("\n--- ruff lint ---")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/", "tests/"],
        cwd=_project_root(),
    )
    return result.returncode


def run_tests(*, coverage: bool = False) -> int:
    """Run pytest with the same flags as CI and return the exit code."""
    print("\n--- pytest ---")
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-x", "-q", "--tb=short",
    ]
    if coverage:
        cmd += ["--cov=tkgis", "--cov-report=term-missing"]

    result = subprocess.run(cmd, cwd=_project_root())
    return result.returncode


def _project_root() -> str:
    """Return the project root directory."""
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lint", action="store_true", help="Run ruff lint check")
    parser.add_argument("--coverage", action="store_true", help="Enable coverage reporting")
    args = parser.parse_args()

    print("=== tkgis local test runner ===\n")

    # 1. Python version
    if not check_python_version():
        sys.exit(1)

    # 2. Import checks
    print("\nChecking required packages:")
    if not check_imports():
        print("\nFAIL: Missing required packages. Install with: pip install -e \".[dev]\"")
        sys.exit(1)

    # 3. Lint (optional)
    if args.lint:
        rc = run_lint()
        if rc != 0:
            print("\nFAIL: ruff reported lint errors.")
            sys.exit(rc)
        print("OK: ruff passed")

    # 4. Tests
    rc = run_tests(coverage=args.coverage)

    # 5. Summary
    print("\n=== Summary ===")
    if rc == 0:
        print("ALL PASSED")
    else:
        print(f"TESTS FAILED (exit code {rc})")

    sys.exit(rc)


if __name__ == "__main__":
    main()
