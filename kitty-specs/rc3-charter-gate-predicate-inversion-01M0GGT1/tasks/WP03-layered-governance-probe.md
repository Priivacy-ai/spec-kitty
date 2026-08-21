---
work_package_id: WP03
title: Governance-slot — layered per-type probe (surface B,
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
- NFR-002
planning_base_branch: pr/rc3-charter-gate-predicate-inversion
merge_target_branch: pr/rc3-charter-gate-predicate-inversion
branch_strategy: Planning artifacts for this mission were generated on pr/rc3-charter-gate-predicate-inversion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/rc3-charter-gate-predicate-inversion unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-charter-gate-predicate-inversion-01M0GGT1
base_commit: d82052e660f6042db6a45bb00b4e523ba7e6dde5
created_at: '2026-08-21T13:43:20.326416+00:00'
subtasks: []
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/mission_type_profiles.py
create_intent:
- tests/charter/test_layered_governance_probe.py
execution_mode: code_change
owned_files:
- src/charter/mission_type_profiles.py
- tests/charter/test_mission_type_profiles.py
- tests/charter/test_layered_governance_probe.py
role: implementer
tags:
- charter
- governance
- red-by-design
tracker_refs: []
---

# WP03 — Governance-slot: layered per-type probe (#3598)

## Context (see plan.md §1, ADR)
`_resolve_governance_slot` (`:766`) tolerates any unregistered type whenever the **project-wide** `_project_has_doctrine_overrides` (`:1235`) is true — so a typo'd type resolves silently with fabricated provenance. Replace with a layered per-type predicate.

**New test file MUST declare a routed `pytestmark` (CI collection gate):** `tests/charter/test_layered_governance_probe.py` → `pytestmark = [pytest.mark.fast, pytest.mark.unit]` (tmp_path fixtures — no `corpus` needed unless it reads `packs/built-in/**`).

## Red-first (ATDD)
1. **AC-4 (new red):** `resolve_mission_type_context(repo_root, "softwaer-dev")` in a project with other `selected_*` doctrine raises `UnknownMissionTypeError` (today it resolves silently). Add to `tests/charter/test_layered_governance_probe.py`.
2. **Reverse AC-6:** `tests/charter/test_mission_type_profiles.py::test_project_with_overrides_does_not_hard_fail_for_unknown_type` — rewrite around the layered predicate. **The current test patches `_project_has_doctrine_overrides`→True, a symbol this WP deletes** — instead seed a real per-type `governance-profile.yaml` with a matching `id`. Do NOT restore the project-wide tolerance.
3. **AC-5 (net-new):** an unregistered type whose per-type `governance-profile.yaml` (matching `id`) exists at **project OR org OR built-in** resolves without error — one fixture per layer (today only the project layer is inspected).

## Implementation
- Replace the `_project_has_doctrine_overrides` tolerance with: tolerate iff `MissionTypeProfileRepository` resolves a per-type `governance-profile.yaml` whose `id` matches the type at any layer (project/org/built-in), via `_GOVERNANCE_PROFILE_GLOB`. Reuse the existing repository — **add no second merge/probe site** (single canonical authority).
- Else raise `UnknownMissionTypeError` (`:805`).
- **NFR-002:** this is the governance surface; the delivery path (`resolve_mission_type_key`) is untouched and stays hard-fail-free.

## DoD / validation surface
`PWHEADLESS=1 pytest tests/charter/test_mission_type_profiles.py tests/charter/test_layered_governance_probe.py -q` green; AC-4/5/6 pass; `_project_has_doctrine_overrides` removed (or no longer the tolerance gate); ruff + mypy clean.
