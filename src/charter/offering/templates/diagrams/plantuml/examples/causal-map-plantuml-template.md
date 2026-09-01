# PlantUML Template: Causal Map

Cause-effect relationship diagram using sticky note macros.
Model causal links between practices, outcomes, and risks.

## Template

```plantuml
@startuml CausalMap
!include ../themes/puml-theme-stickies.puml

hide empty description
skinparam backgroundColor #ffffff

' Nodes
Sticky_Blue(PX, "Practice: {{X}}")
Sticky_Green(OY, "Outcome: {{Y}}")
Sticky_Orange(RZ, "Risk: {{Z}}")

' Edges
s(PX, OY): s (reinforces)
o(PX, RZ) : o (undermines)\n(if constraints satisfied)
o(RZ, OY)

note right of PX
  Preconditions:
  - {{precondition 1}}
  - {{precondition 2}}
end note

@enduml
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{X}}` | Practice or technique name |
| `{{Y}}` | Desired outcome |
| `{{Z}}` | Risk or failure mode |
| `{{precondition N}}` | Entry conditions or assumptions |

## When to Use

- Systems thinking: mapping reinforcing and undermining feedback loops.
- Risk-benefit analysis for architecture or process decisions.
- ADR support: visualizing why a decision was made given trade-offs.
