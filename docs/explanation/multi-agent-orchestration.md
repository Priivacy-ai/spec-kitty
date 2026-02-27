---
title: Multi-Agent Orchestration
description: Coordination model for multi-agent delivery with a host-owned workflow state and external orchestration providers.
---

# Multi-Agent Orchestration

Spec Kitty supports multi-agent delivery through a host/provider split:

- `spec-kitty` owns workflow state, lane validation, and git-safe mutations.
- External providers orchestrate agent execution and call `spec-kitty orchestrator-api`.

This replaces in-core orchestration commands. The core CLI does not provide `spec-kitty orchestrate`.

## Why this model

1. Security boundary: autonomous orchestration is optional and can be disallowed by policy.
2. Extensibility: multiple provider strategies can exist without branching core CLI behavior.
3. Operational clarity: one host contract for state transitions and lifecycle events.

## Core Principles

1. Planning in main, implementation in worktrees.
2. One worktree per WP.
3. Lane transitions validated by the host state model.
4. External providers drive automation through API calls, not direct file edits.

## Two orchestration styles

### 1) Manual (human- or agent-driven)

Manual coordination still works via normal commands:

```bash
spec-kitty implement WP01
spec-kitty agent tasks move-task WP01 --to for_review
spec-kitty agent tasks move-task WP01 --to done
```

### 2) External automated orchestration

Automated coordination is run by external providers such as `spec-kitty-orchestrator`.

```bash
spec-kitty orchestrator-api contract-version
spec-kitty-orchestrator orchestrate --feature 034-my-feature --dry-run
spec-kitty-orchestrator orchestrate --feature 034-my-feature
```

Provider loop responsibilities:

1. Discover ready WPs via host API.
2. Start implementation and run agents in worktrees.
3. Transition WPs through review cycles.
4. Accept and merge when done.

## Host API boundary

All state-changing automation calls flow through `spec-kitty orchestrator-api`.

- `start-implementation`
- `start-review`
- `transition`
- `append-history`
- `accept-feature`
- `merge-feature`

The host returns a stable JSON envelope with `success` and `error_code` for deterministic provider control flow.

## Lane semantics

Public API lanes:

- `planned`
- `in_progress`
- `for_review`
- `done`
- `blocked`
- `canceled`

Compatibility mapping:

- API `in_progress` maps to internal `doing`.
- `planned`, `for_review`, and `done` map directly.

## Policy metadata and mutation authority

Run-affecting operations require policy metadata (`--policy`) and are validated by the host.

This ensures:

- identity and mode are explicit for each mutation
- malformed or secret-like policy payloads are rejected
- orchestrators cannot bypass host transition rules

## What this means for teams

- Teams that want full automation can run an external provider.
- Teams with strict security constraints can keep orchestration manual.
- Teams can build custom providers while preserving a consistent workflow model.

## See Also

- [Run the External Orchestrator](../how-to/run-external-orchestrator.md)
- [Build a Custom Orchestrator](../how-to/build-custom-orchestrator.md)
- [Orchestrator API Reference](../reference/orchestrator-api.md)
- [Kanban Workflow](kanban-workflow.md)
