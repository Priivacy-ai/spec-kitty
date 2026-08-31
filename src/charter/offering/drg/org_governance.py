"""Org-tier governance-profile scope-edge extraction (#3629, WP03 / T014).

Built-in mission types project their type-wide ``governance-profile.yaml``
``selected_*`` selections into ``mission_type --scope--> <artifact>`` DRG edges
via
:func:`charter.offering.drg.migration.extractor.extract_governance_profile_scope_edges`.
Org packs carry the SAME governance grain at a DIFFERENT path shape --
``<pack_root>/mission_types/<type>/governance-profile.yaml`` (per
``charter.activation.mission_type_profiles._resolve_governance_slot``) -- which no
extraction pass ever read. So an org-tier ``selected_*`` typo reached no DRG
edge at all: it was neither minted (the built-in extractor globs only the
built-in missions root) nor guarded (a total no-op, not even a silent prune).

This module reads that org-tier path and returns the scope-edge selections so
they enter the merged DRG through the org-pack fragment path
(:func:`charter.offering.drg.org_pack_loader.load_org_pack`). The post-merge fail-loud
escalation needs no dedicated guard: an unresolved selection is minted as a
dangling ``mission_type --scope--> <artifact>`` edge, which
:func:`charter.offering.drg.validator.validate_dangling_references` (run by
``assert_valid`` inside :func:`charter.activation._drg_helpers.load_validated_graph`) raises
on. The escalation cannot live here anyway: a pre-merge single-pack read cannot
see built-in targets, so it would false-positive on every legitimate reference
into the built-in layer (squad finding G1).

The ``selected_*`` field -> target-kind mapping is IMPORTED from the built-in
extractor
(:data:`~charter.offering.drg.migration.extractor._GOVERNANCE_PROFILE_SCOPE_FIELDS`),
never copied: a hand-copy would be a second source of truth for the one table
(the exact drift this mission removes -- squad finding G2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

import yaml

from charter.offering.drg.migration.extractor import _GOVERNANCE_PROFILE_SCOPE_FIELDS
from charter.offering.drg.migration.id_normalizer import artifact_to_urn

__all__ = ["collect_org_governance_scope_edges"]


class OrgGovernanceScopeEdge(NamedTuple):
    """One org-tier ``mission_type --scope--> <artifact>`` governance selection.

    Carries fully-qualified endpoint URNs plus the machine-provenance text the
    org-pack loader stamps onto the projected fragment edge. The relation is
    always ``scope`` (a governance selection is a scope edge), so it is implied
    rather than stored.
    """

    source: str
    target: str
    generated_reason: str


def _load_profile(path: Path) -> dict[str, Any] | None:
    """Best-effort read of one ``governance-profile.yaml`` into a mapping.

    Malformed YAML or a non-mapping document yields ``None`` so a broken
    per-type profile is skipped rather than crashing the whole pack load; the
    pack validator surfaces authoring errors through its own paths.
    """
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def collect_org_governance_scope_edges(pack_root: Path) -> list[OrgGovernanceScopeEdge]:
    """Read a pack's per-type governance profiles into scope-edge selections.

    Globs ``<pack_root>/mission_types/*/governance-profile.yaml`` and, for each
    ``selected_*`` list field named in
    :data:`_GOVERNANCE_PROFILE_SCOPE_FIELDS`, returns one
    :class:`OrgGovernanceScopeEdge` per bare id. Returns an empty list when the
    pack declares no ``mission_types/`` directory (the common case: an org pack
    that contributes no mission-type governance).

    Endpoints are minted as fully-qualified URNs (via :func:`artifact_to_urn`,
    which normalises directive ids and passes every other kind through), so the
    org-pack merge accepts them verbatim and re-checks them against the fully
    assembled node set -- exactly the deferral the built-in tier already relies
    on.
    """
    edges: list[OrgGovernanceScopeEdge] = []
    mission_types_dir = pack_root / "mission_types"
    if not mission_types_dir.is_dir():
        return edges

    seen: set[tuple[str, str]] = set()
    for profile_path in sorted(mission_types_dir.glob("*/governance-profile.yaml")):
        data = _load_profile(profile_path)
        if data is None:
            continue
        raw_type = data.get("mission_type") or data.get("id") or profile_path.parent.name
        source_urn = artifact_to_urn("mission_type", str(raw_type))
        edges.extend(_profile_scope_edges(data, source_urn, seen))
    return edges


def _profile_scope_edges(
    data: dict[str, Any],
    source_urn: str,
    seen: set[tuple[str, str]],
) -> list[OrgGovernanceScopeEdge]:
    """Yield the scope edges for one already-loaded governance profile.

    Extracted from :func:`collect_org_governance_scope_edges` so the outer loop
    stays flat (ruff C901 <= 15). *seen* is threaded across profiles so a repeat
    of the same ``(mission_type, target)`` selection is emitted once.
    """
    edges: list[OrgGovernanceScopeEdge] = []
    for field_name, kind in _GOVERNANCE_PROFILE_SCOPE_FIELDS:
        for raw_id in data.get(field_name) or []:
            if not isinstance(raw_id, str) or not raw_id:
                continue
            target_urn = artifact_to_urn(kind, raw_id)
            triple = (source_urn, target_urn)
            if triple in seen:
                continue
            seen.add(triple)
            edges.append(
                OrgGovernanceScopeEdge(
                    source=source_urn,
                    target=target_urn,
                    generated_reason=(
                        f"declared via governance-profile.yaml {field_name} selection"
                    ),
                )
            )
    return edges
