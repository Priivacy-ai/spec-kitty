"""
Tactic repository with two-source loading (shipped + project).

Provides:
- Two-source YAML loading (shipped package data + project filesystem)
- Field-level merge semantics for project overrides
- Query methods (list_all, get)
- Save for project tactics
"""

import warnings
from pathlib import Path
from typing import Any

from importlib.resources import files
from ruamel.yaml import YAML

from .models import Tactic


class TacticRepository:
    """Repository for loading and managing tactic YAML files."""

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
    ) -> None:
        self._tactics: dict[str, Tactic] = {}
        self._shipped_dir = shipped_dir or self._default_shipped_dir()
        self._project_dir = project_dir
        self._load()

    @staticmethod
    def _default_shipped_dir() -> Path:
        """Get default shipped tactics directory from package data."""
        try:
            resource = files("doctrine.tactics")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except (ModuleNotFoundError, TypeError):
            return Path(__file__).parent / "shipped"

    def _load(self) -> None:
        """Load tactics from shipped and project directories."""
        yaml = YAML(typ="safe")
        shipped: dict[str, Tactic] = {}

        if self._shipped_dir.exists():
            for yaml_file in sorted(self._shipped_dir.rglob("*.tactic.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    tactic = Tactic.model_validate(data)
                    shipped[tactic.id] = tactic
                except Exception as e:
                    warnings.warn(
                        f"Skipping invalid shipped tactic {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

        self._tactics = shipped.copy()

        if self._project_dir and self._project_dir.exists():
            for yaml_file in sorted(self._project_dir.glob("*.tactic.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    tactic_id = data.get("id")
                    if not tactic_id:
                        warnings.warn(
                            f"Skipping project tactic {yaml_file.name}: no id",
                            UserWarning,
                            stacklevel=2,
                        )
                        continue

                    if tactic_id in shipped:
                        merged = self._merge_tactics(shipped[tactic_id], data)
                        self._tactics[tactic_id] = merged
                    else:
                        tactic = Tactic.model_validate(data)
                        self._tactics[tactic.id] = tactic
                except Exception as e:
                    warnings.warn(
                        f"Skipping invalid project tactic {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

    @staticmethod
    def _merge_tactics(
        shipped: Tactic, project_data: dict[str, Any]
    ) -> Tactic:
        """Merge project data into shipped tactic at field level."""
        shipped_dict = shipped.model_dump()
        merged = {**shipped_dict, **project_data}
        return Tactic.model_validate(merged)

    def list_all(self) -> list[Tactic]:
        """Return all loaded tactics sorted by ID."""
        return sorted(self._tactics.values(), key=lambda t: t.id)

    def get(self, tactic_id: str) -> Tactic | None:
        """Get tactic by ID (kebab-case, e.g. 'zombies-tdd')."""
        return self._tactics.get(tactic_id)

    def save(self, tactic: Tactic) -> Path:
        """Save tactic to project directory.

        Returns:
            Path to the written YAML file.

        Raises:
            ValueError: If project_dir is not configured.
        """
        if self._project_dir is None:
            raise ValueError("Cannot save tactic: project_dir not configured")

        self._project_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{tactic.id}.tactic.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename

        data = tactic.model_dump(mode="json", exclude_none=True)

        with yaml_file.open("w") as f:
            yaml.dump(data, f)

        self._tactics[tactic.id] = tactic
        return yaml_file
