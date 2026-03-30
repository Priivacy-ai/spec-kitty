# PlantUML Template: Event Storming

Event Storming visual template following standard sticky note color
conventions (Alberto Brandolini). Models the flow from actors through
commands, domain events, and policies.

## Template

```plantuml
@startuml EventStorming

title Event Storming - {{Context Name}}

' Domain Events (Orange)
rectangle "{{Event 1}}" #FF8C00
rectangle "{{Event 2}}" #FF8C00
rectangle "{{Event 3}}" #FF8C00

' Commands (Light Blue)
rectangle "{{Command 1}}" #87CEEB
rectangle "{{Command 2}}" #87CEEB

' Actors (Blue)
actor "{{Actor 1}}" #4169E1
actor "{{Actor 2}}" #4169E1

' Policies (Purple)
rectangle "{{Policy 1}}\n(automation)" #9370DB

' Aggregates (Yellow)
rectangle "{{Aggregate 1}}" #FFFF00

' Read Models (Green)
rectangle "{{Read Model 1}}" #90EE90

' Flow
"{{Actor 1}}" --> "{{Command 1}}"
"{{Command 1}}" --> "{{Event 1}}"
"{{Event 1}}" --> "{{Policy 1}}\n(automation)"
"{{Policy 1}}\n(automation)" --> "{{Command 2}}"
"{{Command 2}}" --> "{{Event 2}}"
"{{Event 2}}" --> "{{Event 3}}"

legend right
|= Color |= Element |
|<#FF8C00> | Domain Event |
|<#87CEEB> | Command |
|<#4169E1> | Actor |
|<#9370DB> | Policy / Automation |
|<#FFFF00> | Aggregate |
|<#90EE90> | Read Model |
endlegend

@enduml
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Context Name}}` | Bounded context or domain area being stormed |
| `{{Event N}}` | Domain event name (past tense, e.g., "OrderPlaced") |
| `{{Command N}}` | Command name (imperative, e.g., "PlaceOrder") |
| `{{Actor N}}` | Actor or role triggering commands |
| `{{Policy N}}` | Policy or automation rule reacting to events |
| `{{Aggregate N}}` | Aggregate root name |
| `{{Read Model N}}` | Read model or projection name |

## When to Use

- DDD discovery workshops: identifying domain events, commands, and aggregates.
- Bounded context boundary exploration.
- Onboarding domain experts to the event-first modeling approach.
