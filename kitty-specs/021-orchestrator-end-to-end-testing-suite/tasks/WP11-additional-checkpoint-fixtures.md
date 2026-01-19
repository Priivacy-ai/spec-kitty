---
work_package_id: WP11
title: Additional Checkpoint Fixtures
lane: "doing"
dependencies:
- WP03
subtasks:
- T052
- T053
- T054
- T055
phase: Phase 2 - Extended
assignee: ''
agent: "claude-opus"
shell_pid: "48855"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T09:30:27Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP11 – Additional Checkpoint Fixtures

## Implementation Command

```bash
spec-kitty implement WP11 --base WP05
```

Depends on WP03 (dataclasses) and WP05 (initial fixtures for reference).

---

## Objectives & Success Criteria

Complete the remaining checkpoint fixtures:

- [ ] `checkpoint_review_rejected/` fixture exists with rejection state
- [ ] `checkpoint_review_approved/` fixture exists with approval state
- [ ] `checkpoint_wp_merged/` fixture exists with post-merge state
- [ ] Stale checkpoint detection warns on version mismatch

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/data-model.md` - Standard checkpoints table
- `tests/fixtures/orchestrator/` - Existing fixtures from WP05

**Existing Code**:
- `tests/fixtures/orchestrator/checkpoint_wp_created/` - Reference structure
- `tests/fixtures/orchestrator/__init__.py` - Fixture manifest

**Constraints**:
- Follow same structure as WP05 checkpoints
- Keep features minimal (2 WPs)
- Add version field for staleness detection

---

## Subtasks & Detailed Guidance

### Subtask T052 – Create checkpoint_review_rejected fixture

**Purpose**: Fixture representing WP01 after review rejection.

**Steps**:
1. Create directory:
   ```bash
   mkdir -p tests/fixtures/orchestrator/checkpoint_review_rejected/feature/tasks
   ```

2. Copy base feature files from `checkpoint_wp_created`:
   ```bash
   cp -r tests/fixtures/orchestrator/checkpoint_wp_created/feature/* \
         tests/fixtures/orchestrator/checkpoint_review_rejected/feature/
   ```

3. Create `tests/fixtures/orchestrator/checkpoint_review_rejected/state.json`:
   ```json
   {
     "run_id": "test-run-001",
     "feature_slug": "test-feature",
     "started_at": "2026-01-01T00:00:00Z",
     "status": "running",
     "wps_total": 2,
     "wps_completed": 0,
     "wps_failed": 0,
     "work_packages": {
       "WP01": {
         "wp_id": "WP01",
         "status": "review_rejected",
         "dependencies": [],
         "implementation_agent": "claude",
         "review_agent": "codex",
         "started_at": "2026-01-01T00:01:00Z",
         "implementation_completed_at": "2026-01-01T00:05:00Z",
         "review_started_at": "2026-01-01T00:06:00Z",
         "review_completed_at": "2026-01-01T00:10:00Z",
         "review_count": 1,
         "rejection_reason": "Missing error handling in edge case",
         "history": [
           {
             "timestamp": "2026-01-01T00:01:00Z",
             "from_status": "pending",
             "to_status": "in_progress",
             "agent": "claude"
           },
           {
             "timestamp": "2026-01-01T00:05:00Z",
             "from_status": "in_progress",
             "to_status": "in_review",
             "agent": "claude"
           },
           {
             "timestamp": "2026-01-01T00:10:00Z",
             "from_status": "in_review",
             "to_status": "review_rejected",
             "agent": "codex"
           }
         ]
       },
       "WP02": {
         "wp_id": "WP02",
         "status": "pending",
         "dependencies": ["WP01"]
       }
     }
   }
   ```

4. Update `tests/fixtures/orchestrator/checkpoint_review_rejected/feature/tasks/WP01.md` frontmatter:
   ```yaml
   ---
   work_package_id: "WP01"
   title: "First Task"
   lane: "doing"
   dependencies: []
   subtasks: ["T001"]
   review_status: "rejected"
   reviewed_by: "codex"
   ---
   ```

5. Create `tests/fixtures/orchestrator/checkpoint_review_rejected/worktrees.json`:
   ```json
   {
     "worktrees": [
       {
         "wp_id": "WP01",
         "branch_name": "test-feature-WP01",
         "relative_path": ".worktrees/test-feature-WP01",
         "commit_hash": null
       }
     ]
   }
   ```

**Files**:
- `tests/fixtures/orchestrator/checkpoint_review_rejected/` (complete directory)

**Parallel?**: Yes - can proceed with T053, T054

---

### Subtask T053 – Create checkpoint_review_approved fixture

**Purpose**: Fixture representing WP01 after review approval.

**Steps**:
1. Create directory:
   ```bash
   mkdir -p tests/fixtures/orchestrator/checkpoint_review_approved/feature/tasks
   ```

2. Copy base feature files.

3. Create `tests/fixtures/orchestrator/checkpoint_review_approved/state.json`:
   ```json
   {
     "run_id": "test-run-001",
     "feature_slug": "test-feature",
     "started_at": "2026-01-01T00:00:00Z",
     "status": "running",
     "wps_total": 2,
     "wps_completed": 1,
     "wps_failed": 0,
     "work_packages": {
       "WP01": {
         "wp_id": "WP01",
         "status": "review_approved",
         "dependencies": [],
         "implementation_agent": "claude",
         "review_agent": "codex",
         "started_at": "2026-01-01T00:01:00Z",
         "implementation_completed_at": "2026-01-01T00:05:00Z",
         "review_started_at": "2026-01-01T00:06:00Z",
         "review_completed_at": "2026-01-01T00:10:00Z",
         "review_count": 1,
         "history": [
           {
             "timestamp": "2026-01-01T00:01:00Z",
             "from_status": "pending",
             "to_status": "in_progress",
             "agent": "claude"
           },
           {
             "timestamp": "2026-01-01T00:05:00Z",
             "from_status": "in_progress",
             "to_status": "in_review",
             "agent": "claude"
           },
           {
             "timestamp": "2026-01-01T00:10:00Z",
             "from_status": "in_review",
             "to_status": "review_approved",
             "agent": "codex"
           }
         ]
       },
       "WP02": {
         "wp_id": "WP02",
         "status": "pending",
         "dependencies": ["WP01"]
       }
     }
   }
   ```

4. Update WP01.md frontmatter:
   ```yaml
   ---
   work_package_id: "WP01"
   title: "First Task"
   lane: "for_review"
   dependencies: []
   subtasks: ["T001"]
   review_status: "approved"
   reviewed_by: "codex"
   ---
   ```

5. Create worktrees.json (same as T052).

**Files**:
- `tests/fixtures/orchestrator/checkpoint_review_approved/` (complete directory)

**Parallel?**: Yes - can proceed with T052, T054

---

### Subtask T054 – Create checkpoint_wp_merged fixture

**Purpose**: Fixture representing WP01 after merge to main.

**Steps**:
1. Create directory:
   ```bash
   mkdir -p tests/fixtures/orchestrator/checkpoint_wp_merged/feature/tasks
   ```

2. Copy base feature files.

3. Create `tests/fixtures/orchestrator/checkpoint_wp_merged/state.json`:
   ```json
   {
     "run_id": "test-run-001",
     "feature_slug": "test-feature",
     "started_at": "2026-01-01T00:00:00Z",
     "status": "running",
     "wps_total": 2,
     "wps_completed": 1,
     "wps_failed": 0,
     "work_packages": {
       "WP01": {
         "wp_id": "WP01",
         "status": "done",
         "dependencies": [],
         "implementation_agent": "claude",
         "review_agent": "codex",
         "started_at": "2026-01-01T00:01:00Z",
         "implementation_completed_at": "2026-01-01T00:05:00Z",
         "review_started_at": "2026-01-01T00:06:00Z",
         "review_completed_at": "2026-01-01T00:10:00Z",
         "merged_at": "2026-01-01T00:15:00Z",
         "merge_commit": "abc123def456",
         "review_count": 1,
         "history": [
           {
             "timestamp": "2026-01-01T00:01:00Z",
             "from_status": "pending",
             "to_status": "in_progress",
             "agent": "claude"
           },
           {
             "timestamp": "2026-01-01T00:05:00Z",
             "from_status": "in_progress",
             "to_status": "in_review",
             "agent": "claude"
           },
           {
             "timestamp": "2026-01-01T00:10:00Z",
             "from_status": "in_review",
             "to_status": "review_approved",
             "agent": "codex"
           },
           {
             "timestamp": "2026-01-01T00:15:00Z",
             "from_status": "review_approved",
             "to_status": "done",
             "agent": "system"
           }
         ]
       },
       "WP02": {
         "wp_id": "WP02",
         "status": "in_progress",
         "dependencies": ["WP01"],
         "started_at": "2026-01-01T00:16:00Z",
         "implementation_agent": "claude"
       }
     }
   }
   ```

4. Update WP01.md frontmatter:
   ```yaml
   ---
   work_package_id: "WP01"
   title: "First Task"
   lane: "done"
   dependencies: []
   subtasks: ["T001"]
   review_status: "approved"
   reviewed_by: "codex"
   ---
   ```

5. Create worktrees.json:
   ```json
   {
     "worktrees": [
       {
         "wp_id": "WP02",
         "branch_name": "test-feature-WP02",
         "relative_path": ".worktrees/test-feature-WP02",
         "commit_hash": null
       }
     ]
   }
   ```
   Note: WP01 worktree removed after merge, WP02 worktree active.

**Files**:
- `tests/fixtures/orchestrator/checkpoint_wp_merged/` (complete directory)

**Parallel?**: Yes - can proceed with T052, T053

---

### Subtask T055 – Add stale checkpoint detection

**Purpose**: Warn when fixture version doesn't match current orchestrator.

**Steps**:
1. Update `tests/fixtures/orchestrator/__init__.py`:
   ```python
   """Orchestrator test fixtures.

   Available checkpoints:
   - wp_created: WPs exist in planned lane
   - wp_implemented: WP01 implemented, awaiting review
   - review_pending: WP01 in review
   - review_rejected: WP01 review rejected
   - review_approved: WP01 review approved
   - wp_merged: WP01 merged to main
   """

   from pathlib import Path
   from datetime import datetime
   import warnings

   FIXTURES_DIR = Path(__file__).parent

   # Fixture version - update when fixture schema changes
   FIXTURES_VERSION = "021.1"

   # Checkpoint registry with descriptions
   CHECKPOINTS = {
       "wp_created": "Initial state with WPs in planned lane",
       "wp_implemented": "WP01 implemented, awaiting review",
       "review_pending": "WP01 submitted for review",
       "review_rejected": "WP01 review rejected",
       "review_approved": "WP01 review approved",
       "wp_merged": "WP01 merged to main",
   }


   def get_checkpoint_path(name: str) -> Path:
       """Get path to a checkpoint fixture.

       Args:
           name: Checkpoint name (e.g., 'wp_created')

       Returns:
           Path to checkpoint directory

       Raises:
           ValueError: If checkpoint doesn't exist
       """
       if name not in CHECKPOINTS:
           available = ", ".join(CHECKPOINTS.keys())
           raise ValueError(
               f"Unknown checkpoint: {name}. Available: {available}"
           )

       path = FIXTURES_DIR / f"checkpoint_{name}"
       if not path.exists():
           raise ValueError(f"Checkpoint directory missing: {path}")

       return path


   def list_checkpoints() -> list[str]:
       """List all available checkpoint names."""
       return list(CHECKPOINTS.keys())


   def check_fixture_staleness(checkpoint_path: Path) -> tuple[bool, str | None]:
       """Check if a fixture might be stale.

       Args:
           checkpoint_path: Path to checkpoint directory

       Returns:
           Tuple of (is_stale, warning_message)
       """
       import json

       state_file = checkpoint_path / "state.json"
       if not state_file.exists():
           return True, f"Missing state.json in {checkpoint_path}"

       try:
           with open(state_file) as f:
               state = json.load(f)

           # Check for version field
           fixture_version = state.get("fixture_version")
           if fixture_version is None:
               return True, (
                   f"Fixture {checkpoint_path.name} has no version field. "
                   f"Current version: {FIXTURES_VERSION}"
               )

           if fixture_version != FIXTURES_VERSION:
               return True, (
                   f"Fixture {checkpoint_path.name} version mismatch: "
                   f"fixture={fixture_version}, current={FIXTURES_VERSION}"
               )

           return False, None

       except json.JSONDecodeError as e:
           return True, f"Invalid JSON in {state_file}: {e}"


   def validate_all_checkpoints() -> list[str]:
       """Validate all checkpoints and return any warnings.

       Returns:
           List of warning messages (empty if all valid)
       """
       warnings_list = []

       for name in CHECKPOINTS:
           try:
               path = get_checkpoint_path(name)
               is_stale, warning = check_fixture_staleness(path)
               if is_stale and warning:
                   warnings_list.append(warning)
           except ValueError as e:
               warnings_list.append(str(e))

       return warnings_list


   def get_checkpoint_with_validation(name: str) -> Path:
       """Get checkpoint path with staleness warning.

       Args:
           name: Checkpoint name

       Returns:
           Path to checkpoint directory

       Warns:
           UserWarning: If fixture may be stale
       """
       path = get_checkpoint_path(name)
       is_stale, warning = check_fixture_staleness(path)

       if is_stale and warning:
           warnings.warn(warning, UserWarning, stacklevel=2)

       return path
   ```

2. Update all state.json files to include version:
   ```json
   {
     "fixture_version": "021.1",
     "run_id": "test-run-001",
     ...
   }
   ```

**Files**:
- `tests/fixtures/orchestrator/__init__.py` (update ~60 lines)
- All `state.json` files (add `fixture_version` field)

**Parallel?**: No - should be last (references all checkpoints)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| State schema changes | Match OrchestrationRun exactly |
| Missing required fields | Validate fixtures load in tests |
| Version not updated | CI check for version bump on schema change |
| History format varies | Document expected history structure |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] All 6 checkpoints exist and are loadable
- [ ] `checkpoint_review_rejected` has rejection_reason
- [ ] `checkpoint_review_approved` has review_count
- [ ] `checkpoint_wp_merged` has merge_commit and merged_at
- [ ] `validate_all_checkpoints()` returns empty list for valid fixtures
- [ ] Staleness warning triggers on version mismatch

**Code Quality**:
- Consistent structure across all checkpoints
- History entries have all required fields
- Version field present in all state.json files
- Clear documentation in `__init__.py`

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
- 2026-01-19T12:58:13Z – claude-opus – shell_pid=48855 – lane=doing – Started implementation via workflow command
