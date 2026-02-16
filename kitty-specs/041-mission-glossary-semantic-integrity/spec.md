# Feature Specification: Glossary Semantic Integrity Runtime for Mission Framework

**Feature Branch**: `041-mission-glossary-semantic-integrity`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: Sprint S2 kickoff prompt for glossary semantic integrity runtime behavior in spec-kitty 2.x

## User Scenarios & Testing

### User Story 1 - Mission Author Enables Glossary Checks (Priority: P1)

A mission author wants to ensure semantic consistency in their custom mission by adding glossary checks to critical steps (e.g., specification generation, documentation writing). They add check metadata to step definitions in their mission.yaml, and the runtime automatically enforces glossary resolution before LLM generation.

**Why this priority**: This is the foundational capability - without metadata-driven check attachment, the entire glossary enforcement system cannot function. It's the entry point for all semantic integrity workflows.

**Independent Test**: Can be fully tested by creating a minimal mission with one step that has glossary_check metadata enabled, running the step, and verifying that semantic check events are emitted before generation.

**Acceptance Scenarios**:

1. **Given** a mission step has `glossary_check: enabled` metadata, **When** the step executes, **Then** the runtime extracts candidate terms from step inputs and emits a `SemanticCheckEvaluated` event
2. **Given** a mission step has no glossary check metadata, **When** the step executes, **Then** no semantic checks are performed and generation proceeds normally
3. **Given** a mission has default `glossary_check: enabled` in mission config, **When** a step inherits this default, **Then** glossary checks run for that step

---

### User Story 2 - Developer Resolves High-Severity Semantic Conflict Interactively (Priority: P2)

A developer runs a mission step (e.g., `/spec-kitty.plan`) that triggers a high-severity semantic conflict (e.g., term "workspace" is ambiguous between "git worktree directory" and "VS Code workspace"). The CLI blocks generation, shows up to 3 ranked candidate senses, and prompts the developer to pick one or provide a custom definition. After resolution, the step resumes from the checkpoint.

**Why this priority**: This is the primary user-facing workflow for resolving conflicts. Without interactive resolution, users would be blocked with no clear path forward. It delivers immediate value once P1 is implemented.

**Independent Test**: Can be tested by creating a test scenario with a known ambiguous term, triggering a mission step that uses it, and verifying that (1) generation is blocked, (2) ranked candidates are shown, (3) user selection updates the glossary, and (4) step resumes successfully.

**Acceptance Scenarios**:

1. **Given** a mission step encounters an unresolved high-severity conflict, **When** the runtime reaches the generation gate, **Then** generation is blocked and an interactive prompt shows 1-3 ranked candidate senses
2. **Given** the user is prompted for clarification, **When** they select a candidate sense from the list, **Then** the glossary is updated with the selected sense and the step resumes from the checkpoint
3. **Given** the user is prompted for clarification, **When** they provide a custom sense definition, **Then** the new sense is recorded with provenance (actor, timestamp) and the step resumes
4. **Given** the user is prompted for clarification, **When** they choose to defer resolution, **Then** the conflict is logged to the event stream, generation remains blocked, and the step exits with a clear error message

---

### User Story 3 - Team Bootstraps Domain Glossary with Seed File (Priority: P3)

A team working on a domain-specific project (e.g., healthcare) wants to establish shared terminology upfront. They create a `team_domain.yaml` seed file with key terms (e.g., "patient", "encounter", "claim"), place it in `.kittify/glossaries/`, and the runtime uses it during scope resolution while also auto-populating additional terms from mission I/O.

**Why this priority**: This improves the user experience by reducing initial conflict noise, but it's optional - the system works without seed files via auto-population. It's a nice-to-have for teams with established vocabularies.

**Independent Test**: Can be tested by creating a seed file with 3-5 terms, running a mission step that uses those terms, and verifying that (1) seed terms are loaded into team_domain scope, (2) scope resolution finds them, and (3) no conflicts are raised for those terms.

**Acceptance Scenarios**:

1. **Given** a `team_domain.yaml` seed file exists in `.kittify/glossaries/`, **When** a mission initializes, **Then** the runtime loads seed terms into the team_domain scope
2. **Given** a mission step uses a term defined in the team_domain seed file, **When** scope resolution runs, **Then** the term resolves to the team_domain sense without conflict
3. **Given** no seed file exists for team_domain, **When** scope resolution runs, **Then** the runtime cleanly skips team_domain and continues to audience_domain and spec_kitty_core

---

### User Story 4 - Mission Replay Reproduces Glossary Evolution (Priority: P4)

A developer wants to reproduce a mission execution from a week ago to debug a regression. They run `spec-kitty replay <feature>`, and the event log deterministically recreates the glossary state at each step, including conflict resolutions and generation gate decisions.

**Why this priority**: This is critical for debugging and audit trails, but it depends on P1-P3 being complete. It's a quality-of-life improvement that ensures determinism, not a blocking requirement for initial rollout.

**Independent Test**: Can be tested by running a mission, recording glossary events (term extractions, conflict resolutions), then replaying the mission and verifying that the same glossary state and generation gate outcomes are reproduced.

**Acceptance Scenarios**:

1. **Given** a mission has been executed with glossary checks enabled, **When** the mission is replayed from the event log, **Then** the glossary state at each step matches the original execution
2. **Given** a conflict was resolved during the original execution, **When** the mission is replayed, **Then** the same conflict resolution is applied and the same generation gate outcome occurs
3. **Given** a term was added to the glossary via auto-population, **When** the mission is replayed, **Then** the term appears in the glossary at the same step

---

### User Story 5 - Operator Adjusts Strictness Mode for Different Environments (Priority: P5)

An operator wants to run missions with different enforcement levels in different environments. They set `strictness: off` for local development (fast iteration, no blocking), `strictness: medium` for CI (warn broadly, block only high-severity), and `strictness: max` for production (block any unresolved conflict). They can override at runtime via `--strictness` flag.

**Why this priority**: This is a configurability feature that provides flexibility for different workflows. It's valuable for advanced users but not essential for initial adoption - the default `medium` mode works for most cases.

**Independent Test**: Can be tested by running the same mission step with `--strictness off`, `--strictness medium`, and `--strictness max`, and verifying that (1) `off` skips all checks, (2) `medium` warns but only blocks high-severity, and (3) `max` blocks any unresolved conflict.

**Acceptance Scenarios**:

1. **Given** global strictness is set to `off`, **When** a mission step runs, **Then** no glossary checks are performed and generation proceeds without blocking
2. **Given** mission strictness is set to `medium`, **When** a low-severity conflict occurs, **Then** a warning is logged but generation is not blocked
3. **Given** mission strictness is set to `medium`, **When** a high-severity conflict occurs, **Then** generation is blocked until the conflict is resolved
4. **Given** runtime strictness override is `max`, **When** any unresolved conflict occurs, **Then** generation is blocked regardless of severity
5. **Given** strictness precedence (global → mission → step → runtime), **When** multiple levels are set, **Then** the most specific level takes precedence

---

### Edge Cases

- **Scope resolution with missing scopes**: What happens when `team_domain.yaml` does not exist? → Resolver skips team_domain cleanly and continues to audience_domain/spec_kitty_core.
- **Conflicting sense updates from multiple participants**: What happens when two users propose different senses for the same term simultaneously? → System records both proposals with provenance; mission owner acts as tie-breaker if unresolved tie remains.
- **Context changes during async resolution**: What happens when a user defers conflict resolution, makes code changes, then resolves the conflict? → System requests confirmation before resuming ("Context may have changed. Proceed with resolution?").
- **Replay with manual glossary edits**: What happens when a user manually edits a glossary file between original execution and replay? → Replay uses event log as source of truth, not filesystem state; manual edits are ignored during replay.
- **Nested mission step with inherited strictness**: What happens when a mission calls another mission with different strictness settings? → Child mission inherits parent's strictness unless explicitly overridden.
- **LLM hallucinated term not in any scope**: What happens when LLM generates output using a term that doesn't exist in any scope and has low confidence? → Classified as "unknown critical term" (type D conflict), severity set to high, generation blocked in medium/max modes.

## Requirements

### Functional Requirements

- **FR-001**: System MUST resolve terms against scope hierarchy in order: mission_local → team_domain → audience_domain → spec_kitty_core
- **FR-002**: System MUST detect 4 conflict types: (A) unknown terms (no match in scope stack), (B) ambiguous terms (multiple active senses, unqualified usage), (C) inconsistent usage (LLM output contradicts active glossary), (D) unresolved critical terms (low confidence, no resolved sense before generation)
- **FR-003**: System MUST emit `SemanticCheckEvaluated` events with severity (low/medium/high), confidence (0.0-1.0), and findings (list of conflicts per term)
- **FR-004**: System MUST block LLM generation on unresolved high-severity conflicts in `medium` and `max` strictness modes
- **FR-005**: System MUST support 3 strictness modes: `off` (no enforcement), `medium` (warn broadly, block high-severity only), `max` (block any unresolved conflict)
- **FR-006**: System MUST apply strictness precedence: global defaults → mission defaults → primitive/step metadata → runtime override
- **FR-007**: System MUST extract candidate terms from mission step inputs and outputs using metadata-driven extraction rules
- **FR-008**: System MUST show interactive clarification prompts with 1-3 questions maximum, prioritized by severity (high → medium → low)
- **FR-009**: System MUST allow users to defer conflict resolution to async mode, logging the conflict to the event stream while keeping generation blocked
- **FR-010**: System MUST resume mission step execution from checkpoint after conflict resolution, without requiring full re-run
- **FR-011**: System MUST store all glossary state (terms, senses, resolutions) in the event log using existing event architecture (no side-channel state files)
- **FR-012**: System MUST support optional seed files (`team_domain.yaml`, `audience_domain.yaml`) placed in `.kittify/glossaries/`
- **FR-013**: System MUST skip unconfigured scopes cleanly during resolution (e.g., if `team_domain.yaml` does not exist, resolver continues to next scope without error)
- **FR-014**: System MUST record custom sense definitions with provenance metadata (actor, timestamp, source: "user_clarification")
- **FR-015**: System MUST attach glossary checks to mission primitives via metadata in mission config files (e.g., `glossary_check: enabled` in step definition)
- **FR-016**: System MUST emit `GenerationBlockedBySemanticConflict` event when generation gate blocks due to unresolved high-severity conflict
- **FR-017**: System MUST present ranked candidate senses during clarification (ordered by scope precedence, then by confidence/frequency)
- **FR-018**: System MUST allow free-text custom sense input during clarification (not limited to pre-defined candidates)
- **FR-019**: System MUST request user confirmation before resuming if context has changed materially during async conflict resolution

### Key Entities

- **TermSurface**: Raw string representing a term (e.g., "workspace", "mission", "step")
  - Attributes: surface_text (string)

- **TermSense**: Meaning of a term within a specific scope
  - Attributes: surface (TermSurface), scope (GlossaryScope), definition (string), provenance (actor, timestamp, source), confidence (float 0.0-1.0), status (active/deprecated)

- **GlossaryScope**: Enumeration of scope levels
  - Values: `mission_local`, `team_domain`, `audience_domain`, `spec_kitty_core`
  - Resolution order: mission_local → team_domain → audience_domain → spec_kitty_core

- **SemanticConflict**: Classification of a term conflict
  - Attributes: term (TermSurface), conflict_type (unknown/ambiguous/inconsistent/unresolved_critical), severity (low/medium/high), confidence (float), candidate_senses (list of TermSense), context (usage location)

- **SemanticCheckEvaluated**: Event emitted after semantic check runs
  - Attributes: step_id, mission_id, timestamp, findings (list of SemanticConflict), overall_severity (low/medium/high), blocked (boolean)

- **GenerationBlockedBySemanticConflict**: Event emitted when generation gate blocks
  - Attributes: step_id, mission_id, timestamp, conflicts (list of SemanticConflict), strictness_mode (off/medium/max)

- **GlossaryResolution**: Event recording conflict resolution
  - Attributes: conflict_id, selected_sense (TermSense or custom definition), actor, timestamp, resolution_mode (interactive/async)

## Success Criteria

### Measurable Outcomes

- **SC-001**: Mission authors can enable glossary checks for any custom primitive by adding metadata to mission config (no code changes required)
- **SC-002**: Unresolved high-severity conflicts prevent LLM generation in `medium` and `max` strictness modes (100% enforcement)
- **SC-003**: Developers can resolve semantic conflicts interactively in under 2 minutes (measured from prompt display to resolution commit)
- **SC-004**: Mission replay reproduces identical glossary evolution and generation gate outcomes (deterministic event log replay)
- **SC-005**: `off` strictness mode allows mission execution without any glossary enforcement or blocking (0 generation blocks)
- **SC-006**: Scope resolution gracefully skips unconfigured `team_domain` and `audience_domain` scopes (no errors, continues to next scope)
- **SC-007**: 90% of semantic conflicts are auto-resolvable without user intervention (single candidate sense found in scope hierarchy)
- **SC-008**: Clarification prompt bursts are limited to 3 questions maximum (prevents user fatigue)
- **SC-009**: Async conflict resolution state persists across CLI sessions (users can defer and return later)
- **SC-010**: Custom sense definitions submitted by users are recorded with full provenance (actor, timestamp, source tracked in event log)
