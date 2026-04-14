---
work_package_id: WP06
title: Review-Lock Fixes, Release Lifecycle, and Session-Warning in Task Commands
dependencies:
- WP02
requirement_refs:
- FR-010
- FR-015
- FR-017
- FR-018
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: main-to-main
subtasks:
- T024
- T026
- T027
- T028
- T029
- T031
phase: Phase 1 — Review-lock track
history:
- timestamp: '2026-04-14T05:26:49Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
execution_mode: code_change
mission_id: 01KP54ZWEEPCC2VC3YKRX1HT8W
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/review/lock.py
- tests/integration/review/test_approve_without_force.py
- tests/integration/review/test_reject_without_force.py
tags: []
wp_code: WP06
---

# Work Package Prompt: WP06 — Review-Lock Fixes, Release Lifecycle, and Session-Warning in Task Commands

## Implementation Command

```bash
spec-kitty agent action implement WP06 --agent <your-agent-name> --mission 01KP54ZW
```

Depends on WP02 (uses the warn function). Rebase onto WP02's lane.

---

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- Lane allocation by `finalize-tasks`; resolve from `lanes.json`.

---

## Objective

Close Priivacy-ai/spec-kitty#589 end-to-end: the review lock must no longer trip spec-kitty's own uncommitted-changes guard, the guard's retry guidance must name the caller's actual target lane, the lock must be released on every transition out of review, and the guard must still block on genuine uncommitted implementation work.

Also install the session-warning call sites inside `agent/tasks.py` commands as half of the FR-010 coverage. The complementary external call sites are WP07.

---

## Context

- The self-collision was diagnosed in issue #589 and verified in `src/specify_cli/cli/commands/agent/tasks.py` around lines 592–824 (function `_validate_ready_for_review`) and `src/specify_cli/review/lock.py` (the `ReviewLock` class).
- Constraints: FR-010 (partial), FR-015, FR-017, FR-018, FR-019, C-003 (named deny-list, not patterns), C-004 (genuine drift still blocks).

---

## Subtask Guidance

### T024 — Session-warning call sites in task commands

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**What**: At the top of every user-facing Typer handler in this file that mutates state — specifically `move-task`, `tasks-finalize`, `mark-status`, `map-requirements`, and any other state-mutating command — call:

```python
from specify_cli.git.sparse_checkout import warn_if_sparse_once

warn_if_sparse_once(main_repo_root, command="spec-kitty agent tasks move-task")  # adjust command string per handler
```

Use the command string that matches the user-visible CLI path. Call at the top of the handler before any state is read; detection errors are swallowed inside `warn_if_sparse_once` so this is safe.

**Validation**:
- Every state-mutating handler in tasks.py has exactly one call.
- Command string in each call matches the public CLI path (enables log searches).
- Read-only handlers (like `status`) do not get the hook.

---

### T026 — Deny-list filter in `_validate_ready_for_review`

**Files**: `src/specify_cli/cli/commands/agent/tasks.py` around line 786 (where the porcelain scan produces `uncommitted_in_worktree`).

**What**: Before the scan output is interpreted as drift, filter out lines whose path falls under a named directory in the deny-list. Do NOT convert this to a pattern match. The filter is a literal `startswith` check against a fixed tuple:

```python
_RUNTIME_STATE_DENY_LIST = (".spec-kitty/", ".kittify/")


def _filter_runtime_state_paths(porcelain_output: str) -> str:
    """Strip lines whose path falls under spec-kitty's own runtime state dirs.

    C-003: fixed named list, not patterns. C-004: genuine drift elsewhere still
    reaches the guard unchanged.
    """
    kept: list[str] = []
    for line in porcelain_output.splitlines():
        if not line.strip():
            continue
        # git status --porcelain format: first 3 chars are status + space
        path_part = line[3:] if len(line) > 3 else line.strip()
        if any(path_part.startswith(prefix) for prefix in _RUNTIME_STATE_DENY_LIST):
            continue
        kept.append(line)
    return "\n".join(kept)
```

Apply it to `uncommitted_in_worktree` (line 790):

```python
uncommitted_in_worktree = _filter_runtime_state_paths(result.stdout.strip())
```

**Validation**:
- Constant is module-level so tests can inspect it.
- Does not remove non-deny-list paths.
- When only `.spec-kitty/` is untracked, `uncommitted_in_worktree` becomes empty and the guard does not trip.

---

### T027 — Parameterize retry guidance on `target_lane`

**Files**: `src/specify_cli/cli/commands/agent/tasks.py:823`.

**What**: Replace the hardcoded `for_review` in the retry hint with the caller's actual `target_lane`:

```python
# Before:
guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to for_review")
# After:
guidance.append(f"Then retry: spec-kitty agent tasks move-task {wp_id} --to {target_lane}")
```

Trace the chain: `_validate_ready_for_review` is called from `move-task` with `target_lane` available in the outer scope. Thread `target_lane` as a parameter into `_validate_ready_for_review` so the function has access to it and propagate through every `guidance.append(...for_review)` site in the function (lines 709, 738, 783, 823 based on the current code). Each of those must use `target_lane`, not the hardcoded string.

**Validation**:
- Every retry message in `_validate_ready_for_review` names the actual `target_lane` passed by the caller.
- No occurrences of literal `"for_review"` in retry strings remain in that function.

---

### T028 — Enhance `ReviewLock.release()`

**Files**: `src/specify_cli/review/lock.py`.

**What**: Replace the existing `release` static method:

```python
@staticmethod
def release(worktree: Path) -> None:
    """Release the review lock. Remove the lock file and, if the parent
    `.spec-kitty/` directory is empty after removal, remove the directory too.
    """
    lock_dir = worktree / LOCK_DIR
    lock_path = lock_dir / LOCK_FILE
    if lock_path.exists():
        lock_path.unlink()
    if lock_dir.exists() and lock_dir.is_dir():
        try:
            if not any(lock_dir.iterdir()):
                lock_dir.rmdir()
        except OSError:
            # Non-empty or permission issue — leave the directory in place.
            pass
```

**Validation**:
- Lock file removal behaviour is unchanged when the directory is non-empty.
- The directory is removed ONLY when it is empty.
- `OSError` is swallowed; never crashes the CLI.

---

### T029 — Invoke `ReviewLock.release()` at approve and reject exits

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`.

**What**: At the successful-exit path of `move-task --to approved` and `move-task --to planned` (when the prior state was `in_review` or `for_review`), call:

```python
from specify_cli.review.lock import ReviewLock

try:
    ReviewLock.release(worktree_path)
except Exception as exc:
    logger.warning("Review lock release failed at %s: %s", worktree_path, exc)
```

Placement must be after the lane transition commit succeeds but before the function returns. Use the existing `worktree_path` variable used earlier in the function.

**Validation**:
- Lock release happens on the SUCCESS path of approve and reject.
- Lock release does not happen on other transitions.
- A failed release is logged but does not fail the overall command.

---

### T031 — Integration tests [P]

**Files**: `tests/integration/review/test_approve_without_force.py`, `tests/integration/review/test_reject_without_force.py` (new).

Test cases:

`test_approve_without_force.py`:
- **Happy path**: fixture with lane worktree in `for_review`, only untracked content is `.spec-kitty/review-lock.json`. `move-task WP01 --to approved` succeeds without `--force`.
- **Post-transition state**: `.spec-kitty/` directory is removed after success.
- **Genuine drift still blocks**: fixture with lane worktree where `src/feature.py` is uncommitted AND `.spec-kitty/` exists. `move-task WP01 --to approved` fails; error message lists `src/feature.py` but NOT `.spec-kitty/`.
- **Retry text**: fails on genuine drift; error message says `Then retry: ... --to approved` (not `for_review`).

`test_reject_without_force.py`:
- **Happy path**: same fixture, `move-task WP01 --to planned --review-feedback-file feedback.md` succeeds without `--force`.
- **Post-transition state**: `.spec-kitty/` removed.
- **Genuine drift still blocks**: same as above but target `planned`; error message says `Then retry: ... --to planned`.

Each test uses a lane-worktree fixture. Mock or genuinely stand up a review lock via `ReviewLock.acquire()`.

---

## Definition of Done

- [ ] Session-warning call sites installed in every state-mutating handler of `agent/tasks.py` (T024).
- [ ] Runtime-state deny-list filter applied in `_validate_ready_for_review` (T026).
- [ ] Retry guidance parameterized on `target_lane` in all four guidance sites (T027).
- [ ] `ReviewLock.release()` removes lock file AND empty parent directory (T028).
- [ ] `ReviewLock.release()` invoked on the success path of `move-task --to approved` and `--to planned` (T029).
- [ ] 2 integration test files exist and pass; every case in T031 passes.
- [ ] Existing `tests/integration/review/*` tests still pass — no regression.
- [ ] `mypy --strict src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/review/lock.py` passes.

## Risks

- **Broad change surface in tasks.py**: the file is large and multi-owned historically. Run the whole test suite after modifications to catch side effects.
- **Filter breadth**: resist the urge to add entries to `_RUNTIME_STATE_DENY_LIST` beyond `.spec-kitty/` and `.kittify/`. Per C-003, this is a narrow named list.
- **Lock release ordering**: release must happen AFTER the lane transition commit, so that if release fails, the transition is still recorded. Reviewer should verify this ordering explicitly.

## Reviewer Guidance

- Grep for `"for_review"` in `_validate_ready_for_review` — should only appear when `target_lane == "for_review"` is computed, not as a literal in retry strings.
- Verify `_RUNTIME_STATE_DENY_LIST` is a fixed tuple; no `re.compile`, no glob expansion.
- Verify `ReviewLock.release()` is idempotent: calling it twice does not crash (second call's `lock_path.exists()` is False).
- Verify genuine uncommitted work in the worktree still blocks (C-004 regression test).
