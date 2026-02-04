---
description: "Work packages for Mission-Aware Cleanup & Docs Wiring"
---

# Work Packages: Mission-Aware Cleanup & Docs Wiring

**Inputs**: Design documents from `/kitty-specs/029-mission-aware-cleanup-docs-wiring/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Explicitly required for helper consolidation and documentation mission wiring.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `/tasks/`. This file is the high-level checklist; detailed guidance lives in each prompt.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Include precise file paths or modules.

## Path Conventions
- **Single project**: `src/`, `tests/`

---

## Work Package WP01: Script Cleanup & Template Alignment (Priority: P1)

**Goal**: Remove root-level script duplication, update references/tests to the packaged script source, and align base planning templates with mission guidance.
**Independent Test**: Test suite runs without referencing root `scripts/` copies; plan template guidance matches software-dev mission template.
**Prompt**: `/tasks/WP01-script-cleanup-template-alignment.md`

### Included Subtasks
- [ ] T001 Update tests/utilities to use `src/specify_cli/scripts` as the script source of truth (remove `scripts/` path assumptions).
- [ ] T002 Remove root `scripts/` duplicates and update any docs/help text that still references them.
- [ ] T003 Align `src/specify_cli/templates/command-templates/plan.md` feature-detection guidance with the software-dev mission template.

### Implementation Notes
- Focus on removing duplication without introducing symlinks.
- Ensure any developer-facing docs or help text point to the packaged path.

### Parallel Opportunities
- T001 and T003 can run in parallel once file locations are confirmed.

### Dependencies
- None.

### Risks & Mitigations
- Risk: Removing root scripts breaks tests. Mitigation: update all test utilities and references before deletion.

---

## Work Package WP02: Consolidate Task Helpers (Priority: P1)

**Goal**: Create a single shared helper implementation for task operations and apply consistent worktree-aware behavior.
**Independent Test**: Tasks CLI behaves identically in main repo and worktree, and helper logic exists in one shared module.
**Prompt**: `/tasks/WP02-consolidate-task-helpers.md`

### Included Subtasks
- [ ] T004 Create a shared task helper module (worktree-aware `find_repo_root`, conflict detection, shared frontmatter utilities).
- [ ] T005 Update `src/specify_cli/tasks_support.py` and `src/specify_cli/scripts/tasks/task_helpers.py` to delegate to the shared module.
- [ ] T006 Update `tasks_cli.py` paths/logic to rely on the consolidated helpers.
- [ ] T007 Add/adjust tests for worktree-aware detection and conflict handling parity.

### Implementation Notes
- Keep compatibility with existing scripts by importing from the shared module through the installed package.
- Preserve behavior for legacy lane detection.

### Parallel Opportunities
- T004 must land before T005/T006.
- T007 can run after T005/T006 are sketched.

### Dependencies
- Depends on WP01 (script cleanup to avoid path drift).

### Risks & Mitigations
- Risk: Import path changes break standalone scripts. Mitigation: add compatibility layer and tests in `tests/test_tasks_cli_commands.py`.

---

## Work Package WP03: Unify Acceptance Logic (Priority: P1)

**Goal**: Eliminate duplicate acceptance implementations and remove deprecated dependencies from the main CLI.
**Independent Test**: Acceptance behavior matches across `spec-kitty accept` and the standalone tasks CLI.
**Prompt**: `/tasks/WP03-unify-acceptance-logic.md`

### Included Subtasks
- [ ] T008 Extract shared acceptance core logic into a new non-deprecated module.
- [ ] T009 Update `src/specify_cli/acceptance.py` to use the shared core and remove dependency on deprecated helpers.
- [ ] T010 Update `src/specify_cli/scripts/tasks/acceptance_support.py` to use the shared core.
- [ ] T011 Add/adjust acceptance tests to verify parity between CLI and script entrypoints.

### Implementation Notes
- Ensure both acceptance entrypoints surface consistent errors and JSON output.

### Parallel Opportunities
- T008 is prerequisite; T009/T010 can proceed in parallel after the core exists.

### Dependencies
- Depends on WP02 (shared task helper module).

### Risks & Mitigations
- Risk: Differences in external dependencies for scripts. Mitigation: keep core module dependency-light and verify import behavior in tests.

---

## Work Package WP04: Documentation Mission State & Gap Analysis Wiring (Priority: P2)

**Goal**: Wire documentation mission state initialization and gap analysis execution into existing flows without adding new public commands.
**Independent Test**: Documentation mission features generate gap analysis during plan/research and update documentation state in `meta.json`.
**Prompt**: `/tasks/WP04-doc-mission-state-gap-analysis.md`

### Included Subtasks
- [ ] T012 Wire documentation state initialization into specification flow for documentation missions.
- [ ] T013 Invoke gap analysis during documentation mission planning and persist report paths.
- [ ] T014 Invoke gap analysis during documentation mission research and update documentation state metadata.
- [ ] T015 Integrate documentation generator detection/configuration into the plan flow and record configured generators in state.

### Implementation Notes
- Ensure mission gating so software-dev flows remain untouched.
- Persist gap analysis output in a stable, discoverable location within the feature directory.

### Parallel Opportunities
- T012 can land independently; T013-T015 can be developed in parallel with shared helpers.

### Dependencies
- None (feature-specific wiring).

### Risks & Mitigations
- Risk: External tool availability. Mitigation: fail gracefully with clear guidance when generator tools are missing.

---

## Work Package WP05: Documentation Mission Validation & Tests (Priority: P2)

**Goal**: Enforce documentation mission requirements during validation and acceptance, with tests.
**Independent Test**: Validation/acceptance fails when documentation state or gap analysis artifacts are missing.
**Prompt**: `/tasks/WP05-doc-mission-validation-tests.md`

### Included Subtasks
- [ ] T016 Add documentation-mission checks to validation and acceptance flows (presence/recency of state + gap analysis).
- [ ] T017 Update mission configuration or validators to surface documentation-specific requirements.
- [ ] T018 Add/adjust tests covering documentation mission validation and acceptance behavior.

### Implementation Notes
- Ensure acceptance/validation errors are actionable and mention remediation steps.

### Parallel Opportunities
- T016 and T017 can proceed in parallel after understanding existing validation hooks.

### Dependencies
- Depends on WP04.

### Risks & Mitigations
- Risk: Overly strict validation blocks workflows. Mitigation: keep checks mission-scoped and allow explicit bypass if existing CLI supports it.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03 → WP04 → WP05.
- **Parallelization**: WP04 can proceed in parallel with WP02/WP03 if needed, but WP05 depends on WP04.
- **MVP Scope**: WP01 + WP02 + WP03 (cleanup and consolidation). Documentation mission wiring is P2.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Update tests/utilities to use packaged script paths | WP01 | P1 | Yes |
| T002 | Remove root scripts and update docs/help text | WP01 | P1 | No |
| T003 | Align base plan template guidance | WP01 | P1 | Yes |
| T004 | Create shared task helper module | WP02 | P1 | No |
| T005 | Update tasks_support + scripts task_helpers to use shared module | WP02 | P1 | Yes |
| T006 | Update tasks_cli usage to consolidated helpers | WP02 | P1 | Yes |
| T007 | Add tests for worktree/conflict parity | WP02 | P1 | No |
| T008 | Extract shared acceptance core | WP03 | P1 | No |
| T009 | Update acceptance.py to use core | WP03 | P1 | Yes |
| T010 | Update acceptance_support.py to use core | WP03 | P1 | Yes |
| T011 | Add acceptance parity tests | WP03 | P1 | No |
| T012 | Initialize documentation state during specify | WP04 | P2 | No |
| T013 | Run gap analysis during plan | WP04 | P2 | Yes |
| T014 | Run gap analysis during research | WP04 | P2 | Yes |
| T015 | Add generator detection/config to plan | WP04 | P2 | Yes |
| T016 | Add validation/acceptance checks for doc missions | WP05 | P2 | No |
| T017 | Update mission config/validators for doc mission checks | WP05 | P2 | Yes |
| T018 | Add doc mission validation/accept tests | WP05 | P2 | No |
