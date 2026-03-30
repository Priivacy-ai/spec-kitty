# Feature Specification: Structured Agent Identity & Constitution-Profile Integration

**Feature Branch**: `feature/agent-profile-implementation`  
**Created**: 2026-03-08  
**Status**: Draft  
**Input**: User description: "Feature 048 — structured agent identity and constitution-profile integration"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Record Who Did What (Priority: P1)

An AI agent running a work package assignment (e.g., move a task to "doing") wants to record not just its name but also its model variant, operator profile, and current role. Today the system stores a bare string such as `"claude-opus"`, which makes it impossible to distinguish between two different agents using the same tool under different governance profiles. After this feature, agents record a structured identity that captures all four dimensions.

**Why this priority**: Without a reliable actor identity, governance audit trails are ambiguous. This is the foundational primitive the rest of the feature depends on.

**Independent Test**: Can be tested by assigning a task with a compound identity (`tool:model:profile:role`) and reading the event log — the stored event must carry all four fields.

**Acceptance Scenarios**:

1. **Given** an agent specifies its identity as `claude:claude-opus-4-6:implementer:implementer`, **When** it moves a work package to "doing", **Then** the status event log records a structured actor with all four fields (`tool`, `model`, `profile`, `role`) correctly populated.
2. **Given** an existing event log that contains legacy bare-string actors (e.g., `"claude-opus"`), **When** the system reads those events, **Then** it correctly interprets them as a structured identity with `tool = "claude-opus"` and the remaining fields defaulted to `"unknown"`, without errors or data loss.
3. **Given** an agent provides only a legacy bare string, **When** it emits a status transition, **Then** the system accepts it and stores it using the backwards-compatible format.

---

### User Story 2 — Use Rich Identity from CLI & Frontmatter (Priority: P2)

A developer operating spec-kitty from the terminal wants to pass agent identity information either as a compound flag (`--agent claude:claude-opus-4-6:implementer:implementer`) or as individual flags (`--tool claude --model claude-opus-4-6 --profile implementer --role implementer`). Work package frontmatter should also support the structured format so that assignments captured in task files are unambiguous.

**Why this priority**: Structured identity only delivers value if it can be set easily through all existing entry points (CLI commands, frontmatter files).

**Independent Test**: Can be tested by running `move-task` with structured flags and inspecting the resulting JSONL event for correct actor fields; separately, by writing structured agent frontmatter to a WP file and reading it back.

**Acceptance Scenarios**:

1. **Given** a user runs `spec-kitty agent tasks move-task WP01 --to doing --agent claude:opus-4:implementer:implementer`, **When** the command completes, **Then** the emitted event log entry contains the parsed structured identity.
2. **Given** a user runs the same command with individual flags `--tool claude --model opus-4 --profile implementer --role implementer`, **Then** the result is identical to the compound form.
3. **Given** a work package frontmatter file contains a structured agent mapping (YAML object), **When** the frontmatter is read, **Then** it produces the same structured identity as the equivalent compound string.
4. **Given** a work package frontmatter file contains a legacy scalar agent string, **When** the frontmatter is read, **Then** it is treated as a backwards-compatible identity with appropriate defaults.

---

### User Story 3 — Governance Compilation Follows Agent Profile (Priority: P3)

A project lead generates a constitution for a specific agent (e.g., a code-review agent running under the `reviewer` profile). Currently, the compiler scans raw YAML files and cannot select rules based on which profile is active. After this feature, the compiler can load an agent profile, trace its directive references transitively (directives → tactics → styleguides/toolguides), and produce a governance document tailored to that profile and role.

**Why this priority**: Profile-aware governance is a key differentiator for multi-agent projects. It builds on the structured identity primitive and the expanded doctrine catalog.

**Independent Test**: Can be tested by running `spec-kitty constitution generate-for-agent --profile reviewer` and verifying that the output references only the directives and tactics appropriate to that profile.

**Acceptance Scenarios**:

1. **Given** an agent profile defines a set of directive references, **When** `spec-kitty constitution generate-for-agent --profile reviewer` is called, **Then** the compiled constitution includes the directives, their transitively resolved tactics, and associated styleguides/toolguides for that profile.
2. **Given** an interview selects additional directives beyond what the profile defines, **When** compilation runs, **Then** the output is the union of profile directives and interview-selected directives (profile directives first).
3. **Given** a profile references a tactic that in turn references a styleguide, **When** the compiler resolves references, **Then** the styleguide appears in the output without the user needing to name it explicitly (transitive resolution).
4. **Given** `DoctrineService` is unavailable, **When** compilation runs, **Then** the system falls back gracefully to the existing YAML-scanning path without crashing.

---

### User Story 4 — Full Traceability Through the Pipeline (Priority: P4)

A team auditing an agentic development run wants to trace every work package action back to a specific agent identity — tool, model, profile, and role. The audit trail must be consistent from the CLI command through frontmatter through the event log, with no ambiguity about which agent performed an action.

**Why this priority**: End-to-end consistency validates that all entry points (CLI, frontmatter, event log) agree and that no identity data is lost in transit.

**Independent Test**: Can be tested via an integration test that exercises the full pipeline: write structured identity to frontmatter → emit status event → read back JSONL → assert all four fields are intact.

**Acceptance Scenarios**:

1. **Given** a structured identity is written to a WP frontmatter file, **When** a workflow command reads that frontmatter and emits a status event, **Then** the JSONL event log contains the full four-field identity.
2. **Given** a mixed event log (some legacy strings, some structured identities), **When** the status reducer processes it, **Then** all events produce a valid snapshot with no identity fields lost or corrupted.

---

### Edge Cases

- What happens when a compound identity string has fewer than four colon-separated parts (e.g., `"claude:opus"`)? The system infers missing parts from context where possible (e.g., a known profile name implies a default role); any part that cannot be inferred defaults to `"unknown"`.
- What happens when an agent profile references a directive that no longer exists in the doctrine catalog? The compiler must report it as an unresolved reference without failing the entire compilation.
- What happens when two directive references in a transitive chain create a cycle? The resolver must detect and break cycles without entering an infinite loop.
- What happens when both `--agent` (compound) and individual flags (e.g., `--tool`) are provided simultaneously? The flags are mutually exclusive — the system must raise a clear, actionable error and reject the command.
- What happens when a WP frontmatter contains a structured identity for a tool that is not in the known agent list? The system must store and round-trip the identity faithfully (no data loss for unknown tools).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Structured Actor Identity | As an AI agent, I want to record my identity as a structured 4-part value (tool, model, profile, role) so that governance audit trails are unambiguous. | High | Open |
| FR-002 | Backwards-Compatible Legacy Actors | As a system operator, I want existing bare-string actor values in the event log to continue working so that no data migration is required. | High | Open |
| FR-003 | Compound CLI Identity Flag | As a CLI user, I want to specify agent identity as a compound string or as four individual flags so that I can choose the most convenient input format. | High | Open |
| FR-004 | Structured Frontmatter Agent | As a developer, I want work package frontmatter to support a structured agent format so that task file assignments are unambiguous. | High | Open |
| FR-005 | Expanded Doctrine Catalog | As a constitution author, I want the catalog to enumerate tactics, styleguides, toolguides, procedures, and agent profiles so that I can select from all available governance artifacts. | Medium | Open |
| FR-006 | Transitive Reference Resolution | As a project lead, I want the system to automatically include tactics referenced by a directive, and styleguides/toolguides referenced by those tactics, so that governance documents are complete without manual enumeration. | Medium | Open |
| FR-007 | DoctrineService-Backed Compiler | As a constitution author, I want the compiler to query governance artifacts through the typed doctrine domain model so that references are validated and the compiler benefits from model-level guarantees. | Medium | Open |
| FR-008 | Profile-Aware Governance Compilation | As a project lead, I want to compile a constitution for a specific agent profile and role so that each agent receives only the governance rules relevant to its function. | Medium | Open |
| FR-009 | Graceful Compiler Fallback | As a user on a bare installation, I want constitution compilation to fall back to YAML scanning when doctrine services are unavailable so that the feature degrades gracefully. | Low | Open |
| FR-010 | End-to-End Structured Identity Pipeline | As an auditor, I want structured identity to flow consistently from CLI flags through frontmatter through the event log so that every action is fully traceable. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Event Log Integrity | Reading any combination of legacy and structured actor events must produce a valid status snapshot with no errors or data loss. | Reliability | High | Open |
| NFR-002 | Transitive Resolution Cycle Safety | The reference resolver must terminate for any input, including doctrine assets with circular references. | Reliability | High | Open |
| NFR-003 | Compiler Fallback Transparency | When the compiler falls back to YAML scanning, it must emit a diagnostic warning so operators know which code path was used. | Observability | Medium | Open |
| NFR-004 | Backwards Compatibility | All existing status and constitution tests must continue to pass after this feature is merged. | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No Event Log Migration | Existing JSONL event files must not be modified; the system must read old and new formats side-by-side. | Technical | High | Open |
| C-002 | No Frontmatter Migration | Existing work package frontmatter files with scalar `agent:` values must not require manual updates. | Technical | High | Open |
| C-003 | Compiler Fallback Required | The constitution compiler must not hard-depend on DoctrineService; the legacy YAML scanning path must remain functional. | Technical | Medium | Open |

### Key Entities

- **ActorIdentity**: Represents the four-part identity of an agent (`tool`, `model`, `profile`, `role`). Can be constructed from a compact compound string or from individual fields. Serialises to/from the existing bare-string format for backwards compatibility.
- **ResolvedReferenceGraph**: The output of transitive reference resolution for a set of directives. Contains the full closure of directives, tactics, styleguides, and toolguides reachable from the starting set, plus any unresolved references (type + ID pairs).
- **AgentProfile**: A named governance profile that declares which directives apply to an agent of a given role. Profiles can inherit from parent profiles.
- **GovernanceResolution** *(extended)*: The resolved governance activation result. Currently carries paradigms, directives, tools, template set, metadata, and diagnostics. This feature extends it with `tactics`, `styleguides`, `toolguides`, `profile_id`, and `role` fields so that profile-aware compilation can express the full transitive closure of governance artifacts selected for a given agent.
- **DoctrineCatalog** *(extended)*: An enumeration of all governance artifacts available in a project. Currently carries paradigms, directives, and template sets. This feature extends it with `tactics`, `styleguides`, `toolguides`, `procedures`, and `profiles` so the catalog reflects the full doctrine asset inventory.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of status events written after this feature carry a structured actor identity; 100% of pre-existing events with bare-string actors are read without errors.
- **SC-002**: All existing constitution and status test suites pass without modification after the feature is merged.
- **SC-003**: A transitive governance compilation for any valid agent profile produces a document that includes all transitively referenced tactics and styleguides — verifiable by comparing resolver output against a manually enumerated expected set in integration tests.
- **SC-004**: CLI commands that accept `--agent` or individual identity flags correctly populate the event log actor field in 100% of test scenarios, covering both compound and split-flag forms.
- **SC-005**: Constitution compilation with an unavailable DoctrineService produces a valid (though less rich) output and emits exactly one diagnostic warning — no unhandled exceptions.

## 2.x Architecture Traceability

This feature touches the following 2.x landscape containers and components:

| Container | Component(s) Affected | Change |
|---|---|---|
| Event Store | Event Semantics Reducer, Persistence Layer | `StatusEvent.actor` becomes `ActorIdentity` internally; serialisation remains backwards-compatible |
| Orchestration | WP Lifecycle Engine, Sync Identity Resolver (future consumer) | Lifecycle transitions carry structured identity; Sync Identity Resolver will consume `ActorIdentity` for projection in a future feature |
| Constitution | Constitution Compiler, Action Context Resolver | Compiler gains `DoctrineService` injection and transitive reference resolution; new `generate-for-agent` subcommand surfaces profile-aware compilation |
| Doctrine | Doctrine Catalog Loader | `DoctrineCatalog` expanded to enumerate all artifact types |
| Control Plane | Status Mutation Command Set | CLI gains `--tool`/`--model`/`--profile`/`--role` flags and compound `--agent` parsing |

**Architectural principle compliance**:
- **Principle 3 (Host-Owned State Authority)**: Identity enrichment stays within the host lifecycle pipeline; no delegation.
- **Principle 5 (Governance at Execution Boundary)**: Profile-aware constitution compilation ensures connectors receive role-appropriate governance.
- **Principle 6 (Event-Sourced Persistence)**: `ActorIdentity` enriches events; no mutation of existing JSONL files.

**Forward compatibility**: `ActorIdentity` is the domain primitive that the Sync Identity Resolver component (2.x Orchestration) and the Attribution Tracker (ADR 2026-02-11-4) will consume. This feature provides the structured foundation both depend on.

## Assumptions

- The `feature/agent-profile-implementation` branch is the correct target branch for this work.
- `DoctrineService` exposes (or will expose as part of this feature) repositories for agent profiles, tactics, styleguides, and toolguides.
- The compound identity separator is `:` (colon); colons are not valid within individual field values.
- Agent profile YAML files use a `profile-id` top-level field consistent with existing doctrine ID conventions.
- The existing `AgentProfileRepository.resolve_profile()` already handles profile inheritance; this feature does not need to change inheritance semantics.
