---
affected_files: []
cycle_number: 1
mission_slug: wp-runtime-state-eviction-01KXWN13
reproduction_command:
reviewed_at: '2026-07-19T12:15:00Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP04
review_artifact_override_at: "2026-07-19T12:28:33Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP04"
review_artifact_override_reason: "Cycle2 review passed: _check_unchecked_subtasks flag aligned to WP01/WP02 (ON->snapshot, OFF->legacy) at tasks_shared.py:503; red test runs status_phase=1 (flag ON) green with genuinely-incomplete control still refusing; T017 fixtures realigned; T015 untouched; 8/8 tests pass. Supersedes cycle-1 flag-inversion rejection."
---

# WP04 Review — REJECTED (flag-semantics inversion)

Reviewer: reviewer-renata. Verdict: **REJECT → planned.**

The T015 emit half is correct and should be kept. WP04 is rejected for a single
but load-bearing cross-WP contract defect in the T016 reader half:
`_check_unchecked_subtasks` inverts the `_phase1_dual_write_enabled` flag
relative to the APPROVED foundation (WP01) and the APPROVED WP02.

## Confirmed defect — flag inversion (direct evidence)

The flag has ONE physical meaning: `status_phase == "1"`
(`status/emit.py::_phase1_dual_write_enabled`). Three readers of that same flag:

- **WP01 canonical (approved)** — `status/emit.py::_infer_subtasks_complete:325`
  `if _phase1_dual_write_enabled(...): return <snapshot>` else `<legacy tasks.md>`.
  Docstring is explicit: *flag ON → reduced snapshot (target state, FR-003);
  flag OFF → pre-WP03 default, legacy tasks.md.*
- **WP02 (approved)** — `tasks_transition_core.py::_snapshot_unchecked_subtasks:462`
  `if not _phase1_dual_write_enabled(...): return None  # legacy` else `<snapshot>`.
  Same convention: flag ON → snapshot, flag OFF → legacy.
- **WP04 (this WP) — INVERTED** — `tasks_shared.py::_check_unchecked_subtasks:498`
  `if _phase1_dual_write_enabled(...): return [<legacy tasks.md unchecked>]`
  else `<snapshot>`. i.e. **flag ON → legacy, flag OFF → snapshot.**

A single flag with opposite meanings across WP02 (approved) and WP04 is a latent
mis-gate: both readers feed the SAME `move-task --to for_review` subtask guard
(`_guard_subtasks` prefers WP02's `_snapshot_unchecked_subtasks`, falls back to
`req.unchecked_subtasks` populated by WP04's `_check_unchecked_subtasks`). The
two paths resolve completion from opposite sources under the same flag value —
which reader decides the gate silently depends on stream/snapshot availability.

It also contradicts WP01's stated safety rationale for the gate direction:
WP01 lands *before* WP03 flips/verifies the flag, so the DEFAULT (flag OFF) must
read legacy tasks.md — an ungated/default snapshot read hits an empty,
pre-backfill snapshot. WP04's inversion makes the default read the snapshot and
papers over the empty-snapshot case with an ad-hoc legacy fallback, rather than
using the flag as the cutover switch WP01/WP02 designed.

## Why the green test does not vindicate WP04

`tests/regression/test_issue_2684_subtask_completion_event_sourced.py` passes
ONLY because of the inversion. It creates the mission with `create_mission_core`
and NEVER sets `status_phase: 1`, so it runs at the default (flag OFF). Under
WP04's inversion, flag OFF → snapshot → honors the log → GREEN. Under the CORRECT
(WP01) convention, flag OFF → legacy tasks.md → sees the evicted `- [ ]` boxes →
refuses → the test would be RED unless it runs with the flag ON. The test
asserts the flipped/target state, so it must run with the flag ON, not be made to
pass by inverting production semantics.

## Required changes

1. **Align `_check_unchecked_subtasks` to WP01/WP02**: flag ON → reduced snapshot;
   flag OFF → legacy `tasks.md`. Do NOT keep the inversion. (Keep the
   pre-backfill / empty-snapshot legacy fallback as a *safety net under flag ON*,
   matching WP02's `stream empty / wp absent → None → legacy` behavior — but the
   flag direction itself must flip.)

2. **Make the merged red test pass under the corrected semantics** by running it
   with `_phase1_dual_write_enabled` ON (write `status_phase: "1"` into the
   mission's `meta.json` in the test setup — the test asserts the target/flipped
   state). Editing this pinned acceptance test is a justified out-of-map edit;
   record the one-line rationale in the test (e.g. "#2684 target state requires
   phase-1 cutover ON; foundation convention is flag ON → snapshot"). Do NOT
   invert the production flag to avoid editing the test.

3. **Fix the T017 owned test**
   (`test_check_unchecked_subtasks_snapshot_source.py`) to the corrected
   direction: the discriminating snapshot-authority fixtures must set the flag
   ON (currently they assert snapshot authority at the DEFAULT flag-OFF state);
   and `test_flag_on_uses_legacy_tasks_md_even_when_snapshot_contradicts` must
   become `flag OFF → legacy` (currently asserts flag ON → legacy, the inversion).

4. **Keep T015 (verified correct):** `mark-status` emits ONE `InnerStateChanged`
   subtasks delta per owning WP (grouped via `resolved_tasks_by_wp`), targets
   `st.feature_dir` (topology-resolved in `_ms_resolve_read_dir`, not `cwd` —
   C-003/#2647), stops the canonical CHECKBOX/INLINE_SUBTASKS durable write
   (throwaway `checkbox_probe`; `artifact_mutated` set only for PIPE_TABLE), and
   leaves the canonical `tasks.md` surface byte-stable. PIPE_TABLE (non-canonical;
   the gate's `iter_wp_section_subtask_rows` never reads it) legitimately keeps
   its existing write. The emit is live/reducible and consumed by the snapshot
   reader — no orphan. No changes needed here.

## Secondary (not blocking on their own)

- Ripple edits outside `owned_files` (`test_tasks_mark_status.py`,
  `test_tasks_coreless_orchestration.py`, `tasks.py` re-export,
  `test_tasks_compat_surface.py` golden count) are legitimate consequences of the
  byte-stability change (CHECKBOX/INLINE_SUBTASKS no longer durably written), not
  scope creep, and do not collide with another WP. Re-verify them after the flag
  direction is corrected, since some assertions may shift with the corrected
  reader.
