# Research Specification: Autonomous Multi-Agent Orchestration

**Feature Branch**: `019-autonomous-multi-agent-orchestration-research`
**Created**: 2026-01-18
**Status**: Draft
**Mission**: Research

## Research Objective

Investigate the headless/CLI invocation capabilities of all 12 AI coding agents supported by spec-kitty to determine how they can be programmatically orchestrated for fully autonomous workflow execution.

## Background & Motivation

Spec-kitty currently supports 12 AI coding agents, each with their own slash command directories. The current workflow requires manual intervention at each stage transition (implement → review → implement → etc.).

**The vision**: After `/spec-kitty.tasks` completes, a user runs `/spec-kitty.implement` and walks away. The system autonomously:
1. Assigns WP01 to an implementation agent (e.g., Claude Code)
2. Detects completion and state change to `for_review`
3. Triggers a review agent (e.g., Codex or OpenCode)
4. On review completion, assigns next implementation to another agent
5. Respects WP dependency graph (WP02/WP03/WP04 can run in parallel if independent)
6. Continues until all WPs reach `done` status

## Research Questions *(mandatory)*

### RQ-1: CLI Invocation Capabilities (Priority: P1)

For each of the 12 agents, determine: Can this agent be invoked from a shell script without IDE involvement?

**Why this priority**: Without headless invocation, an agent cannot participate in autonomous orchestration.

**Research Approach**: Examine official documentation, GitHub repos, and npm/pip packages for each agent to identify CLI entry points.

**Deliverables**:
1. **Given** each agent, **Document** the exact CLI command(s) to invoke it
2. **Given** an agent with no CLI, **Document** alternative approaches (API, extension CLI, workarounds)
3. **Given** CLI availability, **Document** required authentication/setup steps

---

### RQ-2: Task Specification Mechanisms (Priority: P1)

For agents with CLI capability, determine: How do you tell the agent what to do?

**Why this priority**: Orchestration requires passing task context (WP prompt files, codebase state) to agents.

**Research Approach**: Test each CLI tool with various input methods (stdin, file paths, arguments, prompt files).

**Deliverables**:
1. **Document** how each agent accepts task instructions (flags, stdin, file path, environment)
2. **Document** whether agents can read markdown prompt files directly
3. **Document** context window limitations and how to provide codebase context

---

### RQ-3: Completion Detection (Priority: P1)

For agents with CLI capability, determine: How do you know when the agent has finished?

**Why this priority**: State transitions require knowing when an agent completes its task.

**Deliverables**:
1. **Document** exit codes and their meanings for each agent
2. **Document** output formats (stdout, files, structured JSON)
3. **Document** how to detect success vs failure vs partial completion

---

### RQ-4: Parallel Execution Constraints (Priority: P2)

Determine: What limits parallel agent execution?

**Why this priority**: Maximizing parallelization accelerates feature delivery.

**Deliverables**:
1. **Document** rate limits for each agent (API quotas, concurrent session limits)
2. **Document** resource requirements (memory, CPU, API tokens)
3. **Document** whether multiple instances can run simultaneously

---

### RQ-5: Agent Configuration & Preferences (Priority: P2)

Determine: How should users specify agent preferences for implementation vs review roles?

**Why this priority**: Users have different subscriptions, preferences, and trust levels for different agents.

**Deliverables**:
1. **Propose** a configuration schema for agent preferences (YAML/JSON in `.kittify/`)
2. **Document** fallback strategies when preferred agent is unavailable
3. **Document** single-agent edge case (same agent does both roles)

---

### RQ-6: Cursor CLI Discovery (Priority: P2)

Specifically investigate Cursor's CLI capabilities, as mentioned by user.

**Why this priority**: Cursor is a popular IDE-based agent; confirming CLI access expands orchestration options.

**Deliverables**:
1. **Find** Cursor's CLI tool (name, installation, documentation link)
2. **Document** how to invoke Cursor from command line
3. **Document** any limitations vs IDE usage

---

## Agents to Research *(mandatory)*

The following 12 agents must be investigated:

| # | Agent | Directory | Primary Interface | CLI Status (to determine) |
|---|-------|-----------|-------------------|---------------------------|
| 1 | Claude Code | `.claude/` | CLI (Anthropic) | Known CLI exists |
| 2 | GitHub Copilot | `.github/` | VS Code extension | TBD |
| 3 | Google Gemini | `.gemini/` | API / CLI | TBD |
| 4 | Cursor | `.cursor/` | IDE | TBD (user reports CLI exists) |
| 5 | Qwen Code | `.qwen/` | API | TBD |
| 6 | OpenCode | `.opencode/` | CLI | Known CLI exists |
| 7 | Windsurf | `.windsurf/` | IDE (Codeium) | TBD |
| 8 | GitHub Codex | `.codex/` | CLI (OpenAI) | Known CLI exists |
| 9 | Kilocode | `.kilocode/` | VS Code extension | TBD |
| 10 | Augment Code | `.augment/` | IDE extension | TBD |
| 11 | Roo Cline | `.roo/` | VS Code extension | TBD |
| 12 | Amazon Q | `.amazonq/` | CLI (AWS) | Known CLI exists |

## Key Entities

- **Agent**: An AI coding assistant that can perform implementation or review tasks
- **Agent Profile**: Configuration for a specific agent including CLI command, auth method, rate limits
- **Orchestrator**: The spec-kitty component that manages agent invocation and state transitions
- **WP State Machine**: Existing spec-kitty states (planned → doing → for_review → done)
- **Agent Preference Config**: User settings specifying which agents to use for which roles

## Success Criteria *(mandatory)*

### Research Deliverables

- **SC-001**: Complete CLI capability matrix for all 12 agents documenting invocation method or "not available"
- **SC-002**: Working example invocation command for each agent with CLI support
- **SC-003**: Documented task specification method for each CLI-capable agent
- **SC-004**: Completion detection strategy documented for each CLI-capable agent
- **SC-005**: Proposed agent preference configuration schema
- **SC-006**: Feasibility assessment: which agents can participate in autonomous orchestration
- **SC-007**: Architecture recommendation for orchestrator implementation

### Quality Gates

- **QG-001**: At least 6 of 12 agents have documented CLI invocation paths
- **QG-002**: Cursor CLI specifically documented (per user request)
- **QG-003**: All research findings include source links (documentation URLs)
- **QG-004**: Parallel execution constraints documented for CLI-capable agents

## Out of Scope

- Implementing the orchestrator (this is research only)
- Performance benchmarking of agents
- Code quality comparison between agents
- Cost analysis of different agents
- IDE integration or GUI workflows

## Assumptions

- CLI tools may require authentication tokens or API keys (user responsibility to configure)
- Some agents may have CLI tools in beta or preview status
- Agent capabilities may have changed since knowledge cutoff; live documentation research required
- Rate limits and quotas vary by subscription tier

## Risks

- Some popular agents (Cursor, Copilot) may be IDE-only with no scriptable interface
- CLI tools may exist but be undocumented or unofficial
- Agent APIs may change, requiring research updates
