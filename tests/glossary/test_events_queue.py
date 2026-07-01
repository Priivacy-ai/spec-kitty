"""Tests confirming queue exclusion for GlossarySenseUpdated (WP04 / T018).

Contract being verified:
- emit_sense_updated() writes to local JSONL but does NOT call _pkg_append_event.
- emit_clarification_resolved() calls _pkg_append_event (canonical SaaS queue).
- emit_clarification_requested() calls _pkg_append_event (canonical SaaS queue).

These tests derive from the external observable behaviour described in the spec
(FR-018, FR-019, FR-020, FR-021, FR-022) — not from internal code structure.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from glossary.events import (
    emit_clarification_requested,
    emit_clarification_resolved,
    emit_sense_updated,
    get_event_log_path,
)
from glossary.models import (
    ConflictType,
    SemanticConflict,
    SenseRef,
    Severity,
    TermSurface,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conflict(term: str = "workspace") -> SemanticConflict:
    """Build a minimal SemanticConflict for testing."""
    return SemanticConflict(
        term=TermSurface(surface_text=term),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.MEDIUM,
        confidence=0.8,
        candidate_senses=[
            SenseRef(surface=term, scope="team_domain", definition="A bounded area", confidence=0.9),
            SenseRef(surface=term, scope="spec_kitty_core", definition="Git worktree checkout", confidence=0.7),
        ],
    )


def _make_context(mission_id: str = "test-mission-001", actor_id: str = "user:alice") -> SimpleNamespace:
    """Build a minimal execution context for testing."""
    return SimpleNamespace(
        mission_id=mission_id,
        actor_id=actor_id,
        step_id="step-001",
        run_id="run-001",
        semantic_check_event_id="evt-001",
    )


def _make_selected_sense(term: str = "workspace") -> SenseRef:
    """Build a minimal SenseRef for testing clarification resolution."""
    return SenseRef(
        surface=term,
        scope="team_domain",
        definition="A bounded area of work",
        confidence=0.95,
    )


# ---------------------------------------------------------------------------
# T018-A: GlossarySenseUpdated must NOT reach _pkg_append_event
# ---------------------------------------------------------------------------


class TestGlossarySenseUpdatedNotQueued:
    """GlossarySenseUpdated is local-only — must never call _pkg_append_event."""

    def test_pkg_append_event_not_called(self, tmp_path: Path) -> None:
        """_pkg_append_event must not be called when emitting GlossarySenseUpdated."""
        conflict = _make_conflict()
        context = _make_context()

        with patch("glossary.events._pkg_append_event") as mock_queue:
            result = emit_sense_updated(
                conflict=conflict,
                custom_definition="A bounded area of work for a team",
                scope_value="team_domain",
                context=context,
                update_type="create",
                repo_root=tmp_path,
            )

        mock_queue.assert_not_called()
        assert result is not None, "emit_sense_updated should return a dict on success"

    def test_local_jsonl_written(self, tmp_path: Path) -> None:
        """The event must be written to the local JSONL file."""
        conflict = _make_conflict("pipeline")
        context = _make_context(mission_id="test-pipeline-mission")

        with patch("glossary.events._pkg_append_event"):
            emit_sense_updated(
                conflict=conflict,
                custom_definition="A data processing pipeline",
                scope_value="team_domain",
                context=context,
                update_type="create",
                repo_root=tmp_path,
            )

        event_log = get_event_log_path(tmp_path, "test-pipeline-mission")
        assert event_log.exists(), "Local JSONL file must be created"

        events = [json.loads(line) for line in event_log.read_text().splitlines() if line.strip()]
        assert len(events) == 1, "Exactly one event must be in the log"
        assert events[0]["event_type"] == "GlossarySenseUpdated"

    def test_local_jsonl_contains_correct_term(self, tmp_path: Path) -> None:
        """The JSONL event must contain the expected term surface."""
        conflict = _make_conflict("feature")
        context = _make_context(mission_id="test-term-mission")

        with patch("glossary.events._pkg_append_event"):
            emit_sense_updated(
                conflict=conflict,
                custom_definition="A user-facing capability (legacy term, use Mission instead)",
                scope_value="team_domain",
                context=context,
                update_type="create",
                repo_root=tmp_path,
            )

        event_log = get_event_log_path(tmp_path, "test-term-mission")
        events = [json.loads(line) for line in event_log.read_text().splitlines() if line.strip()]
        assert events[0]["term_surface"] == "feature"

    def test_no_repo_root_does_not_raise(self) -> None:
        """Without repo_root, emit_sense_updated must log and return the event dict."""
        conflict = _make_conflict()
        context = _make_context()

        with patch("glossary.events._pkg_append_event") as mock_queue:
            result = emit_sense_updated(
                conflict=conflict,
                custom_definition="Some definition",
                scope_value="team_domain",
                context=context,
                update_type="create",
                repo_root=None,
            )

        mock_queue.assert_not_called()
        assert result is not None


# ---------------------------------------------------------------------------
# T018-B: GlossaryClarificationResolved must reach _pkg_append_event
# ---------------------------------------------------------------------------


class TestGlossaryClarificationResolvedQueued:
    """GlossaryClarificationResolved must call _pkg_append_event (canonical SaaS queue)."""

    def test_pkg_append_event_called(self, tmp_path: Path) -> None:
        """_pkg_append_event must be called when emitting GlossaryClarificationResolved."""
        conflict = _make_conflict()
        context = _make_context()
        selected = _make_selected_sense()

        # Provide a real-looking canonical class to satisfy the guard
        fake_canonical_instance = object()
        fake_cls = MagicMock(return_value=fake_canonical_instance)

        with (
            patch("glossary.events.EVENTS_AVAILABLE", True),
            patch("glossary.events._pkg_append_event") as mock_queue,
            patch("glossary.events._CanonicGlossaryClarificationResolved", fake_cls),
        ):
            result = emit_clarification_resolved(
                conflict_id="conflict-uuid-001",
                conflict=conflict,
                selected_sense=selected,
                context=context,
                resolution_mode="interactive",
                repo_root=tmp_path,
            )

        mock_queue.assert_called_once()
        assert result is not None

    def test_local_jsonl_also_written_when_canonical_unavailable(self, tmp_path: Path) -> None:
        """When spec-kitty-events is absent, resolved event must still be locally persisted."""
        conflict = _make_conflict()
        context = _make_context(mission_id="test-resolved-local")
        selected = _make_selected_sense()

        with patch("glossary.events.EVENTS_AVAILABLE", False):
            emit_clarification_resolved(
                conflict_id="conflict-uuid-002",
                conflict=conflict,
                selected_sense=selected,
                context=context,
                resolution_mode="interactive",
                repo_root=tmp_path,
            )

        event_log = get_event_log_path(tmp_path, "test-resolved-local")
        assert event_log.exists(), "Local fallback must write to JSONL when canonical unavailable"
        events = [json.loads(line) for line in event_log.read_text().splitlines() if line.strip()]
        assert any(e.get("event_type") == "GlossaryClarificationResolved" for e in events)


# ---------------------------------------------------------------------------
# T018-C: GlossaryClarificationRequested must reach _pkg_append_event
# ---------------------------------------------------------------------------


class TestGlossaryClarificationRequestedQueued:
    """GlossaryClarificationRequested must call _pkg_append_event (canonical SaaS queue)."""

    def test_pkg_append_event_called(self, tmp_path: Path) -> None:
        """_pkg_append_event must be called when emitting GlossaryClarificationRequested."""
        conflict = _make_conflict()
        context = _make_context()

        fake_canonical_instance = object()
        fake_cls = MagicMock(return_value=fake_canonical_instance)

        with (
            patch("glossary.events.EVENTS_AVAILABLE", True),
            patch("glossary.events._pkg_append_event") as mock_queue,
            patch("glossary.events._CanonicGlossaryClarificationRequested", fake_cls),
        ):
            result = emit_clarification_requested(
                conflict=conflict,
                context=context,
                conflict_id="conflict-uuid-003",
                repo_root=tmp_path,
            )

        mock_queue.assert_called_once()
        assert result is not None

    def test_local_jsonl_written_when_canonical_unavailable(self, tmp_path: Path) -> None:
        """When spec-kitty-events absent, requested event must still be locally persisted."""
        conflict = _make_conflict()
        context = _make_context(mission_id="test-requested-local")

        with patch("glossary.events.EVENTS_AVAILABLE", False):
            emit_clarification_requested(
                conflict=conflict,
                context=context,
                conflict_id="conflict-uuid-004",
                repo_root=tmp_path,
            )

        event_log = get_event_log_path(tmp_path, "test-requested-local")
        assert event_log.exists(), "Local fallback must write to JSONL when canonical unavailable"
        events = [json.loads(line) for line in event_log.read_text().splitlines() if line.strip()]
        assert any(e.get("event_type") == "GlossaryClarificationRequested" for e in events)


# ---------------------------------------------------------------------------
# T018-D: Cross-type isolation — sense_updated never queued even when others are
# ---------------------------------------------------------------------------


class TestQueueIsolation:
    """Confirm GlossarySenseUpdated exclusion does not bleed into other event types."""

    def test_sense_updated_not_queued_while_clarification_is(self, tmp_path: Path) -> None:
        """In the same session, sense_updated must stay local while clarification reaches queue."""
        conflict = _make_conflict("lane")
        context = _make_context(mission_id="test-isolation")
        selected = _make_selected_sense("lane")

        fake_cls = MagicMock(return_value=object())

        with (
            patch("glossary.events.EVENTS_AVAILABLE", True),
            patch("glossary.events._pkg_append_event") as mock_queue,
            patch("glossary.events._CanonicGlossaryClarificationResolved", fake_cls),
        ):
            # Sense update — must NOT queue
            emit_sense_updated(
                conflict=conflict,
                custom_definition="An execution lane in a mission",
                scope_value="team_domain",
                context=context,
                update_type="create",
                repo_root=tmp_path,
            )
            call_count_after_sense = mock_queue.call_count

            # Clarification resolved — must queue
            emit_clarification_resolved(
                conflict_id="conflict-uuid-005",
                conflict=conflict,
                selected_sense=selected,
                context=context,
                resolution_mode="interactive",
                repo_root=tmp_path,
            )
            call_count_after_resolved = mock_queue.call_count

        assert call_count_after_sense == 0, "GlossarySenseUpdated must not call _pkg_append_event"
        assert call_count_after_resolved == 1, "GlossaryClarificationResolved must call _pkg_append_event exactly once"


# ---------------------------------------------------------------------------
# T018-E: FR-021 — seed file write is deferred (Proposed, not Approved)
# ---------------------------------------------------------------------------


class TestFR021SeedWriteDeferred:
    """Document FR-021 current behavior: seed file is NOT written synchronously.

    FR-021 (Proposed — not Approved in delivery contract): "Immediately after a
    GlossaryClarificationResolved event is emitted, the glossary seed file
    (.kittify/glossaries/<scope>.yaml) is updated."

    Current behavior: emit_clarification_resolved() queues the event to the SaaS
    pipeline via _pkg_append_event. It does NOT synchronously write the seed file.
    Seed file updates happen separately in the glossary pipeline (clarification.py
    and downstream writers). This test pins that contract so a future FR-021
    implementation does not silently change the queue-write behavior.

    See: spec-kitty #1549, kitty-specs/event-architecture-cli-git-truth-01KT119Y/spec.md FR-021
    """

    def test_no_seed_file_written_by_emit(self, tmp_path: Path) -> None:
        """emit_clarification_resolved must NOT write a seed file as a side effect."""
        conflict = _make_conflict("workspace")
        context = _make_context()
        selected = _make_selected_sense()

        seed_dir = tmp_path / ".kittify" / "glossaries"
        seed_dir.mkdir(parents=True)

        with patch("glossary.events.EVENTS_AVAILABLE", False):
            emit_clarification_resolved(
                conflict_id="conflict-fr021-001",
                conflict=conflict,
                selected_sense=selected,
                context=context,
                resolution_mode="interactive",
                repo_root=tmp_path,
            )

        seed_files = list(seed_dir.glob("*.yaml"))
        assert seed_files == [], (
            "FR-021 seed write is deferred (Proposed, not Approved). "
            "emit_clarification_resolved must not write seed files synchronously."
        )

    def test_queue_write_still_happens(self, tmp_path: Path) -> None:
        """The SaaS queue write must occur even though the seed file is not written."""
        conflict = _make_conflict("workspace")
        context = _make_context()
        selected = _make_selected_sense()

        fake_cls = MagicMock(return_value=object())

        with (
            patch("glossary.events.EVENTS_AVAILABLE", True),
            patch("glossary.events._pkg_append_event") as mock_queue,
            patch("glossary.events._CanonicGlossaryClarificationResolved", fake_cls),
        ):
            emit_clarification_resolved(
                conflict_id="conflict-fr021-002",
                conflict=conflict,
                selected_sense=selected,
                context=context,
                resolution_mode="interactive",
                repo_root=tmp_path,
            )

        mock_queue.assert_called_once()
