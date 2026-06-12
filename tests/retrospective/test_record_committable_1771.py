"""FR-006 / #1771 regression: the retrospective record must be committable.

Before the cycle-2 relocation, ``retrospect create`` wrote the record to
``.kittify/missions/<mission_id>/retrospective.yaml`` — a path matched by the
``.kittify/missions/`` rule in ``.gitignore`` (line 61). The record was therefore
silently discarded on checkout/clone and uncommittable without ``git add -f``.

These tests prove the record now lands in the tracked feature_dir
(``kitty-specs/<slug>/retrospective.yaml``) and is NOT git-ignored, by running
``git check-ignore`` against a repo carrying the real ignore rule.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.retrospective.writer import (
    canonical_record_path,
    _legacy_record_path,
    write_record,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# Reuse the canonical fixture record from the round-trip suite.
from tests.retrospective.test_schema_roundtrip import make_completed_record  # noqa: E402


def _init_repo_with_gitignore(root: Path) -> None:
    """Initialise a git repo that ignores the .kittify tree like the real project."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    # The load-bearing rule from the project .gitignore (line 61).
    (root / ".gitignore").write_text(".kittify/missions/\n", encoding="utf-8")


def _is_git_ignored(root: Path, path: Path) -> bool:
    """Return True if *path* is matched by .gitignore (git check-ignore exit 0)."""
    rel = path.relative_to(root)
    result = subprocess.run(
        ["git", "check-ignore", str(rel)],
        cwd=root,
        capture_output=True,
    )
    # Exit 0 → ignored; exit 1 → not ignored (committable).
    return result.returncode == 0


def test_canonical_record_path_is_not_gitignored(tmp_path: Path) -> None:
    """The resolved record path is committable (NOT matched by .gitignore)."""
    _init_repo_with_gitignore(tmp_path)
    record = make_completed_record()

    record_path = canonical_record_path(tmp_path, record.mission.mission_slug)

    assert "kitty-specs" in record_path.parts
    assert ".kittify" not in record_path.parts
    assert not _is_git_ignored(tmp_path, record_path), (
        f"Retrospective record path {record_path} is git-ignored — #1771 regression"
    )


def test_legacy_path_was_gitignored_control(tmp_path: Path) -> None:
    """Control: the OLD .kittify/missions/ path IS git-ignored (the original bug)."""
    _init_repo_with_gitignore(tmp_path)

    legacy = _legacy_record_path(tmp_path, "01KQ6YEGT4YBZ3GZF7X680KQ3V")

    assert _is_git_ignored(tmp_path, legacy), (
        "The legacy .kittify/missions/ path should be git-ignored — proves the "
        "relocation actually moves the record off an ignored path."
    )


def test_written_record_is_committable_end_to_end(tmp_path: Path) -> None:
    """write_record() lands the record where git can stage it (committable)."""
    _init_repo_with_gitignore(tmp_path)
    record = make_completed_record()

    written = write_record(record, repo_root=tmp_path)

    assert written.exists()
    assert not _is_git_ignored(tmp_path, written)

    # git add must actually stage it (no -f). A gitignored path would not stage.
    subprocess.run(
        ["git", "add", str(written.relative_to(tmp_path))],
        cwd=tmp_path,
        check=True,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "retrospective.yaml" in staged, (
        "Record was not staged — it is uncommittable (#1771 regression)"
    )
