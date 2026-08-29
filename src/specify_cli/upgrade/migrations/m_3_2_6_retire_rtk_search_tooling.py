"""Migration m_3_2_6_retire_rtk_search_tooling: drop a retired toolguide activation.

Operator ruling 2026-07-28 removed the ``rtk-search-tooling`` toolguide outright:
the artefact, its guide, its DRG node, and its entry in the shipped default
charter pack (``src/charter/packs/default.yaml``) are all gone. RTK will not be
pushed to the userbase.

Why a migration is required
---------------------------
``m_3_2_0rc35_default_charter_pack`` copied the default pack's
``activated_toolguides`` **verbatim** into every upgraded project's
``.kittify/config.yaml``, and — by design — writes only *absent* keys. A later
upgrade therefore never removes a stale member from an already-present key. So
every project that passed through rc35 still names ``rtk-search-tooling`` in
``activated_toolguides`` while the artefact no longer exists on disk.

The charter compiler is deliberately fail-closed: ``charter.activation.compiler`` raises
:class:`charter.activation.kind_vocabulary.UnknownArtifactIdError` rather than silently
dropping an unresolvable stem, and that raise is not caught on the compile
path. The observed consequence is a hard failure::

    UnknownArtifactIdError: No toolguide artifact with config ID
    'rtk-search-tooling' found under doctrine root src/doctrine.

This migration is the unmanaged-retirement backstop: it removes the stale
activation from ``config.yaml`` and also strips the two compiled blocks in
``.kittify/charter/`` (``charter.yaml`` and ``references.yaml``) that would
otherwise be left naming a deleted ``source_path``.

Scope
-----
Three project files, each optional:

* ``.kittify/config.yaml``            — ``activated_toolguides`` list member
* ``.kittify/charter/charter.yaml``   — ``catalog`` reference block + ``activated_toolguides`` member
* ``.kittify/charter/references.yaml``— ``references`` reference block

Nothing is ever created: a project that lacks any of these files (or lacks the
entry) is left untouched. No directory is created by this migration.

Idempotency
-----------
Every removal is conditional on the entry being present, so a second run finds
nothing to do and returns ``success=True`` with the "already absent" note.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

#: Config/file-stem id of the retired toolguide, as it appears in
#: ``activated_toolguides`` in both ``config.yaml`` and ``charter.yaml``.
RETIRED_TOOLGUIDE_STEM = "rtk-search-tooling"

#: Catalog/reference block id of the same artefact, as compiled into
#: ``.kittify/charter/charter.yaml`` (``catalog``) and ``references.yaml``.
RETIRED_TOOLGUIDE_REFERENCE_ID = f"TOOLGUIDE:{RETIRED_TOOLGUIDE_STEM}"

_ACTIVATION_KEY = "activated_toolguides"

_CONFIG_RELATIVE_PATH = Path(".kittify") / "config.yaml"
_CHARTER_RELATIVE_PATH = Path(".kittify") / "charter" / "charter.yaml"
_REFERENCES_RELATIVE_PATH = Path(".kittify") / "charter" / "references.yaml"


def _round_trip_yaml() -> YAML:
    """Return a round-trip parser that preserves comments and quoting."""
    yaml = YAML()
    yaml.preserve_quotes = True
    return yaml


def _load_mapping(path: Path) -> dict[str, Any] | None:
    """Round-trip load *path* as a mapping; ``None`` when absent/unreadable/not a mapping."""
    if not path.exists():
        return None
    try:
        data = _round_trip_yaml().load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a malformed project file is skipped, never fatal
        return None
    return data if isinstance(data, dict) else None


def _has_activation(data: dict[str, Any]) -> bool:
    """True when *data* carries the retired stem in ``activated_toolguides``."""
    values = data.get(_ACTIVATION_KEY)
    return isinstance(values, list) and RETIRED_TOOLGUIDE_STEM in values


def _has_reference_block(data: dict[str, Any], list_key: str) -> bool:
    """True when *data*'s *list_key* holds a block whose ``id`` is the retired artefact."""
    blocks = data.get(list_key)
    if not isinstance(blocks, list):
        return False
    return any(
        isinstance(block, dict) and block.get("id") == RETIRED_TOOLGUIDE_REFERENCE_ID
        for block in blocks
    )


def _drop_activation(data: dict[str, Any]) -> bool:
    """Remove the retired stem from ``activated_toolguides``; True when something changed."""
    values = data.get(_ACTIVATION_KEY)
    if not isinstance(values, list):
        return False
    removed = False
    # Remove every occurrence — a hand-edited config can carry duplicates.
    while RETIRED_TOOLGUIDE_STEM in values:
        values.remove(RETIRED_TOOLGUIDE_STEM)
        removed = True
    return removed


def _drop_reference_block(data: dict[str, Any], list_key: str) -> bool:
    """Remove the retired artefact's block from *list_key*; True when something changed."""
    blocks = data.get(list_key)
    if not isinstance(blocks, list):
        return False
    stale_indexes = [
        index
        for index, block in enumerate(blocks)
        if isinstance(block, dict) and block.get("id") == RETIRED_TOOLGUIDE_REFERENCE_ID
    ]
    for index in reversed(stale_indexes):
        del blocks[index]
    return bool(stale_indexes)


def _write(path: Path, data: dict[str, Any]) -> None:
    """Write *data* back to *path* in round-trip form (the file already exists)."""
    with path.open("w", encoding="utf-8") as handle:
        _round_trip_yaml().dump(data, handle)


#: What the retired artefact can look like in a project surface. ``activation``
#: means a plain string member of an ``activated_<kind>`` list; ``block`` means
#: a compiled reference mapping identified by its ``id`` field.
_ACTIVATION_SHAPE = "activation"
_BLOCK_SHAPE = "block"

#: Every project surface that can name the retired toolguide, with the shapes
#: to look for in each. Shared by :meth:`detect` and :meth:`apply` so the two
#: can never disagree about what counts as stale.
_SURFACES: tuple[tuple[Path, tuple[tuple[str, str], ...]], ...] = (
    (_CONFIG_RELATIVE_PATH, ((_ACTIVATION_SHAPE, _ACTIVATION_KEY),)),
    (
        _CHARTER_RELATIVE_PATH,
        ((_ACTIVATION_SHAPE, _ACTIVATION_KEY), (_BLOCK_SHAPE, "catalog")),
    ),
    (_REFERENCES_RELATIVE_PATH, ((_BLOCK_SHAPE, "references"),)),
)


def _is_present(data: dict[str, Any], shape: str, key: str) -> bool:
    """True when *data* still names the retired artefact in the given *shape*."""
    if shape == _ACTIVATION_SHAPE:
        return _has_activation(data)
    return _has_reference_block(data, key)


def _remove(data: dict[str, Any], shape: str, key: str) -> bool:
    """Remove the retired artefact in the given *shape*; True when *data* changed."""
    if shape == _ACTIVATION_SHAPE:
        return _drop_activation(data)
    return _drop_reference_block(data, key)


@MigrationRegistry.register
class RetireRtkSearchToolingMigration(BaseMigration):
    """Remove the retired ``rtk-search-tooling`` toolguide from project charter surfaces.

    Without this, charter compilation hard-fails with ``UnknownArtifactIdError``
    on every project that received the entry from the rc35 default-pack write.
    """

    migration_id = "3.2.6_retire_rtk_search_tooling"
    description = (
        "Remove the retired rtk-search-tooling toolguide from "
        ".kittify/config.yaml and the compiled .kittify/charter/ blocks so "
        "charter compilation stops failing on the deleted artefact."
    )
    target_version = "3.2.6rc1"

    def detect(self, project_path: Path) -> bool:
        """Return True when any project surface still names the retired toolguide."""
        for relative_path, shapes in _SURFACES:
            data = _load_mapping(project_path / relative_path)
            if data is None:
                continue
            if any(_is_present(data, shape, key) for shape, key in shapes):
                return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Only applicable when at least one stale mention survives."""
        if self.detect(project_path):
            return True, ""
        return False, "rtk-search-tooling is not activated in this project"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Strip the retired toolguide from every project surface that still names it."""
        changes: list[str] = []
        errors: list[str] = []

        for relative_path, shapes in _SURFACES:
            path = project_path / relative_path
            data = _load_mapping(path)
            if data is None:
                continue

            touched_keys = [key for shape, key in shapes if _remove(data, shape, key)]
            if not touched_keys:
                continue

            rel = relative_path.as_posix()
            if dry_run:
                changes.extend(
                    f"Would remove {RETIRED_TOOLGUIDE_STEM} from {rel} ({key})"
                    for key in touched_keys
                )
                continue

            try:
                _write(path, data)
            except OSError as exc:
                errors.append(f"Failed writing {rel}: {exc}")
                continue
            changes.extend(
                f"Removed {RETIRED_TOOLGUIDE_STEM} from {rel} ({key})"
                for key in touched_keys
            )

        if not changes and not errors:
            changes.append(f"{RETIRED_TOOLGUIDE_STEM} already absent; nothing to remove")

        return MigrationResult(
            success=not errors,
            changes_made=changes,
            errors=errors,
        )
