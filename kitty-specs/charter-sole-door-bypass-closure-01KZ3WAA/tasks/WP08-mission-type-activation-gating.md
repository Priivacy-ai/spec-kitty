---
work_package_id: WP08
title: Mission-type activation gating
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: feat/charter-sole-door-bypass-closure
merge_target_branch: feat/charter-sole-door-bypass-closure
branch_strategy: Planning artifacts for this mission were generated on feat/charter-sole-door-bypass-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-sole-door-bypass-closure unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
phase: Phase 2 - Bypass closure
history:
- at: '2026-08-03T14:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/activation/mission_type_profiles.py
create_intent:
- tests/charter/test_mission_type_activation_gating.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/mission_type_profiles.py
- tests/charter/test_mission_type_activation_gating.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – Mission-type activation gating

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer role, claude agent) before parsing
the rest of this prompt.

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` in the event log before starting. Address all feedback; log changes in the Activity Log.

---

## Objectives & Success Criteria

Gate the `mission-type` token — the 10th of 10 doctrine-artifact kinds, and the structurally different one
(FR-006). **This is NOT a copy of WP07's pattern — read the Context section before starting.**

**Success criteria**:
- Activation filtering added entirely within `charter.activation.mission_type_profiles.resolve_mission_type_context()`
  — this WP does NOT touch `MissionTypeProfileRepository`/`mission_type_profile_repository.py` at all (that
  file is WP06's exclusive ownership for the unrelated `builtin_missions_root()` delegate; keeping this WP's
  filtering logic entirely in `resolve_mission_type_context()` avoids a real ownership overlap) — and
  **not** a new property on `charter.activation.resolver.DoctrineService` (see
  `contracts/charter-doctrine-service-contract.md`'s "Explicitly NOT on this class" section — do not add a
  `mission_types` property there as a shortcut).
- A bare-project regression test proves **set-equality** against `builtin_mission_type_id_set()` — not a
  fakeable subset check.
- A subset-activation test proves filtering actually narrows the result when packs are activated.

## Context & Constraints

- Read `research.md`'s D4 finding in full: `PackContext.activated_mission_types`
  (`src/charter/activation/pack_context.py:120`) is a plain `frozenset[str]`, **never `None`** —
  `_read_activated_mission_types` already collapses "key absent" to `builtin_mission_type_id_set()` at
  `PackContext` construction time. The three-state semantics (`None`/`frozenset()`/`{ids}`) the other 9
  kinds use **do not apply here** — do not attempt to force this token into that pattern.
- `src/doctrine/service.py` has **no** `mission_types` property at all — confirmed by grepping every
  `@property` in that file. Mission-type resolution has always lived entirely outside `DoctrineService`.
- Independent of WP01-07 — no dependency.

## Branch Strategy

- **Strategy**: lane-per-WP (normalized by `finalize-tasks`)
- **Planning base branch**: feat/charter-sole-door-bypass-closure
- **Merge target branch**: feat/charter-sole-door-bypass-closure

## Subtasks & Detailed Guidance

### Subtask T034 – Add activation filtering to `resolve_mission_type_context()`

- **Purpose**: The actual gating logic, on the correct function — without touching
  `MissionTypeProfileRepository`'s own file (ownership boundary with WP06).
- **Steps**:
  1. Read `charter.activation.mission_type_profiles.resolve_mission_type_context()` in full, and read
     `MissionTypeProfileRepository` (in `mission_type_profile_repository.py`) for context only — do not
     edit that file.
  2. Add filtering logic, entirely within `mission_type_profiles.py`, that intersects the available
     mission-type set with
     `PackContext.activated_mission_types` — since that field is already collapsed to the full built-in set
     when nothing was authored, a straightforward intersection naturally gives the correct bare-project
     behaviour (full set) and correct activated-subset behaviour (narrowed set) without needing three-state
     branching.
  3. Do not add a `mission_types` property to `charter.activation.resolver.DoctrineService` — that is explicitly
     forbidden by the pinned contract (a different entry point for a different shape of gating is the
     correct design here, not a shortcut to avoid).
- **Files**: `src/charter/activation/mission_type_profiles.py`.
- **Parallel?**: No — foundational for T035-T036.

### Subtask T035 – Bare-project regression test: set-equality

- **Purpose**: Non-fakeable proof — "at least `research`/`software-dev`/`documentation`/`plan` resolve" is
  satisfied even if a fifth built-in type silently drops out.
- **Steps**: Assert the bare-project result **equals** `builtin_mission_type_id_set()` as a set — full
  equality, not a subset containment check.
- **Files**: `tests/charter/test_mission_type_activation_gating.py` (new).
- **Parallel?**: No — depends on T034.

### Subtask T036 – Subset-activation regression test

- **Purpose**: Prove the filtering actually filters, not just that it doesn't break the bare-project case.
- **Steps**: Activate a proper subset of mission-types in a test `PackContext`; assert
  `resolve_mission_type_context()` returns exactly that subset, not the full built-in set.
- **Files**: `tests/charter/test_mission_type_activation_gating.py`.
- **Parallel?**: No — depends on T034.

## Test Strategy

- `pytest tests/charter/ -v`.
- `mypy --strict src/charter/activation/mission_type_profile_repository.py src/charter/activation/mission_type_profiles.py`.

## Risks & Mitigations

- **Trying to force the three-state (`None`/`frozenset()`/`{ids}`) pattern onto `activated_mission_types`.**
  Mitigation: it's a plain `frozenset`, never `None` — an intersection-based approach is simpler and
  correct; do not add unnecessary `is not None` branching that can never be false.
- **Adding a `mission_types` property to `DoctrineService` "for consistency" with WP07.** Mitigation: this
  is explicitly forbidden by the contract — the inconsistency with the other 9 kinds is the correct,
  documented outcome of this token's structural difference, not a gap to paper over.

## Review Guidance

- Confirm no new property was added to `charter.activation.resolver.DoctrineService`.
- Confirm T035's assertion is set-equality, not a 4-item subset check.
- Confirm T036 actually activates a proper subset (not the full set) to prove filtering occurs.

## Activity Log

- 2026-08-03T14:10:00Z – system – Prompt created.
