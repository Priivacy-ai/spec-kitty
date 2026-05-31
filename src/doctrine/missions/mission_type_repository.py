"""MissionTypeRepository — loads and indexes MissionType YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from .models import MissionType

__all__ = ["MissionTypeRepository"]


class MissionTypeRepository:
    """Loads and indexes MissionType YAML files from a directory.

    Scans *mission_types_dir* for ``*.yaml`` files, parses each via the
    :class:`~doctrine.missions.models.MissionType` Pydantic model, validates
    that each file's ``id`` field matches the filename stem, then indexes the
    results for O(1) lookup.

    The repository is eager: all files are loaded at construction time.
    Any parse or validation error raises immediately so callers never receive
    a partially populated repository.

    Parameters
    ----------
    mission_types_dir:
        Path to the directory that contains ``*.yaml`` MissionType files.
    """

    def __init__(self, mission_types_dir: Path) -> None:
        self._dir = mission_types_dir
        self._index: dict[str, MissionType] = self._load(mission_types_dir)

    # ------------------------------------------------------------------
    # Class-level constructor helpers
    # ------------------------------------------------------------------

    @classmethod
    def default(cls) -> MissionTypeRepository:
        """Return a repository loaded from the doctrine-bundled mission_types directory."""
        try:
            from importlib.resources import files

            resource = files("doctrine") / "missions" / "mission_types"
            return cls(Path(str(resource)))
        except (ModuleNotFoundError, TypeError):
            return cls(Path(__file__).parent / "mission_types")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load_all(self) -> list[MissionType]:
        """Return all loaded :class:`MissionType` objects, sorted by ``id``.

        Returns
        -------
        list[MissionType]
            Sorted by ``id`` (ascending, lexicographic).
        """
        return sorted(self._index.values(), key=lambda m: m.id)

    def get(self, mission_type_id: str) -> MissionType | None:
        """Look up a MissionType by its id.

        Parameters
        ----------
        mission_type_id:
            The ``id`` field value (e.g. ``"software-dev"``).

        Returns
        -------
        MissionType | None
            The matching :class:`MissionType`, or ``None`` if not found.
        """
        return self._index.get(mission_type_id)

    def ids(self) -> list[str]:
        """Return a sorted list of all registered mission-type IDs.

        Returns
        -------
        list[str]
            Sorted ascending, lexicographic.
        """
        return sorted(self._index.keys())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load(directory: Path) -> dict[str, MissionType]:
        """Scan *directory* for ``*.yaml`` files and return an id-keyed dict.

        Raises
        ------
        ValueError
            If a file's parsed ``id`` does not match the filename stem.
        pydantic.ValidationError
            If any YAML file fails :class:`MissionType` validation.
        """
        _yaml = YAML(typ="safe")
        index: dict[str, MissionType] = {}
        if not directory.is_dir():
            return index

        for yaml_file in sorted(directory.glob("*.yaml")):
            raw: Any = _yaml.load(yaml_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError(
                    f"Expected a YAML mapping in {yaml_file}; got {type(raw).__name__}"
                )
            mission_type = MissionType.model_validate(raw)
            expected_id = yaml_file.stem
            if mission_type.id != expected_id:
                raise ValueError(
                    f"MissionType id {mission_type.id!r} in {yaml_file.name} "
                    f"does not match filename stem {expected_id!r}. "
                    "Rename the file or correct the id field."
                )
            index[mission_type.id] = mission_type

        return index
