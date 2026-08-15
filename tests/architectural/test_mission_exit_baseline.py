"""WP17 -- mission-exit verification (NFR-001 / SC-009).

Mission ``review-cycle-verdict-seam-rebuild-01KZ2W7W``. NFR-001 pins the
affected-suites node-id set as a **floor**: it may grow (new tests are
welcome), it may never shrink by any of the prohibited methods spec.md's
NFR-001 row enumerates verbatim -- re-running, a skip/xfail/quarantine
marker, widening a threshold without a recorded investigation, deleting an
assertion, deleting the test, moving it out of the affected-suites paths,
reducing its parametrization, narrowing an assertion, or excluding it at
collection or marker-selection level. A node-id disappearing is a violation
regardless of *why* it disappeared.

``tests/architectural/mission_exit_baseline.txt`` is the committed floor:
the full ``--collect-only`` node-id set (2877 entries, measured 2026-08-05)
for the EXACT affected-suites invocation named in quickstart.md's "Before
anything: the baseline" section and
``research/baseline-8466727eb.md``'s "Invocation" section. This module makes
the "floor may grow, never shrink" rule **executable**: it re-collects the
identical invocation and asserts every committed node-id is still present,
so a shrink fails mechanically without requiring a human diff.

It additionally pins, by name, the two node-ids the pre-mission baseline
(measured at merge-base ``8466727eb``) recorded as the ONLY reproducing
failures -- #3157 and #3160 -- as distinct, separately-run entries (not
folded anonymously into the bulk floor check), so a reviewer can see
individually whether each is still red or now green.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

_BASELINE_PATH = Path(__file__).with_name("mission_exit_baseline.txt")
_REPO_ROOT = Path(__file__).resolve().parents[2]

# The EXACT path list from quickstart.md's "Before anything: the baseline"
# section / research/baseline-8466727eb.md's "Invocation" section -- never a
# paraphrase, narrower, or wider substitute.
#
# 2026-08-06 landing-fold path update: the third entry below moved from
# tests/regression/test_2646_stale_verdict_closes_via_fr001.py to
# tests/integration/test_2646_stale_verdict_closes_via_fr001.py once #2646
# closed and this file exited tests/regression/'s red-first-only suite
# (same file, same two tests -- see mission_exit_baseline.txt's matching
# note). The collected node-id SET is unchanged; only the path prefix is.
_AFFECTED_SUITE_PATHS: tuple[str, ...] = (
    "tests/review/",
    "tests/status/",
    "tests/integration/test_2646_stale_verdict_closes_via_fr001.py",
    "tests/integration/test_review_cycle_rejection_only.py",
    "tests/integration/test_ac5_hash_guard.py",
    "tests/integration/test_wp_file_hash_stability.py",
    "tests/post_merge/test_review_artifact_consistency.py",
    "tests/specify_cli/cli/commands/agent/",
)

# The two node-ids research/baseline-8466727eb.md names as reproducing at
# the merge-base 8466727eb -- pinned verbatim, matched against
# mission_exit_baseline.txt in test_known_baseline_pins_are_in_the_floor.
_ISSUE_3157_NODE_ID = (
    "tests/status/test_work_package_lifecycle.py::"
    "test_real_implement_and_review_claims_persist_structured_latest_binding"
)
_ISSUE_3160_NODE_ID = (
    "tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py::"
    "test_command_exposes_exact_flag_surface[acceptance-verdict]"
)

_COLLECT_TIMEOUT_SECONDS = 300
_RUN_SINGLE_TIMEOUT_SECONDS = 180
_SAMPLE_LIMIT = 10


def _load_baseline(path: Path = _BASELINE_PATH) -> frozenset[str]:
    """Committed node-id set, ignoring blank lines and ``#``-prefixed comments."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return frozenset(
        stripped
        for line in lines
        if (stripped := line.strip()) and not stripped.startswith("#")
    )


def _parse_node_ids(collect_only_stdout: str) -> frozenset[str]:
    """Pure: extract test node-ids from a ``pytest --collect-only -q`` transcript.

    Every collected-test line contains ``::``; the summary/warning footer
    does not, so filtering on that substring is sufficient -- the same
    convention ``marker_baseline.txt``'s generation already relies on.
    """
    return frozenset(
        line.strip() for line in collect_only_stdout.splitlines() if "::" in line
    )


def _collect_affected_suite_node_ids() -> frozenset[str]:
    """Re-run the EXACT quickstart.md affected-suites invocation, collect-only."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            *_AFFECTED_SUITE_PATHS,
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=_COLLECT_TIMEOUT_SECONDS,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "affected-suites --collect-only did not complete cleanly "
            f"(exit {result.returncode}):\n"
            f"stdout tail: {result.stdout[-2000:]}\n"
            f"stderr tail: {result.stderr[-2000:]}"
        )
    return _parse_node_ids(result.stdout)


def _run_single_node(node_id: str) -> subprocess.CompletedProcess[str]:
    """Execute exactly one test node-id in a fresh subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", node_id],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=_RUN_SINGLE_TIMEOUT_SECONDS,
        check=False,
    )


def shrunk_node_ids(baseline: frozenset[str], current: frozenset[str]) -> list[str]:
    """NFR-001: the floor may grow, never shrink.

    Returns every committed node-id absent from a live collection -- by
    deletion, a move out of the affected-suites paths, de-parametrization, or
    exclusion at collection/marker-selection level. An empty result is the
    passing case; growth (``current - baseline``) is never itself a
    violation of this check.
    """
    return sorted(baseline - current)


def test_baseline_file_is_non_empty() -> None:
    """Anti-vacuous canary: an empty/corrupted baseline must not pass this
    guard green by having nothing to shrink against.
    """
    baseline = _load_baseline()
    assert baseline, "mission_exit_baseline.txt is empty -- NFR-001 guard would be vacuous"


def test_known_baseline_pins_are_in_the_floor() -> None:
    """Both pinned node-ids must themselves be members of the committed
    floor file -- if either were absent, the floor file itself would be the
    thing that needs fixing, not the pinned test below.
    """
    baseline = _load_baseline()
    assert _ISSUE_3157_NODE_ID in baseline, "issue #3157's node-id is missing from mission_exit_baseline.txt"
    assert _ISSUE_3160_NODE_ID in baseline, "issue #3160's node-id is missing from mission_exit_baseline.txt"


@pytest.mark.slow
def test_committed_floor_present_in_live_collection() -> None:
    """NFR-001's floor, made executable: every committed node-id must still
    collect under the identical affected-suites invocation. This is the
    single mechanical check that discharges NFR-001/SC-009 -- a diff against
    a committed node-id set, never a re-run judgement.
    """
    baseline = _load_baseline()
    current = _collect_affected_suite_node_ids()
    assert current, "affected-suites collection found zero tests -- guard would be vacuous"
    violations = shrunk_node_ids(baseline, current)
    assert not violations, (
        f"NFR-001 VIOLATION: {len(violations)} committed node-id(s) vanished from "
        "a live --collect-only of the affected-suites invocation (deleted, moved "
        "out of the affected-suites paths, de-parametrized, or excluded at "
        f"collection/marker-selection level -- never treat this as an improvement). "
        f"Showing up to {_SAMPLE_LIMIT}: {violations[:_SAMPLE_LIMIT]}"
    )


def test_shrink_detection_fault_injection() -> None:
    """Proves ``shrunk_node_ids`` fails when a committed node-id disappears --
    the mechanism ``test_committed_floor_present_in_live_collection`` relies
    on, exercised directly and deterministically.
    """
    baseline = frozenset({"tests/a.py::test_a", "tests/b.py::test_b"})
    current = frozenset({"tests/a.py::test_a"})
    assert shrunk_node_ids(baseline, current) == ["tests/b.py::test_b"]


def test_growth_is_not_a_violation() -> None:
    """A brand-new test appearing (growth) must never be flagged."""
    baseline = frozenset({"tests/a.py::test_a"})
    current = frozenset({"tests/a.py::test_a", "tests/c.py::test_new"})
    assert not shrunk_node_ids(baseline, current)


def test_identical_sets_pass() -> None:
    baseline = frozenset({"tests/a.py::test_a"})
    assert not shrunk_node_ids(baseline, baseline)


def test_windows_capability_fallback_keeps_committed_posix_node_id() -> None:
    """Capability fallback must not silently rename the collection floor node."""
    source = Path(__file__).with_name("..") / "review" / "test_pre_review_gate_engine.py"
    text = source.resolve().read_text(encoding="utf-8")
    assert 'pytest.param(True, signal.SIGKILL, id="True-9")' in text


@pytest.mark.slow
@pytest.mark.parametrize(
    ("issue", "node_id"),
    [
        pytest.param("3157", _ISSUE_3157_NODE_ID, id="3157"),
        pytest.param("3160", _ISSUE_3160_NODE_ID, id="3160"),
    ],
)
def test_known_baseline_failure_pin(issue: str, node_id: str) -> None:
    """research/baseline-8466727eb.md named these two node-ids as the ONLY
    failures reproducing at the merge-base ``8466727eb``. Each is re-run
    here individually -- a distinct, separately-named case per node-id, not
    folded anonymously into the bulk floor check -- so a reviewer can see,
    by name, whether it is still red or now green without grepping the
    ~2877-line floor file.

    Measured at mission exit (2026-08-05): BOTH now PASS -- #3157 via WP02's
    FR-014 fix (the date-bomb class is banned), #3160 via the flag-surface
    fix integrated through this WP's dependency chain. If either regresses
    back to red, this test reds by name; per this WP's task file Objective,
    that must be investigated and fixed, never silently re-classified back
    to "pre-existing" (that classification is reserved for failures that
    reproduce at the `8466727eb` merge-base itself, verified there).
    """
    result = _run_single_node(node_id)
    assert result.returncode == 0, (
        f"issue #{issue}'s pinned node-id is RED at mission exit. Both were "
        "fixed by this mission's work (see research/baseline-8466727eb.md's "
        "mission-exit section) -- a regression here must be investigated, not "
        f"waved through as pre-existing baseline red.\n"
        f"stdout tail: {result.stdout[-3000:]}"
    )
