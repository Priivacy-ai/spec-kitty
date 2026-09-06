"""Real Git counterfactuals for the archive preservation gate (WP12)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from kernel.clock import UTC, datetime

from specify_cli.invocation.lifecycle import append_lifecycle_record
from specify_cli.invocation.record import ProfileInvocationRecord
from tests.architectural import test_archive_root_byte_identical as gate

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=True,
        env={**os.environ, "SPEC_KITTY_ENABLE_SAAS_SYNC": "0"},
    ).stdout


def append(repo: Path, action: str = "wp12::inspect") -> Path:
    return append_lifecycle_record(repo, ProfileInvocationRecord(
        canonical_action_id=action, phase="started",
        at=datetime(2026, 9, 6, tzinfo=UTC), agent="codex",
        mission_id="01M0QCK4D9D65AVNC15HKWAQZ7",
    ))


@pytest.fixture
def archive_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")
    repo = tmp_path / "archive"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main")
    git(repo, "config", "user.email", "wp12@example.invalid")
    git(repo, "config", "user.name", "WP12 fixture")
    git(repo, "config", "commit.gpgsign", "false")
    append(repo, "wp12::historical")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Nonempty historical archive")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    monkeypatch.setattr(gate, "REPO_ROOT", repo)
    return repo


def test_real_writer_append_passes_existing_gate(archive_repo: Path) -> None:
    """RED first: the old gate rejects a genuine, model-valid suffix."""
    gate.test_archive_baseline_is_non_empty()
    assert git(archive_repo, "merge-base", "HEAD", "origin/main").strip()
    append(archive_repo)
    gate.test_no_preexisting_archived_file_was_modified()


def test_new_archive_path_remains_allowed(archive_repo: Path) -> None:
    path = archive_repo / "kitty-ops/new-proof.txt"
    path.write_bytes(b"New proof\n")
    git(archive_repo, "add", "kitty-ops/new-proof.txt")
    gate.test_no_preexisting_archived_file_was_modified()


def test_unchanged_nonempty_archive_passes(archive_repo: Path) -> None:
    gate.test_archive_baseline_is_non_empty()
    gate.test_no_preexisting_archived_file_was_modified()
