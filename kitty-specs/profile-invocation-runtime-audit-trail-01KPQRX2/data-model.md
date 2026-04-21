# Data Model: Profile Invocation Runtime and Audit Trail

**Mission**: `profile-invocation-runtime-audit-trail-01KPQRX2`
**Date**: 2026-04-21

---

## Entity Overview

```
ProfileRegistry
    └── 1..* AgentProfile (from AgentProfileRepository, existing)

ProfileInvocationExecutor
    ├── uses ProfileRegistry
    ├── uses ActionRouter
    ├── uses build_charter_context() [existing, charter/context.py]
    └── calls InvocationWriter

InvocationRecord (persisted as JSONL)
    ├── opened by: ProfileInvocationExecutor.invoke()
    └── closed by: InvocationWriter.write_completed()

InvocationPayload (CLI response, ephemeral)
    └── derived from: InvocationRecord + CharterContextResult

RouterDecision | RouterAmbiguityError
    └── produced by: ActionRouter.route()

MinimalViableTrailPolicy (code constant)
    └── tier_1 → InvocationRecord
    └── tier_2 → EvidenceArtifact (optional)
    └── tier_3 → kitty-specs / doctrine artifact (optional)

InvocationSaaSPropagator (background)
    └── consumes: InvocationRecord
    └── produces: ProfileInvocationStarted / ProfileInvocationCompleted (SaaS envelopes)
```

---

## InvocationRecord (v1)

The canonical Tier 1 audit record. Written as a JSONL file; each line is a JSON object.

**File path**: `.kittify/events/profile-invocations/<invocation_id>.jsonl`
*(Keyed on invocation_id only — no profile_id prefix. Allows `profile-invocation complete --invocation-id <id>` with no other locator argument. Profile filtering in `invocations list` reads `profile_id` from the started-event content.)*
**Immutability rule**: lines are append-only. `started` event is written first; `completed` event is appended when `profile-invocation complete` is called.

### `started` event line

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event` | `"started"` | ✓ | Event discriminator |
| `invocation_id` | `str` (ULID) | ✓ | Globally unique invocation identity |
| `profile_id` | `str` | ✓ | Profile that was invoked |
| `action` | `str` | ✓ | Resolved canonical action token |
| `request_text` | `str` | ✓ | Original request string from caller |
| `governance_context_hash` | `str` | ✓ | First 16 hex chars of SHA-256 of `CharterContextResult.text` |
| `governance_context_available` | `bool` | ✓ | `false` when DRG/charter is missing |
| `actor` | `str` | ✓ | `"claude"` \| `"operator"` \| `"unknown"` |
| `router_confidence` | `str \| null` | ✓ | `"exact"` \| `"canonical_verb"` \| `"domain_keyword"` \| `null` (when profile_hint was explicit) |
| `started_at` | `str` (ISO-8601 UTC) | ✓ | Timestamp of invocation start |

### `completed` event line

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event` | `"completed"` | ✓ | Event discriminator |
| `invocation_id` | `str` (ULID) | ✓ | Must match `started` event |
| `outcome` | `"done" \| "failed" \| "abandoned" \| null` | ✓ | Caller-supplied outcome; `null` if not provided |
| `evidence_ref` | `str \| null` | ✓ | Relative path to Tier 2 EvidenceArtifact, or `null` |
| `completed_at` | `str` (ISO-8601 UTC) | ✓ | Timestamp of completion |

### State transitions

```
[no file]  ──→  started event written  ──→  completed event appended
              (executor.invoke())          (profile-invocation complete)
```

A file with only a `started` line is a valid open record. A file with both lines is a closed record. A file with multiple `started` lines or mismatched `invocation_id` is corrupt — reader must skip with a warning.

---

## InvocationPayload (ephemeral, CLI response)

Returned to the caller by `advise`, `ask`, and `do`. Not persisted.

| Field | Type | Description |
|-------|------|-------------|
| `invocation_id` | `str` | ULID — used by caller to call `profile-invocation complete` |
| `profile_id` | `str` | Resolved profile identity |
| `profile_friendly_name` | `str` | Human-readable profile name — sourced from `AgentProfile.name` |
| `action` | `str` | Resolved canonical action token |
| `governance_context_text` | `str` | Full `CharterContextResult.text` for this `(profile, action)` pair |
| `governance_context_hash` | `str` | Hash matching the `started` event record |
| `governance_context_available` | `bool` | `false` when charter is missing |
| `router_confidence` | `str \| null` | Routing confidence level; `null` when caller supplied explicit profile |

---

## RouterDecision

| Field | Type | Description |
|-------|------|-------------|
| `profile_id` | `str` | Resolved profile |
| `action` | `str` | Resolved canonical action token |
| `confidence` | `"exact" \| "canonical_verb" \| "domain_keyword"` | How the resolution was made |
| `match_reason` | `str` | Human-readable description (e.g., `"token 'implement' matched IMPLEMENTER canonical verb"`) |

---

## RouterAmbiguityError

Raised (or returned) when the router cannot unambiguously resolve a `(profile, action)` pair.

| Field | Type | Description |
|-------|------|-------------|
| `request_text` | `str` | Original request |
| `error_code` | `"ROUTER_AMBIGUOUS"` \| `"ROUTER_NO_MATCH"` \| `"PROFILE_NOT_FOUND"` | Machine-readable error type |
| `message` | `str` | Human-readable explanation |
| `candidates` | `list[RouterCandidate]` | Non-empty for `ROUTER_AMBIGUOUS`; empty for `ROUTER_NO_MATCH` |
| `suggestion` | `str` | E.g., `"Use 'spec-kitty ask <profile> <request>' to specify a profile explicitly"` |

### RouterCandidate

| Field | Type | Description |
|-------|------|-------------|
| `profile_id` | `str` | Candidate profile |
| `action` | `str` | Candidate action |
| `match_reason` | `str` | Why this candidate was surfaced |

---

## ProfileDescriptor (for `profiles list`)

| Field | Type | Description |
|-------|------|-------------|
| `profile_id` | `str` | Profile identity |
| `name` | `str` | Human-readable name — `AgentProfile.name` (the field is `name`, not `friendly_name`) |
| `role` | `str` | Role enum value or custom role string |
| `action_domains` | `list[str]` | Canonical verbs + domain keywords combined |
| `source` | `"shipped" \| "project_local"` | Whether profile is shipped or project-local override |

---

## MinimalViableTrailPolicy (code constant)

The formal specification of the three-tier audit contract. Immutable frozen dataclass.

```
MinimalViableTrailPolicy
├── tier_1: TierPolicy
│   ├── name: "every_invocation"
│   ├── mandatory: True
│   ├── description: "One InvocationRecord written locally before executor returns."
│   └── storage_path: ".kittify/events/profile-invocations/<profile_id>-<invocation_id>.jsonl"
├── tier_2: TierPolicy
│   ├── name: "evidence_artifact"
│   ├── mandatory: False
│   ├── description: "Optional EvidenceArtifact for invocations producing checkable output."
│   ├── storage_path: ".kittify/evidence/<invocation_id>/"
│   └── promotion_trigger: "caller sets evidence_ref on profile-invocation complete"
└── tier_3: TierPolicy
    ├── name: "durable_project_state"
    ├── mandatory: False
    ├── description: "Promotion to kitty-specs/ or doctrine when invocation changes project-domain state."
    └── promotion_trigger: "spec, plan, tasks, merge, accept commands only"
```

---

## EvidenceArtifact (Tier 2, optional)

Created by `promote_to_evidence(record, evidence_dir, content)`.

**Directory**: `.kittify/evidence/<invocation_id>/`
**Files**:
- `evidence.md` — content supplied by caller (Markdown)
- `record.json` — snapshot of the `InvocationRecord` at promotion time

---

## Storage Layout

```
.kittify/
└── events/
    ├── profile-invocations/
    │   ├── 01KPQRX2EVGMRVB4Q1JQBAZJV3.jsonl    # started + completed (profile_id inside)
    │   ├── 01KPQRX3XXXXXXXXXXXXXXXXXX.jsonl     # started only (open)
    │   └── ...
    ├── invocation-index.jsonl                                # optional; added if list latency > 200ms
    └── propagation-errors.jsonl                             # SaaS propagation failures

.kittify/
└── evidence/
    └── 01KPQRX2EVGMRVB4Q1JQBAZJV3/
        ├── evidence.md
        └── record.json
```

---

## Validation Rules

| Field | Rule |
|-------|------|
| `invocation_id` | Must be a valid ULID (26 chars, base32 Crockford) |
| `started_at` / `completed_at` | Must be ISO-8601 UTC (ends with `Z` or `+00:00`) |
| `outcome` | Must be one of `"done"`, `"failed"`, `"abandoned"`, or `null` |
| `event` discriminator | Must be `"started"` or `"completed"` |
| Two `started` events in same file | Reader warns and skips second; writer raises `InvocationWriteError` |
| `invocation_id` mismatch in `completed` | Reader skips the `completed` line with warning |
| `evidence_ref` path | Must be a relative path under `.kittify/evidence/`; validated on write |
