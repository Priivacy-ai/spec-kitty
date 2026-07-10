---
work_package_id: WP02
title: Low-risk HEAD/branch repoints
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-004
tracker_refs: []
planning_base_branch: fix/merge-base-diff-ssot
merge_target_branch: fix/merge-base-diff-ssot
branch_strategy: Planning artifacts for this mission were generated on fix/merge-base-diff-ssot. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/merge-base-diff-ssot unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
phase: Phase 2 - Repoints
shell_pid: "2577155"
history:
- timestamp: '2026-07-09T20:30:48Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
mission_id: 01KX44SDZPWMA4N7RPKNR3TQT1
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks_dependency_graph.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP02
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

Do not touch code until the profile is loaded and acknowledged.

# Work Package Prompt: WP02 – Low-risk HEAD/branch repoints

## Objective

Route the two straightforward copies of the merge-base/diff idiom through the WP01 surface with **zero behaviour change** (NFR-001). Parallel-safe with WP03 (disjoint files).

## Context & Constraints

- Depends on WP01 (`git_merge_base`, `git_diff_names`, `merge_base_changed_files` must exist). Import from `specify_cli.core.vcs.git`.
- Read `../spec.md` (FR-002, FR-004), `../plan.md` (IC-02), `../research.md` (Decision 5).
- **NFR-001 is load-bearing**: existing tests must pass with NO expected-value assertion changes. The post-plan squad verified these sites are tested via real-repo suites or global-`subprocess` ordered mocks or symbol-identity batteries — so most tests survive with no edit at all. If a test breaks on an *expected value*, you have changed behaviour — stop and reconsider.

## Subtasks & Detailed Guidance

### Subtask T006 – Repoint `tasks_move_task._mt_pre_review_changed_files`
- File: `src/specify_cli/cli/commands/agent/tasks_move_task.py` (~L814).
- Replace the inline `merge-base HEAD <base>` + `diff --name-only <mb>..HEAD` body with `return merge_base_changed_files(worktree_path, base_branch)`.
- Preserve the exact return: `tuple[str, ...]`, `()` on any git failure. Keep the docstring's contract note.

### Subtask T007 – Repoint `tasks_dependency_graph` upstream check
- File: `src/specify_cli/cli/commands/agent/tasks_dependency_graph.py` (~L178-200).
- **CRITICAL (F1)**: this site diffs `<merge_base>..<check_branch>` — the diff target is the **branch, not HEAD**. Use the primitives directly:
  ```python
  mb = git_merge_base(worktree_path, "HEAD", check_branch)
  if mb is None:
      return False
  changed = git_diff_names(worktree_path, mb, check_branch)
  ```
  Do **NOT** use `merge_base_changed_files` here — it would compute `mb..HEAD` and silently invert which commits are inspected.
- Preserve the downstream planning-only bool logic (the `all(... startswith planning/status ...)` verdict) verbatim.

### Subtask T008 – Verify behaviour preservation
- Run the `tasks_move_task` and `tasks_dependency_graph` test suites. Confirm they pass with **no expected-value edits** (a patch-target repoint is acceptable only if a test patched a now-moved subprocess handle; global `subprocess.run` patches resolve into `core/vcs/git.py` unchanged).
- Add one focused assertion (or confirm an existing one) proving `tasks_dependency_graph` inspects `check_branch`, not HEAD — a regression test for the F1 slip. (The WP01 branch-target primitive test is the unit-level guard; this is the site-level guard.)

## Branch Strategy

- Planning/base = merge target = `fix/merge-base-diff-ssot`. `spec-kitty agent action implement WP02 --agent <name>` (depends on WP01 — the lane bases on WP01's tip).

## Definition of Done

- [ ] Both sites route through the WP01 surface; ruff + mypy clean on both files.
- [ ] `tasks_dependency_graph` uses the two-ref primitive (`git_diff_names(mb, check_branch)`), NOT the HEAD convenience — asserted by a test.
- [ ] Existing suites green with zero expected-value assertion edits (NFR-001).

## Risks & Reviewer Guidance

- Reviewer: the #1 thing to verify is T007 — grep the diff for any `merge_base_changed_files(` in `tasks_dependency_graph.py`; if present, it's the F1 behaviour bug. Confirm the branch-target assertion exists and would fail on a HEAD swap.

## Activity Log

- 2026-07-09T22:56:35Z – claude:sonnet:python-pedro:implementer – shell_pid=2503977 – Assigned agent via action command
- 2026-07-09T23:12:35Z – claude:sonnet:python-pedro:implementer – shell_pid=2503977 – Ready: 2 repoints. T006 (_mt_pre_review_changed_files) now returns merge_base_changed_files(worktree_path, base_branch) verbatim. T007 (_behind_commits_touch_only_planning_artifacts) routes its merge-base call through git_merge_base (fixes any risk of the F1 HEAD-vs-branch inversion); the diff step deliberately stays a direct 'git diff --name-only merge_base..check_branch' subprocess call rather than git_diff_names, since that primitive collapses 'diff subprocess failed' and 'no changed files' into the same empty tuple and this site's contract is fail-CLOSED on diff failure (documented inline + in commit). Added test_behind_commits_diffs_check_branch_not_head as the F1 regression guard. Zero expected-value test edits; 199 passed in the affected suites (move_task/dependency_readiness/tasks_helpers). ruff check exit 0 on both changed files; mypy clean on both changed files (only pre-existing WP01-territory no-any-return at core/vcs/git.py:905, confirmed pre-existing via git stash diff).
- 2026-07-09T23:14:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=2577155 – Started review via action command
- 2026-07-09T23:17:27Z – user – shell_pid=2577155 – APPROVE. Both sites route through the WP01 surface: T006 _mt_pre_review_changed_files returns merge_base_changed_files() verbatim (tuple/()-on-failure preserved); T007 merge-base routes through git_merge_base(HEAD,check_branch) — grep confirms no merge_base_changed_files( in tasks_dependency_graph.py (the F1 inversion fence holds). 17 passed with ZERO expected-value edits (NFR-001); ruff exit 0; WP02's own commit touches only owned files + its test. FAIL-CLOSED DIFF DEVIATION ADJUDICATED as JUSTIFIED: git_diff_names collapses diff-failure and empty-diff into the same () tuple, so using it verbatim (as the prompt's literal T007 code suggested) would flip diff-failure from False→True = fail-OPEN, breaking pre-existing test_behind_commits_diff_subprocess_failure_returns_false (returncode 129 expects False) vs test_behind_commits_no_changed_files_returns_true (empty expects True). Implementer correctly kept the diff step as a documented direct subprocess.run returning False on failure, consolidating only the F1-risk merge-base half. NFR-001 (behaviour-preserving) is the mission's load-bearing invariant and explicitly overrides completeness; the actual F1 risk (HEAD-vs-branch inversion) IS eliminated at this site; the residual is only the fail-closed semantics that genuinely differ from the other 4 fail-open-tolerant sites. Extending the shared surface (git_diff_names sentinel/None) would re-open WP01's approved+merged surface and impose None-handling on 4 sites that don't need it — a mission-level call, not a WP02 blocker. Divergence is documented inline (14-line rationale) + commit + backed by real regression test test_behind_commits_diffs_check_branch_not_head. CLOSEOUT MUST CARRY A DOCUMENTED SC-001/NFR-002 EXCEPTION: the tasks_dependency_graph diff step remains one residual direct git-diff subprocess call (zero-residual-copies not literally satisfied at this ONE site), reason=fail-closed semantics unexpressible via the shared surface; optional follow-up to add a fail-distinguishing diff variant if literal zero-residual is later wanted. Anti-pattern checklist all PASS/N-A.
