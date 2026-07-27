---
work_package_id: WP05
title: Worktree-aware status read resolution
dependencies: []
requirement_refs:
- FR-013
- FR-014
- FR-015
planning_base_branch: fix/3.2.x-review-merge-gate-hardening
merge_target_branch: fix/3.2.x-review-merge-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.x-review-merge-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.x-review-merge-gate-hardening unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-review-merge-gate-hardening-3-2-x-01KRC57C
base_commit: fb6a45d54c20041636a147d70c43b3f6d94544b9
created_at: '2026-05-12T13:13:41.755586+00:00'
subtasks:
- T028
- T029
- T030
- T031
agent: "claude:opus:reviewer:reviewer"
shell_pid: "480572"
history:
- at: '2026-05-12'
  actor: planner
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/git/repo_root.py
execution_mode: code_change
mission_id: 01KRC57CNW5JCVBRV8RAQ2ARXZ
mission_slug: review-merge-gate-hardening-3-2-x-01KRC57C
owned_files:
- src/specify_cli/git/repo_root.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/status/lane_reader.py
- tests/status/test_status_read_worktree_resolution.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load implementer-ivan
```

The profile establishes your identity (Implementer Ivan), primary focus (writing and verifying production-grade code), and avoidance boundary (no architectural redesign; no scope expansion beyond what this WP authorizes). If the profile load fails, stop and surface the error — do not improvise a role.

## Objective

`spec-kitty agent tasks status` and other read-only status commands, when invoked from a detached worktree, must read from THAT worktree's `status.events.jsonl` — not silently resolve to the primary checkout's potentially-divergent state. Add `get_status_read_root()` helper; route read-only paths through it; fail loudly when detached-worktree reads are intentionally unsupported.

This WP fixes [#984](https://github.com/Priivacy-ai/spec-kitty/issues/984) and satisfies FR-013, FR-014, FR-015 in [`../spec.md`](../spec.md).

Reference contract: [`../contracts/status-read-worktree-resolution.md`](../contracts/status-read-worktree-resolution.md).

## Context

The reproduction (from #984): create a detached worktree at a verified merge SHA. Run `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty agent tasks status --mission <slug> --json` from inside that worktree. The command silently resolves to the **primary** local checkout (which may be on a divergent branch) and reports state from there — producing false-negative verifications.

The root cause is `get_main_repo_root()` (or its equivalent), which traverses up to the first git directory that has a non-empty `objects` directory — that's the primary repo. The function is correct for write paths (canonical serialization) but wrong for read paths (verification should reflect the current worktree).

Fix: a new `get_status_read_root()` helper that prefers the **current worktree root**; falls back to `get_main_repo_root()` only when no current worktree can be determined (very rare). Read-only status commands switch to the new helper. Write paths stay on `get_main_repo_root()`.

Per `research.md` R-6, the surface in scope is read-only. Write paths must NOT change.

## Branch Strategy

- **Planning/base branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Final merge target**: `main` (after PR review)
- **Execution worktree**: assigned by `spec-kitty implement WP05`. WP05 is independent; runs in parallel with WP02/WP04/WP06/WP07.

## Subtasks

### T028 [P] — Add `get_status_read_root()` helper

**Purpose**: a focused helper that returns the current worktree's root, falling back to `get_main_repo_root()` only when no worktree can be determined.

**Steps**:

1. Locate the existing `get_main_repo_root()` definition (likely in `src/specify_cli/git/repo_root.py` or a similar `git/` module). If the path differs, adjust `owned_files` accordingly during implementation; surface the change in the PR.
2. Add a sibling function:
   ```python
   def get_status_read_root(start: Path | None = None) -> Path:
       """Resolve the root for read-only status commands.

       Prefers the current worktree root over the primary checkout. Falls back
       to get_main_repo_root() only when worktree resolution fails (rare).

       Use this for READ paths only. For write paths (commits, file mutations,
       canonical serialization), continue to use get_main_repo_root().
       """
       cwd = (start or Path.cwd()).resolve()
       # Walk up until we find a .git file (worktree) OR a .git directory (main).
       for ancestor in [cwd, *cwd.parents]:
           git_marker = ancestor / ".git"
           if git_marker.is_file():
               # .git is a file in a worktree (points to the main repo's .git/worktrees/<name>).
               return ancestor
           if git_marker.is_dir():
               # .git is a directory: this is the main repo root.
               return ancestor
       # Fallback: defer to existing main-repo resolver.
       return get_main_repo_root(start)
   ```
3. Add unit tests covering: main-repo invocation, in-worktree invocation, detached worktree at a specific SHA, no-git directory (raises or falls back per the existing semantics).

**Files**: `src/specify_cli/git/repo_root.py` (or actual location)

**Validation**:
- [ ] Helper returns the worktree root from inside a worktree.
- [ ] Helper returns the main repo from inside the main checkout.
- [ ] mypy strict passes.

### T029 — Audit read-only callers of `get_main_repo_root()` and route through the new helper

**Purpose**: identify every call site of `get_main_repo_root()` in code paths that are **read-only** (no file writes, no commits, no status mutations). Route those through `get_status_read_root()`. Write paths stay on `get_main_repo_root()`.

**Steps**:

1. Inventory:
   ```bash
   rg -n 'get_main_repo_root' src/ tests/
   ```
2. For each call site, classify:
   - **Read-only**: `agent tasks status` (CLI), `spec-kitty next --json` (discovery; per R-6 audit only), dashboard scanner `gather_feature_paths()` (already prefers main with worktree fallback per mission 083 — verify the fallback works from a detached worktree).
   - **Write-path**: anything in `merge/`, `status/` writes (e.g., `append_event`), `sync emit`, frontmatter write paths, mission-create, finalize-tasks.
3. Replace the call in read-only sites with `get_status_read_root()`. Add an inline comment:
   ```python
   # Read-only path: use worktree-aware resolution so detached-worktree
   # verification (#984) reads the current worktree's events, not the
   # primary checkout's potentially-divergent state.
   ```
4. Leave write paths unchanged with an inline comment confirming the decision:
   ```python
   # Write path: keep main-repo-root resolution so canonical serialization
   # pins to the primary checkout regardless of where the operator stands.
   ```

**Files**:
- `src/specify_cli/cli/commands/agent/tasks.py` (status command surface)
- `src/specify_cli/status/lane_reader.py` (if it reads `get_main_repo_root` for status reads)
- Any other read-only site identified in the inventory

**Validation**:
- [ ] All read-only call sites route through the new helper.
- [ ] All write call sites unchanged.

### T030 — Fail-loud path for intentionally-unsupported detached-worktree reads

**Purpose**: if a status command intentionally cannot serve from a detached worktree (e.g., a command that requires comparison across worktrees), emit a diagnostic naming the constraint instead of silently reading the wrong checkout.

**Steps**:

1. Identify any read-only command in T029's inventory that genuinely cannot work from a detached worktree. The current inventory should be empty (all read-only commands work fine from worktrees), but flag this in the implementation for future evolution.
2. Add a helper `assert_worktree_supported()` that subcommands call when worktree-detached invocation is not appropriate:
   ```python
   def assert_worktree_supported(command_name: str) -> None:
       """Raise with a clear diagnostic when the current worktree is detached
       and the command does not support that context.
       """
       if _is_detached_worktree():
           raise StatusReadUnsupported(
               f"command '{command_name}' does not support detached-worktree invocation. "
               f"Run from the primary checkout or document the constraint."
           )
   ```
3. As of WP05's scope, this helper exists but is **not called** by any command. It's available for future commands that need it. Document this in the function docstring.

**Files**: same as T029

**Validation**:
- [ ] Helper exists and is unit-testable.
- [ ] No current command calls it (intentional; future use only).

### T031 — Regression fixture: two worktrees with divergent event logs

**Purpose**: prove from a regression that detached-worktree status reads return the worktree-local view, not the main checkout's view.

**Steps**:

1. Create `tests/status/test_status_read_worktree_resolution.py`.
2. Test setup:
   - Init a temporary git repo with a mission directory and `status.events.jsonl`.
   - Create a worktree at a separate path.
   - Write divergent events to each worktree's `status.events.jsonl`.
3. Test cases:
   ```python
   def test_status_read_from_main_repo_returns_main_events(tmp_repo, tmp_worktree):
       # Run agent tasks status --json from main; expect main's events.
       result = run_status_from(tmp_repo.path)
       assert result["events"] == tmp_repo.events

   def test_status_read_from_worktree_returns_worktree_events(tmp_repo, tmp_worktree):
       # Run agent tasks status --json from worktree; expect worktree's events.
       result = run_status_from(tmp_worktree.path)
       assert result["events"] == tmp_worktree.events

   def test_status_read_from_detached_worktree_returns_detached_events(tmp_repo):
       # Create a detached worktree at a specific SHA; verify isolated read.
       ...
   ```
4. Use `subprocess.run(["spec-kitty", "agent", "tasks", "status", "--json"], cwd=worktree_path)` for end-to-end verification.

**Files**: `tests/status/test_status_read_worktree_resolution.py` (new)

**Validation**:
- [ ] All three test cases pass.
- [ ] Removing T029's routing (i.e., reverting to `get_main_repo_root()`) makes the second and third tests fail — proves the test actually exercises the fix.

## Definition of Done

- [ ] T028–T031 acceptance checks pass.
- [ ] FR-013, FR-014, FR-015 cited in commits.
- [ ] Audit table (read-only vs write) committed inline in the PR description.
- [ ] No write-path regression: existing write-path tests pass unchanged.

## Risks and Reviewer Guidance

**Risk**: a write path gets mistakenly routed through `get_status_read_root()` → operator running from a detached worktree writes to the wrong checkout. **Reviewer must verify each routing change is read-only.**

**Risk**: edge case where `.git` is symlinked. The helper handles both `.git is a file` (worktree pointer) and `.git is a directory` (main repo). Symlinked `.git` is rare but should resolve correctly via `.is_dir()` / `.is_file()` on the symlink target. Add a test if relevant.

**Reviewer focus**:
- T029 audit table — is each routing decision correct?
- T031 — does the regression fail without the fix?

## Suggested implement command

```bash
spec-kitty agent action implement WP05 --agent claude --mission review-merge-gate-hardening-3-2-x-01KRC57C
```

## Activity Log

- 2026-05-12T13:13:43Z – claude:sonnet:implementer-ivan:implementer – shell_pid=464158 – Assigned agent via action command
- 2026-05-12T13:20:20Z – claude:sonnet:implementer-ivan:implementer – shell_pid=464158 – WP05 ready: worktree-aware resolver + read-only routing + regression test. Audit table in report. Location note: get_main_repo_root lives in core/paths.py (not git/repo_root.py); new symbols StatusReadUnsupported, get_status_read_root, assert_worktree_supported all land in core/paths.py.
- 2026-05-12T13:21:06Z – claude:opus:reviewer:reviewer – shell_pid=480572 – Started review via action command
- 2026-05-12T13:24:19Z – claude:opus:reviewer:reviewer – shell_pid=480572 – Review passed (FR-013/014/015): get_status_read_root in core/paths.py diverges from get_main_repo_root for worktrees; routed sites (tasks.py status, show_kanban_status) verified read-only; write paths (_ensure_target_branch_checked_out, _find_mission_slug, _check_unchecked_subtasks, _check_dependent_warnings, _validate_ready_for_review, merge.py, orchestrator_api/commands.py, worktree_topology.py, task_utils/support.py) unchanged; 11 regression tests pass; revert-guard test confirms pre-fix code reads wrong events from worktree.
