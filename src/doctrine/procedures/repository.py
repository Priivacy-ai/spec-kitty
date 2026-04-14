"""
Procedure repository with two-source loading (shipped + project).
"""

import warnings
from pathlib import Path
from typing import Any

from importlib.resources import files
from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .models import Procedure
from .validation import reject_procedure_inline_refs


class ProcedureRepository:
    """Repository for loading and managing procedure YAML files."""

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
    ) -> None:
        self._procedures: dict[str, Procedure] = {}
        self._shipped_dir = shipped_dir or self._default_shipped_dir()
        self._project_dir = project_dir
        self._load()

    @staticmethod
    def _default_shipped_dir() -> Path:
        """Get default shipped procedures directory from package data."""
        try:
            resource = files("doctrine.procedures")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "shipped"

    def _load(self) -> None:
        """Load procedures from shipped and project directories."""
        yaml = YAML(typ="safe")
        shipped: dict[str, Procedure] = {}

        if self._shipped_dir.exists():
            for yaml_file in sorted(self._shipped_dir.rglob("*.procedure.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    reject_procedure_inline_refs(data, file_path=str(yaml_file))
                    procedure = Procedure.model_validate(data)
                    shipped[procedure.id] = procedure
                except (YAMLError, ValidationError, OSError) as e:
                    warnings.warn(
                        f"Skipping invalid shipped procedure {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

        self._procedures = shipped.copy()

        if self._project_dir and self._project_dir.exists():
            for yaml_file in sorted(self._project_dir.glob("*.procedure.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    reject_procedure_inline_refs(data, file_path=str(yaml_file))
                    procedure_id = data.get("id")
                    if not procedure_id:
                        warnings.warn(
                            f"Skipping project procedure {yaml_file.name}: no id",
                            UserWarning,
                            stacklevel=2,
                        )
                        continue

                    if procedure_id in shipped:
                        merged = self._merge_procedures(shipped[procedure_id], data)
                        self._procedures[procedure_id] = merged
                    else:
                        procedure = Procedure.model_validate(data)
                        self._procedures[procedure.id] = procedure
                except (YAMLError, ValidationError, OSError) as e:
                    warnings.warn(
                        f"Skipping invalid project procedure {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

    @staticmethod
    def _merge_procedures(
        shipped: Procedure, project_data: dict[str, Any]
    ) -> Procedure:
        """Merge project data into shipped procedure at field level."""
        shipped_dict = shipped.model_dump()
        merged = {**shipped_dict, **project_data}
        return Procedure.model_validate(merged)

    def list_all(self) -> list[Procedure]:
        """Return all loaded procedures sorted by ID."""
        return sorted(self._procedures.values(), key=lambda p: p.id)

    def get(self, procedure_id: str) -> Procedure | None:
        """Get procedure by ID."""
        return self._procedures.get(procedure_id)

    def save(self, procedure: Procedure) -> Path:
        """Save procedure to project directory."""
        if self._project_dir is None:
            raise ValueError("Cannot save procedure: project_dir not configured")

        self._project_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{procedure.id}.procedure.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename

        data = procedure.model_dump(mode="json", exclude_none=True)
        with yaml_file.open("w") as f:
            yaml.dump(data, f)

        self._procedures[procedure.id] = procedure
        return yaml_file
