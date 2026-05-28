---
work_package_id: WP05
title: BookkeepingTransaction + WorkflowMutationPolicy modules
dependencies:
- WP04
requirement_refs:
- C-013
- FR-019
- FR-020
- FR-021
- FR-023
- FR-026
- NFR-001
- NFR-008
- NFR-010
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
agent: claude
history:
- at: '2026-05-28T08:55:00+00:00'
  actor: claude
  event: wp_created
  notes: Generated via /spec-kitty.tasks from plan.md PR 2 design
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/coordination/transaction.py
execution_mode: code_change
owned_files:
- src/specify_cli/coordination/transaction.py
- src/specify_cli/coordination/policy.py
- src/specify_cli/coordination/types.py
- tests/specify_cli/coordination/test_transaction.py
- tests/specify_cli/coordination/test_policy.py
- tests/specify_cli/coordination/test_types.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, invoke `/ad-hoc-profile-load` with the profile listed in this WP's frontmatter (`agent_profile`). This loads the implementer identity, governance scope, and boundaries you must operate under for this WP.

Then return here and proceed.

---

## Objective

This is the **core architectural WP** of the mission. Implement two new modules:
- `src/specify_cli/coordination/policy.py` — `WorkflowMutationPolicy.assert_allowed()`, the single chokepoint for protected-branch refusal that operates on an explicit `destination_ref`.
- `src/specify_cli/coordination/transaction.py` — `BookkeepingTransaction`, the context-manager service that owns coordination-tree writes: acquires the feature status lock, runs pre-flight policy, captures `pre_emit_size`, appends events, re-materializes `status.json`, calls `safe_commit()`, defers outbound side effects, performs surgical rollback on failure, releases the lock.

After this WP lands, WP06 wires the actual workflow call sites to use these services.

## Context

**Spec source**: FR-019, FR-020, FR-021, FR-023, FR-026, NFR-001, NFR-008, NFR-010, C-013, I-1, I-7.
**Predecessor WPs**: WP04 (CoordinationWorkspace).
**Contracts**: `contracts/bookkeeping_transaction.md` and `contracts/workflow_mutation_policy.md` — **read both before starting**.

This WP is where the cross-review's hardest architectural pushback lives. Two things MUST be true:
1. The pre-flight policy gate (FR-019) refuses before any write happens. No rollback machinery is invoked in the refusal path because nothing was written.
2. The atomic window (FR-026) holds the feature status lock across the entire emit → materialize → commit → (rollback) → outbound dispatch. No concurrent emitter can interleave.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Lane B; sequential after WP04.

---

## Subtask T020: `GitChangeSet` value object + `PolicyVerdict` sum type

**Purpose**: Define the immutable value objects passed through the policy + transaction layer. Single source of truth for what a commit "intends to do."

**Steps**:
1. Create `src/specify_cli/coordination/types.py`:
   ```python
   from dataclasses import dataclass
   from pathlib import Path

   @dataclass(frozen=True, kw_only=True)
   class GitChangeSet:
       destination_ref: str
       repo_root: Path
       worktree_root: Path
       paths: tuple[Path, ...]
       message: str
       operation: str  # diagnostic label only

   @dataclass(frozen=True)
   class Allowed:
       pass

   @dataclass(frozen=True, kw_only=True)
   class Refused:
       error_code: str
       message: str
       destination_ref: str
       next_step: str

   PolicyVerdict = Allowed | Refused
   ```
2. Add `__all__ = ["GitChangeSet", "Allowed", "Refused", "PolicyVerdict"]`.
3. Write docstrings on each class. Reference the contract files.
4. Add a `to_dict()` method on `Refused` for JSON serialization.

**Files**:
- `src/specify_cli/coordination/types.py`

**Validation**:
- [ ] `mypy --strict src/specify_cli/coordination/types.py` passes.
- [ ] `GitChangeSet` is frozen; cannot be mutated after construction.
- [ ] `PolicyVerdict = Allowed | Refused` works as a type alias.

## Subtask T021: `WorkflowMutationPolicy.assert_allowed()`

**Purpose**: Implement the single chokepoint that decides whether a `GitChangeSet` is permitted. Stable error codes. Side-effect-free.

**Steps**:
1. Create `src/specify_cli/coordination/policy.py`:
   ```python
   from pathlib import Path
   import subprocess
   from .types import GitChangeSet, Allowed, Refused, PolicyVerdict

   class WorkflowMutationPolicy:
       @staticmethod
       def assert_allowed(change_set: GitChangeSet) -> PolicyVerdict:
           # 1. Validate destination_ref is non-empty.
           if not change_set.destination_ref or change_set.destination_ref.strip() != change_set.destination_ref:
               return Refused(
                   error_code="DESTINATION_REF_INVALID_SHAPE",
                   message=f"destination_ref is empty or has surrounding whitespace.",
                   destination_ref=change_set.destination_ref,
                   next_step="Pass a valid full ref name (e.g. kitty/mission-foo-01ABCDEF).",
               )
           # 2. Reject leading dash (potential CLI-flag confusion).
           if change_set.destination_ref.startswith("-"):
               return Refused(error_code="DESTINATION_REF_INVALID_SHAPE", ...)
           # 3. Reject refs/remotes/.
           if change_set.destination_ref.startswith("refs/remotes/"):
               return Refused(error_code="DESTINATION_REF_NOT_LOCAL", ...)
           # 4. Check existence.
           result = subprocess.run(
               ["git", "-C", str(change_set.repo_root), "rev-parse", "--verify", "--quiet",
                change_set.destination_ref],
               capture_output=True,
           )
           if result.returncode != 0:
               return Refused(error_code="DESTINATION_REF_NOT_FOUND", ...)
           # 5. Check protected-branch list.
           from specify_cli.git.commit_helpers import _is_protected_branch  # or whatever the existing helper is
           if _is_protected_branch(change_set.destination_ref):
               return Refused(
                   error_code="PROTECTED_BRANCH_REFUSED",
                   message=f"destination ref '{change_set.destination_ref}' is on the project's "
                           f"protected branch list. Bookkeeping commits must target a non-protected ref.",
                   destination_ref=change_set.destination_ref,
                   next_step=f"Use the coordination worktree. Re-run the command; the destination "
                             f"will auto-resolve to the coordination branch.",
               )
           return Allowed()
   ```
2. **No state mutation, no file writes, no lock acquisition** inside `assert_allowed`. Pure decision function.

**Files**:
- `src/specify_cli/coordination/policy.py`

**Validation**:
- [ ] All five `Refused` codes have at least one test (in T025).
- [ ] `assert_allowed` is side-effect-free (verified by tests that compare before/after git state).
- [ ] Stable error codes match the contract.

## Subtask T022: `BookkeepingTransaction` context manager

**Purpose**: The aggregate that owns coord-tree writes under the lock.

**Steps**:
1. Create `src/specify_cli/coordination/transaction.py`:
   ```python
   from contextlib import AbstractContextManager
   from pathlib import Path
   from typing import Callable
   from dataclasses import dataclass
   import os
   import subprocess

   from .workspace import CoordinationWorkspace
   from .policy import WorkflowMutationPolicy
   from .types import GitChangeSet, Allowed, Refused

   from specify_cli.locking import acquire_feature_status_lock  # existing helper
   from specify_cli.git.commit_helpers import safe_commit
   from specify_cli.status.models import StatusEvent
   from specify_cli.status.reducer import materialize


   @dataclass(frozen=True, kw_only=True)
   class EventReceipt:
       event_id: str
       commit_sha: str
       destination_ref: str
       worktree_root: Path


   class BookkeepingPolicyRefused(Exception): ...
   class BookkeepingLockTimeout(Exception): ...
   class BookkeepingCommitFailed(Exception): ...


   class BookkeepingTransaction(AbstractContextManager):
       """Holds the feature status lock across acquire → emit → commit → rollback → release."""

       @classmethod
       def acquire(
           cls,
           *,
           repo_root: Path,
           mission_id: str,
           mission_slug: str,
           mid8: str,
           destination_ref: str,
           operation: str,
           timeout: float = 30.0,
       ) -> "BookkeepingTransaction":
           # 1. Resolve coord worktree (or fall back for legacy in WP08).
           worktree_root = CoordinationWorkspace.resolve(repo_root, mission_slug, mid8)
           # 2. Acquire lock.
           lock = acquire_feature_status_lock(repo_root, mission_id, timeout=timeout)
           # 3. Capture pre_emit_size.
           events_path = worktree_root / "kitty-specs" / f"{mission_slug}-{mid8}" / "status.events.jsonl"
           pre_emit_size = events_path.stat().st_size if events_path.exists() else 0
           # 4. Run pre-flight policy.
           change_set = GitChangeSet(
               destination_ref=destination_ref,
               repo_root=repo_root,
               worktree_root=worktree_root,
               paths=tuple(),  # will be filled in as writes accumulate
               message="",     # set on commit
               operation=operation,
           )
           verdict = WorkflowMutationPolicy.assert_allowed(change_set)
           if isinstance(verdict, Refused):
               lock.release()
               raise BookkeepingPolicyRefused(verdict.to_dict())
           # 5. Return constructed object.
           return cls(
               repo_root=repo_root, worktree_root=worktree_root,
               events_path=events_path, pre_emit_size=pre_emit_size,
               destination_ref=destination_ref, operation=operation,
               mission_id=mission_id, lock=lock,
           )

       def __init__(self, *, repo_root, worktree_root, events_path, pre_emit_size,
                    destination_ref, operation, mission_id, lock):
           self.repo_root = repo_root
           self.worktree_root = worktree_root
           self.events_path = events_path
           self.pre_emit_size = pre_emit_size
           self.destination_ref = destination_ref
           self.operation = operation
           self.mission_id = mission_id
           self._lock = lock
           self._staged_paths: list[Path] = []
           self._appended_event_ids: set[str] = set()
           self._deferred_outbound: list[Callable[[], None]] = []
           self._committed = False
           self._receipt: EventReceipt | None = None

       def __enter__(self) -> "BookkeepingTransaction":
           return self

       def __exit__(self, exc_type, exc, tb) -> None:
           try:
               if exc is not None:
                   self._rollback()
                   return
               if not self._committed and self._staged_paths:
                   # implicit commit on clean exit
                   self.commit(self._derive_default_message())
               # run deferred outbound
               for sx in self._deferred_outbound:
                   try:
                       sx()
                   except Exception as e:
                       # log but do not abort other outbound; commit already succeeded
                       import logging
                       logging.getLogger(__name__).warning(
                           "deferred outbound failed: %s", e,
                       )
           finally:
               self._lock.release()

       def append_event(self, event: StatusEvent) -> None:
           if event.event_id in self._appended_event_ids:
               raise BookkeepingDoubleEventId(event.event_id)
           # append JSONL line
           import json
           line = json.dumps(event.to_dict(), sort_keys=True) + "\n"
           with open(self.events_path, "a", encoding="utf-8") as f:
               f.write(line)
           self._appended_event_ids.add(event.event_id)
           # re-materialize status.json
           snapshot = materialize(self.events_path.parent)
           status_json = self.events_path.parent / "status.json"
           status_json.write_text(json.dumps(snapshot.to_dict(), indent=2, sort_keys=True))
           self._staged_paths.append(self.events_path)
           self._staged_paths.append(status_json)

       def write_artifact(self, path: Path, content: bytes) -> None:
           # absolute or relative to worktree
           if not path.is_absolute():
               path = self.worktree_root / path
           path.parent.mkdir(parents=True, exist_ok=True)
           path.write_bytes(content)
           self._staged_paths.append(path)

       def stage_path(self, path: Path) -> None:
           if not path.is_absolute():
               path = self.worktree_root / path
           self._staged_paths.append(path)

       def commit(self, message: str) -> EventReceipt:
           if self._committed:
               return self._receipt  # type: ignore
           result = safe_commit(
               repo_root=self.repo_root,
               worktree_root=self.worktree_root,
               destination_ref=self.destination_ref,
               message=message,
               paths=tuple(self._staged_paths),
           )
           self._receipt = EventReceipt(
               event_id=next(iter(self._appended_event_ids), ""),  # first appended
               commit_sha=result.commit_sha,
               destination_ref=self.destination_ref,
               worktree_root=self.worktree_root,
           )
           self._committed = True
           return self._receipt

       def defer_outbound(self, side_effect: Callable[[], None]) -> None:
           self._deferred_outbound.append(side_effect)

       def _rollback(self) -> None:
           # truncate events file to pre_emit_size
           if self.events_path.exists():
               os.truncate(str(self.events_path), self.pre_emit_size)
           # re-materialize status.json
           snapshot = materialize(self.events_path.parent)
           status_json = self.events_path.parent / "status.json"
           if status_json.exists() or self.pre_emit_size > 0:
               status_json.write_text(json.dumps(snapshot.to_dict(), indent=2, sort_keys=True))
           # restore any other written paths
           for p in self._staged_paths:
               if p == self.events_path or p == status_json:
                   continue
               subprocess.run(
                   ["git", "-C", str(self.worktree_root), "checkout", "--", str(p)],
                   check=False,
               )

       def _derive_default_message(self) -> str:
           return f"chore: {self.operation}"
   ```
2. **No nested transactions**: the lock acquisition fails if another emitter holds it; the timeout raises `BookkeepingLockTimeout`.
3. The lock is `try / finally`-protected; **always** released, even on rollback failure.

**Files**:
- `src/specify_cli/coordination/transaction.py`

**Validation**:
- [ ] mypy --strict passes.
- [ ] Context-manager protocol (`__enter__` / `__exit__`) works correctly.
- [ ] Lock is always released.

## Subtask T023: Surgical truncate rollback path with `pre_emit_size`

**Purpose**: This is the core of FR-010. Verify the byte-identical SHA-256 property (NFR-001).

**Steps**:
1. The `_rollback()` method in T022 already includes the truncate. Verify the implementation:
   - Captures `pre_emit_size` once, at transaction start.
   - On exception, calls `os.truncate(str(events_path), pre_emit_size)`.
   - Re-materializes `status.json` from the truncated event log.
   - Restores any other written paths via `git checkout --` (these are non-event-log artifacts like decisions/index.json).
2. Edge case: if the events file did not exist at acquire time, `pre_emit_size == 0` — truncate to zero is fine.
3. Edge case: if `status.json` did not exist at acquire time, the rollback may leave a zero-event-log + new status.json. Acceptable; `status.json` is derived, not source. If desired, capture `pre_status_json_sha = sha256(status_json.bytes)` and restore.

**Files**:
- `src/specify_cli/coordination/transaction.py` (already in T022)

**Validation**:
- [ ] SHA-256 of `status.events.jsonl` is byte-identical pre/post forced failure (NFR-001 / SC-05 — tested in T025).
- [ ] The rollback path takes < 100ms on a 10MB event log (NFR-002).

## Subtask T024: Outbound-deferral mechanism (`defer_outbound`)

**Purpose**: SaaS event sync, dossier ingress, decision-thread fanout — any "push to external system" — must run only after the local commit succeeds (FR-022, NFR-009, SC-09).

**Steps**:
1. The `defer_outbound(side_effect)` method in T022 registers a no-arg callable into `self._deferred_outbound`.
2. In `__exit__` on success: iterate and call each. Catch exceptions individually so one failure doesn't block the rest. Log warnings on failure.
3. In `__exit__` on exception (rollback path): do NOT call any of them. The list is dropped.

**Files**:
- `src/specify_cli/coordination/transaction.py` (already in T022)

**Validation**:
- [ ] When commit succeeds, all deferred callbacks run in registration order.
- [ ] When commit fails (rollback), zero deferred callbacks run (tested in T025 / SC-09).
- [ ] Individual callback failures are logged but do not abort other callbacks.

## Subtask T025: Unit tests — full transaction lifecycle

**Purpose**: Exhaustive test coverage of the transaction service.

**Steps**:
1. In `tests/specify_cli/coordination/test_transaction.py`:
   - `test_acquire_release_happy_path()` — acquire, do nothing, release. Lock acquired and released.
   - `test_pre_flight_refusal_short_circuits()` — destination_ref is `main` (protected) → `BookkeepingPolicyRefused`; lock never enters held state for the caller (or is released immediately).
   - `test_append_event_then_commit()` — happy path with one event; assert event in file, status.json materialized, commit on coord branch.
   - `test_commit_failure_triggers_rollback()` — inject a failing pre-commit hook; assert SHA-256 of events file is byte-identical pre/post (NFR-001).
   - `test_rollback_status_json_consistent()` — after rollback, materialize from events file matches status.json on disk.
   - `test_double_event_id_in_one_transaction()` — append same event_id twice → `BookkeepingDoubleEventId`.
   - `test_deferred_outbound_runs_on_success()` — defer two callbacks; commit; assert both ran in order.
   - `test_deferred_outbound_skipped_on_failure()` — defer one callback; commit fails; assert callback did NOT run.
   - `test_deferred_outbound_individual_failure_logged()` — defer two callbacks; first raises; second still runs; warning logged.
   - `test_nested_lock_blocks()` — open a transaction; in another thread/process, try to acquire same mission → `BookkeepingLockTimeout`.
2. In `tests/specify_cli/coordination/test_policy.py`:
   - One test per Refused error_code.
   - `test_policy_is_side_effect_free()` — capture `git status` before/after; identical.
3. In `tests/specify_cli/coordination/test_types.py`:
   - `test_git_change_set_is_frozen()` — attempt mutation → `dataclasses.FrozenInstanceError`.
   - `test_refused_to_dict()` — round-trip JSON.

**Files**:
- `tests/specify_cli/coordination/test_transaction.py`
- `tests/specify_cli/coordination/test_policy.py`
- `tests/specify_cli/coordination/test_types.py`

**Validation**:
- [ ] All tests pass.
- [ ] Coverage on `src/specify_cli/coordination/transaction.py` ≥ 90%.
- [ ] Coverage on `src/specify_cli/coordination/policy.py` ≥ 95%.
- [ ] NFR-001 test demonstrates SHA-256 equality on 100 forced failures.

---

## Definition of Done

- [ ] All 6 subtasks complete (T020..T025).
- [ ] `pytest tests/specify_cli/coordination/` passes.
- [ ] `mypy --strict src/specify_cli/coordination/` passes.
- [ ] NFR-001 (SHA-256 byte equality after forced failure) verified via test.
- [ ] NFR-008 (policy gate < 10ms) verified via timed test.
- [ ] NFR-010 (lock hold < 250ms happy path) verified via timed test.

## Risks

- **Lock release on partial failure**: if rollback itself raises, the lock MUST still be released. Use `try/finally` rigorously.
- **`os.truncate` portability**: per DIR-001, must work on Linux/macOS/Windows. Python stdlib `os.truncate` supports all three. Verify on Windows in CI.
- **Materialize function side effects**: confirm `materialize()` is pure (reads events, returns snapshot). If it writes anywhere, fix that first.
- **Performance**: the rollback path must complete in < 100ms even on a 10MB event log. Use file truncation (O(1)) + bounded re-materialize.

## Reviewer guidance

1. **Lock discipline**: every code path through `__exit__` releases the lock. Use `try/finally`. No early returns that skip the release.
2. **Pre-flight refusal**: confirm that `BookkeepingPolicyRefused` is raised BEFORE the lock is held by the caller (or released immediately if briefly held). No writes happen during refusal.
3. **Rollback completeness**: truncate to `pre_emit_size`; re-materialize; restore any other written paths. All under the lock.
4. **Deferred outbound semantics**: only run on success; individual failures isolated.
5. **No nested transactions**: verify by test that a second acquire blocks.

## References

- Spec: FR-019..FR-026, NFR-001, NFR-008, NFR-010, C-013, I-1, I-7
- Plan: PR 2 step 3
- Contracts: [`contracts/bookkeeping_transaction.md`](../contracts/bookkeeping_transaction.md), [`contracts/workflow_mutation_policy.md`](../contracts/workflow_mutation_policy.md)
- Data model: [`data-model.md`](../data-model.md)
- Research: R-001, R-002 in [`research.md`](../research.md)
