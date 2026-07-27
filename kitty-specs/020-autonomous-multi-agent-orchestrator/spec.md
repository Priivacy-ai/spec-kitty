# Feature Specification: Autonomous Multi-Agent Orchestrator

**Feature Branch**: `020-autonomous-multi-agent-orchestrator`
**Created**: 2026-01-18
**Status**: Draft
**Input**: Build orchestrator for autonomous feature execution with parallel WP processing and 9 CLI-capable agents

## Overview

The Autonomous Multi-Agent Orchestrator enables spec-kitty to execute complete features without human intervention. Given a feature with defined work packages and dependencies, the orchestrator assigns WPs to AI agents, executes them in parallel where dependencies allow, uses different agents for implementation vs. review, and handles failures gracefully.

**Research Foundation**: This feature builds on the findings from feature 019 (Autonomous Multi-Agent Orchestration Research), which validated that 9 of 12 AI coding agents have CLI capabilities suitable for autonomous orchestration.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Autonomous Feature Execution (Priority: P1)

A developer has completed planning for a feature (spec, plan, tasks all defined with WP dependencies). They want to execute the entire feature autonomously while they focus on other work.

**Why this priority**: This is the core value proposition - freeing developers from manual WP-by-WP execution.

**Independent Test**: Can be tested by running orchestrator on a prepared feature with 3+ WPs and verifying all WPs complete with commits.

**Acceptance Scenarios**:

1. **Given** a feature with 5 WPs where WP01-WP03 are independent and WP04-WP05 depend on earlier WPs, **When** the user runs the orchestrate command, **Then** WP01-WP03 execute in parallel, WP04 starts when its dependencies complete, and WP05 starts when its dependencies complete.

2. **Given** a feature with all WPs in "planned" lane, **When** orchestration completes successfully, **Then** all WPs are in "done" lane with commits in their worktrees.

3. **Given** an orchestration in progress, **When** the user checks status, **Then** they see which WPs are running, which are complete, and which are pending.

---

### User Story 2 - Cross-Agent Review (Priority: P1)

A developer wants implementation and review done by different AI agents to catch blind spots that a single agent might miss.

**Why this priority**: Different agents using different models provide genuine code review value, not just self-review.

**Independent Test**: Can be tested by configuring two agents and verifying the review agent is different from the implementation agent for each WP.

**Acceptance Scenarios**:

1. **Given** user configures Claude Code for implementation and GitHub Codex for review, **When** a WP is implemented by Claude Code, **Then** the review is performed by GitHub Codex.

2. **Given** user has only one agent configured, **When** orchestration runs, **Then** the same agent performs both implementation and review (single-agent mode) with a configurable delay between phases.

---

### User Story 3 - Failure Recovery (Priority: P2)

An agent fails during execution (rate limit, network error, authentication failure). The orchestrator should handle this gracefully without losing progress.

**Why this priority**: Real-world reliability requires handling failures without manual intervention.

**Independent Test**: Can be tested by simulating agent failure and verifying fallback behavior.

**Acceptance Scenarios**:

1. **Given** preferred agent fails with rate limit error, **When** fallback strategy is "next_in_list", **Then** the next agent in the configured list attempts the task.

2. **Given** all agents fail for a WP, **When** max retries exceeded, **Then** orchestration pauses and alerts the user for manual intervention.

3. **Given** orchestration is interrupted (Ctrl+C, system restart), **When** user runs orchestrate with --resume, **Then** orchestration continues from where it stopped.

---

### User Story 4 - Agent Configuration (Priority: P2)

A developer wants to configure which agents are available, their roles (implementation/review), and priority order.

**Why this priority**: Users have different subscriptions and preferences; configuration must be flexible.

**Independent Test**: Can be tested by creating a config file and verifying orchestrator respects the settings.

**Acceptance Scenarios**:

1. **Given** user creates agents.yaml with specific agent order, **When** orchestration runs, **Then** agents are selected according to configured priority.

2. **Given** user disables an agent in config, **When** orchestration runs, **Then** that agent is never used even if it's installed.

3. **Given** no agents.yaml exists, **When** orchestration runs, **Then** sensible defaults are used based on installed agents.

---

### User Story 5 - Progress Visibility (Priority: P3)

A developer wants to monitor orchestration progress without interrupting execution.

**Why this priority**: Long-running autonomous operations need observability.

**Independent Test**: Can be tested by running orchestration and checking status output.

**Acceptance Scenarios**:

1. **Given** orchestration is running, **When** user runs status command, **Then** they see: active WPs, completed WPs, pending WPs, current agent assignments, and elapsed time.

2. **Given** orchestration completes, **When** user views summary, **Then** they see: total time, WPs completed, agents used, and any errors encountered.

---

### Edge Cases

- What happens when a WP has circular dependencies? (Detected and rejected before orchestration starts)
- What happens when an agent produces invalid output? (Retry with same agent, then fallback)
- What happens when worktree creation fails? (Abort that WP, continue others if independent)
- What happens when git operations fail in a worktree? (Retry, then fail WP with clear error)
- What happens when user has no compatible agents installed? (Clear error message with installation instructions)

## Requirements *(mandatory)*

### Functional Requirements

**Core Orchestration**

- **FR-001**: System MUST read WP dependency graph from task file frontmatter
- **FR-002**: System MUST execute independent WPs in parallel up to a configurable concurrency limit
- **FR-003**: System MUST wait for WP dependencies to complete before starting dependent WPs
- **FR-004**: System MUST assign different agents for implementation vs. review phases when multiple agents are configured
- **FR-005**: System MUST detect WP completion via agent exit codes and output parsing

**Agent Management**

- **FR-006**: System MUST support all 9 CLI-capable agents: Claude Code, GitHub Codex, GitHub Copilot, Google Gemini, Qwen Code, OpenCode, Kilocode, Augment Code, and Cursor
- **FR-007**: System MUST apply timeout wrapper for Cursor agent (Tier-2 workaround)
- **FR-008**: System MUST detect which agents are installed and available
- **FR-009**: System MUST respect agent-specific invocation patterns (different CLI flags per agent)

**State Management**

- **FR-010**: System MUST persist orchestration state to enable resume after interruption
- **FR-011**: System MUST track per-WP status: pending, running, completed, failed
- **FR-012**: System MUST track per-agent health: consecutive failures, last success time

**Failure Handling**

- **FR-013**: System MUST implement fallback strategies: next_in_list, same_agent, fail
- **FR-014**: System MUST retry failed WPs up to a configurable limit before failing
- **FR-015**: System MUST escalate to user when all agents fail for a WP

**Configuration**

- **FR-016**: System MUST read agent configuration from `.kittify/agents.yaml`
- **FR-017**: System MUST support single-agent mode when only one agent is configured
- **FR-018**: System MUST use sensible defaults when no configuration exists

**Integration**

- **FR-019**: System MUST create worktrees for each WP using existing spec-kitty workspace-per-WP model
- **FR-020**: System MUST update WP lane status via existing spec-kitty commands
- **FR-021**: System MUST mark subtasks as done when WP completes

### Key Entities

- **OrchestrationRun**: A single execution of the orchestrator for a feature. Tracks start time, status, WP assignments, and completion state.

- **AgentProfile**: Configuration for a single agent. Includes CLI command, installation status, supported roles, priority, and health metrics.

- **WPExecution**: Tracks a single WP's execution. Includes assigned agent, start time, status, output logs, and retry count.

- **FallbackStrategy**: Defines behavior when an agent fails. Options: next_in_list (try next agent), same_agent (retry same), fail (stop immediately).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Features with 5+ independent WPs complete at least 40% faster than sequential execution
- **SC-002**: Cross-agent review catches issues that same-agent review misses in at least 20% of cases
- **SC-003**: Orchestrator successfully resumes interrupted runs in 100% of cases
- **SC-004**: Users can configure and run orchestration with less than 5 minutes of setup
- **SC-005**: Orchestration status is visible within 2 seconds of status command
- **SC-006**: Failed WPs are correctly identified and reported in 100% of cases
- **SC-007**: All 9 supported agents can be used for orchestration when installed

## Assumptions

- Users have at least one of the 9 supported agents installed with valid authentication
- Features have been fully planned (spec, plan, tasks) before orchestration starts
- WP dependencies are correctly declared in frontmatter (no undeclared dependencies)
- Network connectivity is available for cloud-based agents
- Git is available and configured for worktree operations

## Dependencies

- Feature 019 research findings (data-model.md, sample-agents.yaml)
- Existing spec-kitty workspace-per-WP infrastructure
- Existing spec-kitty lane management commands
- Agent CLIs installed by users (not bundled with spec-kitty)

## Out of Scope

- Rate limit tracking and quota management (deferred to future enhancement)
- Token usage and cost tracking
- Automatic agent installation
- MCP server integration
- Streaming output progress display
- Web-based dashboard for monitoring
