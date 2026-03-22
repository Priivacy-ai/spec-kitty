# Tasks: Documentation Parity Sprint

**Feature**: 056-documentation-parity-sprint
**Mission**: documentation
**Created**: 2026-03-22

---

## Phase 1: Build Infrastructure

### WP01 — DocFX Build Fix and Navigation

**Goal**: Make all existing Divio docs visible on docs.spec-kitty.ai by updating the DocFX build configuration and site navigation.

**Priority**: P0 (blocks all other WPs)
**Dependencies**: none
**Estimated size**: ~250 lines

**Subtasks**:
- [x] T001: Update `docs/docfx.json` to include tutorials/, how-to/, reference/, explanation/ in build output
- [x] T002: Update `docs/toc.yml` top-level navigation to link to all 4 Divio categories
- [x] T003: Update `docs/index.md` homepage with category links and descriptions
- [x] T004: Create missing `docs/how-to/use-operation-history.md` (referenced in toc.yml)
- [x] T005: Verify all toc.yml files in subdirectories have correct file references

**Implementation**: `spec-kitty implement WP01`

---

## Phase 2: How-To Skill Distillations

### WP02 — Glossary Management Guide

**Goal**: Distill glossary-context skill into a user-facing how-to guide.

**Priority**: P1
**Dependencies**: WP01
**Estimated size**: ~300 lines

**Subtasks**:
- [ ] T006: Create `docs/how-to/manage-glossary.md` with glossary concepts (4 scopes, terms, status lifecycle)
- [ ] T007: Document CLI commands (list, conflicts, resolve) with examples and expected output
- [ ] T008: Add strictness modes explanation and when to use each
- [ ] T009: Add seed file editing instructions with YAML schema example
- [ ] T010: Update `docs/how-to/toc.yml` to include new guide

**Implementation**: `spec-kitty implement WP02 --base WP01`

### WP03 — Project Governance Guide

**Goal**: Distill constitution-doctrine skill into a user-facing how-to guide.

**Priority**: P1
**Dependencies**: WP01
**Estimated size**: ~350 lines

**Subtasks**:
- [ ] T011: Create `docs/how-to/setup-governance.md` with the 3-layer model (constitution → config → references)
- [ ] T012: Document interview workflow (minimal vs comprehensive profiles, --defaults flag)
- [ ] T013: Document generation and sync workflow with example commands
- [ ] T014: Document context loading and how it affects workflow actions
- [ ] T015: Add governance anti-patterns section (editing derived files, skipping interview, stale constitution)
- [ ] T016: Update `docs/how-to/toc.yml` to include new guide

**Implementation**: `spec-kitty implement WP03 --base WP01`

### WP04 — Installation Diagnostics Guide

**Goal**: Distill setup-doctor skill into a user-facing how-to guide.

**Priority**: P1
**Dependencies**: WP01
**Estimated size**: ~250 lines

**Subtasks**:
- [ ] T017: Create `docs/how-to/diagnose-installation.md` covering verify-setup command and output interpretation
- [ ] T018: Document common failure patterns (missing skills, missing wrappers, manifest drift, corrupted config)
- [ ] T019: Document recovery steps for each pattern with exact commands
- [ ] T020: Add --remove-orphaned safety warning about shared directories
- [ ] T021: Update `docs/how-to/toc.yml` to include new guide

**Implementation**: `spec-kitty implement WP04 --base WP01`

### WP05 — Review Work Package Guide Update

**Goal**: Expand existing review-work-package.md with runtime-review skill content.

**Priority**: P1
**Dependencies**: WP01
**Estimated size**: ~200 lines

**Subtasks**:
- [x] T022: Add discovery step (finding reviewable WPs with list-tasks --lane for_review)
- [x] T023: Add --feature flag guidance for multi-feature repos
- [x] T024: Add governance context loading step
- [x] T025: Add downstream impact checking with list-dependents command
- [x] T026: Preserve existing content, extend rather than rewrite

**Implementation**: `spec-kitty implement WP05 --base WP01`

---

## Phase 3: Explanation Skill Distillations

### WP06 — Mission System Explanation Update

**Goal**: Expand existing mission-system.md with mission-system skill content.

**Priority**: P1
**Dependencies**: WP01
**Estimated size**: ~350 lines

**Subtasks**:
- [ ] T027: Expand `docs/explanation/mission-system.md` with 4 built-in missions (software-dev, research, plan, documentation)
- [ ] T028: Add mission → feature → WP → workspace hierarchy explanation
- [ ] T029: Add mission selection guide (when to use which mission)
- [ ] T030: Add template resolution chain explanation (override → global → package)
- [ ] T031: Add guard primitives overview at user level

**Implementation**: `spec-kitty implement WP06 --base WP01`

### WP07 — Git Workflow Explanation

**Goal**: Create new explanation doc from git-workflow skill.

**Priority**: P1
**Dependencies**: WP01
**Estimated size**: ~300 lines

**Subtasks**:
- [x] T032: Create `docs/explanation/git-workflow.md` with the core boundary (Python vs agent git operations)
- [x] T033: Document worktree lifecycle (creation → active → review → merged → cleanup)
- [x] T034: Document auto-commit behavior and configuration
- [x] T035: Document what agents must do manually (implementation commits, rebases, conflict resolution)
- [x] T036: Add anti-patterns section (manual worktree creation, committing in wrong repo)
- [x] T037: Update `docs/explanation/toc.yml` to include new guide

**Implementation**: `spec-kitty implement WP07 --base WP01`

### WP08 — Runtime Loop Explanation

**Goal**: Create new explanation doc from runtime-next skill.

**Priority**: P1
**Dependencies**: WP01
**Estimated size**: ~300 lines

**Subtasks**:
- [ ] T038: Create `docs/explanation/runtime-loop.md` explaining what spec-kitty next does and when to use it
- [ ] T039: Document the 4 decision kinds (step, blocked, terminal, decision_required) with user-facing examples
- [ ] T040: Document the agent loop pattern at conceptual level
- [ ] T041: Document known issues (#335, #336) as user-facing notes with workarounds
- [ ] T042: Update `docs/explanation/toc.yml` to include new guide

**Implementation**: `spec-kitty implement WP08 --base WP01`

---

## Phase 4: Reference Update

### WP09 — Orchestrator API Reference Update

**Goal**: Expand existing orchestrator-api.md with orchestrator-api skill content.

**Priority**: P1
**Dependencies**: WP01
**Estimated size**: ~350 lines

**Subtasks**:
- [ ] T043: Expand `docs/reference/orchestrator-api.md` with all 9 commands, flags, and output fields
- [ ] T044: Add JSON output examples for feature-state and list-ready
- [ ] T045: Add complete error code catalog with causes and recovery
- [ ] T046: Add policy metadata schema with all 7 required fields explained
- [ ] T047: Add host boundary rules summary (what external systems must not do)
- [ ] T048: Update `docs/reference/toc.yml` if needed

**Implementation**: `spec-kitty implement WP09 --base WP01`

---

## Phase 5: Content Expansion

### WP10 — 2x Versioned Docs Expansion

**Goal**: Expand thin 2x/ versioned docs and add cross-references to new guides.

**Priority**: P2
**Dependencies**: WP02, WP03, WP06
**Estimated size**: ~250 lines

**Subtasks**:
- [ ] T049: Expand `docs/2x/doctrine-and-constitution.md` (currently 60 lines) with constitution workflow summary
- [ ] T050: Expand `docs/2x/glossary-system.md` (currently 37 lines) with glossary concepts and CLI usage
- [ ] T051: Expand `docs/2x/runtime-and-missions.md` (currently 49 lines) with mission overview and runtime loop
- [ ] T052: Add cross-references from 2x/ docs to new how-to and explanation guides
- [ ] T053: Update `docs/2x/toc.yml` if new entries needed

**Implementation**: `spec-kitty implement WP10 --base WP06`

---

## Summary

| WP | Title | Subtasks | Est. Lines | Dependencies |
|---|---|:---:|:---:|---|
| WP01 | DocFX Build Fix | 5 | ~250 | none |
| WP02 | Glossary Guide | 5 | ~300 | WP01 |
| WP03 | Governance Guide | 6 | ~350 | WP01 |
| WP04 | Diagnostics Guide | 5 | ~250 | WP01 |
| WP05 | Review Guide Update | 5 | ~200 | WP01 |
| WP06 | Mission Explanation | 5 | ~350 | WP01 |
| WP07 | Git Workflow Explanation | 6 | ~300 | WP01 |
| WP08 | Runtime Loop Explanation | 5 | ~300 | WP01 |
| WP09 | Orchestrator API Reference | 6 | ~350 | WP01 |
| WP10 | 2x/ Content Expansion | 5 | ~250 | WP02, WP03, WP06 |

**Total**: 10 WPs, 53 subtasks
**Parallelization**: WP02-WP09 (8 WPs) are fully parallel after WP01
**All WPs within ideal size range** (200-350 lines, 5-6 subtasks each)

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: approved
- WP05: for_review
<!-- status-model:end -->
