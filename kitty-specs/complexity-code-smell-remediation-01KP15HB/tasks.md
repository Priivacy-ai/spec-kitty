# Tasks: Complexity and Code Smell Remediation

**Mission**: `complexity-code-smell-remediation-01KP15HB`
**Branch**: `feat/complexity-debt-remediation`
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)
**Generated**: 2026-04-12

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Add `TransitionRequest` dataclass to `status/models.py` | WP01 | [P] independent of T004 | [D] |
| T002 | Update `emit_status_transition` to accept `TransitionRequest` as sole parameter | WP01 | — | [D] |
| T003 | Migrate all 27 `emit_status_transition` call-site files to `TransitionRequest` | WP01 | [P] file-by-file | [D] |
| T004 | Add `GuardContext` dataclass to `status/transitions.py` | WP01 | [P] independent of T001 | [D] |
| T005 | Update `validate_transition` and `_run_guard` to accept `GuardContext` | WP01 | — | [D] |
| T006 | Migrate all 10 `validate_transition` call-site files to `GuardContext` | WP01 | [P] file-by-file | [D] |
| T007 | Quality gate: ruff + mypy + pytest green on WP01 | WP01 | — | [D] |
| T008 | Write characterization tests for `resolved_agent` (all 4 input branches) | WP02 | — | [D] |
| T009 | Decompose `resolved_agent` (CC=18) into independently testable resolution steps | WP02 | — | [D] |
| T010 | Fix bare `raise ValueError` at `wp_metadata.py:194` → `raise ... from err` | WP02 | [P] trivial, any time | [D] |
| T011 | Rename `FeatureStatusLockTimeout` → `FeatureStatusLockTimeoutError` across all call sites | WP02 | — | [D] |
| T012 | Quality gate: ruff + mypy + pytest green on WP02 | WP02 | — | [D] |
| T013 | Write characterization tests for `_extract_governance` (at least one test per field branch) | WP03 | — | [D] |
| T014 | Replace `_extract_governance` 26-branch `if/elif` with field-name dispatch table; remove `# noqa: C901` | WP03 | — | [D] |
| T015 | Decompose `resolve_governance` into independently callable helpers (FR-007, conditional on C-001) | WP03 | — | [D] |
| T016 | Reduce `_build_references_from_service` to ≤ 5 parameters and ≤ 12 branches | WP03 | — | [D] |
| T017 | Replace magic depth numbers `2`, `3` with named constants in `context.py` | WP03 | [P] trivial | [D] |
| T018 | Replace `else: if` anti-pattern with `elif` in `parser.py:170` | WP03 | [P] trivial | [D] |
| T019 | Quality gate: ruff + mypy + pytest green on WP03 | WP03 | — | [D] |
| T020 | Create `src/doctrine/base.py` with `BaseDoctrineRepository[T]` generic ABC | WP04 | — |
| T021 | Migrate 7 doctrine sub-repositories to `BaseDoctrineRepository[T]` (strangler-fig, one at a time) | WP04 | — |
| T022 | Rename `CurationAborted` → `CurationAbortedError` across all import sites | WP04 | [P] independent of T020 |
| T023 | Replace magic workload thresholds `2`, `4` with named constants in `agent_profiles/repository.py` | WP04 | [P] trivial |
| T024 | Fix TC003, PTH105, PTH108 violations in `kernel/atomic.py`; TC003 in `glossary_runner.py`; I001+TC003 in `_safe_re.py` | WP04 | [P] independent |
| T025 | Quality gate: ruff + mypy + pytest green on WP04 | WP04 | — |
| T026 | Redirect 2 external callers from `specify_cli.charter.*` submodule imports to `charter.*` (workflow.py handled by WP01/T031) | WP05 | — | [D] |
| T027 | Convert `specify_cli/charter/__init__.py` to re-export shim; delete all internal `.py` files | WP05 | — | [D] |
| T028 | Flatten `specify_cli/missions/` shim chain: update `__init__.py` to import from `doctrine.missions`; delete `primitives.py` and `glossary_hook.py` | WP05 | [P] independent of T026 | [D] |
| T029 | Make `mission.py` a thin shim re-exporting `app` from `mission_type.py` | WP05 | [P] independent | [D] |
| T030 | Quality gate: ruff + mypy + pytest green on WP05 | WP05 | — | [D] |
| T031 | Guard `workflow.py` call to `top_level_implement()` against OptionInfo leakage; redirect charter import; add programmatic regression test (#571) | WP01 | [P] independent of T001–T006 | [D] |
| T032 | Characterize and decompose S3776-violating functions in `src/charter/catalog.py` (#594) | WP03 | — | [D] |

---

## Work Packages

### WP01 — Status: Parameter Boundary Reduction

**Goal**: Introduce `TransitionRequest` and `GuardContext` dataclasses; migrate all call sites.
**Priority**: High — enables the cleaner API that WP02 builds on; parallelizes with WP03 and WP04.
**Lane**: A (first)
**Prompt**: [tasks/WP01-status-parameter-boundary.md](tasks/WP01-status-parameter-boundary.md)
**Dependencies**: None
**FRs covered**: FR-001, FR-003, FR-018
**Estimated size**: ~500 lines

#### Included subtasks

- [x] T001 Add `TransitionRequest` dataclass to `status/models.py` (WP01)
- [x] T002 Update `emit_status_transition` to accept `TransitionRequest` as sole parameter (WP01)
- [x] T003 Migrate all 27 `emit_status_transition` call-site files to `TransitionRequest` (WP01)
- [x] T004 Add `GuardContext` dataclass to `status/transitions.py` (WP01)
- [x] T005 Update `validate_transition` and `_run_guard` to accept `GuardContext` (WP01)
- [x] T006 Migrate all 10 `validate_transition` call-site files to `GuardContext` (WP01)
- [x] T007 Quality gate: ruff + mypy + pytest green on WP01 (WP01)
- [x] T031 Guard `workflow.py` `top_level_implement()` calls against OptionInfo leakage; redirect charter import; add programmatic regression test (WP01)

#### Implementation sketch

1. Add `TransitionRequest` to `models.py` (19 fields, all optional)
2. Update `emit_status_transition` body to unpack from `TransitionRequest`; keep internal logic intact
3. File-by-file: construct `TransitionRequest(...)` at each call site; run `mypy src/` after each file
4. Add `GuardContext` to `transitions.py` (10 fields)
5. Update `_run_guard(from_lane, to_lane, ctx: GuardContext)` and `validate_transition(from_lane, to_lane, ctx: GuardContext)`
6. File-by-file: construct `GuardContext(...)` at each call site
7. Full quality gate: ruff + mypy + pytest

#### Parallel opportunities

T001 and T004 (dataclass definitions) can be written simultaneously. T003 and T006 (call-site
migration) can be done in parallel across files. Use `mypy src/ --no-error-summary` between
each file to catch type errors incrementally.

#### Risks

- Large blast radius (27 + 10 files). Mitigate: migrate file-by-file with a green mypy gate after each.
- Circular import: `TransitionRequest` in `models.py` must not import from `emit.py`. Check carefully.
- Test suite may have helper functions that call `emit_status_transition` directly — find them all first with `grep -r "emit_status_transition" tests/ -l`.

---

### WP02 — Status: Complexity Reduction and Cleanup

**Goal**: Reduce `resolved_agent` CC, fix exception chain, rename lock timeout error.
**Priority**: High — Lane A, follows WP01.
**Lane**: A (second, depends on WP01)
**Prompt**: [tasks/WP02-status-cleanup.md](tasks/WP02-status-cleanup.md)
**Dependencies**: WP01 (Lane A sequential — must not start until WP01 is merged)
**FRs covered**: FR-002, FR-004, FR-005
**Estimated size**: ~300 lines

#### Included subtasks

- [x] T008 Write characterization tests for `resolved_agent` (all 4 input branches) (WP02)
- [x] T009 Decompose `resolved_agent` (CC=18) into independently testable resolution steps (WP02)
- [x] T010 Fix bare `raise ValueError` at `wp_metadata.py:194` → `raise ... from err` (WP02)
- [x] T011 Rename `FeatureStatusLockTimeout` → `FeatureStatusLockTimeoutError` across all call sites (WP02)
- [x] T012 Quality gate: ruff + mypy + pytest green on WP02 (WP02)

#### Implementation sketch

1. Read `resolved_agent` and write characterization tests for each branch (string/dict/None/AgentAssignment)
2. Extract `_resolve_agent_from_string`, `_resolve_agent_from_dict`, `_resolve_fallback` or equivalent named helpers; verify CC drops to ≤ 10
3. One-line fix: `raise ValueError(...) from err` at `wp_metadata.py:194`
4. `FeatureStatusLockTimeout` → `FeatureStatusLockTimeoutError`: grep for all usages, apply rename atomically
5. Full quality gate

#### Parallel opportunities

T010 (1-line fix) can be applied at any point in the WP. T011 (rename) is independent of T008/T009.

#### Risks

- `resolved_agent` has 7 distinct fallback paths — characterization tests must cover all branches before restructuring, or the refactor may silently break an edge case.

---

### WP03 — Charter: Dispatch Table and Decomposition

**Goal**: Reduce charter slice CC; remove `# noqa: C901` suppressions.
**Priority**: High — Lane B, independent of Lane A.
**Lane**: B (independent)
**Prompt**: [tasks/WP03-charter-dispatch.md](tasks/WP03-charter-dispatch.md)
**Dependencies**: None
**FRs covered**: FR-006, FR-007 (conditional), FR-008, FR-009, FR-010
**Estimated size**: ~420 lines

#### Included subtasks

- [x] T013 Write characterization tests for `_extract_governance` (at least one per field branch) (WP03)
- [x] T014 Replace `_extract_governance` if/elif with field-name dispatch table; remove `# noqa` (WP03)
- [x] T015 Decompose `resolve_governance` into independently callable helpers (conditional on C-001) (WP03)
- [x] T016 Reduce `_build_references_from_service` to ≤ 5 parameters and ≤ 12 branches (WP03)
- [x] T017 Replace magic depth numbers with named constants in `context.py` (WP03)
- [x] T018 Replace `else: if` with `elif` in `parser.py:170` (WP03)
- [x] T019 Quality gate: ruff + mypy + pytest green on WP03 (WP03)
- [x] T032 Characterize and decompose S3776-violating functions in `catalog.py` (WP03)

#### Implementation sketch

1. Characterize `_extract_governance` — the 26 field names are the test surface; write one parametrized test
2. Build `_FIELD_HANDLERS: dict[str, Callable[...]]` dispatch table; migrate branches one at a time; remove `# noqa: C901` when CC drops to ≤ 10
3. **C-001 check first**: grep `kitty-specs/` for active DRG mission. If present, skip T015. If absent, extract `_resolve_paradigms`, `_resolve_tools`, `_resolve_directives` from `resolve_governance`
4. Reduce `_build_references_from_service` (7 args → ≤ 5; strategy in data-model.md)
5. Named constants in `context.py` — one-liner
6. `elif` fix in `parser.py` — one-liner
7. Full quality gate

#### Parallel opportunities

T017 and T018 (trivial one-liners) can be applied first to clear easy noise before tackling T014.

#### Risks

- `_extract_governance` handles 26 field names; the dispatch table must handle all of them. Verify
  by running the charter test suite after each migrated branch: `pytest tests/ -k charter`.
- T015 is conditional: if a DRG mission appears after this WP is claimed, implement FR-006/FR-008/
  FR-009/FR-010 only and note the T015 deferral in the WP review.

---

### WP04 — Doctrine + Kernel: Repository Base Class and Import Fixes

**Goal**: Eliminate 7-way `_load()` duplication; rename error; fix kernel imports.
**Priority**: High — Lane C, independent of Lane A and B.
**Lane**: C (independent)
**Prompt**: [tasks/WP04-doctrine-base-kernel.md](tasks/WP04-doctrine-base-kernel.md)
**Dependencies**: None
**FRs covered**: FR-011, FR-012, FR-013, FR-014
**Estimated size**: ~380 lines

#### Included subtasks

- [ ] T020 Create `src/doctrine/base.py` with `BaseDoctrineRepository[T]` generic ABC (WP04)
- [ ] T021 Migrate 7 doctrine sub-repositories to `BaseDoctrineRepository[T]` (strangler-fig) (WP04)
- [ ] T022 Rename `CurationAborted` → `CurationAbortedError` across all import sites (WP04)
- [ ] T023 Replace magic workload thresholds in `agent_profiles/repository.py` with named constants (WP04)
- [ ] T024 Fix TC003, PTH105, PTH108 in `kernel/atomic.py`; TC003 in `glossary_runner.py`; I001+TC003 in `_safe_re.py` (WP04)
- [ ] T025 Quality gate: ruff + mypy + pytest green on WP04 (WP04)

#### Implementation sketch

1. Create `src/doctrine/base.py` per the interface in `data-model.md`; add to `src/doctrine/__init__.py` exports
2. Strangler-fig: migrate repositories in order: paradigms → procedures → toolguides → styleguides → mission_step_contracts → tactics → directives. Run `pytest tests/doctrine/` after each.
3. `CurationAborted` → `CurationAbortedError`: grep for all references; 2 files; atomic update
4. Named constants: `MAX_LOW_WORKLOAD = 2`, `MAX_MEDIUM_WORKLOAD = 4` at module scope in `agent_profiles/repository.py`
5. Kernel fixes: `ruff check --fix src/kernel/` handles TC003 and I001 automatically; manually fix PTH105 (use `Path.unlink()`) and PTH108 (use `Path.rename()`) in `atomic.py`
6. Full quality gate

#### Parallel opportunities

T022, T023, T024 are all independent of T020/T021. In a single-agent WP these can be done
in any order; if parallelizing at sub-WP level, tackle T022/T023/T024 while T021 is migrating
repositories.

#### Risks

- `_key()` override: 2 of 7 repositories use a key attribute other than `.id`. Confirm which ones
  before writing the base class to avoid a silent key collision.
- `templates/repository.py` and `missions/repository.py` are NOT in scope for FR-011 — their
  `_load()` patterns differ. Do not migrate them.

---

### WP05 — Deduplicate: specify_cli Charter Shim, Missions Shim, Mission CLI Command

**Goal**: Redirect charter submodule callers to `charter.*`; flatten missions shim chain; make `mission.py` a shim.
**Priority**: High — Lane D, independent. Directly reduces duplication highlighted by Sonar.
**Lane**: D (independent)
**Prompt**: [tasks/WP05-dedup-charter-missions-cmd.md](tasks/WP05-dedup-charter-missions-cmd.md)
**Dependencies**: None
**FRs covered**: FR-015, FR-016, FR-017
**Estimated size**: ~150 lines net change (large deletions, small additions)

#### Included subtasks

- [x] T026 Redirect 2 external callers from `specify_cli.charter.*` to `charter.*` (workflow.py handled by WP01/T031) (WP05)
- [x] T027 Convert `specify_cli/charter/__init__.py` to re-export shim; delete internal `.py` files (WP05)
- [x] T028 Flatten `specify_cli/missions/` shim chain (WP05)
- [x] T029 Make `mission.py` a thin shim (WP05)
- [x] T030 Quality gate: ruff + mypy + pytest green on WP05 (WP05)

#### Implementation sketch

1. Verify baseline green: `pytest tests/agent/glossary/ tests/specify_cli/cli/ -x -q`
2. Redirect the 3 import lines in the 2 external callers (T026) — note: `workflow.py` is handled by WP01/T031
3. Replace `specify_cli/charter/__init__.py` with re-export shim; delete 11 internal files (T027)
4. Flatten `specify_cli/missions/__init__.py`; delete `primitives.py` and `glossary_hook.py` (T028)
5. Replace `mission.py` body with shim (T029)
6. Full quality gate (T030)

T028 and T029 are independent of T026/T027 and can be done in any order.

#### Parallel opportunities

T026/T027 (charter shim) and T028/T029 (missions + mission.py) are fully independent —
they touch different files and different test suites.

#### Risks

- `specify_cli/charter/` internal files cross-reference each other via relative imports.
  After T026 redirects the 3 external callers, run `mypy src/specify_cli/charter/` before
  deleting files to confirm no remaining cross-imports are needed.
- If `src/charter/` is missing any name that `specify_cli/charter/__init__.py` previously
  exported, the shim import will fail at module load time. Run
  `python -c "from specify_cli.charter import *"` after writing the shim to catch this.

---

## Execution Lanes Summary

```
Lane A (sequential): WP01 → WP02
Lane B (independent): WP03
Lane C (independent): WP04
Lane D (independent): WP05
```

All four lanes can run concurrently. WP01 is the highest-risk WP (largest blast radius); it
should be started first or in parallel with WP03, WP04, and WP05.
