"""Review prompt identity fixtures for collision and metadata tests."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from specify_cli.frontmatter import read_frontmatter, write_frontmatter

FIXED_REVIEW_CREATED_AT = "2026-05-02T09:00:00+00:00"
FIXED_REVIEW_INVOCATION_ID = "same-second-review-invocation"


@dataclass(frozen=True)
class ReviewPromptIdentity:
    """Self-identifying metadata for one review prompt invocation."""

    invocation_id: str
    repo_root: Path
    mission_id: str
    mission_slug: str
    work_package_id: str
    lane_worktree: Path
    mission_branch: str
    lane_branch: str
    base_ref: str
    prompt_path: Path
    created_at: str

    def to_frontmatter(self) -> dict[str, str]:
        data = asdict(self)
        return {key: str(value) for key, value in data.items()}


def _safe_repo_identifier(repo_root: Path) -> str:
    digest = hashlib.sha1(str(repo_root).encode("utf-8")).hexdigest()[:12]
    return f"{repo_root.name}-{digest}"


def _prompt_path(
    repo_root: Path,
    *,
    mission_slug: str,
    work_package_id: str,
    invocation_id: str,
) -> Path:
    return (
        repo_root
        / ".spec-kitty"
        / "review-prompts"
        / _safe_repo_identifier(repo_root)
        / mission_slug
        / work_package_id
        / f"{invocation_id}.md"
    )


def concurrent_review_prompt_identities(
    tmp_path: Path,
    *,
    invocation_id: str = FIXED_REVIEW_INVOCATION_ID,
    created_at: str = FIXED_REVIEW_CREATED_AT,
) -> tuple[ReviewPromptIdentity, ReviewPromptIdentity]:
    """Return two same-second review identities whose paths cannot collide."""

    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    mission_slug = "mission-release-320-workflow-reliability-01KQKV85"

    first = ReviewPromptIdentity(
        invocation_id=invocation_id,
        repo_root=repo_a,
        mission_id="01KQKV85REPOA000000000000",
        mission_slug=mission_slug,
        work_package_id="WP03",
        lane_worktree=repo_a / ".worktrees" / "lane-a",
        mission_branch="kitty/mission-release-320-workflow-reliability-01KQKV85",
        lane_branch="kitty/mission-release-320-workflow-reliability-01KQKV85-lane-a",
        base_ref="kitty/mission-release-320-workflow-reliability-01KQKV85",
        prompt_path=_prompt_path(
            repo_a,
            mission_slug=mission_slug,
            work_package_id="WP03",
            invocation_id=invocation_id,
        ),
        created_at=created_at,
    )
    second = ReviewPromptIdentity(
        invocation_id=invocation_id,
        repo_root=repo_b,
        mission_id="01KQKV85REPOB000000000000",
        mission_slug=mission_slug,
        work_package_id="WP03",
        lane_worktree=repo_b / ".worktrees" / "lane-a",
        mission_branch="kitty/mission-release-320-workflow-reliability-01KQKV85",
        lane_branch="kitty/mission-release-320-workflow-reliability-01KQKV85-lane-a",
        base_ref="kitty/mission-release-320-workflow-reliability-01KQKV85",
        prompt_path=_prompt_path(
            repo_b,
            mission_slug=mission_slug,
            work_package_id="WP03",
            invocation_id=invocation_id,
        ),
        created_at=created_at,
    )
    return first, second


def write_review_prompt(identity: ReviewPromptIdentity) -> Path:
    """Write a review prompt with structured identity frontmatter."""

    identity.prompt_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n# Review Prompt\n\nReview only the work identified by this metadata.\n"
    write_frontmatter(identity.prompt_path, identity.to_frontmatter(), body)
    return identity.prompt_path


def assert_prompt_metadata_identity(path: Path, expected: ReviewPromptIdentity) -> dict[str, Any]:
    """Assert a prompt's frontmatter exactly matches its requested identity."""

    frontmatter, _body = read_frontmatter(path)
    expected_frontmatter = expected.to_frontmatter()
    for key, value in expected_frontmatter.items():
        assert frontmatter[key] == value
    return frontmatter
