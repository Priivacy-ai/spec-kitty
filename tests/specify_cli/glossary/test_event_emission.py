"""Integration tests for event emission (WP08 -- T039).

Tests cover:
- Event log path creation and sanitization
- Event persistence to JSONL files
- Event ordering across middleware pipeline
- Event filtering (read_events with event_type filter)
- All 8 canonical event types
- Stub/fallback behavior when spec-kitty-events unavailable
- Event emission at middleware boundaries
- Round-trip: emit -> persist -> read
- Edge cases: corrupt JSONL, empty files, concurrent writes
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field

import pytest

from specify_cli.glossary.events import (
    EVENTS_AVAILABLE,
    append_event,
    build_clarification_requested,
    build_clarification_resolved,
    build_generation_blocked,
    build_glossary_scope_activated,
    build_semantic_check_evaluated,
    build_sense_updated,
    build_step_checkpointed,
    build_term_candidate_observed,
    emit_clarification_requested,
    emit_clarification_resolved,
    emit_generation_blocked_event,
    emit_scope_activated,
    emit_semantic_check_evaluated,
    emit_sense_updated,
    emit_step_checkpointed,
    emit_term_candidate_observed,
    get_event_log_path,
    read_events,
    _sanitize_mission_id,
)
from specify_cli.glossary.extraction import ExtractedTerm
from specify_cli.glossary.models import (
    ConflictType,
    SemanticConflict,
    SenseRef,
    Severity,
    TermSurface,
)
from specify_cli.glossary.scope import GlossaryScope
from specify_cli.glossary.strictness import Strictness


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class MockContext:
    """Mock execution context for event emission tests."""

    step_id: str = "step-001"
    mission_id: str = "041-mission"
    run_id: str = "run-001"
    actor_id: str = "user:alice"
    metadata: Dict[str, Any] = field(default_factory=dict)
    step_input: Dict[str, Any] = field(default_factory=dict)
    step_output: Dict[str, Any] = field(default_factory=dict)
    extracted_terms: List[Any] = field(default_factory=list)
    conflicts: List[SemanticConflict] = field(default_factory=list)
    effective_strictness: str = "medium"


@pytest.fixture
def mock_context():
    """Create a mock execution context."""
    return MockContext()


@pytest.fixture
def temp_event_log(tmp_path):
    """Create temporary event log directory."""
    events_dir = tmp_path / ".kittify" / "events" / "glossary"
    events_dir.mkdir(parents=True)
    return events_dir


@pytest.fixture
def sample_conflict():
    """Create a sample SemanticConflict for testing."""
    return SemanticConflict(
        term=TermSurface("workspace"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        confidence=0.9,
        candidate_senses=[
            SenseRef("workspace", "team_domain", "Git worktree directory", 0.9),
            SenseRef("workspace", "team_domain", "VS Code workspace file", 0.7),
        ],
        context="description field",
    )


@pytest.fixture
def sample_extracted_term():
    """Create a sample ExtractedTerm for testing."""
    return ExtractedTerm(
        surface="workspace",
        source="casing_pattern",
        confidence=0.8,
        original="Workspace",
    )


# ---------------------------------------------------------------------------
# T036: Event Log Path and Sanitization
# ---------------------------------------------------------------------------


class TestEventLogPath:
    """Tests for get_event_log_path() and path sanitization."""

    def test_creates_directory(self, tmp_path):
        """Event log path helper creates directory if it does not exist."""
        event_log_path = get_event_log_path(tmp_path, "041-mission")
        assert event_log_path.parent.exists()
        assert event_log_path.name == "041-mission.events.jsonl"

    def test_creates_nested_directory(self, tmp_path):
        """Creates full .kittify/events/glossary/ hierarchy."""
        event_log_path = get_event_log_path(tmp_path, "test-mission")
        assert (tmp_path / ".kittify" / "events" / "glossary").is_dir()
        assert event_log_path.suffix == ".jsonl"

    def test_returns_correct_filename(self, tmp_path):
        """Filename matches {mission_id}.events.jsonl pattern."""
        path = get_event_log_path(tmp_path, "my-mission-42")
        assert path.name == "my-mission-42.events.jsonl"

    def test_sanitizes_special_characters(self, tmp_path):
        """Special characters in mission_id are replaced with hyphens."""
        path = get_event_log_path(tmp_path, "path/to/mission")
        assert "/" not in path.name
        assert path.name == "path-to-mission.events.jsonl"

    def test_sanitize_mission_id_preserves_safe_chars(self):
        """Safe characters are preserved in sanitized mission ID."""
        assert _sanitize_mission_id("simple-mission_42.v1") == "simple-mission_42.v1"

    def test_sanitize_mission_id_replaces_slashes(self):
        """Slashes are replaced with hyphens."""
        assert _sanitize_mission_id("path/to/mission") == "path-to-mission"

    def test_sanitize_mission_id_replaces_spaces(self):
        """Spaces are replaced with hyphens."""
        assert _sanitize_mission_id("my mission") == "my-mission"

    def test_idempotent_directory_creation(self, tmp_path):
        """Calling get_event_log_path twice does not fail."""
        get_event_log_path(tmp_path, "m1")
        path = get_event_log_path(tmp_path, "m1")
        assert path.parent.is_dir()

    def test_different_missions_different_files(self, tmp_path):
        """Each mission gets its own event log file."""
        p1 = get_event_log_path(tmp_path, "mission-a")
        p2 = get_event_log_path(tmp_path, "mission-b")
        assert p1 != p2
        assert p1.name == "mission-a.events.jsonl"
        assert p2.name == "mission-b.events.jsonl"


# ---------------------------------------------------------------------------
# T036: Event Payload Builders
# ---------------------------------------------------------------------------


class TestEventPayloadBuilders:
    """Tests for build_*() event payload functions."""

    def test_scope_activated_payload(self):
        """GlossaryScopeActivated has all required fields."""
        event = build_glossary_scope_activated(
            scope_id="team_domain",
            glossary_version_id="v3",
            mission_id="041-mission",
            run_id="run-001",
            timestamp="2026-02-16T12:00:00+00:00",
        )
        assert event["event_type"] == "GlossaryScopeActivated"
        assert event["scope_id"] == "team_domain"
        assert event["glossary_version_id"] == "v3"
        assert event["mission_id"] == "041-mission"
        assert event["run_id"] == "run-001"
        assert event["timestamp"] == "2026-02-16T12:00:00+00:00"

    def test_term_candidate_observed_payload(self):
        """TermCandidateObserved has all required fields."""
        event = build_term_candidate_observed(
            term="workspace",
            source_step="step-001",
            actor_id="user:alice",
            confidence=0.8,
            extraction_method="casing_pattern",
            context="description field",
            mission_id="041-mission",
            run_id="run-001",
        )
        assert event["event_type"] == "TermCandidateObserved"
        assert event["term"] == "workspace"
        assert event["confidence"] == 0.8
        assert event["extraction_method"] == "casing_pattern"

    def test_semantic_check_evaluated_payload(self):
        """SemanticCheckEvaluated has all required fields."""
        event = build_semantic_check_evaluated(
            step_id="step-001",
            mission_id="041-mission",
            run_id="run-001",
            findings=[],
            overall_severity="low",
            confidence=1.0,
            effective_strictness="medium",
            recommended_action="proceed",
            blocked=False,
        )
        assert event["event_type"] == "SemanticCheckEvaluated"
        assert event["blocked"] is False
        assert event["findings"] == []

    def test_generation_blocked_payload(self):
        """GenerationBlockedBySemanticConflict has all required fields."""
        event = build_generation_blocked(
            step_id="step-001",
            mission_id="041-mission",
            run_id="run-001",
            conflicts=[{"term": "workspace", "severity": "high"}],
            strictness_mode="medium",
            effective_strictness="medium",
        )
        assert event["event_type"] == "GenerationBlockedBySemanticConflict"
        assert len(event["conflicts"]) == 1
        assert event["strictness_mode"] == "medium"

    def test_clarification_requested_payload(self):
        """GlossaryClarificationRequested has all required fields."""
        event = build_clarification_requested(
            question="What does 'workspace' mean?",
            term="workspace",
            options=["Git worktree", "VS Code workspace"],
            urgency="high",
            mission_id="041-mission",
            run_id="run-001",
            step_id="step-001",
            conflict_id="uuid-1234",
        )
        assert event["event_type"] == "GlossaryClarificationRequested"
        assert event["term"] == "workspace"
        assert len(event["options"]) == 2
        assert event["conflict_id"] == "uuid-1234"

    def test_clarification_requested_auto_generates_conflict_id(self):
        """conflict_id is auto-generated if not provided."""
        event = build_clarification_requested(
            question="Q",
            term="t",
            options=[],
            urgency="low",
            mission_id="m",
            run_id="r",
            step_id="s",
        )
        assert len(event["conflict_id"]) == 36  # UUID format

    def test_clarification_resolved_payload(self):
        """GlossaryClarificationResolved has all required fields."""
        event = build_clarification_resolved(
            conflict_id="uuid-1234",
            term_surface="workspace",
            selected_sense={"surface": "workspace", "scope": "team_domain", "definition": "Git worktree", "confidence": 0.9},
            actor={"actor_id": "user:alice", "actor_type": "human", "display_name": "Alice"},
            resolution_mode="interactive",
            provenance={"source": "user_clarification", "timestamp": "2026-02-16T12:00:00+00:00", "actor_id": "user:alice"},
        )
        assert event["event_type"] == "GlossaryClarificationResolved"
        assert event["conflict_id"] == "uuid-1234"
        assert event["resolution_mode"] == "interactive"

    def test_sense_updated_payload(self):
        """GlossarySenseUpdated has all required fields."""
        event = build_sense_updated(
            term_surface="workspace",
            scope="team_domain",
            new_sense={"surface": "workspace", "scope": "team_domain", "definition": "Git worktree", "confidence": 1.0, "status": "active"},
            actor={"actor_id": "user:alice", "actor_type": "human", "display_name": "Alice"},
            update_type="create",
            provenance={"source": "user_clarification", "timestamp": "2026-02-16T12:00:00+00:00", "actor_id": "user:alice"},
        )
        assert event["event_type"] == "GlossarySenseUpdated"
        assert event["update_type"] == "create"
        assert event["new_sense"]["confidence"] == 1.0

    def test_step_checkpointed_payload(self):
        """StepCheckpointed has all required fields."""
        event = build_step_checkpointed(
            mission_id="041-mission",
            run_id="run-001",
            step_id="step-001",
            strictness="medium",
            scope_refs=[{"scope": "team_domain", "version_id": "v3"}],
            input_hash="a" * 64,
            cursor="pre_generation_gate",
            retry_token=str(uuid.uuid4()),
        )
        assert event["event_type"] == "StepCheckpointed"
        assert event["input_hash"] == "a" * 64
        assert event["cursor"] == "pre_generation_gate"

    def test_all_builders_include_timestamp(self):
        """All event builders generate a timestamp if not provided."""
        builders = [
            lambda: build_glossary_scope_activated("s", "v", "m", "r"),
            lambda: build_term_candidate_observed("t", "s", "a", 0.5, "m", "c", "m", "r"),
            lambda: build_semantic_check_evaluated("s", "m", "r", [], "low", 1.0, "medium", "proceed", False),
            lambda: build_generation_blocked("s", "m", "r", [], "medium", "medium"),
            lambda: build_clarification_requested("q", "t", [], "low", "m", "r", "s"),
            lambda: build_clarification_resolved("c", "t", {}, {}, "interactive", {}),
            lambda: build_sense_updated("t", "s", {}, {}, "create", {}),
            lambda: build_step_checkpointed("m", "r", "s", "medium", [], "a" * 64, "pre_generation_gate", str(uuid.uuid4())),
        ]
        for builder in builders:
            event = builder()
            assert "timestamp" in event
            assert event["timestamp"] is not None

    def test_all_payloads_json_serializable(self):
        """All event payloads can be serialized to JSON."""
        events = [
            build_glossary_scope_activated("s", "v", "m", "r"),
            build_term_candidate_observed("t", "s", "a", 0.5, "m", "c", "m", "r"),
            build_semantic_check_evaluated("s", "m", "r", [], "low", 1.0, "medium", "proceed", False),
            build_generation_blocked("s", "m", "r", [], "medium", "medium"),
            build_clarification_requested("q", "t", [], "low", "m", "r", "s"),
            build_clarification_resolved("c", "t", {}, {}, "interactive", {}),
            build_sense_updated("t", "s", {}, {}, "create", {}),
            build_step_checkpointed("m", "r", "s", "medium", [], "a" * 64, "pre_generation_gate", str(uuid.uuid4())),
        ]
        for event in events:
            # Must not raise
            serialized = json.dumps(event, sort_keys=True)
            assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# T038: Event Persistence (JSONL append and read)
# ---------------------------------------------------------------------------


class TestEventPersistence:
    """Tests for append_event() and read_events()."""

    def test_append_creates_file(self, tmp_path):
        """append_event creates the JSONL file if it does not exist."""
        log_path = tmp_path / "test.events.jsonl"
        event = {"event_type": "TestEvent", "data": "hello"}
        append_event(event, log_path)
        assert log_path.exists()

    def test_append_writes_json_line(self, tmp_path):
        """Each event is written as one JSON line."""
        log_path = tmp_path / "test.events.jsonl"
        append_event({"event_type": "A"}, log_path)
        append_event({"event_type": "B"}, log_path)

        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 2
        assert json.loads(lines[0])["event_type"] == "A"
        assert json.loads(lines[1])["event_type"] == "B"

    def test_append_creates_parent_directory(self, tmp_path):
        """append_event creates parent directories if they do not exist."""
        log_path = tmp_path / "new" / "dir" / "test.events.jsonl"
        append_event({"event_type": "TestEvent"}, log_path)
        assert log_path.exists()

    def test_append_sorted_keys(self, tmp_path):
        """Events are written with sorted keys for deterministic output."""
        log_path = tmp_path / "test.events.jsonl"
        append_event({"z_field": 1, "a_field": 2, "event_type": "Test"}, log_path)

        line = log_path.read_text().strip()
        parsed = json.loads(line)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_read_events_empty_file(self, tmp_path):
        """read_events on empty file yields nothing."""
        log_path = tmp_path / "empty.events.jsonl"
        log_path.write_text("")
        events = list(read_events(log_path))
        assert events == []

    def test_read_events_nonexistent_file(self, tmp_path):
        """read_events on nonexistent file yields nothing."""
        log_path = tmp_path / "missing.events.jsonl"
        events = list(read_events(log_path))
        assert events == []

    def test_read_events_returns_all(self, tmp_path):
        """read_events returns all events without filter."""
        log_path = tmp_path / "test.events.jsonl"
        log_path.write_text(
            '{"event_type": "A", "val": 1}\n'
            '{"event_type": "B", "val": 2}\n'
            '{"event_type": "C", "val": 3}\n'
        )
        events = list(read_events(log_path))
        assert len(events) == 3
        assert [e["event_type"] for e in events] == ["A", "B", "C"]

    def test_read_events_filters_by_type(self, tmp_path):
        """read_events filters by event_type when specified."""
        log_path = tmp_path / "test.events.jsonl"
        log_path.write_text(
            '{"event_type": "TermCandidateObserved", "term": "a"}\n'
            '{"event_type": "SemanticCheckEvaluated", "step_id": "s1"}\n'
            '{"event_type": "TermCandidateObserved", "term": "b"}\n'
        )
        events = list(read_events(log_path, event_type="TermCandidateObserved"))
        assert len(events) == 2
        assert events[0]["term"] == "a"
        assert events[1]["term"] == "b"

    def test_read_events_skips_malformed_lines(self, tmp_path):
        """Malformed JSON lines are skipped with warning."""
        log_path = tmp_path / "test.events.jsonl"
        log_path.write_text(
            '{"event_type": "A", "val": 1}\n'
            'not valid json\n'
            '{"event_type": "B", "val": 2}\n'
        )
        events = list(read_events(log_path))
        assert len(events) == 2

    def test_read_events_skips_blank_lines(self, tmp_path):
        """Blank lines are skipped."""
        log_path = tmp_path / "test.events.jsonl"
        log_path.write_text(
            '{"event_type": "A"}\n'
            '\n'
            '   \n'
            '{"event_type": "B"}\n'
        )
        events = list(read_events(log_path))
        assert len(events) == 2

    def test_round_trip_append_read(self, tmp_path):
        """Events survive round-trip: append -> read."""
        log_path = tmp_path / "test.events.jsonl"

        original = build_term_candidate_observed(
            term="workspace",
            source_step="step-001",
            actor_id="user:alice",
            confidence=0.8,
            extraction_method="casing_pattern",
            context="description field",
            mission_id="041-mission",
            run_id="run-001",
            timestamp="2026-02-16T12:00:00+00:00",
        )
        append_event(original, log_path)

        events = list(read_events(log_path))
        assert len(events) == 1
        assert events[0]["term"] == "workspace"
        assert events[0]["confidence"] == 0.8
        assert events[0]["event_type"] == "TermCandidateObserved"

    def test_multiple_append_preserves_order(self, tmp_path):
        """Multiple appends maintain insertion order."""
        log_path = tmp_path / "test.events.jsonl"

        for i in range(10):
            append_event({"event_type": "Test", "seq": i}, log_path)

        events = list(read_events(log_path))
        assert len(events) == 10
        for i, event in enumerate(events):
            assert event["seq"] == i


# ---------------------------------------------------------------------------
# T037: Event Emission at Middleware Boundaries
# ---------------------------------------------------------------------------


class TestTermCandidateObservedEmission:
    """Tests for emit_term_candidate_observed()."""

    def test_emits_event_with_repo_root(self, tmp_path, sample_extracted_term, mock_context):
        """TermCandidateObserved is persisted when repo_root provided."""
        event = emit_term_candidate_observed(
            term=sample_extracted_term,
            context=mock_context,
            repo_root=tmp_path,
        )
        assert event is not None
        assert event["event_type"] == "TermCandidateObserved"
        assert event["term"] == "workspace"
        assert event["confidence"] == 0.8

        # Verify persisted
        log_path = get_event_log_path(tmp_path, mock_context.mission_id)
        events = list(read_events(log_path))
        assert len(events) == 1

    def test_returns_event_without_repo_root(self, sample_extracted_term, mock_context):
        """Returns event dict even without repo_root (log only)."""
        event = emit_term_candidate_observed(
            term=sample_extracted_term,
            context=mock_context,
            repo_root=None,
        )
        assert event is not None
        assert event["event_type"] == "TermCandidateObserved"

    def test_event_has_correct_fields(self, tmp_path, sample_extracted_term, mock_context):
        """Event payload has all Feature 007 required fields."""
        event = emit_term_candidate_observed(
            term=sample_extracted_term,
            context=mock_context,
            repo_root=tmp_path,
        )
        required_fields = [
            "event_type", "term", "source_step", "actor_id",
            "confidence", "extraction_method", "context",
            "mission_id", "run_id", "timestamp",
        ]
        for field_name in required_fields:
            assert field_name in event, f"Missing field: {field_name}"


class TestSemanticCheckEvaluatedEmission:
    """Tests for emit_semantic_check_evaluated()."""

    def test_emits_event_no_conflicts(self, tmp_path, mock_context):
        """SemanticCheckEvaluated emitted for no-conflict case."""
        event = emit_semantic_check_evaluated(
            context=mock_context,
            conflicts=[],
            repo_root=tmp_path,
        )
        assert event is not None
        assert event["event_type"] == "SemanticCheckEvaluated"
        assert event["blocked"] is False
        assert event["recommended_action"] == "proceed"
        assert event["overall_severity"] == "low"

    def test_emits_event_with_conflicts(self, tmp_path, mock_context, sample_conflict):
        """SemanticCheckEvaluated includes conflict findings."""
        event = emit_semantic_check_evaluated(
            context=mock_context,
            conflicts=[sample_conflict],
            repo_root=tmp_path,
        )
        assert event is not None
        assert len(event["findings"]) == 1
        assert event["overall_severity"] == "high"
        assert event["recommended_action"] == "block"
        assert event["blocked"] is True

    def test_computes_overall_severity_from_max(self, tmp_path, mock_context):
        """Overall severity is the maximum of all conflict severities."""
        low_conflict = SemanticConflict(
            term=TermSurface("term1"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.LOW,
            confidence=0.5,
        )
        med_conflict = SemanticConflict(
            term=TermSurface("term2"),
            conflict_type=ConflictType.UNKNOWN,
            severity=Severity.MEDIUM,
            confidence=0.7,
        )
        event = emit_semantic_check_evaluated(
            context=mock_context,
            conflicts=[low_conflict, med_conflict],
            repo_root=tmp_path,
        )
        assert event["overall_severity"] == "medium"

    def test_effective_strictness_from_context(self, tmp_path, mock_context):
        """Uses effective_strictness from context."""
        mock_context.effective_strictness = Strictness.MAX
        event = emit_semantic_check_evaluated(
            context=mock_context,
            conflicts=[],
            repo_root=tmp_path,
        )
        assert event["effective_strictness"] == "max"


class TestGenerationBlockedEmission:
    """Tests for emit_generation_blocked_event()."""

    def test_emits_blocked_event(self, tmp_path, sample_conflict):
        """GenerationBlockedBySemanticConflict emitted with conflict details."""
        event = emit_generation_blocked_event(
            step_id="step-001",
            mission_id="041-mission",
            conflicts=[sample_conflict],
            strictness_mode=Strictness.MEDIUM,
            run_id="run-001",
            repo_root=tmp_path,
        )
        assert event is not None
        assert event["event_type"] == "GenerationBlockedBySemanticConflict"
        assert len(event["conflicts"]) == 1
        assert event["strictness_mode"] == "medium"

    def test_serializes_conflicts(self, tmp_path, sample_conflict):
        """Conflict objects are serialized to dicts."""
        event = emit_generation_blocked_event(
            step_id="s",
            mission_id="m",
            conflicts=[sample_conflict],
            strictness_mode=Strictness.MAX,
            repo_root=tmp_path,
        )
        conflict_dict = event["conflicts"][0]
        assert conflict_dict["term"]["surface_text"] == "workspace"
        assert conflict_dict["severity"] == "high"

    def test_handles_string_strictness(self, tmp_path, sample_conflict):
        """Accepts string strictness mode (not just enum)."""
        event = emit_generation_blocked_event(
            step_id="s",
            mission_id="m",
            conflicts=[sample_conflict],
            strictness_mode="medium",
            repo_root=tmp_path,
        )
        assert event["strictness_mode"] == "medium"

    def test_logs_only_without_repo_root(self, sample_conflict):
        """Without repo_root, event is returned but not persisted."""
        event = emit_generation_blocked_event(
            step_id="s",
            mission_id="m",
            conflicts=[sample_conflict],
            strictness_mode=Strictness.MEDIUM,
        )
        assert event is not None
        assert event["event_type"] == "GenerationBlockedBySemanticConflict"


class TestStepCheckpointedEmission:
    """Tests for emit_step_checkpointed()."""

    def test_emits_checkpoint_event(self, tmp_path):
        """StepCheckpointed emitted with correct fields."""
        from specify_cli.glossary.checkpoint import create_checkpoint, ScopeRef

        checkpoint = create_checkpoint(
            mission_id="041-mission",
            run_id="run-001",
            step_id="step-001",
            strictness=Strictness.MEDIUM,
            scope_refs=[ScopeRef(GlossaryScope.TEAM_DOMAIN, "v3")],
            inputs={"description": "test"},
            cursor="pre_generation_gate",
        )

        event = emit_step_checkpointed(checkpoint, project_root=tmp_path)
        assert event is not None
        assert event["event_type"] == "StepCheckpointed"
        assert event["step_id"] == "step-001"
        assert event["cursor"] == "pre_generation_gate"

    def test_persists_to_event_log(self, tmp_path):
        """Checkpoint event is persisted to JSONL."""
        from specify_cli.glossary.checkpoint import create_checkpoint

        checkpoint = create_checkpoint(
            mission_id="041-mission",
            run_id="run-001",
            step_id="step-001",
            strictness=Strictness.MEDIUM,
            scope_refs=[],
            inputs={"test": True},
            cursor="pre_generation_gate",
        )

        emit_step_checkpointed(checkpoint, project_root=tmp_path)

        log_path = get_event_log_path(tmp_path, "041-mission")
        events = list(read_events(log_path, event_type="StepCheckpointed"))
        assert len(events) == 1
        assert events[0]["step_id"] == "step-001"

    def test_logs_only_without_project_root(self):
        """Without project_root, checkpoint is logged but not persisted."""
        from specify_cli.glossary.checkpoint import create_checkpoint

        checkpoint = create_checkpoint(
            mission_id="m",
            run_id="r",
            step_id="s",
            strictness=Strictness.OFF,
            scope_refs=[],
            inputs={},
            cursor="pre_generation_gate",
        )

        event = emit_step_checkpointed(checkpoint, project_root=None)
        assert event is not None
        assert event["event_type"] == "StepCheckpointed"


class TestClarificationEmission:
    """Tests for emit_clarification_requested/resolved/sense_updated."""

    def test_requested_event(self, tmp_path, mock_context, sample_conflict):
        """GlossaryClarificationRequested emitted for a conflict."""
        event = emit_clarification_requested(
            conflict=sample_conflict,
            context=mock_context,
            conflict_id="test-uuid",
            repo_root=tmp_path,
        )
        assert event is not None
        assert event["event_type"] == "GlossaryClarificationRequested"
        assert event["term"] == "workspace"
        assert event["conflict_id"] == "test-uuid"
        assert len(event["options"]) == 2
        assert event["urgency"] == "high"

    def test_requested_auto_generates_id(self, tmp_path, mock_context, sample_conflict):
        """conflict_id is auto-generated if not provided."""
        event = emit_clarification_requested(
            conflict=sample_conflict,
            context=mock_context,
            repo_root=tmp_path,
        )
        assert len(event["conflict_id"]) == 36  # UUID

    def test_resolved_event(self, tmp_path, mock_context, sample_conflict):
        """GlossaryClarificationResolved emitted with selected sense."""
        selected = sample_conflict.candidate_senses[0]
        event = emit_clarification_resolved(
            conflict_id="test-uuid",
            conflict=sample_conflict,
            selected_sense=selected,
            context=mock_context,
            repo_root=tmp_path,
        )
        assert event is not None
        assert event["event_type"] == "GlossaryClarificationResolved"
        assert event["conflict_id"] == "test-uuid"
        assert event["selected_sense"]["definition"] == "Git worktree directory"
        assert event["resolution_mode"] == "interactive"

    def test_sense_updated_event(self, tmp_path, mock_context, sample_conflict):
        """GlossarySenseUpdated emitted for custom sense."""
        event = emit_sense_updated(
            conflict=sample_conflict,
            custom_definition="A project workspace directory",
            scope_value="team_domain",
            context=mock_context,
            repo_root=tmp_path,
        )
        assert event is not None
        assert event["event_type"] == "GlossarySenseUpdated"
        assert event["new_sense"]["definition"] == "A project workspace directory"
        assert event["update_type"] == "create"

    def test_scope_activated_event(self, tmp_path):
        """GlossaryScopeActivated emitted correctly."""
        event = emit_scope_activated(
            scope_id="team_domain",
            glossary_version_id="v3",
            mission_id="041-mission",
            run_id="run-001",
            repo_root=tmp_path,
        )
        assert event is not None
        assert event["event_type"] == "GlossaryScopeActivated"
        assert event["scope_id"] == "team_domain"


# ---------------------------------------------------------------------------
# T037: Event Ordering
# ---------------------------------------------------------------------------


class TestEventOrdering:
    """Tests for event ordering across middleware pipeline."""

    def test_pipeline_event_order(self, tmp_path, mock_context, sample_extracted_term, sample_conflict):
        """Events emitted in pipeline order: extraction -> check -> gate."""
        # 1. Extraction emits TermCandidateObserved
        emit_term_candidate_observed(
            term=sample_extracted_term,
            context=mock_context,
            repo_root=tmp_path,
        )

        # 2. Semantic check emits SemanticCheckEvaluated
        emit_semantic_check_evaluated(
            context=mock_context,
            conflicts=[sample_conflict],
            repo_root=tmp_path,
        )

        # 3. Gate emits GenerationBlockedBySemanticConflict
        emit_generation_blocked_event(
            step_id=mock_context.step_id,
            mission_id=mock_context.mission_id,
            conflicts=[sample_conflict],
            strictness_mode=Strictness.MEDIUM,
            run_id=mock_context.run_id,
            repo_root=tmp_path,
        )

        # Verify order in event log
        log_path = get_event_log_path(tmp_path, mock_context.mission_id)
        events = list(read_events(log_path))
        assert len(events) == 3
        assert events[0]["event_type"] == "TermCandidateObserved"
        assert events[1]["event_type"] == "SemanticCheckEvaluated"
        assert events[2]["event_type"] == "GenerationBlockedBySemanticConflict"

    def test_full_pipeline_with_clarification(self, tmp_path, mock_context, sample_extracted_term, sample_conflict):
        """Full pipeline: extraction -> check -> gate -> clarification -> checkpoint."""
        # 1. Scope activation
        emit_scope_activated(
            scope_id="team_domain",
            glossary_version_id="v1",
            mission_id=mock_context.mission_id,
            run_id=mock_context.run_id,
            repo_root=tmp_path,
        )

        # 2. Extraction
        emit_term_candidate_observed(
            term=sample_extracted_term,
            context=mock_context,
            repo_root=tmp_path,
        )

        # 3. Check
        emit_semantic_check_evaluated(
            context=mock_context,
            conflicts=[sample_conflict],
            repo_root=tmp_path,
        )

        # 4. Clarification requested
        emit_clarification_requested(
            conflict=sample_conflict,
            context=mock_context,
            conflict_id="c-001",
            repo_root=tmp_path,
        )

        # 5. Clarification resolved
        emit_clarification_resolved(
            conflict_id="c-001",
            conflict=sample_conflict,
            selected_sense=sample_conflict.candidate_senses[0],
            context=mock_context,
            repo_root=tmp_path,
        )

        # Verify all 5 events in order
        log_path = get_event_log_path(tmp_path, mock_context.mission_id)
        events = list(read_events(log_path))
        assert len(events) == 5
        expected_types = [
            "GlossaryScopeActivated",
            "TermCandidateObserved",
            "SemanticCheckEvaluated",
            "GlossaryClarificationRequested",
            "GlossaryClarificationResolved",
        ]
        actual_types = [e["event_type"] for e in events]
        assert actual_types == expected_types

    def test_multiple_terms_emit_multiple_events(self, tmp_path, mock_context):
        """Each extracted term produces its own TermCandidateObserved event."""
        terms = [
            ExtractedTerm("workspace", "metadata_hint", 1.0, "workspace"),
            ExtractedTerm("mission", "metadata_hint", 1.0, "mission"),
            ExtractedTerm("api", "casing_pattern", 0.8, "API"),
        ]

        for term in terms:
            emit_term_candidate_observed(
                term=term,
                context=mock_context,
                repo_root=tmp_path,
            )

        log_path = get_event_log_path(tmp_path, mock_context.mission_id)
        events = list(read_events(log_path, event_type="TermCandidateObserved"))
        assert len(events) == 3


# ---------------------------------------------------------------------------
# T037: Middleware Integration
# ---------------------------------------------------------------------------


class TestMiddlewareEventIntegration:
    """Tests for event emission at actual middleware boundaries."""

    def test_extraction_middleware_emits_events(self, tmp_path):
        """GlossaryCandidateExtractionMiddleware emits TermCandidateObserved."""
        from specify_cli.glossary.middleware import (
            GlossaryCandidateExtractionMiddleware,
            MockContext,
        )

        middleware = GlossaryCandidateExtractionMiddleware(repo_root=tmp_path)
        context = MockContext(
            metadata={
                "glossary_watch_terms": ["workspace"],
            },
            step_input={"description": 'The "workspace" is important'},
            step_output={},
        )
        # Add context attributes needed by event emission
        context.step_id = "step-001"  # type: ignore[attr-defined]
        context.mission_id = "test-mission"  # type: ignore[attr-defined]
        context.run_id = "run-001"  # type: ignore[attr-defined]
        context.actor_id = "user:test"  # type: ignore[attr-defined]

        middleware.process(context)

        log_path = get_event_log_path(tmp_path, "test-mission")
        events = list(read_events(log_path, event_type="TermCandidateObserved"))
        # Should have at least one term event
        assert len(events) >= 1
        assert all(e["event_type"] == "TermCandidateObserved" for e in events)

    def test_generation_gate_emits_blocked_event(self, tmp_path, sample_conflict):
        """GenerationGateMiddleware emits GenerationBlockedBySemanticConflict."""
        from specify_cli.glossary.middleware import GenerationGateMiddleware
        from specify_cli.glossary.exceptions import BlockedByConflict

        context = MockContext(
            step_id="step-001",
            mission_id="test-mission",
            run_id="run-001",
            conflicts=[sample_conflict],
        )
        context.inputs = {"desc": "test"}

        gate = GenerationGateMiddleware(
            repo_root=tmp_path,
            runtime_override=Strictness.MEDIUM,
        )

        with pytest.raises(BlockedByConflict):
            gate.process(context)

        log_path = get_event_log_path(tmp_path, "test-mission")
        events = list(read_events(log_path))

        # Should have StepCheckpointed and GenerationBlockedBySemanticConflict
        event_types = [e["event_type"] for e in events]
        assert "StepCheckpointed" in event_types
        assert "GenerationBlockedBySemanticConflict" in event_types

        # Checkpoint should come before blocked
        ckpt_idx = event_types.index("StepCheckpointed")
        blocked_idx = event_types.index("GenerationBlockedBySemanticConflict")
        assert ckpt_idx < blocked_idx


# ---------------------------------------------------------------------------
# T039: Error Handling and Edge Cases
# ---------------------------------------------------------------------------


class TestEventEmissionErrorHandling:
    """Tests for error handling in event emission."""

    def test_emission_does_not_crash_on_error(self, mock_context, sample_extracted_term):
        """Event emission failure returns None, does not raise."""
        # Use a path that will cause an error (not a directory)
        bad_root = Path("/dev/null/not/a/path")
        event = emit_term_candidate_observed(
            term=sample_extracted_term,
            context=mock_context,
            repo_root=bad_root,
        )
        # Should return None on failure
        assert event is None

    def test_blocked_event_emission_error_returns_none(self, sample_conflict):
        """emit_generation_blocked_event returns None on persistence error."""
        bad_root = Path("/dev/null/not/a/path")
        event = emit_generation_blocked_event(
            step_id="s",
            mission_id="m",
            conflicts=[sample_conflict],
            strictness_mode=Strictness.MEDIUM,
            run_id="r",
            repo_root=bad_root,
        )
        assert event is None

    def test_events_available_flag(self):
        """EVENTS_AVAILABLE is False when spec-kitty-events not installed."""
        # In the test environment, spec-kitty-events is not installed
        assert EVENTS_AVAILABLE is False


class TestEventLogEdgeCases:
    """Edge cases for event log handling."""

    def test_empty_conflicts_list(self, tmp_path, mock_context):
        """Empty conflicts list produces valid event."""
        event = emit_semantic_check_evaluated(
            context=mock_context,
            conflicts=[],
            repo_root=tmp_path,
        )
        assert event["findings"] == []
        assert event["blocked"] is False

    def test_large_number_of_events(self, tmp_path):
        """Event log handles many events without issues."""
        log_path = tmp_path / "large.events.jsonl"
        for i in range(500):
            append_event({"event_type": "Test", "seq": i}, log_path)

        events = list(read_events(log_path))
        assert len(events) == 500

    def test_unicode_in_events(self, tmp_path):
        """Unicode characters are handled correctly."""
        log_path = tmp_path / "unicode.events.jsonl"
        event = {"event_type": "Test", "term": "Arbeitsbereich", "notes": "Glossar-Eintrag"}
        append_event(event, log_path)

        events = list(read_events(log_path))
        assert len(events) == 1
        assert events[0]["term"] == "Arbeitsbereich"

    def test_concurrent_writes_produce_valid_jsonl(self, tmp_path):
        """Multiple sequential appends produce valid JSONL (each line parseable)."""
        log_path = tmp_path / "concurrent.events.jsonl"

        # Simulate concurrent-ish writes
        for i in range(20):
            append_event({"event_type": f"Event{i}", "seq": i}, log_path)

        # All lines should parse
        events = list(read_events(log_path))
        assert len(events) == 20

    def test_filter_by_nonexistent_type(self, tmp_path):
        """Filtering by nonexistent event_type returns nothing."""
        log_path = tmp_path / "test.events.jsonl"
        append_event({"event_type": "A"}, log_path)
        events = list(read_events(log_path, event_type="Nonexistent"))
        assert events == []

    def test_event_without_event_type_field(self, tmp_path):
        """Events without event_type field are returned when no filter."""
        log_path = tmp_path / "test.events.jsonl"
        log_path.write_text('{"data": "no type"}\n')
        events = list(read_events(log_path))
        assert len(events) == 1
        assert events[0]["data"] == "no type"

    def test_event_without_event_type_filtered_out(self, tmp_path):
        """Events without event_type are filtered out when type filter set."""
        log_path = tmp_path / "test.events.jsonl"
        log_path.write_text('{"data": "no type"}\n')
        events = list(read_events(log_path, event_type="SomeType"))
        assert events == []
