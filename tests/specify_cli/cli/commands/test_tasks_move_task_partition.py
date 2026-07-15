"""move-task's silent second consumer of the partition-aware staging core
(WP03, T009, #2533 FR-005).

``_mt_untracked_planning_artifact_paths``
(``specify_cli.cli.commands.agent.tasks_move_task``:1364, called at :1400)
reuses WP01's :func:`~specify_cli.cli.commands.implement_cores.resolve_planning_artifact_staging`
seam to bundle any OTHER untracked-on-primary planning artifact into the same
``commit_artifact`` call as the WP file. It is wrapped in a bare
``except Exception: return ()`` (best-effort / degrade-never-crash by
design), which means a FUTURE regression in the shared partition core (e.g.
a PRIMARY-kind path silently routed back to the coordination ref) would not
raise here -- it would just silently under-stage or over-stage, with no
crash to signal it. This module locks the real, end-to-end consumer path
(no injected fake :class:`GitPort` -- the shared core defaults to real
``git`` subprocess calls) against exactly that failure mode:

  1. PRIMARY planning artifacts (spec/plan/tasks/data-model/lanes.json/
     meta.json) that are ALREADY COMMITTED on the primary/target branch must
     never be reported as needing staging against the coordination ref (the
     pre-WP01 bug: kind-blind diffing treated a clean, committed primary file
     as "changed" merely because it didn't exist yet on the coordination
     branch, producing a false "Planning artifacts not committed" abort).
  2. A genuinely-dirty COORD-kind artifact (``issue-matrix.md`` -- a COORD
     placement kind, but NOT one of the ``COORD_OWNED_STATUS_FILES`` the
     transactional status emitter already owns) must still be discovered and
     surfaced under coordination topology -- the fix must not have
     over-corrected into dropping coordination-routed content.

The coordination branch is deliberately branched OFF the pre-mission
bootstrap commit, before any planning artifact exists on it, so it
genuinely diverges from primary for these paths. That divergence is
load-bearing: it is what makes a kind-blind (pre-WP01) diff against the
coordination ref actually disagree with a kind-partitioned (post-WP01) diff
against ``HEAD`` -- so this test would have failed red before WP01's fix and
would fail again if that fix regressed, rather than trivially passing
regardless of which ref is consulted.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from mission_runtime import MissionTopology, is_coordination_artifact_residue_path
from specify_cli.cli.commands.agent import tasks_move_task
from specify_cli.cli.commands.agent.tasks_move_task import _MoveTaskState

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# Realistic identity (mirrors test_tasks_move_task_authority_staging.py): a
# real 26-char Crockford ULID and its derived 8-char mid8 prefix -- not a
# synthetic short id.
_MISSION_ID = "01KXMVPART7M8N0RAB4CDXYZ90"
_MID8 = _MISSION_ID[:8]
_MISSION_SLUG = f"movetask-partition-{_MID8}"
_TARGET_BRANCH = "main"
_COORD_BRANCH = f"kitty/mission-{_MISSION_SLUG}-{_MID8}"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", _TARGET_BRANCH)
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / ".kittify").mkdir()
    (r / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )
    _git(r, "add", ".")
    _git(r, "commit", "-q", "-m", "chore: bootstrap")
    return r


def _build_diverged_coord_mission(repo_root: Path) -> Path:
    """A COORD-topology mission whose coordination branch is branched off the
    bootstrap commit -- BEFORE any planning artifact exists on it -- so the
    coordination branch genuinely lacks these paths. PRIMARY artifacts are
    then committed only on the current (primary/target) branch.
    """
    _git(repo_root, "branch", _COORD_BRANCH)

    feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True)
    (feature_dir / "tasks").mkdir()
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "target_branch": _TARGET_BRANCH,
        "friendly_name": "move-task partition regression",
        "topology": MissionTopology.COORD.value,
        "coordination_branch": _COORD_BRANCH,
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    (feature_dir / "data-model.md").write_text("# Data Model\n", encoding="utf-8")
    (feature_dir / "lanes.json").write_text("{}\n", encoding="utf-8")
    wp_file = feature_dir / "tasks" / "WP01-x.md"
    wp_file.write_text("---\nwork_package_id: WP01\ntitle: x\n---\nbody\n", encoding="utf-8")

    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-q", "-m", "fixture: primary planning artifacts")
    return feature_dir


def _make_state(**overrides: Any) -> _MoveTaskState:
    kwargs: dict[str, Any] = {
        "task_id": "WP01",
        "to": "for_review",
        "mission": _MISSION_SLUG,
        "agent": None,
        "assignee": None,
        "shell_pid": None,
        "note": None,
        "review_feedback_file": None,
        "approval_ref": None,
        "reviewer": None,
        "self_review_fallback": False,
        "intended_reviewer": None,
        "reviewer_failure_reason": None,
        "done_override_reason": None,
        "force": False,
        "tracker_ref": None,
        "skip_review_artifact_check": False,
        "auto_commit": None,
        "json_output": True,
    }
    field_names = set(_MoveTaskState.__dataclass_fields__)
    field_overrides = {k: v for k, v in overrides.items() if k in kwargs}
    kwargs.update(field_overrides)
    st = _MoveTaskState(**kwargs)
    for key, value in overrides.items():
        if key not in field_overrides:
            assert key in field_names, f"unknown _MoveTaskState field: {key!r}"
            setattr(st, key, value)
    return st


def _state_for(repo_root: Path, feature_dir: Path) -> _MoveTaskState:
    st = _make_state()
    st.main_repo_root = repo_root
    st.mission_slug = _MISSION_SLUG
    st.feature_dir = feature_dir
    st.target_branch = _TARGET_BRANCH
    st.resolved_auto_commit = True
    return st


# --------------------------------------------------------------------------- #
# T009 (1): committed PRIMARY artifacts are never reported as needing
# staging against the coordination ref.
# --------------------------------------------------------------------------- #


def test_committed_primary_artifacts_not_flagged_against_coord_ref(repo: Path) -> None:
    feature_dir = _build_diverged_coord_mission(repo)
    wp_file = feature_dir / "tasks" / "WP01-x.md"
    st = _state_for(repo, feature_dir)

    # Sanity: git status is clean -- these files are genuinely committed, not
    # merely present on disk. The regression this test guards is specifically
    # about clean/committed primary content being MIS-diffed against the
    # coordination ref, not about live git-status dirt.
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True
    )
    assert status.stdout == ""

    extra = tasks_move_task._mt_untracked_planning_artifact_paths(st, wp_file)

    assert isinstance(extra, tuple)
    assert all(isinstance(p, Path) for p in extra)
    reported_names = {p.name for p in extra}
    primary_filenames = {"spec.md", "plan.md", "tasks.md", "data-model.md", "lanes.json", "meta.json"}
    assert not (reported_names & primary_filenames), (
        "committed PRIMARY planning artifacts must not be reported as "
        f"needing staging: {reported_names & primary_filenames}"
    )


# --------------------------------------------------------------------------- #
# T009 (2): a genuinely-dirty COORD-kind artifact IS still surfaced under
# coordination topology -- the fix must not over-correct into silence.
# --------------------------------------------------------------------------- #


def test_dirty_coord_kind_artifact_still_surfaced(repo: Path) -> None:
    feature_dir = _build_diverged_coord_mission(repo)
    wp_file = feature_dir / "tasks" / "WP01-x.md"

    # issue-matrix.md is a COORD placement kind (mission_runtime.artifacts
    # _COORD_RESIDUE_FILENAMES -> MissionArtifactKind.ISSUE_MATRIX) but is
    # NOT one of COORD_OWNED_STATUS_FILES (status.events.jsonl/status.json),
    # which the transactional status emitter already owns and which
    # _exclude_coord_owned drops unconditionally from this bundling path.
    # Pin that classification so the fixture is genuinely exercising the
    # COORD-residue branch, not merely "any dirty file, any ref".
    issue_matrix_repo_rel = f"kitty-specs/{_MISSION_SLUG}/issue-matrix.md"
    assert is_coordination_artifact_residue_path(issue_matrix_repo_rel) is True

    issue_matrix = feature_dir / "issue-matrix.md"
    issue_matrix.write_text("| # | Title |\n|---|---|\n", encoding="utf-8")

    st = _state_for(repo, feature_dir)
    extra = tasks_move_task._mt_untracked_planning_artifact_paths(st, wp_file)

    # Guard the silent consumer (FR-005): a non-empty, well-typed result for
    # the dirty-coord case -- NOT the `except Exception: return ()` empty
    # tuple the function degrades to on resolution failure. If the shared
    # partition core regressed and this leg started raising, the bare except
    # would silently swallow it and this assertion would go red instead.
    assert extra != ()
    assert isinstance(extra, tuple)
    assert all(isinstance(p, Path) for p in extra)

    resolved = {p.resolve() for p in extra}
    assert issue_matrix.resolve() in resolved
    # wp_path itself is always excluded (the router call's own explicit
    # primary argument, never duplicated by this staging leg).
    assert wp_file.resolve() not in resolved
