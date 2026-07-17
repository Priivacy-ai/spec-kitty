---
work_package_id: WP02
title: Projection seam + caching — the one canonical module
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: feat/mission-step-authority
merge_target_branch: feat/mission-step-authority
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-authority unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 1 - Schema
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1176584"
shell_pid_created_at: "1784230702.38"
history:
- at: '2026-07-16T17:35:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/step_projection.py
create_intent:
- src/doctrine/missions/step_projection.py
- tests/doctrine/missions/test_step_projection.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/step_projection.py
- tests/doctrine/missions/test_step_projection.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Projection seam + caching

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for `python-pedro` (`implementer`, `claude`) before reading further.

---

## Objective

Create the **single canonical projection module** `src/doctrine/missions/step_projection.py` (doctrine layer) that
BOTH the DRG extractor (WP04) and the charter/runtime (WP06) consume — one implementation, no second copy, no
layering inversion (charter depends on doctrine, never the reverse). Ship the **complete** API + the cached
accessor so consumer WPs only import, never edit this file.

Depends on WP01 (the schema fields). Read: [plan.md](../plan.md) refinements, [data-model.md](../data-model.md).

## Scope fences (MUST honor)
- **C-008 whack-a-field:** this projects ONLY `MissionType.template_set` (the `dict[artifact_key→file]`). The
  charter/project **`doctrine.template_set` scalar** (`charter/resolver.py`, `compiler.py`, `compact.py`,
  `generator.py`, `catalog.py`, `prompt_builder.py`, `scope_router.py`, `governance-profile.yaml`) is a
  DIFFERENT domain object — **OUT OF SCOPE, do NOT import or touch it.**
- The cache is `MissionTypeRepository._load` injection + a memoized `default()` — **NOT** a computed property on
  the frozen `MissionType` model (impossible; would put I/O in a frozen model — NFR-007 forbids it).

## Subtasks

### T005 — `project_action_sequence(steps) -> list[str]`
Pure function: take the mission type's `MissionStep` set, return the ids of steps with `in_action_sequence == True`
**sorted by `sequence_index`** (stable, deterministic — the freshness gate needs byte-identical regen). Steps with
`in_action_sequence == False` (e.g. `retrospect`, sw-dev's 7 non-sequence steps) are excluded.

### T006 — `project_template_set(steps) -> dict[str, str] | None`
Pure function keyed on **`artifact_key`** (NOT step-id — `spec` ≠ step-id `specify`; the resolver reads
`template_set["spec"]`). For each step with a `template` ref, emit `{step.template.artifact_key: step.template.template_file}`;
drop steps without a template. Return `None` when empty (matches the 3 null-`template_set` types today).

### T007 — Cached accessor (NFR-007)
Wire the projection into `MissionTypeRepository._load` (`mission_type_repository.py:122`): resolve the builtin
steps (`resolve_all_for_mission_type(id, pack_context=None)` — **builtin-only**), compute both projections, and
inject them into `MissionType.model_validate({**raw, "action_sequence": projected, "template_set": ...})`. Memoize
the hot-path `default()` with `@functools.cache` — **reuse the exact idiom shipped at `mission_type_repository.py:140`**
(`builtin_mission_type_ids`, with a `cache_clear()` test seam). This prevents per-call `step.yaml` re-loading.

### T008 — Projection invariant + module tests
Re-assert the relocated non-empty + unique invariant (WP01→WP02 contract) on the projected sequence. Enduring
module-level tests: projection determinism (same input → identical output), artifact-key keying, empty→None,
`in_action_sequence:false` exclusion, and a `cache_clear()`-based memoization test.

## Branch Strategy
Base/merge: `feat/mission-step-authority`. Implement: `spec-kitty agent action implement WP02 --agent <name>`.

## Definition of Done
- [ ] `step_projection.py` exposes `project_action_sequence` + `project_template_set` (artifact-key) — pure, deterministic.
- [ ] `MissionTypeRepository._load` injects the projection (builtin-only); `default()` memoized via `@functools.cache`.
- [ ] Projection invariant (non-empty + unique) asserted; module tests green.
- [ ] Zero import of the `doctrine.template_set` scalar surfaces (C-008).
- [ ] `ruff` + `mypy --strict` clean; complexity ≤15; `regenerate-graph --check` fresh.

## Risks / Reviewer guidance
- If the projection keys `template_set` on step-id, `template_set["spec"]` silently breaks — reviewer verifies artifact-key keying.
- `default()` un-memoized would amplify hot-path I/O — reviewer confirms the `@functools.cache`.

## Requirements: FR-002, FR-003

## Activity Log

- 2026-07-16T19:08:03Z – claude:sonnet:python-pedro:implementer – shell_pid=1079105 – Assigned agent via action command
- 2026-07-16T19:37:33Z – claude:sonnet:python-pedro:implementer – shell_pid=1079105 – Projection seam (artifact-key template_set) + memoized default() injection + transitional YAML fallback; tests/ruff/mypy green; graph fresh
- 2026-07-16T19:38:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=1176584 – Started review via action command
- 2026-07-16T19:43:12Z – user – shell_pid=1176584 – Review passed (reviewer-renata): transitional fallback keeps ALL 4 shipped types byte-for-byte via real default() (software-dev [specify,plan,tasks,implement,review]+{spec,plan}; documentation/plan/research their authored seqs + template_set=None) — verified by loading the real repo, not just the synthetic-YAML test. Empty projection falls back (action_sequence via 'or', template_set via 'is not None'); non-empty projection wins (proven live by monkeypatched annotated-steps test). default() memoized via @functools.cache reusing the shipped builtin_mission_type_ids idiom; cache_clear() seam genuinely exercised (test counts _load: 1 then 2). No frozen-model I/O — injection is at MissionTypeRepository._load, builtin-only pack_context=None. template_set keyed on artifact_key not step-id (specify->{spec:...}). C-008 scalar surfaces only named in docstring, never imported. MissionStepTemplateRef is a real typed usage. Scope = exactly the 3 owned files. Gates: 343 doctrine tests + 24 dead-symbol green; ruff clean; mypy --strict clean; DRG fresh.
