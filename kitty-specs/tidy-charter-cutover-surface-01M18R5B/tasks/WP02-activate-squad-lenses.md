---
work_package_id: WP02
title: 'Reliability: activate doctrine-daphne + randy-reducer squad lenses (#3810)'
dependencies: []
requirement_refs:
- FR-003
- C-001
planning_base_branch: spec/tidy-charter-cutover-surface
merge_target_branch: spec/tidy-charter-cutover-surface
branch_strategy: Planning artifacts for this mission were generated on spec/tidy-charter-cutover-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/tidy-charter-cutover-surface unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tidy-charter-cutover-surface-01M18R5B
base_commit: 917d2b379810fb9c8686ad32a92132f633f30deb
created_at: '2026-08-30T20:42:38.191512+00:00'
subtasks:
- T005
- T006
- T007
phase: Phase 1
history: []
authoritative_surface: src/charter/activation/packs/default.yaml
create_intent:
- tests/doctrine/test_activation_squad_lenses.py
execution_mode: code_change
mission_id: 01M18R5BMJSQBT1ZN68WSR4X6Q
owned_files:
- src/charter/activation/packs/default.yaml
- tests/doctrine/test_activation_squad_lenses.py
tags: []
tracker_refs: []
---

# WP02 — Reliability: activate doctrine-daphne + randy-reducer squad lenses (#3810)

**Priority**: P1 · **Concern**: IC-02 · **Requirements**: FR-003, C-001 (red-first)
**Owned files**: `src/charter/activation/packs/default.yaml`, `tests/doctrine/test_activation_squad_lenses.py` (new)
**Dependencies**: none (independent lane)

## Goal
The charter `activated_agent_profiles` allowlist omits `doctrine-daphne` and `randy-reducer`
— the exact two lenses the `adversarial-squad` skill hardcodes — so the FR-014 activation
gate returns `EXIT 1 "is not activated"` and compliant delegates dispatch **unprofiled**,
silently. Add both to the shipped allowlist so squads run profiled.

## Context
- Both profiles **exist and are DRG nodes** — they are de-activated, not missing.
- The shipped allowlist source is `src/charter/activation/packs/default.yaml` (near line 187,
  `activated_agent_profiles`) — edit the **source pack**, not a generated copy.
- Regression origin: commit `9a99801f1b` (2026-08-08). FR-014 gate:
  `src/specify_cli/cli/commands/profiles_cmd.py:337`.
- Member of profile-load epic #3809; the durable orchestrator-inject seam is #3811 (out of scope here — this is the near-term allowlist fix only).

## Subtasks
- **T005** — Red-first test (`tests/doctrine/test_activation_squad_lenses.py`): assert both
  `doctrine-daphne` and `randy-reducer` resolve through the activation gate (activated), and
  that the `adversarial-squad` skill's two hardcoded lenses are a subset of the activated set.
  It must FAIL on current `default.yaml`.
- **T006** — Add `doctrine-daphne` and `randy-reducer` to `activated_agent_profiles` in
  `src/charter/activation/packs/default.yaml`. Keep ordering/style consistent; do not deactivate anything.
- **T007** — Verify: the resolver reports both activated (no `EXIT 1`), and the red-first test
  now passes. Do NOT touch a user's deliberate project-local de-activation (edge case) — this
  corrects the shipped default only.

## Acceptance (SC-002)
- `doctrine-daphne` + `randy-reducer` resolve with no `EXIT 1 "is not activated"`.
- Red-first test fails before T006, passes after.
- `ruff`/`mypy`/terminology clean; new test file joins the completeness baselines (union-reconciled at integration).
