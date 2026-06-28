---
work_package_id: WP03
title: Route tasks.py loop reads to the seam
dependencies:
- WP01
- WP02
requirement_refs:
- FR-001
- FR-003
- FR-006
- FR-009
tracker_refs: []
planning_base_branch: design/coord-authority-remediation-2160
merge_target_branch: design/coord-authority-remediation-2160
branch_strategy: Planning artifacts for this mission were generated on design/coord-authority-remediation-2160. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-authority-remediation-2160 unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Routing
assignee: ''
shell_pid: ''
agent: claude
history:
- at: '2026-06-26T18:29:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/integration/test_coord_loop_tasks.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- tests/integration/test_coord_loop_tasks.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Route tasks.py loop reads to the seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Route the PRIMARY-kind `tasks/` reads in `cli/commands/agent/tasks.py` onto
`resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`, splitting mixed reads per-leg, and
remove the corresponding `_DIR_READ_KNOWN_RESIDUALS` pins in the same commit.

Done when, on the WP01 coord fixture: `tasks status` and `tasks list` read `tasks/` from
**primary** while their status-events reads stay **coord**; `finalize_tasks` and
`_map_requirements_feature_dir` resolve `tasks/` primary; the in-loop `build_dependency_graph`
caller passes the primary planning dir; the tasks.py pins are removed; the dir-read gate
is green; per-site RED-first tests pass (and were proven red pre-fix).

## Context & Constraints

- Spec FR-001, FR-003, FR-006, FR-009. Sites (verify line numbers live): `tasks.py:247/249`
  (`_map_requirements_feature_dir`), `:2108` (`list_tasks`, **inline shape**), `:2276`
  (`finalize_tasks` leg), `:2966/:2983` (`status` — **MIXED**: tasks/ PRIMARY + events COORD).
- **C-001 mixed-read discipline:** split per-leg — route only the `tasks/` leg; the status
  events read keeps the coord-aware resolver. Never a one-line `feature_dir` swap.
- **T012 — do NOT change `build_dependency_graph`'s signature** (shared 10-caller seam);
  route by passing the primary planning dir at the tasks.py caller only.
- **FR-009:** remove the tasks.py pins from `tests/architectural/test_gate_read_literal_ban.py`
  in this same commit (out-of-map edit; WP02 owns the file; justified: "route + unpin tasks.py").
- C-009: do not touch `merge/`, `lanes/`, `core/worktree_topology`.

## Branch Strategy

- **Strategy**: already-confirmed
- **Planning base branch**: design/coord-authority-remediation-2160
- **Merge target branch**: design/coord-authority-remediation-2160

## Subtasks & Detailed Guidance

### Subtask T009 – Route `tasks status` (mixed-read split)
- Split: `tasks_dir = resolve_planning_read_dir(repo_root, slug, kind=WORK_PACKAGE_TASK)`;
  keep the `status.events`/`status.json` read on its existing coord-aware seam. Verify the
  WP-title read uses the primary `tasks/`.

### Subtask T010 – Route `list_tasks` + `_map_requirements_feature_dir`
- `list_tasks:2108` is the inline shape — route to the seam; keep its status leg coord.
- `_map_requirements_feature_dir:247/249` — route the tasks-read leg to primary.

### Subtask T011 – Route `finalize_tasks` dir-read leg
- Route the `tasks/`/`tasks.md` read to the seam; keep `bootstrap_canonical_state` (STATUS) coord.

### Subtask T012 – Route the in-loop `build_dependency_graph` caller
- Pass the seam-resolved primary planning dir to `build_dependency_graph(...)` at the tasks.py
  caller. **Do not** alter the function signature (WP06 handles its own caller; out-of-loop
  callers must stay untouched).

### Subtask T013 – Remove tasks.py pins (same commit)
- Delete the tasks.py entries from `_DIR_READ_KNOWN_RESIDUALS`. The gate must stay green
  (routed → no longer a residual). Out-of-map edit to WP02's file; one-line rationale.

### Subtask T014 – RED-first per-site tests (both legs)
- For each routed site, a test on the WP01 fixture asserting tasks-from-PRIMARY AND
  status-from-COORD. Prove each RED against pre-fix code (document the pre-fix failure inline),
  GREEN after. Add to `tests/integration/test_coord_loop_tasks.py`.

## Test Strategy

`PWHEADLESS=1 pytest tests/integration/test_coord_loop_tasks.py tests/architectural/test_gate_read_literal_ban.py -q`.
RED-first: stash the source change, confirm the new tests fail, restore, confirm green.

## Risks & Mitigations

- **Breaking the status leg** when splitting a mixed read → #2155 re-opener. Mitigation: the
  dual-leg assertion (status-from-COORD) catches it.
- **Vacuous pin removal** (removing the pin without routing) → FR-009 violation. Mitigation:
  per-site RED-first test ties the unpin to a real route.

## Review Guidance

- Confirm each mixed-read is split, not swapped.
- Confirm `build_dependency_graph` signature unchanged.
- Confirm the RED-first proof is documented.

## Activity Log

- 2026-06-26T18:29:45Z – system – Prompt created.
- 2026-06-26T20:16:20Z – user – flat
- 2026-06-26T20:16:22Z – user – flat; route tasks.py
- 2026-06-26T20:56:55Z – claude – tasks.py routed (ff2c74067): 5 per-leg splits, build_dependency_graph sig unchanged, 3 pins dropped; 22 passed + 69 broad sanity
- 2026-06-26T21:00:31Z – user – renata review done
- 2026-06-26T21:00:33Z – user – Approved by reviewer-renata (flat): tasks.py 5 reads routed to seam, per-leg mixed splits keep STATUS coord (no #2155), build_dependency_graph sig unchanged, RED-first genuine (status-swap fails), pins dropped, 22/22. 2 LOW non-blocking (docstring 'never raises'; finalize status-leg coverage) → close-out polish.
