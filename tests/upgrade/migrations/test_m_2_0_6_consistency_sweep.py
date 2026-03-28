"""Scope: m 2 0 6 consistency sweep unit tests — no real git or subprocesses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.store import EVENTS_FILENAME, read_events
from specify_cli.status.transitions import CANONICAL_LANES
from specify_cli.upgrade.migrations.m_2_0_6_consistency_sweep import (
    ConsistencySweepMigration,
    _status_events_need_repair,
)

pytestmark = pytest.mark.fast

def _write_wp(tasks_dir: Path, wp_id: str, lane: str) -> Path:
    wp_file = tasks_dir / f"{wp_id}-upgrade.md"
    wp_file.write_text(
        "\n".join(
            [
                "---",
                f'work_package_id: "{wp_id}"',
                f'title: "{wp_id} Upgrade"',
                f'lane: "{lane}"',
                "---",
                f"# {wp_id}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return wp_file


def test_detect_flags_malformed_meta_as_repairable(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    mission_dir = repo_root / "kitty-specs" / "001-broken-meta"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text("{not-json", encoding="utf-8")

    migration = ConsistencySweepMigration()
    assert migration.detect(repo_root) is True


def test_detect_flags_incomplete_meta_as_repairable(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    mission_dir = repo_root / "kitty-specs" / "001-incomplete-meta"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_number": "001",
                "slug": "001-incomplete-meta",
                "target_branch": "main",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    migration = ConsistencySweepMigration()
    assert migration.detect(repo_root) is True


def test_apply_repairs_mission_state_and_legacy_prompt_refs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    mission_dir = repo_root / "kitty-specs" / "001-upgrade-sweep"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    _write_wp(tasks_dir, "WP01", "doing")
    (mission_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "**Prompt**: `.claude/prompts/tasks/doing/WP01-upgrade.md`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (mission_dir / "status.json").write_text(
        json.dumps(
            {
                "mission_slug": "",
                "event_count": 0,
                "work_packages": {},
                "summary": dict.fromkeys(CANONICAL_LANES, 0),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "specify_cli.upgrade.mission_meta.resolve_primary_branch",
        lambda _repo_root: "2.x",
    )
    monkeypatch.setattr(
        "specify_cli.upgrade.migrations.m_2_0_6_consistency_sweep._migrate_runtime_assets",
        lambda _project_path, dry_run: ([], []),
    )

    migration = ConsistencySweepMigration()
    result = migration.apply(repo_root, dry_run=False)

    assert result.success is True

    meta = json.loads((mission_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["target_branch"] == "2.x"
    assert meta["mission"] == "software-dev"

    wp_text = (tasks_dir / "WP01-upgrade.md").read_text(encoding="utf-8")
    assert 'lane: "doing"' not in wp_text
    assert "lane: in_progress" in wp_text

    tasks_md = (mission_dir / "tasks.md").read_text(encoding="utf-8")
    assert ".claude/prompts/tasks/WP01-upgrade.md" in tasks_md
    assert "<!-- status-model:start -->" in tasks_md
    assert "- WP01: in_progress" in tasks_md

    assert (mission_dir / EVENTS_FILENAME).exists()
    assert read_events(mission_dir)

    backup_files = sorted(mission_dir.glob("status.json.orphan.bak.*"))
    assert len(backup_files) == 1

    status = json.loads((mission_dir / "status.json").read_text(encoding="utf-8"))
    assert status["work_packages"]["WP01"]["lane"] == "in_progress"


def test_apply_quarantines_unreadable_planned_only_event_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    mission_dir = repo_root / "kitty-specs" / "001-corrupt-events"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    _write_wp(tasks_dir, "WP01", "planned")
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_number": "001",
                "slug": "001-corrupt-events",
                "mission_slug": "001-corrupt-events",
                "mission": "software-dev",
                "target_branch": "main",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (mission_dir / EVENTS_FILENAME).write_text("{bad json\n", encoding="utf-8")

    monkeypatch.setattr(
        "specify_cli.upgrade.migrations.m_2_0_6_consistency_sweep._migrate_runtime_assets",
        lambda _project_path, dry_run: ([], []),
    )

    migration = ConsistencySweepMigration()
    result = migration.apply(repo_root, dry_run=False)

    assert result.success is True
    assert not (mission_dir / EVENTS_FILENAME).exists()
    assert len(list(mission_dir.glob("status.events.jsonl.unreadable.bak.*"))) == 1
    assert any("archived unreadable status.events.jsonl" in change for change in result.changes_made)

    status = json.loads((mission_dir / "status.json").read_text(encoding="utf-8"))
    assert status["work_packages"] == {}
    assert status["event_count"] == 0


def test_apply_cleans_legacy_worktree_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    worktree = repo_root / ".worktrees" / "001-mission-WP01"
    commands_dir = worktree / ".claude" / "commands"
    scripts_dir = worktree / ".kittify" / "scripts"
    commands_dir.mkdir(parents=True)
    scripts_dir.mkdir(parents=True)
    (commands_dir / "spec-kitty.tasks.md").write_text("legacy", encoding="utf-8")
    (scripts_dir / "task.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(
        "specify_cli.upgrade.migrations.m_2_0_6_consistency_sweep._migrate_runtime_assets",
        lambda _project_path, dry_run: ([], []),
    )

    migration = ConsistencySweepMigration()
    result = migration.apply(repo_root, dry_run=False)

    assert result.success is True
    assert not commands_dir.exists()
    assert not scripts_dir.exists()
    assert any("cleaned 1 worktree" in change for change in result.changes_made)


# ---------------------------------------------------------------------------
# _status_events_need_repair
# ---------------------------------------------------------------------------

_DELEGATION_TARGET = (
    "specify_cli.upgrade.migrations.m_2_0_6_consistency_sweep"
    ".mission_requires_historical_migration"
)


def _make_event_line(
    *,
    wp_id: str = "WP01",
    actor: str = "cli:task:start",
    reason: str | None = None,
) -> str:
    """Build a minimal valid JSONL event line."""
    event = {
        "event_id": "01ABCDE000000000000000TEST",
        "mission_slug": "099-test",
        "wp_id": wp_id,
        "from_lane": "planned",
        "to_lane": "in_progress",
        "at": "2026-01-01T00:00:00+00:00",
        "actor": actor,
        "force": False,
        "execution_mode": "direct_repo",
    }
    if reason is not None:
        event["reason"] = reason
    return json.dumps(event)


class TestStatusEventsNeedRepair:
    """Tests for _status_events_need_repair covering all code paths."""

    def test_no_tasks_dir(self, tmp_path: Path) -> None:
        mission_dir = tmp_path / "099-test"
        mission_dir.mkdir()
        assert _status_events_need_repair(mission_dir) is False

    def test_tasks_dir_no_wp_files(self, tmp_path: Path) -> None:
        mission_dir = tmp_path / "099-test"
        tasks_dir = mission_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "README.md").write_text("not a WP", encoding="utf-8")
        assert _status_events_need_repair(mission_dir) is False

    def test_no_events_file_delegates_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mission_dir = tmp_path / "099-test"
        tasks_dir = mission_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "planned")
        monkeypatch.setattr(_DELEGATION_TARGET, lambda _fd: True)
        assert _status_events_need_repair(mission_dir) is True

    def test_no_events_file_delegates_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mission_dir = tmp_path / "099-test"
        tasks_dir = mission_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "planned")
        monkeypatch.setattr(_DELEGATION_TARGET, lambda _fd: False)
        assert _status_events_need_repair(mission_dir) is False

    def test_empty_events_file_delegates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mission_dir = tmp_path / "099-test"
        tasks_dir = mission_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "planned")
        (mission_dir / EVENTS_FILENAME).write_text("  \n", encoding="utf-8")
        monkeypatch.setattr(_DELEGATION_TARGET, lambda _fd: True)
        assert _status_events_need_repair(mission_dir) is True

    def test_corrupt_jsonl_returns_true(self, tmp_path: Path) -> None:
        mission_dir = tmp_path / "099-test"
        tasks_dir = mission_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "planned")
        (mission_dir / EVENTS_FILENAME).write_text("{bad json\n", encoding="utf-8")
        assert _status_events_need_repair(mission_dir) is True

    def test_events_with_historical_marker_returns_false(
        self, tmp_path: Path
    ) -> None:
        mission_dir = tmp_path / "099-test"
        tasks_dir = mission_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "in_progress")
        line = _make_event_line(
            actor="migration:frontmatter",
            reason="historical_frontmatter_to_jsonl:v1",
        )
        (mission_dir / EVENTS_FILENAME).write_text(line + "\n", encoding="utf-8")
        assert _status_events_need_repair(mission_dir) is False

    def test_events_with_non_migration_actor_returns_false(
        self, tmp_path: Path
    ) -> None:
        mission_dir = tmp_path / "099-test"
        tasks_dir = mission_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "in_progress")
        line = _make_event_line(actor="cli:task:start")
        (mission_dir / EVENTS_FILENAME).write_text(line + "\n", encoding="utf-8")
        assert _status_events_need_repair(mission_dir) is False

    def test_all_migration_actors_no_marker_delegates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mission_dir = tmp_path / "099-test"
        tasks_dir = mission_dir / "tasks"
        tasks_dir.mkdir(parents=True)
        _write_wp(tasks_dir, "WP01", "in_progress")
        line = _make_event_line(actor="migration:upgrade", reason="some other reason")
        (mission_dir / EVENTS_FILENAME).write_text(line + "\n", encoding="utf-8")
        monkeypatch.setattr(_DELEGATION_TARGET, lambda _fd: True)
        assert _status_events_need_repair(mission_dir) is True
