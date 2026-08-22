# Issue matrix — `up-org-template-fsm-01M06F9K`

| issue | verdict | evidence_ref | scope |
|---|---|---|---|
| #3523 | in-scope | this mission's own issue; FR-001–FR-012 | the mission |
| #3522 | deferred-with-followup | filed upstream, still open | out-of-scope gate defect |
| #3091 | no-action | closed upstream; cited only as a stale-comment observation | not a defect of this mission |

## `#3523` — this mission's own issue

Every requirement in `spec.md` traces to it. The two defects it reports — the forked resolvers'
drifted tier-1 probe, and the absent org tier in both the template chain and FSM discovery — are
FR-001 and FR-003–FR-009 respectively. Closing it is the mission's purpose, so there is nothing to
defer.

## `#3522` — deferred, and it bites this mission specifically

The architectural boundary tests hardcode their scan root to `src/specify_cli` and never examine
`src/runtime`, so a direct `doctrine.*` import anywhere under `src/runtime/` passes CI silently.

This mission touches `src/runtime/next/**` (WP04, WP06), which means **its own NFR-003 compliance
cannot be verified by CI**. That is not a reason to widen scope into fixing someone else's gate —
it is a reason to say so out loud. The plan records a three-point review discipline in place of the
missing gate: manual import confirmation at implementation time, an explicit statement in the PR
description naming this issue as the reason no gate caught it, and a spot-check at mission review.

**A green CI run on this PR is not evidence of NFR-003 compliance.** Recording that here so the
claim is on the mission's own record rather than only in the PR description.

Removal condition: when #3522 lands and the boundary tests scan `src/runtime`, this becomes a
gated check and the review discipline can be dropped.

## `#3091` — no action

Closed upstream. This mission cites it only in an observation that `pack_paths.py:112,121` and
`artifact_kinds.py:72,164` still carry pointers to it in comments, which is a documentation nit in
code this mission does not own and does not touch. Not folded in — an unrelated comment cleanup
inside an org-tier resolution change would make the diff harder to review for no benefit.
