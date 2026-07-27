# Approach Evolution

> Track how your approach changed as the mission progressed.

Mission: `sync-batch-400-poison-isolation-01KXW08B` · #2736.

## Starting approach (from spec)

CLI-side **recursive bisection** on a whole-batch 400 (split → re-POST both halves → recurse to
singletons) in `delivery/receivers.py` — isolate the culprit, deliver the innocents. No server change
(non-destructive FIFO drain + selective commit make it CLI-solvable). Turn the merged red-first repro
`tests/delivery/test_poison_batch_2736.py` green.

## Entries (append dated)

- 2026-07-19 (pre-spec squad) — **Scope maximization (operator).** Started narrow (bisection only), then
  folded in the dormant offline-queue fan-out, the #2755 batch-split de-dup, and a CLI FSM force-free
  contract test. Deferral boundary set to the repo boundary — only genuinely cross-repo SaaS work stays out.
- 2026-07-19 (post-spec squad) — **Shift: "one authority" → "one shared MECHANISM."** The #2755 fold was
  first framed as a single ports-and-adapters *authority* consuming four sites. Paula showed that's a false
  unification (two bounded contexts + a limit-halving layer, and "byte-sizing" isn't a distinct site). The
  approach shifted to a pure `split_in_half` + `create_aware_midpoint` primitive with per-caller *policy*,
  and the create-aware cut relocated INTO the primitive so every splitter inherits it.
- 2026-07-19 (post-spec squad) — **Shift: sequence the P0 ahead of the refactor.** Priti flagged the P0
  release gate was welded to the P2 SSOT retrofit (SC-004). Re-sequenced so WP01+WP02→WP03 (primitive +
  bisection) ships the P0 alone; the SSOT retrofit (WP05b) is last and release-optional.
- 2026-07-19 (post-plan squad) — **Shift: the primitive's home moved `delivery/` → `core/`, and ordering
  moved off the primitive onto the bisect adapter.** The plan first placed the SSOT in `delivery/partition.py`
  (its first consumer) and framed `create_aware_midpoint` as the ordering fix. The post-plan squad (alphonso
  seam/layer + pedro feasibility, converging independently) showed (a) the `delivery/` home would create a
  `sync → delivery` runtime cycle at IC-06 that the layer gate can't catch — relocated to `core/batch_partition.py`;
  (b) ordering for a batch-spanning pair is impossible via any midpoint — it's the sequential recursion, so the
  primitive is now ordering-agnostic; (c) `split_in_half` (plain) and `create_aware_midpoint` stay two functions
  so the 413 shrink doesn't inherit create-aware snapping. Plan + spec wording aligned. All three squad verdicts
  were SAFE-WITH-CHANGES (no BLOCK); the P0↔#2755 decoupling was independently re-confirmed genuine.
- 2026-07-19 (post-tasks squad) — **Shift: the offline-queue fix moved from a dormant no-op to the real live
  poison, and WP04 split in two.** The whole mission had characterized the `sync/batch.py` fan-out as
  "dormant" (carried from pre-spec). Paula's post-tasks HIGH — verified from source — showed the named target
  (`_record_all_events_failed`) IS dormant (callers all `transient=True`), but a SIBLING function
  (`_parse_error_response` no-details branch) carries the LIVE poison on the `batch_sync` path. FR-005 re-
  targeted; WP04 split into WP04 (live fix, no dep) + WP05 (#2755 retrofit). Debbie separately confirmed the
  red anchor is honestly RED (ran it: 1 failed, real assertion) and that the pre-review gate green-washes the
  P0 as `no_coverage` (F9) — warnings folded into the WP prompts. Four lenses, all SAFE-WITH-CHANGES, no BLOCK;
  the squad's biggest value was catching a plan defect (a dormant-target fix) before implement.
- <!-- append implement shifts here -->
