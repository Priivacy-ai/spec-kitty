"""CLI tests for ``spec-kitty migrate normalize-lifecycle``."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app as migrate_app


def _write_meta(feature_dir: Path, *, mission_id: str | None = None) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": "2026-04-21T10:00:00+00:00",
        "friendly_name": feature_dir.name,
        "mission_number": "045",
        "mission_slug": feature_dir.name,
        "mission_type": "software-dev",
        "slug": feature_dir.name,
        "target_branch": "main",
    }
    if mission_id is not None:
        payload["mission_id"] = mission_id
    (feature_dir / "meta.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_task(feature_dir: Path, *, lane: str = "in_progress") -> None:
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "WP01-test.md").write_text(
        "---\n"
        "title: Test WP\n"
        f"lane: {lane}\n"
        "---\n",
        encoding="utf-8",
    )


def test_help_flag() -> None:
    runner = CliRunner()
    result = runner.invoke(migrate_app, ["normalize-lifecycle", "--help"])

    assert result.exit_code == 0
    plain = result.output
    assert "normalize-lifecycle" in plain
    assert "--dry-run" in plain
    assert "--json" in plain
    assert "--mission" in plain


def test_dry_run_json_output_shape(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "045-cli-preview"
    (tmp_path / ".kittify").mkdir()
    _write_meta(feature_dir)
    _write_task(feature_dir)

    runner = CliRunner()
    with patch(
        "specify_cli.cli.commands.migrate_cmd.locate_project_root",
        return_value=tmp_path,
    ):
        result = runner.invoke(migrate_app, ["normalize-lifecycle", "--dry-run", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["dry_run"] is True
    assert payload["summary"]["normalized"] == 1
    assert payload["results"][0]["slug"] == "045-cli-preview"
    assert payload["results"][0]["status"] == "normalized"


def test_live_run_writes_event_log_and_lifecycle_projection(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "045-cli-live"
    (tmp_path / ".kittify").mkdir()
    _write_meta(feature_dir)
    _write_task(feature_dir, lane="for_review")

    runner = CliRunner()
    with (
        patch(
            "specify_cli.cli.commands.migrate_cmd.locate_project_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.migration.normalize_mission_lifecycle.trigger_feature_dossier_sync_if_enabled",
            return_value=None,
        ),
    ):
        result = runner.invoke(migrate_app, ["normalize-lifecycle", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["summary"]["normalized"] == 1
    assert (feature_dir / "status.events.jsonl").exists()
    assert (tmp_path / ".kittify" / "derived" / "045-cli-live" / "lifecycle.json").exists()
