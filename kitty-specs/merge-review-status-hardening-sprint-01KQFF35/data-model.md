# Data Model: Merge Abort, Review, and Status Hardening Sprint

**Mission ID**: 01KQFF35BPH2H8971KR0TEY8ST

This mission modifies no persistent data models. All changes operate on
existing data shapes. This document records the relevant entities and any
new fields or validation rules introduced.

---

## Existing Entity: Lock File

**Path**: `.kittify/runtime/merge/__global_merge__/lock`
**Type**: Empty sentinel file
**Invariant**: Presence means a merge is in progress or was interrupted.
**New behaviour (WP01)**: `merge --abort` must remove this file idempotently.

---

## Existing Entity: MergeState

**Path**: `.kittify/merge-state.json`
**Schema**: See `src/specify_cli/merge/state.py` — `MergeState` dataclass
**New behaviour (WP01)**: `merge --abort` must remove this file idempotently.
No schema changes.

---

## Existing Entity: ReviewCycleArtifact

**Path**: `kitty-specs/<slug>/tasks/<WP-dir>/review-cycle-N.md`
**Frontmatter fields** (partial):
```yaml
verdict: approved | approved_after_orchestrator_fix | arbiter_override | rejected
```

**New validation (WP02)**: The `verdict` field is validated against the above
enum at force-approve time. Unknown values emit a warning; they do not block
the command (backward compatibility with artifacts that predate this mission).

---

## Existing Entity: StatusEvent

**Path**: `kitty-specs/<slug>/status.events.jsonl` (one JSON object per line)
**Relevant fields**:
```json
{
  "wp_id": "WP01",
  "to_lane": "in_review",
  "at": "2026-04-30T15:00:00+00:00"
}
```

**New derived property (WP06)**: `age_in_review_minutes` — computed at render
time as `(now_utc - last_event.at).total_seconds() / 60`. Not persisted.

---

## New Entity: MissionReviewReport

**Path**: `kitty-specs/<slug>/mission-review-report.md`
**Written by**: `spec-kitty review --mission <slug>` (WP07)

**Frontmatter schema**:
```yaml
---
verdict: pass | pass_with_notes | fail
reviewed_at: <ISO 8601 timestamp with timezone>
findings: <non-negative integer>
---
```

**Verdict rules**:
- `pass` — all WPs done, zero dead-code findings, zero unjustified BLE001 suppressions
- `pass_with_notes` — all WPs done, dead-code or BLE001 findings present but
  all findings are informational (e.g., dead code is intentional public API)
- `fail` — one or more WPs not in `done`, OR one or more hard findings

**Body**: Bulleted list of findings. Each finding records:
- Type: `dead_code` | `ble001_suppression` | `wp_not_done`
- Location: `<file>:<line>` for code findings, WP ID for lane findings
- Description: one-line explanation

---

## Config Schema Addition (WP06)

**File**: `.kittify/config.yaml`
**New optional key**:
```yaml
review:
  stall_threshold_minutes: 30   # default; any positive integer
```

If the key is absent, the runtime defaults to 30 minutes. No migration needed —
the key is optional and additive.
