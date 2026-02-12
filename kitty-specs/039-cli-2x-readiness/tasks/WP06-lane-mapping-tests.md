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

- Parametrized tests cover all 7 canonical lanes with correct 4-lane sync outputs
- Invalid lane input in the transition pipeline is rejected (`TransitionError`)
- Mapping remains centralized in `status/emit.py` (`_SYNC_LANE_MAP`)
- `contracts/lane-mapping.md` verified to match actual implementation in `status/emit.py`

## Context & Constraints

- **Delivery branch**: 2.x
- **Mapping location**: `src/specify_cli/status/emit.py` (`_SYNC_LANE_MAP`)
- **Expected mapping**: planned→planned, claimed→planned, in_progress→doing, for_review→for_review, done→done, blocked→doing, canceled→planned
- **Lane enum**: `src/specify_cli/status/models.py` — `Lane` enum with 7 values
- **Alias**: `LANE_ALIASES = {"doing": "in_progress"}` in `src/specify_cli/status/transitions.py`
- **Contract doc**: `kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md` (already exists from Phase 1 planning)
- **Reference**: `spec.md` (User Story 5, FR-012, FR-013), `plan.md` (WP06)

## Subtasks & Detailed Guidance

### Subtask T025 – Add parametrized tests for all 7 lanes

- **Purpose**: Ensure every canonical lane maps to the expected 4-lane sync value.
- **Steps**:
  1. Confirm mapping in `src/specify_cli/status/emit.py`:
     ```bash
     grep -n "SYNC_LANE_MAP\|lane\|mapping" src/specify_cli/status/emit.py
     ```
  2. Create `tests/specify_cli/status/test_sync_lane_mapping.py`:
     ```python
     import pytest
     from specify_cli.status.emit import _SYNC_LANE_MAP

     @pytest.mark.parametrize("input_lane,expected_output", [
         ("planned", "planned"),
         ("claimed", "planned"),
         ("in_progress", "doing"),
         ("for_review", "for_review"),
         ("done", "done"),
         ("blocked", "doing"),
         ("canceled", "planned"),
     ])
     def test_sync_lane_map_values(input_lane, expected_output):
         assert _SYNC_LANE_MAP[input_lane] == expected_output
     ```
  3. Verify test runs: `python -m pytest tests/specify_cli/status/test_sync_lane_mapping.py -v`
- **Files**: `tests/specify_cli/status/test_sync_lane_mapping.py` (new)
- **Parallel?**: No — foundation for T026-T028

### Subtask T026 – Test invalid lane handling through transition pipeline

- **Purpose**: Ensure invalid lanes are rejected before canonical persistence/fan-out.
- **Steps**:
  1. Add test for invalid lane transition:
     ```python
     import pytest
     from specify_cli.status.emit import TransitionError, emit_status_transition

     def test_invalid_to_lane_raises_transition_error(feature_dir):
         with pytest.raises(TransitionError):
             emit_status_transition(
                 feature_dir=feature_dir,
                 feature_slug="039-cli-2x-readiness",
                 wp_id="WP01",
                 to_lane="NONEXISTENT",
                 actor="tester",
             )
     ```
  2. Verify behavior is enforced via alias resolution + transition validation.
- **Files**: `tests/specify_cli/status/test_sync_lane_mapping.py` (extend)
- **Parallel?**: No — depends on T025

### Subtask T027 – Verify mapping remains centralized

- **Purpose**: Prevent contract drift from duplicated lane-collapse logic.
- **Steps**:
  1. Confirm `_SYNC_LANE_MAP` exists and is documented in `src/specify_cli/status/emit.py`
  2. Search `src/specify_cli/` for duplicate 7→4 mapping dicts and consolidate if found
  3. Add a brief comment in `emit.py` if needed to mark `_SYNC_LANE_MAP` as contract-owned
- **Files**: `src/specify_cli/status/emit.py` (verify/update)
- **Parallel?**: No — depends on reading the canonical implementation

### Subtask T028 – Verify contract doc matches implementation

- **Purpose**: Ensure `contracts/lane-mapping.md` remains accurate.
- **Steps**:
  1. Read `_SYNC_LANE_MAP` from `status/emit.py`
  2. Read `kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md`
  3. Compare all 7 entries + alias note (`doing` → `in_progress`)
  4. Update contract doc if drift exists
  5. If implementation is wrong, fix code and doc together
- **Files**: `kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md` (verify/update)
- **Parallel?**: No — depends on T025-T027 context

## Test Strategy

- **New tests**: ~8 test cases (7 mapping assertions + invalid lane transition)
- **Run command**: `python -m pytest tests/specify_cli/status/test_sync_lane_mapping.py -v`
- **Baseline**: Existing status and sync tests must still pass

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Mapping location changes on 2.x | Treat `status/emit.py` as source of truth and verify before edits |
| Transition fixture setup is brittle | Reuse existing status test fixtures from `tests/specify_cli/status/` |
| Contract doc stale from prior assumptions | T028 explicitly reconciles with `_SYNC_LANE_MAP` |

## Review Guidance

- Verify all 7 lanes are tested with correct outputs
- Verify invalid lane transitions raise `TransitionError`
- Verify mapping remains centralized in `status/emit.py`
- Verify contract doc matches implementation
- Run `python -m pytest tests/specify_cli/status/test_sync_lane_mapping.py -v` — tests green

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.
