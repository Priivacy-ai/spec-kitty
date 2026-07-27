---
work_package_id: WP04
title: Lane A — Coord-topology integration proof (divergent fixture)
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-009
- NFR-001
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: mission/coord-read-residuals-2185-2186
merge_target_branch: mission/coord-read-residuals-2185-2186
branch_strategy: Planning artifacts for this mission were generated on mission/coord-read-residuals-2185-2186. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/coord-read-residuals-2185-2186 unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
phase: Phase 3 - Integration proof
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1177820"
history:
- at: '2026-06-27T11:00:00Z'
  actor: system
  action: Prompt regenerated via /spec-kitty.tasks (canonical regeneration from corrected spec/plan)
agent_profile: python-pedro
authoritative_surface: tests/integration/
create_intent:
- tests/integration/test_coord_read_residuals_proof.py
execution_mode: code_change
model: ''
owned_files:
- tests/integration/test_coord_read_residuals_proof.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Lane A — Coord-topology integration proof

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer) before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

- A real `git worktree` coord-topology integration test proves the routed Lane A reads land on PRIMARY (on a **returned domain value**), the STATUS legs still read the husk, and the routing is a no-op on flat topology. It **fails if any routed read is reverted to coord-aware**. This is the headline acceptance (SC-001) and the squad's CRITICAL false-green guard.

## Context & Constraints

- Spec [spec.md](../spec.md) (US1 Independent Test; FR-009; NFR-001/003/004; SC-001), [plan.md](../plan.md) IC-04.
- Depends on WP01 (the T001 divergent-fixture extension) + WP02 + WP03 (the routed code under test). **NFR-004 integration-over-stubs** — no unit stubs handing in a primary dir. The fixture's divergence definition lives in ONE place (WP01/T001); **consume** it, do not re-author. **Do NOT** retrofit `write_side/topology_fixtures.py::build_coord` (non-divergent husk, ~26 consumers).

## Branch Strategy
- **Planning base branch**: `mission/coord-read-residuals-2185-2186`
- **Merge target branch**: `mission/coord-read-residuals-2185-2186`

## Subtasks & Detailed Guidance

### T023 – Coord-topology merge/recovery/topology integration test
- **File**: `tests/integration/test_coord_read_residuals_proof.py` (new), consuming the WP01/T001 `coord_topology_fixture.py` variant (husk lacks `lanes.json`/`tasks/`; husk meta `mission_id` is the sentinel `6KERGF2ZNFBPR91YEZMARG99KS` ≠ PRIMARY). **Re-assert the HARD divergence triad before driving.** Drive the real `_run_lane_based_merge` / `scan_recovery_state` / `materialize_worktree_topology` against it; assert the PRIMARY reads return the seeded lanes/WPs on a **returned domain value** (the forecast WP set / materialized worktrees / resolved identity). Add a guard that reverting a routed read to coord-aware FAILS on the domain value (not a path equality, not the fixture's `assert_reads_primary`/`assert_both_legs` helpers).

### T024 – NFR-001 STATUS-from-husk + revert-fails guard
- Assert the STATUS legs (`status.events.jsonl` via `recovery.py:664` / `status_feature_dir` / `show_kanban_status` `read_events`) still read from the **coord husk**, proving zero STATUS legs were re-routed to PRIMARY. This is the NFR-001 primary evidence. Pair it with the explicit revert-fails assertion so a silent STATUS→PRIMARY re-route is caught.

### T025 – Flat-topology parity [P]
- Assert the routing is a **no-op on flat (non-coord) topology** (NFR-003); existing flat-topology merge/lanes/next tests stay green (PRIMARY == primary on flat topology).

## Test Strategy
- This WP *is* the test. Run serially if it touches real ports/daemons; otherwise parallel-safe. `ruff` + `mypy` clean.

## Definition of Done

- Integration test drives real code against the divergent fixture; PRIMARY reads proven on returned domain values.
- STATUS-from-husk assertions present (NFR-001); revert-fails guard present and real.
- Flat-topology parity asserted (NFR-003).
- `ruff` + `mypy` clean.

## Risks & Mitigations
- Non-divergent husk = false-green → the divergence assertions in WP01/T001 (husk lacks `lanes.json`/`tasks/`; husk meta `mission_id` = sentinel ≠ PRIMARY) are the guard; review them explicitly and re-assert the triad in this test.

## Review Guidance
- `reviewer-renata`: confirm the husk genuinely diverges, the revert-fails guard is present and real (on a returned domain value), and the STATUS-from-husk assertions actually exercise the coord husk.

## Activity Log
- 2026-06-27T11:00:00Z – system – Prompt regenerated (canonical /spec-kitty.tasks from corrected spec/plan).
- 2026-06-27T11:28:27Z – claude:opus:python-pedro:implementer – shell_pid=1161522 – Assigned agent via action command
- 2026-06-27T11:39:22Z – claude:opus:python-pedro:implementer – shell_pid=1161522 – WP04 integration proof: 10 tests, real production fns driven, divergence triad proven falsifiable (kills build_coord false-green), NFR-001 STATUS-from-husk + 4 revert→RED demos + flat parity
- 2026-06-27T11:39:24Z – claude:opus:reviewer-renata:reviewer – shell_pid=1177820 – Started review via action command
- 2026-06-27T11:42:46Z – user – shell_pid=1177820 – Review passed: proof is REAL. Triad falsifiable (test_divergence_triad_is_falsifiable copies primary lanes.json+tasks into husk -> _assert_divergence_triad raises 'divergence triad violated', confirmed via pytest.raises + 10/10 PASS, no skip/xfail); triad asserted BEFORE every routed drive (5 drives). 4 revert->RED demos executed on returned DOMAIN VALUES (materialize entries WP set+mission_type; forecast lanes payload; recovery wp_id set; status_lane) not path-equality. Production callables confirmed real (resolve to src/specify_cli; only resolver-revert + pass-through spies patched, no primary-dir stub NFR-004). NFR-001 STATUS-from-husk genuine (read_events pass-through spy: coord dir in seen_dirs, primary NOT; executor status_feature_dir==coord; revert->primary collapses status_lane). Flat parity genuine (NFR-003). Test-only no src (C-009). ruff+mypy clean. SC-001/SC-002/FR-009 proven.
