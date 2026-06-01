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

from pathlib import Path
from typing import ClassVar, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "OrgDRGFragment",
    "OrgPackMissingError",
    "load_org_pack",
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
}

_ORG_DRG_CANONICAL_KINDS: frozenset[str] = frozenset(_ORG_DRG_KIND_ALIASES.keys())


# ---------------------------------------------------------------------------
# Auto-emit configuration (FR-014, mission
# charter-ux-and-org-pack-vocabulary-01KSAF14, WP06 T036)
# ---------------------------------------------------------------------------
# Map plural artifact directory -> (filename glob, singular URN kind).
# Only the 5 kinds that gained `enhances` / `overrides` fields in WP05 are
# scanned for auto-emission; other kinds carry no augmentation vocabulary.

_AUGMENTATION_PLURAL_TO_KIND: dict[str, tuple[str, str]] = {
    "tactics": ("*.tactic.yaml", "tactic"),
    "styleguides": ("*.styleguide.yaml", "styleguide"),
    "paradigms": ("*.paradigm.yaml", "paradigm"),
    "procedures": ("*.procedure.yaml", "procedure"),
    "agent_profiles": ("*.agent.yaml", "agent_profile"),
}


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
                f"unknown kind {value!r}: not in canonical 8-kind universe "
                f"(C-009 binding): {sorted(_ORG_DRG_CANONICAL_KINDS)}"
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

    # FR-014 (WP06 T036): auto-emit ENHANCES / OVERRIDES edges from
    # per-artifact declarative fields. Edges are appended to whatever the pack
    # author already wrote in fragment.yaml; duplicates (same source, target,
    # relation) are deduplicated so hand-authored copies do not collide with
    # the auto-emission.
    auto_edges = _collect_augmentation_edges(pack_root)
    if auto_edges:
        existing_edges = fragment_data.setdefault("edges", []) or []
        seen: set[tuple[str, str, str]] = set()
        for edge in existing_edges:
            if isinstance(edge, dict):
                key = (
                    str(edge.get("source", "")),
                    str(edge.get("target", "")),
                    str(edge.get("relation", "")),
                )
                seen.add(key)
        for auto_edge in auto_edges:
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
# Auto-emit helper (FR-014, WP06 T036)
# ---------------------------------------------------------------------------


def _collect_augmentation_edges(pack_root: Path) -> list[dict[str, str]]:
    """Scan pack artifact directories for ``enhances`` / ``overrides`` fields.

    Returns a list of edge dicts ready to drop into an ``OrgDRGFragment``'s
    ``edges`` list. Each entry has ``source``, ``target``, ``relation``, and
    ``reason`` keys. The function is best-effort: malformed YAML or files
    missing required keys are silently skipped (the pack validator surfaces
    those errors via its own paths).
    """
    edges: list[dict[str, str]] = []
    for plural, (glob, urn_kind) in _AUGMENTATION_PLURAL_TO_KIND.items():
        type_dir = pack_root / plural
        if not type_dir.is_dir():
            continue
        # Use rglob for styleguides (nested) and plain glob for the rest, to
        # mirror the pack validator's file-discovery rules.
        files = (
            sorted(type_dir.rglob(glob))
            if plural == "styleguides"
            else sorted(type_dir.glob(glob))
        )
        for yaml_file in files:
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                continue
            if not isinstance(data, dict):
                continue
            art_id = data.get("id")
            if not isinstance(art_id, str) or not art_id:
                continue
            for field_name, relation in (
                ("enhances", "enhances"),
                ("overrides", "overrides"),
            ):
                target = data.get(field_name)
                if not isinstance(target, str) or not target:
                    continue
                edges.append(
                    {
                        "source": f"{urn_kind}:{art_id}",
                        "target": f"{urn_kind}:{target}",
                        "relation": relation,
                        "reason": f"declared via {urn_kind}.{field_name} field",
                    }
                )
    return edges
