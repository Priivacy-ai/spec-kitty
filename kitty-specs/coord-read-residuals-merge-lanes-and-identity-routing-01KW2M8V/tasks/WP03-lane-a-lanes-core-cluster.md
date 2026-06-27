---
work_package_id: WP03
title: Lane A — Lanes/core cluster routing + recovery extraction + status.py both legs (#2187/#2186)
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-008
- NFR-001
tracker_refs:
- '#2185'
- '#2186'
- '#2187'
planning_base_branch: mission/coord-read-residuals-2185-2186
merge_target_branch: mission/coord-read-residuals-2185-2186
branch_strategy: Planning artifacts for this mission were generated on mission/coord-read-residuals-2185-2186. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/coord-read-residuals-2185-2186 unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
phase: Phase 2 - Lane A (post C-SEQ rebase)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1145629"
history:
- at: '2026-06-27T11:00:00Z'
  actor: system
  action: Prompt regenerated via /spec-kitty.tasks (canonical regeneration from corrected spec/plan)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent:
- tests/integration/test_lanes_core_coord_read.py
- tests/specify_cli/lanes/test_recovery_helpers.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/lanes/merge.py
- src/specify_cli/lanes/recovery.py
- src/specify_cli/lanes/worktree_allocator.py
- src/specify_cli/core/worktree_topology.py
- src/specify_cli/agent_utils/status.py
- tests/integration/test_lanes_core_coord_read.py
- tests/specify_cli/lanes/test_recovery_helpers.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Lane A — Lanes/core cluster routing + recovery extraction + status.py

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer) before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

- Route the `lanes/` + `core/worktree_topology` PRIMARY reads; extract helpers out of the over-complex `scan_recovery_state` and **drop its `# noqa: C901`**; keep the `recovery.py:664` STATUS-write leg coord-aware.
- Route **both** legs of `agent_utils/status.py::show_kanban_status`: the #2187 `:126` `tasks/` glob → `resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)` (and **drain the single #2187 `_DIR_READ_KNOWN_RESIDUALS` pin** — the sole ratchet-visible Lane A drain), and the #2186 `:132` `resolve_mission_identity` → `kind=PRIMARY_METADATA`. The lanes/core sites themselves have **no pins** (vocabulary-blind).

> **Ownership note (Directive 003):** `agent_utils/status.py` is owned wholly by this WP (both `show_kanban_status` legs) to keep `owned_files` disjoint. The `:132` identity route is a #2186 site that the Surface Inventory lists alongside the WP01 identity class, but it lives in the same function as the #2187 `:126` drain, so it is routed here. WP01's FR-007 identity arm scope includes `agent_utils/status.py`, so `:132` is statically gated by the arm — and this WP must leave it GREEN by routing it in the same change.

## Context & Constraints

- Spec [spec.md](../spec.md) (US1; FR-001/002/008; Lane A table — `lanes/recovery.py:664` KEEP, `agent_utils/status.py` mixed), [plan.md](../plan.md) IC-03.
- Depends on WP02 (sequential gate-file chain; transitively WP01) and WP01 (the T001 shared divergent fixture). C-001/C-002/C-009-mirror as WP02.

## Branch Strategy
- **Planning base branch**: `mission/coord-read-residuals-2185-2186`
- **Merge target branch**: `mission/coord-read-residuals-2185-2186`

## Subtasks & Detailed Guidance

### T017 – `lanes/merge.py:68/:198`
- Route the `read_lanes_json` reads (LANE_STATE) via `resolve_planning_read_dir(kind=LANE_STATE)`.

### T018 – `lanes/recovery.py` extraction + route
- `scan_recovery_state` already carries `# noqa: C901`. **Extract** the PRIMARY-planning read (`:356` lanes/tasks) and the status-events read into named helpers, **drop the `# noqa`**, route the PRIMARY leg, keep the events leg coord-aware. Also route `:611` (LANE_STATE). **KEEP `:664` coord-aware** — it binds `feature_dir` feeding `emit_status_transition_transactional` (`:686`), a STATUS-write leg (the C-001/#2155 analog); never route it. Add focused tests for the extracted helpers in `tests/specify_cli/lanes/test_recovery_helpers.py`.

### T019 – `lanes/worktree_allocator.py:360`
- Route the `meta.json` read (`_read_coordination_branch`) via `kind=PRIMARY_METADATA` (topology-blind — correct for the chicken-and-egg coord discovery: it reads meta to *discover* coord).

### T020 – `core/worktree_topology.py:138`
- Single swap of `:138` to `resolve_planning_read_dir(...)` co-resolves the three PRIMARY legs (identity `:139`, lanes `:140`, graph `:141`).

### T021 – `agent_utils/status.py::show_kanban_status` — both legs (#2187 `:126` + #2186 `:132`)
- The function currently resolves a single coord-aware `feature_dir = resolve_feature_dir_for_mission(...)` (`:120`) and reuses it for the PRIMARY `tasks/` glob (`tasks_dir = feature_dir / "tasks"`, `:126`, WORK_PACKAGE_TASK), the `resolve_mission_identity(feature_dir)` identity read (`:132`, PRIMARY_METADATA), **and** the STATUS `read_events(feature_dir)` leg (`:151`).
- **Route the #2187 `:126` PRIMARY `tasks/` leg** via `resolve_planning_read_dir(repo_root, mission_slug, kind=WORK_PACKAGE_TASK)` so the WP*.md frontmatter glob reads off PRIMARY, not the `-coord` husk. **Drain the matching `_DIR_READ_KNOWN_RESIDUALS` entry** for `agent_utils/status.py` in the same commit (FR-008). The FR-011 preflight (WP02/T010) must have confirmed it present on the rebased base.
- **Route the #2186 `:132` identity leg** via `kind=PRIMARY_METADATA` (or `primary_feature_dir_for_mission` + `_canonicalize_primary_read_handle`) so the kanban identity resolves off PRIMARY (the coord husk is STATUS-only post-#2106). This is the leg WP01's FR-007 identity arm statically gates — leave the arm GREEN.
- **Keep the STATUS leg coord-aware** (C-001/NFR-001): `read_events` / `reduce` (`:151`) must continue to read the worktree-local event log (the kanban lane data still reflects the event log).

### T022 – RED-first per-site tests on the divergent fixture (WP01/T001)
- Per-site tests in `tests/integration/test_lanes_core_coord_read.py`; reverting a routed read to coord-aware must FAIL on a **returned domain value** (resolved lanes/WP set / materialized topology / resolved mission identity), NOT a resolved-path equality. For `show_kanban_status`: assert it renders the correct **non-empty** board AND resolves the PRIMARY identity; reverting either routed leg FAILS. **NFR-004 (integration-over-stubs):** a unit stub handing in a primary dir does NOT satisfy (#2187 AC).

## Test Strategy
- Focused tests for the recovery helper extraction + per-site RED-first. `ruff`+`mypy` clean; `scan_recovery_state` ≤ 15 after extraction (no noqa).

## Definition of Done

- All lanes/core PRIMARY reads routed; `recovery.py:664` STATUS-write leg left coord-aware.
- `scan_recovery_state` `# noqa: C901` removed via helper extraction (not a re-suppress); helper tests added.
- `show_kanban_status` both legs routed; STATUS `read_events` leg coord-aware; the single #2187 pin drained.
- RED-first lanes/core tests GREEN after routing, FAIL on revert (returned domain value); non-empty kanban board.
- `ruff` + `mypy` clean; touched functions ≤ 15.

## Risks & Mitigations
- Extraction changes behavior → keep the helpers pure; the events leg must stay coord-aware (NFR-001).
- `worktree_allocator` chicken-and-egg → `kind=PRIMARY_METADATA` is topology-blind and correct. Never route the `:664` STATUS-write leg (C-001/#2155 analog).

## Review Guidance
- `reviewer-renata`: confirm the `# noqa: C901` is gone (not re-suppressed), the events/`:664` STATUS legs stay coord-aware, BOTH `show_kanban_status` legs routed (the #2187 pin drained, the #2186 `:132` identity routed and the WP01 arm GREEN), and the revert-fails proof is on a returned domain value.

## Activity Log
- 2026-06-27T11:00:00Z – system – Prompt regenerated (canonical /spec-kitty.tasks from corrected spec/plan).
- 2026-06-27T10:57:00Z – claude:opus:python-pedro:implementer – shell_pid=1095093 – Assigned agent via action command
- 2026-06-27T11:21:20Z – claude:opus:python-pedro:implementer – shell_pid=1095093 – WP03 lanes/core + status.py both legs + #2187 drain + recovery C901 extraction; recovery:664 STATUS KEEP confirmed; 25 new tests, RED-first proven, 1596 mandatory pass
- 2026-06-27T11:21:21Z – claude:opus:reviewer-renata:reviewer – shell_pid=1145629 – Started review via action command
- 2026-06-27T11:27:26Z – user – shell_pid=1145629 – Review passed (reviewer-renata). C-001/#2155: NO status leg routed to PRIMARY. recovery.py reconcile_status feature_dir stays resolve_feature_dir_for_mission (coord-aware) feeding emit_status_transition_transactional + KEEP comment. scan_recovery_state per-leg split REAL: primary_dir=resolve_planning_read_dir(LANE_STATE) for lanes/tasks; separate coord_dir for events (_get_all_wp_lanes_from_events/_get_wp_lane_from_events on coord_dir). status.py:164 read_events(feature_dir) coord-aware; tasks/identity on primary_dir. C901 extraction behavior-preserving: noqa removed (ruff clean), 7 pure helpers all called. #2187 pin drained by exactly one (genuine: gate passes, routed read no longer flags). RED-first proven by revert spot-check (3 legs RED on domain values); real git fixtures, no path-equality, NFR-004 honored. 60 arch gates + 26 WP tests green; floor=38 honest. mypy: 3 errors pre-existing on base, not WP03 new code.
