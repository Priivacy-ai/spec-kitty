---
work_package_id: WP01
title: Governance Schema Baseline
lane: "done"
dependencies: []
base_branch: develop
base_commit: 5b49198e2f853d0dd3b9a7320349d62f4421864d
created_at: '2026-02-17T15:10:16.319774+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
phase: Phase 1 - Governance Foundation
assignee: ''
agent: codex_nonKitty
shell_pid: '170105'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-17T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Governance Schema Baseline

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies; branch from `develop`.

## Objectives & Success Criteria

1. Minimal schema set exists for mission, directive, tactic, import candidate, and agent profile.
2. Each schema has valid and invalid fixtures.
3. `tests/doctrine` validation tests fail clearly for malformed artifacts.
4. Test output identifies schema + fixture + field-level error location.

## Context & Constraints

- Spec: `kitty-specs/053-doctrine-governance-layer-refactor/spec.md`
- Plan: `kitty-specs/053-doctrine-governance-layer-refactor/plan.md`
- Research decisions: `kitty-specs/053-doctrine-governance-layer-refactor/research.md`
- Contracts: `kitty-specs/053-doctrine-governance-layer-refactor/contracts/governance-layer-contracts.md`

MVP scope is fixed to the agreed minimal set; template-set and constitution-selection schemas are out of scope for this WP.

## Subtasks & Guidance

### T001-T006: Create schema files

- Add schema files under doctrine schema directory:
  - `mission.schema.yaml`
  - `directive.schema.yaml`
  - `tactic.schema.yaml`
  - `import-candidate.schema.yaml`
  - `agent-profile.schema.yaml`
- Keep required fields minimal and explicit.
- Include stable `$id` and version metadata where applicable.

### T007: Add fixtures

- Add `valid/` and `invalid/` fixture samples for each schema.
- Ensure each invalid sample breaks a different rule class (missing field, invalid enum, wrong type).

### T008-T009: Build validation tests

- Create reusable test helper for schema loading + fixture validation.
- Add tests that assert valid fixtures pass and invalid fixtures fail with readable errors.

## Risks & Mitigations

- Risk: schema overfitting to current examples.
  Mitigation: prefer contract-level constraints over implementation details.
- Risk: noisy test failures.
  Mitigation: include fixture path and JSON pointer in assertion messages.

## Activity Log

- 2026-02-17T15:10:23Z – codex_nonKitty – shell_pid=170105 – lane=doing – Assigned agent via workflow command
- 2026-02-17T15:14:53Z – codex_nonKitty – shell_pid=170105 – lane=for_review – Schema baseline implemented with fixtures and validation tests
- 2026-02-17T15:33:51Z – codex_nonKitty – shell_pid=170105 – lane=doing – Started review via workflow command
- 2026-02-17T15:34:38Z – codex_nonKitty – shell_pid=170105 – lane=done – Review passed: schema baseline/fixtures/validator added
