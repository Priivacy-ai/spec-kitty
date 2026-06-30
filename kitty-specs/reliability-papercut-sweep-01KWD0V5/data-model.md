# Phase 1 Data Model: Reliability Papercut Sweep

This is a bug-fix mission over existing structures; no new persisted schema is introduced.
The entities below are the existing concepts whose *invariants* this mission repairs.

## Entities & Invariants

### Self-bookkeeping path (IC-01)
- **What**: a repo path the dirty-tree gate treats as non-blocking debris.
- **Members**: `meta.json`, the encoding-provenance log, and — newly — `kitty-ops/<ulid>.jsonl`.
- **Invariant (repaired)**: a `kitty-ops/<ulid>.jsonl` orphan is self-bookkeeping; genuine
  mission-relevant dirt is NOT. The self-bookkeeping set and the blocking set stay disjoint (G-5).

### MissionTopology (IC-02)
- **What**: `coord` | `single_branch`, produced by the pure `classify_topology(coordination_branch, has_coord)`.
- **Invariant (preserved)**: `classify_topology` is a pure `(str|None, bool) → MissionTopology`
  mapper — **no I/O, no git probe** (C-001). Git existence of a declared branch is decided by
  the *caller* (backfill / surface-resolver), which must not present a declared-but-absent
  branch as healthy `coord`.

### Canonical mission identity (IC-04, IC-06)
- **What**: `mission_id` (ULID, 26 chars) — the only runtime identity; `mid8` is its 8-char
  prefix; `mission_slug` is a human handle.
- **Invariant (repaired)**: `mission_id` persisted anywhere (decision events, coord branch
  composition) is ALWAYS a ULID. A slug is never substituted; an absent ULID fails closed.
  `mid8` is never empty in a composed coordination branch.

### target_branch resolution (IC-05)
- **What**: the merge/base branch read from primary `meta.json`.
- **Invariant (repaired)**: a *field-absent* read yields the documented default; a *read
  failure* (corrupt JSON, I/O error) surfaces a structured error — never a silent fallback to
  the repository default branch.

## State transitions
None changed. The mission repairs read/classification/identity invariants, not lifecycle states.

## Externally visible events
None added. Decision events keep their shape; only the `mission_id` field's content is corrected
(ULID, never slug).
