# Implementation Plan: Reject Cyclic Lane Graphs

**Branch**: `fix/reject-cyclic-lane-graphs` | **Date**: 2026-08-23 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification in `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/spec.md`

## Summary

Make `compute_lanes` the single acceptance authority for the final post-collapse execution-lane dependency graph. After all code and planning-lane dependencies are assembled, a deterministic pure detector finds the first directed cycle using lexical traversal and normalizes it to the smallest lane ID. A cycle raises a typed `LaneDependencyCycleError` before depth calculation or manifest persistence. The mission finalization boundary renders that domain error into the same human or JSON diagnostic for mutating and `--validate-only` calls. Valid DAG behavior remains unchanged.

## Engineering Alignment

- **Invariant**: every `LanesManifest` returned by `compute_lanes` has an acyclic execution-lane dependency graph.
- **Authority**: callers cannot opt out of cycle validation; the pure detector is invoked unconditionally inside `compute_lanes`.
- **Mutation boundary**: rejection occurs before planning SHA capture and `write_lanes_json`, preserving an existing file byte-for-byte or preserving absence.
- **Diagnostic boundary**: the lane domain owns classification and normalized cycle facts; the CLI owns presentation and exit behavior.
- **Compatibility**: `_compute_lane_depths` retains its recursion guard for defensive direct use, while public `compute_lanes` no longer accepts cyclic results.
- **Scope**: authored work-package validation, ownership-collapse rules, automatic cycle repair, non-lane rollback, and the legacy `agent tasks finalize-tasks` command are unchanged.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Python standard-library graph traversal and dataclasses; Typer/Rich at the existing CLI boundary; no new runtime dependency
**Storage**: filesystem `lanes.json`; rejected graphs are diagnostic-only and never persisted
**Testing**: pytest 9, pytest-benchmark for the governed performance fixture, mypy strict, ruff
**Target Platform**: Linux, macOS, and Windows 10+
**Project Type**: single Python CLI package
**Performance Goals**: p95 at most 100 ms across 20 measured runs after 5 warm-ups for 100 lanes and 500 edges
**Constraints**: deterministic across insertion order and hash seeds; closed cycle path; nonzero failure without traceback; exact structured envelope; byte-identical preservation of prior manifest
**Scale/Scope**: one computation seam, one typed error contract, one CLI error renderer, focused unit/CLI/integration/performance coverage

## Charter Check

### Pre-design gate

| Gate | Status | Plan response |
|---|---|---|
| Cross-platform Python 3.11+ | Pass | Use only deterministic standard-library data structures and existing project dependencies. |
| Tests for new functionality | Pass | Add detector, computation, CLI parity, persistence, determinism, planning-lane, and performance coverage. |
| Strict typing and public API documentation | Pass | Type all new values and document the typed domain exception/detector contract. |
| Identifier determinism | Pass | Lane IDs are existing ASCII identifiers; traversal and WP membership are explicitly sorted. |
| Ownership and mutation boundaries | Pass | Domain computation rejects before persistence; the existing writer remains unchanged. |
| Single canonical authority | Pass | `compute_lanes` is the non-bypassable construction door for accepted manifests. |
| Regression vigilance | Pass | Preserve valid DAG output and the direct depth helper's recursion guard; replace the contradictory public acceptance assertion. |
| ATDD-first discipline | Pass | Begin implementation with failing acceptance tests for mutating and validate-only rejection. |
| Pre-existing failure reporting | Pass | Any genuinely pre-existing failure encountered during implementation must be filed under DIR-013 before being treated as baseline. |

No charter violation or exception is required.

### Post-design re-check

The design introduces no alternate persistence path, topology inference, dependency, or platform-specific behavior. The JSON schema makes the externally observable diagnostic reviewable, and the quickstart makes the required evidence reproducible. All gates remain passed.

## Project Structure

### Documentation for this mission

```text
kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── lane-dependency-cycle.schema.json
```

### Source and tests

```text
src/specify_cli/
├── lanes/
│   ├── compute.py
│   └── models.py
└── cli/commands/agent/
    └── mission_finalize.py

tests/
├── lanes/
│   └── test_compute.py
├── specify_cli/lanes/
│   ├── test_compute_lane_depths_cycle_safety.py
│   ├── test_lane_dependency_cycle_detection.py
│   ├── test_lane_dependency_cycle_determinism.py
│   ├── test_lane_dependency_cycle_cli_determinism.py
│   └── test_lane_dependency_cycle_performance.py
└── specify_cli/cli/commands/agent/
    └── test_finalize_lane_dependency_cycle.py
```

**Structure Decision**: keep the change within the existing lane computation and mission-finalization seams. The pure detector and typed error live with lane computation; no new package or persistence abstraction is needed. Tests are split by domain behavior and CLI contract so implementation can remain focused without duplicating acceptance authority.

## Design

### 1. Deterministic domain detector

Add a pure internal function accepting the complete `lane_deps` mapping and returning either `None` or one normalized closed cycle. It performs iterative depth-first search over sorted lane IDs and sorted dependency IDs, stops at the first directed back edge, constructs the closed path, and rotates its unique members so the lexically smallest lane begins the path while preserving edge direction. An explicit stack is required so FR-010 holds for valid mission graphs beyond Python's recursion limit. Complexity is O(V + E), excluding small sorting costs.

### 2. Typed rejection

Add `LaneDependencyCycleError` as a `LaneComputationError` subclass. It carries immutable `cycle_path` and ordered cycle-lane membership values. The error code is the stable constant `LANE_DEPENDENCY_CYCLE`; `str(error)` supplies the human explanation without requiring callers to parse it.

### 3. Non-bypassable acceptance gate

Invoke the detector inside `compute_lanes` after every code and `lane-planning` dependency is present in `lane_deps` and before `_compute_lane_depths`. On detection, derive sorted WP membership from the existing lane assignment and raise the typed error. A returned manifest is therefore valid by construction.

### 4. Shared CLI rendering

Extend the common finalization error renderer to recognize `LaneDependencyCycleError`. JSON output follows `contracts/lane-dependency-cycle.schema.json`; human output includes the closed path and each lane's WPs. Both mutating and `--validate-only` paths already converge on `compute_lanes` and the outer renderer, so no mode-specific validator or reinterpretation is added.

### 5. Persistence guarantee

Keep `write_lanes_json` unchanged. The mutating path computes before capturing the planning commit SHA and before calling the writer. Tests assert that cyclic failure leaves an absent file absent and an existing file byte-identical. The specification's narrower guarantee does not attempt to roll back earlier non-lane state.

## Verification Strategy

1. Add ATDD coverage for two-lane post-collapse rejection in mutating and `--validate-only` modes, including exact JSON and file preservation.
2. Unit-test self-loops, three-lane cycles, multiple cycles, lexical selection, normalization, planning-lane participation, clean DAGs, and sorted WP membership.
3. Permute mapping/dependency insertion order at the domain seam, then invoke canonical `finalize-tasks --validate-only --json` in fresh subprocesses under at least three `PYTHONHASHSEED` values; compare the structured cycle fields byte-for-byte.
4. Change the existing public `compute_lanes` cyclic test to expect the typed rejection; retain direct `_compute_lane_depths` tests proving defensive termination and add a cycle longer than `sys.getrecursionlimit()` that must raise the typed error.
5. Run focused pytest, ruff, and mypy checks, then the relevant broader lane/finalization suites.
6. Run a pytest-benchmark fixture with 5 warm-ups and 20 rounds over a fixed 100-lane/500-edge graph and assert the governed 100 ms p95 budget.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Existing callers relied on permissive cyclic results | Treat returned-manifest acyclicity as the public postcondition; retain only the low-level helper's defensive behavior. |
| Generic cycle utility is nondeterministic | Use a lane-specific detector with explicit sorted traversal and normalization rather than changing unrelated generic callers. |
| JSON paths differ between modes | Carry facts in one typed error and serialize in the shared outer finalization renderer. |
| Diagnostics accidentally reach persistence | Reject before depth/manifest acceptance and assert writer non-invocation plus byte-level file preservation. |
| Performance assertion is noisy | Benchmark only the pure detector on a fixed graph with governed warm-up/round counts and use the p95 statistic. |

## Complexity Tracking

No charter violations require justification. The separate pure helper is internal implementation structure, not a second acceptance authority.
