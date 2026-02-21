"""Tests for canonical 7-lane SaaS fan-out.

Covers:
  T025 - All 7 canonical lanes pass through fan-out without collapse
  T026 - Invalid lane handling via TransitionError
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.status.emit import (
    TransitionError,
    _saas_fan_out,
    emit_status_transition,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.transitions import CANONICAL_LANES


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    """Create a minimal feature directory for tests."""
    fd = tmp_path / "kitty-specs" / "039-test-feature"
    fd.mkdir(parents=True)
    return fd


# ── T025: Canonical 7-lane fan-out ───────────────────────────


class TestCanonicalFanOut:
    """Verify _saas_fan_out passes all 7 canonical lanes directly without collapse."""

    def _make_event(
        self,
        *,
        from_lane: Lane = Lane.PLANNED,
        to_lane: Lane = Lane.CLAIMED,
    ) -> StatusEvent:
        return StatusEvent(
            event_id="01HXYZ0000000000000000TEST",
            feature_slug="039-test-feature",
            wp_id="WP01",
            from_lane=from_lane,
            to_lane=to_lane,
            at="2026-02-08T12:00:00Z",
            actor="test-actor",
            force=False,
            execution_mode="worktree",
        )

    @pytest.mark.parametrize(
        "from_lane,to_lane",
        [
            (Lane.PLANNED, Lane.CLAIMED),
            (Lane.CLAIMED, Lane.IN_PROGRESS),
            (Lane.IN_PROGRESS, Lane.FOR_REVIEW),
            (Lane.FOR_REVIEW, Lane.DONE),
            (Lane.PLANNED, Lane.BLOCKED),
            (Lane.IN_PROGRESS, Lane.BLOCKED),
            (Lane.PLANNED, Lane.CANCELED),
        ],
    )
    def test_fan_out_passes_canonical_lanes_directly(self, from_lane: Lane, to_lane: Lane) -> None:
        """Each canonical lane value is passed directly to emit_wp_status_changed."""
        event = self._make_event(from_lane=from_lane, to_lane=to_lane)
        mock_emit = MagicMock()
        with patch("specify_cli.sync.events.emit_wp_status_changed", mock_emit):
            _saas_fan_out(event, "039-test-feature", None)

        mock_emit.assert_called_once_with(
            wp_id="WP01",
            from_lane=str(from_lane),
            to_lane=str(to_lane),
            actor="test-actor",
            feature_slug="039-test-feature",
            policy_metadata=None,
        )

    def test_planned_to_claimed_now_emits(self) -> None:
        """planned->claimed is no longer a no-op (was collapsed to planned->planned)."""
        event = self._make_event(from_lane=Lane.PLANNED, to_lane=Lane.CLAIMED)
        mock_emit = MagicMock()
        with patch("specify_cli.sync.events.emit_wp_status_changed", mock_emit):
            _saas_fan_out(event, "039-test-feature", None)
        mock_emit.assert_called_once()

    def test_all_canonical_lanes_accepted_by_validators(self) -> None:
        """All 7 canonical lanes are valid values for from_lane/to_lane validators."""
        from specify_cli.sync.emitter import _PAYLOAD_RULES

        rules = _PAYLOAD_RULES["WPStatusChanged"]
        from_validator = rules["validators"]["from_lane"]
        to_validator = rules["validators"]["to_lane"]

        for lane in CANONICAL_LANES:
            assert from_validator(lane), f"from_lane validator rejected '{lane}'"
            assert to_validator(lane), f"to_lane validator rejected '{lane}'"


# ── T026: Invalid lane handling via TransitionError ───────────


class TestInvalidLaneHandling:
    """Ensure invalid lane values are rejected with TransitionError."""

    def test_invalid_to_lane_raises_transition_error(self, feature_dir: Path) -> None:
        """Completely unknown lane value raises TransitionError."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="NONEXISTENT",
                actor="tester",
            )

    def test_empty_to_lane_raises_transition_error(self, feature_dir: Path) -> None:
        """Empty string lane value raises TransitionError."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="",
                actor="tester",
            )

    def test_numeric_lane_raises_transition_error(self, feature_dir: Path) -> None:
        """Numeric lane value raises TransitionError."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="42",
                actor="tester",
            )

    def test_case_sensitive_rejection(self, feature_dir: Path) -> None:
        """Uppercase lane values that are not aliases are rejected."""
        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="Doing_stuff",
                actor="tester",
            )

    def test_invalid_lane_does_not_persist(self, feature_dir: Path) -> None:
        """Invalid lane rejection happens before any event persistence."""
        from specify_cli.status.store import EVENTS_FILENAME

        with pytest.raises(TransitionError):
            emit_status_transition(
                feature_dir=feature_dir,
                feature_slug="039-test-feature",
                wp_id="WP01",
                to_lane="bogus",
                actor="tester",
            )

        events_path = feature_dir / EVENTS_FILENAME
        assert not events_path.exists()
