"""Scope: unit tests for the mutmut environment helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.mutmut_env import (
    copy_missing_tree,
    main,
    missing_required_paths,
    prepare_mutants_environment,
    prepare_mutants_environment_from_cwd,
)

pytestmark = pytest.mark.fast


def test_prepare_mutants_environment_copies_missing_siblings_without_overwriting(tmp_path: Path) -> None:
    """Copies missing files into mutants while leaving mutated files untouched."""
    # Arrange
    repo_root = tmp_path / "repo"
    mutants_root = repo_root / "mutants"
    source_root = repo_root / "src"
    (source_root / "specify_cli" / "dossier").mkdir(parents=True)
    (source_root / "doctrine").mkdir(parents=True)
    (source_root / "specify_cli" / "dossier" / "api.py").write_text("original api\n", encoding="utf-8")
    (source_root / "specify_cli" / "dossier" / "models.py").write_text("original models\n", encoding="utf-8")
    (source_root / "doctrine" / "core.py").write_text("doctrine core\n", encoding="utf-8")
    (mutants_root / "src" / "specify_cli" / "dossier").mkdir(parents=True)
    (mutants_root / "src" / "specify_cli" / "dossier" / "api.py").write_text("mutated api\n", encoding="utf-8")

    # Assumption check
    assert (mutants_root / "src" / "specify_cli" / "dossier" / "api.py").read_text(encoding="utf-8") == "mutated api\n"
    assert not (mutants_root / "src" / "specify_cli" / "dossier" / "models.py").exists()

    # Act
    copied = prepare_mutants_environment(repo_root, mutants_root)

    # Assert
    assert (mutants_root / "src" / "specify_cli" / "dossier" / "api.py").read_text(encoding="utf-8") == "mutated api\n"
    assert (mutants_root / "src" / "specify_cli" / "dossier" / "models.py").read_text(encoding="utf-8") == "original models\n"
    assert (mutants_root / "src" / "doctrine" / "core.py").read_text(encoding="utf-8") == "doctrine core\n"
    assert mutants_root / "src" / "specify_cli" / "dossier" / "models.py" in copied
    assert mutants_root / "src" / "specify_cli" / "dossier" / "api.py" not in copied


def test_prepare_mutants_environment_from_cwd_skips_non_mutants_directory(tmp_path: Path) -> None:
    """Returns immediately when pytest is not running inside mutmut's directory."""
    # Arrange
    outside_dir = tmp_path / "not-mutants"
    outside_dir.mkdir()

    # Assumption check
    assert outside_dir.name != "mutants"

    # Act
    copied = prepare_mutants_environment_from_cwd(outside_dir)

    # Assert
    assert copied == []


def test_copy_missing_tree_ignores_pycache(tmp_path: Path) -> None:
    """Skips ``__pycache__`` trees entirely when copying."""
    # Arrange
    source = tmp_path / "src" / "__pycache__"
    destination = tmp_path / "dest" / "__pycache__"
    source.mkdir(parents=True)
    (source / "junk.pyc").write_bytes(b"compiled")

    # Assumption check
    assert source.name == "__pycache__"

    # Act
    copied = copy_missing_tree(source, destination)

    # Assert
    assert copied == []
    assert not destination.exists()


def test_missing_required_paths_reports_missing_entries(tmp_path: Path) -> None:
    """Reports required paths that are still absent after preparation."""
    # Arrange
    mutants_root = tmp_path / "mutants"
    (mutants_root / "src" / "specify_cli").mkdir(parents=True)
    (mutants_root / "src" / "specify_cli" / "frontmatter.py").write_text("ok\n", encoding="utf-8")

    # Assumption check
    assert (mutants_root / "src" / "specify_cli" / "frontmatter.py").exists()
    assert not (mutants_root / "src" / "doctrine").exists()

    # Act
    missing = missing_required_paths(
        mutants_root,
        ["src/specify_cli/frontmatter.py", "src/doctrine"],
    )

    # Assert
    assert missing == ["src/doctrine"]


def test_main_returns_non_zero_when_required_paths_are_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI exits non-zero when required mutmut paths still do not exist."""
    # Arrange
    repo_root = tmp_path / "repo"
    mutants_root = repo_root / "mutants"
    (repo_root / "src" / "specify_cli").mkdir(parents=True)
    (mutants_root / "src" / "specify_cli").mkdir(parents=True)

    # Assumption check
    assert not (mutants_root / "src" / "doctrine").exists()

    # Act
    exit_code = main(
        [
            "--repo-root",
            str(repo_root),
            "--mutants-root",
            str(mutants_root),
            "--require",
            "src/doctrine",
        ]
    )

    # Assert
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "required mutmut path missing" in captured.out
