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
"""

from __future__ import annotations

import json
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


def test_generate_retrospective_degrades_on_deleted_coord_traces(tmp_path: Path) -> None:
    """``generate_retrospective`` returns ``[]`` traces instead of crashing (T024/T026).

    Red-first: before the WP06 guard, ``_load_traces``'s unwrapped
    ``read_dir(TRACER_FILE)`` call lets ``CoordinationBranchDeleted`` propagate
    through ``generate_retrospective`` uncaught.
    """
    _build_coord_deleted_mission(tmp_path)
    policy = default_policy()

    record = generate_retrospective(_SLUG_WITH_MID8, policy, tmp_path)

    trace_evidence = [ref for ref in record.evidence_refs if "/traces/" in ref.path]
    assert trace_evidence == [], (
        "deleted-coord mission must degrade to zero tracer evidence refs; "
        f"got {[ref.path for ref in trace_evidence]}"
    )
