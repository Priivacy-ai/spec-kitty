"""Tests for normalize_mission_lifecycle helper."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.migration.normalize_mission_lifecycle import normalize_repo
from specify_cli.status.lifecycle import generate_lifecycle_json
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.progress import generate_progress_json
from specify_cli.status.store import append_event
from specify_cli.status.views import write_derived_views

pytestmark = pytest.mark.fast


def _write_meta(
    feature_dir: Path,
    *,
    mission_id: str | None = None,
    mission_number: int | str = 41,
    created_at: str | None = None,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "friendly_name": feature_dir.name,
        "mission_number": mission_number,
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
        "---\n"
        "\n"
        "Body\n",
        encoding="utf-8",
    )


def _append_event(feature_dir: Path, *, lane: str = "claimed") -> None:
    append_event(
        feature_dir,
        StatusEvent(
            event_id="01TESTNORM0000000000000001",
            mission_slug=feature_dir.name,
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane(lane),
            at="2026-04-21T12:00:00+00:00",
            actor="test-agent",
            force=False,
            execution_mode="worktree",
            mission_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        ),
    )


def test_normalize_repo_dry_run_reports_needed_repairs(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "041-legacy"
    (tmp_path / ".kittify").mkdir()
    _write_meta(feature_dir, mission_id=None, mission_number="041")
    _write_task(feature_dir)

    results = normalize_repo(tmp_path, dry_run=True)

    assert len(results) == 1
    result = results[0]
    assert result.status == "normalized"
    assert "Backfilled mission identity metadata" in result.actions
    assert any("status.events.jsonl" in action for action in result.actions)
    assert any("canonical status/progress/lifecycle views" in action for action in result.actions)
    assert result.lifecycle_state == "recoverable"
    assert not (feature_dir / "status.events.jsonl").exists()


def test_normalize_repo_repairs_legacy_mission_and_is_idempotent(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "041-legacy"
    (tmp_path / ".kittify").mkdir()
    _write_meta(feature_dir, mission_id=None, mission_number="041")
    _write_task(feature_dir, lane="for_review")

    with patch(
        "specify_cli.migration.normalize_mission_lifecycle.trigger_feature_dossier_sync_if_enabled",
        return_value=None,
    ):
        first = normalize_repo(tmp_path, dry_run=False)
        second = normalize_repo(tmp_path, dry_run=True)

    assert first[0].status == "normalized"
    meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["mission_id"]
    assert meta["mission_number"] == 41
    assert (feature_dir / "status.events.jsonl").exists()
    assert (tmp_path / ".kittify" / "derived" / "041-legacy" / "lifecycle.json").exists()
    assert first[0].lifecycle_state == "active"

    assert second[0].status == "skipped"
    assert second[0].actions == []


def test_normalize_repo_skips_missing_meta_with_warning(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "042-missing-meta"
    (tmp_path / ".kittify").mkdir()
    _write_task(feature_dir)

    results = normalize_repo(tmp_path, dry_run=True)

    assert results[0].status == "skipped"
    assert "meta.json missing" in results[0].warnings[0]


def test_normalize_repo_reports_identity_errors_per_mission(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "043-bad-number"
    (tmp_path / ".kittify").mkdir()
    _write_meta(feature_dir, mission_id=None, mission_number="pending")
    _write_task(feature_dir)

    results = normalize_repo(tmp_path, dry_run=True)

    assert results[0].status == "error"
    assert "Identity backfill failed" in (results[0].error or "")


def test_normalize_repo_detects_already_current_repo_as_skipped(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "044-current"
    derived_dir = tmp_path / ".kittify" / "derived"
    (tmp_path / ".kittify").mkdir()
    _write_meta(feature_dir, mission_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", mission_number=44)
    _append_event(feature_dir, lane="done")
    write_derived_views(feature_dir, derived_dir)
    generate_progress_json(feature_dir, derived_dir)
    generate_lifecycle_json(feature_dir, derived_dir)

    with patch(
        "specify_cli.migration.normalize_mission_lifecycle.trigger_feature_dossier_sync_if_enabled",
        return_value=None,
    ):
        results = normalize_repo(tmp_path, dry_run=True)

    assert results[0].status == "skipped"
    assert results[0].lifecycle_state == "recently_completed"
