"""
Infrastructure smoke tests to verify adversarial test setup.

These tests validate that the test infrastructure is correctly configured.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.adversarial.conftest import (
    PATH_ATTACK_VECTORS,
    CSV_ATTACK_VECTORS,
    AttackVector,
)


pytestmark = [pytest.mark.adversarial]


class TestAttackVectorData:
    """Verify attack vector data structures are correctly defined."""

    def test_path_attack_vectors_not_empty(self):
        """PATH_ATTACK_VECTORS should contain attack vectors."""
        assert len(PATH_ATTACK_VECTORS) > 0, "Should have path attack vectors"

    def test_csv_attack_vectors_not_empty(self):
        """CSV_ATTACK_VECTORS should contain attack vectors."""
        assert len(CSV_ATTACK_VECTORS) > 0, "Should have CSV attack vectors"

    def test_attack_vector_structure(self):
        """All attack vectors should have required fields."""
        all_vectors = PATH_ATTACK_VECTORS + CSV_ATTACK_VECTORS
        for vector in all_vectors:
            assert isinstance(vector, AttackVector)
            assert vector.name, "Should have a name"
            assert vector.category in ("path", "csv", "git", "migration", "config")
            assert vector.expected in ("reject", "warn", "handle")
            assert vector.description, "Should have a description"


class TestPlatformDetection:
    """Verify platform detection fixtures work correctly."""

    def test_symlinks_supported_is_bool(self, symlinks_supported: bool):
        """symlinks_supported fixture should return a boolean."""
        assert isinstance(symlinks_supported, bool)

    def test_case_insensitive_fs_is_bool(self, case_insensitive_fs: bool):
        """case_insensitive_fs fixture should return a boolean."""
        assert isinstance(case_insensitive_fs, bool)


class TestEnvironmentFixtures:
    """Verify environment fixtures work correctly."""

    def test_adversarial_env_no_template_root(self, adversarial_env: dict[str, str]):
        """adversarial_env should NOT have SPEC_KITTY_TEMPLATE_ROOT."""
        assert "SPEC_KITTY_TEMPLATE_ROOT" not in adversarial_env

    def test_adversarial_env_no_pythonpath(self, adversarial_env: dict[str, str]):
        """adversarial_env should NOT have PYTHONPATH."""
        assert "PYTHONPATH" not in adversarial_env

    def test_adversarial_env_has_path(self, adversarial_env: dict[str, str]):
        """adversarial_env should preserve PATH."""
        assert "PATH" in adversarial_env


class TestProjectFixtures:
    """Verify project creation fixtures work correctly."""

    def test_temp_git_project_is_git_repo(self, temp_git_project: Path):
        """temp_git_project should be a valid git repository."""
        git_dir = temp_git_project / ".git"
        assert git_dir.exists(), "Should have .git directory"

    def test_temp_git_project_has_initial_commit(self, temp_git_project: Path):
        """temp_git_project should have an initial commit."""
        import subprocess

        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=temp_git_project,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Should have at least one commit"

    def test_kittify_project_has_kittify_dir(self, kittify_project: Path):
        """kittify_project should have .kittify directory."""
        kittify = kittify_project / ".kittify"
        assert kittify.exists(), "Should have .kittify directory"
        assert kittify.is_dir(), ".kittify should be a directory"

    def test_kittify_project_has_config(self, kittify_project: Path):
        """kittify_project should have config.yaml."""
        config = kittify_project / ".kittify" / "config.yaml"
        assert config.exists(), "Should have config.yaml"


class TestFactoryFixtures:
    """Verify factory fixtures work correctly."""

    def test_malformed_csv_factory_creates_file(self, malformed_csv_factory, tmp_path):
        """malformed_csv_factory should create CSV files."""
        vector = AttackVector("test", "test,content", "csv", "handle", "Test vector")
        path = malformed_csv_factory(vector, "test.csv")

        assert path.exists(), "Should create file"
        assert path.read_text() == "test,content"

    def test_malformed_csv_factory_handles_bytes(self, malformed_csv_factory, tmp_path):
        """malformed_csv_factory should handle binary content."""
        vector = AttackVector("test", b"\xff\xfe", "csv", "handle", "Binary test")
        path = malformed_csv_factory(vector, "binary.csv")

        assert path.exists(), "Should create file"
        assert path.read_bytes() == b"\xff\xfe"

    def test_symlink_factory_returns_none_if_unsupported(
        self, symlink_factory, symlinks_supported, tmp_path
    ):
        """symlink_factory should return None if symlinks not supported."""
        target = tmp_path / "target"
        target.mkdir()

        result = symlink_factory(target, "link")

        if symlinks_supported:
            assert result is not None, "Should create symlink"
            assert result.is_symlink(), "Should be a symlink"
        else:
            assert result is None, "Should return None if unsupported"
