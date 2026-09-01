# PlantUML Template: Request Lifecycle

Sequence diagram modeling a request flow through system components. Shows
ingress/egress points and processing stages.

## Template

```plantuml
@startuml RequestLifecycle
autonumber
skinparam backgroundColor #ffffff
skinparam sequenceArrowThickness 1
skinparam defaultFontName "Inter, Roboto, Helvetica, Arial, sans-serif"
title Request Lifecycle - {{Task}}

actor User as U
participant "{{Agent / Service}}" as AG
database "{{Data Store}}" as KB
participant "{{Pipeline / CI}}" as CI

U ->> AG: Request + constraints ({{task}})
AG ->> KB: Load context / configuration
KB -->> AG: Context OK / Mismatch
AG -> AG: Analyze -> Plan
AG ->> U: Clarify ambiguities (if needed)
U -->> AG: Answers / approvals
AG -> AG: Generate artifacts (FIRST PASS)
AG ->> U: Diffs + summary
U -->> AG: Approve changes
AG ->> CI: Commit & trigger pipeline
CI -->> U: Build/Test status

@enduml
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Task}}` | Name of the task or request being modeled |
| `{{Agent / Service}}` | The processing agent, service, or component |
| `{{Data Store}}` | Database, context stack, or configuration source |
| `{{Pipeline / CI}}` | CI/CD pipeline or downstream consumer |
| `{{task}}` | Short description of the request payload |

## When to Use

- Documenting how a user request flows through the system end-to-end.
- Clarifying async vs sync interaction boundaries.
- Design reviews for request handling pipelines.
