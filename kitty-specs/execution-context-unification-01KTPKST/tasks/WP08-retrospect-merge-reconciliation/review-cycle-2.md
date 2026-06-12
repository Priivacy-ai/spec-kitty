---
affected_files: []
cycle_number: 2
mission_slug: execution-context-unification-01KTPKST
reproduction_command:
reviewed_at: '2026-06-10T05:17:36Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP08
---

# WP08 Review — Cycle 2 — APPROVED

## Summary

Cycle-1's single blocker — the #1771 gitignored retrospect *record* write — is
fixed. The record is relocated from the gitignored
`.kittify/missions/<mission_id>/retrospective.yaml` to the tracked
`kitty-specs/<mission_slug>/retrospective.yaml`, resolved through the canonical
coord-topology-aware read primitive (`resolve_feature_dir_for_slug` →
`resolve_mission_read_path`), with a read-only legacy fallback for
pre-relocation records. Cycle-1's already-approved items (#1735 status-event
surface routing, flattened-`CommitTarget.kind` parity flip, FR-007 merge no-op)
are unchanged and intact. Approving.

## Blocking Issue 1 (cycle-1) — RESOLVED

**The #1771 fix is real and proven by real git, not mocks.**
`tests/retrospective/test_record_committable_1771.py` — 3 passed — uses an
actual `git init` + the load-bearing `.kittify/missions/` ignore rule and real
`git check-ignore`:
- `test_canonical_record_path_is_not_gitignored` — the resolved record path is
  under `kitty-specs/`, NOT `.kittify`, and `git check-ignore` reports it
  committable.
- `test_legacy_path_was_gitignored_control` — the OLD `.kittify/missions/` path
  IS git-ignored (control proving the relocation actually moves the record off
  an ignored path).
- `test_written_record_is_committable_end_to_end` — `write_record()` lands the
  record where plain `git add` (no `-f`) stages it; `git diff --cached` confirms
  `retrospective.yaml` is staged.

**New writes go to the tracked home; no gitignored write remains.** All write /
emit sites now target `kitty-specs/<slug>/`:
- `write_record` (writer.py:135) → `canonical_record_path(...)`, `target_dir =
  canonical.parent`.
- `write_gen_record` (writer.py:524) → `canonical_record_path(...)`; final write
  `_atomic_write_gen(data, canonical, ...)` (writer.py:582) writes `canonical`,
  never `legacy`.
- `lifecycle_events.emit_captured` (lifecycle_events.py:341) → `feature_dir /
  "retrospective.yaml"` (feature_dir already resolved via the canonical read
  primitive).
- `summary._resolve_summary_record_path` reads from the tracked home, legacy
  fallback for discovery only.
Grep confirms no remaining `.kittify/missions/.../retrospective.yaml` *write*
target in src; all `.kittify/missions/` references are discovery/registry reads,
docstrings, or the legacy back-compat read.

**Legacy fallback is READ-only.** `legacy_record_path` has exactly two call
sites: writer.py:80 (inside `resolve_existing_record_path`, read resolution) and
writer.py:530 (as `prior` for error/update-mode detection). Neither is a write
target. New writes never touch the gitignored location.

**mission_id → mission_slug key change is sound and tested.** The record path is
now keyed by `mission_slug` (the tracked feature_dir) rather than `mission_id`.
The empty-key guard was re-targeted from `mission_id` to `mission_slug`
(writer.py:521) and is covered: `test_writer.py:483` and `test_events.py:851/861/877`
assert `WriterError`/`ValueError` match `mission_slug must be non-empty`. Reads
resolve correctly: tracked path preferred, legacy fallback when present, tracked
path returned when neither exists (canonical-location reporting for
RETROSPECTIVE_RECORD_MISSING).

## Regression check — cycle-1 approved items INTACT

- **#1735 status-event surface routing** through `resolve_status_surface`:
  unchanged in this commit (cycle-2 diff touches only the record-write path and
  its tests).
- **Flattened-`CommitTarget.kind` parity flip:**
  `tests/architectural/test_execution_context_parity.py` = 20 passed, 1 xfailed;
  the sole xfail is `test_runtime_lifecycle_action_parity` (F-008, "converges in
  WP07"), exactly as claimed. The flattened-kind test passes.
- **FR-007 merge no-op:** unchanged.

## Lifecycle / merge — GREEN

`pytest tests/retrospective tests/merge` = 679 passed, 0 failed (retrospect
create/backfill/gate/completed-check + merge-state machine + preflight).

## Gates

- **ruff:** clean on all 6 changed source files.
- **mypy:** zero net-new errors. The 28 `[type-arg]` / `no-any-return` findings
  are pre-existing baseline (e.g. `_atomic_write_gen(data: dict, ...)` exists
  verbatim at parent commit 5a159f115) and fall outside the cycle-2 hunks; none
  are in the new functions (`canonical_record_path`, `legacy_record_path`,
  `resolve_existing_record_path`, `_resolve_summary_record_path`).
- **terminology guard:** `tests/architectural/test_no_legacy_terminology.py` = 2
  passed; no `--feature` flag introduced in new lines.

## Verdict

APPROVED. The #1771 blocker is fixed and committable-by-real-git; cycle-1
approved items are intact; suites and gates are green.
