---
work_package_id: WP06
title: Extract the verdict seam out of tasks_move_task.py
dependencies:
- WP01
requirement_refs:
- C-003
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T022
- T023
- T024
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- tests/architectural/census/verdict_seam_IC01.yaml
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py
- tests/architectural/census/verdict_seam_IC01.yaml
- src/specify_cli/cli/commands/agent/tasks_transition_core.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP06 - Extract the verdict seam out of tasks_move_task.py

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load randy-reducer
```

## Objective

`tasks_move_task.py` is 2554 lines: the `_do_move_task` orchestration core plus
23 `_mt_*` phase helpers, `_MoveTaskState`, and `_default_move_task_ports`. Four
later work packages in this mission (WP09 numbering, WP10 atomicity, WP11
ordering, WP12 arbiter retirement) all need to touch verdict-relevant code
inside this one file, and the mission's own slicing gate
(`validate_no_overlap`) forces them into a strict serial chain
(WP06 → WP11 → WP12) purely because they'd otherwise claim overlapping
`owned_files` in a single 2554-line module.

This WP is the prerequisite that makes those four packages independently
sliceable: extract the four verdict-relevant sites into a small, singly-owned
new module, `tasks_verdict_persistence.py`, so later work happens there instead
of inside the god-module.

**This is a structural move, not a behaviour change.** No verdict-recording
logic, condition, or call ordering changes in this WP — only *where the code
lives*. Any test that goes red must be a fixture patching a now-relocated
symbol at its old dotted path, not a logic regression.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — C-003
  (renames out of scope)
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-00
  ("Extract the verdict seam out of `tasks_move_task.py`")
- `src/specify_cli/cli/commands/agent/tasks_move_task.py` — read the module
  docstring (lines 1-36) in full before touching anything. It documents:
  - the **import-cycle invariant**: "Symbols with ZERO patch sites and a
    canonical home outside `tasks.py` are imported directly at module scope
    (cycle-safe: **none of those modules import `tasks`**)." This sentence is
    the constraint T023 exists to preserve — see below.
  - the "Seam bridge" pattern: relocated bodies reach patched seam symbols via
    a lazy in-function import (`from specify_cli.cli.commands.agent import
    tasks as _tasks`), so every historical `@patch("...agent.tasks.<sym>")` /
    `monkeypatch.setattr(tasks, ...)` keeps intercepting after a move. This is
    the mechanism this WP's own extraction must follow for any symbol that is
    itself a patch target.
- `src/specify_cli/cli/commands/agent/tasks_materialization.py:145` — the
  existing precedent for a function-local import used *specifically* to avoid
  an import cycle. Read this before deciding how `tasks_verdict_persistence.py`
  imports from (or is imported by) `tasks_move_task.py` — it is the house
  pattern, not a one-off.

**Constraints (binding)**:
- **C-003 forbids identifier renames.** `meta.json` carries no `change_mode`
  key for this mission (the only valid value is `bulk_edit`; absence means
  non-bulk). No function, class, or variable is renamed by this WP.
- **A module move is not a no-op under C-003 even without a rename.** Moving a
  function from `tasks_move_task.py` to `tasks_verdict_persistence.py` changes
  its *qualified* name (`tasks_move_task._mt_fire_override_persist` →
  `tasks_verdict_persistence._mt_fire_override_persist`, or whatever the
  post-move name is) even when the local identifier is untouched. **This WP
  must not decide, on its own authority, whether that qualifies as a C-003
  violation.** Before executing the move: pose the exact question — "does
  relocating symbol `X` from module `A` to module `B` without renaming it
  violate C-003's 'no identifier rename' clause?" — to the operator, and
  record the verbatim question and verbatim answer in this WP's Activity Log
  before making the move. Do not proceed on an assumed answer.
- The import-cycle invariant ("none of those modules import `tasks`") must
  survive intact. If `tasks_verdict_persistence.py` needs anything from
  `tasks_move_task.py` or `tasks.py`, use the same lazy in-function import
  pattern already established at `tasks_materialization.py:145` and inside
  `tasks_move_task.py` itself — never a module-scope import that would create
  the cycle.
- A pure move shows up in `git diff` as added lines in the new file and
  removed lines in the old one. **The moved body therefore carries the ≥90%
  diff-coverage cost (NFR-004)** — this is not incidental overhead to
  minimize away; FR-015 (durability coverage) demands real coverage of this
  code regardless of which file it lives in, so budget test-writing time for
  it now rather than treating T023's test-suite move as a formality.

## Subtask T022 — Extract the four verdict-relevant sites into `tasks_verdict_persistence.py`

- **Purpose**: Move the identified verdict-relevant code out of the
  2554-line `tasks_move_task.py` into a new, small, singly-owned module so
  WP09/WP10/WP11/WP12 stop queueing on one file.
- **Steps**:
  1. Create `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`
     with a module docstring following the house style of the file it's
     extracted from (see `tasks_move_task.py`'s own docstring for the pattern:
     state what moved, from where, and why the import-cycle invariant holds).
  2. Move the four sites identified in `plan.md`'s IC-00 (verify current line
     numbers before moving — the plan's numbers are approximate and the file
     may have shifted since planning):
     - `~557` — the inline verdict resolver inside `_mt_gather_review_facts`
       (the block that computes `review_verdict` /
       `st.verdict_artifact_path` via `_get_latest_review_cycle_verdict`).
     - `~649` — the `_mt_fire_override_persist` function (the "OLD-timing
       review-artifact override" — calls `_persist_review_artifact_override`).
     - `~1712-1774` — the writer calls and transition ordering inside
       `_mt_finalize_plan`: the nested `_persist_approved_review_cycle`
       closure and the `if decision.planned_rollback and
       st.resolved_feedback_source is not None:` block that calls
       `create_rejected_review_cycle` for the rejection path.
     - `~2550` — the arbiter-decision persistence block inside the arbiter
       command handler (the `try: _arb_path = persist_arbiter_decision(...)`
       block and its exception handling).
  3. For each moved site, keep the body **byte-identical** apart from import
     paths — no logic change, no reordering, no renamed locals.
  4. Update `tasks_move_task.py` to call the relocated functions from the new
     module (module-scope import if no cycle risk, function-local import
     matching the existing lazy-import pattern if the symbol is itself a
     patch target elsewhere in the test suite — check
     `grep -rn "tasks_move_task\.<symbol_name>" tests/` for each moved symbol
     before deciding).
  5. Confirm `tasks_move_task.py`'s own module docstring (lines 1-36) is
     updated to reflect the extraction — it currently describes all four
     sites as living in this file; that description becomes stale the moment
     this WP lands and must be corrected in the same change, not left for a
     later truthfulness sweep (WP16 is downstream and dependent on this WP's
     surfaces already being accurate).
- **Files**: `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`
  (new), `src/specify_cli/cli/commands/agent/tasks_move_task.py`
- **Validation checklist**:
  - [ ] All four sites are physically absent from `tasks_move_task.py` and
        present in `tasks_verdict_persistence.py`.
  - [ ] `tasks_move_task.py` calls into the new module for all four; no
        duplicated logic remains in either file.
  - [ ] `tasks_move_task.py`'s docstring no longer claims sole ownership of
        the four sites.
  - [ ] `wc -l tasks_move_task.py` shows a real reduction (rough budget:
        ~150 lines move out, per plan.md's estimate for the new module).
- **Edge Cases**: The `~1712-1774` site is inside a closure
  (`_persist_approved_review_cycle` is defined *inside* `_mt_finalize_plan`,
  capturing `st`/`decision`/`ports` from the enclosing scope). Moving it to a
  separate module means it can no longer be a closure — it must become a
  top-level function in the new module taking those values as explicit
  parameters. This is a mechanical parameter-passing change, not a rename of
  the function's own name, and does not by itself trigger the C-003 question
  above (which is about the *module-qualified name* of the function, not its
  parameter list) — but confirm this reading is part of what you ask the
  operator in T024, since it is exactly the kind of edge a narrow ruling might
  not anticipate.

## Subtask T023 — Preserve the import-cycle invariant

- **Purpose**: `tasks_move_task.py:36`'s documented invariant — "none of those
  modules import `tasks`" — is what keeps the lazy in-function `import ... as
  _tasks` seam-bridge pattern working for every historical
  `@patch("...agent.tasks.<sym>")` fixture. If `tasks_verdict_persistence.py`
  imports `tasks.py` (or `tasks_move_task.py`) at module scope while either of
  those modules also (directly or transitively) imports
  `tasks_verdict_persistence.py`, you get a real circular import, not just a
  documentation violation.
- **Steps**:
  1. Before writing any import in the new module, map what
     `tasks_verdict_persistence.py` actually needs from elsewhere: likely
     `specify_cli.review.cycle` (writer), `specify_cli.review.artifacts`
     (reader helpers), `specify_cli.review.arbiter` (arbiter persistence),
     possibly `_MoveTaskState`'s shape from `tasks_move_task.py` for type
     hints only.
  2. For anything needed only for typing, use `if TYPE_CHECKING:` guards —
     zero runtime cost, zero cycle risk.
  3. For anything needed at runtime that itself might import `tasks` or
     `tasks_move_task` transitively, follow `tasks_materialization.py:145`'s
     precedent: a function-local `import` inside the function that needs it,
     not a module-scope import.
  4. After the move, run
     `python -c "import specify_cli.cli.commands.agent.tasks_verdict_persistence"`
     and `python -c "import specify_cli.cli.commands.agent.tasks_move_task"`
     from a clean interpreter (no prior imports cached) and confirm both
     succeed with no `ImportError` / circular-import traceback.
  5. Grep for evidence the invariant statement is still literally true:
     `grep -n "^import\|^from" src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`
     — none of the module-scope imports should resolve back to
     `tasks_move_task` or `tasks`.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`,
  `src/specify_cli/cli/commands/agent/tasks_move_task.py`
- **Validation checklist**:
  - [ ] Both modules import cleanly in isolation (fresh interpreter, no
        `sys.modules` pre-population).
  - [ ] No module-scope import in `tasks_verdict_persistence.py` resolves back
        to `tasks_move_task` or `tasks`.
  - [ ] Every historical `@patch("specify_cli.cli.commands.agent.tasks.<sym>")`
        / `monkeypatch.setattr(tasks, ...)` fixture that targeted a moved
        symbol still intercepts correctly (verified by running the existing
        test suite for `tasks_move_task.py`, not just by inspection).
- **Edge Cases**: A symbol with existing patch sites in the test suite
  (`grep -rn "patch.*tasks_move_task\." tests/` and
  `grep -rn "monkeypatch.setattr(tasks" tests/`) needs the seam-bridge
  treatment even if it's one of the four moved sites — check each moved
  symbol against both grep patterns individually; do not assume "verdict
  code" implies "no existing patch sites".

## Subtask T024 — Obtain and record the C-003 ruling for the module move

- **Purpose**: A prior adversarial round flagged that this WP must not decide,
  on the implementer's own authority, whether a module move that changes
  qualified names (without renaming local identifiers) counts as the kind of
  rename C-003 forbids. This subtask is the escalation, not an implementation
  detail to skip if the answer "seems obvious."
- **Steps**:
  1. Before executing T022's move (this subtask is sequenced conceptually
     first even though it's numbered last — do not write code that assumes an
     answer not yet obtained), formulate the precise question: *"C-003 says no
     identifier rename lands in this mission. This WP proposes moving
     `_mt_fire_override_persist` and three sibling functions/blocks from
     `tasks_move_task.py` to a new `tasks_verdict_persistence.py` module,
     without changing any function or variable name — only the module they
     live in, and therefore their fully-qualified dotted path. Does this
     qualify as a C-003 violation, or is C-003's rename prohibition scoped to
     identifier names only (not module-qualified paths)?"*
  2. Surface this question to the operator through whatever channel this
     mission's Activity Log / decision-recording convention uses (this
     mission's `decisions/` directory already holds five plan-time Decision
     Moments recorded via that mechanism — check whether the same mechanism
     accepts a mid-implementation question, or whether a direct operator
     exchange recorded in this WP's own Activity Log is the right channel for
     an implementation-time ruling; do not silently invent a third
     mechanism).
  3. Record the verbatim question and the verbatim answer in this WP's
     Activity Log (below) before proceeding with T022.
  4. If the ruling is "yes, this is a C-003 violation", stop and escalate
     further — do not attempt to satisfy both C-003 and IC-00's structural
     goal by inventing a workaround (e.g., re-exporting under the old
     qualified name) without that also being explicitly sanctioned, since a
     silent re-export is itself a design decision with its own tradeoffs
     (two import paths for one symbol) that deserves the same explicit
     sign-off.
- **Files**: none (process subtask — the ruling is recorded in this WP file's
  Activity Log, not in source)
- **Validation checklist**:
  - [ ] The exact question asked and the exact answer received are both
        recorded, verbatim, in this WP's Activity Log with a timestamp.
  - [ ] T022's move only proceeds after a ruling of "not a C-003 violation" (or
        an explicitly sanctioned workaround) is recorded.
- **Edge Cases**: If the ruling arrives after T022/T023 have already been
  implemented (e.g., because implementation order in practice differs from
  numbering), do not backfill a plausible-sounding answer after the fact —
  the ruling must be obtained and recorded honestly, even if that means
  reordering the actual work to ask first.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. This WP has no dependencies and
may start immediately from that branch. Completed changes merge back into
`pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly
redirects the landing branch.

## Definition of Done

- The C-003 ruling (T024) is obtained and recorded in this WP's Activity Log
  before the module move is committed.
- `tasks_verdict_persistence.py` exists and owns the four verdict-relevant
  sites; `tasks_move_task.py` no longer contains their bodies, only calls into
  the new module.
- `tasks_move_task.py:36`'s module docstring is corrected to describe the new
  ownership split.
- The import-cycle invariant holds: both modules import cleanly in isolation,
  and no existing `@patch`/`monkeypatch.setattr` fixture targeting a moved
  symbol breaks.
- Behaviour is unchanged: the full existing `tasks_move_task.py` test suite
  passes with zero logic modifications, only import-path updates in test
  fixtures where a moved symbol's patch target changed.
- `tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py` exists
  and directly exercises the new module's public surface (the ≥90%
  diff-coverage obligation this move carries).
- `mypy --strict` and `ruff` are clean on both touched/new files, zero new
  suppressions.
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **C-003 ambiguity resolved by assumption instead of ruling**: the single
  biggest risk named by the prior adversarial round. Mitigate by executing
  T024 first and literally refusing to write the move until the ruling is
  recorded.
- **Import-cycle invariant silently broken**: a module-scope import in the new
  file that resolves back to `tasks_move_task`/`tasks` would reintroduce the
  cycle the docstring says doesn't exist. Mitigate with the fresh-interpreter
  import check in T023, not just a visual read of the import block.
- **Patch-site breakage**: any of the four moved sites with an existing
  `@patch("...tasks_move_task.<sym>")` fixture will silently stop intercepting
  if the move doesn't preserve the seam-bridge pattern — this fails as
  seemingly-unrelated test breakage elsewhere, not as an obvious diff review
  finding. Mitigate by grepping for patch sites per-symbol before moving, not
  after.
- **Diff-coverage cost treated as optional**: a pure move naturally shows as
  100% "new" lines in the diff-coverage tool's eyes. Budget real test-writing
  time in T022/T023, not just a mechanical `git mv`-equivalent.

## Reviewer Guidance

- Confirm the C-003 ruling is recorded in the Activity Log with a verbatim
  question and answer, dated before the move's commit.
- Confirm zero logic changed in the four moved sites — diff each site against
  its pre-move form line-by-line (accounting for the closure-to-parameter
  change in the `~1712-1774` site, which is a mechanical, not logical, change).
- Confirm the import-cycle invariant claim is verified by an actual
  fresh-interpreter import test, not just asserted in the PR description.
- Confirm `tasks_move_task.py`'s docstring was updated in this WP, not left
  for WP16's truthfulness sweep to discover as still-wrong.
- Confirm the new test file exercises the moved code directly (not merely
  re-running the existing `tasks_move_task.py` suite through the new call
  path) — diff-coverage on genuinely new code needs genuinely new assertions.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP06 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
