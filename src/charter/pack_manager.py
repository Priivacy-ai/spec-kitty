"""Charter pack activation manager (FR-001, FR-002, FR-026, FR-027).

Provides ``CharterPackManager`` — the single interface for activating and
deactivating doctrine artifacts in a project's ``.kittify/config.yaml`` and for
discovering which artifacts are *available* across the built-in, org-pack, and
project doctrine layers.

All mutating methods use ``ruamel.yaml`` round-trip mode so that existing
comments and formatting in ``config.yaml`` are preserved across writes.

Canonical kind vocabulary (FR-027, R-009)
-----------------------------------------
There is **no** second kind enumeration in this module. Kind validation routes
through :meth:`doctrine.artifact_kinds.ArtifactKind.from_operator_token` (the
single canonical resolver, WP01), and ``mission-type`` is the one charter-tier
token that is *not* an :class:`ArtifactKind` member (handled explicitly).

``YAML_KEY_MAP`` is **derived** from the canonical charter kind universe
(:data:`doctrine.artifact_kinds.CHARTER_KIND_TOKENS`): every kind maps to
``activated_<plural>`` except the ``mission-type`` outlier
(``mission_type_activations``).

Layer model (FR-026)
--------------------
``list_available`` scans the *built-in* layer plus any caller-supplied org /
project doctrine roots, returning artifact IDs taken from each artifact's
``id:`` field (not the filename stem). :meth:`list_available_detailed` exposes
the same scan annotated by source layer for ``charter list --all`` (WP16).

Org/project roots are passed in **as data** (C-008): ``specify_cli`` resolves
them and hands them to this module. This module MUST NOT import from
``specify_cli`` (C-001, hard ratchet pinned by
``tests/architectural/test_layer_rules.py``).

Activation seam (FR-011/012, NFR-003)
-------------------------------------
``activate()`` and ``deactivate()`` are thin wrappers over the pure
:mod:`charter.activation_engine` plan/commit seam (WP10): they load the config,
discover the available-ID universe, call ``plan_activation`` /
``plan_deactivation`` (which validate *before* computing any post-state), and
then perform the single ``commit_plan`` write. The legacy ``sys.exit(1)`` in
``deactivate`` is gone — the engine raises a typed
:class:`~charter.activation_engine.NoActivationRestrictionsError` that the CLI
(WP12) surfaces.

Cascade parameter (FR-006/007)
--------------------------------
``activate()`` and ``deactivate()`` accept a ``cascade`` parameter for
signature stability, but DRG edge traversal is owned by the CLI layer
(``charter.cascade``). **No warning is emitted** when ``cascade=True`` is
passed; the parameter is silently accepted and forwarded. FR-007 (cascade
execute) is a CLI-level concern — ``pack_manager`` does not interpret or act
on this flag.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from charter.activation_engine import (
    NoActivationRestrictionsError,
    UnknownActivationIdError,
    commit_plan,
    plan_activation,
    plan_deactivation,
)
from doctrine.artifact_kinds import (
    CHARTER_KIND_TOKENS,
    MISSION_TYPE_TOKEN,
    ArtifactKind,
    MissionTypeNotAnArtifactKind,
)

if TYPE_CHECKING:
    from charter.invocation_context import ProjectContext

__all__ = [
    "ActivationResult",
    "AvailableArtifact",
    "CharterPackManager",
    "MergeResult",
    "YAML_KEY_MAP",
]
# ``AvailableArtifact`` is exported now that ``charter list --all`` (WP16)
# imports it as a live ``src/`` consumer (it is the per-layer value object
# returned by ``list_available_detailed``). Before WP16 the symbol-level
# dead-code gate (tests/architectural/test_no_dead_symbols.py) required a live
# importer before the symbol could be exported; WP16 is that importer.

# ---------------------------------------------------------------------------
# Canonical kind tables (derived from the WP01 resolver — no re-enumeration)
# ---------------------------------------------------------------------------


def _yaml_key_for_token(token: str) -> str:
    """Return the ``config.yaml`` activation key for a charter kind *token*.

    The ``mission-type`` token is the documented outlier
    (``mission_type_activations``); every other kind follows the
    ``activated_<plural>`` pattern, with the plural taken from the canonical
    :class:`ArtifactKind` rather than a hand-maintained table (R-009 / CC-4).
    """
    if token == MISSION_TYPE_TOKEN:
        return "mission_type_activations"
    return f"activated_{ArtifactKind.from_operator_token(token).plural}"


#: Maps charter kind operator tokens (hyphenated CLI surface) to ``config.yaml``
#: activation keys. Derived from :data:`CHARTER_KIND_TOKENS` (the canonical kind
#: universe, WP01) so no second kind enumeration is maintained here.
#:
#: The ``mission-type`` → ``mission_type_activations`` mapping is the outlier;
#: all other kinds follow the ``activated_<plural>`` pattern.
YAML_KEY_MAP: dict[str, str] = {
    token: _yaml_key_for_token(token) for token in CHARTER_KIND_TOKENS
}


#: Layer segments scanned for artifact availability (FR-026), in precedence
#: order. ``specify_cli`` resolves the org/project *roots* (C-008); this module
#: only knows the directory-segment names.
_LAYER_SEGMENTS: tuple[str, ...] = ("built-in", "org", "project")
_KITTIFY_DIRNAME = ".kittify"
_CONFIG_FILENAME = "config.yaml"
_CHARTER_FILENAME = "charter.md"
_PROJECT_KIND_DIRS: dict[ArtifactKind, str] = {
    ArtifactKind.DIRECTIVE: "directive",
    ArtifactKind.TACTIC: "tactic",
    ArtifactKind.STYLEGUIDE: "styleguide",
    ArtifactKind.PROCEDURE: "procedure",
}


def _resolve_kind(token: str) -> ArtifactKind | None:
    """Resolve a charter kind *token* to its :class:`ArtifactKind`.

    Returns ``None`` for the ``mission-type`` token (which is part of the
    charter kind universe but is *not* an :class:`ArtifactKind` member — it is
    handled mission-tier). Raises :class:`ValueError` for any token outside the
    canonical universe.

    This is the **single** kind-resolution path in ``pack_manager`` (R-009 /
    CC-4); the kind set is never re-declared here.
    """
    try:
        return ArtifactKind.from_operator_token(token)
    except MissionTypeNotAnArtifactKind:
        return None


def _scan_layout_for(kind: ArtifactKind | None) -> tuple[str, str, bool]:
    """Return ``(base_dir, glob_pattern, layered)`` for a charter kind.

    ``base_dir`` is relative to ``src/`` (the parent of the ``charter`` package
    root). ``layered`` indicates whether the per-layer ``{built-in, org,
    project}`` segment is appended under ``base_dir`` (FR-026); kinds that live
    in a flat directory (``mission-type``) iterate that directory directly.

    The glob pattern is taken from :attr:`ArtifactKind.glob_pattern` (WP01) for
    artifact kinds — suffixes are never re-declared here (T041). ``mission-type``
    is not an :class:`ArtifactKind`, so its flat-directory layout and ``*.yaml``
    glob are spelled out explicitly.

    Two base-dir outliers do not follow ``doctrine/<plural>``:

    * ``mission-step-contract`` lives under
      ``doctrine/missions/built_in_step_contracts`` (a flat directory, not a
      ``built-in`` layer segment) — historically there is no org/project layer
      for step contracts, so ``layered`` is ``False``.
    * ``mission-type`` lives under ``doctrine/missions/mission_types`` (flat).

    Templates (FR-025) are intentionally **not** handled here; ``template`` is
    resolved mission-tier with mission-qualified IDs by WP18, which extends this
    catalog via :meth:`list_available_detailed`.
    """
    if kind is None:
        # mission-type: flat mission-tier directory, not an ArtifactKind.
        return ("doctrine/missions/mission_types", "*.yaml", False)
    if kind is ArtifactKind.MISSION_STEP_CONTRACT:
        # Step contracts live in a single flat directory (no layer segment).
        return ("doctrine/missions/built_in_step_contracts", kind.glob_pattern, False)
    # The 7 standard artifact kinds: doctrine/<plural>/<layer>/ with the
    # canonical glob from ArtifactKind.
    return (f"doctrine/{kind.plural}", kind.glob_pattern, True)


def _resolve_org_layer_dir(root: Path, kind: ArtifactKind, base_dir: str) -> Path:
    """Resolve the org-layer scan directory, tolerant of flat vs nested layouts.

    FR-013 unifies the charter activation subsystem with runtime, which resolves
    org packs from the **flat** ``<pack>/<plural>/`` layout
    (``resolve_org_roots`` → ``DoctrineService``). Flat is therefore the
    canonical, preferred layout. The legacy nested
    ``<pack>/doctrine/<plural>/org/`` layout is kept as a fallback so packs that
    already ship the nested layout keep resolving — a layout-tolerant default,
    not a hard cutover (post-tasks squad decision; keeps the un-owned nested
    catalog fixtures green).
    """
    flat = root / kind.plural
    if flat.is_dir():
        return flat
    return root / base_dir / "org"


def _config_stem(path: Path) -> str:
    """Return the config/file-stem ID for an artifact path.

    The config stem is the filename with all extension suffixes removed
    (e.g. ``001-architectural-integrity-standard.directive.yaml`` →
    ``001-architectural-integrity-standard``). Mirrors
    :func:`charter.kind_vocabulary._config_stem`.
    """
    return path.name.split(".", 1)[0]


#: YAML field that holds an artifact's canonical ID, per kind. Most artifacts
#: use ``id``; agent profiles use ``profile-id`` (matching the WP01 resolver and
#: ``catalog._load_yaml_id_catalog``).
_ID_FIELD_BY_KIND: dict[ArtifactKind, str] = {
    ArtifactKind.AGENT_PROFILE: "profile-id",
}


def _declared_id(path: Path, kind: ArtifactKind | None, yaml: YAML) -> str | None:
    """Return the artifact's declared ``id:`` (URN-side) field, or ``None``.

    Reads the same field the WP01 resolver and ``catalog._extract_artifact_id``
    read (``id`` for most kinds, ``profile-id`` for agent profiles). Returns
    ``None`` when the file is unreadable, not a mapping, or carries no ``id:``.
    """
    id_field = _ID_FIELD_BY_KIND.get(kind, "id") if kind is not None else "id"
    try:
        data = yaml.load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError, TypeError):
        return None
    if isinstance(data, dict):
        raw_id = str(data.get(id_field, "")).strip()
        if raw_id:
            return raw_id
    return None


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AvailableArtifact:
    """A single available artifact, annotated by its source layer (FR-026).

    Attributes
    ----------
    artifact_id:
        The artifact's canonical ``id:`` value (R-011-D), e.g.
        ``"001-architectural-integrity-standard"``.
    layer:
        The source layer the artifact was discovered in: ``"built-in"``,
        ``"org"``, or ``"project"``.
    """

    artifact_id: str
    layer: str


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

#: Doctrine is installed alongside the charter package in ``src/``.
_SRC_ROOT = Path(__file__).parent.parent  # src/charter/.. → src/


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
    if not isinstance(data, dict):
        raise ValueError(".kittify/config.yaml root must be a mapping.")
    return data, yaml


def _activation_list_or_error(data: Any, yaml_key: str) -> list[Any] | None:
    raw = data.get(yaml_key)
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError(f".kittify/config.yaml key '{yaml_key}' must be a list, got {type(raw).__name__}.")
    return raw


def _save_config(config_path: Path, data: Any, yaml: YAML) -> None:
    """Write data back to config_path, creating parent dirs as needed."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


def _load_default_pack() -> dict[str, list[str]]:
    """Load the built-in default pack IDs from the shipped default.yaml."""
    import yaml as _yaml

    with _DEFAULT_PACK_PATH.open("r", encoding="utf-8") as fh:
        raw: Any = _yaml.safe_load(fh)
    if not isinstance(raw, dict):
        return {}
    return {k: list(v) for k, v in raw.items() if isinstance(v, list)}


# ---------------------------------------------------------------------------
# CharterPackManager
# ---------------------------------------------------------------------------


class CharterPackManager:
    """Manages activation/deactivation and availability of doctrine artifacts.

    All mutating methods read from and write to ``.kittify/config.yaml`` using
    ``ruamel.yaml`` round-trip mode (comments and formatting preserved), and
    delegate the validate/plan/commit logic to :mod:`charter.activation_engine`.
    """

    def _require_kind(self, kind: str) -> ArtifactKind | None:
        """Validate *kind* against the canonical universe.

        Returns the :class:`ArtifactKind` (or ``None`` for ``mission-type``).
        Raises :class:`ValueError` with the legacy ``Unknown activation kind``
        message for tokens outside the charter kind universe.
        """
        if kind not in YAML_KEY_MAP:
            raise ValueError(
                f"Unknown activation kind '{kind}'. Valid kinds: {sorted(YAML_KEY_MAP)}"
            )
        return _resolve_kind(kind)

    def activate(
        self,
        ctx: ProjectContext,
        kind: str,
        artifact_id: str,
        *,
        cascade: bool = False,  # noqa: ARG002 — kept for caller API stability
        layer_roots: dict[str, Path] | None = None,
    ) -> ActivationResult:
        """Activate ``artifact_id`` for ``kind`` in the project charter pack.

        Thin wrapper over :func:`charter.activation_engine.plan_activation` +
        :func:`~charter.activation_engine.commit_plan` (WP10). The engine
        validates the artifact ID *before* computing any post-state and
        materializes the default pack into the plan when the kind has no
        explicit activation set (FR-021); this method performs the single
        ``commit_plan`` write.

        Parameters
        ----------
        ctx:
            Project context providing access to the repository root.
        kind:
            Charter kind operator token (e.g. ``"directive"``,
            ``"mission-type"``).
        artifact_id:
            Artifact ID to activate.
        cascade:
            Accepted for signature stability; DRG edge traversal is handled by
            the CLI-level ``charter cascade`` command. No warning is emitted.
        layer_roots:
            Optional org/project doctrine roots, passed as data by CLI callers.
            When omitted, validation remains built-in-only for compatibility.

        Returns
        -------
        ActivationResult
            Contains activated IDs, warnings, and cascade info.

        Raises
        ------
        ValueError
            If ``kind`` is not in the canonical charter kind universe, or the
            artifact ID is unknown (the engine raises the typed
            :class:`~charter.activation_engine.UnknownActivationIdError`, a
            ``ValueError`` subclass).
        """
        self._require_kind(kind)
        yaml_key = YAML_KEY_MAP[kind]

        repo_root = ctx.require_repo_root()
        config_path = repo_root / _KITTIFY_DIRNAME / _CONFIG_FILENAME
        data, yaml_inst = _load_config(config_path)

        available = self.list_available(ctx, kind, layer_roots=layer_roots)
        default_pack = _load_default_pack()
        default_ids = default_pack.get(yaml_key, [])

        # plan_activation validates BEFORE computing any post-state (NFR-003);
        # on an unknown ID it raises UnknownActivationIdError and no write
        # happens.
        plan = plan_activation(
            kind,
            artifact_id,
            yaml_key=yaml_key,
            available_ids=available,
            config_data=data,
            default_ids=default_ids,
        )

        result = ActivationResult(activated=list(plan.activated), warnings=list(plan.warnings))

        commit_plan(config_path, data, plan, save=functools.partial(_save_config, yaml=yaml_inst))
        return result

    def deactivate(
        self,
        ctx: ProjectContext,
        kind: str,
        artifact_id: str,
        *,
        cascade: bool = False,  # noqa: ARG002 — kept for caller API stability
        layer_roots: dict[str, Path] | None = None,
    ) -> ActivationResult:
        """Deactivate ``artifact_id`` for ``kind`` in the project charter pack.

        Thin wrapper over :func:`charter.activation_engine.plan_deactivation` +
        :func:`~charter.activation_engine.commit_plan` (WP10). A kind with no
        explicit activation set has no known baseline, so the engine raises a
        typed :class:`~charter.activation_engine.NoActivationRestrictionsError`
        (the CLI, WP12, surfaces the "run upgrade first" guidance) — there is no
        ``sys.exit`` here.

        Parameters
        ----------
        ctx:
            Project context providing access to the repository root.
        kind:
            Charter kind operator token (e.g. ``"directive"``).
        artifact_id:
            Artifact ID to deactivate.
        cascade:
            Accepted for signature stability; DRG shared-reference analysis is
            handled by the CLI-level ``charter cascade`` command. No warning is emitted.
        layer_roots:
            Accepted for caller symmetry with ``activate``. Deactivation validates
            against the current activation list, not the availability catalog.

        Returns
        -------
        ActivationResult
            Contains deactivated IDs and warnings.

        Raises
        ------
        ValueError
            If ``kind`` is not in the canonical charter kind universe.
        NoActivationRestrictionsError
            If the kind has no explicit activation set (the engine raises this;
            the CLI surfaces the upgrade guidance).
        """
        del layer_roots  # Accepted for API symmetry with activate(); deactivation ignores external layer maps.
        self._require_kind(kind)
        yaml_key = YAML_KEY_MAP[kind]

        repo_root = ctx.require_repo_root()
        config_path = repo_root / _KITTIFY_DIRNAME / _CONFIG_FILENAME
        data, yaml_inst = _load_config(config_path)

        plan = plan_deactivation(
            kind,
            artifact_id,
            yaml_key=yaml_key,
            config_data=data,
        )

        result = ActivationResult(deactivated=list(plan.deactivated), warnings=list(plan.warnings))

        # No-op removal (ID not present): nothing to write, leave config bytes
        # untouched.
        if not plan.deactivated:
            return result

        commit_plan(config_path, data, plan, save=functools.partial(_save_config, yaml=yaml_inst))
        return result

    def list_activated(
        self,
        ctx: ProjectContext,
    ) -> dict[str, frozenset[str] | None]:
        """Return activated artifact IDs keyed by charter kind token.

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
            Mapping of charter kind token to activated IDs (or ``None``).
        """
        repo_root = ctx.require_repo_root()
        config_path = repo_root / _KITTIFY_DIRNAME / _CONFIG_FILENAME
        data, _ = _load_config(config_path)

        result: dict[str, frozenset[str] | None] = {}
        for kind, yaml_key in YAML_KEY_MAP.items():
            raw = _activation_list_or_error(data, yaml_key)
            if raw is None:
                result[kind] = None
            else:
                result[kind] = frozenset(str(item) for item in raw)
        return result

    def _scan_layer_dirs(
        self,
        kind_token: str,
        *,
        layer_roots: dict[str, Path] | None,
    ) -> list[tuple[str, Path]]:
        """Return ``(layer, directory)`` pairs to scan for *kind_token*.

        The built-in layer is rooted under the installed doctrine package
        (``src/doctrine``). Org/project roots are supplied **as data** (C-008).
        Org roots use the pack layout ``doctrine/<plural>/org``. Project roots
        use the live project overlay layout ``doctrine/<singular>`` for kinds
        synthesized into ``.kittify/doctrine``. Non-existent directories are
        skipped so a layer that is simply not present contributes nothing.
        """
        kind = _resolve_kind(kind_token)
        base_dir, _glob, layered = _scan_layout_for(kind)
        roots: dict[str, Path] = {"built-in": _SRC_ROOT}
        if layer_roots:
            roots.update(layer_roots)

        dirs: list[tuple[str, Path]] = []
        for layer in _LAYER_SEGMENTS:
            root = roots.get(layer)
            if root is None:
                continue
            if layered and layer == "project" and kind is not None:
                kind_dir = _PROJECT_KIND_DIRS.get(kind, kind.plural)
                candidate = root / "doctrine" / kind_dir
            elif layered and layer == "org" and kind is not None:
                candidate = _resolve_org_layer_dir(root, kind, base_dir)
            elif layered:
                candidate = root / base_dir / layer
            elif layer == "built-in":
                # Flat-directory kinds (mission-type / step contracts) only have
                # the built-in layer.
                candidate = root / base_dir
            else:
                continue
            if candidate.is_dir():
                dirs.append((layer, candidate))
        return dirs

    def list_available_detailed(
        self,
        ctx: ProjectContext,  # noqa: ARG002 — kept for signature symmetry; roots are data (C-008)
        kind: str,
        *,
        layer_roots: dict[str, Path] | None = None,
    ) -> list[AvailableArtifact]:
        """Return available artifacts for *kind*, annotated by source layer.

        Scans the built-in layer plus any caller-supplied org / project doctrine
        roots (FR-026), reading each artifact's ``id:`` field (R-011-D) rather
        than its filename stem. Org/project roots are passed in **as data**
        (C-008); this method never imports ``specify_cli`` and performs no root
        resolution of its own.

        Parameters
        ----------
        ctx:
            Project context (unused for scanning; roots are passed as data).
        kind:
            Charter kind operator token (e.g. ``"directive"``).
        layer_roots:
            Optional mapping of layer name (``"org"`` / ``"project"``) to the
            resolved doctrine root for that layer. When omitted, only the
            built-in layer is scanned (backward compatible).

        Returns
        -------
        list[AvailableArtifact]
            One entry per discovered artifact, with its operator-facing
            config-stem ID (the form used in ``config.yaml`` activation lists,
            e.g. ``"003-decision-documentation-requirement"``) and its source
            layer. Files that do not parse or carry no ``id:`` field are skipped
            — R-011-D id-awareness: the catalog validates the declared ``id:``
            rather than blindly trusting the filename. When the same ID appears
            in multiple layers, each layer yields its own entry (the caller
            decides precedence/rendering).

        Raises
        ------
        ValueError
            If ``kind`` is not in the canonical charter kind universe.
        """
        _ = ctx
        kind_enum = self._require_kind(kind)
        yaml = YAML(typ="safe")
        _base_dir, glob, _layered = _scan_layout_for(kind_enum)
        if not glob:
            # template kind has no glob; resolved mission-tier by WP18.
            return []

        entries: list[AvailableArtifact] = []
        for layer, scan_dir in self._scan_layer_dirs(kind, layer_roots=layer_roots):
            for yaml_file in sorted(scan_dir.rglob(glob)):
                # R-011-D: confirm the artifact declares an ``id:`` (parse it)
                # rather than trusting the filename; surface the operator-facing
                # config-stem ID that ``config.yaml`` activation lists use.
                if _declared_id(yaml_file, kind_enum, yaml) is None:
                    continue
                entries.append(
                    AvailableArtifact(artifact_id=_config_stem(yaml_file), layer=layer)
                )
        return entries

    def list_available(
        self,
        ctx: ProjectContext,
        kind: str,
        *,
        layer_roots: dict[str, Path] | None = None,
    ) -> frozenset[str]:
        """Return the set of available artifact IDs for *kind* across layers.

        Backward-compatible flat view over :meth:`list_available_detailed`:
        returns the union of artifact ``id:`` values across the built-in, org,
        and project layers (FR-026). Existing callers
        (``consistency_check``, ``charter list --show-available``) keep the
        ``frozenset[str]`` contract; ``layer_roots`` is keyword-only with a safe
        default so the built-in-only call site is unchanged.

        Parameters
        ----------
        ctx:
            Project context (roots are passed as data, C-008).
        kind:
            Charter kind operator token (e.g. ``"directive"``).
        layer_roots:
            Optional mapping of org/project layer name to its doctrine root.

        Returns
        -------
        frozenset[str]
            Available artifact IDs (from each artifact's ``id:`` field). Empty
            when no scannable directory exists for the kind.

        Raises
        ------
        ValueError
            If ``kind`` is not in the canonical charter kind universe.
        """
        return frozenset(
            entry.artifact_id
            for entry in self.list_available_detailed(ctx, kind, layer_roots=layer_roots)
        )

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
        config_path = repo_root / _KITTIFY_DIRNAME / _CONFIG_FILENAME
        charter_path = repo_root / _KITTIFY_DIRNAME / "charter" / _CHARTER_FILENAME

        result = MergeResult()

        # Backup charter.md if it exists before any write
        if charter_path.exists():
            ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
            backup_dir = repo_root / _KITTIFY_DIRNAME / "charter" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"charter-{ts}.md"
            backup_path.write_bytes(charter_path.read_bytes())
            result.backup_path = backup_path

        data, yaml_inst = _load_config(config_path)
        default_pack = _load_default_pack()

        for yaml_key in YAML_KEY_MAP.values():
            raw = _activation_list_or_error(data, yaml_key)
            if raw is None:
                default_ids = default_pack.get(yaml_key, [])
                data[yaml_key] = list(default_ids)
                # Map yaml_key back to CLI kind for the result
                kind = next(k for k, v in YAML_KEY_MAP.items() if v == yaml_key)
                result.kinds_written.append(kind)

        if result.kinds_written:
            _save_config(config_path, data, yaml_inst)

        return result


# Re-export the engine's structured errors for callers that import them from
# ``pack_manager`` (the CLI, WP12, catches these to surface guidance).
__all__ += ["NoActivationRestrictionsError", "UnknownActivationIdError"]
