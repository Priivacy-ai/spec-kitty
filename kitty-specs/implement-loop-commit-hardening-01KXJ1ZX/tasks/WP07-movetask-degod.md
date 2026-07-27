---
work_package_id: WP07
title: '#2649 — tasks_move_task.py degod + param-object (folds #2604)'
dependencies:
- WP06
- WP02
requirement_refs:
- C-001
- C-005
- C-006
- C-008
- FR-004
- NFR-001
- NFR-002
- NFR-004
tracker_refs:
- '2649'
- '2604'
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
- T035
- T036
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2862378"
shell_pid_created_at: "1784126900.2"
history:
- at: '2026-07-15T07:36:38Z'
  actor: claude
  note: Lane C tail; depends_on WP02 (hard C-006 edge). Folds
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/test_tasks_move_task_degod.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/specify_cli/cli/commands/test_tasks_move_task_degod.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration.
You are the **implementer**.

## Objective

Pay down the Sonar debt in `tasks_move_task.py` (FR-004), behavior-preserving: decompose
`_mt_commit_wp_file` (S3776≈19, folds #2604), convert `_do_move_task`'s **21-parameter**
signature to a parameter-object (≤13, the local hard gate), and tidy
`_mt_uncheck_rollback_subtasks` **without** breaking its #2576 dual-handler contract (C-001).

## Context — READ BEFORE CODING

- **C-006 hard dependency on WP02.** This WP's file imports and calls
  `_resolve_bookkeeping_transaction_identifiers` (`:1382/1392`, the 5-tuple) from
  `implement.py`. `depends_on: WP02` guarantees that symbol's contract is frozen before this
  WP integrates — do not re-derive it; consume the frozen 5-tuple.
- **C-001 (#2576):** `_mt_uncheck_rollback_subtasks` (`:1621-1696`) has TWO distinct
  exception handlers — the `#2576 rollback_uncheck_error` recording and the `#2513`
  commit-failure swallow. Do NOT merge them or swap to `logging.exception()`; preserve the
  degrade-never-crash discipline. Characterize before touching.
- **C-005 (#2639):** draft PR #2639 adds a parameter to `_do_move_task`. Measure the ≤13
  param target POST-rebase; use a parameter-object/dataclass so #2639's added arg does not
  breach the ceiling. If #2639 has not landed, note the rebase in the landing log.
- **C-008 / NFR-004:** extracted helpers module-private; no net-new public symbol.
- Gate note: `ruff C901` is already green; the ONE locally-hard gate is `_do_move_task`
  params ≤13. S3776 is advisory-post-merge.

## Subtasks

### T032 — Characterization: the #2576 dual-handler + move-task behavior

Create `tests/specify_cli/cli/commands/test_tasks_move_task_degod.py`:
1. Pin `_mt_uncheck_rollback_subtasks`' two-handler behavior: the `rollback_uncheck_error`
   is recorded (not swallowed) AND the commit-failure path degrades without crashing.
2. Pin `_mt_commit_wp_file`'s current observable behavior before extraction — specifically its
   **degrade-never-crash placement-ref branch** (when placement resolution fails/degrades, the
   commit does not crash the move-task), not just the happy path.

**Validation**: both pass against current code.

### T033 — Parameter-object for _do_move_task (≤13)

1. Extract a `@dataclass` parameter-object grouping the related `_do_move_task` arguments so
   the signature has ≤13 parameters (from 21). Preserve behavior and call sites.
2. If #2639 has landed, rebase first and measure ≤13 AFTER incorporating its added arg.

**Validation**: `_do_move_task` parameter count ≤ 13 (asserted); behavior unchanged.

### T034 — Degod _mt_commit_wp_file (folds #2604)

1. Decompose `_mt_commit_wp_file` into module-private helpers with focused tests to lower
   S3776. Consume the WP02 5-tuple as-is.

**Validation**: focused tests per helper; existing move-task suite green.

### T035 — Tidy _mt_uncheck_rollback_subtasks (preserve C-001)

1. Reduce its complexity while keeping the TWO separate exception handlers intact (do NOT
   collapse to `logging.exception`); T032 stays green.

**Validation**: T032 dual-handler test green; behavior preserved.

### T036 — Gate clean

1. `ruff` + `mypy --strict` zero new issues; `_do_move_task` params ≤13; full move-task
   suite green.

**Validation**: clean gate; param ceiling met.

## Branch Strategy

Planning branch / final merge target: **mission/2533-pr-bound-coord-claim-precondition**.
Lane C tail, after WP06. Cross-lane hard dependency on **WP02** (C-006). Landing note:
rebase after draft PR #2639.

## Definition of Done

- `_mt_commit_wp_file` decomposed (folds #2604), `_do_move_task` params ≤13 via
  parameter-object, `_mt_uncheck_rollback_subtasks` tidied preserving the #2576 dual-handler
  (FR-004, C-001, C-005).
- Consumes the frozen WP02 5-tuple (C-006); no net-new public symbol (C-008, NFR-004).
- Behavior preserved (NFR-002); `ruff` + `mypy --strict` clean (NFR-001).

## Risks & Reviewer Guidance

- **C-001 is the trap:** reviewer must confirm the two `_mt_uncheck_rollback_subtasks`
  handlers remain separate (no `logging.exception` merge) — T032 guards this.
- Confirm the WP02 5-tuple is consumed unchanged (the C-006 contract test in WP02 covers
  the producer side).
- Verify the param count is measured POST-#2639-rebase if #2639 landed.

## Activity Log

- 2026-07-15T14:27:19Z – claude:sonnet:python-pedro:implementer – shell_pid=2819243 – Started implementation via action command
- 2026-07-15T14:47:37Z – claude:sonnet:python-pedro:implementer – shell_pid=2819243 – Ready for review: move-task degod; _do_move_task params ≤13; #2576 dual-handler preserved; folds #2604
- 2026-07-15T14:48:23Z – claude:opus:reviewer-renata:reviewer – shell_pid=2862378 – Started review via action command
- 2026-07-15T14:52:40Z – user – shell_pid=2862378 – Review passed: _do_move_task now 2 params (args:_MoveTaskArgs frozen dataclass + kw-only ports) — well under the ≤13 hard gate; all 3 call sites (move_task Typer wrapper + 2 test _run_move helpers + escape-hatch assertions) correctly converted, behavior-preserving. #2576/#2513 dual-handler INTACT: split into _mt_attempt_uncheck_write (RECORDS st.rollback_uncheck_error + logging.error, never re-raises) and _mt_commit_uncheck_tasks_md (swallows commit failure as warning) — two legs stay distinct, no logging.exception merge; both pinned by TestUncheckRollbackDualHandler. _mt_commit_wp_file degrade-never-crash placement-ref branch preserved + pinned; #2604 folded via _mt_wp_commit_message/_mt_report_commit_outcome extraction. C-008/NFR-004 clean: all 5 re-exported symbols are _-prefixed via the established as-form seam-bridge, NONE added to __all__ (test-patch support, not public API widening). C-006: WP02 5-tuple consumed as-is at :1384/1392, untouched by this commit. Scope clean (only tasks_move_task.py + tasks.py re-export + new degod test + mechanical call-site test updates; WP06 transaction.py & WP01-05 untouched). Gates: 248 move-task tests + 318 compat/arch (no_write_side_rederivation, untrusted_path_containment) green; ruff + mypy --strict clean.
