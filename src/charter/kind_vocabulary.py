"""Canonical kind & artifact-ID vocabulary resolver (FR-027, R-009, R-011-D).

This module is the single seam through which charter-layer consumers route two
vocabularies that were previously re-declared across five+ modules with three
incompatible spellings (research R-009):

1. **Operator kind tokens** (hyphenated CLI surface, e.g. ``agent-profile``) →
   canonical :class:`~doctrine.artifact_kinds.ArtifactKind`. That mapping lives
   on the enum itself (:meth:`ArtifactKind.from_operator_token`); this module
   re-exports the related error type for charter callers.

2. **Artifact config-stem IDs ↔ DRG URN node IDs** (research R-011-D, the dual
   "config stem vs DRG ``id``" system). A config/file-stem ID such as
   ``001-architectural-integrity-standard`` resolves to the DRG URN node ID
   ``directive:DIRECTIVE_001`` (and back) by reading the artifact's existing
   ``id:`` field — the same field already read by
   :func:`charter.catalog._extract_artifact_id`.

Canonical charter kind universe
-------------------------------
The charter kind universe is the 8 artifact :class:`ArtifactKind` kinds **plus**
``mission-type`` (which is *not* an :class:`ArtifactKind` member and is handled
mission-tier; see FR-032 / WP04). ``template`` *is* an :class:`ArtifactKind`
member but is resolved specially (mission-tier, no glob) and has no config-stem
↔ URN entry. Consumers must route every kind string through
:meth:`ArtifactKind.from_operator_token` (CC-4) — no second kind enumeration may
be re-declared in a consumer.

Layering
--------
Charter layer: this module may import ``doctrine`` and ``kernel`` but never
``specify_cli``. Org/project roots are passed in **as data** (C-008); this module
does not resolve them.

This WP (WP01) delivers the resolver and its tests only. Consumer rewiring
(``pack_manager`` WP09, ``list`` WP16, ``context`` WP17) lives in later WPs.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from doctrine.artifact_kinds import (
    CHARTER_KIND_TOKENS,
    MISSION_TYPE_TOKEN,
    ArtifactKind,
    MissionTypeNotAnArtifactKind,
)

__all__ = [
    "ArtifactKind",
    "CHARTER_KIND_TOKENS",
    "MISSION_TYPE_TOKEN",
    "MissionTypeNotAnArtifactKind",
    "UnknownArtifactIdError",
    "resolve_artifact_urn",
    "resolve_config_id",
]


class UnknownArtifactIdError(ValueError):
    """Raised when a config-stem ID or DRG URN node ID cannot be resolved.

    Used by downstream unknown-ID validation (WP10) and cascade resolution
    (WP11). The message names both the kind and the offending ID so the error
    is actionable without grepping.
    """


#: YAML key holding the artifact ID, per kind. Most artifacts use ``id``;
#: agent profiles use ``profile-id`` (matching ``catalog._load_yaml_id_catalog``).
_ID_FIELD_BY_KIND: dict[ArtifactKind, str] = {
    ArtifactKind.AGENT_PROFILE: "profile-id",
}
_DEFAULT_ID_FIELD = "id"
_PROJECT_KIND_DIRS: dict[ArtifactKind, str] = {
    ArtifactKind.DIRECTIVE: "directive",
    ArtifactKind.TACTIC: "tactic",
    ArtifactKind.STYLEGUIDE: "styleguide",
    ArtifactKind.PROCEDURE: "procedure",
}


def _id_field_for(kind: ArtifactKind) -> str:
    return _ID_FIELD_BY_KIND.get(kind, _DEFAULT_ID_FIELD)


def _read_id(path: Path, id_field: str, yaml: YAML) -> str | None:
    """Return the artifact ID from a YAML file, falling back to the file stem.

    Mirrors the logic behind :func:`charter.catalog._extract_artifact_id`
    (without the language-scoping filter, which is not relevant to ID identity).
    """
    try:
        data = yaml.load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError, TypeError):
        return None
    if isinstance(data, dict):
        raw_id = str(data.get(id_field, "")).strip()
        if raw_id:
            return raw_id
    fallback = path.stem.split(".")[0].strip()
    return fallback or None


def _config_stem(path: Path) -> str:
    """Return the config/file-stem ID for an artifact path.

    The config stem is the filename with all extension suffixes removed
    (e.g. ``001-architectural-integrity-standard.directive.yaml`` →
    ``001-architectural-integrity-standard``).
    """
    return path.name.split(".", 1)[0]


def _scan_roots(
    kind: ArtifactKind,
    *,
    doctrine_root: Path,
    org_roots: list[Path] | None,
    layer_roots: dict[str, Path] | None,
) -> list[Path]:
    """Return the directories to scan for *kind*, in precedence order.

    Roots are supplied as data (C-008). ``doctrine_root`` is the resolved
    doctrine package root. ``org_roots`` preserves the legacy package-shaped
    root contract where each root contributes ``<root>/<plural>/built-in``.
    ``layer_roots`` is the modern charter layer map. Org roots contribute
    ``<root>/doctrine/<plural>/org``. Project roots contribute
    ``<root>/doctrine/<singular>`` for live ``.kittify/doctrine`` overlays.
    """
    roots: list[Path] = [doctrine_root]
    if org_roots:
        roots.extend(org_roots)
    dirs: list[Path] = []
    for root in roots:
        candidate = root / kind.plural / "built-in"
        if candidate.is_dir():
            dirs.append(candidate)
    if layer_roots:
        for layer, root in layer_roots.items():
            candidate = (
                root / "doctrine" / _PROJECT_KIND_DIRS.get(kind, kind.plural)
                if layer == "project"
                else root / "doctrine" / kind.plural / layer
            )
            if candidate.is_dir():
                dirs.append(candidate)
    return dirs


def _iter_artifact_paths(
    kind: ArtifactKind,
    *,
    doctrine_root: Path,
    org_roots: list[Path] | None,
    layer_roots: dict[str, Path] | None,
) -> list[Path]:
    pattern = kind.glob_pattern
    if not pattern:
        return []
    paths: list[Path] = []
    for scan_dir in _scan_roots(
        kind,
        doctrine_root=doctrine_root,
        org_roots=org_roots,
        layer_roots=layer_roots,
    ):
        paths.extend(sorted(scan_dir.glob(pattern)))
    return paths


def resolve_artifact_urn(
    kind: ArtifactKind,
    config_id: str,
    *,
    doctrine_root: Path,
    org_roots: list[Path] | None = None,
    layer_roots: dict[str, Path] | None = None,
) -> str:
    """Resolve a config/file-stem ID to its DRG URN node ID.

    Locates the artifact whose config stem (filename without suffixes) equals
    *config_id*, reads its ``id:`` field, and returns ``f"{kind.value}:{id}"``.

    Args:
        kind: The artifact kind (route raw kind strings through
            :meth:`ArtifactKind.from_operator_token` first).
        config_id: The config/file-stem ID, e.g.
            ``"001-architectural-integrity-standard"``.
        doctrine_root: Resolved doctrine package root (passed as data, C-008).
        org_roots: Optional additional org/project doctrine roots to scan.
        layer_roots: Optional modern layer map, e.g. ``{"org": <pack-root>}``.

    Returns:
        The DRG URN node ID, e.g. ``"directive:DIRECTIVE_001"``.

    Raises:
        UnknownArtifactIdError: if no artifact with that config stem exists for
            *kind*.
    """
    yaml = YAML(typ="safe")
    id_field = _id_field_for(kind)
    for path in _iter_artifact_paths(
        kind,
        doctrine_root=doctrine_root,
        org_roots=org_roots,
        layer_roots=layer_roots,
    ):
        if _config_stem(path) == config_id:
            artifact_id = _read_id(path, id_field, yaml)
            if artifact_id:
                return f"{kind.value}:{artifact_id}"
    raise UnknownArtifactIdError(
        f"No {kind.value} artifact with config ID {config_id!r} found "
        f"under doctrine root {doctrine_root}."
    )


def resolve_config_id(
    urn: str,
    *,
    doctrine_root: Path,
    org_roots: list[Path] | None = None,
    layer_roots: dict[str, Path] | None = None,
) -> str:
    """Resolve a DRG URN node ID back to its config/file-stem ID.

    Inverse of :func:`resolve_artifact_urn`. Parses the ``kind:id`` URN, finds
    the artifact whose ``id:`` field matches, and returns its config stem.

    Args:
        urn: A DRG URN node ID, e.g. ``"directive:DIRECTIVE_001"``.
        doctrine_root: Resolved doctrine package root (passed as data, C-008).
        org_roots: Optional additional org/project doctrine roots to scan.
        layer_roots: Optional modern layer map, e.g. ``{"org": <pack-root>}``.

    Returns:
        The config/file-stem ID, e.g. ``"001-architectural-integrity-standard"``.

    Raises:
        ValueError: if *urn* is malformed (missing ``kind:`` prefix or an
            unknown kind value).
        UnknownArtifactIdError: if no artifact with that ID exists for the kind.
    """
    kind_value, sep, artifact_id = urn.partition(":")
    if not sep or not kind_value or not artifact_id:
        raise ValueError(
            f"Malformed URN {urn!r}; expected '<kind>:<artifact_id>'."
        )
    try:
        kind = ArtifactKind(kind_value)
    except ValueError as exc:
        raise ValueError(
            f"Malformed URN {urn!r}; unknown kind {kind_value!r}."
        ) from exc

    yaml = YAML(typ="safe")
    id_field = _id_field_for(kind)
    for path in _iter_artifact_paths(
        kind,
        doctrine_root=doctrine_root,
        org_roots=org_roots,
        layer_roots=layer_roots,
    ):
        if _read_id(path, id_field, yaml) == artifact_id:
            return _config_stem(path)
    raise UnknownArtifactIdError(
        f"No {kind.value} artifact with id {artifact_id!r} found "
        f"under doctrine root {doctrine_root}."
    )
