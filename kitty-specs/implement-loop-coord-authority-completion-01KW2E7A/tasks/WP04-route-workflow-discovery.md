---
work_package_id: WP04
title: Route workflow.py + discovery.py (signature split)
dependencies:
- WP01
- WP03
requirement_refs:
- FR-002
- FR-006
- FR-009
tracker_refs: []
planning_base_branch: design/coord-authority-remediation-2160
merge_target_branch: design/coord-authority-remediation-2160
branch_strategy: Planning artifacts for this mission were generated on design/coord-authority-remediation-2160. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-authority-remediation-2160 unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
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
- tests/integration/test_coord_loop_workflow.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/runtime/next/discovery.py
- tests/integration/test_coord_loop_workflow.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Route workflow.py + discovery.py (signature split)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Route the implement/review-loop reads in `workflow.py`, fixing the **single-arg MIXED read**
in `discovery.py::preview_claimable_wp` by **splitting its signature** (the WP09-trap fix),
and remove the workflow/discovery pins.

Done when, on the WP01 coord fixture: claimable preview, `_resolve_review_context` (lanes.json
+ tasks/), `_find_first_for_review_wp`, and the `review` tasks/ leg resolve **primary**;
review-cycle sub-artifacts still resolve **coord** (C-008); `selection_reason` is unchanged on
a flat topology; the pins are removed; gates green; RED-first per-site tests pass.

## Context & Constraints

- Spec FR-002, FR-006, FR-009. Sites (verify live): `workflow.py:1067`
  (`_preview_claimable_wp_for_mission`), `:1932` (`_resolve_review_context` — lanes.json +
  tasks/), `:2110/2116/2121/2124` (`_find_first_for_review_wp` — **inline**), `:2476/:2610/:2647`
  (`review` — tasks/ leg routes; review-cycle sub-artifact at `:2647` and `baseline-tests.json`
  at `:2614` stay coord). `runtime/next/discovery.py::preview_claimable_wp` (~`:97/:190`).
- **WP09-trap (the load-bearing risk):** `preview_claimable_wp(feature_dir)` reads `tasks/`
  (PRIMARY, via `_read_candidate_wp_ids`/`build_dependency_graph`) AND status events (COORD,
  via `_load_wp_lanes`→`_read_events`) from ONE dir. **Split the signature** into
  `planning_dir` (kind=WORK_PACKAGE_TASK) + `status_dir` (coord-aware). A naive route of the
  single arg breaks the status read on coord topology. DoD asserts both legs + flat-topology
  `selection_reason` unchanged.
- **C-008:** route only WORK_PACKAGE_TASK reads; the review-cycle read/write pair stays coord.
- **Avoid the `workflow.py:539-617` legacy-fallback block** and the `feedback://` deprecation
  paths (`:1782/:1867`) — do not re-point them.
- **build_dependency_graph:** route at the `:2476` in-loop caller; do NOT change its signature.
- **FR-009:** remove workflow/discovery pins from the WP02-owned ratchet file in this commit.
- C-009: do not touch `merge/`, `lanes/`, `core/worktree_topology`.

## Branch Strategy

- **Strategy**: already-confirmed
- **Planning base branch**: design/coord-authority-remediation-2160
- **Merge target branch**: design/coord-authority-remediation-2160

## Subtasks & Detailed Guidance

### Subtask T015 – Split `discovery.py::preview_claimable_wp` signature (backward-compatible)
- **Ripple guard (squad HIGH):** `preview_claimable_wp` has a 2nd production caller
  `src/runtime/next/runtime_bridge.py:3078` AND ~11 calls in
  `tests/next/test_next_claimable_payload.py`. A hard signature change breaks them.
  **Therefore add `status_dir: Path | None = None` (default = `planning_dir`)** — backward-
  compatible: existing single-arg callers keep working; only the coord-aware caller passes a
  distinct `status_dir`. Rename the primary param `feature_dir`→`planning_dir` ONLY if it
  stays positional-compatible; otherwise keep `feature_dir` and add `status_dir=None`.
- Route the candidate-WP/dependency reads off the planning arg; the lane/event reads off
  `status_dir or planning_dir`. Update the docstring (path-derived; not "primary for all").

### Subtask T016 – Route `_preview_claimable_wp_for_mission`
- At the workflow.py caller, pass `planning_dir = resolve_planning_read_dir(...,WORK_PACKAGE_TASK)`
  and `status_dir` = the existing coord-aware dir.

### Subtask T017 – Route `_resolve_review_context` + `_find_first_for_review_wp`
- `_resolve_review_context:1932`: route the lanes.json (LANE_STATE) and tasks/ reads to the
  seam; keep any status leg coord. `_find_first_for_review_wp` inline reads (2110–2124) → seam.

### Subtask T018 – Route the `review` tasks/ leg; keep review-cycle coord (C-008)
- Route the WP-task definition read; **do not** route `baseline-tests.json` (`:2614`) or the
  review-cycle sub-artifact path (`:2647`). Stay clear of the `:539-617` legacy block.

### Subtask T019 – Remove the workflow pins (same commit)
- Delete the **workflow.py** `_DIR_READ_KNOWN_RESIDUALS` entries (out-of-map edit to WP02's
  file). Note: `discovery.py` is under `src/runtime/next/` — OUTSIDE the scanner scope — so
  there is no discovery pin to remove. `implement`/`review` keep their **C-008 permanent-coord**
  pins (their review-cycle sub-artifact legs stay coord; see WP02's C-008 category) — only the
  routable PRIMARY leg of `review` (`:2476` build_dependency_graph caller) is routed here.
- Record a 1:1 map: each removed pin ↔ its routed site ↔ its T020 test (FR-009).

### Subtask T020 – RED-first per-site tests (both legs, through the PRE-EXISTING entry point)
- **RED-first rigor (squad HIGH):** drive the **pre-existing public entry point**
  (`_preview_claimable_wp_for_mission` / the `review` command), NOT the new signature — a test
  written against `preview_claimable_wp(planning_dir, status_dir)` reds via `TypeError` and
  proves nothing. Run on the **COORD** fixture; the documented RED must be a **husk-path
  assertion failure** (not import/signature error, not a flat-topology pass).
- Assert tasks+lanes from PRIMARY and events from COORD; `selection_reason` unchanged on flat;
  the review-cycle artifact still reads coord (C-008). File: `test_coord_loop_workflow.py`.

## Test Strategy

`PWHEADLESS=1 pytest tests/integration/test_coord_loop_workflow.py tests/architectural/test_gate_read_literal_ban.py -q`.
RED-first proof required for the signature-split site especially.

## Risks & Mitigations

- **The WP09 trap** (naive single-arg route silently breaks status on coord). Mitigation:
  signature split + dual-leg assertion + flat `selection_reason` regression.
- **Accidentally routing review-cycle reads** → new split-brain. Mitigation: C-008 assertion
  that review-cycle still reads/writes coord.

## Review Guidance

- Confirm the signature was split, not swapped.
- Confirm review-cycle artifacts untouched and the legacy block avoided.
- Confirm RED-first evidence for T015.

## Activity Log

- 2026-06-26T18:29:45Z – system – Prompt created.
- 2026-06-26T21:00:35Z – user – flat
- 2026-06-26T21:00:37Z – user – flat; route workflow.py+discovery.py
- 2026-06-26T21:24:19Z – claude – workflow+discovery routed (4de977103): backward-compat discovery split (11 payload tests unchanged), C-008 coord preserved, 38 passed
- 2026-06-26T21:27:57Z – user – renata review done
- 2026-06-26T21:27:59Z – user – Approved by reviewer-renata (flat): discovery split backward-compat (11 payload tests unbroken), all STATUS legs coord (no #2155), C-008 review-cycle verifiably unmoved, 38 passed. 2 non-blocking: LOW lanes.json kind-truth (use LANE_STATE), MEDIUM T018 asserts seam not review() entry → close-out polish.
