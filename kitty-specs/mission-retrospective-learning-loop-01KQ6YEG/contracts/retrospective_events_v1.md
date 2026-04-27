# Contract: Retrospective Events v1

**Status**: pinned for this tranche.
**Source of truth (initial)**: `specify_cli.retrospective.events` (this tranche).
**Source of truth (post-cutover)**: `spec_kitty_events.retrospective.*` (after the upstream PR ships).
**Boundary test**: `tests/architectural/test_shared_package_boundary.py` enforces single-home post-cutover (R-007).

The eight event names are **stable**. Renaming requires a deprecation cycle.

---

## Common envelope

Retrospective events share the existing mission event envelope used in `kitty-specs/<slug>/status.events.jsonl`. A retrospective event's serialized JSON line MUST include:

| Envelope field | Type | Notes |
|---|---|---|
| `event_id` | ULID string | Stable, sortable. |
| `event_name` | one of the eight names below | Discriminator. |
| `at` | ISO-8601 UTC timestamp | Wall clock. |
| `actor` | `ActorRef` (see data-model.md) | Who emitted. |
| `mission_id` | `MissionId` (ULID) | Required for retrospective events. |
| `mid8` | `Mid8` | Convenience for log scanners. |
| `mission_slug` | string | Convenience. |
| `payload` | event-specific Pydantic model | See per-event tables below. |

Retrospective events do NOT use the `to_lane`/`from_lane` fields used by status transitions (they don't change WP lane state). They join the same JSONL log so the reducer reads them in order.

The reducer surfaces retrospective state in the snapshot under a new `retrospective` field (additive; existing snapshot consumers see no change).

---

## Event 1: `retrospective.requested`

Emitted at mission terminus (autonomous: by the runtime hook) or on operator action (HiC: when the operator chooses to run / skip).

| Payload field | Type | Notes |
|---|---|---|
| `mode` | `Mode` | Resolved mode + source signal. |
| `terminus_step_id` | string | The mission step that hit terminus. |
| `requested_by` | `ActorRef` | Runtime in autonomous; operator in HiC. |

---

## Event 2: `retrospective.started`

Emitted when the facilitator dispatch begins (after `requested` and before any finding is captured).

| Payload field | Type | Notes |
|---|---|---|
| `facilitator_profile_id` | string | e.g., `retrospective-facilitator`. |
| `action_id` | string | e.g., `retrospect`. |

---

## Event 3: `retrospective.completed`

Emitted after `retrospective.yaml` is persisted with `status: completed`.

| Payload field | Type | Notes |
|---|---|---|
| `record_path` | string | Absolute path to the persisted `retrospective.yaml`. |
| `record_hash` | string | SHA-256 of the canonical-bytes of the persisted YAML. |
| `findings_summary` | `{helped: int, not_helpful: int, gaps: int}` | Counts only; payload is in the file. |
| `proposals_count` | int | |

---

## Event 4: `retrospective.skipped`

HiC-only. Autonomous mode emitting this event MUST be rejected by the gate as a silent-skip attempt.

| Payload field | Type | Notes |
|---|---|---|
| `record_path` | string | Path to the persisted skip record (yaml + this event are both required, FR-010). |
| `skip_reason` | string | Operator-supplied; non-empty. |
| `skipped_by` | `ActorRef` | Operator. |

---

## Event 5: `retrospective.failed`

Emitted when the retrospective could not be produced.

| Payload field | Type | Notes |
|---|---|---|
| `failure_code` | enum (see `RetrospectiveFailure.code`) | |
| `message` | string | Human-readable. |
| `record_path` | string \| null | Path if a partial record was persisted; null if write failed entirely. |

---

## Event 6: `retrospective.proposal.generated`

One per proposal at retrospective write time.

| Payload field | Type | Notes |
|---|---|---|
| `proposal_id` | ULID | Stable across the proposal's lifecycle. |
| `kind` | proposal kind enum | See `retrospective_yaml_v1.md`. |
| `record_path` | string | Path to the retrospective record this proposal lives in. |

---

## Event 7: `retrospective.proposal.applied`

Emitted by the synthesizer when a proposal is materialized into doctrine/DRG/glossary state.

| Payload field | Type | Notes |
|---|---|---|
| `proposal_id` | ULID | |
| `kind` | proposal kind enum | |
| `target_urn` | string | The artifact / edge / term that was created or modified. |
| `provenance_ref` | string | URN-shape reference to the provenance metadata written alongside. |
| `applied_by` | `ActorRef` | The operator who approved (for non-auto kinds) or `runtime` (for `flag_not_helpful`). |

---

## Event 8: `retrospective.proposal.rejected`

Two distinct origins; same event name, distinguished by `rejected_by` + `reason`:

- **Human rejection**: operator declines the proposal; `state.status` becomes `rejected` (terminal).
- **Apply-time rejection**: synthesizer attempted apply but conflict / staleness / invalidity blocked it. `state.status` stays `accepted`; `apply_attempts` records the attempt.

| Payload field | Type | Notes |
|---|---|---|
| `proposal_id` | ULID | |
| `kind` | proposal kind enum | |
| `reason` | enum: `human_decline`, `conflict`, `stale_evidence`, `invalid_payload` | |
| `detail` | string | Free-form context. |
| `rejected_by` | `ActorRef` | Operator (`human_decline`) or `runtime` (others). |

---

## Reducer surface

After this contract is implemented, `materialize(feature_dir)` includes:

```python
class StatusSnapshot(BaseModel):
    # ... existing fields ...
    retrospective: RetrospectiveSnapshot | None

class RetrospectiveSnapshot(BaseModel):
    status: Literal["completed", "skipped", "failed", "pending", "absent"]
    mode: Mode | None
    record_path: str | None
    proposals_total: int
    proposals_applied: int
    proposals_rejected: int
    proposals_pending: int
```

`absent` is reserved for missions that have not yet emitted any retrospective event (legacy + in-flight + terminus_no_retrospective; the cross-mission summary distinguishes them, but the per-mission snapshot reports the unified `absent`).

---

## Append-only invariant

NFR-005: no operation MUST mutate or delete a previously persisted retrospective event. Re-runs append additional events. The reducer treats the latest `completed`/`skipped`/`failed` (by `at` + `event_id`) as the authoritative status while preserving prior history.

---

## Cutover note (Q4-C)

Until the upstream `spec_kitty_events` release ships:

```python
# in specify_cli.retrospective.events:
from pydantic import BaseModel
# ... local definitions matching this contract ...
```

Post-upstream:

```python
# in specify_cli.retrospective.events (deleted after cutover):
from spec_kitty_events.retrospective import (
    Requested, Started, Completed, Skipped, Failed,
    ProposalGenerated, ProposalApplied, ProposalRejected,
)
```

The contract document does not change; only the import does.
