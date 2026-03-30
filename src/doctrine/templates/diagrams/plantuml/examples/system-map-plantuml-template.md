# PlantUML Template: System Map

High-level system context map using colored sticky notes. Good for orienting
stakeholders before deeper component views. Models reinforcing and undermining
relationships between techniques and organizational concerns.

## Template

```plantuml
@startuml SystemMap

!include ../themes/puml-theme-stickies.puml

skinparam backgroundColor #ffffff
skinparam defaultFontName "Inter, Roboto, Helvetica, Arial, sans-serif"

' === NODES (replace {{...}} with concrete items) ===
Sticky_Orange(SP1, "Concern: {{Concern A}}")
Sticky_Orange(SP2, "Concern: {{Concern B}}")

Sticky_BrightBlue(HP1, "Goal: {{Goal A}}")
Sticky_BrightBlue(HP2, "Goal: {{Goal B}}")

Sticky_Green(TX, "Technique: {{Technique X}}")
Sticky_Green(TY, "Technique: {{Technique Y}}")

' === RELATIONSHIPS (s/o) ===
s(TX, SP1)
s(TY, SP2)
o(SP1, HP1)
o(SP2, HP2)

' Optional cross-couplings
s(TX, SP2)
o(TY, HP1)

' Legend
legend left
|= Color |= Meaning |
|<#FFA64D> | Concerns / Risks |
|<#7FB3FF> | Goals / Health Indicators |
|<#76D275> | Techniques / Interventions |
Relationships:
- s : reinforces (positive correlation)
- o : undermines (inverse correlation)
endlegend

@enduml
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Concern A/B}}` | Organizational concern, risk, or destructive lever |
| `{{Goal A/B}}` | Desired outcome or health indicator |
| `{{Technique X/Y}}` | Technique, practice, or intervention |

## When to Use

- High-level stakeholder orientation before detailed architecture views.
- Mapping organizational concerns against techniques and goals.
- Workshop facilitation: quickly sketching system-level dynamics.
