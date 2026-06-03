"""Tests for the .kittify runtime git hygiene migration."""

import subprocess
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_3_2_0rc35_sync_state_gitignore import (
    KittifyRuntimeGitHygieneMigration,
)


pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def test_detect_true_when_sync_state_missing(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(".kittify/runtime/\n", encoding="utf-8")

    assert KittifyRuntimeGitHygieneMigration().detect(tmp_path)


def test_apply_adds_sync_state_entry(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(".kittify/runtime/\n", encoding="utf-8")

    result = KittifyRuntimeGitHygieneMigration().apply(tmp_path)

    assert result.success
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".kittify/sync-state.json" in content


def test_apply_is_idempotent(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(
        ".kittify/sync-state.json\n",
        encoding="utf-8",
    )

    migration = KittifyRuntimeGitHygieneMigration()
    first = migration.apply(tmp_path)
    second = migration.apply(tmp_path)

    assert first.success
    assert second.success
    assert (
        tmp_path / ".gitignore"
    ).read_text(encoding="utf-8").count(".kittify/sync-state.json") == 1


def test_apply_untracks_known_local_runtime_files(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / ".gitignore").write_text(
        ".kittify/charter/context-state.json\n"
        ".kittify/encoding-provenance/\n"
        ".kittify/sync-state.json\n",
        encoding="utf-8",
    )
    context_state = tmp_path / ".kittify" / "charter" / "context-state.json"
    provenance = tmp_path / ".kittify" / "encoding-provenance" / "global.jsonl"
    context_state.parent.mkdir(parents=True)
    provenance.parent.mkdir(parents=True)
    context_state.write_text("{}\n", encoding="utf-8")
    provenance.write_text("{}\n", encoding="utf-8")
    _git(tmp_path, "add", "-f", ".kittify/charter/context-state.json")
    _git(tmp_path, "add", "-f", ".kittify/encoding-provenance/global.jsonl")
    _git(tmp_path, "commit", "-q", "-m", "track runtime files")

    result = KittifyRuntimeGitHygieneMigration().apply(tmp_path)

    assert result.success
    assert context_state.exists()
    assert provenance.exists()
    assert _git(tmp_path, "ls-files", ".kittify/charter/context-state.json").stdout == ""
    assert _git(tmp_path, "ls-files", ".kittify/encoding-provenance/global.jsonl").stdout == ""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
