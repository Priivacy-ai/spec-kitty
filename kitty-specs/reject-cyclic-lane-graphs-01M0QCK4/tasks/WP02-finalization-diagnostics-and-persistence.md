---
work_package_id: WP02
title: Finalization Diagnostics and Persistence Safety
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-006
- FR-008
planning_base_branch: fix/reject-cyclic-lane-graphs
merge_target_branch: fix/reject-cyclic-lane-graphs
branch_strategy: Planning artifacts for this mission were generated on fix/reject-cyclic-lane-graphs. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/reject-cyclic-lane-graphs unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - CLI Contract
history:
- at: '2026-08-23T14:06:21Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: debugger-debbie
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_finalize.py
- tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Finalization Diagnostics and Persistence Safety

## Implementation Command

```bash
spec-kitty agent action implement WP02 --agent <name>
```

## Objective

Translate WP01's typed lane-cycle rejection into the governed external contract for canonical mission finalization. Mutating and `--validate-only` calls must fail with the same cycle facts, and a rejected graph must never create or replace `lanes.json`.

## Context

WP01 is a hard prerequisite. Inspect its actual exception/value API rather than assuming the illustrative names in the plan.

Read:

- `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/spec.md` User Stories 1–2, FR-003/004/006/008 and C-002/C-005/C-006.
- `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/plan.md` Design 4–5 and Verification Strategy.
- `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/contracts/lane-dependency-cycle.schema.json` for the exact JSON fields.
- `kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/quickstart.md` for focused verification.

In `mission_finalize.py`, both modes call `compute_lanes` through different branches but converge at the outer `finalize_tasks` exception boundary. `_emit_finalize_error_with_revert_note` currently renders generic errors as `{"error": str(error)}`. The mutating `_compute_and_write_lanes` computes before planning SHA capture and `write_lanes_json`; preserve that order.

## Branch Strategy

- Planning base branch: `fix/reject-cyclic-lane-graphs`
- Final local merge target: `fix/reject-cyclic-lane-graphs`
- Dependency: WP01. Spec Kitty must allocate this WP from the dependency-aware lane base described by `lanes.json`.
- Do not manually branch from an arbitrary checkout and do not edit files outside `owned_files`.

## Subtasks and Detailed Guidance

### T006 — Add red-first JSON and human parity tests

Create `tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py` using existing mission-finalization fixtures and patch seams.

Exercise the canonical command surface `spec-kitty agent mission finalize-tasks`, not the legacy `agent tasks finalize-tasks` command.

For both mutating and `--validate-only` modes with `--json`, assert:

- nonzero exit;
- exactly one terminal JSON object, without a traceback;
- `error_code == "LANE_DEPENDENCY_CYCLE"`;
- nonempty human-readable `error`;
- a closed `cycle_path` with the first lane repeated at the end;
- `cycle_lanes` in first-path-appearance order;
- each entry contains `lane_id` and sorted `wp_ids`;
- the three structured fields are identical between modes.

Add human-output coverage parameterized across both mutating and `--validate-only` modes. For each, prove nonzero exit, no traceback, the complete closed path, and every lane/WP membership fact. Do not overconstrain Rich coloring or whitespace; constrain the actionable facts.

Declare the mandatory module-level taxonomy in the new CLI test file:

```python
pytestmark = [
    pytest.mark.integration,
    pytest.mark.git_repo,
    pytest.mark.non_sandbox,
    pytest.mark.regression,
]
```

Confirm the tests are red because generic rendering omits structured fields.

### T007 — Add persistence-boundary acceptance tests

Using the same real cyclic planning fixture, cover both required initial states:

1. `lanes.json` absent before mutating finalization: it remains absent afterward.
2. A valid existing `lanes.json`: read its raw bytes before the command and assert the bytes are identical afterward.
3. `--validate-only`: recursively inventory the entire fixture feature directory before and after as relative path, file type, and raw bytes; assert identical path sets and contents. Explicitly prove no `status.events.jsonl`, `status.json`, `acceptance-matrix.json`, or `lanes.json` is created when absent. Do not compare mtimes.

Prefer real filesystem assertions around the canonical feature directory. A mock asserting `write_lanes_json` was not called can supplement but cannot replace byte-level acceptance evidence.

The scope is deliberately narrow: do not assert rollback of earlier non-lane state written by finalization. Do not redesign the writer; the correct proof is that the typed exception prevents execution from reaching it.

### T008 — Render the typed exception once

Extend the shared terminal error rendering path in `mission_finalize.py` to recognize WP01's `LaneDependencyCycleError`.

For JSON output, construct:

```json
{
  "error_code": "LANE_DEPENDENCY_CYCLE",
  "error": "human-readable explanation",
  "cycle_path": ["lane-a", "lane-b", "lane-a"],
  "cycle_lanes": [
    {"lane_id": "lane-a", "wp_ids": ["WP01"]},
    {"lane_id": "lane-b", "wp_ids": ["WP02"]}
  ]
}
```

Preserve the existing optional `target_branch_override_revert_error` addition when a revert itself fails. For all non-cycle exceptions, preserve the current generic payload and human behavior exactly.

For human output, show one error followed by a compact cycle path and lane membership. Do not emit once in an inner mode-specific branch and again in the outer handler. Do not parse `str(error)` to recover fields.

Keep imports structured to avoid a new circular dependency. The domain exception may be imported locally by the renderer if that matches existing module conventions.

### T009 — Planning-lane and validate-only boundaries

Add a fixture whose complete final cycle includes `lane-planning` and at least one code lane. Verify the same typed envelope, including sorted planning WP membership.

Ensure validate-only reaches `compute_lanes` in dry-run mode and still fails; it must not report `validation_passed`. Its output must not claim a lanes count or accepted collapse report after the rejection.

Assert the mutating path fails before planning commit SHA capture if that seam can be observed without brittle internal coupling. The primary acceptance assertion remains no `lanes.json` change.

Cover non-cycle behavior in this file only where necessary to prove the specialized renderer does not alter generic failures or success. Do not duplicate WP03's broad DAG matrix.

### T010 — Run finalization regression gates

Run:

```bash
uv run pytest tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py -q
uv run pytest tests/specify_cli/cli/commands/agent -k 'finalize' -q
uv run ruff check src/specify_cli/cli/commands/agent/mission_finalize.py tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py
uv run mypy --strict src/specify_cli/lanes/models.py src/specify_cli/lanes/compute.py src/specify_cli/cli/commands/agent/mission_finalize.py
```

Also validate a representative payload against the mission JSON Schema using `jsonschema.Draft202012Validator`. Record commands and results in the Activity Log.

If a test failure is pre-existing, DIR-013 applies before it may be treated as baseline.

## Test Strategy

Use a real command-boundary fixture wherever practical. Patch only expensive or unrelated commit/bootstrap seams needed to isolate lane finalization. Always make assertions on exit status, captured output, and filesystem state together; any one of those alone is insufficient.

## Contract and Mutation Boundaries

- The JSON Schema allows unrelated terminal metadata, but the four required fields must always be present for this error classification.
- `cycle_path` and `cycle_lanes` must come directly from the exception. The CLI must not rerun graph traversal or normalize values independently.
- `--validate-only` and mutating mode may perform different setup, but they cannot produce different acceptance decisions or structured cycle facts.
- A failed target-branch override revert remains an additional diagnostic; it must not replace or downgrade `LANE_DEPENDENCY_CYCLE`.
- The nonzero exit must be the governed Typer command failure, not an uncaught exception traceback.
- No diagnostic `lanes.json`, temporary replacement, or “last attempted graph” file may be written.

## Evidence to Capture

Append to the Activity Log:

1. The red JSON-contract failure before renderer changes.
2. The exact mutating and validate-only stable field values used for parity comparison.
3. Hash or byte-length evidence showing a pre-existing manifest is unchanged.
4. Proof that the absent-path fixture remains absent.
5. Focused and adjacent regression counts plus ruff/mypy/schema outcomes.

If any fixture requires patching a bootstrap/commit seam, name the seam and explain why it is unrelated to the lane decision. The reviewer should be able to distinguish isolation from accidentally mocking away the behavior under test.

## Definition of Done

- Both modes return identical structured cycle facts and nonzero exits.
- Human output names the complete path and lane membership in both mutating and validate-only modes.
- Existing/absent lane manifests are preserved exactly.
- Validate-only preserves a recursive whole-feature inventory, creates none of the explicitly named artifacts, and never reports success.
- Planning-lane cycles are rejected.
- Generic error behavior is unchanged.
- Focused tests, ruff, strict mypy, and schema validation are recorded.

## Risks and Mitigations

- **Risk**: duplicate terminal output. **Mitigation**: render only at the shared outer exception boundary.
- **Risk**: test mocks bypass computation. **Mitigation**: use the real WP01 error path for at least one acceptance fixture.
- **Risk**: a preservation assertion checks parsed JSON only. **Mitigation**: compare raw bytes.
- **Risk**: broad rollback work sneaks in. **Mitigation**: enforce the C-005 lane-manifest-only boundary.

## Reviewer Guidance

Verify there is one specialized rendering branch, both modes reach it, the JSON matches the checked-in contract, and no change was made to make persistence validate cyclic input. Reject any solution that catches cycles separately in mutating and validate-only branches.

## Activity Log

- 2026-08-23T14:06:21Z – system – Prompt created.
