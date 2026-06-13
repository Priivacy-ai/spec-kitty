---
affected_files: []
cycle_number: 2
mission_slug: mission-lifecycle-dispatch-drg-closeout-01KV0S99
reproduction_command:
reviewed_at: '2026-06-13T17:16:02Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
review_artifact_override_at: "2026-06-13T17:24:12Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP01"
review_artifact_override_reason: "cycle2 re-review: mypy --strict exit 0 confirmed, _iso_str_to_datetime helper is type-only (no behavior change), lifecycle.py core untouched, all 11 WP01 tests + 329 status-suite tests green, ruff exit 0"
---

# WP01 Review — Cycle 1 (reviewer-renata)

**Verdict: REJECTED (one blocking issue).** The core deliverable is correct and well-tested.
The only blocker is 3 `mypy --strict` errors in WP01's owned file. They are trivial to fix.

## What passed (no action needed)

- **FR-002 crux is genuine.** `derive_mission_lifecycle` → `_classify_state(is_reopened=...)`
  is driven by the `MissionReopened` *event* via `_is_reopened(last_reopen_at > last_merge_at)`,
  NOT by clearing `merged_*`. `test_reopen_event_makes_merged_mission_actionable` exercises the
  real production path (emits the event, asserts `state == "reopened"`), and
  `test_remerge_after_reopen_drops_reopened_state` proves a later `merged_at` flips it back to
  archived. Delete the impl and these tests fail — not synthetic fixtures.
- **Registration:** both constants in `LIFECYCLE_EVENT_TYPES` and `__all__`; emit helpers via
  `append_lifecycle_event`/`_build_envelope` with `aggregate_type="Mission"`, `mission_id`
  attribution (NFR-004). `FollowUpRecorded` dedups on `(mission_id, commit_sha|pr_number)`;
  `MissionReopened` appends-each. All confirmed by tests.
- **Reducer-skip:** `test_events_round_trip_as_reducer_skipped` + `test_emitting_events_is_reducer_skipped`
  prove `read_events`/`reduce` ignore the two new types (WP snapshot byte-identical).
- **SaaS boundary:** new types NOT in `_EVENT_TYPE_TO_MODEL` (verified live: map size 92, neither
  present). `test_new_types_not_on_saas_strict_path` pins it. Local-only, documented inline.
- **Byte-stability:** `post_mission_events` sorted on `(timestamp, event_id)` via `_event_sort_key`.
- **Ownership:** only owned files touched. The out-of-map edit to
  `tests/architectural/test_no_dead_symbols.py` is a **reasonable, rationale-backed** WP-in-flight
  allowlist for the two emit helpers (production callers land in WP02/IC-02, which depends on WP01).
  The entry is documented and the ratchet enforces its removal when WP02 wires the callers. Not masking.
- **Dead-code gate:** the `test_no_public_symbol_in_all_is_unimported` failure flags
  `validators/paths::PathValidationError` — **pre-existing on the base branch**, unrelated to WP01
  (WP01 does not touch `validators/`). Out of scope per the Pre-existing Failure Reporting Rule.
  Note for closeout: the dead-symbol gate is already red on base; WP01 does not make it worse.

## Blocking issue — fix in WP01

**B1. `mypy --strict src/specify_cli/status/lifecycle_events.py` reports 3 errors.** SC-6 requires
`mypy --strict src/specify_cli/status/` to exit 0, and this is WP01's owned file, so these are
WP01's to clear. They are pre-existing (from a `spec_kitty_events 6.0.0` payload-type bump +
a now-redundant ignore) and live in `emit_project_initialized`/`emit_wp_created_local` — trivial
boundary fixes, no behavior change:

- `lifecycle_events.py:124` — `Unused "type: ignore" comment [unused-ignore]`.
  Drop the `# type: ignore[import-not-found]` on the `from ulid import ULID` line (stubs now resolve).
- `lifecycle_events.py:486` — `initialized_at` arg to `ProjectInitializedPayload` is `str`, contract
  now expects `datetime | None`. Coerce at the boundary (parse the ISO string to `datetime`, or pass
  the `datetime` directly) — same pattern used elsewhere in the package.
- `lifecycle_events.py:699` — same for `created_at` arg to `WPCreatedPayload`.

After fixing, confirm `mypy --strict src/specify_cli/status/lifecycle_events.py` exits 0 and the
existing tests still pass. (The remaining whole-package SC-6 errors live in `emit.py`/`aggregate.py`/
`__init__.py` — NOT WP01-owned, pre-existing, out of this WP's scope; flag for mission closeout/SC-6
tracking, do not attempt here.)
