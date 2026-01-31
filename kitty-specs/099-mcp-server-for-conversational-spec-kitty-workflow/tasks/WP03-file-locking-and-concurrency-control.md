---
work_package_id: WP03
title: File Locking & Concurrency Control
lane: "done"
dependencies: [WP02]
base_branch: 099-mcp-server-for-conversational-spec-kitty-workflow-WP02
base_commit: c5d5653835011f41dbe9ee1c90550912e84bde53
created_at: '2026-01-31T12:31:46.392470+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
phase: Phase 1 - Foundation
assignee: 'cursor-reviewer'
agent: "cursor-reviewer"
shell_pid: "71171"
review_status: "approved"
reviewed_by: "Rodrigo Leven"
history:
- timestamp: '2026-01-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – File Locking & Concurrency Control

## Objectives & Success Criteria

**Goal**: Implement pessimistic file-level locking using filelock library to prevent concurrent modifications from multiple MCP clients.

**Success Criteria**:
- filelock dependency installed and tested
- ResourceLock dataclass created with timeout and PID tracking
- Lock acquisition/release working with context manager pattern
- Stale lock detection and cleanup (PID-based)
- Lock granularity implemented (per-WP, per-feature, per-config)
- Multiple clients wait for lock release without errors
- Timeout handling returns structured error messages
- Cross-platform compatibility verified (Windows + Unix)

---

## Context & Constraints

**Prerequisites**:
- Review `data-model.md` section: ResourceLock entity
- Review `spec.md` FR-013: Pessimistic file-level locking requirement
- WP02 completed (ProjectContext provides lock_dir)

**Architectural Constraints**:
- FR-013: Pessimistic locking prevents concurrent modifications
- Cross-platform: Must work on Windows, macOS, Linux
- Timeout: Default 5 minutes with configurable override
- Auto-cleanup: Locks released on process exit (filelock feature)

**Key Design Decisions**:
- Use filelock library (battle-tested, cross-platform)
- Lock files: `.kittify/.lock-{resource_id}`
- Context manager pattern (`with lock.acquire():`)
- PID check for stale lock detection

---

## Subtasks & Detailed Guidance

### Subtask T014 – Install filelock dependency

**Purpose**: Add filelock library to project dependencies.

**Steps**:
1. Open `src/specify_cli/pyproject.toml`
2. Add filelock to dependencies:
   ```toml
   dependencies = [
       # ... existing ...
       "filelock>=3.12.0,<4.0.0",
   ]
   ```
3. Run `uv sync` to install
4. Verify: `python -c "import filelock; print(filelock.__version__)"`

**Files**:
- `src/specify_cli/pyproject.toml` (~2 lines added)

**Validation**:
- [ ] filelock appears in dependencies
- [ ] Import succeeds in Python REPL
- [ ] Version constraint prevents breaking changes

**Notes**:
- filelock 3.12+ has cross-platform improvements
- Pin major version to avoid API breakage

---

### Subtask T015 – Create ResourceLock dataclass

**Purpose**: Define the entity that represents a lock on a project resource.

**Steps**:
1. Create `src/specify_cli/mcp/session/locking.py`
2. Implement ResourceLock:
   ```python
   from dataclasses import dataclass
   from pathlib import Path
   from datetime import datetime, timezone
   from typing import Optional
   import os
   
   @dataclass
   class ResourceLock:
       """Represents a pessimistic lock on a project resource."""
       
       resource_id: str
       lock_file: Path
       timeout_seconds: int = 300  # 5 minutes default
       acquired_at: Optional[str] = None
       owner_pid: Optional[int] = None
       
       def __post_init__(self):
           """Validate timeout is positive."""
           if self.timeout_seconds <= 0:
               raise ValueError("timeout_seconds must be positive")
       
       @classmethod
       def for_resource(
           cls,
           lock_dir: Path,
           resource_id: str,
           timeout_seconds: int = 300
       ) -> "ResourceLock":
           """Create ResourceLock for a specific resource."""
           lock_file = lock_dir / f".lock-{resource_id}"
           
           return cls(
               resource_id=resource_id,
               lock_file=lock_file,
               timeout_seconds=timeout_seconds
           )
   ```

**Files**:
- `src/specify_cli/mcp/session/locking.py` (new, ~40 lines initially)

**Validation**:
- [ ] ResourceLock can be created with resource_id and lock_file
- [ ] `for_resource()` generates correct lock file path
- [ ] Timeout validation raises ValueError for non-positive values

---

### Subtask T016 – Implement lock acquisition with timeout

**Purpose**: Add lock acquisition using filelock with timeout handling.

**Steps**:
1. In `locking.py`, add acquisition method:
   ```python
   from filelock import FileLock, Timeout
   from contextlib import contextmanager
   
   @contextmanager
   def acquire(self):
       """Acquire lock with timeout (context manager)."""
       lock = FileLock(self.lock_file, timeout=self.timeout_seconds)
       
       try:
           with lock.acquire(timeout=self.timeout_seconds):
               # Record acquisition metadata
               self.acquired_at = datetime.now(timezone.utc).isoformat()
               self.owner_pid = os.getpid()
               
               yield self
       except Timeout:
           raise LockTimeout(
               f"Resource {self.resource_id} is locked. "
               f"Retry in a moment."
           )
   
   class LockTimeout(Exception):
       """Raised when lock acquisition times out."""
       pass
   ```
2. Add test:
   ```python
   def test_lock_acquisition_succeeds(tmp_path):
       """Test successful lock acquisition."""
       lock = ResourceLock.for_resource(tmp_path, "test-resource")
       
       with lock.acquire():
           assert lock.acquired_at is not None
           assert lock.owner_pid == os.getpid()
   ```

**Files**:
- `src/specify_cli/mcp/session/locking.py` (add acquire method, ~30 lines)
- `tests/mcp/test_locking.py` (new, ~20 lines initially)

**Validation**:
- [ ] Lock acquisition succeeds when no other process holds lock
- [ ] acquired_at timestamp recorded
- [ ] owner_pid matches current process
- [ ] Context manager pattern works (yield self)

---

### Subtask T017 – Implement lock release

**Purpose**: Ensure locks are released properly, including error cases.

**Steps**:
1. Lock release handled automatically by context manager exit
2. Add cleanup method for manual release:
   ```python
   def release_if_stale(self) -> bool:
       """
       Check if lock is stale (owning process no longer exists).
       If stale, remove lock file.
       
       Returns True if lock was stale and removed.
       """
       if not self.lock_file.exists():
           return False
       
       # Read PID from lock metadata (filelock stores this internally)
       # For our purposes, check if lock file is old
       import time
       
       lock_age = time.time() - self.lock_file.stat().st_mtime
       
       # If lock older than 2x timeout, consider stale
       if lock_age > (self.timeout_seconds * 2):
           try:
               self.lock_file.unlink()
               return True
           except OSError:
               return False
       
       return False
   ```

**Files**:
- `src/specify_cli/mcp/session/locking.py` (add release_if_stale, ~25 lines)

**Validation**:
- [ ] Context manager releases lock on normal exit
- [ ] Context manager releases lock on exception
- [ ] release_if_stale() detects old locks
- [ ] Stale lock file removed successfully

**Notes**:
- filelock auto-releases on process exit
- Manual cleanup for stale locks (process crashed)

---

### Subtask T018 – Add stale lock detection and cleanup

**Purpose**: Detect locks from crashed processes and clean them up automatically.

**Steps**:
1. Enhance stale detection with PID check:
   ```python
   import psutil
   
   def is_lock_active(self) -> bool:
       """Check if lock is held by active process."""
       if not self.lock_file.exists():
           return False
       
       # Try to read PID from lock file (if we stored it)
       # For filelock, check if process can acquire
       try:
           lock = FileLock(self.lock_file, timeout=0.1)
           with lock.acquire(timeout=0.1):
               # Successfully acquired, was not locked
               return False
       except Timeout:
           # Could not acquire, is locked
           return True
   ```
2. Add auto-cleanup before acquisition:
   ```python
   @contextmanager
   def acquire(self):
       """Acquire lock with automatic stale lock cleanup."""
       # Check for stale lock before attempting acquisition
       if self.release_if_stale():
           # Log warning about stale lock cleanup
           import logging
           logging.warning(
               f"Cleaned up stale lock for {self.resource_id}"
           )
       
       # Rest of acquisition logic from T016...
   ```

**Files**:
- `src/specify_cli/mcp/session/locking.py` (enhance acquire, ~20 lines)

**Validation**:
- [ ] Stale lock detection identifies old locks
- [ ] Auto-cleanup runs before acquisition
- [ ] Warning logged when stale lock cleaned
- [ ] Acquisition succeeds after cleanup

---

### Subtask T019 – Implement lock granularity

**Purpose**: Support different lock scopes (per-WP, per-feature, per-config).

**Steps**:
1. Add helper factory methods:
   ```python
   @classmethod
   def for_work_package(
       cls,
       lock_dir: Path,
       wp_id: str,
       timeout_seconds: int = 300
   ) -> "ResourceLock":
       """Create lock for a work package."""
       return cls.for_resource(lock_dir, f"WP-{wp_id}", timeout_seconds)
   
   @classmethod
   def for_feature(
       cls,
       lock_dir: Path,
       feature_slug: str,
       timeout_seconds: int = 300
   ) -> "ResourceLock":
       """Create lock for an entire feature."""
       return cls.for_resource(lock_dir, f"feature-{feature_slug}", timeout_seconds)
   
   @classmethod
   def for_config_file(
       cls,
       lock_dir: Path,
       config_name: str = "config",
       timeout_seconds: int = 300
   ) -> "ResourceLock":
       """Create lock for a configuration file."""
       return cls.for_resource(lock_dir, f"config-{config_name}", timeout_seconds)
   ```
2. Add tests for each granularity level:
   ```python
   def test_work_package_lock_isolation(tmp_path):
       """Test that WP locks are independent."""
       lock1 = ResourceLock.for_work_package(tmp_path, "WP01")
       lock2 = ResourceLock.for_work_package(tmp_path, "WP02")
       
       with lock1.acquire():
           # lock2 should be acquirable (different resource)
           with lock2.acquire():
               assert lock1.owner_pid == lock2.owner_pid
   ```

**Files**:
- `src/specify_cli/mcp/session/locking.py` (add factory methods, ~40 lines)
- `tests/mcp/test_locking.py` (add granularity tests, ~60 lines)

**Validation**:
- [ ] Work package locks are independent (WP01 vs WP02)
- [ ] Feature lock blocks all WPs in that feature
- [ ] Config lock isolated from feature/WP locks
- [ ] Lock file naming convention clear (.lock-WP-WP01, .lock-feature-025-mcp-server)

---

## Test Strategy

**Unit Tests** (`tests/mcp/test_locking.py`):
- Lock acquisition success/failure
- Timeout behavior
- Stale lock detection and cleanup
- Context manager exception handling
- Lock granularity isolation

**Concurrency Tests**:
- Two processes attempting to lock same resource
- Lock release timing
- Cleanup after process crash (simulate with kill)

**Edge Cases**:
- Lock file already exists (stale)
- Permission denied (lock_dir not writable)
- Timeout of zero (fail fast)
- Very short timeout (<1 second)

---

## Risks & Mitigations

**Risk 1: Race condition during stale cleanup**
- **Mitigation**: filelock handles this internally; our cleanup is best-effort

**Risk 2: Lock file orphaned after hard crash**
- **Mitigation**: Age-based stale detection (2x timeout)

**Risk 3: Cross-platform lock behavior differences**
- **Mitigation**: filelock abstracts this; test on Windows + Unix

**Risk 4: Timeout too short causes false failures**
- **Mitigation**: Default 5 minutes (generous); configurable per operation

---

## Review Guidance

**Key Checkpoints**:
- [ ] filelock integrated correctly
- [ ] ResourceLock matches data-model.md
- [ ] Context manager pattern used consistently
- [ ] Stale lock cleanup automatic and logged
- [ ] Lock granularity supports WP, feature, config scopes
- [ ] Tests cover concurrent access scenarios
- [ ] Cross-platform compatibility verified

**Acceptance Criteria**:
- Multiple clients can safely access different resources (no false blocking)
- Same resource locked by one client at a time
- Stale locks cleaned up automatically
- Clear error messages on timeout

---

## Activity Log

- 2026-01-31T00:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

**Implementation Command**:
```bash
spec-kitty implement WP03 --base WP02
```
- 2026-01-31T12:38:20Z – unknown – shell_pid=61781 – lane=for_review – Ready for review: Implemented file locking with ResourceLock dataclass, context manager pattern, stale lock detection, and comprehensive test coverage (23 tests passing)
- 2026-01-31T12:39:42Z – cursor-reviewer – shell_pid=71171 – lane=doing – Started review via workflow command
- 2026-01-31T12:41:03Z – cursor-reviewer – shell_pid=71171 – lane=done – Review passed: Excellent implementation of file locking system. All 23 tests passing, proper ResourceLock dataclass with context manager pattern, stale lock detection working, lock granularity implemented (WP/feature/config), good integration with ProjectContext. Code quality is high with comprehensive docstrings and error handling. Ready for production.
