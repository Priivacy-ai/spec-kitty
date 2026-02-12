---
work_package_id: "WP06"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "Test and document 7-to-4 lane collapse mapping"
phase: "Wave 1 - Independent Fixes"
lane: "planned"  # DO NOT EDIT - use: spec-kitty agent tasks move-task WP06 --to <lane>
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-12T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Test and document 7-to-4 lane collapse mapping

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP06
```

No dependencies — branches directly from the 2.x branch.

---

## Objectives & Success Criteria

- Parametrized tests cover all 7 input lanes with correct 4-lane output values
- Unknown lane input raises `ValueError` (tested)
- Mapping extracted to a named, reusable constant/function if not already
- `contracts/lane-mapping.md` verified to match actual implementation in `emitter.py`

## Context & Constraints

- **Delivery branch**: 2.x
- **Mapping location**: `src/specify_cli/sync/emitter.py` approximately line 46
- **Expected mapping**: PLANNED→planned, CLAIMED→doing, IN_PROGRESS→doing, FOR_REVIEW→for_review, DONE→done, BLOCKED→doing, CANCELED→done
- **Lane enum**: `src/specify_cli/spec_kitty_events/status.py` — `Lane` enum with 7 values
- **Alias**: `LANE_ALIASES = {"doing": IN_PROGRESS}` — resolved before collapse
- **Contract doc**: `kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md` (already exists from Phase 1 planning)
- **Reference**: `spec.md` (User Story 5, FR-012, FR-013), `plan.md` (WP06)

## Subtasks & Detailed Guidance

### Subtask T025 – Add parametrized tests for all 7 lanes

- **Purpose**: Ensure every 7-lane value maps to the correct 4-lane sync value.
- **Steps**:
  1. Find the mapping function in `src/specify_cli/sync/emitter.py` on 2.x:
     ```bash
     grep -n "lane\|collapse\|mapping\|LANE" src/specify_cli/sync/emitter.py
     ```
  2. Identify the function signature (e.g., `collapse_lane(lane: Lane) -> str` or inline dict)
  3. Create `tests/specify_cli/sync/test_lane_mapping.py`:
     ```python
     import pytest
     from specify_cli.spec_kitty_events.status import Lane
     from specify_cli.sync.emitter import collapse_lane  # or actual function name

     @pytest.mark.parametrize("input_lane,expected_output", [
         (Lane.PLANNED, "planned"),
         (Lane.CLAIMED, "doing"),
         (Lane.IN_PROGRESS, "doing"),
         (Lane.FOR_REVIEW, "for_review"),
         (Lane.DONE, "done"),
         (Lane.BLOCKED, "doing"),
         (Lane.CANCELED, "done"),
     ])
     def test_lane_collapse_mapping(input_lane, expected_output):
         """Each 7-lane value maps to the correct 4-lane sync value."""
         assert collapse_lane(input_lane) == expected_output
     ```
  4. Verify test runs: `python -m pytest tests/specify_cli/sync/test_lane_mapping.py -v`
- **Files**: `tests/specify_cli/sync/test_lane_mapping.py` (new)
- **Parallel?**: No — must identify the mapping function first
- **Notes**: The actual function name may differ from `collapse_lane` — read `emitter.py` to find it.

### Subtask T026 – Test unknown lane value raises ValueError

- **Purpose**: Prevent silent data corruption if an unknown lane value is passed to the mapping.
- **Steps**:
  1. Add a test for unknown lane handling:
     ```python
     def test_unknown_lane_raises_value_error():
         """Unknown lane value raises ValueError, not silently maps."""
         with pytest.raises(ValueError, match="Unknown lane"):
             collapse_lane("NONEXISTENT")

     def test_none_lane_raises():
         """None input raises appropriate error."""
         with pytest.raises((ValueError, TypeError)):
             collapse_lane(None)
     ```
  2. If the current implementation doesn't raise ValueError for unknown lanes:
     - Add a guard clause to the mapping function:
       ```python
       def collapse_lane(lane: Lane) -> str:
           mapping = {
               Lane.PLANNED: "planned",
               Lane.CLAIMED: "doing",
               # ... etc
           }
           if lane not in mapping:
               raise ValueError(f"Unknown lane: {lane}")
           return mapping[lane]
       ```
- **Files**: `tests/specify_cli/sync/test_lane_mapping.py` (extend), possibly `src/specify_cli/sync/emitter.py` (add guard)
- **Parallel?**: No — depends on T025's function identification

### Subtask T027 – Extract mapping to named constant/function

- **Purpose**: Make the mapping explicit, documented, and reusable across the codebase.
- **Steps**:
  1. Read `emitter.py` to see if the mapping is already a named dict/function or is inline
  2. If inline (e.g., inside a larger function as a local dict), extract to module level:
     ```python
     # At module level in emitter.py
     LANE_COLLAPSE_MAP: dict[Lane, str] = {
         Lane.PLANNED: "planned",
         Lane.CLAIMED: "doing",
         Lane.IN_PROGRESS: "doing",
         Lane.FOR_REVIEW: "for_review",
         Lane.DONE: "done",
         Lane.BLOCKED: "doing",
         Lane.CANCELED: "done",
     }

     def collapse_lane(lane: Lane) -> str:
         """Collapse a 7-lane canonical status to a 4-lane sync payload value.

         See: kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md
         """
         try:
             return LANE_COLLAPSE_MAP[lane]
         except KeyError:
             raise ValueError(f"Unknown lane: {lane}. Expected one of {list(Lane)}")
     ```
  3. If already extracted: verify it has proper error handling and docstring. Add if missing.
  4. Ensure all call sites use the extracted function/constant (no duplicate inline mappings)
- **Files**: `src/specify_cli/sync/emitter.py` (edit)
- **Parallel?**: No — depends on reading emitter.py

### Subtask T028 – Verify contract doc matches implementation

- **Purpose**: Ensure `contracts/lane-mapping.md` is accurate after reading the actual 2.x implementation.
- **Steps**:
  1. Read the actual mapping from `emitter.py` on 2.x
  2. Read `kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md`
  3. Compare every entry:
     - Are all 7 lanes covered in the contract doc?
     - Do the 4-lane output values match?
     - Is the alias resolution documented correctly?
     - Are edge cases (None from_lane, same from/to, unknown lane) documented?
  4. If any discrepancies: update the contract doc to match the implementation
  5. If the implementation has bugs (e.g., missing a lane): fix the code, not the doc
- **Files**: `kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md` (verify/update)
- **Parallel?**: No — depends on T025-T027 understanding the implementation

## Test Strategy

- **New tests**: ~9 parametrized test cases (7 lanes + unknown + None)
- **Run command**: `python -m pytest tests/specify_cli/sync/test_lane_mapping.py -v`
- **Baseline**: Existing sync tests must still pass

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Mapping function has different name/signature on 2.x | Search emitter.py for "lane" and read the actual code |
| Lane enum import path differs | Verify: `from specify_cli.spec_kitty_events.status import Lane` |
| Contract doc was written before reading 2.x code | T028 explicitly validates and corrects discrepancies |

## Review Guidance

- Verify all 7 lanes are tested with correct expected values
- Verify ValueError is raised for unknown lanes
- Verify mapping is extracted to a named, documented constant/function
- Verify contract doc matches the actual implementation
- Run `python -m pytest tests/specify_cli/sync/test_lane_mapping.py -v` — all 9+ tests green

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.
