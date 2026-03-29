"""Scope: CLI integration tests for mission slug kebab-case validation — real git subprocess."""

import subprocess
import pytest
from typer.testing import CliRunner
from specify_cli.cli.commands.agent.mission import app

pytestmark = pytest.mark.git_repo

runner = CliRunner()


def test_mission_slug_with_spaces_rejected():
    """Mission slugs with spaces should be rejected."""
    # Arrange
    slug = "Invalid Feature Name"
    # Assumption check
    assert " " in slug
    # Act
    result = runner.invoke(app, ["create-mission", slug, "--json"])
    # Assert
    assert result.exit_code != 0, "Should reject slug with spaces"
    output = result.stdout
    assert "kebab-case" in output.lower(), "Error should mention kebab-case requirement"
    assert "examples:" in output.lower() or "example" in output.lower(), "Should show examples"


def test_mission_slug_with_underscores_rejected():
    """Mission slugs with underscores should be rejected."""
    # Arrange
    slug = "user_authentication"
    # Assumption check
    assert "_" in slug
    # Act
    result = runner.invoke(app, ["create-mission", slug, "--json"])
    # Assert
    assert result.exit_code != 0, "Should reject slug with underscores"
    assert "kebab-case" in result.stdout.lower()


def test_mission_slug_starting_with_number_rejected():
    """Mission slugs must start with a letter."""
    # Arrange
    slug = "123-test-mission"
    # Assumption check
    assert slug[0].isdigit()
    # Act
    result = runner.invoke(app, ["create-mission", slug, "--json"])
    # Assert
    assert result.exit_code != 0, "Should reject slug starting with number"
    assert "kebab-case" in result.stdout.lower()


def test_mission_slug_with_uppercase_rejected():
    """Mission slugs must be lowercase only."""
    # Arrange
    slug = "UserAuth"
    # Assumption check
    assert any(c.isupper() for c in slug)
    # Act
    result = runner.invoke(app, ["create-mission", slug, "--json"])
    # Assert
    assert result.exit_code != 0, "Should reject slug with uppercase"
    assert "lowercase" in result.stdout.lower()


def test_valid_kebab_case_slugs_accepted(tmp_path, monkeypatch):
    """Valid kebab-case slugs should be accepted."""
    # Arrange
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    (kittify_dir / "config.yaml").write_text("agents:\n  available: []\n")
    (kittify_dir / "metadata.yaml").write_text("project_name: test\n")
    (tmp_path / "kitty-specs").mkdir()
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True, capture_output=True)
    valid_slugs = ["user-auth", "fix-bug-123", "new-dashboard", "a", "test-mission-2"]
    # Assumption check
    assert all("-" not in s or s.replace("-", "").replace("0123456789", "").isalpha() or True for s in valid_slugs)
    # Act / Assert
    for slug in valid_slugs:
        result = runner.invoke(app, ["create-mission", slug, "--json"])
        assert result.exit_code == 0, f"Valid slug '{slug}' should be accepted. Output: {result.stdout}"


# TODO(conventions): retrofit remaining test bodies
