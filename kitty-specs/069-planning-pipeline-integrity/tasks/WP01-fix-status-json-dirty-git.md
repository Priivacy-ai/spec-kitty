---
work_package_id: WP01
title: Fix status.json dirty-git
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-069-planning-pipeline-integrity
base_commit: 1423753b3ab63d421652c24fee008f2863be2e1c
created_at: '2026-04-07T11:47:53.821730+00:00'
subtasks: [T001, T002, T003, T004, T005, T006]
shell_pid: "10279"
agent: "claude:sonnet:reviewer:reviewer"
history:
- date: '2026-04-07'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
owned_files:
- src/specify_cli/status/reducer.py
- src/specify_cli/status/views.py
- tests/status/test_reducer.py
---

# WP01: Fix status.json dirty-git

## Objective

Make `materialize()` and all read paths idempotent: reading status never writes to disk unless the event log has actually changed. Fixes #524.

**Success criterion**: After running `spec-kitty agent tasks status` (or any read-only status command) against a clean git repository, `git status --porcelain` is empty.

## Context

`src/specify_cli/status/reducer.py` has two problems:

1. `reduce()` sets `materialized_at=_now_utc()` — wall-clock time makes every call produce unique JSON bytes, even when events are identical.
2. `materialize()` always writes `status.json` without comparing to existing content.

`src/specify_cli/status/views.py:materialize_if_stale()` has a third problem:

3. The function returns `materialize(feature_dir)` on line ~154, which always writes — even when the stale check passed and nothing changed.

**Both T002 and T003 are required together.** `write_derived_views()` (called when stale) also calls `materialize()` internally (views.py line ~65). T002's skip-write guard covers that call. T003's return-line fix covers the final unconditional call.

## Branch Strategy

- **Implementation branch**: allocated by `finalize-tasks` (worktree for this lane)
- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Command**: `spec-kitty implement WP01`

---

## Subtask T001: Make `reduce()` deterministic

**Purpose**: Derive `materialized_at` from the last event's `at` timestamp instead of the wall clock. Same event sequence → identical JSON bytes → skip-write guard works.

**File**: `src/specify_cli/status/reducer.py`

**Changes**:

1. Find the two `materialized_at=_now_utc()` calls in `reduce()`:
   - **Empty case** (~line 127, inside `if not events: return StatusSnapshot(...)`):
     ```python
     # Before:
     materialized_at=_now_utc(),
     # After:
     materialized_at="",  # No events → no last-event timestamp; stable empty string
     ```
   - **Normal case** (~line 157, final `return StatusSnapshot(...)`):
     ```python
     # Before:
     materialized_at=_now_utc(),
     # After:
     materialized_at=sorted_events[-1].at,  # Derived from last event; deterministic
     ```

2. The `_now_utc()` helper becomes unused after this change. Remove the call but keep the helper in case it's still used elsewhere — check with `grep -n "_now_utc" src/specify_cli/status/reducer.py`.

**Validation**:
- [ ] `reduce([event_a, event_b])` called twice returns identical `materialized_at` both times
- [ ] `reduce([])` returns `materialized_at == ""`
- [ ] `reduce([event])` where `event.at = "2026-02-08T12:00:00Z"` returns `materialized_at == "2026-02-08T12:00:00Z"`

---

## Subtask T002: Add skip-write guard to `materialize()`

**Purpose**: Skip the atomic write entirely when the computed JSON bytes are identical to the existing `status.json` content.

**File**: `src/specify_cli/status/reducer.py`

**Change** to `materialize()` (~line 184):

```python
def materialize(feature_dir: Path) -> StatusSnapshot:
    """Read events, reduce to snapshot, and write status.json atomically.

    Skips the write when content is byte-identical to the existing file.
    """
    events = read_events(feature_dir)
    snapshot = reduce(events)
    json_str = materialize_to_json(snapshot)

    out_path = feature_dir / SNAPSHOT_FILENAME
    tmp_path = feature_dir / (SNAPSHOT_FILENAME + ".tmp")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Skip write when content unchanged (FR-001, NFR-001)
    if out_path.exists() and out_path.read_text(encoding="utf-8") == json_str:
        return snapshot

    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(str(tmp_path), str(out_path))
    return snapshot
```

**Notes**:
- The comparison reads the existing file once. This is a small I/O cost but prevents false writes — acceptable given the file is always small (<10 KB).
- `out_path.read_text()` is safe here because `materialize_to_json()` always outputs UTF-8.

**Validation**:
- [ ] First call (no existing file): writes, returns snapshot
- [ ] Second call (same events): existing file matches computed JSON, no write
- [ ] After appending a new event: computed JSON differs, write occurs

---

## Subtask T003: Fix `materialize_if_stale()` return

**Purpose**: The final `return materialize(feature_dir)` in `materialize_if_stale()` always writes. Replace with a read-only return.

**File**: `src/specify_cli/status/views.py`

**Change** (~line 149–154):

```python
# Before:
    if _is_stale():
        write_derived_views(feature_dir, derived_dir)
        generate_progress_json(feature_dir, derived_dir)

    # Always return a fresh snapshot from the event log
    return materialize(feature_dir)   # ← always writes status.json

# After:
    if _is_stale():
        write_derived_views(feature_dir, derived_dir)
        generate_progress_json(feature_dir, derived_dir)

    # Return snapshot without writing (T002 covers any write needed by derived views)
    return reduce(read_events(feature_dir))
```

**Add import** at top of views.py if not already present:
```python
from .reducer import materialize, reduce
from .store import EVENTS_FILENAME, read_events
```
`reduce` and `read_events` are already imported — verify with `grep "^from .reducer\|^from .store" src/specify_cli/status/views.py`.

**Validation**:
- [ ] Calling `materialize_if_stale()` on a repo with no stale files: `git status --porcelain` empty
- [ ] Calling `materialize_if_stale()` when stale: derived views written, but `kitty-specs/<feature>/status.json` only written if event log changed

---

## Subtask T004: Unit tests — `reduce()` determinism

**Purpose**: Verify that T001's change produces stable `materialized_at`.

**File**: `tests/status/test_reducer.py` (add new test class)

**Tests to add**:

```python
class TestReduceDeterministicMaterializedAt:
    """Tests for deterministic materialized_at after T001 fix."""

    def test_same_events_produce_same_materialized_at(self) -> None:
        """Same input → same materialized_at (no wall-clock dependency)."""
        event = _make_event(at="2026-02-08T12:00:00Z")
        snapshot1 = reduce([event])
        snapshot2 = reduce([event])
        assert snapshot1.materialized_at == snapshot2.materialized_at

    def test_materialized_at_equals_last_event_at(self) -> None:
        """materialized_at is the timestamp of the last event."""
        e1 = _make_event(event_id="01A", at="2026-01-01T00:00:00Z")
        e2 = _make_event(event_id="01B", at="2026-02-01T00:00:00Z", wp_id="WP02",
                         from_lane=Lane.PLANNED, to_lane=Lane.CLAIMED)
        snapshot = reduce([e1, e2])
        assert snapshot.materialized_at == "2026-02-01T00:00:00Z"

    def test_empty_events_stable_materialized_at(self) -> None:
        """Empty event list → materialized_at is stable empty string."""
        s1 = reduce([])
        s2 = reduce([])
        assert s1.materialized_at == s2.materialized_at == ""
```

---

## Subtask T005: Unit tests — `materialize()` idempotency

**Purpose**: Verify T002's skip-write guard works.

**File**: `tests/status/test_reducer.py` (add to existing file)

**Tests to add** (require a `tmp_path` fixture for a real filesystem):

```python
class TestMaterializeIdempotency:
    """Tests for skip-write guard in materialize()."""

    def test_first_call_writes_file(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "069-test"
        feature_dir.mkdir(parents=True)
        # Write an event so events file exists
        from specify_cli.status.store import append_event
        from specify_cli.status.models import StatusEvent, Lane
        # (use append_event to create a real events file)
        ...
        materialize(feature_dir)
        assert (feature_dir / SNAPSHOT_FILENAME).exists()

    def test_second_call_with_same_events_does_not_write(self, tmp_path: Path) -> None:
        """Second call produces identical JSON — file mtime must not change."""
        feature_dir = tmp_path / "kitty-specs" / "069-test"
        feature_dir.mkdir(parents=True)
        # Populate events, materialize once
        ...
        materialize(feature_dir)
        mtime_before = (feature_dir / SNAPSHOT_FILENAME).stat().st_mtime
        import time; time.sleep(0.01)  # ensure mtime would differ if written
        materialize(feature_dir)
        mtime_after = (feature_dir / SNAPSHOT_FILENAME).stat().st_mtime
        assert mtime_before == mtime_after

    def test_new_event_triggers_write(self, tmp_path: Path) -> None:
        """New event → JSON changes → write occurs → mtime changes."""
        # ... add event, materialize, check mtime changed
        ...
```

Note: Use `append_event()` from `specify_cli.status.store` to populate events in the tmp directory.

---

## Subtask T006: Integration test — clean git tree after read-only commands

**Purpose**: End-to-end regression test verifying NFR-001.

**File**: `tests/status/test_reducer.py` or a new `tests/status/test_materialize_git_clean.py`

**Approach**: Use `pytest-tmp-path` + `subprocess.run("git init")` to create a real git repo, commit an initial state with a `status.events.jsonl`, then call `materialize()` or `reduce()` and assert `git status --porcelain` output is empty.

```python
import subprocess

def test_materialize_leaves_clean_git_tree(tmp_path: Path) -> None:
    """Calling materialize() does not dirty the git working tree."""
    # 1. Init git repo
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True, capture_output=True)

    # 2. Create feature dir with events file and initial status.json
    feature_dir = tmp_path / "kitty-specs" / "069-test"
    feature_dir.mkdir(parents=True)
    # ... write events and initial status.json, git add + commit ...

    # 3. Call materialize() (should skip write)
    materialize(feature_dir)

    # 4. Assert clean tree
    result = subprocess.run(
        ["git", "-C", str(tmp_path), "status", "--porcelain"],
        capture_output=True, text=True
    )
    assert result.stdout.strip() == "", f"Unexpected dirty files: {result.stdout}"
```

---

## Definition of Done

- [ ] `reduce()` uses `sorted_events[-1].at` as `materialized_at` (no `_now_utc()` calls in normal path)
- [ ] `materialize()` reads existing file and skips write when bytes match
- [ ] `materialize_if_stale()` returns `reduce(read_events(...))` on its final line
- [ ] All existing tests in `test_reducer.py` still pass
- [ ] T004, T005, T006 tests pass
- [ ] `git status --porcelain` empty after `spec-kitty agent tasks status` on a clean repo

## Reviewer Guidance

The three changes are small and independent within a single logical unit. Verify:
1. The `sorted_events[-1].at` expression is inside the `if not events` guard's else path (i.e., only reached when `sorted_events` is non-empty)
2. The read-before-write in `materialize()` uses UTF-8 decode to match `write_text(encoding="utf-8")`
3. The import of `reduce` and `read_events` in `views.py` doesn't cause circular imports (status/reducer already imports from status/store; views imports from reducer — no cycle)

## Activity Log

- 2026-04-07T11:51:05Z – unknown – shell_pid=9810 – T001-T006 complete: reduce() deterministic, materialize() skip-write guard, materialize_if_stale() fixed
- 2026-04-07T11:51:23Z – claude:sonnet:reviewer:reviewer – shell_pid=10279 – Started review via action command
