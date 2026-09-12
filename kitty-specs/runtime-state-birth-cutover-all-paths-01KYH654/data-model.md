# Data Model: "Cut Over" State

No new persisted schema. This mission defines and enforces an invariant over
existing corpus artifacts.

## Artifacts (existing)

| Artifact | Partition | Field of interest |
|----------|-----------|-------------------|
| `kitty-specs/<mission>/meta.json` | PRIMARY | `status_phase` (`"1"` = cut over; `null` or **key absent** = not cut over), `mission_id` (ULID, required at stamp time) |
| `kitty-specs/<mission>/status.events.jsonl` | COORD | append-only event log; deterministic seed rows (the `InnerStateChanged` quartet + a seed `planned→claimed`) plus live transitions |

## Definition: a mission is **cut over** iff ALL hold

1. `meta.json.status_phase == "1"` (present, not `null`, key not absent); **and**
2. the mission carries **event-log runtime evidence**
   (`_mission_carries_event_log_runtime`: annotations / non-empty
   `policy_metadata` in `status.events.jsonl`, read independently of frontmatter
   and independently of `status_phase`); **and**
3. the reduced snapshot is **non-empty** and the birth invariant holds
   (`_assert_birth_invariant_holds`); **and**
4. `verify_backfill` does not report a mismatch (necessary-not-sufficient: for a
   natively-born mission it is vacuously `ok` with `wp_count=0`, so it cannot be
   the sole signal).

A mission with event-log evidence but `status_phase != "1"` is **un-cut-over**
and must be caught by the guard. A `verify_backfill.ok=True` with no event-log
evidence and an empty snapshot is **not** proof of cut-over (vacuous-green trap).

## Seed determinism (identity + payload)

- **Identity**: `deterministic_ulid = sha256(mission_id | wp_id | field)` — no
  wall-clock, no randomness. Stable across runs/machines.
- **Payload**: the seed's `at` is the resolved claim anchor
  (`_resolve_anchor` → event-log `claimed` ts, else synthesized from
  `shell_pid_created_at` / `meta.json.created_at`). Payload stability requires the
  anchor to be resolved from **one canonical leg** so both stamp callers produce
  byte-identical rows (NFR-004 / R5).

## Landing-path × cut-over matrix (target invariant)

| Landing path | Before | After this mission |
|--------------|--------|--------------------|
| `spec-kitty merge` | cut over (#2920) | cut over (unchanged) |
| GitHub squash/rebase | **un-cut-over (leak)** | cut over (accept-time stamp committed in branch) |
| any path, stamp bypassed | drift lands silently | **blocked pre-merge by the guard** |
