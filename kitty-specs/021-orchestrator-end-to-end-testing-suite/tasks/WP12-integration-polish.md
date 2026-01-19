---
work_package_id: WP12
title: Integration and Polish
lane: "doing"
dependencies: []
subtasks:
- T056
- T057
- T058
- T059
- T060
phase: Phase 3 - Polish
assignee: ''
agent: "claude-opus"
shell_pid: "58477"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-19T09:30:27Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP12 – Integration and Polish

## Implementation Command

```bash
spec-kitty implement WP12 --base WP11
```

Depends on all previous WPs (final polish).

---

## Objectives & Success Criteria

Final integration, validation utilities, and polish:

- [ ] Root conftest.py registers orchestrator markers
- [ ] `validate_test_result()` utility exists for state validation
- [ ] Test output helpers distinguish skip vs fail messages
- [ ] Timeout configuration via environment variables
- [ ] Quickstart.md scenarios work as documented

## Context & Constraints

**Reference Documents**:
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/quickstart.md` - User scenarios
- `kitty-specs/021-orchestrator-end-to-end-testing-suite/plan.md` - Timeout defaults

**Existing Code**:
- All previous WP implementations
- `tests/conftest.py` - Root pytest configuration

**Constraints**:
- Must not break existing tests
- Timeout defaults: 300s per test, 10s for probe
- Environment variables for configurability

---

## Subtasks & Detailed Guidance

### Subtask T056 – Update root conftest.py

**Purpose**: Register orchestrator markers in root pytest configuration.

**Steps**:
1. Check if `tests/conftest.py` exists, if not create it.

2. Add orchestrator marker registration:
   ```python
   # tests/conftest.py

   import pytest


   def pytest_configure(config):
       """Register custom markers."""
       # Orchestrator e2e test markers
       config.addinivalue_line(
           "markers",
           "orchestrator_availability: tests for agent availability detection"
       )
       config.addinivalue_line(
           "markers",
           "orchestrator_fixtures: tests for fixture loading and management"
       )
       config.addinivalue_line(
           "markers",
           "orchestrator_happy_path: happy path end-to-end tests"
       )
       config.addinivalue_line(
           "markers",
           "orchestrator_review_cycles: review rejection/approval cycle tests"
       )
       config.addinivalue_line(
           "markers",
           "orchestrator_parallel: parallel execution and dependency tests"
       )
       config.addinivalue_line(
           "markers",
           "orchestrator_smoke: basic smoke tests for agent invocation"
       )
       config.addinivalue_line(
           "markers",
           "core_agent: test requires core tier agent (fails if unavailable)"
       )
       config.addinivalue_line(
           "markers",
           "extended_agent: test for extended tier agent (skips if unavailable)"
       )
       config.addinivalue_line(
           "markers",
           "slow: test expected to take >30 seconds"
       )


   # Hook to ensure orchestrator tests report clearly
   def pytest_collection_modifyitems(config, items):
       """Modify test collection for orchestrator tests."""
       for item in items:
           # Add slow marker to orchestrator e2e tests automatically
           if "orchestrator" in str(item.fspath):
               if not item.get_closest_marker("slow"):
                   # Most orchestrator tests are slow
                   pass  # Don't auto-add, let tests declare explicitly
   ```

3. Alternative: Add to `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   markers = [
       "orchestrator_availability: tests for agent availability detection",
       "orchestrator_fixtures: tests for fixture loading and management",
       "orchestrator_happy_path: happy path end-to-end tests",
       "orchestrator_review_cycles: review rejection/approval cycle tests",
       "orchestrator_parallel: parallel execution and dependency tests",
       "orchestrator_smoke: basic smoke tests for agent invocation",
       "core_agent: test requires core tier agent (fails if unavailable)",
       "extended_agent: test for extended tier agent (skips if unavailable)",
       "slow: test expected to take >30 seconds",
   ]
   ```

**Files**:
- `tests/conftest.py` (update ~40 lines)
- OR `pyproject.toml` (add marker configuration)

**Parallel?**: Yes - can proceed with T057-T059

---

### Subtask T057 – Add state validation utilities

**Purpose**: Provide `validate_test_result()` for comprehensive state validation.

**Steps**:
1. Create `tests/specify_cli/orchestrator/validation.py`:
   ```python
   """Validation utilities for orchestrator test results.

   Provides functions to validate OrchestrationRun state after tests.
   """
   from __future__ import annotations

   import json
   from dataclasses import dataclass
   from datetime import datetime
   from pathlib import Path
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from specify_cli.orchestrator.testing.fixtures import TestContext


   @dataclass
   class ValidationResult:
       """Result of state validation."""

       valid: bool
       """Whether validation passed."""

       errors: list[str]
       """List of validation errors."""

       warnings: list[str]
       """List of validation warnings (non-fatal)."""

       def __bool__(self) -> bool:
           return self.valid


   def validate_state_file(state_path: Path) -> ValidationResult:
       """Validate an OrchestrationRun state file.

       Args:
           state_path: Path to state.json

       Returns:
           ValidationResult with any errors/warnings
       """
       errors = []
       warnings = []

       if not state_path.exists():
           return ValidationResult(False, ["State file does not exist"], [])

       try:
           with open(state_path) as f:
               state = json.load(f)
       except json.JSONDecodeError as e:
           return ValidationResult(False, [f"Invalid JSON: {e}"], [])

       # Required top-level fields
       required_fields = [
           "run_id", "feature_slug", "started_at",
           "status", "wps_total", "wps_completed",
           "wps_failed", "work_packages"
       ]
       for field in required_fields:
           if field not in state:
               errors.append(f"Missing required field: {field}")

       if errors:
           return ValidationResult(False, errors, warnings)

       # Validate counts
       wps = state.get("work_packages", {})
       actual_completed = sum(
           1 for wp in wps.values()
           if wp.get("status") == "done"
       )
       actual_failed = sum(
           1 for wp in wps.values()
           if wp.get("status") == "failed"
       )

       if state["wps_completed"] != actual_completed:
           errors.append(
               f"wps_completed mismatch: "
               f"field={state['wps_completed']}, actual={actual_completed}"
           )
       if state["wps_failed"] != actual_failed:
           errors.append(
               f"wps_failed mismatch: "
               f"field={state['wps_failed']}, actual={actual_failed}"
           )
       if state["wps_total"] != len(wps):
           warnings.append(
               f"wps_total ({state['wps_total']}) != work_packages count ({len(wps)})"
           )

       # Validate timestamps
       try:
           datetime.fromisoformat(state["started_at"].replace("Z", "+00:00"))
       except (ValueError, AttributeError):
           errors.append(f"Invalid started_at timestamp: {state.get('started_at')}")

       # Validate each WP
       for wp_id, wp in wps.items():
           if "wp_id" not in wp:
               errors.append(f"WP {wp_id} missing wp_id field")
           elif wp["wp_id"] != wp_id:
               errors.append(f"WP key {wp_id} != wp_id field {wp['wp_id']}")

           if "status" not in wp:
               errors.append(f"WP {wp_id} missing status field")

       return ValidationResult(
           valid=len(errors) == 0,
           errors=errors,
           warnings=warnings
       )


   def validate_lane_consistency(
       feature_dir: Path,
       state_path: Path
   ) -> ValidationResult:
       """Validate WP frontmatter lanes match state file.

       Args:
           feature_dir: Path to feature directory
           state_path: Path to state.json

       Returns:
           ValidationResult with any mismatches
       """
       import re
       import yaml

       errors = []
       warnings = []

       # Load state
       try:
           with open(state_path) as f:
               state = json.load(f)
       except Exception as e:
           return ValidationResult(False, [f"Cannot load state: {e}"], [])

       # Status to lane mapping
       status_to_lane = {
           "pending": "planned",
           "in_progress": "doing",
           "implementation_complete": "for_review",
           "in_review": "for_review",
           "review_rejected": "doing",
           "review_approved": "for_review",
           "done": "done",
           "failed": "done",
       }

       tasks_dir = feature_dir / "tasks"
       if not tasks_dir.exists():
           return ValidationResult(False, ["tasks/ directory not found"], [])

       for wp_file in tasks_dir.glob("WP*.md"):
           wp_id = wp_file.stem
           content = wp_file.read_text()

           # Extract frontmatter
           match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
           if not match:
               warnings.append(f"{wp_id}: No frontmatter found")
               continue

           try:
               fm = yaml.safe_load(match.group(1))
           except yaml.YAMLError:
               warnings.append(f"{wp_id}: Invalid YAML frontmatter")
               continue

           fm_lane = fm.get("lane")
           state_wp = state.get("work_packages", {}).get(wp_id, {})
           state_status = state_wp.get("status")

           expected_lane = status_to_lane.get(state_status)

           if fm_lane != expected_lane:
               errors.append(
                   f"{wp_id}: lane='{fm_lane}' but expected='{expected_lane}' "
                   f"(status={state_status})"
               )

       return ValidationResult(
           valid=len(errors) == 0,
           errors=errors,
           warnings=warnings
       )


   def validate_test_result(ctx: "TestContext") -> ValidationResult:
       """Comprehensive validation of test context after orchestration.

       Args:
           ctx: TestContext to validate

       Returns:
           Combined ValidationResult
       """
       all_errors = []
       all_warnings = []

       # Validate state file
       state_result = validate_state_file(ctx.state_file)
       all_errors.extend(state_result.errors)
       all_warnings.extend(state_result.warnings)

       # Validate lane consistency
       lane_result = validate_lane_consistency(ctx.feature_dir, ctx.state_file)
       all_errors.extend(lane_result.errors)
       all_warnings.extend(lane_result.warnings)

       # Validate temp directory exists
       if not ctx.temp_dir.exists():
           all_errors.append("temp_dir does not exist")

       # Validate repo root has .git
       if not (ctx.repo_root / ".git").exists():
           all_warnings.append("repo_root missing .git directory")

       return ValidationResult(
           valid=len(all_errors) == 0,
           errors=all_errors,
           warnings=all_warnings
       )
   ```

**Files**:
- `tests/specify_cli/orchestrator/validation.py` (~180 lines)

**Parallel?**: Yes - can proceed with T056, T058, T059

---

### Subtask T058 – Add test output helpers

**Purpose**: Distinguish skip vs fail messages in test output.

**Steps**:
1. Add to `tests/specify_cli/orchestrator/conftest.py`:
   ```python
   import pytest


   def pytest_runtest_makereport(item, call):
       """Customize test report for orchestrator tests."""
       if call.when == "call":
           # Check if this is an orchestrator test
           if "orchestrator" in str(item.fspath):
               # Access the test result
               pass  # Hook for future customization


   # Custom skip reasons for better reporting
   class OrchestratorSkipReasons:
       """Standard skip reasons for orchestrator tests."""

       @staticmethod
       def agent_not_available(agent_id: str, reason: str | None = None) -> str:
           """Format skip reason for unavailable agent."""
           if reason:
               return f"Agent '{agent_id}' not available: {reason}"
           return f"Agent '{agent_id}' not available"

       @staticmethod
       def insufficient_agents(required: int, available: int) -> str:
           """Format skip reason for insufficient agents."""
           return f"Test requires {required} agents, only {available} available"

       @staticmethod
       def fixture_not_found(fixture_name: str) -> str:
           """Format skip reason for missing fixture."""
           return f"Fixture '{fixture_name}' not found"

       @staticmethod
       def prerequisite_failed(wp_id: str) -> str:
           """Format skip reason when prerequisite WP failed."""
           return f"Prerequisite WP '{wp_id}' failed"


   # Make available to tests
   skip_reasons = OrchestratorSkipReasons()


   # Helper for conditional skip
   def skip_if_agent_unavailable(
       agent_id: str,
       available_agents: dict,
       tier: str = "any"
   ):
       """Skip test if agent is unavailable.

       Args:
           agent_id: Agent to check
           available_agents: Dict from fixture
           tier: 'core' (fail), 'extended' (skip), or 'any' (skip)
       """
       from specify_cli.orchestrator.testing.availability import CORE_AGENTS

       avail = available_agents.get(agent_id)

       if avail is None or not avail.is_available:
           reason = avail.failure_reason if avail else "Not detected"

           if tier == "core" or (tier == "any" and agent_id in CORE_AGENTS):
               # Core agents should fail, not skip
               pytest.fail(skip_reasons.agent_not_available(agent_id, reason))
           else:
               pytest.skip(skip_reasons.agent_not_available(agent_id, reason))
   ```

2. Add output formatting for validation results:
   ```python
   def format_validation_result(result: "ValidationResult") -> str:
       """Format validation result for test output.

       Args:
           result: ValidationResult to format

       Returns:
           Formatted string for test output
       """
       lines = []

       if result.valid:
           lines.append("✓ Validation passed")
       else:
           lines.append("✗ Validation failed")

       if result.errors:
           lines.append("\nErrors:")
           for error in result.errors:
               lines.append(f"  - {error}")

       if result.warnings:
           lines.append("\nWarnings:")
           for warning in result.warnings:
               lines.append(f"  - {warning}")

       return "\n".join(lines)
   ```

**Files**:
- `tests/specify_cli/orchestrator/conftest.py` (add ~80 lines)

**Parallel?**: Yes - can proceed with T056, T057, T059

---

### Subtask T059 – Add timeout configuration

**Purpose**: Make timeouts configurable via environment variables.

**Steps**:
1. Create `tests/specify_cli/orchestrator/config.py`:
   ```python
   """Configuration for orchestrator tests.

   All timeouts and limits are configurable via environment variables.
   """
   from __future__ import annotations

   import os
   from dataclasses import dataclass


   @dataclass
   class OrchestratorTestConfig:
       """Configuration for orchestrator tests."""

       # Agent detection
       probe_timeout_seconds: int = 10
       """Timeout for agent probe calls."""

       # Test execution
       test_timeout_seconds: int = 300
       """Default timeout for e2e tests."""

       smoke_timeout_seconds: int = 60
       """Timeout for smoke tests."""

       # Orchestration
       max_review_cycles: int = 3
       """Maximum review cycles before failure."""

       # Parallel timing
       parallel_start_tolerance_seconds: int = 30
       """Max time difference for 'parallel' start times."""

       @classmethod
       def from_environment(cls) -> "OrchestratorTestConfig":
           """Load configuration from environment variables.

           Environment variables:
               ORCHESTRATOR_PROBE_TIMEOUT: Probe timeout (default: 10)
               ORCHESTRATOR_TEST_TIMEOUT: Test timeout (default: 300)
               ORCHESTRATOR_SMOKE_TIMEOUT: Smoke test timeout (default: 60)
               ORCHESTRATOR_MAX_REVIEW_CYCLES: Max review cycles (default: 3)
               ORCHESTRATOR_PARALLEL_TOLERANCE: Parallel timing tolerance (default: 30)

           Returns:
               OrchestratorTestConfig with values from environment
           """
           return cls(
               probe_timeout_seconds=int(
                   os.environ.get("ORCHESTRATOR_PROBE_TIMEOUT", "10")
               ),
               test_timeout_seconds=int(
                   os.environ.get("ORCHESTRATOR_TEST_TIMEOUT", "300")
               ),
               smoke_timeout_seconds=int(
                   os.environ.get("ORCHESTRATOR_SMOKE_TIMEOUT", "60")
               ),
               max_review_cycles=int(
                   os.environ.get("ORCHESTRATOR_MAX_REVIEW_CYCLES", "3")
               ),
               parallel_start_tolerance_seconds=int(
                   os.environ.get("ORCHESTRATOR_PARALLEL_TOLERANCE", "30")
               ),
           )


   # Global config instance
   _config: OrchestratorTestConfig | None = None


   def get_config() -> OrchestratorTestConfig:
       """Get the test configuration (singleton).

       Returns:
           OrchestratorTestConfig instance
       """
       global _config
       if _config is None:
           _config = OrchestratorTestConfig.from_environment()
       return _config


   def reset_config() -> None:
       """Reset configuration (for testing)."""
       global _config
       _config = None
   ```

2. Update tests to use config:
   ```python
   # In test files, use:
   from tests.specify_cli.orchestrator.config import get_config

   config = get_config()
   timeout = config.test_timeout_seconds
   ```

3. Add pytest fixture for config:
   ```python
   # In conftest.py
   from tests.specify_cli.orchestrator.config import (
       get_config,
       OrchestratorTestConfig,
   )

   @pytest.fixture(scope="session")
   def orchestrator_config() -> OrchestratorTestConfig:
       """Provide test configuration."""
       return get_config()
   ```

**Files**:
- `tests/specify_cli/orchestrator/config.py` (~90 lines)
- `tests/specify_cli/orchestrator/conftest.py` (add fixture)

**Parallel?**: Yes - can proceed with T056-T058

---

### Subtask T060 – Validate quickstart.md scenarios

**Purpose**: Verify documented quickstart scenarios work.

**Steps**:
1. Create `tests/specify_cli/orchestrator/test_quickstart.py`:
   ```python
   """Tests that validate quickstart.md scenarios work as documented.

   These tests verify the documented user workflows function correctly.
   """
   from __future__ import annotations

   import subprocess
   import pytest
   from pathlib import Path


   @pytest.mark.orchestrator_fixtures
   class TestQuickstartScenarios:
       """Tests for quickstart.md documented scenarios."""

       def test_check_agent_availability_command(self):
           """'spec-kitty agents status' should work."""
           # This tests the documented command works
           result = subprocess.run(
               ["spec-kitty", "agents", "status"],
               capture_output=True,
               text=True,
               timeout=30,
           )

           # Command should execute (may show no agents)
           assert result.returncode == 0 or "error" not in result.stderr.lower(), (
               f"Command failed: {result.stderr}"
           )

       def test_run_orchestrator_tests_command(self):
           """'pytest -m orchestrator_happy_path' should collect tests."""
           result = subprocess.run(
               ["pytest", "--collect-only", "-m", "orchestrator_happy_path"],
               capture_output=True,
               text=True,
               timeout=30,
           )

           # Should collect at least one test (or report none)
           # Returncode 5 means no tests collected, which is OK if no agents
           assert result.returncode in (0, 5), (
               f"pytest failed: {result.stderr}"
           )

       def test_run_smoke_tests_command(self):
           """'pytest -m orchestrator_smoke' should work."""
           result = subprocess.run(
               ["pytest", "--collect-only", "-m", "orchestrator_smoke"],
               capture_output=True,
               text=True,
               timeout=30,
           )

           assert result.returncode in (0, 5)

       def test_environment_variables_documented(self):
           """Documented environment variables should be recognized."""
           from tests.specify_cli.orchestrator.config import (
               OrchestratorTestConfig,
           )

           # Verify config class has documented fields
           config = OrchestratorTestConfig()

           assert hasattr(config, 'probe_timeout_seconds')
           assert hasattr(config, 'test_timeout_seconds')
           assert hasattr(config, 'smoke_timeout_seconds')

       def test_fixture_loading_example(
           self,
           test_context_factory,
       ):
           """Example from quickstart should work."""
           # Load a checkpoint
           ctx = test_context_factory("wp_created")

           # Verify it's usable
           assert ctx.feature_dir.exists()
           assert ctx.state_file.exists()
           assert ctx.repo_root.exists()

       def test_validation_example(
           self,
           test_context_factory,
       ):
           """Validation example from quickstart should work."""
           from tests.specify_cli.orchestrator.validation import (
               validate_test_result,
           )

           ctx = test_context_factory("wp_created")
           result = validate_test_result(ctx)

           # Initial state should be valid
           assert result.valid, f"Validation failed: {result.errors}"


   @pytest.mark.orchestrator_availability
   class TestQuickstartTroubleshooting:
       """Tests for troubleshooting scenarios."""

       def test_no_agents_available_message(
           self,
           available_agents,
       ):
           """Should have clear message when no agents available."""
           available_count = sum(
               1 for a in available_agents.values()
               if a.is_available
           )

           if available_count == 0:
               # Verify we have failure reasons
               for agent_id, avail in available_agents.items():
                   if not avail.is_available:
                       assert avail.failure_reason is not None, (
                           f"{agent_id} unavailable but no reason given"
                       )

       def test_agent_detection_reports_all_agents(
           self,
           available_agents,
       ):
           """Detection should report all 12 agents."""
           assert len(available_agents) == 12, (
               f"Expected 12 agents, found {len(available_agents)}"
           )
   ```

**Files**:
- `tests/specify_cli/orchestrator/test_quickstart.py` (~130 lines)

**Parallel?**: No - should be last (validates everything)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Root conftest conflicts | Check for existing markers before adding |
| Subprocess commands fail | Use appropriate timeouts, check both stdout/stderr |
| Config not loaded | Use singleton pattern with lazy initialization |
| Quickstart outdated | Tests will fail if docs don't match reality |

## Review Guidance

**Key Acceptance Checkpoints**:
- [ ] `pytest --markers` shows all orchestrator markers
- [ ] `validate_test_result()` catches state inconsistencies
- [ ] Skip messages are informative (include agent name, reason)
- [ ] Environment variables override defaults correctly
- [ ] All quickstart commands work (or skip gracefully)

**Code Quality**:
- No marker registration warnings
- Validation errors are actionable
- Config is well-documented with defaults
- Quickstart tests match documentation exactly

## Activity Log

- 2026-01-19T09:30:27Z – system – lane=planned – Prompt created.
- 2026-01-19T14:32:17Z – claude-opus – shell_pid=58477 – lane=doing – Started implementation via workflow command
