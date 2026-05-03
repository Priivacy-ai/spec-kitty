from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.review.artifacts import ReviewCycleArtifact
from specify_cli.review.cycle import (
    ReviewCycleError,
    build_review_cycle_pointer,
    create_rejected_review_cycle,
    resolve_review_cycle_pointer,
    validate_review_artifact_file,
    validate_review_cycle_pointer,
)

pytestmark = pytest.mark.git_repo


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)


def test_create_rejected_cycle_returns_canonical_pointer_and_review_result(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tasks_dir = repo / "kitty-specs" / "001-mission" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-core.md").write_text("# WP01\n", encoding="utf-8")
    feedback = tmp_path / "feedback.md"
    feedback.write_text("**Issue**: Fix the rejected behavior.\n", encoding="utf-8")

    created = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug="001-mission",
        wp_id="WP01",
        wp_slug="WP01-core",
        feedback_source=feedback,
        reviewer_agent="codex",
    )

    assert created.artifact_path == tasks_dir / "WP01-core" / "review-cycle-1.md"
    assert created.pointer == "review-cycle://001-mission/WP01-core/review-cycle-1.md"
    assert created.review_result.verdict == "changes_requested"
    assert created.review_result.reference == created.pointer
    assert created.review_result.feedback_path == str(created.artifact_path)
    assert validate_review_artifact_file(created.artifact_path).body.startswith("**Issue**")


def test_empty_feedback_fails_before_artifact_write(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    feedback = tmp_path / "feedback.md"
    feedback.write_text(" \n", encoding="utf-8")

    with pytest.raises(ReviewCycleError, match="empty"):
        create_rejected_review_cycle(
            main_repo_root=repo,
            mission_slug="001-mission",
            wp_id="WP01",
            wp_slug="WP01-core",
            feedback_source=feedback,
            reviewer_agent="codex",
        )

    assert not (repo / "kitty-specs").exists()


def test_invalid_review_cycle_pointer_segments_are_rejected() -> None:
    with pytest.raises(ReviewCycleError):
        validate_review_cycle_pointer("review-cycle://../WP01/review-cycle-1.md")
    with pytest.raises(ReviewCycleError):
        build_review_cycle_pointer("001-mission", "WP01-core", "notes.md")


def test_resolve_canonical_pointer_validates_required_frontmatter(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    artifact_dir = repo / "kitty-specs" / "001-mission" / "tasks" / "WP01-core"
    artifact_dir.mkdir(parents=True)
    invalid = artifact_dir / "review-cycle-1.md"
    invalid.write_text("---\nverdict: rejected\n---\n\nbody\n", encoding="utf-8")

    resolved = resolve_review_cycle_pointer(
        repo,
        "review-cycle://001-mission/WP01-core/review-cycle-1.md",
    )

    assert resolved.kind == "canonical"
    assert resolved.path is None


def test_resolve_canonical_pointer_returns_valid_artifact(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    feedback = tmp_path / "feedback.md"
    feedback.write_text("**Issue**: canonical context.\n", encoding="utf-8")
    created = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug="001-mission",
        wp_id="WP01",
        wp_slug="WP01-core",
        feedback_source=feedback,
        reviewer_agent="codex",
    )

    resolved = resolve_review_cycle_pointer(repo, created.pointer)

    assert resolved.kind == "canonical"
    assert resolved.path == created.artifact_path.resolve()
    assert resolved.warnings == ()


def test_legacy_feedback_pointer_resolves_with_warning(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    common_dir = repo / ".git"
    feedback_file = common_dir / "spec-kitty" / "feedback" / "001-mission" / "WP01" / "feedback.md"
    feedback_file.parent.mkdir(parents=True)
    feedback_file.write_text("legacy feedback", encoding="utf-8")

    with patch("specify_cli.review.cycle._resolve_git_common_dir", return_value=common_dir):
        resolved = resolve_review_cycle_pointer(repo, "feedback://001-mission/WP01/feedback.md")

    assert resolved.kind == "legacy"
    assert resolved.path == feedback_file.resolve()
    assert resolved.warnings


def test_sentinel_pointer_is_not_feedback_artifact(tmp_path: Path) -> None:
    resolved = resolve_review_cycle_pointer(tmp_path, "action-review-claim")

    assert resolved.kind == "sentinel"
    assert resolved.path is None
