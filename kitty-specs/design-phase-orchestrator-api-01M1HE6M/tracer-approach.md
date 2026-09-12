# Tracer: Approach — design-phase-orchestrator-api-01M1HE6M

Seeded at plan phase (2026-09-02). Appended during implementation; assessed at close.

## High-level WP sequencing approach

1. **WP01 — campsite-clean + baseline-red snapshot.** Lands first, tiny. Snapshots the
   targeted test directories against the pre-mission commit on
   `feat/design-phase-orchestrator-api-3837` so every later WP can distinguish issue
   #3284's ~23 known-red tests from anything this mission introduces. Folds
   domain-matched debt only if found directly in the functions this mission's WPs touch
   in `next_cmd.py`, `orchestrator_api/commands.py`, `envelope.py` — a plan-time pass
   found none; WP01's author re-checks with more time.

2. **Fan out to 5 independent lanes once WP01 lands**: WP02 (FR-014 seam extraction),
   WP03 (FR-001–003, thin specify/plan/tasks shims), WP04 (FR-004/005,
   check-prerequisites/record-analysis with the NFR-004 mechanism), WP05
   (FR-006–009/012, OriginFlow decision verbs), WP06 (FR-010, design-status). These five
   touch disjoint code: WP02 owns `next_cmd.py` + the new
   `runtime/next/next_invocation_lifecycle.py`; WP03–WP06 all add new, non-overlapping
   `@app.command` functions to `orchestrator_api/commands.py`. No WP in this fan-out
   depends on another in the fan-out.

3. **WP08 (FR-013, `answer-decision`) gates strictly on WP02.** This is the one hard
   sequencing constraint in the mission (spec C-005, operator ruling SPEC-FRESH2-001):
   `answer-decision` cannot be implemented, let alone merged, before the seam it calls
   exists. WP08 is otherwise independent of WP03–WP06 and can run in parallel with them
   once WP02 is done.

4. **WP07 (FR-011, contract-version bump) lands after every verb WP (WP03–WP06, WP08) is
   complete**, because its changelog comment must name all 11 new verbs by their final
   landed names/shapes — it is a small, low-risk WP that is trivial to review in
   isolation, but sequenced last among the code WPs so it does not need amending as verb
   WPs land.

5. **WP09 (docs) lands last.** It documents the ACTUAL landed behavior of all 11 verbs
   plus the contract-version bump, not the plan's prediction of that behavior — avoiding
   docs drifting from what shipped, which is exactly the kind of drift Clarification 2
   flagged as a pre-existing defect in the `.kittify/overrides/` copy of `analyze.md`.

## Why this ordering, not a strict linear WP01→WP09 chain

The mission's real complexity is concentrated in two places: WP02 (blast radius — a
refactor of live, always-run `next --answer` control-loop code) and WP08 (stakes — full
event-log/lifecycle-record parity with the host CLI, SC-007/SC-008). Everything else
(WP03–WP06) is precedent-following, additive, low-risk surface work mirroring the
existing `start-review`/`list-ready` verb pattern. Serializing the whole mission
end-to-end would needlessly gate the low-risk work behind the high-risk work; running
WP03–WP06 in parallel with WP02 lets reviewers and implementers spend their attention
where the mission's actual risk lives (WP02, WP08) without slowing down the rest.

## What the tasks phase should NOT have to re-derive

- The FR-014-before-FR-013 dependency (WP02 before WP08) and its rationale.
- The seam's target module (`src/runtime/next/next_invocation_lifecycle.py`) and why.
- That WP03–WP06 are mutually independent and independent of WP02.
- That WP07 depends functionally on nothing but is sequenced after the verb WPs for
  changelog-completeness reasons, not a hard dependency.
- That the SC-008 shared regression test is authored once (WP02, against the CLI path)
  and EXTENDED, not duplicated, by WP08 (against the orchestrator-api path).
