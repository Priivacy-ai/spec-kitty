# Feature Specification: Governance and Doctrine Provider

**Feature Branch**: `044-governance-and-doctrine-provider`
**Created**: 2026-02-15
**Status**: Draft
**Input**: Add a multi-tiered governance system to Spec Kitty 2.x with six lifecycle hooks, tri-state rule evaluation, and a doctrine-to-constitution precedence hierarchy — consolidating the original 1.x features 042 (Governance Plugin Interface) and 043 (Doctrine Governance Provider).

## Overview

Spec Kitty 2.x currently has no active governance enforcement. The constitution (`.kittify/memory/constitution.md`) exists as a reference document served via the dashboard, but no lifecycle phase validates its rules. This feature introduces:

1. **Six lifecycle hooks** — pre-plan, pre-implement, pre-review, pre-accept, pre-merge, pre-release validation points inserted into the 2.x orchestrator
2. **Tri-state rule evaluation** — every governance rule returns pass/warn/block, with warn as the default; blocking requires explicit opt-in via the constitution
3. **Multi-tiered precedence** — doctrine provides immutable general guidelines and operational contracts at the top; the constitution aggregates project-level operational guidelines, overrides, and directives; missions and tactics form the bottom
4. **Agent profile governance** — agent profile definitions adhere to the governance stack; their configuration is part of the constitution layer; behavioral patterns and tactics are selected during bootstrap
5. **Built-in governance rules** — rules ship compiled into spec-kitty (no external plugin loading in MVP)

### Governance Precedence Hierarchy

The governance stack resolves in strict precedence order:

| Layer | Source | Mutability | Example |
|-------|--------|------------|---------|
| **General Guidelines** | Doctrine (ships with spec-kitty) | Immutable — cannot be overridden | "Every decision needs alternatives documented" |
| **Operational Contracts** | Doctrine (ships with spec-kitty) | Immutable — with exception clauses | "Test before merge" (exception: rapid-prototyping spike) |
| **Constitution** | `.kittify/memory/constitution.md` | Project-configurable | Testing standards, code quality gates, branch strategy, agent preferences, pricing overrides |
| **Directives** | Constitution layer | Project-configurable | Cross-cutting behavioral constraints (numbered, traceable) |
| **Mission Guidance** | `.kittify/missions/<key>/mission.yaml` | Mission-scoped | Domain-specific workflow context and templates |
| **Tactics & Templates** | Bootstrap-selected behavioral patterns | Session-scoped | Execution patterns chosen from available repository |

**Key design decisions**:

- The constitution absorbs what was previously split between "constitution" and "local repository" in the original Doctrine stack. There is no separate `doctrine/` directory.
- General Guidelines and Operational Contracts are the only truly immutable layers. Operational Contracts support exception clauses for specific project modes (e.g., spike, prototype).
- Everything from "Constitution" downward is project-configurable.

**2.x baseline**: `src/specify_cli/orchestrator/integration.py` (lifecycle orchestration, no hooks), `src/specify_cli/orchestrator/agent_config.py` (agent selection/routing), `.kittify/memory/constitution.md` (governance documentation, not enforced).

## User Scenarios & Testing

### User Story 1 — Governance Validation at Lifecycle Hooks (Priority: P1)

As a Spec Kitty operator, when the orchestrator reaches a lifecycle phase boundary (plan, implement, review, accept, merge, release), the governance system evaluates applicable rules and returns a tri-state result (pass/warn/block), so I can catch process violations before they propagate.

**Why this priority**: Lifecycle hooks are the core mechanism for all governance enforcement. Without them, rules have nowhere to execute.

**Independent Test**: Trigger `spec-kitty implement WP01` with a governance rule that warns on missing test strategy. Verify the warning appears in console output but implementation proceeds. Then configure the constitution to escalate that rule to blocking. Verify implementation is halted with actionable error message.

#### Functional Requirements

- **FR-1.1**: The governance system SHALL provide six lifecycle hooks: `pre_plan`, `pre_implement`, `pre_review`, `pre_accept`, `pre_merge`, `pre_release`.
- **FR-1.2**: Each hook SHALL receive a context object containing the current feature, work package (if applicable), agent assignment, and constitution configuration.
- **FR-1.3**: Each hook SHALL return a `GovernanceResult` with status (pass/warn/block), a list of rule results, and an aggregate outcome.
- **FR-1.4**: Each individual rule result SHALL include: rule_id, rule_name, status (pass/warn/block), message, severity_source (doctrine/constitution/mission), and suggested_action (optional).
- **FR-1.5**: When aggregate result is `warn`, the orchestrator SHALL log all warnings to console and to the telemetry event log (Feature 043) and proceed with execution.
- **FR-1.6**: When aggregate result is `block`, the orchestrator SHALL halt execution, display all blocking rule violations with suggested remediation, and emit a governance block event.
- **FR-1.7**: The `--skip-governance` CLI flag SHALL bypass all governance hooks (with a logged warning that governance was skipped).
- **FR-1.8**: Hook execution time SHALL NOT exceed 2 seconds for the full hook evaluation (all rules combined).

### User Story 2 — Tri-State Rule Evaluation with Constitution Escalation (Priority: P1)

As a project lead, I want all governance rules to default to advisory (warn) mode, and I want to escalate specific rules to blocking via my constitution, so that governance is non-disruptive by default but enforceable when I need it.

**Why this priority**: The advisory-by-default approach is critical for adoption. Without it, governance becomes a barrier rather than a guide.

**Independent Test**: Run a lifecycle phase with two applicable rules. Verify both produce warnings by default. Edit the constitution to add an `enforcement` section escalating one rule to `block`. Re-run. Verify the escalated rule blocks, the other still warns.

#### Functional Requirements

- **FR-2.1**: All governance rules SHALL default to `warn` severity unless explicitly escalated.
- **FR-2.2**: The constitution SHALL support an `enforcement` section that escalates specific rule_ids to `block` severity.
- **FR-2.3**: The constitution enforcement section SHALL use a simple declarative format:

  ```markdown
  ## Governance Enforcement
  
  | Rule | Severity |
  |------|----------|
  | require-test-strategy | block |
  | require-spec-review | block |
  | budget-limit | block |
  ```

- **FR-2.4**: Rules originating from General Guidelines or Operational Contracts SHALL NOT be demotable below `warn` (they can be escalated to `block` but not silenced).
- **FR-2.5**: Rules originating from the Constitution or below MAY be set to `pass` (effectively disabled) via the enforcement section.
- **FR-2.6**: When a rule is escalated to `block`, the governance result message SHALL include which layer (constitution/directive) caused the escalation and why.
- **FR-2.7**: The `spec-kitty governance status` command SHALL display all active rules with their current severity level and escalation source.

### User Story 3 — Doctrine General Guidelines and Operational Contracts (Priority: P2)

As a framework maintainer, I want spec-kitty to ship with immutable general guidelines and operational contracts that define the framework's core values and behavioral norms, so that all projects using spec-kitty share a baseline governance standard.

**Why this priority**: The doctrine layer provides the invariant foundation. It must be defined before project-level customization can meaningfully extend it.

**Independent Test**: List all doctrine-shipped rules. Attempt to set a General Guideline rule to `pass` severity via constitution. Verify the system rejects this with an error message explaining immutability. Then successfully escalate the same rule to `block`.

#### Functional Requirements

- **FR-3.1**: Spec-kitty SHALL ship with a set of General Guidelines rules stored as structured data in `src/specify_cli/governance/doctrine/guidelines.yaml`.
- **FR-3.2**: Spec-kitty SHALL ship with a set of Operational Contracts stored as structured data in `src/specify_cli/governance/doctrine/contracts.yaml`.
- **FR-3.3**: General Guidelines SHALL be immutable — cannot be overridden, disabled, or demoted by any project-level configuration.
- **FR-3.4**: Operational Contracts SHALL be immutable with exception clauses — they cannot be disabled, but their exception conditions (e.g., `except_modes: [spike, prototype]`) allow project modes to skip specific checks.
- **FR-3.5**: The doctrine data format SHALL include for each rule: `rule_id`, `name`, `description`, `default_severity` (warn), `category` (general_guideline/operational_contract), `applies_to` (list of hooks), `exception_modes` (list, contracts only), and `check_fn` (reference to built-in validation function).
- **FR-3.6**: The `spec-kitty governance list-rules` command SHALL display all doctrine rules grouped by category, showing which hooks each rule applies to.
- **FR-3.7**: The `spec-kitty governance list-rules --category operational_contract` SHALL filter to only operational contracts.

### User Story 4 — Constitution-Driven Project Governance (Priority: P2)

As a project lead, I want the constitution to define project-specific governance rules (testing standards, code quality gates, review requirements) that are validated at the appropriate lifecycle hooks, so that my team's agreed standards are automatically enforced.

**Why this priority**: Project-specific governance rules provide the customization layer that makes governance useful beyond the baseline. Depends on hooks (US1) and evaluation (US2).

**Independent Test**: Create a constitution with a "Testing Requirements" section specifying 80% coverage threshold. Run `pre_review` hook. Verify the governance system evaluates code coverage against the threshold and produces a warn (or block, if escalated) result with the actual vs required coverage.

#### Functional Requirements

- **FR-4.1**: The governance system SHALL parse the constitution's structured sections to derive project-specific rules: testing requirements, code quality gates, review process, branch strategy, and custom directives.
- **FR-4.2**: Constitution-derived rules SHALL be assigned rule_ids in the namespace `constitution.<section>.<rule>` (e.g., `constitution.testing.min-coverage`).
- **FR-4.3**: The constitution parser SHALL support Markdown table format for structured rules and prose sections for qualitative guidance.
- **FR-4.4**: Constitution-derived rules SHALL default to `warn` severity, escalatable to `block` via the enforcement section (FR-2.2).
- **FR-4.5**: When the constitution is updated, the governance system SHALL re-parse rules on next hook invocation (no caching across invocations).
- **FR-4.6**: The governance system SHALL emit a `GovernanceEvent` to the telemetry log (Feature 043) for each rule evaluation, recording rule_id, result, context, and timing.
- **FR-4.7**: Constitution sections that do not map to structured rules SHALL be available as `qualitative_guidance` in the hook context, accessible to agent profiles for soft enforcement.

### User Story 5 — Agent Profile Governance Adherence (Priority: P3)

As a Spec Kitty operator, I want agent profiles to be governed by the doctrine/constitution stack, so that agent behavior, model selection, and task assignment respect the project's governance hierarchy.

**Why this priority**: Agent profile governance connects the governance system to the agent orchestrator. Lower priority because agent routing (Feature 046) provides the mechanical routing; this story adds governance constraints on top.

**Independent Test**: Configure agent profiles in the constitution with role specializations (architect, implementer, reviewer). Trigger agent selection. Verify the governance system validates that the selected agent matches the role requirements for the work package type.

#### Functional Requirements

- **FR-5.1**: Agent profiles SHALL be definable in the constitution with: agent_key, role (implementer/reviewer/architect/planner), preferred_model, capability declarations, and governance scope (which rules apply to this agent's work).
- **FR-5.2**: During `pre_implement` and `pre_review`, the governance system SHALL validate that the assigned agent's profile matches the work package requirements (e.g., security-sensitive WPs assigned to agents with security capability).
- **FR-5.3**: Agent profile mismatches SHALL produce `warn` results by default, escalatable to `block` via constitution.
- **FR-5.4**: The governance system SHALL support behavioral patterns — named sets of tactics and approaches — selectable during bootstrap and referenced in agent profiles.
- **FR-5.5**: Behavioral patterns SHALL be stored in `src/specify_cli/governance/patterns/` and discoverable via `spec-kitty governance list-patterns`.
- **FR-5.6**: Each behavioral pattern SHALL include: pattern_id, name, description, applicable_roles, tactics (list of tactic references), and approach (mental model description).
- **FR-5.7**: During bootstrap, the user SHALL select behavioral patterns for each configured agent, stored in the constitution's agent profile section.

### User Story 6 — Governance Reporting and Observability (Priority: P3)

As a Spec Kitty operator, I want to see a summary of governance evaluations across my project's lifecycle, so I can identify recurring violations and adjust my governance configuration.

**Why this priority**: Observability closes the feedback loop. Lower priority because governance must be functional (US1-4) before reporting adds value.

**Independent Test**: Run several lifecycle phases with mixed pass/warn/block results. Run `spec-kitty governance report`. Verify the report shows rule-by-rule statistics, most-violated rules, and trend over time.

#### Functional Requirements

- **FR-6.1**: The `spec-kitty governance report` command SHALL aggregate all GovernanceEvents from telemetry logs across features.
- **FR-6.2**: The report SHALL show: total evaluations, pass/warn/block counts, most-violated rules (top 5), rules never triggered, and average hook execution time.
- **FR-6.3**: The report SHALL support `--feature <slug>` to scope to a single feature.
- **FR-6.4**: The report SHALL support `--since <date>` to scope to a time window.
- **FR-6.5**: Governance events SHALL integrate with the telemetry dashboard (Feature 043) if available.

## Success Criteria

1. **SC-1**: All six lifecycle hooks execute in under 2 seconds each with the full rule set evaluated.
2. **SC-2**: Default behavior (no constitution enforcement section) produces only warnings — never blocks execution.
3. **SC-3**: Constitution escalation to `block` halts execution with actionable remediation guidance.
4. **SC-4**: General Guidelines and Operational Contracts cannot be disabled or demoted below `warn` via any project configuration.
5. **SC-5**: Governance events integrate with the Feature 043 telemetry event log using the same JSONL store pattern.
6. **SC-6**: `--skip-governance` flag bypasses all hooks with a logged warning (escape hatch for emergencies).
7. **SC-7**: Agent profile governance validates role-task alignment during `pre_implement` and `pre_review`.
8. **SC-8**: Governance report provides actionable insights within 5 seconds for projects with up to 50 features.

## Scope Boundaries

### In Scope

- Six lifecycle hooks with tri-state evaluation
- Doctrine general guidelines and operational contracts (built-in)
- Constitution-derived project rules with Markdown parsing
- Agent profile governance with behavioral patterns
- Governance CLI commands (status, list-rules, list-patterns, report)
- GovernanceEvent emission to telemetry log
- `--skip-governance` escape hatch

### Out of Scope

- External governance plugin loading (future — plugin API deferred)
- Real-time governance enforcement in agent prompts (agents receive guidance, not runtime checks)
- Automated remediation (governance reports violations, does not fix them)
- Governance rules for non-spec-kitty workflows (only spec-kitty lifecycle phases covered)
- GUI-based governance configuration (CLI and constitution only)

## Dependencies

- **Feature 043** (Telemetry Foundation) — governance events use the same JSONL event store pattern; GovernanceEvent type extends the event model
- **Feature 045** (Constitution Sync) — constitution parsing for governance rules depends on a well-defined constitution structure
- **Feature 046** (Routing Provider) — agent profile governance validates assignments made by the routing provider

## Glossary Alignment

| Term | Definition (per project glossary) |
|------|-----------------------------------|
| **Constitution** | Project-level governance document aggregating operational guidelines, overrides, directives, and agent configuration. Single source of truth for project customization. |
| **Doctrine** | Framework-level immutable guidelines and contracts that ship with spec-kitty. Provides the governance floor that projects extend but cannot lower. |
| **Human In Charge (HiC)** | The human operator who has final authority over governance escalation decisions and constitution configuration. |
| **Governance Hook** | An insertion point in the spec-kitty lifecycle where rules are evaluated before a phase proceeds. |
| **Behavioral Pattern** | A named set of tactics and approaches that defines how an agent behaves, selected during bootstrap and stored in the constitution. |
