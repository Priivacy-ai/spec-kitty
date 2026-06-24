# Implementation Plan: Decompose agent/tasks.py god-module

**Branch**: `main` (planning) → merges into `main` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/decompose-agent-tasks-god-module-01KVWVAR/spec.md`

## Summary

Decompose `src/specify_cli/cli/commands/agent/tasks.py` (4633 LOC, maxCC ~178) into a thin typer
command-registration shim (≤ ~1200 LOC) plus five cohesive, independently-testable seam modules,
and internally decompose the six mega-functions so **every** function satisfies maxCC ≤ 15. The public
`agent tasks` CLI surface stays byte-identical (golden characterization tests captured first). Separately,
centralize the three planning-commit tails through the canonical `commit_for_mission` router and delete
the now-dead bespoke `is_protected` pre-checks, while preserving the protected-primary error messages
verbatim. Technical approach and seam boundaries are fixed by Phase 0 research ([research.md](./research.md)).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (frontmatter), `mission_runtime` / `specify_cli.coordination.commit_router` (commit routing) — **no new runtime dependencies**
**Storage**: N/A — no runtime data-schema change; planning artifacts are files
**Testing**: pytest. Golden CLI characterization via `typer.testing.CliRunner` + committed expected-output fixtures (no new snapshot dependency); per-seam unit tests; ruff + `mypy --strict` gates; ≥90% coverage on new/changed code
**Target Platform**: CLI (Linux/macOS), Python package `spec-kitty-cli`
**Project Type**: single (Python CLI package)
**Performance Goals**: zero behavior/perf regression — pure structural refactor + output-preserving commit centralization
**Constraints**: maxCC ≤ 15 for every function (ruff C901 / Sonar S3776); `agent tasks` command/flag/exit-code/`--json` contract byte-identical; one-way imports (seams never import the shim); no new `# noqa`/`# type: ignore`/per-file ignores
**Scale/Scope**: relocate ~1800 LOC into 5 seams; decompose 6 mega-functions (`move_task` 778, `status` 483, `map_requirements` 382, `_validate_ready_for_review` 348, `mark_status` 265, `finalize_tasks` 218); ~410 LOC new tests; 3 commit tails re-routed

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.md`). Policy stack: typer / rich / ruamel.yaml / pytest / mypy --strict / 90%+ new-code coverage / integration tests for CLI commands.

| Charter requirement | Status in this plan |
|---------------------|---------------------|
| typer / rich / ruamel.yaml | Preserved; no replacement, no new deps |
| pytest, 90%+ new-code coverage | NFR-002 + per-seam tests + golden CLI tests |
| mypy --strict, ruff clean, no suppressions | NFR-003 + C-004 |
| Integration tests for CLI commands | Golden CLI characterization tests (SC-006) |
| Complexity ceiling maxCC ≤ 15 | NFR-001 is the binding target |
| Use canonical sources, never improvise | C-002 — route via existing `commit_for_mission`, not a hand-rolled guard |

**No charter violations. No entries in Complexity Tracking.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/decompose-agent-tasks-god-module-01KVWVAR/
├── plan.md              # This file
├── spec.md              # Mission spec
├── research.md          # Phase 0 (complete)
├── data-model.md        # Phase 1 — module topology + invariants
├── quickstart.md        # Phase 1 — how to verify the refactor
├── contracts/
│   └── cli-surface-contract.md   # Frozen `agent tasks` CLI contract (golden-test target)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/agent/
├── tasks.py                       # RESIDUAL SHIM: typer `app` + 9 thinned command handlers (≤ ~1200 LOC)
├── tasks_outline.py               # SEAM 1: tasks.md / manifest parsing, WP-id resolution
├── tasks_materialization.py       # SEAM 2: frontmatter & file persistence, markdown-row mutation
├── tasks_finalize_validation.py   # SEAM 3: dependency/cycle validation, lane metadata, bootstrap glue
├── tasks_dependency_graph.py      # SEAM 4: dependency readiness / dependent-gating glue
└── tasks_parsing_validation.py    # SEAM 5: readiness / verdict / issue-matrix validation

src/specify_cli/coordination/commit_router.py   # EXISTING — the 3 tails route through commit_for_mission (no new module)

tests/specify_cli/cli/commands/agent/
├── test_tasks_cli_contract.py     # NEW: golden CLI characterization (captured pre-refactor)
├── test_tasks_outline.py          # NEW: seam 1 unit tests
├── test_tasks_materialization.py  # NEW: seam 2 unit tests (+ error paths)
├── test_tasks_dependency_readiness.py  # NEW: readiness gating
└── (existing test_tasks*.py suites remain green throughout)
```

**Structure Decision**: Single Python CLI package. Seams are sibling modules under
`src/specify_cli/cli/commands/agent/` (same package as the shim) to keep import paths short and
avoid a new sub-package; one-way dependency enforced by convention + review (INV-2). Commit routing
reuses the existing `coordination/commit_router.py` — no new module (C-002).

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Golden CLI characterization harness (capture FIRST)

- **Purpose**: Pin the `agent tasks` command/flag/exit-code/`--json` contract via `CliRunner` + committed expected-output fixtures, captured against the *current* code BEFORE any refactor, so contract drift is caught mechanically.
- **Relevant requirements**: FR-001, C-005, SC-006.
- **Affected surfaces**: `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py` (new); fixtures dir.
- **Sequencing/depends-on**: none — **must land before all extraction concerns**.
- **Risks**: help text contains volatile content (paths, timestamps) — normalize before snapshotting; ensure fixtures are deterministic under per-worker HOME isolation.

### IC-02 — Extract `tasks_outline` seam (parsing / WP-id resolution)

- **Purpose**: Move tasks.md/manifest parsing + WP-id resolution helpers into an independently-importable module with focused tests.
- **Relevant requirements**: FR-003, FR-004.
- **Affected surfaces**: new `tasks_outline.py`; `tasks.py` (delete moved fns, add imports); new `test_tasks_outline.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: shared regex/consts (`_WP_HEADING_RE`, `_QUALIFIED_TASK_ID_RE`) relocate cleanly; keep re-export if any external test imports by path.

### IC-03 — Extract `tasks_materialization` seam (frontmatter/file persistence)

- **Purpose**: Move markdown-row mutation + file/frontmatter persistence into a seam; add error-path tests.
- **Relevant requirements**: FR-003, FR-004.
- **Affected surfaces**: new `tasks_materialization.py`; `tasks.py`; new `test_tasks_materialization.py`.
- **Sequencing/depends-on**: IC-02 (imports outline parsers).
- **Risks**: fragile markdown regex; cover checkbox/pipe-table/inline cases + write-failure paths.

### IC-04 — Extract `tasks_finalize_validation` seam (dependency/cycle/lane metadata)

- **Purpose**: Move cycle/dependency validation + lane-metadata + bootstrap glue (incl. the validation core extracted from `finalize_tasks`).
- **Relevant requirements**: FR-003, FR-004.
- **Affected surfaces**: new `tasks_finalize_validation.py`; `tasks.py`.
- **Sequencing/depends-on**: IC-01 (parallelizable with IC-02/03).
- **Risks**: preserve the "disagree-loud" conflict detection; existing finalize tests are strong — keep green.

### IC-05 — Extract `tasks_dependency_graph` seam (readiness / dependent-gating)

- **Purpose**: Move `_check_dependent_warnings`, `_behind_commits_touch_only_planning_artifacts`, and the dependent-gating extracted from `move_task`; add readiness-gating tests.
- **Relevant requirements**: FR-003, FR-004.
- **Affected surfaces**: new `tasks_dependency_graph.py`; `tasks.py`; new `test_tasks_dependency_readiness.py`.
- **Sequencing/depends-on**: IC-01. (The two `core/dependency_graph.py` call sites stay in the shim — no cycle.)
- **Risks**: subprocess git calls — keep graceful fallbacks; LOW circular-import risk per research §4.

### IC-06 — Extract `tasks_parsing_validation` seam (readiness/verdict/issue-matrix)

- **Purpose**: Move issue-matrix + verdict + review-cycle validation; **sub-split the 348-LOC `_validate_ready_for_review`** into ≤15-CC helpers (research-artifacts / worktree-state / merge-ancestry / contamination).
- **Relevant requirements**: FR-003, FR-004, NFR-001.
- **Affected surfaces**: new `tasks_parsing_validation.py`; `tasks.py`.
- **Sequencing/depends-on**: IC-02 (uses outline parsers). Largest seam.
- **Risks**: tightly bound to spec-md parsing + git subprocess; existing coverage is STRONG — lean on it.

### IC-07 — Decompose mega-function command bodies + thin the shim

- **Purpose**: Internally decompose `move_task` (778), `status` (483), `map_requirements` (382), `mark_status` (265), `finalize_tasks` (218) so each handler is a thin orchestrator (dispatch → seam calls → emit), achieving maxCC ≤ 15 everywhere and tasks.py ≤ ~1200 LOC.
- **Relevant requirements**: FR-005, NFR-001, NFR-004, SC-002.
- **Affected surfaces**: `tasks.py` (all 5 mega-handlers); helper extraction into the relevant seams.
- **Sequencing/depends-on**: IC-02..IC-06 (seams must exist to delegate to). Coordinate with IC-08 (both touch `move_task`/`mark_status`/`map_requirements`).
- **Risks**: this is the bulk of the effort; lean entirely on IC-01 golden tests + existing suite to prove preservation.

### IC-08 — Centralize commit routing (3 tails → `commit_for_mission`)

- **Purpose**: Route the 3 tails (`tasks.py:2486/3131/3947`) through `commit_for_mission`; thread `target_branch=` on tail 3; delete dead pre-checks (`921-932`, `954-971`, guard conditionals `2448-2470`/`3021-3029`, `_planning_commit_worktree` import `3928`); **map the router's `no_op_wrong_surface` result back to the existing protected-primary messages verbatim** so output stays byte-identical.
- **Relevant requirements**: FR-006, FR-007, FR-008, C-002, C-003, C-006.
- **Affected surfaces**: `tasks.py` (`move_task`/`mark_status`/`map_requirements`); extend `tests/.../test_wp03_bypass_writers_fr008.py`.
- **Sequencing/depends-on**: coordinate with IC-07 (shared functions). `mission.py` is OUT OF SCOPE (C-006).
- **Risks**: message-preservation is the subtle part — assert byte-identical messages + exit codes in the regression test.

### IC-09 — Pointer comment + final gate sweep

- **Purpose**: Add the top-of-file `#2058` decomposition-pointer comment (matching #2056/#1623), and run the full gate sweep (ruff, mypy --strict, coverage ≥90%, maxCC ≤15, terminology guard, golden + existing suites).
- **Relevant requirements**: FR-002, NFR-001, NFR-002, NFR-003, SC-005.
- **Affected surfaces**: `tasks.py` header; CI gates.
- **Sequencing/depends-on**: all prior ICs.
- **Risks**: `integration-tests-core-misc` gates (terminology) run only in CI — run `tests/architectural/` locally before pushing.
