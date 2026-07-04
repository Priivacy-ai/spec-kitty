---
title: 3.2.x Milestone — Roadmap
description: 'Operator-facing roadmap for the 3.2.x milestone: the epic dependency spine, degod/unshim wave status, milestone census, exit criteria, and watch items.'
doc_status: active
updated: '2026-07-04'
---
# 3.2.x Milestone — Roadmap

*Planner synthesis (planner-priti), 2026-07-04. Sources: milestone #4 census, the native epic dependency graph encoded in the tracker on 2026-07-04, [`degod-unshim-roadmap.md`](degod-unshim-roadmap.md), and the epic bodies of #1619 / #1797 / #2071 / #1868 / #2173 / #1746.*

## Intent of 3.2.x

3.2.x is the **stabilization + structural debt paydown** cycle: (G1) deepen Doctrine/Charter/DRG impact on runtime execution, (G2) strangle the core domains — naming, identity, read/write paths — onto canonical SSOTs by *adopting* the existing execution-context machinery rather than building new construction, and (G3) land the DevEx enablers that make (G1)/(G2) enforceable. No new shadow paths. The milestone stays open until all three goals hold (full declaration: [`docs/release-goals/3.2.x.md`](../release-goals/3.2.x.md)). Everything experience-shaped — UX, dashboard, SaaS tie-in — is deliberately deferred to 3.3.x, which builds on the SSOTs this cycle establishes.

## The dependency spine

The epic graph is now encoded **natively in the tracker** as blocked-by edges (2026-07-04):

```
        #1868 seam-binding   #2173 runtime ports      (peer enablers)
                 \               /
                  ▼             ▼
              #1797 degod / unshim DELIVERY        #2071 test-QA friction
                  │       \                          /        │
                  ▼        ▼                        ▼         │
   #1619 runtime/state ROOT (P0)          #1746 Mission Clarity Layer (P1)
                                          — first FUNCTIONAL pickup

   #1931 test hygiene — standing campsite epic, deliberately OUTSIDE the blocking graph
```

**Reading order — enablers → delivery → functional pickup:**

1. **Enablers first.** #1868 binds *what a seam is and refuses bypass* (layer rules, identity value-object, guard capability, CI suite map, contract versions); #2173 binds *how infra is supplied without coupling* (ports + default-param DI). They share mechanism and run as peers.
2. **Delivery next.** #1797 (degod/unshim) is *blocked by* #1868 and #2173: every shim deletion is only safe once the seam it held is bound, and every god-object extraction only pays off once its pure core is stub-testable through a port.
3. **Root closes on delivery + QA.** #1619 (unify mission execution context — the program root) is *blocked by* #1797 and #2071: the `MissionExecutionContext`/`ResolvedMission` adoption cannot complete while god-objects re-derive context per call site and while the suite's accidental-pass/duplicate-knowledge debt makes structural change hazardous.
4. **First functional pickup.** #1746 (Mission Clarity Layer, P1) is *blocked by* #1797 and #2071 — queued as the first functional mission once the debt cluster lands, co-designed with #1666's communication-artefact contract.
5. **#1931** (test quality & suite hygiene) runs as a standing campsite epic: folded opportunistically into missions, never a blocker.

## Wave status board (degod/unshim roadmap)

| Wave | Deliverable | Status | Anchors |
|---|---|---|---|
| **0** (S) | Bind CI suite map — marker→job authority; `-m unit`/`-m contract` select a job; fails closed | **IN-FLIGHT** — mission `ci-suite-map-bind-01KWNPMP`, tasks finalized (5 WPs), triple-squad-hardened; implement next | #2034 (P1, milestoned 3.2.x 2026-07-04) + #2333 (folded in-mission) close with the PR; #2283 factor (a) only — (b)/(c) route to CT7 #2077, so #2283 stays OPEN |
| **1** (D) | tasks.py degod — body-thinning via ports, golden-CLI test first | **SHIPPED** — PR #2308 (tasks.py 4569→1206 LOC, 10/10 WPs) | #2116 CLOSED (+#2305/#2306/#2307) |
| **1∥** (U) | category_4 removable-now shim sweep (8→0) + orphan cleanup | **SHIPPED** — PR #2325 (unshim wave 1) | #2289, #2292, #2258 CLOSED |
| **2** (D+S) | coord-authority trio degod (workflow.py / implement.py / acceptance) + canonicalizer gate | **PARTIALLY QUEUED** — the #2164 Phase-1 canonicalizer gate is CLOSED; the trio degod itself is the next degod slice | #2164 CLOSED; #2160 OPEN (P0) |
| **2∥** (U+S) | `specify_cli.next` + `glossary` + charter shim deletions; WS1 layer rule bound | **SHIPPED** — PR #2328 (unshim wave 2, 9/9 WPs); shim registry drained to `shims: []` | #2291, #2290, #2326, #2327 CLOSED |
| **3** (D+S) | orchestrator_api degod + WS4 daemon-identity bind | **QUEUED** (category_7 orphan triage already executed in PR #2325; PR #2338 advanced the orchestrator-api contract to 1.2.0) | WS4 OPEN |
| **4** (D+S+U) | sync adapter cluster + WS6 contract-policy ADR + `category_b` burn-down (baseline 215) | **QUEUED** — safe last; adapter-shaped | WS6 in-progress |

Seam state carried from the wave plan: WS1/WS2/WS3 **DONE**, WS5 (CI suite map) **in-flight = Wave 0**, WS4 open and WS6 in-progress (pinning bound; policy ADR missing) — they gate Waves 3 and 4 respectively.

## Milestone census (2026-07-04)

**271 issues milestoned: 141 open / 130 closed** (48% burn — the count *grew* by 40 on 2026-07-04 when the sub-issue milestone-consistency sweep pulled the spine's unmilestoned children, the critical-path P1s, and #1716 (folding the retired 3.2.1 milestone) into 3.2.x; the burn percentage dropped for honest reasons: previously-invisible scope now counts). Recent landings: PRs #2332 (dashboard identity fix), #2336 (move-task `for_review` recovery), #2338 (orchestrator-api resolve-workspace + contract 1.2.0 + changelog-symlink cutover + `predict_lane_worktree` SSOT seam); the 2026-07-04 backlog revitalization closed 24 stale issues.

**Hot list:**

- **P0 (5 open in milestone):** #2346 (move-task subtask-guard regex leak — launch-blocker, queued as a post-mission op), #2160 (coord artifact authority — the class the Wave 2 trio closes), #2071 (test-QA epic), #1676 (deterministic structured authoring — verified 2026-07-04: carries **zero native dependency edges**, so it sits entirely outside the spine; it needs an explicit scheduling decision, see exit criterion 7), #1619 (the program root).
- **P1s from the 2026-07-04 sweep — pulled into 3.2.x (operator critical-path ruling, 2026-07-04):** #1239 (retrospect synthesize rejects its own create records), #1231 (stale-WP indicator: shell_pid liveness), #1734 (in_review→approved guard forces `--force` on standard review flows), #825 (restore push-time SonarCloud — CI hygiene).
- **Clusters (open-issue labels):** workflow 54 · reliability 50 · tech-debt 45 · bug 40 — consistent with a stabilization cycle: two-thirds of the open book is reliability/workflow/debt, not new surface.

## Exit criteria for 3.2.x

Derived from the epics' own done-conditions; the milestone closes when all hold:

1. **#1868** — all six seams bound to a type/owner: WS1–WS3 done; **WS5 lands with Wave 0** (marker→job authority, fails closed); WS4 daemon identity and WS6 versioned-contract ADR complete via Waves 3–4.
2. **#2173** — Phase-1 canonicalizer gate ✅ (#2164 closed); **Phase-2 `MissionResolver` port** owning the single `kitty-specs/` walk lands; Clock consolidation and `InstalledVersion` routing complete. No over-injection; frozen `MissionExecutionContext` never carries adapters.
3. **#1797** — shim registry stays `shims: []`; `category_b` honest baseline (215) burned down per Wave 4; the filed unshim children (category sweeps, orphan triage) all closed.
4. **#2071** — audit children (CT1 #2072, CT2 #2073, CT3 #2074, CT4 …) remediated; test-hygiene directive + ratchet in force so the suite is scaffold again (CT8/CT9 already shipped via gate-substrate PR #2317).
5. **#1619** — one canonical `ResolvedMission`/`MissionExecutionContext` minted per invocation and consumed by claim/implement/review/finalize/status/runtime/orchestrator; the dual `target_branch` readers, mid8 fabrications, and S8 silent glob deleted; ambiguity always structured, never silent.
6. **#1746** — Mission Clarity Layer delivered (SI-01…SI-10: mission-card.json, README generation, EMI header injection) as the cycle's functional capstone.
7. **P0 book empty** — #2346 fixed; #2160's class closed by the Wave 2 trio; #1676 resolved or explicitly re-milestoned with rationale.
8. **Non-spine open book dispositioned** — the remaining milestoned issues outside the spine (the reliability/workflow clusters) get an explicit close-or-re-milestone pass; nothing rides into 3.3.x silently.

## Risks / watch items

- **#2339 — two-authority migration-id conflict.** The upgrade dry-run JSON contract rejects dotted `migration_ids` (first live offender: `3.2.0rc45_retire_standalone_skill_surface`); this reds local runs today and is exactly the two-authority failure class Decision 8 of the in-flight suite-map mission exists to prevent. Watch for interaction with Wave 0.
- **#2342 — quarantined perf test pending verdict.** The retrospective 200-mission 5s NFR breach on CI is unadjudicated (real regression vs CI flake); the quarantine lane must not become a permanent parking lot.
- **#2345 / #1790 — dedup decision needed.** Both cover occurrence-map validation timing (bind at plan/tasks-finalize vs implement-claim-only); pick one canonical ticket before either is scheduled.
- **Milestone-drift on critical-path items** — resolved for the known set on 2026-07-04 (#1239/#1231/#1734/#825 and #2034 all pulled into 3.2.x by operator ruling), but the class remains live: a critical-path issue filed without a milestone silently escapes the burn count. The sub-issue milestone sweep (executed 2026-07-04, see next steps) is the standing counter-measure.
- **#2071 children are audit-fed.** The epic forbids pre-creating children; exit criterion 4 has open-ended scope until the audit's ticket set is complete. Watch for scope creep into #1931 territory (hygiene items belong in the campsite epic, not the blocker).
- **Wave-numbering homonyms — confirmed, not hypothetical.** Mission names and the roadmap's Wave 0–4 are distinct namespaces: PR #2308 is literally titled "Wave 2 tasks.py degod" yet delivered the roadmap's **Wave 1**, and "Unshim Wave 1/2" (PRs #2325/#2328) map to roadmap Waves 1∥/2∥ (plus the Wave-3 category_7 slice in #2325). Anchor all status claims to issue/PR numbers, never wave labels.

## Immediate next steps

1. **Finish Wave 0**: implement-review loop for `ci-suite-map-bind-01KWNPMP` (fresh session), closing #2034, #2333 (folded in-mission), and #2283 factor (a) — factors (b)/(c) remain under CT7 (#2077).
2. **Post-mission op**: fix P0 #2346 (queued).
3. **Then the Wave 2 degod trio** (workflow.py / implement.py / acceptance) against the now-bound suite map, closing the #2160 class.
4. **Keep milestones consistent downward** — ✅ executed 2026-07-04: the spine epics' sub-issue trees were swept (33 children assigned 3.2.x, 48 already correct, zero unexplained drift); the surviving deviations are all evidenced (#1711/#1709/#1710 at 3.3.x by operator batch; the Beads epic #1168 deferred to 3.3.0). The retired 3.2.1 milestone was closed and its last resident (#1716) folded into 3.2.x. Re-run the sweep whenever the spine gains children.
