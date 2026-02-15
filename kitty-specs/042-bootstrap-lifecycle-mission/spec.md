# Feature Specification: Bootstrap Lifecycle Mission

**Feature Branch**: `042-bootstrap-lifecycle-mission`
**Created**: 2026-02-15
**Status**: Draft
**Input**: Add a post-init bootstrap command that captures project vision, target audience, agent profiles, and constitution through a hybrid CLI/AI-agent interview flow — establishing project-level context before any feature work begins.

## Overview

After `spec-kitty init` scaffolds the project structure (directories, git, agent assets), there is currently no guided flow to capture **why** the project exists, **who** it serves, or **how** agents should behave. The constitution (`/spec-kitty.constitution`) exists but is disconnected from vision and agent profile setup.

This feature introduces `spec-kitty bootstrap` — a four-phase hybrid command that:

1. **Vision** (required) — captures project purpose, desired outcomes, and scope boundaries using purpose-first framing → `.kittify/memory/vision.md`
2. **Target Audience** (optional, skippable) — identifies stakeholders and user personas → stored in vision.md or constitution
3. **Agent Profiles** (optional, skippable) — selects behavioral patterns, approaches, and tactics from an available repository → stored in constitution agent profile section
4. **Constitution** (optional, skippable) — establishes technical standards, quality gates, and governance rules → `.kittify/memory/constitution.md`

The CLI collects basic inputs (project name, skip flags) and then delegates deeper interview phases to the AI agent. Each phase except vision is independently skippable — the user can accept defaults and proceed.

Bootstrap produces the project-level context that all downstream commands reference. The `/spec-kitty.specify` command soft-blocks without a vision document: it warns and offers to run bootstrap first, but allows proceeding with `--no-bootstrap`.

### Design Decisions

- **Purpose-first framing**: The vision interview asks "what do you want to achieve?" before "what problem are you solving?" — because not all repositories solve a problem (some are creative, educational, or exploratory).
- **Hybrid execution**: CLI handles scaffolding, flags, and phase selection; AI agent conducts the actual interviews. This avoids requiring an AI agent for basic setup while leveraging AI for nuanced question-asking.
- **Separate from init**: `spec-kitty init` remains unchanged (scaffolding + tool selection). Bootstrap is a follow-up command, not a replacement.
- **Constitution subsumption**: The existing `/spec-kitty.constitution` slash command becomes a phase within bootstrap. It remains available standalone for projects that skip bootstrap or need to update their constitution later.

**2.x baseline**: `spec-kitty init` (scaffolds dirs, agents, git), `/spec-kitty.constitution` (AI-driven constitution interview), `.kittify/memory/` (constitution storage), `src/specify_cli/cli/commands/init.py` (init implementation).

## User Scenarios & Testing

### User Story 1 — Complete Bootstrap Flow (Priority: P1)

As a new project owner, after running `spec-kitty init`, I want to run `spec-kitty bootstrap` which guides me through vision capture, audience identification, agent profile selection, and constitution establishment, so that all downstream spec-kitty commands have full project context.

**Why this priority**: The complete bootstrap flow is the core value proposition — it transforms disconnected setup steps into a coherent onboarding experience.

**Independent Test**: Run `spec-kitty init` on a fresh project, then `spec-kitty bootstrap`. Complete all four phases. Verify that `vision.md` and `constitution.md` are created in `.kittify/memory/`, agent profiles are configured, and a commit is created with all bootstrap artifacts.

#### Functional Requirements

- **FR-1.1**: `spec-kitty bootstrap` SHALL be a CLI command (Typer) that accepts `--skip-audience`, `--skip-agents`, `--skip-constitution` flags to skip optional phases.
- **FR-1.2**: The command SHALL validate that `spec-kitty init` has been run (`.kittify/` directory exists) before proceeding.
- **FR-1.3**: The command SHALL detect whether bootstrap has already been run (presence of `vision.md`) and offer to re-run or update.
- **FR-1.4**: The command SHALL proceed through phases in order: Vision → Audience → Agent Profiles → Constitution.
- **FR-1.5**: After all phases complete (or are skipped), the command SHALL commit all generated artifacts to the current branch with a descriptive commit message.
- **FR-1.6**: The command SHALL display a summary of what was created/configured after completion.
- **FR-1.7**: The command SHALL support `--non-interactive` mode that accepts all defaults and creates minimal artifacts (vision placeholder + default constitution).

### User Story 2 — Vision Capture Phase (Priority: P1)

As a project owner, I want the bootstrap flow to interview me about my project's purpose, desired outcomes, and scope boundaries using purpose-first framing, so that a structured vision document is created that provides context for all subsequent feature specifications.

**Why this priority**: Vision is the only required phase — it's the foundation that all other phases and downstream commands reference.

**Independent Test**: Run bootstrap, complete only the vision phase (skip all others). Verify `vision.md` contains structured sections for purpose, desired outcomes, scope boundaries, and success criteria. Verify the document is human-readable and agent-parseable.

#### Functional Requirements

- **FR-2.1**: The vision phase SHALL use purpose-first framing: the first question asks about desired outcomes/purpose, not about problems being solved.
- **FR-2.2**: The AI agent SHALL conduct the vision interview with 3-5 questions covering: purpose/intent, desired outcomes, scope boundaries, success criteria, and project type (product, library, research, educational, creative).
- **FR-2.3**: The vision document SHALL be generated at `.kittify/memory/vision.md` with structured Markdown sections.
- **FR-2.4**: The vision document SHALL include a YAML frontmatter block with machine-parseable metadata: `project_name`, `project_type`, `created_at`, `bootstrap_version`.
- **FR-2.5**: The vision phase SHALL NOT be skippable — it is the minimum required output of bootstrap.
- **FR-2.6**: If the user provides minimal answers, the AI agent SHALL synthesize a reasonable vision document and ask for confirmation before writing.
- **FR-2.7**: The vision document SHALL be referenced by `/spec-kitty.specify` to provide project context during feature specification interviews.

### User Story 3 — Target Audience Phase (Priority: P2)

As a project owner, I want to identify who my project serves — end users, developers, operators — so that feature specifications and design decisions consider the right stakeholder perspectives.

**Why this priority**: Audience context improves specification quality but is not strictly required for spec-kitty to function.

**Independent Test**: Run bootstrap, complete vision and audience phases. Verify audience information is stored (either in vision.md or constitution.md). Skip audience phase. Verify bootstrap completes successfully without audience data.

#### Functional Requirements

- **FR-3.1**: The audience phase SHALL ask 2-3 questions about primary users, secondary stakeholders, and their key needs.
- **FR-3.2**: Audience information SHALL be stored as a structured section in `vision.md` (under "Target Audience") or as a standalone section if the document structure warrants it.
- **FR-3.3**: The audience phase SHALL be skippable with `--skip-audience` flag.
- **FR-3.4**: When skipped, the system SHALL note "Target audience: not specified" in the vision document metadata.
- **FR-3.5**: Audience data SHALL be available to `/spec-kitty.specify` and `/spec-kitty.design` (Feature 041) for context-aware interviews.

### User Story 4 — Agent Profile Configuration Phase (Priority: P2)

As a project owner, I want to select behavioral patterns and approaches for my configured agents during bootstrap, so that agents behave according to my project's development philosophy (e.g., TDD, trunk-based development) from the first feature onward.

**Why this priority**: Agent profiles connect governance to execution. Without them, agents use generic behavior regardless of project conventions.

**Independent Test**: Run bootstrap with agents configured (e.g., claude, codex). Reach the agent profile phase. Select "TDD" approach and "trunk-based" tactic. Verify these are stored in the constitution's agent profile section. Run `/spec-kitty.implement` and verify the agent receives profile context.

#### Functional Requirements

- **FR-4.1**: The agent profile phase SHALL present available behavioral patterns from `src/specify_cli/governance/patterns/` (Feature 044).
- **FR-4.2**: Each behavioral pattern SHALL display: name, description, applicable development approaches, and impact on agent behavior.
- **FR-4.3**: The user SHALL select one or more behavioral patterns per configured agent, or accept defaults.
- **FR-4.4**: Selected patterns SHALL be stored in the constitution under a structured "Agent Profiles" section.
- **FR-4.5**: The agent profile phase SHALL be skippable with `--skip-agents` flag. When skipped, agents use default behavioral patterns.
- **FR-4.6**: Agent profiles configured during bootstrap SHALL be used by the governance system (Feature 044) during `pre_implement` and `pre_review` hooks.
- **FR-4.7**: The profile phase SHALL only configure agents that were selected during `spec-kitty init` (reads from `.kittify/agents.yaml`).
- **FR-4.8**: Behavioral patterns represent **approaches** (mental models like TDD) and **tactics** (execution patterns like red-green-refactor). Both are selectable independently.

### User Story 5 — Constitution Phase Integration (Priority: P2)

As a project owner, I want the constitution phase of bootstrap to reuse the existing `/spec-kitty.constitution` interview flow, so that I get the same thorough governance setup whether I bootstrap or run constitution standalone.

**Why this priority**: Reusing the existing constitution flow avoids duplication and ensures consistency. The existing flow is already well-designed.

**Independent Test**: Run bootstrap through to the constitution phase. Verify the same questions are asked as `/spec-kitty.constitution` standalone. Verify the output `constitution.md` is identical in structure. Run `/spec-kitty.constitution` standalone on a different project and compare.

#### Functional Requirements

- **FR-5.1**: The constitution phase SHALL delegate to the existing constitution template (`src/specify_cli/missions/software-dev/command-templates/constitution.md`) for interview content.
- **FR-5.2**: The constitution phase SHALL pass bootstrap context (vision, audience, agent profiles) as additional context to the constitution interview, allowing the AI to tailor questions.
- **FR-5.3**: The constitution phase SHALL be skippable with `--skip-constitution` flag. When skipped, a minimal placeholder constitution is created with defaults.
- **FR-5.4**: The existing `/spec-kitty.constitution` slash command SHALL remain available for standalone use and for updating the constitution after initial bootstrap.
- **FR-5.5**: If a constitution already exists (from a previous bootstrap or standalone run), the bootstrap SHALL offer to update or replace it.

### User Story 6 — Downstream Soft-Block Integration (Priority: P3)

As a Spec Kitty operator, when I run `/spec-kitty.specify` on a project that has not been bootstrapped, I want to see a warning that bootstrap is recommended, with the option to proceed anyway, so that I'm guided toward better practice without being blocked.

**Why this priority**: Soft-blocking improves adoption by guiding users toward bootstrap without forcing it. Lower priority because it's an enhancement to an existing command, not core bootstrap functionality.

**Independent Test**: Create a project with `spec-kitty init` but no bootstrap. Run `/spec-kitty.specify`. Verify a warning appears suggesting bootstrap. Verify the user can proceed with `--no-bootstrap`. Run bootstrap, then re-run specify. Verify no warning appears.

#### Functional Requirements

- **FR-6.1**: `/spec-kitty.specify` SHALL check for the existence of `.kittify/memory/vision.md` before starting the specification interview.
- **FR-6.2**: If `vision.md` is absent, the specify template SHALL display a warning: "No project vision found. Run `spec-kitty bootstrap` first for better feature specifications."
- **FR-6.3**: The warning SHALL include an option to proceed without bootstrap (the user confirms or the `--no-bootstrap` flag is set).
- **FR-6.4**: When vision.md is present, `/spec-kitty.specify` SHALL include vision context (purpose, scope boundaries, audience) in the specification interview to improve question relevance.
- **FR-6.5**: The soft-block check SHALL also apply to `/spec-kitty.design` (Feature 041) with the same behavior.

## Success Criteria

1. **SC-1**: Complete bootstrap flow (all four phases) produces `vision.md` and `constitution.md` in `.kittify/memory/` with valid structure and frontmatter.
2. **SC-2**: Each optional phase can be independently skipped without affecting other phases or downstream functionality.
3. **SC-3**: Vision document uses purpose-first framing — the first interview question is about outcomes/purpose, not problems.
4. **SC-4**: Agent profiles selected during bootstrap are available to the governance system (Feature 044) at lifecycle hooks.
5. **SC-5**: `/spec-kitty.specify` soft-blocks with a warning when no vision exists, proceeding when `--no-bootstrap` is set.
6. **SC-6**: Re-running bootstrap on a previously bootstrapped project offers update/replace options without data loss.
7. **SC-7**: Non-interactive mode (`--non-interactive`) completes in under 5 seconds, creating minimal valid artifacts.

## Scope Boundaries

### In Scope
- `spec-kitty bootstrap` CLI command with four phases
- Vision document generation (`.kittify/memory/vision.md`)
- Audience capture (stored in vision.md)
- Agent profile behavioral pattern selection
- Constitution phase delegation to existing template
- Soft-block integration with `/spec-kitty.specify` and `/spec-kitty.design`
- Re-bootstrap with update/replace flow
- Non-interactive mode

### Out of Scope
- Modifying `spec-kitty init` — it stays unchanged
- Approach/tactic Python data models — specified by Feature 044 (governance patterns)
- Doctrine selection (choosing which general guidelines apply) — all guidelines ship and are immutable (Feature 044)
- Automated vision-to-spec generation — bootstrap captures context, specify uses it
- Multi-project bootstrap coordination — each project bootstraps independently

## Dependencies

- **Feature 044** (Governance + Doctrine Provider) — agent profiles reference behavioral patterns defined in the governance system; constitution enforcement uses the governance precedence hierarchy
- **Feature 041** (Design Mission) — bootstrap-produced vision.md and audience data are preconditions for the design mission flow
- **Feature 045** (Constitution Sync) — constitution generated during bootstrap may be synced to machine-parseable config

## Glossary Alignment

| Term | Definition (per project glossary) |
|------|-----------------------------------|
| **Bootstrap** | The post-init onboarding flow that captures project vision, audience, agent profiles, and constitution through a guided hybrid CLI/AI interview. |
| **Vision** | A structured document capturing project purpose, desired outcomes, scope boundaries, and success criteria. Purpose-first, not problem-first. |
| **Constitution** | Project-level governance document aggregating operational guidelines, overrides, directives, and agent configuration. |
| **Behavioral Pattern** | A named set of approaches and tactics that defines how an agent behaves, selected during bootstrap. |
| **Approach** | A mental model or development philosophy (e.g., TDD, trunk-based development) that shapes agent reasoning. |
| **Tactic** | A concrete execution pattern (e.g., red-green-refactor, feature flags) that agents follow during implementation. |
| **Human In Charge (HiC)** | The human operator who conducts the bootstrap interview and has final authority over all project governance decisions. |
| **Soft-Block** | A non-disruptive warning that recommends a prerequisite action (bootstrap) but allows the user to proceed without it. |