---
work_package_id: WP11
title: 'coord_authority drain: FR-003 predicate-widen then FR-002 floor 7->2'
dependencies:
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
- WP10
requirement_refs:
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3591215"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_resolution_authority_gates.py
- tests/architectural/resolution_gate_allowlist.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-002, FR-003, NFR-002, SC-001),
`plan.md` (IC-04). **Append to `traces/*.md`.**

## Objective

Drain the `coord_authority` ratchet **7 → 2** after all Thread-A routing (WP04–WP10) lands.
**FR-003 (predicate-widen) MUST precede FR-002 (floor re-pin)** — reclassifying the two by-design
writes moves the live write count before the floor is pinned.

## Context

- Gate: `tests/architectural/test_resolution_authority_gates.py` + `resolution_gate_allowlist.yaml`
  (`coord_authority_baseline: 7`). Depends on ALL Thread-A routing WPs.
- **2 permanent by-design keepers** (the floor-2 residuals): `decisions/emit.py:71`, `widen/state.py:63`.
- **FR-003**: reclassify `lanes/recovery.py:755` + `agent_tasks_ports.py:322` as by-design writes via
  `_COORD_WRITE_BY_DESIGN` (test module ~@679) OR by widening the `_is_write_indicator_call` predicate.
  These are WRITES — never routed; they must not count toward the drainable read census.
- The allow-list line locators drifted (e.g. stale `2670` → live `2747`) — freshen them; the
  census counts by **token**, not line.

## Subtasks

### T034 — FR-003 predicate-widen (FIRST)
Add `lanes/recovery.py:755` + `agent_tasks_ports.py:322` to `_COORD_WRITE_BY_DESIGN` (or widen the
write-indicator predicate). Re-run `scan_coord_authority_call_sites` to confirm the live write count
reflects the reclassification. **Do this before T035.**

### T035 — FR-002 floor 7→2
Re-pin `coord_authority_baseline: 2` with a valid margin; shrink the allow-list to the 2 permanent
keepers; freshen the stale line locators (2670→2747 etc.). Confirm the gate is green at floor 2.

### T036 — NFR-002 non-vacuity
Add/confirm a self-test that a re-introduced raw `resolve_feature_dir_for_mission` read (outside the
seam) goes RED — the floor cannot be pinned so high it masks a regression (margin holds).

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP11 --agent <name>`.

## Definition of Done
- [ ] FR-003 done BEFORE FR-002; the 2 status-write false-negatives reclassified as writes.
- [ ] coord_authority at floor 2 with valid margin; stale locators freshened.
- [ ] Re-introduced raw read goes RED (NFR-002); full gate green; tracer updated.

## Reviewer guidance (opus)
Confirm FR-003 precedes FR-002 (order matters). Verify floor=2 with the 2 correct permanent keepers.
Confirm the non-vacuity self-test bites. Confirm recovery.py:755/agent_tasks_ports.py:322 are marked
by-design writes (never routed).

## Activity Log

- 2026-07-08T10:14:02Z – user – shell_pid=3452488 – Moved to planned
- 2026-07-08T10:14:04Z – claude:sonnet:python-pedro:implementer – shell_pid=3483080 – Started implementation via action command
- 2026-07-08T10:26:44Z – claude:sonnet:python-pedro:implementer – shell_pid=3483080 – FR-003 predicate-widen (agent_tasks_ports.py:feature_write_dir, lanes/recovery.py:reconcile_status added to _COORD_WRITE_BY_DESIGN) + FR-002 floor re-pin (COORD_AUTHORITY_WRITE_FLOOR/coord_authority_baseline 2->4, live census verified via scanner) + NFR-002 non-vacuity self-test. Full gate green (59/59). Orchestrator's combined-drain estimate of floor=2 was pre-FR-003; corrected to 4 post-widen.
- 2026-07-08T10:27:46Z – claude:opus:reviewer-renata:reviewer – shell_pid=3519498 – Started review via action command
- 2026-07-08T10:32:51Z – user – shell_pid=3519498 – Review passed: FR-003 predicate-widen (recovery.py:765 reconcile_status feeds emit_status_transition_transactional + agent_tasks_ports.py:322 feature_write_dir returns committed dir — both genuine by-design writes, never routable, added file-scope to _COORD_WRITE_BY_DESIGN matching decisions/emit.py+widen/state.py pattern, sanctioned in allowlist). Floor pinned to live census 4: INDEPENDENT scan_coord_authority_call_sites(src) = exactly 4 writes (agent_tasks_ports:322, decisions/emit:71, lanes/recovery:765, widen/state:63); spec's est-2 corrected by FR-003 visibility gain (2 previously-blind write helpers surfaced), NOT inflated to mask reads — the 5 drainable reads (4 workflow.py + implement.py) are gone from census. NFR-002 non-vacuity bites (verified: excluding 2 WP11 sites -> 2 < floor 4 RED; has anti-vacuous sanity assert). Allowlist=4 entries, CANON 44/ROUTED_CANON 39 intact. 59 green, ruff+mypy clean on diff. NOTE for WP17 SC-001: floor is 4 not 2.
- 2026-07-08T11:06:15Z – user – shell_pid=3519498 – Re-review to supersede the spurious rejected review-cycle-1 artifact written by the orchestrator blocked->planned unblock (NOT a reviewer rejection; WP11 was approved on merits). Code unchanged.
- 2026-07-08T11:06:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=3591215 – Started review via action command
