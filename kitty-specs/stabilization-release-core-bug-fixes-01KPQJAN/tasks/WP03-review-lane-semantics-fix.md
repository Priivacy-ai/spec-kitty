---
work_package_id: WP03
title: Review Lane Semantics Fix
dependencies:
- WP02
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-012
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-stabilization-release-core-bug-fixes-01KPQJAN
base_commit: aa295eb7d50473be016f6cbddca2976f68ca93b8
created_at: '2026-04-21T09:32:04.439745+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
- T019
shell_pid: "79894"
agent: "claude:sonnet:reviewer:reviewer"
history:
- 2026-04-21T08:41:50Z – planned – stabilization WP03
authoritative_surface: src/specify_cli/cli/commands/agent/workflow.py
execution_mode: code_change
mission_id: 01KPQJAN4P2V4MTHRFGS7VW17M
mission_slug: stabilization-release-core-bug-fixes-01KPQJAN
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/core/execution_context.py
- tests/specify_cli/cli/commands/agent/test_workflow_review*.py
tags: []
---

# WP03 — Review Lane Semantics Fix

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Dependency**: WP02 must be approved before this WP is claimed.
- **Workspace**: Enter with `spec-kitty agent action implement WP03 --agent <name>`.

## Objective

Fix `src/specify_cli/cli/commands/agent/workflow.py` so that a review claim emits a `for_review → in_review` event (using `Lane.IN_REVIEW`) instead of the current illegal `for_review → in_progress`. Remove the `force=True` bypass. Update the `is_review_claimed` detection and the lane-entry guard to accept both the new canonical shape and the legacy shape from historical logs. Ship regression tests for all four behaviors.

**Fixes**: Issue #622  
**Requirements**: FR-009, FR-010, FR-011, FR-012, NFR-001–004

## Context

The review-claim code path in `src/specify_cli/cli/commands/agent/workflow.py` emits:

```python
emit_status_transition(TransitionRequest(
    ...
    to_lane=Lane.IN_PROGRESS,   # BUG: should be Lane.IN_REVIEW
    force=True,                  # BUG: force used to bypass illegal transition check
    review_ref="action-review-claim",
    ...
))
```

The `force=True` was required because `for_review → in_progress` is an **illegal** transition in the 9-lane matrix. The correct lane is `in_review`, and `for_review → in_review` is a legal transition that does not need forcing.

Downstream from the claim, `is_review_claimed` checks for `to_lane == Lane.IN_PROGRESS` with `review_ref == "action-review-claim"` to detect an already-claimed WP. This logic must be updated to recognize the new `IN_REVIEW` shape, while also keeping the old shape for historical log compatibility.

The lane-entry guard checks `current_lane not in {Lane.FOR_REVIEW, Lane.IN_PROGRESS}` to allow entry — `IN_PROGRESS` was included to allow re-entry into an already-claimed WP. After the fix, the allowed set should be `{Lane.FOR_REVIEW, Lane.IN_REVIEW}`, plus a special case for the legacy `IN_PROGRESS + review_ref` shape (for old logs only).

**Important**: Approval and rejection from `in_review` must work. The transition matrix (`src/specify_cli/status/transitions.py`) allows `in_review → approved` and `in_review → in_progress` (rejection — returns WP to implementation). There is **no** `in_review → for_review` transition in the matrix; rejection returns to `in_progress`, not `for_review`. No changes to the transition matrix are needed.

**Second site in `execution_context.py`**: `src/specify_cli/core/execution_context.py` contains a duplicate `_is_review_claimed()` helper (around line 163) and a lane check at line 183 that also hard-codes the legacy `IN_PROGRESS + review_ref` shape. Both must be updated to recognize `IN_REVIEW` alongside the legacy shape. Failing to fix this file would leave the workflow-next command (which uses `execution_context.py`) on the old detection logic while `workflow.py` is on the new one.

---

## Subtask T013 — Change emit to `Lane.IN_REVIEW`, remove `force=True`

**File**: `src/specify_cli/cli/commands/agent/workflow.py`

**Steps**:

1. Find the review-claim `emit_status_transition` call (around line 1418). It currently reads:
   ```python
   emit_status_transition(TransitionRequest(
       feature_dir=feature_dir,
       mission_slug=mission_slug,
       wp_id=normalized_wp_id,
       to_lane=Lane.IN_PROGRESS,
       actor=agent,
       force=True,
       reason="Started review via action command",
       review_ref="action-review-claim",
       workspace_context=f"action-review:{main_repo_root}",
       execution_mode=status_execution_mode,
       repo_root=main_repo_root,
   ))
   ```

2. Change to:
   ```python
   emit_status_transition(TransitionRequest(
       feature_dir=feature_dir,
       mission_slug=mission_slug,
       wp_id=normalized_wp_id,
       to_lane=Lane.IN_REVIEW,   # ← fixed
       actor=agent,
       # force=True removed — for_review → in_review is a legal transition
       reason="Started review via action command",
       review_ref="action-review-claim",
       workspace_context=f"action-review:{main_repo_root}",
       execution_mode=status_execution_mode,
       repo_root=main_repo_root,
   ))
   ```

3. Confirm that `TransitionRequest` does not require `force` as a positional argument. It should be an optional kwarg with a default of `False`.

**Validation**:
- [ ] The emit call uses `Lane.IN_REVIEW`
- [ ] No `force=True` in the review-claim emit
- [ ] `mypy --strict` still passes (no type error from removing `force`)

---

## Subtask T014 — Update `is_review_claimed` to OR new + legacy shapes

**File**: `src/specify_cli/cli/commands/agent/workflow.py`

**Steps**:

1. Find `is_review_claimed` (around line 1344):
   ```python
   is_review_claimed = bool(
       latest_event is not None
       and latest_event.to_lane == Lane.IN_PROGRESS
       and latest_event.review_ref == "action-review-claim"
   )
   ```

2. Update to recognize both the new canonical shape and the legacy shape:
   ```python
   is_review_claimed = bool(
       latest_event is not None
       and (
           # New canonical shape (post-fix)
           latest_event.to_lane == Lane.IN_REVIEW
           or (
               # Legacy shape from event logs written before this fix
               latest_event.to_lane == Lane.IN_PROGRESS
               and latest_event.review_ref == "action-review-claim"
           )
       )
   )
   ```

**Why both shapes**: Any project that ran a review claim before this fix has a `IN_PROGRESS + review_ref=action-review-claim` event in its log. We cannot retroactively change these logs. The OR ensures those projects continue to function correctly after upgrade.

**Validation**:
- [ ] A `latest_event` with `to_lane=IN_REVIEW` → `is_review_claimed` is `True`
- [ ] A `latest_event` with `to_lane=IN_PROGRESS, review_ref="action-review-claim"` → `is_review_claimed` is `True` (legacy compat)
- [ ] A `latest_event` with `to_lane=IN_PROGRESS, review_ref=None` → `is_review_claimed` is `False`
- [ ] `latest_event is None` → `is_review_claimed` is `False`

---

## Subtask T015 — Update lane-entry guard

**File**: `src/specify_cli/cli/commands/agent/workflow.py`

**Steps**:

1. Find the guard around line 1362:
   ```python
   if current_lane not in {Lane.FOR_REVIEW, Lane.IN_PROGRESS}:
       print(f"Error: {normalized_wp_id} is in lane '{current_lane}', not 'for_review'.")
       print("Only work packages in 'for_review' can start workflow review.")
       ...
       raise typer.Exit(1)
   ```

2. The guard previously allowed `IN_PROGRESS` as an entry state because review claims put WPs into `IN_PROGRESS`. After the fix, new review claims will put WPs into `IN_REVIEW`. Legacy-claimed WPs will have `IN_PROGRESS` in the event log.

   The correct entry set is: `{FOR_REVIEW}` for initial claims, `{IN_REVIEW}` for re-entry on new-format claims, and `{IN_PROGRESS}` for re-entry on legacy-format claims. Rather than listing all three, use `is_review_claimed` (already computed above) as the test for re-entry:

   ```python
   if current_lane not in {Lane.FOR_REVIEW, Lane.IN_REVIEW} and not is_review_claimed:
       print(f"Error: {normalized_wp_id} is in lane '{current_lane}', not 'for_review'.")
       print("Only work packages in 'for_review' (or already claimed for review) can start workflow review.")
       ...
       raise typer.Exit(1)
   ```

   This way:
   - `FOR_REVIEW` → allowed (initial claim)
   - `IN_REVIEW` → allowed (re-entry on new-format claims)
   - `IN_PROGRESS + review_ref=action-review-claim` → `is_review_claimed=True` → allowed (legacy re-entry)
   - `IN_PROGRESS` without `review_ref` → `is_review_claimed=False` → blocked with correct error message

3. Also update the error message inside the `current_lane == Lane.IN_PROGRESS and not is_review_claimed` check (around line 1355) to reflect the new canonical lane:
   ```python
   if current_lane == Lane.IN_PROGRESS and not is_review_claimed:
       print(f"Error: {normalized_wp_id} is still being implemented, not claimed for review.")
       print("Only work packages in 'for_review' (or already review-claimed in_review) can start workflow review.")
       ...
       raise typer.Exit(1)
   ```

**Validation**:
- [ ] A WP in `FOR_REVIEW` can be claimed → no gate error
- [ ] A WP in `IN_REVIEW` (already claimed, new format) → re-entry allowed, no gate error
- [ ] A WP in `IN_PROGRESS + review_ref=action-review-claim` (legacy) → re-entry allowed
- [ ] A WP in `IN_PROGRESS` without review_ref → blocked with "still being implemented" message

---

## Subtask T015b — Fix `_is_review_claimed` and lane check in `execution_context.py`

**File**: `src/specify_cli/core/execution_context.py`

This file contains a duplicate of the `is_review_claimed` detection used by the workflow-next path. It must receive the same OR-condition fix as `workflow.py`.

1. Find `_is_review_claimed()` (around line 160):
   ```python
   def _is_review_claimed(_wp_id: str) -> bool:
       for event in reversed(events):
           if getattr(event, "wp_id", None) == _wp_id:
               return bool(event.to_lane == Lane.IN_PROGRESS and event.review_ref == "action-review-claim")
       return False
   ```
   Update to:
   ```python
   def _is_review_claimed(_wp_id: str) -> bool:
       for event in reversed(events):
           if getattr(event, "wp_id", None) == _wp_id:
               return bool(
                   event.to_lane == Lane.IN_REVIEW
                   or (
                       event.to_lane == Lane.IN_PROGRESS
                       and event.review_ref == "action-review-claim"
                   )
               )
       return False
   ```

2. Find the lane check at line 183:
   ```python
   if lane == Lane.IN_PROGRESS and _is_review_claimed(candidate_wp_id):
       return candidate_wp_id
   ```
   Update to accept both `IN_PROGRESS` (legacy) and `IN_REVIEW` (new):
   ```python
   if lane in (Lane.IN_PROGRESS, Lane.IN_REVIEW) and _is_review_claimed(candidate_wp_id):
       return candidate_wp_id
   ```

**Validation**:
- [ ] After fix, a WP in `IN_REVIEW` is correctly returned as the "review-claimed" WP by the execution context scan
- [ ] Legacy `IN_PROGRESS + review_ref=action-review-claim` WPs are still returned correctly

---

## Subtask T016 — Regression test: new claim emits `in_review`

**File**: `tests/specify_cli/cli/commands/agent/test_workflow_review.py` (create if absent; check nearby test files for test infrastructure patterns)

**Test to write**:

```python
def test_review_claim_emits_in_review_transition(tmp_path, ...):
    """A review claim must emit for_review -> in_review, not for_review -> in_progress."""
    # Setup: feature with a WP in for_review
    # Run: trigger the review-claim path (call the relevant function or mock the CLI invocation)
    # Assert: the last event in status.events.jsonl has to_lane == "in_review"
    events = read_events(feature_dir)
    claim_event = next(
        (e for e in reversed(events) if e.review_ref == "action-review-claim"),
        None
    )
    assert claim_event is not None
    assert claim_event.to_lane == Lane.IN_REVIEW
    assert claim_event.to_lane != Lane.IN_PROGRESS
```

**Validation**:
- [ ] Test passes with the fix applied
- [ ] Test would fail without the fix (verify by temporarily reverting T013 and running the test)

---

## Subtask T017 — Regression test: approval from `in_review` succeeds

**File**: `tests/specify_cli/cli/commands/agent/test_workflow_review.py`

**Test to write**:

```python
def test_approval_from_in_review_succeeds(tmp_path, ...):
    """A WP in in_review can be approved successfully."""
    # Setup: feature with a WP that has been review-claimed (now in in_review)
    # Run: trigger the approval path
    # Assert: WP moves to 'approved'
    events = read_events(feature_dir)
    latest = events[-1]
    assert latest.to_lane == Lane.APPROVED
    assert latest.from_lane == Lane.IN_REVIEW
```

**Validation**:
- [ ] Test passes
- [ ] Confirm the transition `in_review → approved` is in the allowed transitions matrix

---

## Subtask T018 — Regression test: rejection from `in_review` succeeds

**File**: `tests/specify_cli/cli/commands/agent/test_workflow_review.py`

**Rejection semantics**: The transition matrix (`src/specify_cli/status/transitions.py`) allows `in_review → in_progress` as the rejection/return path. There is **no** `in_review → for_review` transition. Rejection returns the WP to `in_progress` so the implementer can make corrections before re-submitting for review.

**Test to write**:

```python
def test_rejection_from_in_review_returns_to_in_progress(tmp_path, ...):
    """A WP in in_review can be rejected, returning it to in_progress."""
    # Setup: feature with a WP in in_review
    # Run: trigger the rejection/return path
    # Assert: WP moves back to in_progress
    events = read_events(feature_dir)
    latest = events[-1]
    assert latest.to_lane == Lane.IN_PROGRESS
    assert latest.from_lane == Lane.IN_REVIEW
```

**Validation**:
- [ ] Test passes
- [ ] Confirm `in_review → in_progress` is in the allowed transitions matrix (it is — line ~49 in transitions.py)

---

## Subtask T019 — Regression test: historical logs parse without error

**File**: `tests/specify_cli/cli/commands/agent/test_workflow_review.py` or `tests/specify_cli/status/test_legacy_review_claim.py`

**Test to write**:

```python
def test_legacy_in_progress_review_claim_is_readable(tmp_path, ...):
    """
    Event logs written before this fix contain in_progress + review_ref=action-review-claim.
    These must parse without error and is_review_claimed must return True for them.
    """
    # Build a synthetic event log with the legacy shape:
    legacy_event_json = (
        '{"actor":"claude","at":"2026-01-01T00:00:00+00:00",'
        '"event_id":"01ABC","evidence":null,"execution_mode":"worktree",'
        '"feature_slug":"test-feature","force":true,'
        '"from_lane":"for_review","reason":"Started review via action command",'
        '"review_ref":"action-review-claim","to_lane":"in_progress","wp_id":"WP01"}'
    )
    # Write to a temp status.events.jsonl
    events_path = tmp_path / "status.events.jsonl"
    events_path.write_text(legacy_event_json + "\n")

    # Read back
    events = read_events(tmp_path)
    assert len(events) == 1
    assert events[0].to_lane == Lane.IN_PROGRESS
    assert events[0].review_ref == "action-review-claim"

    # is_review_claimed should detect this as a legacy claim
    latest_event = events[-1]
    is_review_claimed = (
        latest_event.to_lane == Lane.IN_REVIEW
        or (
            latest_event.to_lane == Lane.IN_PROGRESS
            and latest_event.review_ref == "action-review-claim"
        )
    )
    assert is_review_claimed is True
```

**Validation**:
- [ ] Test passes: legacy event parses, `is_review_claimed` returns `True`
- [ ] No exception is raised during event reading

---

## Definition of Done

- [ ] `to_lane=Lane.IN_REVIEW` in the review-claim emit in `workflow.py`, `force=True` removed
- [ ] `is_review_claimed` in `workflow.py` recognizes both `IN_REVIEW` (new) and `IN_PROGRESS + review_ref` (legacy)
- [ ] `_is_review_claimed()` in `execution_context.py` updated with the same OR condition
- [ ] Lane check at `execution_context.py:183` accepts `IN_REVIEW` as a review-claimed state
- [ ] Lane-entry guard in `workflow.py` accepts `IN_REVIEW` as a valid entry state
- [ ] `tests/specify_cli/cli/commands/agent/test_workflow_review.py` has ≥4 regression tests (T016–T019)
- [ ] T018 asserts rejection returns to `in_progress`, not `for_review`
- [ ] All new tests pass, no pre-existing tests fail
- [ ] `mypy --strict src/specify_cli/cli/commands/agent/workflow.py src/specify_cli/core/execution_context.py` exits 0
- [ ] FR-009, FR-010, FR-011, FR-012 satisfied (verify spec scenarios S-05, S-06)

## Risks

- **`execution_context.py` scan loop**: Line 183 is inside a loop that also checks `FOR_REVIEW`. Make sure the `IN_REVIEW` check is added correctly and does not accidentally return non-review-claimed WPs.
- **Transition matrix**: `for_review → in_review` is already in `ALLOWED_TRANSITIONS`. Removing `force=True` is safe.
- **No `in_review → for_review`**: The matrix does NOT have this transition. The rejection path is `in_review → in_progress`. Tests must reflect this.

## Reviewer Guidance

1. Confirm `execution_context.py` and `workflow.py` are both updated — a search for `action-review-claim` across the codebase should return no sites where it is checked only against `IN_PROGRESS` without also checking `IN_REVIEW`.
2. Confirm the rejection test (T018) asserts `to_lane == IN_PROGRESS`.
3. Confirm no `force=True` in the review-claim emit.
4. Verify the legacy-compat test (T019) uses a real JSONL event matching the historical format.

## Activity Log

- 2026-04-21T09:32:06Z – claude:sonnet:implementer:implementer – shell_pid=73261 – Assigned agent via action command
- 2026-04-21T09:36:19Z – claude:sonnet:implementer:implementer – shell_pid=73261 – Ready for review: in_review emit, legacy compat, execution_context.py fixed, tests passing
- 2026-04-21T09:36:49Z – claude:sonnet:reviewer:reviewer – shell_pid=79894 – Started review via action command
- 2026-04-21T09:40:32Z – claude:sonnet:reviewer:reviewer – shell_pid=79894 – Review passed: IN_REVIEW emit, no force, both files updated, legacy compat tested
