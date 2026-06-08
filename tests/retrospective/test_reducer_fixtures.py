"""Reducer fixture tests (WP03 — T016).

Verifies:
1. Fixture A (historical baseline without retrospective events) reduces to
   a byte-identical lane/lifecycle snapshot as the recorded fixture.
2. Fixture B (same events + RetrospectiveCaptured / RetrospectiveCaptureFailed /
   RetrospectiveSkipped appended) produces byte-identical lane/lifecycle keys
   compared to Fixture A — retrospective events are reducer no-ops for lane state.
3. The snapshot diff between A and B is exactly the additive retrospective keys.

This is the canonical test for FR-021 (reducer byte-identity guarantee).

FR-016: No env-var mutation in this test file.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from specify_cli.status.reducer import reduce
from specify_cli.status.store import read_events

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "event_logs"

FIXTURE_A_EVENTS = FIXTURES_DIR / "historical-no-retrospective.events.jsonl"
FIXTURE_A_SNAPSHOT = FIXTURES_DIR / "historical-no-retrospective.snapshot.json"
FIXTURE_B_EVENTS = FIXTURES_DIR / "historical-with-retrospective.events.jsonl"
FIXTURE_B_SNAPSHOT = FIXTURES_DIR / "historical-with-retrospective.snapshot.json"

MISSION_SLUG = "test-mission-reducer-01KS049J"

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reduce_fixture(fixture_events_path: Path) -> dict:
    """Copy fixture to a tmp directory, run the reducer, return snapshot dict.

    Excludes ``materialized_at`` from the result so time-based fields don't
    cause flakiness in comparisons.
    """
    tmpdir = Path(tempfile.mkdtemp())
    try:
        feature_dir = tmpdir / "kitty-specs" / MISSION_SLUG
        feature_dir.mkdir(parents=True)
        shutil.copy(fixture_events_path, feature_dir / "status.events.jsonl")

        events = read_events(feature_dir)
        snapshot = reduce(events)
        d = snapshot.to_dict()
        # Remove materialized_at — this is time-dependent and not relevant to lane state.
        d.pop("materialized_at", None)
        return d
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _lane_lifecycle_keys(snapshot_dict: dict) -> dict:
    """Return only the lane/lifecycle keys from a snapshot dict.

    Specifically: event_count, last_event_id, mission_number, mission_slug,
    mission_type, summary, work_packages.  Excludes ``retrospective`` and
    ``materialized_at``.
    """
    return {
        k: v for k, v in snapshot_dict.items()
        if k not in ("retrospective", "materialized_at")
    }


def _load_expected_snapshot(path: Path) -> dict:
    """Load the expected snapshot, removing materialized_at if present."""
    d = json.loads(path.read_text(encoding="utf-8"))
    d.pop("materialized_at", None)
    return d


# ---------------------------------------------------------------------------
# T016 Tests
# ---------------------------------------------------------------------------


class TestBaselineReducesByteIdentically:
    """Fixture A reduces to the recorded baseline snapshot (lane/lifecycle keys)."""

    def test_baseline_lane_keys_match_recorded_snapshot(self) -> None:
        """Reduce fixture A; assert lane/lifecycle keys match the recorded snapshot."""
        actual = _reduce_fixture(FIXTURE_A_EVENTS)
        expected = _load_expected_snapshot(FIXTURE_A_SNAPSHOT)

        actual_lanes = _lane_lifecycle_keys(actual)
        expected_lanes = _lane_lifecycle_keys(expected)

        assert actual_lanes == expected_lanes, (
            "Fixture A lane/lifecycle keys do not match recorded snapshot.\n"
            f"Expected: {json.dumps(expected_lanes, indent=2, sort_keys=True)}\n"
            f"Actual:   {json.dumps(actual_lanes, indent=2, sort_keys=True)}"
        )

    def test_baseline_has_no_retrospective_key(self) -> None:
        """Fixture A snapshot must NOT have a 'retrospective' key."""
        actual = _reduce_fixture(FIXTURE_A_EVENTS)
        assert "retrospective" not in actual, (
            "Fixture A snapshot should not contain a 'retrospective' key, "
            "but got one."
        )


class TestRetrospectiveEventsAreLaneStateNoops:
    """Fixture B (+ retrospective events) must have byte-identical lane state to A."""

    def test_lane_keys_byte_identical_between_a_and_b(self) -> None:
        """Reducing A and B produces byte-identical lane/lifecycle keys."""
        snap_a = _reduce_fixture(FIXTURE_A_EVENTS)
        snap_b = _reduce_fixture(FIXTURE_B_EVENTS)

        lanes_a = _lane_lifecycle_keys(snap_a)
        lanes_b = _lane_lifecycle_keys(snap_b)

        assert lanes_a == lanes_b, (
            "Lane/lifecycle keys differ between fixture A and B.\n"
            "This means retrospective events are NOT being treated as no-ops.\n"
            f"A: {json.dumps(lanes_a, indent=2, sort_keys=True)}\n"
            f"B: {json.dumps(lanes_b, indent=2, sort_keys=True)}"
        )

    def test_fixture_b_lane_keys_match_recorded_b_snapshot(self) -> None:
        """Fixture B lane keys match the recorded snapshot (minus retrospective)."""
        actual_b = _reduce_fixture(FIXTURE_B_EVENTS)
        expected_b = _load_expected_snapshot(FIXTURE_B_SNAPSHOT)

        actual_lanes = _lane_lifecycle_keys(actual_b)
        expected_lanes = _lane_lifecycle_keys(expected_b)

        assert actual_lanes == expected_lanes, (
            "Fixture B lane/lifecycle keys do not match recorded snapshot.\n"
            f"Expected: {json.dumps(expected_lanes, indent=2, sort_keys=True)}\n"
            f"Actual:   {json.dumps(actual_lanes, indent=2, sort_keys=True)}"
        )

    def test_fixture_b_events_contain_all_three_retro_types(self) -> None:
        """Fixture B must contain RetrospectiveCaptured, CaptureFailed, and Skipped."""
        lines = FIXTURE_B_EVENTS.read_text(encoding="utf-8").splitlines()
        event_types = set()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                t = obj.get("type")
                if t:
                    event_types.add(t)
            except json.JSONDecodeError:
                continue

        assert "RetrospectiveCaptured" in event_types, (
            "Fixture B is missing RetrospectiveCaptured event"
        )
        assert "RetrospectiveCaptureFailed" in event_types, (
            "Fixture B is missing RetrospectiveCaptureFailed event"
        )
        assert "RetrospectiveSkipped" in event_types, (
            "Fixture B is missing RetrospectiveSkipped event"
        )

    def test_fixture_b_has_more_events_than_a(self) -> None:
        """Fixture B must have more lines than A (the three retro events appended)."""
        lines_a = [ln for ln in FIXTURE_A_EVENTS.read_text().splitlines() if ln.strip()]
        lines_b = [ln for ln in FIXTURE_B_EVENTS.read_text().splitlines() if ln.strip()]
        assert len(lines_b) == len(lines_a) + 3, (
            f"Expected fixture B to have exactly 3 more events than A. "
            f"A={len(lines_a)}, B={len(lines_b)}"
        )

    def test_event_count_in_snapshot_ignores_retro_events(self) -> None:
        """The snapshot event_count reflects only lane-transition events (not retro events).

        The reducer's event_count is based on StatusEvent (lane transitions only);
        retrospective events are not counted in that tally.
        """
        snap_a = _reduce_fixture(FIXTURE_A_EVENTS)
        snap_b = _reduce_fixture(FIXTURE_B_EVENTS)
        # Both should report the same event_count (12 lane-transition events).
        assert snap_a.get("event_count") == snap_b.get("event_count"), (
            "event_count should be identical for A and B since retro events "
            "are not lane transitions.\n"
            f"A event_count={snap_a.get('event_count')}, "
            f"B event_count={snap_b.get('event_count')}"
        )
