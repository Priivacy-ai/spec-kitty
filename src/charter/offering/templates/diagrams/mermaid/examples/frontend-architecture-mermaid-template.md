# Mermaid Template: Frontend Architecture

Component-level front-end architecture overview. Highlights boundaries and
responsibilities in UI projects.

## Template

```mermaid
%%{init: {'theme':'base','themeVariables': {
  'fontFamily': 'Trebuchet MS, Verdana, Arial, sans-serif',
  'fontSize': '16px',
  'primaryColor': '#f5f5f5',
  'primaryTextColor': '#103a82',
  'primaryBorderColor': '#1c75cc',
  'lineColor': '#0a0721',
  'secondaryColor': '#eef3f7',
  'tertiaryColor': '#ffffff'
}}}%%
flowchart LR
    subgraph App["{{App Name}}"]
        UI["UI Shell"]
        R["Router"]
        FX["Feature - {{X}}"]
        FY["Feature - {{Y}}"]
        ST["State Store"]
        SVC["Services / Adapters"]
    end

    API["HTTP API"]
    AUTH["Auth"]
    CDN["CDN / Assets"]

    UI --> R
    R --> FX
    R --> FY
    FX --> ST
    FY --> ST
    ST <--> SVC
    SVC --> API
    UI --> CDN
    UI --> AUTH

    classDef core fill:#dceafd,stroke:#1168bd,color:#103a82,stroke-width:2px;
    classDef external fill:#f7f7f7,stroke:#8c9cab,color:#384b5f,stroke-width:1.5px;

    class UI,R,FX,FY,ST,SVC core;
    class API,AUTH,CDN external;
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
