---
work_package_id: WP02
title: Domain Cleanup, Call-Site Gate, and MergeState Field
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-007
- FR-008
- NFR-002
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
agent: claude
history:
- date: '2026-06-05'
  author: spec-kitty.tasks
  note: Initial WP generation
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/merge/
execution_mode: code_change
owned_files:
- src/specify_cli/merge/preflight.py
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/merge/state.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load implementer-ivan
```

---

## ⚠️ ATDD-First Verification (Charter C-011 — binding)

Before writing any implementation code in this WP, confirm that the ATDD failing tests from WP01 T000 exist on your lane branch (or on `planning_base_branch` after WP01 merges). Run:

```bash
pytest tests/merge/test_merge_preflight_atdd.py -v
```

The tests should be **RED** before your implementation and **GREEN** after T007 is complete. If the test file does not exist, stop and escalate — WP01 must be re-run with T000 first.

---

## Objective

Complete the domain/publish layer separation by: (1) cleaning up `preflight.py` so it no longer references the types moved to `push_preflight.py`, (2) gating the push-safety check in `merge.py` so it fires only when `--push` was requested, and (3) adding `push_requested: bool` to `MergeState` for correct resume semantics.

This WP implements the user-visible fix for issue #1706: a user running `spec-kitty merge` without `--push` when local main is ahead of origin will no longer be blocked.

---

## Context

**WP01 must be merged before this WP starts.** This WP assumes:
- `src/specify_cli/merge/push_preflight.py` exists with `check_push_safety`, `TargetBranchSyncStatus`, `TargetBranchRefreshStatus`, and all fetch/inspect functions
- `preflight.py` still has the old definitions (WP01 may have left stubs or re-exports — confirm before T006)

**Key locations**:
- `src/specify_cli/merge/preflight.py`: the domain layer
- `src/specify_cli/cli/commands/merge.py`: line ~1508 has the unconditional preflight call; line ~1225 has `_enforce_target_branch_sync_preflight` definition; line ~1903 has `git push origin`
- `src/specify_cli/merge/state.py`: `MergeState` dataclass; `from_dict` is already backwards-compatible

---

## Subtask T006 — Strip Domain-Incompatible Code from `preflight.py`

**Purpose**: After WP01's migration, `preflight.py` may still have residual references to the moved types. This subtask makes `preflight.py` a clean domain-only module.

**Steps**:

1. Read `preflight.py` in its current state (post-WP01). Identify any remaining:
   - Imports of `subprocess` used only for `_git()` (should be gone)
   - References to `TargetBranchSyncStatus`, `TargetBranchRefreshStatus`, `TargetBranchSyncState` (should be imported from `push_preflight` if used by `run_preflight`, or removed entirely if not)
   - Any lingering `refresh_target_branch_tracking_ref` or `inspect_target_branch_sync` calls

2. If `run_preflight()` uses any types from `push_preflight`:
   - Add a targeted import: `from specify_cli.merge.push_preflight import TargetBranchSyncStatus`
   - Only import what is actually used

3. If `run_preflight()` does NOT use any push-layer types (preferred post-WP01 state):
   - Remove all such imports

4. Ensure the module-level `__all__` (if present) only exports domain types.

5. Run `ruff check src/specify_cli/merge/preflight.py` and fix any unused-import warnings.

**Expected final state of `preflight.py`**: Contains only `run_preflight`, `PreflightResult`, `WPStatus`, and whatever local git helpers they use. No `git fetch`. No `TargetBranchSyncStatus` definition.

**Validation**: `python -c "from specify_cli.merge.preflight import run_preflight; print('OK')"` succeeds. `mypy src/specify_cli/merge/preflight.py --strict` passes.

---

## Subtask T007 — Gate the Push-Safety Check in `merge.py`

**Purpose**: Make `spec-kitty merge` without `--push` perform no origin sync check. Make `spec-kitty merge --push` check push safety only after local lane merges complete.

**File**: `src/specify_cli/cli/commands/merge.py`

**Step 1 — Update `_enforce_target_branch_sync_preflight`**:

Find `_enforce_target_branch_sync_preflight` at line ~1225. This function currently:
1. Calls `refresh_target_branch_tracking_ref` (git fetch)
2. Calls `inspect_target_branch_sync`
3. Checks `status.is_safe` and exits with error if not

Replace its internals to use `check_push_safety`:

```python
def _enforce_target_branch_sync_preflight(
    repo_root: Path,
    target_branch: str,
    mission_slug: str,
    mission_branch: str,
    remote_name: str = "origin",
) -> None:
    """Block the push step if origin sync is unsafe.

    Only called when --push was requested. Fires after local merges complete,
    immediately before git push.
    """
    from specify_cli.merge.push_preflight import check_push_safety

    result = check_push_safety(repo_root, target_branch, remote_name=remote_name)

    if result.fetch_failed:
        # Existing fetch-failed payload builder — keep as-is
        payload = _target_branch_refresh_failed_payload(...)
        _emit_diagnostic(payload)
        raise typer.Exit(1)

    if not result.is_safe_to_push:
        # Existing diverged-guidance payload builder — keep as-is
        payload = _target_branch_sync_payload(result.sync_status, ...)
        _emit_diagnostic(payload)
        raise typer.Exit(1)
```

Read the existing function carefully. Preserve all existing payload-building and diagnostic-emission logic. Only change: (a) the fetch+inspect calls become `check_push_safety`, (b) `status.is_safe` → `result.is_safe_to_push`.

**Step 2 — Gate the call site**:

Find the unconditional call at line ~1508:
```python
_enforce_target_branch_sync_preflight(
    main_repo,
    target_branch=lanes_manifest.target_branch,
    ...
)
```

Replace with:
```python
if push:
    _enforce_target_branch_sync_preflight(
        main_repo,
        target_branch=lanes_manifest.target_branch,
        ...
    )
```

Where `push` is the boolean flag from the CLI invocation. Confirm the variable name by reading the surrounding function signature.

**Step 3 — Move the call**:

Currently the call fires before lock acquisition (before lane merges). After the `if push:` guard, the push-safety check should still fire BEFORE the push step (not before lock acquisition). Check whether the call can stay where it is or should move closer to the push at line ~1903. Moving it closer to the push is architecturally cleaner but is optional for this WP — the `if push:` guard alone satisfies FR-001 and FR-002.

**Validation**:
- Run `mypy src/specify_cli/cli/commands/merge.py --strict` — 0 new errors
- The check fires when `push=True` and not when `push=False` (verify by reading the logic, not by running a full integration test — that's WP03's job)

---

## Subtask T008 — Add `push_requested` to `MergeState`

**Purpose**: Persist push intent so resumed merges perform or skip the push step without user re-input.

**File**: `src/specify_cli/merge/state.py`

**Step 1 — Add field**:

In the `MergeState` dataclass, add after `mission_number_baked`:
```python
push_requested: bool = False  # True if original invocation requested --push
```

The `from_dict` method already filters to known fields — no changes needed there. Backwards compatibility is automatic.

**Step 2 — Find all MergeState construction sites**:

```bash
grep -rn "MergeState(" src/specify_cli/
```

For each construction site, determine whether the invocation knows the `push` flag at that point. If the construction site is in the merge command's CLI handler where `push: bool` is a parameter, add `push_requested=push` to the constructor call.

Expected sites: likely 1-2 in `src/specify_cli/cli/commands/merge.py` and possibly `src/specify_cli/merge/executor.py`.

**Step 3 — Thread `push_requested` into resume logic**:

Find where `MergeState` is loaded for a resume operation. When `spec-kitty merge` is invoked with `--resume` (or equivalent), the code loads the state file and continues. The push step in `_run_lane_based_merge_locked` (or equivalent) should check `state.push_requested` when deciding whether to run `_enforce_target_branch_sync_preflight`.

Specifically: in the push section of the merge executor (near line ~1903 in `merge.py`), the current gate is `if push and has_remote(main_repo)`. Update this to also consult `state.push_requested` on resume paths:

```python
effective_push = push or (state is not None and state.push_requested)
if effective_push and has_remote(main_repo):
    _enforce_target_branch_sync_preflight(...)
    # ... push step
```

Read the actual resume code flow carefully before making this change — the exact pattern may differ.

**Validation**:
```python
# Confirm backwards compat
old_state = {"mission_id": "test", "mission_slug": "test", "target_branch": "main",
             "wp_order": ["WP01"], "started_at": "2026-01-01T00:00:00+00:00",
             "updated_at": "2026-01-01T00:00:00+00:00"}
from specify_cli.merge.state import MergeState
s = MergeState.from_dict(old_state)
assert s.push_requested == False
```

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`
**Execution**: Worktree allocated by `finalize-tasks`. Depends on WP01 lane being merged first.

To start: `spec-kitty agent action implement WP02 --agent claude --mission merge-preflight-remote-state-boundary-separation-01KTBE5M`

---

## Definition of Done

- [ ] `preflight.py` has no `git fetch` calls, no `TargetBranchSyncStatus` definition
- [ ] `_enforce_target_branch_sync_preflight` in `merge.py` uses `check_push_safety` from `push_preflight`
- [ ] The call to `_enforce_target_branch_sync_preflight` at line ~1508 is wrapped in `if push:`
- [ ] `MergeState` has `push_requested: bool = False` field
- [ ] Old state files load with `push_requested=False` default (backwards compat verified)
- [ ] `mypy src/specify_cli/merge/ src/specify_cli/cli/commands/merge.py --strict` passes

## Risks

- **Push flag variable name**: The variable may be named `do_push` or similar in the CLI handler. Read the handler signature before T007 step 2.
- **Resume path complexity**: The resume logic may be spread across multiple functions. Trace the full resume flow before T008 step 3 to avoid missing a code path.
- **Behaviour regression for `--push` path**: The existing diverged-state guidance must be preserved exactly. Do not simplify the payload-building logic; only replace the fetch/inspect calls with `check_push_safety`.
