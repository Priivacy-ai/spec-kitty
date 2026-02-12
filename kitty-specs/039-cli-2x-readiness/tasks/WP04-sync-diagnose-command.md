---
work_package_id: "WP04"
subtasks:
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "Add sync diagnose command"
phase: "Wave 2 - Dependent"
lane: "planned"  # DO NOT EDIT - use: spec-kitty agent tasks move-task WP04 --to <lane>
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP02"]
history:
  - timestamp: "2026-02-12T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Add sync diagnose command

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP02
```

Depends on WP02 — branches from WP02's branch for error categorization reuse.

---

## Objectives & Success Criteria

- New `spec-kitty sync diagnose` command validates queued events locally against Pydantic models
- Valid events reported as valid; malformed events report specific field errors
- Reuses error categorization from WP02 for consistent error grouping
- Command is registered in the sync command group
- Tests cover both valid and malformed events

## Context & Constraints

- **Delivery branch**: 2.x
- **Dependency**: Uses error categorization from WP02 (T006 `categorize_error()` function)
- **Event model**: `src/specify_cli/spec_kitty_events/models.py` — Pydantic `Event` envelope model
- **Payload validation rules**: `src/specify_cli/sync/emitter.py` (`_PAYLOAD_RULES`, including WPStatusChanged 4-lane checks)
- **Queue**: `src/specify_cli/sync/queue.py` — SQLite queue with pending events
- **Reference**: `spec.md` (User Story 3, FR-007), `plan.md` (WP04), `data-model.md` (DiagnoseResult)

## Subtasks & Detailed Guidance

### Subtask T015 – Create diagnose.py validation module

- **Purpose**: Encapsulate event validation logic in a dedicated module for reuse and testability.
- **Steps**:
  1. Create `src/specify_cli/sync/diagnose.py`
  2. Define the `DiagnoseResult` dataclass:
     ```python
     from dataclasses import dataclass, field

     @dataclass
     class DiagnoseResult:
         event_id: str
         valid: bool
         errors: list[str] = field(default_factory=list)
         event_type: str = ""
     ```
  3. Create the main validation function:
     ```python
     def diagnose_events(queue_entries: list[dict]) -> list[DiagnoseResult]:
         results = []
         for entry in queue_entries:
             result = validate_event(entry)
             results.append(result)
         return results
     ```
  4. Import the queue module to read pending events
- **Files**: `src/specify_cli/sync/diagnose.py` (new)
- **Parallel?**: No — foundation for T016/T017

### Subtask T016 – Validate events against Pydantic Event model

- **Purpose**: Check that each queued event has all required envelope fields with correct types.
- **Steps**:
  1. In `diagnose.py`, implement `validate_event()`:
     ```python
     from specify_cli.spec_kitty_events.models import Event
     from pydantic import ValidationError

     def validate_event(event_data: dict) -> DiagnoseResult:
         event_id = event_data.get("event_id", "unknown")
         event_type = event_data.get("event_type", "unknown")

         try:
             Event(**event_data)
             return DiagnoseResult(event_id=event_id, valid=True, event_type=event_type)
         except ValidationError as e:
             errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
             return DiagnoseResult(event_id=event_id, valid=False, errors=errors, event_type=event_type)
     ```
  2. Handle edge cases:
     - Missing `event_id` field entirely
     - Invalid ULID format (26 chars)
     - Missing required fields (event_type, aggregate_id, timestamp, etc.)
     - Invalid types (e.g., lamport_clock as string instead of int)
- **Files**: `src/specify_cli/sync/diagnose.py` (edit)
- **Parallel?**: No — builds on T015

### Subtask T017 – Validate WPStatusChanged payloads

- **Purpose**: For WPStatusChanged events, also validate the payload against `StatusTransitionPayload`.
- **Steps**:
  1. After envelope validation, check if `event_type == "WPStatusChanged"`
  2. If so, validate the `payload` dict against `StatusTransitionPayload`:
     ```python
     from specify_cli.spec_kitty_events.status import StatusTransitionPayload

     if event_data.get("event_type") == "WPStatusChanged":
         try:
             StatusTransitionPayload(**event_data.get("payload", {}))
         except (ValidationError, TypeError) as e:
             result.errors.append(f"Payload validation: {e}")
             result.valid = False
     ```
  3. Check for common payload issues:
     - Missing `feature_slug` or `wp_id`
     - Invalid lane value (not in 7-lane enum)
     - Missing `reason` when `force=True`
     - Missing `evidence` when `to_lane=DONE`
- **Files**: `src/specify_cli/sync/diagnose.py` (edit)
- **Parallel?**: Yes — can develop independently of T016's envelope validation
- **Notes**: Not all event types have dedicated payload models. Only validate payload for types that have models.

### Subtask T018 – Register sync diagnose CLI command

- **Purpose**: Make `spec-kitty sync diagnose` available to users.
- **Steps**:
  1. Find where sync CLI commands are registered on 2.x:
     ```bash
     grep -rn "sync" src/specify_cli/cli/commands/ --include="*.py" -l
     ```
  2. Add the diagnose command to the sync command group:
     ```python
     @sync_app.command()
     def diagnose():
         """Validate queued events locally against the event schema."""
         from specify_cli.sync.queue import EventQueue
         from specify_cli.sync.diagnose import diagnose_events

         queue = EventQueue()
         pending = queue.get_pending_events()

         if not pending:
             console.print("[green]No pending events in queue.[/green]")
             return

         results = diagnose_events(pending)

         valid_count = sum(1 for r in results if r.valid)
         invalid_count = sum(1 for r in results if not r.valid)

         console.print(f"\nValidated {len(results)} events: {valid_count} valid, {invalid_count} invalid")

         for r in results:
             if not r.valid:
                 console.print(f"\n[red]INVALID[/red] {r.event_id} ({r.event_type})")
                 for err in r.errors:
                     console.print(f"  - {err}")
     ```
  3. Ensure the command is discoverable: `spec-kitty sync diagnose --help`
- **Files**: CLI command file for sync (find on 2.x)
- **Parallel?**: No — depends on T015/T016

### Subtask T019 – Write diagnose validation tests

- **Purpose**: Verify diagnose correctly identifies valid and malformed events.
- **Steps**:
  1. Create `tests/sync/test_diagnose.py`:
     ```python
     def test_valid_event_passes():
         """A well-formed event passes validation."""

     def test_missing_required_field():
         """Event missing event_id reports specific error."""

     def test_invalid_ulid_format():
         """Event with wrong-length event_id reports format error."""

     def test_invalid_lamport_clock_type():
         """Event with string lamport_clock reports type error."""

     def test_wp_status_payload_valid():
         """WPStatusChanged with valid payload passes."""

     def test_wp_status_payload_missing_fields():
         """WPStatusChanged with incomplete payload reports errors."""

     def test_wp_status_payload_invalid_lane():
         """WPStatusChanged with unknown lane in payload reports error."""

     def test_mixed_batch():
         """Batch of valid + invalid events returns correct counts."""
     ```
  2. Use factory functions to create test events:
     ```python
     def make_valid_event(**overrides) -> dict:
         base = {
             "event_id": "01HXYZ1234567890ABCDEFGH",
             "event_type": "WPStatusChanged",
             "aggregate_id": "039-test/WP01",
             "payload": {"feature_slug": "039-test", "wp_id": "WP01", ...},
             "timestamp": "2026-02-12T10:00:00+00:00",
             "node_id": "test-node",
             "lamport_clock": 1,
             "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
             "correlation_id": "01HXYZ1234567890ABCDEFJK",
             "schema_version": "1.0.0",
             "data_tier": 0,
         }
         base.update(overrides)
         return base
     ```
  3. Run: `python -m pytest tests/sync/test_diagnose.py -x -v`
- **Files**: `tests/sync/test_diagnose.py` (new)
- **Parallel?**: No — depends on T015-T018

## Test Strategy

- **New tests**: ~8-10 tests in `test_diagnose.py`
- **Run command**: `python -m pytest tests/sync/test_diagnose.py -x -v`
- **Fixtures**: Factory functions for valid/malformed events; no external dependencies

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Pydantic model validation is too strict for 2.x data | Test with actual queue data from 2.x; adjust validation to match real schema |
| Queue read API differs on 2.x | Read queue.py first; adapt to actual method signatures |
| Event model import path differs on 2.x | Verify import: `from specify_cli.spec_kitty_events.models import Event` |

## Review Guidance

- Verify diagnose correctly identifies missing fields, type errors, and payload issues
- Verify reuse of WP02's error categorization (not duplicated logic)
- Check that the CLI command is properly registered and accessible
- Run `python -m pytest tests/sync/ -x -v` — all tests green

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.
