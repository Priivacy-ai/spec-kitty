"""
MissionStepContract repository with two-source loading (shipped + project).

Provides:
- Two-source YAML loading (shipped package data + project filesystem)
- Field-level merge semantics for project overrides
- Query methods (list_all, get, get_by_action)
- Save for project step contracts
"""

import warnings
from pathlib import Path
from typing import Any

from importlib.resources import files
from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .models import MissionStepContract


class MissionStepContractRepository:
    """Repository for loading and managing mission step contract YAML files."""

    GLOB = "*.step-contract.yaml"

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
    ) -> None:
        self._contracts: dict[str, MissionStepContract] = {}
        self._shipped_dir = shipped_dir or self._default_shipped_dir()
        self._project_dir = project_dir
        self._load()

    @staticmethod
    def _default_shipped_dir() -> Path:
        """Get default shipped directory from package data."""
        try:
            resource = files("doctrine.mission_step_contracts")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "shipped"

    def _load(self) -> None:
        """Load contracts from shipped and project directories."""
        yaml = YAML(typ="safe")
        shipped: dict[str, MissionStepContract] = {}

        if self._shipped_dir.exists():
            for yaml_file in sorted(self._shipped_dir.glob(self.GLOB)):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    contract = MissionStepContract.model_validate(data)
                    shipped[contract.id] = contract
                except (YAMLError, ValidationError, OSError) as e:
                    warnings.warn(
                        f"Skipping invalid shipped step contract "
                        f"{yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

        self._contracts = shipped.copy()

        if self._project_dir and self._project_dir.exists():
            for yaml_file in sorted(self._project_dir.glob(self.GLOB)):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    contract_id = data.get("id")
                    if not contract_id:
                        warnings.warn(
                            f"Skipping project step contract "
                            f"{yaml_file.name}: no id",
                            UserWarning,
                            stacklevel=2,
                        )
                        continue

                    if contract_id in shipped:
                        merged = self._merge_contracts(
                            shipped[contract_id], data
                        )
                        self._contracts[contract_id] = merged
                    else:
                        contract = MissionStepContract.model_validate(data)
                        self._contracts[contract.id] = contract
                except (YAMLError, ValidationError, OSError) as e:
                    warnings.warn(
                        f"Skipping invalid project step contract "
                        f"{yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

    @staticmethod
    def _merge_contracts(
        shipped: MissionStepContract, project_data: dict[str, Any]
    ) -> MissionStepContract:
        """Merge project data into shipped contract at field level."""
        shipped_dict = shipped.model_dump()
        merged = {**shipped_dict, **project_data}
        return MissionStepContract.model_validate(merged)

    def list_all(self) -> list[MissionStepContract]:
        """Return all loaded contracts sorted by ID."""
        return sorted(self._contracts.values(), key=lambda c: c.id)

    def get(self, contract_id: str) -> MissionStepContract | None:
        """Get contract by ID."""
        return self._contracts.get(contract_id)

    def get_by_action(
        self, mission: str, action: str
    ) -> MissionStepContract | None:
        """Get contract by mission and action name.

        Scans all loaded contracts for matching mission + action pair.
        Returns None if no match found.
        """
        for contract in self._contracts.values():
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

        self._contracts[contract.id] = contract
        return yaml_file
