# Research Mission

Mission type for structured research workflows that produce findings, evidence, and
synthesized knowledge artifacts.

## State Machine

```
scoping → methodology → gathering → synthesis → output → done
```

The gathering → synthesis transition is guarded by
`event_count("source_documented", 3)`, requiring at least 3 documented sources
before synthesis can begin.

## Contents

- `mission.yaml` — State machine with evidence-count guards
- `command-templates/` — Prompt files for research workflow steps
- `templates/` — Content scaffolds (spec, plan, tasks, data-model, task-prompt)
- `templates/research/` — Research-specific artifacts (evidence-log.csv, source-register.csv)
