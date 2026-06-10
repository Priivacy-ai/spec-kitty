# Data Model: Do Dispatch Open-Op Lifecycle

## Entities

### OpStartedEvent (replaces started-mode `InvocationRecord`)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `event` | `Literal["started"]` | yes | discriminator |
| `invocation_id` | str (ULID, 26) | yes | identity; filename stem |
| `profile_id` | str | yes | resolved agent profile |
| `action` | str | yes | canonical action token; non-empty |
| `request_text` | str | yes | verbatim user request (may be empty only for query mode) |
| `actor` | str | yes | "claude" \| "codex" \| "operator" \| … (detected, never silently "unknown" when detectable) |
| `mode_of_work` | str | yes | task_execution \| advisory \| mission_step \| query |
| `governance_context_hash` | str | yes | 16 hex chars; empty string only when `governance_context_available=false` |
| `governance_context_available` | bool | yes | |
| `router_confidence` | str \| None | no | exact \| canonical_verb \| domain_keyword; None when profile explicit |
| `started_at` | str (ISO-8601 UTC) | yes | |
| `mission_id` | str \| None | no | standalone Ops: None |
| `wp_id` | str \| None | no | |

Frozen Pydantic v2 model. Serialized as the first JSONL line; write-once (exclusive create).

### OpCompletedEvent (new)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `event` | `Literal["completed"]` | yes | discriminator |
| `invocation_id` | str (ULID) | yes | must match file |
| `completed_at` | str (ISO-8601 UTC) | yes | |
| `outcome` | `Literal["done","failed","abandoned"]` | **yes** | non-null by construction |
| `closed_by` | `Literal["agent","doctor_sweep"]` | yes | who closed: working agent vs stale sweep |
| `evidence_ref` | str \| None | no | Tier 2 promotion path; mode-gated (advisory/query refuse) |

Frozen Pydantic v2 model. Appended once; second append attempt → `AlreadyClosedError`. Carries **no** started-only fields — invalid blank-default states are unrepresentable.

### Unchanged event shapes (same JSONL file)

- `artifact_link` — `{event, invocation_id, kind, ref, at}`
- `commit_link` — `{event, invocation_id, sha, at}`
- `glossary_checked` — existing bundle shape

### Op file (`kitty-ops/<invocation_id>.jsonl`)

Append-only event log. Line order: started → [glossary_checked] → [completed] → [artifact_link*] → [commit_link]. The file, read alone, answers who/what/when/why/outcome (FR-005).

### Ops index (`kitty-ops/ops-index.jsonl`)

Unchanged: `{invocation_id, profile_id, started_at}` per started event.

## State Machine (Op lifecycle)

```
            do / ask / advise                    profile-invocation complete
 (none) ────────────────────────► OPEN ─────────────────────────────────────► CLOSED(done|failed)
                                   │                                              ▲
                                   │  doctor ops --close-stale (age > threshold)  │
                                   └──────────────────────────────────────────────┘
                                                CLOSED(abandoned, closed_by=doctor_sweep)
```

**Invariants**
1. A started event exists before any other event in the file (exclusive create).
2. At most one completed event per Op; double close raises `AlreadyClosedError` (idempotent for sweep: reported, not fatal).
3. `outcome` is never null on a completed event; `done` is never written by dispatch — only by an explicit close.
4. Open Ops are never auto-committed to git; closed Ops are auto-committed at close time (including sweep closes), commit message `op(<profile>): <action> [<id8>]`.
5. Evidence promotion is refused for advisory/query modes (existing FR-009 gate preserved).
6. Sweep closes only Ops with `started_at` older than threshold; `--threshold 0` means all open Ops.

## Migration mapping (legacy → v2)

| Legacy record | Disposition |
|---------------|-------------|
| started event with `invocation_id` + `profile_id` | rewrite → `OpStartedEvent` (missing `mode_of_work` → `"task_execution"`; `actor` preserved when non-empty) |
| started event with missing/empty `actor` or `action` | emit the literal `"unrecorded"` for the missing field — never fabricate a plausible value |
| completed event with non-null `outcome` | rewrite → `OpCompletedEvent`, `closed_by="agent"` (missing `completed_at` → fall back to the started event's `started_at`, flagged in the migration report) |
| completed event with null `outcome` (old auto-close artifacts) | rewrite → `OpCompletedEvent`, `outcome="abandoned"`, `closed_by="agent"` |
| link/glossary events | pass through unchanged |
| file with unparseable/identity-less started event | delete file |
| file already v2 (completed has `closed_by`) | skip (idempotency) |
