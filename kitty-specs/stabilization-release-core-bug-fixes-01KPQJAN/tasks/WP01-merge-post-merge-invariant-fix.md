---
work_package_id: WP01
title: Merge Post-Merge Invariant Fix
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: single-lane serial; WP01 executes first with no prerequisites
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- 2026-04-21T08:41:50Z – planned – stabilization WP01
authoritative_surface: src/specify_cli/cli/commands/merge.py
execution_mode: code_change
mission_id: 01KPQJAN4P2V4MTHRFGS7VW17M
mission_slug: stabilization-release-core-bug-fixes-01KPQJAN
owned_files:
- src/specify_cli/cli/commands/merge.py
- tests/merge/test_merge_post_merge_invariant*.py
tags: []
---

# WP01 — Merge Post-Merge Invariant Fix

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Workspace**: Lane-allocated by `finalize-tasks`. Enter it with `spec-kitty agent action implement WP01 --agent <name>`.
- Execution worktrees are `.worktrees/<slug>-<mid8>-lane-<id>/`. Do not branch manually.

## Objective

Fix `src/specify_cli/cli/commands/merge.py` so the post-merge working-tree invariant correctly classifies porcelain `??` lines (untracked files) as non-divergent. Update the error message to reflect the actual failure type. Ship regression tests for both the untracked-file and tracked-dirty cases.

**Fixes**: Issue #675  
**Requirements**: FR-001, FR-002, FR-003, FR-004, NFR-001–004

## Context

After a `spec-kitty merge` operation, the code runs `git status --porcelain` and collects any output line whose path is not in the small `expected_paths` set (`status.events.jsonl` and `status.json`). Any other line is treated as divergence and aborts the merge.

The bug: the code does not parse the two-character porcelain status code. A line like `?? .claude/` is included in `offending_lines` even though `??` means the file is untracked — it doesn't touch HEAD at all. The error message then tells the user to run `spec-kitty doctor sparse-checkout --fix`, which is irrelevant.

The relevant code block is in `src/specify_cli/cli/commands/merge.py` around lines 846–884, inside the `# -- WP05/T007 FR-014: Post-merge working-tree invariant --` comment block.

Porcelain v1 format: `XY path` where `X` is index status, `Y` is working-tree status. `??` is the only two-character code that means entirely untracked; everything else that passes the `len(line) < 4 or line[2] != " "` guard represents a tracked-file state (modified, added, deleted, renamed, conflict, etc.).

## Subtask T001 — Parse `??` prefix and skip untracked lines

**File**: `src/specify_cli/cli/commands/merge.py`

**Steps**:

1. Locate the loop that builds `offending_lines` (around line 868):
   ```python
   for line in (_out_status or "").splitlines():
       if not line.strip():
           continue
       if len(line) < 4 or line[2] != " ":
           continue
       path_part = line[3:].strip()
       if path_part in expected_paths:
           continue
       offending_lines.append(line)
   ```

2. After the `expected_paths` check, add an untracked-file guard:
   ```python
   status_code = line[:2]
   if status_code == "??":
       continue  # untracked files do not diverge from HEAD
   offending_lines.append(line)
   ```

3. The `??` check must be the only status code silently skipped. Do not expand this to other codes.

**Validation**:
- [ ] A mocked porcelain output of `?? .claude/` → `offending_lines` is empty → no abort
- [ ] A mocked porcelain output of ` M src/foo.py` → `offending_lines` has the entry → abort fires
- [ ] `A  src/bar.py` (staged new file) → `offending_lines` has the entry → abort fires

---

## Subtask T002 — Bifurcate error message by failure type

**File**: `src/specify_cli/cli/commands/merge.py`

**Context**: The current message always says `spec-kitty doctor sparse-checkout --fix`. Sparse-checkout failures manifest as tracked-file modifications/deletions, not untracked entries. Since we've already filtered out `??` in T001, all remaining `offending_lines` are tracked-file states. But the sparse-checkout guidance is only appropriate for certain tracked-file failure modes (missing/deleted files). For all other unexpected tracked states, a general `git status` message is more accurate.

**Steps**:

1. After collecting `offending_lines`, classify them:
   ```python
   # Classify offending lines to pick the right message
   has_tracked_changes = any(
       line[:2].strip() and line[:2] != "??"
       for line in offending_lines
   )
   ```
   (All remaining offending lines passed the `??` filter, so they're all tracked changes at this point. The classification just gates whether to recommend sparse-checkout or not.)

2. Replace the current unconditional message block:
   ```python
   if offending_lines:
       console.print(
           "[red]Error:[/red] Post-merge working-tree invariant violated. "
           "The following paths diverge from HEAD unexpectedly:"
       )
       for line in offending_lines:
           console.print(f"  {line}")
       # Choose guidance based on failure type
       deleted_or_modified = any(
           line[1] in ("D", "M") or line[0] in ("D", "M")
           for line in offending_lines
           if len(line) >= 2
       )
       if deleted_or_modified:
           console.print(
               "\nThis may indicate a sparse-checkout or filter-driver issue. Run\n"
               "  spec-kitty doctor sparse-checkout --fix\n"
               "before retrying the merge."
           )
       else:
           console.print(
               "\nUnexpected working-tree state after merge. "
               "Run `git status` to investigate before retrying."
           )
       raise typer.Exit(1)
   ```

**Validation**:
- [ ] Mocked `D  src/foo.py` (deletion) → message contains `sparse-checkout`
- [ ] Mocked `M  src/foo.py` (modification) → message contains `sparse-checkout`
- [ ] Mocked `UU src/conflict.py` (conflict) → message contains `git status` investigation guidance, not `sparse-checkout`

---

## Subtask T003 — Regression test: untracked files do not abort merge

**File**: `tests/merge/test_merge_post_merge_invariant.py` (create if not present)

**Pattern**: Use the existing test infrastructure in `tests/merge/`. Look at how `run_command` is mocked in nearby test files. Typically these tests mock `run_command` to return preset stdout.

**Test to add**:

```python
def test_post_merge_invariant_ignores_untracked_files(monkeypatch, ...):
    """?? lines for tooling directories must not trigger the invariant."""
    # Simulate git status --porcelain returning only untracked entries
    porcelain_output = "\n".join([
        "?? .claude/",
        "?? .agents/",
        "?? .kittify/merge-state.json",
    ])
    # ... patch run_command to return porcelain_output for the git status call
    # ... run the invariant logic (or extract it to a testable function)
    # Assert: no typer.Exit raised, offending_lines is empty
```

If the invariant logic is embedded in the CLI command, consider extracting the filtering logic to a small helper function `_classify_porcelain_lines(lines, expected_paths)` that returns `(offending, untracked_only_skipped)` — this makes it directly unit-testable without mocking the full CLI.

**Validation**:
- [ ] Test asserts no abort when only `??` lines are present outside expected_paths
- [ ] Test covers multiple agent directory patterns (`.claude/`, `.agents/`, `.worktrees/`)

---

## Subtask T004 — Regression test: tracked-dirty files abort with correct message

**File**: `tests/merge/test_merge_post_merge_invariant.py`

**Tests to add**:

```python
def test_post_merge_invariant_aborts_on_modified_tracked_file(...):
    """M lines for tracked files must still trigger the invariant."""
    porcelain_output = " M src/specify_cli/some_module.py"
    # Assert: typer.Exit(1) raised, error message present

def test_post_merge_invariant_message_mentions_sparse_checkout_for_deletions(...):
    """Deleted tracked files → sparse-checkout guidance."""
    porcelain_output = " D src/specify_cli/some_module.py"
    # Assert: error message contains 'sparse-checkout'

def test_post_merge_invariant_mixed_untracked_and_tracked_uses_tracked_message(...):
    """Mix of ?? and M → tracked-file message, not silenced by the ?? entries."""
    porcelain_output = "?? .claude/\n M src/specify_cli/some_module.py"
    # Assert: typer.Exit(1) raised (the M entry causes abort)
    # Assert: error message reflects the tracked-file issue
```

**Validation**:
- [ ] Three tests written and passing
- [ ] Each test's assertion matches the expected abort/message behavior

---

## Subtask T005 — Full suite green check

After completing T001–T004, run the full test suite:

```bash
cd /path/to/worktree
pytest -q tests/
```

Confirm:
- [ ] 0 new failures
- [ ] 0 new mypy --strict errors: `mypy --strict src/specify_cli/cli/commands/merge.py`
- [ ] Specifically the already-passing reference tests pass:
  ```bash
  pytest -q tests/merge/test_merge_done_recording.py
  pytest -q tests/upgrade/migrations/test_m_3_1_1_event_log_merge_driver.py
  ```

---

## Definition of Done

- [ ] `src/specify_cli/cli/commands/merge.py` updated with `??` filtering and bifurcated error message
- [ ] `tests/merge/test_merge_post_merge_invariant.py` created with ≥3 regression tests
- [ ] All new tests pass
- [ ] No pre-existing merge tests fail
- [ ] `mypy --strict src/specify_cli/cli/commands/merge.py` exits 0
- [ ] FR-001, FR-002, FR-003, FR-004 all satisfied (verify each scenario from spec.md S-01, S-02)

## Risks

- **Over-filtering**: Skipping only `??` is intentionally narrow. Do not generalize to other status codes.
- **Helper extraction boundary**: If you extract `_classify_porcelain_lines()`, keep it private to `merge.py` — no new public API needed.
- **False-positive test mock**: Tests that mock `run_command` globally may return the porcelain string for calls other than `git status`. Scope the mock narrowly (match on the `["git", "status", "--porcelain"]` call signature).

## Reviewer Guidance

Verify:
1. The `??` filter is applied only in the invariant section, not elsewhere in `merge.py`.
2. The error message for `??`-only violations was not accidentally suppressed — `??`-only output means `offending_lines` is empty, which correctly skips the error block entirely.
3. The message for deletion/modification failures mentions `sparse-checkout`; the message for other unexpected states does not.
4. Regression tests cover the mixed case (untracked + tracked in same status output).
