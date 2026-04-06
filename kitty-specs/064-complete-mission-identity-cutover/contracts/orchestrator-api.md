# Contract: Orchestrator API (Post-Cutover)

**Feature**: 064-complete-mission-identity-cutover
**Date**: 2026-04-06
**Consumer**: spec-kitty-orchestrator (Priivacy-ai/spec-kitty-orchestrator)

## Commands

### Renamed Commands

| Command | Purpose | Key Parameters |
|---------|---------|---------------|
| `mission-state` | Query mission status and WP lanes | `--feature` (mission slug), `--policy` |
| `accept-mission` | Mark all WPs done, accept mission | `--feature` (mission slug), `--policy` |
| `merge-mission` | Merge mission worktrees to target branch | `--feature` (mission slug), `--strategy`, `--policy` |

### Unchanged Commands

| Command | Purpose |
|---------|---------|
| `contract-version` | Report contract version and minimum provider version |
| `list-ready` | List WPs ready for implementation/review |
| `start-implementation` | Claim and start implementing a WP |
| `start-review` | Start reviewing a WP |
| `transition` | Transition a WP between lanes |
| `append-history` | Append audit history entry |

## Error Codes

| Code | Meaning |
|------|---------|
| `MISSION_NOT_FOUND` | Mission slug does not resolve to a kitty-specs directory |
| `MISSION_NOT_READY` | Not all WPs are done (for accept-mission) |
| `USAGE_ERROR` | CLI parse/usage error |
| `POLICY_METADATA_REQUIRED` | --policy missing on run-affecting command |
| `POLICY_VALIDATION_FAILED` | Policy JSON invalid or contains secrets |
| `WP_NOT_FOUND` | WP ID does not exist in the mission |
| `TRANSITION_REJECTED` | Transition not allowed by state machine |
| `WP_ALREADY_CLAIMED` | WP claimed by a different actor |
| `PREFLIGHT_FAILED` | Preflight checks failed (for merge-mission) |
| `CONTRACT_VERSION_MISMATCH` | Provider version below minimum |
| `UNSUPPORTED_STRATEGY` | Merge strategy not implemented |

## Response Envelope

All commands emit a single JSON object to stdout. The envelope always includes:

```json
{
  "ok": true,
  "command": "mission-state",
  "contract_version": "...",
  "mission_slug": "064-my-mission",
  "data": { ... }
}
```

**Removed fields**: `feature_slug` (was injected as alias, no longer present).

**Required field**: `mission_slug` (always present in data payloads that reference a mission).

## Failure Envelope

```json
{
  "ok": false,
  "command": "mission-state",
  "error_code": "MISSION_NOT_FOUND",
  "error": "Mission '064-nonexistent' not found in kitty-specs/",
  "contract_version": "..."
}
```

## Unknown Command Behavior

Calling a removed command name (e.g., `feature-state`, `accept-feature`, `merge-feature`) results in a standard CLI unknown-command error. The orchestrator API does not recognize these names and does not provide a redirect or deprecation notice.
