"""Retention/cleanup behaviour for per-invocation review-prompt files (#2439).

These tests pin the FR-001/FR-002/NFR-002 contract for
``write_review_prompt_with_metadata``:

* after exceeding the cap, only the newest retained set survives on disk;
* the just-written current invocation is *never* pruned — even when every
  other file is newer by mtime;
* the prune is fail-safe: if the underlying ``scandir``/``unlink`` raises, the
  write still returns its path and does not surface an exception.

All prompt files are redirected under a per-test ``tmp_path`` so the system
temp dir is never touched and the ``<repo-id>/<mission>/<wp>`` path scheme
(#959 isolation) is exercised end to end.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

import pytest

from specify_cli.review import prompt_metadata
from specify_cli.review.prompt_metadata import (
    DEFAULT_REVIEW_PROMPT_RETENTION,
    ReviewPromptMetadata,
    build_review_prompt_metadata,
    write_review_prompt_with_metadata,
)

pytestmark = [pytest.mark.fast]


@pytest.fixture
def review_prompts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect review-prompt storage under an isolated tmp dir."""
    monkeypatch.setattr(prompt_metadata.tempfile, "gettempdir", lambda: str(tmp_path))
    return tmp_path


def _build_meta(repo_root: Path) -> ReviewPromptMetadata:
    """Build metadata for a fresh, uniquely-scoped review invocation."""
    return build_review_prompt_metadata(
        repo_root=repo_root,
        mission_id="01J00000000000000000000000",
        mission_slug=f"mission-{uuid.uuid4().hex}",
        work_package_id="WP01",
        lane_worktree=repo_root,
        mission_branch="kitty/mission-x",
        lane_branch="kitty/mission-x-lane-a",
        base_ref="main",
    )


def _make_old_prompt(wp_dir: Path, name: str, mtime: float) -> Path:
    """Create a stale ``<name>.md`` invocation file with a fixed mtime."""
    path = wp_dir / f"{name}.md"
    path.write_text("stale invocation", encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path


def test_default_retention_is_a_sane_positive_cap() -> None:
    assert isinstance(DEFAULT_REVIEW_PROMPT_RETENTION, int)
    assert DEFAULT_REVIEW_PROMPT_RETENTION >= 1


def test_prune_keeps_only_newest_within_cap(review_prompts_root: Path) -> None:
    meta = _build_meta(review_prompts_root)
    wp_dir = meta.prompt_path.parent
    wp_dir.mkdir(parents=True, exist_ok=True)
    # Ten stale invocations, oldest -> newest by mtime.
    for i in range(10):
        _make_old_prompt(wp_dir, f"old-{i:03d}", 1000.0 + i)

    result = write_review_prompt_with_metadata("body", meta, retention=3)

    remaining = {p.name for p in wp_dir.glob("*.md")}
    assert result == meta.prompt_path
    # Cap of 3 = current invocation + the 2 newest stale files.
    assert len(remaining) == 3
    assert meta.prompt_path.name in remaining
    assert "old-009.md" in remaining
    assert "old-008.md" in remaining
    assert "old-000.md" not in remaining


def test_current_invocation_never_pruned_even_if_oldest(review_prompts_root: Path) -> None:
    meta = _build_meta(review_prompts_root)
    wp_dir = meta.prompt_path.parent
    wp_dir.mkdir(parents=True, exist_ok=True)
    # Stale files dated in the FUTURE so the current invocation is the oldest by
    # mtime — a naive "keep newest N" would delete it. It must survive anyway.
    future = time.time() + 10_000
    for i in range(5):
        _make_old_prompt(wp_dir, f"future-{i}", future + i)

    result = write_review_prompt_with_metadata("body", meta, retention=2)

    remaining = {p.name for p in wp_dir.glob("*.md")}
    assert result == meta.prompt_path
    assert meta.prompt_path.exists()
    assert meta.prompt_path.name in remaining
    # Cap of 2 = current invocation + the single newest stale file.
    assert len(remaining) == 2
    assert "future-4.md" in remaining


def test_prune_failure_on_scandir_is_swallowed(
    review_prompts_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    meta = _build_meta(review_prompts_root)

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise OSError("scandir exploded")

    monkeypatch.setattr(prompt_metadata.os, "scandir", _boom)

    result = write_review_prompt_with_metadata("body", meta, retention=2)

    assert result == meta.prompt_path
    assert meta.prompt_path.exists()


def test_prune_failure_on_unlink_is_swallowed(
    review_prompts_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    meta = _build_meta(review_prompts_root)
    wp_dir = meta.prompt_path.parent
    wp_dir.mkdir(parents=True, exist_ok=True)
    # Over the cap so the prune actually reaches unlink().
    for i in range(5):
        _make_old_prompt(wp_dir, f"old-{i:03d}", 1000.0 + i)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("unlink exploded")

    monkeypatch.setattr(Path, "unlink", _boom)

    result = write_review_prompt_with_metadata("body", meta, retention=2)

    assert result == meta.prompt_path
    assert meta.prompt_path.exists()
