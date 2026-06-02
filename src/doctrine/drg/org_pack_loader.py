"""Doctrine-layer org-pack schema and per-pack loader (Slice F WP06 / DDD boundary).

This module is the canonical home for the org-pack on-disk schema.  It was
split out of ``charter.drg`` per the PR #1119 pre-review comment: org-pack
schema knowledge belongs in the ``doctrine`` layer so it cannot silently
drift from the main DRG schema as ``doctrine`` evolves.

Architectural boundary
----------------------

``doctrine`` sits below ``charter`` in the dependency hierarchy::

    kernel (root) <- doctrine <- charter <- specify_cli

This module MUST NOT import from ``charter`` or ``specify_cli``. Charter
reads ``organisation_packs:`` from ``.kittify/config.yaml`` (project-config
knowledge, charter-domain) and calls :func:`load_org_pack` for each
configured pack root. All per-pack parsing and schema validation is the
doctrine domain's responsibility and lives here.

C-009 / kind universe
---------------------

The 8-kind plural universe (``_ORG_DRG_CANONICAL_KINDS``) is declared here
rather than imported from elsewhere so that any drift from
``charter.activations._ALLOWED_KINDS`` is surfaced by the contract test
sweep (C-009 binding). Do not import this constant across the boundary;
use the contract sweep to detect drift.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any, ClassVar, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from doctrine.artifact_kinds import ArtifactKind
from doctrine.drg.models import Relation

__all__ = [
    "AUGMENTATION_ELIGIBLE_KINDS",
    "AUGMENTATION_RELATIONS",
    "TOPOLOGY_KINDS",
    "OrgDRGFragment",
    "OrgPackMissingError",
    "augmentation_plural_kinds",
    "load_org_pack",
    "merge_topology_artifact",
]


# ---------------------------------------------------------------------------
# C-009: 8-kind plural universe inherited from Mission B
# ---------------------------------------------------------------------------
# Byte-identical to ``charter.activations._ALLOWED_KINDS``. We re-declare
# rather than import to keep this module free of charter imports; the
# contract test sweep enforces drift detection between the two declarations
# (C-009 binding).
#
# Mission ``charter-doctrine-mission-type-configuration-01KSWJVX`` (WP01 + WP11)
# renames ``mission_step_contracts`` → ``mission_steps`` as the canonical plural
# kind, aligning the DRG with the runtime domain model in
# ``doctrine.missions.models.MissionStep``. The legacy plural is preserved as
# an alias for one release so that org packs authored against the previous
# universe continue to validate; the alias resolves to the same canonical
# kind on parse, so downstream code only sees the canonical form.

#: Canonical plural-kind alias map. Keys = forms accepted on input; values =
#: canonical form retained on the validated node. Identity entries (canonical
#: → canonical) keep ``_ORG_DRG_CANONICAL_KINDS`` semantics intact.
# DIRECTIVE_003 (FR-032, decision locked): mission-type augmentation is
# delivered by EXPANDING this canonical kind universe to include mission types,
# NOT by a separate augmentation path. The plural ``mission_types`` is added to
# the universe and to ``_ORG_DRG_KIND_ALIASES`` so an org-pack fragment may
# author ``enhances`` / ``overrides`` / ``specializes_from`` edges against a
# built-in mission type and have them validate. This is a binding change to the
# (formerly 8-kind) universe; the lockstep drift guard against
# ``charter.activations._ALLOWED_KINDS`` lives in
# ``tests/doctrine/test_org_pack_augmentation.py`` (it asserts the loader
# universe equals ``_ALLOWED_KINDS`` plus the mission-type extension, so neither
# side can drift silently and mission types are never silently dropped).
_ORG_DRG_KIND_ALIASES: dict[str, str] = {
    "directives": "directives",
    "tactics": "tactics",
    "styleguides": "styleguides",
    "toolguides": "toolguides",
    "paradigms": "paradigms",
    "procedures": "procedures",
    "agent_profiles": "agent_profiles",
    "mission_steps": "mission_steps",
    # Backward-compat alias: pre-WP01 packs used `mission_step_contracts`.
    "mission_step_contracts": "mission_steps",
    # FR-032 (DIRECTIVE_003): mission types are now part of the canonical
    # org-pack DRG kind universe so mission-type augmentation reuses the same
    # fragment-edge auto-emit + validator-parity path as every other kind.
    "mission_types": "mission_types",
    # Singular spelling accepted on input for ergonomics; resolves to plural.
    "mission_type": "mission_types",
}

#: Accepted input forms = every alias key (canonical forms + backward-compat
#: aliases such as ``mission_step_contracts`` and the ``mission_type`` singular).
#: The validator resolves each to its canonical value via
#: :data:`_ORG_DRG_KIND_ALIASES` after the membership check.
_ORG_DRG_CANONICAL_KINDS: frozenset[str] = frozenset(_ORG_DRG_KIND_ALIASES.keys())

#: The plural kind newly admitted to the universe by FR-032. Exposed so the
#: lockstep drift guard can express the universe as
#: ``_ALLOWED_KINDS | _MISSION_TYPE_UNIVERSE_EXTENSION`` without re-listing it.
_MISSION_TYPE_UNIVERSE_EXTENSION: frozenset[str] = frozenset({"mission_types"})


# ---------------------------------------------------------------------------
# Augmentation single-source (FR-030, T013) — one definition, two derivations
# ---------------------------------------------------------------------------
# Historically two hand-synced tables existed (R-011-A): the loader's
# ``_AUGMENTATION_PLURAL_TO_KIND`` (5 kinds) and the pack validator's
# ``_AUGMENTATION_PLURAL_KINDS`` (the same 5 kinds, "kept in sync" by comment).
# FR-030 collapses them to ONE source here. Adding a kind is a one-line change
# in :data:`AUGMENTATION_ELIGIBLE_KINDS`; both the loader auto-emitter and
# ``specify_cli.doctrine.pack_validator`` derive from it.
#
# Coverage is now all 9 augmentation-eligible kinds (FR-028, T015): the
# original five (tactic, styleguide, paradigm, procedure, agent_profile) plus
# the four previously-uncovered kinds (directive, toolguide,
# mission_step_contract, mission_type). ``template`` is the one ``ArtifactKind``
# member that is NOT augmentation-eligible (no augmentation vocabulary).

#: The mission-tier "kind" that is not an :class:`ArtifactKind` member but is
#: augmentation-eligible after the FR-032 universe expansion. Modelled here as a
#: ``(singular_urn_kind, plural)`` pair so the eligible-kind set can carry it
#: alongside the :class:`ArtifactKind`-derived entries.
_MISSION_TYPE_SINGULAR = "mission_type"
_MISSION_TYPE_PLURAL = "mission_types"

#: SINGLE SOURCE OF TRUTH (FR-030). Maps the singular URN kind to its plural
#: directory/universe form for every augmentation-eligible kind. Derived from
#: :class:`ArtifactKind` (minus ``template``) plus the mission-type extension —
#: no second kind enumeration is hand-maintained.
AUGMENTATION_ELIGIBLE_KINDS: dict[str, str] = {
    **{
        kind.value: kind.plural
        for kind in ArtifactKind
        if kind is not ArtifactKind.TEMPLATE
    },
    _MISSION_TYPE_SINGULAR: _MISSION_TYPE_PLURAL,
}

#: The relation set that augmentation/lineage edges may carry (T014). Extracted
#: as a module constant so adding a relation (e.g. ``specializes_from`` for
#: FR-001 lineage plumbing) is a one-line change rather than a hardcoded tuple
#: edit in two places (R-011-A). ``specializes_from`` is included so lineage
#: edges auto-emit through the same path as the augmentation pair.
AUGMENTATION_RELATIONS: tuple[Relation, ...] = (
    Relation.ENHANCES,
    Relation.OVERRIDES,
    Relation.SPECIALIZES_FROM,
)

#: The augmentation-eligible kinds that carry an internal action-sequence /
#: step-I/O topology, whose ``enhances`` field-merge has extra ordering- and
#: contract-preservation obligations (FR-029, T018, ADR 2026-05-16-1).
TOPOLOGY_KINDS: frozenset[str] = frozenset(
    {ArtifactKind.MISSION_STEP_CONTRACT.value, _MISSION_TYPE_SINGULAR}
)

#: File-discovery globs per plural directory for the legacy field-projection
#: emission path (see :func:`_collect_field_projection_edges`). Built from the
#: single source above; ``ArtifactKind.glob_pattern`` supplies the pattern for
#: every artifact kind, and mission types have no per-file glob (they are
#: authored as fragment edges only).
_AUGMENTATION_GLOBS: dict[str, str] = {
    kind.plural: kind.glob_pattern
    for kind in ArtifactKind
    if kind is not ArtifactKind.TEMPLATE
}


def augmentation_plural_kinds() -> frozenset[str]:
    """Return the plural directory names of all augmentation-eligible kinds.

    FR-030 single-source derivation: ``specify_cli.doctrine.pack_validator``
    imports this instead of re-declaring its own ``_AUGMENTATION_PLURAL_KINDS``
    table. Includes ``mission_step_contracts`` and ``mission_types`` (the
    newly-covered kinds, T015 / FR-032).
    """
    return frozenset(AUGMENTATION_ELIGIBLE_KINDS.values())


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OrgPackMissingError(Exception):
    """Raised when a configured org pack's ``local_path`` does not exist (FR-004).

    Mirrors Mission B FR-015 — missing org packs hard-fail at load time
    with an operator-actionable error. No silent fallback.
    """

    REMEDIATION: ClassVar[str] = (
        "Either fetch the pack (`spec-kitty doctrine fetch --pack <name>`) "
        "or remove the entry from `.kittify/config.yaml`."
    )

    def __init__(self, pack_name: str, configured_path: str | Path):
        self.pack_name = pack_name
        self.configured_path = str(configured_path)
        super().__init__(
            f"Org pack {pack_name!r} configured at {self.configured_path!r} "
            f"not found. {self.REMEDIATION}"
        )


class OrgPackParseError(Exception):
    """Raised when a pack's ``drg/fragment.yaml`` cannot be parsed as YAML.

    Operator-actionable: the message includes the offending file path and
    the underlying YAML error.
    """


class OrgPackSchemaError(Exception):
    """Raised when a pack's ``drg/fragment.yaml`` fails Pydantic validation.

    This covers unknown kinds (C-009 enforcement), extra fields, and type
    errors.  The message includes the offending file path and the Pydantic
    error details.
    """


# ---------------------------------------------------------------------------
# Private fragment-side node / edge models (contract YAML shape)
# ---------------------------------------------------------------------------


class _OrgDRGNode(BaseModel):
    """One node in an organisation-tier DRG fragment.

    Shape matches the contract YAML example: ``id`` + plural ``kind`` +
    ``title`` + optional ``body_path``. Distinct from
    ``doctrine.drg.models.DRGNode`` (URN-based). The merge bridges the two
    by minting URNs at merge time (handled in ``charter.drg``).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: str
    title: str | None = None
    body_path: str | None = None

    @field_validator("kind")
    @classmethod
    def _validate_kind(cls, value: str) -> str:
        if value not in _ORG_DRG_CANONICAL_KINDS:
            # "unknown kind" wording is binding per the contract example
            # at kitty-specs/.../contracts/contract-round-trip-frontmatter.md
            # (expect_message substring); do not weaken without updating
            # the contract.
            raise ValueError(
                f"unknown kind {value!r}: not in the canonical org-pack kind "
                f"universe (C-009 binding, FR-032 mission-type expansion): "
                f"{sorted(_ORG_DRG_CANONICAL_KINDS)}"
            )
        # Resolve legacy aliases (e.g. ``mission_step_contracts`` →
        # ``mission_steps``) to the canonical plural form so that downstream
        # code only ever sees the post-WP01 vocabulary.
        return _ORG_DRG_KIND_ALIASES.get(value, value)


class _OrgDRGEdge(BaseModel):
    """One typed edge in an organisation-tier DRG fragment.

    Mirrors the contract YAML example shape: ``source`` + ``target`` +
    ``relation`` (free-form string label; the merge bridges to
    ``doctrine.drg.models.Relation`` when possible, handled in
    ``charter.drg``). The optional ``reason`` field captures provenance for
    auto-emitted edges (FR-014, WP06 T036) and is accepted on hand-authored
    edges for audit purposes.
    """

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    relation: str
    reason: str | None = None


# ---------------------------------------------------------------------------
# Public fragment schema (FR-001)
# ---------------------------------------------------------------------------


class OrgDRGFragment(BaseModel):
    """A loaded organisation-tier DRG fragment with provenance metadata.

    One instance per configured ``organisation_packs:`` entry. The loader
    (:func:`load_org_pack`) produces a single fragment per pack root.
    ``layer_index`` (1..N) is assigned by the caller
    (``charter.drg.load_org_drg``) once it knows the declaration order.
    ``provenance_marker`` is the fixed string ``"org"`` — every node and
    edge from this fragment is tagged ``source: org:<pack_name>`` in the
    resolved DRG (see ``charter.drg.merge_three_layers``).
    """

    model_config = ConfigDict(extra="forbid")

    pack_name: str
    source_kind: Literal["local_path", "url", "package"]
    source_ref: str
    layer_index: int = Field(ge=1)
    provenance_marker: Literal["org"] = "org"
    nodes: list[_OrgDRGNode] = Field(default_factory=list)
    edges: list[_OrgDRGEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Per-pack loader (FR-001, FR-004)
# ---------------------------------------------------------------------------


def load_org_pack(
    pack_name: str,
    pack_root: Path,
    layer_index: int,
) -> OrgDRGFragment:
    """Read, parse, and validate a single org pack's DRG fragment.

    Parameters
    ----------
    pack_name:
        The operator-declared name for this pack (from
        ``.kittify/config.yaml``).  Used as the canonical name in the
        returned fragment and in error messages.
    pack_root:
        The resolved filesystem root of the org pack directory.  The
        function reads ``<pack_root>/drg/fragment.yaml``.
    layer_index:
        Declaration-order index (1..N) assigned by the caller.

    Returns
    -------
    OrgDRGFragment
        A validated fragment.  The ``pack_name``, ``source_kind``,
        ``source_ref``, and ``layer_index`` fields are set from the
        caller-supplied arguments, overriding any values present in the
        YAML file (per the operator-authority rule in the original
        ``charter.drg.load_org_drg`` implementation).

    Raises
    ------
    OrgPackMissingError:
        When ``pack_root`` does not exist, or when
        ``<pack_root>/drg/fragment.yaml`` is absent.
    OrgPackParseError:
        When the fragment YAML cannot be parsed.
    OrgPackSchemaError:
        When the parsed YAML fails :class:`OrgDRGFragment` validation
        (unknown kinds, extra fields, type errors, etc.).
    """
    if not pack_root.is_dir():
        raise OrgPackMissingError(pack_name, pack_root)

    fragment_yaml = pack_root / "drg" / "fragment.yaml"
    if not fragment_yaml.exists():
        raise OrgPackMissingError(pack_name, fragment_yaml)

    try:
        fragment_data = yaml.safe_load(fragment_yaml.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        raise OrgPackParseError(
            f"Org pack {pack_name!r}: YAML parse error in {fragment_yaml}: {exc}"
        ) from exc

    # Operator-side authoritative fields override pack-side declarations.
    # This is intentional: the loader knows the canonical pack name,
    # source kind, source_ref, and layer_index from the operator
    # configuration; the pack-side fragment.yaml's copies are advisory
    # and would be wrong if the operator renamed or relocated the pack.
    fragment_data["pack_name"] = pack_name
    fragment_data["source_kind"] = "local_path"
    fragment_data["source_ref"] = str(pack_root)
    fragment_data["layer_index"] = layer_index

    # FR-028..FR-032 augmentation/lineage emission. Per the locked authoring
    # decision (data-model §3, OQ-2-i) augmentation/lineage relationships are
    # **DRG-fragment edges** — the fragment author writes ``enhances`` /
    # ``overrides`` / ``specializes_from`` edges directly in ``edges:`` and they
    # flow through :class:`OrgDRGFragment` natively. This loader no longer
    # depends on artifact *fields* as the authority for those edges.
    #
    # During the migration window (WP06 removes the projection fields; WP07
    # migrates built-in/shipped field-authored relationships into fragment
    # edges) the field-projection path is RETAINED so already-shipped artifacts
    # keep emitting their edges. Both paths route through the single relation
    # source (:data:`AUGMENTATION_RELATIONS`) and are deduplicated against the
    # fragment-authored edges by ``(source, target, relation)``.
    existing_edges = fragment_data.setdefault("edges", []) or []
    seen: set[tuple[str, str, str]] = set()
    for edge in existing_edges:
        if isinstance(edge, dict):
            seen.add(
                (
                    str(edge.get("source", "")),
                    str(edge.get("target", "")),
                    str(edge.get("relation", "")),
                )
            )
    for auto_edge in _collect_augmentation_edges(pack_root):
        key = (auto_edge["source"], auto_edge["target"], auto_edge["relation"])
        if key in seen:
            continue
        existing_edges.append(auto_edge)
        seen.add(key)
    fragment_data["edges"] = existing_edges

    try:
        return OrgDRGFragment.model_validate(fragment_data)
    except Exception as exc:  # noqa: BLE001
        raise OrgPackSchemaError(
            f"Org pack {pack_name!r}: schema validation error in {fragment_yaml}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Field-projection emission helper (backward-compat, retired by WP06 / WP07)
# ---------------------------------------------------------------------------
#
# T014: the augmentation/lineage authority is the DRG fragment, not artifact
# fields. The fragment-authored edges are loaded natively by
# :class:`OrgDRGFragment`; this helper only emits the *projection* edges from
# any artifact that still carries ``enhances`` / ``overrides`` /
# ``specializes_from`` fields, so shipped artifacts keep working until WP06
# removes the fields and WP07 migrates the relationships into fragment edges.
# The relation list is data-driven from :data:`AUGMENTATION_RELATIONS` (no
# hardcoded ``("enhances", "overrides")`` tuple — R-011-A), and the per-file
# extraction is split out so this stays under ruff's C901 complexity limit.

#: Map the projection field name -> its canonical relation, derived from the
#: single relation source so adding a relation is a one-line change to
#: :data:`AUGMENTATION_RELATIONS`.
_PROJECTION_FIELD_TO_RELATION: dict[str, Relation] = {
    relation.value: relation for relation in AUGMENTATION_RELATIONS
}


def _augmentation_files(type_dir: Path, plural: str, glob: str) -> list[Path]:
    """Return augmentation-bearing files in *type_dir* (rglob for styleguides)."""
    if not type_dir.is_dir() or not glob:
        return []
    return (
        sorted(type_dir.rglob(glob))
        if plural == "styleguides"
        else sorted(type_dir.glob(glob))
    )


def _projection_edges_for_file(yaml_file: Path, urn_kind: str) -> list[dict[str, str]]:
    """Emit projection edges for one artifact file (best-effort).

    Reads the artifact's ``id`` and any augmentation/lineage field present,
    yielding one edge dict per declared relation. Malformed YAML or files
    missing the required keys are skipped silently — the pack validator
    surfaces those errors through its own paths.
    """
    try:
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(data, dict):
        return []
    art_id = data.get("id")
    if not isinstance(art_id, str) or not art_id:
        return []
    edges: list[dict[str, str]] = []
    for field_name, relation in _PROJECTION_FIELD_TO_RELATION.items():
        target = data.get(field_name)
        if not isinstance(target, str) or not target:
            continue
        edges.append(
            {
                "source": f"{urn_kind}:{art_id}",
                "target": f"{urn_kind}:{target}",
                "relation": relation.value,
                "reason": f"declared via {urn_kind}.{field_name} field",
            }
        )
    return edges


def _collect_augmentation_edges(pack_root: Path) -> list[dict[str, str]]:
    """Collect projection edges for every augmentation-eligible kind.

    Iterates the single-source :data:`AUGMENTATION_ELIGIBLE_KINDS` mapping so
    the four newly-covered kinds (directive, toolguide, mission_step_contract)
    project edges at parity with the original five (T015). Mission types carry
    no per-file glob and are authored as fragment edges only.
    """
    edges: list[dict[str, str]] = []
    for urn_kind, plural in AUGMENTATION_ELIGIBLE_KINDS.items():
        glob = _AUGMENTATION_GLOBS.get(plural, "")
        for yaml_file in _augmentation_files(pack_root / plural, plural, glob):
            edges.extend(_projection_edges_for_file(yaml_file, urn_kind))
    return edges


# ---------------------------------------------------------------------------
# Topology field-merge semantics (FR-029, T018, ADR 2026-05-16-1)
# ---------------------------------------------------------------------------


class TopologyMergeError(ValueError):
    """Raised when an ``enhances`` overlay would corrupt a topology artifact.

    FR-029 forbids silently reordering an action sequence or dropping a step
    input/output contract. When an overlay would do so, the merge fails closed
    rather than producing a corrupt artifact.
    """


def merge_topology_artifact(
    base: Mapping[str, Any],
    overlay: Mapping[str, Any],
    *,
    mode: Relation,
) -> dict[str, Any]:
    """Merge an org-pack overlay onto a built-in topology artifact (FR-029).

    Defines the field-merge semantics for the topology-bearing kinds
    (mission step contracts and mission types) consistent with ADR
    ``2026-05-16-1`` (field-level merge with the higher layer winning per
    field):

    * ``mode == Relation.OVERRIDES`` — full replacement: the overlay is
      returned as-is (validated by the caller's schema). The base is discarded.
    * ``mode == Relation.ENHANCES`` — field-level merge: overlay fields replace
      same-named base fields; fields absent from the overlay fall through to the
      base. The **action sequence** (``steps`` / ``actions``) is the topology
      backbone: if the overlay omits it, the base ordering is preserved
      verbatim; if the overlay supplies it, ordering is taken from the overlay
      but every base step id MUST still be present (no silent drop) and a step's
      input/output contract MUST NOT be removed. Violations raise
      :class:`TopologyMergeError` (fail closed, never silent corruption).

    Args:
        base: The built-in (lower-layer) artifact as a plain mapping.
        overlay: The org-pack (higher-layer) artifact as a plain mapping.
        mode: The augmentation relation driving the merge —
            :attr:`Relation.ENHANCES` or :attr:`Relation.OVERRIDES`.

    Returns:
        The merged artifact as a new dict (inputs are not mutated).

    Raises:
        TopologyMergeError: when an ``enhances`` overlay would reorder away or
            drop a base step, or strip a step's I/O contract.
        ValueError: when *mode* is not an augmentation relation.
    """
    if mode is Relation.OVERRIDES:
        return deepcopy(dict(overlay))
    if mode is not Relation.ENHANCES:
        raise ValueError(
            f"merge_topology_artifact only supports ENHANCES / OVERRIDES, "
            f"got {mode!r}"
        )

    merged: dict[str, Any] = {**deepcopy(dict(base)), **deepcopy(dict(overlay))}

    # The action-sequence field is whichever of ``steps`` / ``actions`` the
    # artifact uses (step contracts use ``steps``; mission types sequence their
    # actions). Both are preserved with the same invariant.
    for seq_field in ("steps", "actions"):
        base_seq = base.get(seq_field)
        if not isinstance(base_seq, list):
            continue
        overlay_seq = overlay.get(seq_field)
        if overlay_seq is None:
            # Overlay omitted the sequence -> base ordering preserved verbatim.
            merged[seq_field] = deepcopy(base_seq)
            continue
        if not isinstance(overlay_seq, list):
            raise TopologyMergeError(
                f"enhances overlay set {seq_field!r} to a non-list; an "
                f"action sequence must remain a list"
            )
        merged[seq_field] = _merge_action_sequence(base_seq, overlay_seq, seq_field)
    return merged


def _step_id(step: Any) -> str | None:
    """Return a step's identity (``id`` or ``title``) when it is a mapping."""
    if isinstance(step, Mapping):
        for key in ("id", "title"):
            value = step.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _merge_action_sequence(
    base_seq: list[Any],
    overlay_seq: list[Any],
    seq_field: str,
) -> list[Any]:
    """Field-merge two action sequences preserving ordering + step I/O (FR-029).

    Ordering follows the overlay, but every identifiable base step MUST appear
    in the overlay and its declared input/output contract MUST NOT be stripped.
    Steps the overlay does not mention fall through unchanged. Fails closed on
    any drop or I/O removal.
    """
    base_by_id = {sid: step for step in base_seq if (sid := _step_id(step))}
    overlay_ids = {sid for step in overlay_seq if (sid := _step_id(step))}

    dropped = sorted(set(base_by_id) - overlay_ids)
    if dropped:
        raise TopologyMergeError(
            f"enhances overlay silently drops {seq_field} step(s) {dropped} "
            f"from the base action sequence; declare 'overrides' for a full "
            f"replacement instead"
        )

    merged_seq: list[Any] = []
    for step in overlay_seq:
        sid = _step_id(step)
        base_step = base_by_id.get(sid) if sid is not None else None
        if isinstance(step, Mapping) and isinstance(base_step, Mapping):
            merged_step = {**deepcopy(dict(base_step)), **deepcopy(dict(step))}
            for io_field in ("inputs", "outputs"):
                base_io = base_step.get(io_field)
                # Only a *deliberate* empty restatement strips the contract;
                # omitting the field entirely preserves the base I/O (the merge
                # keeps the base value via the dict-merge above).
                if base_io and io_field in step and not step.get(io_field):
                    raise TopologyMergeError(
                        f"enhances overlay strips {io_field!r} from {seq_field} "
                        f"step {sid!r}; step input/output contracts must be "
                        f"preserved"
                    )
            merged_seq.append(merged_step)
        else:
            merged_seq.append(deepcopy(step))
    return merged_seq
