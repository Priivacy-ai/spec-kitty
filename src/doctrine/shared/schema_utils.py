"""Shared schema loading utilities for doctrine artifact validation."""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class SchemaUtilities:
    """Utilities for loading and caching doctrine JSON Schemas.

    All schemas live in ``src/doctrine/schemas/`` and follow the naming
    convention ``<artifact-type>.schema.yaml`` (e.g. ``directive.schema.yaml``).

    Usage::

        schema = SchemaUtilities.load_schema("directive")
    """

    @staticmethod
    @cache
    def load_schema(name: str) -> dict[str, Any]:
        """Load a doctrine JSON schema by artifact type name.

        Tries ``importlib.resources`` first (installed wheel), then falls back to
        the relative filesystem path used in development checkouts.

        Args:
            name: Schema stem without extension, e.g. ``"directive"``, ``"tactic"``.

        Returns:
            Parsed schema dict ready for use with ``jsonschema`` validators.

        Raises:
            FileNotFoundError: If the schema file cannot be found via either path.
        """
        filename = f"{name}.schema.yaml"
        schema_path = _resolve_schema_path(filename)
        yaml = YAML(typ="safe")
        with schema_path.open() as f:
            schema_data: dict[str, Any] = yaml.load(f)
        return schema_data


def _resolve_schema_path(filename: str) -> Path:
    """Resolve the filesystem path for a schema file.

    Tries the importlib.resources API first (correct for installed packages),
    then falls back to a path relative to this file (development layout).

    Args:
        filename: Schema filename, e.g. ``"directive.schema.yaml"``.

    Returns:
        Resolved :class:`~pathlib.Path` to the schema file.
    """
    try:
        resource = files("doctrine.schemas")
        if hasattr(resource, "joinpath"):
            return Path(str(resource.joinpath(filename)))
        return Path(str(resource)) / filename
    except (ModuleNotFoundError, AttributeError, TypeError):
        return Path(__file__).parent.parent / "schemas" / filename
