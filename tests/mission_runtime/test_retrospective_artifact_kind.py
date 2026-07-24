"""Unit assertions for the ``RETROSPECTIVE`` PRIMARY-partition artifact kind.

Mission ``retrospective-durable-home-01KVYM1W`` WP02 (FR-002, NFR-001).

FR-002 adds a single ``RETROSPECTIVE`` member to :class:`MissionArtifactKind`
and to the ``_PRIMARY_ARTIFACT_KINDS`` partition so ``retrospective.yaml`` is
classified as a PRIMARY-partition artifact: it resolves to the durable
``kitty-specs/<slug>/`` home for EVERY topology (via the WP01 handle-safe
``primary_feature_dir_for_mission`` gated by :func:`is_primary_artifact_kind`)
and never transits the coordination branch.

These tests pin the partition membership as an explicit unit fact (FR-002), not
an integration side-effect, and confirm the classifier wires
``retrospective.yaml`` to the new kind so it is NOT treated as coordination
residue (PRIMARY, not residue).
"""
from __future__ import annotations

import pytest

from mission_runtime import (
    MissionArtifactKind,
    is_primary_artifact_kind,
    kind_for_mission_file,
)
from mission_runtime.artifacts import _PRIMARY_ARTIFACT_KINDS
from specify_cli.coordination.coherence import is_coord_residue_churn

# Schema/partition-membership guard (enum + classifier invariants). Selected by
# the `misc` integration shard's `(git_repo or integration or architectural)`
# marker expr; `unit` is selected by NO CI gate, so it ran in zero gates
# (gate-coverage orphan ratchet).
pytestmark = [pytest.mark.architectural]

_MISSION_SLUG = "retrospective-durable-home-01KVYM1W"


def test_retrospective_enum_value_is_retrospective() -> None:
    """Guard against a typo'd enum value (mirrors ``SPEC = "spec"``)."""
    assert MissionArtifactKind.RETROSPECTIVE.value == "retrospective"


def test_retrospective_is_in_primary_partition() -> None:
    """FR-002: ``RETROSPECTIVE`` is a member of the PRIMARY partition."""
    assert MissionArtifactKind.RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS


def test_is_primary_artifact_kind_true_for_retrospective() -> None:
    """The public predicate over the partition returns True for the new kind."""
    assert is_primary_artifact_kind(MissionArtifactKind.RETROSPECTIVE) is True


def test_retrospective_yaml_classifies_to_retrospective_kind() -> None:
    """The path classifier wires ``retrospective.yaml`` → ``RETROSPECTIVE``."""
    path = f"kitty-specs/{_MISSION_SLUG}/retrospective.yaml"

    assert kind_for_mission_file(path) is MissionArtifactKind.RETROSPECTIVE


def test_retrospective_yaml_is_not_coordination_residue() -> None:
    """Integration verification: ``retrospective.yaml`` is PRIMARY, not residue.

    A PRIMARY-partition artifact lives on the primary ``target_branch`` for every
    topology, so its primary-checkout copy is REAL content, never stale coord
    residue — the predicate must return False.
    """
    path = f"kitty-specs/{_MISSION_SLUG}/retrospective.yaml"

    assert is_coord_residue_churn(path) is False
