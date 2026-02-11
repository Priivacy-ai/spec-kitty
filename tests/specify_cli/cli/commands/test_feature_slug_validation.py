"""Tests for feature slug validation (kebab-case enforcement).

Bug #95: Feature slugs with spaces, underscores, or uppercase are currently
accepted but cause downstream failures in worktree/branch creation.

These tests verify that only valid kebab-case slugs are accepted.
"""

import subprocess
from typer.testing import CliRunner
from specify_cli.cli.commands.agent.feature import app

runner = CliRunner()


def test_feature_slug_with_spaces_rejected():
    """Feature slugs with spaces should be rejected."""
    result = runner.invoke(
        app,
        ["create-feature", "Invalid Feature Name", "--json"]
    )

    # Should fail with validation error
    assert result.exit_code != 0, "Should reject slug with spaces"

    # Check error message contains helpful guidance
    output = result.stdout
    assert "kebab-case" in output.lower(), "Error should mention kebab-case requirement"
    assert "examples:" in output.lower() or "example" in output.lower(), "Should show examples"


def test_feature_slug_with_underscores_rejected():
    """Feature slugs with underscores should be rejected."""
    result = runner.invoke(
        app,
        ["create-feature", "user_authentication", "--json"]
    )

    assert result.exit_code != 0, "Should reject slug with underscores"
    assert "kebab-case" in result.stdout.lower()


def test_feature_slug_starting_with_number_rejected():
    """Feature slugs must start with a letter."""
    result = runner.invoke(
        app,
        ["create-feature", "123-test-feature", "--json"]
    )

    assert result.exit_code != 0, "Should reject slug starting with number"
    assert "kebab-case" in result.stdout.lower()


def test_feature_slug_with_uppercase_rejected():
    """Feature slugs must be lowercase only."""
    result = runner.invoke(
        app,
        ["create-feature", "UserAuth", "--json"]
    )

    assert result.exit_code != 0, "Should reject slug with uppercase"
    assert "lowercase" in result.stdout.lower()


def test_valid_kebab_case_slugs_accepted(tmp_path, monkeypatch):
    """Valid kebab-case slugs should be accepted."""
    # Run in isolated temp directory to avoid polluting repo
    monkeypatch.chdir(tmp_path)

    # Initialize a minimal git repo for testing
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)

    # Create main branch and make initial commit
    subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)

    # Create minimal .kittify structure
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    (kittify_dir / "config.yaml").write_text("agents:\n  available: []\n")
    (kittify_dir / "metadata.yaml").write_text("project_name: test\n")

    # Create kitty-specs directory
    (tmp_path / "kitty-specs").mkdir()

    # Make initial commit so we're not in detached HEAD
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True, capture_output=True)

    valid_slugs = [
        "user-auth",
        "fix-bug-123",
        "new-dashboard",
        "a",
        "test-feature-2"
    ]

    for slug in valid_slugs:
        result = runner.invoke(
            app,
            ["create-feature", slug, "--json"]
        )

        # Valid slugs should be accepted (exit code 0)
        assert result.exit_code == 0, f"Valid slug '{slug}' should be accepted. Output: {result.stdout}"
