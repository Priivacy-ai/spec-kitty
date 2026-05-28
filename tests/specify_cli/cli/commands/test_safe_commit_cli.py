"""Integration tests for the post-#1348 ``spec-kitty safe-commit`` CLI.

These tests exercise the four CLI modes specified by WP02 / T009:

1. ``--to-branch <ref>`` happy path — succeeds when HEAD matches.
2. Missing ``--to-branch`` AND no env var — exits non-zero with a clear message.
3. Missing ``--to-branch`` WITH ``SPEC_KITTY_INFER_DESTINATION_REF=1`` —
   succeeds, prints a one-line stderr deprecation.
4. ``--to-branch`` pointing at a non-HEAD branch — exits non-zero with the
   ``SafeCommitHeadMismatch`` error surface (stable error code from WP01).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app


pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# Newer click/typer ships separate stdout/stderr on Result by default; older
# versions accept ``mix_stderr=False``. We construct conservatively for both.
try:
    runner = CliRunner(mix_stderr=False)  # type: ignore[call-arg]
except TypeError:
    runner = CliRunner()


def _init_lane_repo(repo: Path, *, branch: str = "kitty/mission-test-01ABCDEF") -> None:
    """Initialize a tmp git repo checked out to a non-protected lane branch."""
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", f"--initial-branch={branch}"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / ".kittify").mkdir()
    (repo / ".kittify" / "config.json").write_text("{}\n", encoding="utf-8")
    (repo / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", ".kittify/config.json"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial commit"], cwd=repo, check=True, capture_output=True)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# T009 — CLI mode tests
# ---------------------------------------------------------------------------


def test_cli_with_to_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`--to-branch <ref>` succeeds when HEAD matches the declared branch."""
    monkeypatch.delenv("SPEC_KITTY_INFER_DESTINATION_REF", raising=False)
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    _init_lane_repo(tmp_path, branch="kitty/mission-test-01ABCDEF")

    target = tmp_path / "alpha.txt"
    target.write_text("alpha v1\n", encoding="utf-8")

    head_before = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            cli_app,
            [
                "safe-commit",
                "--to-branch",
                "kitty/mission-test-01ABCDEF",
                "--message",
                "T009: add alpha",
                "--json",
                "alpha.txt",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, result.stdout + (result.stderr or "")
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["committed"] is True

    head_after = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    assert head_after != head_before, "expected a new commit on HEAD"
    last_message = _git(tmp_path, "log", "-1", "--format=%s").stdout.strip()
    assert last_message == "T009: add alpha"


def test_cli_without_to_branch_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No `--to-branch` and no env var → CLI exits non-zero with a clear message."""
    monkeypatch.delenv("SPEC_KITTY_INFER_DESTINATION_REF", raising=False)
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    _init_lane_repo(tmp_path, branch="kitty/mission-test-01ABCDEF")

    target = tmp_path / "beta.txt"
    target.write_text("beta v1\n", encoding="utf-8")

    head_before = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            cli_app,
            ["safe-commit", "--message", "T009: no flag", "--json", "beta.txt"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert "--to-branch" in payload["error"]
    assert "SPEC_KITTY_INFER_DESTINATION_REF" in payload["error"]

    head_after = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    assert head_after == head_before, "no commit must be created when --to-branch is missing"


def test_cli_deprecation_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`SPEC_KITTY_INFER_DESTINATION_REF=1` without `--to-branch` → succeeds with stderr deprecation."""
    monkeypatch.setenv("SPEC_KITTY_INFER_DESTINATION_REF", "1")
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    _init_lane_repo(tmp_path, branch="kitty/mission-test-01ABCDEF")

    target = tmp_path / "gamma.txt"
    target.write_text("gamma v1\n", encoding="utf-8")

    head_before = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            cli_app,
            ["safe-commit", "--message", "T009: deprecation env var", "--json", "gamma.txt"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0, (result.stdout or "") + (result.stderr or "")
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["committed"] is True

    # Deprecation lands on stderr (not stdout) so --json piping is unaffected.
    stderr_text = result.stderr or ""
    assert "warning:" in stderr_text
    assert "--to-branch will be required in v3.3" in stderr_text
    assert "SPEC_KITTY_INFER_DESTINATION_REF" in stderr_text

    head_after = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    assert head_after != head_before, "expected a new commit under the deprecation env var path"


def test_cli_head_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`--to-branch` for a branch that isn't HEAD → exits non-zero with HEAD-mismatch surface."""
    monkeypatch.delenv("SPEC_KITTY_INFER_DESTINATION_REF", raising=False)
    monkeypatch.delenv("SPEC_KITTY_TEST_MODE", raising=False)
    _init_lane_repo(tmp_path, branch="kitty/mission-test-01ABCDEF")

    # Create a second branch so destination_ref is a real ref, not a missing one.
    _git(tmp_path, "branch", "kitty/mission-other-02ZZZZZZ")

    target = tmp_path / "delta.txt"
    target.write_text("delta v1\n", encoding="utf-8")

    head_before = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(
            cli_app,
            [
                "safe-commit",
                "--to-branch",
                "kitty/mission-other-02ZZZZZZ",
                "--message",
                "T009: head mismatch",
                "--json",
                "delta.txt",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["success"] is False

    # The error must surface the destination-ref-aware HEAD assertion (NFR-007:
    # stable error code from SafeCommitHeadMismatch in WP01).
    err_msg = payload["error"]
    head_mismatch_signals = (
        "SAFE_COMMIT_HEAD_MISMATCH",
        "head_mismatch",
        "HEAD does not match",
        "destination_ref",
        "HEAD",
    )
    assert any(signal in err_msg for signal in head_mismatch_signals), (
        f"expected HEAD-mismatch signal in error message, got: {err_msg!r}"
    )

    head_after = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    assert head_after == head_before, "no commit must be created on HEAD-mismatch"
