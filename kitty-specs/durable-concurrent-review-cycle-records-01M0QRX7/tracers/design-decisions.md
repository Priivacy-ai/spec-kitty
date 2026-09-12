---
divio_type: explanation
audience: agentic-framework-core-team
updated: 2026-08-23
---

# Design Decisions Tracer

## Planning decisions

| Decision | Outcome | Reason |
|---|---|---|
| Contention behavior | Wait in line | Simplest deterministic behavior for a rare concurrent save. |
| Serialization scope | Verdict saves only | Avoid changing unrelated Git operations. |
| Lock scope | Git-common-directory checkout-wide | Covers missions and linked worktrees sharing Git state. |
| Wait bound | 10 seconds, no automatic retry | Gives automation a bounded, truthful failure. |
| Explicit local mode | Preserve `--no-auto-commit` | Existing sanctioned local-only workflow remains useful. |
| Commit failure | Retain artifact; identical retry adopts | Avoids data deletion and manual orphan cleanup. |
| Authority split | Event=current verdict; artifact=evidence content | Preserves accepted architecture and prevents duplicate authority. |
| Queue/event boundary | Release queue before event append | Prevents nesting independent locks while requiring evidence durability before verdict success. |

Canonical decision-moment records are stored in `kitty-specs/durable-concurrent-review-cycle-records-01M0QRX7/decisions/`.
