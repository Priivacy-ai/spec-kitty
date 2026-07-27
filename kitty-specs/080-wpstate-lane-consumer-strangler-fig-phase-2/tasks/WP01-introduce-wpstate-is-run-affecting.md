---
work_package_id: WP01
title: Introduce WPState.is_run_affecting Property
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-080-wpstate-lane-consumer-strangler-fig-phase-2
base_commit: 1b4791729e95667bfd3898d72198b42dc4fe0a90
created_at: '2026-04-09T16:40:45.349722+00:00'
subtasks:
- T001
- T002
- T003
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "70208"
history: []
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
owned_files:
- src/specify_cli/status/wp_state.py
- tests/specify_cli/status/test_wp_state.py
tags: []
---

# WP01: Introduce WPState.is_run_affecting Property

**Objective**: Add `is_run_affecting` as a typed property on `WPState`, encapsulating the query "is this WP currently affecting execution?" This foundation enables all downstream consumer migrations to replace ad-hoc lane tuple checks with a single, authoritative interface.

---

## Context

Currently, consumers scattered across the codebase manually check WP lane state using hardcoded tuples like:
```python
RUN_AFFECTING_LANES = (Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.APPROVED)
if lane in RUN_AFFECTING_LANES:
    # route to implementation
```

This duplicates lane logic and makes it harder to evolve lane semantics. By centralizing the check in `WPState.is_run_affecting`, we establish a single point of truth.

**Design Decision**: `is_run_affecting` returns `True` for all "active" lanes (planned through approved); `False` for terminal and blocked lanes. It answers the question: "Does this WP contribute to the current execution run?"

---

## Detailed Guidance

### T001: Add `is_run_affecting` Property to `src/specify_cli/status/wp_state.py`

**Purpose**: Implement the property with full docstring and examples.

**Steps**:
1. Locate `src/specify_cli/status/wp_state.py` and find the `WPState` class definition.
2. Add a new `@property` method `is_run_affecting(self) -> bool`:
   - Returns `True` if `self.lane` is in {PLANNED, CLAIMED, IN_PROGRESS, FOR_REVIEW, IN_REVIEW, APPROVED}
   - Returns `False` if `self.lane` is in {DONE, BLOCKED, CANCELED}
3. Include comprehensive docstring:
   ```python
   @property
   def is_run_affecting(self) -> bool:
       """Return True if WP affects execution progress.
       
       A WP is "run-affecting" if it is active (planned through approved).
       Does not include terminal or blocked lanes.
       
       Returns:
           True if lane in {planned, claimed, in_progress, for_review, in_review, approved}
           False if lane in {done, blocked, canceled}
       
       Usage:
           if state.is_run_affecting:
               # Route to implementation or review
       """
       return self.lane in {
           Lane.PLANNED,
           Lane.CLAIMED,
           Lane.IN_PROGRESS,
           Lane.FOR_REVIEW,
           Lane.IN_REVIEW,
           Lane.APPROVED,
       }
   ```
4. Verify the implementation compiles and passes linting.

**Validation**: Property is accessible, type hint is correct, docstring is clear and includes usage example.

---

### T002: Write Behavior Tests for All 9 Lanes

**Purpose**: Verify `is_run_affecting` returns the correct value for all possible lane states.

**Steps**:
1. Create or locate `tests/specify_cli/status/test_wp_state.py` (or add tests to existing file if it exists).
2. Write a test function `test_is_run_affecting_all_lanes()` that verifies:
   - `wp_state_for({"lane": "planned"}).is_run_affecting == True`
   - `wp_state_for({"lane": "claimed"}).is_run_affecting == True`
   - `wp_state_for({"lane": "in_progress"}).is_run_affecting == True`
   - `wp_state_for({"lane": "for_review"}).is_run_affecting == True`
   - `wp_state_for({"lane": "in_review"}).is_run_affecting == True`
   - `wp_state_for({"lane": "approved"}).is_run_affecting == True`
   - `wp_state_for({"lane": "done"}).is_run_affecting == False`
   - `wp_state_for({"lane": "blocked"}).is_run_affecting == False`
   - `wp_state_for({"lane": "canceled"}).is_run_affecting == False`
3. Use `pytest.mark.parametrize()` for conciseness:
   ```python
   @pytest.mark.parametrize("lane,expected", [
       ("planned", True), ("claimed", True), ("in_progress", True),
       ("for_review", True), ("in_review", True), ("approved", True),
       ("done", False), ("blocked", False), ("canceled", False),
   ])
   def test_is_run_affecting(lane, expected):
       state = wp_state_for({"lane": lane})
       assert state.is_run_affecting == expected
   ```
4. Run tests locally and verify all pass.

**Validation**: All 9 lanes tested, parametrize used for clarity, tests pass.

---

### T003: Verify WPState.is_terminal Already Exists

**Purpose**: Confirm that the current codebase already has `WPState.is_terminal`, so this WP does not introduce redundant logic.

**Steps**:
1. Search `src/specify_cli/status/wp_state.py` for `is_terminal` property definition.
2. If found, verify it returns `True` only for {DONE, CANCELED}:
   ```python
   @property
   def is_terminal(self) -> bool:
       return self.lane in {Lane.DONE, Lane.CANCELED}
   ```
3. Add a comment or docstring clarifying the distinction:
   - `is_run_affecting`: True for active lanes (planned through approved)
   - `is_terminal`: True for cleanup-only lanes (done, canceled)
   - Merge validation uses **explicit** approved|done check, NOT `is_terminal`
4. If `is_terminal` does not exist, raise a **STOP** error and report to the user (this would be a discovery failure, not expected given the spec).

**Validation**: `is_terminal` property confirmed in current tree; docstring clarifies distinction from merge-ready semantics.

---

## Test Strategy

**Scope**: Behavior tests only. No integration or regression tests needed for WP01.

**Coverage Target**: 100% of `is_run_affecting` property.

**Test Cases**:
- All 9 lanes (parametrized test)
- Type check: `isinstance(state.is_run_affecting, bool)`

---

## Definition of Done

- [ ] `is_run_affecting` property added to `WPState` with full docstring
- [ ] All 9 lanes tested (parametrized test case with all lanes)
- [ ] `is_terminal` already exists confirmed (no new logic introduced)
- [ ] mypy --strict passes on `wp_state.py`
- [ ] All new tests pass locally
- [ ] No regressions in existing WPState tests

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| `is_run_affecting` duplicates existing logic | Verify `is_terminal` exists; document distinction clearly |
| Test coverage gaps (missing lane) | Use parametrize for all 9 lanes explicitly; review test output |
| Type safety issue | mypy --strict enforces correct return type |

---

## Reviewer Guidance

- Verify the property returns the correct boolean for all 9 lanes
- Confirm docstring is clear and includes usage example
- Check that the distinction from `is_terminal` is well-documented (for merge validation clarity in WP06)
- Ensure no unintended side effects on existing WPState behavior

---

## Change Log

- **2026-04-09**: Initial WP for 080-wpstate-lane-consumer-strangler-fig-phase-2

## Activity Log

- 2026-04-09T14:22:46Z – claude:haiku:implementer:implementer – shell_pid=35099 – Assigned agent via action command
- 2026-04-09T15:07:22Z – claude:haiku:implementer:implementer – shell_pid=35099 – Ready for review: is_run_affecting property fully implemented with comprehensive test coverage
- 2026-04-09T15:17:04Z – claude:haiku:reviewer:reviewer – shell_pid=17759 – Started review via action command
- 2026-04-09T15:17:29Z – claude:haiku:reviewer:reviewer – shell_pid=17759 – Review passed: is_run_affecting property correctly implements all requirements. Full test coverage (9 lanes parametrized), proper docstring, correct type hints, no regressions.
- 2026-04-09T16:34:59Z – claude:haiku:reviewer:reviewer – shell_pid=21064 – Ready for review: is_run_affecting property implemented with full 9-lane parametrized tests, is_terminal confirmed present
- 2026-04-09T16:35:13Z – claude:sonnet:reviewer:reviewer – shell_pid=37936 – Started review via action command
- 2026-04-09T16:37:11Z – claude:sonnet:reviewer:reviewer – shell_pid=37936 – Review passed: is_run_affecting property correctly implements all 9 lanes (planned/claimed/in_progress/for_review/in_review/approved → True; done/blocked/canceled → False). Parametrized test covers all 9 lanes. is_terminal already exists on WPState base class for both DoneState and CanceledState. Docstring includes usage example and clearly distinguishes from is_terminal. No regressions — all 79 tests in test_wp_state.py pass.
- 2026-04-09T16:47:05Z – claude:sonnet:reviewer:reviewer – shell_pid=52172 – Ready for review: is_run_affecting property added to WPState base class with full docstring and parametrized 9-lane test coverage
- 2026-04-09T16:47:46Z – claude:sonnet:reviewer:reviewer – shell_pid=70208 – Started review via action command
- 2026-04-09T16:49:38Z – claude:sonnet:reviewer:reviewer – shell_pid=70208 – Review passed: is_run_affecting correctly implemented in WPState base class with full docstring. All 9 lanes tested via pytest.mark.parametrize. is_terminal already exists on DoneState and CanceledState (T003 confirmed). Tests are regression-detecting: deleting is_run_affecting causes AttributeError on all 9 parametrized test cases. mypy --strict reports 0 errors in wp_state.py. 80 tests pass.
