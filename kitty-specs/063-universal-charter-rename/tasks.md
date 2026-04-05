# Tasks: Universal Charter Rename

**Feature**: 063-universal-charter-rename
**Created**: 2026-04-04
**Branch**: main → main

## Subtask Index

| ID | Description | WP | Parallel |
|----|------------|-----|----------|
| T001 | Rename src/constitution/ → src/charter/ directory | WP01 | [P] |
| T002 | Update class/function names in src/charter/ modules | WP01 | |
| T003 | Rename src/specify_cli/constitution/ → src/specify_cli/charter/ | WP01 | [P] |
| T004 | Update class/function names in src/specify_cli/charter/ | WP01 | |
| T005 | Update __init__.py exports in both packages | WP01 | |
| T006 | Rename CLI command file + update typer app name/help | WP02 | |
| T007 | Update CLI registration in commands/__init__.py | WP02 | |
| T008 | Rename dashboard module + update function names | WP02 | [P] |
| T009 | Update state_contract.py constitution references | WP02 | [P] |
| T010 | Update worktree.py setup_feature_directory() | WP02 | [P] |
| T011 | Rename copy_constitution_templates() in template/manager.py | WP02 | [P] |
| T012 | Update init.py constitution setup references | WP02 | |
| T013 | Update all import statements across codebase | WP03 | |
| T014 | Update pyproject.toml package configuration | WP03 | |
| T015 | Update importlib.import_module references | WP03 | |
| T016 | Verify mypy --strict passes on renamed modules | WP03 | |
| T017 | Smoke test: verify imports resolve correctly | WP03 | |
| T018 | Rename src/doctrine/constitution/ → src/doctrine/charter/ | WP04 | [P] |
| T019 | Rename skill directory + update SKILL.md + references | WP04 | [P] |
| T020 | Rename command template file + update content | WP04 | [P] |
| T021 | Rename doctrine procedure file + update content | WP04 | [P] |
| T022 | Update software-dev mission templates | WP04 | |
| T023 | Update software-dev action guidelines (4 files) | WP04 | |
| T024 | Update documentation + research mission templates | WP04 | |
| T025 | Rename command files in all 12 agent directories | WP05 | |
| T026 | Rename skill directories in all agent directories | WP05 | |
| T027 | Update .kittify/skills-manifest.json | WP05 | |
| T028 | Update .kittify/AGENTS.md + overrides/AGENTS.md | WP05 | [P] |
| T029 | Update .gitignore entries | WP05 | [P] |
| T030 | Rename .kittify/constitution/ → .kittify/charter/ (dev repo) | WP05 | |
| T031 | Update CLAUDE.md constitution references | WP05 | [P] |
| T032 | Convert m_0_10_12 + m_0_13_0 to stubs | WP06 | [P] |
| T033 | Convert m_2_0_0 + m_2_0_2 + m_2_1_2 to stubs | WP06 | [P] |
| T034 | Add _LEGACY_MIGRATION_ID_MAP to metadata.py | WP06 | |
| T035 | Create m_3_1_1 Phase 1: layout normalization | WP06 | |
| T036 | Create m_3_1_1 Phase 2: content rewriting | WP06 | |
| T037 | Create m_3_1_1 Phases 3-4: agent artifacts + metadata | WP06 | |
| T038 | Verify migration registration and ordering | WP06 | |
| T039 | Rename tests/constitution/ → tests/charter/ + update content | WP07 | |
| T040 | Rename 8 additional test files + update content | WP07 | |
| T041 | Update tests/git_ops/test_worktree.py | WP07 | [P] |
| T042 | Write charter-rename migration tests (layouts A, B, C) | WP07 | |
| T043 | Write content rewriting + agent prompt tests | WP07 | |
| T044 | Write metadata normalization tests | WP07 | |
| T045 | Write idempotency + partial state tests | WP07 | |
| T046 | Rename 4 doc files with "constitution" in filename | WP08 | |
| T047 | Update README.md + docs/reference/ files | WP08 | |
| T048 | Update glossary/ files | WP08 | [P] |
| T049 | Update remaining docs (development, how-to, examples, architecture) | WP08 | [P] |
| T050 | Update .kittify/memory notes + src/kernel/ files | WP08 | [P] |
| T051 | Run acceptance verification gate | WP08 | |

## Work Packages

### Phase 1: Package & Module Renames (parallel)

#### WP01: Core Package Renames
- **Priority**: P0 (foundation)
- **Subtasks**: T001, T002, T003, T004, T005
- **Dependencies**: none
- **Prompt**: [tasks/WP01-core-package-renames.md](tasks/WP01-core-package-renames.md)
- **Estimated size**: ~350 lines
- **Summary**: Rename `src/constitution/` and `src/specify_cli/constitution/` packages to charter equivalents. Update all class names, function names, docstrings, and string literals within the renamed modules.
- **Success criteria**: Both packages exist at charter paths with all internal references updated. No "constitution" in any file within these directories.
- **Risks**: Symbol renames may break downstream imports (addressed in WP03).

#### WP02: CLI, Dashboard, Worktree & Runtime Renames
- **Priority**: P0 (foundation)
- **Subtasks**: T006, T007, T008, T009, T010, T011, T012
- **Dependencies**: none
- **Prompt**: [tasks/WP02-cli-dashboard-runtime-renames.md](tasks/WP02-cli-dashboard-runtime-renames.md)
- **Estimated size**: ~450 lines
- **Summary**: Rename CLI command module, dashboard path resolver, worktree setup code, template manager, and init code. Update typer app registration.
- **Success criteria**: `spec-kitty charter` commands are registered. Worktree setup uses charter paths. No "constitution" in any modified file.
- **Risks**: CLI registration change affects all subcommands; verify none are lost.

### Phase 2: Integration & Build (sequential after Phase 1)

#### WP03: Import, Build & Cross-Reference Updates
- **Priority**: P0 (integration)
- **Subtasks**: T013, T014, T015, T016, T017
- **Dependencies**: WP01, WP02
- **Prompt**: [tasks/WP03-import-build-updates.md](tasks/WP03-import-build-updates.md)
- **Estimated size**: ~350 lines
- **Summary**: Update all import statements across the codebase that reference constitution packages. Update pyproject.toml. Verify compilation and type checking.
- **Success criteria**: `mypy --strict` passes on charter modules. No import errors.

### Phase 3: Doctrine, Skills & Agent Artifacts (parallel with Phase 2)

#### WP04: Doctrine, Skills, Templates & Mission Artifacts
- **Priority**: P1
- **Subtasks**: T018, T019, T020, T021, T022, T023, T024
- **Dependencies**: none
- **Prompt**: [tasks/WP04-doctrine-skills-templates.md](tasks/WP04-doctrine-skills-templates.md)
- **Estimated size**: ~450 lines
- **Summary**: Rename doctrine defaults directory, skill package, command template, and procedure file. Update all 9 doctrine mission artifact files containing "constitution".
- **Success criteria**: Skill deploys as `spec-kitty-charter-doctrine`. All mission templates reference charter. No "constitution" in doctrine/ or missions/.

#### WP05: Agent Artifacts & Configuration
- **Priority**: P1
- **Subtasks**: T025, T026, T027, T028, T029, T030, T031
- **Dependencies**: WP04
- **Prompt**: [tasks/WP05-agent-artifacts-config.md](tasks/WP05-agent-artifacts-config.md)
- **Estimated size**: ~400 lines
- **Summary**: Rename agent command/skill files across all 12 directories. Update skills manifest, AGENTS.md, .gitignore, CLAUDE.md, and rename the dev repo's .kittify/constitution/ directory.
- **Success criteria**: All agent directories use charter naming. Dev repo .kittify/ uses charter layout. No "constitution" in config files.

### Phase 4: Migration System (parallel with Phase 3)

#### WP06: Migration Overhaul
- **Priority**: P0 (critical path)
- **Subtasks**: T032, T033, T034, T035, T036, T037, T038
- **Dependencies**: WP01
- **Prompt**: [tasks/WP06-migration-overhaul.md](tasks/WP06-migration-overhaul.md)
- **Estimated size**: ~550 lines
- **Summary**: Convert 5 old migrations to no-op stubs. Add metadata normalization to metadata.py. Create comprehensive charter-rename migration handling Layouts A/B/C, content rewriting, agent artifacts, and metadata normalization.
- **Success criteria**: Old stubs contain zero "constitution". New migration handles all layouts. Metadata normalization bridges old IDs.
- **Risks**: Most complex WP. Charter-rename must handle edge cases (partial state, concurrent runs, Windows paths).

### Phase 5: Testing (after Phases 2 + 4)

#### WP07: Test Overhaul
- **Priority**: P1
- **Subtasks**: T039, T040, T041, T042, T043, T044, T045
- **Dependencies**: WP01, WP02, WP03, WP06
- **Prompt**: [tasks/WP07-test-overhaul.md](tasks/WP07-test-overhaul.md)
- **Estimated size**: ~500 lines
- **Summary**: Rename all test directories and files. Update test content. Write comprehensive tests for the new charter-rename migration and metadata normalization.
- **Success criteria**: `pytest tests/ -x -q` passes. 90%+ coverage on new migration code.

### Phase 6: Documentation & Verification (after all)

#### WP08: Documentation & Acceptance
- **Priority**: P2
- **Subtasks**: T046, T047, T048, T049, T050, T051
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07
- **Prompt**: [tasks/WP08-documentation-acceptance.md](tasks/WP08-documentation-acceptance.md)
- **Estimated size**: ~400 lines
- **Summary**: Rename doc files, update 30+ documentation files with 100+ constitution references, update glossary, and run the acceptance verification gate.
- **Success criteria**: Acceptance grep returns zero matches (outside 2 bounded exception files). All filename checks pass.

## Dependency Graph

```
WP01 ──┐
       ├──→ WP03 ──┐
WP02 ──┘            │
                    ├──→ WP07 ──┐
WP04 ──→ WP05      │           ���──→ WP08
                    │           │
WP06 ───────────────┘──────���────┘
```

## Parallelization Opportunities

- **Phase 1**: WP01 + WP02 + WP04 can run in parallel (no shared files)
- **Phase 2-4**: WP03 (after WP01+WP02), WP05 (after WP04), WP06 (after WP01) can run in parallel
- **Phase 5**: WP07 requires WP01+WP02+WP03+WP06
- **Phase 6**: WP08 requires all

**Maximum parallelism**: 3 agents (WP01 + WP02 + WP04 simultaneously)

## Requirement Coverage

| Requirement | Work Package(s) |
|------------|----------------|
| FR-001 | WP02 |
| FR-002, FR-003 | WP06 |
| FR-004, FR-005 | WP04, WP05 |
| FR-006, FR-007, FR-008, FR-009 | WP06 |
| FR-010 | WP01, WP03 |
| FR-011 | WP03 |
| FR-012 | WP04 |
| FR-013 | WP02 |
| FR-014 | WP05 |
| FR-015 | WP06 |
| FR-016 | WP02 |
| FR-017 | WP06 |
| FR-018 | WP06 |
| FR-019 | WP06 |
| FR-020 | WP06 |
| NFR-001, NFR-002 | WP08 |
| NFR-003 | WP06 |
| NFR-004 | WP07 |
| NFR-005 | WP03 |
