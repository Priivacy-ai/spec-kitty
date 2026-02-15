# Feature Specification: Design Mission

**Feature Branch**: `041-design-mission`
**Created**: 2026-02-15
**Status**: Draft
**Input**: User description: "Add a 'design' mission to spec-kitty that captures system context, stakeholders, user journeys, ADRs, and a living glossary (DDD ubiquitous language style). The goal is to reduce ambiguity and ensure tasks/context/specifications match the user's intent and vision. The design mission sits between bootstrap (purpose) and specify (features) — it captures structure. Implementation follows the same pattern as Feature 012 (documentation mission)."

## Overview

Add a new "design" mission type to spec-kitty that guides teams through structured architectural design sessions producing living artifacts: stakeholder personas, a DDD-style living glossary, user journey maps, ADRs, and bounded context maps. Unlike feature-scoped specifications, design artifacts are project-wide and continuously referenced by downstream commands (`/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.review`).

The design mission is repeatable — teams run it initially to establish shared understanding, then re-run it as the system evolves to capture new terminology, stakeholders, and decisions. The glossary serves as connective tissue: terms defined during design become the canonical vocabulary enforced across all subsequent spec-kitty activities.

**Lifecycle position**:
```
init → bootstrap → design → specify → plan → tasks → implement → review → accept
```

**Reference journey**: [003 — System Design & Shared Understanding](../../architecture/journeys/003-system-design-and-shared-understanding.md)

## User Scenarios & Testing

### User Story 1 — Greenfield Design Session (Priority: P1)

A team has bootstrapped their project (vision + constitution exist) and wants to establish shared architectural understanding before starting feature work. They run `/spec-kitty.design` which guides them through stakeholder discovery, terminology harvesting from code, glossary refinement, and decision formalization — producing a living glossary, stakeholder personas, and at least one ADR.

**Why this priority**: Without shared understanding, feature specifications drift from intent. Different contributors use different terms for the same concept. This is the foundational use case that all others depend on.

**Independent Test**: Run `/spec-kitty.design` on a bootstrapped project with existing code but no architecture artifacts. Verify it produces `glossary/README.md`, at least one stakeholder entry, and at least one ADR in `architecture/adrs/`.

**Acceptance Scenarios**:

1. **Given** a bootstrapped project with `vision.md` and `constitution.md` but no architecture artifacts, **When** user runs `/spec-kitty.design`, **Then** the AI conducts a phased discovery interview starting with stakeholder identification
2. **Given** discovery identifies 3+ stakeholder types, **When** the AI scans the codebase for domain terms, **Then** it presents a candidate glossary with term sources (class names, method names, docs) grouped by domain area
3. **Given** candidate glossary presented, **When** the architect validates terms, **Then** each confirmed term gets: name, definition, bounded context affinity, and status (canonical/candidate/deprecated)
4. **Given** glossary refinement complete, **When** the AI detects significant decisions made during the session, **Then** it drafts ADRs with context, decision, at least 2 alternatives, and consequences

---

### User Story 2 — Glossary Detects Terminology Conflict (Priority: P1)

A codebase uses the same term with different meanings in different modules (e.g., "session" means "login session" in auth and "subscription period" in billing). During language harvesting, the AI detects this conflict and surfaces it as a bounded context hint, allowing the architect to decide whether to unify the term or acknowledge a context boundary.

**Why this priority**: Equally critical — terminology conflicts are the primary signal the design mission is built to detect. This is the core value proposition of language-first architecture.

**Independent Test**: Create a project with intentionally conflicting term usage across modules. Run the design mission and verify the conflict is surfaced with module-level attribution and the architect can resolve or acknowledge it.

**Acceptance Scenarios**:

1. **Given** a codebase where `Order` is used as "purchase order" in `sales/` and "sort order" in `ui/`, **When** the AI harvests terms, **Then** the conflict is flagged with source locations and both meanings
2. **Given** a flagged conflict, **When** the architect says "these are different concepts", **Then** the glossary records both terms with distinct bounded context affinity and a context boundary is hinted
3. **Given** a flagged conflict, **When** the architect says "these should be the same concept", **Then** the glossary records a single canonical term and the AI suggests renaming in one module
4. **Given** 3+ terms with dual meanings across module boundaries, **When** context mapping runs, **Then** the AI proposes bounded context boundaries aligned with the term clusters

---

### User Story 3 — Incremental Design Session (Priority: P2)

A project that previously ran `/spec-kitty.design` has added new code and features. The architect runs the design mission again. The AI loads existing design artifacts, harvests only new/changed terms from recent code, and presents deltas rather than repeating the full session.

**Why this priority**: Architecture evolves. Without incremental updates, the living glossary becomes stale and the design mission becomes a one-shot tool rather than a continuous practice.

**Independent Test**: Run `/spec-kitty.design` twice on the same project, adding new code between runs. Verify the second run loads existing glossary, shows only new terms, and does not overwrite existing ADRs.

**Acceptance Scenarios**:

1. **Given** a project with existing `glossary/README.md` from a prior design session, **When** the architect runs `/spec-kitty.design` again, **Then** the AI loads the existing glossary and presents it as baseline
2. **Given** new code added since last session, **When** language harvesting runs, **Then** only new/changed terms are flagged for review (not the entire glossary)
3. **Given** existing ADRs in `architecture/adrs/`, **When** a new decision conflicts with a prior ADR, **Then** the AI flags the conflict and asks the architect to supersede or reconsider
4. **Given** incremental session completes, **When** artifacts are committed, **Then** existing terms/ADRs are preserved and new ones are appended

---

### User Story 4 — Downstream Glossary Consumption (Priority: P2)

After a design session produces a glossary, subsequent spec-kitty commands reference it for consistency. When an architect runs `/spec-kitty.specify` and uses a non-canonical term, the system flags the inconsistency.

**Why this priority**: The glossary's value is realized downstream. Without consumption, it's just documentation.

**Independent Test**: Complete a design session establishing "WorkPackage" as canonical, then run `/spec-kitty.specify` using "task bundle". Verify the inconsistency is flagged.

**Acceptance Scenarios**:

1. **Given** a glossary containing "WorkPackage" (canonical) with "task bundle" as deprecated synonym, **When** the architect runs `/spec-kitty.specify` and uses "task bundle", **Then** the discovery interview flags the non-canonical term and suggests "WorkPackage"
2. **Given** a glossary and existing ADRs, **When** `/spec-kitty.plan` runs, **Then** the "Technical Context" section cross-references relevant ADRs
3. **Given** a completed feature implementation, **When** `/spec-kitty.review` runs, **Then** it checks terminology in code/docs against the glossary and flags drift

---

### User Story 5 — Minimal Design Session (Priority: P3)

An architect wants to focus only on terminology, skipping stakeholder personas, context mapping, and ADR formalization. The design mission supports partial adoption — they can complete only the glossary phases and skip the rest.

**Why this priority**: Not every project needs full architectural design. Small projects or early-stage repos benefit from just a shared vocabulary.

**Independent Test**: Run `/spec-kitty.design` and skip all phases after glossary refinement. Verify only `glossary/README.md` is created, with no persona files, ADRs, or context maps.

**Acceptance Scenarios**:

1. **Given** an architect who starts the design mission, **When** they complete glossary phases and choose to skip remaining phases, **Then** only `glossary/README.md` is produced
2. **Given** a minimal session completed, **When** the architect later runs a full design session, **Then** the existing glossary is loaded and remaining phases proceed normally

---

### User Story 6 — User Journey Capture (Priority: P3)

During the design session, the architect describes key cross-boundary flows. The AI generates structured user journey artifacts with actors, phases, coordination rules, and events, linking to stakeholder personas identified earlier.

**Why this priority**: Journeys add significant value but require more architect time. Not all projects need formal journey maps.

**Independent Test**: During a design session, describe a multi-actor workflow. Verify the AI generates a journey file in `architecture/journeys/` using the standard template format with linked personas.

**Acceptance Scenarios**:

1. **Given** stakeholder personas identified in Phase 1, **When** the AI interviews for key flows in Phase 5, **Then** it generates journey artifacts with actor tables linking to persona files
2. **Given** a generated journey, **When** the architect reviews, **Then** the journey includes actors, phases, coordination rules, events, and acceptance scenarios
3. **Given** a journey referencing "DevOps Engineer" persona, **When** persona was generated in Phase 1, **Then** the journey's actor table links to the persona file

---

### Edge Cases

- What happens when the project has no source code yet (design-first)? Language harvesting scans only vision.md and constitution.md; the AI notes that code-based term extraction will be available after implementation begins.
- What happens when the glossary grows beyond 100 terms? The AI groups terms by bounded context affinity and presents only the relevant cluster during downstream command execution, not the full glossary.
- How does the system handle conflicting ADRs from different design sessions? Each ADR has a status field (proposed/accepted/superseded/deprecated). The AI shows active ADRs and flags superseded ones.
- What happens when the codebase uses abbreviations not in the glossary (e.g., `usr`, `txn`)? The AI flags these as candidate terms during harvesting and asks whether they should be expanded or accepted as canonical abbreviations.
- How does the system handle a team that doesn't want ADRs? ADR formalization is optional — the architect can skip Phase 7 entirely. The system records that no architectural decisions were formalized and notes it as design debt.
- What happens when vision.md or constitution.md don't exist? The design mission checks preconditions and recommends running `/spec-kitty.bootstrap` first, but does not hard-block — the session can proceed with reduced context.

## Requirements

### Functional Requirements

#### Mission Infrastructure

- **FR-001**: System MUST support a new mission type called "design" with its own phase workflow distinct from software-dev, research, and documentation missions
- **FR-002**: Design mission MUST support iterative execution — users can run multiple design sessions on the same project, each building on prior artifacts
- **FR-003**: System MUST persist design session state between iterations to support incremental term harvesting and ADR conflict detection
- **FR-004**: System MUST add `"design"` to the domain `Literal` in `MissionConfig` and register the mission via auto-discovery in `src/specify_cli/missions/design/`

#### Discovery Phase (Stakeholders)

- **FR-005**: Specify phase MUST detect whether this is an initial design session (no existing artifacts) or an incremental session (existing glossary/ADRs) and adapt the interview accordingly
- **FR-005a**: Discovery and language harvesting phases (1-2) MUST run semi-autonomously without requiring per-phase confirmation; glossary validation (3), context mapping (4), and ADR formalization (7) MUST be gated — requiring explicit human confirmation before proceeding
- **FR-006**: AI MUST interview the architect to identify stakeholder categories: users, operators, developers, business owners, compliance/regulatory, and affected parties
- **FR-007**: System MUST capture each stakeholder with at minimum: name/role, type, and primary concerns
- **FR-008**: System MUST optionally generate full persona files using the stakeholder persona template in `architecture/stakeholders/`

#### Language Harvesting & Glossary

- **FR-009**: System MUST provide a hybrid term extraction approach: CLI performs a lightweight name-based scan (file names, class names, function/method names, module names) and the AI agent performs deeper semantic analysis on flagged areas (comments, docstrings, README content, variable naming patterns)
- **FR-010**: AI MUST scan `vision.md`, `constitution.md`, and any existing `glossary/README.md` for domain vocabulary
- **FR-011**: AI MUST present candidate terms with source locations, frequencies, and apparent domain area groupings for architect validation
- **FR-012**: For each confirmed term, system MUST record: name, definition, bounded context affinity (if clear), status (canonical/candidate/deprecated), and synonyms (if any)
- **FR-013**: System MUST detect terminology conflicts — same term used with different implicit meanings across module boundaries — and surface them as bounded context hints
- **FR-014**: System MUST store the glossary as `glossary/README.md` (create or update existing)
- **FR-015**: For incremental sessions, system MUST present only deltas (new terms, changed usage, deprecated terms) rather than re-validating the entire glossary

#### Context Mapping

- **FR-016**: Based on terminology conflicts detected in FR-013, AI MUST propose bounded context boundaries with supporting evidence (which terms conflict, where)
- **FR-017**: For each proposed boundary, AI MUST suggest an integration pattern (ACL, shared kernel, published language, or other)
- **FR-018**: Context mapping MUST be optional — small projects may defer or skip it entirely
- **FR-019**: AI MUST apply Locality of Change discipline — if the proposed context complexity is disproportionate to team size and project scale, it flags this and suggests simplification

#### User Journey Capture

- **FR-020**: AI MUST interview the architect for 1-3 key cross-boundary flows and generate structured journey artifacts
- **FR-021**: Journey artifacts MUST use the standard template format: actors (with persona links), phases, coordination rules, events, and acceptance scenarios
- **FR-022**: User journey capture MUST be optional — the architect can skip it

#### Constraint & NFR Capture

- **FR-023**: AI MUST interview for hard constraints (technology locks, team size, compliance) and quality attributes with measurable targets
- **FR-024**: Quality attributes MUST be measurable — vague statements like "the system should be fast" MUST be rejected in favor of quantified targets
- **FR-025**: AI MUST capture the "do nothing" baseline — what happens if architectural design is skipped

#### Decision Formalization (ADRs)

- **FR-026**: AI MUST review all decisions surfaced during the session and draft ADRs for significant ones
- **FR-027**: Each ADR MUST include: context, decision, at least 2 alternatives (including "do nothing"), and consequences
- **FR-028**: System MUST cross-reference proposed decisions against existing ADRs in `architecture/adrs/` and flag conflicts
- **FR-029**: ADRs MUST be stored in `architecture/adrs/` with auto-incrementing numbering: `ADR-NNN-title-slug.md`
- **FR-030**: Decision formalization MUST be optional — the architect can skip it if no significant decisions were made

#### Downstream Integration

- **FR-031**: `/spec-kitty.specify` MUST load the glossary (if it exists) and use canonical terms during discovery interviews; non-canonical synonyms SHOULD be flagged. Implementation: add glossary-loading and term-flagging hooks to the specify command template across all agents
- **FR-032**: `/spec-kitty.plan` MUST cross-reference ADRs in the "Technical Context" section when design artifacts exist. Implementation: add ADR-loading stubs to the plan command template
- **FR-033**: `/spec-kitty.review` MUST check terminology consistency in code and documentation against the glossary and flag drift. Implementation: add glossary-check hooks to the review command template
- **FR-034**: Downstream integration MUST be passive in MVP — commands reference design artifacts but do not block if they are missing

#### Artifact Generation & Commit

- **FR-035**: CLI MUST commit all design artifacts to the current branch with structured commit messages after each phase or at session end
- **FR-036**: Design artifacts MUST live in project-wide directories (`glossary/`, `architecture/`), NOT in per-feature `kitty-specs/` directories

#### Event Emission

- **FR-041**: Design mission MUST emit events through the 2.x status event system (JSONL event log) for all significant state transitions
- **FR-042**: Required events: `DesignSessionStarted`, `StakeholderIdentified`, `TerminologyExtracted`, `GlossaryDraftCreated`, `TermDefined`, `AmbiguityDetected`, `BoundaryHinted`, `ContextBoundaryProposed`, `ContextMapCreated`, `JourneyCaptured`, `ConstraintCaptured`, `QualityAttributeDefined`, `ArchitectureDecisionRecorded`, `DesignArtifactsGenerated`, `DesignSessionCompleted`
- **FR-043**: Events MUST include actor, timestamp, feature_slug, and phase metadata consistent with the existing `StatusEvent` model

#### Preconditions & Soft-Block

- **FR-044**: If `vision.md` or `constitution.md` is missing, the design mission MUST warn the user and explicitly ask "Proceed without vision/constitution?" requiring confirmation before continuing
- **FR-045**: The warning MUST recommend running `/spec-kitty.bootstrap` first and explain what context will be reduced

#### Mission Workflow Commands

- **FR-046**: System MUST support `/spec-kitty.specify` for design missions with discovery questions tailored to architectural design goals
- **FR-047**: System MUST support `/spec-kitty.plan` for design missions generating design-specific implementation plans
- **FR-048**: System MUST support `/spec-kitty.implement` for design missions that conduct the phased design session and produce artifacts
- **FR-049**: System MUST support `/spec-kitty.review` for design missions validating artifact quality, glossary consistency, and ADR completeness

### Key Entities

- **Design Mission**: A specification-plan-implement workflow focused on establishing or refining project-wide architectural understanding; runs iteratively over project lifetime
- **Living Glossary**: A continuously-updated vocabulary of domain terms with definitions, bounded context affinity, canonical/deprecated status, and synonyms; stored in `glossary/README.md`
- **Glossary Term**: A single entry in the living glossary with: name, definition, context affinity, status, synonyms, source locations
- **Terminology Conflict**: Detection of the same term used with different meanings across module boundaries; signals a potential bounded context boundary
- **Bounded Context Map**: A lightweight representation of domain areas, which terms belong to which context, and integration patterns between contexts
- **Stakeholder Persona**: A named actor with type (human/system), primary concerns, and optional full persona file in `architecture/stakeholders/`
- **User Journey**: A multi-actor workflow map with phases, coordination rules, events, and acceptance scenarios; stored in `architecture/journeys/`
- **Architecture Decision Record (ADR)**: A structured document recording context, decision, alternatives (min 2), and consequences; stored in `architecture/adrs/`
- **Design Session State**: Persisted metadata tracking which phases have been completed, last harvest timestamp, and incremental delta tracking
- **Design Vision**: Optional high-level document capturing system context, quality attributes, constraints, and solution overview

## Success Criteria

### Measurable Outcomes

- **SC-001**: A greenfield design session on a bootstrapped project with ~50 source files produces a glossary with ≥15 validated terms, at least 1 stakeholder entry, and at least 1 ADR within a single interactive session
- **SC-002**: Language harvesting correctly identifies ≥80% of domain terms in class/method names and module names from a codebase scan
- **SC-003**: Terminology conflict detection correctly surfaces same-term-different-meaning conflicts when terms are used in ≥2 modules with different semantic contexts
- **SC-004**: An incremental design session on a project with existing glossary presents only deltas (new/changed/deprecated terms) without re-validating unchanged terms
- **SC-005**: Downstream `/spec-kitty.specify` correctly loads the glossary and flags at least 1 non-canonical synonym when the architect uses a deprecated term
- **SC-006**: ADR conflict detection correctly identifies when a proposed decision contradicts an existing accepted ADR
- **SC-007**: The Locality of Change gate correctly flags disproportionate context complexity (e.g., 5 bounded contexts for a 2-person team)
- **SC-008**: A minimal design session (glossary only) completes without producing persona files, ADRs, or context maps

## Assumptions

- **ASM-001**: Projects running the design mission have been bootstrapped — `vision.md` and `constitution.md` exist. If missing, the mission soft-blocks with a warning and requires explicit confirmation to proceed with reduced context
- **ASM-002**: Language harvesting uses a hybrid approach: CLI extracts names (file, class, function, module) via lightweight scanning; the AI agent performs deeper semantic analysis on flagged areas. No AST parsing or deep code analysis in MVP
- **ASM-003**: The living glossary is stored as Markdown in `glossary/README.md` — no database or structured query system
- **ASM-004**: Bounded context mapping is proportional to project scale — the system does not aim for full strategic DDD
- **ASM-005**: ADR templates follow the established format in `architecture/adrs/` with auto-incrementing numbering
- **ASM-006**: Downstream integration is passive in MVP — commands reference design artifacts but do not enforce or block
- **ASM-007**: The design mission command templates override only the commands that differ from `software-dev` (template merging is automatic)
- **ASM-008**: Design artifacts are project-wide (in `glossary/`, `architecture/`) and are NOT scoped to individual features

## Out of Scope

The following are explicitly NOT included in this feature:

- **Automated glossary enforcement in CI/CD**: No PR-time checks or build-time validation of terminology compliance
- **Full strategic DDD**: No event storming, aggregate design, saga patterns, or domain event modeling
- **C4 model diagramming**: No automated generation of system context, container, component, or code diagrams
- **Technology selection / vendor evaluation**: Design mission captures constraints, not technology choices
- **Code refactoring based on context boundaries**: The mission identifies boundaries but does not restructure code
- **Real-time glossary sync across agents**: No live push of glossary updates to running agent sessions
- **Visual artifact generation**: No diagrams, flowcharts, or visual context maps — all outputs are Markdown
- **Multi-language glossary (i18n)**: Glossary is single-language only
- **Glossary versioning / history**: No temporal queries ("what did this term mean 3 months ago?") — git history serves this purpose
- **Integration with external architecture tools**: No ArchiMate, Structurizr, or PlantUML integration

## Research Sources

This specification incorporates research from:

- **Doctrine framework** (approaches): Living Glossary Practice, Bounded Context Discovery via Linguistic Analysis, Language-First Architecture, Traceable Decisions
- **Doctrine framework** (tactics): ADR drafting workflow, terminology extraction mapping, context boundary inference
- **Doctrine framework** (templates): PERSONA.md, adr.md, design_vision.md, functional_requirements.md
- **DDD (Domain-Driven Design)**: Ubiquitous language, bounded contexts, context mapping, published language
- **Feature 012 (documentation mission)**: Implementation pattern — mission.yaml, command-templates, artifact templates, migration
- **User Journey 003**: System Design & Shared Understanding — 9-phase journey with coordination rules and acceptance scenarios