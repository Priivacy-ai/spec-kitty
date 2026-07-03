"""Layer-4 seam interception tests for the WP06 map_requirements-family relocation.

Mission ``tasks-py-degod-wave2-01KWH9EQ`` — parity-contract Layer 4 (NFR-002):
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/contracts/parity-contract.md``.

Two batteries (the WP02/WP05 pattern, applied to the ``tasks_map_requirements``
move-set):

1. **Interception** — each test patches ``...agent.tasks.<symbol>`` with a
   sentinel and drives a relocated ``_mr_*`` phase helper (or
   ``_default_map_requirements_ports`` construction) THROUGH the moved body,
   asserting the sentinel is hit — proving the lazy ``_tasks.<attr>`` seam
   bridge preserves patch interception, not merely import resolution. The
   C-001 divergence wiring (REFUSE-exit-1 through
   ``_protected_branch_status_commit_error`` with NO
   ``_skip_target_branch_commit`` pre-gate) is pinned explicitly.

2. **Identity** — parametrized ``tasks.<sym> is tasks_map_requirements.<sym>``
   over the FULL 14-symbol move-set (binding present and the SAME object;
   cheap, non-fakeable), plus a completeness guard so a def added to
   ``tasks_map_requirements`` without a battery row goes RED.

Seam checklist (per-symbol evidence):
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
import typer

from mission_runtime import CommitTarget
from specify_cli.cli.commands.agent import tasks, tasks_map_requirements
from specify_cli.cli.commands.agent.tasks_map_requirements import _MapReqState

pytestmark = pytest.mark.fast

_TASKS = "specify_cli.cli.commands.agent.tasks"

#: The definitive WP06 move-set. One row per relocated symbol; the identity
#: battery below parametrizes over ALL of them (no spot-checking).
_MOVE_SET: tuple[str, ...] = (
    "_default_map_requirements_ports",
    "_MapReqState",
    "_mr_validate_modes",
    "_mr_resolve_context",
    "_mr_build_new_mappings",
    "_mr_unknown_wp_gate",
    "_mr_resolve_read_dirs",
    "_mr_plan",
    "_mr_gate_offenders",
    "_mr_write_frontmatter",
    "_mr_stale_gate",
    "_mr_auto_commit",
    "_mr_emit_output",
    "_do_map_requirements",
    # WP09 (FR-008, IC-07): the final registration-shim sweep relocated the
    # family straggler that stayed ``tasks.py``-resident at WP06; the identity
    # battery covers it like every other moved symbol.
    "_map_requirements_feature_dir",
)


class _SentinelHit(Exception):
    """Raised by sentinel patches to prove the patched attribute was called."""


def _make_state(**overrides: Any) -> _MapReqState:
    """A minimal ``_MapReqState`` (raw command inputs only) with overrides."""
    kwargs: dict[str, Any] = {
        "wp": "WP01",
        "refs": "FR-001",
        "batch": None,
        "replace": False,
        "tracker_ref": None,
        "mission": "034-feature",
        "json_output": True,
        "auto_commit": None,
    }
    field_overrides = {k: v for k, v in overrides.items() if k in kwargs}
    kwargs.update(field_overrides)
    st = _MapReqState(**kwargs)
    for key, value in overrides.items():
        if key not in field_overrides:
            setattr(st, key, value)
    return st


# ---------------------------------------------------------------------------
# Interception battery — patch tasks.<symbol>, drive the relocated body,
# assert the sentinel bites. All patches target the ``tasks`` namespace; the
# bodies live in ``tasks_map_requirements`` (research.md D1 seam bridge).
# ---------------------------------------------------------------------------


def test_c001_refuse_arm_intercepts_through_tasks_namespace(tmp_path: Path) -> None:
    """C-001 REFUSE arm: with auto-commit resolved on, ``_mr_resolve_context``
    resolves the placement, consults ``_protected_branch_status_commit_error``
    via ``_tasks.<attr>`` and refuses exit-1 — and the ``move_task``-only
    ``_skip_target_branch_commit`` skip pre-gate is NEVER consulted (the
    divergence the coord-harness refuse-arm case T005 pins end-to-end)."""
    st = _make_state(auto_commit=True)
    with (
        patch(f"{_TASKS}.locate_project_root", return_value=tmp_path) as locate_mock,
        patch(f"{_TASKS}._emit_sparse_session_warning") as sparse_mock,
        patch(f"{_TASKS}._find_mission_slug", return_value="034-feature") as slug_mock,
        patch(
            f"{_TASKS}._ensure_target_branch_checked_out",
            return_value=(tmp_path, "main"),
        ) as branch_mock,
        patch(
            "specify_cli.coordination.commit_router._resolve_planning_placement",
            return_value=CommitTarget(ref="main"),
        ) as placement_mock,
        patch(
            f"{_TASKS}._protected_branch_status_commit_error",
            return_value="protected: refuse",
        ) as protected_mock,
        patch(f"{_TASKS}._skip_target_branch_commit") as skip_mock,
        patch(f"{_TASKS}._output_error") as error_mock,
        pytest.raises(typer.Exit) as exc_info,
    ):
        tasks_map_requirements._mr_resolve_context(st)
    assert exc_info.value.exit_code == 1
    locate_mock.assert_called_once()
    sparse_mock.assert_called_once_with(
        tmp_path, command="spec-kitty agent tasks map-requirements"
    )
    slug_mock.assert_called_once()
    branch_mock.assert_called_once_with(tmp_path, "034-feature", True)
    placement_mock.assert_called_once()
    protected_mock.assert_called_once_with(
        "main", tmp_path, "spec-kitty agent tasks map-requirements"
    )
    skip_mock.assert_not_called()
    error_mock.assert_called_once_with(True, "protected: refuse")


def test_c001_protected_gate_not_consulted_when_auto_commit_resolves_false(
    tmp_path: Path,
) -> None:
    """C-001 wiring: with auto-commit resolved False (via the patched
    ``tasks.get_auto_commit_default`` D7 seam) the placement resolution and the
    protected-branch refusal are NOT consulted; ``commit_target`` keeps the
    resolved target branch."""
    st = _make_state(auto_commit=None)
    with (
        patch(f"{_TASKS}.locate_project_root", return_value=tmp_path),
        patch(f"{_TASKS}._emit_sparse_session_warning"),
        patch(f"{_TASKS}._find_mission_slug", return_value="034-feature"),
        patch(
            f"{_TASKS}._ensure_target_branch_checked_out",
            return_value=(tmp_path, "main"),
        ),
        patch(f"{_TASKS}.get_auto_commit_default", return_value=False) as auto_mock,
        patch(
            f"{_TASKS}._protected_branch_status_commit_error"
        ) as protected_mock,
    ):
        tasks_map_requirements._mr_resolve_context(st)
    auto_mock.assert_called_once_with(tmp_path)
    protected_mock.assert_not_called()
    assert st.auto_commit_on is False
    assert st.commit_target.ref == "main"


def test_patched_output_error_intercepts_validate_modes() -> None:
    """``tasks._output_error`` bites through ``_mr_validate_modes``' operator
    mode gate (batch + wp is a refused combination)."""
    st = _make_state(batch='{"WP01": ["FR-001"]}')
    with (
        patch(f"{_TASKS}._output_error", side_effect=_SentinelHit) as error_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks_map_requirements._mr_validate_modes(st)
    error_mock.assert_called_once()


def test_patched_output_error_intercepts_build_new_mappings_bad_json() -> None:
    """``tasks._output_error`` bites through ``_mr_build_new_mappings``'
    malformed ``--batch`` JSON leg."""
    st = _make_state(wp=None, refs=None, batch="{not json")
    with (
        patch(f"{_TASKS}._output_error", side_effect=_SentinelHit) as error_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks_map_requirements._mr_build_new_mappings(st)
    error_mock.assert_called_once()


def test_patched_console_intercepts_unknown_wp_gate_human_leg(tmp_path: Path) -> None:
    """``tasks.console`` bites through ``_mr_unknown_wp_gate``'s human error
    leg (the moved body prints via ``_tasks.console``)."""
    (tmp_path / "WP01-x.md").write_text("body", encoding="utf-8")
    st = _make_state(json_output=False)
    st.tasks_dir = tmp_path
    st.new_mappings = {"WP99": ["FR-001"]}
    with (
        patch(f"{_TASKS}.console") as console_mock,
        pytest.raises(typer.Exit) as exc_info,
    ):
        tasks_map_requirements._mr_unknown_wp_gate(st)
    assert exc_info.value.exit_code == 1
    assert console_mock.print.call_count == 2
    assert "Unknown WP IDs" in console_mock.print.call_args_list[0].args[0]


def test_patched_render_intercepts_unknown_wp_gate_json_leg(tmp_path: Path) -> None:
    """``tasks.RealRender`` bites through ``_mr_unknown_wp_gate``'s ``--json``
    error leg (envelope construction via ``_tasks.RealRender()``)."""
    st = _make_state(json_output=True)
    st.tasks_dir = tmp_path
    st.new_mappings = {"WP99": ["FR-001"]}
    with (
        patch(f"{_TASKS}.RealRender") as render_cls,
        pytest.raises(typer.Exit),
    ):
        tasks_map_requirements._mr_unknown_wp_gate(st)
    render_cls.assert_called_once_with()
    payload = render_cls.return_value.json_envelope.call_args.args[0]
    assert payload["unknown_wps"] == ["WP99"]


def test_patched_map_requirements_feature_dir_intercepts_resolve_read_dirs(
    tmp_path: Path,
) -> None:
    """``tasks._map_requirements_feature_dir`` (the pre30-guard-wiring patch
    seam, tests/upgrade/test_pre30_guard_wiring.py) bites through
    ``_mr_resolve_read_dirs``'s ``_tasks.<attr>`` route."""
    st = _make_state()
    st.main_repo_root = tmp_path
    st.mission_slug = "034-feature"
    with (
        patch(
            f"{_TASKS}._map_requirements_feature_dir", side_effect=_SentinelHit
        ) as dir_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks_map_requirements._mr_resolve_read_dirs(st, ports=MagicMock())
    dir_mock.assert_called_once_with(tmp_path, "034-feature")


def test_patched_plan_mapping_intercepts_mr_plan(tmp_path: Path) -> None:
    """``tasks.plan_mapping`` (sentinel-monkeypatch seam,
    test_tasks_mapping_core.py) bites through ``_mr_plan``'s ``_tasks.<attr>``
    route."""
    st = _make_state()
    st.tasks_dir = tmp_path
    st.feature_dir = tmp_path
    st.all_spec_ids = {"FR-001"}
    st.functional_ids = {"FR-001"}
    st.new_mappings = {"WP01": ["FR-001"]}
    with (
        patch(f"{_TASKS}.plan_mapping", side_effect=_SentinelHit) as plan_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks_map_requirements._mr_plan(st)
    request = plan_mock.call_args.args[0]
    assert request.mode == "wp_refs"
    assert request.new_mappings == {"WP01": ["FR-001"]}


def test_patched_render_intercepts_stale_gate_json_leg(tmp_path: Path) -> None:
    """``tasks.RealRender`` bites through ``_mr_stale_gate``'s post-write
    refusal ``--json`` leg (stale refs found on disk)."""
    (tmp_path / "WP01-x.md").write_text(
        "---\nwork_package_id: WP01\nrequirement_refs:\n- FR-999\n---\nbody",
        encoding="utf-8",
    )
    st = _make_state(json_output=True)
    st.tasks_dir = tmp_path
    st.all_spec_ids = {"FR-001"}
    with (
        patch(f"{_TASKS}.RealRender") as render_cls,
        pytest.raises(typer.Exit) as exc_info,
    ):
        tasks_map_requirements._mr_stale_gate(st)
    assert exc_info.value.exit_code == 1
    payload = render_cls.return_value.json_envelope.call_args.args[0]
    assert payload["stale_refs"] == {"WP01": ["FR-999"]}


def test_patched_protection_policy_intercepts_auto_commit(tmp_path: Path) -> None:
    """``tasks.ProtectionPolicy`` bites through ``_mr_auto_commit``'s
    ``_tasks.<attr>`` route and the resolved policy reaches the ports
    ``commit_artifact`` capability."""
    wp_file = tmp_path / "WP01-x.md"
    wp_file.write_text("body", encoding="utf-8")
    st = _make_state()
    st.auto_commit_on = True
    st.tasks_dir = tmp_path
    st.main_repo_root = tmp_path
    st.mission_slug = "034-feature"
    st.new_mappings = {"WP01": ["FR-001"]}
    ports = MagicMock()
    ports.coord.commit_artifact.return_value = SimpleNamespace(
        status="committed", commit_hash="abc123", placement_ref="main"
    )
    with patch(f"{_TASKS}.ProtectionPolicy") as policy_cls:
        tasks_map_requirements._mr_auto_commit(st, ports)
    policy_cls.resolve.assert_called_once_with(tmp_path)
    assert (
        ports.coord.commit_artifact.call_args.kwargs["policy"]
        is policy_cls.resolve.return_value
    )
    assert st.committed is True
    assert st.commit_sha == "abc123"
    assert st.commit_result_payload == {
        "sha": "abc123",
        "destination_ref": "main",
        "worktree_root": str(tmp_path),
    }


def test_patched_console_intercepts_auto_commit_warning(tmp_path: Path) -> None:
    """``tasks.console`` bites through ``_mr_auto_commit``'s defensive
    warning leg (commit failure on the human output path)."""
    wp_file = tmp_path / "WP01-x.md"
    wp_file.write_text("body", encoding="utf-8")
    st = _make_state(json_output=False)
    st.auto_commit_on = True
    st.tasks_dir = tmp_path
    st.main_repo_root = tmp_path
    st.mission_slug = "034-feature"
    st.new_mappings = {"WP01": ["FR-001"]}
    ports = MagicMock()
    ports.coord.commit_artifact.side_effect = RuntimeError("boom")
    with (
        patch(f"{_TASKS}.ProtectionPolicy"),
        patch(f"{_TASKS}.console") as console_mock,
    ):
        tasks_map_requirements._mr_auto_commit(st, ports)
    assert console_mock.print.call_count == 1
    assert "Auto-commit skipped" in console_mock.print.call_args.args[0]


def test_patched_identity_payload_intercepts_emit_output(tmp_path: Path) -> None:
    """``tasks._mission_identity_payload`` / ``tasks.RealRender`` bite through
    ``_mr_emit_output``'s success-envelope reconstruction (``--json`` leg)."""
    st = _make_state(json_output=True)
    st.tasks_dir = tmp_path
    st.primary_dir = tmp_path
    st.functional_ids = {"FR-001"}
    st.new_mappings = {"WP01": ["FR-001"]}
    st.mapping_plan = cast(Any, SimpleNamespace(unmapped_fr=[]))
    with (
        patch(
            f"{_TASKS}._mission_identity_payload",
            return_value={"mission_id": "01SENTINEL"},
        ) as identity_mock,
        patch(f"{_TASKS}.RealRender") as render_cls,
    ):
        tasks_map_requirements._mr_emit_output(st)
    identity_mock.assert_called_once_with(tmp_path)
    payload = render_cls.return_value.json_envelope.call_args.args[0]
    assert payload["mission_id"] == "01SENTINEL"
    assert payload["result"] == "success"
    assert payload["coverage"]["mapped_functional"] == 1


def test_patched_output_error_intercepts_do_map_requirements_exception_arm() -> None:
    """``tasks._output_error`` bites through ``_do_map_requirements``' generic
    exception arm (exit-1 translation). The failure is injected through the
    routed ``tasks.locate_project_root`` D7 seam — the orchestrator reaches its
    ``_mr_*`` phase siblings by bare same-module name (the ratchet-closure
    invariant), so the phases themselves are deliberately NOT patch targets."""
    with (
        patch(
            f"{_TASKS}.locate_project_root", side_effect=RuntimeError("boom")
        ),
        patch(f"{_TASKS}._output_error") as error_mock,
        pytest.raises(typer.Exit) as exc_info,
    ):
        tasks_map_requirements._do_map_requirements(
            wp="WP01",
            refs="FR-001",
            batch=None,
            replace=False,
            tracker_ref=None,
            mission="034-feature",
            json_output=True,
            auto_commit=None,
        )
    assert exc_info.value.exit_code == 1
    error_mock.assert_called_once_with(True, "boom")


def test_default_ports_constructs_through_tasks_bindings() -> None:
    """The moved ``_default_map_requirements_ports`` constructs its adapters
    via the ``tasks`` bindings, so ``@patch("...tasks.<Adapter>")`` intercepts
    construction (the WP03 checklist invariant, preserved across the move) —
    and the coord router carries the resolved ``target_branch``."""
    with (
        patch(f"{_TASKS}.seam_coord_router") as router_factory,
        patch(f"{_TASKS}.RealFsReader") as fs_cls,
        patch(f"{_TASKS}.RealGitOps") as git_cls,
        patch(f"{_TASKS}.RealRender") as render_cls,
    ):
        ports = tasks._default_map_requirements_ports("main")
    # map_requirements threads the resolved target_branch (ff-advance parity).
    router_factory.assert_called_once_with(thread_target_branch=True, target_branch="main")
    assert ports.coord is router_factory.return_value
    assert ports.fs is fs_cls.return_value
    assert ports.git is git_cls.return_value
    assert ports.render is render_cls.return_value


# ---------------------------------------------------------------------------
# Identity battery — binding present AND the same object, for the FULL
# move-set (parity-contract Layer 4 leg (a); cheap and non-fakeable).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("symbol", _MOVE_SET)
def test_tasks_binding_is_tasks_map_requirements_object(symbol: str) -> None:
    """``tasks.<sym>`` is the SAME object as ``tasks_map_requirements.<sym>``."""
    assert getattr(tasks, symbol) is getattr(tasks_map_requirements, symbol)


def test_move_set_matches_tasks_map_requirements_defs() -> None:
    """The parametrized move-set list is the COMPLETE tasks_map_requirements
    surface.

    Guards the identity battery against silently drifting out of sync with
    ``tasks_map_requirements`` (a def added there without a ``tasks`` re-export
    row would otherwise escape the battery).
    """
    module_defs = {
        name
        for name, obj in vars(tasks_map_requirements).items()
        if getattr(obj, "__module__", None) == tasks_map_requirements.__name__
        and callable(obj)
    }
    assert module_defs == set(_MOVE_SET)
