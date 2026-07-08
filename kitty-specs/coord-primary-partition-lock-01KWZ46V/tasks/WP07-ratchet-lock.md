---
work_package_id: WP07
title: Ratchet lock
dependencies:
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-011
- NFR-001
- NFR-004
tracker_refs: []
planning_base_branch: design/coord-primary-partition-lock
merge_target_branch: design/coord-primary-partition-lock
branch_strategy: Planning artifacts for this mission were generated on design/coord-primary-partition-lock. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-primary-partition-lock unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1882036"
history:
- at: '2026-07-07T20:40:00+00:00'
  actor: planner
  action: created
agent_profile: architect-alphonso
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_no_write_side_rederivation.py
- tests/architectural/test_write_surface_placement_guard.py
- tests/architectural/test_wp05_write_target_drain.py
- tests/architectural/resolution_gate_allowlist.yaml
- tests/architectural/test_resolution_authority_gates.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `architect-alphonso` via `/ad-hoc-profile-load`. Read `spec.md`, `plan.md` (IC-04),
`research.md` (D7), `contracts/ratchet-contract.md`. **Depends on WP02–WP05** (all write sites must be
routed first). Implement via `spec-kitty agent action implement WP07 --agent claude`.

## Objective

Lock the strangle: extend the existing ratchet with the `CommitTarget(ref=<checkout>)` grammar that
was the blind spot, set the **write-side** allow-list to its floor, and expand the adopted-module set
to every strangled surface. (The `coord_authority` read-side baseline drain is deferred to #2453 — see
T034.) **Extend — do not fork** (C-001).

## Context

- Runs LAST among the routing chain: by the time it lands, WP02–WP05 have routed every named write
  site, so the new grammar finds zero un-allow-listed offenders and the allow-list can sit at floor.
- The ratchet already exists (`test_no_write_side_rederivation.py`, seed allow-list = 1 at
  `status_transition.py:347`); the partition-stability gate `test_write_surface_placement_guard.py`
  already exists (#2198, CLOSED) — **extend it, do not duplicate**. Also present:
  `tests/architectural/test_wp05_write_target_drain.py` co-anchors the same seed (347) — this WP owns it too (squad M-1).

## Subtasks

### T033 — New grammar
- Extend the `test_no_write_side_rederivation.py` AST scanner to flag `CommitTarget(...)` /
  `safe_commit(...)` whose `ref`/`destination_ref` derives from a current-checkout expression rather
  than a `seam.write_target(...)` call. Guard the detection boundary: allow-list the sanctioned coord
  primitives (`branch_naming.py` `coord_*`, `CoordinationWorkspace`, `mission_runtime/*` internals) and
  legacy/migration modules (`upgrade/migrations/*`, `migration/*`, `upgrade/autocommit.py`,
  `invocation/executor.py`).
- **Tracked-VISIBLE allow-list (squad H-1/H-4/L-2):** allow-list `retrospective/writer.py` (the sanctioned #2119 RETROSPECTIVE authority), and the residual checkout-derived fallbacks `orchestrator_api/commands.py:1451`, `coordination/transaction.py` legacy override, and `tasks_map_requirements.py:177` — **each with a `tracked: #2453` rationale**. These are flagged, not silently ignored; routing them is #2453, not this mission.

### T034 — Write-side allow-list to floor + adopted-module expansion
- Set the **write-side line allow-list** to its permanent-fixture floor (seed = 1, `status_transition.py:347` — re-anchored 343→347 by the #1842 tombstone hook; the composite `(qualname, token)` key is authoritative, the number is only a locator), now that WP02–WP05 removed the routed sites. Expand the adopted-module set to include `core/mission_creation.py`, `cli/commands/implement.py`, `cli/commands/agent/workflow.py`, `cli/commands/agent/tasks_move_task.py`, `cli/commands/agent/mission_record_analysis.py`.
- **Do NOT shrink `coord_authority_baseline` (keep at 7):** its 5 drainable entries are kind-blind `resolve_feature_dir_for_mission` **reads** (disjoint from the routed writes) — the 7→2 drain belongs to the **#2453** read-site sweep. Shrinking it here would falsely claim work not done.

### T035 — Extend the #2198 gate
- Extend `test_write_surface_placement_guard.py` (611 lines, already present) with the new grammar /
  partition assertions. Do NOT create a new gate.

### T036 — Full suite green + self-test
- `pytest tests/architectural/` green. Add a self-test that re-introducing a `CommitTarget(ref=<checkout>)`
  bypass makes the ratchet go red (proves the grammar bites).

### T037 — Campsite
- Test files are ruff/Sonar clean (relaxed selects for `tests/**`); no campsite. Keep new scanner code ≤15.

## Campsite (Sonar issues in owned files)

| File | Rule | Location | Class | Action |
|------|------|----------|-------|--------|
| `tests/architectural/*` | — | clean (relaxed selects for tests) | — | keep new scanner ≤15 |

## Branch Strategy

Base / merge target `design/coord-primary-partition-lock`. Worktree per computed lane. **Depends on
WP02–WP05** — cannot be claimed until they are approved/done. Shared substrate with the sibling
gate-hardening mission; per C-005 our baseline changes are authoritative (operator sequences merges).

## Definition of Done

- New grammar catches `CommitTarget(ref=<checkout>)`; boundary allow-list correct (incl. the tracked-VISIBLE `#2453` entries).
- Write-side allow-list at floor (seed=1 @ `:347`); adopted-module set expanded; `coord_authority_baseline` left at 7 (drain deferred to #2453, not falsely claimed).
- #2198 gate extended (not duplicated); full architectural suite green (incl. `test_wp05_write_target_drain.py`); self-test proves the ratchet bites.
- `ruff` + `mypy` clean.

## Risks & Reviewer guidance

- **No parallel gate** — reviewer rejects a new ratchet file; this must extend the existing ones.
- Verify the boundary allow-list does not false-positive on the sanctioned coord primitives or legacy modules.
- Confirm the baseline shrink is real (a routed-but-not-shrunk allow-list is a silent regression).

## Activity Log

- 2026-07-07T23:30:44Z – claude:sonnet:architect-alphonso:implementer – shell_pid=1744022 – Assigned agent via action command
- 2026-07-08T00:08:57Z – claude:sonnet:architect-alphonso:implementer – shell_pid=1744022 – Ready; grammar bites (self-test); write-side floor 1->2 (honest: dedup'd 2 pre-existing workflow.py read-path parent.parent hits into 1 helper); coord_authority stays 7 (drain #2453). Pre-existing red in test_single_mission_surface_resolver.py (unrelated mission gate, traced to WP02) filed as #2461, not fixed here.
- 2026-07-08T00:14:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=1882036 – Started review via action command
