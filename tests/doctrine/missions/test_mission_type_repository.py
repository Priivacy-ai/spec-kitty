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
- Authoring ``template_set:`` (model kwarg or YAML) fails loudly (SC-002,
  mission-step-creatability-01KXQA6R WP01) -- the retired field's key is
  now rejected by ``extra="forbid"`` rather than silently honored or dropped.
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
        assert not hasattr(mt, "governance_refs")
        assert not hasattr(mt, "template_set")

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

    def test_template_set_kwarg_raises_validation_error(self) -> None:
        """SC-002 / FR-001: authoring the retired field now fails loudly.

        ``extra="forbid"`` rejects the unknown key regardless of value --
        this is the model-constructor half of the pack-fails-loud proof
        (T007); ``TestTemplateSetAuthoringFailsLoudly`` below exercises the
        equivalent through the YAML-loader entry point.
        """
        with pytest.raises(ValidationError, match="template_set"):
            MissionType(
                id="my-type",
                display_name="My Type",
                action_sequence=["step-a"],
                template_set={"spec": "spec-template.md"},  # type: ignore[call-arg]
            )

    def test_template_set_none_kwarg_also_raises(self) -> None:
        """Even an explicit ``None`` for the retired key is rejected -- the key's
        mere presence is forbidden, not just a non-``None`` value."""
        with pytest.raises(ValidationError, match="template_set"):
            MissionType(
                id="my-type",
                display_name="My Type",
                action_sequence=["step-a"],
                template_set=None,  # type: ignore[call-arg]
            )


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
        """S-C cutover (WP01, C-005): ``template_set`` is no longer a ``MissionType``
        field -- migrated to the step-authority projection (mirrors
        ``TestSoftwareDevProjectionParity`` in ``test_softwaredev_roundtrip.py``)."""
        from doctrine.missions.mission_step_repository import MissionStepRepository
        from doctrine.missions.step_projection import project_template_set

        steps = list(
            MissionStepRepository.default()
            .resolve_all_for_mission_type("software-dev", pack_context=None)
            .values()
        )
        assert project_template_set(steps) == {
            "spec": "spec-template.md",
            "plan": "plan-template.md",
        }

    def test_research_template_set(self) -> None:
        """S-C Concern B (WP03, C-003/C-010): ``research`` authors a ``spec`` ref
        on ``scoping`` and a ``plan`` ref on ``methodology``, with per-type-unique
        ``template_file`` names (NFR-006) -- mirrors ``test_software_dev_template_set``
        above."""
        from doctrine.missions.mission_step_repository import MissionStepRepository
        from doctrine.missions.step_projection import project_template_set

        steps = list(
            MissionStepRepository.default()
            .resolve_all_for_mission_type("research", pack_context=None)
            .values()
        )
        assert project_template_set(steps) == {
            "spec": "research-spec-template.md",
            "plan": "research-plan-template.md",
        }

    def test_documentation_template_set(self) -> None:
        """S-C Concern B (mission-step-creatability-01KXQA6R WP02, reconciled by
        WP05, C-003/C-010): ``documentation`` authors a ``spec`` ref on
        ``discover`` and a ``plan`` ref on ``design``, with per-type-unique
        ``template_file`` names (NFR-006) -- mirrors ``test_research_template_set``
        above. ``documentation`` was removed from the now-deleted
        ``test_non_software_builtin_template_set_is_explicitly_null``
        parametrization once WP02 authored these refs."""
        from doctrine.missions.mission_step_repository import MissionStepRepository
        from doctrine.missions.step_projection import project_template_set

        steps = list(
            MissionStepRepository.default()
            .resolve_all_for_mission_type("documentation", pack_context=None)
            .values()
        )
        assert project_template_set(steps) == {
            "spec": "documentation-spec-template.md",
            "plan": "documentation-plan-template.md",
        }

    def test_plan_template_set(self) -> None:
        """S-C Concern B (mission-step-creatability-01KXQA6R WP04, reconciled by
        WP05, C-003/C-010): ``plan`` authors a ``spec`` ref on ``specify`` and a
        ``plan`` ref on ``plan``, with per-type-unique ``template_file`` names
        (NFR-006) -- mirrors ``test_research_template_set`` above. ``plan`` was
        removed from the now-deleted
        ``test_non_software_builtin_template_set_is_explicitly_null``
        parametrization once WP04 authored these refs."""
        from doctrine.missions.mission_step_repository import MissionStepRepository
        from doctrine.missions.step_projection import project_template_set

        steps = list(
            MissionStepRepository.default()
            .resolve_all_for_mission_type("plan", pack_context=None)
            .values()
        )
        assert project_template_set(steps) == {
            "spec": "plan-spec-skeleton.md",
            "plan": "plan-plan-skeleton.md",
        }


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


class TestTemplateSetAuthoringFailsLoudly:
    """SC-002 / FR-001 (S-C cutover, mission-step-creatability-01KXQA6R WP01).

    A ``mission_types/*.yaml`` that (incorrectly) authors ``template_set:``
    must fail loudly at load time -- neither silently honored nor silently
    dropped. This is the YAML-loader-entry-point half of the pack-fails-loud
    proof (T007); ``TestMissionTypeModel.test_template_set_kwarg_raises_validation_error``
    covers the equivalent at the bare model-constructor level.

    ``_inject_projected_fields`` no longer overlays a ``template_set`` key
    (the entire overlay assignment was dropped, FR-001) -- ``payload =
    dict(raw)`` preserves the authored key verbatim, and ``MissionType``'s
    ``extra="forbid"`` rejects it during ``MissionType.model_validate``,
    which ``MissionTypeRepository.__init__`` (eager) surfaces immediately.
    """

    def _write_yaml(self, directory: Path, filename: str, content: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_text(content, encoding="utf-8")

    def test_authored_template_set_raises_validation_error(self, tmp_path: Path) -> None:
        self._write_yaml(
            tmp_path,
            "rogue-type.yaml",
            "schema_version: 1\n"
            "id: rogue-type\n"
            "display_name: Rogue\n"
            "action_sequence:\n"
            "  - step-one\n"
            "template_set:\n"
            "  spec: spec-template.md\n",
        )
        with pytest.raises(ValidationError, match="template_set"):
            MissionTypeRepository(tmp_path)
