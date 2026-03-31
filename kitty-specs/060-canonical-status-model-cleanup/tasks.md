# Tasks: Canonical Status Model Cleanup

**Feature**: 060-canonical-status-model-cleanup
**Branch**: main → main
**Date**: 2026-03-31
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Create bootstrap helper in `status/bootstrap.py` (scan WPs → check event log → emit → materialize) | WP01 | |
| T002 | Write tests for bootstrap helper | WP01 | |
| T003 | Integrate bootstrap into feature.py finalize-tasks + --validate-only | WP02 | |
| T004 | Update feature.py:640 generated README (lane-free) | WP02 | |
| T005 | Write tests for feature.py finalize-tasks bootstrap | WP02 | |
| T006 | Integrate bootstrap into tasks.py finalize-tasks + --validate-only | WP03 | |
| T007 | Remove lane= from tasks.py:1169 move_task body note | WP03 | |
| T008 | Remove lane= from tasks.py:1572 add_note body note | WP03 | |
| T009 | Delete tasks.py:1088-1115 bootstrap/sync block + add hard-fail | WP03 | |
| T010 | Write tests for tasks.py changes | WP03 | |
| T011 | Remove lane= from workflow.py:476 implement body note | WP04 | [P] |
| T012 | Remove lane= from workflow.py:1010 review body note | WP04 | [P] |
| T013 | Remove workflow.py:390 implement frontmatter fallback + hard-fail | WP04 | [P] |
| T014 | Remove workflow.py:954 review frontmatter fallback + hard-fail | WP04 | [P] |
| T015 | Write tests for workflow hard-fail behavior | WP04 | [P] |
| T016 | Clean specify_cli mission templates (4 files) | WP05 | [P] |
| T017 | Clean specify_cli command templates (2 files) | WP05 | [P] |
| T018 | Clean doctrine root template | WP05 | [P] |
| T019 | Clean doctrine mission templates (3 files) | WP05 | [P] |
| T020 | Add regression test scanning templates for lane: | WP05 | [P] |
| T021 | Update worktree.py:384 generated README (lane-free) | WP06 | |
| T022 | Remove lane from conftest.py WP fixtures | WP06 | |
| T023 | Update active tests that assert lane: in modern WP frontmatter | WP06 | |
| T024 | tasks_support.py:293 — remove frontmatter fallback, hard-fail | WP07 | |
| T025 | dashboard/scanner.py:322 + :454 — remove both fallback branches | WP07 | |
| T026 | mission_v1/guards.py:169 — delete/redirect to lane_reader | WP07 | |
| T027 | next/runtime_bridge.py:117 — use lane_reader | WP07 | |
| T028 | merge.py:72 — remove frontmatter fallback | WP07 | |
| T029 | Tests for hard-fail (event log absent, WP missing → uninitialized/error) | WP07 | |
| T030 | Mark repair_lane_mismatch + history_parser as migration-only | WP08 | |
| T031 | Add migration-only docstrings to m_0_9_1, m_2_0_6 | WP08 | |
| T032 | Update active docs (README, CLAUDE.md, command help) | WP08 | |
| T033 | Add targeted regression guard tests (template scan + runtime scan) | WP08 | |

## Work Packages

### Wave 1 (parallel)

#### WP01 — Canonical Bootstrap Helper
**Priority**: P1 (foundation for all other WPs)
**Prompt**: [tasks/WP01-canonical-bootstrap-helper.md](tasks/WP01-canonical-bootstrap-helper.md)
**Subtasks**: T001-T002 (2 subtasks, ~300 lines)
**Dependencies**: None
**Goal**: Create a shared `bootstrap_canonical_state()` function that scans WPs, checks event log, emits initial `planned` events, and materializes `status.json`.

#### WP05 — Template Cleanup
**Priority**: P1 (parallel with WP01)
**Prompt**: [tasks/WP05-template-cleanup.md](tasks/WP05-template-cleanup.md)
**Subtasks**: T016-T020 (5 subtasks, ~400 lines)
**Dependencies**: None (template text changes only — no runtime code)
**Goal**: Remove lane from all active template frontmatter, activity log examples, and history entries across specify_cli and doctrine.

### Wave 2 (parallel, after WP01)

#### WP02 — feature.py Changes
**Priority**: P1
**Prompt**: [tasks/WP02-feature-finalize-readme.md](tasks/WP02-feature-finalize-readme.md)
**Subtasks**: T003-T005 (3 subtasks, ~350 lines)
**Dependencies**: WP01
**Goal**: Integrate canonical bootstrap into feature.py finalize-tasks, add --validate-only, update generated README.

#### WP03 — tasks.py Changes
**Priority**: P1
**Prompt**: [tasks/WP03-tasks-finalize-body-bootstrap.md](tasks/WP03-tasks-finalize-body-bootstrap.md)
**Subtasks**: T006-T010 (5 subtasks, ~450 lines)
**Dependencies**: WP01
**Goal**: Integrate canonical bootstrap into tasks.py finalize-tasks, remove lane= body notes, delete bootstrap/sync block.

#### WP04 — workflow.py Changes
**Priority**: P1
**Prompt**: [tasks/WP04-workflow-body-fallback.md](tasks/WP04-workflow-body-fallback.md)
**Subtasks**: T011-T015 (5 subtasks, ~400 lines)
**Dependencies**: WP01
**Goal**: Remove lane= from workflow body notes, remove implement/review frontmatter fallbacks, add hard-fail.

### Wave 3 (parallel, after WP02+WP03)

#### WP06 — Generators + Test Fixtures
**Priority**: P1
**Prompt**: [tasks/WP06-generators-test-fixtures.md](tasks/WP06-generators-test-fixtures.md)
**Subtasks**: T021-T023 (3 subtasks, ~300 lines)
**Dependencies**: WP02, WP03
**Goal**: Update worktree.py README generator, remove lane from test fixtures, update tests.

#### WP07 — Runtime Fallback Removal
**Priority**: P1
**Prompt**: [tasks/WP07-runtime-fallback-removal.md](tasks/WP07-runtime-fallback-removal.md)
**Subtasks**: T024-T029 (6 subtasks, ~500 lines)
**Dependencies**: WP02, WP03
**Goal**: Remove frontmatter-lane fallbacks from tasks_support, scanner, guards, runtime_bridge, merge. Add hard-fail tests.

### Wave 4

#### WP08 — Migration Fence + Docs + Guards
**Priority**: P2
**Prompt**: [tasks/WP08-migration-fence-docs-guards.md](tasks/WP08-migration-fence-docs-guards.md)
**Subtasks**: T030-T033 (4 subtasks, ~350 lines)
**Dependencies**: WP07
**Goal**: Mark migration-only code, update docs, add regression guards.

## Dependency Graph

```
WP01 (Bootstrap Helper) ──┬──▶ WP02 (feature.py) ──┐
                          ├──▶ WP03 (tasks.py)    ──┼──▶ WP06 (Generators+Fixtures)
                          ├──▶ WP04 (workflow.py)   ├──▶ WP07 (Fallback Removal) ──▶ WP08 (Fence+Docs)
WP05 (Templates)          │                         │
  (parallel with WP01)    └─────────────────────────┘
```

## Parallelization Waves

| Wave | WPs | Agents |
|------|-----|--------|
| 1 | WP01, WP05 | 2 parallel |
| 2 | WP02, WP03, WP04 | 3 parallel |
| 3 | WP06, WP07 | 2 parallel |
| 4 | WP08 | 1 |

**Critical path**: WP01 → WP03 → WP07 → WP08

## Requirement Coverage

| WP | Requirements |
|----|-------------|
| WP01 | FR-001, FR-002, FR-003 |
| WP02 | FR-001, FR-002, FR-003, FR-011 |
| WP03 | FR-001, FR-002, FR-003, FR-007, FR-009 |
| WP04 | FR-007, FR-008 |
| WP05 | FR-004, FR-006, FR-010 |
| WP06 | FR-005, FR-011, FR-013 |
| WP07 | FR-008, FR-009, FR-009a |
| WP08 | FR-012, FR-014, FR-015, FR-016, FR-017 |
