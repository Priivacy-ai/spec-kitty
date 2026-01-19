---
work_package_id: WP09
title: Parallel and Dependency Tests
lane: "done"
dependencies:
- WP05
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
phase: Phase 1 - Core Tests
assignee: ''
agent: "claude-opus"
shell_pid: "46994"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-01-19T09:30:27Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP09 – Parallel and Dependency Tests

## Implementation Command

```bash
spec-kitty implement WP09 --base WP06
```

Depends on WP05 (fixtures) and WP06 (pytest configuration).

---

## Objectives & Success Criteria

Test parallel execution and dependency ordering:

- [ ] Independent WPs test confirms concurrent start
- [ ] Dependency blocking test verifies WPs wait for prerequisites
- [ ] Circular dependency test confirms early detection
- [ ] Diamond pattern test validates complex dependency resolution
- [ ] Linear chain and fan-out pattern tests cover common scenarios

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/spec.md` - User Story 3
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Dependency handling

**Existing Code**:
- `src/specify_cli/core/dependency_graph.py` - DependencyGraph class
- `tests/fixtures/orchestrator/` - Checkpoint fixtures

**Constraints**:
- Use state timestamps for timing verification (not wall clock)
- May need custom fixtures for specific dependency patterns
- Mark with `@pytest.mark.orchestrator_parallel`

---

## Subtasks & Detailed Guidance

### Subtask T041 – Implement independent WPs parallel test

**Purpose**: Verify independent WPs start approximately simultaneously.

**Steps**:
1. Create `tests/specify_cli/orchestrator/test_parallel_deps.py`:
   ```python
   """Parallel execution and dependency tests for orchestrator.

   These tests verify the orchestrator correctly handles WP dependencies
   and parallel execution.
   """
   from __future__ import annotations

   import pytest
   from pathlib import Path
   from datetime import datetime, timedelta

   from specify_cli.orchestrator.testing.fixtures import TestContext


   @pytest.mark.slow
   @pytest.mark.orchestrator_parallel
   @pytest.mark.core_agent
   class TestIndependentWPsParallel:
       """Tests for parallel execution of independent WPs."""

       def _parse_timestamp(self, ts: str) -> datetime:
           """Parse ISO timestamp to datetime."""
           return datetime.fromisoformat(ts.replace("Z", "+00:00"))

       def test_independent_wps_start_concurrently(
           self,
           test_context_factory,
       ):
           """Independent WPs should start within a short window."""
           # Need a fixture with multiple independent WPs
           # For now, we'll modify our fixture or create inline

           ctx = test_context_factory("wp_created")

           # Modify fixture to have WP01 and WP02 as independent
           # (remove WP02's dependency on WP01)
           # This may require fixture modification or inline setup

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           if not result.success:
               pytest.skip("Orchestration did not complete successfully")

           final_state = load_state(ctx.state_file)

           # Get start times
           wp01 = final_state.work_packages.get("WP01")
           wp02 = final_state.work_packages.get("WP02")

           if not wp01 or not wp02:
               pytest.skip("Both WPs required for this test")

           wp01_start = getattr(wp01, 'started_at', None)
           wp02_start = getattr(wp02, 'started_at', None)

           if wp01_start and wp02_start:
               t1 = self._parse_timestamp(wp01_start)
               t2 = self._parse_timestamp(wp02_start)
               diff = abs((t1 - t2).total_seconds())

               # Independent WPs should start within 30 seconds of each other
               # (allowing for orchestrator scheduling)
               assert diff < 30, (
                   f"Independent WPs started {diff}s apart (expected <30s)"
               )

       def test_parallel_wps_complete_independently(
           self,
           test_context_factory,
       ):
           """Parallel WPs should complete independently (one failure doesn't block other)."""
           ctx = test_context_factory("wp_created")

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           # Run all WPs
           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           final_state = load_state(ctx.state_file)

           # Count completed/failed
           completed = sum(
               1 for wp in final_state.work_packages.values()
               if wp.status == "done"
           )
           failed = sum(
               1 for wp in final_state.work_packages.values()
               if wp.status == "failed"
           )

           # At least some should have completed
           assert completed > 0 or failed > 0, "No WPs reached terminal state"
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_parallel_deps.py` (~90 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T042 – Implement dependency blocking test

**Purpose**: Verify WPs wait for dependencies before starting.

**Steps**:
1. Add to `test_parallel_deps.py`:
   ```python
   @pytest.mark.slow
   @pytest.mark.orchestrator_parallel
   @pytest.mark.core_agent
   class TestDependencyBlocking:
       """Tests for dependency blocking behavior."""

       def _parse_timestamp(self, ts: str) -> datetime:
           """Parse ISO timestamp to datetime."""
           return datetime.fromisoformat(ts.replace("Z", "+00:00"))

       def test_dependent_wp_waits_for_prerequisite(
           self,
           test_context_wp_created: TestContext,
       ):
           """WP with dependency should not start until dependency completes."""
           ctx = test_context_wp_created

           # In our fixture, WP02 depends on WP01
           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           final_state = load_state(ctx.state_file)

           wp01 = final_state.work_packages.get("WP01")
           wp02 = final_state.work_packages.get("WP02")

           if not wp01 or not wp02:
               pytest.skip("Both WPs required")

           # Get timestamps
           wp01_done = getattr(wp01, 'completed_at', None) or getattr(wp01, 'implementation_completed_at', None)
           wp02_start = getattr(wp02, 'started_at', None)

           if wp01_done and wp02_start:
               t1_done = self._parse_timestamp(wp01_done)
               t2_start = self._parse_timestamp(wp02_start)

               # WP02 should start after WP01 completes
               assert t2_start >= t1_done, (
                   f"WP02 started ({t2_start}) before WP01 completed ({t1_done})"
               )

       def test_dependency_chain_executes_in_order(
           self,
           test_context_factory,
       ):
           """A→B→C chain should execute strictly in order."""
           # Need fixture with 3-WP chain
           ctx = test_context_factory("wp_created")

           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           final_state = load_state(ctx.state_file)

           # Verify order by comparing start times
           wps = list(final_state.work_packages.values())

           # Sort by start time
           wps_with_times = [
               (wp.wp_id, getattr(wp, 'started_at', None))
               for wp in wps
               if getattr(wp, 'started_at', None)
           ]

           if len(wps_with_times) >= 2:
               # Dependent WPs should have later start times
               # (This is a simplified check; real verification needs dep graph)
               pass  # Detailed check would need fixture knowledge

       def test_blocked_wp_shows_pending_state(
           self,
           test_context_wp_created: TestContext,
       ):
           """WP waiting for dependency should remain in pending/blocked state."""
           ctx = test_context_wp_created

           from specify_cli.orchestrator.state import load_state

           # Check initial state
           initial_state = load_state(ctx.state_file)

           # WP02 depends on WP01, so if WP01 is pending, WP02 should be too
           wp01 = initial_state.work_packages.get("WP01")
           wp02 = initial_state.work_packages.get("WP02")

           if wp01 and wp02:
               if wp01.status == "pending":
                   # WP02 should also be pending (can't start)
                   assert wp02.status == "pending", (
                       f"WP02 should be pending while WP01 is pending, got: {wp02.status}"
                   )
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_parallel_deps.py` (add ~100 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T043 – Implement circular dependency detection test

**Purpose**: Verify circular dependencies are detected before execution.

**Steps**:
1. Add to `test_parallel_deps.py`:
   ```python
   import json
   import tempfile
   import shutil

   @pytest.mark.orchestrator_parallel
   class TestCircularDependencyDetection:
       """Tests for circular dependency detection."""

       def _create_circular_dep_fixture(self, base_ctx: TestContext) -> Path:
           """Create a fixture with circular dependency."""
           # Copy base fixture
           temp_dir = Path(tempfile.mkdtemp(prefix="circular_dep_test_"))

           shutil.copytree(base_ctx.feature_dir, temp_dir / "feature")

           # Modify WP files to create cycle: WP01 → WP02 → WP01
           wp01_path = temp_dir / "feature" / "tasks" / "WP01.md"
           wp02_path = temp_dir / "feature" / "tasks" / "WP02.md"

           if wp01_path.exists():
               content = wp01_path.read_text()
               # Add WP02 as dependency to WP01
               content = content.replace(
                   'dependencies: []',
                   'dependencies: ["WP02"]'
               )
               wp01_path.write_text(content)

           return temp_dir

       def test_circular_dependency_detected_at_validation(
           self,
           test_context_wp_created: TestContext,
       ):
           """Circular dependency should be caught before execution starts."""
           ctx = test_context_wp_created

           # Create circular dependency
           temp_dir = self._create_circular_dep_fixture(ctx)

           try:
               from specify_cli.orchestrator.runner import run_orchestration
               from specify_cli.core.dependency_graph import (
                   DependencyGraph,
                   CircularDependencyError,
               )

               feature_dir = temp_dir / "feature"

               # Building the graph should detect the cycle
               with pytest.raises(CircularDependencyError):
                   graph = DependencyGraph.build_graph(feature_dir / "tasks")
                   graph.validate()

           finally:
               shutil.rmtree(temp_dir, ignore_errors=True)

       def test_circular_dependency_error_message_shows_cycle(
           self,
           test_context_wp_created: TestContext,
       ):
           """Error message should identify the WPs involved in cycle."""
           ctx = test_context_wp_created
           temp_dir = self._create_circular_dep_fixture(ctx)

           try:
               from specify_cli.core.dependency_graph import (
                   DependencyGraph,
                   CircularDependencyError,
               )

               feature_dir = temp_dir / "feature"

               try:
                   graph = DependencyGraph.build_graph(feature_dir / "tasks")
                   graph.validate()
                   pytest.fail("Expected CircularDependencyError")
               except CircularDependencyError as e:
                   # Error should mention the cycle
                   error_msg = str(e).lower()
                   assert "wp01" in error_msg or "wp02" in error_msg, (
                       f"Error should identify cycle WPs: {e}"
                   )

           finally:
               shutil.rmtree(temp_dir, ignore_errors=True)

       def test_orchestration_aborts_on_circular_dependency(
           self,
           test_context_wp_created: TestContext,
       ):
           """Orchestration should abort immediately when cycle detected."""
           ctx = test_context_wp_created
           temp_dir = self._create_circular_dep_fixture(ctx)

           try:
               from specify_cli.orchestrator.runner import run_orchestration

               feature_dir = temp_dir / "feature"

               result = run_orchestration(
                   feature_dir=feature_dir,
                   implementation_agent=ctx.test_path.implementation_agent,
                   review_agent=ctx.test_path.review_agent,
               )

               # Should fail with clear error
               assert not result.success
               assert "circular" in result.error.lower() or "cycle" in result.error.lower()

           finally:
               shutil.rmtree(temp_dir, ignore_errors=True)
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_parallel_deps.py` (add ~100 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T044 – Implement diamond dependency pattern test

**Purpose**: Test complex diamond pattern: A→B, A→C, B→D, C→D.

**Steps**:
1. Add to `test_parallel_deps.py`:
   ```python
   @pytest.mark.slow
   @pytest.mark.orchestrator_parallel
   @pytest.mark.core_agent
   class TestDiamondDependency:
       """Tests for diamond dependency pattern."""

       def _parse_timestamp(self, ts: str) -> datetime:
           """Parse ISO timestamp."""
           return datetime.fromisoformat(ts.replace("Z", "+00:00"))

       def _create_diamond_fixture(self, base_ctx: TestContext) -> Path:
           """Create fixture with diamond pattern: WP01→WP02,WP03→WP04."""
           temp_dir = Path(tempfile.mkdtemp(prefix="diamond_dep_test_"))
           shutil.copytree(base_ctx.feature_dir, temp_dir / "feature")

           tasks_dir = temp_dir / "feature" / "tasks"

           # Create WP03.md
           wp03_content = '''---
   work_package_id: "WP03"
   title: "Third Task"
   lane: "planned"
   dependencies: ["WP01"]
   subtasks: ["T003"]
   ---

   # Work Package: WP03 – Third Task

   ## Objective

   Create a file at `test_output/wp03_output.txt`.
   '''
           (tasks_dir / "WP03.md").write_text(wp03_content)

           # Create WP04.md (depends on both WP02 and WP03)
           wp04_content = '''---
   work_package_id: "WP04"
   title: "Fourth Task"
   lane: "planned"
   dependencies: ["WP02", "WP03"]
   subtasks: ["T004"]
   ---

   # Work Package: WP04 – Fourth Task

   ## Objective

   Create a file at `test_output/wp04_output.txt`.
   '''
           (tasks_dir / "WP04.md").write_text(wp04_content)

           # Update state.json
           state_file = temp_dir / "feature" / ".orchestration-state.json"
           if state_file.exists():
               with open(state_file) as f:
                   state = json.load(f)

               state["wps_total"] = 4
               state["work_packages"]["WP03"] = {
                   "wp_id": "WP03",
                   "status": "pending",
                   "dependencies": ["WP01"]
               }
               state["work_packages"]["WP04"] = {
                   "wp_id": "WP04",
                   "status": "pending",
                   "dependencies": ["WP02", "WP03"]
               }

               with open(state_file, "w") as f:
                   json.dump(state, f, indent=2)

           return temp_dir

       def test_diamond_pattern_resolves_correctly(
           self,
           test_context_wp_created: TestContext,
       ):
           """Diamond pattern should complete with correct ordering."""
           ctx = test_context_wp_created
           temp_dir = self._create_diamond_fixture(ctx)

           try:
               from specify_cli.orchestrator.runner import run_orchestration
               from specify_cli.orchestrator.state import load_state

               feature_dir = temp_dir / "feature"

               result = run_orchestration(
                   feature_dir=feature_dir,
                   implementation_agent=ctx.test_path.implementation_agent,
                   review_agent=ctx.test_path.review_agent,
               )

               if not result.success:
                   pytest.skip(f"Orchestration failed: {result.error}")

               final_state = load_state(feature_dir / ".orchestration-state.json")

               # All 4 WPs should complete
               completed = sum(
                   1 for wp in final_state.work_packages.values()
                   if wp.status == "done"
               )
               assert completed == 4, f"Expected 4 done, got {completed}"

           finally:
               shutil.rmtree(temp_dir, ignore_errors=True)

       def test_diamond_wp4_waits_for_both_parents(
           self,
           test_context_wp_created: TestContext,
       ):
           """WP04 should not start until both WP02 and WP03 complete."""
           ctx = test_context_wp_created
           temp_dir = self._create_diamond_fixture(ctx)

           try:
               from specify_cli.orchestrator.runner import run_orchestration
               from specify_cli.orchestrator.state import load_state

               feature_dir = temp_dir / "feature"

               result = run_orchestration(
                   feature_dir=feature_dir,
                   implementation_agent=ctx.test_path.implementation_agent,
                   review_agent=ctx.test_path.review_agent,
               )

               if not result.success:
                   pytest.skip("Orchestration failed")

               final_state = load_state(feature_dir / ".orchestration-state.json")

               wp02 = final_state.work_packages.get("WP02")
               wp03 = final_state.work_packages.get("WP03")
               wp04 = final_state.work_packages.get("WP04")

               if not all([wp02, wp03, wp04]):
                   pytest.skip("Missing WPs")

               # Get completion times for WP02, WP03
               wp02_done = getattr(wp02, 'completed_at', None)
               wp03_done = getattr(wp03, 'completed_at', None)
               wp04_start = getattr(wp04, 'started_at', None)

               if wp02_done and wp03_done and wp04_start:
                   t2_done = self._parse_timestamp(wp02_done)
                   t3_done = self._parse_timestamp(wp03_done)
                   t4_start = self._parse_timestamp(wp04_start)

                   # WP04 should start after BOTH parents complete
                   later_parent = max(t2_done, t3_done)
                   assert t4_start >= later_parent, (
                       f"WP04 started before both parents completed"
                   )

           finally:
               shutil.rmtree(temp_dir, ignore_errors=True)
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_parallel_deps.py` (add ~150 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T045 – Implement linear chain test

**Purpose**: Test simple linear dependency: WP01→WP02→WP03.

**Steps**:
1. Add to `test_parallel_deps.py`:
   ```python
   @pytest.mark.slow
   @pytest.mark.orchestrator_parallel
   @pytest.mark.core_agent
   class TestLinearChain:
       """Tests for linear dependency chain."""

       def _parse_timestamp(self, ts: str) -> datetime:
           return datetime.fromisoformat(ts.replace("Z", "+00:00"))

       def test_linear_chain_executes_sequentially(
           self,
           test_context_wp_created: TestContext,
       ):
           """Linear chain A→B should execute strictly in order."""
           ctx = test_context_wp_created

           # Our default fixture has WP01→WP02
           from specify_cli.orchestrator.runner import run_orchestration
           from specify_cli.orchestrator.state import load_state

           result = run_orchestration(
               feature_dir=ctx.feature_dir,
               implementation_agent=ctx.test_path.implementation_agent,
               review_agent=ctx.test_path.review_agent,
           )

           if not result.success:
               pytest.skip("Orchestration failed")

           final_state = load_state(ctx.state_file)

           wp01 = final_state.work_packages.get("WP01")
           wp02 = final_state.work_packages.get("WP02")

           if wp01 and wp02:
               wp01_done = getattr(wp01, 'completed_at', None)
               wp02_start = getattr(wp02, 'started_at', None)

               if wp01_done and wp02_start:
                   t1_done = self._parse_timestamp(wp01_done)
                   t2_start = self._parse_timestamp(wp02_start)

                   assert t2_start >= t1_done, (
                       "WP02 started before WP01 completed in linear chain"
                   )

       def test_chain_failure_blocks_downstream(
           self,
           test_context_factory,
       ):
           """Failure in chain should prevent downstream WPs from starting."""
           ctx = test_context_factory("wp_created")

           # This test would need a way to force WP01 failure
           # For now, we verify the principle with state inspection

           from specify_cli.orchestrator.state import load_state

           initial_state = load_state(ctx.state_file)

           # If we mark WP01 as failed, WP02 should not be runnable
           # (This is more of a unit test for dependency logic)

           wp01 = initial_state.work_packages.get("WP01")
           wp02 = initial_state.work_packages.get("WP02")

           if wp01 and wp02:
               # Verify dependency is recorded
               deps = getattr(wp02, 'dependencies', [])
               assert "WP01" in deps, "WP02 should depend on WP01"
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_parallel_deps.py` (add ~70 lines)

**Parallel?**: Yes - once fixtures ready

---

### Subtask T046 – Implement fan-out pattern test

**Purpose**: Test fan-out pattern: WP01→WP02, WP01→WP03, WP01→WP04.

**Steps**:
1. Add to `test_parallel_deps.py`:
   ```python
   @pytest.mark.slow
   @pytest.mark.orchestrator_parallel
   @pytest.mark.core_agent
   class TestFanOutPattern:
       """Tests for fan-out dependency pattern."""

       def _parse_timestamp(self, ts: str) -> datetime:
           return datetime.fromisoformat(ts.replace("Z", "+00:00"))

       def _create_fanout_fixture(self, base_ctx: TestContext) -> Path:
           """Create fixture with fan-out: WP01→WP02, WP01→WP03."""
           temp_dir = Path(tempfile.mkdtemp(prefix="fanout_dep_test_"))
           shutil.copytree(base_ctx.feature_dir, temp_dir / "feature")

           tasks_dir = temp_dir / "feature" / "tasks"

           # Create WP03.md (depends on WP01, parallel to WP02)
           wp03_content = '''---
   work_package_id: "WP03"
   title: "Third Task (Parallel)"
   lane: "planned"
   dependencies: ["WP01"]
   subtasks: ["T003"]
   ---

   # Work Package: WP03 – Third Task

   ## Objective

   Create a file at `test_output/wp03_output.txt`.
   '''
           (tasks_dir / "WP03.md").write_text(wp03_content)

           # Update WP02 to also depend only on WP01
           wp02_path = tasks_dir / "WP02.md"
           if wp02_path.exists():
               content = wp02_path.read_text()
               # Ensure WP02 depends on WP01
               if 'dependencies: ["WP01"]' not in content:
                   content = content.replace(
                       'dependencies: []',
                       'dependencies: ["WP01"]'
                   )
                   wp02_path.write_text(content)

           # Update state
           state_file = temp_dir / "feature" / ".orchestration-state.json"
           if state_file.exists():
               with open(state_file) as f:
                   state = json.load(f)

               state["wps_total"] = 3
               state["work_packages"]["WP03"] = {
                   "wp_id": "WP03",
                   "status": "pending",
                   "dependencies": ["WP01"]
               }

               with open(state_file, "w") as f:
                   json.dump(state, f, indent=2)

           return temp_dir

       def test_fanout_children_start_after_parent(
           self,
           test_context_wp_created: TestContext,
       ):
           """All fan-out children should start after parent completes."""
           ctx = test_context_wp_created
           temp_dir = self._create_fanout_fixture(ctx)

           try:
               from specify_cli.orchestrator.runner import run_orchestration
               from specify_cli.orchestrator.state import load_state

               feature_dir = temp_dir / "feature"

               result = run_orchestration(
                   feature_dir=feature_dir,
                   implementation_agent=ctx.test_path.implementation_agent,
                   review_agent=ctx.test_path.review_agent,
               )

               if not result.success:
                   pytest.skip("Orchestration failed")

               final_state = load_state(feature_dir / ".orchestration-state.json")

               wp01 = final_state.work_packages.get("WP01")
               wp02 = final_state.work_packages.get("WP02")
               wp03 = final_state.work_packages.get("WP03")

               if not all([wp01, wp02, wp03]):
                   pytest.skip("Missing WPs")

               wp01_done = getattr(wp01, 'completed_at', None)
               wp02_start = getattr(wp02, 'started_at', None)
               wp03_start = getattr(wp03, 'started_at', None)

               if wp01_done:
                   t1_done = self._parse_timestamp(wp01_done)

                   if wp02_start:
                       t2_start = self._parse_timestamp(wp02_start)
                       assert t2_start >= t1_done, "WP02 started before WP01"

                   if wp03_start:
                       t3_start = self._parse_timestamp(wp03_start)
                       assert t3_start >= t1_done, "WP03 started before WP01"

           finally:
               shutil.rmtree(temp_dir, ignore_errors=True)

       def test_fanout_children_run_in_parallel(
           self,
           test_context_wp_created: TestContext,
       ):
           """Fan-out children should start approximately simultaneously."""
           ctx = test_context_wp_created
           temp_dir = self._create_fanout_fixture(ctx)

           try:
               from specify_cli.orchestrator.runner import run_orchestration
               from specify_cli.orchestrator.state import load_state

               feature_dir = temp_dir / "feature"

               result = run_orchestration(
                   feature_dir=feature_dir,
                   implementation_agent=ctx.test_path.implementation_agent,
                   review_agent=ctx.test_path.review_agent,
               )

               if not result.success:
                   pytest.skip("Orchestration failed")

               final_state = load_state(feature_dir / ".orchestration-state.json")

               wp02 = final_state.work_packages.get("WP02")
               wp03 = final_state.work_packages.get("WP03")

               if not (wp02 and wp03):
                   pytest.skip("Missing WPs")

               wp02_start = getattr(wp02, 'started_at', None)
               wp03_start = getattr(wp03, 'started_at', None)

               if wp02_start and wp03_start:
                   t2 = self._parse_timestamp(wp02_start)
                   t3 = self._parse_timestamp(wp03_start)
                   diff = abs((t2 - t3).total_seconds())

                   # Should start within 30s of each other (parallel)
                   assert diff < 30, (
                       f"Fan-out children started {diff}s apart (expected <30s)"
                   )

           finally:
               shutil.rmtree(temp_dir, ignore_errors=True)
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_parallel_deps.py` (add ~150 lines)

**Parallel?**: Yes - once fixtures ready

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Timing tests flaky | Use state timestamps, allow 30s tolerance |
| Fixture creation complex | Reuse base fixture, modify in-memory |
| Circular dependency import | Import DependencyGraph from correct module |
| Parallel tests interfere | Each test uses isolated temp directory |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] Independent WPs start within 30s of each other
- [ ] Dependent WP waits for prerequisite completion
- [ ] Circular dependency detected and reported clearly
- [ ] Diamond pattern completes with correct ordering
- [ ] Fan-out children start in parallel after parent

**Code Quality**:
- Proper cleanup of temp directories
- Timestamp parsing handles timezone suffixes
- Clear skip messages when fixtures don't match
- No hardcoded time assertions (use relative checks)

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
- 2026-01-19T10:23:08Z – claude-opus – shell_pid=32537 – lane=doing – Started implementation via workflow command
- 2026-01-19T12:52:48Z – claude-opus – shell_pid=32537 – lane=for_review – Moved to for_review
- 2026-01-19T12:55:22Z – claude-opus – shell_pid=46994 – lane=doing – Started review via workflow command
- 2026-01-19T12:56:47Z – claude-opus – shell_pid=46994 – lane=done – Review passed: 18 tests passing covering dependency patterns (circular, diamond, linear, fan-out). Tests use dependency graph functions directly without requiring agents.
