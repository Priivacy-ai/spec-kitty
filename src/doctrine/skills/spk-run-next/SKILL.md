---
name: spk-run-next
description: "Drive the canonical spec-kitty next control loop and route step, blocked, decision_required, and terminal results."
---

# spk-run-next

Use this skill when advancing an active mission, asking what to do next, or
recovering from a runtime decision.

## Flow

1. Run `spec-kitty next --agent <name>` or use the host's equivalent action.
2. Read the returned decision kind.
3. For `step`, execute the generated prompt file.
4. For `decision_required`, answer the decision explicitly.
5. For `blocked`, fix guard failures before retrying.
6. For `terminal`, route to `spk-gate-accept`.

## Legacy Alias

For detailed runtime semantics, use `spec-kitty-runtime-next` when available.
