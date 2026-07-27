---
work_package_id: WP03
title: move_task transition decision core (pure)
dependencies:
- WP02
requirement_refs:
- C-003
- FR-002
- FR-004
- NFR-002
tracker_refs: []
planning_base_branch: design/degod-tasks-2116
merge_target_branch: design/degod-tasks-2116
branch_strategy: Planning artifacts for this mission were generated on design/degod-tasks-2116. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/degod-tasks-2116 unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
phase: Phase 3 - Pure cores
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2991422"
history:
- at: '2026-07-01T15:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_transition_core.py
create_intent:
- src/specify_cli/cli/commands/agent/tasks_transition_core.py
- tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_transition_core.py
- tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – move_task transition decision core (pure)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Lift `move_task`'s transition decision into **one pure function** reproducing exact behavior, wired so the core genuinely **drives** behavior (not a shadow call).

- `decide_transition(TransitionRequest)->TransitionOutcome` in `tasks_transition_core.py` — no I/O.
- `--cov-branch`-gated unit tests cover every branch (from the WP01 harness), fail on reverted extraction (NFR-002).
- Wiring **deletes** the inline decision block; a fake-core sentinel test proves the core's return value flips observable behavior; golden byte-identical.

## Context & Constraints

- Read `data-model.md` (§`TransitionDecision`), `contracts/ports-and-cores.md` (`decide_transition`), `research.md` (D4, D7).
- **FR-004 — reproduce, do not unify**: reproduce move_task's exact behavior incl. the coord skip arm; do NOT reconcile the skip-vs-refuse divergence (#2300, deferred).
- **Anti-shadow-code (squad MUST)**: "grep-for-callers" is insufficient — a result-discarding call passes it while old inline logic still runs. T016 **deletes** the inline block; T017 proves the core drives behavior via a sentinel.
- Nested state machine: arbiter-override, FR-008a planning-artifact arm, for_review→in_progress force, review-currency, coord skip arm → all in the pure core; orchestrator executes the outcome via ports.
- **C-003**: selector/handle ambiguity raises `MissionSelectorAmbiguous` — never silent-fallback.
- **C-011 / D7**: the RED-first artifact is the per-core unit test.
- **Ownership/leeway**: own the new core + test. Editing `move_task` (delete + wire) is a documented leeway edit to `tasks.py` (owned by WP09); execution stays inline (WP06 thins it).

## Branch Strategy

- **Planning base branch**: `design/degod-tasks-2116`
- **Merge target branch**: `design/degod-tasks-2116`

## Subtasks & Detailed Guidance

### T014 — Failing-first per-branch unit test (RED on base)
`test_tasks_transition_core.py` enumerating `TransitionOutcome` branches (Emit/SkipExit0/RefuseExit1 + each guard) **from the WP01 golden cases**, `--cov-branch` on the module. RED against base.

### T015 — Implement `decide_transition` (pure)
Implement in `tasks_transition_core.py`. Pure: no I/O. Encode the coord skip arm as `skip_primary`/`SkipExit0`; carry guard failures (agent-ownership, rejected-verdict, protected-branch-without-skip, feedback-required, done-override) as `RefuseExit1`.

### T016 — Delete inline block + wire
**Delete** `move_task`'s inline decision block and route through `decide_transition`. The old logic is gone, not shadowed. Golden byte-identical.

### T017 — Fake-core sentinel test
Inject a fake core / sentinel outcome and assert the command's observable result **follows the sentinel** (proves the core drives execution, not merely called). Run golden + per-core test; ruff+mypy clean.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q --cov-branch`

## Risks & Mitigations

- **Shadow dead code**: guarded by T016 (delete) + T017 (sentinel). **Silent drift**: any change to skip-vs-refuse behavior breaks pure parity — reproduce exactly.

## Review Guidance

- Confirm the old inline block is **deleted** (not left beside a discarded call), the sentinel test proves drive, `--cov-branch` meets threshold, golden byte-identical.

## Activity Log

- 2026-07-01T15:16:35Z – system – Prompt created.
- 2026-07-01T19:51:58Z – claude:opus:randy-reducer:implementer – shell_pid=2835419 – Assigned agent via action command
- 2026-07-01T20:43:27Z – claude:opus:randy-reducer:implementer – shell_pid=2835419 – decide_transition pure core: 25 decision branches covered (--cov-branch 99%, only 2 defensive-unreachable partials), inline block DELETED (8 fragments gone from tasks.py) + wired via two-pass at tasks.py:1319 + sentinel tests prove core drives exit-code AND skip json, golden 42 byte-identical, WP02 ports 19 incl FR-010 hazard green, strict mypy clean 0 suppressions, ruff clean.
- 2026-07-01T20:44:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=2915889 – Started review via action command
- 2026-07-01T20:54:39Z – user – shell_pid=2915889 – Moved to planned
- 2026-07-01T20:55:37Z – claude:opus:randy-reducer:implementer – shell_pid=2938278 – Started implementation via action command
- 2026-07-01T21:26:32Z – claude:opus:randy-reducer:implementer – shell_pid=2938278 – Cycle 2: override/arbiter persists fire at OLD guard positions (partial-write-on-refusal preserved); red-first regression test pins it; core stays pure. Golden 42 byte-identical, WP02 19 green, strict mypy clean.
- 2026-07-01T21:27:48Z – claude:opus:reviewer-renata:reviewer – shell_pid=2991422 – Started review via action command
- 2026-07-01T21:35:48Z – user – shell_pid=2991422 – Cycle-2 fix verified. Partial-write-on-refusal reproduced at OLD guard positions: override_persist_signal fires when guards[:4] (pre-rejected-verdict) clear + _authorize_review_override; arbiter_persist_signal fires when guards[:10] (thru done-ancestry) clear + is_arbiter_override (=old arbiter_forward). NO double-persist: each persist call site appears exactly ONCE at the early position, post-Emit blocks removed. Signals PURE (guard eval on frozen req, no I/O). RED-first bites: reverting src -> frontmatter absent/FAIL, with fix PASS (non-tautological). Golden 42 byte-identical, ports 19 green, core cov-branch 99%, agent dir 860 passed/2 xfailed incl force_done_blocked_by_rejected_verdict, mypy --strict clean on core+owned-test+wired tasks.py, ruff clean, zero new noqa/type-ignore. CHECK-3: test_tasks.py 4 mypy-strict errors are PRE-EXISTING on lane base (shifted +104 = added-block size, zero new); CI runs mypy only over src/ not tests/, so non-gating; regression test placement appropriate (CLI-integration sibling of TestSkipReviewArtifactCheck). Accept + recommend DIR-013 follow-up for pre-existing test debt (non-blocking).
