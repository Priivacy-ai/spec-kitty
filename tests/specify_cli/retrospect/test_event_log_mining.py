"""Tests for T039 / FR-010 (F-04): retrospective event-log mining heuristics.

These cover the new detectors added by WP10:
- ``_detect_force_overrides``  — operator-driven --force events (not bootstrap)
- ``_detect_arbiter_overrides`` — events whose note/reason mentions "arbiter"
- ``_detect_implementation_cycles`` — WPs that needed >1 planned→in_progress

The detectors must be pure functions over the event dicts and must NOT regress
the existing empty-output behaviour (a clean event log yields no findings).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]


from specify_cli.retrospective.generator import (
    _detect_arbiter_overrides,
    _detect_force_overrides,
    _detect_implementation_cycles,
    _is_arbiter_event,
    _is_force_override_event,
)


# ---------------------------------------------------------------------------
# _detect_force_overrides
# ---------------------------------------------------------------------------


class TestForceOverrideDetection:
    def test_finalize_tasks_force_is_excluded(self) -> None:
        """Bootstrap actors emit force=True legitimately; must NOT count."""
        events = [
            {
                "wp_id": "WP01",
                "actor": "finalize-tasks",
                "force": True,
                "from_lane": "planned",
                "to_lane": "planned",
                "event_id": "e1",
            },
        ]
        assert _detect_force_overrides(events) == {}

    def test_operator_force_counts(self) -> None:
        """User-driven --force on a real transition is an override."""
        events = [
            {
                "wp_id": "WP02",
                "actor": "claude",
                "force": True,
                "from_lane": "approved",
                "to_lane": "planned",
                "event_id": "e2",
            },
        ]
        assert _detect_force_overrides(events) == {"WP02": 1}

    def test_multiple_force_overrides_per_wp(self) -> None:
        events = [
            {
                "wp_id": "WP03",
                "actor": "claude",
                "force": True,
                "from_lane": "for_review",
                "to_lane": "in_progress",
                "event_id": "e3",
            },
            {
                "wp_id": "WP03",
                "actor": "user",
                "force": True,
                "from_lane": "approved",
                "to_lane": "planned",
                "event_id": "e4",
            },
        ]
        assert _detect_force_overrides(events) == {"WP03": 2}

    def test_no_op_force_is_excluded(self) -> None:
        """force=True with from_lane == to_lane carries no signal."""
        events = [
            {
                "wp_id": "WP04",
                "actor": "claude",
                "force": True,
                "from_lane": "in_progress",
                "to_lane": "in_progress",
                "event_id": "e5",
            },
        ]
        assert _detect_force_overrides(events) == {}

    def test_force_false_is_excluded(self) -> None:
        events = [
            {
                "wp_id": "WP05",
                "actor": "claude",
                "force": False,
                "from_lane": "planned",
                "to_lane": "in_progress",
                "event_id": "e6",
            },
        ]
        assert _detect_force_overrides(events) == {}

    def test_is_force_override_event_predicate(self) -> None:
        """The predicate itself is the deciding gate."""
        good = {
            "wp_id": "WP10",
            "actor": "claude",
            "force": True,
            "from_lane": "approved",
            "to_lane": "planned",
        }
        bootstrap = {
            "wp_id": "WP10",
            "actor": "finalize-tasks",
            "force": True,
            "from_lane": "planned",
            "to_lane": "planned",
        }
        assert _is_force_override_event(good) is True
        assert _is_force_override_event(bootstrap) is False


# ---------------------------------------------------------------------------
# _detect_arbiter_overrides
# ---------------------------------------------------------------------------


class TestArbiterOverrideDetection:
    def test_reason_contains_arbiter(self) -> None:
        events = [
            {
                "wp_id": "WP01",
                "actor": "claude",
                "reason": "Arbiter override after deadlock",
                "from_lane": "for_review",
                "to_lane": "approved",
                "event_id": "a1",
            },
        ]
        assert _detect_arbiter_overrides(events) == {"WP01": 1}

    def test_evidence_note_contains_arbiter(self) -> None:
        events = [
            {
                "wp_id": "WP02",
                "actor": "user",
                "evidence": {"note": "Arbiter intervened to break tie."},
                "from_lane": "for_review",
                "to_lane": "approved",
                "event_id": "a2",
            },
        ]
        assert _detect_arbiter_overrides(events) == {"WP02": 1}

    def test_no_arbiter_marker(self) -> None:
        events = [
            {
                "wp_id": "WP03",
                "actor": "claude",
                "reason": "Reviewer approved.",
                "from_lane": "for_review",
                "to_lane": "approved",
                "event_id": "a3",
            },
        ]
        assert _detect_arbiter_overrides(events) == {}

    def test_case_insensitive_match(self) -> None:
        events = [
            {
                "wp_id": "WP04",
                "actor": "user",
                "reason": "ARBITER OVERRIDE was required.",
                "from_lane": "for_review",
                "to_lane": "approved",
                "event_id": "a4",
            },
        ]
        assert _is_arbiter_event(events[0]) is True
        assert _detect_arbiter_overrides(events) == {"WP04": 1}


# ---------------------------------------------------------------------------
# _detect_implementation_cycles
# ---------------------------------------------------------------------------


class TestImplementationCycleDetection:
    def test_single_cycle_is_not_reported(self) -> None:
        """One implementation cycle is normal flow; only multi-cycle is interesting."""
        events = [
            {
                "wp_id": "WP01",
                "actor": "claude",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "event_id": "i1",
            },
        ]
        assert _detect_implementation_cycles(events) == {}

    def test_multiple_cycles_reported(self) -> None:
        events = [
            {
                "wp_id": "WP02",
                "actor": "claude",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "event_id": "i2",
            },
            {
                "wp_id": "WP02",
                "actor": "claude",
                "from_lane": "claimed",
                "to_lane": "in_progress",
                "event_id": "i3",
            },
            {
                "wp_id": "WP02",
                "actor": "claude",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "event_id": "i4",
            },
        ]
        assert _detect_implementation_cycles(events) == {"WP02": 3}

    def test_finalize_tasks_excluded(self) -> None:
        events = [
            {
                "wp_id": "WP03",
                "actor": "finalize-tasks",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "event_id": "i5",
            },
            {
                "wp_id": "WP03",
                "actor": "finalize-tasks",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "event_id": "i6",
            },
        ]
        assert _detect_implementation_cycles(events) == {}


# ---------------------------------------------------------------------------
# Empty-event-log regression guard (FR-010 stability invariant)
# ---------------------------------------------------------------------------


class TestEmptyLogStability:
    def test_no_events_yields_no_findings(self) -> None:
        assert _detect_force_overrides([]) == {}
        assert _detect_arbiter_overrides([]) == {}
        assert _detect_implementation_cycles([]) == {}

    def test_events_without_wp_id_are_skipped(self) -> None:
        """Mission-level events (no wp_id) must not break the detectors."""
        events = [
            {"actor": "user", "force": True, "from_lane": "x", "to_lane": "y"},
            {"actor": "user", "reason": "arbiter ruling"},
        ]
        assert _detect_force_overrides(events) == {}
        assert _detect_arbiter_overrides(events) == {}
        assert _detect_implementation_cycles(events) == {}
