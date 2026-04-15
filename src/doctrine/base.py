"""Generic two-source loading base class for all doctrine asset repositories.

All seven doctrine sub-repositories share an identical ``_load()`` pattern:
walk a shipped YAML directory (rglob), optionally walk a project override
directory (glob), parse each file with Pydantic ``model_validate``, merge
project overrides into shipped instances at field level, and warn on bad
files.  ``BaseDoctrineRepository[T]`` captures that pattern once.

Subclasses declare:

- ``_schema`` — the Pydantic model class (abstract property)
- ``_glob``   — the YAML file glob pattern, e.g. ``"*.paradigm.yaml"``
  (abstract property)

Subclasses may override:

- ``_key(obj)``             — extract the dict key; default is ``obj.id``
- ``_pre_validate(data, f)`` — hook called before ``model_validate``; default
  is a no-op.  Use it for inline-ref rejection or other pre-checks.
- ``_project_scan(dir)``    — return the list of project YAML files; default
  is a non-recursive ``glob``.  Override with ``rglob`` for repos that allow
  subdirectory structure in the project layer (e.g. styleguides).
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from doctrine.shared.scoping import applies_to_languages_match, normalize_languages

T = TypeVar("T", bound=BaseModel)


class BaseDoctrineRepository(ABC, Generic[T]):
    """Abstract base for all doctrine asset repositories.

    Provides the two-source loading pattern (shipped rglob + project glob)
    with field-level merge semantics and warning emission on bad files.
    """

    def __init__(
        self,
        shipped_dir: Path,
        project_dir: Path | None = None,
        active_languages: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        self._shipped_dir = shipped_dir
        self._project_dir = project_dir
        self._active_languages = None if active_languages is None else normalize_languages(active_languages)
        self._items: dict[str, T] = {}
        self._load()

    # ------------------------------------------------------------------ #
    # Abstract interface — subclasses must implement these                 #
    # ------------------------------------------------------------------ #

    @property
    @abstractmethod
    def _schema(self) -> type[T]:
        """Pydantic model class for this repository's asset type."""
        ...

    @property
    @abstractmethod
    def _glob(self) -> str:
        """YAML file glob pattern, e.g. ``"*.paradigm.yaml"``."""
        ...

    # ------------------------------------------------------------------ #
    # Virtual hooks — subclasses may override                              #
    # ------------------------------------------------------------------ #

    def _pre_validate(self, data: dict[str, Any], yaml_file: Path) -> None:
        """Called on raw YAML data before ``model_validate``. Default: no-op.

        Override to add inline-ref rejection or other pre-checks.
        """

    def _key(self, obj: T) -> str:
        """Extract the dict key for a loaded asset. Default: ``obj.id``."""
        return obj.id  # type: ignore[attr-defined, no-any-return]

    def _project_scan(self, project_dir: Path) -> list[Path]:
        """Return the project YAML files to load. Default: non-recursive glob.

        Override with ``rglob`` for repos that support subdirectories in the
        project layer (e.g. ``styleguides/writing/*.styleguide.yaml``).
        """
        return sorted(project_dir.glob(self._glob))

    def _include_item(self, obj: T) -> bool:
        """Return whether a loaded asset applies to the active language scope."""
        return applies_to_languages_match(
            getattr(obj, "applies_to_languages", None),
            self._active_languages,
        )

    # ------------------------------------------------------------------ #
    # Concrete implementation                                              #
    # ------------------------------------------------------------------ #

    @property
    def _kind(self) -> str:
        """Human-readable asset kind derived from the class name."""
        return type(self).__name__.removesuffix("Repository").lower()

    def _load(self) -> None:
        """Walk shipped + project dirs, parse, merge, warn on failure."""
        yaml_parser = YAML(typ="safe")
        schema = self._schema
        glob = self._glob
        shipped: dict[str, T] = {}

        if self._shipped_dir.exists():
            for yaml_file in sorted(self._shipped_dir.rglob(glob)):
                try:
                    data = yaml_parser.load(yaml_file)
                    if data is None:
                        continue
                    self._pre_validate(data, yaml_file)
                    obj = schema.model_validate(data)
                    if not self._include_item(obj):
                        continue
                    shipped[self._key(obj)] = obj
                except (YAMLError, ValidationError, OSError) as exc:
                    warnings.warn(
                        f"Skipping invalid shipped {self._kind} "
                        f"{yaml_file.name}: {exc}",
                        UserWarning,
                        stacklevel=2,
                    )

        self._items = shipped.copy()

        if self._project_dir and self._project_dir.exists():
            for yaml_file in self._project_scan(self._project_dir):
                try:
                    data = yaml_parser.load(yaml_file)
                    if data is None:
                        continue
                    self._pre_validate(data, yaml_file)
                    item_id = data.get("id")
                    if not item_id:
                        warnings.warn(
                            f"Skipping project {self._kind} "
                            f"{yaml_file.name}: no id",
                            UserWarning,
                            stacklevel=2,
                        )
                        continue
                    if item_id in shipped:
                        merged = self._merge(shipped[item_id], data)
                        if not self._include_item(merged):
                            continue
                        self._items[item_id] = merged
                    else:
                        obj = schema.model_validate(data)
                        if not self._include_item(obj):
                            continue
                        self._items[self._key(obj)] = obj
                except (YAMLError, ValidationError, OSError) as exc:
                    warnings.warn(
                        f"Skipping invalid project {self._kind} "
                        f"{yaml_file.name}: {exc}",
                        UserWarning,
                        stacklevel=2,
                    )

    def _merge(self, shipped: T, project_data: dict[str, Any]) -> T:
        """Merge project override into a shipped instance at field level."""
        merged = {**shipped.model_dump(), **project_data}
        return type(shipped).model_validate(merged)

    def list_all(self) -> list[T]:
        """Return all loaded assets sorted by key."""
        return sorted(self._items.values(), key=lambda obj: self._key(obj))

    def get(self, item_id: str) -> T | None:
        """Get asset by ID."""
        return self._items.get(item_id)


__all__ = ["BaseDoctrineRepository"]
