"""Tests for the public ``spec-kitty safe-commit`` command."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app


pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

runner = CliRunner()


def _init_spec_kitty_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / ".kittify").mkdir()
    (repo / ".kittify" / "config.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", ".kittify/config.json"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)


@pytest.mark.parametrize(
    "message",
    [
        "chore: apply spec-kitty upgrade changes (3.0.3 -> 3.1.4)",
        "chore: release 3.2.0",
        "release: 3.2.0",
        "chore(099-demo): record done transitions for merged WPs",
    ],
)
def test_public_safe_commit_does_not_honor_internal_protected_branch_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    message: str,
) -> None:
    """Public CLI messages must not spoof internal safe_commit exceptions."""
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", raising=False)
    _init_spec_kitty_repo(tmp_path)
    (tmp_path / "change.txt").write_text("protected branch change\n", encoding="utf-8")
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Post-#1348 (WP02): --to-branch is required. The test runs on
        # `main` (the protected branch) so the helper rejects the commit at the
        # protected-branch check, which is what this test asserts.
        result = runner.invoke(
            cli_app,
            ["safe-commit", "--to-branch", "main", "--message", message, "--json", "change.txt"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    payload = json.loads(result.stdout)
    head_after = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert result.exit_code == 1
    assert payload["success"] is False
    assert "protected branch 'main'" in payload["error"]
    assert head_after == head_before
