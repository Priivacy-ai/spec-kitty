---
work_package_id: WP07
title: Resolve-by-URN lane (Concern C)
dependencies:
- WP01
- WP06
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: feat/mission-step-creatability
merge_target_branch: feat/mission-step-creatability
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-creatability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-creatability unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/runtime/resolver.py
create_intent:
- tests/runtime/test_resolve_by_urn.py
- tests/architectural/test_urn_resolver_scalar_fence.py
execution_mode: code_change
owned_files:
- src/specify_cli/runtime/resolver.py
- tests/runtime/test_resolve_by_urn.py
- tests/architectural/test_urn_resolver_scalar_fence.py
role: implementer
tags: []
shell_pid_created_at: "1784302537.09"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2901996"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer) before anything else.

## Objective
Add URN-addressed template resolution as a **second lane** alongside resolve-by-name (the filesystem↔URN duality is a compatibility contract, C-004). Depends on WP01 (cutover) + WP06 (qualified nodes exist). See `contracts/name-urn-resolution.md`.

## Context & FROZEN
- **C-004 two lanes, do NOT collapse**: resolve-by-name (`template_set[artifact_kind]→filename→5-tier`) stays as the creation path; resolve-by-URN is added *alongside*. The `template_file` filename remains the 5-tier override key; the URN identifies the DRG node. Both terminate in the same Stage-2 `resolve_template`.
- **Scope bound (FR-010)**: add the lane + an equivalence test **only**. Do NOT re-wire the name-based creation path. `resolve_configured_template`'s signature is unchanged.
- **C-002 scalar fence**: `resolver.py` neighbours the scalar surfaces. The new URN code must **never reference** `resolution.template_set`, `MissionTypeProfile.template_set`, or `doctrine.template_set`. Importing `ResolvedMissionType` from `charter.mission_type_profiles` is REQUIRED and allowed — the fence is on *referencing the scalar*, not on importing from charter.
- **C-001 fail-closed**: an absent/blank/unresolvable URN → typed error; never default an unqualified URN's `mission` segment to `software-dev` (no #2660 inference reintroduction).

## Subtasks
### T031 — Add the resolve-by-URN function
- In `resolver.py`, add a function that resolves a mission-qualified `template:<mission>/<name>` URN by converging on `template_catalog.resolve_template_by_id` (which splits `<mission>/<name>` and delegates to the same Stage-2 `resolve_template`). Fail-closed on a malformed/unresolvable URN.

### T032 — Equivalence + override-wins test
- `tests/runtime/test_resolve_by_urn.py`: (a) for an authored template, by-URN resolves to the **same file** as by-name (US3.2); (b) a `.kittify/overrides/templates/<file>` override **wins on the URN lane** (US3.3), proving the URN lane honors the 5-tier precedence.

### T033 — C-002 arch assertion
- `tests/architectural/test_urn_resolver_scalar_fence.py`: assert the new URN resolver code references none of the scalar `template_set` surfaces (`resolution.template_set`, `MissionTypeProfile.template_set`, `doctrine.template_set`). Model on the existing import/reference-boundary arch tests (`tests/architectural/test_layer_rules.py`).

## Branch Strategy
Base `feat/mission-step-creatability`; worktree per `lanes.json`. `spec-kitty agent action implement WP07 --agent <tool>:<model>:python-pedro:implementer` (after WP01 + WP06 approved).

## Definition of Done
- Resolve-by-URN function added (signature-stable, fail-closed); equivalence + override-wins tests green; C-002 arch assertion green; creation path unchanged; ruff/mypy clean, complexity ≤15.

## Risks & Reviewer Guidance
- Reviewer: confirm the name-based creation path is untouched; both lanes end in the same `resolve_template`; override wins on the URN lane; no scalar reference; no software-dev default on an unqualified URN.

## Activity Log

- 2026-07-17T12:55:00Z – claude:sonnet:python-pedro:implementer – shell_pid=2703348 – Assigned agent via action command
- 2026-07-17T15:18:03Z – claude:sonnet:python-pedro:implementer – shell_pid=2703348 – Resolve-by-URN lane added ALONGSIDE the name path (resolve_configured_template signature unchanged; creation path untouched, C-004). by-URN==by-name equivalence + .kittify override-wins on the URN lane both proven; C-002 scalar-fence arch test green. 18 WP07 tests pass, ruff/mypy clean, DRG fresh. Orchestrator finished handoff (implementer stalled post-gate).
- 2026-07-17T15:18:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=2860261 – Started review via action command
- 2026-07-17T15:26:10Z – user – Moved to planned
- 2026-07-17T15:29:16Z – claude:sonnet:python-pedro:implementer – shell_pid=2884984 – Started implementation via action command
- 2026-07-17T15:34:42Z – claude:sonnet:python-pedro:implementer – shell_pid=2884984 – Cycle-2: allowlisted the 2 designed-ahead URN-lane public symbols (consumer tracked #2761) — dead-symbol gate now green; all cycle-1-approved surfaces unchanged.
- 2026-07-17T15:35:40Z – claude:opus:reviewer-renata:reviewer – shell_pid=2901996 – Started review via action command
