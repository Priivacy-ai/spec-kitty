# Research: 3.2.0 Release Blocker Cleanup

**Mission**: `stable-320-release-blocker-cleanup-01KQW4DF`
**Phase**: 0 — Research and unknowns resolution
**Date**: 2026-05-05

---

## Summary

All planning unknowns have been resolved through direct code inspection of the
affected modules and through the DM-01KQW556RAG1N0QF7PVSTP08P7 planning
decision. No NEEDS CLARIFICATION items remain. Phase 1 design artifacts can
proceed.

---

## Blocker 1 — Sync Final-Sync Diagnostic Hygiene (#952)

### Investigation: sync module structure

**Source inspected**: `src/specify_cli/sync/` (all files)

**Findings**:

| File | Role | Relevant behavior |
|------|------|-------------------|
| `sync/__init__.py` | Lazy import registry | Routes imports to submodules |
| `sync/daemon.py` | Machine-global daemon lifecycle | `fcntl.flock` / `msvcrt.locking` lock acquisition; 10-second timeout; errors wrapped in `DaemonStartOutcome` with `skipped_reason` |
| `sync/batch.py` | Batch sync / offline queue replay | `categorize_error()` (line 65) substring matches against `ERROR_CATEGORIES`; `format_sync_summary()` builds JSON + console output; `generate_failure_report()` (line 178) per-event details |
| `sync/runtime.py` | SyncRuntime singleton | WebSocket state; event queues |
| `sync/client.py` | WebSocketClient | Server connectivity |
| `sync/background.py` | Background sync service | Async worker |
| `sync/events.py` | Event emission API | `emit_wp_status_changed()` etc. |

**Root cause confirmed**: Error messages from `daemon.py` (lock timeout) and `batch.py` (sync failures) are emitted directly to the console output stream — not routed through a stderr-only diagnostic channel. There is no deduplication. `--json` mode does not suppress them from stdout.

**Decision: CLI-side fix only.** The observed `sync.final_sync_lock_unavailable` is a local `fcntl.flock` timeout. The auth-refresh contention ("Another spec-kitty process is refreshing the auth session; retry in a moment") is local process coordination — the CLI detects that another CLI process holds the session lock. No changes to `spec-kitty-saas` are required.

### Existing error categories in batch.py

```python
ERROR_CATEGORIES = {
    "schema_mismatch": [...],
    "auth_expired": ["token", "expired", "unauthorized", "401"],
    "server_error": [...],
    "unknown": [...],
}
```

**Gap**: No categories for lock unavailable, auth refresh in progress, WebSocket offline, or interpreter shutdown. These four + the existing server/auth failure = the five categories required by FR-004.

### Design: SyncDiagnosticCode (5 categories)

```
sync.final_sync_lock_unavailable   — fcntl/flock timeout; daemon lock held
sync.auth_refresh_in_progress      — session lock held by another process refreshing auth
sync.websocket_offline             — WebSocket connection unavailable; events queued
sync.event_loop_unavailable        — RuntimeError on event loop during interpreter shutdown
sync.server_auth_failure           — 401/auth error from SaaS server
```

**Deduplication**: Per-process module-level `frozenset` accumulator; `emit_sync_diagnostic()` checks before emitting; reset is not needed (CLI is single-invocation).

---

## Blocker 2 — mark-status Non-Checkbox ID Resolution (#783)

### Investigation: tasks.py mark_status function

**Source inspected**: `src/specify_cli/cli/commands/agent/tasks.py`

**mark_status signature** (lines 1974–2002):
```python
def mark_status(
    task_ids: list[str],        # positional — CLI arguments
    status: str,                # --status done|pending
    mission: str | None,        # --mission <slug>
    feature: str | None,        # --feature (hidden, deprecated)
    auto_commit: bool | None,   # --auto-commit
    json_output: bool,          # --json
) -> None
```

**Current resolution strategies**:
1. Checkbox row: regex `r'-\s*\[[ x]\]\s*{task_id}\b'` against `tasks.md`
2. Pipe-table row: `_is_pipe_table_task_row()` + `_update_pipe_table_status()`

**Gaps**:
- No search for `Subtasks: T001, T002, T003` inline patterns
- No handling of bare WP IDs (e.g., `WP02`)
- No per-ID result structure — command exits on first failure; no partial results

**Normalization**: `_QUALIFIED_TASK_ID_RE` handles `<mission>/(T|WP)\d+` and `<mission>:(T|WP)\d+` → extracts bare form. This already handles qualified WP IDs; the gap is the resolution strategy after normalization.

**Output path**: `tasks.md` written in-place; `safe_commit()` for optional auto-commit; `emit_history_added()` for SaaS sync.

**WP ID delegation**: Confirmed via FR-008 and status module architecture: `mark-status WP02 --status done` should call `emit_status_transition(wp_id="WP02", to_lane="done")` from `src/specify_cli/status/emit.py`. The status module's `validate_transition()` guards invalid transitions. WP ID strategy does not mutate task artifact files.

### Inline Subtasks regex

New pattern to add:
```
r'Subtasks:\s*(?P<ids>(?:T|WP)\d+(?:\s*,\s*(?:T|WP)\d+)*)'
```
Extract individual IDs from the `ids` capture group by splitting on `,` + strip.

---

## Blocker 3 — Cross-Repo E2E uv-Managed Python (#975)

### Investigation: contract_drift_caught.py

**Source inspected**: `spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py`

**Current nested-env creation** (line 90):
```python
venv.create(venv_dir, with_pip=True, clear=True)
py = venv_dir / ("Scripts" if os.name == "nt" else "bin") / "python"
```

**Root cause confirmed**: `venv.create(with_pip=True)` calls `ensurepip` internally. uv-managed Python builds do not expose `libpython3.x.dylib` at the copied venv path on macOS, causing `ensurepip` to raise `EnsurepipDisabled` or an import error.

**Existing skip gates**: Each `subprocess.run()` pip call can skip the test if it fails, but the skip happens *after* the venv creation attempt, not before. The venv creation crash is uncaught.

**Drift assertions** (lines 126–137):
```python
assert result.returncode != 0                # drift must be detected
assert any(kw in combined for kw in ["event_id", "envelope", "999.0.0"])
```
These assertions remain valid after the fix; the helper just needs to get the venv created first.

### uv detection heuristic

```python
def _is_uv_managed() -> bool:
    if shutil.which("uv") is None:
        return False
    exe = sys.executable
    return any(marker in exe for marker in (".uv", "/uv/", "uv-managed"))
```

In practice, any runner with `uv` on PATH will benefit from `uv venv`. The heuristic errs toward using uv when available.

### Helper interface design

```python
# spec-kitty-end-to-end-testing/support/nested_env.py

@dataclass
class NestedEnvResult:
    venv_dir: Path
    python: Path
    pip: Path
    method: str  # "uv_venv" | "stdlib_venv"

def create_nested_env(venv_dir: Path) -> NestedEnvResult:
    ...
```

Skip/xfail reason format when both methods fail:
```
E2E environment limitation: could not create a nested Python environment.
uv venv failed: <reason>. stdlib venv unavailable on uv-managed Python (no libpython).
To run this scenario, ensure a standard CPython installation is on PATH.
```

---

## Blocker 4 — merge --dry-run Missing Mission Branch (#976)

### Investigation: merge.py dry-run path

**Source inspected**: `src/specify_cli/cli/commands/merge.py`

**Dry-run path** (lines 1447–1509):
- Requires `--mission` slug
- Reads `lanes.json`, resolves `assign_next_mission_number()`
- Outputs JSON with `would_assign_mission_number`, lanes, strategy
- Does **not** call `_run_lane_based_merge()` — actual merge skipped
- Does **not** check mission branch existence before reporting ready state

**Existing branch helpers**:
- `_has_branch_ref(branch)` at line 445: `git rev-parse --verify <branch>^{commit}` — already exists
- `_validate_target_branch()` (lines 668–684): uses `git rev-parse --verify refs/heads/{target}` / remote fallback

**Missing branch check**: Expected branch name is `kitty/mission-<slug>` where `<slug>` is `mission_slug`. The `_has_branch_ref()` helper can be reused directly.

**Existing preflight order**: `_enforce_git_preflight()` → `_enforce_target_branch_sync_preflight()` → `_enforce_review_artifact_consistency()`.

**Insertion point**: After target-branch sync preflight (which establishes tracking state), before review artifact consistency (which is merge-specific) for dry-run; before `merge_lane_to_mission()` for real merge.

### Decision: always_blocker (DM-01KQW556RAG1N0QF7PVSTP08P7)

`merge --dry-run` is read-only. Auto-creating the mission branch from a dry-run path violates this contract. If the branch is missing:
- Dry-run: output `ready: false`, `blocker: missing_mission_branch`, `expected_branch`, `remediation`
- Real merge: block before any irreversible git operation with the same error

**Remediation command in JSON output**:
```
git branch kitty/mission-<slug> <base-commit>
```
Where `<base-commit>` is the current `HEAD` of the target branch (e.g., `main`).

---

## References

| File | Role | Action |
|------|------|--------|
| `src/specify_cli/sync/diagnostics.py` | New diagnostic module | Create |
| `src/specify_cli/sync/daemon.py` | Lock error output | Refactor |
| `src/specify_cli/sync/batch.py` | Sync error output | Refactor |
| `src/specify_cli/cli/commands/agent/tasks.py` | mark-status resolution | Extend |
| `src/specify_cli/status/emit.py` | WP ID delegation target | Use (no change) |
| `src/specify_cli/cli/commands/merge.py` | Dry-run + real merge preflight | Extend |
| `spec-kitty-end-to-end-testing/support/nested_env.py` | uv-aware venv helper | Create |
| `spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py` | E2E scenario | Refactor |
