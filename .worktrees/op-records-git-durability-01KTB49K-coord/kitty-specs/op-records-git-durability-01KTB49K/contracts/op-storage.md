# Contract: Op Storage and Git Commit

**Mission**: op-records-git-durability-01KTB49K  
**Date**: 2026-06-05  
**Status**: Proposed

---

## Storage Location

All Op records are written to `kitty-ops/` under the repository root. This directory is git-tracked.

```
kitty-ops/
├── <op_id>.jsonl          # one per Op (ULID filename)
├── ops-index.jsonl        # performance index
├── lifecycle.jsonl        # loop-lifecycle pairing log
└── propagation-errors.jsonl
```

**Always true**:
- `kitty-ops/` is not listed in `.gitignore`
- `kitty-ops/<op_id>.jsonl` is named after the Op's ULID only (no profile prefix)

---

## JSONL Event Schema

Each `<op_id>.jsonl` contains exactly two event lines (append-only):

### Line 1 — `started` event

Required fields (always present):

| Field | Type | Description |
|-------|------|-------------|
| `event` | `"started"` | Discriminator |
| `invocation_id` | `string` (ULID, 26 chars) | Op identity |
| `profile_id` | `string` | Agent profile that governed this Op |
| `action` | `string` | Canonical action token (e.g. `"investigate"`) |
| `started_at` | `string` (ISO-8601 UTC) | Wall-clock timestamp |

Optional fields (omitted when `None`):

| Field | Type | Description |
|-------|------|-------------|
| `request_text` | `string` | User's input text |
| `governance_context_hash` | `string` | First 16 hex chars of SHA-256 of context |
| `governance_context_available` | `bool` | Whether charter context was loadable |
| `actor` | `string` | `"claude"` \| `"operator"` \| `"unknown"` |
| `router_confidence` | `string \| null` | `"exact"` \| `"canonical_verb"` \| `"domain_keyword"` |
| `mode_of_work` | `string \| null` | `"advisory"` \| `"query"` \| `"execution"` |
| `mission_id` | `string \| null` | ULID of the mission context (null for standalone) |
| `wp_id` | `string \| null` | Work package ID (null for standalone) |

### Line 2 — `completed` event

Required fields:

| Field | Type | Description |
|-------|------|-------------|
| `event` | `"completed"` | Discriminator |
| `invocation_id` | `string` (ULID) | Must match the `started` event |
| `profile_id` | `string` | Copied from started event |
| `action` | `""` | Empty string (not re-stated in completed) |
| `completed_at` | `string` (ISO-8601 UTC) | Wall-clock timestamp |

Optional fields:

| Field | Type | Description |
|-------|------|-------------|
| `outcome` | `"done" \| "failed" \| "abandoned" \| null` | |
| `evidence_ref` | `string \| null` | Path or URL to evidence artifact |

---

## Git Commit Contract

**Trigger**: The `completed` event is successfully appended to `kitty-ops/<op_id>.jsonl`.

**Message format**:
```
op(<profile_id>): <action> [<op_id[:8]>]
```

Examples:
```
op(debugger-debbie): investigate [01KTB49K]
op(researcher-ryan): research [01KTB49J]
```

**Always true**:
- The commit message starts with `op(`
- `git log --grep="^op("` returns only Op commits and no other commits
- The commit stages exactly `kitty-ops/<op_id>.jsonl` and `kitty-ops/ops-index.jsonl`

---

## Orphan Definition

An Op is an **orphan** if:
- `kitty-ops/<op_id>.jsonl` exists as an untracked working-tree file, AND
- The file does NOT contain a line where `"event" == "completed"`

Orphans are never committed to git. `spec-kitty doctor ops` reports them.

---

## Backward Compatibility

- Pre-fix records in `.kittify/events/profile-invocations/` are abandoned. They are never read, migrated, or deleted by this mission.
- The `InvocationRecord` model change is additive — existing records without `mission_id`/`wp_id` fields deserialise correctly (fields default to `None`).
