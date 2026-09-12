"""WP06 (FR-006) — ``_load_traces`` degrades on a deleted coord branch.

``retrospective/generator.py::_load_traces`` reads ``TRACER_FILE`` through
``mission_runtime.placement_seam(...).read_dir(...)``. That call resolves the
coordination surface for a coord-topology mission and raises
:class:`~specify_cli.coordination.surface_resolver.CoordinationBranchDeleted`
(a :class:`~specify_cli.missions._read_path_resolver.StatusReadPathNotFound`
subclass, #1848 data-loss signal) when ``meta.json`` declares a
``coordination_branch`` that no longer exists in git and no coord worktree is
materialized on disk.

``_load_traces`` is documented best-effort (FR-007 docstring: a tracer that
cannot be read is skipped, not a generator crash). Per C-READ-1
(``contracts/degrade-and-read-hygiene.md``), a deleted coord branch must
degrade the SAME way — ``generate_retrospective`` completes with ``[]``
traces rather than propagating the exception. Today (pre-fix) the
``read_dir`` call is unwrapped, so the exception propagates through
``_load_traces`` -> ``generate_retrospective`` uncaught. Scope (C-003): this
guards ONLY the single ``_load_traces`` call site — it must NOT widen to a
bare ``Exception`` and must NOT touch the ~50-module read-side set tracked
under #2922.

Landing-fold follow-up (P2): the bare ``except ... return []`` originally
carried no log line and no record marker, so a deleted-coord degrade was
indistinguishable from a mission that genuinely has zero tracer files — both
yield ``trace_evidence == []``. The generator now emits a ``WARNING`` naming
the mission and its declared ``coordination_branch`` on the degrade path.
``test_generate_retrospective_degrades_on_deleted_coord_traces`` below
asserts that warning fires; ``test_generate_retrospective_zero_traces_on_healthy_surface_logs_nothing``
is the discriminating sibling — a healthy, coord-less mission with no
``traces/`` directory also yields ``trace_evidence == []`` but must NOT log a
warning, proving the log line tracks surface-unreachability and not mere
absence of tracers.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import pytest

from specify_cli.retrospective.generator import generate_retrospective
from specify_cli.retrospective.policy import default_policy

pytestmark = pytest.mark.git_repo

# Production-shaped identity: a real 26-char ULID, mid8 = first 8 chars
# (Mission Identity Model 083+), matching the on-disk composed dir name.
_MISSION_ID = "01KW7TRACEDELETEDCOORD0WP06"[:26]
_MID8 = _MISSION_ID[:8]
_MISSION_SLUG = "trace-deleted-coord-mission"
_SLUG_WITH_MID8 = f"{_MISSION_SLUG}-{_MID8}"
_COORD_BRANCH = f"kitty/mission-{_SLUG_WITH_MID8}"

# Second fixture identity: a healthy SINGLE_BRANCH mission with genuinely zero
# tracer files (no coordination_branch declared at all).
_HEALTHY_MISSION_ID = "01KW7TRACEHEALTHYNOCOORD0"[:26]
_HEALTHY_MID8 = _HEALTHY_MISSION_ID[:8]
_HEALTHY_MISSION_SLUG = "trace-healthy-no-coord-mission"
_HEALTHY_SLUG_WITH_MID8 = f"{_HEALTHY_MISSION_SLUG}-{_HEALTHY_MID8}"

_SPEC_TEXT = """\
# Mission Spec — trace deleted coord

## User Scenarios

### User Story 1 — Read traces best-effort

As an operator, I want retrospective generation to degrade gracefully when
the coordination branch is gone.

## Requirements

- **FR-001**: Retrospective generation must not crash on a deleted coord branch.

## Success Criteria

- **SC-001**: `generate_retrospective` completes with empty traces.
"""


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _build_coord_deleted_mission(repo_root: Path) -> Path:
    """Real git repo: mission declares a coord branch that was never created.

    Mirrors ``tests/status/test_aggregate_coord_deleted_contract.py``'s fixture
    (the canonical coord-deleted (R3) shape): ``coordination_branch`` recorded
    in ``meta.json`` while the branch is absent from git and no coord worktree
    exists on disk.
    """
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "trace-deleted-coord@example.test")
    _git(repo_root, "config", "user.name", "Trace Deleted Coord Contract")

    feature_dir = repo_root / "kitty-specs" / _SLUG_WITH_MID8
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mission_slug": _MISSION_SLUG,
                "slug": _SLUG_WITH_MID8,
                "friendly_name": _MISSION_SLUG,
                "mission_type": "software-dev",
                "coordination_branch": _COORD_BRANCH,
                "topology": "coord",
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text(_SPEC_TEXT, encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n\nImplementation plan.\n", encoding="utf-8")
    (feature_dir / "status.events.jsonl").write_text("", encoding="utf-8")

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-qm", "init mission with deleted coord branch")
    return feature_dir


def _build_healthy_no_traces_mission(repo_root: Path) -> Path:
    """Real git repo: a healthy SINGLE_BRANCH mission with genuinely zero tracers.

    No ``coordination_branch`` is declared at all (SINGLE_BRANCH topology), and
    no ``traces/`` directory is ever created. This is the discriminating
    sibling of :func:`_build_coord_deleted_mission`: both fixtures yield
    ``trace_evidence == []`` from ``generate_retrospective``, but only the
    coord-deleted one should log a warning — this one has nothing to warn
    about, the tracer surface is reachable and simply empty.
    """
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "trace-healthy-no-coord@example.test")
    _git(repo_root, "config", "user.name", "Trace Healthy No Coord Contract")

    feature_dir = repo_root / "kitty-specs" / _HEALTHY_SLUG_WITH_MID8
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _HEALTHY_MISSION_ID,
                "mission_slug": _HEALTHY_MISSION_SLUG,
                "slug": _HEALTHY_SLUG_WITH_MID8,
                "friendly_name": _HEALTHY_MISSION_SLUG,
                "mission_type": "software-dev",
                "topology": "SINGLE_BRANCH",
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text(_SPEC_TEXT, encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n\nImplementation plan.\n", encoding="utf-8")
    (feature_dir / "status.events.jsonl").write_text("", encoding="utf-8")

    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-qm", "init healthy mission with zero tracers")
    return feature_dir


def test_generate_retrospective_degrades_on_deleted_coord_traces(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """``generate_retrospective`` returns ``[]`` traces instead of crashing (T024/T026).

    Red-first: before the WP06 guard, ``_load_traces``'s unwrapped
    ``read_dir(TRACER_FILE)`` call lets ``CoordinationBranchDeleted`` propagate
    through ``generate_retrospective`` uncaught.

    Landing-fold (P2): the degrade must also be *observable* — a WARNING
    naming the mission and its declared coordination branch — so this state
    is distinguishable from a mission with genuinely zero tracer files (see
    ``test_generate_retrospective_zero_traces_on_healthy_surface_logs_nothing``
    below, which asserts the negative).
    """
    _build_coord_deleted_mission(tmp_path)
    policy = default_policy()

    with caplog.at_level(logging.WARNING, logger="specify_cli.retrospective.generator"):
        record = generate_retrospective(_SLUG_WITH_MID8, policy, tmp_path)

    trace_evidence = [ref for ref in record.evidence_refs if "/traces/" in ref.path]
    assert trace_evidence == [], (
        "deleted-coord mission must degrade to zero tracer evidence refs; "
        f"got {[ref.path for ref in trace_evidence]}"
    )

    warnings = [rec for rec in caplog.records if rec.levelno == logging.WARNING]
    assert len(warnings) == 1, (
        f"expected exactly one WARNING for the deleted-coord tracer degrade, got {len(warnings)}: "
        f"{[rec.message for rec in warnings]}"
    )
    message = warnings[0].getMessage()
    assert _SLUG_WITH_MID8 in message, (
        f"degrade warning must name the mission ({_SLUG_WITH_MID8!r}); got: {message!r}"
    )
    assert _COORD_BRANCH in message, (
        f"degrade warning must name the declared coordination branch ({_COORD_BRANCH!r}); "
        f"got: {message!r}"
    )


def test_generate_retrospective_zero_traces_on_healthy_surface_logs_nothing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A healthy mission with genuinely zero tracers yields ``[]`` with NO warning.

    This is the discriminating sibling of the deleted-coord test above: both
    fixtures produce identical ``trace_evidence == []`` output, but only an
    unreachable tracer surface should emit a WARNING. Without this test, the
    warning could regress into firing on every trace-less mission (a much
    noisier, less useful signal) and nothing would catch it.
    """
    _build_healthy_no_traces_mission(tmp_path)
    policy = default_policy()

    with caplog.at_level(logging.WARNING, logger="specify_cli.retrospective.generator"):
        record = generate_retrospective(_HEALTHY_SLUG_WITH_MID8, policy, tmp_path)

    trace_evidence = [ref for ref in record.evidence_refs if "/traces/" in ref.path]
    assert trace_evidence == [], (
        "healthy mission with no tracers must still yield zero tracer evidence refs; "
        f"got {[ref.path for ref in trace_evidence]}"
    )

    warnings = [rec for rec in caplog.records if rec.levelno == logging.WARNING]
    assert warnings == [], (
        "a healthy, reachable tracer surface with zero tracers must NOT log a warning; "
        f"got: {[rec.message for rec in warnings]}"
    )
