# Quickstart: Orchestrator Documentation Sprint

Quick reference for writing orchestrator documentation.

## Document Checklist

| ID | Type | File | Status |
|----|------|------|--------|
| E1 | Explanation | `docs/explanation/autonomous-orchestration.md` | TODO |
| R3 | Reference | `docs/reference/orchestration-state.md` | TODO |
| R1 | Reference | `docs/reference/cli-commands.md` (update) | TODO |
| R2 | Reference | `docs/reference/configuration.md` (update) | TODO |
| H1 | How-To | `docs/how-to/run-autonomous-orchestration.md` | TODO |
| H2 | How-To | `docs/how-to/configure-orchestration-agents.md` | TODO |
| H3 | How-To | `docs/how-to/monitor-orchestration.md` | TODO |
| H4 | How-To | `docs/how-to/resume-failed-orchestration.md` | TODO |
| H5 | How-To | `docs/how-to/override-orchestration-agents.md` | TODO |
| T1 | Tutorial | `docs/tutorials/autonomous-orchestration.md` | TODO |
| E2 | Explanation | `docs/explanation/multi-agent-orchestration.md` (update) | TODO |
| N1 | Navigation | `docs/toc.yml` (update) | TODO |

## Key CLI Commands

```bash
# Start orchestration
spec-kitty orchestrate --feature <slug>

# Check status
spec-kitty orchestrate --status

# Resume after failure
spec-kitty orchestrate --resume

# Abort orchestration
spec-kitty orchestrate --abort
spec-kitty orchestrate --abort --cleanup

# Skip failed WP
spec-kitty orchestrate --skip WP03

# Override agents
spec-kitty orchestrate --feature <slug> --impl-agent claude --review-agent codex
```

## State Machine

```
PENDING → READY → IMPLEMENTATION → REVIEW → COMPLETED
                       ↑              ↓
                       └── REWORK ←───┘
                              ↓
                           FAILED (max retries)
```

## Agent Selection Strategies

| Strategy | Description |
|----------|-------------|
| `preferred` | User specifies preferred implementer and reviewer |
| `random` | Randomly select from available agents |

## Config Structure (`.kittify/config.yaml`)

```yaml
agents:
  available:
    - claude
    - codex
    - opencode
  selection:
    strategy: preferred  # or "random"
    preferred_implementer: claude
    preferred_reviewer: codex
```

## State File (`.kittify/orchestration-state.json`)

Key fields:

- `run_id`: Unique orchestration run ID
- `feature_slug`: Feature being orchestrated
- `status`: PENDING | RUNNING | PAUSED | COMPLETED | FAILED
- `work_packages`: Map of WP ID → WPExecution
- `wps_total`, `wps_completed`, `wps_failed`: Counts

WPExecution fields:

- `status`: pending | ready | implementation | review | rework | completed | failed
- `implementation_agent`, `review_agent`: Agent IDs
- `implementation_retries`, `review_retries`: Retry counts
- `review_feedback`: Feedback from rejected review
- `last_error`: Error message if failed

## Cross-Reference Links

When referencing other docs, use relative paths:

- From how-to to tutorial: `../tutorials/autonomous-orchestration.md`
- From tutorial to reference: `../reference/cli-commands.md`
