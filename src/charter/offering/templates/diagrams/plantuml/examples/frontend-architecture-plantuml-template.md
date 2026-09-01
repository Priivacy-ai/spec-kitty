# PlantUML Template: Frontend Architecture

Component-level front-end architecture overview. Highlights boundaries and
responsibilities in UI projects.

## Template

```plantuml
@startuml FrontendArchitecture
skinparam backgroundColor #ffffff
skinparam defaultFontName "Inter, Roboto, Helvetica, Arial, sans-serif"
title Front-End Architecture - {{App Name}}

package "{{App Name}}" {
  [UI Shell] as UI
  [Router] as R
  [State Store] as ST
  [Services / Adapters] as SVC
  component "Feature - {{X}}" as FX
  component "Feature - {{Y}}" as FY
}

queue "HTTP API" as API
rectangle "Auth" as AUTH
rectangle "CDN / Assets" as CDN

UI --> R
R --> FX
R --> FY
FX --> ST
FY --> ST
ST <--> SVC
SVC --> API
UI --> CDN
UI --> AUTH

note right of SVC
  Adapter boundaries:
  - HTTP/REST/GraphQL
  - Caching & retries
  - Error normalization
end note

@enduml
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{App Name}}` | Application or front-end project name |
| `{{X}}`, `{{Y}}` | Feature module names |

## When to Use

- Documenting front-end component boundaries for design reviews.
- Showing the adapter layer between UI and back-end APIs.
- Onboarding developers to the front-end code structure.
