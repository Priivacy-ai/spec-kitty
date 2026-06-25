"""Regression tests for the encoding-provenance gitignore repair.

Covers the bug where ``.kittify/encoding-provenance/global.jsonl`` was listed
for untracking but never added to ``.gitignore``, so a freshly-generated
(untracked) provenance log showed up in ``git status`` forever.

- apply() adds the provenance entry to .gitignore
- detect() returns True when the provenance entry is missing even though
  sync-state is already present (the already-upgraded-project case)
- detect() returns False once both entries are present and nothing is tracked
- apply() is idempotent when both entries are already present
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_3_2_0rc35_sync_state_gitignore import (
    KittifyRuntimeGitHygieneMigration,
)

pytestmark = [pytest.mark.unit]

_PROVENANCE_ENTRY = ".kittify/encoding-provenance/global.jsonl"
_SYNC_STATE_ENTRY = ".kittify/sync-state.json"


def _init_git_repo(project_root: Path) -> None:
    subprocess.run(["git", "-C", str(project_root), "init", "-q"], check=True)


def _write_gitignore(project_root: Path, *entries: str) -> None:
    project_root.joinpath(".gitignore").write_text(
        "# Added by Spec Kitty CLI (auto-managed)\n" + "\n".join(entries) + "\n",
        encoding="utf-8",
    )


def test_apply_adds_provenance_entry(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    migration = KittifyRuntimeGitHygieneMigration()

    migration.apply(tmp_path)

    gitignore_text = tmp_path.joinpath(".gitignore").read_text(encoding="utf-8")
    assert _PROVENANCE_ENTRY in gitignore_text
    assert _SYNC_STATE_ENTRY in gitignore_text


def test_detect_true_when_only_provenance_entry_missing(tmp_path: Path) -> None:
    """Already-upgraded project: sync-state present, provenance entry missing."""
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, _SYNC_STATE_ENTRY)

    assert KittifyRuntimeGitHygieneMigration().detect(tmp_path) is True


def test_detect_false_when_both_entries_present(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, _SYNC_STATE_ENTRY, _PROVENANCE_ENTRY)

    assert KittifyRuntimeGitHygieneMigration().detect(tmp_path) is False


def test_apply_is_idempotent(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, _SYNC_STATE_ENTRY, _PROVENANCE_ENTRY)

    result = KittifyRuntimeGitHygieneMigration().apply(tmp_path)

    assert result.success
    assert result.errors == []
    # Entry must appear exactly once — no duplication on re-apply.
    gitignore_text = tmp_path.joinpath(".gitignore").read_text(encoding="utf-8")
    assert gitignore_text.count(_PROVENANCE_ENTRY) == 1
