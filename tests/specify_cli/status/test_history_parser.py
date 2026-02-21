"""Tests for the history parser module.

Covers all subtasks T001-T007: dataclasses, normalize_entries,
collapse_duplicates, pair_transitions, gap_fill, extract_done_evidence,
and build_transition_chain.
"""

from __future__ import annotations

import pytest

from specify_cli.status.history_parser import (
    NormalizedHistoryEntry,
    Transition,
    TransitionChain,
    build_transition_chain,
    collapse_duplicates,
    extract_done_evidence,
    gap_fill,
    normalize_entries,
    pair_transitions,
)
from specify_cli.status.models import DoneEvidence, ReviewApproval


# ─── T001: Dataclass Tests ────────────────────────────────────────────


class TestNormalizedHistoryEntry:
    def test_frozen(self) -> None:
        entry = NormalizedHistoryEntry(timestamp="2026-01-01T00:00:00Z", lane="planned", actor="system")
        with pytest.raises(AttributeError):
            entry.lane = "done"  # type: ignore[misc]

    def test_fields(self) -> None:
        entry = NormalizedHistoryEntry(timestamp="2026-01-01T00:00:00Z", lane="in_progress", actor="claude")
        assert entry.timestamp == "2026-01-01T00:00:00Z"
        assert entry.lane == "in_progress"
        assert entry.actor == "claude"


class TestTransition:
    def test_frozen(self) -> None:
        t = Transition(
            from_lane="planned",
            to_lane="in_progress",
            timestamp="2026-01-01T00:00:00Z",
            actor="claude",
        )
        with pytest.raises(AttributeError):
            t.to_lane = "done"  # type: ignore[misc]

    def test_evidence_defaults_to_none(self) -> None:
        t = Transition(
            from_lane="planned",
            to_lane="in_progress",
            timestamp="2026-01-01T00:00:00Z",
            actor="claude",
        )
        assert t.evidence is None

    def test_evidence_can_be_set(self) -> None:
        evidence = DoneEvidence(review=ReviewApproval(reviewer="bob", verdict="approved", reference="test"))
        t = Transition(
            from_lane="for_review",
            to_lane="done",
            timestamp="2026-01-01T00:00:00Z",
            actor="bob",
            evidence=evidence,
        )
        assert t.evidence is not None
        assert t.evidence.review.reviewer == "bob"


class TestTransitionChain:
    def test_mutable(self) -> None:
        chain = TransitionChain(transitions=[], history_entries=0, has_evidence=False)
        chain.transitions.append(
            Transition(
                from_lane="planned",
                to_lane="done",
                timestamp="2026-01-01T00:00:00Z",
                actor="test",
            )
        )
        assert len(chain.transitions) == 1

    def test_fields(self) -> None:
        chain = TransitionChain(transitions=[], history_entries=5, has_evidence=True)
        assert chain.history_entries == 5
        assert chain.has_evidence is True


# ─── T002: normalize_entries() Tests ──────────────────────────────────


class TestNormalizeEntries:
    def test_basic_format_a(self) -> None:
        history = [
            {
                "timestamp": "2026-01-01T10:00:00Z",
                "lane": "planned",
                "agent": "system",
                "shell_pid": "",
                "action": "Prompt generated",
            },
            {
                "timestamp": "2026-01-01T11:00:00Z",
                "lane": "doing",
                "agent": "claude-code",
                "shell_pid": "32403",
                "action": "Started",
            },
        ]
        result = normalize_entries(history)
        assert len(result) == 2
        assert result[0].lane == "planned"
        assert result[0].actor == "system"
        assert result[1].lane == "in_progress"  # doing -> in_progress
        assert result[1].actor == "claude-code"

    def test_empty_history(self) -> None:
        assert normalize_entries([]) == []

    def test_skips_non_dict_entries(self) -> None:
        history = ["not a dict", 42, None, {"lane": "planned", "agent": "sys"}]
        result = normalize_entries(history)
        assert len(result) == 1
        assert result[0].lane == "planned"

    def test_skips_missing_lane(self) -> None:
        history = [
            {"agent": "system", "timestamp": "2026-01-01T00:00:00Z"},
        ]
        result = normalize_entries(history)
        assert len(result) == 0

    def test_skips_empty_lane(self) -> None:
        history = [
            {"lane": "", "agent": "system", "timestamp": "2026-01-01T00:00:00Z"},
        ]
        result = normalize_entries(history)
        assert len(result) == 0

    def test_fallback_actor_when_missing(self) -> None:
        history = [{"lane": "planned", "timestamp": "2026-01-01T00:00:00Z"}]
        result = normalize_entries(history)
        assert result[0].actor == "migration"

    def test_fallback_actor_when_empty(self) -> None:
        history = [{"lane": "planned", "agent": "", "timestamp": "2026-01-01T00:00:00Z"}]
        result = normalize_entries(history)
        assert result[0].actor == "migration"

    def test_fallback_timestamp_when_missing(self) -> None:
        history = [{"lane": "planned", "agent": "system"}]
        result = normalize_entries(history)
        assert result[0].timestamp != ""
        # Should be a valid ISO timestamp
        assert "T" in result[0].timestamp

    def test_preserves_order(self) -> None:
        history = [
            {"lane": "planned", "agent": "a", "timestamp": "2026-01-01T01:00:00Z"},
            {"lane": "doing", "agent": "b", "timestamp": "2026-01-01T02:00:00Z"},
            {"lane": "for_review", "agent": "c", "timestamp": "2026-01-01T03:00:00Z"},
        ]
        result = normalize_entries(history)
        assert [e.lane for e in result] == ["planned", "in_progress", "for_review"]
        assert [e.actor for e in result] == ["a", "b", "c"]

    def test_alias_resolution(self) -> None:
        history = [
            {"lane": "doing", "agent": "sys", "timestamp": "2026-01-01T00:00:00Z"},
        ]
        result = normalize_entries(history)
        assert result[0].lane == "in_progress"

    def test_lane_with_whitespace(self) -> None:
        history = [
            {"lane": "  doing  ", "agent": "sys", "timestamp": "2026-01-01T00:00:00Z"},
        ]
        result = normalize_entries(history)
        assert result[0].lane == "in_progress"


# ─── T003: collapse_duplicates() Tests ────────────────────────────────


class TestCollapseDuplicates:
    def test_no_duplicates(self) -> None:
        entries = [
            NormalizedHistoryEntry("t1", "planned", "a"),
            NormalizedHistoryEntry("t2", "in_progress", "b"),
            NormalizedHistoryEntry("t3", "for_review", "c"),
        ]
        result = collapse_duplicates(entries)
        assert len(result) == 3
        assert [e.lane for e in result] == ["planned", "in_progress", "for_review"]

    def test_consecutive_duplicates_collapsed(self) -> None:
        entries = [
            NormalizedHistoryEntry("t1", "planned", "a"),
            NormalizedHistoryEntry("t2", "planned", "b"),
            NormalizedHistoryEntry("t3", "in_progress", "c"),
            NormalizedHistoryEntry("t4", "in_progress", "d"),
            NormalizedHistoryEntry("t5", "for_review", "e"),
        ]
        result = collapse_duplicates(entries)
        assert len(result) == 3
        assert [e.lane for e in result] == ["planned", "in_progress", "for_review"]
        # First occurrence of each lane is kept
        assert result[0].actor == "a"
        assert result[1].actor == "c"
        assert result[2].actor == "e"

    def test_empty_list(self) -> None:
        assert collapse_duplicates([]) == []

    def test_single_entry(self) -> None:
        entries = [NormalizedHistoryEntry("t1", "planned", "a")]
        result = collapse_duplicates(entries)
        assert len(result) == 1

    def test_non_consecutive_same_lane_kept(self) -> None:
        entries = [
            NormalizedHistoryEntry("t1", "planned", "a"),
            NormalizedHistoryEntry("t2", "in_progress", "b"),
            NormalizedHistoryEntry("t3", "planned", "c"),
        ]
        result = collapse_duplicates(entries)
        assert len(result) == 3
        assert [e.lane for e in result] == ["planned", "in_progress", "planned"]

    def test_all_same_lane(self) -> None:
        entries = [
            NormalizedHistoryEntry("t1", "planned", "a"),
            NormalizedHistoryEntry("t2", "planned", "b"),
            NormalizedHistoryEntry("t3", "planned", "c"),
        ]
        result = collapse_duplicates(entries)
        assert len(result) == 1
        assert result[0].actor == "a"


# ─── T004: pair_transitions() Tests ───────────────────────────────────


class TestPairTransitions:
    def test_basic_pairing(self) -> None:
        entries = [
            NormalizedHistoryEntry("t1", "planned", "system"),
            NormalizedHistoryEntry("t2", "in_progress", "claude"),
            NormalizedHistoryEntry("t3", "for_review", "claude"),
        ]
        result = pair_transitions(entries)
        assert len(result) == 2

        assert result[0].from_lane == "planned"
        assert result[0].to_lane == "in_progress"
        assert result[0].timestamp == "t2"
        assert result[0].actor == "claude"

        assert result[1].from_lane == "in_progress"
        assert result[1].to_lane == "for_review"
        assert result[1].timestamp == "t3"
        assert result[1].actor == "claude"

    def test_single_entry_no_transitions(self) -> None:
        entries = [NormalizedHistoryEntry("t1", "planned", "system")]
        result = pair_transitions(entries)
        assert result == []

    def test_empty_entries_no_transitions(self) -> None:
        result = pair_transitions([])
        assert result == []

    def test_no_evidence_on_raw_pairs(self) -> None:
        entries = [
            NormalizedHistoryEntry("t1", "planned", "a"),
            NormalizedHistoryEntry("t2", "done", "b"),
        ]
        result = pair_transitions(entries)
        assert len(result) == 1
        assert result[0].evidence is None

    def test_uses_target_entry_timestamp_and_actor(self) -> None:
        entries = [
            NormalizedHistoryEntry("2026-01-01T10:00:00Z", "planned", "system"),
            NormalizedHistoryEntry("2026-01-01T11:00:00Z", "in_progress", "agent-x"),
        ]
        result = pair_transitions(entries)
        assert result[0].timestamp == "2026-01-01T11:00:00Z"
        assert result[0].actor == "agent-x"


# ─── T005: gap_fill() Tests ──────────────────────────────────────────


class TestGapFill:
    def test_no_history_planned_current(self) -> None:
        """Case 1: No history, current is planned -> no transitions."""
        result = gap_fill([], None, "planned", "2026-01-01T00:00:00Z")
        assert result == []

    def test_no_history_non_planned_current(self) -> None:
        """Case 2: No history, current is not planned -> bootstrap transition."""
        result = gap_fill([], None, "done", "2026-01-01T00:00:00Z")
        assert len(result) == 1
        assert result[0].from_lane == "planned"
        assert result[0].to_lane == "done"
        assert result[0].actor == "migration"
        assert result[0].timestamp == "2026-01-01T00:00:00Z"

    def test_last_matches_current(self) -> None:
        """Case 3: Last history lane matches current -> unchanged."""
        existing = [
            Transition("planned", "in_progress", "t1", "claude"),
        ]
        result = gap_fill(existing, "in_progress", "in_progress", "t2")
        assert result == existing

    def test_last_differs_from_current(self) -> None:
        """Case 4: Last history lane differs from current -> append gap-fill."""
        existing = [
            Transition("planned", "in_progress", "t1", "claude"),
        ]
        result = gap_fill(existing, "in_progress", "done", "2026-01-01T12:00:00Z")
        assert len(result) == 2
        assert result[0] == existing[0]
        assert result[1].from_lane == "in_progress"
        assert result[1].to_lane == "done"
        assert result[1].actor == "migration"
        assert result[1].timestamp == "2026-01-01T12:00:00Z"

    def test_does_not_mutate_input(self) -> None:
        """gap_fill should not modify the input list."""
        existing = [Transition("planned", "in_progress", "t1", "claude")]
        original_len = len(existing)
        gap_fill(existing, "in_progress", "done", "t2")
        assert len(existing) == original_len

    def test_no_history_in_progress_current(self) -> None:
        """Bootstrap transition for a WP found in_progress with no history."""
        result = gap_fill([], None, "in_progress", "2026-01-01T00:00:00Z")
        assert len(result) == 1
        assert result[0].from_lane == "planned"
        assert result[0].to_lane == "in_progress"


# ─── T006: extract_done_evidence() Tests ─────────────────────────────


class TestExtractDoneEvidence:
    def test_approved_with_reviewer(self) -> None:
        frontmatter = {
            "review_status": "approved",
            "reviewed_by": "alice",
        }
        result = extract_done_evidence(frontmatter, "WP01")
        assert result is not None
        assert isinstance(result, DoneEvidence)
        assert result.review.reviewer == "alice"
        assert result.review.verdict == "approved"
        assert result.review.reference == "frontmatter-migration:WP01"

    def test_no_review_status(self) -> None:
        frontmatter = {"reviewed_by": "alice"}
        assert extract_done_evidence(frontmatter, "WP01") is None

    def test_wrong_review_status(self) -> None:
        frontmatter = {"review_status": "rejected", "reviewed_by": "alice"}
        assert extract_done_evidence(frontmatter, "WP01") is None

    def test_empty_reviewed_by(self) -> None:
        frontmatter = {"review_status": "approved", "reviewed_by": ""}
        assert extract_done_evidence(frontmatter, "WP01") is None

    def test_missing_reviewed_by(self) -> None:
        frontmatter = {"review_status": "approved"}
        assert extract_done_evidence(frontmatter, "WP01") is None

    def test_whitespace_reviewed_by(self) -> None:
        frontmatter = {"review_status": "approved", "reviewed_by": "  "}
        assert extract_done_evidence(frontmatter, "WP01") is None

    def test_reviewed_by_with_whitespace_trimmed(self) -> None:
        frontmatter = {"review_status": "approved", "reviewed_by": "  bob  "}
        result = extract_done_evidence(frontmatter, "WP01")
        assert result is not None
        assert result.review.reviewer == "bob"

    def test_empty_frontmatter(self) -> None:
        assert extract_done_evidence({}, "WP01") is None


# ─── T007: build_transition_chain() Tests ─────────────────────────────


class TestBuildTransitionChain:
    def test_typical_lifecycle(self) -> None:
        """Full lifecycle: planned -> doing -> for_review -> done."""
        frontmatter = {
            "lane": "done",
            "review_status": "approved",
            "reviewed_by": "reviewer-agent",
            "history": [
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
                {
                    "timestamp": "2026-01-01T11:00:00Z",
                    "lane": "doing",
                    "agent": "claude",
                },
                {
                    "timestamp": "2026-01-01T12:00:00Z",
                    "lane": "for_review",
                    "agent": "claude",
                },
                {
                    "timestamp": "2026-01-01T13:00:00Z",
                    "lane": "done",
                    "agent": "reviewer-agent",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")

        assert chain.history_entries == 4
        assert len(chain.transitions) == 3

        assert chain.transitions[0].from_lane == "planned"
        assert chain.transitions[0].to_lane == "in_progress"

        assert chain.transitions[1].from_lane == "in_progress"
        assert chain.transitions[1].to_lane == "for_review"

        assert chain.transitions[2].from_lane == "for_review"
        assert chain.transitions[2].to_lane == "done"
        assert chain.transitions[2].evidence is not None
        assert chain.transitions[2].evidence.review.reviewer == "reviewer-agent"

        assert chain.has_evidence is True

    def test_planned_wp_no_transitions(self) -> None:
        """WP still at planned with planned history -> no transitions."""
        frontmatter = {
            "lane": "planned",
            "history": [
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")
        assert chain.history_entries == 1
        assert len(chain.transitions) == 0
        assert chain.has_evidence is False

    def test_gap_fill_when_history_lags_current(self) -> None:
        """History ends at doing, but current lane is for_review."""
        frontmatter = {
            "lane": "for_review",
            "history": [
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
                {
                    "timestamp": "2026-01-01T11:00:00Z",
                    "lane": "doing",
                    "agent": "claude",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")

        assert len(chain.transitions) == 2
        # First: planned -> in_progress (from history)
        assert chain.transitions[0].from_lane == "planned"
        assert chain.transitions[0].to_lane == "in_progress"
        # Second: in_progress -> for_review (gap-fill)
        assert chain.transitions[1].from_lane == "in_progress"
        assert chain.transitions[1].to_lane == "for_review"
        assert chain.transitions[1].actor == "migration"

    def test_no_history_with_done_lane(self) -> None:
        """No history, current lane is done -> bootstrap planned -> done."""
        frontmatter = {"lane": "done"}
        chain = build_transition_chain(frontmatter, "WP01")

        assert chain.history_entries == 0
        assert len(chain.transitions) == 1
        assert chain.transitions[0].from_lane == "planned"
        assert chain.transitions[0].to_lane == "done"
        assert chain.has_evidence is False

    def test_no_history_planned(self) -> None:
        """No history, still planned -> zero transitions."""
        frontmatter = {"lane": "planned"}
        chain = build_transition_chain(frontmatter, "WP01")
        assert chain.history_entries == 0
        assert len(chain.transitions) == 0

    def test_duplicate_history_entries_collapsed(self) -> None:
        """Consecutive same-lane entries in history are collapsed."""
        frontmatter = {
            "lane": "in_progress",
            "history": [
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
                {
                    "timestamp": "2026-01-01T10:30:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
                {
                    "timestamp": "2026-01-01T11:00:00Z",
                    "lane": "doing",
                    "agent": "claude",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")
        assert chain.history_entries == 3
        # Only 1 transition: planned -> in_progress (no gap-fill needed)
        assert len(chain.transitions) == 1
        assert chain.transitions[0].from_lane == "planned"
        assert chain.transitions[0].to_lane == "in_progress"

    def test_alias_resolved_in_current_lane(self) -> None:
        """Current lane 'doing' resolved to 'in_progress'."""
        frontmatter = {
            "lane": "doing",
            "history": [
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")
        assert len(chain.transitions) == 1
        assert chain.transitions[0].to_lane == "in_progress"

    def test_missing_lane_defaults_to_planned(self) -> None:
        """Missing lane field defaults to planned."""
        frontmatter = {
            "history": [
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")
        # current_lane defaults to planned, history has planned -> no transitions
        assert len(chain.transitions) == 0

    def test_empty_lane_defaults_to_planned(self) -> None:
        """Empty lane field defaults to planned."""
        frontmatter = {
            "lane": "",
            "history": [
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")
        assert len(chain.transitions) == 0

    def test_evidence_only_on_done_transitions(self) -> None:
        """DoneEvidence attached only to transitions targeting done."""
        frontmatter = {
            "lane": "done",
            "review_status": "approved",
            "reviewed_by": "bob",
            "history": [
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
                {
                    "timestamp": "2026-01-01T11:00:00Z",
                    "lane": "doing",
                    "agent": "claude",
                },
                {
                    "timestamp": "2026-01-01T12:00:00Z",
                    "lane": "done",
                    "agent": "bob",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")

        # planned -> in_progress: no evidence
        assert chain.transitions[0].evidence is None
        # in_progress -> done: has evidence
        assert chain.transitions[1].evidence is not None

    def test_history_not_a_list(self) -> None:
        """history field is not a list -> treated as empty."""
        frontmatter = {"lane": "done", "history": "not a list"}
        chain = build_transition_chain(frontmatter, "WP01")
        assert chain.history_entries == 0
        assert len(chain.transitions) == 1  # bootstrap planned -> done

    def test_malformed_entries_skipped(self) -> None:
        """Non-dict entries in history are skipped."""
        frontmatter = {
            "lane": "in_progress",
            "history": [
                "not a dict",
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
                42,
                {
                    "timestamp": "2026-01-01T11:00:00Z",
                    "lane": "doing",
                    "agent": "claude",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")
        # Only 2 valid entries -> 1 transition: planned -> in_progress
        assert len(chain.transitions) == 1
        assert chain.transitions[0].from_lane == "planned"
        assert chain.transitions[0].to_lane == "in_progress"

    def test_pure_no_side_effects(self) -> None:
        """build_transition_chain does not modify its input."""
        history = [
            {
                "timestamp": "2026-01-01T10:00:00Z",
                "lane": "planned",
                "agent": "system",
            },
        ]
        frontmatter = {"lane": "done", "history": history}
        original_history_len = len(history)

        build_transition_chain(frontmatter, "WP01")

        assert len(history) == original_history_len
        assert len(frontmatter["history"]) == original_history_len

    def test_done_without_review_no_evidence(self) -> None:
        """WP at done without review_status/reviewed_by -> no evidence."""
        frontmatter = {
            "lane": "done",
            "history": [
                {
                    "timestamp": "2026-01-01T10:00:00Z",
                    "lane": "planned",
                    "agent": "system",
                },
                {
                    "timestamp": "2026-01-01T11:00:00Z",
                    "lane": "done",
                    "agent": "migration",
                },
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")
        assert chain.has_evidence is False
        assert chain.transitions[0].evidence is None

    def test_full_multi_step_history(self) -> None:
        """Complex lifecycle with blocked and back transitions."""
        frontmatter = {
            "lane": "done",
            "review_status": "approved",
            "reviewed_by": "reviewer",
            "history": [
                {"timestamp": "t1", "lane": "planned", "agent": "system"},
                {"timestamp": "t2", "lane": "doing", "agent": "claude"},
                {"timestamp": "t3", "lane": "blocked", "agent": "claude"},
                {"timestamp": "t4", "lane": "doing", "agent": "claude"},
                {"timestamp": "t5", "lane": "for_review", "agent": "claude"},
                {"timestamp": "t6", "lane": "done", "agent": "reviewer"},
            ],
        }
        chain = build_transition_chain(frontmatter, "WP01")

        assert chain.history_entries == 6
        assert len(chain.transitions) == 5
        assert chain.transitions[0] == Transition("planned", "in_progress", "t2", "claude")
        assert chain.transitions[1] == Transition("in_progress", "blocked", "t3", "claude")
        assert chain.transitions[2] == Transition("blocked", "in_progress", "t4", "claude")
        assert chain.transitions[3] == Transition("in_progress", "for_review", "t5", "claude")
        # Last transition has evidence
        assert chain.transitions[4].from_lane == "for_review"
        assert chain.transitions[4].to_lane == "done"
        assert chain.transitions[4].evidence is not None
        assert chain.has_evidence is True
