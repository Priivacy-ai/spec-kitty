---
work_package_id: WP05
title: Route workspace/context + context/resolver + task_utils
dependencies:
- WP01
- WP04
requirement_refs:
- FR-005
- FR-006
- FR-009
tracker_refs: []
planning_base_branch: design/coord-authority-remediation-2160
merge_target_branch: design/coord-authority-remediation-2160
branch_strategy: Planning artifacts for this mission were generated on design/coord-authority-remediation-2160. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-authority-remediation-2160 unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
phase: Phase 2 - Routing
assignee: ''
shell_pid: ''
agent: claude
history:
- at: '2026-06-26T18:29:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/workspace/
create_intent:
- tests/integration/test_coord_loop_workspace.py
execution_mode: code_change
owned_files:
- src/specify_cli/workspace/context.py
- src/specify_cli/context/resolver.py
- src/specify_cli/task_utils/support.py
- tests/integration/test_coord_loop_workspace.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Route workspace/context + context/resolver + task_utils

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Route the workspace/context-resolution PRIMARY-kind reads (`tasks/`, `lanes.json`,
WP-frontmatter) onto the seam; split the mixed read; remove the pins.

Done when, on the WP01 coord fixture: `build_normalized_wp_index`, `resolve_workspace_for_wp`/
`resolve_feature_worktree`, `context/resolver.py` MissionContext build, and
`task_utils.locate_work_package` read **primary**; status legs stay **coord**; the
`:714` "WP not found" message path still resolves; pins removed; gates green; RED-first tests pass.

## Context & Constraints

- Spec FR-005, FR-006, FR-009. Sites (verify live): `workspace/context.py:666`
  (`build_normalized_wp_index`, tasks/), `:752/:790/:853` (`resolve_workspace_for_wp`/
  `resolve_feature_worktree`, lanes.json=LANE_STATE), `:470` (`resolve_active_wp_for_branch`
  — **MIXED**: WP-frontmatter PRIMARY + `get_all_wp_lanes` events COORD), `:714` (not-found
  message); `context/resolver.py:163`; `task_utils/support.py:309` (`locate_work_package`).
- **C-007:** do NOT consolidate the coord-aware twin `resolve_feature_dir_for_slug`; only
  re-point its PRIMARY-kind call sites here.
- `context/resolver.py:163` should adopt the `implement.py:1018` primary-anchor pattern
  (resolve, fall back to canonical primary if meta-less) rather than a bare seam swap.
- **FR-009:** remove the workspace/context pins from the WP02-owned ratchet file this commit.
- C-009: do not touch `merge/`, `lanes/`, `core/worktree_topology`.

## Branch Strategy

- **Strategy**: already-confirmed
- **Planning base branch**: design/coord-authority-remediation-2160
- **Merge target branch**: design/coord-authority-remediation-2160

## Subtasks & Detailed Guidance

### Subtask T021 – Route `build_normalized_wp_index` + lane resolvers
- `:666` tasks/ → `resolve_planning_read_dir(...,WORK_PACKAGE_TASK)`. `:752/:790/:853`
  lanes.json → seam (`kind=LANE_STATE`). Confirm `require_lanes_json`/`resolve_lanes_dir`
  fail-closed semantics preserved.

### Subtask T022 – Split `resolve_active_wp_for_branch:470` mixed read
- WP-frontmatter read → seam; `get_all_wp_lanes` status-events read → keep coord-aware.

### Subtask T023 – Route context/resolver + task_utils
- `context/resolver.py:163`: adopt the primary-anchor pattern. `task_utils/support.py:309`
  (`locate_work_package`): route the tasks/ read to the seam.

### Subtask T024 – Remove the workspace/context pins (same commit)
- Delete the corresponding `_DIR_READ_KNOWN_RESIDUALS` entries (out-of-map edit to WP02's file).

### Subtask T025 – RED-first per-site tests (both legs)
- On the WP01 fixture, assert primary tasks/lanes reads + coord status reads; assert the
  `:714` not-found path still resolves. File: `test_coord_loop_workspace.py`. Prove RED pre-fix.

## Test Strategy

`PWHEADLESS=1 pytest tests/integration/test_coord_loop_workspace.py tests/architectural/test_gate_read_literal_ban.py -q`.

## Risks & Mitigations

- **Twin-resolver consolidation creep** (C-007) → out of scope; only re-point call sites.
- **lanes.json fail-closed semantics** lost on route → keep the error path; assert it.

## Review Guidance

- Confirm no resolver consolidation; only call-site re-points.
- Confirm the mixed read at `:470` is split per-leg.
- Confirm RED-first evidence.

## Activity Log

- 2026-06-26T18:29:45Z – system – Prompt created.
- 2026-06-26T21:28:01Z – user – flat
- 2026-06-26T21:28:03Z – user – flat; route workspace/context cluster
- 2026-06-27T03:15:38Z – claude – workspace/context routed + #2064 re-pin
- 2026-06-27T03:19:08Z – user – renata review done
- 2026-06-27T03:19:10Z – user – Approved by reviewer-renata (flat): kind-truth routing (lanes.json=LANE_STATE), no status-leg swap (#2155), C-007 twin un-consolidated, fail-closed preserved, RED-first genuine, 4 pins dropped. #2064 re-pin adjudicated LEGITIMATE stronger-contract (sibling preserved, test-only). 31 passed.
