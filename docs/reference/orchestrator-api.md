---
title: Orchestrator API Reference
description: Machine-contract API for external orchestration providers.
---

# Orchestrator API Reference

`spec-kitty orchestrator-api` is the canonical JSON-first host interface for
external orchestrators.

It is intentionally stricter than the human-facing CLI:

- use `--mission`, never `--feature`
- expect one JSON envelope on stdout for both success and failure
- treat `error_code` as the stable machine discriminator

## Canonical Terms

- `Mission Type` = reusable blueprint key
- `Mission` = tracked item under `kitty-specs/<mission-slug>/`
- `Mission Run` = runtime/session instance

## Contract Version

- `CONTRACT_VERSION`: `1.0.0`
- `MIN_PROVIDER_VERSION`: `0.1.0`
- Startup probe: `spec-kitty orchestrator-api contract-version`

## Response Envelope

Every command returns exactly one JSON object with these 7 top-level keys:

```json
{
  "contract_version": "1.0.0",
  "command": "orchestrator-api.mission-state",
  "timestamp": "2026-04-08T12:00:00+00:00",
  "correlation_id": "corr-0123456789abcdef",
  "success": true,
  "error_code": null,
  "data": {}
}
```

| Field | Meaning |
|---|---|
| `contract_version` | Host API contract version. |
| `command` | Fully-qualified command name. |
| `timestamp` | ISO 8601 UTC response timestamp. |
| `correlation_id` | Unique per-response correlation token. |
| `success` | `true` for success, `false` for failure. |
| `error_code` | Machine-readable failure code, otherwise `null`. |
| `data` | Command-specific payload. |

Parser and usage failures also return the same envelope shape with
`error_code="USAGE_ERROR"`.

## Canonical Mission Identity

Success payloads that identify a tracked mission emit:

| Field | Meaning |
|---|---|
| `mission_id` | Canonical ULID machine identity. Aggregate routing uses this field. |
| `mission_slug` | Human-readable mission slug. Display context only. |
| `mission_number` | **Display-only** numeric prefix. `null` pre-merge, assigned at merge time. Never used for identity. |
| `mission_type` | Blueprint key |

The `--mission` selector accepts any of `mission_id`, `mid8` (first 8 chars of
the ULID), or `mission_slug`. Ambiguous handles return
`MISSION_AMBIGUOUS_SELECTOR` and list the candidates — there is no silent
fallback. See [Mission ID Canonical Identity Migration](../migration/mission-id-canonical-identity.md).

Forbidden in orchestrator-api payloads:

- `feature_slug`

Forbidden at the CLI boundary:

- `--feature`

## Commands

| Command | Purpose |
|---|---|
| `contract-version` | Check API compatibility |
| `mission-state` | Query mission state and WP lanes |
| `list-ready` | List WPs ready to start |
| `start-implementation` | Atomically move a WP into implementation |
| `start-review` | Claim review for a WP |
| `transition` | Emit one explicit lane transition |
| `append-history` | Append a WP activity-log note |
| `accept-mission` | Record mission acceptance |
| `merge-mission` | Merge the mission into its target branch |

Legacy command names such as `feature-state`, `accept-feature`, and
`merge-feature` are forbidden.

## Required Flags

The tracked-mission selector is always:

```bash
spec-kitty orchestrator-api mission-state --mission 077-mission-terminology-cleanup
```

Run-affecting commands also require `--policy`, whose JSON object must include:

- `orchestrator_id`
- `orchestrator_version`
- `agent_family`
- `approval_mode`
- `sandbox_mode`
- `network_mode`
- `dangerous_flags`

Secret-like values in `--policy` are rejected.

## Example Commands

```bash
spec-kitty orchestrator-api contract-version
spec-kitty orchestrator-api mission-state --mission 077-mission-terminology-cleanup
spec-kitty orchestrator-api list-ready --mission 077-mission-terminology-cleanup
spec-kitty orchestrator-api start-implementation \
  --mission 077-mission-terminology-cleanup \
  --wp WP12 \
  --actor codex \
  --policy '{"orchestrator_id":"local","orchestrator_version":"1.0.0","agent_family":"codex","approval_mode":"never","sandbox_mode":"danger-full-access","network_mode":"enabled","dangerous_flags":[]}'
```

## Error Codes

Current machine-readable error codes:

- `USAGE_ERROR`
- `POLICY_METADATA_REQUIRED`
- `POLICY_VALIDATION_FAILED`
- `MISSION_NOT_FOUND`
- `WP_NOT_FOUND`
- `TRANSITION_REJECTED`
- `WP_ALREADY_CLAIMED`
- `MISSION_NOT_READY`
- `PREFLIGHT_FAILED`
- `CONTRACT_VERSION_MISMATCH`
- `UNSUPPORTED_STRATEGY`

## Migration Notes

- The human-facing CLI still supports hidden deprecated aliases during the
  migration window.
- The orchestrator API does not. It is canonical-only on `--mission` and
  `mission_*` payload fields.

See also:

- [Event Envelope Reference](event-envelope.md)
- [Feature Flag Deprecation](../migration/feature-flag-deprecation.md)
- [Mission Type Flag Deprecation](../migration/mission-type-flag-deprecation.md)
