---
work_package_id: WP06
title: CLI guard family — resolve actual family (surface D,
dependencies:
- WP01
requirement_refs:
- FR-014
- NFR-003
planning_base_branch: pr/rc3-charter-gate-predicate-inversion
merge_target_branch: pr/rc3-charter-gate-predicate-inversion
branch_strategy: Planning artifacts for this mission were generated on pr/rc3-charter-gate-predicate-inversion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/rc3-charter-gate-predicate-inversion unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-charter-gate-predicate-inversion-01M0GGT1
base_commit: d82052e660f6042db6a45bb00b4e523ba7e6dde5
created_at: '2026-08-21T13:51:47.420594+00:00'
subtasks: []
history: []
agent_profile: python-pedro
authoritative_surface: src/runtime/next/runtime_bridge.py
create_intent:
- tests/runtime/next/test_cli_guard_family.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge.py
- tests/runtime/next/test_cli_guard_family.py
- tests/runtime/test_bridge_parity.py
role: implementer
tags:
- runtime
- cli-guard
- latent-pin
tracker_refs: []
---

# WP06 — CLI guard family: resolve actual family (#3407)

## Context (see plan.md §1 D, ADR)
`_check_cli_guards` (`runtime_bridge.py:785`) hardcodes `mission_family="software-dev"` (`:797`) into `gather_artifact_presence`, routing every mission type's CLI-guard evaluation around the per-type `_GUARD_TABLES` — including the **already-existing** `plan` table (`_evaluate_plan_guards`, `runtime_bridge_cores.py:680`). **Route, don't rebuild.** WP01 dependency is sequencing-only (no red-by-design reversal here).

**New test file MUST declare a routed `pytestmark` (CI collection gate):** `tests/runtime/next/test_cli_guard_family.py` → `pytestmark = [pytest.mark.unit, pytest.mark.fast]`.

## Red-first (ATDD — latent-defect pin)
1. **AC-13** (`test_cli_guard_family.py`): seed `meta.json mission_type: plan` + an unapproved `tasks/WP01.md` lane; `_check_cli_guards("review", <plan dir>)` today aliases into `_evaluate_wp_iteration_guard` (returns the WP-block string). After the fix it routes to `_GUARD_TABLES["plan"]` (`_evaluate_plan_guards` → `[]`; real gate `gate_passed("plan_approved")`). Label it a latent route-around pin.
2. **AC-14 / NFR-003:** a software-dev mission evaluates exactly as on `main` (unchanged).

## Implementation
- Resolve the mission's actual family at `runtime_bridge.py:797` via `get_mission_type(feature_dir)` (already imported at `:177`) instead of the hardcoded `"software-dev"`, passing it to `gather_artifact_presence`. The existing `evaluate_guards_strict` → `_GUARD_TABLES.get(family)` dispatch then reaches the correct table (incl. the existing `plan` branch); a genuinely unregistered family still fail-closes via `UnregisteredMissionFamilyError`.
- **Verify** `get_mission_type` returns exactly the `_GUARD_TABLES` family key for every built-in (`research/documentation/software-dev/plan`) — if a type's string diverges from its family key, a valid mission would wrongly fail-close. Add a guard/test for the identity.

## DoD / validation surface
`PWHEADLESS=1 pytest tests/runtime/next/test_cli_guard_family.py -q` green; AC-13 plan-review routes to the plan table; AC-14 software-dev unchanged; the `get_mission_type`↔family-key identity is asserted; ruff + mypy clean.
