---
work_package_id: WP06
title: 'Migrate Slice 4: Merge Validation & Recovery'
dependencies:
- WP01
requirement_refs:
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
history: []
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/lanes/recovery.py
- tests/specify_cli/cli/commands/test_merge.py
- tests/specify_cli/lanes/test_recovery.py
tags: []
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "67703"
---

# WP06: Migrate Slice 4 — Merge Validation & Recovery

**Objective**: Migrate two consumers in Slice 4:
- **Part A**: `cli/commands/merge.py` — Preserve explicit Lane.DONE|Lane.APPROVED check (NOT delegated to `is_terminal`); use typed Lane enum
- **Part B**: `lanes/recovery.py` — Replace hardcoded transition tuples with `validate_transition()` from status module

---

## Context

**Part A (merge.py)** — CRITICAL CONSTRAINT:
Currently checks merge-ready state with raw strings:
```python
lane_str = str(get_wp_lane(feature_dir, wp_id))
if lane_str not in ("done", "approved"):
    incomplete.append(f"{wp_id}={lane_str}")
```

By design, merge-ready is **explicit** approved|done, NOT delegated to `is_terminal` (which is cleanup logic: done/canceled only). We must preserve this distinction to avoid conflating business logic with cleanup logic.

**Part B (recovery.py)**:
Currently uses hardcoded transition tuples:
```python
_RECOVERY_TRANSITIONS = {
    Lane.PLANNED: [Lane.CLAIMED, Lane.IN_PROGRESS],
    Lane.CLAIMED: [Lane.IN_PROGRESS],
}

if current_lane not in _RECOVERY_TRANSITIONS:
    raise RecoveryError(f"Cannot recover from {current_lane}")
```

By using `validate_transition()` from the status module, we centralize transition rules.

---

## Detailed Guidance

### T015: Migrate cli/commands/merge.py — Preserve approved|done Check

**Purpose**: Update merge validation to use typed Lane enum while preserving the explicit approved|done distinction.

**Steps**:
1. Locate `src/specify_cli/cli/commands/merge.py`.
2. Find the merge validation logic that checks `lane_str not in ("done", "approved")`.
3. Replace with:
   ```python
   from specify_cli.status.models import Lane
   from specify_cli.status.lane_reader import get_wp_lane
   
   lane = Lane(str(get_wp_lane(feature_dir, wp_id)))
   
   # CRITICAL: Explicit approved|done check, NOT delegated to is_terminal
   if lane not in (Lane.DONE, Lane.APPROVED):
       incomplete.append(f"{wp_id}={lane.value}")
   ```
4. **IMPORTANT**: Do NOT use `state.is_terminal` for this check. That property is for cleanup logic (done/canceled), not merge readiness.
5. Verify the merge validation logic is unchanged (same WPs are marked incomplete).
6. Remove any raw string comparisons like `== "done"` or `== "approved"`.

**Validation**: Typed Lane enum used, approved|done distinction preserved explicitly, merge logic unchanged.

---

### T016: Migrate lanes/recovery.py to Use validate_transition()

**Purpose**: Replace hardcoded transition tuples with centralized transition validation.

**Steps**:
1. Locate `src/specify_cli/lanes/recovery.py`.
2. Find the hardcoded `_RECOVERY_TRANSITIONS` dictionary (or similar).
3. Find all places where it's used:
   ```python
   if current_lane not in _RECOVERY_TRANSITIONS:
       raise RecoveryError(f"Cannot recover from {current_lane}")
   if target_lane not in _RECOVERY_TRANSITIONS[current_lane]:
       raise RecoveryError(f"Cannot transition {current_lane} → {target_lane}")
   ```
4. Replace with:
   ```python
   from specify_cli.status.transitions import validate_transition
   
   if not validate_transition(current_lane, target_lane):
       raise RecoveryError(f"Invalid: {current_lane} → {target_lane}")
   ```
5. Remove the `_RECOVERY_TRANSITIONS` dictionary entirely.
6. Verify recovery transitions are unchanged (same valid paths allowed, same paths blocked).

**Validation**: Hardcoded tuples removed, `validate_transition()` used, recovery transitions unchanged.

---

### T017: Write Integration Tests for Merge & Recovery

**Purpose**: Verify both consumers work correctly with typed Lane enum and transition validation.

**Steps**:
1. Locate or create `tests/specify_cli/cli/commands/test_merge.py` and `tests/specify_cli/lanes/test_recovery.py`.
2. For **merge**, write test verifying approved|done check:
   ```python
   def test_merge_ready_check_preserved():
       """Verify approved|done check is explicit and preserved."""
       from specify_cli.status.models import Lane
       
       ready_lanes = (Lane.DONE, Lane.APPROVED)
       
       test_cases = [
           ("done", True),
           ("approved", True),
           ("in_progress", False),
           ("for_review", False),
           ("claimed", False),
           ("in_review", False),
           ("planned", False),
           ("blocked", False),
           ("canceled", False),
       ]
       for lane_str, should_be_ready in test_cases:
           lane = Lane(lane_str)
           is_ready = lane in ready_lanes
           assert is_ready == should_be_ready, f"Lane {lane_str}"
   ```
3. Write integration test for merge command (if applicable):
   ```bash
   # Test that merge command correctly identifies incomplete WPs
   spec-kitty agent merge --feature 080-feature --dry-run
   ```
4. For **recovery**, write test verifying transitions:
   ```python
   def test_recovery_transitions_preserved():
       """Verify recovery transitions are allowed/blocked correctly."""
       from specify_cli.status.transitions import validate_transition
       from specify_cli.status.models import Lane
       
       # Allowed transitions
       assert validate_transition(Lane.PLANNED, Lane.CLAIMED) == True
       assert validate_transition(Lane.PLANNED, Lane.IN_PROGRESS) == True
       assert validate_transition(Lane.CLAIMED, Lane.IN_PROGRESS) == True
       
       # Not allowed (in recovery mode)
       assert validate_transition(Lane.PLANNED, Lane.DONE) == False
       assert validate_transition(Lane.CLAIMED, Lane.APPROVED) == False
   ```
5. Run both test suites and verify all pass.
6. Verify no regressions in existing merge and recovery tests.

**Validation**: Merge ready check passes, recovery transitions pass, logic unchanged.

---

## Integration Points

- **Depends on**: WP01 (Lane enum available)
- **Does not depend on**: WP02, WP03, WP04, WP05 (can run in parallel after WP01 completes)
- **Blocks**: WP07 verification step (final grep pass)

---

## Test Strategy

**Scope**: Regression + integration tests.

**Coverage Target**: 100% of modified logic in both files.

**Test Cases**:
- merge.py: approved|done check for all 9 lanes
- recovery.py: Allowed and blocked transitions (recovery ceiling at IN_PROGRESS)
- CLI integration: Merge command end-to-end (if applicable)

---

## Definition of Done

- [ ] Manual lane string check removed from merge.py
- [ ] Typed Lane enum used; approved|done distinction preserved explicitly
- [ ] `is_terminal` NOT used for merge validation (correct semantic)
- [ ] Hardcoded `_RECOVERY_TRANSITIONS` tuple removed from recovery.py
- [ ] `validate_transition()` used instead; recovery transitions unchanged
- [ ] Merge ready check test passes (approved|done detection correct)
- [ ] Recovery transition test passes (allowed paths work, blocked paths fail)
- [ ] Integration tests pass (merge and recovery CLI commands work)
- [ ] All existing tests pass
- [ ] mypy --strict passes on both modified files
- [ ] No performance regression

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Merge validation regression (approved/done handling) | Explicit Lane enum check; NOT delegated to is_terminal; careful testing all 9 lanes |
| Recovery transition regression (wrong paths allowed) | Test both allowed and blocked transitions; verify ceiling at IN_PROGRESS |
| is_terminal/approved conflation | Documented constraint: is_terminal for cleanup logic only; merge uses explicit check |
| Backward compat break | These consumers' APIs unchanged; only internal logic changed |

---

## Reviewer Guidance

- **CRITICAL**: Verify `is_terminal` is NOT used for merge validation (preserve explicit approved|done check)
- Verify all raw lane string checks removed from merge.py
- Check that typed Lane enum is used for merge ready check
- Confirm hardcoded transition tuples removed from recovery.py
- Check that `validate_transition()` is called correctly
- Verify tests cover all 9 lanes for merge validation
- Verify tests cover both allowed and blocked transitions for recovery
- Confirm merge and recovery CLI commands work end-to-end
- Double-check that merge-ready (approved|done) is distinct from is_terminal (done|canceled)

---

## Change Log

- **2026-04-09**: Initial WP for 080-wpstate-lane-consumer-strangler-fig-phase-2

## Activity Log

- 2026-04-09T15:48:40Z – claude:sonnet:implementer:implementer – shell_pid=84574 – Started implementation via action command
- 2026-04-09T16:05:02Z – claude:sonnet:implementer:implementer – shell_pid=84574 – Ready for review: T015 typed Lane enum in merge.py (approved|done check preserved, not delegated to is_terminal); T016 _RECOVERY_TRANSITIONS removed, validate_transition() used; T017 38 tests pass covering all 9 lanes and recovery transition paths
- 2026-04-09T16:05:12Z – claude:sonnet:reviewer:reviewer – shell_pid=9668 – Started review via action command
- 2026-04-09T16:06:29Z – claude:sonnet:reviewer:reviewer – shell_pid=9668 – Review passed: T015 typed Lane enum in merge.py (approved|done explicit, not delegated to is_terminal); T016 _RECOVERY_TRANSITIONS removed and replaced with validate_transition()-based helpers; T017 38/38 tests pass covering all 9 lanes and recovery transitions
- 2026-04-09T17:17:50Z – claude:sonnet:implementer:implementer – shell_pid=40361 – Started implementation via action command
- 2026-04-09T17:31:28Z – claude:sonnet:implementer:implementer – shell_pid=40361 – T015 typed Lane enum in merge.py (approved|done check preserved explicit, NOT delegated to is_terminal); T016 _RECOVERY_TRANSITIONS removed, replaced with _get_recovery_transitions() delegating to validate_transition(); T017 28 tests pass covering all 9 lanes and all recovery transition paths
- 2026-04-09T17:31:49Z – claude:sonnet:reviewer:reviewer – shell_pid=67703 – Started review via action command
- 2026-04-09T17:33:21Z – claude:sonnet:reviewer:reviewer – shell_pid=67703 – Review passed: merge.py and recovery.py fully migrated, live function tests, zero raw strings. _RECOVERY_TRANSITIONS gone, replaced by _get_recovery_transitions(). merge.py uses explicit Lane.DONE|Lane.APPROVED check (NOT is_terminal). 28/28 tests pass.
