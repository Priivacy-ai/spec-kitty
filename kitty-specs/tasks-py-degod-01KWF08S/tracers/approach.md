# Tracer: Approach

**Mission**: tasks-py-degod-01KWF08S
**Created**: 2026-07-02 (retrospectively at close — not seeded at planning; captured from the implement-loop history)
**Lifecycle**: seed at planning → append during implement → assess at close (experiment #2095)

The working strategy and how it evolved: plan-time intent vs implement-time reality, re-scopes, dead ends.

## Planning-phase approach (as specced, 9 WPs strictly-linear)

Golden-CLI-characterization-first → stratified ports → 3 pure decision/aggregation cores → rewire the fat bodies to thin orchestrators → census honesty. Behavior-preserving (pure parity); the golden harness is the safety net. Template = the completed `mission.py` degod (per-command extraction, golden-first). Hardened by two pre-plan squads + a 4-lens post-tasks squad (which reshaped the spec: two-capability port, #2072-predecessor, WP07 split, at-floor census).

## Implement-time reality (what actually happened)

- **The review gate earned its keep repeatedly.** Genuine parity defects caught *before* propagating: WP02 (a coord READ/WRITE split-brain in the FR-010 pin), WP03 (a partial-write-on-refusal eliminated by guard-consolidation), plus two strict-mypy CI-skew catches. Each fix landed with a pinning regression test.
- **The captured lessons compounded.** WP04 approved first-cycle *because* it proactively reproduced its own partial-write timing (the WP03 lesson) — every dispatch after WP03 front-loaded the accumulated gotchas, and later WPs increasingly landed clean.
- **Two structural re-scopes:**
  1. **WP07 split (planning-time, post-squad):** the original single 4-body rewire WP was split into WP07 (core-backed: map_requirements + status) + WP08 (coreless: mark_status + finalize_tasks) — the squad flagged it as overloaded. 8 → 9 WPs.
  2. **WP09 descope (implement-time, 8/9):** `tasks.py` had *grown* 3617 → ~4547 LOC during the rewires (decision logic left for the cores; orchestration glue + port-seam adapters accumulated in-file). The ≤1400 shim relocation (~3150-LOC move) + the Render seam were **descoped to a follow-up mission**; WP09 slimmed to census-cleanup-only (the self-inflicted red-gate debt that must land here). Operator decision — ship the delivered core value, don't cram the big relocation.

## Dead ends / corrections

- **FR-010 "same-dir equivalence" was wrong.** The spec claimed the kind-blind and kind-aware resolvers resolve the same dir; WP02 proved they *differ by construction* on coord topology (that divergence *is* the split-brain). Reframed to **guard-outcome equivalence** (the reads feed a no-op pre30 guard), with a **per-site pin table**: guard-only sites → primary; `move_task:1138` is a SHARED coord-status var → stays coord-husk. Spec + WP06/WP07 prompts corrected.
- **One-size-pin dead end.** WP02 cycle-1 pinned all three FR-010 sites to `WORK_PACKAGE_TASK`→primary; that would have moved move_task's authoritative status read off the coord husk (a real split-brain regression). Corrected to `STATUS_STATE`/coord-husk for move_task + a red-first hazard test.
- **Guard-consolidation dead end.** WP03 cycle-1 consolidated move_task's guards into the pure core cleanly — but moved two durable persists (override/arbiter) to after-all-guards, eliminating a partial-write-on-refusal. Corrected: fire the persists at their OLD guard positions via pure guard-slice signals.

## Net outcome

Core value delivered at 8 WPs: the change-magnet decision logic is in four pure tested cores behind injected ports; all fat bodies are ≤150 LOC thin orchestrators; behavior byte-identical. The "make tasks.py a pretty shim + unify rendering" work is a clean, well-scoped follow-up (see `docs/plans/tasks-py-degod-followup-mission-debrief.md`).

## Close assessment (2026-07-02) — outcome vs plan

Landed **9/9** on `design/degod-tasks-2116` (squash-merge, mission #157). Core value delivered: the change-magnet decision logic is in 4 pure tested cores behind injected ports; all fat bodies ≤150 LOC; behavior byte-identical (golden 42 throughout). Descoped (→ follow-up mission): the Render seam (FR-008) + the ≤1400 whole-file shim relocation (SC-005) — `tasks.py` is 4547 LOC (glue-heavy) pending that relocation. The cumulative arch-gate debt the rewires introduced (untrusted-path, status-boundary, tmp, marker, orphan-surface) was remediated pre-PR (the `post-merge-arch-gate-adjudication` procedure); the status-boundary import was routed through the `specify_cli.status` facade (not allowlisted). Merged branch is fully green (arch + agent 917 + git 46 + golden). Two campsite ops closed in-branch: CHANGELOG BOM/drift + test_tasks.py mypy debt.
