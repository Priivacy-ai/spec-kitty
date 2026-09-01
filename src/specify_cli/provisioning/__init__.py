"""Fail-closed default-charter provisioning for fresh-init projects.

Mission ``resolution-activation-foundation-01KZ9FKG`` WP03 (FR-009/010/011,
NFR-004). Today ``spec-kitty init`` writes no ``mission_type_activations``
key at all, relying on an implicit config-absent backfill elsewhere in the
charter runtime. That implicit backfill is removed in WP04; this package is
its load-bearing prerequisite: it seeds a brand-new project's
``.kittify/config.yaml`` with an explicit, non-empty ``mission_type_activations``
list **copied** from the shipped ``src/charter/activation/packs/default.yaml`` (never
re-derived by scanning the mission-type catalog), and fails closed with an
actionable error if that shipped pack cannot be found.
"""

from __future__ import annotations

from specify_cli.provisioning.default_charter import (
    DefaultCharterPackMissingError,
    provision_default_mission_type_activations,
)

__all__ = [
    "DefaultCharterPackMissingError",
    "provision_default_mission_type_activations",
]
