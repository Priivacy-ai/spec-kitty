# Mermaid Template: Causal Map

Cause-effect relationship diagram using Mermaid flowchart. Models reinforcing
and undermining causal links between practices, outcomes, and risks.

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
    PX["Practice: {{X}}"]
    OY["Outcome: {{Y}}"]
    RZ["Risk: {{Z}}"]

    PX -- "s (reinforces)" --> OY
    PX -. "o (undermines)" .-> RZ
    RZ -. "o (undermines)" .-> OY

    classDef practice fill:#9EBDCC,stroke:#517B9A,color:#070829,stroke-width:2px;
    classDef outcome fill:#99DB84,stroke:#389545,color:#0C1D0C,stroke-width:2px;
    classDef risk fill:#DBA872,stroke:#9A4C2E,color:#160909,stroke-width:2px;

    class PX practice;
    class OY outcome;
    class RZ risk;
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{X}}` | Practice or technique name |
| `{{Y}}` | Desired outcome |
| `{{Z}}` | Risk or failure mode |

## Notes

- Solid arrows (`-->`) represent reinforcing relationships.
- Dotted arrows (`.->`) represent undermining relationships.
- Mermaid does not support PlantUML-style `s()` / `o()` macros; use edge
  labels and line styles instead.

## When to Use

- Systems thinking: mapping feedback loops between practices and outcomes.
- Risk-benefit analysis for architecture or process decisions.
- ADR support: visualizing trade-offs behind a decision.
