# Design Trace — implement-loop-coord-authority-completion-01KW2E7A

**Purpose:** a running log of the DESIGN itself — the decisions, the invariants kept
(KEEP set), the seam adopted — so we can assess afterward whether the design held under
implementation (the loop reads agreed with the writers, no #2155 re-opener, the gate
hardening actually closed the blind spot, #2140/#2183 closed cleanly).

---

## The design (seeded 2026-06-26)

**Frame:** the closing read-side increment of #2160. Adopt the *existing* kind-aware seam
`resolve_planning_read_dir(kind=...)` at every implement-loop read site, so PRIMARY-kind
artifacts (WP `tasks/`, `WP*.md`) resolve primary for all topologies while STATUS-kind
reads (events, matrices) stay coordination-aware. No new resolver is invented — the seam
landed in Phase 1 (PR #2181); this mission *consumes* it and *hardens the gate* that was
supposed to enforce it.

### Core design moves
- **Route PRIMARY-kind reads to the seam (FR-001..FR-005):** the 6 named cli residuals +
  the inline-shape residuals (`list_tasks`, `_find_first_for_review_wp`, review@2647) +
  `merge/done_bookkeeping.py` + the `workspace/context.py` cluster. Per-leg, not a
  one-line `feature_dir` swap.
- **Harden the gate that missed them (FR-007/008):** teach the dir-read AST scanner the
  inline-call shape `resolver(...) / "<name>"`, widen scope to all of `src/specify_cli/`,
  add a mandatory self-test, and triage the surfaced residual set (route or
  ticket-and-pin — no silent skip). This is the structural fix so the *next* residual
  can't hide.
- **Floor recompute (FR-012):** compute the post-fix live routed census, set the floor
  strictly below it (don't hardcode 31).
- **#2140 close (FR-010):** docstring refresh + a **negative-assertion** regression pin
  (returns False on a husk path lacking spec.md) — not a behavioral fix (already correct).
- **#2183 fold (FR-011):** teach `is_def_use_canonical` the `_canonicalize_bare_modern_handle`
  fold seam; 4 entries auto-route; permanent allowlist 7→3.

### KEEP set (load-bearing invariants — the anti-over-reduction guard)
- **C-001** STATUS-partition stays coord-aware — every **mixed-read** site split per-leg
  (tasks→primary, events→coord); a wholesale swap re-opens #2155.
- **C-002** no silent fallback; the coord-deleted hard-fail (#1848) on the status leg
  preserved; tasks-leg routing must not add a silent stale-primary fallback.
- **C-003** `primary_feature_dir_for_mission` stays handle-blind (canonicalize at caller).
- **C-004** `is_committed` stays single-surface (no multi-leg OR).
- **C-007** the `candidate_feature_dir`/`resolve_feature_dir_for_slug` resolver
  **consolidation** stays deferred — re-point call sites, don't merge resolvers.
- **C-008** review-cycle sub-artifacts (`baseline-tests.json`, rejected-review-cycle,
  arbiter, baseline) keep reads coord-aware as a matched read/write pair — route only the
  WP_TASK definition reads. (alphonso: routing reads without co-moving writers = NEW
  split-brain.)

### Design risks surfaced (to validate in implement)
- **Mixed-read sites are the highest risk** (paula): `tasks status` (2966/2983/2997),
  `_preview_claimable_wp_for_mission` via `discovery.py` (needs a **signature change**,
  not a one-liner), `finalize_tasks` (2276). Watch the per-leg split land cleanly.
- **The fixture is the load-bearing oracle** (renata): if it patches the
  topology-resolution stack (the `test_done_bookkeeping_seam.py:353` anti-pattern), every
  per-site test green-washes. FR-014 forbids stubbing the stack; assert BOTH legs.
- **Gate hardening can't self-validate** (gate-unmask-cannot-self-validate): the
  inline-shape detection + whole-`src` scope + floor raises only bite post-merge → NFR-005
  merged-branch verbatim dry-run is mandatory, not optional.
- **FR-008 is a discovery step:** whole-`src` widening will surface unknown residuals.
  Lane sizing must absorb the triage (the mission could undersize a *7th* time here).
- **Write-before-drop ordering** (lesson banked from the sibling mission's WP03 catch):
  any mechanical resolver swap that changes a call signature needs a transitional step,
  not a same-commit drop. Watch the `_preview_claimable` signature change.

## During / after implement — APPEND BELOW
<!-- Assess: did the loop reads actually agree with the writers on a live post-#2106
     coord fixture? did the hardened scanner catch the inline shape (self-test) and stay
     green on the merged branch? did any mixed-read split accidentally break a status read
     (C-001 regression)? did C-008 hold (no review-cycle split-brain)? did FR-008 surface
     a residual that should have been in-scope? net: is #2160 actually closeable, or did a
     residual escape again? -->

_(append during/after implement)_
