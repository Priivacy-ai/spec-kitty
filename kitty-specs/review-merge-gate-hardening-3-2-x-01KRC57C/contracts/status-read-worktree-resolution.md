# Contract: Status-read worktree resolution

**WP**: WP05 | **FRs**: FR-013, FR-014, FR-015 | **Source bug**: #984

## Surface in scope

Read-only status commands and their JSON outputs:

- `spec-kitty agent tasks status --json`
- (`spec-kitty next --json` discovery — audit; likely already correct after mission 068)

## Resolution rule

Read-only status commands resolve their data source via `get_status_read_root()` (new helper), which returns:

1. **The current worktree root** if invoked from inside a git worktree (including detached worktrees).
2. **`get_main_repo_root()`** as the fallback only when no current worktree can be determined.

Write paths (move-task, finalize-tasks, merge, sync emit) are **not** changed; they continue to resolve via `get_main_repo_root()` so canonical serialization remains pinned to the main checkout.

## Fail-loud cases

If a read-only command is invoked in a context where worktree resolution legitimately cannot apply (e.g., command requires comparison across worktrees), it MUST fail with a diagnostic naming the constraint and the operator's options — never silently fall back to the main repo root in a way that produces stale state.

## Acceptance fixtures

- Two-worktree fixture with divergent `status.events.jsonl`: from each worktree, `agent tasks status --json` reflects the local event log.
- Detached worktree at a verification SHA: `agent tasks status --json` matches a direct reducer pass over the worktree's events.
- Invocation from the main checkout: behavior unchanged from today.
- Write path invoked from a detached worktree: still resolves to main checkout (regression guard).

## Invariants

- `get_main_repo_root()` and `get_status_read_root()` are distinct, single-purpose helpers.
- Audit of all callers of `get_main_repo_root()` in read-only paths is part of WP05 done criteria.
