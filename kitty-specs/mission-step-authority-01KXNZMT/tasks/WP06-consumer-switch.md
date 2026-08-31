---
work_package_id: WP06
title: Consumer switch — every authority read → the cached seam
dependencies:
- WP02
- WP03
- WP05
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/mission-step-authority
merge_target_branch: feat/mission-step-authority
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-authority unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
phase: Phase 3 - Cutover spine
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1376305"
shell_pid_created_at: "1784234013.09"
history:
- at: '2026-07-16T17:35:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/mission_type_profiles.py
create_intent:
- tests/runtime/test_runtime_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/mission_type_profiles.py
- src/runtime/next/decision.py
- src/runtime/next/runtime_bridge_composition.py
- tests/runtime/test_runtime_seam.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Consumer switch

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for `python-pedro` (`implementer`, `claude`).

---

## Objective

Switch **every real authority read** of `action_sequence`/`template_set` to the cached projection seam, so no
consumer re-reads a retained flat field (that would be a 5th authority, C-003). Depends on WP02 (seam), WP03
(sw-dev data), WP05 (4-type data) so the projection is populated for all types before the switch.

## Context (grounded — the switch is narrower than a naive sweep)
Every runtime/CLI consumer funnels through the **charter bundle** `ResolvedMissionType.action_sequence` and
switches **transitively** once the model projects (WP02 injection). The genuine authority reads to touch:
- `_resolve_action_slot` — `mission_type_profiles.py:694/697` (reads `mission.action_sequence` / `parent.action_sequence`). **This is THE read** — NOT the `:496` bundle pass-through.
- `_resolve_template_set_slot` — `mission_type_profiles.py:750` (`mission.template_set`).
- `decision.py:606` + `runtime_bridge_composition.py:186/321` — bundle reads; confirm they consume the projected value.

## Scope fence (C-008)
Do **NOT** touch the `doctrine.template_set` **scalar** (charter selection authority: `resolver.py`, `compiler.py`,
`compact.py`, `generator.py`, `catalog.py`, `prompt_builder.py`, `scope_router.py`, `governance-profile.yaml`). It
is a different domain object. Only `MissionType.template_set` (dict) is in scope.

## Subtasks

### T018 — Switch the slot resolvers
Point `_resolve_action_slot` (:694/697) + `_resolve_template_set_slot` (:750) at the cached projected value (from
WP02's `MissionTypeRepository` injection + memoized `default()`), not a raw YAML field.

### T019 — Confirm the bundle consumers
Verify `decision.py:606` + `runtime_bridge_composition.py:186/321` read the projected value transitively; adjust
only if they bypass the bundle.

### T020 — extends-fallback check + seam-equivalence tests
- The `extends` fallback (`mission_type_profiles.py:694`): a projected-empty child would trip the non-empty
  validator before the runtime can inherit the parent. One-line check across the **4 built-in types** — confirm
  none relies on `extends` to supply an otherwise-empty sequence (pre-existing behavior must be preserved).
- `tests/runtime/test_runtime_seam.py`: seam-equivalence — resolved `action_sequence`/`template_set` via the seam
  equal the pre-mission values for all 4 types; no hot-path uncached I/O (assert the memoized `default()`).

## Branch Strategy
Base/merge: `feat/mission-step-authority`. Implement: `spec-kitty agent action implement WP06 --agent <name>`.

## Definition of Done
- [ ] `_resolve_action_slot` (:694/697) + `_resolve_template_set_slot` (:750) read the cached projection.
- [ ] Bundle consumers (decision/runtime_bridge) confirmed on the projected value; no missed authority.
- [ ] extends-fallback preserved across 4 types; seam-equivalence tests green.
- [ ] `doctrine.template_set` scalar surfaces untouched (C-008).
- [ ] `ruff`/`mypy --strict` clean; complexity ≤15; `regenerate-graph --check` fresh.

## Risks / Reviewer guidance
- A naive `rg template_set` sweep that edits the scalar surfaces = corruption. Reviewer confirms only the dict is switched.
- YAML fields are still authored at this point (removal is WP07) — consumers read the projected value while the YAML coexists.

## Requirements: FR-012

## Activity Log

- 2026-07-16T20:06:21Z – claude:sonnet:python-pedro:implementer – shell_pid=1276333 – Assigned agent via action command
- 2026-07-16T20:33:16Z – claude:sonnet:python-pedro:implementer – shell_pid=1276333 – Authority reads confirmed on injected/projected value (no bypass); seam-equivalence 4 types (26 tests) + extends-fallback; C-008 scalar untouched; owned files ruff/mypy clean (schema.py:29 mypy error is pre-existing, out of owned scope)
- 2026-07-16T20:33:35Z – claude:opus:reviewer-renata:reviewer – shell_pid=1376305 – Started review via action command
- 2026-07-16T20:38:47Z – user – shell_pid=1376305 – Review passed (reviewer-renata). C-003 no-missed-authority: _resolve_action_slot/_resolve_template_set_slot read MissionTypeRepository.default().get() (WP02-injected/projected model); decision.py:606 + runtime_bridge_composition.py:186/321 read resolve_mission_type_context(...).action_sequence (the bundle) — no raw-YAML re-read. Broader grep found only the C-008 doctrine.template_set SCALAR (correctly fenced), migration tooling, and a CLI display that also resolves via the seam. Seam-equivalence: test_runtime_seam.py invokes real resolve_mission_type_context and compares vs independent raw-YAML ground truth for all 4 built-in types (not synthetic). extends-fallback: no built-in sets extends; locked by test. C-008: git diff --name-only shows ZERO scalar surfaces touched. mypy fix list(x or []) behavior-preserving (field now list[str]|None). Scope: feat commit touches only owned mission_type_profiles.py (docstrings + 2-line narrowing) + new test; decision.py/rbc.py legitimately unchanged. Gates green: pytest seam(42)+charter(56), ruff clean, mypy clean on 4 owned files, regenerate-graph --check fresh. Pre-existing for WP07 aggregate: _internal_runtime/schema.py:29 mypy StructuredError; cli/commands/charter/mission_type.py:88 list(mt.action_sequence) needs same Optional narrowing when WP07 nulls the raw field.
