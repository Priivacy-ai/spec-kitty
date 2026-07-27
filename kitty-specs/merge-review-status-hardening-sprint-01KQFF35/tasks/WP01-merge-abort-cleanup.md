---
work_package_id: WP01
title: merge --abort cleanup + merge.py BLE001
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-merge-review-status-hardening-sprint-01KQFF35
base_commit: 26df0d78b45a9f86e0e48171a3831bc0b242da17
created_at: '2026-04-30T15:43:37.437347+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:claude-sonnet-4-6:python-pedro:reviewer"
shell_pid: "5241"
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/merge.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge.py
- tests/specify_cli/cli/commands/test_merge.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load python-pedro
```

Wait for the profile to load, then continue reading this work package.

---

## Objective

Fix `spec-kitty merge --abort` so it fully cleans up after a crashed merge: removes the runtime lock file, removes the merge-state JSON, and aborts any in-progress git merge — all idempotently. Also add justification comments to the two bare `# noqa: BLE001` suppressions in `merge.py` (lines ~1026 and ~1275) that lack inline explanation.

## Context

**Why this matters**: After a squash merge crashed at commit `94007e4c`, operators could not re-run `spec-kitty merge` because `.kittify/runtime/merge/__global_merge__/lock` still existed. `merge --abort` did not clean it up. This required a manual `rm` to unblock. The fix is straightforward: make `--abort` explicitly delete both the lock file and the merge-state JSON, and abort any in-progress git merge.

The BLE001 changes are bundled here because WP01 already owns `merge.py`; keeping all changes to that file in one WP avoids ownership conflicts.

**Key location**: `src/specify_cli/cli/commands/merge.py`
- `_GLOBAL_MERGE_LOCK_ID = "__global_merge__"` is a constant near the top of the file
- The `--abort` flag is handled inside the `merge()` command function
- Lock path is constructed using `acquire_merge_lock` / the lock ID constant

## Branch Strategy

- **Planning branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: resolved by `spec-kitty agent action implement WP01 --agent claude`; do not create worktrees manually.

---

## Subtask T001 — Locate lock-file path derivation

**Purpose**: Understand exactly how the lock file path is constructed so T002 can delete the right file.

**Steps**:
1. Read `src/specify_cli/cli/commands/merge.py` — search for `_GLOBAL_MERGE_LOCK_ID` and `acquire_merge_lock`.
2. Identify the function or module that converts the lock ID to a filesystem path (e.g., `get_lock_path(id)` or inline construction).
3. Note the full path pattern: expected to be something like `<repo_root>/.kittify/runtime/merge/__global_merge__/lock`.
4. Also identify where the `--abort` flag is read inside the `merge()` callback (look for `if abort:` or similar).

**Files**: `src/specify_cli/cli/commands/merge.py` (read-only in this subtask)

**Validation**: You can describe the path before writing any code.

---

## Subtask T002 — Idempotent lock file deletion

**Purpose**: Delete `.kittify/runtime/merge/__global_merge__/lock` during `--abort`, silently if absent.

**Steps**:
1. In the `--abort` handler (found in T001), add:
   ```python
   from contextlib import suppress
   lock_path = <derived path from T001>
   with suppress(FileNotFoundError):
       lock_path.unlink()
   ```
2. Use `suppress(FileNotFoundError)` — do not use `try/except` with a bare `except Exception`.
3. Print a user-visible line: `"Removed merge lock."` if the file existed, or `"No merge lock found."` if it did not (optional — check whether existing `--abort` output is rich or plain and match the style).

**Files**: `src/specify_cli/cli/commands/merge.py`

**Validation**: After the change, running `--abort` when the lock file does not exist must not raise.

---

## Subtask T003 — Idempotent merge-state JSON deletion

**Purpose**: Delete `.kittify/merge-state.json` during `--abort`, silently if absent.

**Steps**:
1. Resolve the `merge-state.json` path. Check whether `clear_state()` from `src/specify_cli/merge/state.py` already does this — if so, call it instead of reimplementing.
2. If `clear_state()` exists and already suppresses `FileNotFoundError`, just call it.
3. If `clear_state()` does not suppress the error, either patch it or add `suppress(FileNotFoundError)` around the call.
4. Print: `"Removed merge-state."` or `"No merge-state found."` (match existing output style).

**Files**: `src/specify_cli/cli/commands/merge.py`, possibly `src/specify_cli/merge/state.py`

**Validation**: `--abort` exits 0 whether `.kittify/merge-state.json` exists or not.

---

## Subtask T004 — Conditional git merge --abort

**Purpose**: If git is in a merging state (`.git/MERGE_HEAD` exists), run `git merge --abort` to clean up the git side too.

**Steps**:
1. In the `--abort` handler, after lock and state cleanup, check whether git is in a merging state:
   ```python
   import subprocess
   merge_head = repo_root / ".git" / "MERGE_HEAD"
   if merge_head.exists():
       result = subprocess.run(
           ["git", "merge", "--abort"],
           cwd=repo_root,
           capture_output=True,
       )
       if result.returncode == 0:
           console.print("Aborted in-progress git merge.")
       else:
           console.print(f"git merge --abort failed: {result.stderr.decode().strip()}")
   ```
2. Do not raise on git failure — just report. The lock and state cleanup already happened.
3. Use `repo_root` from the existing context (check how other parts of `merge.py` resolve the repo root).

**Files**: `src/specify_cli/cli/commands/merge.py`

**Validation**: When `.git/MERGE_HEAD` does not exist, no git command is run. When it does exist, `git merge --abort` is attempted.

---

## Subtask T005 — Annotate merge.py BLE001 suppressions

**Purpose**: Add inline justification to the two bare `# noqa: BLE001` lines in `merge.py` (~L1026 and ~L1275).

**Steps**:
1. Find the lines with bare `# noqa: BLE001` (or `# noqa: BLE001, S110`):
   ```bash
   grep -n "noqa: BLE001" src/specify_cli/cli/commands/merge.py
   ```
2. For each, read the surrounding context (5-10 lines) and understand what exception is being swallowed and why.
3. Add an inline justification after `BLE001`:
   - Example: `# noqa: BLE001 — meta.json may be absent for legacy missions; fail-open is correct here`
4. The justification must explain WHY the swallow is safe, not just WHAT is happening.
5. If after reading the context you conclude the swallow is NOT safe (e.g., it masks a real error that should propagate), replace it with a narrower `except` or remove the suppression. In that case, note it in the commit message.

**Files**: `src/specify_cli/cli/commands/merge.py`

**Validation**: `grep "noqa: BLE001" src/specify_cli/cli/commands/merge.py` — every match has text after `BLE001`.

---

## Subtask T006 — Tests

**Purpose**: Verify --abort cleanup is correct and idempotent.

**Steps**:
1. Find or create the test file for `merge.py` (check `tests/specify_cli/cli/commands/`).
2. Write `test_abort_clears_lock_and_state`:
   - Setup: create a tmp repo dir with `.kittify/runtime/merge/__global_merge__/lock` and `.kittify/merge-state.json`.
   - Invoke the `--abort` path (via the Typer test runner or by calling the handler function directly).
   - Assert both files are gone.
   - Assert exit code 0.
3. Write `test_abort_idempotent`:
   - Setup: tmp repo dir with neither file present.
   - Invoke `--abort`.
   - Assert exit code 0 (no FileNotFoundError raised).
4. Ensure `uv run pytest tests/specify_cli/cli/commands/test_merge.py -x` passes.
5. Ensure `uv run mypy --strict src/specify_cli/cli/commands/merge.py` passes.

**Files**: `tests/specify_cli/cli/commands/test_merge.py`

---

## Definition of Done

- [ ] `spec-kitty merge --abort` removes `.kittify/runtime/merge/__global_merge__/lock` when present
- [ ] `spec-kitty merge --abort` removes `.kittify/merge-state.json` when present
- [ ] `spec-kitty merge --abort` aborts in-progress git merge when `.git/MERGE_HEAD` exists
- [ ] All three steps exit 0 whether or not the artifacts were present
- [ ] `merge.py` BLE001 suppressions at ~L1026 and ~L1275 have inline justification text
- [ ] Tests pass: `test_abort_clears_lock_and_state`, `test_abort_idempotent`
- [ ] `uv run mypy --strict src/specify_cli/cli/commands/merge.py` — zero errors
- [ ] `uv run ruff check src/specify_cli/cli/commands/merge.py` — zero errors

## Reviewer Guidance

- Verify the lock path used in the cleanup matches the actual path created by `acquire_merge_lock`.
- Run `spec-kitty merge --abort` manually (no lock/state present); confirm exit 0 and clean output.
- Confirm BLE001 justifications describe WHY (not just WHAT) the swallow is safe.

## Activity Log

- 2026-04-30T17:39:51Z – claude – shell_pid=41457 – Ready for review: idempotent abort cleanup + BLE001 annotations
- 2026-04-30T17:40:13Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=5241 – Started review via action command
- 2026-04-30T17:43:52Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=5241 – Review passed: idempotent abort cleanup and BLE001 annotations verified
