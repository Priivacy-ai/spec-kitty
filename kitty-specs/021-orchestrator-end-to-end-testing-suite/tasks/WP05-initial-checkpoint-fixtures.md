---
work_package_id: "WP05"
subtasks:
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
title: "Initial Checkpoint Fixtures"
phase: "Phase 1 - Fixtures"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP03"]
history:
  - timestamp: "2026-01-19T09:30:27Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Initial Checkpoint Fixtures

## Implementation Command

```bash
spec-kitty implement WP05 --base WP03
```

Depends on WP03 (needs data structure definitions for validation).

---

## Objectives & Success Criteria

Create the first set of checkpoint fixtures for testing:

- [ ] Minimal test feature structure exists with spec.md, plan.md, tasks/
- [ ] `checkpoint_wp_created/` fixture exists with WPs in planned lane
- [ ] `checkpoint_wp_implemented/` fixture exists with WP01 implemented
- [ ] `checkpoint_review_pending/` fixture exists with WP01 in review
- [ ] Fixture manifest allows programmatic discovery

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Fixture structure
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/data-model.md` - Standard checkpoints table

**Constraints**:
- Fixtures go in `tests/fixtures/orchestrator/`
- Each fixture is a directory with state.json, feature/, worktrees.json
- Keep features minimal (2 WPs, no actual implementation code)

---

## Subtasks & Detailed Guidance

### Subtask T021 – Create minimal test feature structure

**Purpose**: Create a reusable minimal feature that all checkpoints will use.

**Steps**:
1. Create base directory:
   ```bash
   mkdir -p tests/fixtures/orchestrator/base_feature
   ```

2. Create `tests/fixtures/orchestrator/base_feature/spec.md`:
   ```markdown
   # Feature Specification: Test Feature

   **Feature Branch**: `test-feature`
   **Created**: 2026-01-01
   **Status**: Draft

   ## Overview

   A minimal test feature for orchestrator e2e tests.

   ## User Scenarios

   ### User Story 1 - Basic Task (Priority: P1)

   A simple task that can be implemented and reviewed.

   **Acceptance Scenarios**:
   1. **Given** the task prompt, **When** implemented, **Then** a file is created.

   ## Requirements

   - **FR-001**: System MUST create a file when WP01 executes
   - **FR-002**: System MUST create a second file when WP02 executes

   ## Success Criteria

   - Files created successfully
   ```

3. Create `tests/fixtures/orchestrator/base_feature/plan.md`:
   ```markdown
   # Implementation Plan: Test Feature

   ## Technical Context

   **Language**: Python 3.11+
   **Testing**: pytest

   ## Project Structure

   ```
   test_output/
   ├── wp01_output.txt
   └── wp02_output.txt
   ```
   ```

4. Create `tests/fixtures/orchestrator/base_feature/meta.json`:
   ```json
   {
     "feature_number": "test",
     "slug": "test-feature",
     "friendly_name": "Test Feature",
     "mission": "software-dev",
     "created_at": "2026-01-01T00:00:00Z"
   }
   ```

5. Create task files - see T022 for WP task content

**Files**:
- `tests/fixtures/orchestrator/base_feature/spec.md` (~30 lines)
- `tests/fixtures/orchestrator/base_feature/plan.md` (~20 lines)
- `tests/fixtures/orchestrator/base_feature/meta.json`

**Parallel?**: No - must complete before T022-T024

---

### Subtask T022 – Create checkpoint_wp_created fixture

**Purpose**: Fixture representing initial state with WPs in planned lane.

**Steps**:
1. Create directory structure:
   ```bash
   mkdir -p tests/fixtures/orchestrator/checkpoint_wp_created/feature/tasks
   ```

2. Copy base feature files:
   ```bash
   cp tests/fixtures/orchestrator/base_feature/* \
      tests/fixtures/orchestrator/checkpoint_wp_created/feature/
   ```

3. Create `tests/fixtures/orchestrator/checkpoint_wp_created/feature/tasks/WP01.md`:
   ```markdown
   ---
   work_package_id: "WP01"
   title: "First Task"
   lane: "planned"
   dependencies: []
   subtasks: ["T001"]
   ---

   # Work Package: WP01 – First Task

   ## Objective

   Create a file at `test_output/wp01_output.txt`.

   ## Subtasks

   ### T001 – Create output file

   Create the file with content "WP01 complete".
   ```

4. Create `tests/fixtures/orchestrator/checkpoint_wp_created/feature/tasks/WP02.md`:
   ```markdown
   ---
   work_package_id: "WP02"
   title: "Second Task"
   lane: "planned"
   dependencies: ["WP01"]
   subtasks: ["T002"]
   ---

   # Work Package: WP02 – Second Task

   ## Objective

   Create a file at `test_output/wp02_output.txt`.

   ## Subtasks

   ### T002 – Create output file

   Create the file with content "WP02 complete".
   ```

5. Create `tests/fixtures/orchestrator/checkpoint_wp_created/state.json`:
   ```json
   {
     "run_id": "test-run-001",
     "feature_slug": "test-feature",
     "started_at": "2026-01-01T00:00:00Z",
     "status": "pending",
     "wps_total": 2,
     "wps_completed": 0,
     "wps_failed": 0,
     "work_packages": {
       "WP01": {
         "wp_id": "WP01",
         "status": "pending",
         "dependencies": []
       },
       "WP02": {
         "wp_id": "WP02",
         "status": "pending",
         "dependencies": ["WP01"]
       }
     }
   }
   ```

6. Create `tests/fixtures/orchestrator/checkpoint_wp_created/worktrees.json`:
   ```json
   {
     "worktrees": []
   }
   ```

**Files**:
- `tests/fixtures/orchestrator/checkpoint_wp_created/feature/tasks/WP01.md`
- `tests/fixtures/orchestrator/checkpoint_wp_created/feature/tasks/WP02.md`
- `tests/fixtures/orchestrator/checkpoint_wp_created/state.json`
- `tests/fixtures/orchestrator/checkpoint_wp_created/worktrees.json`

**Parallel?**: Yes - once T021 complete

---

### Subtask T023 – Create checkpoint_wp_implemented fixture

**Purpose**: Fixture representing WP01 implemented, awaiting review.

**Steps**:
1. Create directory:
   ```bash
   mkdir -p tests/fixtures/orchestrator/checkpoint_wp_implemented/feature/tasks
   ```

2. Copy base files and update WP01 task to lane: "doing"

3. Create `tests/fixtures/orchestrator/checkpoint_wp_implemented/state.json`:
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
         "status": "implementation_complete",
         "dependencies": [],
         "implementation_agent": "claude",
         "started_at": "2026-01-01T00:01:00Z",
         "implementation_completed_at": "2026-01-01T00:05:00Z"
       },
       "WP02": {
         "wp_id": "WP02",
         "status": "pending",
         "dependencies": ["WP01"]
       }
     }
   }
   ```

4. Create worktrees.json with WP01 worktree:
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
- `tests/fixtures/orchestrator/checkpoint_wp_implemented/` (complete directory)

**Parallel?**: Yes - once T021 complete

---

### Subtask T024 – Create checkpoint_review_pending fixture

**Purpose**: Fixture representing WP01 submitted for review.

**Steps**:
1. Create directory structure similar to T023

2. Update state to show review pending:
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
         "status": "in_review",
         "dependencies": [],
         "implementation_agent": "claude",
         "review_agent": "codex",
         "started_at": "2026-01-01T00:01:00Z",
         "implementation_completed_at": "2026-01-01T00:05:00Z",
         "review_started_at": "2026-01-01T00:06:00Z"
       },
       "WP02": {
         "wp_id": "WP02",
         "status": "pending",
         "dependencies": ["WP01"]
       }
     }
   }
   ```

3. Update WP01.md frontmatter to `lane: "for_review"`

**Files**:
- `tests/fixtures/orchestrator/checkpoint_review_pending/` (complete directory)

**Parallel?**: Yes - once T021 complete

---

### Subtask T025 – Add fixture manifest for discovery

**Purpose**: Allow programmatic discovery of available fixtures.

**Steps**:
1. Create `tests/fixtures/orchestrator/__init__.py`:
   ```python
   """Orchestrator test fixtures.

   Available checkpoints:
   - wp_created: WPs exist in planned lane
   - wp_implemented: WP01 implemented, awaiting review
   - review_pending: WP01 in review
   - review_rejected: WP01 review rejected (WP11)
   - review_approved: WP01 review approved (WP11)
   - wp_merged: WP01 merged to main (WP11)
   """

   from pathlib import Path
   from datetime import datetime

   # Import will be available after WP03
   # from specify_cli.orchestrator.testing.fixtures import FixtureCheckpoint

   FIXTURES_DIR = Path(__file__).parent

   # Checkpoint registry
   CHECKPOINTS = {
       "wp_created": "Initial state with WPs in planned lane",
       "wp_implemented": "WP01 implemented, awaiting review",
       "review_pending": "WP01 submitted for review",
       # Added by WP11:
       # "review_rejected": "WP01 review rejected",
       # "review_approved": "WP01 review approved",
       # "wp_merged": "WP01 merged to main",
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

   # Version for staleness detection
   FIXTURES_VERSION = "021.1"
   ```

**Files**:
- `tests/fixtures/orchestrator/__init__.py` (~60 lines)

**Parallel?**: No - should be last (references all checkpoints)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| State schema changes | Match OrchestrationRun exactly from state.py |
| Fixtures become stale | Include version field for detection |
| Missing required fields | Validate fixtures load successfully in tests |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] All checkpoint directories exist with required files
- [ ] state.json matches OrchestrationRun schema
- [ ] worktrees.json is valid (even if empty)
- [ ] WP task files have correct lane frontmatter
- [ ] `get_checkpoint_path()` returns valid paths
- [ ] `list_checkpoints()` returns all available names

**Code Quality**:
- Minimal features (no unnecessary complexity)
- Consistent structure across checkpoints
- Clear documentation in manifest

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
