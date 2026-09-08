---
work_package_id: WP01
title: Repair project doctrine ingestion
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
- C-001
- C-002
- C-003
- C-004
planning_base_branch: issue-4103-migrate-guidance-glossary-step
merge_target_branch: issue-4103-migrate-guidance-glossary-step
branch_strategy: Planning artifacts for this mission were generated on issue-4103-migrate-guidance-glossary-step. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-4103-migrate-guidance-glossary-step unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Implementation
history: []
agent_profile: implementer-ivan
authoritative_surface: src/charter/activation/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter/**
- src/specify_cli/cli/commands/doctrine.py
- src/specify_cli/cli/commands/glossary.py
- src/charter/activation/**
- src/charter/offering/drg/**
- src/charter/offering/skills/spec-kitty-charter-doctrine/**
- tests/charter/**
- tests/doctrine/**
- tests/specify_cli/cli/commands/**
- docs/changelog/CHANGELOG.md
- packs/built-in/procedures/migrate-project-guidance-to-spec-kitty-charter.procedure.yaml
- packs/built-in/procedure.graph.yaml
- packs/built-in/pack-manifest.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package WP01: Repair project doctrine ingestion

## Do This First: Load Agent Profile

Resolve implementer-ivan with `spec-kitty agent profile show implementer-ivan` and load `charter context --action implement --json`. Follow spk-doctrine-profile-load.

## Objectives & Success Criteria

Deliver spec FR-001 through FR-006 and the exact operator acceptance flow. Preserve one PR, issue-separated commits, v3.2.6.1 ancestry and delayed remote CI.

## Context & Constraints

Read spec.md, plan.md and the project charter. The gist is the acceptance contract. #4103 is already transplanted. Architecture investigation selected direct-authored project registration (option b), recorded on #4097 before coding. No generated-source duplicate authority, directory renames, new suppressions or main pushes.

## Branch Strategy

Planning and implementation target: issue-4103-migrate-guidance-glossary-step. Single-branch topology implements directly on this user-selected existing PR branch; preserve the branch and use canonical runtime operations for task state.

## Subtasks & Detailed Guidance

### T001 — Migration glossary step

Verify transplanted procedure semantics and generated graph freshness.

### T002 — Charter command parity

Pin missing public commands red-first. Register doctrine new/validate/fetch and org app on charter through shared handlers. Name remaining doctrine-only commands in deprecation guidance. Update the canonical CLI surface assertions and changelog; run the focused tests before committing #4098.

### T003 — Seed glossary lookup

Pin a valid lowercase team_domain seed listed but not shown. Reuse list's store for show fallback; preserve compiled-page behavior and unknown-term diagnostics. Test URN and bare names, scope ambiguity and missing terms. Commit #4102 after local tests.

### T004 — Project registration and provenance

Extend canonical project scanning to validate and project user-authored kinds with source provenance and existing reference extraction. Widen manifest kind contracts as required. Reconcile without dropping unrelated data. Make status and shipped skill describe actual support. Commit #4097 after owning tests.

### T005 — Cascade

From deactivated state, activate profile with all four references and assert all five become active. Warn about unreachable references; preserve filtered cascade behavior. Commit #4100 with tests and changelog.

### T006 — Resynthesis

Pass project layer roots through activated-ID resolution. Plan and validate before writing activation when resynthesis is requested. Error text names charter.yaml. Test built-in/org/project and refusal without mutation. Commit #4101 after tests.

### T007 — Delivery verification

Run all required owning tests, ruff/mypy and terminology guard. Execute gist acceptance in fresh git repository through dev CLI, record transcript. Obtain independent review and address findings. Prepare and retarget/update the existing PR, preserving original verification.

## Post-acceptance delivery gate

After local WP review and Spec Kitty acceptance, publish the complete evidence and verify all final-head remote checks pass before handoff. This external delivery gate remains mandatory; it is separate from T007 so recording the local review does not require a prior remote CI run. Do not merge.

## Test Strategy

Use red/green public CLI tests per issue, tests/charter and tests/doctrine for offering changes, glossary subsystem, targeted command tests, terminology guard, generated graph check and fresh CLI acceptance. Run baseline make test-fast where available; no whole-repository test run.

## Risks & Mitigations

Project root semantics require `.kittify` in layer_roots. Manifest kind restrictions need deliberate extension. Start without persisted graph so tests expose actual defect. Repeated reconciliation must preserve unrelated state.

## Review Guidance

Independent reviewer checks every gist item and failure atomicity, layer precedence, provenance integrity and source preservation against actual diff and results.

## Definition of Done

All scenarios pass locally; PR has complete issue sections and transcript; final CI passes. Post-merge ingestion skill remains excluded.
