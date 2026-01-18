---
work_package_id: "WP04"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "State Management"
phase: "Phase 1 - Components"
lane: "doing"
assignee: ""
agent: "claude-opus"
shell_pid: "46741"
review_status: ""
reviewed_by: ""
dependencies:
  - "WP01"
history:
  - timestamp: "2026-01-18T16:21:51Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – State Management

## Objectives & Success Criteria

Implement orchestration state persistence to enable resume after interruption.

**Success Criteria**:
- OrchestrationRun, WPExecution, InvocationResult dataclasses implemented
- State saves to `.kittify/orchestration-state.json`
- State loads correctly, preserving all fields
- Atomic writes prevent corruption on crash
- State transitions validated per data-model.md rules

## Context & Constraints

**Reference Documents**:
- [data-model.md](../data-model.md) - Entity schemas, validation rules, JSON schema
- [spec.md](../spec.md) - FR-010, FR-011, FR-012 (state management requirements)
- [plan.md](../plan.md) - Follow `merge/state.py` patterns

**Existing Patterns**:
- `src/specify_cli/merge/state.py` - MergeState persistence pattern

**Implementation Command**:
```bash
spec-kitty implement WP04 --base WP01
```

## Subtasks & Detailed Guidance

### Subtask T017 – Implement OrchestrationRun dataclass

**Purpose**: Track complete orchestration execution state.

**Steps**:
1. Create `src/specify_cli/orchestrator/state.py`
2. Implement OrchestrationRun matching data-model.md:
   ```python
   from dataclasses import dataclass, field
   from datetime import datetime
   from typing import Any

   @dataclass
   class OrchestrationRun:
       run_id: str
       feature_slug: str
       started_at: datetime
       completed_at: datetime | None
       status: OrchestrationStatus

       # Configuration snapshot
       config_hash: str
       concurrency_limit: int

       # Progress tracking
       wps_total: int
       wps_completed: int = 0
       wps_failed: int = 0

       # Metrics
       parallel_peak: int = 0
       total_agent_invocations: int = 0

       # Work package states
       work_packages: dict[str, "WPExecution"] = field(default_factory=dict)
   ```

3. Add serialization methods:
   ```python
   def to_dict(self) -> dict[str, Any]:
       """Serialize to JSON-compatible dict."""
       ...

   @classmethod
   def from_dict(cls, data: dict[str, Any]) -> "OrchestrationRun":
       """Deserialize from dict."""
       ...
   ```

**Files**:
- `src/specify_cli/orchestrator/state.py`

**Parallel?**: Yes - can proceed alongside T018, T019

---

### Subtask T018 – Implement WPExecution dataclass

**Purpose**: Track individual work package execution state.

**Steps**:
1. Add to `state.py`:
   ```python
   @dataclass
   class WPExecution:
       wp_id: str
       status: WPStatus

       # Implementation phase
       implementation_agent: str | None = None
       implementation_started: datetime | None = None
       implementation_completed: datetime | None = None
       implementation_exit_code: int | None = None
       implementation_retries: int = 0

       # Review phase
       review_agent: str | None = None
       review_started: datetime | None = None
       review_completed: datetime | None = None
       review_exit_code: int | None = None
       review_retries: int = 0

       # Output tracking
       log_file: Path | None = None
       worktree_path: Path | None = None

       # Error tracking
       last_error: str | None = None
       fallback_agents_tried: list[str] = field(default_factory=list)
   ```

2. Add validation method:
   ```python
   def validate(self) -> None:
       """Validate state transitions per data-model.md rules."""
       if self.implementation_completed and not self.implementation_started:
           raise StateValidationError("implementation_completed requires implementation_started")
       if self.review_started and not self.implementation_completed:
           raise StateValidationError("review_started requires implementation_completed")
   ```

**Parallel?**: Yes

---

### Subtask T019 – Implement InvocationResult dataclass

**Purpose**: Capture result from a single agent invocation.

**Steps**:
1. Move InvocationResult from `agents/base.py` to `state.py` (or keep in base and import):
   ```python
   @dataclass
   class InvocationResult:
       success: bool
       exit_code: int

       # Parsed from JSON output if available
       files_modified: list[str] | None = None
       commits_made: list[str] | None = None
       errors: list[str] | None = None
       warnings: list[str] | None = None

       # Raw output
       stdout: str = ""
       stderr: str = ""
       duration_seconds: float = 0.0
   ```

**Notes**:
- This may already exist in WP02; ensure consistent definition
- Consider keeping in `agents/base.py` and importing to `state.py`

**Parallel?**: Yes

---

### Subtask T020 – Implement state.py with save/load JSON functions

**Purpose**: Persist and restore orchestration state.

**Steps**:
1. Implement save function:
   ```python
   def save_state(state: OrchestrationRun, repo_root: Path) -> None:
       """Save orchestration state to JSON file."""
       state_file = repo_root / ".kittify" / "orchestration-state.json"
       state_file.parent.mkdir(parents=True, exist_ok=True)

       data = state.to_dict()
       # Atomic write via temp file
       _atomic_write(state_file, data)
   ```

2. Implement load function:
   ```python
   def load_state(repo_root: Path) -> OrchestrationRun | None:
       """Load orchestration state from JSON file."""
       state_file = repo_root / ".kittify" / "orchestration-state.json"
       if not state_file.exists():
           return None

       with open(state_file) as f:
           data = json.load(f)

       return OrchestrationRun.from_dict(data)
   ```

3. Implement helper functions:
   ```python
   def has_active_orchestration(repo_root: Path) -> bool:
       """Check if there's an active (running/paused) orchestration."""
       ...

   def clear_state(repo_root: Path) -> None:
       """Remove state file."""
       ...
   ```

**Files**:
- `src/specify_cli/orchestrator/state.py`

---

### Subtask T021 – Implement atomic writes with backup

**Purpose**: Prevent state corruption from crashes during write.

**Steps**:
1. Implement atomic write pattern:
   ```python
   import tempfile
   import shutil

   def _atomic_write(path: Path, data: dict) -> None:
       """Write JSON atomically via temp file rename."""
       # Create backup of existing state
       if path.exists():
           backup_path = path.with_suffix(".json.bak")
           shutil.copy2(path, backup_path)

       # Write to temp file in same directory (ensures same filesystem)
       fd, temp_path = tempfile.mkstemp(
           dir=path.parent,
           prefix=".orchestration-state-",
           suffix=".tmp"
       )
       try:
           with os.fdopen(fd, "w") as f:
               json.dump(data, f, indent=2, default=_json_serializer)
           # Atomic rename
           os.rename(temp_path, path)
       except Exception:
           # Clean up temp file on failure
           if os.path.exists(temp_path):
               os.unlink(temp_path)
           raise
   ```

2. Implement JSON serializer for datetime:
   ```python
   def _json_serializer(obj: Any) -> Any:
       """JSON serializer for datetime and Path objects."""
       if isinstance(obj, datetime):
           return obj.isoformat()
       if isinstance(obj, Path):
           return str(obj)
       raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
   ```

**Notes**:
- Backup file allows recovery if new write is corrupted
- Atomic rename ensures either old or new state, never partial

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| State corruption on crash | Atomic writes via temp file + rename |
| Datetime serialization | Custom JSON serializer |
| Cross-filesystem atomic rename | Temp file in same directory |

## Definition of Done Checklist

- [ ] OrchestrationRun dataclass with to_dict/from_dict
- [ ] WPExecution dataclass with validation
- [ ] InvocationResult dataclass defined
- [ ] `save_state()` writes JSON atomically
- [ ] `load_state()` reads and deserializes correctly
- [ ] Backup created before each write
- [ ] Datetime and Path serialization works

## Review Guidance

- Verify all fields from data-model.md are present
- Test save/load round-trip preserves all data
- Verify atomic write creates temp file in same directory
- Test validation rules catch invalid state transitions

## Activity Log

- 2026-01-18T16:21:51Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T19:00:10Z – claude-opus – shell_pid=46741 – lane=doing – Started implementation via workflow command
