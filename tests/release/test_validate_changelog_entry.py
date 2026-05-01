"""Regression tests for FR-603: CHANGELOG-presence check in branch mode.

Test T7.3 from WP07 mission 079-post-555-release-hardening.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "release"))
from validate_release import changelog_has_entry  # type: ignore[import]

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts" / "release" / "validate_release.py"


def _write_release_files(
    tmp_path: Path,
    version: str,
    changelog: str,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        dedent(
            f"""\
            [project]
            name = "spec-kitty-cli"
            version = "{version}"
            description = "Test project"
            """
        ),
        encoding="utf-8",
    )
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    (tmp_path / ".kittify").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kittify" / "metadata.yaml").write_text(
        f"spec_kitty:\n  version: {version}\n",
        encoding="utf-8",
    )


def _init_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# changelog_has_entry unit tests
# ---------------------------------------------------------------------------


def test_changelog_has_entry_returns_true_when_present() -> None:
    changelog = (
        "# Changelog\n\n"
        "## [3.1.1] - 2026-04-09\n\n"
        "### Fixed\n- The fix\n"
    )
    assert changelog_has_entry(changelog, "3.1.1") is True


def test_changelog_has_entry_returns_false_when_absent() -> None:
    changelog = (
        "# Changelog\n\n"
        "## [3.0.0] - 2025-01-01\n\n"
        "### Fixed\n- Old fix\n"
    )
    assert changelog_has_entry(changelog, "3.1.1") is False


def test_changelog_has_entry_returns_false_for_empty_section() -> None:
    changelog = "# Changelog\n\n## [3.1.1] - 2026-04-09\n\n"
    assert changelog_has_entry(changelog, "3.1.1") is False


def test_changelog_has_entry_prerelease_version() -> None:
    changelog = (
        "# Changelog\n\n"
        "## [3.1.1a3] - 2026-04-07\n\n"
        "### Changed\n- Alpha release\n"
    )
    assert changelog_has_entry(changelog, "3.1.1a3") is True
    assert changelog_has_entry(changelog, "3.1.1") is False


# ---------------------------------------------------------------------------
# T7.3 — Branch mode CHANGELOG presence check (integration)
# ---------------------------------------------------------------------------


@pytest.mark.git_repo
def test_missing_changelog_entry_fails_in_branch_mode(tmp_path: Path) -> None:
    """Validator exits non-zero in branch mode when CHANGELOG entry is missing."""
    changelog = "# Changelog\n\n## [3.0.0] - 2025-01-01\n\n### Fixed\n- Old fix\n"
    _write_release_files(tmp_path, "3.1.1", changelog)
    _init_git_repo(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--mode",
            "branch",
            "--pyproject",
            str(tmp_path / "pyproject.toml"),
            "--changelog",
            str(tmp_path / "CHANGELOG.md"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "3.1.1" in combined


@pytest.mark.git_repo
def test_present_changelog_entry_passes_in_branch_mode(tmp_path: Path) -> None:
    """Validator exits 0 in branch mode when CHANGELOG entry exists."""
    changelog = (
        "# Changelog\n\n"
        "## [3.1.1] - 2026-04-09\n\n"
        "### Fixed\n- The fix\n"
        "\n## [3.0.0] - 2025-01-01\n\n### Fixed\n- Old fix\n"
    )
    _write_release_files(tmp_path, "3.1.1", changelog)
    _init_git_repo(tmp_path)

    # Tag v3.0.0 so progression check passes
    subprocess.run(["git", "tag", "v3.0.0"], cwd=tmp_path, check=True, capture_output=True)

    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--mode",
            "branch",
            "--pyproject",
            str(tmp_path / "pyproject.toml"),
            "--changelog",
            str(tmp_path / "CHANGELOG.md"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
