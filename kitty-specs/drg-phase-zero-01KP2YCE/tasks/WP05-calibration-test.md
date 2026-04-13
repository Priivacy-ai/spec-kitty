---
work_package_id: WP05
title: Surface Calibration Test
dependencies:
- WP03
requirement_refs:
- FR-008
- FR-009
- FR-010
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
agent: "claude:opus-4-6:implementer:implementer"
shell_pid: "74141"
history:
- date: '2026-04-13'
  author: claude
  action: created
  note: Initial WP generation from /spec-kitty.tasks
authoritative_surface: tests/charter/
execution_mode: code_change
owned_files:
- tests/charter/test_surface_calibration.py
tags: []
---

# WP05: Surface Calibration Test

## Objective

Assert that each action's governance surface respects the minimum-effective-dose calibration inequalities. When violated, the fix is adjusting `scope` edges in `graph.yaml`, never adding filtering logic.

## Context

The calibration inequalities from the spec:

```
|context(specify)| < |context(plan)| < |context(implement)|
|context(tasks)|   < |context(implement)|
|context(review)|  ≈ |context(implement)|
```

Where `|context(X)|` is the number of distinct artifacts reachable from the action node `X` via the DRG query (scope + requires + suggests). The `≈` for review means within 80% of implement's surface.

Current measured surfaces after WP02 calibration should satisfy these. This test ensures they stay satisfied as the graph evolves.

**Key constraint (FR-009)**: The DRG is the only knob. If this test fails, the fix is editing `graph.yaml` scope edges, not adding conditional logic in code.

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- Execution worktrees allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T028: Implement surface size measurement

**Purpose**: Measure the governance surface for a given action using the DRG.

**Steps**:
1. Create `tests/charter/test_surface_calibration.py`
2. Implement a helper function `measure_surface(graph: DRGGraph, action_urn: str, depth: int = 2) -> int`:
   - Call `resolve_context(graph, action_urn, depth)` from `src/doctrine/drg/query.py`
   - Return `len(resolved.artifact_urns)` (count of distinct artifacts)
3. Also implement `measure_surface_detailed(graph: DRGGraph, action_urn: str, depth: int = 2) -> dict[str, int]`:
   - Break down by artifact kind: how many directives, tactics, styleguides, etc.
   - Useful for debugging when inequalities are violated
4. Load the merged DRG from `src/doctrine/graph.yaml` in a fixture

**Files**: `tests/charter/test_surface_calibration.py`

**Validation**:
- [ ] Surface measurement returns a positive integer for each action
- [ ] Detailed measurement breaks down by kind
- [ ] Uses DRG query primitives (not reimplementing traversal)

### T029: Assert calibration inequalities

**Purpose**: The core test that enforces minimum-effective-dose ordering.

**Steps**:
1. Implement the calibration test:
   ```python
   REVIEW_THRESHOLD = 0.80  # review must be >= 80% of implement
   
   def test_surface_calibration_inequalities(loaded_graph):
       """Each action's surface respects minimum-effective-dose ordering."""
       graph = loaded_graph
       
       specify = measure_surface(graph, "action:software-dev/specify")
       plan = measure_surface(graph, "action:software-dev/plan")
       tasks = measure_surface(graph, "action:software-dev/tasks")
       implement = measure_surface(graph, "action:software-dev/implement")
       review = measure_surface(graph, "action:software-dev/review")
       
       # Strict ordering
       assert specify < plan, (
           f"specify ({specify}) must be < plan ({plan}). "
           f"Fix: remove scope edges from specify or add to plan in graph.yaml"
       )
       assert plan < implement, (
           f"plan ({plan}) must be < implement ({implement}). "
           f"Fix: add scope edges to implement or remove from plan in graph.yaml"
       )
       assert tasks < implement, (
           f"tasks ({tasks}) must be < implement ({implement}). "
           f"Fix: remove scope edges from tasks or add to implement in graph.yaml"
       )
       
       # Approximate equality for review
       assert review >= implement * REVIEW_THRESHOLD, (
           f"review ({review}) must be >= {REVIEW_THRESHOLD*100}% of implement ({implement}). "
           f"Actual: {review/implement*100:.0f}%. "
           f"Fix: add scope edges to review in graph.yaml"
       )
   ```
2. Add a reporting test that prints the current surface sizes:
   ```python
   def test_surface_report(loaded_graph):
       """Report current surface sizes for visibility."""
       graph = loaded_graph
       for action in ["specify", "plan", "tasks", "implement", "review"]:
           urn = f"action:software-dev/{action}"
           size = measure_surface(graph, urn)
           detailed = measure_surface_detailed(graph, urn)
           print(f"{action}: {size} total ({detailed})")
   ```
3. The reporting test always passes -- it's for CI output visibility, not enforcement.

**Files**: `tests/charter/test_surface_calibration.py`

**Validation**:
- [ ] specify < plan < implement
- [ ] tasks < implement
- [ ] review >= 80% of implement
- [ ] Error messages tell the user exactly what to fix (scope edges in graph.yaml)

### T030: Verify DRG-only-knob rule

**Purpose**: Structural audit confirming that no per-action filtering logic exists anywhere.

**Steps**:
1. Add a test that scans `src/charter/context.py` for `build_context_v2`:
   - Parse the function body with `ast`
   - Assert no `if` statements that compare `action` to specific action name strings
   - Assert no dict/set of action names used for filtering
2. Add a test that scans `src/doctrine/drg/query.py`:
   - Assert no action-specific logic in query primitives
   - Query functions should be generic (work with any graph, any node kinds)
3. These are structural regression tests. They prevent future drift where someone adds a quick-fix filter instead of adjusting the graph.

**Files**: `tests/charter/test_surface_calibration.py`

**Validation**:
- [ ] No action-specific filtering in `build_context_v2`
- [ ] No action-specific logic in DRG query primitives
- [ ] Tests would fail if someone added `if action == "specify": skip(...)` logic

### T031: Configure CI triggers

**Purpose**: Ensure calibration test runs alongside the invariant test.

**Steps**:
1. Verify `tests/charter/test_surface_calibration.py` is picked up by the existing test runner
2. If the CI configuration from WP04 T027 already covers `tests/charter/`, no additional work needed
3. Ensure changes to `src/doctrine/graph.yaml` trigger this test (graph edits are the most likely source of calibration regressions)

**Files**: CI configuration files (if modification needed)

**Validation**:
- [ ] Test runs in CI when graph.yaml changes
- [ ] Test is part of the standard test suite

## Definition of Done

1. Calibration inequalities hold for all shipped actions
2. Review surface is >= 80% of implement surface
3. DRG-only-knob rule verified by structural test
4. Error messages tell the user to fix graph.yaml, not code
5. Test runs in CI alongside invariant test
6. mypy --strict clean

## Risks

- **Threshold too strict/loose**: The 80% threshold for review ≈ implement is a judgment call. If review legitimately needs a different surface from implement, the threshold can be adjusted. But changing it should be a deliberate decision, not a way to avoid fixing calibration.
- **Future actions**: If new actions are added to the software-dev mission, the test should detect them and require calibration entries. The test should not silently skip new actions.

## Reviewer Guidance

- Verify error messages are actionable (point to graph.yaml, not code)
- Verify the structural tests would actually catch filtering logic (not just checking string literals)
- Verify the 80% threshold is applied correctly (review >= 0.80 * implement, not the other way)
- Verify the test loads the real `graph.yaml` from WP02, not a hand-crafted fixture

## Activity Log

- 2026-04-13T09:26:10Z – claude:opus-4-6:implementer:implementer – shell_pid=74141 – Started implementation via action command
- 2026-04-13T09:30:29Z – claude:opus-4-6:implementer:implementer – shell_pid=74141 – Calibration test verifies all inequalities against real graph.yaml. Untracked tests/charter/fixtures/ belongs to WP04 (parallel).
