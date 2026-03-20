# Tasks: Agent Skills Installer Infrastructure

**Feature**: 042-agent-skills-installer-infrastructure
**Date**: 2026-03-20
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Work Package Overview

| WP | Title | Subtasks | Priority | Dependencies | Est. Lines |
|----|-------|----------|----------|-------------|------------|
| WP01 | Canonical Agent Surface Config | T001–T007 | P1 | — | ~450 |
| WP02 | Skill Root Resolution | T008–T012 | P1 | WP01 | ~350 |
| WP03 | Skills Manifest CRUD | T013–T017 | P2 | — | ~350 |
| WP04 | Post-Init Verification | T018–T020 | P2 | WP02, WP03 | ~300 |
| WP05 | Init Wiring | T021–T027 | P1 | WP01, WP02, WP03, WP04 | ~500 |
| WP06 | Agent Config Sync Skill Awareness | T028–T032 | P3 | WP02, WP03 | ~350 |
| WP07 | Upgrade Migration | T033–T036 | P2 | WP01, WP02, WP03, WP04 | ~400 |
| WP08 | Asset Generator Refactor | T037–T039 | P1 | WP01 | ~250 |
| WP09 | Integration Tests and Final Validation | T040–T044 | P1 | WP05, WP06, WP07, WP08 | ~450 |

## Parallelization Waves

```
Wave 1: WP01 + WP03 (independent, parallel)
Wave 2: WP02 + WP08 (both depend on WP01 only, parallel)
Wave 3: WP04 + WP06 (both depend on WP02+WP03, parallel)
Wave 4: WP05 + WP07 (both depend on WP01–WP04, parallel)
Wave 5: WP09 (depends on all, final validation)
```

## Subtask Registry

| ID | Description | WP | Parallel? |
|----|-------------|-----|----------|
| T001 | Create agent_surface.py with DistributionClass, WrapperConfig, AgentSurface dataclasses | WP01 | No |
| T002 | Populate AGENT_SURFACE_CONFIG with all 12 agents per PRD 8.1 matrix | WP01 | No |
| T003 | Implement derived view functions | WP01 | No |
| T004 | Wire derived AGENT_COMMAND_CONFIG into config.py | WP01 | No |
| T005 | Wire derived AGENT_DIRS and AGENT_DIR_TO_KEY into directories.py | WP01 | No |
| T006 | Update core/__init__.py and agent_utils/__init__.py re-exports | WP01 | No |
| T007 | Unit tests for agent surface config, derived views, PRD matrix validation | WP01 | No |
| T008 | Create src/specify_cli/skills/ package with __init__.py | WP02 | No |
| T009 | Create roots.py with resolve_skill_roots() function signature | WP02 | No |
| T010 | Implement auto and shared mode resolution logic | WP02 | No |
| T011 | Implement native and wrappers-only mode resolution logic | WP02 | No |
| T012 | Parametrized unit tests for all modes × agent combinations | WP02 | No |
| T013 | Create manifest.py with ManagedFile and SkillsManifest dataclasses | WP03 | [P] |
| T014 | Implement write_manifest() YAML serialization | WP03 | No |
| T015 | Implement load_manifest() YAML deserialization with error handling | WP03 | No |
| T016 | Implement compute_file_hash() SHA-256 helper | WP03 | [P] |
| T017 | Unit tests for manifest round-trip, missing file, corruption | WP03 | No |
| T018 | Create verification.py with VerificationResult dataclass | WP04 | No |
| T019 | Implement verify_installation() with all four checks | WP04 | No |
| T020 | Unit tests for pass case and each failure mode | WP04 | No |
| T021 | Add --skills typer Option to init command signature | WP05 | No |
| T022 | Validate --skills flag value (auto/native/shared/wrappers-only) | WP05 | No |
| T023 | Add skill root resolution step after wrapper generation | WP05 | No |
| T024 | Add skill root directory creation with .gitkeep markers | WP05 | No |
| T025 | Add manifest collection, hashing, and writing step | WP05 | No |
| T026 | Add verification step with rich error/warning display | WP05 | No |
| T027 | Add tracker steps for skill installation progress | WP05 | No |
| T028 | Load manifest in sync_agents if exists | WP06 | No |
| T029 | Implement skill root repair for configured agents | WP06 | No |
| T030 | Implement shared root protection logic during orphan removal | WP06 | No |
| T031 | Update manifest after sync changes | WP06 | No |
| T032 | Unit tests for sync repair and shared root protection | WP06 | No |
| T033 | Create m_2_1_0_agent_surface_manifest.py migration class | WP07 | No |
| T034 | Implement detect() and can_apply() methods | WP07 | No |
| T035 | Implement apply() — manifest from current state + empty skill roots | WP07 | No |
| T036 | Migration tests with fixture projects (multiple agent configs) | WP07 | No |
| T037 | Update asset_generator.py import to use get_agent_surface | WP08 | No |
| T038 | Refactor generate_agent_assets and render_command_template to use AgentSurface | WP08 | No |
| T039 | Backward compatibility test — byte-exact wrapper comparison for all 12 agents | WP08 | No |
| T040 | End-to-end init integration test with multiple agent combinations and --skills modes | WP09 | No |
| T041 | Backward compat wrapper comparison across all 12 agents (golden file test) | WP09 | No |
| T042 | mypy --strict validation on all new modules | WP09 | [P] |
| T043 | ruff check validation on all new modules | WP09 | [P] |
| T044 | Full test suite run and coverage report for new code | WP09 | No |

---

## WP01 — Canonical Agent Surface Config

**Goal**: Create `AGENT_SURFACE_CONFIG` as the single canonical agent registry and wire derived compatibility views for `AGENT_COMMAND_CONFIG`, `AGENT_DIRS`, and `AGENT_DIR_TO_KEY`.

**Priority**: P1 — everything else depends on this.

**Subtasks**: T001, T002, T003, T004, T005, T006, T007

**Dependencies**: None

**Requirements Refs**: FR-001, FR-002, FR-003, FR-018, NFR-001, NFR-004, NFR-005, C-006

**Implementation sketch**:
1. Create `src/specify_cli/core/agent_surface.py` with dataclasses and 12-entry config dict
2. Wire `config.py` to derive AGENT_COMMAND_CONFIG from the canonical source
3. Wire `directories.py` to derive AGENT_DIRS and AGENT_DIR_TO_KEY from the canonical source
4. Update __init__.py re-exports
5. Unit tests verify all 12 agents, distribution class correctness, and byte-exact derived view equivalence

**Risks**: Circular import if agent_surface.py imports from config.py. Mitigate by ensuring agent_surface.py is self-contained (no imports from sibling config modules).

**Prompt file**: [tasks/WP01-canonical-agent-surface-config.md](tasks/WP01-canonical-agent-surface-config.md)

---

## WP02 — Skill Root Resolution

**Goal**: Implement pure-logic skill root resolver that computes the minimum set of project skill root directories for a given agent selection and `--skills` mode.

**Priority**: P1

**Subtasks**: T008, T009, T010, T011, T012

**Dependencies**: WP01 (needs DistributionClass and AGENT_SURFACE_CONFIG)

**Requirements Refs**: FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, NFR-002

**Implementation sketch**:
1. Create `src/specify_cli/skills/` package
2. Implement `resolve_skill_roots()` with mode dispatch
3. Exhaustive parametrized tests for all modes × agent combinations

**Prompt file**: [tasks/WP02-skill-root-resolution.md](tasks/WP02-skill-root-resolution.md)

---

## WP03 — Skills Manifest CRUD

**Goal**: Implement the managed install manifest — dataclasses, YAML serialization, content hashing — so init and sync can track what Spec Kitty installed.

**Priority**: P2

**Subtasks**: T013, T014, T015, T016, T017

**Dependencies**: None (parallel with WP01)

**Requirements Refs**: FR-013, FR-023

**Implementation sketch**:
1. Create `src/specify_cli/skills/manifest.py` with ManagedFile and SkillsManifest dataclasses
2. Implement write/load/hash functions
3. Unit tests for round-trip, error handling, hash correctness

**Prompt file**: [tasks/WP03-skills-manifest-crud.md](tasks/WP03-skills-manifest-crud.md)

---

## WP04 — Post-Init Verification

**Goal**: Implement the verification engine that checks installation integrity after init or migration.

**Priority**: P2

**Subtasks**: T018, T019, T020

**Dependencies**: WP02 (skill root expectations), WP03 (manifest reading)

**Requirements Refs**: FR-014, FR-015

**Implementation sketch**:
1. Create `src/specify_cli/skills/verification.py` with VerificationResult
2. Implement four verification checks
3. Unit tests for pass and each distinct failure mode

**Prompt file**: [tasks/WP04-post-init-verification.md](tasks/WP04-post-init-verification.md)

---

## WP05 — Init Wiring

**Goal**: Wire skill root creation, manifest writing, and verification into the `spec-kitty init` command flow.

**Priority**: P1

**Subtasks**: T021, T022, T023, T024, T025, T026, T027

**Dependencies**: WP01, WP02, WP03, WP04

**Requirements Refs**: FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-022

**Implementation sketch**:
1. Add `--skills` flag to init signature
2. After wrapper generation loop, resolve and create skill roots
3. Collect managed files (wrappers + markers), write manifest
4. Run verification, display results
5. Integration tests with `--skills` flag combinations

**Prompt file**: [tasks/WP05-init-wiring.md](tasks/WP05-init-wiring.md)

---

## WP06 — Agent Config Sync Skill Awareness

**Goal**: Extend `spec-kitty agent config sync` to repair missing skill roots and clean up orphaned roots using the manifest.

**Priority**: P3

**Subtasks**: T028, T029, T030, T031, T032

**Dependencies**: WP02 (skill root resolution), WP03 (manifest CRUD)

**Requirements Refs**: FR-016, FR-017, FR-023

**Implementation sketch**:
1. Load manifest in sync_agents
2. Add repair path for missing skill roots
3. Add shared root protection during orphan removal
4. Update manifest after changes
5. Unit tests for each scenario

**Prompt file**: [tasks/WP06-sync-skill-awareness.md](tasks/WP06-sync-skill-awareness.md)

---

## WP07 — Upgrade Migration

**Goal**: Create migration that bootstraps manifest and skill roots for pre-Phase-0 projects.

**Priority**: P2

**Subtasks**: T033, T034, T035, T036

**Dependencies**: WP01, WP02, WP03, WP04

**Requirements Refs**: FR-020, FR-021, FR-022, NFR-006

**Implementation sketch**:
1. Create migration class following existing BaseMigration pattern
2. detect() checks for missing manifest
3. apply() creates manifest from current wrappers + empty skill roots
4. Migration tests with fixture projects of various configurations

**Prompt file**: [tasks/WP07-upgrade-migration.md](tasks/WP07-upgrade-migration.md)

---

## WP08 — Asset Generator Refactor

**Goal**: Update `asset_generator.py` to read wrapper config from `AgentSurface` instead of the dict-based `AGENT_COMMAND_CONFIG`, maintaining byte-exact output.

**Priority**: P1

**Subtasks**: T037, T038, T039

**Dependencies**: WP01

**Requirements Refs**: FR-019, FR-003

**Implementation sketch**:
1. Change import to `get_agent_surface`
2. Replace dict access with dataclass attribute access
3. Byte-exact wrapper comparison test for all 12 agents

**Prompt file**: [tasks/WP08-asset-generator-refactor.md](tasks/WP08-asset-generator-refactor.md)

---

## WP09 — Integration Tests and Final Validation

**Goal**: End-to-end integration tests, golden-file backward compatibility validation, and quality gate checks (mypy, ruff, coverage).

**Priority**: P1

**Subtasks**: T040, T041, T042, T043, T044

**Dependencies**: WP05, WP06, WP07, WP08

**Requirements Refs**: SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007, NFR-003, NFR-004, NFR-005

**Implementation sketch**:
1. End-to-end init tests with multiple agent/skills mode combinations
2. Golden-file wrapper comparison for all 12 agents
3. mypy --strict and ruff check on new code
4. Coverage report validation

**Prompt file**: [tasks/WP09-integration-tests-final-validation.md](tasks/WP09-integration-tests-final-validation.md)

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: approved
- WP02: approved
- WP03: approved
- WP04: planned
- WP06: in_progress
- WP08: approved
<!-- status-model:end -->
