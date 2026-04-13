---
work_package_id: WP03
title: Update tests for final contract state
dependencies:
- WP01
- WP02
requirement_refs:
- FR-005
- FR-006
- FR-007
planning_base_branch: main
merge_target_branch: main
branch_strategy: Lane-based worktree allocated by finalize-tasks. Branch from planning_base_branch, merge into merge_target_branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
history:
- at: '2026-04-13T04:59:36Z'
  by: spec-kitty.tasks
  note: WP created during task generation
authoritative_surface: tests/
execution_mode: code_change
owned_files:
- tests/status/test_event_mission_id.py
- tests/contract/test_identity_contract_matrix.py
tags: []
---

# WP03: Update tests for final contract state

## Objective

Update test assertions to reflect the removed `legacy_aggregate_id` shim. Flip tests that asserted field presence to assert field absence. Update the identity contract matrix. Verify legacy event read tolerance is preserved (C-002).

## Context

After WP01 and WP02, `legacy_aggregate_id` is no longer emitted in status events and the emitter methods require `mission_id`. Tests must now reflect this final state:
- Tests asserting `legacy_aggregate_id` **is present** must flip to assert it **is absent**
- Tests asserting drift-window backward compatibility must be updated to reflect the drift window is closed
- Tests for legacy event deserialization (events without `mission_id`) must remain unchanged — they verify C-002

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Implementation

### Subtask T012: Flip T025 assertion — legacy_aggregate_id presence → absence

**File**: `tests/status/test_event_mission_id.py`

**Current test** (around line 317):
```python
def test_to_dict_includes_legacy_aggregate_id_when_mission_id_present(self) -> None:
    """T025: legacy_aggregate_id must equal mission_slug for new events."""
    event = StatusEvent(...)
    d = event.to_dict()
    assert d["legacy_aggregate_id"] == _MISSION_SLUG
```

**Changes**:
1. Rename method to `test_to_dict_omits_legacy_aggregate_id_after_drift_window_closure`
2. Update docstring to reflect the new contract
3. Change assertion:
   ```python
   assert "legacy_aggregate_id" not in d
   ```
4. Verify `mission_id` is still present in the dict

### Subtask T013: Remove legacy_aggregate_id from Fixture 2 data

**File**: `tests/status/test_event_mission_id.py`

**Current fixture data** (around line 68):
```python
"legacy_aggregate_id": _MISSION_SLUG,
```

**Changes**:
1. Remove the `"legacy_aggregate_id": _MISSION_SLUG` entry from the new-format fixture dict
2. Verify the fixture still includes `"mission_id": _MISSION_ID` and `"mission_slug": _MISSION_SLUG`
3. Check if any test in `TestNewFormatEventRead` class (line 170) depends on this field in the fixture — if so, update those tests

### Subtask T014: Flip T028 assertion — emitted event legacy_aggregate_id → assert absent

**File**: `tests/status/test_event_mission_id.py`

**Current test** (around line 414):
```python
def test_emitted_event_legacy_aggregate_id_equals_mission_slug(
    self, feature_dir_with_meta: Path
) -> None:
    """T028: on-disk event must carry legacy_aggregate_id == meta.json.mission_slug."""
    ...
    raw_event = claimed_raw[-1]
    assert raw_event.get("legacy_aggregate_id") == _MISSION_SLUG
```

**Changes**:
1. Rename to `test_emitted_event_omits_legacy_aggregate_id`
2. Update docstring: "On-disk event must not carry legacy_aggregate_id after drift-window closure."
3. Change assertion:
   ```python
   assert "legacy_aggregate_id" not in raw_event
   ```
4. Keep the rest of the test intact (it still validates that events are written to disk correctly)

### Subtask T015: Verify legacy event read-tolerance test unchanged (C-002)

**File**: `tests/status/test_event_mission_id.py`

**Current test** (around line 334):
```python
def test_to_dict_omits_legacy_aggregate_id_for_legacy_events(self) -> None:
    """Events without mission_id must not carry legacy_aggregate_id."""
    event = StatusEvent(... mission_id=None ...)
    d = event.to_dict()
    assert "mission_id" not in d
    assert "legacy_aggregate_id" not in d
```

**Action**: This test should still pass as-is. **Do not modify it.** Verify it passes after WP01/WP02 changes. If it breaks, investigate why — it should not break since it tests events with `mission_id=None`.

Also verify the `TestLegacyEventLogRead` class (Fixture 1) tests still pass — these test deserialization of events that lack `mission_id` entirely.

### Subtask T016: Update contract matrix identity_locations

**File**: `tests/contract/test_identity_contract_matrix.py`

**Current entry** (around line 190):
```python
ContractSurface(
    name="wp_status_event",
    builder=_build_wp_status_event,
    identity_locations=("mission_id", "mission_slug", "legacy_aggregate_id"),
    ulid_equals=("mission_id",),
),
```

**Changes**:
1. Remove `"legacy_aggregate_id"` from the `identity_locations` tuple:
   ```python
   identity_locations=("mission_id", "mission_slug"),
   ```
2. Check if `_build_wp_status_event` produces events with `legacy_aggregate_id` — if so, verify it no longer does after WP01 changes

Also update the assertion around line 281:
```python
assert "legacy_aggregate_id" not in payload, (
    "legacy_aggregate_id is only emitted when mission_id is present"
)
```
This assertion now becomes universally true (never emitted), so update the message to reflect the drift window is closed.

### Subtask T017: Update drift-window backward-compat test

**File**: `tests/contract/test_identity_contract_matrix.py`

**Current test** (around line 406):
```python
def test_...(self) -> None:
    """Backward-compat: omitting mission_id must leave aggregate_id = slug.

    This protects the drift window where some call sites may still pass
    ``mission_id=None`` before they are updated.  The emitter must never
    synthesise a false ULID.
    """
```

**Changes**:
1. This test was protecting the drift window that is now closed. Since `mission_id` is now mandatory on the emitter, the scenario "omitting mission_id" is no longer possible at the type level.
2. **Remove or replace this test**:
   - If the test calls the emitter without `mission_id`, it will now fail to compile (TypeError). Remove it.
   - Replace with a test that verifies `mission_id` is mandatory: calling without it raises `TypeError`.
3. Update the class/module docstring if it references the drift window.

## Definition of Done

- [ ] T025 assertion flipped to assert `legacy_aggregate_id` absence
- [ ] Fixture 2 no longer contains `legacy_aggregate_id`
- [ ] T028 assertion flipped to assert absence on disk
- [ ] Legacy event read-tolerance tests pass unchanged
- [ ] Contract matrix `identity_locations` excludes `legacy_aggregate_id`
- [ ] Drift-window backward-compat test updated or replaced
- [ ] Full test suite passes: `pytest tests/status/test_event_mission_id.py tests/contract/test_identity_contract_matrix.py`
- [ ] No test references `legacy_aggregate_id` as expected present (only as expected absent)

## Risks

- **Low**: Test changes are mechanical — flipping assertions and removing a field from fixtures.
- **T017 complexity**: The drift-window backward-compat test may have interdependencies with other tests in the same class. Read the full test class before removing/replacing.

## Reviewer Guidance

- Verify that legacy event tests (events without `mission_id`) still pass — these are C-002 compliance
- Verify no test still asserts `legacy_aggregate_id` is *present* in any output
- Check that test fixtures for new-format events have been cleaned of the removed field
- Confirm the contract matrix reflects the final wire format: `mission_id` + `mission_slug` only
