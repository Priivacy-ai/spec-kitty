# Feature Specification: Orchestrator End-to-End Testing Suite

**Feature Branch**: `021-orchestrator-end-to-end-testing-suite`
**Created**: 2026-01-19
**Status**: Draft
**Input**: Comprehensive end-to-end testing for the orchestrator (feature 020) covering all agents with tiered coverage

## Clarifications

### Session 2026-01-19

- Q: Should tests deliberately trigger retry/fallback logic, or only test when real failures occur? → A: Remove retry/fallback testing from scope; only test with real failures that occur naturally.

## Overview

This feature provides a comprehensive end-to-end testing infrastructure for the Autonomous Multi-Agent Orchestrator (feature 020). The testing suite validates that the orchestrator correctly executes work packages across multiple AI agents and maintains state through complex multi-turn workflows.

**Key design decisions**:
- **Tiered agent coverage**: Core agents (Claude Code, Codex, Copilot, Gemini, OpenCode) get full integration tests; extended agents get smoke tests
- **Real agent execution**: Tests call actual agent CLIs, not mocks, to validate true end-to-end behavior
- **Checkpoint-based fixtures**: Pre-created snapshots at known states enable faster test execution while maintaining realism
- **Tiered failure handling**: Core agent unavailability fails tests; extended agent unavailability skips gracefully

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Happy Path Orchestration Test (Priority: P1)

A test developer wants to verify that the orchestrator can execute a simple feature end-to-end: implement a WP, review it, and mark it complete.

**Why this priority**: The happy path is the foundation - if basic orchestration doesn't work, nothing else matters.

**Independent Test**: Can be tested by running a single-WP feature through orchestration and verifying the WP reaches "done" lane with commits.

**Acceptance Scenarios**:

1. **Given** a fixture feature with one independent WP and a core agent available, **When** the orchestration test runs, **Then** the WP is implemented, reviewed, and marked done.

2. **Given** a fixture feature with three independent WPs, **When** the orchestration test runs, **Then** all three WPs execute in parallel (up to concurrency limit) and complete successfully.

3. **Given** orchestration completes, **When** the test validates results, **Then** each WP has commits in its worktree and correct lane status.

---

### User Story 2 - Agent Availability Detection (Priority: P1)

A test developer wants tests to behave correctly based on which agents are installed and authenticated on the test machine.

**Why this priority**: Tests must run reliably across different environments; proper skip/fail behavior prevents false positives and debugging headaches.

**Independent Test**: Can be tested by mocking agent detection and verifying correct skip/fail behavior.

**Acceptance Scenarios**:

1. **Given** Claude Code is not installed, **When** a test requiring Claude Code runs, **Then** the test fails with a clear error message about the missing agent.

2. **Given** Cursor is not installed (extended tier), **When** a smoke test for Cursor runs, **Then** the test is skipped with a warning, not failed.

3. **Given** all core agents are available, **When** the full integration suite runs, **Then** no tests are skipped due to agent availability.

4. **Given** agent detection runs, **When** an agent is installed but not authenticated, **Then** the detection reports the agent as unavailable with auth failure reason.

---

### User Story 3 - Review Cycle Testing (Priority: P1)

A test developer wants to verify the orchestrator handles review rejection and re-implementation cycles correctly.

**Why this priority**: Review cycles are the core value of cross-agent review; bugs here would undermine the orchestrator's purpose.

**Independent Test**: Can be tested with a fixture that triggers review rejection and verifying the re-implementation flow.

**Acceptance Scenarios**:

1. **Given** a WP implementation that fails review, **When** orchestration processes the review result, **Then** the WP is sent back for re-implementation.

2. **Given** a WP goes through rejection -> re-implement -> re-review -> approve, **When** the test validates state, **Then** the state file shows correct transition history.

3. **Given** max review cycles exceeded, **When** orchestration continues, **Then** the WP is marked as failed and user is alerted.

---

### User Story 4 - Fixture Snapshot Management (Priority: P2)

A test developer wants to create and use checkpoint snapshots to speed up test execution without sacrificing realism.

**Why this priority**: Full end-to-end tests are slow; snapshots enable fast iteration while testing specific scenarios.

**Independent Test**: Can be tested by creating a snapshot, restoring it, and verifying the restored state matches the original.

**Acceptance Scenarios**:

1. **Given** an orchestration run reaches "WP implemented, awaiting review" state, **When** the snapshot tool runs, **Then** a checkpoint is created that can restore this exact state.

2. **Given** a checkpoint snapshot exists, **When** a test loads the snapshot, **Then** the test starts from that checkpoint state, not from scratch.

3. **Given** multiple checkpoints exist for different states, **When** a test selects a checkpoint, **Then** only the relevant state is loaded.

4. **Given** the orchestrator code changes, **When** snapshots become invalid, **Then** the fixture tooling detects and reports stale snapshots.

---

### User Story 5 - Parallel Execution and Dependency Testing (Priority: P2)

A test developer wants to verify the orchestrator respects WP dependencies and executes independent WPs in parallel.

**Why this priority**: Parallel execution is a key performance feature; dependency bugs could cause race conditions or incorrect ordering.

**Independent Test**: Can be tested with a fixture having specific dependency patterns and verifying execution order.

**Acceptance Scenarios**:

1. **Given** WP01, WP02, WP03 are independent, **When** orchestration runs with concurrency=3, **Then** all three start simultaneously.

2. **Given** WP04 depends on WP01 and WP02, **When** WP01 completes but WP02 is running, **Then** WP04 does not start until WP02 completes.

3. **Given** circular dependencies in fixture, **When** orchestration attempts to start, **Then** orchestration fails with clear circular dependency error before any WP execution.

4. **Given** diamond dependency pattern (WP04 depends on WP02 and WP03, both depend on WP01), **When** orchestration runs, **Then** execution order is correct and WP04 starts only after both WP02 and WP03 complete.

---

### User Story 6 - Extended Agent Smoke Tests (Priority: P3)

A test developer wants basic validation that extended-tier agents (Cursor, Qwen, Augment, Kilocode, Roo, Windsurf, Amazon Q) can be invoked by the orchestrator.

**Why this priority**: Full integration tests for all agents would be prohibitively slow; smoke tests provide confidence without excessive runtime.

**Independent Test**: Can be tested by invoking each extended agent with a minimal task and verifying basic response.

**Acceptance Scenarios**:

1. **Given** an extended agent is installed, **When** smoke test runs, **Then** the agent successfully receives and acknowledges a minimal task.

2. **Given** an extended agent is not installed, **When** smoke test runs, **Then** the test is skipped with informative message.

3. **Given** all extended agents are available, **When** smoke test suite runs, **Then** each agent completes its minimal task.

---

### Edge Cases

- What happens when a fixture snapshot references agents that aren't installed? (Test skips with clear message about missing dependencies)
- What happens when checkpoint restoration fails mid-way? (Cleanup partial state and report which step failed)
- What happens when two tests try to use the same fixture concurrently? (Fixture isolation via unique directories or locking)
- What happens when agent output is malformed? (Parse error is captured, WP marked as needing retry)
- What happens when git operations fail during fixture setup? (Clear error with git state, fixture marked as corrupt)
- What happens when test timeout expires during long agent execution? (Agent process killed, test fails with timeout indicator)

## Requirements *(mandatory)*

### Functional Requirements

**Agent Availability Detection**

- **FR-001**: System MUST detect installation status of all 12 supported agents
- **FR-002**: System MUST verify authentication status for detected agents
- **FR-003**: System MUST categorize agents into core tier (Claude Code, Codex, Copilot, Gemini, OpenCode) and extended tier (remaining 7 agents)
- **FR-004**: System MUST fail tests when core tier agents are unavailable
- **FR-005**: System MUST skip tests with warning when extended tier agents are unavailable

**Fixture Management**

- **FR-006**: System MUST provide tooling to create checkpoint snapshots at defined orchestration states
- **FR-007**: System MUST support snapshots for: "WP created", "WP implemented", "review pending", "review rejected", "review approved", "WP merged"
- **FR-008**: System MUST restore snapshots to exact state including git worktrees, lane status, and state files
- **FR-009**: System MUST detect and report stale snapshots when orchestrator code changes
- **FR-010**: System MUST isolate fixtures to prevent test interference

**Core Integration Tests**

- **FR-011**: System MUST test happy path: implement -> review -> done
- **FR-012**: System MUST test review cycles: implement -> review-reject -> re-implement -> review-approve -> done
- **FR-013**: System MUST test parallel execution with configurable concurrency
- **FR-014**: System MUST test dependency ordering with various graph patterns (linear, fan-out, diamond)

**Extended Agent Smoke Tests**

- **FR-015**: System MUST test basic invocation for each extended agent
- **FR-016**: System MUST verify agent receives task and produces some output
- **FR-017**: System MUST complete smoke tests in under 60 seconds per agent

**Test Organization**

- **FR-018**: System MUST organize tests by category: availability, fixtures, integration, smoke
- **FR-019**: System MUST support running specific test categories via pytest markers
- **FR-020**: System MUST provide clear test output distinguishing skips, failures, and passes
- **FR-021**: System MUST support parallel test execution where fixtures allow

**State Validation**

- **FR-022**: System MUST validate orchestration state file integrity after each test
- **FR-023**: System MUST verify WP lane transitions are recorded correctly
- **FR-024**: System MUST validate git state (commits, branches) matches expected post-orchestration state

### Key Entities

- **AgentAvailability**: Detection result for a single agent. Includes: agent_id, is_installed, is_authenticated, tier (core/extended), and failure_reason if unavailable.

- **FixtureCheckpoint**: A snapshot of orchestration state at a known point. Includes: checkpoint_name, orchestration_state, git_state (branches, commits), created_at, and orchestrator_version.

- **TestCategory**: Classification of tests. Values: availability, fixture_management, integration_happy_path, integration_review_cycles, integration_parallel, smoke_extended.

- **TestResult**: Outcome of a single test. Includes: test_name, category, status (passed/failed/skipped), duration, skip_reason if skipped, failure_details if failed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Full integration test suite for core agents completes in under 30 minutes
- **SC-002**: Smoke test suite for extended agents completes in under 10 minutes (when all agents available)
- **SC-003**: Fixture snapshots reduce test startup time by at least 70% compared to fresh setup
- **SC-004**: Test suite correctly identifies orchestrator bugs with zero false positives over 10 consecutive runs
- **SC-005**: All 5 core agents have full integration test coverage
- **SC-006**: All 7 extended agents have smoke test coverage
- **SC-007**: Test results clearly distinguish between "agent unavailable" skips and actual test failures
- **SC-008**: Developers can run tests locally with 2 or more core agents installed

## Assumptions

- At least 2 core agents are installed for meaningful local test runs
- Test machine has sufficient resources to run agent processes concurrently
- Git is available and properly configured
- Network connectivity is available for cloud-based agents during test runs
- Orchestrator (feature 020) is fully implemented and merged
- pytest is the test framework (already used in spec-kitty)

## Dependencies

- Feature 020: Autonomous Multi-Agent Orchestrator (must be complete and merged)
- Existing spec-kitty test infrastructure (pytest, fixtures)
- Existing agent invoker implementations from feature 020
- Git worktree functionality for fixture state management

## Out of Scope

- Mocked agent tests (this feature explicitly uses real agents)
- CI/CD configuration (tests designed for local execution)
- Performance benchmarking beyond basic timing
- Agent-specific bug testing (focus is on orchestrator, not individual agents)
- Cost/token tracking during tests
- Test coverage reporting integration
- Deliberate retry/fallback testing (retry/fallback paths tested only when real failures occur naturally)
