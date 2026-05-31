"""Tests for migration 3.2.0rc28_github_diff_attributes."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_3_2_0rc28_github_diff_attributes import (
    GitHubDiffAttributesMigration,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _git(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *cmd],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def test_apply_adds_generated_artifact_attributes(tmp_path: Path) -> None:
    migration = GitHubDiffAttributesMigration()

    assert migration.detect(tmp_path) is True
    result = migration.apply(tmp_path)

    assert result.success is True
    attributes = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
    assert "kitty-specs/**/status.json linguist-generated=true" in attributes
    assert "kitty-specs/**/tasks/** linguist-generated=true" in attributes
    assert "kitty-specs/**/research/evidence-log.csv linguist-generated=true" in attributes
    assert ".kittify/workspaces/** linguist-generated=true" in attributes
    assert ".kittify/workspaces/** -diff" in attributes
    assert ".kittify/migrations/** linguist-generated=true" in attributes
    assert ".kittify/migrations/** -diff" in attributes
    assert migration.detect(tmp_path) is False


def test_apply_preserves_existing_attributes_and_is_idempotent(tmp_path: Path) -> None:
    attributes_path = tmp_path / ".gitattributes"
    attributes_path.write_text("kitty-specs/**/status.events.jsonl merge=spec-kitty-event-log\n", encoding="utf-8")
    migration = GitHubDiffAttributesMigration()

    first = migration.apply(tmp_path)
    second = migration.apply(tmp_path)

    attributes = attributes_path.read_text(encoding="utf-8").splitlines()
    assert first.success is True
    assert second.success is True
    assert second.changes_made == []
    assert attributes.count("kitty-specs/**/status.json linguist-generated=true") == 1
    assert attributes[0] == "kitty-specs/**/status.events.jsonl merge=spec-kitty-event-log"


def test_can_apply_rejects_missing_project_path(tmp_path: Path) -> None:
    migration = GitHubDiffAttributesMigration()

    ok, reason = migration.can_apply(tmp_path / "missing")

    assert ok is False
    assert "Project path does not exist" in reason


def test_apply_dry_run_reports_missing_entries_without_writing(tmp_path: Path) -> None:
    migration = GitHubDiffAttributesMigration()

    result = migration.apply(tmp_path, dry_run=True)

    assert result.success is True
    assert result.changes_made
    assert result.changes_made[0].startswith("Would add .gitattributes entry:")
    assert not (tmp_path / ".gitattributes").exists()


def test_attributes_match_nested_generated_artifacts(tmp_path: Path) -> None:
    _git(["init", "-b", "main"], tmp_path)
    migration = GitHubDiffAttributesMigration()
    migration.apply(tmp_path)

    mission_dir = tmp_path / "kitty-specs" / "example"
    (mission_dir / "tasks").mkdir(parents=True)
    (mission_dir / "research").mkdir(parents=True)
    (mission_dir / "contracts").mkdir(parents=True)
    (tmp_path / ".kittify" / "workspaces").mkdir(parents=True)
    (tmp_path / ".kittify" / "migrations" / "mission-state").mkdir(parents=True)
    status_file = mission_dir / "status.json"
    wp_file = mission_dir / "tasks" / "WP01.md"
    evidence_file = mission_dir / "research" / "evidence-log.csv"
    workspace_file = tmp_path / ".kittify" / "workspaces" / "example-WP01.json"
    migration_file = tmp_path / ".kittify" / "migrations" / "mission-state" / "snapshot.json"
    visible_spec_file = mission_dir / "spec.md"
    visible_plan_file = mission_dir / "plan.md"
    visible_tasks_file = mission_dir / "tasks.md"
    visible_research_file = mission_dir / "research.md"
    visible_contract_file = mission_dir / "contracts" / "api.md"
    visible_review_file = mission_dir / "mission-review.md"
    status_file.touch()
    wp_file.touch()
    evidence_file.touch()
    workspace_file.touch()
    migration_file.touch()
    visible_spec_file.touch()
    visible_plan_file.touch()
    visible_tasks_file.touch()
    visible_research_file.touch()
    visible_contract_file.touch()
    visible_review_file.touch()

    result = _git(
        [
            "check-attr",
            "linguist-generated",
            "diff",
            "--",
            str(status_file.relative_to(tmp_path)),
            str(wp_file.relative_to(tmp_path)),
            str(evidence_file.relative_to(tmp_path)),
            str(workspace_file.relative_to(tmp_path)),
            str(migration_file.relative_to(tmp_path)),
            str(visible_spec_file.relative_to(tmp_path)),
            str(visible_plan_file.relative_to(tmp_path)),
            str(visible_tasks_file.relative_to(tmp_path)),
            str(visible_research_file.relative_to(tmp_path)),
            str(visible_contract_file.relative_to(tmp_path)),
            str(visible_review_file.relative_to(tmp_path)),
        ],
        tmp_path,
    )

    assert "kitty-specs/example/status.json: linguist-generated: true" in result.stdout
    assert "kitty-specs/example/tasks/WP01.md: linguist-generated: true" in result.stdout
    assert "kitty-specs/example/research/evidence-log.csv: linguist-generated: true" in result.stdout
    assert ".kittify/workspaces/example-WP01.json: linguist-generated: true" in result.stdout
    assert ".kittify/workspaces/example-WP01.json: diff: unset" in result.stdout
    assert ".kittify/migrations/mission-state/snapshot.json: linguist-generated: true" in result.stdout
    assert ".kittify/migrations/mission-state/snapshot.json: diff: unset" in result.stdout
    assert "kitty-specs/example/spec.md: linguist-generated: unspecified" in result.stdout
    assert "kitty-specs/example/plan.md: linguist-generated: unspecified" in result.stdout
    assert "kitty-specs/example/tasks.md: linguist-generated: unspecified" in result.stdout
    assert "kitty-specs/example/research.md: linguist-generated: unspecified" in result.stdout
    assert "kitty-specs/example/contracts/api.md: linguist-generated: unspecified" in result.stdout
    assert "kitty-specs/example/mission-review.md: linguist-generated: unspecified" in result.stdout
