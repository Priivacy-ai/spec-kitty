---
work_package_id: WP01
title: Storage Path Constants and Model Fields
dependencies: []
requirement_refs:
- FR-001
- FR-006
- FR-007
- FR-009
- FR-010
- NFR-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: claude
history:
- date: '2026-06-05'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/writer.py
- src/specify_cli/invocation/lifecycle.py
- src/specify_cli/invocation/propagator.py
- src/specify_cli/invocation/record.py
- tests/specify_cli/invocation/test_writer.py
- tests/specify_cli/invocation/test_record.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

Wait for the profile to load, then proceed.

---

## Objective

Change 5 storage path constants across 4 existing files to redirect Op records from the gitignored `.kittify/events/` subtree to the git-tracked `kitty-ops/` directory. Add 2 optional timeline-correlation fields (`mission_id`, `wp_id`) to `InvocationRecord`. Write unit tests proving the paths resolve correctly and the model serialises correctly.

This is WP01 of 2 for mission `op-records-git-durability-01KTB49K` (issue #1688 Step 1). WP02 (executor auto-commit + doctor ops) depends on this WP.

**Implement with**: `spec-kitty agent action implement WP01 --agent claude`

---

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- Execution worktrees are allocated per lane from `lanes.json`. Do not manually create worktrees.

---

## Context

The invocation module (`src/specify_cli/invocation/`) tracks Op records for `ask`, `advise`, and `do` commands. Records are currently written to `.kittify/events/profile-invocations/`, which is gitignored — records are lost on `git clean`.

This WP redirects the write target to `kitty-ops/` (a new git-tracked directory, not currently in `.gitignore`) by changing 5 constants. No logic changes to write paths other than the `_append_to_index` inline computation fix (see T002).

**Key invariant**: `.gitignore` must NOT be modified. `kitty-ops/` is tracked by its absence from ignore rules.

---

## Subtask T001: Change `EVENTS_DIR` in `writer.py`

**File**: `src/specify_cli/invocation/writer.py`  
**Location**: Line 16

**Current**:
```python
EVENTS_DIR = ".kittify/events/profile-invocations"
```

**Change to**:
```python
EVENTS_DIR = "kitty-ops"
```

**Impact**: `InvocationWriter.__init__` sets `self._dir = repo_root / EVENTS_DIR`. After this change, all JSONL files are written to `repo_root/kitty-ops/<op_id>.jsonl`.

**Validation**: The constant is referenced in `__init__` only. No other code reads it directly. Check with `grep -n "EVENTS_DIR" src/specify_cli/invocation/writer.py` before and after.

---

## Subtask T002: Change `INDEX_PATH` and fix `_append_to_index` in `writer.py`

**File**: `src/specify_cli/invocation/writer.py`  
**Locations**: Line 17 (constant) + Line 81 (inline computation)

⚠️ **Critical**: The `INDEX_PATH` constant and the inline path in `_append_to_index` are independent. You MUST fix both.

### 2a. Constant (line 17)

**Current**:
```python
INDEX_PATH = ".kittify/events/invocation-index.jsonl"
```

**Change to**:
```python
INDEX_PATH = "kitty-ops/ops-index.jsonl"
```

### 2b. `_append_to_index` inline computation (line 81)

**Current**:
```python
index_path = self._dir.parent / "invocation-index.jsonl"
```

**Change to**:
```python
index_path = self._dir / "ops-index.jsonl"
```

**Why**: After T001, `self._dir = repo_root / "kitty-ops"`. The old code computed `self._dir.parent = repo_root`, placing the index at the root. The fix puts it at `kitty-ops/ops-index.jsonl`.

**Validation**: After T001+T002, `write_started()` should create files at:
- `kitty-ops/<op_id>.jsonl` (JSONL record)
- `kitty-ops/ops-index.jsonl` (performance index)

---

## Subtask T003: Change `LIFECYCLE_LOG_RELATIVE_PATH` in `lifecycle.py`

**File**: `src/specify_cli/invocation/lifecycle.py`  
**Location**: Line 44

**Current**:
```python
LIFECYCLE_LOG_RELATIVE_PATH = Path(".kittify") / "events" / "profile-invocation-lifecycle.jsonl"
```

**Change to**:
```python
LIFECYCLE_LOG_RELATIVE_PATH = Path("kitty-ops") / "lifecycle.jsonl"
```

**Impact**: `lifecycle_log_path(repo_root)` returns `repo_root / LIFECYCLE_LOG_RELATIVE_PATH`, so the log moves to `kitty-ops/lifecycle.jsonl`. No structural changes to `ProfileInvocationRecord` or any lifecycle logic.

**Validation**: `grep -n "LIFECYCLE_LOG_RELATIVE_PATH" src/specify_cli/invocation/lifecycle.py` — appears only in the constant definition and `lifecycle_log_path()`. Both will resolve correctly after the change.

---

## Subtask T004: Change `PROPAGATION_ERRORS_PATH` in `propagator.py`

**File**: `src/specify_cli/invocation/propagator.py`  
**Location**: Line 53

**Current**:
```python
PROPAGATION_ERRORS_PATH = ".kittify/events/propagation-errors.jsonl"
```

**Change to**:
```python
PROPAGATION_ERRORS_PATH = "kitty-ops/propagation-errors.jsonl"
```

**Scope boundary**: Do NOT modify any propagator logic. The `InvocationSaaSPropagator` class and `ThreadPoolExecutor` wiring are unchanged (Step 2 scope). Only the constant changes.

---

## Subtask T005: Add `mission_id`/`wp_id` to `InvocationRecord`; update MVTP constant

**File**: `src/specify_cli/invocation/record.py`

### 5a. Add fields to `InvocationRecord`

`InvocationRecord` is a Pydantic v2 model with `model_config = {"frozen": True}`. Add two optional fields after the existing `mode_of_work` field:

**Current** (end of field list, around line 41):
```python
    mode_of_work: str | None = None
```

**Add after**:
```python
    # Timeline correlation: populated when Op runs inside a mission execution context.
    # None for standalone ask/advise/do invocations (excluded from serialisation via exclude_none=True).
    mission_id: str | None = None
    wp_id: str | None = None
```

**Serialisation note**: `write_started()` in `writer.py` calls `record.model_dump(exclude_none=True)`, so `mission_id=None` and `wp_id=None` produce no on-disk change for records where neither is set. This is backward compatible.

### 5b. Update `MINIMAL_VIABLE_TRAIL_POLICY.tier_1.storage_path`

In `record.py`, around line 87, find:

```python
        storage_path=".kittify/events/profile-invocations/{invocation_id}.jsonl",
```

Change to:

```python
        storage_path="kitty-ops/{invocation_id}.jsonl",
```

**Scope boundary**: Do NOT modify `TIER_3_ACTIONS`, `TierEligibility`, `EvidenceArtifact`, `ProfileInvocationRecord`, or any other model in `record.py`.

---

## Subtask T006: Add path-change tests to `test_writer.py`

**File**: `tests/specify_cli/invocation/test_writer.py`

Add two new test functions (or a new test class `TestKittyOpsStorage`) covering:

### Test T-001: EVENTS_DIR resolves to `kitty-ops`

```python
def test_events_dir_is_kitty_ops() -> None:
    from specify_cli.invocation.writer import EVENTS_DIR
    assert EVENTS_DIR == "kitty-ops"
```

### Test: LIFECYCLE_LOG_RELATIVE_PATH resolves to `kitty-ops/lifecycle.jsonl`

```python
def test_lifecycle_log_relative_path_is_kitty_ops() -> None:
    from specify_cli.invocation.lifecycle import LIFECYCLE_LOG_RELATIVE_PATH
    from pathlib import Path
    assert LIFECYCLE_LOG_RELATIVE_PATH == Path("kitty-ops") / "lifecycle.jsonl"
```

### Test: PROPAGATION_ERRORS_PATH resolves to `kitty-ops/propagation-errors.jsonl`

```python
def test_propagation_errors_path_is_kitty_ops() -> None:
    from specify_cli.invocation.propagator import PROPAGATION_ERRORS_PATH
    assert PROPAGATION_ERRORS_PATH == "kitty-ops/propagation-errors.jsonl"
```

These two tests may live in `test_writer.py` or in their respective existing test files (`test_lifecycle_pairing.py`, any propagator test file). Place them wherever the existing constant-import pattern already exists.

### Test T-002: Index written at `kitty-ops/ops-index.jsonl`

Use `tmp_path` fixture. Create an `InvocationWriter`, call `write_started()` with a minimal `InvocationRecord`, then assert:
- The JSONL file exists at `tmp_path / "kitty-ops" / f"{invocation_id}.jsonl"`
- The index file exists at `tmp_path / "kitty-ops" / "ops-index.jsonl"`
- The index file does NOT exist at `tmp_path / "invocation-index.jsonl"` (regression guard)

Example structure:
```python
def test_index_written_at_kitty_ops_ops_index(tmp_path: Path) -> None:
    import ulid
    from specify_cli.invocation.writer import InvocationWriter
    from specify_cli.invocation.record import InvocationRecord

    writer = InvocationWriter(tmp_path)
    inv_id = str(ulid.new())
    record = InvocationRecord(
        event="started",
        invocation_id=inv_id,
        profile_id="test-profile",
        action="test",
        started_at="2026-06-05T00:00:00+00:00",
    )
    writer.write_started(record)

    assert (tmp_path / "kitty-ops" / f"{inv_id}.jsonl").exists()
    assert (tmp_path / "kitty-ops" / "ops-index.jsonl").exists()
    assert not (tmp_path / "invocation-index.jsonl").exists(), "index must not be at root"
```

---

## Subtask T007: Add field tests to `test_record.py`

**File**: `tests/specify_cli/invocation/test_record.py`

Add two test functions:

### Test: New fields present with defaults

```python
def test_invocation_record_has_mission_id_and_wp_id() -> None:
    from specify_cli.invocation.record import InvocationRecord
    record = InvocationRecord(
        event="started",
        invocation_id="01KTB49KJKRJ71YR8KERVDMHHA",
        profile_id="p",
        action="a",
    )
    assert record.mission_id is None
    assert record.wp_id is None
```

### Test: Fields excluded from serialisation when None

```python
def test_mission_id_wp_id_excluded_when_none() -> None:
    from specify_cli.invocation.record import InvocationRecord
    record = InvocationRecord(
        event="started",
        invocation_id="01KTB49KJKRJ71YR8KERVDMHHA",
        profile_id="p",
        action="a",
    )
    dumped = record.model_dump(exclude_none=True)
    assert "mission_id" not in dumped
    assert "wp_id" not in dumped
```

### Test: Fields included when set

```python
def test_mission_id_wp_id_included_when_set() -> None:
    from specify_cli.invocation.record import InvocationRecord
    record = InvocationRecord(
        event="started",
        invocation_id="01KTB49KJKRJ71YR8KERVDMHHA",
        profile_id="p",
        action="a",
        mission_id="01ABCDEFGHIJKLMNOPQRSTUVWX",
        wp_id="WP01",
    )
    dumped = record.model_dump(exclude_none=True)
    assert dumped["mission_id"] == "01ABCDEFGHIJKLMNOPQRSTUVWX"
    assert dumped["wp_id"] == "WP01"
```

---

## Definition of Done

- [ ] `EVENTS_DIR == "kitty-ops"` (writer.py line 16)
- [ ] `INDEX_PATH == "kitty-ops/ops-index.jsonl"` (writer.py line 17)
- [ ] `_append_to_index` computes `self._dir / "ops-index.jsonl"` (writer.py line 81)
- [ ] `LIFECYCLE_LOG_RELATIVE_PATH == Path("kitty-ops") / "lifecycle.jsonl"` (lifecycle.py line 44)
- [ ] `PROPAGATION_ERRORS_PATH == "kitty-ops/propagation-errors.jsonl"` (propagator.py line 53)
- [ ] `InvocationRecord` has `mission_id: str | None = None` and `wp_id: str | None = None`
- [ ] `MINIMAL_VIABLE_TRAIL_POLICY.tier_1.storage_path == "kitty-ops/{invocation_id}.jsonl"`
- [ ] `pytest tests/specify_cli/invocation/test_writer.py` passes (including T-001, T-002)
- [ ] `pytest tests/specify_cli/invocation/test_record.py` passes (including new field tests)
- [ ] `LIFECYCLE_LOG_RELATIVE_PATH == Path("kitty-ops") / "lifecycle.jsonl"` asserted in a test
- [ ] `PROPAGATION_ERRORS_PATH == "kitty-ops/propagation-errors.jsonl"` asserted in a test
- [ ] `mypy --strict src/specify_cli/invocation/` passes
- [ ] No `.gitignore` changes made

---

## Risks

| Risk | Mitigation |
|------|-----------|
| `_append_to_index` uses inline path (not `INDEX_PATH` constant) | Fix both the constant and the inline computation (T002) |
| `InvocationRecord` is frozen — adding fields without defaults breaks construction | Both new fields have `= None` defaults |
| Existing tests may check for the old `.kittify/events/` path | Run `pytest tests/specify_cli/invocation/test_writer.py` and `test_record.py` before and after — fix any assertions that expected the old path |

---

## Reviewer Guidance

- Verify exactly 3 edits in `writer.py` (lines 16, 17, 81)
- Verify exactly 1 edit in `lifecycle.py` (line 44)
- Verify exactly 1 edit in `propagator.py` (line 53)
- Verify exactly 2 new fields + 1 constant update in `record.py`
- Confirm no propagator logic was changed (only the path constant)
- Confirm no `.gitignore` was modified
- Check test_writer.py T-002 includes the regression guard (`not exists at root`)
