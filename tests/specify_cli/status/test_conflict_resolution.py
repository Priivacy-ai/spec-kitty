"""Comprehensive tests for rollback-aware merge resolution and JSONL merge.

Tests cover:
- LANE_PRIORITY completeness and ordering
- Rollback detection heuristics
- Rollback-aware lane conflict resolution
- JSONL event log merge (concat, dedup, sort)
- Backward compatibility with existing 4-lane behavior
"""

from __future__ import annotations

import json

import pytest

from specify_cli.merge.status_resolver import (
    LANE_PRIORITY,
    _detect_rollback,
    extract_lane_value,
    is_status_file,
    resolve_jsonl_conflict,
    resolve_lane_conflict,
    resolve_lane_conflict_rollback_aware,
)


# ---------------------------------------------------------------------------
# LANE_PRIORITY Tests
# ---------------------------------------------------------------------------


class TestLanePriority:
    """Tests for the expanded LANE_PRIORITY map."""

    def test_all_canonical_lanes_present(self):
        """All 7 canonical lanes must be in LANE_PRIORITY."""
        canonical = {"planned", "claimed", "in_progress", "for_review", "done", "blocked", "canceled"}
        for lane in canonical:
            assert lane in LANE_PRIORITY, f"Missing canonical lane: {lane}"

    def test_doing_alias_present(self):
        """Legacy 'doing' alias must be in LANE_PRIORITY."""
        assert "doing" in LANE_PRIORITY

    def test_doing_alias_has_same_priority_as_in_progress(self):
        """'doing' must map to the same priority as 'in_progress'."""
        assert LANE_PRIORITY["doing"] == LANE_PRIORITY["in_progress"]

    def test_priority_ordering(self):
        """planned < claimed < in_progress < for_review < done."""
        assert LANE_PRIORITY["planned"] < LANE_PRIORITY["claimed"]
        assert LANE_PRIORITY["claimed"] < LANE_PRIORITY["in_progress"]
        assert LANE_PRIORITY["in_progress"] < LANE_PRIORITY["for_review"]
        assert LANE_PRIORITY["for_review"] < LANE_PRIORITY["done"]

    def test_blocked_lowest_priority(self):
        """'blocked' should have priority 0 (lowest)."""
        assert LANE_PRIORITY["blocked"] == 0

    def test_canceled_highest_priority(self):
        """'canceled' should be the highest monotonic priority."""
        assert LANE_PRIORITY["canceled"] > LANE_PRIORITY["done"]

    def test_total_count_is_eight(self):
        """7 canonical lanes + 1 'doing' alias = 8 entries total."""
        assert len(LANE_PRIORITY) == 8

    @pytest.mark.parametrize(
        "lane,expected_priority",
        [
            ("planned", 1),
            ("claimed", 2),
            ("in_progress", 3),
            ("for_review", 4),
            ("done", 5),
            ("blocked", 0),
            ("canceled", 6),
            ("doing", 3),
        ],
    )
    def test_specific_priority_values(self, lane, expected_priority):
        """Each lane has its expected numeric priority."""
        assert LANE_PRIORITY[lane] == expected_priority


# ---------------------------------------------------------------------------
# Rollback Detection Tests
# ---------------------------------------------------------------------------


class TestDetectRollback:
    """Tests for _detect_rollback() function."""

    def test_detect_rollback_has_feedback(self):
        """Content with review_status: 'has_feedback' is a rollback."""
        content = """---
lane: in_progress
review_status: "has_feedback"
reviewed_by: "alice"
---
# WP content
"""
        assert _detect_rollback(content) is True

    def test_detect_rollback_has_feedback_no_quotes(self):
        """review_status without quotes is also detected."""
        content = """---
lane: in_progress
review_status: has_feedback
---
"""
        assert _detect_rollback(content) is True

    def test_detect_rollback_has_feedback_single_quotes(self):
        """review_status with single quotes is also detected."""
        content = """---
lane: in_progress
review_status: 'has_feedback'
---
"""
        assert _detect_rollback(content) is True

    def test_detect_rollback_review_history(self):
        """Content with review-related history entry and backward lane."""
        content = """---
lane: in_progress
review_status: ""
---
# Content
history:
  - timestamp: "2026-01-05T10:00:00Z"
    action: review_changes_requested
    lane: in_progress
    agent: reviewer-bot
"""
        assert _detect_rollback(content) is True

    def test_detect_rollback_reviewed_by_backward(self):
        """Content with reviewed_by set and lane behind for_review."""
        content = """---
lane: in_progress
review_status: ""
reviewed_by: alice
---
"""
        assert _detect_rollback(content) is True

    def test_detect_rollback_reviewed_by_doing(self):
        """Content with reviewed_by and 'doing' lane (legacy alias)."""
        content = """---
lane: doing
reviewed_by: bob
---
"""
        assert _detect_rollback(content) is True

    def test_detect_rollback_reviewed_by_planned(self):
        """Content with reviewed_by and 'planned' lane."""
        content = """---
lane: planned
reviewed_by: carol
---
"""
        assert _detect_rollback(content) is True

    def test_detect_rollback_reviewed_by_claimed(self):
        """Content with reviewed_by and 'claimed' lane."""
        content = """---
lane: claimed
reviewed_by: dave
---
"""
        assert _detect_rollback(content) is True

    def test_detect_rollback_forward_progression(self):
        """Content with lane=done and no review signals is NOT a rollback."""
        content = """---
lane: done
review_status: ""
reviewed_by: ""
---
"""
        assert _detect_rollback(content) is False

    def test_detect_rollback_for_review_not_rollback(self):
        """Content with lane=for_review is forward movement, NOT a rollback."""
        content = """---
lane: for_review
review_status: ""
reviewed_by: ""
---
"""
        assert _detect_rollback(content) is False

    def test_detect_rollback_no_review_signals(self):
        """Content with lane=in_progress but no review signals is NOT a rollback."""
        content = """---
lane: in_progress
review_status: ""
reviewed_by: ""
---
"""
        assert _detect_rollback(content) is False

    def test_detect_rollback_reviewed_by_empty(self):
        """Empty reviewed_by is not a rollback signal."""
        content = """---
lane: in_progress
reviewed_by: ""
---
"""
        assert _detect_rollback(content) is False

    def test_detect_rollback_reviewed_by_for_review_lane(self):
        """reviewed_by set but lane is for_review (not backward)."""
        content = """---
lane: for_review
reviewed_by: alice
---
"""
        assert _detect_rollback(content) is False

    def test_detect_rollback_reviewed_by_done_lane(self):
        """reviewed_by set but lane is done (not backward)."""
        content = """---
lane: done
reviewed_by: alice
---
"""
        assert _detect_rollback(content) is False

    def test_detect_rollback_action_review_with_for_review_lane(self):
        """History mentions 'review' but lane is for_review (forward, not rollback)."""
        content = """---
lane: for_review
---
history:
  - timestamp: "2026-01-05T10:00:00Z"
    action: moved_to_review
    lane: for_review
    agent: worker-bot
"""
        assert _detect_rollback(content) is False


# ---------------------------------------------------------------------------
# Rollback-Aware Resolution Tests
# ---------------------------------------------------------------------------


class TestResolveLaneConflictRollbackAware:
    """Tests for resolve_lane_conflict_rollback_aware() function."""

    def test_rollback_beats_forward_progression(self):
        """Theirs has rollback to in_progress, ours has forward to done."""
        ours_content = """---
lane: done
review_status: ""
reviewed_by: ""
---
"""
        theirs_content = """---
lane: in_progress
review_status: "has_feedback"
reviewed_by: alice
---
"""
        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane="done",
            theirs_lane="in_progress",
        )
        assert result == "in_progress"

    def test_ours_rollback_beats_theirs_forward(self):
        """Ours has rollback, theirs is forward."""
        ours_content = """---
lane: in_progress
review_status: "has_feedback"
---
"""
        theirs_content = """---
lane: done
review_status: ""
reviewed_by: ""
---
"""
        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane="in_progress",
            theirs_lane="done",
        )
        assert result == "in_progress"

    def test_no_rollback_uses_monotonic(self):
        """Both sides have no rollback, highest priority wins."""
        ours_content = """---
lane: for_review
review_status: ""
reviewed_by: ""
---
"""
        theirs_content = """---
lane: in_progress
review_status: ""
reviewed_by: ""
---
"""
        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane="for_review",
            theirs_lane="in_progress",
        )
        assert result == "for_review"

    def test_no_rollback_theirs_wins_if_higher(self):
        """No rollback: theirs is higher priority, theirs wins."""
        ours_content = """---
lane: in_progress
review_status: ""
reviewed_by: ""
---
"""
        theirs_content = """---
lane: done
review_status: ""
reviewed_by: ""
---
"""
        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane="in_progress",
            theirs_lane="done",
        )
        assert result == "done"

    def test_both_rollback_picks_lower(self):
        """Both sides have rollback, lower priority lane wins."""
        ours_content = """---
lane: in_progress
review_status: "has_feedback"
reviewed_by: alice
---
"""
        theirs_content = """---
lane: for_review
review_status: "has_feedback"
reviewed_by: bob
---
"""
        # for_review (4) vs in_progress (3) -- in_progress is lower
        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane="in_progress",
            theirs_lane="for_review",
        )
        assert result == "in_progress"

    def test_both_rollback_theirs_lower(self):
        """Both rollbacks, theirs has the lower lane."""
        ours_content = """---
lane: for_review
review_status: "has_feedback"
---
"""
        theirs_content = """---
lane: planned
review_status: "has_feedback"
---
"""
        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane="for_review",
            theirs_lane="planned",
        )
        assert result == "planned"

    def test_same_lane_no_conflict(self):
        """Both sides have same lane, return either."""
        ours_content = """---
lane: in_progress
review_status: ""
reviewed_by: ""
---
"""
        theirs_content = """---
lane: in_progress
review_status: ""
reviewed_by: ""
---
"""
        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane="in_progress",
            theirs_lane="in_progress",
        )
        assert result == "in_progress"

    def test_unknown_lane_defaults_to_zero(self):
        """Unknown lane not in LANE_PRIORITY treated as priority 0."""
        ours_content = """---
lane: unknown_state
review_status: ""
reviewed_by: ""
---
"""
        theirs_content = """---
lane: planned
review_status: ""
reviewed_by: ""
---
"""
        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane="unknown_state",
            theirs_lane="planned",
        )
        # planned (1) > unknown_state (0), so planned wins in monotonic mode
        assert result == "planned"


# ---------------------------------------------------------------------------
# JSONL Merge Tests
# ---------------------------------------------------------------------------


class TestResolveJsonlConflict:
    """Tests for resolve_jsonl_conflict() function."""

    def test_merge_non_overlapping_events(self):
        """Two files with non-overlapping events produce merged sorted output."""
        ours = json.dumps({"event_id": "ev1", "at": "2026-01-01T10:00:00Z", "type": "lane_changed"}) + "\n"
        theirs = json.dumps({"event_id": "ev2", "at": "2026-01-02T11:00:00Z", "type": "lane_changed"}) + "\n"

        result = resolve_jsonl_conflict(ours, theirs)
        lines = result.strip().splitlines()
        assert len(lines) == 2

        events = [json.loads(line) for line in lines]
        assert events[0]["event_id"] == "ev1"
        assert events[1]["event_id"] == "ev2"

    def test_merge_duplicate_events(self):
        """Shared event_ids are deduplicated (first occurrence wins)."""
        event = {"event_id": "ev1", "at": "2026-01-01T10:00:00Z", "type": "lane_changed", "lane": "done"}
        ours = json.dumps(event) + "\n"
        theirs = json.dumps(event) + "\n"

        result = resolve_jsonl_conflict(ours, theirs)
        lines = result.strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["event_id"] == "ev1"

    def test_merge_sort_order(self):
        """Output is sorted by (at, event_id)."""
        ev_late = json.dumps({"event_id": "ev_z", "at": "2026-01-03T10:00:00Z", "type": "a"}) + "\n"
        ev_early = json.dumps({"event_id": "ev_a", "at": "2026-01-01T10:00:00Z", "type": "b"}) + "\n"
        ev_mid = json.dumps({"event_id": "ev_m", "at": "2026-01-02T10:00:00Z", "type": "c"}) + "\n"

        result = resolve_jsonl_conflict(ev_late + ev_mid, ev_early)
        lines = result.strip().splitlines()
        assert len(lines) == 3

        events = [json.loads(line) for line in lines]
        assert events[0]["event_id"] == "ev_a"
        assert events[1]["event_id"] == "ev_m"
        assert events[2]["event_id"] == "ev_z"

    def test_merge_same_timestamp_sorts_by_event_id(self):
        """Events with same timestamp are sorted by event_id."""
        ts = "2026-01-01T10:00:00Z"
        ev_b = json.dumps({"event_id": "ev_b", "at": ts, "type": "x"}) + "\n"
        ev_a = json.dumps({"event_id": "ev_a", "at": ts, "type": "y"}) + "\n"

        result = resolve_jsonl_conflict(ev_b, ev_a)
        lines = result.strip().splitlines()
        events = [json.loads(line) for line in lines]
        assert events[0]["event_id"] == "ev_a"
        assert events[1]["event_id"] == "ev_b"

    def test_merge_corrupted_line(self):
        """Corrupted JSON line is skipped, valid events preserved."""
        valid = json.dumps({"event_id": "ev1", "at": "2026-01-01T10:00:00Z", "type": "ok"}) + "\n"
        corrupted = "this is not json\n"

        result = resolve_jsonl_conflict(valid + corrupted, "")
        lines = result.strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["event_id"] == "ev1"

    def test_merge_empty_files(self):
        """Both empty inputs produce empty output."""
        result = resolve_jsonl_conflict("", "")
        assert result == ""

    def test_merge_one_empty(self):
        """One side empty, other side preserved."""
        event = json.dumps({"event_id": "ev1", "at": "2026-01-01T10:00:00Z", "type": "a"}) + "\n"

        result_ours_empty = resolve_jsonl_conflict("", event)
        assert "ev1" in result_ours_empty

        result_theirs_empty = resolve_jsonl_conflict(event, "")
        assert "ev1" in result_theirs_empty

    def test_merge_no_event_id_skipped(self):
        """Events without event_id are skipped."""
        no_id = json.dumps({"at": "2026-01-01T10:00:00Z", "type": "orphan"}) + "\n"
        with_id = json.dumps({"event_id": "ev1", "at": "2026-01-02T10:00:00Z", "type": "ok"}) + "\n"

        result = resolve_jsonl_conflict(no_id, with_id)
        lines = result.strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["event_id"] == "ev1"

    def test_merge_dedup_first_occurrence_wins(self):
        """When both sides have the same event_id, first (ours) occurrence wins."""
        ours_event = {"event_id": "ev1", "at": "2026-01-01T10:00:00Z", "lane": "done"}
        theirs_event = {"event_id": "ev1", "at": "2026-01-01T10:00:00Z", "lane": "in_progress"}

        result = resolve_jsonl_conflict(
            json.dumps(ours_event) + "\n",
            json.dumps(theirs_event) + "\n",
        )
        lines = result.strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["lane"] == "done"  # ours wins

    def test_output_ends_with_newline(self):
        """Non-empty output ends with trailing newline."""
        event = json.dumps({"event_id": "ev1", "at": "2026-01-01T10:00:00Z"}) + "\n"
        result = resolve_jsonl_conflict(event, "")
        assert result.endswith("\n")

    def test_output_uses_sort_keys(self):
        """Output JSON uses sorted keys for determinism."""
        event = {"event_id": "ev1", "at": "2026-01-01T10:00:00Z", "zebra": "z", "alpha": "a"}
        result = resolve_jsonl_conflict(json.dumps(event) + "\n", "")
        lines = result.strip().splitlines()
        parsed_line = lines[0]
        # Keys should appear in alphabetical order
        alpha_pos = parsed_line.index('"alpha"')
        at_pos = parsed_line.index('"at"')
        event_id_pos = parsed_line.index('"event_id"')
        zebra_pos = parsed_line.index('"zebra"')
        assert alpha_pos < at_pos < event_id_pos < zebra_pos


# ---------------------------------------------------------------------------
# STATUS_FILE_PATTERNS Tests
# ---------------------------------------------------------------------------


class TestStatusFilePatterns:
    """Tests for is_status_file() with JSONL support."""

    def test_matches_jsonl_event_log(self):
        """JSONL event log files match status file patterns."""
        assert is_status_file("kitty-specs/017-feature/status.events.jsonl")

    def test_matches_tasks_md(self):
        """Standard task files still match."""
        assert is_status_file("kitty-specs/feature/tasks.md")
        assert is_status_file("kitty-specs/feature/tasks/WP01.md")

    def test_rejects_non_status_files(self):
        """Non-status files are rejected."""
        assert not is_status_file("kitty-specs/feature/spec.md")
        assert not is_status_file("src/module.py")

    def test_rejects_non_kitty_jsonl(self):
        """JSONL files outside kitty-specs are rejected."""
        assert not is_status_file("logs/events.jsonl")
        assert not is_status_file("status.events.jsonl")


# ---------------------------------------------------------------------------
# Backward Compatibility Tests
# ---------------------------------------------------------------------------


class TestExistingBehaviorPreserved:
    """Tests that existing 4-lane conflicts still work correctly."""

    def test_existing_done_beats_doing(self):
        """Old behavior: done > doing (now in_progress equivalent)."""
        ours = "lane: done\n"
        theirs = "lane: doing\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert "done" in result

    def test_existing_for_review_beats_doing(self):
        """Old behavior: for_review > doing."""
        ours = "lane: doing\n"
        theirs = "lane: for_review\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert "for_review" in result

    def test_existing_doing_beats_planned(self):
        """Old behavior: doing > planned."""
        ours = "lane: doing\n"
        theirs = "lane: planned\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert "doing" in result

    def test_doing_alias_in_conflict_with_in_progress(self):
        """'doing' and 'in_progress' have same priority, ours wins."""
        ours = "lane: doing\n"
        theirs = "lane: in_progress\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        # Same priority, ours wins (existing behavior)
        assert extract_lane_value(result) == "doing"

    def test_in_progress_vs_doing_same_priority(self):
        """'in_progress' and 'doing' resolve to ours (same priority)."""
        ours = "lane: in_progress\n"
        theirs = "lane: doing\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert extract_lane_value(result) == "in_progress"

    def test_new_lanes_in_monotonic_resolution(self):
        """New lanes (claimed, blocked, canceled) work in monotonic resolution."""
        # claimed < in_progress
        ours = "lane: claimed\n"
        theirs = "lane: in_progress\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert extract_lane_value(result) == "in_progress"

        # canceled > done
        ours = "lane: canceled\n"
        theirs = "lane: done\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert extract_lane_value(result) == "canceled"

    def test_blocked_loses_to_everything(self):
        """blocked (priority 0) loses to all other lanes in monotonic mode."""
        ours = "lane: blocked\n"
        theirs = "lane: planned\n"
        result = resolve_lane_conflict(ours, theirs)
        assert result is not None
        assert extract_lane_value(result) == "planned"


# ---------------------------------------------------------------------------
# Parametrized Transition Pair Tests
# ---------------------------------------------------------------------------


class TestExhaustiveTransitionPairs:
    """Parametrized tests for all interesting lane transition pairs."""

    @pytest.mark.parametrize(
        "ours_lane,theirs_lane,expected_winner",
        [
            ("planned", "done", "done"),
            ("done", "planned", "done"),
            ("in_progress", "for_review", "for_review"),
            ("for_review", "in_progress", "for_review"),
            ("blocked", "claimed", "claimed"),
            ("claimed", "blocked", "claimed"),
            ("canceled", "done", "canceled"),
            ("done", "canceled", "canceled"),
            ("doing", "for_review", "for_review"),
            ("for_review", "doing", "for_review"),
        ],
    )
    def test_monotonic_resolution_pairs(self, ours_lane, theirs_lane, expected_winner):
        """No rollback: higher priority lane always wins."""
        ours_content = f'---\nlane: {ours_lane}\nreview_status: ""\nreviewed_by: ""\n---\n'
        theirs_content = f'---\nlane: {theirs_lane}\nreview_status: ""\nreviewed_by: ""\n---\n'

        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane=ours_lane,
            theirs_lane=theirs_lane,
        )
        assert result == expected_winner

    @pytest.mark.parametrize(
        "rollback_lane",
        [
            "planned",
            "claimed",
            "in_progress",
            "doing",
        ],
    )
    def test_rollback_always_beats_done(self, rollback_lane):
        """Any rollback (lane behind for_review) beats forward 'done'."""
        ours_content = '---\nlane: done\nreview_status: ""\nreviewed_by: ""\n---\n'
        theirs_content = f'---\nlane: {rollback_lane}\nreview_status: "has_feedback"\nreviewed_by: alice\n---\n'

        result = resolve_lane_conflict_rollback_aware(
            ours_content,
            theirs_content,
            ours_lane="done",
            theirs_lane=rollback_lane,
        )
        assert result == rollback_lane
