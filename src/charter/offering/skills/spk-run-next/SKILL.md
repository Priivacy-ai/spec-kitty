---
name: spk-run-next
description: "Drive the canonical spec-kitty next control loop and route query, step, blocked, decision_required, and terminal results."
---

# spk-run-next

Use this skill when advancing an active mission, asking what to do next, or
recovering from a runtime decision.

## Flow

1. Query state with `spec-kitty next --mission <handle> --json` or advance with
   `spec-kitty next --agent <name> --mission <handle> --result <success|failed|blocked>`.
2. Read the returned decision kind.
3. For `query`, inspect only; do not execute a prompt or mark a result.
4. For `step`, execute the generated prompt file.
5. For `decision_required`, answer with `--answer`, `--result`, `--agent`, and
   `--decision-id` when multiple decisions are pending.
6. For `blocked`, fix guard failures before retrying.
7. For `terminal`, route to `spk-gate-accept`.

## Legacy Alias

For detailed runtime semantics, use `spec-kitty-runtime-next` when available.
