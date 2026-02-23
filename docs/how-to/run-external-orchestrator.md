---
title: Run the External Orchestrator
description: Use spec-kitty-orchestrator with spec-kitty orchestrator-api to automate multi-agent WP execution.
---

# Run the External Orchestrator

Use this guide to run `spec-kitty-orchestrator` against a feature managed by `spec-kitty`.

This is the supported automation model in `1.x` and `2.x`:

- Host workflow state is owned by `spec-kitty`.
- Automation runtime is external (`spec-kitty-orchestrator` or your own provider).
- Integration happens only through `spec-kitty orchestrator-api`.

## Prerequisites

- `spec-kitty` installed and available on `PATH`
- `spec-kitty-orchestrator` installed and available on `PATH`
- A prepared feature (`spec.md`, `plan.md`, `tasks.md`, and `tasks/WP*.md`)
- At least one supported agent CLI installed

## 1. Verify Host Contract

```bash
spec-kitty orchestrator-api contract-version --json
```

Expected result:

- `success: true`
- `data.api_version` present
- `data.min_supported_provider_version` present

## 2. Run a Dry-Run

```bash
spec-kitty-orchestrator orchestrate --feature 034-my-feature --dry-run
```

Use this to validate configuration before mutating WP lanes.

## 3. Start Orchestration

```bash
spec-kitty-orchestrator orchestrate --feature 034-my-feature
```

The orchestrator loop will typically:

1. Read ready WPs via `list-ready`.
2. Claim/start via `start-implementation`.
3. Transition through `for_review` and `done` via host API calls.
4. Continue until all WPs are terminal.

## 4. Monitor or Recover

```bash
spec-kitty-orchestrator status
spec-kitty-orchestrator resume
spec-kitty-orchestrator abort
```

Use `resume` after interruption. Use `abort` to mark the provider run as stopped.

## 5. Confirm Host State

```bash
spec-kitty orchestrator-api feature-state --feature 034-my-feature --json
```

This is the authoritative source of lane state.

## Troubleshooting

### `No such command 'orchestrate'`

Expected for `spec-kitty` core CLI. Use:

- `spec-kitty-orchestrator orchestrate ...` for the external runtime
- `spec-kitty orchestrator-api ...` for host state operations

### Contract mismatch

If `contract-version` returns mismatch, upgrade either host (`spec-kitty`) or provider (`spec-kitty-orchestrator`) so versions are compatible.

### Policy validation failures

Mutation calls may fail with `POLICY_METADATA_REQUIRED` or `POLICY_VALIDATION_FAILED`. Ensure the provider sends required policy fields and does not include secret-like values.

## See Also

- [Orchestrator API Reference](../reference/orchestrator-api.md)
- [How to Build a Custom Orchestrator](build-custom-orchestrator.md)
