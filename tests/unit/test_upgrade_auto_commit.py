"""Tests for upgrade auto-commit path filtering and commit wiring."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import specify_cli.cli.commands.upgrade as upgrade_cmd


# ---------------------------------------------------------------------------
# _git_status_paths – parsing logic (real subprocess mock)
# ---------------------------------------------------------------------------


def test_git_status_paths_parses_modified_files(tmp_path: Path, monkeypatch) -> None:
    """Porcelain output with modified files is parsed correctly."""
    # Simulate: " M src/foo.py\0 M src/bar.py\0"
    raw = b" M src/foo.py\0 M src/bar.py\0"
    fake_result = MagicMock(returncode=0, stdout=raw)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: fake_result,
    )
    paths = upgrade_cmd._git_status_paths(tmp_path)
    assert paths == {"src/foo.py", "src/bar.py"}


def test_git_status_paths_parses_added_and_untracked(tmp_path: Path, monkeypatch) -> None:
    """New files (A) and untracked files (??) are both captured."""
    raw = b"A  .kittify/metadata.yaml\0?? docs/new.md\0"
    fake_result = MagicMock(returncode=0, stdout=raw)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: fake_result)
    paths = upgrade_cmd._git_status_paths(tmp_path)
    assert paths == {".kittify/metadata.yaml", "docs/new.md"}


def test_git_status_paths_handles_rename(tmp_path: Path, monkeypatch) -> None:
    """Rename entries use the destination (new) path."""
    # git status -z for rename: "R  old.py\0new.py\0"
    raw = b"R  old.py\0new.py\0"
    fake_result = MagicMock(returncode=0, stdout=raw)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: fake_result)
    paths = upgrade_cmd._git_status_paths(tmp_path)
    assert "new.py" in paths
    assert "old.py" not in paths


def test_git_status_paths_returns_none_on_failure(tmp_path: Path, monkeypatch) -> None:
    """Non-zero returncode → None (not empty set)."""
    fake_result = MagicMock(returncode=128, stdout=b"")
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: fake_result)
    result = upgrade_cmd._git_status_paths(tmp_path)
    assert result is None


def test_git_status_paths_empty_repo(tmp_path: Path, monkeypatch) -> None:
    """Clean working tree returns empty set (not None)."""
    fake_result = MagicMock(returncode=0, stdout=b"")
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: fake_result)
    result = upgrade_cmd._git_status_paths(tmp_path)
    assert result == set()


def test_git_status_paths_strips_dot_slash(tmp_path: Path, monkeypatch) -> None:
    """Leading ./ is normalised away."""
    raw = b" M ./src/foo.py\0"
    fake_result = MagicMock(returncode=0, stdout=raw)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: fake_result)
    paths = upgrade_cmd._git_status_paths(tmp_path)
    assert paths == {"src/foo.py"}


# ---------------------------------------------------------------------------
# _is_upgrade_commit_eligible – edge cases
# ---------------------------------------------------------------------------


def test_eligible_subdirectory_file(tmp_path: Path) -> None:
    assert upgrade_cmd._is_upgrade_commit_eligible("kitty-specs/001/WP01.md", tmp_path) is True


def test_eligible_rejects_empty(tmp_path: Path) -> None:
    assert upgrade_cmd._is_upgrade_commit_eligible("", tmp_path) is False


def test_eligible_rejects_whitespace_only(tmp_path: Path) -> None:
    assert upgrade_cmd._is_upgrade_commit_eligible("   ", tmp_path) is False


def test_eligible_rejects_root_level_file(tmp_path: Path) -> None:
    assert upgrade_cmd._is_upgrade_commit_eligible("README.md", tmp_path) is False


def test_eligible_rejects_parent_traversal(tmp_path: Path) -> None:
    assert upgrade_cmd._is_upgrade_commit_eligible("../secret.txt", tmp_path) is False


def test_eligible_accepts_kittify_in_non_home(tmp_path: Path) -> None:
    assert upgrade_cmd._is_upgrade_commit_eligible(".kittify/metadata.yaml", tmp_path) is True


def test_eligible_rejects_home_kittify(monkeypatch) -> None:
    home = Path.home().resolve()
    assert upgrade_cmd._is_upgrade_commit_eligible(".kittify/metadata.yaml", home) is False


# ---------------------------------------------------------------------------
# _prepare_upgrade_commit_files
# ---------------------------------------------------------------------------


def test_prepare_upgrade_commit_files_excludes_root_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir()

    monkeypatch.setattr(
        upgrade_cmd,
        "_git_status_paths",
        lambda _repo: {
            ".kittify/metadata.yaml",
            "kitty-specs/001-test/tasks/WP01.md",
            "README.md",
            "AGENTS.md",
            "docs/how-to/upgrade.md",
        },
    )

    files = upgrade_cmd._prepare_upgrade_commit_files(project_path, baseline_paths=set())

    assert {str(path) for path in files} == {
        ".kittify/metadata.yaml",
        "kitty-specs/001-test/tasks/WP01.md",
        "docs/how-to/upgrade.md",
    }


def test_prepare_upgrade_commit_files_excludes_preexisting_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir()

    monkeypatch.setattr(
        upgrade_cmd,
        "_git_status_paths",
        lambda _repo: {
            ".kittify/metadata.yaml",
            "kitty-specs/001-test/tasks/WP01.md",
        },
    )

    files = upgrade_cmd._prepare_upgrade_commit_files(
        project_path,
        baseline_paths={"kitty-specs/001-test/tasks/WP01.md"},
    )

    assert [str(path) for path in files] == [".kittify/metadata.yaml"]


def test_prepare_upgrade_commit_files_skips_home_level_kittify(monkeypatch) -> None:
    project_path = Path.home().resolve()

    monkeypatch.setattr(
        upgrade_cmd,
        "_git_status_paths",
        lambda _repo: {
            ".kittify/metadata.yaml",
            "Code/demo/.kittify/metadata.yaml",
            "Code/demo/kitty-specs/001-test/tasks/WP01.md",
        },
    )

    files = upgrade_cmd._prepare_upgrade_commit_files(project_path, baseline_paths=set())

    assert {str(path) for path in files} == {
        "Code/demo/.kittify/metadata.yaml",
        "Code/demo/kitty-specs/001-test/tasks/WP01.md",
    }


def test_prepare_skips_when_baseline_is_none(tmp_path: Path) -> None:
    """When baseline git status failed (None), skip auto-commit entirely."""
    files = upgrade_cmd._prepare_upgrade_commit_files(tmp_path, baseline_paths=None)
    assert files == []


def test_prepare_skips_when_current_status_fails(tmp_path: Path, monkeypatch) -> None:
    """When post-upgrade git status fails, skip auto-commit."""
    monkeypatch.setattr(upgrade_cmd, "_git_status_paths", lambda _repo: None)
    files = upgrade_cmd._prepare_upgrade_commit_files(tmp_path, baseline_paths=set())
    assert files == []


# ---------------------------------------------------------------------------
# _auto_commit_upgrade_changes
# ---------------------------------------------------------------------------


def test_auto_commit_upgrade_changes_calls_safe_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir()

    monkeypatch.setattr(
        upgrade_cmd,
        "_prepare_upgrade_commit_files",
        lambda _project, baseline_paths: [
            Path(".kittify/metadata.yaml"),
            Path("kitty-specs/001-test/tasks/WP01.md"),
        ],
    )

    captured: dict[str, object] = {}

    def _fake_safe_commit(
        repo_path: Path,
        files_to_commit: list[Path],
        commit_message: str,
        allow_empty: bool = False,
    ) -> bool:
        captured["repo_path"] = repo_path
        captured["files_to_commit"] = files_to_commit
        captured["commit_message"] = commit_message
        captured["allow_empty"] = allow_empty
        return True

    monkeypatch.setattr(upgrade_cmd, "safe_commit", _fake_safe_commit)

    committed, committed_paths, warning = upgrade_cmd._auto_commit_upgrade_changes(
        project_path=project_path,
        from_version="0.13.0",
        to_version="0.14.0",
        baseline_paths=set(),
    )

    assert committed is True
    assert warning is None
    assert committed_paths == [
        ".kittify/metadata.yaml",
        "kitty-specs/001-test/tasks/WP01.md",
    ]
    assert captured["repo_path"] == project_path
    assert captured["files_to_commit"] == [
        Path(".kittify/metadata.yaml"),
        Path("kitty-specs/001-test/tasks/WP01.md"),
    ]
    assert "0.13.0 -> 0.14.0" in str(captured["commit_message"])
    assert captured["allow_empty"] is False


def test_auto_commit_returns_warning_on_safe_commit_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """When safe_commit returns False the caller gets a warning string."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    monkeypatch.setattr(
        upgrade_cmd,
        "_prepare_upgrade_commit_files",
        lambda _project, baseline_paths: [Path("kitty-specs/001/WP01.md")],
    )
    monkeypatch.setattr(
        upgrade_cmd,
        "safe_commit",
        lambda **_kw: False,
    )

    committed, committed_paths, warning = upgrade_cmd._auto_commit_upgrade_changes(
        project_path=project_path,
        from_version="0.13.0",
        to_version="0.14.0",
        baseline_paths=set(),
    )

    assert committed is False
    assert warning is not None
    assert "review and commit manually" in warning
    assert committed_paths == ["kitty-specs/001/WP01.md"]


def test_auto_commit_noop_when_no_new_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """No files to commit → (False, [], None) with no safe_commit call."""
    monkeypatch.setattr(
        upgrade_cmd,
        "_prepare_upgrade_commit_files",
        lambda _project, baseline_paths: [],
    )

    committed, committed_paths, warning = upgrade_cmd._auto_commit_upgrade_changes(
        project_path=tmp_path,
        from_version="0.13.0",
        to_version="0.14.0",
        baseline_paths=set(),
    )

    assert committed is False
    assert committed_paths == []
    assert warning is None


def test_auto_commit_noop_when_baseline_is_none(
    tmp_path: Path,
) -> None:
    """None baseline propagates through to no-op (no accidental commits)."""
    committed, committed_paths, warning = upgrade_cmd._auto_commit_upgrade_changes(
        project_path=tmp_path,
        from_version="0.13.0",
        to_version="0.14.0",
        baseline_paths=None,
    )

    assert committed is False
    assert committed_paths == []
    assert warning is None


# ---------------------------------------------------------------------------
# upgrade() function – auto-commit wiring (no-migrations path)
# ---------------------------------------------------------------------------


def _setup_upgrade_project(tmp_path: Path) -> Path:
    """Create a minimal .kittify project structure for upgrade() tests."""
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    metadata_file = kittify_dir / "metadata.yaml"
    metadata_file.write_text(
        "spec_kitty:\n"
        "  version: '1.0.0a1'\n"
        "  initialized_at: '2026-01-01T00:00:00'\n"
        "environment:\n"
        "  python_version: '3.12'\n"
        "  platform: linux\n"
        "  platform_version: ''\n"
        "migrations:\n"
        "  applied: []\n"
    )
    return tmp_path


def test_upgrade_no_migrations_json_includes_auto_commit_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The JSON output of a no-migrations upgrade includes auto_committed / auto_commit_paths."""
    project_path = _setup_upgrade_project(tmp_path)

    # Patch cwd to our project
    monkeypatch.setattr(Path, "cwd", lambda: project_path)

    # Baseline returns a set (git works), post-upgrade has one new file
    call_count = {"n": 0}

    def _fake_status(repo_path):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return set()  # baseline: clean
        return {".kittify/metadata.yaml"}  # post-upgrade: metadata changed

    monkeypatch.setattr(upgrade_cmd, "_git_status_paths", _fake_status)
    monkeypatch.setattr(
        upgrade_cmd,
        "safe_commit",
        lambda repo_path, files_to_commit, commit_message, allow_empty=False: True,
    )

    # Capture console output
    captured_output: list[str] = []
    monkeypatch.setattr(
        upgrade_cmd.console,
        "print",
        lambda text, **kw: captured_output.append(str(text)),
    )

    upgrade_cmd.upgrade(
        dry_run=False,
        force=True,
        target="1.0.0a1",  # same as metadata → no migrations
        json_output=True,
        verbose=False,
        no_worktrees=True,
    )

    assert len(captured_output) == 1
    data = json.loads(captured_output[0])
    assert data["status"] == "up_to_date"
    assert data["auto_committed"] is True
    assert ".kittify/metadata.yaml" in data["auto_commit_paths"]
    assert data["warnings"] == []


def test_upgrade_dry_run_skips_auto_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """In dry-run mode the upgrade command must not auto-commit anything."""
    project_path = _setup_upgrade_project(tmp_path)
    monkeypatch.setattr(Path, "cwd", lambda: project_path)

    # baseline_changed_paths will be called once; auto_commit should not be called
    monkeypatch.setattr(upgrade_cmd, "_git_status_paths", lambda _rp: set())

    safe_commit_called = {"called": False}

    def _spy_safe_commit(**_kw):
        safe_commit_called["called"] = True
        return True

    monkeypatch.setattr(upgrade_cmd, "safe_commit", _spy_safe_commit)

    captured_output: list[str] = []
    monkeypatch.setattr(
        upgrade_cmd.console,
        "print",
        lambda text, **kw: captured_output.append(str(text)),
    )

    upgrade_cmd.upgrade(
        dry_run=True,
        force=True,
        target="1.0.0a1",
        json_output=True,
        verbose=False,
        no_worktrees=True,
    )

    data = json.loads(captured_output[0])
    assert data["auto_committed"] is False
    assert data["auto_commit_paths"] == []
    assert safe_commit_called["called"] is False


def test_upgrade_baseline_failure_skips_auto_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """When the baseline git-status fails (None), auto-commit is skipped entirely."""
    project_path = _setup_upgrade_project(tmp_path)
    monkeypatch.setattr(Path, "cwd", lambda: project_path)

    # Baseline fails → None
    monkeypatch.setattr(upgrade_cmd, "_git_status_paths", lambda _rp: None)

    safe_commit_called = {"called": False}

    def _spy_safe_commit(**_kw):
        safe_commit_called["called"] = True
        return True

    monkeypatch.setattr(upgrade_cmd, "safe_commit", _spy_safe_commit)

    captured_output: list[str] = []
    monkeypatch.setattr(
        upgrade_cmd.console,
        "print",
        lambda text, **kw: captured_output.append(str(text)),
    )

    upgrade_cmd.upgrade(
        dry_run=False,
        force=True,
        target="1.0.0a1",
        json_output=True,
        verbose=False,
        no_worktrees=True,
    )

    data = json.loads(captured_output[0])
    assert data["auto_committed"] is False
    assert data["auto_commit_paths"] == []
    assert safe_commit_called["called"] is False


def test_upgrade_no_migrations_rich_output_shows_auto_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Rich (non-JSON) output shows the auto-commit summary line."""
    project_path = _setup_upgrade_project(tmp_path)
    monkeypatch.setattr(Path, "cwd", lambda: project_path)

    call_count = {"n": 0}

    def _fake_status(repo_path):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return set()
        return {"kitty-specs/001/tasks/WP01.md"}

    monkeypatch.setattr(upgrade_cmd, "_git_status_paths", _fake_status)
    monkeypatch.setattr(
        upgrade_cmd,
        "safe_commit",
        lambda repo_path, files_to_commit, commit_message, allow_empty=False: True,
    )

    captured_output: list[str] = []
    monkeypatch.setattr(
        upgrade_cmd.console,
        "print",
        lambda *args, **kw: captured_output.append(str(args[0])) if args else None,
    )
    monkeypatch.setattr(upgrade_cmd, "show_banner", lambda: None)

    upgrade_cmd.upgrade(
        dry_run=False,
        force=True,
        target="1.0.0a1",
        json_output=False,
        verbose=False,
        no_worktrees=True,
    )

    full = "\n".join(captured_output)
    assert "Auto-committed upgrade changes" in full
    assert "1 files" in full


def test_upgrade_no_migrations_safe_commit_failure_shows_warning(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """When safe_commit fails, the JSON output includes a warning."""
    project_path = _setup_upgrade_project(tmp_path)
    monkeypatch.setattr(Path, "cwd", lambda: project_path)

    call_count = {"n": 0}

    def _fake_status(repo_path):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return set()
        return {".kittify/metadata.yaml"}

    monkeypatch.setattr(upgrade_cmd, "_git_status_paths", _fake_status)
    monkeypatch.setattr(
        upgrade_cmd,
        "safe_commit",
        lambda repo_path, files_to_commit, commit_message, allow_empty=False: False,
    )

    captured_output: list[str] = []
    monkeypatch.setattr(
        upgrade_cmd.console,
        "print",
        lambda text, **kw: captured_output.append(str(text)),
    )

    upgrade_cmd.upgrade(
        dry_run=False,
        force=True,
        target="1.0.0a1",
        json_output=True,
        verbose=False,
        no_worktrees=True,
    )

    data = json.loads(captured_output[0])
    assert data["auto_committed"] is False
    assert len(data["warnings"]) == 1
    assert "review and commit manually" in data["warnings"][0]
