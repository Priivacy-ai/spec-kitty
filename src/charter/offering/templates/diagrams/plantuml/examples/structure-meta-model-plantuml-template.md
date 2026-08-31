# PlantUML Template: Structure Meta Model

Sense-making meta model using C4 architecture elements. Shows conceptual
relationships between axioms, values, creeds, behaviors, and effects.

Uses remote C4-PlantUML includes from the PlantUML stdlib. Requires network
access during rendering or a local copy of the C4 libraries.

## Template

```plantuml
@startuml
title {{Meta Model Title}}

!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4.puml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

skinparam defaultFontName "Verdana"
skinparam defaultFontSize 14
skinparam wrapWidth 324

skinparam arrow {
  FontSize 8
  Thickness 1.25
}

AddElementTag("conceptual", $legendText="conceptual")
AddElementTag("actual", $legendText="actual")

Boundary(drivers, "Primary Drivers") {
  System(a, "{{Driver A}}", "{{Description A}}", $tags="conceptual")
  System(b, "{{Driver B}}", "{{Description B}}", $tags="conceptual")
  System_Ext(c, "{{External Driver}}", "{{Description C}}", $tags="actual")
}

System(d, "{{Derived Concept}}", "{{Description D}}", $tags="conceptual")
System(e, "{{Observable Behavior}}", "{{Description E}}", $tags="actual")
System_Ext(f, "{{Effects}}", "{{Description F}}", $tags="actual")

Rel(a, d, "reflected in")
Rel(b, e, "drives")
Rel_D(d, e, "drives")
Rel(c, e, "influences")
Rel_D(e, f, "produces")

SHOW_LEGEND()
@enduml
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Meta Model Title}}` | Title of the conceptual model |
| `{{Driver A/B}}` | Primary conceptual drivers |
| `{{External Driver}}` | External context or environmental factor |
| `{{Derived Concept}}` | Concept derived from drivers |
| `{{Observable Behavior}}` | Observable actions or patterns |
| `{{Effects}}` | Outcomes or consequences |
| `{{Description X}}` | Short description for each element |

## When to Use

- Domain modeling: showing how fundamental concepts relate.
- Philosophical or strategic architecture: values -> behaviors -> effects.
- C4-style context views for conceptual (non-technical) domains.
