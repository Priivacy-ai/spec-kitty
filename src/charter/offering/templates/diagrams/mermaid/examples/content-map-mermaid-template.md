# Mermaid Template: Content Map

Content inventory diagram showing repository artifact relationships and
governance links.

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
flowchart TD
    ROOT["Repository Root"]

    subgraph Patterns
        P1["Pattern - {{Name 1}}"]
        P2["Pattern - {{Name 2}}"]
        P3["Pattern - {{Name 3}}"]
    end

    subgraph Docs
        D1["README.md"]
        D2["CONTRIBUTING.md"]
        D3["docs/WORKFLOWS.md"]
    end

    subgraph Context
        C1["Operational v1.0.0"]
        C2["Strategic v1.0.0"]
    end

    ROOT --> P1
    ROOT --> P2
    ROOT --> P3
    ROOT --> D1
    ROOT --> D2
    ROOT --> D3
    ROOT --> C1
    ROOT --> C2

    P1 -.- D3
    C1 -. "governs" .-> P1
    C1 -. "governs" .-> D1
    C1 -. "governs" .-> D3

    classDef core fill:#dceafd,stroke:#1168bd,color:#103a82,stroke-width:2px;
    classDef external fill:#f7f7f7,stroke:#8c9cab,color:#384b5f,stroke-width:1.5px;
    classDef storage fill:#fff6e7,stroke:#ea7400,color:#6e3d00,stroke-width:1.5px;

    class ROOT core;
    class C1,C2 storage;
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Name N}}` | Pattern, module, or artifact name |

## When to Use

- Mapping documentation topology of a repository.
- Showing governance relationships between context documents and content.
- Onboarding orientation for new contributors.
