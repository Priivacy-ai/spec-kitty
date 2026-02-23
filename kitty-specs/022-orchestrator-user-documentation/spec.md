# Feature Specification: Orchestrator User Documentation

**Feature Branch**: `022-orchestrator-user-documentation`
**Created**: 2026-01-19
**Status**: Draft
**Input**: Documentation sprint for orchestrator features 020 and 021 using full Divio method

## Overview

This feature creates comprehensive user-facing documentation for the Autonomous Multi-Agent Orchestrator (feature 020) and its testing suite (feature 021). Documentation follows the Divio method (Tutorial, How-To, Reference, Explanation) and matches the existing docs/ style.

**Scope**: User-facing documentation only. Developer/contributor documentation is out of scope.

**Key documentation areas**:
- The `spec-kitty orchestrate` command and its workflow
- Agent configuration during `spec-kitty init`
- The implement→review→rework state machine
- Agent selection strategies (preferred vs random)
- CLI override options for agent selection
- Monitoring, resuming, and aborting orchestration

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learn Autonomous Orchestration (Priority: P1)

A new Spec Kitty user wants to understand what autonomous orchestration is and how to use it for their first feature.

**Why this priority**: New users need a guided path to successfully run their first autonomous orchestration.

**Independent Test**: A reader with no prior orchestration knowledge can follow the tutorial and successfully run autonomous orchestration on a sample feature.

**Acceptance Scenarios**:

1. **Given** a user reads the Autonomous Orchestration Tutorial, **When** they follow all steps, **Then** they can run `spec-kitty orchestrate --feature <slug>` and see WPs complete automatically.

2. **Given** a user completes the tutorial, **When** they check the dashboard, **Then** they understand which WPs are in progress, complete, or failed.

---

### User Story 2 - Configure Orchestration Agents (Priority: P1)

A user wants to configure which AI agents are used for implementation vs review during orchestration.

**Why this priority**: Agent configuration is essential for cross-agent review, the core value proposition.

**Independent Test**: A reader can follow the how-to guide to configure agent selection strategy during init and verify it works.

**Acceptance Scenarios**:

1. **Given** a user reads the agent configuration how-to, **When** they run `spec-kitty init`, **Then** they understand the "preferred" vs "random" strategy options.

2. **Given** a user has configured preferred agents, **When** they run orchestration, **Then** the configured agents are used as expected.

---

### User Story 3 - Monitor and Control Orchestration (Priority: P1)

A user wants to check orchestration status, resume after failure, or abort a stuck orchestration.

**Why this priority**: Users need control over long-running autonomous processes.

**Independent Test**: A reader can use --status, --resume, and --abort options correctly after reading the how-to guides.

**Acceptance Scenarios**:

1. **Given** an orchestration is running, **When** the user runs `spec-kitty orchestrate --status`, **Then** they see active WPs, progress, and elapsed time.

2. **Given** an orchestration paused due to failure, **When** the user runs `spec-kitty orchestrate --resume`, **Then** orchestration continues from where it stopped.

3. **Given** a user wants to stop orchestration, **When** they run `spec-kitty orchestrate --abort`, **Then** orchestration stops and they can optionally clean up worktrees.

---

### User Story 4 - Override Agent Selection (Priority: P2)

A user wants to override the configured agent selection for a specific orchestration run.

**Why this priority**: Flexibility for testing or preference changes without modifying config.

**Independent Test**: A reader can use --impl-agent and --review-agent flags correctly.

**Acceptance Scenarios**:

1. **Given** a user wants to use a specific agent, **When** they run `spec-kitty orchestrate --feature <slug> --impl-agent claude`, **Then** Claude is used for all implementations regardless of config.

2. **Given** a user wants different implementation and review agents, **When** they use both `--impl-agent` and `--review-agent` flags, **Then** the specified agents are used.

---

### User Story 5 - Understand the Orchestration Architecture (Priority: P2)

A user wants to understand how the orchestrator works internally: the state machine, agent selection, and review cycles.

**Why this priority**: Understanding the architecture helps users debug issues and make informed configuration choices.

**Independent Test**: A reader can explain the implement→review→rework cycle and why cross-agent review provides value.

**Acceptance Scenarios**:

1. **Given** a user reads the architecture explanation, **When** they encounter a WP in "rework" status, **Then** they understand it was rejected by review and is being re-implemented.

2. **Given** a user reads about agent selection, **When** they configure agents, **Then** they understand why cross-agent review (different agent for implementation vs review) is recommended.

---

## Functional Requirements *(mandatory)*

### Documentation Deliverables

#### Tutorials (Learning-oriented)

| ID | Document | Description |
|----|----------|-------------|
| T1 | `tutorials/autonomous-orchestration.md` | Step-by-step guide to run first autonomous orchestration |

**T1 Content Requirements**:
- Time estimate and prerequisites
- Step 1: Prepare a feature with tasks (link to existing tutorials)
- Step 2: Configure agents during init (or use existing config)
- Step 3: Run `spec-kitty orchestrate --feature <slug>`
- Step 4: Monitor progress with --status
- Step 5: Handle completion or failure
- Expected output at each step
- Cross-references to how-to guides for deeper topics

#### How-To Guides (Task-oriented)

| ID | Document | Description |
|----|----------|-------------|
| H1 | `how-to/run-autonomous-orchestration.md` | Quick guide to start orchestration |
| H2 | `how-to/configure-orchestration-agents.md` | Configure agent selection strategy |
| H3 | `how-to/monitor-orchestration.md` | Check status and track progress |
| H4 | `how-to/resume-failed-orchestration.md` | Resume after failure or interruption |
| H5 | `how-to/override-orchestration-agents.md` | Use CLI flags to override agents |

**H1-H5 Content Requirements**:
- Prerequisites section
- Numbered steps with code examples
- "What happens" section explaining the outcome
- Cross-references to related guides

#### Reference (Information-oriented)

| ID | Document | Description |
|----|----------|-------------|
| R1 | Update `reference/cli-commands.md` | Add `spec-kitty orchestrate` command |
| R2 | Update `reference/configuration.md` | Add agents section to config.yaml |
| R3 | `reference/orchestration-state.md` | State file structure reference |

**R1 Content Requirements**:
- Synopsis, description, arguments
- Options table with all flags (--feature, --status, --resume, --abort, --skip, --cleanup, --impl-agent, --review-agent)
- Examples section

**R2 Content Requirements**:
- agents.available list
- agents.selection.strategy (preferred/random)
- agents.selection.implementer_agent
- agents.selection.reviewer_agent

**R3 Content Requirements**:
- State file location (`.kittify/orchestration-state.json`)
- JSON schema with field descriptions
- WP status values and meanings

#### Explanations (Understanding-oriented)

| ID | Document | Description |
|----|----------|-------------|
| E1 | `explanation/autonomous-orchestration.md` | How the orchestrator works |
| E2 | Update `explanation/multi-agent-orchestration.md` | Add autonomous orchestration section |

**E1 Content Requirements**:
- Overview of autonomous orchestration concept
- The implement→review→rework state machine diagram (ASCII or description)
- Why cross-agent review matters
- Agent selection strategies explained
- Concurrency and parallel execution
- Failure handling and recovery
- Relationship to manual orchestration

#### Navigation Updates

| ID | Change | Description |
|----|--------|-------------|
| N1 | Update `toc.yml` | Add new documents to navigation |

### Style Requirements

All documentation must:
- Follow existing docs/ style conventions
- Include `**Divio type**: <type>` header for tutorials
- Use `---` frontmatter with title/description for explanations
- Include code blocks with expected output
- Cross-reference related documents
- Use consistent terminology (WP, worktree, lane, etc.)

---

## Success Criteria *(mandatory)*

| Criterion | Measure |
|-----------|---------|
| Tutorial completeness | A new user can follow the tutorial and successfully run autonomous orchestration without additional help |
| How-to coverage | All common orchestration tasks have dedicated how-to guides |
| Reference accuracy | CLI reference matches actual `--help` output; config reference matches actual config schema |
| Navigation | All new documents appear in toc.yml and are accessible from the docs site |
| Style consistency | All documents pass style review (Divio headers, code blocks, cross-references) |

---

## Assumptions

- The orchestrator implementation (feature 020) is complete and stable
- The `spec-kitty orchestrate` command is available in the CLI
- Agent configuration via `spec-kitty init` is implemented
- Documentation will be served via the existing DocFX site

---

## Dependencies

- Feature 020 (Autonomous Multi-Agent Orchestrator) - must be complete
- Feature 021 (Orchestrator E2E Testing) - provides validation that documented features work

---

## Out of Scope

- Developer/contributor documentation (code architecture, API internals)
- Testing infrastructure documentation (feature 021 specifics)
- Video tutorials or interactive demos
- Translations
