"""
Paradigm repository with two-source loading (shipped + project).
"""

import warnings
from pathlib import Path
from typing import Any

from importlib.resources import files
from ruamel.yaml import YAML

from .models import Paradigm


class ParadigmRepository:
    """Repository for loading and managing paradigm YAML files."""

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
    ) -> None:
        self._paradigms: dict[str, Paradigm] = {}
        self._shipped_dir = shipped_dir or self._default_shipped_dir()
        self._project_dir = project_dir
        self._load()

    @staticmethod
    def _default_shipped_dir() -> Path:
        """Get default shipped paradigms directory from package data."""
        try:
            resource = files("doctrine.paradigms")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except Exception:
            return Path(__file__).parent / "shipped"

    def _load(self) -> None:
        """Load paradigms from shipped and project directories."""
        yaml = YAML(typ="safe")
        shipped: dict[str, Paradigm] = {}

        if self._shipped_dir.exists():
            for yaml_file in sorted(self._shipped_dir.glob("*.paradigm.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    paradigm = Paradigm.model_validate(data)
                    shipped[paradigm.id] = paradigm
                except Exception as e:
                    warnings.warn(
                        f"Skipping invalid shipped paradigm {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

        self._paradigms = shipped.copy()

        if self._project_dir and self._project_dir.exists():
            for yaml_file in sorted(self._project_dir.glob("*.paradigm.yaml")):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    paradigm_id = data.get("id")
                    if not paradigm_id:
                        warnings.warn(
                            f"Skipping project paradigm {yaml_file.name}: no id",
                            UserWarning,
                            stacklevel=2,
                        )
                        continue

                    if paradigm_id in shipped:
                        merged = self._merge_paradigms(shipped[paradigm_id], data)
                        self._paradigms[paradigm_id] = merged
                    else:
                        paradigm = Paradigm.model_validate(data)
                        self._paradigms[paradigm.id] = paradigm
                except Exception as e:
                    warnings.warn(
                        f"Skipping invalid project paradigm {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

    @staticmethod
    def _merge_paradigms(
        shipped: Paradigm, project_data: dict[str, Any]
    ) -> Paradigm:
        """Merge project data into shipped paradigm at field level."""
        shipped_dict = shipped.model_dump()
        merged = {**shipped_dict, **project_data}
        return Paradigm.model_validate(merged)

    def list_all(self) -> list[Paradigm]:
        """Return all loaded paradigms sorted by ID."""
        return sorted(self._paradigms.values(), key=lambda p: p.id)

    def get(self, paradigm_id: str) -> Paradigm | None:
        """Get paradigm by ID."""
        return self._paradigms.get(paradigm_id)

    def save(self, paradigm: Paradigm) -> Path:
        """Save paradigm to project directory."""
        if self._project_dir is None:
            raise ValueError("Cannot save paradigm: project_dir not configured")

        self._project_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{paradigm.id}.paradigm.yaml"
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / filename

        data = paradigm.model_dump(mode="json", exclude_none=True)
        with yaml_file.open("w") as f:
            yaml.dump(data, f)

        self._paradigms[paradigm.id] = paradigm
        return yaml_file

