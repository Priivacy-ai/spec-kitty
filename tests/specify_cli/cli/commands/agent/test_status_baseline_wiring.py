"""End-to-end wiring: the CLI staleness reader threads the PID-reuse baseline (#2575).

WP02 co-writes a ``shell_pid_created_at`` identity baseline alongside ``shell_pid``
at every claim site, and ``core.stale_detection`` compares it. This file proves the
fix is NOT dormant: the CLI status reader (``tasks_status_cmd``) actually surfaces
the baseline into the per-WP row dicts that feed ``check_doing_wps_for_staleness``,
so a recycled PID (live PID + mismatched baseline) is caught as stale-eligible
through the real consumer — not merely by the unit-level companion.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent import tasks_status_cmd
from specify_cli.cli.commands.agent.tasks_status_cmd import _StatusState, _st_load_work_packages
from specify_cli.core.stale_detection import LIVE_CLAIM_PROCESS_REASON, check_doing_wps_for_staleness
from specify_cli.frontmatter import SHELL_PID_BASELINE_FIELD
from specify_cli.workspace.context import ResolvedWorkspace

pytestmark = pytest.mark.fast


def _write_wp(tasks_dir: Path, *, shell_pid: str, baseline: str | None) -> None:
    tasks_dir.mkdir(parents=True, exist_ok=True)
    baseline_line = f'{SHELL_PID_BASELINE_FIELD}: "{baseline}"\n' if baseline is not None else ""
    (tasks_dir / "WP01.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Example\n"
        "phase: Phase 1\n"
        "agent: claude\n"
        f'shell_pid: "{shell_pid}"\n'
        f"{baseline_line}"
        "history: []\n"
        "---\n\n# Body\n",
        encoding="utf-8",
    )


def _lane_workspace(tmp_path: Path) -> ResolvedWorkspace:
    """A resolvable lane workspace (has a ``.git`` marker so ``.exists`` is True)."""
    lane_dir = tmp_path / ".worktrees" / "mission-lane-a"
    lane_dir.mkdir(parents=True, exist_ok=True)
    (lane_dir / ".git").write_text("gitdir: /somewhere\n", encoding="utf-8")
    return ResolvedWorkspace(
        mission_slug="mission",
        wp_id="WP01",
        execution_mode="code_change",
        mode_source="test",
        resolution_kind="lane_workspace",
        workspace_name="mission-lane-a",
        worktree_path=lane_dir,
        branch_name="kitty/mission-lane-a",
        lane_id="a",
        lane_wp_ids=["WP01"],
    )


def test_cli_reader_threads_baseline_into_row_dict(tmp_path: Path) -> None:
    """``_st_load_work_packages`` surfaces ``shell_pid_created_at`` into each WP row dict.

    This is the field the two ``check_doing_wps_for_staleness`` callers
    (``_st_emit_json`` and ``_st_render_human``, which share the same row objects
    via ``_kanban_rollup``) read as ``wp.get(SHELL_PID_BASELINE_FIELD)``.
    """
    tasks_dir = tmp_path / "tasks"
    _write_wp(tasks_dir, shell_pid="4242", baseline="1700000000.5")

    st = _StatusState(mission="mission", json_output=True, stale_threshold=10)
    st.mission_slug = "mission"
    st.main_repo_root = tmp_path
    st.feature_dir = tmp_path
    st.tasks_dir = tasks_dir

    _st_load_work_packages(st)

    assert len(st.work_packages) == 1
    row = st.work_packages[0]
    assert row["shell_pid"] == "4242"
    assert row[SHELL_PID_BASELINE_FIELD] == "1700000000.5"


def test_cli_reader_baseline_absent_defaults_to_none(tmp_path: Path) -> None:
    """A legacy WP (no baseline field) yields ``None`` — additive degradation (D3a)."""
    tasks_dir = tmp_path / "tasks"
    _write_wp(tasks_dir, shell_pid="4242", baseline=None)

    st = _StatusState(mission="mission", json_output=True, stale_threshold=10)
    st.mission_slug = "mission"
    st.main_repo_root = tmp_path
    st.feature_dir = tmp_path
    st.tasks_dir = tasks_dir

    _st_load_work_packages(st)

    assert st.work_packages[0][SHELL_PID_BASELINE_FIELD] is None


def test_recycled_pid_caught_through_check_doing_wps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A live PID + MISMATCHED baseline is stale-eligible through the real consumer.

    Feeds ``check_doing_wps_for_staleness`` a doing-WP row shaped exactly like the
    CLI reader now produces (``shell_pid`` + ``SHELL_PID_BASELINE_FIELD``). Because
    the baseline does not match the live process's creation time, the claim is NOT
    trusted alive: the ``live_claim_process`` short-circuit is bypassed and staleness
    falls through to the commit-timestamp heuristic (never a hard-stale flag).
    """
    monkeypatch.setattr(
        "specify_cli.core.stale_detection.resolve_workspace_for_wp",
        lambda root, slug, wp_id: _lane_workspace(tmp_path),
    )

    doing_wps = [
        {
            "id": "WP01",
            "shell_pid": str(os.getpid()),  # a genuinely live PID
            SHELL_PID_BASELINE_FIELD: "1.0",  # deliberately wrong creation-time baseline
        }
    ]

    results = check_doing_wps_for_staleness(
        main_repo_root=tmp_path,
        mission_slug="mission",
        doing_wps=doing_wps,
        threshold_minutes=10,
    )

    assert "WP01" in results
    # Did NOT take the trusted-alive short-circuit: the mismatched baseline defeated it.
    assert results["WP01"].stale.reason != LIVE_CLAIM_PROCESS_REASON


def test_matching_baseline_still_trusts_live_pid_through_check_doing_wps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Contrast: a MATCHING baseline preserves the trusted-alive short-circuit.

    Proves the divergence above is caused by the threaded baseline, not by an
    unrelated code path: same wiring, correct baseline -> ``live_claim_process``.
    """
    from specify_cli.core.process_liveness import capture_creation_time_baseline

    monkeypatch.setattr(
        "specify_cli.core.stale_detection.resolve_workspace_for_wp",
        lambda root, slug, wp_id: _lane_workspace(tmp_path),
    )

    own_pid = os.getpid()
    baseline = capture_creation_time_baseline(own_pid)
    assert baseline is not None

    doing_wps = [
        {
            "id": "WP01",
            "shell_pid": str(own_pid),
            SHELL_PID_BASELINE_FIELD: baseline,
        }
    ]

    results = check_doing_wps_for_staleness(
        main_repo_root=tmp_path,
        mission_slug="mission",
        doing_wps=doing_wps,
        threshold_minutes=10,
    )

    assert results["WP01"].stale.reason == LIVE_CLAIM_PROCESS_REASON


def test_module_exposes_load_work_packages_seam() -> None:
    """Guard: the phase helper the wiring lives in stays importable at its seam."""
    assert hasattr(tasks_status_cmd, "_st_load_work_packages")
