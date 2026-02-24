"""Tests for upgrade auto-commit path filtering and commit wiring."""

from __future__ import annotations

from pathlib import Path

import specify_cli.cli.commands.upgrade as upgrade_cmd


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
    assert captured["allow_empty"] is True
