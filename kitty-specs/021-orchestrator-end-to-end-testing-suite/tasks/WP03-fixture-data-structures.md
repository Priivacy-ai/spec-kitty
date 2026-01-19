---
work_package_id: "WP03"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "Fixture Data Structures"
phase: "Phase 0 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude-opus"
shell_pid: "6815"
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-19T09:30:27Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Fixture Data Structures

## Implementation Command

```bash
spec-kitty implement WP03
```

No dependencies - this WP branches from main. Can proceed in parallel with WP01 and WP02.

---

## Objectives & Success Criteria

Define all data structures for fixture management:

- [ ] `FixtureCheckpoint` dataclass represents a restorable snapshot
- [ ] `WorktreeMetadata` dataclass represents git worktree info
- [ ] `TestContext` dataclass combines all test runtime context
- [ ] JSON schema validation for `worktrees.json` format
- [ ] JSON schema validation for `state.json` (OrchestrationRun)

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/data-model.md` - All entity definitions
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Fixture structure

**Existing Code**:
- `src/specify_cli/orchestrator/state.py` - `OrchestrationRun` dataclass

**Constraints**:
- Use `pathlib.Path` for all file paths
- Match data-model.md specifications exactly
- Ensure JSON serialization/deserialization works

---

## Subtasks & Detailed Guidance

### Subtask T010 – Implement FixtureCheckpoint dataclass

**Purpose**: Represent a restorable snapshot of orchestration state.

**Steps**:
1. Open `src/specify_cli/orchestrator/testing/fixtures.py`
2. Add imports:
   ```python
   from __future__ import annotations

   from dataclasses import dataclass, field
   from datetime import datetime
   from pathlib import Path
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from specify_cli.orchestrator.state import OrchestrationRun
       from specify_cli.orchestrator.testing.paths import TestPath
   ```

3. Implement dataclass:
   ```python
   @dataclass
   class FixtureCheckpoint:
       """A restorable snapshot of orchestration state."""

       name: str
       """Checkpoint identifier (e.g., 'wp_created', 'review_pending')."""

       path: Path
       """Absolute path to the checkpoint directory."""

       orchestrator_version: str
       """Version of spec-kitty that created this checkpoint."""

       created_at: datetime
       """When this checkpoint was created."""

       @property
       def state_file(self) -> Path:
           """Path to state.json within checkpoint."""
           return self.path / "state.json"

       @property
       def feature_dir(self) -> Path:
           """Path to feature/ directory within checkpoint."""
           return self.path / "feature"

       @property
       def worktrees_file(self) -> Path:
           """Path to worktrees.json within checkpoint."""
           return self.path / "worktrees.json"

       def exists(self) -> bool:
           """Check if all required checkpoint files exist."""
           return (
               self.path.exists()
               and self.state_file.exists()
               and self.feature_dir.exists()
               and self.worktrees_file.exists()
           )
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/fixtures.py` (~50 lines)

**Parallel?**: Yes - can proceed with T011, T012

---

### Subtask T011 – Implement WorktreeMetadata dataclass

**Purpose**: Store information needed to recreate a git worktree.

**Steps**:
1. Add to `fixtures.py`:
   ```python
   @dataclass
   class WorktreeMetadata:
       """Information needed to recreate a git worktree."""

       wp_id: str
       """Work package identifier (e.g., 'WP01')."""

       branch_name: str
       """Git branch name for this worktree."""

       relative_path: str
       """Path relative to repo root (e.g., '.worktrees/test-feature-WP01')."""

       commit_hash: str | None = None
       """Optional commit hash to checkout (None = branch HEAD)."""

       def to_dict(self) -> dict:
           """Convert to JSON-serializable dict."""
           return {
               "wp_id": self.wp_id,
               "branch_name": self.branch_name,
               "relative_path": self.relative_path,
               "commit_hash": self.commit_hash,
           }

       @classmethod
       def from_dict(cls, data: dict) -> WorktreeMetadata:
           """Create from JSON dict."""
           return cls(
               wp_id=data["wp_id"],
               branch_name=data["branch_name"],
               relative_path=data["relative_path"],
               commit_hash=data.get("commit_hash"),
           )
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~35 lines)

**Parallel?**: Yes - can proceed with T010, T012

---

### Subtask T012 – Implement TestContext dataclass

**Purpose**: Combine all runtime context for an e2e test.

**Steps**:
1. Add to `fixtures.py`:
   ```python
   @dataclass
   class TestContext:
       """Complete context for running an e2e orchestrator test."""

       temp_dir: Path
       """Temporary directory containing the test environment."""

       repo_root: Path
       """Root of the test git repository."""

       feature_dir: Path
       """Path to the test feature directory."""

       test_path: "TestPath"
       """Selected test path with agent assignments."""

       checkpoint: FixtureCheckpoint | None = None
       """Loaded checkpoint if test started from snapshot."""

       orchestration_state: "OrchestrationRun | None" = None
       """Loaded state from checkpoint (None if fresh start)."""

       worktrees: list[WorktreeMetadata] = field(default_factory=list)
       """Worktree metadata for this test context."""

       @property
       def kitty_specs_dir(self) -> Path:
           """Path to kitty-specs directory in test repo."""
           return self.repo_root / "kitty-specs"

       @property
       def worktrees_dir(self) -> Path:
           """Path to .worktrees directory in test repo."""
           return self.repo_root / ".worktrees"

       @property
       def state_file(self) -> Path:
           """Path to orchestration state file."""
           return self.feature_dir / ".orchestration-state.json"
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~45 lines)

**Parallel?**: Yes - can proceed with T010, T011

---

### Subtask T013 – Add worktrees.json schema validation

**Purpose**: Validate worktrees.json files when loading fixtures.

**Steps**:
1. Add validation function:
   ```python
   import json

   class WorktreesFileError(Exception):
       """Error loading or validating worktrees.json."""
       pass

   def load_worktrees_file(path: Path) -> list[WorktreeMetadata]:
       """Load and validate worktrees.json file.

       Args:
           path: Path to worktrees.json

       Returns:
           List of WorktreeMetadata objects

       Raises:
           WorktreesFileError: If file is invalid
       """
       if not path.exists():
           raise WorktreesFileError(f"Worktrees file not found: {path}")

       try:
           with open(path) as f:
               data = json.load(f)
       except json.JSONDecodeError as e:
           raise WorktreesFileError(f"Invalid JSON in {path}: {e}")

       # Validate structure
       if not isinstance(data, dict):
           raise WorktreesFileError(f"Expected object, got {type(data).__name__}")

       if "worktrees" not in data:
           raise WorktreesFileError("Missing 'worktrees' key")

       worktrees_list = data["worktrees"]
       if not isinstance(worktrees_list, list):
           raise WorktreesFileError("'worktrees' must be an array")

       # Parse each worktree
       result = []
       for i, item in enumerate(worktrees_list):
           required_keys = {"wp_id", "branch_name", "relative_path"}
           missing = required_keys - set(item.keys())
           if missing:
               raise WorktreesFileError(
                   f"Worktree {i} missing keys: {missing}"
               )
           result.append(WorktreeMetadata.from_dict(item))

       return result

   def save_worktrees_file(path: Path, worktrees: list[WorktreeMetadata]) -> None:
       """Save worktrees to JSON file.

       Args:
           path: Path to write to
           worktrees: List of worktree metadata
       """
       data = {"worktrees": [w.to_dict() for w in worktrees]}
       with open(path, "w") as f:
           json.dump(data, f, indent=2)
   ```

**Files**:
- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~55 lines)

**Parallel?**: No - depends on T011

---

### Subtask T014 – Add state.json schema validation

**Purpose**: Validate state.json files (OrchestrationRun format).

**Steps**:
1. Add validation function:
   ```python
   from specify_cli.orchestrator.state import OrchestrationRun

   class StateFileError(Exception):
       """Error loading or validating state.json."""
       pass

   def load_state_file(path: Path) -> OrchestrationRun:
       """Load and validate state.json file.

       Args:
           path: Path to state.json

       Returns:
           OrchestrationRun object

       Raises:
           StateFileError: If file is invalid
       """
       if not path.exists():
           raise StateFileError(f"State file not found: {path}")

       try:
           with open(path) as f:
               data = json.load(f)
       except json.JSONDecodeError as e:
           raise StateFileError(f"Invalid JSON in {path}: {e}")

       # Validate required fields
       required_fields = {
           "run_id", "feature_slug", "started_at", "status",
           "wps_total", "wps_completed", "wps_failed", "work_packages"
       }
       missing = required_fields - set(data.keys())
       if missing:
           raise StateFileError(f"Missing required fields: {missing}")

       # Use OrchestrationRun's deserialization
       try:
           return OrchestrationRun.from_dict(data)
       except Exception as e:
           raise StateFileError(f"Failed to parse OrchestrationRun: {e}")

   def save_state_file(path: Path, state: OrchestrationRun) -> None:
       """Save OrchestrationRun to JSON file.

       Args:
           path: Path to write to
           state: Orchestration state
       """
       with open(path, "w") as f:
           json.dump(state.to_dict(), f, indent=2)
   ```

2. Note: May need to check if `OrchestrationRun.from_dict()` and `to_dict()` exist. If not, implement them or use dataclasses.asdict().

**Files**:
- `src/specify_cli/orchestrator/testing/fixtures.py` (add ~50 lines)

**Parallel?**: No - depends on T010

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| OrchestrationRun serialization missing | Check existing state.py; implement if needed |
| Circular imports | Use TYPE_CHECKING guard for imports |
| Schema drift | Import directly from orchestrator.state |
| Path handling on Windows | Use pathlib consistently |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] All three dataclasses match data-model.md
- [ ] `WorktreeMetadata.from_dict()` and `to_dict()` work correctly
- [ ] `load_worktrees_file()` validates schema and returns list
- [ ] `load_state_file()` returns valid `OrchestrationRun`
- [ ] Error messages are clear and actionable

**Code Quality**:
- Type hints on all functions
- Custom exceptions for each file type
- Proper JSON handling with error recovery

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
- 2026-01-19T09:47:29Z – claude-opus – shell_pid=6815 – lane=doing – Started implementation via workflow command
- 2026-01-19T09:54:50Z – claude-opus – shell_pid=6815 – lane=for_review – Ready for review: Implemented FixtureCheckpoint, WorktreeMetadata, TestContext dataclasses with JSON schema validation for worktrees.json and state.json. 40 tests passing.
