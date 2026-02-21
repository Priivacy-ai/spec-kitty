"""Tests for project_identity module."""

from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from ruamel.yaml import YAML

from specify_cli.sync.project_identity import (
    ProjectIdentity,
    atomic_write_config,
    derive_project_slug,
    ensure_identity,
    generate_node_id,
    generate_project_uuid,
    is_writable,
    load_identity,
)


class TestProjectIdentity:
    """Tests for ProjectIdentity dataclass."""

    def test_default_creation(self) -> None:
        """Default ProjectIdentity has None fields."""
        identity = ProjectIdentity()
        assert identity.project_uuid is None
        assert identity.project_slug is None
        assert identity.node_id is None

    def test_is_complete_all_none(self) -> None:
        """is_complete returns False when all fields are None."""
        identity = ProjectIdentity()
        assert identity.is_complete is False

    def test_is_complete_partial(self) -> None:
        """is_complete returns False when some fields are None."""
        identity = ProjectIdentity(project_uuid=UUID("12345678-1234-5678-1234-567812345678"))
        assert identity.is_complete is False

    def test_is_complete_all_set(self) -> None:
        """is_complete returns True when all fields are set."""
        identity = ProjectIdentity(
            project_uuid=UUID("12345678-1234-5678-1234-567812345678"),
            project_slug="my-project",
            node_id="abcd12345678",
        )
        assert identity.is_complete is True

    def test_with_defaults_generates_missing(self, tmp_path: Path) -> None:
        """with_defaults generates missing fields."""
        identity = ProjectIdentity()
        filled = identity.with_defaults(tmp_path)

        assert filled.project_uuid is not None
        assert isinstance(filled.project_uuid, UUID)
        assert filled.project_slug is not None
        assert filled.node_id is not None
        assert len(filled.node_id) == 12

    def test_with_defaults_preserves_existing(self, tmp_path: Path) -> None:
        """with_defaults preserves existing fields."""
        existing_uuid = UUID("12345678-1234-5678-1234-567812345678")
        identity = ProjectIdentity(project_uuid=existing_uuid)
        filled = identity.with_defaults(tmp_path)

        assert filled.project_uuid == existing_uuid
        assert filled.project_slug is not None
        assert filled.node_id is not None

    def test_to_dict(self) -> None:
        """to_dict serializes to dictionary."""
        uuid = UUID("12345678-1234-5678-1234-567812345678")
        identity = ProjectIdentity(
            project_uuid=uuid,
            project_slug="my-project",
            node_id="abcd12345678",
        )
        result = identity.to_dict()

        assert result == {
            "uuid": "12345678-1234-5678-1234-567812345678",
            "slug": "my-project",
            "node_id": "abcd12345678",
        }

    def test_to_dict_with_none(self) -> None:
        """to_dict handles None fields."""
        identity = ProjectIdentity()
        result = identity.to_dict()

        assert result == {
            "uuid": None,
            "slug": None,
            "node_id": None,
        }

    def test_from_dict(self) -> None:
        """from_dict deserializes from dictionary."""
        data = {
            "uuid": "12345678-1234-5678-1234-567812345678",
            "slug": "my-project",
            "node_id": "abcd12345678",
        }
        identity = ProjectIdentity.from_dict(data)

        assert identity.project_uuid == UUID("12345678-1234-5678-1234-567812345678")
        assert identity.project_slug == "my-project"
        assert identity.node_id == "abcd12345678"

    def test_from_dict_with_missing(self) -> None:
        """from_dict handles missing fields."""
        identity = ProjectIdentity.from_dict({})

        assert identity.project_uuid is None
        assert identity.project_slug is None
        assert identity.node_id is None


class TestGenerateProjectUuid:
    """Tests for generate_project_uuid function."""

    def test_returns_uuid4(self) -> None:
        """generate_project_uuid returns valid UUID4."""
        uuid = generate_project_uuid()
        assert isinstance(uuid, UUID)
        assert uuid.version == 4

    def test_unique_each_call(self) -> None:
        """Each call returns a unique UUID."""
        uuids = [generate_project_uuid() for _ in range(10)]
        assert len(set(uuids)) == 10


class TestDeriveProjectSlug:
    """Tests for derive_project_slug function."""

    def test_from_directory_name(self, tmp_path: Path) -> None:
        """Derives slug from directory name when no git remote."""
        project_dir = tmp_path / "My_Project"
        project_dir.mkdir()

        slug = derive_project_slug(project_dir)
        assert slug == "my-project"

    def test_from_git_remote_https(self, tmp_path: Path) -> None:
        """Derives slug from HTTPS git remote URL."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="https://github.com/user/awesome-repo.git\n",
                returncode=0,
            )

            slug = derive_project_slug(project_dir)
            assert slug == "awesome-repo"

    def test_from_git_remote_ssh(self, tmp_path: Path) -> None:
        """Derives slug from SSH git remote URL."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="git@github.com:user/my_project.git\n",
                returncode=0,
            )

            slug = derive_project_slug(project_dir)
            assert slug == "my-project"

    def test_handles_no_git_extension(self, tmp_path: Path) -> None:
        """Handles URLs without .git extension."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="https://github.com/user/repo\n",
                returncode=0,
            )

            slug = derive_project_slug(project_dir)
            assert slug == "repo"

    def test_fallback_on_git_error(self, tmp_path: Path) -> None:
        """Falls back to directory name on git error."""
        project_dir = tmp_path / "fallback_project"
        project_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            import subprocess

            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            slug = derive_project_slug(project_dir)
            assert slug == "fallback-project"


class TestGenerateNodeId:
    """Tests for generate_node_id function."""

    def test_returns_12_char_hex(self) -> None:
        """generate_node_id returns 12-character hex string."""
        node_id = generate_node_id()
        assert len(node_id) == 12
        assert re.match(r"^[0-9a-f]+$", node_id)

    def test_stable_across_calls(self) -> None:
        """Same value returned across multiple calls."""
        ids = [generate_node_id() for _ in range(5)]
        assert len(set(ids)) == 1


class TestIsWritable:
    """Tests for is_writable function."""

    def test_existing_writable_file(self, tmp_path: Path) -> None:
        """Returns True for existing writable file."""
        file_path = tmp_path / "test.yaml"
        file_path.touch()

        assert is_writable(file_path) is True

    def test_existing_readonly_file(self, tmp_path: Path) -> None:
        """Returns False for read-only file."""
        file_path = tmp_path / "readonly.yaml"
        file_path.touch()
        os.chmod(file_path, 0o444)

        try:
            assert is_writable(file_path) is False
        finally:
            os.chmod(file_path, 0o644)  # Cleanup

    def test_nonexistent_in_writable_dir(self, tmp_path: Path) -> None:
        """Returns True for nonexistent file in writable directory."""
        file_path = tmp_path / "new.yaml"
        assert is_writable(file_path) is True

    def test_nonexistent_in_readonly_dir(self, tmp_path: Path) -> None:
        """Returns False for nonexistent file in read-only directory."""
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o555)

        try:
            file_path = readonly_dir / "new.yaml"
            assert is_writable(file_path) is False
        finally:
            os.chmod(readonly_dir, 0o755)  # Cleanup


class TestAtomicWriteConfig:
    """Tests for atomic_write_config function."""

    def test_creates_new_config(self, tmp_path: Path) -> None:
        """Creates new config.yaml with identity."""
        config_path = tmp_path / ".kittify" / "config.yaml"
        identity = ProjectIdentity(
            project_uuid=UUID("12345678-1234-5678-1234-567812345678"),
            project_slug="my-project",
            node_id="abcd12345678",
        )

        atomic_write_config(config_path, identity)

        assert config_path.exists()
        yaml = YAML()
        with open(config_path) as f:
            config = yaml.load(f)

        assert config["project"]["uuid"] == "12345678-1234-5678-1234-567812345678"
        assert config["project"]["slug"] == "my-project"
        assert config["project"]["node_id"] == "abcd12345678"

    def test_preserves_existing_keys(self, tmp_path: Path) -> None:
        """Preserves other keys in existing config."""
        config_path = tmp_path / ".kittify" / "config.yaml"
        config_path.parent.mkdir(parents=True)

        yaml = YAML()
        with open(config_path, "w") as f:
            yaml.dump({"agents": {"available": ["claude"]}}, f)

        identity = ProjectIdentity(
            project_uuid=UUID("12345678-1234-5678-1234-567812345678"),
            project_slug="my-project",
            node_id="abcd12345678",
        )

        atomic_write_config(config_path, identity)

        with open(config_path) as f:
            config = yaml.load(f)

        assert config["agents"]["available"] == ["claude"]
        assert config["project"]["slug"] == "my-project"

    def test_cleans_up_on_failure(self, tmp_path: Path) -> None:
        """Cleans up temp file on write failure."""
        config_path = tmp_path / ".kittify" / "config.yaml"
        config_path.parent.mkdir(parents=True)

        identity = ProjectIdentity(
            project_uuid=UUID("12345678-1234-5678-1234-567812345678"),
            project_slug="my-project",
            node_id="abcd12345678",
        )

        # Make the final replace fail by making target immutable
        config_path.touch()
        os.chmod(config_path.parent, 0o555)

        try:
            with pytest.raises(OSError):
                atomic_write_config(config_path, identity)

            # No temp files left behind
            temp_files = list(config_path.parent.glob(".config.yaml.*.tmp"))
            assert len(temp_files) == 0
        finally:
            os.chmod(config_path.parent, 0o755)


class TestLoadIdentity:
    """Tests for load_identity function."""

    def test_returns_empty_for_missing_config(self, tmp_path: Path) -> None:
        """Returns empty identity when config doesn't exist."""
        config_path = tmp_path / "config.yaml"
        identity = load_identity(config_path)

        assert identity.project_uuid is None
        assert identity.project_slug is None
        assert identity.node_id is None

    def test_loads_existing_identity(self, tmp_path: Path) -> None:
        """Loads identity from existing config."""
        config_path = tmp_path / "config.yaml"
        yaml = YAML()
        with open(config_path, "w") as f:
            yaml.dump(
                {
                    "project": {
                        "uuid": "12345678-1234-5678-1234-567812345678",
                        "slug": "my-project",
                        "node_id": "abcd12345678",
                    }
                },
                f,
            )

        identity = load_identity(config_path)

        assert identity.project_uuid == UUID("12345678-1234-5678-1234-567812345678")
        assert identity.project_slug == "my-project"
        assert identity.node_id == "abcd12345678"

    def test_handles_malformed_yaml(self, tmp_path: Path) -> None:
        """Returns empty identity for malformed YAML."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("invalid: yaml: here: {")

        identity = load_identity(config_path)
        assert identity.project_uuid is None

    def test_handles_missing_project_section(self, tmp_path: Path) -> None:
        """Handles config without 'project' section."""
        config_path = tmp_path / "config.yaml"
        yaml = YAML()
        with open(config_path, "w") as f:
            yaml.dump({"agents": {"available": ["claude"]}}, f)

        identity = load_identity(config_path)
        assert identity.project_uuid is None

    def test_handles_invalid_project_section(self, tmp_path: Path) -> None:
        """Handles non-dict 'project' section."""
        config_path = tmp_path / "config.yaml"
        yaml = YAML()
        with open(config_path, "w") as f:
            yaml.dump({"project": "invalid"}, f)

        identity = load_identity(config_path)
        assert identity.project_uuid is None


class TestEnsureIdentity:
    """Tests for ensure_identity function."""

    def test_returns_existing_complete_identity(self, tmp_path: Path) -> None:
        """Returns existing identity without modification."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        config_path = kittify / "config.yaml"

        yaml = YAML()
        with open(config_path, "w") as f:
            yaml.dump(
                {
                    "project": {
                        "uuid": "12345678-1234-5678-1234-567812345678",
                        "slug": "existing-project",
                        "node_id": "abcd12345678",
                    }
                },
                f,
            )

        identity = ensure_identity(tmp_path)

        assert identity.project_uuid == UUID("12345678-1234-5678-1234-567812345678")
        assert identity.project_slug == "existing-project"
        assert identity.node_id == "abcd12345678"

    def test_generates_missing_fields(self, tmp_path: Path) -> None:
        """Generates missing identity fields."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()

        identity = ensure_identity(tmp_path)

        assert identity.is_complete
        assert isinstance(identity.project_uuid, UUID)
        assert identity.project_slug is not None
        assert identity.node_id is not None

    def test_persists_generated_identity(self, tmp_path: Path) -> None:
        """Persists generated identity to config."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()

        identity = ensure_identity(tmp_path)
        config_path = kittify / "config.yaml"

        assert config_path.exists()

        yaml = YAML()
        with open(config_path) as f:
            config = yaml.load(f)

        assert config["project"]["uuid"] == str(identity.project_uuid)

    def test_handles_read_only_filesystem(self, tmp_path: Path) -> None:
        """Returns in-memory identity for read-only filesystem."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        os.chmod(kittify, 0o555)

        try:
            identity = ensure_identity(tmp_path)
            assert identity.is_complete
            # Identity should still be returned (in-memory)
        finally:
            os.chmod(kittify, 0o755)

    def test_backfills_partial_identity(self, tmp_path: Path) -> None:
        """Backfills missing fields in partial identity."""
        kittify = tmp_path / ".kittify"
        kittify.mkdir()
        config_path = kittify / "config.yaml"

        yaml = YAML()
        with open(config_path, "w") as f:
            yaml.dump(
                {
                    "project": {
                        "uuid": "12345678-1234-5678-1234-567812345678",
                        # slug and node_id missing
                    }
                },
                f,
            )

        identity = ensure_identity(tmp_path)

        # Existing UUID preserved
        assert identity.project_uuid == UUID("12345678-1234-5678-1234-567812345678")
        # Missing fields generated
        assert identity.project_slug is not None
        assert identity.node_id is not None
