"""Kernel-level schema loading utilities.

Canonical home for :class:`SchemaUtilities`. The kernel layer is the lowest
architectural layer (per ADR 2026-03-27-1, ``kernel ← doctrine ← charter ←
specify_cli``); ``SchemaUtilities`` is a generic JSON-Schema helper that does
not belong behind a charter facade because it is not doctrine-domain logic —
it merely loads schema files packaged under ``doctrine.schemas``.

Promotion rationale (mission ``charter-mediated-doctrine-selection-01KRTZCA``,
WP07): ``src/specify_cli/bulk_edit/occurrence_map.py`` is the only runtime
consumer. Routing it through a charter facade would model a generic helper as
doctrine-domain surface; promoting to kernel keeps the boundary honest.

The doctrine subpackage ``doctrine.shared.schema_utils`` re-exports
:class:`SchemaUtilities` from this module so existing doctrine internals
(``directives.validation``, ``tactics.validation``, etc.) continue to import
from their historical path without churn.

This module reads files via ``importlib.resources`` (``doctrine.schemas``)
in installed wheels and falls back to a relative filesystem path in dev
checkouts. The resource lookup does NOT import the ``doctrine`` Python
package — ``importlib.resources.files("doctrine.schemas")`` only requires the
package to be importable as a resource container, and in practice the schema
directory is colocated with the doctrine sources. This preserves the kernel
layer invariant (no top-level imports of ``doctrine``).
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class SchemaUtilities:
    """Utilities for loading and caching JSON Schemas packaged with doctrine.

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
    then falls back to a path computed relative to the doctrine package's
    schema directory (development layout).

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
        # Dev-checkout fallback: schemas live two levels up under doctrine/schemas/.
        # This module lives at src/kernel/schema_utils.py and the schemas
        # directory is at src/doctrine/schemas/.
        return Path(__file__).resolve().parent.parent / "doctrine" / "schemas" / filename


__all__ = ["SchemaUtilities"]
