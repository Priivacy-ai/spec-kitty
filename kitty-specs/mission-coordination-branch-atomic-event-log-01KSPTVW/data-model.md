# Data Model: Mission Coordination Branch with Atomic Event Log

This document specifies the new entities, value objects, and invariants introduced by this mission. No persistent schema changes beyond ensuring `status.events.jsonl` and `status.json` are written exclusively by the new transaction layer.

---

## Entities and value objects

### `GitChangeSet` (value object)

A description of a would-be git commit, passed to `safe_commit()` and `WorkflowMutationPolicy.assert_allowed()`. Immutable.

```python
@dataclass(frozen=True, kw_only=True)
class GitChangeSet:
    destination_ref: str           # SHORT branch name (e.g. "kitty/mission-foo-01ABCDEF")
    repo_root: Path                # absolute path; primary checkout root
    worktree_root: Path            # absolute path; the worktree the commit will land in
    paths: tuple[Path, ...]        # files to stage (absolute or relative to worktree_root)
    message: str                   # commit message
    operation: str                 # human-readable label for diagnostics ("record WP01 claim")
```

**Invariants**:
- `destination_ref` is the **short branch name** (e.g. `kitty/mission-foo-01ABCDEF`), NEVER the fully-qualified `refs/heads/...` form. The HEAD assertion in `safe_commit()` normalizes `git symbolic-ref HEAD` output (strips the `refs/heads/` prefix) before comparing. Persisted artifacts (`meta.json`, `lanes.json`) use the short form. CLI inputs are normalized on entry. (C-016.)
- `worktree_root` is the worktree the commit will land in. For coordination-branch writes, this is the coordination worktree. For lane code commits, this is the lane worktree.
- `paths` is the staged set; if empty, the commit is a no-op (rejected by `safe_commit()` with `EMPTY_CHANGESET`).
- `operation` is for diagnostics only — never used as policy input.

### `PolicyVerdict` (sum type)

Result of `WorkflowMutationPolicy.assert_allowed(change_set)`. Either an `Allowed` marker or a `Refused` carrying structured error data.

```python
@dataclass(frozen=True)
class Allowed:
    pass

@dataclass(frozen=True, kw_only=True)
class Refused:
    error_code: str                # stable identifier; e.g. "PROTECTED_BRANCH_REFUSED"
    message: str                   # human-readable
    destination_ref: str           # echoed back for diagnostics
    next_step: str                 # one-line operator guidance

PolicyVerdict = Allowed | Refused
```

**Stable error codes** (NFR-007):
- `PROTECTED_BRANCH_REFUSED` — destination_ref is on the protected-branch list.
- `DESTINATION_REF_NOT_FOUND` — destination_ref does not exist in the repo.
- `DESTINATION_REF_NOT_LOCAL` — destination_ref is a remote-tracking branch; commit cannot land directly.

### `BookkeepingTransaction` (aggregate)

The single owner of writes that target the coordination branch (or, in legacy mode, the lane branch). Context-manager.

```python
class BookkeepingTransaction:
    """
    Acquired via `BookkeepingTransaction.acquire(mission_id, destination_ref, operation)`.
    Holds the feature status lock for the lifetime of the context.
    All workflow writes happen inside `with` block.
    """

    @classmethod
    def acquire(
        cls,
        *,
        repo_root: Path,
        mission_id: str,                 # ULID; canonical identity
        mission_slug: str,                # required: needed to resolve coord worktree path
        mid8: str,                        # required: needed for worktree disambiguation
        destination_ref: str,             # SHORT branch name (C-016)
        operation: str,                   # diagnostic label
    ) -> "BookkeepingTransaction": ...

    def __enter__(self) -> "BookkeepingTransaction": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...

    # Workflow operations (must be called inside `with` block)
    def append_event(self, event: StatusEvent) -> PendingEventHandle: ...
    def write_artifact(self, path: Path, content: bytes) -> None: ...
    def stage_path(self, path: Path) -> None: ...
    def commit(self, message: str) -> CommitReceipt: ...     # optional explicit; otherwise implicit on __exit__
    def defer_outbound(self, side_effect: Callable[[], None]) -> None: ...
```

**Invariants**:
- `__enter__` MUST: resolve the coordination worktree (or lane worktree in legacy mode), acquire the feature status lock, capture `pre_emit_size` for `status.events.jsonl`, run `WorkflowMutationPolicy.assert_allowed()` against `destination_ref`. If the policy refuses, raise `BookkeepingPolicyRefused` *before* any write.
- All writes inside the `with` block happen on the resolved worktree.
- `__exit__` (no exception): run any deferred outbound side effects, release the lock.
- `__exit__` (exception during writes): truncate `status.events.jsonl` to `pre_emit_size`, re-materialize `status.json`, do NOT run deferred outbound side effects, release the lock, re-raise the exception.
- `__exit__` (exception during commit): same rollback path as above.
- The lock is held for the entire `with` block. No nested transactions for the same mission.

### `PendingEventHandle` and `CommitReceipt` (value objects)

The cross-review correctly flagged that the earlier draft's `EventReceipt` was incoherent: it returned `commit_sha` from `append_event()` *before* a commit existed. Split into two distinct types:

```python
@dataclass(frozen=True, kw_only=True)
class PendingEventHandle:
    """Returned by BookkeepingTransaction.append_event().
    The event was appended to status.events.jsonl under the lock,
    but the tracking commit has not yet been attempted.
    """
    event_id: str                  # ULID from the StatusEvent

@dataclass(frozen=True, kw_only=True)
class CommitReceipt:
    """Returned by BookkeepingTransaction.commit() (or accumulated at successful __exit__).
    Confirms the tracking commit landed and lists every event_id included.
    """
    commit_sha: str                # git commit SHA
    committed_at: datetime         # commit timestamp (UTC)
    destination_ref: str           # short branch name the commit landed on
    worktree_root: Path            # worktree it was committed via
    event_ids: tuple[str, ...]     # every event_id included in this commit
```

**Invariants**:
- `PendingEventHandle` is returned even if the transaction later fails (the event was written to disk; the rollback path will remove it). Callers MUST NOT treat a `PendingEventHandle` as "the event is durably committed."
- `CommitReceipt` is returned ONLY after the tracking commit succeeds. On rollback, no receipt is produced.

### `CoordinationWorkspace` (service)

Resolves and idempotently creates the per-mission coordination worktree.

```python
class CoordinationWorkspace:
    """Service for managing .worktrees/<slug>-<mid8>-coord/."""

    @staticmethod
    def resolve(
        repo_root: Path,
        mission_slug: str,
        mid8: str,
    ) -> Path:
        """Return absolute path to coordination worktree; create if missing."""

    @staticmethod
    def teardown(
        repo_root: Path,
        mission_slug: str,
        mid8: str,
    ) -> None:
        """Remove the coordination worktree (idempotent)."""

    @staticmethod
    def is_present(
        repo_root: Path,
        mission_slug: str,
        mid8: str,
    ) -> bool: ...
```

**Invariants**:
- Idempotent (FR-018, FR-024): calling `resolve()` twice returns the same path; creating an already-existing worktree is a no-op.
- The coordination worktree is checked out to `kitty/mission-<slug>-<mid8>`. Never to any other branch.
- The worktree's `.git/info/sparse-checkout` is NOT modified by this service — coordination worktrees are full-tree.

### `WorkflowMutationPolicy` (service)

Wraps the existing protected-branch helper. Single chokepoint for refusal.

```python
class WorkflowMutationPolicy:
    @staticmethod
    def assert_allowed(change_set: GitChangeSet) -> PolicyVerdict:
        """
        Inspect change_set.destination_ref. Return Allowed if safe to proceed,
        Refused with stable error_code otherwise.
        """
```

**Invariants** (C-012):
- The policy input is `change_set.destination_ref` — never `os.getcwd()`, `git rev-parse HEAD`, or any inferred-from-checkout value.
- Idempotent and side-effect-free; calling `assert_allowed()` does not change repo state.

### `LaneWorktreeSparseCheckoutPolicy` (configuration)

The sparse-checkout pattern registered for every lane worktree at creation time.

```python
LANE_SPARSE_CHECKOUT_EXCLUSIONS = (
    "kitty-specs/*/status.events.jsonl",
    "kitty-specs/*/status.json",
)
```

The lane allocator runs `git sparse-checkout init --no-cone` and then `git sparse-checkout set` with the inverse-pattern (include everything *except* the exclusions). Exact mechanism is in [`contracts/coordination_workspace.md`](contracts/coordination_workspace.md).

---

## Updated existing entities

### `StatusEvent` (unchanged schema; new write contract)

No schema change. Existing fields: `event_id`, `wp_id`, `from_lane`, `to_lane`, `actor`, `at`, `evidence`, `feature_slug`, `force`, `execution_mode`, `reason`, `review_ref`.

**New write contract**:
- `StatusEvent` instances MUST be persisted via `BookkeepingTransaction.append_event()`. Direct writes to `status.events.jsonl` are forbidden (architectural test in PR 3 catches this).
- Reads remain via the existing `read_events()` / `reduce()` / `materialize()` functions in `src/specify_cli/status/`. Read-side code is unchanged.

### `safe_commit()` (signature change; FR-031)

**Before**:
```python
def safe_commit(repo_root: Path, message: str, paths: list[Path]) -> CommitResult: ...
```

**After**:
```python
def safe_commit(
    *,
    repo_root: Path,
    worktree_root: Path,
    destination_ref: str,
    message: str,
    paths: tuple[Path, ...],
) -> CommitResult: ...
```

**Internal behavior** (FR-031, C-015):
1. Resolve the worktree's HEAD: `git -C <worktree_root> symbolic-ref HEAD` → `actual_head`.
2. If `actual_head != destination_ref` → raise `SafeCommitHeadMismatch(destination_ref, observed_head=actual_head, worktree_root=worktree_root)`.
3. Run the existing protected-branch check against `destination_ref`. Refuse if protected.
4. Stage `paths`, run the commit, return `CommitResult`.

mypy --strict catches missing `destination_ref` at every call site.

### WP frontmatter (no schema change; FR-012)

Existing fields `planning_base_branch` and `merge_target_branch` are unchanged. `finalize-tasks` now writes the canonical merge target value (from `meta.json` → `target_branch`) rather than the current checkout branch.

---

## Invariants (cross-cutting)

| ID  | Invariant                                                                                                                                                   | Enforced by                                                  |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| I-1 | `status.events.jsonl` is byte-identical pre/post any forced commit failure when no concurrent writers were active.                                          | Lock + surgical truncate (FR-010, FR-026); test SC-05         |
| I-2 | No spec-kitty bookkeeping commit lands on a protected branch under any code path (new or legacy topology).                                                  | `safe_commit()` HEAD assertion + protected-branch check (FR-031, FR-019); tests SC-01 / SC-08 / SC-11 |
| I-3 | `status.events.jsonl` is append-only after every emit (no event_id is ever rewritten or removed from a committed log).                                       | Lock-only writes (R-001); truncate operates only on uncommitted post-emit bytes (FR-010); C-004 / C-014 |
| I-4 | `mission_id` (ULID) is the canonical identity. `mission_number` never appears in branch names, worktree paths, or commit messages.                          | FR-015; pre-existing from mission 083                         |
| I-5 | Every workflow write happens under the feature status lock; the lock is held across emit → materialize → commit → (optional rollback) → outbound dispatch.   | FR-026; architectural test (PR 3)                            |
| I-6 | A `safe_commit()` call cannot proceed when its worktree HEAD does not match `destination_ref`.                                                              | FR-031 HEAD assertion; structured error `SAFE_COMMIT_HEAD_MISMATCH` |
| I-7 | Outbound side effects (SaaS sync, dossier ingress) emit only after the corresponding local commit succeeds; on commit failure, zero outbound emission.       | FR-022 + `BookkeepingTransaction.defer_outbound()`; test SC-09 |
| I-8 | Lane worktrees never produce a diff for `status.events.jsonl` or `status.json`.                                                                              | FR-029 sparse-checkout pattern; doctor drift check (RR-04)   |
| I-9 | Lane integration merges (lane → coordination) never trigger a merge conflict on `status.events.jsonl` or `status.json` because the lane branch has no diff. | FR-028 + I-8 in combination; test SC-10                       |

---

## State transitions (unchanged)

No changes to the 9-lane WP state machine (planned → claimed → in_progress → for_review → in_review → approved → done; plus blocked / canceled). Aliases (`doing` → `in_progress`) and guards remain as in the 3.0 status model.

Lane integration introduces *no new lane state* — the `done` WP is the trigger for `lane → coordination` integration; the merge itself does not produce a new `StatusEvent` lane. (An optional `lane_integrated` event was discussed in FR-008's rewrite; it is a tracking event, not a lane transition.)

---

## Storage layout (after PR 2 lands)

```
<repo_root>/
├── .git/
├── .worktrees/
│   ├── <slug>-<mid8>-coord/              # NEW: coordination worktree
│   │   └── kitty-specs/<mission>/
│   │       ├── status.events.jsonl       # AUTHORITATIVE COPY
│   │       ├── status.json
│   │       ├── decisions/
│   │       ├── issue-matrix.md
│   │       ├── spec.md
│   │       ├── plan.md
│   │       ├── tasks/
│   │       └── ...
│   ├── <slug>-<mid8>-lane-a/             # lane worktree (sparse-checkout)
│   │   └── kitty-specs/<mission>/
│   │       ├── # status.events.jsonl     # EXCLUDED via sparse-checkout (FR-029)
│   │       ├── # status.json             # EXCLUDED via sparse-checkout (FR-029)
│   │       ├── spec.md                   # readable
│   │       ├── tasks/                    # readable
│   │       └── ...
│   └── <slug>-<mid8>-lane-b/             # ditto
├── kitty-specs/<mission>/                # primary checkout view (on canonical target)
│   └── ...                                # all files present after merge
├── src/
│   ├── specify_cli/
│   │   ├── coordination/                 # NEW: coordination + transaction + policy modules
│   │   │   ├── __init__.py
│   │   │   ├── workspace.py              # CoordinationWorkspace
│   │   │   ├── transaction.py            # BookkeepingTransaction
│   │   │   └── policy.py                 # WorkflowMutationPolicy
│   │   ├── git/
│   │   │   └── commit_helpers.py         # UPDATED: safe_commit() signature
│   │   ├── status/
│   │   │   └── emit.py                   # UPDATED: routes through BookkeepingTransaction
│   │   ├── locking.py                    # UNCHANGED
│   │   └── ...
└── .kittify/
    └── config.yaml                       # UNCHANGED
```
