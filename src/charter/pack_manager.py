"""Charter pack activation manager (FR-001, FR-002).

Provides ``CharterPackManager`` — the single interface for activating and
deactivating doctrine artifacts in a project's ``.kittify/config.yaml``.

All mutating methods use ``ruamel.yaml`` round-trip mode so that existing
comments and formatting in ``config.yaml`` are preserved across writes.

Key constants
-------------
``YAML_KEY_MAP`` — maps CLI kind names (hyphenated) to ``config.yaml`` YAML
keys.  The outlier is ``mission-type`` → ``mission_type_activations`` (not
``activated_mission_types``).  All other kinds follow the ``activated_<plural>``
pattern.

Cascade deferral (FR-006/007)
------------------------------
``activate()`` and ``deactivate()`` accept ``cascade=True`` but DRG edge
traversal is **not** implemented in this WP.  A warning is emitted when
``cascade=True`` is passed.  FR-008 (warn on no-cascade) is satisfied by
this warning; FR-006 and FR-007 are explicitly deferred to a follow-on
mission.  This is intentional scope control, not a defect.

Layer rule
----------
This module MUST NOT import from ``specify_cli`` (C-001, hard ratchet pinned
by ``tests/architectural/test_layer_rules.py``).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML

if TYPE_CHECKING:
    from charter.invocation_context import ProjectContext

__all__ = [
    "ActivationResult",
    "CharterPackManager",
    "MergeResult",
    "YAML_KEY_MAP",
]

# ---------------------------------------------------------------------------
# YAML_KEY_MAP
# ---------------------------------------------------------------------------

#: Maps CLI kind names (hyphenated) to ``config.yaml`` YAML keys.
#: The ``mission-type`` → ``mission_type_activations`` mapping is the outlier:
#: it does NOT follow the ``activated_*`` pattern.  All other kinds do.
YAML_KEY_MAP: dict[str, str] = {
    "mission-type":           "mission_type_activations",
    "directive":              "activated_directives",
    "tactic":                 "activated_tactics",
    "styleguide":             "activated_styleguides",
    "toolguide":              "activated_toolguides",
    "paradigm":               "activated_paradigms",
    "procedure":              "activated_procedures",
    "agent-profile":          "activated_agent_profiles",
    "mission-step-contract":  "activated_mission_step_contracts",
}

# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass
class ActivationResult:
    """Result of a single activate() or deactivate() operation."""

    activated: list[str] = field(default_factory=list)
    deactivated: list[str] = field(default_factory=list)
    cascade_activated: dict[str, list[str]] = field(default_factory=dict)
    cascade_deactivated: dict[str, list[str]] = field(default_factory=dict)
    skipped_shared: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MergeResult:
    """Result of a merge_defaults() operation."""

    kinds_written: list[str] = field(default_factory=list)
    backup_path: Path | None = None
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_DEFAULT_PACK_PATH = Path(__file__).parent / "packs" / "default.yaml"

#: Maps CLI kind names to (doctrine_relative_dir, filename_suffix) tuples.
#: The ``relative_dir`` is relative to ``src/`` (i.e. the parent of the
#: ``charter`` package root).
_KIND_TO_DOCTRINE_DIR: dict[str, tuple[str, str]] = {
    "directive":             ("doctrine/directives/built-in", ".directive.yaml"),
    "tactic":                ("doctrine/tactics/built-in", ".tactic.yaml"),
    "styleguide":            ("doctrine/styleguides/built-in", ".styleguide.yaml"),
    "toolguide":             ("doctrine/toolguides/built-in", ".toolguide.yaml"),
    "paradigm":              ("doctrine/paradigms/built-in", ".paradigm.yaml"),
    "procedure":             ("doctrine/procedures/built-in", ".procedure.yaml"),
    "agent-profile":         ("doctrine/agent_profiles/built-in", ".agent.yaml"),
    "mission-type":          ("doctrine/missions/mission_types", ".yaml"),
    "mission-step-contract": (
        "doctrine/missions/built_in_step_contracts", ".step-contract.yaml"
    ),
}


def _load_config(config_path: Path) -> tuple[Any, YAML]:
    """Load config.yaml using ruamel.yaml round-trip mode.

    Returns (data_dict_or_empty_dict, yaml_instance).
    If the file does not exist, returns ({}, yaml_instance).
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.load(fh)
    else:
        data = {}
    if data is None:
        data = {}
    return data, yaml


def _save_config(config_path: Path, data: Any, yaml: YAML) -> None:
    """Write data back to config_path, creating parent dirs as needed."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


def _load_default_pack() -> dict[str, list[str]]:
    """Load the built-in default pack IDs from the shipped default.yaml."""
    import yaml as _yaml  # type: ignore[import-untyped]  # PyYAML stubs optional

    with _DEFAULT_PACK_PATH.open("r", encoding="utf-8") as fh:
        raw: Any = _yaml.safe_load(fh)
    if not isinstance(raw, dict):
        return {}
    return {k: list(v) for k, v in raw.items() if isinstance(v, list)}


# ---------------------------------------------------------------------------
# CharterPackManager
# ---------------------------------------------------------------------------


class CharterPackManager:
    """Manages activation/deactivation of doctrine artifacts in a project's charter pack.

    All methods read from and write to ``.kittify/config.yaml`` using
    ``ruamel.yaml`` round-trip mode (comments and formatting preserved).
    """

    def activate(
        self,
        ctx: ProjectContext,
        kind: str,
        artifact_id: str,
        *,
        cascade: bool = False,
    ) -> ActivationResult:
        """Activate ``artifact_id`` for ``kind`` in the project charter pack.

        If the kind has no explicit activation set in ``config.yaml``, the
        default pack is materialized first (all built-in IDs for the kind are
        written), then ``artifact_id`` is appended.

        Parameters
        ----------
        ctx:
            Project context providing access to the repository root.
        kind:
            CLI kind name (e.g. ``"directive"``, ``"mission-type"``).
        artifact_id:
            Artifact ID to activate (e.g. ``"001-architectural-integrity-standard"``).
        cascade:
            Accepted but DRG edge traversal is deferred to a follow-on mission.
            A warning is emitted when ``True``.

        Returns
        -------
        ActivationResult
            Contains activated IDs, warnings, and cascade info.

        Raises
        ------
        ValueError
            If ``kind`` is not in ``YAML_KEY_MAP``.
        """
        repo_root = ctx.require_repo_root()
        config_path = repo_root / ".kittify" / "config.yaml"

        if kind not in YAML_KEY_MAP:
            raise ValueError(
                f"Unknown activation kind '{kind}'. "
                f"Valid kinds: {sorted(YAML_KEY_MAP)}"
            )

        yaml_key = YAML_KEY_MAP[kind]
        data, yaml_inst = _load_config(config_path)
        result = ActivationResult()

        # Materialize from default pack if this kind is absent
        if yaml_key not in data or data[yaml_key] is None:
            default_pack = _load_default_pack()
            default_ids: list[str] = default_pack.get(yaml_key, [])
            data[yaml_key] = list(default_ids)
            result.warnings.append(
                f"Kind '{kind}' had no explicit activation set. "
                f"Initialized from default pack ({len(default_ids)} entries)."
            )

        current: list[str] = list(data[yaml_key])
        if artifact_id not in current:
            current.append(artifact_id)
            data[yaml_key] = current
            result.activated.append(artifact_id)
        else:
            result.warnings.append(
                f"'{artifact_id}' is already activated for kind '{kind}'."
            )

        # Cascade: DRG edge traversal deferred to follow-on mission.
        if cascade:
            result.warnings.append(
                "cascade=True requested but DRG edge traversal is not yet implemented "
                "(deferred to follow-on mission). Manual activation of cross-kind "
                "dependencies may be required."
            )

        _save_config(config_path, data, yaml_inst)
        return result

    def deactivate(
        self,
        ctx: ProjectContext,
        kind: str,
        artifact_id: str,
        *,
        cascade: bool = False,
    ) -> ActivationResult:
        """Deactivate ``artifact_id`` for ``kind`` in the project charter pack.

        Parameters
        ----------
        ctx:
            Project context providing access to the repository root.
        kind:
            CLI kind name (e.g. ``"directive"``).
        artifact_id:
            Artifact ID to deactivate.
        cascade:
            Accepted but DRG shared-reference analysis is deferred.
            A warning is emitted when ``True``.

        Returns
        -------
        ActivationResult
            Contains deactivated IDs and warnings.

        Raises
        ------
        ValueError
            If ``kind`` is not in ``YAML_KEY_MAP``.
        SystemExit(1)
            If the kind has no explicit activation set (None-state). The
            operator must run ``spec-kitty upgrade`` first.
        """
        repo_root = ctx.require_repo_root()
        config_path = repo_root / ".kittify" / "config.yaml"

        if kind not in YAML_KEY_MAP:
            raise ValueError(
                f"Unknown activation kind '{kind}'. "
                f"Valid kinds: {sorted(YAML_KEY_MAP)}"
            )

        yaml_key = YAML_KEY_MAP[kind]
        data, yaml_inst = _load_config(config_path)
        result = ActivationResult()

        if yaml_key not in data or data[yaml_key] is None:
            # None-state: the project has not been upgraded to the pack model.
            # Modifying individual activations is unsafe without a known baseline.
            print(
                f"Error: Kind '{kind}' has no explicit activation set. "
                f"Run 'spec-kitty upgrade' to initialize the default pack "
                f"before modifying individual activations.",
                file=sys.stderr,
            )
            sys.exit(1)

        current: list[str] = list(data[yaml_key])

        if artifact_id not in current:
            result.warnings.append(
                f"'{artifact_id}' is not in the activation set for kind '{kind}'. "
                f"Nothing to deactivate."
            )
            return result

        current.remove(artifact_id)
        data[yaml_key] = current
        result.deactivated.append(artifact_id)

        # Cascade: DRG shared-reference analysis deferred to follow-on mission.
        if cascade:
            result.warnings.append(
                "cascade=True requested but DRG shared-reference analysis is not yet "
                "implemented (deferred to follow-on mission). Cross-kind cascade "
                "deactivation was skipped."
            )

        _save_config(config_path, data, yaml_inst)
        return result

    def list_activated(
        self,
        ctx: ProjectContext,
    ) -> dict[str, frozenset[str] | None]:
        """Return activated artifact IDs keyed by CLI kind name.

        A ``None`` value means the kind has no explicit activation set
        in ``config.yaml`` (the project has not yet been upgraded to
        the pack-based model for that kind).

        Parameters
        ----------
        ctx:
            Project context providing access to the repository root.

        Returns
        -------
        dict[str, frozenset[str] | None]
            Mapping of CLI kind name to activated IDs (or ``None``).
        """
        repo_root = ctx.require_repo_root()
        config_path = repo_root / ".kittify" / "config.yaml"
        data, _ = _load_config(config_path)

        result: dict[str, frozenset[str] | None] = {}
        for kind, yaml_key in YAML_KEY_MAP.items():
            raw = data.get(yaml_key)
            if raw is None:
                result[kind] = None
            else:
                result[kind] = frozenset(str(item) for item in raw)
        return result

    def list_available(
        self,
        ctx: ProjectContext,  # noqa: ARG002 — reserved for future org-pack support
        kind: str,
    ) -> frozenset[str]:
        """Return all artifact IDs available in doctrine for ``kind``.

        Scans the built-in doctrine filesystem for files matching the
        kind's suffix pattern and returns their stem IDs.

        Parameters
        ----------
        ctx:
            Project context (unused for filesystem scanning but kept for
            consistency and future org-pack support).
        kind:
            CLI kind name (e.g. ``"directive"``).

        Returns
        -------
        frozenset[str]
            Set of available artifact IDs.  Empty if the doctrine directory
            does not exist.

        Raises
        ------
        ValueError
            If ``kind`` is not in ``_KIND_TO_DOCTRINE_DIR``.
        """
        if kind not in _KIND_TO_DOCTRINE_DIR:
            raise ValueError(
                f"Unknown activation kind '{kind}'. "
                f"Valid kinds: {sorted(_KIND_TO_DOCTRINE_DIR)}"
            )

        rel_dir, suffix = _KIND_TO_DOCTRINE_DIR[kind]
        # Doctrine is installed alongside the charter package in src/
        src_root = Path(__file__).parent.parent  # src/charter/.. → src/
        doctrine_dir = src_root / rel_dir

        if not doctrine_dir.is_dir():
            return frozenset()

        ids: set[str] = set()
        for yaml_file in doctrine_dir.rglob(f"*{suffix}"):
            # Strip the suffix to get the ID
            stem = yaml_file.name[: -len(suffix)]
            ids.add(stem)
        return frozenset(ids)

    def merge_defaults(
        self,
        ctx: ProjectContext,
    ) -> MergeResult:
        """Merge the default pack into ``config.yaml`` for all absent kinds.

        Only absent keys are written; present keys are not overwritten.
        If ``.kittify/charter/charter.md`` exists it is backed up before
        any write.

        Parameters
        ----------
        ctx:
            Project context providing access to the repository root.

        Returns
        -------
        MergeResult
            Contains kinds written, backup path (if any), and warnings.
        """
        from datetime import UTC, datetime

        repo_root = ctx.require_repo_root()
        config_path = repo_root / ".kittify" / "config.yaml"
        charter_path = repo_root / ".kittify" / "charter" / "charter.md"

        result = MergeResult()

        # Backup charter.md if it exists before any write
        if charter_path.exists():
            ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
            backup_dir = repo_root / ".kittify" / "charter" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"charter-{ts}.md"
            backup_path.write_bytes(charter_path.read_bytes())
            result.backup_path = backup_path

        data, yaml_inst = _load_config(config_path)
        default_pack = _load_default_pack()

        for yaml_key in YAML_KEY_MAP.values():
            if yaml_key not in data or data[yaml_key] is None:
                default_ids = default_pack.get(yaml_key, [])
                data[yaml_key] = list(default_ids)
                # Map yaml_key back to CLI kind for the result
                kind = next(k for k, v in YAML_KEY_MAP.items() if v == yaml_key)
                result.kinds_written.append(kind)

        if result.kinds_written:
            _save_config(config_path, data, yaml_inst)

        return result
