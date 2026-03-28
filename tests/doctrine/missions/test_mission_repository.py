"""Tests for MissionTemplateRepository (renamed from MissionRepository)."""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.missions.repository import MissionTemplateRepository

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def missions_root() -> Path:
    """Return the real bundled missions root from the doctrine package."""
    return MissionTemplateRepository.default_missions_root()


@pytest.fixture()
def repo(missions_root: Path) -> MissionTemplateRepository:
    """Return a MissionTemplateRepository pointing at the real bundled missions."""
    return MissionTemplateRepository(missions_root)


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> MissionTemplateRepository:
    """Return a MissionTemplateRepository pointing at a temporary (empty) directory."""
    return MissionTemplateRepository(tmp_path)


# ---------------------------------------------------------------------------
# default_missions_root()
# ---------------------------------------------------------------------------


class TestDefaultMissionsRoot:
    def test_returns_path(self) -> None:
        root = MissionTemplateRepository.default_missions_root()
        assert isinstance(root, Path)

    def test_is_directory(self) -> None:
        root = MissionTemplateRepository.default_missions_root()
        assert root.is_dir(), f"Expected {root} to be a directory"

    def test_contains_software_dev(self) -> None:
        root = MissionTemplateRepository.default_missions_root()
        assert (root / "software-dev").is_dir()


# ---------------------------------------------------------------------------
# default() classmethod
# ---------------------------------------------------------------------------


class TestDefault:
    def test_returns_instance(self) -> None:
        repo = MissionTemplateRepository.default()
        assert isinstance(repo, MissionTemplateRepository)

    def test_instance_has_missions(self) -> None:
        repo = MissionTemplateRepository.default()
        assert "software-dev" in repo.list_missions()


# ---------------------------------------------------------------------------
# list_missions()
# ---------------------------------------------------------------------------


class TestListMissions:
    def test_returns_list(self, repo: MissionTemplateRepository) -> None:
        result = repo.list_missions()
        assert isinstance(result, list)

    def test_contains_software_dev(self, repo: MissionTemplateRepository) -> None:
        assert "software-dev" in repo.list_missions()

    def test_all_have_mission_yaml(self, repo: MissionTemplateRepository, missions_root: Path) -> None:
        for mission in repo.list_missions():
            assert (missions_root / mission / "mission.yaml").exists(), (
                f"Mission '{mission}' is listed but lacks mission.yaml"
            )

    def test_sorted(self, repo: MissionTemplateRepository) -> None:
        result = repo.list_missions()
        assert result == sorted(result)

    def test_empty_root_returns_empty(self, tmp_repo: MissionTemplateRepository) -> None:
        assert tmp_repo.list_missions() == []

    def test_dirs_without_mission_yaml_excluded(self, tmp_path: Path) -> None:
        (tmp_path / "fake-mission").mkdir()
        r = MissionTemplateRepository(tmp_path)
        assert "fake-mission" not in r.list_missions()


# ---------------------------------------------------------------------------
# _command_template_path()
# ---------------------------------------------------------------------------


class TestCommandTemplatePath:
    def test_existing_template_returns_path(self, repo: MissionTemplateRepository) -> None:
        path = repo._command_template_path("software-dev", "implement")
        assert path is not None
        assert path.is_file()
        assert path.suffix == ".md"

    def test_missing_command_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._command_template_path("software-dev", "nonexistent-command") is None

    def test_missing_mission_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._command_template_path("no-such-mission", "implement") is None

    def test_multiple_commands_resolve(self, repo: MissionTemplateRepository) -> None:
        for command in ("specify", "plan", "review"):
            path = repo._command_template_path("software-dev", command)
            assert path is not None and path.is_file(), f"Template for '{command}' not found"


# ---------------------------------------------------------------------------
# _content_template_path()
# ---------------------------------------------------------------------------


class TestContentTemplatePath:
    def test_existing_template_returns_path(self, repo: MissionTemplateRepository) -> None:
        path = repo._content_template_path("software-dev", "spec-template.md")
        assert path is not None
        assert path.is_file()

    def test_missing_template_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._content_template_path("software-dev", "ghost.md") is None

    def test_missing_mission_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._content_template_path("no-such-mission", "spec-template.md") is None


# ---------------------------------------------------------------------------
# _action_index_path()
# ---------------------------------------------------------------------------


class TestActionIndexPath:
    def test_existing_action_returns_path(self, repo: MissionTemplateRepository) -> None:
        path = repo._action_index_path("software-dev", "implement")
        assert path is not None
        assert path.is_file()
        assert path.name == "index.yaml"

    def test_missing_action_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._action_index_path("software-dev", "bogus-action") is None

    def test_missing_mission_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._action_index_path("no-such-mission", "implement") is None


# ---------------------------------------------------------------------------
# _action_guidelines_path()
# ---------------------------------------------------------------------------


class TestActionGuidelinesPath:
    def test_existing_action_returns_path(self, repo: MissionTemplateRepository) -> None:
        path = repo._action_guidelines_path("software-dev", "implement")
        assert path is not None
        assert path.is_file()
        assert path.name == "guidelines.md"

    def test_missing_action_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._action_guidelines_path("software-dev", "bogus-action") is None

    def test_missing_mission_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._action_guidelines_path("no-such-mission", "implement") is None


# ---------------------------------------------------------------------------
# _mission_config_path()
# ---------------------------------------------------------------------------


class TestMissionConfigPath:
    def test_existing_mission_returns_path(self, repo: MissionTemplateRepository) -> None:
        path = repo._mission_config_path("software-dev")
        assert path is not None
        assert path.is_file()
        assert path.name == "mission.yaml"

    def test_missing_mission_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._mission_config_path("no-such-mission") is None


# ---------------------------------------------------------------------------
# _expected_artifacts_path()
# ---------------------------------------------------------------------------


class TestExpectedArtifactsPath:
    def test_existing_mission_returns_path(self, repo: MissionTemplateRepository) -> None:
        path = repo._expected_artifacts_path("software-dev")
        assert path is not None
        assert path.is_file()
        assert path.name == "expected-artifacts.yaml"

    def test_missing_mission_returns_none(self, repo: MissionTemplateRepository) -> None:
        assert repo._expected_artifacts_path("no-such-mission") is None


# ---------------------------------------------------------------------------
# _missions_root property
# ---------------------------------------------------------------------------


class TestMissionsRootProperty:
    def test_returns_root(self, repo: MissionTemplateRepository, missions_root: Path) -> None:
        assert repo._missions_root == missions_root

    def test_is_directory(self, repo: MissionTemplateRepository) -> None:
        assert repo._missions_root.is_dir()


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class TestTemplateResult:
    def test_properties(self) -> None:
        from doctrine.missions.repository import TemplateResult

        result = TemplateResult(content="hello", origin="test/origin", tier=None)
        assert result.content == "hello"
        assert result.origin == "test/origin"
        assert result.tier is None

    def test_repr(self) -> None:
        from doctrine.missions.repository import TemplateResult

        result = TemplateResult(content="hello", origin="test/origin", tier=None)
        assert "test/origin" in repr(result)


class TestConfigResult:
    def test_properties(self) -> None:
        from doctrine.missions.repository import ConfigResult

        result = ConfigResult(content="key: val", origin="test/origin", parsed={"key": "val"})
        assert result.content == "key: val"
        assert result.origin == "test/origin"
        assert result.parsed == {"key": "val"}

    def test_repr(self) -> None:
        from doctrine.missions.repository import ConfigResult

        result = ConfigResult(content="key: val", origin="test/origin", parsed={"key": "val"})
        assert "test/origin" in repr(result)


# ---------------------------------------------------------------------------
# Backward-compatible alias
# ---------------------------------------------------------------------------


class TestBackwardCompatAlias:
    def test_alias_import(self) -> None:
        from doctrine.missions import MissionRepository

        assert MissionRepository is MissionTemplateRepository

    def test_alias_isinstance(self) -> None:
        from doctrine.missions import MissionRepository

        repo = MissionTemplateRepository.default()
        assert isinstance(repo, MissionRepository)

    def test_alias_construction(self) -> None:
        from doctrine.missions import MissionRepository

        root = MissionTemplateRepository.default_missions_root()
        repo = MissionRepository(root)
        assert isinstance(repo, MissionTemplateRepository)
        assert "software-dev" in repo.list_missions()
