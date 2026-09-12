---
work_package_id: WP04
title: Resolve remaining doctrine minor code smells
dependencies: []
requirement_refs:
- C-004
- FR-008
- NFR-004
- NFR-005
planning_base_branch: fix/gate-artifact-merge-driver-unit-gate
merge_target_branch: fix/gate-artifact-merge-driver-unit-gate
branch_strategy: Planning artifacts for this mission were generated on fix/gate-artifact-merge-driver-unit-gate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/gate-artifact-merge-driver-unit-gate unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-gate-artifact-merge-driver-unit-gate-01KZPG7V
base_commit: ec37ad919f2cd336fd1532990e1f876425f5170c
created_at: '2026-08-10T19:36:03.622160+00:00'
subtasks:
- T012
- T013
- T014
history:
- event: created
  at: '2026-08-10T19:04:04Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/drg/org_pack_config.py
- src/doctrine/artifact_kinds.py
- src/doctrine/missions/glossary_hook.py
role: implementer
tags: []
tracker_refs:
- '#3232'
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objectives & Success Criteria

Resolve the 3 remaining doctrine code-smell minors (FR-008, SC-007). Behavior-preserving; no suppressions
(NFR-005); scoped to the 3 named files (C-004). Done when a fresh Sonar analysis reports 0 open `S6353`,
`S7632`, `S117` in these files and `ruff`/`mypy` + the modules' tests stay green.

**Ownership boundary (squad fix 4)**: these are behavior-preserving fixes with no new tests. WP03 owns
`tests/doctrine/**`; do NOT create a test file under `tests/doctrine/` (it would collide with WP03).

## Subtasks & Detailed Guidance

### Subtask T012 — S6353 concise regex (`src/doctrine/drg/org_pack_config.py:71`)

- Replace the character class `[A-Za-z0-9_]` with `\w` in the regex (equivalent under default flags for
  ASCII identifiers). Verify any test that exercises this pattern still passes — if the pattern is used on
  non-ASCII input where `\w` would differ under the `re.UNICODE` default, keep `[A-Za-z0-9_]` and record
  why (the one legitimate reason to leave it). Confirm the intended semantics first.

### Subtask T013 — S7632 malformed suppression comment (`src/doctrine/artifact_kinds.py:118`)

- Sonar flags a suppression comment with wrong syntax. Inspect it: if the suppression is unnecessary,
  REMOVE it (preferred — NFR-005 favors no suppressions); if a suppression is genuinely warranted, fix its
  syntax to the correct form and add a one-line rationale. Do not leave a malformed/no-op suppression.

### Subtask T014 — S117 local variable naming (`src/doctrine/missions/glossary_hook.py:134`)

- Rename the local variable `GlossaryAwarePrimitiveRunner` to snake_case (e.g. `glossary_aware_runner`)
  to match the naming convention, updating all in-scope references. If it is actually a class alias that
  reads better in PascalCase, confirm whether a module-level alias (exempt) is more appropriate — but the
  Sonar finding is on a LOCAL variable, so a snake_case rename is the expected fix.

## Review Guidance

- All three findings resolved via real fixes (no new suppressions); behavior unchanged; tests green.
- Confirm via Sonar query that S6353/S7632/S117 for these files dropped to 0.

## Activity Log

- 2026-08-10T19:04:04Z – system – lane=planned – Prompt created.
