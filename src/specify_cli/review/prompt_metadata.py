"""Invocation-scoped review prompt metadata.

Review prompts are dispatch artifacts: a reviewer reads them to decide which
repo, mission, work package, and worktree to inspect.  The prompt file must
therefore identify the requested review context and fail closed if a stale or
wrong-context prompt is about to be handed to a reviewer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specify_cli.frontmatter import FrontmatterError, read_frontmatter, write_frontmatter

logger = logging.getLogger(__name__)

REVIEW_PROMPT_METADATA_MISMATCH = "REVIEW_PROMPT_METADATA_MISMATCH"
REVIEW_PROMPT_METADATA_MISSING = "REVIEW_PROMPT_METADATA_MISSING"

# FR-001/FR-002: keep at most this many newest per-invocation review-prompt
# files per (repo, mission, WP) directory. Small enough to bound growth, large
# enough to keep recent history for debugging a dispatch.
DEFAULT_REVIEW_PROMPT_RETENTION = 20

REQUIRED_REVIEW_PROMPT_FIELDS: tuple[str, ...] = (
    "invocation_id",
    "repo_root",
    "mission_id",
    "mission_slug",
    "work_package_id",
    "lane_worktree",
    "mission_branch",
    "lane_branch",
    "base_ref",
    "prompt_path",
    "created_at",
)


@dataclass(frozen=True)
class ReviewPromptMetadata:
    """Structured identity bound to one review prompt invocation."""

    invocation_id: str
    repo_root: Path
    mission_id: str | None  # WP04/FR-004: ULID or None; never a slug
    mission_slug: str
    work_package_id: str
    lane_worktree: Path
    mission_branch: str
    lane_branch: str
    base_ref: str
    prompt_path: Path
    created_at: str

    def to_frontmatter(self) -> dict[str, str]:
        """Serialize metadata as prompt YAML frontmatter."""
        data = asdict(self)
        # WP04: mission_id is str | None; serialize None as "" so frontmatter
        # stays a clean string map (never "None" string).
        return {key: str(value) if value is not None else "" for key, value in data.items()}


class ReviewPromptMetadataError(RuntimeError):
    """Raised when prompt metadata does not match the requested review."""

    def __init__(
        self,
        *,
        diagnostic_code: str,
        requested_context: dict[str, str],
        prompt_context: dict[str, str],
        prompt_path: Path,
    ) -> None:
        self.diagnostic = {
            "diagnostic_code": diagnostic_code,
            "requested_context": requested_context,
            "prompt_context": prompt_context,
            "prompt_path": str(prompt_path),
        }
        super().__init__(json.dumps(self.diagnostic, indent=2, sort_keys=True))


def new_review_invocation_id() -> str:
    """Return an unguessable per-dispatch review invocation id."""
    return uuid.uuid4().hex


def utc_now_for_review_prompt() -> str:
    """Return a compact UTC timestamp for prompt metadata."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def safe_repo_identifier(repo_root: Path) -> str:
    """Return a filesystem-safe repo identity component with a path hash."""
    resolved = str(repo_root.expanduser().resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:12]  # noqa: TID251 - production raw SHA-256 owner
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", repo_root.name).strip("-") or "repo"
    return f"{safe_name}-{digest}"


def _safe_component(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return safe or "unknown"


def review_prompt_path(
    repo_root: Path,
    *,
    mission_slug: str,
    work_package_id: str,
    invocation_id: str,
) -> Path:
    """Return an invocation-specific review prompt path."""
    return (
        Path(tempfile.gettempdir())
        / "spec-kitty-review-prompts"
        / safe_repo_identifier(repo_root)
        / _safe_component(mission_slug)
        / _safe_component(work_package_id)
        / f"{_safe_component(invocation_id)}.md"
    )


def build_review_prompt_metadata(
    *,
    repo_root: Path,
    mission_id: str | None,
    mission_slug: str,
    work_package_id: str,
    lane_worktree: Path,
    mission_branch: str,
    lane_branch: str,
    base_ref: str,
    invocation_id: str | None = None,
    created_at: str | None = None,
) -> ReviewPromptMetadata:
    """Build metadata for a single review prompt dispatch."""
    resolved_invocation_id = invocation_id or new_review_invocation_id()
    resolved_repo_root = repo_root.expanduser().resolve()
    prompt_path = review_prompt_path(
        resolved_repo_root,
        mission_slug=mission_slug,
        work_package_id=work_package_id,
        invocation_id=resolved_invocation_id,
    )
    return ReviewPromptMetadata(
        invocation_id=resolved_invocation_id,
        repo_root=resolved_repo_root,
        mission_id=mission_id,  # WP04/FR-004: ULID or None; slug fallback removed
        mission_slug=mission_slug,
        work_package_id=work_package_id,
        lane_worktree=lane_worktree.expanduser().resolve(),
        mission_branch=mission_branch,
        lane_branch=lane_branch,
        base_ref=base_ref,
        prompt_path=prompt_path,
        created_at=created_at or utc_now_for_review_prompt(),
    )


def _prune_review_prompt_dir(wp_dir: Path, *, keep: int, current_name: str) -> None:
    """Best-effort prune of older review-prompt files under one WP directory.

    Retains at most ``keep`` newest ``*.md`` invocation files (by mtime) in
    *wp_dir*, always keeping *current_name* (the just-written invocation) — it
    is excluded from the deletion candidates entirely, so it survives even when
    every other file is newer by mtime.

    Scope is strictly *wp_dir*: a single, non-recursive ``scandir`` — the prune
    never walks above the ``spec-kitty-review-prompts/<repo-id>/…`` subtree and
    never touches the path scheme or metadata (NFR-001).

    Fail-safe (NFR-002): any error (missing dir, permission, race) is swallowed
    and logged at debug so a review can never fail on retention housekeeping.
    """
    try:
        others: list[tuple[float, Path]] = []
        with os.scandir(wp_dir) as entries:
            for entry in entries:
                if entry.name == current_name or not entry.name.endswith(".md"):
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                others.append((entry.stat().st_mtime, Path(entry.path)))
        # Newest first; retain (keep - 1) other files so that, with the current
        # invocation, at most ``keep`` files remain.
        others.sort(key=lambda item: item[0], reverse=True)
        for _mtime, stale_path in others[max(keep - 1, 0) :]:
            stale_path.unlink()
    except Exception as exc:  # fail-safe: housekeeping must never break a review (NFR-002)
        logger.debug("Review-prompt retention prune skipped for %s: %s", wp_dir, exc)


def write_review_prompt_with_metadata(
    content: str,
    metadata: ReviewPromptMetadata,
    *,
    retention: int = DEFAULT_REVIEW_PROMPT_RETENTION,
) -> Path:
    """Write a review prompt with identity frontmatter, then prune old invocations.

    After the current ``<invocation-id>.md`` is written, the WP directory is
    pruned to the newest ``retention`` files (best-effort, current always kept).
    """
    metadata.prompt_path.parent.mkdir(parents=True, exist_ok=True)
    body = content if content.startswith("\n") else f"\n{content}"
    write_frontmatter(metadata.prompt_path, metadata.to_frontmatter(), body)
    _prune_review_prompt_dir(
        metadata.prompt_path.parent,
        keep=retention,
        current_name=metadata.prompt_path.name,
    )
    return metadata.prompt_path


def read_review_prompt_metadata(prompt_path: Path) -> dict[str, str]:
    """Read raw review prompt metadata frontmatter as strings."""
    frontmatter, _ = read_frontmatter(prompt_path)
    return {key: str(value) for key, value in frontmatter.items()}


def validate_review_prompt_metadata(prompt_path: Path, requested: ReviewPromptMetadata) -> None:
    """Fail closed if *prompt_path* is not bound to *requested* context."""
    requested_context = requested.to_frontmatter()
    try:
        prompt_context = read_review_prompt_metadata(prompt_path)
    except (FrontmatterError, OSError) as exc:
        raise ReviewPromptMetadataError(
            diagnostic_code=REVIEW_PROMPT_METADATA_MISSING,
            requested_context=requested_context,
            prompt_context={"error": str(exc)},
            prompt_path=prompt_path,
        ) from exc

    missing = [field for field in REQUIRED_REVIEW_PROMPT_FIELDS if field not in prompt_context]
    mismatched = {
        field: {"requested": requested_context[field], "prompt": prompt_context.get(field, "")}
        for field in REQUIRED_REVIEW_PROMPT_FIELDS
        if field in requested_context and prompt_context.get(field) != requested_context[field]
    }
    if missing or mismatched:
        diagnostic_prompt_context: dict[str, Any] = dict(prompt_context)
        if missing:
            diagnostic_prompt_context["_missing_fields"] = ", ".join(missing)
        if mismatched:
            diagnostic_prompt_context["_mismatched_fields"] = json.dumps(mismatched, sort_keys=True)
        raise ReviewPromptMetadataError(
            diagnostic_code=REVIEW_PROMPT_METADATA_MISMATCH,
            requested_context=requested_context,
            prompt_context={key: str(value) for key, value in diagnostic_prompt_context.items()},
            prompt_path=prompt_path,
        )
