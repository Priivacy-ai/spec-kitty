# PlantUML Template: Repo Content Graph

Repository structure graph mapping artifacts to audiences. Intentionally
avoids theming to teach raw PlantUML composition.

## Template

```plantuml
@startuml RepoContentGraph
skinparam backgroundColor #ffffff
skinparam defaultFontName "Inter, Roboto, Helvetica, Arial, sans-serif"
title Repo Content Graph - Artifacts -> Audiences

cloud "Developers" as A1
cloud "Architects" as A2
cloud "{{Audience 3}}" as A3

folder "{{Folder 1}}/" as F1
folder "{{Folder 2}}/" as F2
artifact "docs/WORKFLOWS.md" as F3
artifact "README.md" as F4
folder "context/*" as F5

F1 --> A1
F1 --> A2
F2 --> A3
F3 --> A1
F4 --> A1
F4 --> A3
F5 .down.> F1 : governs
F5 .down.> F2 : governs
F5 .down.> F3 : governs
F5 .down.> F4 : governs

@enduml
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Audience 3}}` | Target audience segment |
| `{{Folder N}}` | Repository folder or module name |

## When to Use

- Mapping which artifacts serve which audience segments.
- Governance visualization: which context documents govern which content.
- Repository orientation for new contributors.
