# Mermaid Template: Structure Meta Model

Conceptual meta model showing relationships between foundational drivers,
derived concepts, behaviors, and effects. Mermaid equivalent of the C4-based
PlantUML structure template.

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
    subgraph Drivers["Primary Drivers"]
        A["{{Driver A}}"]
        B["{{Driver B}}"]
        C["{{External Driver}}"]
    end

    D["{{Derived Concept}}"]
    E["{{Observable Behavior}}"]
    F["{{Effects}}"]

    A -- "reflected in" --> D
    A -- "constrains" --> E
    B -- "drives" --> E
    B -- "reflected in" --> D
    D -- "drives" --> E
    C -- "influences" --> E
    C -- "drives" --> F
    E -- "produces" --> F

    classDef conceptual fill:#dceafd,stroke:#1168bd,color:#103a82,stroke-width:2px;
    classDef actual fill:#f7f7f7,stroke:#8c9cab,color:#384b5f,stroke-width:1.5px;
    classDef external fill:#fff6e7,stroke:#ea7400,color:#6e3d00,stroke-width:1.5px;

    class A,B,D conceptual;
    class E actual;
    class C,F external;
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Driver A/B}}` | Primary conceptual drivers (e.g., Axioms, Values) |
| `{{External Driver}}` | External context or environmental factor |
| `{{Derived Concept}}` | Concept derived from drivers (e.g., Creeds, Principles) |
| `{{Observable Behavior}}` | Observable actions or patterns |
| `{{Effects}}` | Outcomes or consequences |

## When to Use

- Domain modeling: showing how fundamental concepts relate.
- Strategic architecture: values -> behaviors -> effects chains.
- Conceptual (non-technical) domain visualization.
