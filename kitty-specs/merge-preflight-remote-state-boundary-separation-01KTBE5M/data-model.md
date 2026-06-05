# Data Model: Merge Preflight Remote-State Boundary Separation

## Overview

This mission modifies three existing value objects and introduces one new module. No new persistent data stores are introduced. All changes are to in-memory Python types and one JSON-serialized state file schema.

---

## Value Objects

### TargetBranchSyncStatus (modified)

**Current location**: `src/specify_cli/merge/preflight.py`
**New location**: `src/specify_cli/merge/push_preflight.py`

Represents the relationship between a local branch and its remote tracking branch.

```
TargetBranchSyncStatus
  target_branch: str          # Local branch name (e.g., "main")
  tracking_branch: str | None # Remote tracking ref (e.g., "origin/main"), None if no tracking branch
  ahead_count: int            # Commits local has that origin lacks
  behind_count: int           # Commits origin has that local lacks
  state: TargetBranchSyncState  # "in_sync" | "ahead" | "behind" | "diverged" | "no_tracking_branch" | "missing_local_branch"

  is_safe_to_push: bool       # NEW: True for in_sync, ahead, behind, no_tracking_branch; False for diverged only
  is_safe: bool               # DEPRECATED ALIAS: was "safe for local merge" (a misnomer) — now always True; kept for any callers that may exist outside this WP's scope
```

**Push-safety invariant**:
- `"in_sync"` → safe to push (no-op or fast-forward)
- `"ahead"` → safe to push (fast-forward)
- `"behind"` → push will be rejected by git; preflight does NOT block and does NOT warn (git's own rejection message is sufficient feedback; a warning is out of scope per spec Assumption 2)
- `"diverged"` → push requires force; preflight blocks
- `"no_tracking_branch"` → no remote to push to; no-op safe

**Transition from `is_safe` to `is_safe_to_push`**: The call in `merge.py` switches to `is_safe_to_push`. `is_safe` is deprecated but retained to avoid breaking any external callers (returns `True` always).

---

### TargetBranchPushSafetyResult (new)

**Location**: `src/specify_cli/merge/push_preflight.py`

The result object returned by `check_push_safety()`. Combines the fetch result with the sync status and a top-level verdict.

```
TargetBranchPushSafetyResult
  refresh_status: TargetBranchRefreshStatus  # Outcome of the git fetch attempt
  sync_status: TargetBranchSyncStatus | None # None if fetch failed and status unavailable
  is_safe_to_push: bool                      # Top-level verdict: can we push without force?
  fetch_failed: bool                          # True if the git fetch itself failed
  error: str | None                           # Human-readable error if fetch_failed
```

**Invariants**:
- `fetch_failed=True` → `sync_status=None` and `is_safe_to_push=False`
- `fetch_failed=False` and `sync_status.state == "diverged"` → `is_safe_to_push=False`
- All other non-fetch-failed states → `is_safe_to_push=True`

---

### MergeState (modified)

**Location**: `src/specify_cli/merge/state.py`
**JSON schema file**: `.kittify/runtime/merge/<mission_id>/state.json`

Adds `push_requested` field for correct resume semantics.

```
MergeState
  mission_id: str
  mission_slug: str
  target_branch: str
  wp_order: list[str]
  completed_wps: list[str]  # default []
  current_wp: str | None    # default None
  has_pending_conflicts: bool  # default False
  strategy: str             # "merge" | "squash" | "rebase"
  workspace_path: str | None
  started_at: str           # ISO 8601
  updated_at: str           # ISO 8601
  mission_number_baked: bool  # default False
  push_requested: bool      # NEW — default False; True if original invocation requested --push
```

**Backwards compatibility**:
- `from_dict` already filters to known fields. Old state files without `push_requested` load cleanly; the dataclass default (`False`) applies.
- No migration needed. No version field required.

**JSON schema addition**:
```json
{
  "push_requested": false
}
```

---

## New Module: push_preflight.py

**Location**: `src/specify_cli/merge/push_preflight.py`

Owns all remote-state inspection for the publish layer. The local-merge domain layer must not import from this module.

**Public interface**:

```
check_push_safety(
  repo_root: Path,
  target_branch: str,
  remote_name: str = "origin"
) -> TargetBranchPushSafetyResult
```

**Moves from preflight.py**:
- `TargetBranchSyncState` (type alias)
- `TargetBranchSyncStatus` (value object)
- `TargetBranchRefreshStatus` (value object)
- `refresh_target_branch_tracking_ref()` (performs git fetch)
- `inspect_target_branch_sync()` (reads git rev-list divergence counts)
- `_resolve_tracking_branch()` (helper)
- `_branch_commit_exists()` (helper)

**Stays in preflight.py**:
- `run_preflight()` — WP-level local-graph checks (worktrees clean, no git merge in progress)
- `PreflightResult`, `WPStatus` — WP-level result types

---

## Module Dependency Graph (after this mission)

```
merge.py (CLI command)
  ├── preflight.py          (local-graph domain checks only)
  │     └── [local git operations only — no network]
  └── push_preflight.py     (publish-layer checks, imported only when push=True)
        └── [git fetch + sync inspection]
```

**Invariant enforced by this design**: `merge.py` imports `push_preflight` only inside the `if push:` branch. `preflight.py` does not import `push_preflight`.

---

## State Transition: Merge with Push

```
invoke spec-kitty merge --push
  → set MergeState.push_requested = True
  → persist MergeState
  → run local lane merges (no network I/O)
  → if push:
      check_push_safety(repo_root, target_branch) → TargetBranchPushSafetyResult
      if not result.is_safe_to_push:
          emit blocked guidance (diverged — rebase or use focused-PR-branch)
          exit 1
      git push origin <target_branch>

invoke spec-kitty merge (resume, no --push flag)
  → load MergeState → push_requested = True (persisted from original invocation)
  → resume lane merges
  → push step executes (because push_requested=True)
```

---

## Architectural Decision Record (to be authored in WP01)

**ADR location**: `architecture/3.x/adr/2026-06-05-1-merge-publish-layer-boundary.md`

**Decision**: Remote-state inspection is a publish-layer concern. The local-merge domain layer must not perform network I/O or reference remote tracking branch state.

**Consequences**:
- `push_preflight.py` owns all network I/O in the merge subsystem
- `preflight.py` is domain-only: local git graph checks, no fetch
- `merge.py` imports `push_preflight` conditionally (only when push was requested)
- This boundary is enforced architecturally — not by convention — because `preflight.py` simply does not export the fetch functions after the migration

**Rejected alternatives documented in ADR**:
1. Add `"ahead"` to `is_safe` whitelist (bandaid — leaves the wrong layer intact)
2. Add `if push:` guard without relocating the module (corrects call site but not boundary)
