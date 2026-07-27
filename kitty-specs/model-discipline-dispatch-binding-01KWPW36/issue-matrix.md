# Issue matrix — model-discipline-dispatch-binding-01KWPW36

One row per issue referenced in spec.md. Branch: `design/model-discipline-dispatch-2364`. Lands as its own sequential PR (not combined with #2365).

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2364 | model-discipline rule not applied at the dispatch/delegation seam | in-mission | Primary. FR-001–FR-009 (full-evaluator scope): catalog loader + action→task_type map + objective-function evaluator + advisory payload + profile field + tactic/DRG resolution + populated catalog + no-dangling invariant. Reaches terminal `fixed` before mission `done`. Claimed 2026-07-04. |
| #1799 | Epic: Charter & Doctrine — governance configuration | deferred-with-followup | Parent functional epic; stays open. Both #2364 and #2365 roll up here. |
| #1049 | Feature request: per-step model routing for Spec Kitty workflows | deferred-with-followup | Complementary static per-step config surface; explicitly out of scope (C-003) — this mission is doctrine-bound task-class routing. #1049 stays open as the separate config-surface track. |
| #1841 | Deterministic pre-execution profile load in Python, not prompt preambles | deferred-with-followup | Same "rule instructed not structurally bound" pattern (different rule). Cross-referenced in design; not folded. Follow-up: #1841 (stays open as the profile-load-binding track). |
| #1438 | model-task-routing Pydantic model / JSON Schema disagree | verified-already-fixed | Closed by PR #1545 — schema/Pydantic parity only, no consumer wiring. The schema this mission consumes is the one #1438 stabilized. |
| #1545 | PR: fix model-task-routing schema/Pydantic parity (closed #1438) | verified-already-fixed | Referenced as context only — the merged parity PR behind #1438. Not modified by this mission. |

**Ancestor (paper trail):** #240 "[2.x] Model Discipline and Cost-Aware Routing" (CLOSED, research-complete) — archived at `docs/archive/2x/model-discipline-routing.md`; the original intent this mission binds.

**Ruled out as wrong parent (verified by pre-spec squad):** #2196 (catfooding — closed) and #2216 (governance override/immutability tiers — orthogonal).

**Root cause (no reopen):** routing schema shipped in mission 057's bulk doctrine bootstrap (`623057f97`) with the consumer never scoped — a defined-but-dead catalog awaiting a binding.
