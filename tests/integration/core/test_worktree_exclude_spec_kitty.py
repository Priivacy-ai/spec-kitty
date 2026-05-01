"""Integration tests for WP07 FR-016 per-worktree ``.spec-kitty/`` exclude writer.

Exercises ``_ensure_spec_kitty_exclude`` and the worktree-creation paths that
invoke it, confirming:

* the helper writes ``.spec-kitty/`` to the per-worktree
  ``<git-common-dir>/worktrees/<name>/info/exclude`` file;
* the entry is idempotent (re-invocation never duplicates lines);
* the helper is called from the live worktree-creation path in
  ``create_feature_worktree`` so new lane worktrees benefit without a
  separate opt-in step;
* failures in git probing are swallowed (non-git paths must not raise).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.core.worktree import (
    _ensure_spec_kitty_exclude,
    create_feature_worktree,
)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _make_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main", str(path)])
    _run(["git", "-C", str(path), "config", "user.email", "t@example.com"])
    _run(["git", "-C", str(path), "config", "user.name", "T"])
    # An initial commit is required before ``git worktree add -b`` can succeed.
    (path / "README.md").write_text("seed\n", encoding="utf-8")
    _run(["git", "-C", str(path), "add", "README.md"])
    _run(["git", "-C", str(path), "commit", "-q", "-m", "seed"])


def _resolve_exclude_path(worktree_path: Path) -> Path:
    """Return the per-worktree info/exclude path.

    This deliberately re-derives the path independently of the helper under
    test so the test exercises the real on-disk location. For a git worktree
    the path is ``<git-common-dir>/worktrees/<name>/info/exclude``, NOT
    ``<worktree>/.git/info/exclude`` (the worktree's ``.git`` is a *file*
    pointing at the common dir).
    """
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
        check=True,
    )
    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (worktree_path / git_dir).resolve()
    return git_dir / "info" / "exclude"


def test_ensure_spec_kitty_exclude_writes_entry_in_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "main"
    _make_repo(repo)

    worktree = tmp_path / "worktree"
    _run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            "-b",
            "lane-a",
            str(worktree),
        ]
    )

    _ensure_spec_kitty_exclude(worktree)

    exclude_path = _resolve_exclude_path(worktree)
    assert exclude_path.exists(), "exclude file must be created"
    content = exclude_path.read_text(encoding="utf-8")
    assert ".spec-kitty/" in content.splitlines(), f"exclude file must contain .spec-kitty/ entry; got: {content!r}"
    # The exclude path is per-worktree, NOT under <worktree>/.git (which is a
    # file for worktrees). This sanity check guards against the common
    # mistake of writing to the wrong location.
    assert "worktrees" in exclude_path.parts, f"exclude must live under <git-common-dir>/worktrees/.../info/exclude, got: {exclude_path}"


def test_ensure_spec_kitty_exclude_is_idempotent(tmp_path: Path) -> None:
    """Re-invocation must not duplicate the ``.spec-kitty/`` entry."""
    repo = tmp_path / "main"
    _make_repo(repo)

    worktree = tmp_path / "worktree"
    _run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            "-b",
            "lane-a",
            str(worktree),
        ]
    )

    for _ in range(5):
        _ensure_spec_kitty_exclude(worktree)

    exclude_path = _resolve_exclude_path(worktree)
    content = exclude_path.read_text(encoding="utf-8")
    matches = [line for line in content.splitlines() if line.strip() == ".spec-kitty/"]
    assert len(matches) == 1, f"Expected exactly one '.spec-kitty/' entry after 5 invocations; found {len(matches)}: {content!r}"


def test_ensure_spec_kitty_exclude_preserves_existing_lines(tmp_path: Path) -> None:
    """Pre-existing exclude lines must be preserved, not overwritten."""
    repo = tmp_path / "main"
    _make_repo(repo)

    worktree = tmp_path / "worktree"
    _run(
        [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            "-b",
            "lane-a",
            str(worktree),
        ]
    )

    exclude_path = _resolve_exclude_path(worktree)
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    exclude_path.write_text("# pre-existing\nnode_modules/\n", encoding="utf-8")

    _ensure_spec_kitty_exclude(worktree)

    content = exclude_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    assert "# pre-existing" in lines
    assert "node_modules/" in lines
    assert ".spec-kitty/" in lines


def test_ensure_spec_kitty_exclude_swallows_non_git_path(tmp_path: Path) -> None:
    """On a non-git path, helper must not raise (failures are advisory)."""
    non_git = tmp_path / "not-a-repo"
    non_git.mkdir()
    # Must not raise.
    _ensure_spec_kitty_exclude(non_git)


def test_create_feature_worktree_invokes_exclude_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Live verification: ``create_feature_worktree`` must write the entry.

    This is the integration-level contract: operators get the FR-016
    protection without opting in. A new lane worktree created through the
    production code path should come back with ``.spec-kitty/`` in its
    per-worktree exclude file.
    """
    repo = tmp_path / "main"
    _make_repo(repo)

    # Avoid filesystem dependencies on the packaged spec template — the
    # ``create_feature_worktree`` helper falls back to creating an empty
    # ``spec.md`` when no template is found, which is fine for this test.
    monkeypatch.chdir(repo)

    mission_id = "01JXFAKEFAKEFAKEFAKE123456"  # 26-char ULID shape
    mission_slug = "fake-mission"

    worktree_path, _feature_dir = create_feature_worktree(
        repo_root=repo,
        mission_slug=mission_slug,
        mission_id=mission_id,
    )

    exclude_path = _resolve_exclude_path(worktree_path)
    assert exclude_path.exists(), "create_feature_worktree must produce a per-worktree exclude file"
    lines = exclude_path.read_text(encoding="utf-8").splitlines()
    assert ".spec-kitty/" in lines, f"create_feature_worktree must invoke _ensure_spec_kitty_exclude; exclude content: {lines!r}"
