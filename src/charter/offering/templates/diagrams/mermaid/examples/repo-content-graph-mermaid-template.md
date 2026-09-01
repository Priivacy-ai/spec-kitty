# Mermaid Template: Repo Content Graph

Repository structure graph mapping artifacts to audience segments. Shows
governance relationships between context documents and content.

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
    A1(("Developers"))
    A2(("Architects"))
    A3(("{{Audience 3}}"))

    F1["{{Folder 1}}/"]
    F2["{{Folder 2}}/"]
    F3["docs/WORKFLOWS.md"]
    F4["README.md"]
    F5["context/*"]

    F1 --> A1
    F1 --> A2
    F2 --> A3
    F3 --> A1
    F4 --> A1
    F4 --> A3
    F5 -. "governs" .-> F1
    F5 -. "governs" .-> F2
    F5 -. "governs" .-> F3
    F5 -. "governs" .-> F4

    classDef audience fill:#eef3f7,stroke:#1c75cc,color:#103a82,stroke-width:2px;
    classDef artifact fill:#f7f7f7,stroke:#8c9cab,color:#384b5f,stroke-width:1.5px;
    classDef context fill:#fff6e7,stroke:#ea7400,color:#6e3d00,stroke-width:1.5px;

    class A1,A2,A3 audience;
    class F1,F2,F3,F4 artifact;
    class F5 context;
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
