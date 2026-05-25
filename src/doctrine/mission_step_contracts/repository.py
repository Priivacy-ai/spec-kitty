"""
MissionStepContract repository with two-source loading (built-in + project).

Provides:
- Two-source YAML loading (built-in package data + project filesystem)
- Field-level merge semantics for project overrides
- Query methods (list_all, get, get_by_action)
- Save for project step contracts
"""

from pathlib import Path

from importlib.resources import files
from ruamel.yaml import YAML

from doctrine.base import BaseDoctrineRepository
from .models import MissionStepContract


class MissionStepContractRepository(BaseDoctrineRepository[MissionStepContract]):
    """Repository for loading and managing mission step contract YAML files."""

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
        """Get default built-in directory from package data."""
        try:
            resource = files("doctrine.mission_step_contracts")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("built-in")))
            return Path(str(resource)) / "built-in"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "built-in"

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
        Returns None if no match found.
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
            ValueError: If project_dir is not configured.
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
