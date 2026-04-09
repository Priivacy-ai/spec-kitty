"""T1.6 — Regression tests: init inside an existing git repo leaves git state unchanged.

Verifies:
- Running init inside a repo with an existing commit leaves HEAD hash unchanged.
- git log still shows only the original commit (no new commit added).
- git status --porcelain shows only new init files (no modified tracked files).
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest
from rich.console import Console  # noqa: F401  (used in _make_app helper)
from typer import Typer
from typer.testing import CliRunner

from specify_cli.cli.commands import init as init_module
from specify_cli.cli.commands.init import register_init_command


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(monkeypatch: pytest.MonkeyPatch) -> Typer:
    out = io.StringIO()
    console = Console(file=out, force_terminal=False, highlight=False)
    app = Typer()

    register_init_command(
        app,
        console=console,
        show_banner=lambda: None,
        activate_mission=lambda proj, mtype, mdisplay, _con: mdisplay,
        ensure_executable_scripts=lambda path, tracker=None: None,
    )
    return app


def _run(app: Typer, args: list[str]) -> object:
    runner = CliRunner()
    return runner.invoke(app, args, catch_exceptions=True)


def _fake_copy_package(project_path: Path) -> Path:
    kittify = project_path / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    return kittify / "templates" / "command-templates"


def _git(*args: str, cwd: Path) -> str:
    """Run a git command and return its stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _setup_git_repo_with_commit(repo_path: Path) -> str:
    """Initialize a git repo and create one commit.  Return the HEAD hash."""
    _git("init", cwd=repo_path)
    _git("config", "user.email", "test@example.com", cwd=repo_path)
    _git("config", "user.name", "Test User", cwd=repo_path)

    readme = repo_path / "README.md"
    readme.write_text("# Test project\n", encoding="utf-8")

    _git("add", "README.md", cwd=repo_path)
    _git("-c", "commit.gpgsign=false", "commit", "-m", "initial user commit", cwd=repo_path)

    return _git("rev-parse", "HEAD", cwd=repo_path)


# ---------------------------------------------------------------------------
# T1.6: init inside existing repo does not touch git state
# ---------------------------------------------------------------------------

def test_init_does_not_touch_git_state_in_existing_repo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """T1.6: Running init inside an existing git repo leaves HEAD hash and history unchanged."""
    repo = tmp_path / "myrepo"
    repo.mkdir()

    # Set up a git repo with one commit
    head_before = _setup_git_repo_with_commit(repo)
    assert head_before, "HEAD hash should be non-empty after initial commit"

    commit_count_before = len(
        _git("log", "--oneline", cwd=repo).splitlines()
    )
    assert commit_count_before == 1, "Should have exactly 1 commit before init"

    # Run init inside the existing repo
    app = _make_app(monkeypatch)

    monkeypatch.chdir(repo)
    monkeypatch.setattr(init_module, "get_local_repo_root", lambda override_path=None: None)
    monkeypatch.setattr(init_module, "copy_specify_base_from_package", _fake_copy_package)

    result = _run(app, ["init", "--ai", "codex", "--non-interactive"])
    assert result.exit_code == 0, f"init failed inside existing repo: {result.output}"

    # HEAD hash must be unchanged
    head_after = _git("rev-parse", "HEAD", cwd=repo)
    assert head_after == head_before, (
        f"HEAD changed after init!\n  before: {head_before}\n  after:  {head_after}\n"
        "init must not create any commits."
    )

    # Commit count must be unchanged
    commit_count_after = len(
        _git("log", "--oneline", cwd=repo).splitlines()
    )
    assert commit_count_after == commit_count_before, (
        f"Commit count changed from {commit_count_before} to {commit_count_after}.\n"
        "init must not create any git commits."
    )

    # Existing tracked files must be unmodified (README.md should be clean)
    porcelain = _git("status", "--porcelain", cwd=repo)
    modified_tracked = [
        line for line in porcelain.splitlines()
        if not line.startswith("?? ")  # untracked new files are expected
    ]
    assert modified_tracked == [], (
        f"init modified existing tracked files:\n"
        + "\n".join(modified_tracked)
    )
