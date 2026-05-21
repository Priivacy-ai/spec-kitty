"""Inventory loader for ``scripts/docs`` tooling.

Loads ``PageInventoryEntry`` rows from a YAML manifest using ``ruamel.yaml``
and validates each row against the invariants documented in
``kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/data-model.md``.

The data model intentionally uses ``@dataclass(slots=True, frozen=True)``
so loaded rows are immutable; downstream tools must rebuild rather than
mutate in place. Errors during parsing or validation are surfaced as a
:class:`LoadError` so the CLI can map them to exit code ``2`` per the
``version_leakage_check`` contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

__all__ = [
    "DivioType",
    "LoadError",
    "PageInventoryEntry",
    "VersionTag",
    "load_inventory",
]


class VersionTag(StrEnum):
    """Canonical version-relevance classification (FR-001)."""

    CURRENT = "current"
    SUPPORTED = "supported"
    ARCHIVAL = "archival"
    MIGRATION = "migration"
    INTERNAL = "internal"


class DivioType(StrEnum):
    """Divio documentation classification."""

    TUTORIAL = "tutorial"
    HOW_TO = "how-to"
    REFERENCE = "reference"
    EXPLANATION = "explanation"
    NONE = "none"


@dataclass(slots=True, frozen=True)
class PageInventoryEntry:
    """One row of ``docs/development/3-2-page-inventory.yaml``."""

    path: str
    tag: VersionTag
    divio_type: DivioType
    owning_workstream: str
    current_target: bool
    citation_refs: tuple[str, ...]
    notes: str | None


class LoadError(Exception):
    """Raised when the inventory cannot be loaded or validated.

    The CLI converts this to exit code ``2`` (input error).
    """


_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "path",
        "tag",
        "divio_type",
        "owning_workstream",
        "current_target",
        "citation_refs",
    }
)


def load_inventory(inventory_path: Path) -> list[PageInventoryEntry]:
    """Load and validate a ``PageInventoryEntry`` list from YAML.

    Parameters
    ----------
    inventory_path:
        Path to the inventory manifest. Must exist and be readable.

    Returns
    -------
    list[PageInventoryEntry]
        Validated entries in source order.

    Raises
    ------
    LoadError
        If the file is missing, unreadable, malformed YAML, or contains
        rows that violate the validation invariants in ``data-model.md``.
    """
    if not inventory_path.exists():
        raise LoadError(f"Inventory file not found: {inventory_path}")
    if not inventory_path.is_file():
        raise LoadError(f"Inventory path is not a file: {inventory_path}")

    yaml = YAML(typ="safe")
    try:
        with inventory_path.open("r", encoding="utf-8") as handle:
            raw: Any = yaml.load(handle)
    except YAMLError as exc:
        raise LoadError(f"Malformed YAML in {inventory_path}: {exc}") from exc
    except OSError as exc:
        raise LoadError(f"Could not read {inventory_path}: {exc}") from exc

    if raw is None:
        return []
    if not isinstance(raw, list):
        raise LoadError(
            f"Inventory root must be a list of rows, got {type(raw).__name__}"
        )

    entries: list[PageInventoryEntry] = []
    for index, row in enumerate(raw):
        entries.append(_validate_row(row, index, inventory_path))
    return entries


def _validate_row(
    row: Any, index: int, inventory_path: Path
) -> PageInventoryEntry:
    """Validate one raw YAML row and return a :class:`PageInventoryEntry`."""
    if not isinstance(row, dict):
        raise LoadError(
            f"{inventory_path}: row {index} must be a mapping, "
            f"got {type(row).__name__}"
        )

    missing = _REQUIRED_KEYS - set(row.keys())
    if missing:
        raise LoadError(
            f"{inventory_path}: row {index} missing keys: "
            f"{sorted(missing)}"
        )

    path_value = row["path"]
    if not isinstance(path_value, str) or not path_value:
        raise LoadError(
            f"{inventory_path}: row {index} 'path' must be a non-empty string"
        )

    try:
        tag = VersionTag(row["tag"])
    except ValueError as exc:
        raise LoadError(
            f"{inventory_path}: row {index} ({path_value}) "
            f"invalid tag: {row['tag']!r}"
        ) from exc

    try:
        divio_type = DivioType(row["divio_type"])
    except ValueError as exc:
        raise LoadError(
            f"{inventory_path}: row {index} ({path_value}) "
            f"invalid divio_type: {row['divio_type']!r}"
        ) from exc

    owning_workstream = row["owning_workstream"]
    if not isinstance(owning_workstream, str) or not owning_workstream:
        raise LoadError(
            f"{inventory_path}: row {index} ({path_value}) "
            f"'owning_workstream' must be a non-empty string"
        )

    current_target = row["current_target"]
    if not isinstance(current_target, bool):
        raise LoadError(
            f"{inventory_path}: row {index} ({path_value}) "
            f"'current_target' must be a boolean"
        )

    refs_raw = row["citation_refs"]
    if not isinstance(refs_raw, list) or not all(
        isinstance(item, str) for item in refs_raw
    ):
        raise LoadError(
            f"{inventory_path}: row {index} ({path_value}) "
            f"'citation_refs' must be a list of strings"
        )
    citation_refs = tuple(refs_raw)

    notes_raw = row.get("notes")
    if notes_raw is not None and not isinstance(notes_raw, str):
        raise LoadError(
            f"{inventory_path}: row {index} ({path_value}) "
            f"'notes' must be a string or null"
        )

    # Cross-field invariants from data-model.md §PageInventoryEntry.
    if tag is VersionTag.ARCHIVAL and current_target:
        raise LoadError(
            f"{inventory_path}: row {index} ({path_value}) "
            f"archival pages must have current_target=false"
        )
    if tag is VersionTag.CURRENT and not current_target:
        raise LoadError(
            f"{inventory_path}: row {index} ({path_value}) "
            f"current pages must have current_target=true"
        )

    return PageInventoryEntry(
        path=path_value,
        tag=tag,
        divio_type=divio_type,
        owning_workstream=owning_workstream,
        current_target=current_target,
        citation_refs=citation_refs,
        notes=notes_raw,
    )
