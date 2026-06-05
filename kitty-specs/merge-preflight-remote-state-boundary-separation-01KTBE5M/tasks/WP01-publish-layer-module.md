---
work_package_id: WP01
title: Publish-Layer Module and Boundary Types
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T000
- T001
- T002
- T003
- T004
- T005
agent: claude
history:
- date: '2026-06-05'
  author: spec-kitty.tasks
  note: Initial WP generation
- date: '2026-06-05'
  author: analyze
  note: Added T000 ATDD stub (charter C-011); restricted T003 to push_preflight.py only
agent_profile: architect-alphonso
authoritative_surface: src/specify_cli/merge/
execution_mode: code_change
owned_files:
- src/specify_cli/merge/push_preflight.py
- architecture/3.x/adr/2026-06-05-1-merge-publish-layer-boundary.md
- tests/merge/test_merge_preflight_atdd.py
role: architect
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load architect-alphonso
```

This sets your role, boundaries, and working style for this WP.

---

## ⚠️ ATDD-First (Charter C-011 — binding)

**Before writing any implementation code**, commit a failing ATDD stub as your first commit on the lane branch. This is a binding charter requirement.

### Subtask T000 — ATDD Failing Stubs

**File**: `tests/merge/test_merge_preflight_atdd.py` (new file — owned by this WP)

Write two minimal failing tests and commit them. These tests must be RED on `planning_base_branch` (before any implementation) and GREEN after WP02 completes.

```python
"""ATDD acceptance tests for merge-preflight-remote-state-boundary-separation.

These tests were committed RED before any implementation began (charter C-011).
They must turn GREEN when WP01 + WP02 complete. Do not delete this file — it
is the verifiable proof that the implementation was test-first.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_local_merge_proceeds_when_local_is_ahead_without_push():
    """ATDD: FR-002 — local merge ignores origin state when push not requested.

    Verifies that a merge invoked without --push does NOT call any remote-state
    fetch function, even when local is ahead of origin.
    """
    # This test should FAIL until WP02 gates the push-preflight call on push=True.
    # Once WP02 is implemented, the fetch function must not be called.
    with patch("specify_cli.merge.push_preflight.refresh_target_branch_tracking_ref") as mock_fetch:
        # Simulate a merge invocation with push=False
        # (exact call surface resolved by the implementer after WP01 exists)
        # For now, assert the module exists and the function is importable:
        from specify_cli.merge import push_preflight  # noqa: F401 — existence check
        # After WP02: assert mock_fetch.assert_not_called() holds after merge runs
        # Stub: just import for now. Full assertion added in WP03 T009.
        assert hasattr(push_preflight, "check_push_safety"), (
            "push_preflight.check_push_safety must exist after WP01"
        )


def test_issue_1706_local_ahead_behind_no_push_does_not_block():
    """ATDD: FR-010 — #1706 regression. Local ahead+behind of origin must not block no-push merge.

    Issue: https://github.com/Priivacy-ai/spec-kitty/issues/1706
    This test is RED until WP02 removes the unconditional origin-sync check.
    """
    # Minimal existence check — full regression test written in WP03 T011.
    # This stub ensures the behavioral contract is pinned before implementation.
    try:
        from specify_cli.merge.push_preflight import TargetBranchSyncStatus
        status = TargetBranchSyncStatus(
            target_branch="main",
            tracking_branch="origin/main",
            ahead_count=10,
            behind_count=5,
            state="diverged",
        )
        # After WP01: is_safe_to_push must exist and return False for diverged
        assert hasattr(status, "is_safe_to_push"), "is_safe_to_push predicate must exist"
        # After WP02: local merge must proceed even for diverged state when push=False
        # Full end-to-end assertion is in WP03 T011.
    except ImportError:
        pytest.fail(
            "push_preflight module does not exist yet — "
            "this test is intentionally RED before WP01 is implemented."
        )
```

**Commit this file first, before T001.** The commit message should reference C-011:
```
test: ATDD stubs for merge-preflight boundary separation (charter C-011)

RED on main. These turn green when WP01 + WP02 complete.
Pins FR-002 (local-ahead does not block) and FR-010 (#1706 regression).
```

---

## Objective

Create `src/specify_cli/merge/push_preflight.py` as the canonical publish-layer module for remote-state inspection. Move all remote-state infrastructure out of `preflight.py` into this new module. Author the ADR documenting the boundary decision. Add a `is_safe_to_push` predicate to `TargetBranchSyncStatus` and deprecate the misnamed `is_safe` alias.

After this WP, `preflight.py` is a domain-only module with zero network I/O.

---

## Context

`src/specify_cli/merge/preflight.py` currently contains two distinct responsibilities:
1. **WP-level local-graph checks** (`run_preflight()`, `PreflightResult`, `WPStatus`) — domain-only, no network, correct layer
2. **Remote-state inspection** (`refresh_target_branch_tracking_ref`, `inspect_target_branch_sync`, plus `TargetBranchSyncStatus`, `TargetBranchRefreshStatus`, `TargetBranchSyncState`) — performs `git fetch`, belongs in the publish layer

The `TargetBranchSyncStatus.is_safe` property returns `True` for `{"in_sync", "no_tracking_branch"}` only. `"ahead"` (local has commits origin lacks) is incorrectly classified as unsafe for local merge.

**Reference**: `src/specify_cli/merge/preflight.py` lines 1–185, `src/specify_cli/cli/commands/merge.py` lines 1225–1274 and 1508, `kitty-specs/merge-preflight-remote-state-boundary-separation-01KTBE5M/data-model.md`.

---

## Subtask T001 — Author ADR for Merge-Publish Layer Boundary

**Purpose**: Document the architectural decision that remote-state inspection is a publish-layer concern so future contributors cannot inadvertently re-introduce the boundary violation.

**File**: `architecture/3.x/adr/2026-06-05-1-merge-publish-layer-boundary.md`

Follow the ADR format used by the existing ADRs in `architecture/3.x/adr/`. Look at one existing ADR to confirm the format before writing.

The ADR must cover:
- **Status**: Accepted
- **Context**: `spec-kitty merge` is a local-integration command. It must not require network access. The former `_enforce_target_branch_sync_preflight` check fired before any local mutation and performed a live `git fetch origin`, blocking the local merge if origin was not in sync. This is architecturally inverted: the check enforces a push-safety invariant at the wrong layer and on the wrong operation.
- **Decision**: All remote-state inspection lives in `push_preflight.py` (publish layer). The local-merge domain layer (`preflight.py`) contains only local git graph checks. `merge.py` imports `push_preflight` conditionally (only inside `if push:` branches).
- **Consequences**: Domain layer is network-free. Push-safety checks only fire when a push is requested. `TargetBranchSyncStatus.is_safe_to_push` is the correct predicate for push decisions. The deprecated `is_safe` alias always returns `True` (was the local-merge safety predicate; local merge is always safe regardless of origin state).
- **Rejected alternatives**: (1) Add `"ahead"` to `is_safe` whitelist — bandaid, leaves network code in domain layer. (2) Add `if push:` guard without module relocation — corrects call site but not layer boundary.

---

## Subtask T002 — Create `push_preflight.py` Skeleton

**Purpose**: Establish the new module with its public types before moving functions into it.

**File**: `src/specify_cli/merge/push_preflight.py` (new file)

Create the module with:

```python
"""Push-layer preflight checks for target branch remote-state safety.

This module owns all network I/O against origin in the merge subsystem.
The local-merge domain layer (preflight.py) must NOT import from here.
"""

from __future__ import annotations
# ... imports

TargetBranchSyncState = Literal[
    "in_sync", "ahead", "behind", "diverged",
    "no_tracking_branch", "missing_local_branch",
]

@dataclass(frozen=True)
class TargetBranchSyncStatus:
    target_branch: str
    tracking_branch: str | None
    ahead_count: int
    behind_count: int
    state: TargetBranchSyncState

    @property
    def is_safe_to_push(self) -> bool:
        # "diverged" requires force push — block. All other states are safe or
        # handled by git's own push rejection.
        return self.state not in {"diverged"}

    @property
    def is_safe(self) -> bool:
        # Deprecated: was used as "safe for local merge" but that predicate
        # is always True. Retained as alias to avoid breaking callers.
        # Use is_safe_to_push for push decisions.
        return True

@dataclass(frozen=True)
class TargetBranchRefreshStatus:
    target_branch: str
    remote_name: str
    attempted: bool
    success: bool
    error: str | None = None

@dataclass(frozen=True)
class TargetBranchPushSafetyResult:
    refresh_status: TargetBranchRefreshStatus
    sync_status: TargetBranchSyncStatus | None
    is_safe_to_push: bool
    fetch_failed: bool
    error: str | None = None
```

Ensure all fields are fully type-annotated and the module passes `mypy --strict`.

**Validation**: `mypy src/specify_cli/merge/push_preflight.py --strict` exits 0.

---

## Subtask T003 — Move Fetch/Inspect Functions

**Purpose**: Relocate the remote-state functions from `preflight.py` to `push_preflight.py`.

**Source**: `src/specify_cli/merge/preflight.py`
**Destination**: `src/specify_cli/merge/push_preflight.py`

Functions to move (in order, preserving their signatures and logic exactly):
1. `_git(repo_root, args)` — internal subprocess helper
2. `_branch_commit_exists(repo_root, ref)` — checks if a git ref exists
3. `_resolve_tracking_branch(repo_root, target_branch)` — resolves upstream tracking ref
4. `refresh_target_branch_tracking_ref(repo_root, target_branch, remote_name)` — performs `git fetch`
5. `inspect_target_branch_sync(repo_root, target_branch)` — reads `git rev-list --left-right --count`

After adding to `push_preflight.py`:

> ⚠️ **Do NOT delete or modify `preflight.py` in this WP.**
>
> `preflight.py` is owned by **WP02** (T006). Leave the original function definitions
> in place. WP02 T006 handles stripping them from `preflight.py` after WP01 merges.
> If you delete from `preflight.py` in this WP, you will create a merge conflict
> with WP02's lane.

- Do NOT add a backward-compat re-export shim in `preflight.py` — WP02 decides what stays.

**Validation**: `from specify_cli.merge.push_preflight import refresh_target_branch_tracking_ref, inspect_target_branch_sync` succeeds. The original `from specify_cli.merge.preflight import run_preflight` also still succeeds (functions not yet removed from preflight.py — that's WP02's job).

---

## Subtask T004 — Implement `check_push_safety()`

**Purpose**: Add the top-level push-safety function that `merge.py` will call.

**File**: `src/specify_cli/merge/push_preflight.py`

```python
def check_push_safety(
    repo_root: Path,
    target_branch: str,
    remote_name: str = "origin",
) -> TargetBranchPushSafetyResult:
    """Check whether pushing target_branch to remote_name is safe.

    Performs a git fetch to refresh the tracking ref, then inspects the
    divergence between local and remote. Returns a result object with
    is_safe_to_push=False only when the state is "diverged" (force push
    would be required).

    Args:
        repo_root: Repository root path.
        target_branch: Local branch to check (e.g., "main").
        remote_name: Remote name (default "origin").

    Returns:
        TargetBranchPushSafetyResult with verdict and diagnostic details.
    """
    refresh = refresh_target_branch_tracking_ref(
        repo_root, target_branch, remote_name=remote_name
    )
    if not refresh.success:
        return TargetBranchPushSafetyResult(
            refresh_status=refresh,
            sync_status=None,
            is_safe_to_push=False,
            fetch_failed=True,
            error=refresh.error,
        )
    sync = inspect_target_branch_sync(repo_root, target_branch)
    return TargetBranchPushSafetyResult(
        refresh_status=refresh,
        sync_status=sync,
        is_safe_to_push=sync.is_safe_to_push,
        fetch_failed=False,
    )
```

**Validation**: Unit test calling `check_push_safety` with a mock that simulates fetch success + `"diverged"` sync returns `is_safe_to_push=False`. Mock simulating `"ahead"` returns `is_safe_to_push=True`.

---

## Subtask T005 — Update `TargetBranchSyncStatus.is_safe` in Old Callers

**Purpose**: Ensure any remaining callers of `.is_safe` in `merge.py` or elsewhere use the correct semantics going forward. The type is now in `push_preflight.py`; all callers must import from there.

**Search**: `grep -rn "is_safe" src/specify_cli/merge/ tests/merge/`

For each caller of `.is_safe`:
- If the caller is `_enforce_target_branch_sync_preflight` in `merge.py` — WP02 will replace this entire function call with `check_push_safety()`, so leave it alone for now.
- If there are other callers — update them to use `.is_safe_to_push` if they are making push-safety decisions, or remove the check if they are making local-merge decisions (which is always safe).

Update `__all__` in `push_preflight.py` to export: `TargetBranchSyncState`, `TargetBranchSyncStatus`, `TargetBranchRefreshStatus`, `TargetBranchPushSafetyResult`, `check_push_safety`, `refresh_target_branch_tracking_ref`, `inspect_target_branch_sync`.

**Validation**: `mypy src/specify_cli/merge/ --strict` exits 0 with zero new errors. `ruff check src/specify_cli/merge/` exits 0.

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`
**Execution**: Worktree allocated by `finalize-tasks` from `lanes.json`. Branch will be `kitty/mission-merge-preflight-remote-state-boundary-separation-01KTBE5M-lane-a` or equivalent. Do not create branches manually.

To start: `spec-kitty agent action implement WP01 --agent claude --mission merge-preflight-remote-state-boundary-separation-01KTBE5M`

---

## Definition of Done

- [ ] **T000**: `tests/merge/test_merge_preflight_atdd.py` committed RED as the first commit on this lane
- [ ] `architecture/3.x/adr/2026-06-05-1-merge-publish-layer-boundary.md` committed
- [ ] `src/specify_cli/merge/push_preflight.py` created with all five functions + `TargetBranchPushSafetyResult` + `check_push_safety`
- [ ] `preflight.py` is NOT modified by this WP (WP02 T006 handles cleanup)
- [ ] `mypy src/specify_cli/merge/push_preflight.py --strict` passes with 0 errors
- [ ] `ruff check src/specify_cli/merge/push_preflight.py` passes
- [ ] No import of `push_preflight` from `preflight.py`

## Risks

- **Import cycle**: `merge.py` imports `preflight.py` and will import `push_preflight.py`. Ensure neither `preflight.py` nor `push_preflight.py` import from `merge.py`. Check the existing import graph before moving functions.
- **Missing re-exports**: If `_enforce_target_branch_sync_preflight` in `merge.py` currently imports `TargetBranchSyncStatus` from `preflight.py`, that import must be updated to come from `push_preflight.py`. WP02 will do this — coordinate so types are available.
- **Test breakage**: Some tests in `test_target_branch_preflight.py` import from `preflight.py`. After this WP, those imports will need updating. WP03 handles this, but ensure the module's public API is stable before WP03 starts.
