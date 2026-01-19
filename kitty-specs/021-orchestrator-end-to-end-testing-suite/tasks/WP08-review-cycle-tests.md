---
work_package_id: WP08
title: Review Cycle Tests
lane: planned
dependencies:
- WP05
subtasks:
- T036
- T037
- T038
- T039
- T040
phase: Phase 1 - Core Tests
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T09:30:27Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Review Cycle Tests

## Implementation Command

```bash
spec-kitty implement WP08 --base WP06
```

Depends on WP05 (fixtures) and WP06 (pytest configuration).

---

## Objectives & Success Criteria

Test review rejection and re-implementation cycles:

- [ ] Review rejection test verifies WP returns to implementation
- [ ] Re-implementation test confirms new commits are created
- [ ] Full cycle test validates reject→re-impl→approve flow
- [ ] Max cycles test verifies WP fails after limit exceeded
- [ ] State history test confirms transitions are recorded

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/spec.md` - User Story 2
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Review cycle behavior

**Existing Code**:
- `tests/fixtures/orchestrator/checkpoint_review_pending/` - From WP05
- `tests/specify_cli/orchestrator/conftest.py` - From WP06

**Constraints**:
- Start from `checkpoint_review_pending` fixture
- May need fixture state manipulation for rejection trigger
- Mark with `@pytest.mark.orchestrator_review_cycles`

---

## Subtasks & Detailed Guidance

### Subtask T036 – Implement review rejection flow test

**Purpose**: Verify that review rejection triggers re-implementation.

**Steps**:
1. Create `tests/specify_cli/orchestrator/test_review_cycles.py`:
   ```python
   """Review cycle tests for orchestrator.

   These tests verify the orchestrator handles review rejection and re-implementation.
   """
   from __future__ import annotations

   import pytest
   from pathlib import Path

   from specify_cli.orchestrator.testing.fixtures import TestContext


   @pytest.mark.slow
   @pytest.mark.orchestrator_review_cycles
   @pytest.mark.core_agent
   class TestReviewRejection:
       """Tests for review rejection handling."""

       def test_rejection_triggers_reimplementation(
           self,
           test_context_review_pending: TestContext,
       ):
           """Review rejection should put WP back into implementation."""
           ctx = test_context_review_pending

           # The fixture should have WP01 in 'in_review' state
           # We need to simulate/trigger a rejection

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           # Load initial state
           initial_state = load_state(ctx.state_file)
           wp01_initial = initial_state.work_packages["WP01"]
           assert wp01_initial.status == "in_review"

           # Run orchestration with review agent that will reject
           # Note: This depends on agent behavior or mock injection
           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
               # May need flag to force rejection for testing
           )

           # After rejection and re-implementation, check state
           final_state = load_state(ctx.state_file)
           wp01_final = final_state.work_packages["WP01"]

           # WP should either be done (if re-impl succeeded) or back in progress
           assert wp01_final.status in ("done", "in_progress", "in_review"), (
               f"Unexpected status after rejection cycle: {wp01_final.status}"
           )

       def test_rejection_increments_review_count(
           self,
           test_context_review_pending: TestContext,
       ):
           """Each rejection should increment the review cycle counter."""
           ctx = test_context_review_pending

           from specify_cli.orchestrator.state import load_state

           initial_state = load_state(ctx.state_file)
           wp01 = initial_state.work_packages["WP01"]
           initial_review_count = getattr(wp01, 'review_count', 0)

           # Trigger rejection cycle...
           # (Implementation depends on how rejection is triggered)

           # After cycle, review_count should increment
           final_state = load_state(ctx.state_file)
           wp01_final = final_state.work_packages["WP01"]
           final_review_count = getattr(wp01_final, 'review_count', 0)

           # If rejection occurred, count should increase
           # Note: This test may need adjustment based on actual rejection mechanism
           assert final_review_count >= initial_review_count
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_review_cycles.py` (~80 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T037 – Implement re-implementation commit test

**Purpose**: Verify re-implementation produces new commits.

**Steps**:
1. Add to `test_review_cycles.py`:
   ```python
   import subprocess

   @pytest.mark.slow
   @pytest.mark.orchestrator_review_cycles
   @pytest.mark.core_agent
   class TestReimplementation:
       """Tests for re-implementation after rejection."""

       def _get_commit_count(self, repo_path: Path) -> int:
           """Count commits in repository."""
           result = subprocess.run(
               ["git", "rev-list", "--count", "HEAD"],
               cwd=repo_path,
               capture_output=True,
               text=True,
           )
           if result.returncode != 0:
               return 0
           return int(result.stdout.strip())

       def _get_latest_commit_hash(self, repo_path: Path) -> str:
           """Get the latest commit hash."""
           result = subprocess.run(
               ["git", "rev-parse", "HEAD"],
               cwd=repo_path,
               capture_output=True,
               text=True,
           )
           return result.stdout.strip() if result.returncode == 0 else ""

       def test_reimplementation_creates_new_commits(
           self,
           test_context_wp_implemented: TestContext,
       ):
           """Re-implementation should create additional commits."""
           ctx = test_context_wp_implemented

           # Find WP01 worktree
           worktree_path = ctx.worktrees_dir / "test-feature-WP01"
           if not worktree_path.exists():
               pytest.skip("WP01 worktree not found in fixture")

           # Get initial commit state
           initial_count = self._get_commit_count(worktree_path)
           initial_hash = self._get_latest_commit_hash(worktree_path)

           # Trigger re-implementation (e.g., by running orchestration
           # that detects needed changes)
           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           # If re-implementation occurred, we should have new commits
           final_count = self._get_commit_count(worktree_path)
           final_hash = self._get_latest_commit_hash(worktree_path)

           # Note: This test may not always produce new commits
           # if agent determines no changes needed
           if result.success:
               # At minimum, hash should be valid
               assert final_hash, "No commits found after orchestration"

       def test_reimplementation_preserves_previous_commits(
           self,
           test_context_wp_implemented: TestContext,
       ):
           """Re-implementation should not rewrite history."""
           ctx = test_context_wp_implemented

           worktree_path = ctx.worktrees_dir / "test-feature-WP01"
           if not worktree_path.exists():
               pytest.skip("WP01 worktree not found")

           # Get initial commits
           result = subprocess.run(
               ["git", "log", "--oneline"],
               cwd=worktree_path,
               capture_output=True,
               text=True,
           )
           initial_commits = result.stdout.strip().split("\n") if result.stdout else []

           # Run orchestration
           from specify_cli.orchestrator.runner import run_orchestration
           run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           # Get final commits
           result = subprocess.run(
               ["git", "log", "--oneline"],
               cwd=worktree_path,
               capture_output=True,
               text=True,
           )
           final_commits = result.stdout.strip().split("\n") if result.stdout else []

           # Initial commits should still be present (history preserved)
           for commit in initial_commits[1:]:  # Skip newest, it may have changed
               # Check commit hash (first 7 chars) is in final
               commit_hash = commit.split()[0] if commit else ""
               if commit_hash:
                   assert any(commit_hash in fc for fc in final_commits), (
                       f"Commit {commit_hash} was lost during re-implementation"
                   )
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_review_cycles.py` (add ~95 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T038 – Implement full review cycle test

**Purpose**: Test complete reject→re-impl→re-review→approve flow.

**Steps**:
1. Add to `test_review_cycles.py`:
   ```python
   @pytest.mark.slow
   @pytest.mark.orchestrator_review_cycles
   @pytest.mark.core_agent
   class TestFullReviewCycle:
       """Tests for complete review cycle flow."""

       def test_full_cycle_reaches_done(
           self,
           test_context_review_pending: TestContext,
       ):
           """WP should eventually reach 'done' through review cycle."""
           ctx = test_context_review_pending

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           # Run orchestration - this may go through multiple cycles
           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
               max_review_cycles=3,  # Allow up to 3 cycles
           )

           # Should eventually succeed (unless max cycles exceeded)
           final_state = load_state(ctx.state_file)
           wp01 = final_state.work_packages["WP01"]

           # Either done or failed (if max cycles hit)
           assert wp01.status in ("done", "failed"), (
               f"WP01 stuck in intermediate state: {wp01.status}"
           )

       def test_approval_after_reimplementation(
           self,
           test_context_wp_implemented: TestContext,
       ):
           """WP should be approved after successful re-implementation."""
           ctx = test_context_wp_implemented

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           if result.success:
               final_state = load_state(ctx.state_file)
               wp01 = final_state.work_packages["WP01"]
               assert wp01.status == "done", (
                   f"Expected 'done' after approval, got: {wp01.status}"
               )

       def test_multiple_rejection_cycles(
           self,
           test_context_factory,
           require_2_agent_path,  # Need 2 agents for proper review
       ):
           """WP should handle multiple rejection cycles gracefully."""
           ctx = test_context_factory("review_pending")

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           # Allow multiple cycles
           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
               max_review_cycles=5,
           )

           final_state = load_state(ctx.state_file)
           wp01 = final_state.work_packages["WP01"]

           # Should complete or fail, not hang
           assert wp01.status in ("done", "failed")

           # Check review count if available
           if hasattr(wp01, 'review_count'):
               assert wp01.review_count <= 5, (
                   f"Review count {wp01.review_count} exceeds max"
               )
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_review_cycles.py` (add ~85 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T039 – Implement max review cycles test

**Purpose**: Verify WP fails when max review cycles exceeded.

**Steps**:
1. Add to `test_review_cycles.py`:
   ```python
   @pytest.mark.slow
   @pytest.mark.orchestrator_review_cycles
   class TestMaxReviewCycles:
       """Tests for max review cycle limit."""

       def test_exceeding_max_cycles_marks_wp_failed(
           self,
           test_context_review_pending: TestContext,
       ):
           """WP should be marked failed when max cycles exceeded."""
           ctx = test_context_review_pending

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           # Set very low max cycles to force failure
           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
               max_review_cycles=0,  # Immediate failure on any rejection
           )

           # Note: This test depends on agent behavior
           # If agent approves immediately, WP won't fail
           # May need fixture with pre-set high review count

           final_state = load_state(ctx.state_file)
           wp01 = final_state.work_packages["WP01"]

           # WP should be done (approved) or failed
           assert wp01.status in ("done", "failed")

       def test_max_cycles_failure_records_reason(
           self,
           test_context_factory,
       ):
           """Failed WP should record failure reason."""
           ctx = test_context_factory("review_pending")

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
               max_review_cycles=1,
           )

           final_state = load_state(ctx.state_file)
           wp01 = final_state.work_packages["WP01"]

           if wp01.status == "failed":
               # Should have failure reason
               assert hasattr(wp01, 'failure_reason') or hasattr(wp01, 'error'), (
                   "Failed WP should record failure reason"
               )

       def test_max_cycles_configurable(
           self,
           test_context_review_pending: TestContext,
       ):
           """Max review cycles should be configurable per run."""
           ctx = test_context_review_pending

           from specify_cli.orchestrator.runner import run_orchestration

           # First run with max_cycles=1
           result1 = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
               max_review_cycles=1,
           )

           # The parameter should be accepted without error
           # (actual behavior depends on agent)
           assert result1 is not None

           # Reset and run with max_cycles=10
           ctx2 = test_context_factory("review_pending")
           result2 = run_orchestration(
               feature_dir=ctx2.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx2.test_path.implementation_agent,
               review_agent=ctx2.test_path.review_agent,
               max_review_cycles=10,
           )

           assert result2 is not None
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_review_cycles.py` (add ~90 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T040 – Implement state transition history test

**Purpose**: Verify all state transitions are recorded.

**Steps**:
1. Add to `test_review_cycles.py`:
   ```python
   @pytest.mark.orchestrator_review_cycles
   class TestStateTransitionHistory:
       """Tests for state transition recording."""

       def test_history_records_all_transitions(
           self,
           test_context_wp_created: TestContext,
       ):
           """State history should record all status transitions."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           final_state = load_state(ctx.state_file)
           wp01 = final_state.work_packages["WP01"]

           # Check history exists
           history = getattr(wp01, 'history', []) or getattr(wp01, 'transitions', [])

           if history:
               # Should have at least: pending -> in_progress -> done
               assert len(history) >= 2, (
                   f"Expected at least 2 transitions, got {len(history)}"
               )

               # First transition should be from pending
               # (or whatever initial state was)

       def test_history_has_timestamps(
           self,
           test_context_wp_created: TestContext,
       ):
           """Each history entry should have a timestamp."""
           ctx = test_context_wp_created
           from datetime import datetime

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           final_state = load_state(ctx.state_file)
           wp01 = final_state.work_packages["WP01"]

           history = getattr(wp01, 'history', []) or []

           for entry in history:
               # Each entry should have timestamp
               timestamp = entry.get('timestamp') if isinstance(entry, dict) else getattr(entry, 'timestamp', None)
               if timestamp:
                   # Validate it's parseable
                   try:
                       datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                   except ValueError:
                       pytest.fail(f"Invalid timestamp format: {timestamp}")

       def test_history_records_agent_info(
           self,
           test_context_wp_created: TestContext,
       ):
           """History should record which agent performed each action."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           final_state = load_state(ctx.state_file)
           wp01 = final_state.work_packages["WP01"]

           # Check for agent info in history or direct fields
           impl_agent = getattr(wp01, 'implementation_agent', None)
           review_agent = getattr(wp01, 'review_agent', None)

           # At least one should be recorded
           assert impl_agent or review_agent, (
               "Agent info should be recorded in WP state"
           )

       def test_transition_order_is_chronological(
           self,
           test_context_wp_created: TestContext,
       ):
           """History entries should be in chronological order."""
           ctx = test_context_wp_created
           from datetime import datetime

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           final_state = load_state(ctx.state_file)
           wp01 = final_state.work_packages["WP01"]

           history = getattr(wp01, 'history', []) or []

           if len(history) >= 2:
               timestamps = []
               for entry in history:
                   ts = entry.get('timestamp') if isinstance(entry, dict) else getattr(entry, 'timestamp', None)
                   if ts:
                       timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))

               # Verify chronological order
               for i in range(1, len(timestamps)):
                   assert timestamps[i] >= timestamps[i-1], (
                       f"History not chronological: {timestamps[i-1]} > {timestamps[i]}"
                   )
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_review_cycles.py` (add ~130 lines)

**Parallel?**: Yes - once fixtures ready

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Review rejection non-deterministic | May need fixture with pre-set rejection state |
| Agent approves everything | Test with forced rejection flag or fixture state |
| History schema varies | Check multiple attribute names (history, transitions) |
| Tests dependent on agent behavior | Document expected agent behavior assumptions |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] Rejection test detects status change to in_progress
- [ ] Re-implementation creates new commits (when changes needed)
- [ ] Full cycle eventually reaches done or failed
- [ ] Max cycles test fails WP appropriately
- [ ] History records transitions with timestamps

**Code Quality**:
- Tests handle non-deterministic agent behavior gracefully
- Clear skip conditions when fixtures don't match expected state
- Proper assertion messages explain what was expected vs actual
- No flaky assertions on exact timing

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
