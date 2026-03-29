"""Comprehensive tests for MissionTemplateRepository public API.

Covers all public content-returning and config-returning methods,
value objects, enumeration, backward compatibility, and edge cases.
The existing test_mission_repository.py covers private _*_path() methods;
this file focuses on the public surface that consumers actually call.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctrine.missions.repository import (
    ConfigResult,
    MissionTemplateRepository,
    TemplateResult,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo() -> MissionTemplateRepository:
    """Return a MissionTemplateRepository for the real doctrine-bundled missions."""
    return MissionTemplateRepository.default()


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> MissionTemplateRepository:
    """Return a MissionTemplateRepository pointing at an empty temp directory."""
    return MissionTemplateRepository(tmp_path)


# ---------------------------------------------------------------------------
# Category 1: Value Object Tests
# ---------------------------------------------------------------------------


class TestTemplateResult:
    def test_properties(self) -> None:
        result = TemplateResult(content="hello", origin="doctrine/test/a.md")
        assert result.content == "hello"
        assert result.origin == "doctrine/test/a.md"
        assert result.tier is None

    def test_with_tier(self) -> None:
        result = TemplateResult(content="hello", origin="test", tier="package_default")
        assert result.tier == "package_default"

    def test_repr_contains_origin(self) -> None:
        result = TemplateResult(content="x", origin="doctrine/test/o.md")
        r = repr(result)
        assert "TemplateResult" in r
        assert "doctrine/test/o.md" in r

    def test_repr_contains_tier(self) -> None:
        result = TemplateResult(content="x", origin="o", tier="my_tier")
        assert "my_tier" in repr(result)

    def test_repr_none_tier(self) -> None:
        result = TemplateResult(content="x", origin="o")
        assert "None" in repr(result)


class TestConfigResult:
    def test_properties(self) -> None:
        result = ConfigResult(
            content="key: val", origin="test.yaml", parsed={"key": "val"}
        )
        assert result.content == "key: val"
        assert result.origin == "test.yaml"
        assert result.parsed == {"key": "val"}

    def test_parsed_list(self) -> None:
        result = ConfigResult(content="- a\n- b", origin="test.yaml", parsed=["a", "b"])
        assert result.parsed == ["a", "b"]

    def test_repr_contains_origin(self) -> None:
        result = ConfigResult(content="x", origin="test/origin.yaml", parsed={})
        r = repr(result)
        assert "ConfigResult" in r
        assert "test/origin.yaml" in r


# ---------------------------------------------------------------------------
# Category 2: Doctrine-Level Read Tests (get_command_template)
# ---------------------------------------------------------------------------


class TestGetCommandTemplate:
    def test_existing_template_returns_template_result(
        self, repo: MissionTemplateRepository
    ) -> None:
        result = repo.get_command_template("software-dev", "implement")
        assert result is not None
        assert isinstance(result, TemplateResult)

    def test_content_is_nonempty(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_command_template("software-dev", "implement")
        assert result is not None
        assert len(result.content) > 0

    def test_origin_format(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_command_template("software-dev", "implement")
        assert result is not None
        assert result.origin == "doctrine/software-dev/command-templates/implement.md"

    def test_tier_is_none_for_doctrine_level(
        self, repo: MissionTemplateRepository
    ) -> None:
        result = repo.get_command_template("software-dev", "implement")
        assert result is not None
        assert result.tier is None

    def test_multiple_known_templates(self, repo: MissionTemplateRepository) -> None:
        for name in ("specify", "plan", "review", "tasks", "accept"):
            result = repo.get_command_template("software-dev", name)
            assert result is not None, f"Expected template for '{name}'"
            assert len(result.content) > 0, f"Empty content for '{name}'"

    def test_nonexistent_template_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_command_template("software-dev", "nonexistent-xyz") is None

    def test_nonexistent_mission_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_command_template("no-such-mission", "implement") is None

    def test_empty_root_returns_none(self, tmp_repo: MissionTemplateRepository) -> None:
        assert tmp_repo.get_command_template("software-dev", "implement") is None


# ---------------------------------------------------------------------------
# Category 3: Doctrine-Level Read Tests (get_content_template)
# ---------------------------------------------------------------------------


class TestGetContentTemplate:
    def test_existing_template_returns_template_result(
        self, repo: MissionTemplateRepository
    ) -> None:
        result = repo.get_content_template("software-dev", "spec-template.md")
        assert result is not None
        assert isinstance(result, TemplateResult)

    def test_content_is_nonempty(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_content_template("software-dev", "spec-template.md")
        assert result is not None
        assert len(result.content) > 0

    def test_origin_format(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_content_template("software-dev", "spec-template.md")
        assert result is not None
        assert result.origin == "doctrine/software-dev/templates/spec-template.md"

    def test_plan_template_exists(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_content_template("software-dev", "plan-template.md")
        assert result is not None
        assert len(result.content) > 0

    def test_nonexistent_template_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_content_template("software-dev", "ghost.md") is None

    def test_nonexistent_mission_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_content_template("no-such-mission", "spec-template.md") is None

    def test_empty_root_returns_none(self, tmp_repo: MissionTemplateRepository) -> None:
        assert tmp_repo.get_content_template("software-dev", "spec-template.md") is None


# ---------------------------------------------------------------------------
# Category 4: Config-Level Read Tests (get_action_index)
# ---------------------------------------------------------------------------


class TestGetActionIndex:
    def test_existing_action_returns_config_result(
        self, repo: MissionTemplateRepository
    ) -> None:
        result = repo.get_action_index("software-dev", "implement")
        assert result is not None
        assert isinstance(result, ConfigResult)

    def test_parsed_is_dict(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_action_index("software-dev", "implement")
        assert result is not None
        assert isinstance(result.parsed, dict)

    def test_content_is_nonempty(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_action_index("software-dev", "implement")
        assert result is not None
        assert len(result.content) > 0

    def test_origin_format(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_action_index("software-dev", "implement")
        assert result is not None
        assert result.origin == "doctrine/software-dev/actions/implement/index.yaml"

    def test_nonexistent_action_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_action_index("software-dev", "nonexistent-action") is None

    def test_nonexistent_mission_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_action_index("no-such-mission", "implement") is None

    def test_empty_root_returns_none(self, tmp_repo: MissionTemplateRepository) -> None:
        assert tmp_repo.get_action_index("software-dev", "implement") is None


# ---------------------------------------------------------------------------
# Category 5: Config-Level Read Tests (get_action_guidelines)
# ---------------------------------------------------------------------------


class TestGetActionGuidelines:
    def test_existing_action_returns_template_result(
        self, repo: MissionTemplateRepository
    ) -> None:
        result = repo.get_action_guidelines("software-dev", "implement")
        assert result is not None
        assert isinstance(result, TemplateResult)

    def test_content_is_nonempty(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_action_guidelines("software-dev", "implement")
        assert result is not None
        assert len(result.content) > 0

    def test_origin_format(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_action_guidelines("software-dev", "implement")
        assert result is not None
        assert (
            result.origin
            == "doctrine/software-dev/actions/implement/guidelines.md"
        )

    def test_nonexistent_action_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_action_guidelines("software-dev", "nonexistent-action") is None

    def test_nonexistent_mission_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_action_guidelines("no-such-mission", "implement") is None

    def test_empty_root_returns_none(
        self, tmp_repo: MissionTemplateRepository
    ) -> None:
        assert tmp_repo.get_action_guidelines("software-dev", "implement") is None


# ---------------------------------------------------------------------------
# Category 6: Config-Level Read Tests (get_mission_config)
# ---------------------------------------------------------------------------


class TestGetMissionConfig:
    def test_existing_mission_returns_config_result(
        self, repo: MissionTemplateRepository
    ) -> None:
        result = repo.get_mission_config("software-dev")
        assert result is not None
        assert isinstance(result, ConfigResult)

    def test_parsed_is_dict(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_mission_config("software-dev")
        assert result is not None
        assert isinstance(result.parsed, dict)

    def test_content_is_nonempty(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_mission_config("software-dev")
        assert result is not None
        assert len(result.content) > 0

    def test_origin_contains_mission_yaml(
        self, repo: MissionTemplateRepository
    ) -> None:
        result = repo.get_mission_config("software-dev")
        assert result is not None
        assert "mission.yaml" in result.origin

    def test_nonexistent_mission_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_mission_config("no-such-mission") is None

    def test_empty_root_returns_none(self, tmp_repo: MissionTemplateRepository) -> None:
        assert tmp_repo.get_mission_config("software-dev") is None


# ---------------------------------------------------------------------------
# Category 7: Config-Level Read Tests (get_expected_artifacts)
# ---------------------------------------------------------------------------


class TestGetExpectedArtifacts:
    def test_existing_mission_returns_config_result(
        self, repo: MissionTemplateRepository
    ) -> None:
        result = repo.get_expected_artifacts("software-dev")
        assert result is not None
        assert isinstance(result, ConfigResult)

    def test_parsed_is_dict_or_list(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_expected_artifacts("software-dev")
        assert result is not None
        assert isinstance(result.parsed, (dict, list))

    def test_content_is_nonempty(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_expected_artifacts("software-dev")
        assert result is not None
        assert len(result.content) > 0

    def test_origin_format(self, repo: MissionTemplateRepository) -> None:
        result = repo.get_expected_artifacts("software-dev")
        assert result is not None
        assert result.origin == "doctrine/software-dev/expected-artifacts.yaml"

    def test_nonexistent_mission_returns_none(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.get_expected_artifacts("no-such-mission") is None

    def test_empty_root_returns_none(self, tmp_repo: MissionTemplateRepository) -> None:
        assert tmp_repo.get_expected_artifacts("software-dev") is None


# ---------------------------------------------------------------------------
# Category 8: Enumeration Tests (list_command_templates, list_content_templates)
# ---------------------------------------------------------------------------


class TestListCommandTemplates:
    def test_returns_sorted_list(self, repo: MissionTemplateRepository) -> None:
        names = repo.list_command_templates("software-dev")
        assert isinstance(names, list)
        assert names == sorted(names)

    def test_contains_known_templates(self, repo: MissionTemplateRepository) -> None:
        names = repo.list_command_templates("software-dev")
        assert "implement" in names
        assert "specify" in names
        assert "plan" in names
        assert "review" in names

    def test_no_md_extension(self, repo: MissionTemplateRepository) -> None:
        names = repo.list_command_templates("software-dev")
        assert all(not n.endswith(".md") for n in names)

    def test_excludes_readme(self, repo: MissionTemplateRepository) -> None:
        names = repo.list_command_templates("software-dev")
        assert "README" not in names

    def test_nonexistent_mission_returns_empty(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.list_command_templates("no-such-mission") == []

    def test_empty_root_returns_empty(
        self, tmp_repo: MissionTemplateRepository
    ) -> None:
        assert tmp_repo.list_command_templates("software-dev") == []

    def test_mission_without_command_templates_dir(self, tmp_path: Path) -> None:
        """Mission dir exists but has no command-templates subdirectory."""
        mission_dir = tmp_path / "my-mission"
        mission_dir.mkdir()
        (mission_dir / "mission.yaml").write_text("name: test\n")
        repo = MissionTemplateRepository(tmp_path)
        assert repo.list_command_templates("my-mission") == []


class TestListContentTemplates:
    def test_returns_sorted_list(self, repo: MissionTemplateRepository) -> None:
        names = repo.list_content_templates("software-dev")
        assert isinstance(names, list)
        assert names == sorted(names)

    def test_contains_known_templates(self, repo: MissionTemplateRepository) -> None:
        names = repo.list_content_templates("software-dev")
        assert "spec-template.md" in names
        assert "plan-template.md" in names

    def test_excludes_readme(self, repo: MissionTemplateRepository) -> None:
        names = repo.list_content_templates("software-dev")
        assert "README.md" not in names

    def test_nonexistent_mission_returns_empty(
        self, repo: MissionTemplateRepository
    ) -> None:
        assert repo.list_content_templates("no-such-mission") == []

    def test_empty_root_returns_empty(
        self, tmp_repo: MissionTemplateRepository
    ) -> None:
        assert tmp_repo.list_content_templates("software-dev") == []

    def test_mission_without_templates_dir(self, tmp_path: Path) -> None:
        """Mission dir exists but has no templates subdirectory."""
        mission_dir = tmp_path / "my-mission"
        mission_dir.mkdir()
        (mission_dir / "mission.yaml").write_text("name: test\n")
        repo = MissionTemplateRepository(tmp_path)
        assert repo.list_content_templates("my-mission") == []


# ---------------------------------------------------------------------------
# Category 9: Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    def test_alias_import(self) -> None:
        from doctrine.missions import MissionRepository, MissionTemplateRepository

        assert MissionRepository is MissionTemplateRepository

    def test_isinstance(self) -> None:
        from doctrine.missions import MissionRepository

        repo = MissionTemplateRepository.default()
        assert isinstance(repo, MissionRepository)

    def test_default_missions_root_on_alias(self) -> None:
        from doctrine.missions import MissionRepository

        root = MissionRepository.default_missions_root()
        assert root.is_dir()

    def test_alias_default_factory(self) -> None:
        from doctrine.missions import MissionRepository

        repo = MissionRepository.default()
        assert isinstance(repo, MissionTemplateRepository)
        assert "software-dev" in repo.list_missions()

    def test_alias_public_methods_work(self) -> None:
        from doctrine.missions import MissionRepository

        repo = MissionRepository.default()
        result = repo.get_command_template("software-dev", "implement")
        assert result is not None
        assert isinstance(result, TemplateResult)


# ---------------------------------------------------------------------------
# Category 10: Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_missions_root(self, tmp_path: Path) -> None:
        repo = MissionTemplateRepository(tmp_path)
        assert repo.list_missions() == []
        assert repo.get_command_template("anything", "anything") is None
        assert repo.get_content_template("anything", "anything") is None
        assert repo.get_action_index("anything", "anything") is None
        assert repo.get_action_guidelines("anything", "anything") is None
        assert repo.get_mission_config("anything") is None
        assert repo.get_expected_artifacts("anything") is None

    def test_nonexistent_missions_root(self, tmp_path: Path) -> None:
        repo = MissionTemplateRepository(tmp_path / "nonexistent")
        assert repo.list_missions() == []
        assert repo.get_command_template("anything", "anything") is None

    def test_default_classmethod(self) -> None:
        repo = MissionTemplateRepository.default()
        assert isinstance(repo, MissionTemplateRepository)
        assert repo._missions_root.is_dir()

    def test_malformed_yaml_in_action_index(self, tmp_path: Path) -> None:
        """Action index with invalid YAML returns None, doesn't raise."""
        mission_dir = tmp_path / "test-mission" / "actions" / "test-action"
        mission_dir.mkdir(parents=True)
        (mission_dir / "index.yaml").write_text(": invalid: yaml: [[[")
        repo = MissionTemplateRepository(tmp_path)
        assert repo.get_action_index("test-mission", "test-action") is None

    def test_malformed_yaml_in_mission_config(self, tmp_path: Path) -> None:
        """Mission config with invalid YAML returns None, doesn't raise."""
        mission_dir = tmp_path / "test-mission"
        mission_dir.mkdir()
        (mission_dir / "mission.yaml").write_text(": invalid: yaml: [[[")
        repo = MissionTemplateRepository(tmp_path)
        assert repo.get_mission_config("test-mission") is None

    def test_malformed_yaml_in_expected_artifacts(self, tmp_path: Path) -> None:
        """Expected artifacts with invalid YAML returns None, doesn't raise."""
        mission_dir = tmp_path / "test-mission"
        mission_dir.mkdir()
        (mission_dir / "expected-artifacts.yaml").write_text(": invalid: yaml: [[[")
        repo = MissionTemplateRepository(tmp_path)
        assert repo.get_expected_artifacts("test-mission") is None

    def test_empty_yaml_file_returns_none(self, tmp_path: Path) -> None:
        """YAML file that parses to None returns None for config methods."""
        mission_dir = tmp_path / "test-mission"
        mission_dir.mkdir()
        (mission_dir / "mission.yaml").write_text("")
        repo = MissionTemplateRepository(tmp_path)
        assert repo.get_mission_config("test-mission") is None

    def test_empty_template_file_returns_result(self, tmp_path: Path) -> None:
        """An empty template file still returns a TemplateResult (content='')."""
        mission_dir = tmp_path / "test-mission" / "command-templates"
        mission_dir.mkdir(parents=True)
        (mission_dir / "empty.md").write_text("")
        repo = MissionTemplateRepository(tmp_path)
        result = repo.get_command_template("test-mission", "empty")
        assert result is not None
        assert result.content == ""
        assert result.origin == "doctrine/test-mission/command-templates/empty.md"

    def test_unicode_content_preserved(self, tmp_path: Path) -> None:
        """UTF-8 content is read and preserved correctly."""
        mission_dir = tmp_path / "test-mission" / "command-templates"
        mission_dir.mkdir(parents=True)
        content = "# Instruction\n\nUse emojis: \U0001f431\U0001f431\nAccented: caf\u00e9\n"
        (mission_dir / "unicode.md").write_text(content, encoding="utf-8")
        repo = MissionTemplateRepository(tmp_path)
        result = repo.get_command_template("test-mission", "unicode")
        assert result is not None
        assert result.content == content

    def test_get_command_template_consistency_with_list(
        self, repo: MissionTemplateRepository
    ) -> None:
        """Every template returned by list_command_templates is readable."""
        names = repo.list_command_templates("software-dev")
        for name in names:
            result = repo.get_command_template("software-dev", name)
            assert result is not None, f"list returned '{name}' but get returned None"
            assert len(result.content) > 0, f"Empty content for listed template '{name}'"

    def test_get_content_template_consistency_with_list(
        self, repo: MissionTemplateRepository
    ) -> None:
        """Every template returned by list_content_templates is readable."""
        names = repo.list_content_templates("software-dev")
        for name in names:
            result = repo.get_content_template("software-dev", name)
            assert result is not None, f"list returned '{name}' but get returned None"
            assert len(result.content) > 0, f"Empty content for listed template '{name}'"

    def test_all_missions_have_readable_config(
        self, repo: MissionTemplateRepository
    ) -> None:
        """Every listed mission has a readable mission config."""
        for mission in repo.list_missions():
            result = repo.get_mission_config(mission)
            assert result is not None, f"Mission '{mission}' listed but config unreadable"
            assert isinstance(result.parsed, dict)
