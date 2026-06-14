# Data Model — Phase 1 (01KV0S99)

Only workstream A introduces new persisted data. B is behavior-preserving refactor
(no new schema); C edits generated/source doctrine (no new runtime model).

## New lifecycle event types (workstream A)

Both are **lifecycle** events appended to the existing per-mission stream
(`kitty-specs/<slug>/status.events.jsonl`), sharing the canonical envelope built by
`status/lifecycle_events.py::_build_envelope`. They are **reducer-skipped** (carry no
`to_lane`/`wp_id`), so WP snapshots are unaffected. `aggregate_id` = `mission_id` (ULID),
`aggregate_type` = `"Mission"`, `schema_version` matches the existing lifecycle stream.

**Registration (required):** both type constants MUST be added to the local
`LIFECYCLE_EVENT_TYPES` frozenset **and** `__all__` in `lifecycle_events.py` — otherwise
`append_lifecycle_event` silently drops them (and a *valid* re-open would degrade to
"no event written"). Keep them **off the SaaS strict-validation path** (do not add to the
external-package model map): they are local-only this mission; SaaS propagation is a follow-up
needing an external `spec_kitty_events` contract bump.

### `MissionReopened`

Records that a merged/closed mission was returned to an actionable state.
**Requires a prior completion** (#1926): only emittable once the mission has reached completion
(`is_mission_completed` — `merged_at` present **OR** `derive_mission_lifecycle` reports
`recently_completed`/`archived`). The producer (`emit_mission_reopened`) and the command layer both
guard this fail-closed; a re-open of a not-yet-completed mission raises `MissionNotCompletedError`
and writes no event / clears no `merged_*`.

| payload field | type | required | notes |
|---|---|---|---|
| `mission_id` | str (ULID) | yes | canonical identity; lookup key |
| `mission_slug` | str | yes | human handle (display) |
| `reason` | str (non-empty) | yes | audit; mirrors WP force-exit `reason` discipline |
| `reopened_by` | str (actor) | yes | detected actor |
| `reopened_at` | str (ISO-8601 UTC) | yes | event time |
| `cleared_merge` | object\|null | no | snapshot of the `merged_*` fields cleared from `meta.json` (for reversibility/audit) |

- **Semantics:** appended *each* time (every re-open is a distinct fact — NOT deduped).
  Side effects: clears `merged_at/by/commit/into/strategy` from `meta.json` (audit/reversibility)
  AND — the part that actually makes the mission actionable — `derive_mission_lifecycle` is
  taught to treat a `MissionReopened` that postdates the last merge/completion marker as the
  **authority**, yielding a `reopened` surface_state until a subsequent merge re-stamps
  `merged_*`. (Clearing `merged_*` alone is a no-op: the classifier reads WP lanes + age, not
  `merged_*` — review-verified.) Does **not** mutate WP lanes.
- **Fail-closed (NFR-004):** if the mission cannot be resolved through `mission_id` + git
  registry (branch/worktree unrecoverable), no event is written; a structured error +
  remediation hint is returned.

### `FollowUpRecorded`

Records a follow-up commit or PR against an **already-completed** mission (#1926). A follow-up is a
post-mission fact — only valid once the mission has reached completion (same `is_mission_completed`
predicate as `MissionReopened`). Recording one against a not-yet-completed mission raises
`MissionNotCompletedError` and writes no event. (Supersedes the earlier "allowed in any state"
design.)

| payload field | type | required | notes |
|---|---|---|---|
| `mission_id` | str (ULID) | yes | attribution key |
| `mission_slug` | str | yes | display |
| `follow_up_type` | `"commit"` \| `"pr"` | yes | discriminator |
| `commit_sha` | str (40-hex) \| null | conditional | required iff type==commit |
| `pr_number` | int \| null | conditional | required iff type==pr |
| `recorded_by` | str (actor) | yes | detected actor |
| `recorded_at` | str (ISO-8601 UTC) | yes | event time |

- **Semantics:** valid only once the mission has **reached completion** (post-mission fact, #1926).
  **Idempotent** via dedup key `(mission_id, commit_sha | pr_number)` — re-recording the
  identical `--commit`/`--pr` reference is a no-op (no duplicate event), consistent with the
  existing `has_lifecycle_event()` dedup pattern.
- **Cross-type dedup is intentionally NOT attempted:** a commit and the PR that contains it
  are recorded as **distinct** follow-up facts by design (no resolved-commit-of-PR lookup).
  Dedup only suppresses re-recording the *same* reference.

## Derived view + classification extension

`status/lifecycle.py::derive_mission_lifecycle` changes in two ways:
1. **Classification (the FR-002 crux):** `_classify_state` gains a `reopened` state/surface_state
   — when the latest `MissionReopened` postdates the last merge/completion marker and is not
   itself followed by a re-merge, the mission is actionable regardless of WP terminality.
2. **Rendering:** the result gains a `post_mission_events` list (MissionReopened +
   FollowUpRecorded, sorted by `(timestamp, event_id)` for byte-stable `lifecycle.json`) and
   `last_follow_up_at`. `status/views.py` renders these in the lifecycle/history surface.

The result dataclass is `frozen` and serialized with `sort_keys=True`; adding fields changes
`lifecycle.json` on next regen, so update any golden-file in the **same** change. No change to
WP `status.json` (reducer untouched).

## `meta.json` interaction

No new persisted field. Re-open **removes** the existing optional `merged_*` keys
(`mission_metadata.py`); a later merge re-stamps them. `mission_id`/`mission_number` are
immutable across re-open (number reused on re-merge — deferred sub-decision, default reuse).

## Invariants

- Event log is append-only; no past line is rewritten (reducer determinism preserved).
- **Post-mission events require completion (#1926):** both `MissionReopened` and `FollowUpRecorded`
  are emittable only when `is_mission_completed` is true. The producer guards fail-closed, so no
  emit path can record a post-mission fact for a not-yet-completed mission.
- `FollowUpRecorded` is idempotent on its dedup key; `MissionReopened` is append-each.
- Every closing behavior carries pinning regression coverage (NFR-005).
