# Event Contract: Retrospective Lifecycle Events

**Mission**: `retrospective-default-policy-01KS049J`
**Phase**: 1 — Contracts

This contract specifies the new (or extended) retrospective lifecycle event payloads that join the canonical event log. Wire shape is additive; existing reducers MUST continue to reduce historical events byte-identically (FR-021).

## Reuse vs new

Per [research.md R-3](../research.md#r-3--existing-event-type-coverage), implementation MUST first check whether `spec_kitty_events` (consumed via the FR-024 frozen public surface) already exposes a retrospective-capture event. If yes, reuse with additive `policy_source` attribution. If no, the new types below land in the local emit path under `specify_cli.status` infrastructure.

The contracts below specify the canonical payloads regardless of whether the event-type name is new or reused; the reduction shape is identical.

## Common envelope

All retrospective lifecycle events share the canonical event envelope used by other `kitty-specs/<mission_slug>/status.events.jsonl` entries:

```
{
  "type": <event_type>,
  "schema_version": 1,
  "event_id": <ULID>,
  "lamport": <int>,
  "at": <RFC 3339 timestamp>,
  "actor": {"kind": "human"|"agent"|"runtime", "id": <str>, "display": <str?>},
  "mission_id": <ULID>,
  "mission_slug": <str>,
  "wp_id": null,         # always null for mission-level retrospective events
  "force": false,        # retrospective events are never lane transitions
  "execution_mode": "worktree" | "main",
  ...<event-specific fields>
}
```

`from_lane`, `to_lane`, `review_ref`, `reason`, `feature_slug` are NOT present on retrospective events — they are state-transition envelope fields only.

## `RetrospectiveCaptured`

Fired when generation succeeds and a record is on disk.

### Payload (event-specific fields)

| Field | Type | Description |
|---|---|---|
| `findings_status` | `enum{has_findings, ran_no_findings}` | Outcome category. Never `missing` or `failed` here — see `RetrospectiveCaptureFailed`. |
| `record_path` | `string` | Absolute (or repo-relative) path to the written record. |
| `generator_version` | `string` | Generator version that produced the record. |
| `policy_source` | `dict[str,str]` | Resolver source-map snapshot. Per [retrospective-policy.schema.json](./retrospective-policy.schema.json) leaf-key conventions. |
| `provenance_kind` | `enum{runtime_post_completion, runtime_strict_gate, explicit_create, backfill}` | How the action was invoked. `synthesize_fabricate` provenance fires a separate provenance attribution but reuses this event type for the captured record. |
| `proposal_count` | `int` | Number of proposals in the captured record. |
| `evidence_ref_count` | `int` | Number of evidence references. |

### Example

```json
{
  "type": "RetrospectiveCaptured",
  "schema_version": 1,
  "event_id": "01KS06EXAMPLECAPTUREDXYZAB",
  "lamport": 142,
  "at": "2026-05-19T13:00:00+00:00",
  "actor": {"kind": "runtime", "id": "spec-kitty-cli@3.2.0", "display": "spec-kitty runtime"},
  "mission_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
  "mission_slug": "my-feature-01J6XW9K",
  "wp_id": null,
  "force": false,
  "execution_mode": "main",
  "findings_status": "has_findings",
  "record_path": "/abs/.kittify/missions/01J6XW9KQT7M0YB3N4R5CQZ2EX/retrospective.yaml",
  "generator_version": "1.0",
  "policy_source": {
    "enabled": ".kittify/config.yaml#retrospective.enabled",
    "timing": "<default>",
    "failure_policy": "<default>"
  },
  "provenance_kind": "runtime_post_completion",
  "proposal_count": 3,
  "evidence_ref_count": 10
}
```

### Invariants

- A single mission can have ≥ 0 `RetrospectiveCaptured` events. The most recent is authoritative.
- The reducer in `specify_cli.status.reducer` MUST NOT classify this as a lane transition. Existing materializations are unaffected.
- `findings_status` MUST match the value persisted in the record at `record_path`.

## `RetrospectiveCaptureFailed`

Fired when generation is attempted under `failure_policy: warn` and fails. Does NOT fire under `failure_policy: block` (the completion-block event itself carries the failure reason) or `enabled: false` (no attempt is made).

### Payload (event-specific fields)

| Field | Type | Description |
|---|---|---|
| `failure_category` | `enum` | One of: `missing_artifacts`, `generator_exception`, `schema_validation_error`, `io_error`, `other`. |
| `failure_message` | `string` | Plain-text human-readable description. Stripped of stack traces — those go to logs. |
| `remediation_hint` | `string \| null` | Suggested next action. E.g. `"Mission lacks an event log; rebuild via spec-kitty migrate normalize-lifecycle."`. |
| `policy_source` | `dict[str,str]` | Resolver source-map snapshot at the time of attempt. |
| `attempted_provenance_kind` | `enum{runtime_post_completion, runtime_strict_gate, explicit_create, backfill}` | The provenance the attempt would have carried on success. |
| `missing_artifacts` | `list[string] \| null` | When `failure_category == missing_artifacts`, the specific paths checked. |

### Example

```json
{
  "type": "RetrospectiveCaptureFailed",
  "schema_version": 1,
  "event_id": "01KS06EXAMPLEFAILEDXYZABCD",
  "lamport": 143,
  "at": "2026-05-19T13:01:00+00:00",
  "actor": {"kind": "runtime", "id": "spec-kitty-cli@3.2.0", "display": "spec-kitty runtime"},
  "mission_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
  "mission_slug": "my-feature-01J6XW9K",
  "wp_id": null,
  "force": false,
  "execution_mode": "main",
  "failure_category": "missing_artifacts",
  "failure_message": "Cannot author retrospective: required artifacts not found.",
  "remediation_hint": "Mission lacks status.events.jsonl. Rebuild via `spec-kitty migrate normalize-lifecycle --mission <handle>` and retry with `spec-kitty retrospect create --mission <handle>`.",
  "policy_source": {
    "enabled": ".kittify/config.yaml#retrospective.enabled",
    "timing": "<default>",
    "failure_policy": "<default>"
  },
  "attempted_provenance_kind": "runtime_post_completion",
  "missing_artifacts": ["kitty-specs/my-feature-01J6XW9K/status.events.jsonl"]
}
```

### Invariants

- A `RetrospectiveCaptureFailed` event MUST NOT block mission completion under `failure_policy: warn`.
- Subsequent `RetrospectiveCaptured` for the same mission supersedes prior `RetrospectiveCaptureFailed` for read-purposes (summary's `failed` lane is "most recent Failed not followed by a Captured").
- Reducer impact identical to `RetrospectiveCaptured` — no lane transition.

## Reduction guarantees (FR-021)

For every mission's `status.events.jsonl` file:

- The lane-state reduction (current lane of each WP, mission lifecycle phase) MUST be byte-identical before and after this mission, when the file contains only pre-existing event types.
- Adding the new retrospective event types is additive; the reducer MUST treat unknown-to-it event types as no-ops for lane reduction and pass them through for read-purposes.
- Materialized snapshots (`status.json`, lifecycle views) MAY gain new top-level keys reflecting retrospective state (e.g. `retrospective.last_captured_at`, `retrospective.last_failed_at`), but MUST NOT mutate keys that pre-date this mission.

## Schema test obligations

- Round-trip test: a `RetrospectiveCaptured` event serialized to JSONL and read back via the canonical event reader produces the same payload (byte-equal after sort-keys normalization).
- Schema test: validating each example payload against the JSON envelope used by `spec-kitty validate events` (if such a validator exists in the canonical event log infrastructure) passes.
- Backward-compat test: a historical mission's `status.events.jsonl` with no retrospective events still produces the same `status.json` snapshot before and after this mission merges.
