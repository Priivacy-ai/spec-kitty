"""Focused persistence coverage for status aliases and forced transitions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.emit import emit_status_transition
from specify_cli.status.models import Lane
from specify_cli.status.reducer import SNAPSHOT_FILENAME
from specify_cli.status.store import read_events, read_events_raw

pytestmark = pytest.mark.git_repo


def _setup_mission_dir(tmp_path: Path, *, initial_lane: str = "planned") -> Path:
    """Create one WP whose canonical event stream starts in ``initial_lane``."""
    repo_root = tmp_path / "repo"
    mission_dir = repo_root / "kitty-specs" / "099-test"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-test.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test WP\n"
        f"lane: {initial_lane}\n"
        "dependencies: []\nsubtasks: []\n---\n\n# WP01 Content\n",
        encoding="utf-8",
    )
    (mission_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01 — Test WP\n- [x] T001 Done (WP01)\n",
        encoding="utf-8",
    )
    (mission_dir / "meta.json").write_text(
        json.dumps({"status_phase": 1}),
        encoding="utf-8",
    )
    seed_event = {
        "actor": "seed",
        "at": "2026-05-31T00:00:00+00:00",
        "event_id": "01HXYZ0123456789ABCDEFGS01",
        "evidence": None,
        "execution_mode": "worktree",
        "force": False,
        "from_lane": "genesis",
        "mission_slug": "099-test",
        "reason": "seed",
        "review_ref": None,
        "to_lane": initial_lane,
        "wp_id": "WP01",
    }
    (mission_dir / "status.events.jsonl").write_text(
        json.dumps(seed_event, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return mission_dir


def _read_snapshot(mission_dir: Path) -> dict[str, object]:
    return json.loads((mission_dir / SNAPSHOT_FILENAME).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _reset_sync_singletons_after_emit(
    monkeypatch: pytest.MonkeyPatch,
):  # type: ignore[no-untyped-def]
    """Isolate emit's local-only path without destroying prior worker state."""
    from specify_cli.sync import background as background_module
    from specify_cli.sync import runtime as runtime_module

    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    prior_runtime = runtime_module._runtime
    prior_service = background_module._service
    runtime_module._runtime = None
    background_module._service = None
    try:
        yield
    finally:
        current_runtime = runtime_module._runtime
        current_service = background_module._service
        runtime_module._runtime = None
        background_module._service = None
        try:
            if current_runtime is not None and current_runtime is not prior_runtime:
                current_runtime.stop()
        finally:
            try:
                if current_service is not None and current_service is not prior_service:
                    current_service.stop()
            finally:
                runtime_module._runtime = prior_runtime
                background_module._service = prior_service


class TestDualWriteAliasResolvedEverywhere:
    def test_dual_write_alias_resolved_everywhere(self, tmp_path: Path) -> None:
        """The ``doing`` alias is canonical in return, journal, and snapshot."""
        mission_dir = _setup_mission_dir(tmp_path)
        repo_root = mission_dir.parent.parent
        emit_status_transition(
            mission_dir=mission_dir,
            mission_slug="099-test",
            wp_id="WP01",
            to_lane="claimed",
            actor="agent-1",
            repo_root=repo_root,
            ensure_sync_daemon=False,
            sync_dossier=False,
        )

        event = emit_status_transition(
            mission_dir=mission_dir,
            mission_slug="099-test",
            wp_id="WP01",
            to_lane="doing",
            actor="agent-1",
            repo_root=repo_root,
            ensure_sync_daemon=False,
            sync_dossier=False,
        )

        assert event.to_lane is Lane.IN_PROGRESS
        assert read_events(mission_dir)[-1].to_lane is Lane.IN_PROGRESS
        assert read_events_raw(mission_dir)[-1]["to_lane"] == "in_progress"
        snapshot = _read_snapshot(mission_dir)
        assert snapshot["work_packages"]["WP01"]["lane"] == "in_progress"  # type: ignore[index]


class TestDualWriteForceTransitionRecorded:
    def test_dual_write_force_transition_recorded(self, tmp_path: Path) -> None:
        """Force metadata survives return, journal serialization, and reduction."""
        mission_dir = _setup_mission_dir(tmp_path, initial_lane="done")
        reason = "Rework needed after production issue"
        event = emit_status_transition(
            mission_dir=mission_dir,
            mission_slug="099-test",
            wp_id="WP01",
            to_lane="in_progress",
            actor="admin",
            force=True,
            reason=reason,
            repo_root=mission_dir.parent.parent,
            ensure_sync_daemon=False,
            sync_dossier=False,
        )

        assert event.actor == "admin"
        assert event.force is True
        assert event.reason == reason
        persisted = read_events(mission_dir)[-1]
        assert persisted.actor == "admin"
        assert persisted.force is True
        assert persisted.reason == reason
        raw = read_events_raw(mission_dir)[-1]
        assert raw["actor"] == "admin"
        assert raw["force"] is True
        assert raw["reason"] == reason
        snapshot = _read_snapshot(mission_dir)
        wp = snapshot["work_packages"]["WP01"]  # type: ignore[index]
        assert wp["lane"] == "in_progress"
        assert wp["actor"] == "admin"
        assert wp["force_count"] == 1
