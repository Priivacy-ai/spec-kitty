"""``move-task`` STATUS_STATE placement routing (coord-primary-partition-lock WP05).

WP05 (T022-T024, FR-004/FR-005, C-001/C-005/C-006) closes the last write
bypass D6 names on this surface: the WP-file auto-commit path
(``_mt_commit_wp_file``) reported bookkeeping placement purely from
``st.target_branch`` — the CURRENT-CHECKOUT branch
``_ensure_target_branch_checked_out`` resolves (see its own docstring:
"respects user's current branch") — never consulting the ONE kind-aware
placement authority (``mission_runtime.placement_seam(...)
.write_target(MissionArtifactKind.STATUS_STATE)``, contracts/seam-api.md).
Under coordination topology the two answers genuinely diverge (STATUS_STATE
routes to the coordination branch; the checkout can be anywhere), so a
checkout-derived answer is a real placement bug, not just a style nit.

RED-FIRST (T022, pre-fix): ``tasks_move_task`` carries no
``_mt_resolve_status_placement_ref`` / ``_mt_write_and_commit_wp_file`` split
at all — every symbol asserted below raises ``AttributeError`` against the
pre-WP05 module. POST-fix (T024): the WP-file commit helper resolves
STATUS_STATE via the seam BEFORE routing (T023 extraction), and the resolved
ref is independent of whatever ``st.target_branch`` happens to hold.

Fixture data mirrors ``tests/mission_runtime/test_placement_seam.py`` (real
git repo, real 26-char ULID mission_id, real coordination branch) — no
synthetic short IDs (realistic test data).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from mission_runtime import MissionTopology, placement_seam, routes_through_coordination
from mission_runtime.artifacts import MissionArtifactKind
from specify_cli.cli.commands.agent import tasks_move_task
from specify_cli.cli.commands.agent.tasks_move_task import _MoveTaskState

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

_TASKS = "specify_cli.cli.commands.agent.tasks"

# Realistic identity (mirrors test_placement_seam.py): a real 26-char
# Crockford ULID and its derived 8-char mid8 prefix.
_MISSION_ID = "01KWZ46V5P3QY7M8N0RAB4CDEF"
_MID8 = _MISSION_ID[:8]
_MISSION_SLUG = f"coord-primary-partition-lock-{_MID8}"
_TARGET_BRANCH = "design/coord-primary-partition-lock"
_COORD_BRANCH = f"kitty/mission-{_MISSION_SLUG}-{_MID8}"
# The branch the OPERATOR happens to have checked out — deliberately NEITHER
# the primary target branch NOR the coordination branch, so a test that
# passes only because it echoes ``st.target_branch`` is impossible: the
# seam-resolved STATUS_STATE ref can never accidentally equal this value.
_OPERATOR_CHECKOUT_BRANCH = "kitty/mission-unrelated-scratch-lane"


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


def _build_mission(repo_root: Path, *, topology: MissionTopology) -> Path:
    """Build a mission whose STORED topology is ``topology`` (mirrors T003 fixture)."""
    from specify_cli.missions._read_path_resolver import coord_feature_dir

    feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True)
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "target_branch": _TARGET_BRANCH,
        "friendly_name": "Coord/primary partition lock",
        "topology": topology.value,
    }
    if routes_through_coordination(topology):
        meta["coordination_branch"] = _COORD_BRANCH
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (feature_dir / "tasks").mkdir()
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-q", "-m", "fixture")

    if routes_through_coordination(topology):
        _git(repo_root, "branch", _COORD_BRANCH)
        coord_dir = coord_feature_dir(repo_root, _MISSION_SLUG, _MID8)
        coord_dir.mkdir(parents=True)
        (coord_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

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
# T022 — RED-FIRST: the seam is the ONE authority for STATUS_STATE placement.
# --------------------------------------------------------------------------- #


def test_status_placement_ref_matches_seam_under_coord_topology(repo: Path) -> None:
    """The resolved STATUS_STATE placement is the seam's answer, not the checkout.

    ``st.target_branch`` is deliberately set to a THIRD branch (neither the
    primary target nor the coordination branch) — the operator's current
    checkout. If the production code derived placement from ``st.target_branch``
    (the pre-WP05 bug), the resolved ref would equal
    ``_OPERATOR_CHECKOUT_BRANCH`` or ``_TARGET_BRANCH``; instead it must equal
    the coordination branch the seam independently resolves.
    """
    _build_mission(repo, topology=MissionTopology.COORD)
    expected_ref = placement_seam(repo, _MISSION_SLUG).write_target(
        MissionArtifactKind.STATUS_STATE
    ).ref
    assert expected_ref == _COORD_BRANCH  # sanity: fixture really is coord-routed

    st = _make_state()
    st.main_repo_root = repo
    st.mission_slug = _MISSION_SLUG
    st.target_branch = _OPERATOR_CHECKOUT_BRANCH

    resolved_ref = tasks_move_task._mt_resolve_status_placement_ref(st)

    assert resolved_ref == expected_ref
    assert resolved_ref != st.target_branch
    assert resolved_ref != _TARGET_BRANCH


def test_status_placement_ref_matches_target_branch_under_flat_topology(repo: Path) -> None:
    """Non-regression: a flat/single-branch mission has no coord split.

    STATUS_STATE and WORK_PACKAGE_TASK both resolve to the primary target
    branch (C-001 — the coord-less cells have no primary<->coordination
    split), independent of whatever the operator has checked out.
    """
    _build_mission(repo, topology=MissionTopology.SINGLE_BRANCH)
    st = _make_state()
    st.main_repo_root = repo
    st.mission_slug = _MISSION_SLUG
    st.target_branch = _OPERATOR_CHECKOUT_BRANCH

    resolved_ref = tasks_move_task._mt_resolve_status_placement_ref(st)

    assert resolved_ref == _TARGET_BRANCH


def test_status_placement_ref_degrades_to_none_on_unresolvable_mission(tmp_path: Path) -> None:
    """Best-effort (never raises): an unresolvable mission degrades to ``None``.

    Mirrors ``_mt_run_pre_review_gate``'s degrade-never-crash discipline —
    bookkeeping-placement observability is additive, never a gate. An empty
    ``mission_slug`` is ``resolve_placement_only``'s own explicit
    ``ActionContextError`` trigger (never a silent fallback there either) —
    this proves the WP-file commit path swallows that failure rather than
    propagating it.
    """
    st = _make_state()
    st.main_repo_root = tmp_path
    st.mission_slug = ""
    st.target_branch = "main"

    assert tasks_move_task._mt_resolve_status_placement_ref(st) is None


# --------------------------------------------------------------------------- #
# T023/T024 — the extracted write+commit helper resolves placement BEFORE
# routing, and stays composable with the skip-gate + #2438 review gate.
# --------------------------------------------------------------------------- #


def test_write_and_commit_wp_file_resolves_placement_before_committing(
    repo: Path,
) -> None:
    """``_mt_write_and_commit_wp_file`` returns the seam-resolved ref alongside
    the commit outcome, and the primary WORK_PACKAGE_TASK commit still fires."""
    _build_mission(repo, topology=MissionTopology.COORD)
    wp_file = repo / "kitty-specs" / _MISSION_SLUG / "tasks" / "WP01-x.md"
    wp_file.write_text("body", encoding="utf-8")

    st = _make_state()
    st.main_repo_root = repo
    st.mission_slug = _MISSION_SLUG
    st.feature_dir = repo / "kitty-specs" / _MISSION_SLUG
    st.target_branch = _OPERATOR_CHECKOUT_BRANCH
    st.wp = cast(Any, SimpleNamespace(path=wp_file))

    ports = MagicMock()
    ports.coord.commit_artifact.return_value = SimpleNamespace(status="committed", diagnostic=None)

    with (
        patch(f"{_TASKS}.ProtectionPolicy") as policy_cls,
        patch(f"{_TASKS}._primary_bundle_status_artifacts", return_value=[]) as bundle_mock,
    ):
        file_written, commit_success, router_result, status_placement_ref = (
            tasks_move_task._mt_write_and_commit_wp_file(
                st, ports, "updated", "chore: test commit", skip_target_commit=False
            )
        )

    assert file_written is True
    assert commit_success is True
    assert router_result is not None and router_result.status == "committed"
    assert status_placement_ref == _COORD_BRANCH
    policy_cls.resolve.assert_called_once_with(repo)
    bundle_mock.assert_called_once()
    assert ports.coord.commit_artifact.call_args.kwargs["kind"] is MissionArtifactKind.WORK_PACKAGE_TASK
    assert wp_file.read_text(encoding="utf-8") == "updated"


def test_write_and_commit_wp_file_skip_gate_composes_with_placement_resolution(
    repo: Path, tmp_path: Path
) -> None:
    """The pre-existing ``_skip_target_branch_commit`` skip arm still short-
    circuits the WRITE (C-001) — the new placement lookup composes with it
    (runs first, informational-only) rather than replacing or racing it."""
    _build_mission(repo, topology=MissionTopology.COORD)
    wp_file = tmp_path / "WP01-x.md"
    st = _make_state(json_output=True)
    st.main_repo_root = repo
    st.mission_slug = _MISSION_SLUG
    st.feature_dir = repo / "kitty-specs" / _MISSION_SLUG
    st.target_branch = _TARGET_BRANCH
    st.wp = cast(Any, SimpleNamespace(path=wp_file))

    ports = MagicMock()
    ports.coord.commit_artifact.side_effect = AssertionError(
        "commit_artifact must NOT be called on the skip arm"
    )

    file_written, commit_success, router_result, status_placement_ref = (
        tasks_move_task._mt_write_and_commit_wp_file(
            st, ports, "updated", "chore: test commit", skip_target_commit=True
        )
    )

    assert file_written is False
    assert commit_success is False
    assert router_result is None
    # Placement resolution still ran (composability), independent of the skip.
    assert status_placement_ref == _COORD_BRANCH
    assert not wp_file.exists()  # skip arm never writes


# --------------------------------------------------------------------------- #
# T025 — success message enrichment + non-regression for the plain path.
# --------------------------------------------------------------------------- #


def test_wp_commit_success_message_enriches_when_status_diverges_from_checkout() -> None:
    st = _make_state()
    st.target_branch = _TARGET_BRANCH
    message = tasks_move_task._mt_wp_commit_success_message(st, _COORD_BRANCH)
    assert _TARGET_BRANCH in message
    assert _COORD_BRANCH in message


def test_wp_commit_success_message_stays_plain_when_no_divergence() -> None:
    st = _make_state()
    st.target_branch = _TARGET_BRANCH
    message = tasks_move_task._mt_wp_commit_success_message(st, _TARGET_BRANCH)
    assert message == f"[cyan]→ Committed status change to {_TARGET_BRANCH} branch[/cyan]"


def test_wp_commit_success_message_stays_plain_when_placement_unresolvable() -> None:
    """Non-regression (test_patched_protection_policy_intercepts_commit_wp_file
    sibling): a degraded ``None`` placement produces the ORIGINAL message
    verbatim — the enrichment is purely additive."""
    st = _make_state()
    st.target_branch = _TARGET_BRANCH
    message = tasks_move_task._mt_wp_commit_success_message(st, None)
    assert message == f"[cyan]→ Committed status change to {_TARGET_BRANCH} branch[/cyan]"
