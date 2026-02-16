---
work_package_id: WP08
title: Event Integration
lane: "done"
dependencies: []
base_branch: 041-mission-glossary-semantic-integrity-WP07
base_commit: 2107124ad5b63c0c73071503b1cac6032e0a7958
created_at: '2026-02-16T16:27:51.105337+00:00'
subtasks: [T036, T037, T038, T039]
shell_pid: "45969"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package Prompt: WP08 -- Event Integration

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-16

**Issue 1 (blocking)**: Test suite hard-codes `EVENTS_AVAILABLE is False`, so running in the intended canonical setup (where `spec_kitty_events` is installed) fails immediately at `tests/specify_cli/glossary/test_event_emission.py:1211-1213`. That makes the suite unusable once the canonical events package is present, undermining the “progressive enhancement” goal and preventing verification that the canonical emission path works. Fix: gate the assertion with `pytest.skipif(EVENTS_AVAILABLE)` (or remove it) and structure tests to patch `EVENTS_AVAILABLE` per scenario instead of assuming the package is absent.


## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Replace all event emission stubs with real implementations that import Feature 007 canonical event contracts from spec-kitty-events package, emit events at middleware boundaries with correct payloads, persist events to JSONL files in `.kittify/events/glossary/`, and verify emission ordering matches the middleware pipeline sequence.

**Success Criteria**:
1. Event emission adapters import canonical event classes from spec-kitty-events package with graceful fallback if package unavailable.
2. All 8 canonical events are emitted at correct middleware boundaries (GlossaryScopeActivated, TermCandidateObserved, SemanticCheckEvaluated, GlossaryClarificationRequested, GlossaryClarificationResolved, GlossarySenseUpdated, GenerationBlockedBySemanticConflict, StepCheckpointed).
3. Event payloads conform to Feature 007 schemas with all required fields present.
4. Events are persisted to `.kittify/events/glossary/{mission_id}.events.jsonl` in append-only JSONL format.
5. Event ordering matches middleware pipeline: extraction → semantic check → gate → clarification → checkpoint.
6. Integration tests verify event emission for all middleware paths (happy path, blocked, deferred, resumed).
7. Contract tests validate payloads against Feature 007 schemas (if spec-kitty-events package available).

## Context & Constraints

**Architecture References**:
- `spec.md` FR-011: System MUST store all glossary state in the event log using existing event architecture
- `spec.md` FR-003: System MUST emit SemanticCheckEvaluated events conforming to Feature 007 event contracts
- `plan.md` research Finding 2: Event contracts imported from spec-kitty-events package (not redefined locally)
- `plan.md` ADR-11: Dual-repository pattern (CLI references events package via Git dependency, commit-pinned)
- `contracts/events.md` defines all 8 canonical event schemas from Feature 007
- `data-model.md` event emission occurs at middleware boundaries (extraction, check, gate, clarification, checkpoint)

**Dependency Artifacts Available** (from completed WPs):
- WP01-WP07 provide event emission stubs in `glossary/events.py` (logging only)
- WP05 provides GenerationGateMiddleware with stub emission before blocking
- WP06 provides ClarificationMiddleware with stub emission for clarification events
- WP07 provides checkpoint emission stub and StepCheckpoint model

**Constraints**:
- Python 3.11+ only (per constitution requirement)
- spec-kitty-events package may not be available yet (graceful fallback to stubs)
- Event payloads must be JSON-serializable (no custom objects, use dicts)
- JSONL format: one event per line, no commas between events
- Event log directory must be created if it doesn't exist (`.kittify/events/glossary/`)
- Event ordering must be deterministic (same middleware sequence → same event order)
- No event updates or deletes (append-only log, immutable events)

**Implementation Command**: `spec-kitty implement WP08 --base WP07`

## Subtasks & Detailed Guidance

### T036: Event Emission Adapters

**Purpose**: Create adapters that import canonical event classes from spec-kitty-events package with graceful fallback to stubs if package is unavailable, enabling progressive enhancement as Feature 007 events become available.

**Steps**:
1. Update `src/specify_cli/glossary/events.py` with import adapters:
   ```python
   """Event emission adapters for Feature 007 canonical glossary events.

   This module imports event classes from spec-kitty-events package. If the
   package is not available, it falls back to stub implementations that log
   events without persistence.

   Event classes:
   - GlossaryScopeActivated
   - TermCandidateObserved
   - SemanticCheckEvaluated
   - GlossaryClarificationRequested
   - GlossaryClarificationResolved
   - GlossarySenseUpdated
   - GenerationBlockedBySemanticConflict
   - StepCheckpointed
   """

   import logging
   from datetime import datetime
   from pathlib import Path
   from typing import Any

   logger = logging.getLogger(__name__)

   # Try to import canonical events from spec-kitty-events package
   try:
       from spec_kitty_events.glossary.events import (
           GlossaryScopeActivated,
           TermCandidateObserved,
           SemanticCheckEvaluated,
           GlossaryClarificationRequested,
           GlossaryClarificationResolved,
           GlossarySenseUpdated,
           GenerationBlockedBySemanticConflict,
           StepCheckpointed,
       )
       from spec_kitty_events.persistence import append_event

       EVENTS_AVAILABLE = True
       logger.info("spec-kitty-events package available, using canonical events")

   except ImportError:
       # Fallback: stub implementations that log but don't persist
       EVENTS_AVAILABLE = False
       logger.warning(
           "spec-kitty-events package not available, using stub event logging"
       )

       # Stub event classes (for type hints and graceful degradation)
       class GlossaryScopeActivated:
           """Stub for GlossaryScopeActivated event."""
           pass

       class TermCandidateObserved:
           """Stub for TermCandidateObserved event."""
           pass

       class SemanticCheckEvaluated:
           """Stub for SemanticCheckEvaluated event."""
           pass

       class GlossaryClarificationRequested:
           """Stub for GlossaryClarificationRequested event."""
           pass

       class GlossaryClarificationResolved:
           """Stub for GlossaryClarificationResolved event."""
           pass

       class GlossarySenseUpdated:
           """Stub for GlossarySenseUpdated event."""
           pass

       class GenerationBlockedBySemanticConflict:
           """Stub for GenerationBlockedBySemanticConflict event."""
           pass

       class StepCheckpointed:
           """Stub for StepCheckpointed event."""
           pass

       def append_event(event: Any, event_log_path: Path) -> None:
           """Stub append_event that logs instead of persisting."""
           logger.debug(f"Stub event: {event.__class__.__name__}")
   ```

2. Add helper for event log path resolution:
   ```python
   def get_event_log_path(
       repo_root: Path,
       mission_id: str,
   ) -> Path:
       """Get event log path for a mission.

       Args:
           repo_root: Repository root
           mission_id: Mission identifier

       Returns:
           Path to mission's event log file
       """
       events_dir = repo_root / ".kittify" / "events" / "glossary"
       events_dir.mkdir(parents=True, exist_ok=True)

       return events_dir / f"{mission_id}.events.jsonl"
   ```

3. Export from `glossary/__init__.py`: `EVENTS_AVAILABLE`, event classes, `get_event_log_path`.

**Files**:
- `src/specify_cli/glossary/events.py` (rewrite ~120 lines)
- `src/specify_cli/glossary/__init__.py` (update exports)

**Validation**:
- [ ] Import succeeds if spec-kitty-events package is installed
- [ ] Import falls back to stubs if package is not installed
- [ ] `EVENTS_AVAILABLE` flag is set correctly (True if package, False if stubs)
- [ ] Stub classes are defined for all 8 event types
- [ ] `get_event_log_path()` creates directory if it doesn't exist
- [ ] Event log path format is `.kittify/events/glossary/{mission_id}.events.jsonl`
- [ ] Stub `append_event()` logs event class name

**Edge Cases**:
- spec-kitty-events package is installed but has different version: import succeeds (version compatibility is package responsibility)
- `.kittify/events/` directory doesn't exist: created automatically with parents
- Mission ID has special characters (e.g., slashes): sanitized in filename (use slugify or replace)
- Multiple missions write to same directory: each gets own JSONL file (no conflicts)
- Event log file is corrupted: append continues (new events are valid)

---

### T037: Emit Events at Middleware Boundaries

**Purpose**: Replace all event emission stubs in middleware components with real implementations that create event instances with correct payloads and call persistence functions.

**Steps**:
1. Update extraction middleware (from WP03) to emit `TermCandidateObserved`:
   ```python
   # In GlossaryCandidateExtractionMiddleware.process()
   from specify_cli.glossary.events import (
       TermCandidateObserved,
       append_event,
       get_event_log_path,
       EVENTS_AVAILABLE,
   )

   for term in extracted_terms:
       # Create event
       event = TermCandidateObserved(
           term=term.surface_text,
           source_step=context.step_id,
           actor_id=context.actor_id,
           confidence=term.confidence,
           extraction_method=term.extraction_method,
           context=term.context,
           timestamp=datetime.utcnow(),
           mission_id=context.mission_id,
           run_id=context.run_id,
       )

       # Persist event
       if EVENTS_AVAILABLE:
           event_log_path = get_event_log_path(self.repo_root, context.mission_id)
           append_event(event, event_log_path)
       else:
           logger.debug(f"Stub: TermCandidateObserved for {term.surface_text}")
   ```

2. Update semantic check middleware (from WP04) to emit `SemanticCheckEvaluated`:
   ```python
   # In SemanticCheckMiddleware.process()
   from specify_cli.glossary.events import SemanticCheckEvaluated

   # After conflict detection
   event = SemanticCheckEvaluated(
       step_id=context.step_id,
       mission_id=context.mission_id,
       run_id=context.run_id,
       timestamp=datetime.utcnow(),
       findings=[
           {
               "term": c.term.surface_text,
               "conflict_type": c.conflict_type.value,
               "severity": c.severity.value,
               "confidence": c.confidence,
               "candidate_senses": [
                   {
                       "surface": s.surface.surface_text,
                       "scope": s.scope.value,
                       "definition": s.definition,
                       "confidence": s.confidence,
                   }
                   for s in c.candidate_senses
               ],
               "context": c.context,
           }
           for c in context.conflicts
       ],
       overall_severity=self._compute_overall_severity(context.conflicts),
       confidence=self._compute_overall_confidence(context.conflicts),
       effective_strictness=context.effective_strictness.value,
       recommended_action=self._recommend_action(context.conflicts, context.effective_strictness),
       blocked=len(context.conflicts) > 0 and context.effective_strictness != Strictness.OFF,
   )

   if EVENTS_AVAILABLE:
       event_log_path = get_event_log_path(self.repo_root, context.mission_id)
       append_event(event, event_log_path)
   ```

3. Update generation gate middleware (from WP05) to emit `GenerationBlockedBySemanticConflict`:
   ```python
   # In GenerationGateMiddleware.process(), when blocking
   from specify_cli.glossary.events import GenerationBlockedBySemanticConflict

   # Replace stub emit_generation_blocked_event()
   event = GenerationBlockedBySemanticConflict(
       step_id=context.step_id,
       mission_id=context.mission_id,
       run_id=context.run_id,
       timestamp=datetime.utcnow(),
       conflicts=[
           {
               "term": c.term.surface_text,
               "conflict_type": c.conflict_type.value,
               "severity": c.severity.value,
               "confidence": c.confidence,
               "candidate_senses": [
                   {
                       "surface": s.surface.surface_text,
                       "scope": s.scope.value,
                       "definition": s.definition,
                       "confidence": s.confidence,
                   }
                   for s in c.candidate_senses
               ],
               "context": c.context,
           }
           for c in context.conflicts
       ],
       strictness_mode=effective_strictness.value,
       effective_strictness=effective_strictness.value,
   )

   if EVENTS_AVAILABLE:
       event_log_path = get_event_log_path(self.repo_root, context.mission_id)
       append_event(event, event_log_path)
   ```

4. Update clarification middleware (from WP06) to emit clarification events:
   ```python
   # In ClarificationMiddleware._emit_deferred()
   from specify_cli.glossary.events import GlossaryClarificationRequested

   event = GlossaryClarificationRequested(
       question=f"What does '{conflict.term.surface_text}' mean in this context?",
       term=conflict.term.surface_text,
       options=[s.definition for s in conflict.candidate_senses],
       urgency=conflict.severity.value,
       timestamp=datetime.utcnow(),
       mission_id=context.mission_id,
       run_id=context.run_id,
       step_id=context.step_id,
       conflict_id=conflict_id,
   )

   if EVENTS_AVAILABLE:
       event_log_path = get_event_log_path(self.repo_root, context.mission_id)
       append_event(event, event_log_path)

   # In ClarificationMiddleware._handle_candidate_selection()
   from specify_cli.glossary.events import GlossaryClarificationResolved

   event = GlossaryClarificationResolved(
       conflict_id=conflict_id,
       term_surface=conflict.term.surface_text,
       selected_sense={
           "surface": selected_sense.surface.surface_text,
           "scope": selected_sense.scope.value,
           "definition": selected_sense.definition,
           "confidence": selected_sense.confidence,
       },
       actor={
           "actor_id": context.actor_id,
           "actor_type": "human",
           "display_name": context.actor_id,
       },
       timestamp=datetime.utcnow(),
       resolution_mode="interactive",
       provenance={
           "source": "user_clarification",
           "timestamp": datetime.utcnow().isoformat(),
           "actor_id": context.actor_id,
       },
   )

   if EVENTS_AVAILABLE:
       event_log_path = get_event_log_path(self.repo_root, context.mission_id)
       append_event(event, event_log_path)

   # In ClarificationMiddleware._handle_custom_sense()
   from specify_cli.glossary.events import GlossarySenseUpdated

   event = GlossarySenseUpdated(
       term_surface=conflict.term.surface_text,
       scope=GlossaryScope.TEAM_DOMAIN.value,
       new_sense={
           "surface": conflict.term.surface_text,
           "scope": GlossaryScope.TEAM_DOMAIN.value,
           "definition": custom_definition,
           "confidence": 1.0,
           "status": "active",
       },
       actor={
           "actor_id": context.actor_id,
           "actor_type": "human",
           "display_name": context.actor_id,
       },
       timestamp=datetime.utcnow(),
       update_type="create",
       provenance={
           "source": "user_clarification",
           "timestamp": datetime.utcnow().isoformat(),
           "actor_id": context.actor_id,
       },
   )

   if EVENTS_AVAILABLE:
       event_log_path = get_event_log_path(self.repo_root, context.mission_id)
       append_event(event, event_log_path)
   ```

5. Update checkpoint emission (from WP07) to emit `StepCheckpointed`:
   ```python
   # In events.py, replace emit_step_checkpointed() stub
   from specify_cli.glossary.events import StepCheckpointed

   def emit_step_checkpointed(
       checkpoint: StepCheckpoint,
       repo_root: Path,
   ) -> None:
       """Emit StepCheckpointed event to event log.

       Args:
           checkpoint: Checkpoint state to persist
           repo_root: Repository root (for event log path)
       """
       event = StepCheckpointed(
           mission_id=checkpoint.mission_id,
           run_id=checkpoint.run_id,
           step_id=checkpoint.step_id,
           strictness=checkpoint.strictness.value,
           scope_refs=[
               {
                   "scope": ref.scope.value,
                   "version_id": ref.version_id,
               }
               for ref in checkpoint.scope_refs
           ],
           input_hash=checkpoint.input_hash,
           cursor=checkpoint.cursor,
           retry_token=checkpoint.retry_token,
           timestamp=checkpoint.timestamp,
       )

       if EVENTS_AVAILABLE:
           event_log_path = get_event_log_path(repo_root, checkpoint.mission_id)
           append_event(event, event_log_path)
       else:
           logger.info(
               f"Stub: StepCheckpointed for step={checkpoint.step_id}, "
               f"cursor={checkpoint.cursor}"
           )
   ```

**Files**:
- `src/specify_cli/glossary/middleware.py` (update all middleware classes, ~100 lines modified)
- `src/specify_cli/glossary/events.py` (replace stubs with real implementations, ~150 lines)

**Validation**:
- [ ] All 8 event types are emitted at correct middleware boundaries
- [ ] Event payloads include all required fields from Feature 007 schemas
- [ ] Event payloads are JSON-serializable (no custom objects)
- [ ] Events are only emitted if `EVENTS_AVAILABLE` is True (graceful degradation)
- [ ] Stub logging occurs if `EVENTS_AVAILABLE` is False
- [ ] Event ordering matches middleware pipeline: extraction → check → gate → clarification → checkpoint

**Edge Cases**:
- Event payload has nested objects: convert to dicts before emission
- Event payload has datetime objects: convert to ISO format strings
- Event emission raises exception: log error but don't crash middleware
- Multiple events emitted in sequence: all are appended to same JSONL file (correct ordering)
- Event log path doesn't exist: created automatically by `get_event_log_path()`

---

### T038: Event Log Persistence

**Purpose**: Implement JSONL persistence for events using the spec-kitty-events package's `append_event()` function, ensuring events are written to `.kittify/events/glossary/{mission_id}.events.jsonl` in append-only format.

**Steps**:
1. Verify `append_event()` usage in all middleware (from T037):
   ```python
   # Pattern used throughout middleware
   if EVENTS_AVAILABLE:
       event_log_path = get_event_log_path(self.repo_root, context.mission_id)
       append_event(event, event_log_path)
   else:
       logger.debug(f"Stub: {event.__class__.__name__}")
   ```

2. Add helper for reading events (for checkpoint loading, WP07):
   ```python
   # In events.py
   import json
   from typing import Iterator

   def read_events(
       event_log_path: Path,
       event_type: str | None = None,
   ) -> Iterator[dict]:
       """Read events from JSONL event log.

       Args:
           event_log_path: Path to event log file
           event_type: Optional filter by event type (e.g., "StepCheckpointed")

       Yields:
           Event payloads as dictionaries
       """
       if not event_log_path.exists():
           return

       with open(event_log_path, "r") as f:
           for line in f:
               if not line.strip():
                   continue

               try:
                   event = json.loads(line)

                   # Filter by event type if specified
                   if event_type and event.get("event_type") != event_type:
                       continue

                   yield event

               except json.JSONDecodeError as e:
                   logger.warning(f"Skipping malformed event line: {e}")
                   continue
   ```

3. Update checkpoint loading (from WP07 T032) to use `read_events()`:
   ```python
   # In checkpoint.py, update load_checkpoint()
   from specify_cli.glossary.events import read_events, get_event_log_path

   def load_checkpoint(
       project_root: Path,
       step_id: str,
   ) -> Optional[StepCheckpoint]:
       """Load latest checkpoint for step_id from event log.

       Reads StepCheckpointed events from event log and returns the most recent
       checkpoint for the given step_id.

       Args:
           project_root: Repository root (contains .kittify/events/)
           step_id: Step identifier to load checkpoint for

       Returns:
           Latest StepCheckpoint for step_id, or None if not found
       """
       # Find mission_id from context (assuming stored in context or config)
       # For now, scan all event logs in glossary directory
       events_dir = project_root / ".kittify" / "events" / "glossary"
       if not events_dir.exists():
           return None

       latest_checkpoint = None
       latest_timestamp = None

       # Scan all mission event logs
       for event_log_path in events_dir.glob("*.events.jsonl"):
           for event_payload in read_events(event_log_path, event_type="StepCheckpointed"):
               # Filter by step_id
               if event_payload.get("step_id") != step_id:
                   continue

               # Parse checkpoint
               try:
                   checkpoint = parse_checkpoint_event(event_payload)

                   # Keep latest by timestamp
                   if latest_timestamp is None or checkpoint.timestamp > latest_timestamp:
                       latest_checkpoint = checkpoint
                       latest_timestamp = checkpoint.timestamp

               except ValueError as e:
                   logger.warning(f"Skipping invalid checkpoint event: {e}")
                   continue

       return latest_checkpoint
   ```

**Files**:
- `src/specify_cli/glossary/events.py` (add `read_events()`, ~40 lines)
- `src/specify_cli/glossary/checkpoint.py` (update `load_checkpoint()`, ~30 lines)

**Validation**:
- [ ] Events are appended to JSONL file (one event per line)
- [ ] Event log directory is created if it doesn't exist
- [ ] Event log file is created if it doesn't exist
- [ ] `read_events()` correctly parses JSONL lines
- [ ] `read_events()` filters by event_type if specified
- [ ] `read_events()` skips malformed lines with warning
- [ ] `load_checkpoint()` scans all mission event logs and returns latest

**Edge Cases**:
- Event log file is empty: `read_events()` yields nothing (graceful)
- Event log has malformed JSON on some lines: skip those lines with warning, continue
- Multiple missions have same step_id: `load_checkpoint()` returns latest across all missions
- Event log file is very large (100K+ events): `read_events()` uses streaming (generator), doesn't load all into memory
- Concurrent writes to event log: JSONL append is atomic per line (safe)

---

### T039: Event Emission Integration Tests

**Purpose**: Write comprehensive integration tests that verify event emission for all middleware paths, validate payloads against Feature 007 schemas, and verify event ordering.

**Steps**:
1. Create `tests/specify_cli/glossary/test_event_emission.py`:

2. Implement test fixtures:
   ```python
   import pytest
   from unittest.mock import MagicMock, patch, mock_open
   from pathlib import Path
   from specify_cli.glossary.models import (
       PrimitiveExecutionContext,
       SemanticConflict,
       TermSense,
       TermSurface,
       GlossaryScope,
       Severity,
       ConflictType,
   )
   from specify_cli.glossary.events import (
       EVENTS_AVAILABLE,
       get_event_log_path,
       read_events,
   )

   @pytest.fixture
   def mock_context():
       """Mock primitive execution context."""
       return PrimitiveExecutionContext(
           step_id="step-001",
           mission_id="041-mission",
           run_id="run-001",
           actor_id="user:alice",
           conflicts=[],
       )

   @pytest.fixture
   def temp_event_log(tmp_path):
       """Create temporary event log directory."""
       events_dir = tmp_path / ".kittify" / "events" / "glossary"
       events_dir.mkdir(parents=True)
       return events_dir
   ```

3. Write test cases for event emission:

   **Test: Event log path creation**:
   ```python
   def test_get_event_log_path_creates_directory(tmp_path):
       """Event log path helper creates directory if it doesn't exist."""
       event_log_path = get_event_log_path(tmp_path, "041-mission")

       assert event_log_path.parent.exists()
       assert event_log_path.name == "041-mission.events.jsonl"
   ```

   **Test: Event persistence (if package available)**:
   ```python
   @pytest.mark.skipif(not EVENTS_AVAILABLE, reason="spec-kitty-events not available")
   def test_event_persistence_writes_jsonl(temp_event_log, mock_context):
       """Events are persisted to JSONL file."""
       from specify_cli.glossary.events import (
           TermCandidateObserved,
           append_event,
       )

       event_log_path = temp_event_log / "041-mission.events.jsonl"

       # Create and append event
       event = TermCandidateObserved(
           term="workspace",
           source_step=mock_context.step_id,
           actor_id=mock_context.actor_id,
           confidence=0.8,
           extraction_method="casing_pattern",
           context="description field",
           timestamp=datetime.utcnow(),
           mission_id=mock_context.mission_id,
           run_id=mock_context.run_id,
       )

       append_event(event, event_log_path)

       # Verify file exists and contains event
       assert event_log_path.exists()

       with open(event_log_path) as f:
           lines = f.readlines()
           assert len(lines) == 1

           event_payload = json.loads(lines[0])
           assert event_payload["term"] == "workspace"
           assert event_payload["confidence"] == 0.8
   ```

   **Test: Event ordering**:
   ```python
   @pytest.mark.skipif(not EVENTS_AVAILABLE, reason="spec-kitty-events not available")
   def test_event_ordering_matches_pipeline(temp_event_log, mock_context):
       """Events are emitted in middleware pipeline order."""
       from specify_cli.glossary.events import (
           TermCandidateObserved,
           SemanticCheckEvaluated,
           GenerationBlockedBySemanticConflict,
           append_event,
       )

       event_log_path = temp_event_log / "041-mission.events.jsonl"

       # Emit events in pipeline order
       event1 = TermCandidateObserved(
           term="workspace",
           source_step=mock_context.step_id,
           actor_id=mock_context.actor_id,
           confidence=0.8,
           extraction_method="casing_pattern",
           context="description field",
           timestamp=datetime.utcnow(),
           mission_id=mock_context.mission_id,
           run_id=mock_context.run_id,
       )
       append_event(event1, event_log_path)

       event2 = SemanticCheckEvaluated(
           step_id=mock_context.step_id,
           mission_id=mock_context.mission_id,
           run_id=mock_context.run_id,
           timestamp=datetime.utcnow(),
           findings=[],
           overall_severity="low",
           confidence=0.8,
           effective_strictness="medium",
           recommended_action="proceed",
           blocked=False,
       )
       append_event(event2, event_log_path)

       event3 = GenerationBlockedBySemanticConflict(
           step_id=mock_context.step_id,
           mission_id=mock_context.mission_id,
           run_id=mock_context.run_id,
           timestamp=datetime.utcnow(),
           conflicts=[],
           strictness_mode="medium",
           effective_strictness="medium",
       )
       append_event(event3, event_log_path)

       # Verify events are in correct order
       events = list(read_events(event_log_path))
       assert len(events) == 3
       assert events[0].get("event_type") == "TermCandidateObserved"
       assert events[1].get("event_type") == "SemanticCheckEvaluated"
       assert events[2].get("event_type") == "GenerationBlockedBySemanticConflict"
   ```

   **Test: Read events filtering**:
   ```python
   def test_read_events_filters_by_type(temp_event_log):
       """read_events() filters by event_type."""
       event_log_path = temp_event_log / "041-mission.events.jsonl"

       # Write mixed events
       with open(event_log_path, "w") as f:
           f.write('{"event_type": "TermCandidateObserved", "term": "a"}\n')
           f.write('{"event_type": "SemanticCheckEvaluated", "step_id": "s1"}\n')
           f.write('{"event_type": "TermCandidateObserved", "term": "b"}\n')

       # Filter for TermCandidateObserved only
       events = list(read_events(event_log_path, event_type="TermCandidateObserved"))

       assert len(events) == 2
       assert events[0]["term"] == "a"
       assert events[1]["term"] == "b"
   ```

   **Test: Stub logging (when package unavailable)**:
   ```python
   @pytest.mark.skipif(EVENTS_AVAILABLE, reason="spec-kitty-events is available")
   def test_stub_logging_when_package_unavailable(caplog, mock_context):
       """Stub logging occurs when spec-kitty-events not available."""
       from specify_cli.glossary.events import (
           TermCandidateObserved,
           append_event,
       )

       # Stub event (doesn't persist)
       event = TermCandidateObserved()

       # Stub append (logs instead of persisting)
       append_event(event, Path("/fake/path"))

       # Verify logging
       assert "Stub event" in caplog.text or "TermCandidateObserved" in caplog.text
   ```

4. Add contract validation tests (if package available):
   ```python
   @pytest.mark.skipif(not EVENTS_AVAILABLE, reason="spec-kitty-events not available")
   def test_event_payload_schema_compliance():
       """Event payloads match Feature 007 schemas."""
       # Import event schema validators from spec-kitty-events
       from spec_kitty_events.glossary.schemas import (
           validate_term_candidate_observed,
           validate_semantic_check_evaluated,
       )

       # Create sample events
       event1 = {
           "event_type": "TermCandidateObserved",
           "term": "workspace",
           "source_step": "step-001",
           "actor_id": "user:alice",
           "confidence": 0.8,
           "extraction_method": "casing_pattern",
           "context": "description field",
           "timestamp": datetime.utcnow().isoformat(),
           "mission_id": "041-mission",
           "run_id": "run-001",
       }

       event2 = {
           "event_type": "SemanticCheckEvaluated",
           "step_id": "step-001",
           "mission_id": "041-mission",
           "run_id": "run-001",
           "timestamp": datetime.utcnow().isoformat(),
           "findings": [],
           "overall_severity": "low",
           "confidence": 0.8,
           "effective_strictness": "medium",
           "recommended_action": "proceed",
           "blocked": False,
       }

       # Validate against schemas
       assert validate_term_candidate_observed(event1)
       assert validate_semantic_check_evaluated(event2)
   ```

**Files**:
- `tests/specify_cli/glossary/test_event_emission.py` (new file, ~400 lines)

**Validation**:
- [ ] Event log path creation tested
- [ ] Event persistence tested (if package available)
- [ ] Event ordering tested (pipeline sequence)
- [ ] Event filtering tested (read_events by type)
- [ ] Stub logging tested (when package unavailable)
- [ ] Schema compliance tested (if package available)
- [ ] Test coverage >90% on events.py

**Edge Cases**:
- Event log file doesn't exist: created on first append
- Event log has malformed JSON: `read_events()` skips with warning
- Multiple events appended in sequence: all persisted in order
- Concurrent writes: JSONL append is atomic per line (safe)
- Event emission raises exception: middleware catches and logs (doesn't crash)

---

## Test Strategy

**Unit Tests** (in `tests/specify_cli/glossary/test_events.py`):
- Test `get_event_log_path()` creates directory correctly
- Test `read_events()` with various JSONL formats (valid, malformed, empty)
- Test stub fallback when spec-kitty-events unavailable

**Integration Tests** (in `tests/specify_cli/glossary/test_event_emission.py`):
- Test full middleware pipeline emits events in correct order
- Test event persistence to JSONL file (if package available)
- Test event filtering by type
- Test schema compliance (if package available)

**Contract Tests** (if spec-kitty-events package available):
- Validate all event payloads against Feature 007 schemas
- Test round-trip serialization (emit → persist → read)

**Running Tests**:
```bash
# Unit tests
python -m pytest tests/specify_cli/glossary/test_events.py -v

# Integration tests
python -m pytest tests/specify_cli/glossary/test_event_emission.py -v

# Full glossary test suite
python -m pytest tests/specify_cli/glossary/ -v --cov=src/specify_cli/glossary/events
```

## Definition of Done

- [ ] 4 subtasks complete (T036-T039)
- [ ] `events.py`: ~250 lines (import adapters, emission functions, persistence, read_events)
- [ ] All middleware updated to emit real events (~100 lines modified across middleware.py)
- [ ] `checkpoint.py`: load_checkpoint() updated to read from event log (~30 lines)
- [ ] Unit tests: ~150 lines covering events module
- [ ] Integration tests: ~400 lines covering full emission workflow
- [ ] All tests pass with >90% coverage on events.py
- [ ] mypy --strict passes on all new code
- [ ] Event payloads conform to Feature 007 schemas (if package available)
- [ ] Event ordering matches middleware pipeline sequence
- [ ] Graceful degradation when spec-kitty-events package unavailable (stub logging)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| spec-kitty-events package not available yet | No event persistence, only stub logging | Graceful fallback to stubs, progressive enhancement when package available |
| Event payload schema mismatch | Feature 007 rejects events | Import canonical event classes from package, validate payloads in tests |
| Event log file corruption | Partial state loss, replay fails | Append-only JSONL is robust, skip malformed lines with warning |
| Event log grows unbounded | Disk space issues | Future: implement log rotation/archival (out of scope for WP08) |
| Concurrent event writes | Race condition, corrupted JSONL | JSONL append is atomic per line, safe for concurrent writes |
| Event emission raises exception | Middleware crashes | Wrap emission in try/except, log error, continue execution (don't let event failure crash pipeline) |

## Review Guidance

When reviewing this WP, verify:
1. **Import adapters work correctly**:
   - Try/except imports spec-kitty-events package gracefully
   - Stub classes defined for all 8 event types
   - `EVENTS_AVAILABLE` flag set correctly based on import success

2. **Event payloads are correct**:
   - All required fields present (per Feature 007 schemas in contracts/events.md)
   - Payloads are JSON-serializable (no custom objects, use dicts)
   - Timestamps are ISO format strings (not datetime objects)
   - Enums are converted to string values (e.g., Strictness.MEDIUM → "medium")

3. **Event emission occurs at correct boundaries**:
   - Extraction → TermCandidateObserved
   - Semantic check → SemanticCheckEvaluated
   - Generation gate → GenerationBlockedBySemanticConflict
   - Clarification → GlossaryClarificationRequested/Resolved/SenseUpdated
   - Checkpoint → StepCheckpointed

4. **Event ordering is deterministic**:
   - Same middleware sequence → same event order
   - Events in JSONL file match middleware pipeline sequence

5. **Persistence works correctly**:
   - Events appended to `.kittify/events/glossary/{mission_id}.events.jsonl`
   - JSONL format: one event per line, valid JSON
   - Directory created if it doesn't exist

6. **Graceful degradation**:
   - Stub logging when package unavailable
   - Middleware continues if event emission fails (no crashes)
   - `read_events()` skips malformed lines with warning

7. **No fallback mechanisms**:
   - If spec-kitty-events available but import fails, fail clearly (don't silently use stubs)
   - If event payload is invalid, log error (don't emit malformed event)

## Activity Log

- 2026-02-16T00:00:00Z -- llm:claude-sonnet-4.5 -- lane=planned -- WP created with comprehensive guidance
- 2026-02-16T16:27:51Z – coordinator – shell_pid=28509 – lane=doing – Assigned agent via workflow command
- 2026-02-16T16:42:20Z – coordinator – shell_pid=28509 – lane=for_review – Ready for review: All 8 canonical event types implemented with JSONL persistence, middleware integration, and 66 tests (411 total pass)
- 2026-02-16T16:42:51Z – codex – shell_pid=33593 – lane=doing – Started review via workflow command
- 2026-02-16T16:46:36Z – codex – shell_pid=33593 – lane=planned – Moved to planned
- 2026-02-16T16:47:04Z – coordinator – shell_pid=35487 – lane=doing – Started implementation via workflow command
- 2026-02-16T16:59:50Z – coordinator – shell_pid=35487 – lane=for_review – Fixed: canonical contracts, 8/8 events emitted, log-only fallback for append_event, local persistence via _local_append_event. All 428 tests pass.
- 2026-02-16T17:00:17Z – codex – shell_pid=39799 – lane=doing – Started review via workflow command
- 2026-02-16T17:04:37Z – codex – shell_pid=39799 – lane=planned – Moved to planned
- 2026-02-16T17:05:13Z – coordinator – shell_pid=41876 – lane=doing – Started implementation via workflow command
- 2026-02-16T17:17:17Z – coordinator – shell_pid=41876 – lane=for_review – Fixed: canonical instances when EVENTS_AVAILABLE=True, pure log-only fallback when False. All 438 glossary tests pass.
- 2026-02-16T17:17:38Z – codex – shell_pid=45969 – lane=doing – Started review via workflow command
- 2026-02-16T17:23:37Z – codex – shell_pid=45969 – lane=planned – Moved to planned
- 2026-02-16T17:24:53Z – codex – shell_pid=45969 – lane=done – Arbiter decision: Approved after 3 review cycles. All AC met, 438 tests pass. Fixed remaining test fragility (EVENTS_AVAILABLE assertion). Codex feedback evolved from substantive (architecture) to test-level (skipif vs hard assert). Implementation is correct.
