"""Tests for deterministic mission-state repair."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from packaging.version import Version

from specify_cli.migration.mission_state import (
    MissionStateDryRunError,
    _repo_slug,
    deterministic_ulid,
    repair_repo,
    teamspace_dry_run,
)


def _has_events_5() -> bool:
    import spec_kitty_events

    return Version(spec_kitty_events.__version__) >= Version("5.0.0")


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, object], data)


def _init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "repair-test@spec-kitty.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "repair test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=repo, check=True)


def test_repair_canonicalizes_historical_meta_and_status_events(tmp_path: Path) -> None:
    repo = tmp_path
    mission = repo / "kitty-specs" / "042-historical-shape"
    mission.mkdir(parents=True)
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "feature_number": "042",
            "feature_slug": "042-historical-shape",
            "friendly_name": "Historical Shape",
            "mission": "software-dev",
            "slug": "042-historical-shape",
            "target_branch": "main",
        },
    )
    status_row = {
        "actor": "Claude Code",
        "at": "2026-01-01T00:00:00+00:00",
        "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGR",
        "execution_mode": "worktree",
        "feature_slug": "042-historical-shape",
        "force": False,
        "from_lane": "doing",
        "legacy_aggregate_id": "feature:042-historical-shape",
        "to_lane": "in_review",
        "work_package_id": "WP01",
    }
    duplicate_row = dict(status_row)
    typed_row = {
        "at": "2026-01-01T00:00:01+00:00",
        "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
        "event_type": "DecisionPointOpened",
        "payload": {"decision_point_id": "DP01"},
    }
    (mission / "status.events.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in (status_row, duplicate_row, typed_row)) + "\n",
        encoding="utf-8",
    )
    (mission / "mission-events.jsonl").write_text(
        json.dumps({"event_type": "MissionNextInvoked", "payload": {"mission_slug": "042-historical-shape"}}) + "\n",
        encoding="utf-8",
    )

    report = repair_repo(repo)

    report_dict = cast(dict[str, Any], report.to_dict())
    assert report_dict["summary"]["missions_updated"] == 1
    result = report.missions[0]
    assert result.status == "updated"
    assert result.quarantined_rows == 1
    meta = _read_json(mission / "meta.json")
    assert meta["mission_id"] == deterministic_ulid(
        json.dumps(
            {
                "first_event_at": "2026-01-01T00:00:00+00:00",
                "first_event_id": "01KQHRB8GCFJAX7HM4ZY52AQGR",
                "meta": {
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "friendly_name": "Historical Shape",
                    "mission_slug": "042-historical-shape",
                    "mission_type": "software-dev",
                    "slug": "042-historical-shape",
                    "target_branch": "main",
                },
            },
            sort_keys=True,
        )
    )
    assert meta["mission_number"] == 42
    assert meta["mission_slug"] == "042-historical-shape"
    assert meta["mission_type"] == "software-dev"
    assert "feature_slug" not in meta
    assert "feature_number" not in meta
    assert "mission" not in meta

    rows = [
        json.loads(line)
        for line in (mission / "status.events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row["mission_slug"] == "042-historical-shape"
    assert row["mission_id"] == meta["mission_id"]
    assert row["wp_id"] == "WP01"
    assert row["from_lane"] == "in_progress"
    assert row["to_lane"] == "in_review"
    assert row["actor"] == "claude-code"
    assert "feature_slug" not in row
    assert "work_package_id" not in row
    assert "legacy_aggregate_id" not in row

    status = _read_json(mission / "status.json")
    status_summary = cast(dict[str, object], status["summary"])
    assert status_summary["in_review"] == 1
    quarantine = repo / ".kittify" / "migrations" / "mission-state" / "quarantine" / report.run_id / "042-historical-shape" / "status.events.jsonl"
    assert "DecisionPointOpened" in quarantine.read_text(encoding="utf-8")

    if not _has_events_5():
        with pytest.raises(MissionStateDryRunError, match="requires spec-kitty-events >= 5.0.0"):
            teamspace_dry_run(repo, mission="042-historical-shape")
        return

    dry_run = teamspace_dry_run(repo, mission="042-historical-shape")

    assert dry_run.valid
    assert dry_run.schema_version == "3.0.0"
    assert dry_run.events_package_version == "5.0.0"
    assert dry_run.envelope_count == 1
    assert dry_run.errors == ()
    assert len(dry_run.row_mappings) == 1
    mapping = dry_run.row_mappings[0].to_dict()
    assert mapping["mission_slug"] == "042-historical-shape"
    assert mapping["artifact_path"] == "kitty-specs/042-historical-shape/status.events.jsonl"
    assert mapping["line_number"] == 1
    assert mapping["source_event_id"] == "01KQHRB8GCFJAX7HM4ZY52AQGR"
    assert mapping["synthesized_event_id"] == "01KQHRB8GCFJAX7HM4ZY52AQGR"
    assert mapping["synthesized_event_type"] == "WPStatusChanged"
    assert mapping["aggregate_id"] == "WP01"
    assert isinstance(mapping["row_sha256"], str)
    assert isinstance(mapping["envelope_sha256"], str)
    assert {
        warning["code"]
        for warning in dry_run.context_warnings
    } == {
        "TEAMSPACE_PROJECT_CONTEXT_MISSING",
        "TEAMSPACE_TEAM_CONTEXT_NOT_VALIDATED",
    }
    assert dry_run.side_logs == (
        {
            "artifact_path": "kitty-specs/042-historical-shape/mission-events.jsonl",
            "disposition": "skipped_local_side_log",
            "reason": "out_of_scope_for_launch_import",
            "row_count": 1,
        },
    )


def test_repair_is_idempotent_after_first_canonicalization(tmp_path: Path) -> None:
    repo = tmp_path
    mission = repo / "kitty-specs" / "001-modern"
    mission.mkdir(parents=True)
    mission_id = "01KQHRB8GCFJAX7HM4ZY52AQGR"
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Modern",
            "mission_id": mission_id,
            "mission_number": 1,
            "mission_slug": "001-modern",
            "mission_type": "software-dev",
            "slug": "001-modern",
            "target_branch": "main",
        },
    )
    (mission / "status.events.jsonl").write_text(
        json.dumps(
            {
                "actor": "codex",
                "at": "2026-01-01T00:00:00+00:00",
                "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
                "execution_mode": "worktree",
                "force": False,
                "from_lane": "planned",
                "mission_id": mission_id,
                "mission_slug": "001-modern",
                "policy_metadata": None,
                "reason": None,
                "review_ref": None,
                "evidence": None,
                "to_lane": "claimed",
                "wp_id": "WP01",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    first = repair_repo(repo)
    second = repair_repo(repo)

    assert first.missions[0].status == "updated"
    assert second.missions[0].status == "unchanged"
    assert second.missions[0].row_transformations == []


def test_deterministic_repair_ids_follow_fork_seed_material(tmp_path: Path) -> None:
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    mission_a = repo_a / "kitty-specs" / "001-historical"
    mission_b = repo_b / "kitty-specs" / "001-historical"
    mission_a.mkdir(parents=True)
    mission_b.mkdir(parents=True)
    for mission, event_id in (
        (mission_a, "01KQHRB8GCFJAX7HM4ZY52AQGR"),
        (mission_b, "01KQHRB8GCFJAX7HM4ZY52AQGS"),
    ):
        _write_json(
            mission / "meta.json",
            {
                "created_at": "2026-01-01T00:00:00+00:00",
                "feature_number": "001",
                "feature_slug": "001-historical",
                "friendly_name": "Historical",
                "mission": "software-dev",
                "target_branch": "main",
            },
        )
        (mission / "status.events.jsonl").write_text(
            json.dumps(
                {
                    "actor": "codex",
                    "at": "2026-01-01T00:00:00+00:00",
                    "event_id": event_id,
                    "from_lane": "planned",
                    "to_lane": "claimed",
                    "work_package_id": "WP01",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    repair_repo(repo_a)
    repair_repo(repo_b)

    assert _read_json(mission_a / "meta.json")["mission_id"] != _read_json(mission_b / "meta.json")["mission_id"]


def test_teamspace_dry_run_fails_when_status_rows_still_contain_legacy_keys(tmp_path: Path) -> None:
    if not _has_events_5():
        pytest.skip("TeamSpace dry-run validation requires spec-kitty-events >= 5.0.0")

    repo = tmp_path
    mission = repo / "kitty-specs" / "001-needs-repair"
    mission.mkdir(parents=True)
    mission_id = "01KQHRB8GCFJAX7HM4ZY52AQGR"
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Needs Repair",
            "mission_id": mission_id,
            "mission_number": 1,
            "mission_slug": "001-needs-repair",
            "mission_type": "software-dev",
            "slug": "001-needs-repair",
            "target_branch": "main",
        },
    )
    (mission / "status.events.jsonl").write_text(
        json.dumps(
            {
                "actor": "codex",
                "at": "2026-01-01T00:00:00+00:00",
                "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
                "execution_mode": "worktree",
                "force": False,
                "from_lane": "planned",
                "mission_id": mission_id,
                "mission_slug": "001-needs-repair",
                "to_lane": "claimed",
                "wp_id": "WP01",
                "nested": {"feature_slug": "001-needs-repair"},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    dry_run = teamspace_dry_run(repo, mission="001-needs-repair")

    assert not dry_run.valid
    assert dry_run.envelope_count == 0
    assert dry_run.errors == (
        {
            "artifact_path": "kitty-specs/001-needs-repair/status.events.jsonl",
            "error": "FORBIDDEN_LEGACY_KEY",
            "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
            "key": "feature_slug",
            "line_number": 1,
            "mission_slug": "001-needs-repair",
            "path": "$.nested.feature_slug",
        },
    )


def test_teamspace_dry_run_synthesizes_repo_evidence_for_historical_done_rows(tmp_path: Path) -> None:
    if not _has_events_5():
        pytest.skip("TeamSpace dry-run validation requires spec-kitty-events >= 5.0.0")

    repo = tmp_path
    mission = repo / "kitty-specs" / "001-historical-done"
    mission.mkdir(parents=True)
    mission_id = "01KQHRB8GCFJAX7HM4ZY52AQGR"
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Historical Done",
            "mission_id": mission_id,
            "mission_number": 1,
            "mission_slug": "001-historical-done",
            "mission_type": "software-dev",
            "slug": "001-historical-done",
            "target_branch": "main",
        },
    )
    (mission / "status.events.jsonl").write_text(
        json.dumps(
            {
                "actor": "codex",
                "at": "2026-01-01T00:00:00+00:00",
                "event_id": "01KQHRB8GCFJAX7HM4ZY52AQGS",
                "execution_mode": "worktree",
                "force": False,
                "from_lane": "approved",
                "mission_id": mission_id,
                "mission_slug": "001-historical-done",
                "policy_metadata": None,
                "reason": None,
                "review_ref": "review://historical",
                "evidence": {
                    "review": {
                        "reviewer": "historical-reviewer",
                        "verdict": "approved",
                        "reference": "review://historical",
                    }
                },
                "to_lane": "done",
                "wp_id": "WP01",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    dry_run = teamspace_dry_run(repo, mission="001-historical-done")

    assert dry_run.valid
    assert dry_run.envelope_count == 1
    assert dry_run.errors == ()
    assert len(dry_run.row_mappings) == 1


def test_repo_slug_preserves_https_remote_colon(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class _Result:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_git(repo_root: Path, *args: str, check: bool = False) -> _Result:
        assert repo_root == tmp_path
        assert args == ("config", "--get", "remote.origin.url")
        assert check is False
        return _Result("https://github.com/Priivacy-ai/spec-kitty.git\n")

    monkeypatch.setattr("specify_cli.migration.mission_state._git", fake_git)

    assert _repo_slug(tmp_path) == "Priivacy-ai/spec-kitty"


def test_repair_refuses_when_common_git_lock_is_held(tmp_path: Path) -> None:
    repo = tmp_path
    mission = repo / "kitty-specs" / "001-modern"
    mission.mkdir(parents=True)
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Modern",
            "mission_id": "01KQHRB8GCFJAX7HM4ZY52AQGR",
            "mission_number": 1,
            "mission_slug": "001-modern",
            "mission_type": "software-dev",
            "slug": "001-modern",
            "target_branch": "main",
        },
    )
    _init_git_repo(repo)
    lock = repo / ".git" / "spec-kitty-mission-state.lock"
    lock.write_text("held", encoding="ascii")

    with pytest.raises(Exception, match="Another mission-state repair appears to be running"):
        repair_repo(repo)


def test_repair_checks_dirty_relevant_paths_in_linked_worktrees(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    mission = repo / "kitty-specs" / "001-modern"
    mission.mkdir(parents=True)
    _write_json(
        mission / "meta.json",
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "friendly_name": "Modern",
            "mission_id": "01KQHRB8GCFJAX7HM4ZY52AQGR",
            "mission_number": 1,
            "mission_slug": "001-modern",
            "mission_type": "software-dev",
            "slug": "001-modern",
            "target_branch": "main",
        },
    )
    _init_git_repo(repo)
    linked = tmp_path / "linked"
    subprocess.run(["git", "worktree", "add", "-q", "-b", "linked-branch", str(linked)], cwd=repo, check=True)
    (linked / "kitty-specs" / "001-modern" / "meta.json").write_text(
        json.dumps({"mission_slug": "dirty"}, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="dirty relevant paths"):
        repair_repo(repo)

    report = repair_repo(repo, allow_dirty=True)
    assert report.missions[0].status == "unchanged"
