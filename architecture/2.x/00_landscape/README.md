# 2.x System Landscape

| Field | Value |
|---|---|
| Status | Draft |
| Date | 2026-03-04 |
| Scope | C4 Level 0 — system landscape and domain container boundaries |
| Related ADRs | `2026-02-09-1..4`, `2026-02-17-1..3`, `2026-02-23-1..3`, `2026-02-27-1..3` |

## Purpose

Establish the canonical top-level framing for Spec Kitty 2.x: the domain
containers, their allowed interaction directions, and the interface contracts
between them. This is the north star that all lower-level C4 views (context,
container, component) must align to.

## Design Philosophy

Every container boundary in this view represents a **domain module with an
interface contract**. The current codebase provides the first concrete
implementation of each contract, but the design is deliberately
implementation-agnostic:

| Container (concept) | Current implementation | Could also be |
|---|---|---|
| Control Plane | CLI (`spec-kitty` commands) | TUI, web app, IDE plugin |
| Dashboard | `spec-kitty dashboard` (local browser kanban) | SaaS web view, IDE panel |
| Kitty-core | Python modules (specify, plan, tasks) | Same — domain logic |
| Event Store | Filesystem (JSONL, frontmatter, meta.json) | Database, cloud event store |
| Orchestration | Python modules (lifecycle engine, status) | Same — domain logic |
| Agent Tool Connectors | In-tool (`spec-kitty implement`) | Async shell, SDK, remote API |
| Doctrine | YAML artifacts in `src/doctrine/`; canonical skill packs in `src/doctrine/skills/`; deployment bridge in `src/specify_cli/skills/` | Same — knowledge artifacts, different deployment target |
| Constitution | Compiled governance bundle in `.kittify/` | Same — governance artifacts |
| Kernel | Zero-dependency shared primitives in `src/kernel/` | Same — utility layer |

Whether a module is in-process, a separate service, or a remote API is an
implementation detail — the contracts between them remain stable regardless.

## Architectural Principles

These principles govern all design decisions across the system. They were
established during the architecture discovery process and are non-negotiable
constraints for C4 container, component, and code-level design.

### 1. Interface-First Design

Every container boundary is an **interface contract**. The current codebase
provides the first concrete adapter behind each interface. Adding a new
deployment topology (separate service, remote API, alternative UI) means
implementing the existing interface — not restructuring the domain.

### 2. Implementation-Agnostic Domain Boundaries

Whether a module runs in-process, as a separate service, or as a remote API
is an **implementation detail irrelevant at the architectural level**. Domain
boundaries are defined by responsibility and contract, not by deployment
topology. This allows the system to evolve from a single CLI process toward
distributed deployment without architectural redesign.

### 3. Host-Owned State Authority

Lifecycle state mutation authority is **never delegated to external actors**.
Orchestration is pluggable, but state authority is not. External systems
(trackers, orchestrators, agent tools) consume host contracts and project
host state — they cannot become an alternate source of truth or bypass
lifecycle guards.

### 4. Local-First Operation

All external integrations (tracker sync, orchestrator APIs) are **optional
and feature-gated**. The system must function fully with filesystem-only
persistence and no network connectivity. This ensures that the core
planning → execution → review workflow is never blocked by external
service availability.

### 5. Governance at the Execution Boundary

Agent Tool Connectors inject **Doctrine and Constitution context into every
execution**, ensuring governance constraints are enforced regardless of which
connector implementation dispatches the work. Agents cannot bypass governance
or directly mutate lifecycle state — the connector is the enforcement point.

### 6. Event-Sourced Persistence

All state changes are **recorded as events**; current state is derived from
the event history. This is a conceptual model, not a deployment prescription —
the event log may be implemented as JSONL files, YAML frontmatter, metadata
JSON files, a database, or any combination. The principle ensures auditability,
reproducibility, and the ability to reconstruct state from history regardless
of the persistence mechanism.

## Domain Containers

### User

The Human in Charge. Interacts with the system through the Control Plane
(commands, interviews, approvals) and the Dashboard (read-only visibility).
Retains final acceptance authority over all governance and lifecycle decisions.

### Control Plane

The user-facing interaction surface. Accepts commands and routes them to
Kitty-core (planning workflows), Constitution (governance updates), and
Orchestration (execution control). The CLI is the current implementation.

### Kitty-core

The planning domain. Owns the Spec-Driven Development workflow:
specify → plan → tasks. Constructs the execution graph (WP dependency DAG)
driven by the **mission template** (a doctrine artifact defining the high-level
process) and the **concrete mission** (the user's requirements applied to that
template). Writes planning events to the Event Store.

> **Note:** "Mission" replaces "Feature" as the canonical term for a concrete
> unit of planned work. See [issue #241](https://github.com/Priivacy-ai/spec-kitty/issues/241).

### Event Store

Central persistence for all system state. Both Kitty-core and Orchestration
write events; Dashboard reads them. Today implemented as filesystem artifacts
(JSONL event logs, WP frontmatter, meta.json). Exposed through a service
layer / DDD repository interface so the backing store can change without
affecting consumers.

### Orchestration

The execution coordination domain. Reads current state from the Event Store
to make scheduling decisions. Controls execution order by dispatching work
to Agent Tool Connectors, respecting the dependency graph produced by
Kitty-core. Writes lifecycle and execution events back to the Event Store.

### Dashboard

Read-only visibility surface. Reads from the Event Store to present a kanban
view of mission progress, WP status, and execution history. Has no write path
to any other container.

### Agent Tool Connectors

Pluggable execution providers. Receive dispatched work from Orchestration and
execute it through whatever mechanism the connector implements (in-tool prompt,
async shell command, SDK call, remote API). Consume Doctrine and Constitution
at execution time to operate within governance constraints and with doctrine
context.

### Doctrine

The knowledge store. Contains typed, schema-validated governance artifacts:
directives, tactics, paradigms, styleguides, toolguides, agent profiles,
canonical skill packs, and mission templates.
Includes per-action governance indexes (`actions/<action>/index.yaml`) that
scope which artifacts apply to each execution phase within a mission.
Consumed by Constitution (compilation source and action-scoped intersection)
and by Agent Tool Connectors (execution-time governance context). The Skills
Installer (`specify_cli/skills/`) deploys canonical skill packs from
`doctrine/skills/` into agent directories during `spec-kitty init`. Doctrine
itself is standalone — it does not depend on any other container.

### Constitution

Compiled governance rules. Built from Doctrine artifacts through the
constitution interview flow (initiated via Control Plane by the User).
Consumed by Agent Tool Connectors at execution time. Depends on Doctrine
as its source material.

## System Landscape Diagram

```mermaid
flowchart TB
    user([fa:fa-user User])

    subgraph ControlPlane["Control Plane"]
        cp_desc["Create / Control\n(CLI, TUI, Web App)"]
    end

    subgraph KittyCore["Kitty-core"]
        kc_desc["Planning Domain\nspec / plan / tasks\nexecution graph construction"]
    end

    subgraph EventStore["Event Store"]
        es_desc["Central Persistence\n(filesystem / database)"]
    end

    subgraph Orchestration["Orchestration"]
        orch_desc["Execution Coordination\nscheduling / lifecycle / dispatch"]
    end

    subgraph Dashboard["Dashboard"]
        dash_desc["Read-only Visibility\nkanban / status / history"]
    end

    subgraph Connectors["Agent Tool Connectors"]
        conn_desc["Execution Providers\nSDK / prompt / shell"]
    end

    subgraph Doctrine["Doctrine"]
        doc_desc["Knowledge Store\ndirectives / tactics / paradigms\nstyleguides / toolguides\nmission templates"]
    end

    subgraph Constitution["Constitution"]
        const_desc["Governance Rules\ncompiled from Doctrine"]
    end

    %% User interactions
    user --> ControlPlane
    user --> Dashboard

    %% Control Plane routes
    ControlPlane --> KittyCore
    ControlPlane --> Constitution

    %% Kitty-core writes to Event Store
    KittyCore -- "writes" --> EventStore

    %% Event Store <-> Orchestration (bidirectional)
    Orchestration -- "reads" --> EventStore
    Orchestration -- "writes" --> EventStore

    %% Dashboard reads from Event Store
    Dashboard -- "reads" --> EventStore

    %% Orchestration dispatches to Connectors
    Orchestration --> Connectors

    %% Connectors use Doctrine and Constitution
    Connectors -. "uses" .-> Doctrine
    Connectors -. "uses" .-> Constitution

    %% Constitution uses Doctrine
    Constitution -. "uses" .-> Doctrine

    %% Styling
    classDef person fill:#E1F5FE,stroke:#0288D1,stroke-width:2px
    classDef control fill:#E0F7FA,stroke:#00838F,stroke-width:2px
    classDef core fill:#E0F7FA,stroke:#00838F,stroke-width:2px
    classDef store fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px
    classDef view fill:#F5F5F5,stroke:#616161,stroke-width:2px
    classDef knowledge fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px

    class user person
    class ControlPlane control
    class KittyCore core
    class Orchestration core
    class EventStore store
    class Dashboard view
    class Connectors knowledge
    class Doctrine knowledge
    class Constitution knowledge
```

## Interaction Contracts

| From | To | Direction | Contract |
|---|---|---|---|
| User | Control Plane | → | Commands, interview answers, approvals |
| User | Dashboard | → | Read-only queries (kanban, status) |
| Control Plane | Kitty-core | → | Planning workflow invocations (specify, plan, tasks) |
| Control Plane | Constitution | → | Governance interview flow, constitution updates |
| Kitty-core | Event Store | → write | Planning artifacts, mission events |
| Orchestration | Event Store | ↔ read/write | Reads state for scheduling; writes lifecycle/execution events |
| Dashboard | Event Store | ← read | WP status, mission progress, execution history |
| Orchestration | Agent Tool Connectors | → | Work dispatch (WP prompt, context, constraints) |
| Agent Tool Connectors | Doctrine | ← uses | Directive/tactic/paradigm context at execution time |
| Agent Tool Connectors | Constitution | ← uses | Governance rules at execution time |
| Constitution | Doctrine | ← uses | Source material for governance compilation |

## Dependency Rules

1. **Kernel is a root dependency** — zero-dependency shared primitives (`atomic_write`, etc.) consumed by `specify_cli`, `constitution`, and `doctrine`. Nothing imports from Kernel except to use its utilities; Kernel imports nothing from them.
2. **Doctrine is a root knowledge dependency** — consumed by Constitution and Agent Tool Connectors; depends on nothing except Kernel.
3. **Constitution depends only on Doctrine and Kernel** — never on Kitty-core, Orchestration, or Event Store.
4. **Event Store is a shared persistence boundary** — writers (Kitty-core, Orchestration) and readers (Dashboard, Orchestration) interact through interface contracts, never directly with each other through the store.
5. **Dashboard has no write path** — strictly read-only against Event Store.
6. **Agent Tool Connectors are leaf nodes** — they execute work and consume governance context; they do not write to other containers except through Orchestration (results/events flow back through Orchestration to Event Store).
7. **Orchestration does not bypass Kitty-core** — it executes the graph that Kitty-core produced; it does not construct planning artifacts.
8. **Control Plane is the single user entry point** for mutations — Dashboard is read-only.

## Traceability

- System context (C4 Level 1): `../01_context/README.md`
- Container view (C4 Level 2): `../02_containers/README.md`
- Component view (C4 Level 3): `../03_components/README.md`
- Domain breakdown: `../README.md#domain-breakdown`
- Usage flow: `../README.md#usage-flow-high-level-user-journey`
- Doctrine governance ADR: `../adr/2026-02-23-1-doctrine-artifact-governance-model.md`
- Mission rename: [issue #241](https://github.com/Priivacy-ai/spec-kitty/issues/241)
