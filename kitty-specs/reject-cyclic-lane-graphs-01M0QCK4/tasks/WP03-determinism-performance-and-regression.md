---
work_package_id: WP03
title: Determinism Performance and Regression Proof
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-009
- FR-010
planning_base_branch: fix/reject-cyclic-lane-graphs
merge_target_branch: fix/reject-cyclic-lane-graphs
branch_strategy: Planning artifacts for this mission were generated on fix/reject-cyclic-lane-graphs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reject-cyclic-lane-graphs unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 2 - Release Evidence
history:
- at: '2026-08-23T14:06:21Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: debugger-debbie
authoritative_surface: tests/lanes/
create_intent:
- tests/specify_cli/lanes/test_lane_dependency_cycle_determinism.py
- tests/specify_cli/lanes/test_lane_dependency_cycle_performance.py
execution_mode: code_change
owned_files:
- tests/lanes/test_compute.py
- tests/specify_cli/lanes/test_lane_dependency_cycle_determinism.py
- tests/specify_cli/lanes/test_lane_dependency_cycle_performance.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Determinism, Performance, and Regression Proof

## Implementation Command

```bash
spec-kitty agent action implement WP03 --agent <name>
```

## Objective

Supply independent release evidence that WP01's authoritative detector preserves every valid DAG, selects byte-stable diagnostics across equivalent inputs and process hash seeds, terminates safely, and meets the 100-lane/500-edge p95 budget.

## Context

This package depends only on WP01 and can execute in parallel with WP02. It owns test files only; do not change `compute.py` or `mission_finalize.py`. If evidence exposes a production defect, reject/return feedback to WP01 rather than crossing ownership boundaries.

Read:

- `spec.md` FR-007/009/010, NFR-002/003, SC-004/005.
- `plan.md` Verification Strategy and Risks.
- `research.md` R-003 and R-006.
- `quickstart.md` determinism, performance, and broad gate commands.

## Branch Strategy

- Planning base branch: `fix/reject-cyclic-lane-graphs`
- Final local merge target: `fix/reject-cyclic-lane-graphs`
- Dependency: WP01. Execution worktree allocation and dependency base come from `lanes.json`.
- WP02 is a sibling after WP01 and may run concurrently; its files are outside this WP's ownership.

## Subtasks and Detailed Guidance

### T011 — Lock clean-DAG compatibility

Update `tests/lanes/test_compute.py` to strengthen public postconditions without rewriting unrelated coverage.

Select representative existing fixtures for:

- independent lanes;
- a linear dependency chain;
- fan-in/fan-out;
- ownership collapse that remains acyclic;
- planning-artifact participation if already represented in this file.

Assert the same lane membership, sorted dependency tuples, parallel groups, collapse report, mission/target branch fields, and planning-lane behavior as before WP01. Avoid asserting `computed_at` exact values.

Add at least one explicit assertion that every returned manifest graph is acyclic using a test-only helper or topological check. Do not introduce a second production validator.

The intent is regression locking, not snapshotting the entire manifest format. Keep assertions readable enough to identify which invariant drifted.

### T012 — Add input-order and multiple-cycle matrix

Create `tests/specify_cli/lanes/test_lane_dependency_cycle_determinism.py`.

Build a graph with at least two available directed cycles and a deterministic expected winner. Construct equivalent inputs using:

- forward and reverse dictionary insertion order;
- varied dependency-list order;
- set materialization in different orders before conversion;
- different ownership-manifest insertion order;
- repeated runs in the same process.

Capture only stable facts from `LaneDependencyCycleError`: `error_code`, `cycle_path`, and `(lane_id, wp_ids)` values. Serialize those facts with stable JSON options and assert byte equality.

Also assert:

- the path is closed;
- every edge in the path exists;
- the first/closing member is the smallest lane ID in the selected cycle;
- membership excludes the repeated closer;
- WP IDs are sorted.

Do not require the human sentence to be byte-identical unless the implementation explicitly governs it; the specification governs structured cycle details.

### T013 — Add cross-process hash-seed proof

In the determinism test file, add a subprocess-based test that runs a minimal Python snippet against the working-tree package under at least three seeds, for example `1`, `7`, and `97`.

Requirements:

1. Set `PYTHONHASHSEED` explicitly in a copied environment.
2. Ensure `PYTHONPATH` or the command invocation imports this checkout, not a globally installed Spec Kitty.
3. Construct equivalent cyclic input and catch the typed exception.
4. Print only canonical JSON containing the stable fields.
5. Assert subprocess return codes are zero and stdout bytes are equal.
6. Include stderr in assertion diagnostics without mixing it into the compared payload.

Keep the snippet compact but understandable. Prefer `sys.executable -c` so the interpreter matches the test environment. Avoid shell quoting dependencies for Windows compatibility.

### T014 — Add governed performance benchmark

Create `tests/specify_cli/lanes/test_lane_dependency_cycle_performance.py` using the repository's existing pytest-benchmark conventions and performance marker/environment gate.

Construct a deterministic fixed graph of exactly 100 lane IDs and 500 dependency edges. It must exercise the pure detector and include a known cycle near a traversal position that prevents the benchmark from measuring only an immediate first-edge return.

Benchmark requirements from NFR-003:

- 5 warm-up runs;
- 20 measured runs;
- compute or retrieve p95 from measured durations;
- assert p95 ≤ 0.100 seconds on the CI runner;
- keep fixture construction outside the measured callable;
- assert the result is the expected normalized cycle so speed cannot replace correctness.

Use the existing off-PR performance gating convention if required to avoid noisy blocking PR checks, but ensure the configured performance job actually selects the test. Do not replace the statistical requirement with a single `time.monotonic()` observation.

### T015 — Run broad proof and schema check

Run:

```bash
uv run pytest tests/lanes tests/specify_cli/lanes -q
PYTHONHASHSEED=1 uv run pytest tests/specify_cli/lanes/test_lane_dependency_cycle_determinism.py -q
PYTHONHASHSEED=7 uv run pytest tests/specify_cli/lanes/test_lane_dependency_cycle_determinism.py -q
PYTHONHASHSEED=97 uv run pytest tests/specify_cli/lanes/test_lane_dependency_cycle_determinism.py -q
SPEC_KITTY_RUN_PERFORMANCE=1 uv run pytest tests/specify_cli/lanes/test_lane_dependency_cycle_performance.py -m benchmark
uv run ruff check tests/lanes/test_compute.py tests/specify_cli/lanes/test_lane_dependency_cycle_determinism.py tests/specify_cli/lanes/test_lane_dependency_cycle_performance.py
```

Validate `contracts/lane-dependency-cycle.schema.json` with `Draft202012Validator.check_schema` and validate a representative exception-derived payload if WP02 is already integrated; otherwise validate a representative payload matching WP01 facts without importing WP02.

Record exact counts/timings. If a pre-existing failure appears, comply with DIR-013 rather than silently excluding it.

## Test Strategy

This entire WP is test evidence. Keep correctness, determinism, and performance assertions separated so a failure explains its dimension. Tests must work on Linux, macOS, and Windows; avoid shell-only subprocess construction and timing assumptions outside the governed benchmark.

## Evidence Design Boundaries

- Keep stable-field serialization local to tests; do not add production serialization solely for this WP.
- Do not reuse the production detector to assert that returned valid manifests are acyclic; use an independent topological property check.
- Do not seed randomness without recording the seed. Prefer enumerated construction-order variants for reproducibility.
- Do not loosen the p95 ceiling when a runner is slow. Diagnose fixture or pipeline selection; any charter-governed exception requires explicit approval.
- Do not mark the benchmark as ordinary fast coverage if repository policy routes statistical benchmarks off the blocking PR path.
- Do not edit sibling-owned source when tests fail. Report a focused rejection with the smallest reproducer to WP01 or WP02.

## Evidence to Capture

Record in the Activity Log:

1. The list of construction-order variants and their common normalized path.
2. The three hash seeds, subprocess interpreter, and common stdout digest.
3. Benchmark rounds, warm-ups, p95, fixture vertex count, and edge count.
4. Broad lane-suite pass/fail totals.
5. JSON Schema validation result and whether the payload came from an integrated exception or a representative fixture.

The final review handoff should distinguish blocking correctness evidence from the environment-gated performance job so future maintainers know where each guarantee is enforced.

## Definition of Done

- Representative acyclic manifests preserve their observable fields.
- Equivalent multi-cycle inputs produce byte-identical stable facts.
- At least three process hash seeds produce identical output.
- The fixed 100/500 fixture meets p95 ≤100 ms under the governed run shape.
- The diagnostic JSON Schema is valid and accepts a representative payload.
- Broad lane suites and ruff pass, or any pre-existing failure is handled under DIR-013.

## Risks and Mitigations

- **Risk**: benchmark measures fixture setup. **Mitigation**: prebuild all mappings outside the measured function.
- **Risk**: hash-seed test imports another installation. **Mitigation**: assert/import from the repository's `src` path in the subprocess.
- **Risk**: test duplicates the production algorithm. **Mitigation**: validate graph properties independently rather than copying DFS implementation.
- **Risk**: sibling WP conflict. **Mitigation**: never edit WP02's CLI source/test file.

## Reviewer Guidance

Verify the determinism matrix actually changes construction order, the hash-seed check uses separate processes, and the benchmark reports a statistical p95 with the exact fixture scale. Reject evidence that compares timestamps, benchmarks CLI startup, or weakens the 100 ms requirement.

## Activity Log

- 2026-08-23T14:06:21Z – system – Prompt created.
