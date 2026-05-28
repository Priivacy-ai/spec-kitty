---
title: Run the External Orchestrator
description: Use spec-kitty-orchestrator with spec-kitty orchestrator-api to automate multi-agent WP execution.
---

# Run the External Orchestrator

Use this guide to run `spec-kitty-orchestrator` against a mission managed by
`spec-kitty`. This is the right page when you want a normal operator workflow:
Claude implements, Codex reviews, and Spec Kitty remains the workflow host.

This is the supported automation model:

- Host workflow state is owned by `spec-kitty`.
- Automation runtime is external (`spec-kitty-orchestrator` or your own provider).
- Integration happens only through `spec-kitty orchestrator-api`.

## Prerequisites

- `spec-kitty` installed and available on `PATH`
- `spec-kitty-orchestrator` installed and available on `PATH`
- A prepared mission (`spec.md`, `plan.md`, `tasks.md`, and `tasks/WP*.md`)
- At least one supported agent CLI installed
- A clean enough git repository for worktree creation

Install the released orchestrator package from PyPI:

```bash
pip install spec-kitty-orchestrator
```

For the common "Claude implements, Codex reviews" workflow, install and
authenticate both CLIs before starting:

```bash
claude --version
codex --version
```

## 1. Verify the Host Contract

```bash
spec-kitty orchestrator-api contract-version
```

Expected result:

- `success: true`
- `data.api_version` is present
- `data.min_supported_provider_version` present

Do this before debugging provider behavior. If the host contract cannot be
queried, the external orchestrator cannot safely mutate mission state.

## 2. Choose Implementer and Reviewer Agents

The most common pairing is Claude Code for implementation and Codex for review:

```bash
spec-kitty-orchestrator orchestrate \
  --mission 034-my-feature \
  --impl-agent claude-code \
  --review-agent codex \
  --max-concurrent 1 \
  --dry-run
```

Useful pairings:

| Implementer | Reviewer | When to use |
|---|---|---|
| `claude-code` | `codex` | Default local automation: broad implementation, independent review. |
| `codex` | `claude-code` | Codex implementation with Claude review. |
| `claude-code` | `opencode` | Only when OpenCode has a working local model/provider config. |

`--max-concurrent 1` is a conservative first run. Increase it after the first
mission succeeds and your agents handle parallel work safely.

## 3. Run a Dry Run

```bash
spec-kitty-orchestrator orchestrate \
  --mission 034-my-feature \
  --impl-agent claude-code \
  --review-agent codex \
  --max-concurrent 1 \
  --dry-run
```

Use this to validate configuration before mutating WP lanes.

## 4. Start Orchestration

```bash
spec-kitty-orchestrator orchestrate \
  --mission 034-my-feature \
  --impl-agent claude-code \
  --review-agent codex \
  --max-concurrent 1
```

The orchestrator loop will typically:

1. Read ready WPs via `list-ready`.
2. Claim/start via `start-implementation`.
3. Run the implementation agent in the WP worktree.
4. Transition to `for_review`.
5. Run the reviewer.
6. Claim `in_review`.
7. Transition to `done` on approval, or back to `in_progress` for rework.

The provider prepares worktrees before spawning agents. The host remains the
source of truth for lane events.

## 5. Monitor or Recover

```bash
spec-kitty-orchestrator status
spec-kitty-orchestrator resume
spec-kitty-orchestrator abort --cleanup-worktrees
```

Use `resume` after interruption. Use `abort --cleanup-worktrees` to remove the
provider-local run state. This does not rewrite the mission event log.

Agent logs are written under:

```text
.kittify/logs/
```

## 6. Confirm Host State

```bash
spec-kitty orchestrator-api mission-state --mission 034-my-feature
```

This is the authoritative source of lane state.

## 7. Accept and Merge After Orchestration

If your workflow separates orchestration from merge, finish with the normal
accept/merge process:

```bash
spec-kitty orchestrator-api accept-mission \
  --mission 034-my-feature \
  --actor spec-kitty-orchestrator
```

Then use your project’s normal merge path. The reference orchestrator can drive
WP implementation and review, but the team should still decide when the mission
is ready to land.

## Troubleshooting

### `No such command 'orchestrate'`

Expected for `spec-kitty` core CLI. Use:

- `spec-kitty-orchestrator orchestrate ...` for the external runtime
- `spec-kitty orchestrator-api ...` for host state operations

### Contract mismatch

If `contract-version` returns mismatch, upgrade either host (`spec-kitty`) or provider (`spec-kitty-orchestrator`) so versions are compatible.

### Policy validation failures

Mutation calls may fail with `POLICY_METADATA_REQUIRED` or `POLICY_VALIDATION_FAILED`. Ensure the provider sends required policy fields and does not include secret-like values.

### OpenCode exits before review

If an OpenCode-backed run blocks with an error such as `Model not found`, fix
the local OpenCode provider/model configuration and rerun. The orchestrator
will surface the agent error, but it cannot repair an unavailable model.

### Protected branch commit errors

Status-writing commands should run through orchestrator-managed worktrees, not
directly on protected `main`. If a custom provider invokes `append-history`
from `main`, the host may reject the commit. Use a lane/worktree branch for
mutation calls.

## See Also

- [Orchestrator Quickstart](../tutorials/orchestrator-quickstart.md)
- [Orchestrator API Reference](../reference/orchestrator-api.md)
- [How to Build a Custom Orchestrator](build-custom-orchestrator.md)
