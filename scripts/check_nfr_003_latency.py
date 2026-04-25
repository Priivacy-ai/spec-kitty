#!/usr/bin/env python3
"""CI gate for NFR-003 of mission shared-package-boundary-cutover-01KQ22DS.

Runs ``spec-kitty next --agent test --mission clean-install-fixture-01KQ22XX --json``
N times against the bundled clean-install fixture and compares the median
wall-clock time against the pinned pre-cutover baseline stored in
``kitty-specs/shared-package-boundary-cutover-01KQ22DS/nfr-003-baseline.json``.

Exits non-zero if the current median exceeds the baseline by more than the
configured tolerance (default 20%).

Run from a repo checkout where ``spec-kitty`` is installed (editable or
wheel) into the active Python:

    python scripts/check_nfr_003_latency.py

Or as a CI step:

    - name: NFR-003 latency gate
      run: python scripts/check_nfr_003_latency.py
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = (
    REPO_ROOT
    / "kitty-specs"
    / "shared-package-boundary-cutover-01KQ22DS"
    / "nfr-003-baseline.json"
)
DEFAULT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "clean_install_fixture_mission"


def measure(
    python_exe: str,
    fixture_dir: Path,
    runs: int,
    mission: str,
) -> list[float]:
    """Run spec-kitty next ``runs`` times and return per-run wall-clock seconds."""
    times: list[float] = []
    for i in range(runs):
        t0 = time.perf_counter()
        proc = subprocess.run(
            [
                python_exe,
                "-m",
                "specify_cli",
                "next",
                "--agent",
                "test",
                "--mission",
                mission,
                "--json",
            ],
            cwd=str(fixture_dir),
            capture_output=True,
        )
        dt = time.perf_counter() - t0
        if proc.returncode != 0:
            sys.stderr.write(
                f"NFR-003 gate: subprocess returned {proc.returncode} on run {i + 1}\n"
            )
            sys.stderr.write(
                proc.stderr.decode("utf-8", errors="replace") or "<no stderr>"
            )
            sys.stderr.write("\n")
            sys.exit(2)
        times.append(dt)
    return times


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs", type=int, default=5, help="Number of measurement runs (default: 5)"
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Path to the clean-install fixture",
    )
    parser.add_argument(
        "--mission",
        default="clean-install-fixture-01KQ22XX",
        help="Mission slug to drive in --mission",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to invoke `python -m specify_cli` with",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE_PATH,
        help="Path to the pinned baseline JSON",
    )
    parser.add_argument(
        "--tolerance-pct",
        type=float,
        default=None,
        help="Override tolerance percentage (else read from baseline)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print measurements but do not exit non-zero on regression",
    )
    args = parser.parse_args(argv)

    if not args.baseline.exists():
        sys.stderr.write(f"NFR-003 gate: baseline file missing at {args.baseline}\n")
        return 2

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    pre_median = float(baseline["pre_cutover_median_seconds"])
    tolerance = (
        float(args.tolerance_pct)
        if args.tolerance_pct is not None
        else float(baseline.get("tolerance_pct", 20.0))
    )
    ceiling = pre_median * (1.0 + tolerance / 100.0)

    if not args.fixture.exists():
        sys.stderr.write(f"NFR-003 gate: fixture missing at {args.fixture}\n")
        return 2

    times = measure(args.python, args.fixture, args.runs, args.mission)
    median = statistics.median(times)
    delta_pct = (median - pre_median) / pre_median * 100.0

    print(f"NFR-003 latency gate report")
    print(f"  pre_cutover_median: {pre_median:.3f}s ({pre_median * 1000:.0f}ms)")
    print(
        f"  post_cutover_median: {median:.3f}s ({median * 1000:.0f}ms)  "
        f"(n={args.runs}, runs={[f'{t:.3f}' for t in times]})"
    )
    print(f"  delta: {delta_pct:+.1f}% (ceiling: <={tolerance:.1f}%)")
    print(f"  ceiling_seconds: {ceiling:.3f}s")

    if median <= ceiling:
        print("  verdict: PASS")
        return 0

    print("  verdict: FAIL")
    if args.report_only:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
