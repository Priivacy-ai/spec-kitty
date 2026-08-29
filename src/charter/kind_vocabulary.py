"""Canonical kind & artifact-ID vocabulary resolver (FR-027, R-009, R-011-D).

This module is the single seam through which charter-layer consumers route two
vocabularies that were previously re-declared across five+ modules with three
incompatible spellings (research R-009):

1. **Operator kind tokens** (hyphenated CLI surface, e.g. ``agent-profile``) →
   canonical :class:`~charter.offering.artifact_kinds.ArtifactKind`. That mapping lives
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

from charter.offering.artifact_kinds import (
    CHARTER_KIND_TOKENS,
    MISSION_TYPE_TOKEN,
    PROJECT_KIND_DIRS as _PROJECT_KIND_DIRS,
    ArtifactKind,
    MissionTypeNotAnArtifactKind,
)
from charter.offering.discovery_recursion import overlay_scan_is_recursive
from charter.offering.pack_paths import (
    BuiltInContentDirNotAvailable,
    PackRootNotFound,
    built_in_dir,
)

#: Public re-export of :data:`charter.offering.artifact_kinds.PROJECT_KIND_DIRS`.
#:
#: Landing-fold addition (write-side-seam-matrix-tracer Wave B / #3070):
#: ``specify_cli.cli.commands.doctrine``'s ``new`` scaffolder needs the
#: project-tier directory-per-kind mapping but, as a runtime-layer module,
#: may not import ``doctrine.*`` directly (the runtime -> charter ->
#: doctrine boundary ratchet, ``test_runtime_charter_doctrine_boundary.py``).
#: This module already imports the mapping privately (as
#: ``_PROJECT_KIND_DIRS``, kept for the existing internal partial-table
#: distinction below); this public alias is the thin facade re-export the
#: boundary doc's Phase-2 recipe calls for, without disturbing the private
#: name other tests already import.
PROJECT_KIND_DIRS = _PROJECT_KIND_DIRS

__all__ = [
    "ArtifactKind",
    "CHARTER_KIND_TOKENS",
    "MISSION_TYPE_TOKEN",
    "PROJECT_KIND_DIRS",
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
#: The project-tier overlay directory name per kind is the single canonical
#: authority :data:`charter.offering.artifact_kinds.PROJECT_KIND_DIRS` (imported and
#: re-exported above as ``PROJECT_KIND_DIRS`` — the runtime→charter→doctrine
#: boundary facade for this mapping; see ``cli/commands/doctrine.py``'s
#: ``new`` scaffolder for the consumer). It is *total*, so
#: ``.get(kind, kind.plural)`` below never actually falls back — the default
#: is retained only as a belt-and-braces guard against a future partial
#: authority. No mapping is re-declared here (WP03 T014).


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
    _doctrine_root: Path,
    org_roots: list[Path] | None,
    layer_roots: dict[str, Path] | None,
) -> list[tuple[Path, bool]]:
    """Return the ``(directory, recursive)`` pairs to scan for *kind*.

    Roots are supplied as data (C-008). ``_doctrine_root`` is the resolved
    doctrine package root -- retained in the signature for call-site symmetry
    with :func:`_iter_artifact_paths` (and its callers' diagnostics) but no
    longer used as a scan root itself: built-in content was flattened out of
    ``<doctrine_root>/<kind>/built-in`` into ``packs/built-in/<kind>``
    (relocation mission doctrine-built-in-seam-consolidation-01KYW3TX, WP02),
    which resolves via the shared :func:`~charter.offering.pack_paths.built_in_dir`
    seam below instead. ``org_roots`` contributes, for each root, the flat
    ``<root>/<plural>`` layout that every real org pack uses today -- plus,
    additively, the legacy package-shaped ``<root>/<plural>/built-in`` layout
    (``recursive=True``) where that also separately exists.

    The flat entry's ``recursive`` flag is sourced from the single shared
    recursion authority :func:`charter.offering.discovery_recursion.overlay_scan_is_recursive`
    -- the same authority the live loader consults
    (:meth:`charter.offering.base.BaseDoctrineRepository._project_scan`, which now
    recurses unconditionally for every kind's org/project overlay, and
    :meth:`charter.offering.agent_profiles.repository.AgentProfileRepository._load`).
    So the resolver and the loader recurse identically for **every** kind
    (C-001, unconditional), reading nested org/project subdirectories such as
    ``styleguides/writing/`` the same way. The prior divergence -- where the
    resolver emitted ``recursive=False`` while only the ``styleguide`` and
    ``asset`` repositories overrode ``_project_scan`` to ``rglob`` -- is closed:
    those redundant overrides were removed in favour of the recursive base, and
    the parity/totality gate pins loader↔resolver agreement.
    ``layer_roots`` is the modern charter layer map.
    Org roots contribute ``<root>/doctrine/<plural>/org``. Project roots
    contribute ``<root>/doctrine/<singular>`` for live ``.kittify/doctrine``
    overlays.

    Several built-in kinds (tactics, styleguides, toolguides) organize
    artifacts into category subdirectories (e.g.
    ``tactics/built-in/testing/acceptance-test-first.tactic.yaml``), which a
    non-recursive scan would silently miss -- the exact silent-drop failure
    mode C-006 forbids; the shared authority makes org/project match built-in
    here.
    """
    dirs: list[tuple[Path, bool]] = []
    built_in = _built_in_scan_dir(kind)
    if built_in is not None:
        dirs.append(built_in)
    dirs.extend(_org_scan_dirs(kind, org_roots))
    dirs.extend(_layer_scan_dirs(kind, layer_roots))
    return dirs


def _built_in_scan_dir(kind: ArtifactKind) -> tuple[Path, bool] | None:
    """Return the flattened built-in scan dir for *kind*, or ``None``.

    ``None`` covers both the fail-soft ``built_in_dir`` errors (see the
    ``_scan_roots`` docstring) and the case where the resolved directory does
    not exist on disk.
    """
    try:
        flattened_built_in = built_in_dir(kind)
    except (PackRootNotFound, BuiltInContentDirNotAvailable):
        return None
    if flattened_built_in is not None and flattened_built_in.is_dir():
        return (flattened_built_in, True)
    return None


def _org_scan_dirs(
    kind: ArtifactKind, org_roots: list[Path] | None
) -> list[tuple[Path, bool]]:
    """Return the flat and legacy ``built-in`` org-pack dirs that exist.

    For every configured org root, contributes (in this order) the flat
    ``<root>/<plural>`` layout when it exists, then the legacy
    ``<root>/<plural>/built-in`` layout (``recursive=True``, unchanged)
    when it separately exists. Neither directory existing is not an error --
    fewer entries are returned, never a raise.

    **Recursion is sourced from the shared authority (#3426 closed).** The
    flat entry's ``recursive`` flag comes from
    :func:`charter.offering.discovery_recursion.overlay_scan_is_recursive` -- the same
    single authority the live loader (``BaseDoctrineRepository._project_scan``
    and ``AgentProfileRepository._load``) consults -- so the resolver and the
    loader recurse identically for every kind (unconditional per C-001). This
    closes the prior list-vs-activate divergence: a ``styleguide`` (or any
    charter-activatable kind) stored under *any* subdirectory of an org root --
    e.g. ``styleguides/writing/`` -- now resolves for ``charter activate`` just
    as it already loads at runtime and already lists via
    ``pack_manager.list_available_detailed`` (which was always ``rglob``). The
    parity/totality gate pins loader↔resolver agreement so the divergence
    cannot silently return.

    **Global flat-before-legacy grouping** (PR-BOUNDARY-002 fix, pre-merge
    adversarial squad, severity 3; operator-ruled "fix it properly" rather
    than merely documenting the gap). FR-001's precedence rule is worded
    "for one org root" -- this widens it beyond that literal text, a
    deliberate, operator-authorized scope expansion to close the defect
    class rather than leave it as a documented limitation: the returned
    list is grouped as *every flat entry, in org-root order* followed by
    *every legacy entry, in org-root order* -- entries are **not**
    interleaved per root as they were before this fix. Previously, with
    ``org_roots=[a, b]``, a legacy entry from ``a`` could precede a flat
    entry from ``b`` in the returned list, so a same-config-stem collision
    straddling two different org packs -- one legacy-shaped, one
    flat-shaped -- was decided by ``org_roots`` order, not by flat-vs-legacy
    shape, contradicting the documented flat-wins invariant whenever the
    legacy-shaped root happened to be listed first.
    :func:`resolve_artifact_urn`'s first-match-wins semantics over this
    grouped list now make the flat-layout file win a same-config-stem
    collision regardless of which org root either file came from, or which
    order the roots were supplied in -- see
    ``TestOrgScanDirsHelper.test_multi_root_precedence_flat_wins_regardless_of_root_order``
    (``tests/charter/test_kind_vocabulary_scan_roots.py``) for the
    regression, exercised in both root orderings.
    """
    flat_dirs: list[tuple[Path, bool]] = []
    legacy_dirs: list[tuple[Path, bool]] = []
    recursive = overlay_scan_is_recursive(kind)
    for root in org_roots or []:
        flat = root / kind.plural
        if flat.is_dir():
            flat_dirs.append((flat, recursive))
        legacy = flat / "built-in"
        if legacy.is_dir():
            legacy_dirs.append((legacy, True))
    return flat_dirs + legacy_dirs


def _layer_candidate_dir(kind: ArtifactKind, layer: str, root: Path) -> Path:
    """Return the candidate doctrine dir for *kind* within a single *layer*."""
    if layer == "project":
        return root / "doctrine" / PROJECT_KIND_DIRS.get(kind, kind.plural)
    return root / "doctrine" / kind.plural / layer


def _layer_scan_dirs(
    kind: ArtifactKind, layer_roots: dict[str, Path] | None
) -> list[tuple[Path, bool]]:
    """Return layer doctrine dirs that exist for *kind*, across *layer_roots*."""
    dirs: list[tuple[Path, bool]] = []
    recursive = overlay_scan_is_recursive(kind)
    for layer, root in (layer_roots or {}).items():
        candidate = _layer_candidate_dir(kind, layer, root)
        if candidate.is_dir():
            dirs.append((candidate, recursive))
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
    for scan_dir, recursive in _scan_roots(
        kind,
        _doctrine_root=doctrine_root,
        org_roots=org_roots,
        layer_roots=layer_roots,
    ):
        paths.extend(sorted(_scan_dir_matches(scan_dir, pattern, recursive=recursive)))
    return paths


def _scan_dir_matches(scan_dir: Path, pattern: str, *, recursive: bool) -> list[Path]:
    """Return the artifact files under *scan_dir* matching *pattern*.

    A recursive scan excludes the reserved ``built-in/`` subtree (handled by its
    own dedicated entry — see :func:`_under_reserved_builtin_subdir`); a
    non-recursive scan is a flat glob.
    """
    if not recursive:
        return list(scan_dir.glob(pattern))
    return [
        match
        for match in scan_dir.rglob(pattern)
        if not _under_reserved_builtin_subdir(match, scan_dir)
    ]


def _under_reserved_builtin_subdir(match: Path, scan_dir: Path) -> bool:
    """Return whether *match* is directly under the reserved ``built-in/`` child.

    The **immediate** child ``<plural>/built-in`` is the reserved legacy
    package-shaped layer, scanned by its **own** dedicated
    ``(<plural>/built-in, recursive=True)`` entry (see :func:`_org_scan_dirs`).
    A now-recursive flat ``<plural>`` entry would otherwise double-cover it and —
    because a ``built-in/`` file would sort ahead of the sibling flat file —
    silently invert the flat-wins-over-legacy precedence guarantee (FR-001 / the
    ``TestOrgScanDirsHelper`` precedence regressions). Excluding it from the
    recursive flat scan leaves ``built-in/`` to its dedicated, later-ordered
    entry so flat still wins.

    The check is scoped to the **immediate** child (``parts[0] == "built-in"``),
    NOT any ``built-in`` component at arbitrary depth: the compensating dedicated
    entry only covers ``<plural>/built-in``, so excluding a deeper
    ``<plural>/<category>/built-in/`` would drop it from the resolver while the
    loader (``base._project_scan`` rglob, no exclusion) still loads it — exactly
    the loader↔resolver discovery divergence this mission eliminates. Deeper
    ``built-in`` components (a user directory that merely happens to be named
    ``built-in`` below a category) stay discoverable, matching the loader.
    """
    parts = match.relative_to(scan_dir).parts
    return len(parts) > 1 and parts[0] == "built-in"


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
        f"No {kind.value} artifact with config ID {config_id!r} found under "
        f"doctrine root {doctrine_root}{_org_roots_clause(org_roots)}. "
        f"Check `.kittify/config.yaml` activated_{kind.plural} for a stale or "
        f"misspelled entry, or run `spec-kitty doctor doctrine` to verify the "
        f"doctrine corpus (including any org packs) is intact."
    )


def _org_roots_clause(org_roots: list[Path] | None) -> str:
    """Name the org roots that were also scanned, when any were supplied."""
    if not org_roots:
        return ""
    return f" or org/project pack roots {[str(root) for root in org_roots]}"


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
        f"No {kind.value} artifact with id {artifact_id!r} found under "
        f"doctrine root {doctrine_root}{_org_roots_clause(org_roots)}. "
        f"Check `.kittify/config.yaml` activated_{kind.plural} for a stale or "
        f"misspelled entry, or run `spec-kitty doctor doctrine` to verify the "
        f"doctrine corpus (including any org packs) is intact."
    )
