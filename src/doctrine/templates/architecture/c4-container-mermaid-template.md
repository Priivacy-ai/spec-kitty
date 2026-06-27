# C4 Level 2: Containers

| Field | Value |
|---|---|
| Status | Draft |
| Date | YYYY-MM-DD |
| Scope | Deployable/runtime containers and major subsystems |
| Related ADRs | `architecture/2.x/adr/...` |

## Purpose

Describe the major runtime/application containers and their responsibilities.

## Container Diagram (Mermaid)

```mermaid
flowchart TB
    subgraph Host["Spec Kitty Host"]
      cli[CLI Command Surface]
      runtime[Runtime and Mission Resolver]
      governance[Charter and Governance Engine]
      doctrine[Doctrine Artifact Catalog]
      glossary[Glossary Corpus and Hook Layer]
      api[Orchestrator API]
      tracker[Tracker Connector Boundary]
    end

    cli --> runtime
    cli --> governance
    runtime --> doctrine
    runtime --> glossary
    api --> runtime
    api --> tracker
```

## Container Responsibilities

| Container | Responsibility |
|---|---|
| CLI Command Surface | User and agent entrypoint |
| Runtime and Mission Resolver | Canonical `next` loop and mission resolution |
| Charter and Governance Engine | Charter interview/generate/context/status/sync |
| Doctrine Artifact Catalog | Typed directives/tactics/styleguides/templates |
| Glossary Corpus and Hook Layer | Context glossary and runtime glossary checks |
| Orchestrator API | External automation contract |
| Tracker Connector Boundary | Tracker integration handoff point |

## Interaction Notes

1. Primary data/control flows.
2. Safety/authority constraints.
3. Known limitations.

## Traceability

List links to ADRs and companion C4 levels.
