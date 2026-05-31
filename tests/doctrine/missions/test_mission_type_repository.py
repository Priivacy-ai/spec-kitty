"""Tests for MissionType model and MissionTypeRepository.

Covers:
- Built-in YAML round-trip: software-dev.yaml loads with correct action_sequence
- All four built-in YAMLs load without error
- action_sequence non-empty validator fires on empty list
- action_sequence uniqueness validator fires on duplicate step IDs
- MissionType.id rejected on non-kebab-case input
- MissionTypeRepository.get("software-dev") returns the correct artifact
- MissionTypeRepository.get("nonexistent") returns None
- Repository raises on YAML with id mismatching filename stem
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from doctrine.missions.mission_type_repository import MissionTypeRepository
from doctrine.missions.models import MissionType

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


# ── MissionType model unit tests ─────────────────────────────────────────────


class TestMissionTypeModel:
    """Unit tests for MissionType Pydantic model validation."""

    def test_valid_mission_type_constructs_successfully(self) -> None:
        mt = MissionType(
            schema_version=1,
            id="my-type",
            display_name="My Type",
            action_sequence=["step-a", "step-b"],
        )
        assert mt.id == "my-type"
        assert mt.display_name == "My Type"
        assert mt.action_sequence == ["step-a", "step-b"]
        assert mt.extends is None
        assert mt.governance_refs == []
        assert mt.template_set is None

    def test_empty_action_sequence_raises(self) -> None:
        with pytest.raises(ValidationError, match="action_sequence must be non-empty"):
            MissionType(
                id="my-type",
                display_name="My Type",
                action_sequence=[],
            )

    def test_duplicate_action_sequence_raises(self) -> None:
        with pytest.raises(
            ValidationError, match="action_sequence must contain unique step IDs"
        ):
            MissionType(
                id="my-type",
                display_name="My Type",
                action_sequence=["step-a", "step-b", "step-a"],
            )

    def test_id_with_uppercase_rejected(self) -> None:
        with pytest.raises(ValidationError, match="IDENTIFIER_PATTERN"):
            MissionType(
                id="MyType",
                display_name="Bad",
                action_sequence=["step-a"],
            )

    def test_id_with_leading_digit_rejected(self) -> None:
        with pytest.raises(ValidationError, match="IDENTIFIER_PATTERN"):
            MissionType(
                id="1bad",
                display_name="Bad",
                action_sequence=["step-a"],
            )

    def test_id_with_underscore_rejected(self) -> None:
        with pytest.raises(ValidationError, match="IDENTIFIER_PATTERN"):
            MissionType(
                id="bad_id",
                display_name="Bad",
                action_sequence=["step-a"],
            )

    def test_template_set_dict_accepted(self) -> None:
        mt = MissionType(
            id="my-type",
            display_name="My Type",
            action_sequence=["step-a"],
            template_set={"spec": "spec-template.md"},
        )
        assert mt.template_set == {"spec": "spec-template.md"}

    def test_template_set_none_accepted(self) -> None:
        mt = MissionType(
            id="my-type",
            display_name="My Type",
            action_sequence=["step-a"],
            template_set=None,
        )
        assert mt.template_set is None


# ── MissionTypeRepository with built-in YAMLs ────────────────────────────────


def _builtin_repo() -> MissionTypeRepository:
    """Return a MissionTypeRepository pointed at the doctrine-bundled mission_types dir."""
    mission_types_dir = Path(__file__).parent.parent.parent.parent / "src" / "doctrine" / "missions" / "mission_types"
    return MissionTypeRepository(mission_types_dir)


class TestBuiltinYamlFiles:
    """Verify the four built-in YAML files load correctly."""

    def test_software_dev_loads(self) -> None:
        repo = _builtin_repo()
        mt = repo.get("software-dev")
        assert mt is not None
        assert mt.id == "software-dev"
        assert mt.display_name == "Software Development"
        assert mt.action_sequence == ["specify", "plan", "tasks", "implement", "review"]

    def test_documentation_loads(self) -> None:
        repo = _builtin_repo()
        mt = repo.get("documentation")
        assert mt is not None
        assert mt.id == "documentation"
        assert mt.action_sequence == [
            "discover",
            "audit",
            "design",
            "generate",
            "validate",
            "publish",
            "accept",
        ]

    def test_research_loads(self) -> None:
        repo = _builtin_repo()
        mt = repo.get("research")
        assert mt is not None
        assert mt.id == "research"
        assert mt.action_sequence == [
            "scoping",
            "methodology",
            "gathering",
            "synthesis",
            "output",
        ]

    def test_plan_loads(self) -> None:
        repo = _builtin_repo()
        mt = repo.get("plan")
        assert mt is not None
        assert mt.id == "plan"
        assert mt.action_sequence == ["specify", "research", "plan", "review"]

    def test_all_four_builtin_yamls_load(self) -> None:
        repo = _builtin_repo()
        ids = repo.ids()
        assert "software-dev" in ids
        assert "documentation" in ids
        assert "research" in ids
        assert "plan" in ids

    def test_ids_sorted(self) -> None:
        repo = _builtin_repo()
        ids = repo.ids()
        assert ids == sorted(ids)

    def test_load_all_sorted_by_id(self) -> None:
        repo = _builtin_repo()
        all_types = repo.load_all()
        assert [mt.id for mt in all_types] == sorted(mt.id for mt in all_types)

    def test_software_dev_template_set(self) -> None:
        repo = _builtin_repo()
        mt = repo.get("software-dev")
        assert mt is not None
        assert isinstance(mt.template_set, dict)
        assert "spec" in mt.template_set
        assert "plan" in mt.template_set


# ── MissionTypeRepository lookup behavior ────────────────────────────────────


class TestMissionTypeRepositoryLookup:
    """Test get() and ids() semantics."""

    def test_get_known_id_returns_mission_type(self) -> None:
        repo = _builtin_repo()
        mt = repo.get("software-dev")
        assert isinstance(mt, MissionType)

    def test_get_nonexistent_returns_none(self) -> None:
        repo = _builtin_repo()
        result = repo.get("nonexistent")
        assert result is None

    def test_get_empty_string_returns_none(self) -> None:
        repo = _builtin_repo()
        result = repo.get("")
        assert result is None

    def test_empty_directory_returns_empty_repo(self, tmp_path: Path) -> None:
        repo = MissionTypeRepository(tmp_path)
        assert repo.ids() == []
        assert repo.load_all() == []

    def test_nonexistent_directory_returns_empty_repo(self, tmp_path: Path) -> None:
        repo = MissionTypeRepository(tmp_path / "no-such-dir")
        assert repo.ids() == []
        assert repo.load_all() == []


# ── MissionTypeRepository YAML loading ────────────────────────────────────────


class TestMissionTypeRepositoryYamlLoading:
    """Test YAML parsing and id-stem validation."""

    def _write_yaml(self, directory: Path, filename: str, content: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_text(content, encoding="utf-8")

    def test_valid_yaml_round_trip(self, tmp_path: Path) -> None:
        self._write_yaml(
            tmp_path,
            "my-mission.yaml",
            "schema_version: 1\n"
            "id: my-mission\n"
            "display_name: My Mission\n"
            "action_sequence:\n"
            "  - step-one\n"
            "  - step-two\n",
        )
        repo = MissionTypeRepository(tmp_path)
        mt = repo.get("my-mission")
        assert mt is not None
        assert mt.action_sequence == ["step-one", "step-two"]

    def test_id_mismatch_with_filename_stem_raises(self, tmp_path: Path) -> None:
        self._write_yaml(
            tmp_path,
            "correct-name.yaml",
            "schema_version: 1\n"
            "id: wrong-name\n"
            "display_name: Wrong\n"
            "action_sequence:\n"
            "  - step-one\n",
        )
        with pytest.raises(ValueError, match="does not match filename stem"):
            MissionTypeRepository(tmp_path)

    def test_non_mapping_yaml_raises(self, tmp_path: Path) -> None:
        self._write_yaml(tmp_path, "list-type.yaml", "- step-one\n- step-two\n")
        with pytest.raises(ValueError, match="Expected a YAML mapping"):
            MissionTypeRepository(tmp_path)

    def test_invalid_model_yaml_raises_validation_error(self, tmp_path: Path) -> None:
        self._write_yaml(
            tmp_path,
            "bad-model.yaml",
            "schema_version: 1\n"
            "id: bad-model\n"
            "display_name: Bad\n"
            "action_sequence: []\n",  # empty — fails non-empty validator
        )
        with pytest.raises((ValueError, Exception)):
            MissionTypeRepository(tmp_path)

    def test_multiple_yamls_all_indexed(self, tmp_path: Path) -> None:
        for slug, step in [("alpha-type", "step-x"), ("beta-type", "step-y")]:
            self._write_yaml(
                tmp_path,
                f"{slug}.yaml",
                f"schema_version: 1\nid: {slug}\ndisplay_name: {slug}\n"
                f"action_sequence:\n  - {step}\n",
            )
        repo = MissionTypeRepository(tmp_path)
        assert set(repo.ids()) == {"alpha-type", "beta-type"}
