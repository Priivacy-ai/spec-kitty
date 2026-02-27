---
title: Orchestrator API Reference
description: Contract reference for external orchestration providers that integrate with spec-kitty via the orchestrator-api command group.
---

# Orchestrator API Reference

`spec-kitty orchestrator-api` is the host-side contract for external orchestration providers.

- Core CLI does not include `spec-kitty orchestrate`.
- External providers (for example `spec-kitty-orchestrator`) must use this API.
- Commands always emit JSON: exactly one JSON envelope on stdout; non-zero exit on failure.
- Parser/usage errors (missing required args, unknown options) also return a JSON envelope with error code `USAGE_ERROR`.

## Contract Version

- `CONTRACT_VERSION`: `1.0.0`
- Command: `spec-kitty orchestrator-api contract-version`

## Canonical Envelope

All commands return:

```json
{
  "contract_version": "1.0.0",
  "command": "orchestrator-api.feature-state",
  "timestamp": "2026-02-23T18:03:22.152177+00:00",
  "correlation_id": "corr-9b9385...",
  "success": true,
  "error_code": null,
  "data": {}
}
```

Field meanings:

- `contract_version`: Host API contract version.
- `command`: Fully qualified command name (`orchestrator-api.<subcommand>`).
- `timestamp`: Host generation timestamp (ISO 8601).
- `correlation_id`: Unique request/response correlation token.
- `success`: Success/failure indicator.
- `error_code`: Machine-readable error identifier on failure, otherwise `null`.
- `data`: Command-specific payload.

## Lanes and Mapping

Public API lane model:

- `planned`
- `in_progress`
- `for_review`
- `done`
- `blocked`
- `canceled`

Host internal lane compatibility:

- API `in_progress` maps to internal `doing`.
- API `for_review`, `planned`, and `done` map directly.

## Policy Contract (Mutation Commands)

Run-affecting operations require `--policy` JSON and validate it server-side.

Required fields:

- `orchestrator_id`
- `orchestrator_version`
- `agent_family`
- `approval_mode`
- `sandbox_mode`
- `network_mode`
- `dangerous_flags` (array)

Validation rules:

- Missing required fields fail with `POLICY_VALIDATION_FAILED`.
- Non-array `dangerous_flags` fails validation.
- Secret-like values (`token`, `secret`, `key`, `password`, `credential`) are rejected.

## Subcommands

### contract-version

```bash
spec-kitty orchestrator-api contract-version --json [--provider-version <semver>]
```

Returns host `api_version` and minimum supported provider version.

### feature-state

```bash
spec-kitty orchestrator-api feature-state --feature <slug>```

Returns WP states, dependency data, and lane summary.

### list-ready

```bash
spec-kitty orchestrator-api list-ready --feature <slug>```

Returns WPs in `planned` with all dependencies in `done`.

### start-implementation

```bash
spec-kitty orchestrator-api start-implementation \
  --feature <slug> --wp <WP##> --actor <actor-id> --policy '<json>'```

Composite transition into `in_progress` for implementation. Returns `workspace_path` and `prompt_path`.

### start-review

```bash
spec-kitty orchestrator-api start-review \
  --feature <slug> --wp <WP##> --actor <actor-id> --policy '<json>' \
  --review-ref <ref>```

Moves a rejected WP from `for_review` back to `in_progress`.

### transition

```bash
spec-kitty orchestrator-api transition \
  --feature <slug> --wp <WP##> --to <lane> --actor <actor-id> \
  [--note <text>] [--policy '<json>'] [--review-ref <ref>] [--force]```

Applies one lane transition with deterministic validation errors.

### append-history

```bash
spec-kitty orchestrator-api append-history \
  --feature <slug> --wp <WP##> --actor <actor-id> --note <text>```

Appends an activity entry to the WP prompt history.

### accept-feature

```bash
spec-kitty orchestrator-api accept-feature --feature <slug> --actor <actor-id>```

Accepts a feature when all WPs are `done`.

### merge-feature

```bash
spec-kitty orchestrator-api merge-feature \
  --feature <slug> [--target main] [--strategy merge|squash] [--push]```

Runs preflight and merges WP branches in dependency order.

## Common Error Codes

- `USAGE_ERROR`
- `CONTRACT_VERSION_MISMATCH`
- `FEATURE_NOT_FOUND`
- `WP_NOT_FOUND`
- `TRANSITION_REJECTED`
- `WP_ALREADY_CLAIMED`
- `POLICY_METADATA_REQUIRED`
- `POLICY_VALIDATION_FAILED`
- `FEATURE_NOT_READY`
- `PREFLIGHT_FAILED`
- `MERGE_FAILED`
- `PUSH_FAILED`
- `UNSUPPORTED_STRATEGY`

## Integration Notes

- Treat `error_code` as the stable failure discriminator.
- Do not parse human-readable `message` text for control flow.
- Do not mutate `kitty-specs/` state directly from external providers.

## See Also

- [How to Run the External Orchestrator](../how-to/run-external-orchestrator.md)
- [How to Build a Custom Orchestrator](../how-to/build-custom-orchestrator.md)
