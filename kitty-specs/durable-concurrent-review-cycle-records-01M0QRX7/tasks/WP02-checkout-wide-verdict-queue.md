---
work_package_id: WP02
title: Checkout-Wide Verdict Queue
dependencies: []
requirement_refs:
- C-002
- C-006
- FR-002
- FR-007
- NFR-004
planning_base_branch: mission/durable-concurrent-review-cycle-records
merge_target_branch: mission/durable-concurrent-review-cycle-records
branch_strategy: Planning artifacts for this mission were generated on mission/durable-concurrent-review-cycle-records. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/durable-concurrent-review-cycle-records unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-durable-concurrent-review-cycle-records-01M0QRX7
base_commit: 8a88b69a7a31bfe19a03285eb9865cd0ea9e007a
created_at: '2026-08-24T04:45:07.308675+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Concurrency foundation
history:
- at: '2026-08-23T18:37:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent:
- src/specify_cli/review/verdict_commit_queue.py
- tests/review/test_verdict_commit_queue.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/verdict_commit_queue.py
- tests/review/test_verdict_commit_queue.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- https://github.com/Priivacy-ai/spec-kitty/issues/3235
---

# Work Package Prompt: WP02 – Checkout-Wide Verdict Queue

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the `python-pedro` profile and apply its Python, typing, test, and boundary guidance before reading further.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

## ⚠️ IMPORTANT: Review Feedback

Check the event-log `review_ref` via `spec-kitty agent tasks status --mission 01M0QRX7`. Resolve every feedback item before resubmitting and append evidence to the Activity Log.

## Objectives & Success Criteria

Create a small synchronous cross-process queue for automatic verdict evidence saves. The queue is keyed by canonical Git common directory, spans missions and linked worktrees that share checkout Git state, waits up to exactly 10 seconds by default, then produces a typed explicit busy failure. It has no daemon, retry scheduler, global Git policy, or dependency addition.

Completion requires:

- one new review-domain production module with strict types and a narrow API;
- one new focused test module;
- identical lock path for main/linked worktrees and different mission slugs in one checkout;
- different lock path for independent clones;
- `filelock` timeout mapping with default `10.0` pinned by unit test;
- safe release on normal exit, Python exception, and child-process death;
- explicit and tested reentrancy semantics;
- structural evidence that no background process/thread/service is created;
- no change to the existing per-mission status-lock implementation.

## Context & Constraints

Read:

- `kitty-specs/durable-concurrent-review-cycle-records-01M0QRX7/plan.md` Critical-section and lock order.
- `kitty-specs/durable-concurrent-review-cycle-records-01M0QRX7/data-model.md` `VerdictCommitQueue`.
- `kitty-specs/durable-concurrent-review-cycle-records-01M0QRX7/contracts/verdict-save-queue.md` queue contract.
- `src/specify_cli/status/locking.py` for the repository's `filelock` conventions.
- `src/kernel/git_topology.py` for canonical `git_common_dir` resolution.
- `.kittify/charter/charter.md` for canonical-authority and cross-platform rules.

The operator explicitly rejected compare-and-swap/retry complexity. Do not add automatic retry, isolated indexes, SQLite, daemon lifecycle, or serialization of unrelated commits.

This WP owns only the new queue module and its tests. Downstream WPs integrate it. Avoid edits to `cycle.py`, `tasks_move_task.py`, `tasks_verdict_persistence.py`, or generic status/Git modules.

## Branch Strategy

- **Planning base branch**: `mission/durable-concurrent-review-cycle-records`
- **Final merge target**: `mission/durable-concurrent-review-cycle-records`
- **Execution**: run `spec-kitty agent action implement WP02 --agent codex --mission 01M0QRX7`; use the lane worktree selected from `lanes.json`.

## Subtasks & Detailed Guidance

### T006 – Implement canonical checkout-wide keying

**Purpose**: Serialize exactly the Git state shared by verdict evidence commits.

**Steps**:

1. Add `src/specify_cli/review/verdict_commit_queue.py`.
2. Resolve the repository's Git common directory via `kernel.git_topology.git_common_dir`; do not duplicate `.git` parsing.
3. Derive a stable mission-independent lock filename under that common directory.
4. Normalize absolute/relative common-dir forms consistently across platforms.
5. Keep path resolution free of mission slug, WP ID, branch, and process identity.
6. Expose the smallest useful API: a context manager/factory plus a typed busy exception and default timeout constant.

**Validation**:

- Linked worktrees converge on one path.
- Independent clones do not share a path.
- No placement or status authority is introduced.

### T007 – Implement bounded acquisition and typed refusal

**Purpose**: Turn contention into a bounded, truthful caller outcome.

**Steps**:

1. Set the production default to exactly `10.0` seconds.
2. Forward that value to `FileLock.acquire(timeout=...)` rather than implementing polling/retry.
3. Map `filelock.Timeout` to a review-domain exception such as `VerdictSaveBusy`.
4. Include safe diagnostics: lock scope/path and timeout, but no sensitive environment data.
5. Preserve the original cause for debugging.
6. Do not sleep after timeout or retry the verdict operation.

**Test**: inject a fake lock that captures `10.0` and raises immediately; do not make a unit test wait ten wall-clock seconds.

### T008 – Define cleanup, death, and reentrancy behavior

**Purpose**: Ensure no process can strand queue ownership.

**Steps**:

1. Release in a `finally`-safe context-manager path.
2. Test normal exit and arbitrary exception exit.
3. Use a portable spawned child that acquires the lock, then terminate/reap it; prove a later process can acquire.
4. Avoid POSIX signals as the only death proof.
5. Decide whether same-process nested acquisition is supported or refused. Prefer explicit refusal if supporting reentrancy adds hidden state.
6. Pin the decision with a bounded test so nested use cannot silently deadlock.

### T009 – Test keying across repository shapes

**Purpose**: Prove the queue scope matches the architecture rather than the current fixture.

**Cases**:

- two mission slugs in one checkout → same queue path;
- main worktree and linked worktree → same queue path;
- coordination topology sharing a common directory → same path;
- two independent clones → different paths;
- relative and absolute `commondir` representations → normalized correctly;
- Windows-compatible path construction → no colon/slash assumptions.

Use real temporary Git repositories for topology behavior where practical; use narrow fakes only for error mapping.

### T010 – Pin lock ordering and no-daemon boundaries

**Purpose**: Prevent future integration from turning the queue into another status lock or service.

**Steps**:

1. Document in the production module that verdict queue may be held over Git, while `feature_status_lock` may not.
2. Provide an assertion/helper seam downstream tests can use to detect forbidden status-lock/Git overlap without production test hooks.
3. Add a structural guard that the module creates no `Thread`, `Process`, `Popen`, scheduler, or service lifecycle.
4. Confirm the queue module does not import command orchestration or status event mutation.
5. Keep dependency direction review-domain → kernel topology/filelock only.

## Test Strategy

```bash
uv run python -m pytest tests/review/test_verdict_commit_queue.py -n0 -q --tb=short
uv run ruff check src/specify_cli/review/verdict_commit_queue.py tests/review/test_verdict_commit_queue.py
uv run mypy --strict src/specify_cli/review/verdict_commit_queue.py
```

Where platform-specific behavior cannot run locally, write portable tests for the native OS matrix in WP05; do not mark core behavior POSIX-only.

## Risks & Mitigations

- **Wrong key scope**: use canonical common-dir resolver and topology tests.
- **Deadlock through reentrancy**: explicitly refuse or rigorously support; never leave undefined.
- **Lock file cleanup misconception**: correctness is lock ownership release, not deleting the lock file.
- **Clock confusion**: delegate waiting to `filelock`, which uses bounded acquisition; any elapsed diagnostics use `time.perf_counter`, never wall-clock timestamps.
- **Scope creep**: integration belongs to WP03/WP04, not this primitive.

## Review Guidance

Reject if the lock includes mission identity, if generic commits are serialized, if a daemon/retry appears, if timeout is not exactly pinned, if tests depend on `fork`, or if the module duplicates Git topology logic. Confirm strict typing and that process death cannot strand ownership.

## Definition of Done

- T006–T010 recorded done through `mark-status`.
- New files remain within declared ownership.
- Focused tests, Ruff, and strict mypy pass.
- Public API is narrow enough for WP03/WP04 integration without exposing `FileLock` details.
- Independent review can verify every queue invariant from tests.

## Activity Log

- 2026-08-23T18:37:05Z – system – Prompt created.

Use `spec-kitty agent tasks move-task WP02 --to for_review --mission 01M0QRX7` when ready.
- 2026-08-24T10:50:43Z – codex – Cycle 3 correction commit 30901c69a; 15 focused and CI-selector tests pass; main-push collection completeness passes; Ruff and strict production mypy pass. Independent review approved; two test-only mypy findings reproduce identically on parent 77d626395.
