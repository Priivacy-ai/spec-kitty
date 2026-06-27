---
work_package_id: WP02
title: Lane A — Merge cluster routing
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-006
- FR-008
- FR-011
- NFR-001
tracker_refs:
- '#2185'
planning_base_branch: mission/coord-read-residuals-2185-2186
merge_target_branch: mission/coord-read-residuals-2185-2186
branch_strategy: Planning artifacts for this mission were generated on mission/coord-read-residuals-2185-2186. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/coord-read-residuals-2185-2186 unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
- T016
phase: Phase 2 - Lane A (post C-SEQ rebase)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1063526"
history:
- at: '2026-06-27T11:00:00Z'
  actor: system
  action: Prompt regenerated via /spec-kitty.tasks (canonical regeneration from corrected spec/plan)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
create_intent:
- tests/integration/test_merge_cluster_coord_read.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/merge/forecast.py
- src/specify_cli/merge/executor.py
- src/specify_cli/merge/resolve.py
- src/specify_cli/merge/done_bookkeeping.py
- src/specify_cli/cli/commands/merge.py
- tests/integration/test_merge_cluster_coord_read.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Lane A — Merge cluster routing

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer) before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

- Route the `merge/` + `cli/commands/merge.py` PRIMARY reads by their real kind; per-leg split where a single resolved dir feeds both a PRIMARY and a STATUS leg. **No merge-cluster pins exist to drain** (the ratchet vocabulary is blind to `lanes.json`/`meta.json` reads) — regression coverage is the FR-007 lanes.json call-shape arm (WP01) + the FR-009 divergent fixture (WP04), NOT a pin drain.

## Context & Constraints

- Spec [spec.md](../spec.md) (US1; FR-001/002/003/006/008/011; Lane A table), [plan.md](../plan.md) IC-02.
- **C-SEQ FIRST**: rebase onto post-implement-loop-merge `main`; re-resolve all line citations; run the T010 preflight (asserts the single #2187 pin present; records the honest-scope note).
- **C-001**: STATUS legs stay coord-aware. **C-002**: consume the resolver; never edit its internals or remove `candidate_feature_dir_for_mission`.
- **C-009-mirror**: `merge.py` line ranges differ from the sibling's `_mark_wp_merged_done`; this WP drains no pins (no merge-cluster pin exists).

## Branch Strategy
- **Planning base branch**: `mission/coord-read-residuals-2185-2186`
- **Merge target branch**: `mission/coord-read-residuals-2185-2186`

## Subtasks & Detailed Guidance

### T010 – Preflight + honest-scope note
- **FR-011 (narrowed):** assert `_DIR_READ_KNOWN_RESIDUALS` on the rebased base contains the single **#2187** pin (`agent_utils/status.py::show_kanban_status`) before WP03/T021 drains it. **FR-006 (honest scope):** record that the ratchet's literal vocabulary (`tasks`/`.md`) is structurally blind to `lanes.json` (LANE_STATE) and `meta.json` function-call reads — so the **merge/lanes/core #2185 cluster has ZERO pins, and their absence is EXPECTED, never a STOP.** Do NOT halt Lane A on missing merge/lanes/core pins (that would mis-read a permanent vocabulary limit as a landing-timing failure). The sibling's whole-`src` scan *scope* is real but does NOT make these reads literal-visible. **Arm-scope asymmetry (state honestly):** the merge-cluster **identity** reads (`merge/resolve.py:103`, `merge/executor.py:981`/`:1003`) are ROUTED but their regression coverage is the **FR-009 revert-fails fixture (behavioral), NOT the FR-007 identity arm** (which does not scan `merge/`).

### T011 – `merge/forecast.py:153`+`:159`
- Route the `require_lanes_json` read (LANE_STATE, `:153`) and the review-artifact `tasks/` preflight (WORK_PACKAGE_TASK, `:159`) onto `resolve_planning_read_dir(kind=...)`.

### T012 – `merge/executor.py` — route `:976` legs DIRECTLY, per-leg
- The `:976` legs (`feature_dir = candidate_…`) live in `_run_lane_based_merge` (def `:947`), a **DIFFERENT function** from the `:887` PRIMARY anchor in `_run_lane_based_merge_locked` (def `:866`) — verified on merged main. **Do NOT "thread `:887` through."** Route each leg directly: `:997` `require_lanes_json(feature_dir)` → LANE_STATE seam; `:981`/`:1003` `resolve_mission_identity(feature_dir)` → META (`kind=PRIMARY_METADATA`). Keep the `run.feature_dir` STATUS leg(s) (`status_feature_dir` at `:503`/`:560`) coord-aware.

### T013 – `merge/resolve.py:98`
- Route the `resolve_mission_identity` (meta, PRIMARY_METADATA) read; **leave `:63`** (handle→dir-name canonicalization at the no-silent-fallback boundary) on `candidate_`. Do not reintroduce the silent `main` target-branch fallback (#2139 neighborhood).

### T014 – `merge/done_bookkeeping.py:237`
- Route the WP-path leg via `kind=WORK_PACKAGE_TASK`; **remove the misleading "do not use the read-path resolver" comment** (FR-003); keep the status-transactional legs (`:248-249`) on the meta-bearing **primary** dir (not coord-ified).

### T015 – `cli/commands/merge.py:269`
- Verify the `--abort` coord-teardown semantics first, then route the `_load_meta` (PRIMARY_METADATA) read.

### T016 – RED-first tests
- Per-site tests (both legs) on the divergent fixture (WP01/T001), in `tests/integration/test_merge_cluster_coord_read.py`. Reverting a routed read to coord-aware must FAIL on a **returned domain value** (the forecast WP set / resolved identity), NOT a resolved-path equality. **NFR-004 (integration-over-stubs):** a unit stub handing in a primary dir directly does NOT satisfy.

## Test Strategy
- RED-first per-site; the WP04 integration test is the cross-cutting proof. `ruff`+`mypy` clean; complexity ≤ 15.

## Definition of Done

- C-SEQ rebase done; citations re-resolved; T010 preflight green (#2187 pin present) with the honest-scope note recorded.
- All five merge-cluster sites routed by real kind; mixed sites split per-leg with STATUS legs untouched.
- `done_bookkeeping` misleading comment removed; status-transactional legs on primary.
- RED-first merge tests GREEN after routing, FAIL on revert (returned domain value).
- `ruff` + `mypy` clean; touched functions ≤ 15.

## Risks & Mitigations
- Over-routing a STATUS leg (NFR-001) → split per-leg. Don't reintroduce #2139's silent `main` target-branch fallback in this neighborhood.

## Review Guidance
- `reviewer-renata`: confirm STATUS legs untouched; executor `:976` legs routed DIRECTLY per-leg (NOT threaded from `:887`); no pin drained here (none exists); the revert-fails proof is on a returned domain value.

## Activity Log
- 2026-06-27T11:00:00Z – system – Prompt regenerated (canonical /spec-kitty.tasks from corrected spec/plan).
- 2026-06-27T10:14:32Z – claude:opus:python-pedro:implementer – shell_pid=994844 – Assigned agent via action command
- 2026-06-27T10:42:13Z – claude:opus:python-pedro:implementer – shell_pid=994844 – WP02 Lane A merge cluster: 5 files routed (forecast/executor per-leg/resolve/done_bookkeeping/merge.py) + 7 revert-fails tests; lanes.json arm passes on merge/; 67 gate + 624 merge/missions pass
- 2026-06-27T10:42:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=1063526 – Started review via action command
- 2026-06-27T10:54:05Z – user – shell_pid=1063526 – Review passed (reviewer-renata). WRITE-SIDE C-001/#2155 VERDICT: PASS — done_bookkeeping status-transactional legs receive the PRIMARY meta-bearing dir, but the STATUS write TARGET is internally re-resolved via _resolve_write_target -> resolve_placement_only(STATUS_STATE), staying topology-routed to the coordination branch (explicitly MUST-NOT-be-flipped, untouched by WP02). The passed dir only anchors coord-ref derivation; PRIMARY is the correct anchor post-#2106 (coord husk lacks meta). NO status write moved to PRIMARY. executor STATUS legs (run.feature_dir/status_feature_dir) kept coord-aware; only identity(PRIMARY_METADATA)+lanes(LANE_STATE) routed per-leg; :887 anchor NOT threaded. resolve.py:63 KEEP on candidate_; done_bookkeeping misleading comment removed (FR-003). RED-first proven (spot-checked 2). ruff/mypy/C901 clean; 564 merge + 7 fixture tests green; no out-of-scope src (C-009). NOTE(non-blocking): FR-007 lanes call-shape arm has merge/ in scope + self-tests but no production scan over real merge/; live teeth = WP02 fixture (proven), consistent with T010 honest-scope note.
