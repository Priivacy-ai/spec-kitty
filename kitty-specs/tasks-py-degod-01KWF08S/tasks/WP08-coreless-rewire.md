---
work_package_id: WP08
title: Coreless rewire — mark_status + finalize_tasks + read folds
dependencies:
- WP07
requirement_refs:
- FR-007
- FR-010
- NFR-004
tracker_refs: []
planning_base_branch: design/degod-tasks-2116
merge_target_branch: design/degod-tasks-2116
branch_strategy: Planning artifacts for this mission were generated on design/degod-tasks-2116. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/degod-tasks-2116 unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
phase: Phase 4 - Body thinning
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3676835"
history:
- at: '2026-07-01T15:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: tests/specify_cli/cli/commands/agent/test_tasks_coreless_orchestration.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_coreless_orchestration.py
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/agent/test_tasks_coreless_orchestration.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – Coreless rewire (mark_status + finalize_tasks + read folds)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Thin the two **coreless** bodies via ports + existing seam modules (no borrowed core), migrate the remaining kind-blind reads, and add a **structural non-import gate** that guards the deferred-unification boundary. (Coreless half of the split WP07.)

- `mark_status` + `finalize_tasks` → ≤150 LOC orchestrators via ports + `tasks_finalize_validation`/parsing seams.
- `finalize_tasks:2373` + `list_dependents:3568` reads migrated to `resolve_planning_read_dir(kind=…)` (pinned kinds per WP02 proof), byte-identical.
- An AST gate asserts `tasks_transition_core` is NOT reachable from `mark_status`/`finalize_tasks`; golden byte-identical.

## Context & Constraints

- Read `plan.md` (IC-04, IC-05), `research.md` (D8, D10), `spec.md` (FR-007, FR-010).
- **Coreless thinning (FR-007)**: `mark_status`/`finalize_tasks` carry **no new decision core**. Thin via ports + existing seams. **Do NOT borrow `move_task`'s core** — that is the deferred cross-command unification (#2300). The squad flagged that behavior-parity alone (golden) does NOT catch an illicit import (an implementer could route through the transition core then special-case the exit code back to 1) — so T036 adds a **structural** guard.
- **FR-010**: migrate `finalize_tasks:2373` + `list_dependents:3568` with the kinds pinned by the WP02 proof. Confirm `finalize_tasks:2373` (the read that currently slips the gate) is covered. Byte-identical.
- **NFR-004**: each body ≤150 LOC; glue helpers ≤150 LOC/CC≤15 (WP09 LOC gate).
- **Ownership/leeway**: own `test_tasks_coreless_orchestration.py`; the two body edits + read-fold sites are documented **leeway edits** to `tasks.py` (owned by WP09).

## Branch Strategy

- **Planning base branch**: `design/degod-tasks-2116`
- **Merge target branch**: `design/degod-tasks-2116`

## Subtasks & Detailed Guidance

### T033 — Thin `mark_status` (coreless)
Thin via ports + existing `tasks_finalize_validation`/parsing seams. ≤150 LOC. No borrowed core.

### T034 — Thin `finalize_tasks` (coreless)
Thin via ports + existing seams. ≤150 LOC.

### T035 — FR-010 read folds (pinned kinds)
Migrate `finalize_tasks:2373` + `list_dependents:3568` kind-blind reads → `resolve_planning_read_dir(kind=…)` via `FsReader`, using the kinds pinned by the WP02 proof. Byte-identical.

### T036 — Structural non-import AST gate + prove
Add a `tests/architectural/`-style AST assertion that `tasks_transition_core` is NOT imported/reachable from the `mark_status`/`finalize_tasks` code paths (guards the #2300 boundary structurally, not just behaviorally). Golden byte-identical for both commands; `test_tasks_coreless_orchestration.py` green; ruff + mypy clean.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_coreless_orchestration.py tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q`

## Risks & Mitigations

- **Illicit unification**: borrowing move_task's core to hit ≤150 LOC changes refuse-exit-1 behavior (#2300) — the T036 AST gate catches it structurally.
- **FR-010 dir shift** on the two sites → revert and escalate.

## Out-of-map edits

- `src/specify_cli/cli/commands/agent/tasks.py` (`mark_status`, `finalize_tasks`, `list_dependents` read sites) — documented leeway; `tasks.py` owned by WP09. Strictly-linear chain → no parallel collision.

## Review Guidance

- Confirm both bodies ≤150 LOC via existing seams (no borrowed core), the non-import AST gate present + green, FR-010 folds byte-identical, golden byte-identical.

## Activity Log

- 2026-07-01T15:16:35Z – system – Prompt created.
- 2026-07-02T04:18:44Z – claude:opus:randy-reducer:implementer – shell_pid=3595886 – Assigned agent via action command
- 2026-07-02T04:56:29Z – claude:opus:randy-reducer:implementer – shell_pid=3595886 – mark_status 39 (orchestrator 47) + finalize_tasks 25 (orchestrator 35) LOC coreless via existing tasks_finalize_validation/parsing seams + WP02 FsReader/commit_artifact ports (helpers <=61 LOC, CC<=15); NO borrowed transition core. FR-010: finalize guard->WORK_PACKAGE_TASK via ports.fs, list_dependents guard->WORK_PACKAGE_TASK (consolidated, redundant reassignment removed) — both byte-identical per WP02 T013 proof + pre30_guard_wiring green. Non-import AST gate (with non-vacuous move_task control) green; golden 42 + refuse-exit-1 (T005) intact; strict mypy (src+test together) clean; ruff clean. Census drain for WP09: coord-authority WRITE census 10->9 (list_dependents drained; gate was ALREADY red pre-WP08 at 10<floor12 from cumulative-merge line drift + 5 stale allowlist entries) — floor-lower is WP09 shrink-only territory, did NOT raise/lower it.
- 2026-07-02T04:57:56Z – claude:opus:reviewer-renata:reviewer – shell_pid=3676835 – Started review via action command
- 2026-07-02T05:05:17Z – user – shell_pid=3676835 – APPROVED. Coreless invariant held: mark_status (39 LOC body/47 orch) + finalize_tasks (25/35) thinned via existing tasks_finalize_validation/parsing seams + WP02 ports (helpers <=61 LOC, ruff C901 clean), NO borrowed decide_transition/tasks_transition_core core. T036 AST gate is REAL + non-tautological: reachability-closure scan asserts zero core symbols reachable from mark_status/finalize_tasks + local-import smuggle check + non-vacuous core_syms assert + positive control proving move_task's path DOES reach the core (would go red if mark_status routed through decide_transition). refuse-exit-1 (T005) preserved not reconciled (#2300 deferred). FR-010 folds byte-identical: finalize guard-only read + list_dependents:3568 migrated resolve_feature_dir_for_mission->resolve_planning_read_dir(WORK_PACKAGE_TASK); genuinely guard-only (var fed only check_pre30_layout); pre30_guard_wiring 14/14 green; move_task:1138 UNTOUCHED (still coord-husk, both hazard tests green). Census shrink GENUINE (10->9: list_dependents fold drained a write-classified resolve_feature_dir_for_mission, not census-masking). test_resolution_authority_gates RED is PRE-EXISTING: parent commit 7048965b6 already fails identical 4 tests (census 10<floor12 + same 5 stale entries) from cumulative WP01-WP07 line drift; WP08 did NOT touch floors/allowlist (WP09 shrink-only territory). mypy --strict clean on src+test together, zero type:ignore/noqa added, ruff clean. Agent suite 917 passed/2 xfailed/0 fail; coreless test 9 green.
