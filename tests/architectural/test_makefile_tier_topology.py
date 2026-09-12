"""Makefile test-tier topology drift guard (planning#22).

``test_serial_port_preservation.py`` used to pin the CI workflow split
against the (now-deleted, issue #5) ``tests/_real_port_suites.py`` registry,
but nothing parsed the repo ``Makefile`` itself. After #5 removed the sync
transport's fixed-range serial pass, ``test-full``'s topology is:

* one parallel pass over ``tests/`` carrying ``-m "$(PARALLEL_UNSAFE_MARKERS)"``
  (``not stress and not timing``) with ``--dist loadfile``; then
* one dedicated ``-n0`` pass per parallel-unsafe family (``stress``, ``timing``),
  each positively selecting its family.

``test-fast`` runs ``$(FAST_TIER_DIRS)`` under ``$(FAST_TIER_MARKERS)``, which
must keep negating the slow-tier marker family it was written to exclude
(Makefile:24, "every slow tier is deselected by marker").

None of that was guarded: renaming a variable, dropping a serial pass, or
adding a new parallel-unsafe marker to ``pytest.ini`` without updating the
Makefile targets would drift silently. This test parses the Makefile and
pytest.ini live and cross-checks them; the classifier functions are pure so
the fault-injection tests below can prove each check actually bites.
"""

from __future__ import annotations

import re

import pytest

from tests.architectural import _gate_coverage as gc
from tests.architectural.test_marker_job_completeness import negated_marker_tokens

pytestmark = pytest.mark.architectural

_MAKEFILE_PATH = gc.REPO_ROOT / "Makefile"

_VAR_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*:?=\s*(.+)$")
_DASH_N_AUTO_RE = re.compile(r"-n\s*auto\b")
_DASH_N0_RE = re.compile(r"-n0\b|-n\s*0\b")
_BARE_LOAD_RE = re.compile(r"--dist\s+load(?!file)\b")
_DASH_M_RE = re.compile(r'-m\s+(?:"([^"]+)"|(\S+))')

# The slow-tier family FAST_TIER_MARKERS was written to exclude (Makefile:24).
# Cross-checked against pytest.ini's live registry below so a rename/removal
# there reds this ledger instead of silently narrowing what the fast tier
# excludes; cross-checked against the live Makefile expression so dropping one
# of these negations (accidentally or via a careless edit) reds too.
SLOW_TIER_MARKERS = frozenset(
    {
        "slow",
        "e2e",
        "integration",
        "regression",
        "distribution",
        "live_adapter",
        "stress",
        "windows_ci",
        "platform_darwin",
    }
)

# The two marker families PARALLEL_UNSAFE_MARKERS exists to deselect from
# test-full's parallel pass (Makefile:27-31) — each needs its own dedicated
# `-n0` pass, positively selecting it.
PARALLEL_UNSAFE_FAMILIES = frozenset({"stress", "timing"})


def _makefile_text() -> str:
    return _MAKEFILE_PATH.read_text(encoding="utf-8")


def _variables(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = _VAR_RE.match(line.strip())
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def _recipe_commands(text: str, target: str) -> list[str]:
    """Backslash-joined pytest command lines from ``target``'s recipe block."""
    lines = text.splitlines()
    header = f"{target}:"
    start = next((i + 1 for i, line in enumerate(lines) if line.startswith(header)), None)
    if start is None:
        raise AssertionError(f"no {target!r} target found in {_MAKEFILE_PATH}")
    block: list[str] = []
    for line in lines[start:]:
        if line.strip() and not line.startswith(("\t", " ")):
            break
        block.append(line[1:] if line.startswith("\t") else line)
    return [cmd for cmd in gc.join_continuations("\n".join(block)) if "pytest" in cmd]


def _dash_m_value(cmd: str) -> str:
    match = _DASH_M_RE.search(cmd)
    if not match:
        return ""
    return match.group(1) or match.group(2) or ""


# ---------------------------------------------------------------------------
# Pure classifiers (fault-injectable — no Makefile/pytest.ini I/O).
# ---------------------------------------------------------------------------


def missing_slow_tier_negations(fast_tier_markers_expr: str) -> frozenset[str]:
    """Slow-tier markers ``FAST_TIER_MARKERS`` fails to negate. Empty == healthy."""
    return SLOW_TIER_MARKERS - negated_marker_tokens(fast_tier_markers_expr)


def parallel_unsafe_family_mismatch(parallel_unsafe_expr: str) -> frozenset[str]:
    """Symmetric difference between what's negated and the declared family set."""
    return negated_marker_tokens(parallel_unsafe_expr) ^ PARALLEL_UNSAFE_FAMILIES


def parallel_pass_violations(commands: list[str]) -> list[str]:
    """test-full's ``-n auto`` pass keeps its marker filter and safe dist mode."""
    parallel = [c for c in commands if _DASH_N_AUTO_RE.search(c)]
    if len(parallel) != 1:
        return [f"expected exactly one '-n auto' pass in test-full, found {len(parallel)}"]
    cmd = parallel[0]
    violations = []
    if "$(PARALLEL_UNSAFE_MARKERS)" not in cmd:
        violations.append(f"parallel pass drops $(PARALLEL_UNSAFE_MARKERS): {cmd.strip()}")
    if _BARE_LOAD_RE.search(cmd):
        violations.append(f"parallel pass uses bare --dist load (use loadfile): {cmd.strip()}")
    if "--dist loadfile" not in cmd:
        violations.append(f"parallel pass missing --dist loadfile: {cmd.strip()}")
    return violations


def missing_serial_passes(commands: list[str], families: frozenset[str] = PARALLEL_UNSAFE_FAMILIES) -> frozenset[str]:
    """Families with no dedicated ``-n0`` pass positively selecting them."""
    serial = [c for c in commands if _DASH_N0_RE.search(c)]
    return frozenset(family for family in families if not any(family in gc.positive_marker_tokens(_dash_m_value(c)) for c in serial))


# ---------------------------------------------------------------------------
# Live checks.
# ---------------------------------------------------------------------------


def test_fast_tier_markers_negates_the_slow_tier_family_live() -> None:
    expr = _variables(_makefile_text())["FAST_TIER_MARKERS"]
    missing = missing_slow_tier_negations(expr)
    assert not missing, f"FAST_TIER_MARKERS no longer negates {sorted(missing)}: {expr!r}"


def test_slow_tier_ledger_entries_are_registered_in_pytest_ini_live() -> None:
    registered = set(gc.registered_markers())
    missing = SLOW_TIER_MARKERS - registered
    assert not missing, f"SLOW_TIER_MARKERS ledger entries not in pytest.ini: {sorted(missing)}"


def test_fast_tier_markers_positively_requires_fast_or_unit_live() -> None:
    expr = _variables(_makefile_text())["FAST_TIER_MARKERS"]
    positive = gc.positive_marker_tokens(expr)
    assert {"fast", "unit"} <= positive, f"FAST_TIER_MARKERS dropped fast/unit: {expr!r}"


def test_fast_target_references_the_shared_tier_variables_live() -> None:
    cmds = _recipe_commands(_makefile_text(), "test-fast")
    assert len(cmds) == 1, f"expected exactly one pytest command in test-fast: {cmds}"
    cmd = cmds[0]
    assert "$(FAST_TIER_DIRS)" in cmd, f"test-fast dropped $(FAST_TIER_DIRS): {cmd.strip()}"
    assert "$(FAST_TIER_MARKERS)" in cmd, f"test-fast dropped $(FAST_TIER_MARKERS): {cmd.strip()}"
    assert "--dist loadfile" in cmd, f"test-fast dropped --dist loadfile: {cmd.strip()}"
    assert not _BARE_LOAD_RE.search(cmd), f"test-fast uses bare --dist load: {cmd.strip()}"


def test_parallel_unsafe_markers_negates_exactly_stress_and_timing_live() -> None:
    expr = _variables(_makefile_text())["PARALLEL_UNSAFE_MARKERS"]
    mismatch = parallel_unsafe_family_mismatch(expr)
    assert not mismatch, f"PARALLEL_UNSAFE_MARKERS family drifted from {sorted(PARALLEL_UNSAFE_FAMILIES)}: {expr!r}"


def test_full_parallel_pass_is_structurally_sound_live() -> None:
    cmds = _recipe_commands(_makefile_text(), "test-full")
    violations = parallel_pass_violations(cmds)
    assert not violations, "\n".join(violations)


def test_full_has_a_dedicated_serial_pass_per_family_live() -> None:
    cmds = _recipe_commands(_makefile_text(), "test-full")
    missing = missing_serial_passes(cmds)
    assert not missing, f"no dedicated -n0 pass positively selects: {sorted(missing)} (commands: {cmds})"


# ---------------------------------------------------------------------------
# Fault injection — each check above must actually bite.
# ---------------------------------------------------------------------------


def test_faultinjection_dropped_slow_negation_reds() -> None:
    drifted = "(fast or unit) and not slow and not e2e and not windows_ci"
    missing = missing_slow_tier_negations(drifted)
    assert missing == SLOW_TIER_MARKERS - {"slow", "e2e", "windows_ci"}


def test_faultinjection_parallel_unsafe_family_drift_reds() -> None:
    # A new parallel-unsafe marker (`flaky_stress`) added to pytest.ini without
    # widening PARALLEL_UNSAFE_MARKERS would show up as a mismatch here.
    assert parallel_unsafe_family_mismatch("not stress") == {"timing"}
    assert parallel_unsafe_family_mismatch("not stress and not timing and not flaky_stress") == {"flaky_stress"}


def test_faultinjection_bare_dist_load_reds() -> None:
    cmds = ['uv run pytest tests/ -m "$(PARALLEL_UNSAFE_MARKERS)" -n auto --dist load -q']
    violations = parallel_pass_violations(cmds)
    assert any("bare --dist load" in v for v in violations), violations


def test_faultinjection_dropped_marker_reference_reds() -> None:
    cmds = ['uv run pytest tests/ -m "not stress and not timing" -n auto --dist loadfile -q']
    violations = parallel_pass_violations(cmds)
    assert any("$(PARALLEL_UNSAFE_MARKERS)" in v for v in violations), violations


def test_faultinjection_dropped_serial_pass_reds() -> None:
    cmds = [
        'uv run pytest tests/ -m "$(PARALLEL_UNSAFE_MARKERS)" -n auto --dist loadfile -q',
        'uv run pytest tests/ -m "stress and not windows_ci" -n0 --timeout=240 -q',
        # timing's dedicated serial pass silently dropped.
    ]
    missing = missing_serial_passes(cmds)
    assert missing == {"timing"}


def test_faultinjection_healthy_topology_is_clean() -> None:
    """Sanity: a topology mirroring the real one produces no findings anywhere."""
    fast_expr = (
        "(fast or unit) and not slow and not e2e and not integration and not "
        "regression and not distribution and not live_adapter and not stress "
        "and not windows_ci and not platform_darwin"
    )
    parallel_unsafe_expr = "not stress and not timing"
    cmds = [
        'uv run pytest tests/ -m "$(PARALLEL_UNSAFE_MARKERS)" -n auto --dist loadfile -q',
        'uv run pytest tests/ -m "stress and not windows_ci" -n0 --timeout=240 -q',
        "uv run pytest tests/ -m timing -n0 --timeout=240 -q",
    ]
    assert not missing_slow_tier_negations(fast_expr)
    assert not parallel_unsafe_family_mismatch(parallel_unsafe_expr)
    assert not parallel_pass_violations(cmds)
    assert not missing_serial_passes(cmds)
