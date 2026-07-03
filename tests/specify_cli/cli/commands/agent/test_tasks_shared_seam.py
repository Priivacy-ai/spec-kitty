"""Layer-4 seam interception tests for the WP02 shared-helper relocation.

Mission ``tasks-py-degod-wave2-01KWH9EQ`` — parity-contract Layer 4 (NFR-002):
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/contracts/parity-contract.md``.

Two batteries:

1. **Interception** — each test patches ``...agent.tasks.<symbol>`` with a
   sentinel and invokes a shared helper THROUGH the ``tasks`` namespace,
   asserting the sentinel is hit. These tests were committed GREEN against the
   pre-move tree (helpers still defined in ``tasks.py``) and must stay green
   after the relocation to ``tasks_shared.py`` — proving the lazy
   ``_tasks.<attr>`` seam bridge preserves patch interception, not merely
   import resolution.

2. **Identity** — parametrized ``tasks.<sym> is tasks_shared.<sym>`` over the
   FULL move-set (binding present and the SAME object; cheap, non-fakeable).

Seam checklist (per-symbol evidence):
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks, tasks_shared
from specify_cli.core.constants import KITTY_SPECS_DIR

pytestmark = pytest.mark.fast

_TASKS = "specify_cli.cli.commands.agent.tasks"

#: The definitive WP02 move-set (T007). One row per relocated symbol; the
#: identity battery below parametrizes over ALL of them (no spot-checking).
_MOVE_SET: tuple[str, ...] = (
    "resolve_primary_branch",
    "_review_currency_check_branch",
    "_RUNTIME_STATE_DENY_LIST",
    "_filter_runtime_state_paths",
    "_emit_sparse_session_warning",
    "_ensure_target_branch_checked_out",
    "_find_mission_slug",
    "_output_result",
    "_output_error",
    "_protected_branch_status_commit_error",
    "_coord_topology_active",
    "_skip_target_branch_commit",
    "_mission_identity_payload",
    "_resolve_git_common_dir",
    "_check_unchecked_subtasks",
    "_validate_ready_for_review",
    "_wp_branch_merged_into_target",
    "_filter_by_planning_tip_content",
    "_list_wp_branch_mission_specs_changes",
    "_list_wp_branch_specs_changes_for_guard",
    "_mark_status_json_payload",
)


class _SentinelHit(Exception):
    """Raised by sentinel patches to prove the patched attribute was called."""


# ---------------------------------------------------------------------------
# Interception battery — patch tasks.<symbol>, invoke a shared helper, assert
# the sentinel bites. Committed green PRE-move; must stay green POST-move.
# ---------------------------------------------------------------------------


def test_patched_console_intercepts_output_error() -> None:
    """``tasks.console`` route: ``_output_error`` human leg prints via it."""
    with patch(f"{_TASKS}.console") as console_mock:
        tasks._output_error(False, "boom")
    console_mock.print.assert_called_once_with("[red]Error:[/red] boom")


def test_patched_console_intercepts_output_result() -> None:
    """``tasks.console`` route: ``_output_result`` human leg prints via it."""
    with patch(f"{_TASKS}.console") as console_mock:
        tasks._output_result(False, {"ignored": True}, "all good")
    console_mock.print.assert_called_once_with("all good")


def test_patched_get_main_repo_root_intercepts_find_mission_slug(tmp_path: Path) -> None:
    """``tasks.get_main_repo_root`` route inside ``_find_mission_slug``."""
    with (
        patch(f"{_TASKS}.get_main_repo_root", side_effect=_SentinelHit) as root_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks._find_mission_slug(
            "tasks-py-degod-wave2-01KWH9EQ", json_output=True, repo_root=tmp_path
        )
    root_mock.assert_called_once_with(tmp_path)


def test_patched_get_main_repo_root_intercepts_ensure_target_branch(tmp_path: Path) -> None:
    """``tasks.get_main_repo_root`` route inside ``_ensure_target_branch_checked_out``."""
    with (
        patch(f"{_TASKS}.get_main_repo_root", side_effect=_SentinelHit) as root_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks._ensure_target_branch_checked_out(
            tmp_path, "tasks-py-degod-wave2-01KWH9EQ", True
        )
    root_mock.assert_called_once_with(tmp_path)


def test_patched_get_main_repo_root_intercepts_check_unchecked_subtasks(tmp_path: Path) -> None:
    """``tasks.get_main_repo_root`` route inside ``_check_unchecked_subtasks``."""
    with (
        patch(f"{_TASKS}.get_main_repo_root", side_effect=_SentinelHit) as root_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks._check_unchecked_subtasks(
            tmp_path, "tasks-py-degod-wave2-01KWH9EQ", "WP01", False
        )
    root_mock.assert_called_once_with(tmp_path)


def test_patched_get_main_repo_root_intercepts_validate_ready_for_review(
    tmp_path: Path,
) -> None:
    """``tasks.get_main_repo_root`` collaborator injection in ``_validate_ready_for_review``.

    The wrapper must bind the injected collaborators from the LIVE ``tasks``
    namespace at call time (not import time), so the historical patch seams
    keep applying after relocation.
    """
    with (
        patch(f"{_TASKS}.get_main_repo_root", side_effect=_SentinelHit) as root_mock,
        pytest.raises(_SentinelHit),
    ):
        tasks._validate_ready_for_review(
            tmp_path, "tasks-py-degod-wave2-01KWH9EQ", "WP01", False
        )
    root_mock.assert_called_once_with(tmp_path)


def test_patched_subprocess_intercepts_resolve_git_common_dir(tmp_path: Path) -> None:
    """``tasks.subprocess`` route inside ``_resolve_git_common_dir``."""
    completed = MagicMock(returncode=0, stdout=f"{tmp_path}/.git\n")
    with patch(f"{_TASKS}.subprocess.run", return_value=completed) as run_mock:
        resolved = tasks._resolve_git_common_dir(tmp_path)
    assert resolved == tmp_path / ".git"
    run_mock.assert_called_once()


def test_patched_coord_topology_intercepts_skip_target_branch_commit(tmp_path: Path) -> None:
    """``tasks._coord_topology_active`` moved-sibling route + short-circuit order.

    With coord topology inactive the ``and`` short-circuits BEFORE the
    protection policy resolve — the verbatim evaluation order is part of the
    contract (no policy I/O on flat missions).
    """
    with (
        patch(f"{_TASKS}._coord_topology_active", return_value=False) as coord_mock,
        patch(f"{_TASKS}.ProtectionPolicy") as policy_mock,
    ):
        result = tasks._skip_target_branch_commit(tmp_path, "some-mission", "main")
    assert result is False
    coord_mock.assert_called_once_with(tmp_path, "some-mission")
    policy_mock.resolve.assert_not_called()


def test_patched_protection_policy_intercepts_skip_target_branch_commit(
    tmp_path: Path,
) -> None:
    """``tasks.ProtectionPolicy`` route: coord active + protected primary → skip."""
    with (
        patch(f"{_TASKS}._coord_topology_active", return_value=True),
        patch(f"{_TASKS}.ProtectionPolicy") as policy_mock,
    ):
        policy_mock.resolve.return_value.is_protected.return_value = True
        result = tasks._skip_target_branch_commit(tmp_path, "some-mission", "main")
    assert result is True
    policy_mock.resolve.assert_called_once_with(tmp_path)
    policy_mock.resolve.return_value.is_protected.assert_called_once_with("main")


def test_patched_protection_policy_intercepts_protected_branch_error(tmp_path: Path) -> None:
    """``tasks.ProtectionPolicy`` route inside ``_protected_branch_status_commit_error``."""
    with patch(f"{_TASKS}.ProtectionPolicy") as policy_mock:
        policy_mock.resolve.return_value.is_protected.return_value = True
        message = tasks._protected_branch_status_commit_error("main", tmp_path, "mark-status")
        policy_mock.resolve.return_value.is_protected.return_value = False
        cleared = tasks._protected_branch_status_commit_error("main", tmp_path, "mark-status")
    assert message is not None and "mark-status" in message and "'main'" in message
    assert cleared is None


def test_patched_workspace_and_subprocess_intercept_wp_branch_merged(tmp_path: Path) -> None:
    """``tasks.resolve_workspace_for_wp`` + ``tasks.subprocess`` routes in the ancestry check."""
    workspace = MagicMock()
    workspace.branch_name = "kitty/mission-x-lane-a"
    rev_parse_ok = MagicMock(returncode=0)
    is_ancestor_ok = MagicMock(returncode=0)
    with (
        patch(f"{_TASKS}.resolve_workspace_for_wp", return_value=workspace) as ws_mock,
        patch(
            f"{_TASKS}.subprocess.run", side_effect=[rev_parse_ok, is_ancestor_ok]
        ) as run_mock,
    ):
        merged, message = tasks._wp_branch_merged_into_target(
            tmp_path, "mission-x", "WP01", "degod-follow-ups"
        )
    assert merged is True
    assert "kitty/mission-x-lane-a" in message
    ws_mock.assert_called_once_with(tmp_path, "mission-x", "WP01")
    assert run_mock.call_count == 2


def test_patched_topology_symbols_intercept_review_currency_branch(tmp_path: Path) -> None:
    """``tasks.resolve_placement_only``/``resolve_topology``/``routes_through_coordination`` routes."""
    placement = MagicMock()
    placement.ref = "kitty/mission-x-coord"
    topology = MagicMock()
    with (
        patch(f"{_TASKS}.resolve_placement_only", return_value=placement) as place_mock,
        patch(f"{_TASKS}.resolve_topology", return_value=topology) as topo_mock,
        patch(
            f"{_TASKS}.routes_through_coordination", return_value=True
        ) as routes_mock,
    ):
        branch = tasks._review_currency_check_branch(
            main_repo_root=tmp_path,
            mission_slug="mission-x",
            target_branch="degod-follow-ups",
            workspace=None,
        )
    assert branch == "kitty/mission-x-coord"
    place_mock.assert_called_once()
    topo_mock.assert_called_once_with(tmp_path, "mission-x")
    routes_mock.assert_called_once_with(topology)


def test_patched_kitty_specs_alias_intercepts_guard(tmp_path: Path) -> None:
    """The dynamically-named ``tasks._list_wp_branch_kitty_specs_changes`` alias
    remains the guard's live patch seam (test_tasks.py precedent, 2 sites)."""
    marker = ["kitty-specs/mission-x/spec.md"]
    with patch(
        f"{_TASKS}._list_wp_branch_kitty_specs_changes", return_value=marker
    ) as alias_mock:
        result = tasks._list_wp_branch_specs_changes_for_guard(tmp_path, "degod-follow-ups")
    assert result == marker
    alias_mock.assert_called_once_with(worktree_path=tmp_path, base_branch="degod-follow-ups")


def test_patched_filter_intercepts_list_wp_branch_changes(tmp_path: Path) -> None:
    """``tasks._filter_by_planning_tip_content`` moved-sibling route in the two-pass list."""
    merge_base = MagicMock(returncode=0, stdout="0123456789abcdef0123456789abcdef01234567\n")
    name_only = MagicMock(returncode=0, stdout="kitty-specs/mission-x/tasks.md\n")
    marker = ["kitty-specs/mission-x/tasks.md"]
    with (
        patch(f"{_TASKS}.subprocess.run", side_effect=[merge_base, name_only]),
        patch(
            f"{_TASKS}._filter_by_planning_tip_content", return_value=marker
        ) as filter_mock,
    ):
        result = tasks._list_wp_branch_mission_specs_changes(tmp_path, "degod-follow-ups")
    assert result == marker
    filter_mock.assert_called_once_with(
        tmp_path, ["kitty-specs/mission-x/tasks.md"], "degod-follow-ups"
    )


def test_patched_locate_project_root_intercepts_list_tasks_command() -> None:
    """``tasks.locate_project_root`` binding stays the live seam for command bodies.

    No WP02-relocated helper calls ``locate_project_root`` (its callers are the
    command bodies that REMAIN in ``tasks.py``); this pins the module binding's
    interception through a real command invocation (top D7 symbol, 66 sites).
    """
    runner = CliRunner()
    with patch(f"{_TASKS}.locate_project_root", return_value=None) as locate_mock:
        result = runner.invoke(
            tasks.app, ["list-tasks", "--json", "--mission", "mission-x"]
        )
    assert result.exit_code == 1
    assert '"error": "Could not locate project root"' in result.stdout
    locate_mock.assert_called_once()


# ---------------------------------------------------------------------------
# Identity battery — binding present AND the same object, for the FULL
# move-set (parity-contract Layer 4 leg (a); cheap and non-fakeable).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("symbol", _MOVE_SET)
def test_tasks_binding_is_tasks_shared_object(symbol: str) -> None:
    """``tasks.<sym>`` is the SAME object as ``tasks_shared.<sym>``."""
    assert getattr(tasks, symbol) is getattr(tasks_shared, symbol)


def test_kitty_specs_dynamic_alias_bound_in_tasks_namespace() -> None:
    """The dynamically-named guard alias stays assigned in ``tasks`` globals.

    ``_list_wp_branch_specs_changes_for_guard`` resolves the alias THROUGH the
    ``tasks`` namespace at call time, so the alias (not only the canonical
    name) must live there — it is the historical patch target.
    """
    alias_name = "_list_wp_branch_" + KITTY_SPECS_DIR.replace("-", "_") + "_changes"
    assert alias_name == "_list_wp_branch_kitty_specs_changes"
    alias = getattr(tasks, alias_name)
    assert alias is tasks_shared._list_wp_branch_mission_specs_changes


def test_move_set_matches_tasks_shared_public_defs() -> None:
    """The parametrized move-set list is the COMPLETE tasks_shared surface.

    Guards the identity battery against silently drifting out of sync with
    ``tasks_shared`` (a def added there without a ``tasks`` re-export row
    would otherwise escape the battery).
    """
    module_defs = {
        name
        for name, obj in vars(tasks_shared).items()
        if getattr(obj, "__module__", None) == tasks_shared.__name__
        and callable(obj)
    }
    module_defs.add("_RUNTIME_STATE_DENY_LIST")
    assert module_defs == set(_MOVE_SET)
