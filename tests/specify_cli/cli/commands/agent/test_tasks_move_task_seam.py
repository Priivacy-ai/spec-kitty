"""Layer-4 seam interception tests for the WP05 move_task-family relocation.

Mission ``tasks-py-degod-wave2-01KWH9EQ`` — parity-contract Layer 4 (NFR-002):
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/contracts/parity-contract.md``.

Two batteries (the WP02 pattern, applied to the ``tasks_move_task`` move-set):

1. **Interception** — each test patches ``...agent.tasks.<symbol>`` with a
   sentinel and drives a relocated ``_mt_*`` phase helper (or ``_do_move_task``
   collaborator construction) THROUGH the moved body, asserting the sentinel is
   hit — proving the lazy ``_tasks.<attr>`` seam bridge preserves patch
   interception, not merely import resolution. The C-001 divergence wiring
   (``_skip_target_branch_commit`` pre-gate position + auto-commit gating) is
   pinned explicitly.

2. **Identity** — parametrized ``tasks.<sym> is tasks_move_task.<sym>`` over
   the FULL 26-symbol move-set (binding present and the SAME object; cheap,
   non-fakeable), plus a completeness guard so a def added to
   ``tasks_move_task`` without a battery row goes RED.

Seam checklist (per-symbol evidence):
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.agent import tasks, tasks_move_task
from specify_cli.cli.commands.agent.tasks_move_task import _MoveTaskState
from specify_cli.status import Lane

pytestmark = pytest.mark.fast

_TASKS = "specify_cli.cli.commands.agent.tasks"

#: The definitive WP05 move-set. One row per relocated symbol; the identity
#: battery below parametrizes over ALL of them (no spot-checking).
_MOVE_SET: tuple[str, ...] = (
    "_default_move_task_ports",
    "_MoveTaskState",
    "_mt_warn_worktree_kitty_specs",
    "_mt_resolve_targets",
    "_mt_resolve_feedback",
    "_mt_build_request",
    # #2335: for_review deliverable-recovery pair (porcelain parser + pre-guard
    # auto-commit), re-exported through ``tasks`` like the rest of the family.
    "_lane_deliverable_paths",
    "_mt_commit_lane_deliverables",
    "_mt_gather_review_facts",
    "_mt_fire_override_persist",
    "_mt_done_ancestry_facts",
    "_mt_issue_matrix_facts",
    "_mt_approval_facts",
    "_mt_gather_late_facts",
    "_mt_fire_arbiter_persist",
    "_mt_run_decision",
    "_mt_finalize_plan",
    "_mt_current_event_lane",
    "_mt_hop_review_result",
    "_mt_hop_actor",
    "_mt_emit_transitions",
    "_mt_commit_wp_file",
    "_mt_persist_tracker_refs",
    "_mt_persist_wp_file",
    "_mt_release_review_lock",
    "_mt_execute",
    "_mt_output",
    "_do_move_task",
    # WP09 (FR-008, IC-07): the final registration-shim sweep relocated the
    # six family stragglers that stayed ``tasks.py``-resident at WP05; the
    # identity battery covers them like every other moved symbol.
    "_primary_bundle_status_artifacts",
    "_coord_status_events_path",
    "_status_event_result_fields",
    "_detect_reviewer_name",
    "_detect_arbiter_override",
    "_run_arbiter_override",
    # WP02 (review-regression-gate-01KWX6DF, T004/T005): the for_review
    # pre-review regression-gate hook + its precedence/messaging helpers join
    # the family surface like every other def in this module.
    "_mt_run_pre_review_gate",
    "_mt_resolve_pre_review_workspace",
    "_mt_pre_review_changed_files",
    "_mt_pre_review_gate_with_override_scope",
    "_mt_empty_scope_verdict",
    "_mt_pre_review_gate_verdict",
    "_mt_pre_review_gate_metadata",
    "_mt_pre_review_gate_console_warning",
    "_mt_pre_review_gate_block_message",
    "_mt_review_config_section",
    "_mt_pre_review_block_enabled",
    "_mt_pre_review_scope_override",
    "_pre_review_gate_filter_groups",
    "_pre_review_gate_composite_routing",
    # coord-primary-partition-lock WP05 (T023/T024): the STATUS_STATE seam
    # lookup + the extracted write/commit core + the enriched success message
    # join the family surface like every other def.
    "_mt_resolve_status_placement_ref",
    "_mt_write_and_commit_wp_file",
    "_mt_wp_commit_success_message",
)


class _SentinelHit(Exception):
    """Raised by sentinel patches to prove the patched attribute was called."""


class _StopFlow(Exception):
    """Raised by fake ports to halt a phase helper after the point under test."""


def _make_state(**overrides: Any) -> _MoveTaskState:
    """A minimal ``_MoveTaskState`` (raw command inputs only) with overrides."""
    kwargs: dict[str, Any] = {
        "task_id": "WP01",
        "to": "doing",
        "mission": "034-feature",
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
    field_overrides = {k: v for k, v in overrides.items() if k in kwargs}
    kwargs.update(field_overrides)
    st = _MoveTaskState(**kwargs)
    for key, value in overrides.items():
        if key not in field_overrides:
            setattr(st, key, value)
    return st


# ---------------------------------------------------------------------------
# Interception battery — patch tasks.<symbol>, drive the relocated body,
# assert the sentinel bites. All patches target the ``tasks`` namespace; the
# bodies live in ``tasks_move_task`` (research.md D1 seam bridge).
# ---------------------------------------------------------------------------


def test_c001_pre_gate_intercepts_through_tasks_namespace(tmp_path: Path) -> None:
    """C-001: the ``_skip_target_branch_commit`` pre-gate fires at its original
    position in ``_mt_resolve_targets`` — after auto-commit/mission/branch
    resolution, before everything else — and is reached via ``_tasks.<attr>``,
    so the historical ``tasks``-namespace patches keep intercepting."""
    st = _make_state()
    with (
        patch(f"{_TASKS}.locate_project_root", return_value=tmp_path) as locate_mock,
        patch(f"{_TASKS}._emit_sparse_session_warning") as sparse_mock,
        patch(f"{_TASKS}.get_auto_commit_default", return_value=True) as auto_mock,
        patch(f"{_TASKS}._find_mission_slug", return_value="034-feature") as slug_mock,
        patch(
            f"{_TASKS}._ensure_target_branch_checked_out",
            return_value=(tmp_path, "main"),
        ) as branch_mock,
        patch(
            f"{_TASKS}._skip_target_branch_commit", side_effect=_SentinelHit
        ) as skip_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks_move_task._mt_resolve_targets(st, ports=MagicMock())
    locate_mock.assert_called_once()
    sparse_mock.assert_called_once()
    auto_mock.assert_called_once_with(tmp_path)
    slug_mock.assert_called_once()
    branch_mock.assert_called_once_with(tmp_path, "034-feature", True)
    skip_mock.assert_called_once_with(tmp_path, "034-feature", "main")


def test_c001_pre_gate_not_consulted_when_auto_commit_resolves_false(
    tmp_path: Path,
) -> None:
    """C-001 wiring: with auto-commit resolved False the pre-gate is NOT
    consulted (``skip_target_branch_commit`` stays False by the original
    ternary), and the flow proceeds to the ports read."""
    st = _make_state()
    ports = MagicMock()
    ports.coord.feature_write_dir.side_effect = _StopFlow
    with (
        patch(f"{_TASKS}.locate_project_root", return_value=tmp_path),
        patch(f"{_TASKS}._emit_sparse_session_warning"),
        patch(f"{_TASKS}.get_auto_commit_default", return_value=False),
        patch(f"{_TASKS}._find_mission_slug", return_value="034-feature"),
        patch(
            f"{_TASKS}._ensure_target_branch_checked_out",
            return_value=(tmp_path, "main"),
        ),
        patch(f"{_TASKS}._skip_target_branch_commit") as skip_mock,
        pytest.raises(_StopFlow),
    ):
        tasks_move_task._mt_resolve_targets(st, ports=ports)
    skip_mock.assert_not_called()
    assert st.skip_target_branch_commit is False


def test_patched_decide_transition_intercepts_run_decision() -> None:
    """``tasks.decide_transition`` (sentinel-monkeypatch seam) bites through
    ``_mt_run_decision``'s ``_tasks.<attr>`` route."""
    st = _make_state()
    st.request = cast(Any, MagicMock())
    st.verdict_artifact_path = None  # keeps the OLD-timing override persist inert
    with (
        patch(f"{_TASKS}.decide_transition", side_effect=_SentinelHit) as decide_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks_move_task._mt_run_decision(st)
    decide_mock.assert_called_once_with(st.request)


def test_patched_review_gates_intercept_gather_review_facts() -> None:
    """``tasks._check_unchecked_subtasks`` / ``tasks._validate_ready_for_review``
    bite through ``_mt_gather_review_facts`` and land in the built request."""
    st = _make_state(to="for_review")
    st.target_lane = Lane.FOR_REVIEW
    st.wp = cast(Any, SimpleNamespace(path=Path("WP01-x.md"), frontmatter=""))
    with (
        patch(
            f"{_TASKS}._check_unchecked_subtasks", return_value=["T9"]
        ) as unchecked_mock,
        patch(
            f"{_TASKS}._validate_ready_for_review", return_value=(False, ["fix it"])
        ) as ready_mock,
    ):
        tasks_move_task._mt_gather_review_facts(st)
    unchecked_mock.assert_called_once()
    ready_mock.assert_called_once()
    assert st.request is not None
    assert st.request.unchecked_subtasks == ("T9",)
    assert st.request.review_ready is False
    assert st.request.review_guidance == ("fix it",)


def test_patched_workspace_and_ancestry_intercept_done_facts(tmp_path: Path) -> None:
    """``tasks.resolve_workspace_for_wp`` / ``tasks._wp_branch_merged_into_target``
    bite through ``_mt_done_ancestry_facts``."""
    st = _make_state(to="done")
    st.target_lane = Lane.DONE
    st.main_repo_root = tmp_path
    st.mission_slug = "034-feature"
    st.target_branch = "main"
    with (
        patch(
            f"{_TASKS}.resolve_workspace_for_wp",
            return_value=SimpleNamespace(execution_mode="code_change"),
        ) as ws_mock,
        patch(
            f"{_TASKS}._wp_branch_merged_into_target",
            return_value=(True, "merged via PR"),
        ) as merged_mock,
    ):
        mode, merged, msg = tasks_move_task._mt_done_ancestry_facts(st)
    ws_mock.assert_called_once_with(tmp_path, "034-feature", "WP01")
    merged_mock.assert_called_once()
    assert (mode, merged, msg) == ("code_change", True, "merged via PR")


def test_patched_detect_reviewer_intercepts_approval_facts() -> None:
    """``tasks._detect_reviewer_name`` (module-resident def) bites through
    ``_mt_approval_facts`` when no ``--reviewer`` is given."""
    st = _make_state(to="approved")
    st.target_lane = Lane.APPROVED
    with patch(
        f"{_TASKS}._detect_reviewer_name", return_value="sentinel-reviewer"
    ) as detect_mock:
        reviewer, approval_ref = tasks_move_task._mt_approval_facts(st)
    detect_mock.assert_called_once()
    assert reviewer == "sentinel-reviewer"
    assert approval_ref is not None and approval_ref.startswith("auto-approval:WP01:")


def test_patched_primary_feature_dir_intercepts_issue_matrix_facts(
    tmp_path: Path,
) -> None:
    """``tasks.primary_feature_dir_for_mission`` (the pre30-guard-wiring patch
    seam) bites through ``_mt_issue_matrix_facts``'s ``_tasks.<attr>`` route."""
    st = _make_state(to="approved")
    st.target_lane = Lane.APPROVED
    st.main_repo_root = tmp_path
    st.mission_slug = "034-feature"
    with (
        patch(
            f"{_TASKS}.primary_feature_dir_for_mission", side_effect=_SentinelHit
        ) as primary_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks_move_task._mt_issue_matrix_facts(st)
    primary_mock.assert_called_once()


def test_patched_read_events_intercepts_current_event_lane(tmp_path: Path) -> None:
    """``tasks.read_events_transactional`` bites through ``_mt_current_event_lane``."""
    st = _make_state()
    st.feature_dir = tmp_path
    st.main_repo_root = tmp_path
    st.mission_slug = "034-feature"
    fake_events = [SimpleNamespace(wp_id="WP01", to_lane="in_progress")]
    with patch(
        f"{_TASKS}.read_events_transactional", return_value=fake_events
    ) as events_mock:
        lane = tasks_move_task._mt_current_event_lane(st)
    events_mock.assert_called_once()
    assert lane == "in_progress"


def test_patched_feature_status_lock_intercepts_execute(tmp_path: Path) -> None:
    """``tasks.feature_status_lock`` (top-D7 context-manager seam) bites through
    ``_mt_execute`` before any emit/persist side effect."""
    st = _make_state()
    st.main_repo_root = tmp_path
    st.mission_slug = "034-feature"
    with (
        patch(f"{_TASKS}.feature_status_lock", side_effect=_SentinelHit) as lock_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks_move_task._mt_execute(st, ports=MagicMock())
    lock_mock.assert_called_once_with(tmp_path, "034-feature")


def test_patched_protection_policy_intercepts_commit_wp_file(tmp_path: Path) -> None:
    """``tasks.ProtectionPolicy`` bites through ``_mt_commit_wp_file``'s
    ``_tasks.<attr>`` route and the resolved policy reaches ``commit_artifact``."""
    wp_file = tmp_path / "WP01-x.md"
    wp_file.write_text("body", encoding="utf-8")
    st = _make_state()
    st.main_repo_root = tmp_path
    st.mission_slug = "034-feature"
    st.feature_dir = tmp_path
    st.target_branch = "main"
    st.wp = cast(Any, SimpleNamespace(path=wp_file))
    ports = MagicMock()
    ports.coord.commit_artifact.return_value = SimpleNamespace(
        status="committed", diagnostic=None
    )
    with (
        patch(f"{_TASKS}.ProtectionPolicy") as policy_cls,
        patch(
            f"{_TASKS}._primary_bundle_status_artifacts", return_value=[]
        ) as bundle_mock,
    ):
        tasks_move_task._mt_commit_wp_file(
            st, ports, updated_doc="updated", agent_name="unknown", skip_target_commit=False
        )
    policy_cls.resolve.assert_called_once_with(tmp_path)
    bundle_mock.assert_called_once()
    assert (
        ports.coord.commit_artifact.call_args.kwargs["policy"]
        is policy_cls.resolve.return_value
    )
    assert wp_file.read_text(encoding="utf-8") == "updated"


def test_patched_console_intercepts_tracker_ref_warning(tmp_path: Path) -> None:
    """``tasks.console`` bites through ``_mt_persist_tracker_refs``'s defensive
    warning leg (human output; the moved body prints via ``_tasks.console``)."""
    st = _make_state(json_output=False)
    st.tracker_ref_values = ("#1298",)
    st.wp = cast(Any, SimpleNamespace(path=tmp_path / "missing" / "WP01-x.md"))
    with patch(f"{_TASKS}.console") as console_mock:
        tasks_move_task._mt_persist_tracker_refs(st, skip_target_commit=False)
    assert console_mock.print.call_count == 1
    assert "Failed to persist --tracker-ref" in console_mock.print.call_args.args[0]


def test_patched_output_helpers_intercept_mt_output(tmp_path: Path) -> None:
    """``tasks._status_event_result_fields`` / ``_coord_status_events_path`` /
    ``_output_result`` / ``_check_dependent_warnings`` all bite through
    ``_mt_output`` (the coord skip arm drives the polymorphic envelope)."""
    st = _make_state()
    st.wp = cast(Any, SimpleNamespace(path=tmp_path / "WP01-x.md"))
    st.decision = cast(Any, SimpleNamespace(skip_primary=True))
    st.feature_dir = tmp_path
    st.main_repo_root = tmp_path
    st.mission_slug = "034-feature"
    st.canonical_lane = "in_progress"
    coord_events = tmp_path / "coord" / "status.events.jsonl"
    with (
        patch(
            f"{_TASKS}._status_event_result_fields",
            return_value={"event_id": "01H", "to_lane": "in_progress"},
        ) as fields_mock,
        patch(
            f"{_TASKS}._coord_status_events_path", return_value=coord_events
        ) as coord_mock,
        patch(f"{_TASKS}._output_result") as output_mock,
        patch(f"{_TASKS}._check_dependent_warnings") as warn_mock,
    ):
        tasks_move_task._mt_output(st)
    fields_mock.assert_called_once_with(st.event)
    coord_mock.assert_called_once_with(tmp_path, "034-feature")
    warn_mock.assert_called_once()
    result = output_mock.call_args.args[1]
    assert result["wp_file_update"] == "skipped"
    assert result["status_events_path"] == str(coord_events)


def test_default_ports_constructs_through_tasks_bindings() -> None:
    """The moved ``_default_move_task_ports`` constructs its adapters via the
    ``tasks`` bindings, so ``@patch("...tasks.<Adapter>")`` intercepts
    construction (the WP03 checklist invariant, preserved across the move)."""
    with (
        patch(f"{_TASKS}.seam_coord_router") as router_factory,
        patch(f"{_TASKS}.RealFsReader") as fs_cls,
        patch(f"{_TASKS}.RealGitOps") as git_cls,
        patch(f"{_TASKS}.RealRender") as render_cls,
    ):
        ports = tasks._default_move_task_ports()
    # move_task routes BOTH seams through ``tasks`` (route_emit=True), no target_branch.
    router_factory.assert_called_once_with(route_emit=True)
    assert ports.coord is router_factory.return_value
    assert ports.fs is fs_cls.return_value
    assert ports.git is git_cls.return_value
    assert ports.render is render_cls.return_value


# ---------------------------------------------------------------------------
# Identity battery — binding present AND the same object, for the FULL
# move-set (parity-contract Layer 4 leg (a); cheap and non-fakeable).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("symbol", _MOVE_SET)
def test_tasks_binding_is_tasks_move_task_object(symbol: str) -> None:
    """``tasks.<sym>`` is the SAME object as ``tasks_move_task.<sym>``."""
    assert getattr(tasks, symbol) is getattr(tasks_move_task, symbol)


def test_move_set_matches_tasks_move_task_defs() -> None:
    """The parametrized move-set list is the COMPLETE tasks_move_task surface.

    Guards the identity battery against silently drifting out of sync with
    ``tasks_move_task`` (a def added there without a ``tasks`` re-export row
    would otherwise escape the battery).
    """
    module_defs = {
        name
        for name, obj in vars(tasks_move_task).items()
        if getattr(obj, "__module__", None) == tasks_move_task.__name__
        and callable(obj)
    }
    assert module_defs == set(_MOVE_SET)
