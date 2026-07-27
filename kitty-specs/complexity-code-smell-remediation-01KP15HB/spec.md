# Complexity and Code Smell Remediation

**Mission ID:** 01KP15HBKQH3EAK44QEAJBV4Q5
**Mission slug:** complexity-code-smell-remediation-01KP15HB
**Type:** software-dev
**Target branch:** feat/complexity-debt-remediation → main
**Related issues:** #264 (primary), #391 (tech debt umbrella)

---

## Overview

The codebase carries 65 `# noqa: C901` suppression markers added in PR #252 to unblock the ruff
complexity gate without fixing the underlying structural problems. Sonar independently surfaces
15,596 cognitive complexity units and 557 code smells across the project. This mission remediates
the complexity and smell backlog in four functional slices — status, charter, doctrine, and kernel —
which are the highest-value targets with the clearest remediation paths. The CLI and core layers
(which contain the project's worst single functions, CC > 80) are out of scope for this mission and
tracked as follow-on work.

---

## Problem Statement

### For contributors and maintainers:
High cyclomatic and cognitive complexity in core domain modules makes changes risky, slow to review,
and difficult to test in isolation. The `# noqa: C901` suppressions mask real design problems that
generate recurring bugs and confusion (evidenced by other issues under #391). Without remediation,
each new feature layered on top of these functions increases the debt interest.

### Measurable evidence:
- Sonar: 23 CRITICAL S3776 violations; project-wide cognitive complexity = 15,596
- Local ruff: 29 violations across four target slices (PLR0912, PLR0913, PLR0911, PLR0915, B, N, SIM)
- Active `# noqa: C901` suppressions in scope: 2 (both on `_extract_governance` in charter)

---

## Scope

### In scope
- `src/specify_cli/status/` — status state machine and event orchestration
- `src/charter/` — charter parsing, compilation, and governance resolution (canonical module only)
- `src/doctrine/` — doctrine asset repository layer
- `src/kernel/` — atomic I/O, regex, and glossary utilities

### Explicitly out of scope
- `src/specify_cli/charter/` — **deprecated**, being removed; do not apply any fixes here
- `reducer.py::_should_apply_event` (CC=14) and `reduce` (CC=10) — both already below the ≤ 15 target threshold; no remediation required in this mission
- CLI command handlers (`cli/commands/`, `agent_utils/`) — addressed in a separate mission; `src/specify_cli/cli/commands/agent/tasks.py` S3776 violations (#594) are explicitly deferred as follow-on
- `core/`, `next/`, `runtime/` modules — separate mission
- Security hotspots (Bandit/S-rules) — tracked via Sonar security workflow; Sonar quality gate hotspot triage and new-code coverage gap (#595) are a separate initiative
- `find_repo_root()` resolution inside worktrees (#539) — architectural research issue, separate research mission required before implementation
- Raising mypy `--strict` compliance project-wide — long-tail effort, separate concern
- Any net-new features or behaviour changes

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The `emit_status_transition` callable in `specify_cli/status/emit.py` presents a public boundary of ≤ 5 parameters. All existing external call sites continue to work without behavioural modification; each call site requires a syntactic update to construct a `TransitionRequest` object, but the observable behaviour is unchanged. | Proposed |
| FR-002 | The `resolved_agent` method in `specify_cli/status/wp_metadata.py` has a measured cyclomatic complexity of ≤ 10, with each resolution step independently testable. | Proposed |
| FR-003 | The `validate_transition` and `_run_guard` functions in `specify_cli/status/transitions.py` accept a `GuardContext` dataclass in place of their current 12 individual arguments. | Proposed |
| FR-004 | The bare `raise ValueError(...)` at `specify_cli/status/wp_metadata.py:194` is replaced with `raise ValueError(...) from err` to preserve the exception chain. | Proposed |
| FR-005 | The exception class `FeatureStatusLockTimeout` in `specify_cli/status/locking.py` is renamed to `FeatureStatusLockTimeoutError`. All import sites are updated. | Proposed |
| FR-006 | The `_extract_governance` method in `src/charter/extractor.py` has a measured cyclomatic complexity of ≤ 10 with no `# noqa` suppression. | Proposed |
| FR-007 | The `resolve_governance` function in `src/charter/resolver.py` is decomposed into independently callable helpers, reducing measured cyclomatic complexity of the parent function to ≤ 8. | Proposed |
| FR-008 | The `_build_references_from_service` function in `src/charter/compiler.py` has ≤ 5 parameters and ≤ 12 branches. | Proposed |
| FR-009 | Named constants replace magic-number depth comparisons (2, 3) in `src/charter/context.py`. | Proposed |
| FR-010 | The `else: if` anti-pattern in `src/charter/parser.py:170` is replaced with `elif`. | Proposed |
| FR-011 | The seven doctrine sub-repository classes (`directives`, `tactics`, `paradigms`, `styleguides`, `mission_step_contracts`, `toolguides`, `procedures`) share a common `_load()` implementation with no duplication, each measuring CC ≤ 4. | Proposed |
| FR-012 | The exception class `CurationAborted` in `src/doctrine/curation/workflow.py` is renamed to `CurationAbortedError`. All import sites are updated. | Proposed |
| FR-013 | Magic workload threshold values (2, 4) in `src/doctrine/agent_profiles/repository.py` are replaced with named module-level constants. | Proposed |
| FR-014 | Import-organization violations in `src/kernel/atomic.py`, `src/kernel/_safe_re.py`, and `src/kernel/glossary_runner.py` (TC003, PTH, I001) are resolved. | Proposed |
| FR-015 | The three callers of `specify_cli.charter` submodules (`specify_cli/runtime/doctor.py`, `specify_cli/next/prompt_builder.py`, `specify_cli/cli/commands/agent/workflow.py`) import from `charter.*` directly. `src/specify_cli/charter/` retains only a re-export `__init__.py`; all internal implementation files are deleted. | Proposed |
| FR-016 | `src/specify_cli/missions/__init__.py` imports `PrimitiveExecutionContext` and `execute_with_glossary` directly from `doctrine.missions`; the intermediate shim files `primitives.py` and `glossary_hook.py` inside `specify_cli/missions/` are deleted. | Proposed |
| FR-017 | `src/specify_cli/cli/commands/mission.py` is a thin shim re-exporting `app` from `mission_type.py`. No duplicate command logic remains in `mission.py`. | Proposed |
| FR-018 | The `workflow.py` call to `top_level_implement()` passes all optional parameters as explicit Python values (not typer `OptionInfo` objects). A regression test calls `top_level_implement()` programmatically (not via subprocess) and asserts the workspace path is returned. (Addresses #571.) | Proposed |
| FR-019 | High-complexity functions in `src/charter/catalog.py` reporting Sonar S3776 violations are decomposed into independently callable helpers, with measured cyclomatic complexity ≤ 10 per function. No `# noqa: C901` suppressions added. (Addresses #594.) | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Ruff exits clean (`ruff check src/`) on all modified files after each work package merges, with zero new suppressions introduced. | 0 ruff violations on changed files | Proposed |
| NFR-002 | Mypy exits clean (`mypy src/`) on all modified files after each work package merges, with no new `# type: ignore` comments added. | 0 new mypy errors on changed files | Proposed |
| NFR-003 | The full test suite passes after each work package merges. No test modifications other than those required to update call sites for renamed exceptions or refactored constructors. | 0 test failures | Proposed |
| NFR-004 | No function in any modified file has a cyclomatic complexity above 15 after the work package that modifies it is merged. | CC ≤ 15 per function (ruff C901) | Proposed |
| NFR-005 | No public API behaviour changes. All refactors are internal restructuring only. External call sites (CLI, tests, other modules) continue to work without behavioural modification, with three categories of required syntactic updates: (1) renamed exception classes require import-site updates; (2) call sites of `emit_status_transition` require construction of a `TransitionRequest` object (FR-001); (3) call sites of `validate_transition` and `_run_guard` require construction of a `GuardContext` object (FR-003). These are mechanical syntactic updates only — observable behaviour is unchanged. | Zero behavioral regressions — all pre-existing passing tests continue to pass after each WP merges | Proposed |
| NFR-006 | Sonar cognitive complexity for each function named in the Functional Requirements section falls below 15 after its work package merges. Baseline: wp_metadata CC=18, transitions CC ~20, charter resolver CC=20, doctrine repositories CC=12×7. | Each named function's Sonar cognitive complexity score < 15 after its WP merges | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | **Charter resolver deferral gate:** FR-007 (`resolve_governance` decomposition) must not be executed if the DRG rebuild EPIC has an active, in-flight mission at the time of implementation. If the DRG rebuild is cancelled or has not started, FR-007 proceeds. The implementer must check for an active DRG mission before starting the charter resolver WP. | Active |
| C-002 | **No touches to `src/specify_cli/charter/`:** This module is deprecated and slated for removal. Any fix attempted there is wasted effort and creates merge conflicts with the removal PR. | Active |
| C-003 | **No behaviour changes:** This mission is structural refactoring only. No new CLI flags, no new configuration keys, no changed output formats, no changed error messages (except exception class names). | Active |
| C-004 | **Rename side effects:** FR-005 (FeatureStatusLockTimeout) and FR-012 (CurationAborted) require all call sites to be updated in the same WP as the rename. Partial renames are not acceptable. | Active |
| C-005 | **Backward-compatible shims (charter):** `from specify_cli.charter import X` must continue to work after FR-015 is applied. The `specify_cli/charter/__init__.py` re-export shim preserves this path. Do not remove the `__init__.py`. | Active |
| C-006 | **Backward-compatible shims (missions):** `from specify_cli.missions import PrimitiveExecutionContext, execute_with_glossary` must continue to work after FR-016 is applied. Only the intermediate shim files are deleted, not the package itself. | Active |

---

## User Scenarios

### Scenario A — Contributor adds a new lane transition

**Current state:** Before contributing, the developer reads `validate_transition` — 12 function arguments, 10 return statements, complex guard evaluation logic all inlined. The function is hard to reason about and takes 30+ minutes to understand.

**After remediation (FR-003):** `validate_transition` accepts a `GuardContext` dataclass. The developer reads a clear struct with named fields and a simplified function body. Adding a new guard condition requires editing one small helper, not the monolithic function.

### Scenario B — Reviewer spots a ruff or mypy CI failure

**Current state:** `emit_status_transition` has 17 arguments with no suppression — any type error at the call site produces a confusing error spanning the entire argument list.

**After remediation (FR-001):** `emit_status_transition` accepts a `TransitionRequest`. Call sites construct the request explicitly with named fields. Type errors are localised to the specific field.

### Scenario C — Developer adds a new doctrine asset type

**Current state:** Adding a new doctrine repository (e.g., `examples/`) requires hand-rolling a new `_load()` method that is a copy of the other 7. Copy-paste error risk is high.

**After remediation (FR-011):** The developer creates a `ExamplesRepository(BaseDoctrineRepository[ExampleModel])` with no `_load()` override needed. The base class handles loading, error handling, and warning emission.

### Scenario D — CI runs ruff on the charter module

**Current state:** `_extract_governance` carries a `# noqa: C901` suppression masking a CC=28 function.

**After remediation (FR-006):** `# noqa: C901` is removed. Ruff passes without suppression. The function is a clean dispatch table.

---

## Success Criteria

1. All `# noqa: C901` suppressions in the four target slices are removed without introducing new suppressions elsewhere.
2. Ruff and mypy exit clean on all files modified by this mission, with zero new suppressions.
3. The full test suite passes with no new test failures.
4. Sonar cognitive complexity for the four target slices is measurably lower than baseline after the mission merges.
5. No public API behaviour change is introduced (verified by the unmodified test suite passing).
6. The `FeatureStatusLockTimeout` and `CurationAborted` names no longer appear anywhere in the codebase.

---

## Assumptions

- The DRG rebuild EPIC is not currently in active mission execution. If it enters active execution before the charter resolver WP starts, FR-007 is deferred and the charter WP proceeds without it (FR-006, FR-008 through FR-010 are independent).
- `src/specify_cli/charter/` will be removed in a separate, concurrent or prior PR. This mission does not drive that removal.
- Existing tests provide sufficient coverage to validate that refactors do not change behaviour. Where tests are sparse (coverage is 28% project-wide), the implementer must add regression tests for the specific functions being refactored before making changes.
- The `TransitionRequest` and `GuardContext` dataclasses will live in the `specify_cli/status/` package namespace (not a shared `models` module), unless architecture review determines otherwise.
- When refactoring extracts a helper whose signature contains only plain Python / stdlib types and which is useful unchanged across more than one slice, the implementing agent must evaluate whether it belongs in `src/kernel/` rather than the local module. The full placement principle is documented in `plan.md § Placement principle for extracted logic`. Logical duplication of a primitive across two or more slices is treated as evidence that a `kernel/` utility is missing.

---

## Doctrine References

This section maps each requirement to the governance directives, refactoring tactics, and procedure
that implementing agents must apply. Agents should retrieve the full tactic text from
`src/doctrine/` before starting each work package.

### Governing Procedure

All work packages in this mission follow the **`refactoring` procedure**
(`src/doctrine/procedures/shipped/refactoring.procedure.yaml`). The procedure mandates:

1. Name the smell before selecting a tactic.
2. Lock behavior with tests before restructuring.
3. Apply in smallest viable steps — one tactic at a time, tests green after each.
4. Commit refactoring separately from feature or bug-fix work.

### Governing Directives

| Directive | Title | Applies to |
|-----------|-------|-----------|
| DIRECTIVE_001 | Architectural Integrity Standard | FR-011 (base class introduction), FR-001/FR-003 (new dataclass boundaries) |
| DIRECTIVE_024 | Locality of Change | All WPs — edits must stay within the stated module slice |
| DIRECTIVE_025 | Boy Scout Rule | Permits minor opportunistic cleanup in touched files; subordinate to DIRECTIVE_024 |
| DIRECTIVE_030 | Test and Typecheck Quality Gate | All WPs — ruff + mypy + pytest must be green before handoff |
| DIRECTIVE_034 | Test-First Development | All WPs — characterization tests required before any structural change |

### Tactic Map by Requirement

#### Status slice (FR-001 – FR-005)

| FR | Smell | Primary tactic | Supporting tactic |
|----|-------|---------------|------------------|
| FR-001 | `emit_status_transition` has 17 arguments — long parameter list | `refactoring-change-function-declaration` (migration mechanics: new `TransitionRequest` dataclass; old signature delegates to new) | `refactoring-encapsulate-record` (design `TransitionRequest` with validation) |
| FR-002 | `resolved_agent` CC=18 — implicit fallback chain with 7 undifferentiated steps | `refactoring-extract-first-order-concept` (each fallback step is a named extractor: `_try_resolve_from_string`, `_try_resolve_from_dict`, `_try_resolve_from_none`) | `refactoring-guard-clauses-before-polymorphism` (flatten the type-dispatch cascade first) |
| FR-003 | `validate_transition`/`_run_guard` have 12 arguments and 10 return statements | `refactoring-change-function-declaration` (introduce `GuardContext` dataclass; migrate callers) + `refactoring-consolidate-conditional-expression` (collapse same-outcome guards into named predicates, reducing return count) | `refactoring-encapsulate-record` (design `GuardContext`) |
| FR-004 | Bare `raise ValueError(...)` in `except ValueError:` block | `change-apply-smallest-viable-diff` (single-line fix: `raise ValueError(...) from err`) | — |
| FR-005 | `FeatureStatusLockTimeout` missing `Error` suffix | `refactoring-change-function-declaration` (simple mechanics: rename class + all import sites in one pass) | — |

#### Charter slice (FR-006 – FR-010)

| FR | Smell | Primary tactic | Supporting tactic |
|----|-------|---------------|------------------|
| FR-006 | `_extract_governance` CC=28 — 26-branch `if/elif` keyed on `field_name` | `refactoring-conditional-to-strategy` (define dispatch table `dict[str, Callable[[Section, GovernanceConfig], None]]`; one handler per field; remove branch after each migration) | `refactoring-guard-clauses-before-polymorphism` (flatten to guards first, then introduce dispatch) |
| FR-007 | `resolve_governance` CC=20 — three independent resource blocks inlined | `refactoring-extract-first-order-concept` (each resource type — paradigms, tools, directives — is an independent concept; extract `_resolve_paradigms()`, `_resolve_tools()`, `_resolve_directives()` each returning a `Resolution` namedtuple) | `refactoring-change-function-declaration` (update parent signature after extraction) |
| FR-008 | `_build_references_from_service` has 7 arguments and 17 branches | `refactoring-change-function-declaration` (reduce args via keyword-only grouping or parameter object) + `refactoring-extract-class-by-responsibility-split` (if multiple reference source types are mixed) | — |
| FR-009 | Magic numbers 2, 3 for `effective_depth` in `context.py` | `refactoring-replace-magic-number-with-symbolic-constant` (introduce `MIN_DEPTH_FOR_SUMMARY = 2`, `DEPTH_FOR_EXTENDED_CONTEXT = 3` at module scope) | — |
| FR-010 | `else: if` anti-pattern in `parser.py:170` | `change-apply-smallest-viable-diff` (mechanical: replace `else: if` with `elif`) | — |

#### Doctrine slice (FR-011 – FR-013)

| FR | Smell | Primary tactic | Supporting tactic |
|----|-------|---------------|------------------|
| FR-011 | 7 × identical `_load()` methods across doctrine sub-repositories (CC=12 each) | `refactoring-extract-class-by-responsibility-split` (map the shared responsibility; extract `BaseDoctrineRepository[T]`; delegate incrementally one repository at a time) | `refactoring-extract-first-order-concept` (the load pattern — walk YAML dir, parse, warn on failure, store — is a reusable first-order concept) + `refactoring-strangler-fig` (migrate each repository class one at a time; remove `_load` override only after its tests pass) |
| FR-012 | `CurationAborted` missing `Error` suffix | `refactoring-change-function-declaration` (simple mechanics: rename + all import sites) | — |
| FR-013 | Magic workload thresholds (2, 4) in `repository.py` | `refactoring-replace-magic-number-with-symbolic-constant` (introduce `MAX_LOW_WORKLOAD = 2`, `MAX_MEDIUM_WORKLOAD = 4`) | — |

#### Kernel slice (FR-014)

| FR | Smell | Approach |
|----|-------|---------|
| FR-014 | TC003 (stdlib imports not in `TYPE_CHECKING` block), PTH105/PTH108 (`os.*` instead of `Path.*`), I001 (unsorted imports) | `change-apply-smallest-viable-diff` — TC003 and I001 are auto-fixable; PTH items require targeted manual edit. |

### Key Tactic Locations

Agents can retrieve full tactic text via:
```
src/doctrine/tactics/shipped/refactoring/<tactic-id>.tactic.yaml
src/doctrine/tactics/shipped/<tactic-id>.tactic.yaml
src/doctrine/procedures/shipped/refactoring.procedure.yaml
```

Or via CLI:
```bash
spec-kitty charter context --action implement --json
```

---

## Key Entities

| Entity | Module | Role in this mission |
|--------|--------|---------------------|
| `TransitionRequest` | `specify_cli/status/emit.py` (new) | Absorbs 17 arguments of `emit_status_transition` |
| `GuardContext` | `specify_cli/status/transitions.py` (new) | Absorbs 12 arguments of `_run_guard` / `validate_transition` |
| `BaseDoctrineRepository[T]` | `src/doctrine/` (new) | Generic base for 7 doctrine sub-repositories |
| `FeatureStatusLockTimeoutError` | `specify_cli/status/locking.py` (rename) | Renamed from `FeatureStatusLockTimeout` |
| `CurationAbortedError` | `doctrine/curation/workflow.py` (rename) | Renamed from `CurationAborted` |
| `_extract_governance` | `src/charter/extractor.py` | Dispatch-table refactor, CC 28 → ≤ 10 |
| `resolve_governance` | `src/charter/resolver.py` | Decomposed into helpers (conditional on C-001) |
