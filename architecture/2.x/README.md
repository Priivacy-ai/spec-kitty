# Architecture 2.x

This directory is the current architecture track for Spec Kitty.

## What This Track Captures

1. Core architecture decisions and constraints (`adr/`).
2. End-to-end behavior expectations (`user_journey/`).
3. Active architecture initiatives (`initiatives/`).
4. Layered C4 documentation for system responsibilities and behavior:
   - `00_landscape/` (system landscape — canonical top-level framing)
   - `01_context/`
   - `02_containers/`
   - `03_components/`
5. Cross-cutting domain responsibility map (see [Domain Breakdown](#domain-breakdown) below).

## C4 Entrypoint Rule

Each C4 directory uses a single canonical entrypoint document:

- `01_context/README.md`
- `02_containers/README.md`
- `03_components/README.md`

Additional detailed pages can live beside the entrypoint files when needed.
This removes README indirection while preserving clear expansion space.

## Recommended Reading Order

1. [C4 System Landscape](00_landscape/README.md) (canonical top-level framing)
2. [Domain Breakdown](#domain-breakdown) (this file)
3. [Usage Flow High-Level User Journey](#usage-flow-high-level-user-journey)
4. [C4 Context](01_context/README.md)
5. [C4 Containers](02_containers/README.md)
6. [Runtime/Execution Domain Detail](02_containers/runtime-execution-domain.md)
7. [C4 Components](03_components/README.md)
8. [Implementation Mapping](04_implementation_mapping/README.md)
9. [Audience Personas](../audience/README.md)
10. [2.x ADR Index](adr/README.md)
11. [2.x User Journeys](user_journey/README.md)

---

## Domain Breakdown

| Field | Value |
|---|---|
| Status | Draft |
| Date | 2026-03-01 |
| Scope | 2.x domain responsibilities and behavior loops |
| Related ADRs | `2026-02-09-1..4`, `2026-02-17-1..3`, `2026-02-23-1..3`, `2026-02-27-1..3` |

### Purpose

Define the core behavioral domains in Spec Kitty 2.x so C4 context, container,
and component documents stay aligned and non-overlapping.

### Domain Map

| Domain | Core Responsibilities | Runtime Inputs | Runtime Outputs | Primary Audience | Primary Containers |
|---|---|---|---|---|---|
| Project and Governance Onboarding | Capture project intent, bootstrap governance defaults, and establish mission entry conditions | Project context, constitution interview answers | Compiled governance context, enabled mission surfaces | [Project Owner](../audience/external/project-owner.md), [Maintainer](../audience/internal/maintainer.md) | `CLI Command Surface`, `Constitution and Governance Engine` |
| Mission Runtime and Flow Control | Drive the canonical `next` loop, mission discovery, and action execution sequencing | Command intent, feature context, mission assets | Next-action decisions, routed lifecycle command intent | [AI Collaboration Agent](../audience/internal/ai-collaboration-agent.md), [Spec Kitty CLI Runtime](../audience/internal/spec-kitty-cli-runtime.md) | `Runtime and Mission Resolver`, `CLI Command Surface` |
| Doctrine and Knowledge Governance | Load and validate doctrine assets, maintain glossary compatibility, and provide policy context | Doctrine catalog assets, glossary checks, governance constraints | Validated policy/context artifacts for runtime use | [System Architect](../audience/internal/system-architect.md), [AI Collaboration Agent](../audience/internal/ai-collaboration-agent.md) | `Doctrine Artifact Catalog`, `Glossary Corpus and Runtime Hook Layer` |
| Work Package State and Evidence | Enforce canonical lifecycle transitions, event semantics, and evidence quality boundaries | Routed lifecycle mutation commands, transition evidence payloads | Event log entries, state snapshot materialization, auditable transition history | [Lead Developer](../audience/internal/lead-developer.md), [Maintainer](../audience/internal/maintainer.md) | `Status and Event Model Layer`, `Runtime and Mission Resolver` |
| External Integration Boundaries | Expose orchestrator and tracker integration surfaces without transferring host state authority | Host state/events, sync configuration, auth availability | Optional external projection, orchestrator contract responses | [Spec Kitty CLI Runtime](../audience/internal/spec-kitty-cli-runtime.md), [System Architect](../audience/internal/system-architect.md) | `Orchestrator API Boundary`, `Tracker Connector Boundary` |

### Core Behavioral Loops

```mermaid
flowchart LR
    onboarding[Project and Governance Onboarding]
    runtime[Mission Runtime and Flow Control]
    doctrine[Doctrine and Knowledge Governance]
    state[Work Package State and Evidence]
    external[External Integration Boundaries]

    onboarding --> runtime
    runtime --> doctrine
    runtime --> state
    doctrine --> runtime
    state --> runtime
    runtime --> external
    external --> state
```

### Domain Invariants

#### Runtime Decisioning vs State Mutation

1. Mission runtime decides what should happen next.
2. Status/event model validates and persists what did happen.
3. Runtime may recommend a transition, but only the status/event model can apply it.
4. This split preserves deterministic decisioning and auditable mutation authority.

#### Branch Topology and Target-Line Routing

1. Feature metadata is the authority source for target-line routing (`target_branch`).
2. Lifecycle commits route to the feature target line (`main` for legacy, `2.x` or other explicit value when set).
3. Worktree execution context must not override target-line authority.
4. Cross-domain usage flow reference: [Usage Flow High-Level User Journey](#usage-flow-high-level-user-journey).

#### Work Package Lifecycle and Execution Model

Detailed runtime/execution lifecycle modeling (including canonical FSM,
transition guards, and branch-target routing invariants) is documented in:
[Runtime/Execution Domain (Container Detail)](02_containers/runtime-execution-domain.md).

#### Sync Reliability and Runtime Asset Lifecycle

1. Sync behavior is not only a connector boundary; it depends on internal reliability primitives:
   identity attribution, Lamport ordering, offline queue persistence, and runtime lifecycle coordination.
2. Runtime asset lifecycle includes deterministic tiered resolution and controlled migration behavior.
3. These behaviors remain host-owned and feed both runtime decisioning and projection reliability.

### Loop Notes

1. Onboarding initializes constraints and defaults consumed by runtime execution.
2. Runtime consumes doctrine/glossary context conditionally, based on mission and configured checks.
3. Runtime decisioning and state mutation are separate loops connected by explicit command handoff.
4. State and evidence outputs can be projected to external systems through gated boundaries.
5. External integrations are adapters, not alternate owners of lifecycle state.

### Traceability Pointers

- Context framing: `01_context/README.md`
- Container responsibility model: `02_containers/README.md`
- Component behavior model: `03_components/README.md`
- Usage flow reference: [Usage Flow High-Level User Journey](#usage-flow-high-level-user-journey)
- Audience persona catalog: `../audience/README.md`

---

## Usage Flow High-Level User Journey

| Field | Value |
|---|---|
| Status | Draft |
| Date | 2026-03-01 |
| Scope | Generic end-to-end execution and authority flow for Spec Kitty 2.x |
| Related ADRs | `2026-02-09-1`, `2026-02-09-2`, `2026-02-17-1`, `2026-01-29-13` |

### Purpose

Provide a generic, implementation-aligned usage flow that the C4 context,
container, and component views can reference.

### High-Level Flow

```mermaid
flowchart LR
    hic[Human in Charge]
    agent[AI Agent\n'generic-agent' or specialist]
    runtime[Runtime Decisioning]
    status[Status Mutation Engine]
    repo[Repository State]
    sync[Optional Sync Projection]

    hic -->|invoke command| runtime
    runtime -->|recommend next action + assign executor| hic
    hic -->|HiC WP: human executes directly| status
    hic -->|agent WP: dispatch to agent| agent
    agent -->|execute with specialist profile injected| agent
    agent -->|lifecycle mutation command| status
    status -->|persist events and snapshot| repo
    status -->|project events when enabled| sync
```

### WP Executor Assignment

Work packages are assigned an executor via the `agent_profile` frontmatter field:

| Value | Executor | Behaviour |
|---|---|---|
| _(absent)_ | AI agent — `generic-agent` default | Generic governance injected; no specialist identity |
| `architect`, `implementer`, etc. | AI agent — specialist profile | Specialist identity fragment injected at execution time |
| `human-in-charge` | Human (HiC) | Sentinel profile — no agent context injected; WP appears with 👤 marker in kanban |

The `human-in-charge` value is a **workflow sentinel**, not an agent identity. It signals that the WP requires direct human execution or collaborative human-AI work. The Human in Charge retains final acceptance authority regardless of executor assignment.

### Authority Notes

1. Runtime decisioning and status mutation are separate responsibilities.
2. Runtime decides what should happen next; executor assignment communicates *who* acts.
3. Status engine validates and persists what did happen — authority is independent of executor.
4. Lifecycle persistence is host-authoritative and event-sourced.
5. External projections do not own canonical lifecycle state.
6. The Human in Charge is always accountable; agent executor assignment is a coordination signal, not a delegation of responsibility.

### Branch and Target-Line Routing (Generic)

1. Each feature carries routing intent in feature metadata.
2. Lifecycle/status commits are routed to the feature target line.
3. Invocation location (for example, main repo vs worktree) does not transfer
   lifecycle authority away from the configured target line.
4. Legacy features without explicit target-line metadata use default routing.

### Lifecycle Model Reference

See [C4 Components](03_components/README.md) for the canonical lifecycle FSM
diagram and transition guard summary.

## Structural Breakdown (Hierarchy)

```mermaid
flowchart TD
    root["architecture/2.x/"]

    readme["README.md (domain-breakdown + usage-flow)"]
    c1dir["01_context/"]
    c1doc["README.md"]
    c2dir["02_containers/"]
    c2doc["README.md"]
    c2detail["runtime-execution-domain.md"]
    c3dir["03_components/"]
    c3doc["README.md"]
    audience["../audience/README.md"]
    adrdir["adr/README.md"]
    ujdir["user_journey/README.md"]
    initdir["initiatives/README.md"]

    root --> readme
    c0dir["00_landscape/"]
    c0doc["README.md"]
    root --> c0dir
    c0dir --> c0doc
    root --> c1dir
    c1dir --> c1doc
    root --> c2dir
    c2dir --> c2doc
    c2dir --> c2detail
    root --> c3dir
    c3dir --> c3doc
    c4dir["04_implementation_mapping/"]
    c4doc["README.md"]
    root --> c4dir
    c4dir --> c4doc
    root --> adrdir
    root --> ujdir
    root --> initdir
    root --> audience

    click readme "README.md" "Domain Breakdown and Usage Flow"
    click c1doc "01_context/README.md" "C4 Context"
    click c2doc "02_containers/README.md" "C4 Containers"
    click c2detail "02_containers/runtime-execution-domain.md" "Runtime/Execution Domain Detail"
    click c3doc "03_components/README.md" "C4 Components"
    click audience "../audience/README.md" "Audience Personas"
    click adrdir "adr/README.md" "2.x ADR Index"
    click ujdir "user_journey/README.md" "2.x User Journeys"
    click initdir "initiatives/README.md" "2.x Initiatives"
```

## Scope Guardrail

Do not duplicate code-level inventories or class-level maps in architecture docs.
Code-level tracking belongs in `src/` README and package-level documentation.
