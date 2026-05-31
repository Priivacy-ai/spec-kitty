"""Legacy MissionStepContract domain model + repository.

WP01 (mission ``charter-doctrine-mission-type-configuration-01KSWJVX``)
relocates the previously-standalone ``doctrine/mission_step_contracts/``
subpackage here. The on-disk ``*.step-contract.yaml`` schema is preserved
verbatim so existing built-in / project contracts keep loading; only the
import path changes.

The new unified :class:`doctrine.missions.models.MissionStep` model (FR-011)
supersedes the legacy step-shape semantically for ``MissionType``-owned
steps. The legacy contract types in this module are retained as a
compatibility surface for the runtime contract registry, contract
synthesis, and the on-disk ``*.step-contract.yaml`` loader path until
later WPs migrate those callers to the unified model. The inner step
shape consumed by ``MissionStepContract`` is named
:class:`MissionStepContractStep` to keep it distinct from the unified
:class:`~doctrine.missions.models.MissionStep`.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ruamel.yaml import YAML

from doctrine.artifact_kinds import ArtifactKind
from doctrine.base import BaseDoctrineRepository

__all__ = [
    "DelegatesTo",
    "MissionStepContract",
    "MissionStepContractRepository",
    "MissionStepContractStep",
]


class DelegatesTo(BaseModel):
    """Delegation link from a contract step to doctrine artifacts.

    The ``kind`` identifies the artifact type (paradigm, tactic,
    directive, etc.). The ``candidates`` list names which artifacts
    *could* concretize this step — the charter's selections determine
    which one actually applies at runtime.
    """

    model_config = ConfigDict(frozen=True)

    kind: ArtifactKind
    candidates: list[str] = Field(min_length=1)


class MissionStepContractStep(BaseModel):
    """A single step inside a legacy :class:`MissionStepContract`.

    This is the LEGACY shape used by ``*.step-contract.yaml`` files and
    by the runtime contract registry. The unified mission-step model
    owned by ``MissionType`` is
    :class:`doctrine.missions.models.MissionStep`; that class is the
    canonical surface for new mission-step authoring (FR-011).
    """

    model_config = ConfigDict(frozen=True)

    id: str
    description: str
    command: str | None = None
    delegates_to: DelegatesTo | None = None
    guidance: str | None = None


class MissionStepContract(BaseModel):
    """Legacy contract defining the structural steps of a mission action.

    A step contract replaces inline governance prose in command
    templates with a structured, schema-validated sequence of steps.
    Each step may delegate its concretization to doctrine artifacts via
    ``delegates_to`` and/or carry freeform ``guidance`` for
    step-specific instructions.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    schema_version: str = Field(alias="schema_version")
    action: str
    mission: str
    steps: list[MissionStepContractStep] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_step_ids(self) -> MissionStepContract:
        ids = [s.id for s in self.steps]
        duplicates = [sid for sid in ids if ids.count(sid) > 1]
        if duplicates:
            raise ValueError(
                f"duplicate step IDs: {sorted(set(duplicates))}"
            )
        return self


class MissionStepContractRepository(BaseDoctrineRepository[MissionStepContract]):
    """Repository for loading and managing mission step contract YAML files.

    Two-source loading (built-in + project) with field-level merge
    semantics. Built-in contracts ship under
    ``doctrine.missions.built_in_step_contracts``; project-layer
    contracts live in
    ``<repo_root>/.kittify/doctrine/mission_step_contracts/``
    (path unchanged from the legacy location to preserve operator UX).
    """

    GLOB = "*.step-contract.yaml"

    def __init__(
        self,
        built_in_dir: Path | None = None,
        *,
        org_dirs: list[Path] | None = None,
        project_dir: Path | None = None,
    ) -> None:
        super().__init__(
            built_in_dir=built_in_dir or self._default_built_in_dir(),
            org_dirs=org_dirs,
            project_dir=project_dir,
        )

    @staticmethod
    def _default_built_in_dir() -> Path:
        """Locate the built-in step-contract directory packaged with doctrine."""
        try:
            resource = files("doctrine.missions.built_in_step_contracts")
            if hasattr(resource, "joinpath"):
                return Path(str(resource))
            return Path(str(resource))
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "built_in_step_contracts"

    @property
    def _schema(self) -> type[MissionStepContract]:
        return MissionStepContract

    @property
    def _glob(self) -> str:
        return self.GLOB

    def get_by_action(
        self, mission: str, action: str
    ) -> MissionStepContract | None:
        """Get contract by mission and action name.

        Scans all loaded contracts for matching mission + action pair.
        Returns ``None`` if no match found.
        """
        for contract in self._items.values():
            if contract.mission == mission and contract.action == action:
                return contract
        return None

    def save(self, contract: MissionStepContract) -> Path:
        """Save contract to project directory.

        Returns:
            Path to the written YAML file.

        Raises:
            ValueError: If ``project_dir`` is not configured.
        """
        if self._project_dir is None:
            raise ValueError(
                "Cannot save step contract: project_dir not configured"
            )

        self._project_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{contract.id}.step-contract.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename

        data = contract.model_dump(mode="json", exclude_none=True)

        with yaml_file.open("w") as f:
            yaml.dump(data, f)

        self._items[contract.id] = contract
        return yaml_file
