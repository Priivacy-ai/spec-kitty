"""``move-task`` coord-lane staging via the authority path (WP07, #2555.1/#2580).

FR-010 / C-002 / C-E1: a coord-topology ``move-task --to for_review`` with
untracked planning artifacts on primary must resolve staging through the
established authority path (``commit_router`` WORK_PACKAGE_TASK routing,
reusing WP01's :func:`resolve_planning_artifact_staging` seam) rather than
leaving those artifacts for a lane-branch commit to pick up and trip
``commit_guard.block_mission_specs`` (the manual ``git restore`` recovery this
closes). **NO** ``commit_guard`` exemption — the fix is routing, not a guard
carve-out (K-6).

Dual pin (contract C-E1):
  (a) STATUS_STATE ref/event placement is byte-identical pre/post the new
      staging leg (:func:`_mt_resolve_status_placement_ref` is untouched).
  (b) zero ``kitty-specs/`` entries are ever committed via the lane-branch
      commit mechanism (``specify_cli.git.safe_commit``) — the untracked
      planning artifact lands ONLY through ``ports.coord.commit_artifact``
      (the primary/coord authority route).
  (c) the operation completes in ONE pass (no exception, no retry) — no
      manual ``git restore`` dance.
  (d) #2580: ``shell_pid`` + its ``shell_pid_created_at`` baseline persist
      byte-identically through the canonical ``write_shell_pid_claim``
      (``_mt_persist_wp_file`` routes through it — the SAME symbol WP01
      designates — closing the 4th divergent writer).

T028 (K-4): an arch guard pins the exact source of the three status-bundling
symbols this WP must never touch (``_mt_resolve_status_placement_ref`` /
``_primary_bundle_status_artifacts`` / the ``_collect_status_artifacts``
re-import identity) — any edit to them fails this test, by construction.

Fixture data mirrors ``test_tasks_move_task_placement.py`` (real git repo,
real 26-char ULID mission_id, real coordination branch) — no synthetic short
IDs (realistic test data).
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from mission_runtime import MissionTopology, placement_seam
from mission_runtime.artifacts import MissionArtifactKind
from specify_cli.cli.commands.agent import tasks_materialization
from specify_cli.cli.commands.agent import tasks_move_task
from specify_cli.cli.commands.agent.tasks_move_task import _MoveTaskState
from specify_cli.frontmatter import SHELL_PID_BASELINE_FIELD, write_shell_pid_claim
from specify_cli.task_utils.support import build_document, split_frontmatter

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

_TASKS = "specify_cli.cli.commands.agent.tasks"

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


def _coord_state_with_untracked_artifact(repo_root: Path) -> tuple[_MoveTaskState, Path, Path]:
    """A coord-topology state with an untracked ``research-addendum.md`` planning
    artifact sitting dirty on primary alongside the WP file being committed."""
    feature_dir = _build_coord_mission(repo_root)
    wp_file = feature_dir / "tasks" / "WP01-x.md"
    wp_file.write_text("---\nwork_package_id: WP01\n---\nbody", encoding="utf-8")
    extra_artifact = feature_dir / "research-addendum.md"
    extra_artifact.write_text("untracked planning note", encoding="utf-8")

    st = _make_state()
    st.main_repo_root = repo_root
    st.mission_slug = _MISSION_SLUG
    st.feature_dir = feature_dir
    st.target_branch = _TARGET_BRANCH
    st.resolved_auto_commit = True
    st.wp = cast(Any, SimpleNamespace(path=wp_file))
    return st, wp_file, extra_artifact


def _committed_ports() -> MagicMock:
    ports = MagicMock()
    ports.coord.commit_artifact.return_value = SimpleNamespace(status="committed", diagnostic=None)
    return ports


# --------------------------------------------------------------------------- #
# T025 / FR-010 — authority-path staging: untracked primary artifacts land in
# the SAME commit_artifact call as the WP file, never on the lane branch.
# --------------------------------------------------------------------------- #


def test_write_and_commit_wp_file_stages_untracked_primary_planning_artifact(
    repo: Path,
) -> None:
    """The untracked ``research-addendum.md`` rides the SAME primary-routed
    ``commit_artifact`` call as the WP file (pin (c): one pass, no retry)."""
    st, wp_file, extra_artifact = _coord_state_with_untracked_artifact(repo)
    ports = _committed_ports()

    with (
        patch(f"{_TASKS}.ProtectionPolicy") as policy_cls,
        patch(f"{_TASKS}._primary_bundle_status_artifacts", return_value=[]),
    ):
        file_written, commit_success, router_result, _status_ref = (
            tasks_move_task._mt_write_and_commit_wp_file(
                st, ports, "updated", "chore: test commit", skip_target_commit=False
            )
        )

    assert file_written is True
    assert commit_success is True
    assert router_result is not None and router_result.status == "committed"
    policy_cls.resolve.assert_called_once_with(repo)
    committed_paths = ports.coord.commit_artifact.call_args.args[1]
    committed_resolved = {p.resolve() for p in committed_paths}
    assert extra_artifact.resolve() in committed_resolved
    assert wp_file.resolve() in committed_resolved
    # The WP file appears exactly once — the staging leg dedupes against the
    # router call's own explicit primary argument.
    assert list(committed_paths).count(wp_file.resolve()) == 1


def test_write_and_commit_wp_file_never_invokes_lane_branch_commit(repo: Path) -> None:
    """Pin (b): the lane-branch commit mechanism (``safe_commit``) is NEVER
    invoked while staging untracked kitty-specs/ planning artifacts — they
    are only ever routed through ``ports.coord.commit_artifact`` (primary/
    coord authority), so the lane branch is never asked to commit
    ``kitty-specs/`` and ``commit_guard.block_mission_specs`` never fires."""
    st, _wp_file, _extra_artifact = _coord_state_with_untracked_artifact(repo)
    ports = _committed_ports()

    with (
        patch(f"{_TASKS}.ProtectionPolicy"),
        patch(f"{_TASKS}._primary_bundle_status_artifacts", return_value=[]),
        patch("specify_cli.git.safe_commit") as safe_commit_mock,
    ):
        _file_written, commit_success, _router_result, _status_ref = (
            tasks_move_task._mt_write_and_commit_wp_file(
                st, ports, "updated", "chore: test commit", skip_target_commit=False
            )
        )

    assert commit_success is True
    safe_commit_mock.assert_not_called()


def test_write_and_commit_wp_file_status_placement_unperturbed_by_staging(
    repo: Path,
) -> None:
    """Pin (a): STATUS_STATE ref is byte-identical before and after the new
    staging leg runs — the authority-path addition never touches placement."""
    st, _wp_file, _extra_artifact = _coord_state_with_untracked_artifact(repo)
    expected_ref = placement_seam(repo, _MISSION_SLUG).write_target(
        MissionArtifactKind.STATUS_STATE
    ).ref
    assert expected_ref == _COORD_BRANCH  # sanity: fixture really is coord-routed

    ref_before = tasks_move_task._mt_resolve_status_placement_ref(st)
    ports = _committed_ports()
    with (
        patch(f"{_TASKS}.ProtectionPolicy"),
        patch(f"{_TASKS}._primary_bundle_status_artifacts", return_value=[]),
    ):
        tasks_move_task._mt_write_and_commit_wp_file(
            st, ports, "updated", "chore: test commit", skip_target_commit=False
        )
    ref_after = tasks_move_task._mt_resolve_status_placement_ref(st)

    assert ref_before == ref_after == _COORD_BRANCH


# --------------------------------------------------------------------------- #
# T025 — the extracted staging helper itself (new branch/helper needs its
# own focused tests per Sonar Expectations).
# --------------------------------------------------------------------------- #


def test_untracked_planning_artifact_paths_excludes_wp_file_itself(repo: Path) -> None:
    st, wp_file, extra_artifact = _coord_state_with_untracked_artifact(repo)

    extra_paths = tasks_move_task._mt_untracked_planning_artifact_paths(st, wp_file)

    resolved = {p.resolve() for p in extra_paths}
    assert extra_artifact.resolve() in resolved
    assert wp_file.resolve() not in resolved


def test_untracked_planning_artifact_paths_degrades_to_empty_on_resolution_failure(
    tmp_path: Path,
) -> None:
    """Best-effort (never raises): an unresolvable mission degrades to an
    empty tuple, mirroring ``_mt_resolve_status_placement_ref``'s
    degrade-never-crash discipline — this staging leg is additive, never a
    new way for the WP-file transition to fail."""
    st = _make_state()
    st.main_repo_root = tmp_path
    st.mission_slug = ""
    st.feature_dir = tmp_path / "nonexistent"
    st.resolved_auto_commit = True

    result = tasks_move_task._mt_untracked_planning_artifact_paths(
        st, tmp_path / "nonexistent" / "tasks" / "WP01.md"
    )

    assert result == ()


# --------------------------------------------------------------------------- #
# T026 / #2580 — the canonical shell_pid writer closes the 4th divergent
# writer in ``_mt_persist_wp_file``.
# --------------------------------------------------------------------------- #


def test_persist_wp_file_shell_pid_routes_through_canonical_writer(repo: Path) -> None:
    """Pin (d): ``_mt_persist_wp_file`` co-writes ``shell_pid`` +
    ``shell_pid_created_at`` byte-identically to what ``write_shell_pid_claim``
    alone would produce from the same starting frontmatter — no parallel,
    baseline-less writer.

    Uses this test process's OWN real pid (realistic test data) so the
    creation-time baseline is genuinely capturable — a fabricated pid would
    make ``capture_creation_time_baseline`` degrade to ``None`` on BOTH sides
    of the comparison and mask a regression that drops the baseline field.
    """
    feature_dir = _build_coord_mission(repo)
    wp_file = feature_dir / "tasks" / "WP01-x.md"
    original_content = "---\nwork_package_id: WP01\ntitle: x\n---\nbody\n"
    wp_file.write_text(original_content, encoding="utf-8")
    original_front, orig_body, orig_padding = split_frontmatter(original_content)
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

    persisted_front, _body, _padding = split_frontmatter(
        wp_file.read_text(encoding="utf-8-sig")
    )
    # Round-trip the expectation through the SAME build_document/split_frontmatter
    # boundary the production code crosses, so the comparison isolates the
    # shell_pid/baseline co-write invariant from split-boundary newline
    # normalization (an unrelated, pre-existing convention of this pair).
    expected_doc = build_document(
        write_shell_pid_claim(original_front, live_pid), orig_body, orig_padding
    )
    expected_front, _expected_body, _expected_padding = split_frontmatter(expected_doc)

    assert persisted_front == expected_front
    assert f'shell_pid: "{live_pid}"' in persisted_front
    assert SHELL_PID_BASELINE_FIELD in persisted_front


# --------------------------------------------------------------------------- #
# T028 (K-4) — arch guard: the WP07 diff must not touch the three
# status-bundling symbols (placement drift would perturb STATUS_STATE
# placement — a second split-brain).
# --------------------------------------------------------------------------- #

# Hashes of the exact source of the two locally-defined protected symbols,
# captured from the pre-WP07 baseline (unchanged by this WP's diff). Any
# future edit to either function — including this WP's own — fails this
# test by construction, forcing a deliberate, reviewed decision rather than
# an incidental drift.
_EXPECTED_PLACEMENT_REF_SHA256 = (
    "42fe33c1ce11cd329112d95a3b7da023ca606d967903553a7816280fa3582908"
)
_EXPECTED_BUNDLE_SHA256 = "9b96497b56f12952121eb9e34f8a1b36a6a98716fe332aa6c345b7c62e64467d"


def _source_sha256(func: Callable[..., object]) -> str:
    # File-integrity source pin (K-4), not a charter content hash — TID251
    # exempts non-charter uses (PKCE, checksums, file-integrity checks).
    return hashlib.sha256(inspect.getsource(func).encode("utf-8")).hexdigest()  # noqa: TID251


def test_wp07_diff_does_not_touch_status_bundling_symbols() -> None:
    assert _source_sha256(tasks_move_task._mt_resolve_status_placement_ref) == (
        _EXPECTED_PLACEMENT_REF_SHA256
    )
    assert _source_sha256(tasks_move_task._primary_bundle_status_artifacts) == (
        _EXPECTED_BUNDLE_SHA256
    )
    # _collect_status_artifacts must stay a pure re-import from
    # tasks_materialization — never a locally shadowed/redefined copy.
    assert (
        tasks_move_task._collect_status_artifacts
        is tasks_materialization._collect_status_artifacts
    )
