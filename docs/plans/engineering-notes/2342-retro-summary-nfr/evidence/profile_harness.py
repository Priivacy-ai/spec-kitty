"""Profiling harness for `build_summary` over the test's 200-mission corpus (#2342).

Rebuilds the exact same 200-mission corpus content as the
`large_corpus` fixture in `tests/retrospective/test_summary_tolerance.py`
(reusing that module's `_make_completed_yaml` template, per C-004 / the
"reuse the corpus fixture" constraint) without depending on pytest's fixture
machinery, so it can run as a standalone script during profiling/bisection.

Runs `cProfile` over `build_summary(project_path=corpus)` for N repeated
local runs (default 7, i.e. >=5 per NFR-001), then reports:
  - median + min-max wall-time spread across runs
  - a per-phase breakdown (filesystem scan / YAML parse / schema
    coerce+validate / reduce) aggregated from the *last* run's pstats,
    by attributing each profiled function's *tottime* (self time, so costs
    are not double-counted across nested calls) to one of the four phases
    by (filename, function-name) pattern match.

Usage:
    PYTHONPATH=<repo>/src <venv-python> profile_harness.py [N_RUNS]

Output: prints a human-readable table to stdout. Redirect to
`evidence/profiling.txt` to capture the raw record for the report.
"""

from __future__ import annotations

import cProfile
import io
import pstats
import statistics
import sys
import tempfile
import time
from pathlib import Path

# Make the worktree's own `tests` and `src` packages importable regardless of
# cwd — this script is invoked with PYTHONPATH=<worktree>/src pointed at the
# retrospective package under study, but the test-helper reuse below needs
# the repo root (parent of `src`) on sys.path too.
_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.retrospective.test_summary_tolerance import _make_completed_yaml  # noqa: E402

from specify_cli.retrospective.summary import build_summary  # noqa: E402

DEFAULT_RUNS = 7
CORPUS_SIZE = 200


def build_corpus(root: Path) -> Path:
    """Rebuild the exact 200-mission corpus the quarantined test builds.

    Mirrors `large_corpus()` in test_summary_tolerance.py verbatim (same
    mission-id derivation, same per-mission YAML template) so profiling
    numbers are directly about the real workload, not a stand-in.
    """
    missions_root = root / ".kittify" / "missions"
    missions_root.mkdir(parents=True, exist_ok=True)

    safe_chars = "ABCDEFGHJKMNPQRSTVWXYZ0123456789"
    for i in range(CORPUS_SIZE):
        mid = f"01KQ6YEGT4YBZ3GZF7X{i:07d}"[:26]
        mid_safe = "".join(c if c in safe_chars else "A" for c in mid.upper())
        mid_safe = mid_safe[:26]
        if len(mid_safe) < 26:
            mid_safe = mid_safe + "A" * (26 - len(mid_safe))

        mission_dir = missions_root / mid_safe
        mission_dir.mkdir(exist_ok=True)
        (mission_dir / "retrospective.yaml").write_text(
            _make_completed_yaml(
                mission_id=mid_safe,
                slug=f"perf-mission-{i:04d}",
                not_helpful_urn=f"glossary:term:item{i % 50:02d}",
                gaps_urn=f"glossary:term:gap{i % 20:02d}",
            ),
            encoding="utf-8",
        )
    return root


# ---------------------------------------------------------------------------
# Per-phase attribution of pstats entries
# ---------------------------------------------------------------------------

_FS_SCAN_MARKERS = ("_iter_mission_dirs", "_resolve_summary_record_path", "scandir", "iterdir", "stat", "exists")
_YAML_PARSE_MARKERS = ("_load_yaml_mapping", "ruamel", "reader.py")
_VALIDATE_MARKERS = ("_coerce_legacy_schema_versions", "model_validate", "pydantic", "schema.py", "read_record")
_PHASES = ("fs_scan", "yaml_parse", "schema_validate", "reduce_other")


def classify(filename: str, funcname: str) -> str:
    """Attribute one profiled function's self-time to a report phase.

    Order matters: check the most specific reader.py/schema.py markers
    before the generic fs-scan markers, since some helper names could
    otherwise collide.
    """
    haystack = f"{filename}:{funcname}"
    if any(m in haystack for m in _VALIDATE_MARKERS):
        return "schema_validate"
    if any(m in haystack for m in _YAML_PARSE_MARKERS):
        return "yaml_parse"
    if any(m in haystack for m in _FS_SCAN_MARKERS):
        return "fs_scan"
    return "reduce_other"


def phase_breakdown(profile: cProfile.Profile) -> dict[str, float]:
    stats = pstats.Stats(profile)
    totals = dict.fromkeys(_PHASES, 0.0)
    for (filename, _lineno, funcname), (_cc, _nc, tottime, _ct, _callers) in stats.stats.items():  # type: ignore[attr-defined]
        phase = classify(filename, funcname)
        totals[phase] += tottime
    return totals


def run_unprofiled(corpus: Path) -> float:
    """Real (uninstrumented) wall-time for one `build_summary` call.

    This is the number that matters for NFR-001/the 5.0s budget — `cProfile`
    instrumentation overhead (function-call tracing) measurably inflates
    elapsed time and must not be reported as the wall-time reading.
    """
    start = time.monotonic()
    snapshot = build_summary(project_path=corpus)
    elapsed = time.monotonic() - start
    assert snapshot.mission_count == CORPUS_SIZE
    return elapsed


def run_profiled(corpus: Path) -> tuple[float, cProfile.Profile]:
    """One instrumented run, for per-phase *relative* attribution only.

    The absolute elapsed time under cProfile is NOT comparable to the
    budget or to `run_unprofiled` — only the relative phase percentages are.
    """
    profile = cProfile.Profile()
    start = time.monotonic()
    profile.enable()
    snapshot = build_summary(project_path=corpus)
    profile.disable()
    elapsed = time.monotonic() - start
    assert snapshot.mission_count == CORPUS_SIZE
    return elapsed, profile


def main(argv: list[str]) -> int:
    n_runs = int(argv[1]) if len(argv) > 1 else DEFAULT_RUNS
    if n_runs < 5:
        raise SystemExit("NFR-001 requires >=5 repeated runs")

    with tempfile.TemporaryDirectory(prefix="retro-summary-perf-") as tmp:
        corpus = build_corpus(Path(tmp))

        print(f"-- {n_runs} unprofiled (real wall-time) runs --")
        elapsed_times: list[float] = []
        for run_idx in range(n_runs):
            elapsed = run_unprofiled(corpus)
            elapsed_times.append(elapsed)
            print(f"run {run_idx + 1}/{n_runs}: {elapsed:.4f}s")

        print()
        print("-- 1 profiled run (cProfile instrumentation inflates elapsed"
              " time; use only for the per-phase relative breakdown) --")
        profiled_elapsed, last_profile = run_profiled(corpus)
        print(f"profiled run elapsed (inflated): {profiled_elapsed:.4f}s")

    median = statistics.median(elapsed_times)
    lo, hi = min(elapsed_times), max(elapsed_times)
    print()
    print(f"N runs           : {n_runs}")
    print(f"median wall-time : {median:.4f}s")
    print(f"min-max spread   : {lo:.4f}s - {hi:.4f}s")
    print(f"all readings     : {[f'{t:.4f}' for t in elapsed_times]}")

    totals = phase_breakdown(last_profile)
    grand_total = sum(totals.values()) or 1.0
    print()
    print("Per-phase self-time breakdown (last run, cProfile tottime):")
    for phase in _PHASES:
        pct = 100.0 * totals[phase] / grand_total
        print(f"  {phase:16s}: {totals[phase]:.4f}s ({pct:5.1f}%)")

    print()
    print("Top 20 functions by cumulative time (last run):")
    buf = io.StringIO()
    stats = pstats.Stats(last_profile, stream=buf)
    stats.sort_stats("cumulative")
    stats.print_stats(20)
    print(buf.getvalue())

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
