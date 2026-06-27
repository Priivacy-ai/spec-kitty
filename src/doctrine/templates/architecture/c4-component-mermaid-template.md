# C4 Level 3: Components

| Field | Value |
|---|---|
| Status | Draft |
| Date | YYYY-MM-DD |
| Scope | Logical components inside key containers |
| Related ADRs | `architecture/2.x/adr/...` |

## Purpose

Describe component boundaries and responsibilities without code-level inventories.

## Component Diagram (Mermaid)

```mermaid
flowchart TB
    subgraph CLI["CLI Command Surface"]
      cmd[Command Router]
      wf[Workflow Commands]
      cfg[Configuration Commands]
    end

    subgraph Runtime["Runtime and Mission Resolver"]
      loop[Next Loop Coordinator]
      discover[Mission Discovery and Resolution]
      render[Template Resolution]
    end

    subgraph Governance["Charter and Governance Engine"]
      interview[Interview Flow]
      compiler[Charter Compiler]
      context[Charter Context Resolver]
    end

    cmd --> loop
    wf --> loop
    loop --> discover
    discover --> render
    cfg --> interview
    interview --> compiler
    compiler --> context
```

## Component Responsibilities

| Component | Responsibility |
|---|---|
| Command Router | Dispatches command invocations |
| Workflow Commands | Feature/task lane transitions and execution surface |
| Next Loop Coordinator | Canonical per-agent loop orchestration |
| Mission Discovery and Resolution | Mission/runtime lookup and precedence |
| Template Resolution | Prompt/template retrieval for resolved action |
| Interview Flow | Captures governance/charter intent |
| Charter Compiler | Produces charter bundle artifacts |
| Charter Context Resolver | Provides action-scoped charter context |

## Boundary and Coupling Notes

1. Stable boundaries.
2. Intentional couplings.
3. Guardrails against drift.

## Traceability

List links to ADRs and companion C4 levels.
