#!/usr/bin/env python3
"""Check tiered coverage thresholds.

Reads tier configuration from [tool.coverage_tiers] in pyproject.toml and
validates that each tier meets its minimum coverage threshold against the
.coverage data file produced by a preceding `pytest --cov` run.

Usage (from repo root):
    python scripts/check_coverage.py

The script exits 0 if all thresholds are met, 1 otherwise.
Tiers with min_coverage = 0 are reported but never fail the build.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _check_tier(name: str, include_patterns: list[str], min_coverage: int) -> bool:
    """Run coverage report for one tier. Return True if threshold is met."""
    if min_coverage == 0:
        print(f"  skip  {name:<12}  threshold: 0% (not enforced)")
        return True

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "report",
            *[f"--include={p}" for p in include_patterns],
            f"--fail-under={min_coverage}",
            "--skip-empty",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    # Extract the TOTAL line to report the actual percentage.
    total = "?"
    for line in result.stdout.splitlines():
        if line.startswith("TOTAL"):
            parts = line.split()
            total = parts[-1]  # e.g. "78%"

    if result.returncode == 0:
        print(f"  pass  {name:<12}  {total} >= {min_coverage}%")
        return True

    print(f"  FAIL  {name:<12}  {total} < {min_coverage}% required")
    # Print the full report so the developer knows exactly which files are under-covered.
    if result.stdout:
        print()
        for line in result.stdout.splitlines():
            print(f"    {line}")
        print()
    return False


def main() -> int:
    coverage_data = REPO_ROOT / ".coverage"
    if not coverage_data.exists():
        print("error: .coverage not found -- run `pytest --cov` first")
        return 1

    pyproject = REPO_ROOT / "pyproject.toml"
    with pyproject.open("rb") as fh:
        config = tomllib.load(fh)

    tiers: dict[str, dict[str, object]] = config.get("tool", {}).get("coverage_tiers", {})
    if not tiers:
        print("error: no [tool.coverage_tiers] section in pyproject.toml")
        return 1

    print("Coverage tier check")
    print("-" * 44)

    failures: list[str] = []
    for tier_name, tier_config in tiers.items():
        min_coverage = int(tier_config.get("min_coverage", 0))  # type: ignore[arg-type]
        include_patterns = list(tier_config.get("include", []))  # type: ignore[arg-type]
        if not _check_tier(tier_name, include_patterns, min_coverage):
            failures.append(tier_name)

    print("-" * 44)
    if failures:
        print(f"Failed: {', '.join(failures)}")
        return 1

    print("All tiers passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
