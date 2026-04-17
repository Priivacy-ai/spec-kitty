# Plan Mission

Mission type for standalone planning workflows that produce structured plans without
necessarily proceeding to implementation.

## State Machine

```
goals → research → structure → draft → review → done
                      ↑          |       |
                      └──────────┘       └── (revise to draft)
```

Supports revision loops: draft can return to structure, and review can return to
draft.

## Runtime DAG (v1.0.0)

4 sequential steps: specify → research → plan → review. The planner profile handles
the plan step; the reviewer profile handles review.

## Contents

- `mission.yaml` — State machine with revision edges
- `mission-runtime.yaml` — Runtime DAG with step ordering
- `command-templates/` — Prompt files for plan, research, review, specify
