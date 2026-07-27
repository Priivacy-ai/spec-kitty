---
work_package_id: WP04
title: Extractor re-point — emit edges from the projection (0-delta)
dependencies:
- WP02
- WP03
requirement_refs:
- FR-004
- FR-010
tracker_refs: []
planning_base_branch: feat/mission-step-authority
merge_target_branch: feat/mission-step-authority
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-authority unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
phase: Phase 3 - Cutover spine
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1272805"
shell_pid_created_at: "1784232318.26"
history:
- at: '2026-07-16T17:35:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/migration/extractor.py
create_intent:
- tests/doctrine/drg/migration/test_extractor_projection.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/migration/extractor.py
- tests/doctrine/drg/migration/test_extractor_projection.py
- tests/doctrine/drg/test_mission_type_nodes.py
- tests/doctrine/drg/migration/test_extractor.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Extractor re-point

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for `python-pedro` (`implementer`, `claude`).

---

## Objective

Re-point the DRG edge generator to read the **projection** instead of the raw `action_sequence`, preserving the
shipped graph **exactly** (280 nodes / 757 edges / 10 orphans, fresh). Depends on WP02 (seam) + WP03 (sw-dev data
— so the projection is populated for the parity type).

## Context (grounded, critical)
- `extract_mission_type_edges` (`extractor.py:835/849`) today reads `data.get("action_sequence", [])` off the raw YAML dict and emits `mission_type:X → action:X/<step>` `requires` edges.
- The **action NODES** come from a SEPARATE path: `extract_action_edges` → `rglob("actions/*/index.yaml")` (`extractor.py:674`). **WP04 must NOT change the node source** — nodes stay minted from `actions/*/index.yaml`. WP05 does not touch `actions/*/index.yaml` either, so node count stays 280.
- The extractor currently has **zero** coupling to the step repository — re-pointing adds one. Pin it: **builtin-only** (`pack_context=None`, so project/org overrides never leak into the shipped graph) and **projection-filtered** (read `project_action_sequence`, NEVER a `mission-steps/` dir listing — a dir listing would blow sw-dev 5→12 edges).

## Subtasks

### T011 — Re-point `extract_mission_type_edges` to the projection
Replace the `data.get("action_sequence")` read with a call through the projection seam (WP02): resolve builtin
steps for the type (`pack_context=None`), `project_action_sequence(...)`, emit the same `requires` edges. Determinism
preserved (projection is sorted by `sequence_index`) so `regenerate-graph` stays byte-identical.

### T012 — Invariance assertions
`tests/doctrine/drg/migration/test_extractor_projection.py`:
- DRG counts equal the baseline **280 / 757 / 10**, graph fresh (load `load_built_in_graph()`).
- **`in_action_sequence: false` steps mint no `mission_type→action` edge** (retrospect + sw-dev's 7 non-sequence steps) — else NFR-002 breaks.
- The projected edge set == the pre-mission `action_sequence`-derived edge set (per type).

### T013 — Re-point raw-YAML test helpers
`tests/doctrine/drg/test_mission_type_nodes.py:98` and `tests/doctrine/drg/migration/test_extractor.py:700`
(`_shipped_action_sequences`) read `data.get("action_sequence")` off shipped YAML — they go **red at cutover**
(WP07). Re-point them to the projection now so they become referential-integrity checks, not raw-YAML reads.

## Branch Strategy
Base/merge: `feat/mission-step-authority`. Implement: `spec-kitty agent action implement WP04 --agent <name>`.

## Definition of Done
- [ ] Extractor reads the projection (builtin-only, filtered); NO `mission-steps/` dir listing.
- [ ] DRG **280 / 757 / 10**, fresh — 0 delta; `in_action_sequence:false` mints no edge.
- [ ] Node source (`actions/*/index.yaml`) untouched.
- [ ] Raw-YAML test helpers re-pointed to the projection.
- [ ] `ruff`/`mypy --strict` clean; complexity ≤15; `regenerate-graph --check` fresh + byte-identical.

## Risks / Reviewer guidance
- The 12→5 blow-up trap: reviewer confirms the extractor reads the **projection**, not a directory of step.yaml.
- 0-delta is load-bearing (NFR-002) — any count drift is a defect, not an accepted change.

## Requirements: FR-004, FR-010

## Activity Log

- 2026-07-16T19:53:10Z – claude:sonnet:python-pedro:implementer – shell_pid=1231354 – Assigned agent via action command
- 2026-07-16T20:04:42Z – claude:sonnet:python-pedro:implementer – shell_pid=1231354 – Extractor reads projection (builtin-only, filtered, no dir listing); DRG 280/757/10 fresh 0-delta; in_action_sequence:false mints no edge; test helpers re-pointed
- 2026-07-16T20:05:21Z – claude:opus:reviewer-renata:reviewer – shell_pid=1272805 – Started review via action command
- 2026-07-16T20:10:06Z – user – shell_pid=1272805 – Review passed (reviewer-renata): Extractor reads the WP02 PROJECTION (project_action_sequence via MissionStepRepository, pack_context=None, builtin-only) NOT a mission-steps/ dir listing — verified sw-dev projects exactly 5 edges (a listing would give 12). Action-NODE source (rglob actions/*/index.yaml) untouched. in_action_sequence:false mints NO edge (sw-dev 7 non-sequence steps + retrospect asserted). Transitional fallback confirmed: sw-dev PROJECTS, the 3 unannotated types FALL BACK to authored action_sequence; both yield byte-identical edges. DRG 280/757/10 fresh + byte-identical (regenerate-graph --check clean, no fragments touched). T013 helpers re-pointed to MissionTypeRepository resolved value. Gates: 552 passed, ruff clean, mypy --strict clean, complexity ≤15. Scope: only extractor + 3 test files.
