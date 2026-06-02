"""Single-source doctrine health model for ``spec-kitty doctor doctrine`` (WP08).

Both the human-readable renderer and the ``--json`` emitter consume one
:class:`DoctrineHealthReport`; neither assembles its own parallel view of the
data (research R-011-C found the old command built the two surfaces
independently and let pack health "green" on snapshot *presence* rather than on
whether every discovered profile actually loaded).

The two invariants this module enforces:

* **I-H1 (derived health):** a pack/layer is healthy iff every discovered
  profile loaded *and* there are no invalid-profile diagnostics
  (``valid_count == discovered_count and not invalid_profiles``).  Health is
  never inferred from snapshot presence (FR-010).
* **Single source:** :meth:`DoctrineHealthReport.to_dict` is the only JSON
  shape, and the human renderer reads the same dataclasses, so the two output
  surfaces can never drift.

Invalid-profile diagnostics are a verbatim passthrough of the WP05
:class:`~doctrine.agent_profiles.diagnostics.SkippedProfile` records returned by
``AgentProfileRepository.skipped_profiles()`` — they are *not* scraped from
warning text (FR-008/FR-009).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from doctrine.agent_profiles.diagnostics import SkippedProfile

__all__ = ["PackHealth", "DoctrineHealthReport", "build_pack_health_by_layer"]

#: Operator-facing reading order for doctrine layers.
_LAYER_ORDER: tuple[str, ...] = ("builtin", "org", "project")


def _skipped_to_dict(skipped: SkippedProfile) -> dict[str, object]:
    """Serialise one :class:`SkippedProfile` to a stable JSON dict.

    The field set is pinned (``layer``/``path``/``profile_id``/
    ``error_summary``) so downstream tooling can rely on it (T034 validation).
    """
    return {
        "layer": skipped.layer,
        "path": skipped.path,
        "profile_id": skipped.profile_id,
        "error_summary": skipped.error_summary,
    }


@dataclass(frozen=True)
class PackHealth:
    """Health of the agent-profile surface for a single doctrine layer.

    Attributes:
        pack_id: Stable identifier for the surface (the layer name, since
            agent-profile health is attributed per layer, not per org pack).
        layer: One of ``"builtin"``, ``"org"``, ``"project"``.
        discovered_count: Profile files discovered for this layer
            (valid + invalid).
        valid_count: Profile files that loaded successfully for this layer.
        invalid_profiles: WP05 ``SkippedProfile`` records for this layer
            (verbatim passthrough, never regex-scraped).
    """

    pack_id: str
    layer: str
    discovered_count: int
    valid_count: int
    invalid_profiles: list[SkippedProfile] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        """Derived health (I-H1 / FR-010).

        Healthy iff every discovered profile loaded *and* there are no
        invalid-profile diagnostics — never inferred from snapshot presence.
        """
        return self.valid_count == self.discovered_count and not self.invalid_profiles

    def to_dict(self) -> dict[str, object]:
        """JSON-able view; ``healthy`` is emitted explicitly for callers."""
        return {
            "pack_id": self.pack_id,
            "layer": self.layer,
            "discovered_count": self.discovered_count,
            "valid_count": self.valid_count,
            "healthy": self.healthy,
            "invalid_profiles": [
                _skipped_to_dict(profile) for profile in self.invalid_profiles
            ],
        }


@dataclass(frozen=True)
class DoctrineHealthReport:
    """Aggregate doctrine health consumed by both human and JSON surfaces.

    Attributes:
        packs: Per-layer agent-profile health (see :class:`PackHealth`).
        org_drg: Structured org-layer DRG state (configured packs, node/edge
            counts, collision warnings, errors) — produced once by the report
            builder so the human and JSON surfaces share a single org-DRG load.
    """

    packs: list[PackHealth] = field(default_factory=list)
    org_drg: dict[str, object] = field(default_factory=dict)

    @property
    def healthy(self) -> bool:
        """The whole doctrine surface is healthy iff every pack/layer is."""
        return all(pack.healthy for pack in self.packs)

    @property
    def invalid_profiles(self) -> list[SkippedProfile]:
        """Flattened invalid-profile diagnostics across all layers."""
        flattened: list[SkippedProfile] = []
        for pack in self.packs:
            flattened.extend(pack.invalid_profiles)
        return flattened

    def to_dict(self) -> dict[str, object]:
        """The single JSON shape for ``doctor doctrine --json``."""
        return {
            "healthy": self.healthy,
            "packs": [pack.to_dict() for pack in self.packs],
            "org_drg": self.org_drg,
        }


def build_pack_health_by_layer(
    *,
    provenance_by_layer: dict[str, int],
    skipped_profiles: list[SkippedProfile],
) -> list[PackHealth]:
    """Group valid + skipped profile counts into one :class:`PackHealth` per layer.

    Args:
        provenance_by_layer: ``{layer: valid_count}`` — number of profiles that
            loaded successfully for each layer (from
            ``AgentProfileRepository`` provenance).
        skipped_profiles: WP05 ``SkippedProfile`` diagnostics (any layer).

    Only layers that actually have profiles (valid or skipped) produce a
    ``PackHealth``; a layer with zero discovered profiles is omitted so the
    report does not invent empty surfaces.  ``discovered_count`` is the sum of
    valid + skipped for the layer, so ``healthy`` is purely derived (I-H1).
    """
    skipped_by_layer: dict[str, list[SkippedProfile]] = {}
    for skipped in skipped_profiles:
        skipped_by_layer.setdefault(skipped.layer, []).append(skipped)

    layers = set(provenance_by_layer) | set(skipped_by_layer)
    ordered = [layer for layer in _LAYER_ORDER if layer in layers]
    ordered.extend(sorted(layer for layer in layers if layer not in _LAYER_ORDER))

    packs: list[PackHealth] = []
    for layer in ordered:
        valid = provenance_by_layer.get(layer, 0)
        invalid = skipped_by_layer.get(layer, [])
        packs.append(
            PackHealth(
                pack_id=layer,
                layer=layer,
                discovered_count=valid + len(invalid),
                valid_count=valid,
                invalid_profiles=invalid,
            )
        )
    return packs
