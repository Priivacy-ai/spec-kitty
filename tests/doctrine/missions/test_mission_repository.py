"""Tests for MissionRepository."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.missions.repository import MissionRepository

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def missions_root() -> Path:
    """Return the real bundled missions root from the doctrine package."""
    return MissionRepository.default_missions_root()


@pytest.fixture()
def repo(missions_root: Path) -> MissionRepository:
    """Return a MissionRepository pointing at the real bundled missions."""
    return MissionRepository(missions_root)


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> MissionRepository:
    """Return a MissionRepository pointing at a temporary (empty) directory."""
    return MissionRepository(tmp_path)


# ---------------------------------------------------------------------------
# default_missions_root()
# ---------------------------------------------------------------------------


class TestDefaultMissionsRoot:
    def test_returns_path(self) -> None:
        root = MissionRepository.default_missions_root()
        assert isinstance(root, Path)

    def test_is_directory(self) -> None:
        root = MissionRepository.default_missions_root()
        assert root.is_dir(), f"Expected {root} to be a directory"

    def test_contains_software_dev(self) -> None:
        root = MissionRepository.default_missions_root()
        assert (root / "software-dev").is_dir()


# ---------------------------------------------------------------------------
# list_missions()
# ---------------------------------------------------------------------------


class TestListMissions:
    def test_returns_list(self, repo: MissionRepository) -> None:
        result = repo.list_missions()
        assert isinstance(result, list)

    def test_contains_software_dev(self, repo: MissionRepository) -> None:
        assert "software-dev" in repo.list_missions()

    def test_all_have_mission_yaml(self, repo: MissionRepository, missions_root: Path) -> None:
        for mission in repo.list_missions():
            assert (missions_root / mission / "mission.yaml").exists(), (
                f"Mission '{mission}' is listed but lacks mission.yaml"
            )

    def test_sorted(self, repo: MissionRepository) -> None:
        result = repo.list_missions()
        assert result == sorted(result)

    def test_empty_root_returns_empty(self, tmp_repo: MissionRepository) -> None:
        assert tmp_repo.list_missions() == []

    def test_dirs_without_mission_yaml_excluded(self, tmp_path: Path) -> None:
        (tmp_path / "fake-mission").mkdir()
        r = MissionRepository(tmp_path)
        assert "fake-mission" not in r.list_missions()


# ---------------------------------------------------------------------------
# get_command_template()
# ---------------------------------------------------------------------------


class TestGetCommandTemplate:
    def test_existing_template_returns_path(self, repo: MissionRepository) -> None:
        path = repo.get_command_template("software-dev", "implement")
        assert path is not None
        assert path.is_file()
        assert path.suffix == ".md"

    def test_missing_command_returns_none(self, repo: MissionRepository) -> None:
        assert repo.get_command_template("software-dev", "nonexistent-command") is None

    def test_missing_mission_returns_none(self, repo: MissionRepository) -> None:
        assert repo.get_command_template("no-such-mission", "implement") is None

    def test_multiple_commands_resolve(self, repo: MissionRepository) -> None:
        for command in ("specify", "plan", "review"):
            path = repo.get_command_template("software-dev", command)
            assert path is not None and path.is_file(), f"Template for '{command}' not found"


# ---------------------------------------------------------------------------
# get_template()
# ---------------------------------------------------------------------------


class TestGetTemplate:
    def test_existing_template_returns_path(self, repo: MissionRepository) -> None:
        path = repo.get_template("software-dev", "spec-template.md")
        assert path is not None
        assert path.is_file()

    def test_missing_template_returns_none(self, repo: MissionRepository) -> None:
        assert repo.get_template("software-dev", "ghost.md") is None

    def test_missing_mission_returns_none(self, repo: MissionRepository) -> None:
        assert repo.get_template("no-such-mission", "spec-template.md") is None


# ---------------------------------------------------------------------------
# get_action_index_path()
# ---------------------------------------------------------------------------


class TestGetActionIndexPath:
    def test_existing_action_returns_path(self, repo: MissionRepository) -> None:
        path = repo.get_action_index_path("software-dev", "implement")
        assert path is not None
        assert path.is_file()
        assert path.name == "index.yaml"

    def test_missing_action_returns_none(self, repo: MissionRepository) -> None:
        assert repo.get_action_index_path("software-dev", "bogus-action") is None

    def test_missing_mission_returns_none(self, repo: MissionRepository) -> None:
        assert repo.get_action_index_path("no-such-mission", "implement") is None


# ---------------------------------------------------------------------------
# get_action_guidelines_path()
# ---------------------------------------------------------------------------


class TestGetActionGuidelinesPath:
    def test_existing_action_returns_path(self, repo: MissionRepository) -> None:
        path = repo.get_action_guidelines_path("software-dev", "implement")
        assert path is not None
        assert path.is_file()
        assert path.name == "guidelines.md"

    def test_missing_action_returns_none(self, repo: MissionRepository) -> None:
        assert repo.get_action_guidelines_path("software-dev", "bogus-action") is None

    def test_missing_mission_returns_none(self, repo: MissionRepository) -> None:
        assert repo.get_action_guidelines_path("no-such-mission", "implement") is None


# ---------------------------------------------------------------------------
# get_mission_config_path()
# ---------------------------------------------------------------------------


class TestGetMissionConfigPath:
    def test_existing_mission_returns_path(self, repo: MissionRepository) -> None:
        path = repo.get_mission_config_path("software-dev")
        assert path is not None
        assert path.is_file()
        assert path.name == "mission.yaml"

    def test_missing_mission_returns_none(self, repo: MissionRepository) -> None:
        assert repo.get_mission_config_path("no-such-mission") is None
