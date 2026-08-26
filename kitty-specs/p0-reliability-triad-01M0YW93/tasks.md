# Tasks: 3.2.6 P0 reliability triad

**Mission**: p0-reliability-triad-01M0YW93 | **Branch**: `fix/p0-reliability-triad`
**Input**: spec.md, plan.md, research.md (adversarial dispositions), contracts/behavioral-contracts.md

Three independent, file-disjoint work packages — one per P0. No inter-WP dependencies; all three parallelizable. Red-first per WP.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | RED: pointer-charter + authored-empty fixture; drive `upgrade` CLI; assert activations land in `charter.yaml`, registry non-empty | WP01 | [P] |
| T002 | Route `_provision_missing_mission_type_activations` through pointer-aware `charter.compiler.provision_mission_type_activations` | WP01 | |
| T003 | Rewrite `_mission_type_activation_provisioning_pending` on the resolved write target; non-crashing dangling-pointer contract | WP01 | |
| T004 | Preserve authored-empty-`[]`/idempotency; update stale init/upgrade divergence docstring; ruff/mypy clean | WP01 | |
| T005 | RED: `_stale_remediation` planning-lane names `spec-kitty agent status materialize` | WP02 | [P] |
| T006 | Edit `_stale_remediation` to name the `materialize` + `git add` remedy; introduce NO `status.json` merge driver | WP02 | |
| T007 | Lockstep-update remediation assertions in `test_stale_check.py` + `test_merge.py`; confirm T013 arch guard green; record #3531 same-schema scope note | WP02 | |
| T008 | RED: retry over a leftover worktree missing the planning SHA re-enters self-heal; reconcile #1832/#1833 invariant with rationale | WP03 | [P] |
| T009 | exists-branch decision tree in `ensure_workspace_materialized` (ancestry-correct → no-op; stale → dedicated idempotent self-heal, main-repo context) | WP03 | |
| T010 | Atomic fresh-path allocation: `git worktree remove` on planning-commit-merge raise + RED atomicity test | WP03 | |
| T011 | POST-materialize ancestry predicate (merged tip), coupled to self-heal (route back on failure; hard-refuse only if unrecoverable) | WP03 | |
| T012 | Place the ancestry seam so BOTH the CLI (`workflow.py`) and `orchestrator_api/commands.py` claim paths cross it (C-005 parity) | WP03 | |
| T013 | Focused unit test for ancestry refusal at the seam (FR-007) + integration backup; land FR-005+FR-007 together; ruff/mypy/complexity ≤15 | WP03 | |

## Work Packages

### WP01 — Upgrade heals pointer-based charter activations (#3282)

- **Goal**: `spec-kitty upgrade` provisions mission-type activations to the *effective* authority (pointer projects → `charter.yaml`), so mission creation works immediately.
- **Priority**: P1 (release-blocking). **Requirements**: FR-001, FR-002; NFR-003; C-004.
- **Independent test**: pointer-charter fixture → `upgrade` CLI → `PackContext.from_config(project).activated_mission_types` non-empty AND key in `charter.yaml`.
- **Subtasks**: T001, T002, T003, T004. **Est. prompt**: ~300 lines.
- **Prompt**: `tasks/WP01-upgrade-pointer-charter-activation.md`

### WP02 — Merge stale-lane halt names a reachable remedy (#3579)

- **Goal**: the stale-lane halt remediation names `spec-kitty agent status materialize` instead of a raw-`git` dead end; no `status.json` merge driver.
- **Priority**: P1 (release-blocking). **Requirements**: FR-003, FR-004; C-002.
- **Independent test**: `check_lane_staleness()` → `_stale_remediation()` names the materialize remedy for a planning lane.
- **Subtasks**: T005, T006, T007. **Est. prompt**: ~250 lines.
- **Prompt**: `tasks/WP02-merge-stale-lane-remediation.md`

### WP03 — Lane-allocation retry + post-materialize ancestry gate (#3281)

- **Goal**: retry re-enters the idempotent self-heal; fresh-path allocation is atomic; a POST-materialize ancestry check (both claim paths) refuses claiming a WP against a lane missing its dependencies — without deadlocking approved deps.
- **Priority**: P1 (release-blocking; heaviest). **Requirements**: FR-005, FR-006, FR-007; NFR-002; C-003, C-005, C-006.
- **Coordinate**: robertDouglass (assignee), #3432 (compute, closed), #2570 friction #1 (allocator serialization).
- **Independent test**: leftover-worktree retry re-enters self-heal; conflicting planning SHA leaves no worktree; ancestry refusal at the post-materialize seam.
- **Subtasks**: T008, T009, T010, T011, T012, T013. **Est. prompt**: ~480 lines.
- **Prompt**: `tasks/WP03-lane-allocation-retry-ancestry.md`

## Parallelization

All three WPs run concurrently (disjoint owned files; no dependencies). MVP / first-to-land recommendation: **WP01** (cleanest, most isolated). WP03 is the heaviest and carries the coordination load.
