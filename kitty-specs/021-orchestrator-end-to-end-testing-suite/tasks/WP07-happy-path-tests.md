---
work_package_id: WP07
title: Happy Path Tests
lane: "doing"
dependencies:
- WP05
subtasks:
- T031
- T032
- T033
- T034
- T035
phase: Phase 1 - Core Tests
assignee: ''
agent: "claude-opus"
shell_pid: "37792"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T09:30:27Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Happy Path Tests 🎯 MVP

## Implementation Command

```bash
spec-kitty implement WP07 --base WP06
```

Depends on WP05 (fixtures) and WP06 (pytest configuration).

---

## Objectives & Success Criteria

Implement end-to-end tests for happy path orchestration:

- [ ] Single WP orchestration test passes with correct final state
- [ ] Multiple parallel WPs test validates concurrent execution
- [ ] State validation test confirms OrchestrationRun integrity
- [ ] Lane status consistency test verifies frontmatter matches state
- [ ] Commit verification test confirms git history in worktrees

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/spec.md` - User Story 1
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Test behavior

**Existing Code**:
- `src/specify_cli/orchestrator/` - Orchestrator implementation
- `tests/fixtures/orchestrator/` - Checkpoint fixtures from WP05
- `tests/specify_cli/orchestrator/conftest.py` - pytest fixtures from WP06

**Constraints**:
- Use real agents (no mocks)
- Start from checkpoint fixtures
- Mark with `@pytest.mark.slow` and `@pytest.mark.orchestrator_happy_path`

---

## Subtasks & Detailed Guidance

### Subtask T031 – Implement single WP orchestration test

**Purpose**: Verify basic orchestration flow for a single work package.

**Steps**:
1. Create `tests/specify_cli/orchestrator/test_happy_path.py`:
   ```python
   """Happy path end-to-end tests for orchestrator.

   These tests verify the orchestrator completes successfully under normal conditions.
   """
   from __future__ import annotations

   import pytest
   from pathlib import Path

   from specify_cli.orchestrator.testing.fixtures import TestContext


   @pytest.mark.slow
   @pytest.mark.orchestrator_happy_path
   @pytest.mark.core_agent
   class TestSingleWPOrchestration:
       """Tests for single work package orchestration."""

       def test_single_wp_completes_successfully(
           self,
           test_context_wp_created: TestContext,
       ):
           """A single WP should complete through implement→review→done."""
           ctx = test_context_wp_created

           # Import orchestrator runner
           from specify_cli.orchestrator.runner import run_orchestration

           # Run orchestration for WP01 only
           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           # Assert success
           assert result.success, f"Orchestration failed: {result.error}"

           # Verify final state
           assert result.wps_completed == 1
           assert result.wps_failed == 0

           # Verify WP01 is in 'done' state
           wp_state = result.work_packages.get("WP01")
           assert wp_state is not None
           assert wp_state.status == "done"

       def test_single_wp_creates_worktree(
           self,
           test_context_wp_created: TestContext,
       ):
           """Orchestration should create worktree for WP."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           # Verify worktree was created
           worktree_path = ctx.worktrees_dir / "test-feature-WP01"
           assert worktree_path.exists(), "Worktree should be created"

           # Verify worktree has .git
           assert (worktree_path / ".git").exists()
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_happy_path.py` (~80 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T032 – Implement multiple parallel WPs test

**Purpose**: Verify orchestrator can run independent WPs concurrently.

**Steps**:
1. Add to `test_happy_path.py`:
   ```python
   @pytest.mark.slow
   @pytest.mark.orchestrator_happy_path
   @pytest.mark.core_agent
   class TestParallelWPOrchestration:
       """Tests for parallel work package orchestration."""

       def test_independent_wps_run_in_parallel(
           self,
           test_context_factory,
       ):
           """Independent WPs should start approximately simultaneously."""
           # Need a fixture with multiple independent WPs
           # For this test, we'll use a custom fixture or modify wp_created

           ctx = test_context_factory("wp_created")

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01", "WP02"],  # Both if WP02 is independent
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           # Note: WP02 depends on WP01 in our fixture, so this tests
           # sequential execution. To test true parallelism, need fixture
           # with independent WPs.

           assert result.success
           assert result.wps_completed == 2

       def test_multiple_wps_all_reach_done(
           self,
           test_context_wp_created: TestContext,
       ):
           """All orchestrated WPs should reach 'done' state."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           # All WPs should be done
           for wp_id, wp_state in result.work_packages.items():
               assert wp_state.status == "done", f"{wp_id} not done: {wp_state.status}"
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_happy_path.py` (add ~55 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T033 – Implement state validation test

**Purpose**: Verify OrchestrationRun state file integrity after completion.

**Steps**:
1. Add to `test_happy_path.py`:
   ```python
   import json

   @pytest.mark.orchestrator_happy_path
   class TestStateValidation:
       """Tests for orchestration state file integrity."""

       def test_state_file_written_after_orchestration(
           self,
           test_context_wp_created: TestContext,
       ):
           """State file should be written with valid JSON."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           # Read state file
           state_file = ctx.state_file
           assert state_file.exists(), "State file should exist"

           # Validate JSON
           with open(state_file) as f:
               state_data = json.load(f)

           # Check required fields
           assert "run_id" in state_data
           assert "feature_slug" in state_data
           assert "status" in state_data
           assert "work_packages" in state_data

       def test_state_counts_are_accurate(
           self,
           test_context_wp_created: TestContext,
       ):
           """State counters should match actual WP states."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           # Load state
           with open(ctx.state_file) as f:
               state_data = json.load(f)

           # Count actual done/failed WPs
           actual_done = sum(
               1 for wp in state_data["work_packages"].values()
               if wp["status"] == "done"
           )
           actual_failed = sum(
               1 for wp in state_data["work_packages"].values()
               if wp["status"] == "failed"
           )

           assert state_data["wps_completed"] == actual_done
           assert state_data["wps_failed"] == actual_failed
           assert state_data["wps_total"] == len(state_data["work_packages"])

       def test_state_timestamps_are_valid(
           self,
           test_context_wp_created: TestContext,
       ):
           """State timestamps should be valid ISO format."""
           ctx = test_context_wp_created
           from datetime import datetime

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           with open(ctx.state_file) as f:
               state_data = json.load(f)

           # Validate started_at
           started_at = datetime.fromisoformat(state_data["started_at"].replace("Z", "+00:00"))
           assert started_at is not None

           # Validate WP timestamps
           for wp_id, wp in state_data["work_packages"].items():
               if "started_at" in wp and wp["started_at"]:
                   wp_started = datetime.fromisoformat(wp["started_at"].replace("Z", "+00:00"))
                   assert wp_started >= started_at, f"{wp_id} started before run"
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_happy_path.py` (add ~90 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T034 – Implement lane status consistency test

**Purpose**: Verify WP frontmatter lane matches state file.

**Steps**:
1. Add to `test_happy_path.py`:
   ```python
   import re
   import yaml

   @pytest.mark.orchestrator_happy_path
   class TestLaneConsistency:
       """Tests for lane status consistency between frontmatter and state."""

       def _read_wp_frontmatter(self, wp_file: Path) -> dict:
           """Extract YAML frontmatter from WP file."""
           content = wp_file.read_text()
           match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
           if not match:
               raise ValueError(f"No frontmatter in {wp_file}")
           return yaml.safe_load(match.group(1))

       def test_frontmatter_lane_matches_state(
           self,
           test_context_wp_created: TestContext,
       ):
           """WP frontmatter lane should match state after orchestration."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           # Load state
           with open(ctx.state_file) as f:
               state_data = json.load(f)

           # Check each WP file
           tasks_dir = ctx.feature_dir / "tasks"
           for wp_file in tasks_dir.glob("WP*.md"):
               wp_id = wp_file.stem  # e.g., "WP01"

               frontmatter = self._read_wp_frontmatter(wp_file)
               fm_lane = frontmatter.get("lane")

               state_wp = state_data["work_packages"].get(wp_id, {})
               state_status = state_wp.get("status")

               # Map state status to expected lane
               status_to_lane = {
                   "pending": "planned",
                   "in_progress": "doing",
                   "implementation_complete": "for_review",
                   "in_review": "for_review",
                   "done": "done",
                   "failed": "done",  # Failed WPs also go to done
               }
               expected_lane = status_to_lane.get(state_status)

               assert fm_lane == expected_lane, (
                   f"{wp_id}: frontmatter lane '{fm_lane}' != "
                   f"expected '{expected_lane}' (status: {state_status})"
               )

       def test_all_wps_in_done_lane_after_success(
           self,
           test_context_wp_created: TestContext,
       ):
           """All WPs should be in 'done' lane after successful orchestration."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           tasks_dir = ctx.feature_dir / "tasks"
           for wp_file in tasks_dir.glob("WP*.md"):
               frontmatter = self._read_wp_frontmatter(wp_file)
               assert frontmatter.get("lane") == "done", (
                   f"{wp_file.name} not in 'done' lane"
               )
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_happy_path.py` (add ~85 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T035 – Implement commit verification test

**Purpose**: Verify git commits exist in worktree branches.

**Steps**:
1. Add to `test_happy_path.py`:
   ```python
   import subprocess

   @pytest.mark.orchestrator_happy_path
   class TestCommitVerification:
       """Tests for git commit verification in worktrees."""

       def _get_git_log(self, repo_path: Path, count: int = 5) -> list[str]:
           """Get recent commit messages from git log."""
           result = subprocess.run(
               ["git", "log", f"-{count}", "--oneline"],
               cwd=repo_path,
               capture_output=True,
               text=True,
           )
           if result.returncode != 0:
               return []
           return result.stdout.strip().split("\n") if result.stdout.strip() else []

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

       def test_worktree_has_implementation_commit(
           self,
           test_context_wp_created: TestContext,
       ):
           """Worktree should have commit from implementation phase."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           # Find WP01 worktree
           worktree_path = ctx.worktrees_dir / "test-feature-WP01"
           assert worktree_path.exists()

           # Get commit count
           initial_commit = 1  # From fixture init
           commit_count = self._get_commit_count(worktree_path)

           # Should have more than just initial commit
           assert commit_count > initial_commit, (
               f"Expected implementation commits, found only {commit_count}"
           )

       def test_implementation_commit_references_wp(
           self,
           test_context_wp_created: TestContext,
       ):
           """Implementation commit message should reference the WP."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           worktree_path = ctx.worktrees_dir / "test-feature-WP01"
           commits = self._get_git_log(worktree_path, count=10)

           # At least one commit should mention WP01
           wp_mentioned = any("WP01" in commit or "wp01" in commit.lower() for commit in commits)
           # Or have conventional pattern like "implement" or "complete"
           has_impl_commit = any(
               any(word in commit.lower() for word in ["implement", "complete", "add", "create"])
               for commit in commits
           )

           assert wp_mentioned or has_impl_commit, (
               f"No implementation commit found. Commits: {commits}"
           )

       def test_main_branch_unchanged_during_orchestration(
           self,
           test_context_wp_created: TestContext,
       ):
           """Main branch should not receive commits during orchestration."""
           ctx = test_context_wp_created

           # Get initial main branch commit count
           initial_count = self._get_commit_count(ctx.repo_root)

           from specify_cli.orchestrator.runner import run_orchestration

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               wp_ids=["WP01"],
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           assert result.success

           # Main branch should have same commit count
           final_count = self._get_commit_count(ctx.repo_root)

           assert final_count == initial_count, (
               f"Main branch modified: {initial_count} -> {final_count} commits"
           )
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_happy_path.py` (add ~110 lines)

**Parallel?**: Yes - once fixtures ready

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Tests too slow | Mark with `@pytest.mark.slow`, run separately |
| Agent unavailable | Use `core_agent` marker to fail clearly |
| Flaky due to timing | Use state file timestamps, not wall clock |
| Orchestrator API changes | Import directly, update tests if needed |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] Single WP test completes in reasonable time (<5 minutes)
- [ ] State file validation catches invalid states
- [ ] Lane consistency test detects mismatches
- [ ] Commit verification confirms git history
- [ ] All tests pass with at least 1 core agent available

**Code Quality**:
- Tests are independent (can run in any order)
- Clear assertion messages explain failures
- Proper cleanup via fixtures
- No hardcoded agent names (use test_path)

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
- 2026-01-19T10:14:33Z – claude-opus – shell_pid=24345 – lane=doing – Started implementation via workflow command
- 2026-01-19T10:27:37Z – claude-opus – shell_pid=24345 – lane=for_review – Ready for review: Added happy path e2e tests (T031-T035). 12 tests passing, 6 e2e tests skipped (require real agents).
- 2026-01-19T10:27:56Z – claude-opus – shell_pid=37792 – lane=doing – Started review via workflow command
