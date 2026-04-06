from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from specify_cli.cli.commands.agent import context
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.status.store import append_event
from specify_cli.status.models import StatusEvent, Lane


def _seed_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    """Seed a WP into a specific lane in the event log."""
    _lane_alias = {"doing": "in_progress"}
    canonical_lane = _lane_alias.get(lane, lane)
    event = StatusEvent(
        event_id=f"test-{wp_id}-{canonical_lane}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane.PLANNED,
        to_lane=Lane(canonical_lane),
        at="2026-01-01T00:00:00+00:00",
        actor="test",
        force=True,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def _write_wp(path: Path, wp_id: str, lane: str, dependencies: str = "[]") -> None:
    path.write_text(
        "---\n"
        f'work_package_id: "{wp_id}"\n'
        f'lane: "{lane}"\n'
        f"dependencies: {dependencies}\n"
        f'title: "{wp_id} title"\n'
        "---\n"
        f"# {wp_id}\n",
        encoding="utf-8",
    )


def _make_feature(repo_root: Path, slug: str, *, target_branch: str = "main") -> Path:
    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission": "software-dev", "target_branch": target_branch}),
        encoding="utf-8",
    )
    (feature_dir / "tasks").mkdir()
    return feature_dir


def _write_lanes(feature_dir: Path, *lane_defs: tuple[str, tuple[str, ...]]) -> None:
    lanes = [
        ExecutionLane(
            lane_id=lane_id,
            wp_ids=wp_ids,
            write_scope=("src/**",),
            predicted_surfaces=("core",),
            depends_on_lanes=(),
            parallel_group=index,
        )
        for index, (lane_id, wp_ids) in enumerate(lane_defs)
    ]
    write_lanes_json(
        feature_dir,
        LanesManifest(
            version=1,
            feature_slug=feature_dir.name,
            mission_id=f"mission-{feature_dir.name}",
            mission_branch=f"kitty/mission-{feature_dir.name}",
            target_branch="main",
            lanes=lanes,
            computed_at="2026-04-04T10:00:00Z",
            computed_from="test",
        ),
    )


def test_context_resolve_tasks_uses_latest_incomplete(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()

    feature_a = _make_feature(repo_root, "001-first")
    _write_wp(feature_a / "tasks" / "WP01.md", "WP01", "done")
    _seed_wp_lane(feature_a, "WP01", "done")

    feature_b = _make_feature(repo_root, "002-second", target_branch="2.x")
    _write_wp(feature_b / "tasks" / "WP01.md", "WP01", "planned")
    # No event seeding needed for planned lane (defaults to planned)

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)

    # context.app has a single command (resolve) exposed directly (no subcommand prefix)
    # --feature is required since auto-detection was removed
    result = CliRunner().invoke(context.app, ["--action", "tasks", "--feature", "002-second", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["feature_slug"] == "002-second"
    assert payload["target_branch"] == "2.x"
    assert payload["commands"]["check_prerequisites"].endswith("--feature 002-second")
    assert payload["commands"]["finalize_tasks"].endswith("--feature 002-second --json")


def test_context_resolve_implement_auto_resolves_base(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()

    feature_dir = _make_feature(repo_root, "021-context-test")
    _write_wp(feature_dir / "tasks" / "WP01.md", "WP01", "done")
    _seed_wp_lane(feature_dir, "WP01", "done")
    _write_wp(feature_dir / "tasks" / "WP02.md", "WP02", "planned", dependencies="[WP01]")
    _write_lanes(feature_dir, ("lane-a", ("WP01", "WP02")))
    # No event seeding needed for planned lane

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)

    # context.app has a single command (resolve) exposed directly (no subcommand prefix)
    result = CliRunner().invoke(
        context.app,
        ["--action", "implement", "--feature", "021-context-test", "--agent", "codex", "--json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["wp_id"] == "WP02"
    assert payload["resolved_base"] is None
    assert payload["workspace_path"].endswith(".worktrees/021-context-test-lane-a")
    assert payload["commands"]["workflow"].endswith("implement WP02 --agent codex")


def test_context_resolve_canonicalizes_doing_lane_when_selecting_wp(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()

    feature_dir = _make_feature(repo_root, "021-context-test")
    _write_wp(feature_dir / "tasks" / "WP01.md", "WP01", "doing")
    _seed_wp_lane(feature_dir, "WP01", "in_progress")
    _write_lanes(feature_dir, ("lane-a", ("WP01",)))

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)

    # context.app has a single command (resolve) exposed directly (no subcommand prefix)
    result = CliRunner().invoke(
        context.app,
        ["--action", "implement", "--feature", "021-context-test", "--json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["wp_id"] == "WP01"
    assert payload["lane"] == "in_progress"


def test_context_resolve_review_returns_approve_command(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()

    feature_dir = _make_feature(repo_root, "021-context-test")
    _write_wp(feature_dir / "tasks" / "WP01.md", "WP01", "for_review")
    _seed_wp_lane(feature_dir, "WP01", "for_review")
    _write_lanes(feature_dir, ("lane-a", ("WP01",)))

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)

    # context.app has a single command (resolve) exposed directly (no subcommand prefix)
    result = CliRunner().invoke(
        context.app,
        ["--action", "review", "--feature", "021-context-test", "--agent", "codex", "--json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["wp_id"] == "WP01"
    assert payload["commands"]["workflow"].endswith("review WP01 --agent codex")
    assert "--to approved" in payload["commands"]["approve"]


def test_context_resolve_rejects_invalid_action(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)

    result = CliRunner().invoke(context.app, ["--action", "foobar", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert payload["error_code"] == "INVALID_ACTION"
