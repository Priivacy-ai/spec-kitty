"""``move-task`` WP-file persist is EVENT-ONLY, post-cutover (#2580 / #2816).

Pin (d), post-cutover (#2816/IC-04, WP04): ``_mt_persist_wp_file`` is
event-only -- the runtime-state god-write (``shell_pid`` +
``shell_pid_created_at`` frontmatter co-write via the retired
``write_shell_pid_claim``) was deleted (FR-006/FR-007), so persisting the WP
leaves the on-disk frontmatter BYTE-IDENTICAL. The claim triple rides the
transition's ``policy_metadata`` and is reduced into the snapshot, never
written back into ``tasks/WP##.md`` (C-001, INV-2).

Provenance: this module originally also held the WP07
(loop-friction-quickwins-2 / coord-primary-partition-lock) authority-path
staging battery -- ``_mt_write_and_commit_wp_file`` /
``_mt_untracked_planning_artifact_paths`` /
``_mt_resolve_status_placement_ref`` / ``_primary_bundle_status_artifacts`` +
the ``test_wp07_diff_does_not_touch_status_bundling_symbols`` source pin. That
whole WP-file write/commit closure went production-dead when #2816/IC-04 (WP05)
deleted ``_mt_dual_write_wp_file`` (its last caller); #2816/IC-06 (WP07)
deleted the closure and reconciled those now-orphaned arms away, leaving only
the event-only persist pin below (which exercises the LIVE
``_mt_persist_wp_file``).

Fixture data mirrors ``test_tasks_move_task_placement.py`` (real git repo, real
26-char ULID mission_id, real coordination branch) -- no synthetic short IDs.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from mission_runtime import MissionTopology
from specify_cli.cli.commands.agent import tasks_move_task
from specify_cli.cli.commands.agent.tasks_move_task import _MoveTaskState
from specify_cli.frontmatter import SHELL_PID_BASELINE_FIELD
from specify_cli.task_utils.support import split_frontmatter

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# Realistic identity (mirrors test_tasks_move_task_placement.py): a real
# 26-char Crockford ULID and its derived 8-char mid8 prefix.
_MISSION_ID = "01KXC0STAGE7M8N0RAB4CDXYZ9"
_MID8 = _MISSION_ID[:8]
_MISSION_SLUG = f"movetask-authority-staging-{_MID8}"
_TARGET_BRANCH = "design/movetask-authority-staging"
_COORD_BRANCH = f"kitty/mission-{_MISSION_SLUG}-{_MID8}"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / ".kittify").mkdir()
    (r / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )
    return r


def _build_coord_mission(repo_root: Path) -> Path:
    """Build a COORD-topology mission fixture (mirrors the sibling module)."""
    feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True)
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "target_branch": _TARGET_BRANCH,
        "friendly_name": "move-task authority staging",
        "topology": MissionTopology.COORD.value,
        "coordination_branch": _COORD_BRANCH,
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (feature_dir / "tasks").mkdir()
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-q", "-m", "fixture")
    _git(repo_root, "branch", _COORD_BRANCH)
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


# --------------------------------------------------------------------------- #
# #2580 / #2816-IC-04 — persisting the WP is EVENT-ONLY: the frontmatter is
# left byte-identical (the runtime-state god-write is gone, not merely gated).
# --------------------------------------------------------------------------- #


def test_persist_wp_file_is_event_only_leaves_frontmatter_byte_stable(repo: Path) -> None:
    """Pin (d), post-cutover (#2816/IC-04, WP04): ``_mt_persist_wp_file`` is
    EVENT-ONLY -- the runtime-state god-write (``shell_pid`` +
    ``shell_pid_created_at`` frontmatter co-write via the retired
    ``write_shell_pid_claim``) was deleted (FR-006/FR-007), so persisting the WP
    leaves the on-disk frontmatter BYTE-IDENTICAL. The claim triple is carried on
    the transition's ``policy_metadata`` and reduced into the snapshot, never
    written back into ``tasks/WP##.md`` (C-001, INV-2).

    Uses this test process's OWN real pid (realistic test data) so a resurrected
    baseline co-write would be genuinely capturable -- a fabricated pid would let
    the byte-stability hold vacuously if a partial writer degraded to ``None``.
    """
    feature_dir = _build_coord_mission(repo)
    wp_file = feature_dir / "tasks" / "WP01-x.md"
    original_content = "---\nwork_package_id: WP01\ntitle: x\n---\nbody\n"
    wp_file.write_text(original_content, encoding="utf-8")
    bytes_before = wp_file.read_bytes()
    live_pid = os.getpid()

    st = _make_state()
    st.main_repo_root = repo
    st.mission_slug = _MISSION_SLUG
    st.feature_dir = feature_dir
    st.target_branch = _TARGET_BRANCH
    st.resolved_auto_commit = False  # bypass the commit/router leg entirely
    st.target_lane = tasks_move_task.Lane.FOR_REVIEW
    st.shell_pid = str(live_pid)
    st.decision = cast(Any, SimpleNamespace(skip_primary=False))
    st.wp = cast(Any, SimpleNamespace(path=wp_file))

    tasks_move_task._mt_persist_wp_file(st, MagicMock())

    # Event-only: the WP file bytes are unchanged -- NO shell_pid / baseline was
    # written into the frontmatter (the god-write is gone, not merely gated).
    assert wp_file.read_bytes() == bytes_before
    persisted_front, _body, _padding = split_frontmatter(
        wp_file.read_text(encoding="utf-8-sig")
    )
    assert "shell_pid" not in persisted_front
    assert SHELL_PID_BASELINE_FIELD not in persisted_front
