# User Journey: [Journey Title]

<!--
  Design Mission Template: User Journey
  
  Purpose: Capture a structured, end-to-end user journey that spans actors,
  system boundaries, and coordination concerns. Unlike a User Story (single
  slice of value), a User Journey maps the full flow across phases, actors,
  and responsibilities.

  When to use:
  - Multi-actor workflows (humans + AI agents + services)
  - Flows that cross system boundaries (CLI ↔ SaaS, local ↔ remote)
  - Collaborative or concurrent scenarios requiring coordination rules
  - Features where observability, presence, or governance matter

  When NOT to use (use a User Story in spec.md instead):
  - Single-actor, single-system interactions
  - Simple CRUD operations
  - Features fully captured by a BDD acceptance scenario

  Source: Derived from https://gist.github.com/robertDouglass/e5b53e360fcee01bd9bebd7e33850ebf
  Doctrine alignment: Traceable Decisions (decision capture), Human In Charge
  (actor attribution), Locality of Change (scope boundaries)
-->

**Status**: DRAFT | REVIEW | ACCEPTED
**Date**: YYYY-MM-DD
**Primary Contexts**: [Domain contexts this journey lives in]
**Supporting Contexts**: [Domain contexts this journey touches]
**Related Spec**: [Link to spec.md or domain spec, if applicable]

---

## Scenario

<!--
  One paragraph framing what this journey accomplishes and why it matters.
  Include the initial product slice or MVP scope if applicable.
-->

[Describe the end-to-end scenario in 2-4 sentences. What are participants
trying to achieve? What is the initial scope boundary?]

---

## Actors

<!--
  List every participant type. Annotate with role classification:
  - `human`  — a person (developer, reviewer, admin, end user)
  - `llm`    — an AI/LLM execution context
  - `system` — an automated service, daemon, or infrastructure component

  For each actor, one line: what they do in this journey.

  PERSONA LINK: Each actor maps to a full stakeholder persona. If the persona
  doesn't exist yet, create one using the companion `stakeholder-persona-template.md`.
  The Actor table here is the inline summary; the Persona file is the deep profile.

  Relationship:
    Actor table (this file)     →  lightweight, inline, journey-scoped
    stakeholder-persona-template.md  →  full profile: motivations, frustrations,
                                        behavioral cues, collaboration preferences,
                                        measures of success

  Use Persona ID to cross-reference. When an actor's behavior in a journey phase
  seems surprising, the full persona explains why (via Behavioral Cues and
  Frustrations sections).
-->

| # | Actor | Type | Persona | Role in Journey |
|---|-------|------|---------|-----------------|
| 1 | [Actor Name] | `human` | [Persona ID or link] | [What they do] |
| 2 | [Actor Name] | `llm` | [Persona ID or link] | [What they do] |
| 3 | [Actor Name] | `system` | [Persona ID or link] | [What they do] |

---

## Preconditions

<!--
  What must be true before this journey can begin?
  Include technical prerequisites, access requirements, and state assumptions.
-->

1. [Precondition 1]
2. [Precondition 2]
3. [Precondition 3]

---

## Journey Map

<!--
  The core of the template. Each row is a phase in the journey.
  
  Columns:
  - Phase:        Sequential phase name (verb-based: Start, Observe, Decide...)
  - Actor(s):     Who is active in this phase (reference actor table)
  - System:       What the system/service does in this phase
  - Key Events:   Domain events emitted (use PascalCase event names)
  
  Adapt column headers to your domain. The gist used "Local Participant(s)"
  and "SaaS" — rename to match your system boundaries.
-->

| Phase | Actor(s) | System | Key Events |
|-------|----------|--------|------------|
| 1. [Phase Name] | [Who acts] | [What system does] | `EventName1`, `EventName2` |
| 2. [Phase Name] | [Who acts] | [What system does] | `EventName3` |
| 3. [Phase Name] | [Who acts] | [What system does] | `EventName4`, `EventName5` |
| 4. [Phase Name] | [Who acts] | [What system does] | `EventName6` |
| 5. [Phase Name] | [Who acts] | [What system does] | `EventName7`, `EventName8` |

---

## Coordination Rules

<!--
  How do actors coordinate when their actions overlap or conflict?
  
  Choose a default posture:
  - **Advisory** (soft): Warnings emitted, no blocking. Actors decide.
  - **Gated** (medium): Progression paused until acknowledgement.
  - **Locked** (hard): Exclusive access enforced via leases.
  
  List the rules as numbered statements. Be explicit about defaults.
-->

**Default posture**: [Advisory | Gated | Locked]

1. [Rule 1 — e.g., "Multiple active drivers are valid state"]
2. [Rule 2 — e.g., "Overlap on same artifact emits warning; default is advisory"]
3. [Rule 3 — e.g., "Progression continues after explicit acknowledgement"]
4. [Rule 4]

---

## Responsibilities

<!--
  Split responsibilities by system boundary. Adapt headers to your domain.
  Examples: CLI / SaaS, Frontend / Backend, Agent / Orchestrator, Local / Remote
-->

### [Boundary A] (e.g., CLI / Local Runtime)

1. [Responsibility 1]
2. [Responsibility 2]
3. [Responsibility 3]

### [Boundary B] (e.g., SaaS / Cloud Service)

1. [Responsibility 1]
2. [Responsibility 2]
3. [Responsibility 3]

---

## Scope: [Milestone Name] (e.g., M1, MVP, Phase 1)

<!--
  Define what's IN and OUT of the initial delivery scope.
  Use two sections: Observe (read-only capabilities) and Decide (write/action capabilities).
  Adapt categories to your domain.
-->

### In Scope

1. **Observe**:
   - [What participants can see/monitor]
   - [What state is projected/visible]

2. **Decide**:
   - [What actions participants can take]
   - [What decisions are captured]

### Out of Scope (Deferred)

- [Capability deferred to future milestone]
- [Capability deferred to future milestone]

---

## Required Event Set

<!--
  List all domain events this journey requires. These become the contract
  between system boundaries. Use PascalCase naming.
  
  Group by phase or concern if the list is long (>10 events).
  This section directly informs the EventBridge / telemetry implementation.
-->

| # | Event | Emitted By | Phase |
|---|-------|-----------|-------|
| 1 | `EventName` | [Actor/System] | [Phase #] |
| 2 | `EventName` | [Actor/System] | [Phase #] |

---

## Acceptance Scenarios

<!--
  BDD-style Given/When/Then scenarios that validate the journey.
  Each scenario should be independently testable.
  Number them for traceability (link from work packages).
-->

1. **[Scenario Title]**
   Given [precondition],
   when [action],
   then [expected outcome].

2. **[Scenario Title]**
   Given [precondition],
   when [action],
   then [expected outcome].

3. **[Scenario Title]**
   Given [precondition],
   when [action],
   then [expected outcome].

---

## Design Decisions

<!--
  Link to ADRs or decision markers relevant to this journey.
  If no ADRs exist yet, capture inline decisions with rationale.
  
  Doctrine alignment: Traceable Decisions — every design choice recorded.
-->

| Decision | Rationale | ADR |
|----------|-----------|-----|
| [What was decided] | [Why] | [Link or "pending"] |

---

## Product Alignment

<!--
  How does this journey align with broader product principles?
  Keep to 3-5 bullet points. Reference governance principles if applicable.
-->

1. [Alignment statement 1]
2. [Alignment statement 2]
3. [Alignment statement 3]
