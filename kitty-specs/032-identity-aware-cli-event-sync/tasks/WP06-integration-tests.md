---
work_package_id: "WP06"
subtasks:
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
title: "Integration Tests"
phase: "Phase 4 - Validation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01", "WP02", "WP04", "WP05"]
history:
  - timestamp: "2026-02-07T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Integration Tests

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

---

## Objectives & Success Criteria

**Goal**: End-to-end tests validating the full identity-aware sync flow.

**Scope Note**: Post-MVP (run after core identity + auto-sync are stable).

**Success Criteria**:
- [ ] Full test suite passes
- [ ] All emitted events contain project_uuid
- [ ] Graceful degradation works when unauthenticated
- [ ] Config backfill works on existing projects
- [ ] Read-only repos handled correctly
- [ ] No duplicate emissions detected

---

## Context & Constraints

**Target Branch**: 2.x

**Supporting Documents**:
- [spec.md](../spec.md) - All acceptance scenarios
- [quickstart.md](../quickstart.md) - Validation scenarios

**Prerequisites**: WP01, WP02, WP04, WP05 must be complete.

**Key Constraints**:
- Tests must be isolated (no shared state)
- Mock WebSocket for reliability
- Handle async code correctly

---

## Subtasks & Detailed Guidance

### Subtask T027 – Create e2e test fixtures

**Purpose**: Set up reusable fixtures for integration tests.

**Steps**:
1. Create `tests/integration/test_sync_e2e.py`
2. Add fixtures:
   ```python
   import pytest
   import tempfile
   import os
   from pathlib import Path
   
   @pytest.fixture
   def temp_repo(tmp_path):
       """Create temporary git repository."""
       repo = tmp_path / "test-repo"
       repo.mkdir()
       
       # Initialize git
       subprocess.run(["git", "init"], cwd=repo, check=True)
       subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)
       subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
       
       # Create .kittify directory
       (repo / ".kittify").mkdir()
       
       yield repo
   
   @pytest.fixture
   def temp_repo_with_config(temp_repo):
       """Temp repo with existing config.yaml (no identity)."""
       config_path = temp_repo / ".kittify" / "config.yaml"
       config_path.write_text("vcs:\n  type: git\n")
       return temp_repo
   
   @pytest.fixture
   def mock_queue():
       """Mock OfflineQueue for inspecting queued events."""
       from unittest.mock import MagicMock
       queue = MagicMock()
       queue.events = []
       queue.queue_event = lambda e: queue.events.append(e)
       queue.size = lambda: len(queue.events)
       return queue
   
   @pytest.fixture
   def mock_websocket():
       """Mock WebSocketClient."""
       from unittest.mock import MagicMock, AsyncMock
       ws = MagicMock()
       ws.connected = False
       ws.connect = AsyncMock()
       ws.send_event = AsyncMock()
       return ws
   ```

**Files**:
- `tests/integration/test_sync_e2e.py` (NEW, ~60 lines fixtures)

---

### Subtask T028 – Test init -> implement flow with identity

**Purpose**: Verify full flow from init to event emission.

**Steps**:
1. Add test:
   ```python
   class TestIdentityAwareFlow:
       def test_init_creates_identity(self, temp_repo):
           """spec-kitty init creates config.yaml with identity."""
           os.chdir(temp_repo)
           
           # Run init (may need CLI runner or direct call)
           from specify_cli.sync.project_identity import ensure_identity
           identity = ensure_identity(temp_repo)
           
           # Verify identity created
           assert identity.project_uuid is not None
           assert identity.project_slug == "test-repo"
           assert identity.node_id is not None
           
           # Verify persisted
           config_path = temp_repo / ".kittify" / "config.yaml"
           assert config_path.exists()
           
           # Load and verify
           identity2 = load_identity(config_path)
           assert identity2.project_uuid == identity.project_uuid
       
       def test_event_contains_identity(self, temp_repo, mock_queue):
           """Emitted events contain project_uuid."""
           os.chdir(temp_repo)
           
           from specify_cli.sync.emitter import EventEmitter
           emitter = EventEmitter(queue=mock_queue)
           
           event = emitter.emit_wp_status_changed("WP01", "planned", "doing")
           
           assert event is not None
           assert "project_uuid" in event
           assert event["project_uuid"] is not None
           # Verify it's a valid UUID string
           from uuid import UUID
           UUID(event["project_uuid"])  # Should not raise
   ```

**Files**:
- `tests/integration/test_sync_e2e.py` (append, ~50 lines)

---

### Subtask T029 – Test unauthenticated graceful degradation

**Purpose**: Verify queue-only mode when not authenticated.

**Steps**:
1. Add test:
   ```python
   def test_unauthenticated_queues_only(self, temp_repo, mock_queue, mock_websocket):
       """Events are queued (not sent via WS) when unauthenticated."""
       os.chdir(temp_repo)
       
       with patch("specify_cli.sync.auth.AuthClient.is_authenticated", return_value=False):
           from specify_cli.sync.runtime import SyncRuntime
           runtime = SyncRuntime()
           runtime.start()
           
           # WebSocket should not be connected
           assert runtime.ws_client is None
           # Background service should still be running
           assert runtime.background_service is not None
       
       # Emit event
       emitter = EventEmitter(queue=mock_queue)
       event = emitter.emit_wp_status_changed("WP01", "planned", "doing")
       
       # Event should be queued
       assert mock_queue.size() == 1
       # But not sent via WebSocket (no ws_client)
   ```

**Files**:
- `tests/integration/test_sync_e2e.py` (append, ~30 lines)

---

### Subtask T030 – Test config backfill on existing project

**Purpose**: Verify identity is generated for projects without it.

**Steps**:
1. Add test:
   ```python
   def test_backfill_existing_config(self, temp_repo_with_config):
       """Identity added to existing config.yaml without overwriting other fields."""
       config_path = temp_repo_with_config / ".kittify" / "config.yaml"
       
       # Verify config exists but has no identity
       from ruamel.yaml import YAML
       yaml = YAML()
       with open(config_path) as f:
           config = yaml.load(f)
       assert "project" not in config
       assert config["vcs"]["type"] == "git"
       
       # Trigger backfill
       from specify_cli.sync.project_identity import ensure_identity
       identity = ensure_identity(temp_repo_with_config)
       
       # Verify identity created
       assert identity.is_complete
       
       # Verify other fields preserved
       with open(config_path) as f:
           config = yaml.load(f)
       assert config["vcs"]["type"] == "git"  # Preserved
       assert config["project"]["uuid"] is not None  # Added
   ```

**Files**:
- `tests/integration/test_sync_e2e.py` (append, ~30 lines)

---

### Subtask T031 – Test read-only repo fallback

**Purpose**: Verify in-memory identity when config is not writable.

**Steps**:
1. Add test:
   ```python
   def test_readonly_fallback(self, temp_repo, caplog):
       """Read-only repo uses in-memory identity with warning."""
       config_path = temp_repo / ".kittify" / "config.yaml"
       
       # Create config
       config_path.write_text("vcs:\n  type: git\n")
       
       # Make read-only
       import stat
       config_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
       
       try:
           from specify_cli.sync.project_identity import ensure_identity
           identity = ensure_identity(temp_repo)
           
           # Identity should still be complete (in-memory)
           assert identity.is_complete
           
           # Warning should be logged
           assert "not writable" in caplog.text.lower() or "in-memory" in caplog.text.lower()
           
           # Config should NOT have identity (couldn't write)
           from ruamel.yaml import YAML
           yaml = YAML()
           with open(config_path) as f:
               config = yaml.load(f)
           assert "project" not in config
       finally:
           # Restore permissions for cleanup
           config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
   ```

**Files**:
- `tests/integration/test_sync_e2e.py` (append, ~35 lines)

---

### Subtask T032 – Test no duplicate emissions

**Purpose**: Verify each command emits exactly one status change.

**Steps**:
1. Add test:
   ```python
   def test_no_duplicate_emissions(self, temp_repo):
       """Commands emit exactly one WPStatusChanged per transition."""
       os.chdir(temp_repo)
       
       with patch("specify_cli.sync.events.emit_wp_status_changed", return_value=None) as mock_emit:
           # Trigger implement via CLI runner (or direct command)
           # ...
           pass
       
       assert mock_emit.call_count == 1
   ```

**Files**:
- `tests/integration/test_sync_e2e.py` (append, ~30 lines)

---

## Test Commands

```bash
# Run all integration tests
pytest tests/integration/test_sync_e2e.py -v

# Run with coverage
pytest tests/integration/test_sync_e2e.py -v --cov=specify_cli.sync

# Type check
mypy tests/integration/test_sync_e2e.py
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Flaky tests from timing | Use proper async waits; avoid sleeps |
| Test isolation issues | Each test gets fresh temp directory |
| Async code testing | Use pytest-asyncio or proper async mocks |

---

## Review Guidance

**Reviewers should verify**:
1. Tests are isolated (no shared state between tests)
2. All acceptance scenarios from spec.md are covered
3. Mocks are appropriate (WebSocket, auth)
4. Cleanup happens even on failure (try/finally)

---

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
