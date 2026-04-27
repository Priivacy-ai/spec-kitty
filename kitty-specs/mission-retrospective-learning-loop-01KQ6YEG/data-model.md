# Phase 1 Data Model: Mission Retrospective Learning Loop

**Mission**: `01KQ6YEGT4YBZ3GZF7X680KQ3V` (mid8: `01KQ6YEG`)
**Plan**: [./plan.md](./plan.md)
**Research**: [./research.md](./research.md)
**Date**: 2026-04-27

This document specifies entities, fields, validation rules, and state transitions. The contract files under `contracts/` reference this model and turn it into per-surface contracts. All entities are Pydantic v2 models; field types use Python annotations.

---

## Identity primitives

| Type | Definition | Notes |
|---|---|---|
| `MissionId` | 26-char ULID string | Canonical mission identity (post-083). |
| `Mid8` | 8-char prefix of `MissionId` | Used in branch / worktree names; never as identity. |
| `EventId` | 26-char ULID string | Stable id of a mission event in `status.events.jsonl`. |
| `ProposalId` | 26-char ULID string | Stable id assigned at proposal generation; survives synthesis. |
| `Timestamp` | ISO-8601 UTC, second-precision minimum | `2026-04-27T07:46:18.715532+00:00` shape used elsewhere in the project. |
| `ActorRef` | `{kind: "human" | "agent" | "runtime", id: str, profile_id: str | None}` | Identifies who authored or approved an entry. |

---

## Entity: `RetrospectiveRecord`

The top-level model serialized as `retrospective.yaml`. One per mission (with re-runs preserved as additional events; the latest yaml record wins for the gate).

### Required fields

| Field | Type | Source | Notes |
|---|---|---|---|
| `schema_version` | `Literal["1"]` | constant | Pinned for forward compatibility. |
| `mission` | `MissionIdentity` | meta.json | See `MissionIdentity` below. |
| `mode` | `Mode` | mode detection | See `Mode` below. |
| `status` | `Literal["completed", "skipped", "failed", "pending"]` | runtime | See state diagram. |
| `started_at` | `Timestamp` | event `retrospective.started` | Required even when `status=skipped` (records when the offer was made). |
| `completed_at` | `Timestamp \| None` | event `retrospective.completed` or `retrospective.skipped` or `retrospective.failed` | Set when status leaves `pending`. |
| `actor` | `ActorRef` | runtime | Who ran (or skipped) the retrospective. |
| `helped` | `list[Finding]` | facilitator output | May be empty. |
| `not_helpful` | `list[Finding]` | facilitator output | May be empty. |
| `gaps` | `list[Finding]` | facilitator output | May be empty. |
| `proposals` | `list[Proposal]` | facilitator output | May be empty; proposals carry their own lifecycle state. |
| `provenance` | `RecordProvenance` | runtime | Who/what authored the record itself. |

### Optional fields

| Field | Type | When present |
|---|---|---|
| `skip_reason` | `str` | Required when `status=="skipped"`; absent otherwise. |
| `failure` | `RetrospectiveFailure` | Required when `status=="failed"`; absent otherwise. |
| `successor_mission_id` | `MissionId \| None` | Set if a subsequent retrospective record supersedes this one (re-run). |

### Validation rules

- `status=="skipped"` ⇒ `skip_reason is not None and len(skip_reason) > 0`.
- `status=="completed"` ⇒ `completed_at is not None`.
- `status=="failed"` ⇒ `failure is not None`.
- `status=="pending"` is only valid in-memory or in transit; the writer refuses to persist a `pending` record (NFR-002 invariant).
- All `EventId` references in any nested `Provenance` must exist in the mission's event log at write time. (Soft check: writer warns; reader treats unreachable references as `[degraded]` markers in summary, not as schema failure.)
- `mission.mission_id` must be a valid ULID string.

### State transitions (record `status`)

```
                 +--- skipped ---+
                 |               |
   pending ----> +--- completed -+--> (terminal: file persisted)
                 |               |
                 +--- failed ----+
```

`pending` is never persisted. Transitions are driven by retrospective events; the writer materializes the in-memory record at the moment of `completed`/`skipped`/`failed` and never returns to `pending`.

---

## Entity: `MissionIdentity` (embedded)

```python
class MissionIdentity(BaseModel):
    mission_id: MissionId
    mid8: Mid8
    mission_slug: str
    mission_type: str           # e.g., "software-dev", "research", "documentation", "<custom>"
    mission_started_at: Timestamp
    mission_completed_at: Timestamp | None
```

Sourced from `meta.json` and the mission's event log. Snapshotted at retrospective write time; the record is durable independent of later `meta.json` mutations.

---

## Entity: `Mode` (embedded)

```python
class ModeSourceSignal(BaseModel):
    kind: Literal["charter_override", "explicit_flag", "environment", "parent_process"]
    evidence: str               # short human-readable description: charter clause id / flag value / env var name / process name

class Mode(BaseModel):
    value: Literal["autonomous", "human_in_command"]
    source_signal: ModeSourceSignal
```

Source signal precedence: `charter_override > explicit_flag > environment > parent_process` (FR-016, C-013, R-001).

---

## Entity: `Finding`

A single entry inside `helped`, `not_helpful`, or `gaps`.

```python
class Finding(BaseModel):
    id: str                                   # short stable id, unique inside the record
    target: TargetReference                   # what the finding is about
    note: str                                 # ≤2000 chars; human-readable observation
    provenance: FindingProvenance
```

```python
class TargetReference(BaseModel):
    kind: Literal[
        "doctrine_directive", "doctrine_tactic", "doctrine_procedure",
        "drg_edge", "drg_node",
        "glossary_term",
        "prompt_template",
        "test",
        "context_artifact",
    ]
    urn: str                                  # canonical reference (e.g., "drg:edge:<id>", "glossary:term:<key>")

class FindingProvenance(BaseModel):
    source_mission_id: MissionId
    evidence_event_ids: list[EventId]         # ≥1 required
    actor: ActorRef
    captured_at: Timestamp
```

### Validation rules

- `Finding.id` must be unique within the surrounding record.
- `Finding.target.urn` must be syntactically well-formed for its `kind` (per a small URN dispatch table in `schema.py`).
- `provenance.evidence_event_ids` must have at least one entry; if a mission produced zero events, the gate refuses to write a non-empty `helped`/`not_helpful`/`gaps` list (the empty-evidence edge case is `gaps=[]` etc., not synthetic-evidence).

---

## Entity: `Proposal`

A machine-actionable change request.

```python
class Proposal(BaseModel):
    id: ProposalId
    kind: Literal[
        "synthesize_directive", "synthesize_tactic", "synthesize_procedure",
        "rewire_edge", "add_edge", "remove_edge",
        "add_glossary_term", "update_glossary_term",
        "flag_not_helpful",
    ]
    payload: ProposalPayload                  # discriminated union; see contracts/retrospective_yaml_v1.md
    rationale: str                            # ≤2000 chars
    state: ProposalState
    provenance: ProposalProvenance
```

```python
class ProposalState(BaseModel):
    status: Literal["pending", "accepted", "rejected", "applied", "superseded"]
    decided_at: Timestamp | None              # set when status moves out of pending
    decided_by: ActorRef | None
    apply_attempts: list[ProposalApplyAttempt]  # may be empty

class ProposalApplyAttempt(BaseModel):
    attempt_id: EventId                       # references a `retrospective.proposal.applied` or `.rejected` event
    at: Timestamp
    outcome: Literal["applied", "rejected_conflict", "rejected_stale", "rejected_invalid"]
    error: str | None
```

```python
class ProposalProvenance(BaseModel):
    source_mission_id: MissionId
    source_evidence_event_ids: list[EventId]
    authored_by: ActorRef                     # the facilitator that proposed it
    approved_by: ActorRef | None              # set when state becomes "accepted" or "applied"
```

### Validation rules

- `kind == "flag_not_helpful"` ⇒ payload references at most one target URN; auto-applicable.
- All other kinds ⇒ payload must include the proposal-kind-specific fields enumerated in `contracts/retrospective_yaml_v1.md`. Default policy: **staged**, never auto-applied (FR-020, Q2-A).
- `state.status == "applied"` ⇒ `apply_attempts` contains at least one `outcome == "applied"` entry.
- `state.status == "rejected"` is a human-rejection (declined for content). Conflict / staleness / validity rejections at apply time are recorded as `apply_attempts[*].outcome` while keeping `state.status == "accepted"`, so the proposal can be retried after the conflict is resolved.

### State transitions (`ProposalState.status`)

```
   pending --(human reject)--> rejected (terminal)
   pending --(human accept)--> accepted
   accepted --(synthesize, no conflict)--> applied (terminal)
   accepted --(synthesize, conflict/stale/invalid)--> accepted   # records an apply_attempt; retries possible
   accepted --(later proposal supersedes)--> superseded (terminal)
   applied --(no further state)
```

`flag_not_helpful` skips `pending` and goes directly `accepted → applied` (auto-application), still recording an `apply_attempt`.

---

## Entity: `RecordProvenance`

```python
class RecordProvenance(BaseModel):
    authored_by: ActorRef                     # the facilitator that wrote the record
    runtime_version: str                      # spec-kitty CLI version
    written_at: Timestamp
    schema_version: Literal["1"]
```

---

## Entity: `RetrospectiveFailure`

```python
class RetrospectiveFailure(BaseModel):
    code: Literal[
        "writer_io_error", "schema_invalid", "facilitator_error",
        "evidence_unreachable", "mode_resolution_error", "internal_error",
    ]
    message: str
    error_chain: list[str]                    # short chain of contributing errors; bounded ≤16
```

---

## Entity: `GateDecision` (in-memory only; not serialized in `retrospective.yaml`)

The lifecycle gate's return type. Consumed by `next` and any other caller.

```python
class GateDecision(BaseModel):
    allow_completion: bool
    mode: Mode
    reason: GateReason

class GateReason(BaseModel):
    code: Literal[
        "completed_present",                  # autonomous: completed event present
        "skipped_permitted",                  # HiC: skip event present
        "completed_present_hic",              # HiC: completed event present
        "missing_completion_autonomous",      # autonomous block
        "silent_skip_attempted",              # autonomous: skip seen, blocking
        "silent_auto_run_attempted",          # HiC: completed seen without operator action
        "charter_override_blocks",            # charter clause forbids the requested transition
        "facilitator_failure",                # retrospective.failed event present
    ]
    detail: str
    blocking_event_ids: list[EventId]
    charter_clause_ref: str | None            # set when code == "charter_override_blocks"
```

`GateDecision` is the externally observable property NFR-008 requires: same event log + same mode signals → same decision.

---

## Entity: `RetrospectiveEventEnvelope` (mission event log)

Retrospective events are appended into the canonical `status.events.jsonl`. They share the existing envelope (sorted-key JSON, mission-scoped) and add the eight retrospective-specific names.

| Event name | Payload Pydantic model | Allowed transitions |
|---|---|---|
| `retrospective.requested` | `RequestedPayload` | mission terminus (autonomous); operator action (HiC) |
| `retrospective.started` | `StartedPayload` | facilitator dispatch begins |
| `retrospective.completed` | `CompletedPayload` | record persisted with `status=completed` |
| `retrospective.skipped` | `SkippedPayload` | record persisted with `status=skipped` (HiC only) |
| `retrospective.failed` | `FailedPayload` | record persisted with `status=failed`, or write itself failed |
| `retrospective.proposal.generated` | `ProposalGeneratedPayload` | one per proposal at write time |
| `retrospective.proposal.applied` | `ProposalAppliedPayload` | one per successful apply attempt |
| `retrospective.proposal.rejected` | `ProposalRejectedPayload` | one per rejection (human or apply-time) |

Payload field minimums are pinned in `contracts/retrospective_events_v1.md`.

---

## Cross-mission summary entities (read-side)

```python
class SummarySnapshot(BaseModel):
    project_path: str
    generated_at: Timestamp
    mission_count: int
    completed_count: int
    skipped_count: int
    failed_count: int
    in_flight_count: int
    legacy_no_retro_count: int
    terminus_no_retro_count: int
    malformed: list[MalformedSummaryEntry]

    not_helpful_top: list[TargetCount]                # sorted desc by count
    missing_terms_top: list[TermCount]
    missing_edges_top: list[EdgeCount]
    over_inclusion_top: list[TargetCount]
    under_inclusion_top: list[TargetCount]
    proposal_acceptance: ProposalAcceptanceMetrics
    skip_reasons_top: list[ReasonCount]

class MalformedSummaryEntry(BaseModel):
    mission_id: MissionId | None              # None if mission_id couldn't be parsed
    path: str
    reason: str

class ProposalAcceptanceMetrics(BaseModel):
    total: int
    accepted: int
    rejected: int
    applied: int
    pending: int
    superseded: int
```

Top-N counts are bounded (default 20) and tunable via the CLI.

---

## Validation pipeline

For any read or write of a retrospective record:

1. **Pydantic schema validation** — types, enums, required-vs-optional, regex on URN forms.
2. **Cross-field validation** — status/skip_reason/failure/completed_at consistency (see "Validation rules" above).
3. **Provenance reachability check** — soft, evidence event ids referenced by findings/proposals should exist in the mission event log.

The reader returns either a `RetrospectiveRecord` (Pydantic-validated, cross-field-checked, evidence-checked-or-degraded) or a `SchemaError` describing the first failure with field path and reason.

---

## Closure

This data model is the source of truth for `contracts/retrospective_yaml_v1.md`, `contracts/retrospective_events_v1.md`, `contracts/gate_api.md`, and `contracts/synthesizer_hook.md`. Tasks must derive their fixtures and unit tests from this model.
