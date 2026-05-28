---
title: Orchestrator Quickstart
description: Learn how Spec Kitty and spec-kitty-orchestrator work together to run a small mission through implementation and review.
---

# Orchestrator Quickstart

This tutorial shows the external orchestration model end to end:

- `spec-kitty` owns mission state and lane transitions.
- `spec-kitty-orchestrator` runs agents and calls `spec-kitty orchestrator-api`.
- Implementation and review happen in git worktrees, not on protected `main`.

By the end, you will know how to check the host contract, run the reference
orchestrator, watch mission state, and recover from a stopped run.

## Prerequisites

You need:

- a git repository initialized with Spec Kitty
- `spec-kitty` on `PATH`
- `spec-kitty-orchestrator` on `PATH`
- at least one agent CLI supported by the orchestrator, such as Claude Code,
  Codex, or OpenCode
- a mission with at least one `tasks/WP*.md` file

If you do not have a mission yet, finish [Your First Feature](your-first-feature.md)
first.

## 1. Confirm the host API works

Run this from the project root:

```bash
spec-kitty orchestrator-api contract-version
```

The output is a JSON envelope. For a compatible host it includes:

```json
{
  "success": true,
  "data": {
    "api_version": "1.0.0"
  }
}
```

The orchestrator performs this check at startup too, but running it yourself
confirms that the host CLI is installed and that JSON output is available.

## 2. Find your mission slug

Use the dashboard, `kitty-specs/`, or the mission commands to identify the
mission slug:

```bash
ls kitty-specs
```

Examples look like:

```text
034-payment-retry-flow
099-orchestrator-e2e
```

The orchestrator API selector is always `--mission`, even when the selector is
a slug, mission id, or short mission id.

## 3. Inspect ready work

```bash
spec-kitty orchestrator-api list-ready --mission 034-payment-retry-flow
```

Ready work packages are WPs in `planned` whose dependencies are already `done`.
If no WPs are ready, inspect the whole mission:

```bash
spec-kitty orchestrator-api mission-state --mission 034-payment-retry-flow
```

## 4. Dry-run the orchestrator

```bash
spec-kitty-orchestrator orchestrate \
  --mission 034-payment-retry-flow \
  --impl-agent claude-code \
  --review-agent codex \
  --max-concurrent 1 \
  --dry-run
```

Use `--dry-run` before the first real run. It validates configuration without
moving WP lanes.

## 5. Run implementation and review

```bash
spec-kitty-orchestrator orchestrate \
  --mission 034-payment-retry-flow \
  --impl-agent claude-code \
  --review-agent codex \
  --max-concurrent 1
```

The reference orchestrator will:

1. call `list-ready`
2. call `start-implementation` for a ready WP
3. run the implementation agent in the WP worktree
4. transition the WP to `for_review`
5. run the review agent
6. claim `in_review` and transition to `done` when the review passes
7. move rejected work back to `in_progress` for rework

The orchestrator writes its local run state under `.kittify/` and agent logs
under `.kittify/logs/`.

## 6. Check progress

In another terminal:

```bash
spec-kitty-orchestrator status
spec-kitty orchestrator-api mission-state --mission 034-payment-retry-flow
```

Use `mission-state` as the source of truth for WP lanes. Use
`spec-kitty-orchestrator status` for provider-local details such as retry
counts and the last agent log path.

## 7. Resume or abort

If the process is interrupted:

```bash
spec-kitty-orchestrator resume
```

If you need to stop tracking the run state:

```bash
spec-kitty-orchestrator abort --cleanup-worktrees
```

`abort --cleanup-worktrees` removes provider-local state. It does not rewrite
authoritative mission lane history.

## What to read next

- [Run the External Orchestrator](../how-to/run-external-orchestrator.md) for
  operational commands and troubleshooting.
- [Build a Custom Orchestrator](../how-to/build-custom-orchestrator.md) if you
  want to write your own provider loop.
- [Orchestrator API Reference](../reference/orchestrator-api.md) for command
  flags and JSON payloads.
- [Multi-Agent Orchestration](../explanation/multi-agent-orchestration.md) for
  the host/provider model.
