# Tasks: Decompose agent/tasks.py god-module

**Mission**: 01KVWVARJKSH9T2QNHJVE4ZC7Y · **Slug**: decompose-agent-tasks-god-module-01KVWVAR
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Branch**: `main` → `main`

## Overview

Decompose `src/specify_cli/cli/commands/agent/tasks.py` (4633 LOC, maxCC ~178) into a thin command
shim + 5 cohesive seam modules, byte-identically preserving the `agent tasks` CLI surface, and
centralizing the 3 planning-commit tails through `commit_for_mission` (output-preserving). 7 work
packages, sequential dependency chain (one file → no safe parallelism).

**Ownership model (zero-overlap):** each seam WP owns only its *new* module + test file. `tasks.py`
is owned solely by **WP07**. Seam WPs (WP02–06) make small, justified out-of-map edits to `tasks.py`
to wire in their seam and remove the moved block — safe because the chain is sequential.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Build `CliRunner` help/contract capture harness | WP01 | | [D] |
| T002 | Capture golden fixtures for all 9 commands (help + flags) | WP01 | [D] |
| T003 | Capture exit-code + `--json` envelope fixtures | WP01 | [D] |
| T004 | Normalize volatile substrings (paths/timestamps/ULIDs) | WP01 | | [D] |
| T005 | Wire contract test into suite; prove green on current code | WP01 | | [D] |
| T006 | Create `tasks_outline.py`; move parsing/WP-id helpers + regex consts | WP02 | | [D] |
| T007 | Wire `tasks.py` to import from `tasks_outline`; delete moved block | WP02 | | [D] |
| T008 | Add `test_tasks_outline.py` (isolated parser unit tests) | WP02 | | [D] |
| T009 | Verify golden + existing suites green | WP02 | | [D] |
| T010 | Create `tasks_materialization.py`; move persistence/markdown-mutation helpers | WP03 | | [D] |
| T011 | Wire `tasks.py`; delete moved block | WP03 | | [D] |
| T012 | Add `test_tasks_materialization.py` incl. write-failure paths | WP03 | | [D] |
| T013 | Verify suites green | WP03 | | [D] |
| T014 | Create `tasks_finalize_validation.py`; move cycle/lane helpers + finalize core | WP04 | | [D] |
| T015 | Wire `tasks.py`; thin `finalize_tasks` body | WP04 | | [D] |
| T016 | Add `test_tasks_finalize_validation.py` | WP04 | | [D] |
| T017 | Verify suites green | WP04 | | [D] |
| T018 | Create `tasks_dependency_graph.py`; move dependent-gating helpers | WP05 | | [D] |
| T019 | Wire `tasks.py`; thin `move_task` dependent-warning slice | WP05 | | [D] |
| T020 | Add `test_tasks_dependency_readiness.py` (readiness gating) | WP05 | | [D] |
| T021 | Verify suites green | WP05 | | [D] |
| T022 | Create `tasks_parsing_validation.py`; move issue-matrix/verdict helpers | WP06 | | [D] |
| T023 | Sub-split `_validate_ready_for_review` (348 LOC) into ≤15-CC helpers | WP06 | | [D] |
| T024 | Wire `tasks.py`; delete moved block | WP06 | | [D] |
| T025 | Add `test_tasks_parsing_validation.py` | WP06 | | [D] |
| T026 | Verify suites green | WP06 | | [D] |
| T027 | Route `move_task` commit tail (2486) via `commit_for_mission`, preserve message | WP07 | | [D] |
| T028 | Route `mark_status` commit tail (3131) via `commit_for_mission`, preserve message | WP07 | | [D] |
| T029 | Route `map_requirements` commit tail (3947) via `commit_for_mission`, thread `target_branch`, preserve message | WP07 | | [D] |
| T030 | Delete dead pre-checks + `_planning_commit_worktree` import | WP07 | | [D] |
| T031 | Extend `test_wp03_bypass_writers_fr008.py`: routing + verbatim messages/exit codes | WP07 | | [D] |
| T032 | Final maxCC≤15 sweep + add `#2058` pointer comment | WP07 | | [D] |
| T033 | Full gate sweep (golden+existing suites, ruff, mypy --strict, coverage, terminology); confirm ≤~1200 LOC | WP07 | | [D] |

---

## Phase 1 — Safety net

### WP01 — Golden CLI characterization harness

- **Goal**: Pin the `agent tasks` CLI contract (commands/flags/exit-codes/`--json`) against current code BEFORE any refactor, so contract drift is caught mechanically. (FR-001, C-005, SC-006)
- **Priority**: P0 — MVP / blocker for all extraction.
- **Independent test**: `pytest test_tasks_cli_contract.py` passes on current `main` HEAD.
- **Subtasks**: T001–T005
- **Dependencies**: none
- **Owned files**: `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py`, `tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/**`
- **Prompt**: [tasks/WP01-golden-cli-characterization-harness.md](./tasks/WP01-golden-cli-characterization-harness.md) · ~300 lines

## Phase 2 — Seam extraction (sequential)

### WP02 — Extract `tasks_outline` seam

- **Goal**: Move tasks.md/manifest parsing + WP-id resolution into an independently-importable module with isolated tests. (FR-003, FR-004)
- **Independent test**: `pytest test_tasks_outline.py`; golden + existing suites stay green.
- **Subtasks**: T006–T009 · **Dependencies**: WP01
- **Owned files**: `src/specify_cli/cli/commands/agent/tasks_outline.py`, `tests/specify_cli/cli/commands/agent/test_tasks_outline.py`
- **Prompt**: [tasks/WP02-extract-tasks-outline-seam.md](./tasks/WP02-extract-tasks-outline-seam.md) · ~320 lines

### WP03 — Extract `tasks_materialization` seam

- **Goal**: Move frontmatter/file persistence + markdown-row mutation into a seam; add error-path tests. (FR-003, FR-004)
- **Independent test**: `pytest test_tasks_materialization.py`; suites green.
- **Subtasks**: T010–T013 · **Dependencies**: WP02 (imports outline parsers)
- **Owned files**: `src/specify_cli/cli/commands/agent/tasks_materialization.py`, `tests/specify_cli/cli/commands/agent/test_tasks_materialization.py`
- **Prompt**: [tasks/WP03-extract-tasks-materialization-seam.md](./tasks/WP03-extract-tasks-materialization-seam.md) · ~340 lines

### WP04 — Extract `tasks_finalize_validation` seam

- **Goal**: Move dependency/cycle validation + lane metadata + the validation core of `finalize_tasks`; thin the command body. (FR-003, FR-004)
- **Independent test**: `pytest test_tasks_finalize_validation.py`; finalize tests green.
- **Subtasks**: T014–T017 · **Dependencies**: WP02
- **Owned files**: `src/specify_cli/cli/commands/agent/tasks_finalize_validation.py`, `tests/specify_cli/cli/commands/agent/test_tasks_finalize_validation.py`
- **Prompt**: [tasks/WP04-extract-tasks-finalize-validation-seam.md](./tasks/WP04-extract-tasks-finalize-validation-seam.md) · ~340 lines

### WP05 — Extract `tasks_dependency_graph` seam

- **Goal**: Move dependent-gating + behind-commit helpers; add readiness-gating tests. The two `core/dependency_graph.py` call sites stay in the shim (no cycle). (FR-003, FR-004)
- **Independent test**: `pytest test_tasks_dependency_readiness.py`; suites green.
- **Subtasks**: T018–T021 · **Dependencies**: WP02
- **Owned files**: `src/specify_cli/cli/commands/agent/tasks_dependency_graph.py`, `tests/specify_cli/cli/commands/agent/test_tasks_dependency_readiness.py`
- **Prompt**: [tasks/WP05-extract-tasks-dependency-graph-seam.md](./tasks/WP05-extract-tasks-dependency-graph-seam.md) · ~300 lines

### WP06 — Extract `tasks_parsing_validation` seam (+ sub-split the 348-LOC validator)

- **Goal**: Move issue-matrix/verdict/review-cycle validation; sub-split `_validate_ready_for_review` into ≤15-CC helpers. (FR-003, FR-004, NFR-001)
- **Independent test**: `pytest test_tasks_parsing_validation.py`; suites green.
- **Subtasks**: T022–T026 · **Dependencies**: WP03
- **Owned files**: `src/specify_cli/cli/commands/agent/tasks_parsing_validation.py`, `tests/specify_cli/cli/commands/agent/test_tasks_parsing_validation.py`
- **Prompt**: [tasks/WP06-extract-tasks-parsing-validation-seam.md](./tasks/WP06-extract-tasks-parsing-validation-seam.md) · ~400 lines

## Phase 3 — Shim finalization

### WP07 — Centralize commit routing + final shim sweep

- **Goal**: Route the 3 commit tails through `commit_for_mission` (output-preserving), delete dead pre-checks, add the `#2058` pointer comment, and run the final maxCC≤15 / size / gate sweep. **Sole owner of `tasks.py`.** (FR-001, FR-002, FR-005, FR-006, FR-007, FR-008)
- **Independent test**: extended `test_wp03_bypass_writers_fr008.py`; golden + full suites green; `ruff`/`mypy --strict` clean; tasks.py ≤ ~1200 LOC, maxCC ≤15.
- **Subtasks**: T027–T033 · **Dependencies**: WP02, WP03, WP04, WP05, WP06
- **Owned files**: `src/specify_cli/cli/commands/agent/tasks.py`, `tests/specify_cli/cli/commands/test_wp03_bypass_writers_fr008.py`
- **Prompt**: [tasks/WP07-centralize-commit-routing-and-shim-sweep.md](./tasks/WP07-centralize-commit-routing-and-shim-sweep.md) · ~420 lines

---

## Dependency graph

```
WP01 ──▶ WP02 ──┬─▶ WP03 ──▶ WP06 ──┐
                ├─▶ WP04 ───────────┤
                └─▶ WP05 ───────────┼─▶ WP07
                                    │
                    (WP03,WP04,WP05)┘
```

WP07 depends on WP02–06. WP03→WP06 (parsing uses outline+materialization). All other Phase-2 WPs
depend only on WP02. Execution is effectively a single sequential lane (shared `tasks.py` surface).

## MVP scope

**WP01** is the non-negotiable first step — without the golden contract net, no extraction is safe.
The minimum *useful* increment is WP01 + WP02 (first seam proven extractable end-to-end).

## Requirement coverage

| FR | WPs |
|----|-----|
| FR-001 | WP01, WP07 |
| FR-002 | WP07 |
| FR-003 | WP02, WP03, WP04, WP05, WP06 |
| FR-004 | WP02, WP03, WP04, WP05, WP06 |
| FR-005 | WP07 |
| FR-006 | WP07 |
| FR-007 | WP07 |
| FR-008 | WP07 |
