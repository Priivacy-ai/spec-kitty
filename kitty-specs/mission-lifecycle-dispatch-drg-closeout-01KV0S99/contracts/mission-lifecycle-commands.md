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
- **Fail-closed — concrete predicate:** "unrecoverable" =
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
- Allowed in **any** mission state (passive post-merge follow-ups are valid).
- **Idempotent**: dedup key `(mission_id, commit_sha | pr_number)` — re-recording the same
  reference is a no-op (no duplicate event).
- Surfaced in the mission lifecycle/history view (`post_mission_events`).
- Exit: 0 on success (including idempotent no-op); non-zero on invalid ref / unresolved handle.

## History surface

`spec-kitty mission` status/history (and the derived `lifecycle` view) renders
`post_mission_events` chronologically with actor, reason (re-open), and commit/PR (follow-up).
