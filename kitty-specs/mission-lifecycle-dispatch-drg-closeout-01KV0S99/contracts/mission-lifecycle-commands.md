# Contract — Post-mission lifecycle commands (workstream A, FR-001/002, NFR-004)

## `spec-kitty mission reopen <handle> --reason "<text>" [--json]`

- `<handle>`: `mission_id` (ULID) | `mid8` | `mission_slug` (resolver disambiguates by
  `mission_id`; ambiguous → structured `MISSION_AMBIGUOUS_SELECTOR`, no silent fallback).
- `--reason` is **required** (mirrors WP force-exit actor+reason discipline).
- Effect: appends a `MissionReopened` lifecycle event (actor detected); clears `merged_*`
  from `meta.json`. The mission becomes actionable because `derive_mission_lifecycle` honors
  the `MissionReopened` event (new `reopened` surface_state) — NOT merely because `merged_*`
  was cleared (clearing alone is a no-op for the classifier, which reads WP lanes + age).
- Does **not** mutate WP lanes (operator repositions WPs explicitly afterward).
- **Completion precondition (#1926, fail-closed):** a mission can only be re-opened once it has
  **reached completion** — `is_mission_completed(feature_dir)` is true iff `merged_at` is present
  in `meta.json` **OR** `derive_mission_lifecycle` classifies it `recently_completed`/`archived`
  (all WPs terminal). Checked **before** any metadata mutation or event emission: a re-open of a
  not-yet-completed mission exits non-zero with a structured error
  (`cannot re-open: mission has not completed/merged`); no `merged_*` is cleared, no event written.
  (Self-correcting: after a re-open clears `merged_*` and the state flips to `reopened`/active, the
  mission is no longer completed, so a second re-open is blocked until it is re-completed.)
- **Fail-closed — concrete unrecoverable predicate:** "unrecoverable" =
  (a) `meta.json` absent/corrupt (no resolvable `mission_id`), OR
  (b) the mission branch resolves in **neither** the local repo **nor** any configured remote
  (via the `core/vcs`/`git_ops` lookup the resolver uses).
  A missing **worktree directory alone is recoverable** (re-materializable from the branch)
  and does NOT fail closed. On unrecoverable: exit non-zero with a structured error +
  remediation hint; no event written, no metadata change.
- Reversible: a later `spec-kitty merge` re-stamps `merged_*`.
- Exit: 0 on success; non-zero structured error on unresolved/unrecoverable mission.

## `spec-kitty mission follow-up <handle> (--commit <sha> | --pr <n>) [--json]`

- Exactly one of `--commit <40-hex>` / `--pr <int>` (validated).
- Effect: appends a `FollowUpRecorded` lifecycle event attributed to `mission_id`.
- **Completion precondition (#1926, fail-closed):** a follow-up is a **post-mission** fact and is
  only valid once the mission has **reached completion** (`is_mission_completed(feature_dir)` —
  `merged_at` present **OR** `derive_mission_lifecycle` reports `recently_completed`/`archived`).
  A follow-up against a not-yet-completed mission exits non-zero with a structured error
  (`cannot record follow-up: mission has not completed/merged`); no event is written. Checked
  before emission. (Replaces the earlier "allowed in any mission state" behaviour.)
- **Idempotent**: dedup key `(mission_id, commit_sha | pr_number)` — re-recording the same
  reference is a no-op (no duplicate event).
- Surfaced in the mission lifecycle/history view (`post_mission_events`).
- Exit: 0 on success (including idempotent no-op); non-zero on invalid ref / unresolved handle /
  not-yet-completed mission.

## History surface

`spec-kitty mission` status/history (and the derived `lifecycle` view) renders
`post_mission_events` chronologically with actor, reason (re-open), and commit/PR (follow-up).
