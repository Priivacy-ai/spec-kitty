# PlantUML Template: Content Map

Content inventory diagram showing repository artifact relationships and
governance links. Useful for mapping documentation artifacts and their
dependencies.

## Template

```plantuml
@startuml ContentMap
skinparam backgroundColor #ffffff
skinparam defaultFontName "Inter, Roboto, Helvetica, Arial, sans-serif"

title Content Map - {{Repository/Project}}

package "Patterns" {
  node "Pattern - {{Name 1}}" as P1
  node "Pattern - {{Name 2}}" as P2
  node "Pattern - {{Name 3}}" as P3
}

package "Docs" {
  artifact "README.md" as D1
  artifact "CONTRIBUTING.md" as D2
  artifact "docs/WORKFLOWS.md" as D3
}

package "Context" {
  folder "Operational v1.0.0" as C1
  folder "Strategic v1.0.0" as C2
}

rectangle "Repository Root" as ROOT

ROOT --> P1
ROOT --> P2
ROOT --> P3
ROOT --> D1
ROOT --> D2
ROOT --> D3
ROOT --> C1
ROOT --> C2

' Cross-links and governance
P1 .. D3
C1 .down.> P1 : governs
C1 .down.> D1 : governs
C1 .down.> D3 : governs

@enduml
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Repository/Project}}` | Repository or project name |
| `{{Name N}}` | Pattern, module, or artifact name |

## When to Use

- Mapping the documentation topology of a repository.
- Showing governance relationships between context documents and content.
- Onboarding orientation: "here is what lives where and who owns it."
