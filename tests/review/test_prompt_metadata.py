from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.review.prompt_metadata import (
    REVIEW_PROMPT_METADATA_MISMATCH,
    ReviewPromptMetadataError,
    build_review_prompt_metadata,
    read_review_prompt_metadata,
    validate_review_prompt_metadata,
    write_review_prompt_with_metadata,
)


def _metadata(
    repo_root: Path,
    *,
    mission_slug: str = "release-320-workflow-reliability-01KQKV85",
    wp_id: str = "WP03",
    invocation_id: str = "same-second-a",
):
    return build_review_prompt_metadata(
        repo_root=repo_root,
        mission_id=f"mission-id-{repo_root.name}",
        mission_slug=mission_slug,
        work_package_id=wp_id,
        lane_worktree=repo_root / ".worktrees" / f"{mission_slug}-lane-a",
        mission_branch=f"kitty/mission-{mission_slug}",
        lane_branch=f"kitty/mission-{mission_slug}-lane-a",
        base_ref=f"kitty/mission-{mission_slug}",
        invocation_id=invocation_id,
        created_at="2026-05-02T09:00:00Z",
    )


def test_concurrent_review_prompts_for_two_repos_do_not_collide(tmp_path: Path) -> None:
    first = _metadata(tmp_path / "repo-a", invocation_id="same-second")
    second = _metadata(tmp_path / "repo-b", invocation_id="same-second")

    assert first.prompt_path != second.prompt_path

    first_path = write_review_prompt_with_metadata("# Review A", first)
    second_path = write_review_prompt_with_metadata("# Review B", second)

    assert first_path != second_path
    assert read_review_prompt_metadata(first_path)["repo_root"] == str(first.repo_root)
    assert read_review_prompt_metadata(second_path)["repo_root"] == str(second.repo_root)


def test_concurrent_review_prompts_for_two_missions_do_not_collide(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    first = _metadata(repo_root, mission_slug="mission-alpha", invocation_id="same-second")
    second = _metadata(repo_root, mission_slug="mission-beta", invocation_id="same-second")

    assert first.prompt_path != second.prompt_path

    write_review_prompt_with_metadata("# Review A", first)
    write_review_prompt_with_metadata("# Review B", second)

    assert read_review_prompt_metadata(first.prompt_path)["mission_slug"] == "mission-alpha"
    assert read_review_prompt_metadata(second.prompt_path)["mission_slug"] == "mission-beta"


def test_same_second_same_wp_invocations_get_distinct_prompt_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    first = _metadata(repo_root, invocation_id="invocation-a")
    second = _metadata(repo_root, invocation_id="invocation-b")

    assert first.created_at == second.created_at
    assert first.work_package_id == second.work_package_id
    assert first.prompt_path != second.prompt_path


def test_prompt_metadata_mismatch_fails_closed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_context = _metadata(repo_root, wp_id="WP03", invocation_id="invocation-a")
    requested_context = _metadata(repo_root, wp_id="WP04", invocation_id="invocation-a")
    write_review_prompt_with_metadata("# stale WP03 review prompt", prompt_context)

    with pytest.raises(ReviewPromptMetadataError) as exc_info:
        validate_review_prompt_metadata(prompt_context.prompt_path, requested_context)

    diagnostic = exc_info.value.diagnostic
    assert diagnostic["diagnostic_code"] == REVIEW_PROMPT_METADATA_MISMATCH
    assert diagnostic["requested_context"]["work_package_id"] == "WP04"
    assert diagnostic["prompt_context"]["work_package_id"] == "WP03"
    assert diagnostic["prompt_path"] == str(prompt_context.prompt_path)
