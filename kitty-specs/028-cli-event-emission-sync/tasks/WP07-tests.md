---
work_package_id: "WP07"
subtasks:
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
  - "T042"
  - "T043"
title: "Test Suite"
phase: "Phase 4 - Validation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP06"]
history:
  - timestamp: "2026-02-03T18:58:09Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - Test Suite

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- 90%+ line coverage for new code in `src/specify_cli/sync/`
- All 8 event types have dedicated test cases
- All success criteria (SC-001 through SC-012) verified via tests
- Edge cases covered: offline queue, schema validation, clock desync, queue overflow

## Context & Constraints

### Reference Documents
- **Spec**: `kitty-specs/028-cli-event-emission-sync/spec.md` - Success criteria, edge cases
- **Plan**: `kitty-specs/028-cli-event-emission-sync/plan.md` - Test strategy
- **Contract**: `kitty-specs/028-cli-event-emission-sync/contracts/events.schema.json` - Schema validation

### Testing Requirements
- pytest with --cov for coverage
- mypy --strict for type checking
- All new code must have type hints

### Dependencies
- All WPs (WP01-WP06) must be complete
- Mock server for integration tests

---

## Subtasks & Detailed Guidance

### Subtask T036 - test_events.py Unit Tests

- **Purpose**: Test EventEmitter class and event builders
- **Steps**:
  1. Create `tests/sync/test_events.py`
  2. Test cases to implement:
     ```python
     import pytest
     from unittest.mock import MagicMock, patch
     from specify_cli.sync.events import get_emitter, emit_wp_status_changed

     class TestEventEmitter:
         def test_singleton_pattern(self):
             """get_emitter() returns same instance"""
             e1 = get_emitter()
             e2 = get_emitter()
             assert e1 is e2

         def test_emit_wp_status_changed(self, mock_queue):
             """WPStatusChanged event has correct structure"""
             emit_wp_status_changed(
                 wp_id="WP01",
                 previous_status="planned",
                 new_status="doing",
             )
             # Verify event in queue
             events = mock_queue.drain_queue()
             assert len(events) == 1
             assert events[0]["event_type"] == "WPStatusChanged"
             assert events[0]["payload"]["wp_id"] == "WP01"

         def test_emit_requires_ulid_event_id(self, mock_queue):
             """Event ID is valid ULID format"""
             emit_wp_status_changed("WP01", "planned", "doing")
             events = mock_queue.drain_queue()
             event_id = events[0]["event_id"]
             assert len(event_id) == 26  # ULID length
             assert event_id.isalnum()

         def test_emit_increments_lamport_clock(self, mock_queue):
             """Lamport clock increments on each emit"""
             emit_wp_status_changed("WP01", "planned", "doing")
             emit_wp_status_changed("WP02", "planned", "doing")
             events = mock_queue.drain_queue()
             assert events[1]["lamport_clock"] > events[0]["lamport_clock"]

         # Add tests for all 8 event types...
     ```
  3. Test each event builder: WPCreated, WPAssigned, FeatureCreated, etc.
  4. Test validation failures are handled gracefully
- **Files**: `tests/sync/test_events.py`
- **Parallel?**: No (main test file)
- **Notes**:
  - Use pytest fixtures for mock queue, mock auth
  - Test both success paths and error paths

### Subtask T037 - test_clock.py Unit Tests

- **Purpose**: Test LamportClock persistence and operations
- **Steps**:
  1. Create `tests/sync/test_clock.py`
  2. Test cases:
     ```python
     import pytest
     import tempfile
     from pathlib import Path
     from specify_cli.sync.clock import LamportClock

     class TestLamportClock:
         def test_tick_increments_value(self):
             """tick() returns incremented value"""
             clock = LamportClock(value=0, node_id="test")
             assert clock.tick() == 1
             assert clock.tick() == 2
             assert clock.value == 2

         def test_receive_updates_to_max(self):
             """receive() updates to max(local, remote) + 1"""
             clock = LamportClock(value=5, node_id="test")
             clock.receive(10)
             assert clock.value == 11

         def test_persistence_save_load(self, tmp_path):
             """Clock persists to JSON and reloads"""
             clock_path = tmp_path / ".spec-kitty" / "clock.json"
             clock1 = LamportClock(value=42, node_id="test123")
             clock1.save(clock_path)

             clock2 = LamportClock.load(clock_path)
             assert clock2.value == 42
             assert clock2.node_id == "test123"

         def test_atomic_write(self, tmp_path):
             """Save uses atomic write (temp file + rename)"""
             # Test that partial writes don't corrupt file
             ...

         def test_missing_file_initializes_zero(self, tmp_path):
             """Missing clock file initializes with value=0"""
             clock = LamportClock.load(tmp_path / "nonexistent.json")
             assert clock.value == 0
     ```
- **Files**: `tests/sync/test_clock.py`
- **Parallel?**: Yes (independent test file)
- **Notes**:
  - Use tmp_path fixture for isolated file operations
  - Test edge cases: corruption, permissions

### Subtask T038 - test_background.py Unit Tests

- **Purpose**: Test BackgroundSyncService operations
- **Steps**:
  1. Create `tests/sync/test_background.py`
  2. Test cases:
     ```python
     import pytest
     from unittest.mock import MagicMock, patch
     from specify_cli.sync.background import BackgroundSyncService

     class TestBackgroundSyncService:
         def test_start_schedules_timer(self):
             """start() schedules first sync timer"""
             service = BackgroundSyncService(...)
             service.start()
             assert service._timer is not None
             service.stop()

         def test_stop_cancels_timer(self):
             """stop() cancels running timer"""
             service = BackgroundSyncService(...)
             service.start()
             service.stop()
             assert not service._running

         def test_exponential_backoff(self):
             """Backoff doubles on failure, resets on success"""
             service = BackgroundSyncService(...)
             service._backoff_seconds = 0.5

             # Simulate failures
             for _ in range(3):
                 service._on_sync_failure()

             assert service._backoff_seconds == 4.0  # 0.5 * 2^3

             # Simulate success
             service._on_sync_success()
             assert service._backoff_seconds == 0.5

         def test_backoff_capped_at_30s(self):
             """Backoff doesn't exceed 30 seconds"""
             service = BackgroundSyncService(...)
             service._backoff_seconds = 16
             service._on_sync_failure()
             service._on_sync_failure()
             assert service._backoff_seconds == 30  # Capped

         def test_sync_now_bypasses_timer(self):
             """sync_now() syncs immediately"""
             ...
     ```
- **Files**: `tests/sync/test_background.py`
- **Parallel?**: Yes (independent test file)
- **Notes**:
  - Mock batch_sync to avoid network calls
  - Test timer behavior with short intervals

### Subtask T039 - test_integration.py Integration Tests

- **Purpose**: Test full flow with mock server
- **Steps**:
  1. Create `tests/sync/test_integration.py`
  2. Use pytest-httpx or responses to mock HTTP endpoints
  3. Test cases:
     ```python
     import pytest
     from specify_cli.sync.events import emit_wp_status_changed, get_emitter
     from specify_cli.sync.batch import batch_sync

     class TestIntegration:
         def test_event_emission_to_queue_to_sync(self, mock_server, temp_queue):
             """Full flow: emit -> queue -> batch sync -> server"""
             # Emit events
             emit_wp_status_changed("WP01", "planned", "doing")
             emit_wp_status_changed("WP02", "planned", "doing")

             # Verify in queue
             assert temp_queue.size() == 2

             # Sync to server
             result = batch_sync(
                 queue=temp_queue,
                 auth_token="test_token",
                 server_url=mock_server.url,
             )

             # Verify success
             assert result.synced_count == 2
             assert temp_queue.size() == 0  # Queue drained

         def test_auth_token_refresh_on_401(self, mock_server):
             """401 triggers token refresh and retry"""
             ...

         def test_lamport_clock_reconciliation(self, mock_server):
             """Clock updates when server reports higher value"""
             ...
     ```
- **Files**: `tests/sync/test_integration.py`
- **Parallel?**: No (integration tests)
- **Notes**:
  - Mock server should match Feature 008 API contract
  - Test both success and failure scenarios

### Subtask T040 - test_event_emission.py Command Tests

- **Purpose**: Test CLI commands emit correct events
- **Steps**:
  1. Create `tests/cli/commands/test_event_emission.py`
  2. Test cases:
     ```python
     import pytest
     from unittest.mock import patch
     from typer.testing import CliRunner
     from specify_cli import app

     runner = CliRunner()

     class TestCommandEventEmission:
         def test_implement_emits_wp_status_changed(self, mock_emitter):
             """implement command emits WPStatusChanged(planned->doing)"""
             with patch('specify_cli.sync.events.get_emitter', return_value=mock_emitter):
                 result = runner.invoke(app, ["implement", "WP01"])

             mock_emitter.emit_wp_status_changed.assert_called_once()
             args = mock_emitter.emit_wp_status_changed.call_args
             assert args.kwargs["wp_id"] == "WP01"
             assert args.kwargs["previous_status"] == "planned"
             assert args.kwargs["new_status"] == "doing"

         def test_merge_emits_wp_status_changed(self, mock_emitter):
             """merge command emits WPStatusChanged(doing->for_review)"""
             ...

         def test_accept_emits_wp_status_changed(self, mock_emitter):
             """accept command emits WPStatusChanged(for_review->done)"""
             ...

         def test_finalize_tasks_emits_batch(self, mock_emitter):
             """finalize-tasks emits FeatureCreated + WPCreated for each WP"""
             ...

         def test_emission_failure_does_not_block_command(self, mock_emitter):
             """Command succeeds even when emission fails"""
             mock_emitter.emit_wp_status_changed.side_effect = Exception("Network error")

             result = runner.invoke(app, ["implement", "WP01"])

             assert result.exit_code == 0  # Command still succeeds
             assert "Warning" in result.output
     ```
- **Files**: `tests/cli/commands/test_event_emission.py`
- **Parallel?**: Yes (independent test file)
- **Notes**:
  - Use typer.testing.CliRunner for CLI tests
  - Mock emitter to avoid actual queue writes

### Subtask T041 - Test Fixtures

- **Purpose**: Create reusable fixtures for all tests
- **Steps**:
  1. Create `tests/sync/conftest.py`:
     ```python
     import pytest
     import tempfile
     from pathlib import Path
     from unittest.mock import MagicMock

     @pytest.fixture
     def temp_queue(tmp_path):
         """Temporary SQLite queue for testing"""
         from specify_cli.sync.queue import OfflineQueue
         db_path = tmp_path / "test_queue.db"
         return OfflineQueue(db_path=db_path)

     @pytest.fixture
     def mock_auth():
         """Mock AuthClient for testing"""
         auth = MagicMock()
         auth.is_authenticated.return_value = True
         auth.get_access_token.return_value = "test_token"
     # Provide team_slug for whatever accessor the emitter uses
     auth.team_slug = "test-team"
     # If you implement an accessor method, stub it here as well
     # auth.get_team_slug.return_value = "test-team"
         return auth

     @pytest.fixture
     def mock_emitter(temp_queue, mock_auth):
         """Mock EventEmitter with temp queue"""
         from specify_cli.sync.emitter import EventEmitter
         emitter = EventEmitter()
         emitter.queue = temp_queue
         emitter.auth = mock_auth
         emitter.ws_client = None
         return emitter

     @pytest.fixture
     def mock_server(httpx_mock):
         """Mock HTTP server matching Feature 008 contract"""
         httpx_mock.add_response(
             method="POST",
             url="https://api.spec-kitty.dev/api/v1/events/batch/",
             json={"results": [{"event_id": "test", "status": "success"}]},
         )
         return httpx_mock
     ```
  2. Add fixtures to `tests/cli/commands/conftest.py` for CLI tests
- **Files**: `tests/sync/conftest.py`, `tests/cli/commands/conftest.py`
- **Parallel?**: No (shared fixtures)
- **Notes**:
  - Fixtures provide isolation between tests
  - Use tmp_path for file system tests

### Subtask T042 - Success Criteria Verification

- **Purpose**: Ensure all SC-001 through SC-012 are covered by tests
- **Steps**:
  1. Create verification matrix:
     | SC | Description | Test File | Test Function |
     |----|-------------|-----------|---------------|
     | SC-001 | implement emits WPStatusChanged | test_event_emission.py | test_implement_emits_* |
     | SC-002 | merge emits WPStatusChanged | test_event_emission.py | test_merge_emits_* |
     | SC-003 | accept emits WPStatusChanged | test_event_emission.py | test_accept_emits_* |
     | SC-004 | finalize-tasks emits batch | test_event_emission.py | test_finalize_tasks_* |
     | SC-005 | orchestrate emits WPAssigned | test_event_emission.py | test_orchestrate_* |
     | SC-006 | Offline queue stores events | test_integration.py | test_offline_queue_* |
     | SC-007 | Batch sync sends events | test_integration.py | test_batch_sync_* |
     | SC-008 | Non-blocking emission | test_event_emission.py | test_emission_failure_* |
     | SC-009 | Lamport clock increments | test_events.py | test_emit_increments_* |
     | SC-010 | team_slug included | test_events.py | test_team_slug_* |
     | SC-011 | ErrorLogged emitted on errors | test_event_emission.py | test_error_logged_* |
     | SC-012 | DependencyResolved emitted | test_event_emission.py | test_dependency_resolved_* |
  2. Add tests for any missing criteria
  3. Document coverage in test file comments
- **Files**: All test files
- **Parallel?**: No (verification)
- **Notes**:
  - This is a checklist task, not new code
  - Ensure each SC has at least one dedicated test

### Subtask T043 - Edge Case Tests

- **Purpose**: Test edge cases from spec
- **Steps**:
  1. Add edge case tests:
     ```python
     class TestEdgeCases:
         def test_network_failure_queues_event(self):
             """Network failure during emit queues event locally"""
             ...

         def test_invalid_schema_discards_event(self):
             """Invalid event schema logs warning and discards"""
             ...

         def test_lamport_clock_desync_recovery(self):
             """Clock reconciles when behind server"""
             ...

         def test_queue_overflow_warning(self):
             """Queue at 10K limit warns and drops new events"""
             ...

         def test_concurrent_emission(self):
             """Concurrent emits don't corrupt queue"""
             import threading
             ...

         def test_token_expiry_refresh(self):
             """401 during sync triggers token refresh"""
             ...
     ```
  2. Reference spec edge cases section for complete list
- **Files**: `tests/sync/test_edge_cases.py` or add to existing files
- **Parallel?**: No (final validation)
- **Notes**:
  - Edge cases are critical for production reliability
  - Some may require complex setup (concurrent threads, mocked timeouts)

---

## Test Strategy

Run full test suite:
```bash
# Run all tests with coverage
pytest tests/sync tests/cli/commands/test_event_emission.py -v --cov=src/specify_cli/sync --cov-report=term-missing

# Run specific test file
pytest tests/sync/test_events.py -v

# Run with mypy type checking
mypy src/specify_cli/sync --strict
```

Coverage target: 90%+ for new code in sync module

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Flaky tests | Use deterministic mocks, avoid time-dependent tests |
| Coverage gaps | Use --cov-report to identify uncovered lines |
| Slow integration tests | Mock HTTP, don't use real network |
| Test isolation | Use tmp_path and fixtures, reset singletons |

---

## Review Guidance

- Verify 90%+ coverage on sync module
- Verify all SC-001 through SC-012 have tests
- Verify edge cases are covered
- Run `pytest --cov` and check report
- Verify tests pass on clean checkout

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-03T18:58:09Z - system - lane=planned - Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP07 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
