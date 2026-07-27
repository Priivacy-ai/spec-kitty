# Contract: `BookkeepingTransaction`

**Spec source**: FR-023, FR-024, FR-025, FR-026
**Module**: `src/specify_cli/coordination/transaction.py`

## Purpose

The single owner of writes that target the coordination branch (or, in legacy mode, the lane branch). Holds the feature status lock across the entire atomic window: emit → materialize → commit → (rollback on failure) → outbound dispatch → release.

## Signature

```python
class BookkeepingTransaction:
    @classmethod
    def acquire(
        cls,
        *,
        repo_root: Path,
        mission_id: str,                  # ULID; canonical identity
        mission_slug: str,                # required to resolve coord worktree path
        mid8: str,                        # required for worktree disambiguation
        destination_ref: str,             # SHORT branch name (C-016)
        operation: str,                   # diagnostic label
    ) -> "BookkeepingTransaction":
        """Construct + lock + pre-flight gate. Returns context manager."""

    def __enter__(self) -> "BookkeepingTransaction": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...

    def append_event(self, event: StatusEvent) -> PendingEventHandle: ...
    def write_artifact(self, path: Path, content: bytes) -> None: ...
    def stage_path(self, path: Path) -> None: ...
    def commit(self, message: str) -> CommitReceipt: ...     # implicit on __exit__ if not called
    def defer_outbound(self, side_effect: Callable[[], None]) -> None: ...
```

**Critical signature note (cross-review correction)**: An earlier draft of this contract showed `acquire(repo_root, mission_id, destination_ref, operation)`. That was incomplete — the worktree resolution path needs `mission_slug` + `mid8` to compute `.worktrees/<slug>-<mid8>-coord/`. The corrected signature above is canonical.

**Return-type note (cross-review correction)**: An earlier draft had `append_event()` returning an `EventReceipt` that carried `commit_sha`. That was incoherent — the commit doesn't exist when `append_event` returns. The corrected types are: `PendingEventHandle` (event_id only) from `append_event()`; `CommitReceipt` (commit_sha, committed_at, destination_ref, worktree_root, event_ids) from `commit()` / successful `__exit__`.

## Lifecycle invariants

1. **`acquire()`** synchronously:
   - Resolves the worktree to operate against:
     - Coordination-branch missions: `CoordinationWorkspace.resolve(repo_root, mission_slug, mid8)`.
     - Legacy missions: the current lane worktree.
   - Acquires the feature status lock (`src/specify_cli/locking.py`). Blocks if another emitter holds it; respects standard timeout (default 30s).
   - Captures `pre_emit_size = os.path.getsize(<worktree>/kitty-specs/<mission>/status.events.jsonl)`.
   - Constructs a `GitChangeSet` with the resolved `worktree_root`, `destination_ref`, and operation label.
   - Calls `WorkflowMutationPolicy.assert_allowed(change_set)`. If `Refused`, releases the lock and raises `BookkeepingPolicyRefused(verdict)` *before any write*.
   - Returns the transaction object.

2. **Inside the `with` block**, the caller may:
   - `append_event(event)` — appends a JSONL line to `status.events.jsonl` in the resolved worktree; re-materializes `status.json`. Idempotent within the transaction (calling twice with the same event_id is an error).
   - `write_artifact(path, content)` — write a non-event artifact (e.g. `decisions/index.json`, `issue-matrix.md`).
   - `stage_path(path)` — explicitly stage a path that was already modified out-of-band.
   - `defer_outbound(side_effect)` — register a callable to run *after* the commit succeeds.
   - `commit(message)` — explicit commit. Optional; if not called, `__exit__` does the commit using a default message derived from `operation`.

3. **`__exit__` on no exception**:
   - If the caller did not call `commit()`, perform it now.
   - On commit success: run deferred outbound side effects in registration order. Each failure is logged but does not abort the rest (best-effort fanout per FR-022 with degraded mode).
   - Release the feature status lock.

4. **`__exit__` on exception**:
   - The exception is from `append_event`, `write_artifact`, `commit()`, or a deferred-outbound callable that ran inside the block.
   - **Surgical rollback** (C-009 prohibits `git checkout --` for any rollback path):
     - `os.truncate(<worktree>/kitty-specs/<mission>/status.events.jsonl, pre_emit_size)` (FR-010).
     - Re-materialize `status.json` from the truncated event log.
     - For every path written via `write_artifact()` inside this transaction: restore from the **byte snapshot** captured at write time. Each `write_artifact()` call records `pre_write_bytes = path.read_bytes() if path.exists() else None` *before* writing the new content. On rollback: if `pre_write_bytes is None`, `path.unlink(missing_ok=True)`; otherwise `path.write_bytes(pre_write_bytes)`. No `git checkout --`. (C-009.)
     - For every path passed to `stage_path()` (already-modified files that the caller wants tracked), the rollback path does **nothing** — the caller is responsible for any state they wrote outside `write_artifact()`. Documented contract: only paths flowing through `write_artifact()` get snapshot/restore semantics.
   - **Do NOT** run deferred outbound side effects.
   - Release the feature status lock.
   - Re-raise the original exception (or wrap in `BookkeepingTransactionFailed` if useful for diagnostics).

5. **No nested transactions**: acquiring a second `BookkeepingTransaction` for the same `mission_id` while one is held raises `BookkeepingLockTimeout` after the lock-acquire timeout.

## Error codes

| Code                            | When raised                                                                       |
| ------------------------------- | --------------------------------------------------------------------------------- |
| `BOOKKEEPING_POLICY_REFUSED`    | Pre-flight policy gate refused (carries underlying `Refused` verdict)             |
| `BOOKKEEPING_LOCK_TIMEOUT`      | Feature status lock could not be acquired within the timeout                      |
| `BOOKKEEPING_WORKTREE_MISSING`  | Resolution found neither a coordination worktree nor a valid lane worktree         |
| `BOOKKEEPING_COMMIT_FAILED`     | Inner `safe_commit()` raised; rollback ran successfully; original error chained   |
| `BOOKKEEPING_ROLLBACK_FAILED`   | Rollback itself failed (rare; lock is still released, exception re-raised loudly) |
| `BOOKKEEPING_DOUBLE_EVENT_ID`   | Same event_id appended twice in one transaction                                   |

## Diagnostics emitted on commit failure (FR-011)

```
Tracking commit '<message>' was rejected by <reason> on branch <destination_ref>.
Lane transition <from_lane> → <to_lane> for <wp_id> has been rolled back.
status.events.jsonl restored to pre-emit state.
Next step: <concrete action — e.g. "Fix the pre-commit hook and re-run">.
```

JSON output mode (FR-014): the same fields surface as keys:
```json
{
  "error_code": "BOOKKEEPING_COMMIT_FAILED",
  "destination_ref": "kitty/mission-foo-01ABCDEF",
  "rejected_message": "<commit message>",
  "rejected_reason": "<git stderr or hook output>",
  "rolled_back_transition": {"wp_id": "WP01", "from_lane": "planned", "to_lane": "claimed"},
  "next_step": "Fix the pre-commit hook and re-run"
}
```

## Test surface

- **Unit acquire/release happy path**: lock acquired, no writes, lock released cleanly.
- **Unit pre-flight refusal**: policy refuses → lock never acquired (or released immediately); `BOOKKEEPING_POLICY_REFUSED` raised.
- **Unit append + commit happy path**: event appended, status materialized, commit succeeds, lock released, receipt returned.
- **Unit commit failure → rollback**: inject a pre-commit hook that always rejects; verify byte-identical pre/post `status.events.jsonl` (SC-05); verify no outbound side effects ran (SC-09).
- **Unit deferred outbound**: register two `defer_outbound()` callables; commit succeeds; both run in order.
- **Unit deferred outbound on failure**: register callable; commit fails; verify callable did NOT run.
- **Unit nested-lock attempt**: a second `acquire()` for the same mission blocks; the second raises `BOOKKEEPING_LOCK_TIMEOUT` after timeout.
- **Integration multi-process stress**: 20 parallel `acquire()` for the same mission; each runs serially; no interleaved events (SC-12).

## Public surface

`BookkeepingTransaction.acquire` is the only public entry point from this module. The class itself is exposed for type annotations but its `__init__` is private (use `acquire`).

## Performance budget

- `acquire()` → first `append_event()` ready: < 100ms on a typical repo (NFR-008 covers the policy gate sub-step).
- Lock hold time end-to-end (happy path): < 250ms (NFR-010).
- Rollback path (truncate + re-materialize): < 100ms on a 10MB event log (NFR-002).
