"""Unit tests for the single planning-lane classifier seam.

These pin the shared predicates ``is_planning_lane`` / ``is_planning_artifact_only``
in :mod:`specify_cli.lanes.compute`. They are the one place lane classification
lives so the backing of "what counts as a planning lane" can later be swapped to a
charter / mission-type-derived surface (#1666) as a localized change.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from specify_cli.lanes.compute import (
    PLANNING_LANE_ID,
    is_planning_artifact_only,
    is_planning_lane,
)

pytestmark = pytest.mark.fast


def _lane(lane_id: str | None) -> SimpleNamespace:
    return SimpleNamespace(lane_id=lane_id)


def _manifest(*lane_ids: str | None) -> SimpleNamespace:
    return SimpleNamespace(lanes=[_lane(lid) for lid in lane_ids])


class TestIsPlanningLane:
    def test_planning_lane_id_is_planning(self) -> None:
        assert is_planning_lane(_lane(PLANNING_LANE_ID)) is True

    def test_code_lane_is_not_planning(self) -> None:
        assert is_planning_lane(_lane("lane-a")) is False

    def test_missing_lane_id_is_not_planning(self) -> None:
        assert is_planning_lane(_lane(None)) is False
        assert is_planning_lane(SimpleNamespace()) is False


class TestIsPlanningArtifactOnly:
    def test_planning_only_manifest_is_true(self) -> None:
        assert is_planning_artifact_only(_manifest(PLANNING_LANE_ID)) is True

    def test_mixed_planning_and_code_is_false(self) -> None:
        assert is_planning_artifact_only(_manifest(PLANNING_LANE_ID, "lane-a")) is False

    def test_code_only_manifest_is_false(self) -> None:
        assert is_planning_artifact_only(_manifest("lane-a", "lane-b")) is False

    def test_empty_lanes_is_false(self) -> None:
        assert is_planning_artifact_only(_manifest()) is False
        assert is_planning_artifact_only(SimpleNamespace(lanes=None)) is False

    def test_missing_lane_id_is_false(self) -> None:
        assert is_planning_artifact_only(_manifest(None)) is False
