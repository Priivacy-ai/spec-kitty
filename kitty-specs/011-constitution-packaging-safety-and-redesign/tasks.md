# Tasks: Constitution Packaging Safety and Redesign

**Feature**: 011-constitution-packaging-safety-and-redesign
**Branch**: `011-constitution-packaging-safety-and-redesign`
**Status**: Planned
**Priority**: P0 (Emergency release)

## Overview

Emergency 0.10.x release with 4 critical goals across 2 parallel implementation tracks:

**Track 1 - Critical Safety (P0)**:
- Segregate template source code from project instances (`.kittify/` → `src/specify_cli/`)
- Fix upgrade migrations for 0.6.4+ users
- Remove mission-specific constitution system

**Track 2 - UX Improvements (P1)**:
- Fix Windows dashboard with psutil
- Redesign constitution command with phase-based discovery

**Dependencies**: Track 1 must complete template relocation before Track 2 updates constitution command template.

---

## Work Package Summary

| ID | Title | Track | Subtasks | Priority | Dependencies |
|----|-------|-------|----------|----------|--------------|
| WP01 | Template Relocation & Packaging | Track 1 | T001-T009 | P0 | None |
| WP02 | Migration Repairs & Graceful Handling | Track 1 | T010-T016 | P0 | None [P] |
| WP03 | Mission Constitution Removal | Track 1 | T017-T021 | P0 | None [P] |
| WP04 | Windows Dashboard psutil Refactor | Track 2 | T022-T027 | P1 | None [P] |
| WP05 | Constitution Command Redesign | Track 2 | T028-T033 | P1 | WP01 (template location) |
| WP06 | Integration Testing & Validation | Both | T034-T040 | P0 | WP01-WP05 |

**[P] = Parallelizable** - Can run concurrently with other [P] packages
**Total Subtasks**: 40

---

## Setup Work Packages

None required - all design artifacts complete.

---

## Foundational Work Packages

### WP01: Template Relocation & Packaging ⚡ CRITICAL ⚡

**Goal**: Move all template sources from `.kittify/` to `src/specify_cli/` and eliminate packaging contamination

**Priority**: P0 - MUST complete before Track 2 constitution work
**Status**: `planned`
**Prompt**: [tasks/WP01-template-relocation-packaging.md](tasks/WP01-template-relocation-packaging.md)

**Success Criteria**:
- All templates moved to `src/specify_cli/templates/`, `src/specify_cli/missions/`, `src/specify_cli/scripts/`
- `pyproject.toml` force-includes removed (lines 86-110)
- `template/manager.py` loads from package resources, not `.kittify/`
- Build package and verify: zero `.kittify/` or `memory/constitution.md` entries in wheel

**Subtasks**:
- [ ] T001: Audit codebase for `.kittify/` references
- [ ] T002: Move `.kittify/templates/` → `src/specify_cli/templates/`
- [ ] T003: Move `.kittify/missions/` → `src/specify_cli/missions/`
- [ ] T004: Move `.kittify/scripts/` → `src/specify_cli/scripts/` (if exists)
- [ ] T005: Update `src/specify_cli/template/manager.py` to load from `src/specify_cli/*`
- [ ] T006: Remove `.kittify/*` force-includes from `pyproject.toml` (lines 86-89, 94-97, 109-110)
- [ ] T007: Verify spec-kitty's own `.kittify/` still works for dogfooding
- [ ] T008: Build wheel and inspect contents (verify no contamination)
- [ ] T009: Test `spec-kitty init` from installed package

**Risks**:
- Breaking template loading for existing code
- Worktree symlinks may break if paths not updated
- Package size could increase if src/ structure not clean

**Dependencies**: None (can start immediately)
**Parallel**: NO - Other tracks may need template locations

---

## Feature Work Packages (by User Story)

### WP02: Migration Repairs & Graceful Handling

**Goal**: Fix 4 existing migrations to handle missing files gracefully + add new constitution cleanup migration

**Priority**: P0 - Critical for upgrade path reliability
**Status**: `planned`
**Prompt**: [tasks/WP02-migration-repairs-graceful-handling.md](tasks/WP02-migration-repairs-graceful-handling.md)

**Success Criteria**:
- All 4 migrations (`m_0_7_3`, `m_0_10_2`, `m_0_10_6`, `m_0_10_0`) have graceful `can_apply()` and robust `apply()`
- New `m_0_10_12_constitution_cleanup.py` migration created and registered
- All migrations are idempotent (can run multiple times safely)
- Upgrade from 0.6.4 → 0.10.12 completes without manual intervention

**Subtasks**:
- [ ] T010: Fix `m_0_7_3_update_scripts.py` - graceful handling when bash scripts missing
- [ ] T011: Fix `m_0_10_6_workflow_simplification.py` - copy templates before validation
- [ ] T012: Fix `m_0_10_2_update_slash_commands.py` - explicit .toml file removal
- [ ] T013: Fix `m_0_10_0_python_only.py` - verify explicit `.kittify/scripts/tasks/` cleanup
- [ ] T014: Create `m_0_10_12_constitution_cleanup.py` - remove mission constitution directories
- [ ] T015: Register new migration in migration registry
- [ ] T016: Test migration idempotency (run twice, verify same result)

**Risks**:
- Breaking existing upgrade paths
- Data loss if migrations too aggressive
- Overlapping migration cleanup causing failures

**Dependencies**: None (migrations are independent of template relocation)
**Parallel**: YES [P] - Can run alongside WP03, WP04

---

### WP03: Mission Constitution Removal

**Goal**: Remove mission-specific constitution system entirely (code + directory structure)

**Priority**: P0 - Required for architectural cleanup
**Status**: `planned`
**Prompt**: [tasks/WP03-mission-constitution-removal.md](tasks/WP03-mission-constitution-removal.md)

**Success Criteria**:
- `src/specify_cli/mission.py` no longer has `constitution_dir` property
- `src/specify_cli/manifest.py` no longer scans for constitution files
- `.kittify/missions/*/constitution/` directories deleted (template sources after WP01 move)
- All tests updated to reflect single project-level constitution model
- No code references to mission constitutions remain

**Subtasks**:
- [ ] T017: Remove `constitution_dir` property from `src/specify_cli/mission.py` (line 247-249)
- [ ] T018: Remove constitution scanning from `src/specify_cli/manifest.py` (lines 70-74)
- [ ] T019: Delete `src/specify_cli/missions/*/constitution/` directories (after WP01 template move)
- [ ] T020: Update tests to remove mission constitution references
- [ ] T021: Grep codebase for "mission.*constitution" and clean up any remaining references

**Risks**:
- Breaking code that relies on mission constitutions
- User confusion about where constitutions live
- Documentation may still reference old system

**Dependencies**: WP01 (templates moved first)
**Parallel**: YES [P] - Can run alongside WP02, WP04

---

### WP04: Windows Dashboard psutil Refactor

**Goal**: Replace POSIX-only signal handling with cross-platform psutil for Windows support

**Priority**: P1 - Fixes Windows ERR_EMPTY_RESPONSE issue (#71)
**Status**: `planned`
**Prompt**: [tasks/WP04-windows-dashboard-psutil-refactor.md](tasks/WP04-windows-dashboard-psutil-refactor.md)

**Success Criteria**:
- `psutil>=5.9.0` added to `pyproject.toml` dependencies
- All `os.kill()` and `signal.SIGKILL` usage in `dashboard/lifecycle.py` replaced with psutil
- Dashboard starts successfully on Windows 10/11
- Dashboard serves HTML content (not empty response) on Windows
- Process termination works gracefully across all platforms

**Subtasks**:
- [ ] T022: Add `psutil>=5.9.0` to `pyproject.toml` dependencies
- [ ] T023: Replace `os.kill(pid, 0)` with `psutil.Process(pid).is_running()` (line 100)
- [ ] T024: Replace `signal.SIGKILL` with `psutil.Process(pid).kill()` (lines 188, 289, 354, 381, 470, 499)
- [ ] T025: Replace `signal.SIGTERM` with `psutil.Process(pid).terminate()` (line 464)
- [ ] T026: Add proper exception handling for `psutil.NoSuchProcess` and `psutil.TimeoutExpired`
- [ ] T027: Update imports (remove `signal`, add `psutil`)

**Risks**:
- psutil may behave differently across platforms
- Process termination timing may change
- Existing dashboard instances may need manual kill after upgrade

**Dependencies**: None
**Parallel**: YES [P] - Independent of other work

---

### WP05: Constitution Command Redesign

**Goal**: Replace placeholder-filling approach with phase-based interactive discovery workflow

**Priority**: P1 - Improves constitution UX, makes it optional
**Status**: `planned`
**Prompt**: [tasks/WP05-constitution-command-redesign.md](tasks/WP05-constitution-command-redesign.md)

**Success Criteria**:
- Constitution command template updated with 4-phase discovery workflow
- Each phase has skip option
- Minimal path (3-5 questions) produces 1-page constitution
- Comprehensive path (8-12 questions) produces 2-3 page constitution
- Plan command gracefully skips constitution check if no constitution exists
- All spec-kitty commands work without constitution

**Subtasks**:
- [ ] T028: Update `src/specify_cli/templates/command-templates/constitution.md` with phase-based workflow
- [ ] T029: Implement Phase 1 (Technical Standards) with 4 questions + skip option
- [ ] T030: Implement Phase 2 (Code Quality) with 4 questions + skip option
- [ ] T031: Implement Phase 3 (Tribal Knowledge) with 4 questions + skip option
- [ ] T032: Implement Phase 4 (Governance) with 4 questions + skip option
- [ ] T033: Add summary presentation and user confirmation before writing

**Risks**:
- Users may skip all phases and have no constitution
- Phase questions may not cover all project needs
- Backward compatibility with existing constitutions

**Dependencies**: WP01 (template must be moved to `src/specify_cli/` first)
**Parallel**: NO - Depends on WP01 template relocation

---

## Polish & Integration Work Packages

### WP06: Integration Testing & Validation

**Goal**: Verify all 4 feature goals work together end-to-end across platforms

**Priority**: P0 - Gate for release
**Status**: `planned`
**Prompt**: [tasks/WP06-integration-testing-validation.md](tasks/WP06-integration-testing-validation.md)

**Success Criteria**:
- Package build produces clean wheel (no `.kittify/` or filled constitutions)
- Upgrade path 0.6.4 → 0.10.12 completes successfully in clean VM
- Dashboard works on Windows 10/11 (starts, serves HTML, shuts down)
- Constitution workflow tested (minimal + comprehensive paths)
- All spec-kitty commands work without constitution
- Dogfooding workflow tested (dev fills constitution, builds package, verifies clean)

**Subtasks**:
- [ ] T034: Create test script for package inspection (`unzip -l dist/*.whl | grep -E ...`)
- [ ] T035: Test upgrade path in Docker container (0.6.4 → 0.10.12)
- [ ] T036: Test dashboard on Windows (smoke test: start, access, shutdown)
- [ ] T037: Test constitution minimal workflow (3-5 questions, 1 page output)
- [ ] T038: Test constitution comprehensive workflow (8-12 questions, 2-3 pages)
- [ ] T039: Test all spec-kitty commands without constitution (specify, plan, tasks, implement)
- [ ] T040: Test dogfooding workflow (fill constitution, build, inspect package)

**Risks**:
- Platform-specific issues may not surface in testing
- Migration edge cases may only appear with real 0.6.4 projects
- Windows testing requires actual Windows system (not WSL)

**Dependencies**: WP01-WP05 (all features complete)
**Parallel**: NO - Must run after all implementation complete

---

## Subtask Inventory

### Track 1: Critical Safety (T001-T021)

**Template Relocation (T001-T009)**:
- T001: Audit codebase for `.kittify/` references
- T002: Move `.kittify/templates/` → `src/specify_cli/templates/`
- T003: Move `.kittify/missions/` → `src/specify_cli/missions/`
- T004: Move `.kittify/scripts/` → `src/specify_cli/scripts/` (if exists)
- T005: Update `src/specify_cli/template/manager.py` to load from `src/specify_cli/*`
- T006: Remove `.kittify/*` force-includes from `pyproject.toml`
- T007: Verify spec-kitty's own `.kittify/` still works
- T008: Build wheel and inspect contents
- T009: Test `spec-kitty init` from installed package

**Migration Repairs (T010-T016)**:
- T010: Fix `m_0_7_3_update_scripts.py` graceful handling
- T011: Fix `m_0_10_6_workflow_simplification.py` copy before validate
- T012: Fix `m_0_10_2_update_slash_commands.py` .toml removal
- T013: Fix `m_0_10_0_python_only.py` tasks/ cleanup verification
- T014: Create `m_0_10_12_constitution_cleanup.py` migration
- T015: Register new migration
- T016: Test migration idempotency

**Mission Constitution Removal (T017-T021)**:
- T017: Remove `constitution_dir` property from `mission.py`
- T018: Remove constitution scanning from `manifest.py`
- T019: Delete `missions/*/constitution/` directories
- T020: Update tests
- T021: Grep and cleanup remaining references

### Track 2: UX Improvements (T022-T033)

**Windows Dashboard (T022-T027)**:
- T022: Add psutil dependency
- T023: Replace `os.kill(pid, 0)` with psutil
- T024: Replace `signal.SIGKILL` with psutil (6 locations)
- T025: Replace `signal.SIGTERM` with psutil
- T026: Add psutil exception handling
- T027: Update imports

**Constitution Redesign (T028-T033)**:
- T028: Update constitution command template
- T029: Implement Phase 1 (Technical Standards)
- T030: Implement Phase 2 (Code Quality)
- T031: Implement Phase 3 (Tribal Knowledge)
- T032: Implement Phase 4 (Governance)
- T033: Add summary and confirmation

### Integration (T034-T040)

**Testing & Validation (T034-T040)**:
- T034: Package inspection test script
- T035: Upgrade path test (Docker)
- T036: Windows dashboard smoke test
- T037: Constitution minimal workflow test
- T038: Constitution comprehensive workflow test
- T039: Commands-without-constitution test
- T040: Dogfooding workflow test

---

## Implementation Strategy

### Phase 1: Foundational (Sequential)
1. **WP01**: Template Relocation (MUST complete first)
   - Moves all templates to `src/specify_cli/`
   - Unblocks WP05 constitution template update

### Phase 2: Parallel Implementation
**Track 1 (P0)**:
2. **WP02**: Migration Repairs [P]
3. **WP03**: Mission Constitution Removal [P] (depends on WP01 for template location)

**Track 2 (P1)**:
4. **WP04**: Windows Dashboard [P]
5. **WP05**: Constitution Redesign (depends on WP01 for template location)

### Phase 3: Integration (Sequential)
6. **WP06**: Integration Testing & Validation
   - Runs after all implementation complete
   - Gates release

---

## Coordination & Sync Points

**Sync Point 1** (After WP01):
- Templates moved to `src/specify_cli/`
- WP03 can delete mission constitution directories
- WP05 can update constitution command template
- All other work packages can reference stable template locations

**Sync Point 2** (Before WP06):
- WP02, WP03, WP04, WP05 all complete
- Code review complete
- Ready for integration testing

**Conflict Resolution**:
- `pyproject.toml`: WP01 removes force-includes, WP04 adds psutil. Different sections, no conflict.
- Templates: WP01 moves directory, WP05 updates content. Sequential, no conflict.

---

## MVP Scope Recommendation

**Minimum viable for 0.10.12 release**:
- **WP01**: Template Relocation (CRITICAL - prevents packaging contamination)
- **WP02**: Migration Repairs (CRITICAL - unblocks upgrade path)
- **WP06**: Integration Testing (CRITICAL - validates release)

**Can defer to 0.10.13** (if time pressure):
- **WP03**: Mission Constitution Removal (cleanup, not breaking)
- **WP04**: Windows Dashboard (P2 priority, platform-specific)
- **WP05**: Constitution Redesign (UX improvement, not critical)

However, all 6 work packages are recommended for a complete emergency release addressing all 4 stated goals.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Template relocation breaks existing code | Medium | High | Comprehensive grep audit, test from installed package | WP01 |
| Migration fails on edge cases | Medium | High | Test with real 0.6.4 project in VM | WP02 |
| Windows dashboard still broken | Low | Medium | Test on actual Windows 10/11 | WP04 |
| Package still includes wrong files | Low | Critical | Automated wheel inspection test | WP01, WP06 |
| Breaking changes to user workflows | Low | High | Integration testing across all commands | WP06 |

---

## Progress Tracking

- [ ] **WP01**: Template Relocation & Packaging
- [ ] **WP02**: Migration Repairs & Graceful Handling
- [ ] **WP03**: Mission Constitution Removal
- [ ] **WP04**: Windows Dashboard psutil Refactor
- [ ] **WP05**: Constitution Command Redesign
- [ ] **WP06**: Integration Testing & Validation

**Legend**: `[ ]` planned | `[▶]` doing | `[R]` for_review | `[✓]` done

---

## Next Steps

1. Review this task breakdown with stakeholders
2. Assign WP01 to start immediately (unblocks other work)
3. Assign WP02, WP04 in parallel once WP01 progresses
4. Assign WP03, WP05 after WP01 completes
5. Run WP06 integration testing before merging to main

**Estimated Effort**: 6 work packages, 40 subtasks, 2 parallel tracks
**Critical Path**: WP01 → WP05 → WP06 (template relocation gates constitution redesign)
**Recommended Next Command**: `/spec-kitty.implement WP01` (start with template relocation)
