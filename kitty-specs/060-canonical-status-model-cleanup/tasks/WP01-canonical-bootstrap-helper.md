---
work_package_id: WP01
title: Canonical Bootstrap Helper
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: 88346dd70961ff1ca1d0684c30d134725c221f14
created_at: '2026-03-31T07:05:59.680714+00:00'
subtasks: [T001, T002]
shell_pid: "82589"
history:
- at: '2026-03-31T06:58:09+00:00'
  actor: planner
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/status/bootstrap.py
execution_mode: code_change
owned_files:
- src/specify_cli/status/bootstrap.py
- tests/status/test_bootstrap.py
---

# WP01: Canonical Bootstrap Helper

## Objective

Create `src/specify_cli/status/bootstrap.py` — a shared helper that scans WP files in a feature directory, checks `status.events.jsonl` for existing canonical state, emits initial `planned` events for any WP that lacks one, and materializes `status.json`. This helper is imported by both finalize-tasks entrypoints (WP02 + WP03).

## Context

- The `specify_cli/status/` package already has `emit.py` (`emit_status_transition`), `reducer.py` (`reduce`, `materialize`), `store.py` (`append_event`, `read_events`), and `models.py` (`StatusEvent`, `Lane`).
- This helper uses those existing functions — it does not reimplement status infrastructure.
- After this WP, no active runtime path should need to bootstrap canonical state from frontmatter.

## Implementation Command

```bash
spec-kitty implement WP01
```

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- No dependencies — branch directly from `main`.

---

## Subtask T001: Create bootstrap_canonical_state()

**Purpose**: Single function that ensures every WP in a feature has canonical state.

**Steps**:

1. Create `src/specify_cli/status/bootstrap.py`
2. Implement `bootstrap_canonical_state(feature_dir: Path, feature_slug: str, *, dry_run: bool = False) -> BootstrapResult`:
   - Scan `feature_dir/tasks/` for WP files (`WP*.md`)
   - Parse each WP file's frontmatter to extract `work_package_id`
   - Read existing events from `status.events.jsonl` via `read_events(feature_dir)`
   - For each WP: check if any event exists with that `wp_id`
   - If no event: this WP needs bootstrapping
   - If `dry_run=True`: return report of what would be emitted, without mutating files
   - If `dry_run=False`: for each uninitialized WP, call `emit_status_transition()` with:
     - `feature_dir=feature_dir`
     - `feature_slug=feature_slug`
     - `wp_id=wp_id`
     - `to_lane="planned"`
     - `actor="finalize-tasks"`
     - `force=True` (no prior state to transition from)
   - After all events emitted, call `materialize(feature_dir)` to write `status.json`
   - Return `BootstrapResult` with counts and details

3. Define `BootstrapResult` dataclass:
   ```python
   @dataclass
   class BootstrapResult:
       total_wps: int
       already_initialized: int
       newly_seeded: int
       wp_details: dict[str, str]  # wp_id → "initialized" | "already_exists" | "would_seed" (dry_run)
   ```

4. Handle edge cases:
   - No WP files found → return result with total_wps=0
   - Event log doesn't exist yet → create it by emitting first event
   - WP file with missing/invalid work_package_id → skip with warning in result

**Files**: `src/specify_cli/status/bootstrap.py` (~80 lines)

**Imports needed**:
```python
from specify_cli.status.emit import emit_status_transition
from specify_cli.status.reducer import materialize
from specify_cli.status.store import read_events
from specify_cli.frontmatter import read_frontmatter
```

---

## Subtask T002: Write Tests

**Purpose**: Verify bootstrap behavior for all scenarios.

**Steps**:

1. Create `tests/status/test_bootstrap.py`
2. Write tests:

   a. **Seeds planned events for uninitialized WPs**:
   - Create feature dir with 3 WP files, no event log
   - Call `bootstrap_canonical_state()`
   - Verify 3 events emitted to `status.events.jsonl`, all with `to_lane="planned"`
   - Verify `status.json` materialized with 3 WPs in "planned" lane

   b. **Skips already-initialized WPs**:
   - Create feature dir with 2 WP files and event log with 1 WP's event
   - Call `bootstrap_canonical_state()`
   - Verify only 1 new event emitted (the missing WP)
   - Verify result: `already_initialized=1`, `newly_seeded=1`

   c. **Dry-run does not mutate**:
   - Create feature dir with WP files, no event log
   - Call `bootstrap_canonical_state(dry_run=True)`
   - Verify no `status.events.jsonl` created
   - Verify result reports what would be seeded

   d. **Empty tasks directory**:
   - Feature dir with no WP files
   - Returns `total_wps=0`

   e. **WP with missing work_package_id**:
   - WP file with malformed frontmatter
   - Skipped, others still seeded

**Files**: `tests/status/test_bootstrap.py` (~200 lines)

---

## Definition of Done

- [ ] `bootstrap_canonical_state()` seeds planned events for uninitialized WPs
- [ ] Already-initialized WPs are skipped
- [ ] `dry_run=True` reports without mutating
- [ ] `status.json` materialized after seeding
- [ ] Uses existing `emit_status_transition()` and `materialize()` — no reimplementation
- [ ] Tests cover all scenarios
- [ ] `mypy --strict` passes

## Reviewer Guidance

- Verify the function calls `emit_status_transition()` (not raw `append_event`) to ensure events go through the full validation/materialization pipeline
- Verify `force=True` is used (no prior state to validate against)
- Verify `materialize()` is called after all events are emitted, not after each one
