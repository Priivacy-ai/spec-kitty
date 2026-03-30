# Mermaid Template: Request Lifecycle Sequence

Sequence diagram modeling a request flow through system components. Shows
ingress/egress points and processing stages.

## Template

```mermaid
%%{init: {'theme':'base','themeVariables': {
  'fontFamily': 'Verdana, Arial, sans-serif',
  'fontSize': '14px',
  'primaryColor': '#1c75cc',
  'primaryTextColor': '#ffffff',
  'primaryBorderColor': '#1168bd',
  'secondaryColor': '#f2f2f2',
  'secondaryTextColor': '#5a5a5a',
  'lineColor': '#5a5a5a',
  'tertiaryColor': '#ffffff'
}}}%%
sequenceDiagram
    autonumber
    actor User
    participant Agent as {{Agent / Service}}
    participant Store as {{Data Store}}
    participant CI as {{Pipeline / CI}}

    User->>Agent: Request + constraints ({{task}})
    Agent->>Store: Load context / configuration
    Store-->>Agent: Context OK / Mismatch
    Agent->>Agent: Analyze -> Plan
    Agent->>User: Clarify ambiguities (if needed)
    User-->>Agent: Answers / approvals
    Agent->>Agent: Generate artifacts
    Agent->>User: Diffs + summary
    User-->>Agent: Approve changes
    Agent->>CI: Commit & trigger pipeline
    CI-->>User: Build/Test status
```

## Placeholders

| Placeholder | Replace With |
|---|---|
| `{{Agent / Service}}` | The processing agent, service, or component |
| `{{Data Store}}` | Database, context stack, or configuration source |
| `{{Pipeline / CI}}` | CI/CD pipeline or downstream consumer |
| `{{task}}` | Short description of the request payload |

## When to Use

- Documenting how a user request flows through the system end-to-end.
- Clarifying async vs sync interaction boundaries.
- Design reviews for request handling pipelines.
