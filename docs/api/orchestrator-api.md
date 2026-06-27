---
title: Orchestrator API Reference
description: Machine-contract API for external orchestration providers.
doc_status: active
updated: '2026-06-26'
related:
- docs/api/event-envelope.md
- docs/migration/feature-flag-deprecation.md
- docs/migration/mission-id-canonical-identity.md
- docs/migration/mission-type-flag-deprecation.md
---
# Orchestrator API Reference

`spec-kitty orchestrator-api` is the canonical JSON-first host interface for
external orchestrators.

It is intentionally stricter than the human-facing CLI:

- use `--mission`; the `--feature` flag has been removed from all user-facing commands
- expect one JSON envelope on stdout for both success and failure
- treat `error_code` as the stable machine discriminator
- do not append `--json`; JSON is the default output for this command group

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

Removed at the CLI boundary:

- `--feature` (hard-removed in #1060; passing it yields exit code 2 with "No such option: --feature")

## Commands

| Command | Mutates state | Purpose |
|---|---:|---|
| `contract-version` | no | Check API compatibility. |
| `mission-state` | no | Query mission state and WP lanes. |
| `list-ready` | no | List WPs ready to start. |
| `start-implementation` | yes | Atomically move a WP into implementation. |
| `start-review` | yes | Claim active review for a WP. |
| `transition` | yes | Emit one explicit lane transition. |
| `append-history` | yes | Append a WP activity-log note. |
| `accept-mission` | yes | Record mission acceptance. |
| `merge-mission` | yes | Merge the mission into its target branch. |

Legacy command names such as `feature-state`, `accept-feature`, and
`merge-feature` are forbidden.

## Required Flags

The tracked-mission selector is always:

```bash
spec-kitty orchestrator-api mission-state --mission 077-mission-terminology-cleanup
```

Run-affecting implementation and review mutations require `--policy`. Today
that means `start-implementation`, `start-review`, and `transition` when the
target lane is run-affecting. `append-history`, `accept-mission`, and
`merge-mission` do not accept `--policy`.

The policy JSON object must include:

- `orchestrator_id`
- `orchestrator_version`
- `agent_family`
- `approval_mode`
- `sandbox_mode`
- `network_mode`
- `dangerous_flags`

Secret-like values in `--policy` are rejected.

Minimal policy example:

```json
{
  "orchestrator_id": "spec-kitty-orchestrator",
  "orchestrator_version": "0.1.0",
  "agent_family": "claude",
  "approval_mode": "full_auto",
  "sandbox_mode": "workspace_write",
  "network_mode": "none",
  "dangerous_flags": []
}
```

## Lane Model for Orchestrators

External providers should treat these lanes as the public orchestration model:

| Lane | Meaning |
|---|---|
| `planned` | WP exists but has not started. |
| `claimed` | WP is claimed by an actor as part of implementation start. |
| `in_progress` | Implementation or rework is active. |
| `for_review` | Implementation is ready for review. |
| `in_review` | A reviewer has claimed active review. |
| `approved` | Review accepted but integration may still be pending. |
| `done` | WP is complete. |
| `blocked` | WP cannot continue without intervention. |
| `canceled` | WP was intentionally canceled. |

The reference orchestrator normally drives:

```text
planned -> claimed -> in_progress -> for_review -> in_review -> done
```

Rejected review cycles move back through:

```text
in_review -> in_progress -> for_review
```

## Acceptance Payload

`accept-mission` requires every WP to be `approved` or `done`. It returns:

| Field | Meaning |
|---|---|
| `accepted_wps` | WPs counted by mission acceptance (`approved` plus `done`) |
| `approved_wps` | Review-passed WPs still awaiting merge/integration |
| `done_wps` | WPs already merged/integrated |
| `merge_pending_wps` | Alias of `approved_wps`; WPs accepted-ready but not done |

`accept-mission` does not move WPs from `approved` to `done`; merge owns that
transition.

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

### Start implementation

```bash
spec-kitty orchestrator-api start-implementation \
  --mission 077-mission-terminology-cleanup \
  --wp WP12 \
  --actor spec-kitty-orchestrator \
  --policy '{"orchestrator_id":"spec-kitty-orchestrator","orchestrator_version":"0.1.0","agent_family":"claude","approval_mode":"full_auto","sandbox_mode":"workspace_write","network_mode":"none","dangerous_flags":[]}'
```

Important response fields:

| Field | Meaning |
|---|---|
| `workspace_path` | Path where the provider should run the implementation agent. |
| `prompt_path` | WP markdown prompt file to feed to the implementation agent. |
| `to_lane` | Expected to be `in_progress` on a fresh start. |
| `no_op` | `true` when the same actor already owns the compatible state. |

### Mark implementation ready for review

```bash
spec-kitty orchestrator-api transition \
  --mission 077-mission-terminology-cleanup \
  --wp WP12 \
  --to for_review \
  --actor spec-kitty-orchestrator \
  --policy '{"orchestrator_id":"spec-kitty-orchestrator","orchestrator_version":"0.1.0","agent_family":"claude","approval_mode":"full_auto","sandbox_mode":"workspace_write","network_mode":"none","dangerous_flags":[]}' \
  --subtasks-complete \
  --implementation-evidence-present \
  --note "Implementation complete"
```

`in_progress -> for_review` requires evidence that the implementation handoff
is ready. A provider may use `--force` with a clear `--note` when it has its own
reviewable evidence model.

### Claim review

```bash
spec-kitty orchestrator-api start-review \
  --mission 077-mission-terminology-cleanup \
  --wp WP12 \
  --actor spec-kitty-orchestrator \
  --policy '{"orchestrator_id":"spec-kitty-orchestrator","orchestrator_version":"0.1.0","agent_family":"codex","approval_mode":"full_auto","sandbox_mode":"workspace_write","network_mode":"none","dangerous_flags":[]}' \
  --review-ref review/WP12/attempt-1
```

On current hosts this moves `for_review -> in_review`.

### Complete approved review

```bash
spec-kitty orchestrator-api transition \
  --mission 077-mission-terminology-cleanup \
  --wp WP12 \
  --to done \
  --actor spec-kitty-orchestrator \
  --policy '{"orchestrator_id":"spec-kitty-orchestrator","orchestrator_version":"0.1.0","agent_family":"codex","approval_mode":"full_auto","sandbox_mode":"workspace_write","network_mode":"none","dangerous_flags":[]}' \
  --review-ref review/WP12/attempt-1 \
  --force \
  --note "Codex review approved"
```

Use `--force` with an audit note for the current external-review completion
path. The provider is responsible for keeping the review artifact reference in
`--review-ref` stable enough for later audit.

### Send rejected review back to rework

```bash
spec-kitty orchestrator-api transition \
  --mission 077-mission-terminology-cleanup \
  --wp WP12 \
  --to in_progress \
  --actor spec-kitty-orchestrator \
  --policy '{"orchestrator_id":"spec-kitty-orchestrator","orchestrator_version":"0.1.0","agent_family":"codex","approval_mode":"full_auto","sandbox_mode":"workspace_write","network_mode":"none","dangerous_flags":[]}' \
  --review-ref review/WP12/attempt-1 \
  --force \
  --note "Review rejected; rework required"
```

Then rerun the implementation agent with the review feedback and transition
back to `for_review`.

## Worktree Expectations

The host returns the workspace path. The provider is responsible for ensuring
the path exists and is usable for the agent process before spawning an agent.
Do not treat the returned string as proof that a worktree already exists.

State mutation commands should not be run from a protected main branch when
they need to commit activity-log updates. Use a mission lane/worktree branch for
provider-owned mutation calls.

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
- `WORKFLOW_EVIDENCE_REQUIRED`
- `PREFLIGHT_FAILED`
- `CONTRACT_VERSION_MISMATCH`
- `UNSUPPORTED_STRATEGY`
- `HISTORY_COMMIT_FAILED`
- `SAFE_COMMIT_BACKSTOP`
- `SAFE_COMMIT_DESTINATION_NOT_FOUND`
- `SAFE_COMMIT_DESTINATION_REF_SHAPE`
- `SAFE_COMMIT_EMPTY_CHANGESET`
- `SAFE_COMMIT_GENERIC`
- `SAFE_COMMIT_HEAD_MISMATCH`
- `SAFE_COMMIT_NOT_A_WORKTREE`
- `SAFE_COMMIT_PROTECTED_BRANCH`
- `SAFE_COMMIT_RECOVERY_FAILED`

## Provider Rules

- Call `contract-version` once before mutating state.
- Use only `orchestrator-api` for lane changes.
- Keep retry decisions based on `error_code`, not prose.
- Preserve `review_ref` values in logs and issue/PR links.
- Treat `mission-state` as authoritative after every recovery.
- Keep agent stdout/stderr in provider logs; do not stuff full logs into WP
  history entries.

## Migration Notes

- The human-facing CLI still supports hidden deprecated aliases during the
  migration window.
- The orchestrator API does not. It is canonical-only on `--mission` and
  `mission_*` payload fields.

See also:

- [Event Envelope Reference](event-envelope.md)
- [Feature Flag Deprecation](../migration/feature-flag-deprecation.md)
- [Mission Type Flag Deprecation](../migration/mission-type-flag-deprecation.md)
