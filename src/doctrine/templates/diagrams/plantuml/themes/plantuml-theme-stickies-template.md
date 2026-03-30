# PlantUML Theme: Stickies

Workshop-style theme providing colored sticky note macros for brainstorming,
event storming, causal mapping, and exploratory design sessions. Extends the
bluegray palette with sticky-note-specific colors and causal relationship
primitives.

Author: Stijn Dejongh (2024, SD Development BV).

## Snippet

Include the theme file at the top of your `.puml` file.

```plantuml
@startuml
!include <relative-path>/puml-theme-stickies.puml

skinparam backgroundColor #ffffff

' Sticky notes
Sticky_Orange(a, "Risk: {{description}}")
Sticky_Blue(b, "Action: {{description}}")
Sticky_Green(c, "Outcome: {{description}}")

' Causal relationships
s(a, b)
o(a, c)

@enduml
```

## Sticky Note Macros

| Macro | Color | Typical Use |
|---|---|---|
| `Sticky(alias, label)` | Yellow | General-purpose |
| `Sticky_Orange(alias, label)` | Orange | Risks, domain events, warnings |
| `Sticky_Blue(alias, label)` | Blue | Actions, commands, calm items |
| `Sticky_BrightBlue(alias, label)` | Bright Blue | Health indicators, positive items |
| `Sticky_Green(alias, label)` | Green | Outcomes, techniques, positive |
| `Sticky_Purple(alias, label)` | Purple | Policies, automation, categorization |
| `Sticky_Pink(alias, label)` | Pink | People, actors, roles |
| `Sticky_Gray(alias, label)` | Gray | Deferred, archived, low-priority |

All macros accept optional `$descr` and `$sprite` parameters.

## Causal Relationship Macros

| Macro | Meaning | Visual |
|---|---|---|
| `s(start, end)` / `same(start, end)` | Reinforces (positive correlation) | Dark blue arrow |
| `o(start, end)` / `opposite(start, end)` | Undermines (inverse correlation) | Red arrow with bold "O" label |

Both accept an optional `$descr` parameter that renders as a note on the link.

## Recommended Use

1. Causal maps and systems-thinking diagrams.
2. Event storming boards.
3. Workshop ideation and planning visuals.
4. Any diagram where provisional/exploratory status should be visually signaled.
