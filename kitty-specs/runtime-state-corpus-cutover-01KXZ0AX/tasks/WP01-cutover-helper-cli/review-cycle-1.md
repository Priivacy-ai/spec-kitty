---
affected_files: []
cycle_number: 1
mission_slug: runtime-state-corpus-cutover-01KXZ0AX
reproduction_command: null
reviewed_at: '2026-07-20T12:17:27Z'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP01
---

# WP01 Review — Cycle 1: CHANGES REQUESTED

The fail-closed `backfill → verify → atomic flip` spine is correct and well-proven (28 tests pass, real fault injection, `_flip_phase` unreachable on non-ok verify, canonicalized write target, sole `status_phase` writer, ruff+mypy clean, cx≤15). The C-006 frozenset **shrink** (16→11, removing only the 5 now-wired symbols) was verified **SOUND** and is accepted. Two fixes required before approval:

## BLOCKER — `--mission` bypasses the canonical handle resolver (charter: use canonical sources)
`src/specify_cli/cli/commands/migrate_cmd.py:592-601` resolves `--mission` with a raw directory join:
```python
mission_dir = repo_root / "kitty-specs" / mission
if not mission_dir.is_dir(): _error(...); raise typer.Exit(1)
```
But `_MISSION_HELP` (line 57) advertises "mission_id / mid8 / slug" and T002 requires the same. A raw join only matches the literal **slug** directory, so `--mission 01KXZ0AX` (mid8) or the full ULID falsely fails with "No mission directory found". The repo already has the canonical seam **`resolve_mission_handle(handle, repo_root, *, json_mode)`** at `src/specify_cli/cli/selector_resolution.py:183` (accepts ULID → mid8 → prefixed/human slug → numeric prefix), used by sibling `--mission` commands (`agent_retrospect.py`, `decision.py`, `_coordination_doctor.py`).

**Fix (preferred, fulfils T002):** route `--mission` through `resolve_mission_handle(mission, repo_root, json_mode=json_output)` and drive `cutover_mission`/`cutover_repo` off the resolved feature dir so mission_id/mid8/slug all resolve. Add a test asserting `--mission <mid8>` and `--mission <full-ULID>` resolve the dogfood mission (not just the slug).

## MINOR (fold this cycle) — dry-run mislabels healthy legacy missions as "Failed"
In `--dry-run` over an unseeded legacy corpus, `verify_backfill` is expectedly not-ok (seeds aren't written), so `_cutover_failed` (`migrate_cmd.py:639`) classifies every healthy mission as failed → `_print_cutover_summary` prints `Failed: N` + a mismatch wall, and `_cutover_payload` emits `verify_ok:false`. Exit code (0) and would-seed counts are correct, but the framing is misleading. **Fix:** in dry-run mode, do not classify verify-not-ok-pre-seed as "Failed" — relabel as "would seed (verify pending)" (or suppress the failed framing when `dry_run`). Add/extend a dry-run test asserting a healthy legacy corpus reports 0 "failed".

## Note (no action in WP01) — pass to WP03
The dead-symbol gate counts only `src/` callers. The retained residuals `read_legacy_runtime` / `LegacyWPRuntime` (annotated "WP03") will NOT drain if WP03 only adds *test-facing* usage. WP03 must land a `src/` caller for them, or fold their removal. (Recorded here for the mission lead; not WP01's to fix.)

## Unchanged / accepted
- C-006 shrink (sound, 4-way verified). Out-of-map edits to `test_no_dead_modules.py` + `_baselines.yaml` (forced ratchet consequence, accepted). `--skip-pre-review-gate` (legitimate — arch-dir 300s timeout limitation). Pre-existing `SYNC_DISABLE_ENV_VARS` red (not WP01's).
