---
work_package_id: WP02
title: Coverage-safety harness
dependencies: []
requirement_refs:
- FR-004
- FR-012
- NFR-005
- NFR-007
tracker_refs: []
planning_base_branch: feat/test-suite-acceleration
merge_target_branch: feat/test-suite-acceleration
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-acceleration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-acceleration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-suite-acceleration-01KV3H59-01KV3H59
base_commit: 3aaf618fd051440a2dab99582995d25d346a39d9
created_at: '2026-06-14T17:29:27.045783+00:00'
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 1 - Foundational safety
agent: claude
shell_pid: '71386'
history:
- at: '2026-06-14T17:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: tests/_support/coverage_safety/
create_intent:
- tests/_support/__init__.py
- tests/_support/coverage_safety/__init__.py
- tests/_support/coverage_safety/collection_equivalence.py
- tests/_support/coverage_safety/test_collection_equivalence.py
- tests/_support/coverage_safety/ratchet.py
- tests/_support/coverage_safety/test_ratchet.py
- tests/_support/coverage_safety/equivalence.py
- tests/_support/coverage_safety/test_equivalence.py
- tests/_support/coverage_safety/README.md
- tests/architectural/test_real_home_isolation_guard.py
execution_mode: code_change
model: ''
owned_files:
- tests/_support/coverage_safety/**
- tests/architectural/test_real_home_isolation_guard.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Coverage-safety harness

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Recommended review profile for this cross-cutting safety work: **paula-patterns** (recurring-pattern scout).

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

Build the reusable safeguards that let every later reduction or parallelization flip be *proven* coverage-neutral. This WP is foundational: WP03 and WP05 consume it.

**Done when**: each helper has direct unit tests; the architectural guard fails on a simulated real-home mutation and passes otherwise; `ruff`/`mypy --strict` clean; new code ≥90% covered.

## Context & Constraints

- Evidence: `architecture/test-suite-acceleration-plan.md` (safeguards section); `contracts/behavioral-contracts.md` (C-EQUIV, C-RATCHET); `data-model.md` (E3, E4).
- The repo already ships a no-op-stability run-twice ratchet — study it and mirror its conventions rather than inventing a new shape.
- All helpers live under a NEW package `tests/_support/coverage_safety/` so they are importable and unit-testable. Do NOT place anything under `tests/_support/git_template/` (owned by WP06).

## Branch Strategy

- **Planning base branch**: feat/test-suite-acceleration
- **Merge target branch**: feat/test-suite-acceleration

## Subtasks & Detailed Guidance

### Subtask T005 – Collection-equivalence helper

- **Purpose**: Prove a shard collects the identical nodeid set serially and under `-n auto --dist loadfile` (C-EQUIV, FR-004).
- **Steps**:
  1. Create `tests/_support/coverage_safety/collection_equivalence.py` with `collect_nodeids(args: list[str]) -> set[str]` (run `pytest --collect-only -q` in a subprocess, parse nodeids) and `assert_equivalent(serial_args, parallel_args) -> None` that diffs the two sets and raises with the symmetric difference on mismatch.
  2. Unit-test with a tiny fixture test dir: identical selectors → empty diff; a deliberately different selector → raises naming the missing nodeid.
- **Files**: `tests/_support/coverage_safety/collection_equivalence.py`, `tests/_support/coverage_safety/test_collection_equivalence.py`.

### Subtask T006 – Stability ratchet helper

- **Purpose**: Accept a flip only after N consecutive green parallel runs (C-RATCHET, FR-012, NFR-005).
- **Steps**:
  1. Create `tests/_support/coverage_safety/ratchet.py` with `run_ratchet(pytest_args: list[str], n: int = 3) -> RatchetResult` capturing per-run pass/fail and any newly-failing nodeids.
  2. Expose a thin CLI entry (`python -m tests._support.coverage_safety.ratchet ...`) usable from CI.
  3. Unit-test the result aggregation logic with a stubbed runner (do not actually run N real suites in the unit test).
- **Files**: `tests/_support/coverage_safety/ratchet.py`, `.../test_ratchet.py`.

### Subtask T007 – Architectural guard: no real home mutation under xdist

- **Purpose**: Fail the build if ANY test reads/writes/truncates the real `Path.home()/.spec-kitty` under xdist (protects WP04’s guarantee, SC-006).
- **Steps**:
  1. Create `tests/architectural/test_real_home_isolation_guard.py`. It records the real home’s `~/.spec-kitty` state (absent, or mtime/inode), runs a representative parallel selection in a subprocess with `-n auto`, and asserts the real path is unchanged/absent afterward.
  2. Make the guard skip cleanly (with a clear reason) if WP04’s isolation fixture is not yet present, so it can merge before WP04 without red CI, then bite once WP04 lands.
- **Files**: `tests/architectural/test_real_home_isolation_guard.py`.
- **Notes**: This file is OUTSIDE `tests/_support/`; it is the one architectural test this WP owns.

### Subtask T008 – Equivalence/mutation-check helper + recipe

- **Purpose**: Give restructured tests (e.g. the FSM collapse in WP03) a repeatable way to prove behavioral equivalence (C-001).
- **Steps**:
  1. Create `tests/_support/coverage_safety/equivalence.py` with a small utility to run a target test, inject a single known-bad mutation into the data-under-test, and assert the test now fails and names the mutation (anti-vacuity).
  2. Write a short `tests/_support/coverage_safety/README.md` recipe: "how to prove a collapsed/parametrized test still catches a planted regression."
- **Files**: `tests/_support/coverage_safety/equivalence.py`, `.../README.md`, `.../test_equivalence.py`.

## Test Strategy

- `.venv/bin/pytest tests/_support/coverage_safety -q` green; helpers covered ≥90%.
- The home guard is exercised directly and skips gracefully pre-WP04.

## Risks & Mitigations

- **Risk**: subprocess collection is slow. **Mitigation**: scope helper self-tests to a tiny fixture dir, not the real suite.
- **Risk**: the guard is flaky on shared CI homes. **Mitigation**: assert on a dedicated sentinel path, capture before/after, and skip when isolation absent.

## Review Guidance

- Confirm helpers are pure/deterministic and unit-tested in isolation.
- Confirm the home guard genuinely fails on a simulated mutation (not vacuous).

## Activity Log

- 2026-06-14T17:10:00Z – system – Prompt created.
