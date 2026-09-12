# Mermaid Template: System Map

High-level system context map modeling reinforcing and undermining
relationships between concerns, goals, and techniques.

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
    SP1["Concern: {{Concern A}}"]
    SP2["Concern: {{Concern B}}"]

    HP1["Goal: {{Goal A}}"]
    HP2["Goal: {{Goal B}}"]

    TX["Technique: {{Technique X}}"]
    TY["Technique: {{Technique Y}}"]

    TX -- "s (reinforces)" --> SP1
    TY -- "s (reinforces)" --> SP2
    SP1 -. "o (undermines)" .-> HP1
    SP2 -. "o (undermines)" .-> HP2

    TX -- "s (reinforces)" --> SP2
    TY -. "o (undermines)" .-> HP1

    classDef concern fill:#DBA872,stroke:#9A4C2E,color:#160909,stroke-width:2px;
    classDef goal fill:#7FB3FF,stroke:#517B9A,color:#070829,stroke-width:2px;
    classDef technique fill:#99DB84,stroke:#389545,color:#0C1D0C,stroke-width:2px;

    class SP1,SP2 concern;
    class HP1,HP2 goal;
    class TX,TY technique;
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Concern A/B}}` | Organizational concern, risk, or destructive lever |
| `{{Goal A/B}}` | Desired outcome or health indicator |
| `{{Technique X/Y}}` | Technique, practice, or intervention |

## Notes

- Solid arrows (`-->`) represent reinforcing (same-direction) relationships.
- Dotted arrows (`.->`) represent undermining (opposite-direction) relationships.
- Color classes mirror the PlantUML stickies theme: orange for concerns,
  bright blue for goals, green for techniques.

## When to Use

- High-level stakeholder orientation before detailed architecture views.
- Mapping organizational concerns against techniques and goals.
- Workshop facilitation: quickly sketching system-level dynamics.
