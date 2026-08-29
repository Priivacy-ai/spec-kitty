"""WP11 focused unit tests for the pure ``sync workspace`` decision core.

The *rendered* behaviour-lock is the WP11 monkeypatch-golden
(``tests/characterization/test_sync_workspace_render.py``). These tests drive the
pure core — :func:`build_sync_render_plan` and :func:`sync_stats_summary` — over
every ``SyncStatus`` arm, the verbose toggle, the stats permutations, and the
FAILED exit decision, with no I/O and no ``Console`` in sight. They are the
branch-level new-code coverage the extraction adds (Sonar new-code-coverage).
"""

from __future__ import annotations

import pytest

from pathlib import Path
from typing import Any

from specify_cli.core.vcs import ConflictInfo, SyncResult, SyncStatus
from specify_cli.core.vcs.types import ConflictType
from specify_cli.sync.sync_workspace_core import (
    NOT_IN_WORKSPACE_EXIT,
    NOT_IN_WORKSPACE_LINES,
    RenderChanges,
    RenderConflicts,
    RenderLine,
    build_sync_render_plan,
    sync_stats_summary,
)


def _result(status: SyncStatus, **overrides: Any) -> SyncResult:
    base: dict[str, Any] = {
        "status": status,
        "conflicts": [],
        "files_updated": 0,
        "files_added": 0,
        "files_deleted": 0,
        "changes_integrated": [],
        "message": "",
    }
    base.update(overrides)
    return SyncResult(**base)


def _conflict() -> ConflictInfo:
    return ConflictInfo(
        file_path=Path("src/x.py"),
        conflict_type=ConflictType.CONTENT,
        line_ranges=None,
        sides=2,
        is_resolved=False,
        our_content=None,
        their_content=None,
        base_content=None,
    )


def _line_texts(plan_steps: tuple[object, ...]) -> list[str]:
    return [s.text for s in plan_steps if isinstance(s, RenderLine)]


# ---------------------------------------------------------------------------
# sync_stats_summary
# ---------------------------------------------------------------------------

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


def test_stats_summary_all_zero_is_no_file_changes() -> None:
    assert sync_stats_summary(_result(SyncStatus.SYNCED)) == "no file changes"


def test_stats_summary_only_nonzero_counts_in_order() -> None:
    result = _result(SyncStatus.SYNCED, files_updated=3, files_added=0, files_deleted=2)
    assert sync_stats_summary(result) == "3 updated, 2 deleted"


def test_stats_summary_all_three() -> None:
    result = _result(SyncStatus.SYNCED, files_updated=1, files_added=2, files_deleted=3)
    assert sync_stats_summary(result) == "1 updated, 2 added, 3 deleted"


# ---------------------------------------------------------------------------
# UP_TO_DATE arm
# ---------------------------------------------------------------------------


def test_up_to_date_no_message_single_line_no_exit() -> None:
    plan = build_sync_render_plan(_result(SyncStatus.UP_TO_DATE), verbose=False)
    assert plan.exit_code is None
    assert _line_texts(plan.steps) == ["\n[green]✓ Already up to date[/green]"]


def test_up_to_date_with_message_appends_dim_line() -> None:
    plan = build_sync_render_plan(_result(SyncStatus.UP_TO_DATE, message="tip"), verbose=False)
    assert _line_texts(plan.steps)[-1] == "[dim]tip[/dim]"


# ---------------------------------------------------------------------------
# SYNCED arm
# ---------------------------------------------------------------------------


def test_synced_non_verbose_has_no_changes_step() -> None:
    plan = build_sync_render_plan(_result(SyncStatus.SYNCED, files_updated=1, changes_integrated=[]), verbose=False)
    assert plan.exit_code is None
    assert not any(isinstance(s, RenderChanges) for s in plan.steps)
    assert _line_texts(plan.steps)[0] == "\n[green]✓ Synced[/green] - 1 updated"


def test_synced_verbose_inserts_changes_step_before_message() -> None:
    plan = build_sync_render_plan(_result(SyncStatus.SYNCED, files_updated=1, message="done"), verbose=True)
    kinds = [type(s).__name__ for s in plan.steps]
    assert kinds == ["RenderLine", "RenderChanges", "RenderLine"]
    assert _line_texts(plan.steps)[-1] == "[dim]done[/dim]"


# ---------------------------------------------------------------------------
# CONFLICTS arm
# ---------------------------------------------------------------------------


def test_conflicts_non_verbose_emits_conflicts_step_no_changes() -> None:
    plan = build_sync_render_plan(_result(SyncStatus.CONFLICTS, conflicts=[_conflict()]), verbose=False)
    assert plan.exit_code is None
    assert any(isinstance(s, RenderConflicts) for s in plan.steps)
    assert not any(isinstance(s, RenderChanges) for s in plan.steps)
    assert _line_texts(plan.steps)[0] == "\n[yellow]⚠ Synced with conflicts[/yellow]"


def test_conflicts_verbose_appends_changes_step() -> None:
    plan = build_sync_render_plan(_result(SyncStatus.CONFLICTS, conflicts=[_conflict()]), verbose=True)
    assert any(isinstance(s, RenderChanges) for s in plan.steps)


# ---------------------------------------------------------------------------
# FAILED arm (exit 1)
# ---------------------------------------------------------------------------


def test_failed_arm_exits_1_with_try_hint() -> None:
    plan = build_sync_render_plan(_result(SyncStatus.FAILED, message="boom"), verbose=False)
    assert plan.exit_code == 1
    texts = _line_texts(plan.steps)
    assert texts[0] == "\n[red]✗ Sync failed[/red]"
    assert "[dim]boom[/dim]" in texts
    assert "  spec-kitty sync workspace --repair" in texts


def test_failed_arm_with_conflicts_inserts_conflicts_step() -> None:
    plan = build_sync_render_plan(_result(SyncStatus.FAILED, conflicts=[_conflict()]), verbose=False)
    assert any(isinstance(s, RenderConflicts) for s in plan.steps)


def test_failed_arm_without_conflicts_has_no_conflicts_step() -> None:
    plan = build_sync_render_plan(_result(SyncStatus.FAILED), verbose=False)
    assert not any(isinstance(s, RenderConflicts) for s in plan.steps)


# ---------------------------------------------------------------------------
# not-in-workspace constants
# ---------------------------------------------------------------------------


def test_not_in_workspace_constants_are_frozen_lines_and_exit_1() -> None:
    assert NOT_IN_WORKSPACE_EXIT == 1
    assert NOT_IN_WORKSPACE_LINES[0] == "[yellow]⚠ Not in a recognized workspace[/yellow]"
    assert any(".worktrees/" in line for line in NOT_IN_WORKSPACE_LINES)
