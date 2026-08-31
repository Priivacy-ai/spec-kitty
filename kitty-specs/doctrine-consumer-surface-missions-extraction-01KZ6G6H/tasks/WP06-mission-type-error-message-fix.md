---
work_package_id: WP06
title: Mission-type error message fix
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: research/doctrine-wheel-mission-types-public-api
merge_target_branch: research/doctrine-wheel-mission-types-public-api
branch_strategy: Planning artifacts for this mission were generated on research/doctrine-wheel-mission-types-public-api. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/doctrine-wheel-mission-types-public-api unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-consumer-surface-missions-extraction-01KZ6G6H
base_commit: 11f36ea6b8c8e890ccdb0cf94ee2fa6821d01671
created_at: '2026-08-04T16:54:01.756176+00:00'
subtasks:
- T026
- T027
- T028
phase: Phase 3 - Bundled fixes
history:
- at: '2026-08-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/mission_type_profiles.py
- tests/charter/test_mission_type_profiles.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Mission-type error message fix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

`UnknownMissionTypeError`'s current message states that a mission-type id is both "unknown" and "registered" in the same sentence, when an activated custom mission type has no loadable profile — a real, reproducible defect (issue #3183).

This WP is done when:
- A new red-first reproduction test for the actual scenario (activated id, no loadable profile) exists and initially fails.
- The message is fixed so it never claims both facts contradictorily.
- The new test passes; the existing, unrelated `test_unknown_type_raises_unknown_mission_type_error` still passes.

## Context & Constraints

Read `spec.md` (FR-006, SC-003, User Story 3) and `research.md` (R4) before starting.

**The exact reproduction is already documented.** `src/charter/mission_type_profiles.py` (~line 506-514) carries an in-repo docstring reproducing the defect verbatim: activating only `my-custom` with no resolvable `MissionTypeProfile` on disk raises `"Unknown mission type 'my-custom'. Registered types: my-custom."` — the id appears in both the "unknown" clause and the "registered" list.

**Important — the existing test does not cover this.** `tests/charter/test_mission_type_profiles.py::test_unknown_type_raises_unknown_mission_type_error` only checks an id absent from `existing_mission_types()` entirely — a different, non-contradictory case. Do not treat that test passing as evidence this defect is already covered.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### T026 – Red-first reproduction test

- **Purpose**: ATDD-first discipline (C-011) — prove the defect before fixing it.
- **Steps**: Add a new test that configures `activated_mission_types: [my-custom]` with no resolvable `MissionTypeProfile` on disk, and asserts the current message's self-contradiction (this test should fail against today's code, in a way that demonstrates the actual bug — not just "an exception is raised").
- **Files**: `tests/charter/test_mission_type_profiles.py`.
- **Parallel?**: [P] — independent of the fix itself, write first.

### T027 – Fix the message

- **Purpose**: Resolve the vocabulary collision.
- **Steps**: Change the message so it states the two distinct facts separately — e.g. "Mission type 'my-custom' is activated but has no loadable profile" — never claiming both "unknown" and "registered" of the same id in one sentence.
- **Files**: `src/charter/mission_type_profiles.py`.
- **Parallel?**: No — depends on T026 existing first (red).

### T028 – Verify

- **Purpose**: Confirm both the new and existing tests are green.
- **Steps**: Run both tests; confirm T026's reproduction now passes and the existing unrelated test is unaffected.
- **Files**: n/a (verification).
- **Parallel?**: No — final gate.

## Test Strategy

```bash
PYTHONPATH=src python -m pytest tests/charter/test_mission_type_profiles.py -q
```

## Risks & Mitigations

- **Risk**: Fixing the wording without a red-first test, then discovering the "fix" doesn't actually address the real scenario. **Mitigation**: T026 before T027, strictly.

## Review Guidance

- Confirm T026's test genuinely reproduces the activated-but-unresolvable case, not a restatement of the already-passing existing test.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append new entries at the end.

- 2026-08-04T15:30:00Z – system – Prompt created.
