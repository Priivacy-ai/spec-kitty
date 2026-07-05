---
title: 3.2.x Milestone — Roadmap
description: 'Operator-facing roadmap for the 3.2.x milestone: the epic dependency spine, degod/unshim wave status, milestone census, exit criteria, and watch items.'
doc_status: active
updated: '2026-07-05'
related:
- docs/changelog/index.md
- docs/plans/index.md
- docs/release-goals/index.md
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
   #2392 upgrade-worktree coherence — #1619 child epic, consolidation-only (see Watch items)
   #2400 metadata & profile authority (P1) — #1799 sub-epic, consolidation-only (see Watch items)
```

**Reading order — enablers → delivery → functional pickup:**

1. **Enablers first.** #1868 binds *what a seam is and refuses bypass* (layer rules, identity value-object, guard capability, CI suite map, contract versions); #2173 binds *how infra is supplied without coupling* (ports + default-param DI). They share mechanism and run as peers.
2. **Delivery next.** #1797 (degod/unshim) is *blocked by* #1868 and #2173: every shim deletion is only safe once the seam it held is bound, and every god-object extraction only pays off once its pure core is stub-testable through a port.
3. **Root closes on delivery + QA.** #1619 (unify mission execution context — the program root) is *blocked by* #1797 and #2071: the `MissionExecutionContext`/`ResolvedMission` adoption cannot complete while god-objects re-derive context per call site and while the suite's accidental-pass/duplicate-knowledge debt makes structural change hazardous.
4. **First functional pickup.** #1746 (Mission Clarity Layer, P1) is *blocked by* #1797 and #2071 — queued as the first functional mission once the debt cluster lands, co-designed with #1666's communication-artefact contract.
5. **#1931** (test quality & suite hygiene) runs as a standing campsite epic: folded opportunistically into missions, never a blocker.
6. **#2392** (upgrade-worktree coherence, child of #1619) is the same kind of standing consolidation epic as #1931, not a blocking node — it exists to fold a git-state bug cluster (#2385, #1873, #2105, and the partly-fenced #2367) into **one** canonical fix seam instead of letting each land as an independent partial patch. Alphonso's design: a canonical invariant (*every write in every checkout the upgrade run touches ends in exactly one auto-commit — derived from real `git status --porcelain`, not a hardcoded list — or is intentionally reverted*), landed via a single `commit_touched_checkout` helper extracted from `_auto_commit_upgrade_changes` (`upgrade.py`) and applied symmetrically across main + every `.worktrees/*` enumerated by `runner.py`. #2367 is flagged as one-invariant-three-seams and kept OUT of this helper (see Watch items).
7. **#2400** (metadata & profile authority, **P1**, sub-epic of #1799) is a second standing consolidation epic of the same shape as #1931/#2392, not a blocking node — it exists to fold the "instructed, not enforced" defect class (the same class as #2364's dispatch-time model-discipline rule) into one canonical resolver/event-log authority instead of leaving it as prompt instructions or drifting hardcoded frontmatter. Members: **#2399** (structurally enforce agent-profile loading across all four invocation contexts — ops/ad-hoc/dispatch/mission-WP) and **#2093** (WP-metadata authority split: static design-intent stays frontmatter-canonical; dynamic runtime state — `agent`/`shell_pid`/`history`/reviews — retires to event-log/invocation authority, generalizing the `lane` retirement; architect-alphonso's DECISION already rules this REWORK-staged). Related but not reparented: #1841 (WP-claim Python profile-load) and #1840 (skills subagent-delegation preamble). Mutual coupling: splitting `agent_profile` (intent vs. resolved-binding, #2093) is the **precondition** for #2399's enforcement seam; #2399's resolve→materialize→record mechanism is the **mechanism** that makes #2093's dynamic half real — sequence the pair together (see Watch items).

## Wave status board (degod/unshim roadmap)

| Wave | Deliverable | Status | Anchors |
|---|---|---|---|
| **0** (S) | Bind CI suite map — marker→job authority; `-m unit`/`-m contract` select a job; fails closed | **SHIPPED** — PR #2368 (merged 2026-07-04, commit `6db60d367`; mission `ci-suite-map-bind-01KWNPMP`), marker→job authority bound — the substrate the ci-topology-shrink mission (below) builds on | #2297, #2296, #2034, #2333 CLOSED; #2283 factor (a) only — (b)/(c) route to CT7 #2077, so #2283 stays OPEN |
| **1** (D) | tasks.py degod — body-thinning via ports, golden-CLI test first | **SHIPPED** — PR #2308 (tasks.py 4569→1206 LOC, 10/10 WPs) | #2116 CLOSED (+#2305/#2306/#2307) |
| **1∥** (U) | category_4 removable-now shim sweep (8→0) + orphan cleanup | **SHIPPED** — PR #2325 (unshim wave 1) | #2289, #2292, #2258 CLOSED |
| **2** (D+S) | coord-authority trio degod (workflow.py / implement.py / acceptance) + canonicalizer gate | **PARTIALLY QUEUED** — the #2164 Phase-1 canonicalizer gate is CLOSED; the trio degod itself is the next degod slice | #2164 CLOSED; #2160 OPEN (P0) |
| **2∥** (U+S) | `specify_cli.next` + `glossary` + charter shim deletions; WS1 layer rule bound | **SHIPPED** — PR #2328 (unshim wave 2, 9/9 WPs); shim registry drained to `shims: []` | #2291, #2290, #2326, #2327 CLOSED |
| **3** (D+S) | orchestrator_api degod + WS4 daemon-identity bind | **QUEUED** (category_7 orphan triage already executed in PR #2325; PR #2338 advanced the orchestrator-api contract to 1.2.0) | WS4 OPEN |
| **4** (D+S+U) | sync adapter cluster + WS6 contract-policy ADR + `category_b` burn-down (baseline 215) | **QUEUED** — safe last; adapter-shaped | WS6 in-progress |

Seam state carried from the wave plan: WS1/WS2/WS3 **DONE**, WS5 (CI suite map) **DONE — shipped with Wave 0 (PR #2368)**, WS4 open and WS6 in-progress (pinning bound; policy ADR missing) — they gate Waves 3 and 4 respectively.

## Milestone census (2026-07-04)

**271 issues milestoned: 141 open / 130 closed** (48% burn — the count *grew* by 40 on 2026-07-04 when the sub-issue milestone-consistency sweep pulled the spine's unmilestoned children, the critical-path P1s, and #1716 (folding the retired 3.2.1 milestone) into 3.2.x; the burn percentage dropped for honest reasons: previously-invisible scope now counts). Recent landings: PRs #2332 (dashboard identity fix), #2336 (move-task `for_review` recovery), #2338 (orchestrator-api resolve-workspace + contract 1.2.0 + changelog-symlink cutover + `predict_lane_worktree` SSOT seam); the 2026-07-04 backlog revitalization closed 24 stale issues.

**Since census (2026-07-05): mission `ci-topology-shrink-01KWQAVX` SHIPPED (all 6 WPs done)** — a concrete instance of #1931's standing campsite epic folding into a mission (see dependency spine, above), and built directly on the Wave 0 marker→job substrate (PR #2368, above). It delivers **all three #1931 pillars in one pass**: **shrink** (**#1933** — the 32 previously-unmapped `src/specify_cli` dirs folded into six named composite `dorny/paths-filter` groups: `auth_audit_git`, `lifecycle`, `agent_surface`, `closeout`, `governance`, `platform`), **split** (**#2378** — `fast-tests-core-misc` divided into two disjoint matrix shards), and **un-blind** (**#2383** — the `arch-adversarial` guard de-serialized off the `fast-tests-core-misc` critical path: `if: always()` (100% of `src/`, no filter-group gating) plus a dropped `needs` edge — path collapses `sum`→`max` toward the ≤13.6-min ceiling). Also fixed in-flight: the pre-existing `mission-loader-coverage` C-005 coverage-drop (silently absent from `sonarcloud.needs`). Gate-coverage ratchet refreshed: `total_tests` 28573→28709, `duplicate_test_count` 3550→707, `orphan_test_count` 0. Closes #2378, #1933, #2383 under #1931. Draft PR (`pr/ci-topology-shrink`) prepared, not yet merged to upstream/main.

  *Discoveries worth carrying into future #1931 slices:* (a) a freshness/coverage invariant that derives its expected set from the **live**, mission-mutated tree is self-emptying once the mission's own change lands — WP01 hit exactly this (the worklist-vs-mapped-dirs check became mutually unsatisfiable post-WP03) and the fix is to derive against a **frozen pre-mission baseline** instead; (b) the mandatory full `tests/architectural/` sweep at closeout caught 4 stale sibling contract tests (`test_ci_quality_path_filters.py`, `test_ci_architectural_gate_coverage.py`) still asserting the pre-mission CI topology — per-WP review suites never ran them and would have missed the regression; (c) `if: always()` alone only un-blinds a job, it does **not** de-serialize it — de-serialization needs the `needs` edge dropped separately, and this mission required both moves together to hit the wallclock ceiling; (d) a completeness guard must **derive its scan scope from the surface it protects** — the docs-only trim's first guard hardcoded 2 of the pole's 4 `matrix.paths` roots and ran green while blind to a docs-scanning test in an uncovered root, a false-green caught only by independent review; the fix parses the pole's live roots so the guard can't drift.

  *Backfilled in-PR (both prior residual items now RESOLVED):* the timings artifact carries the live measurement from PR #2391 ci-quality run `28731385584` — measured core-misc critical path **14.4 min** (arch-adversarial pole), a **51% cut** from 29.4; and the escape-hatch honesty-note wording is corrected. The measurement met NFR-001's binding 55% bound (14.4 ≤ 16.17) but the arch pole came in heavier than projected (14.4 vs ~12.3), so it sits just over the aspirational ~13.6-min next-lane sub-target.
  *Follow-up (P1, #2397 — under #1931):* **matrix-shard the `arch-adversarial` pole** — post-de-serialization it is the single un-sharded critical-path bottleneck on every code PR (14.4 min), so sharding it (the pattern already applied to `fast-tests-core-misc`) is the remaining lever to bring the path under ~13.6 min and cut per-PR feedback latency for all contributors (high PR-friction/devex impact). Same invariant surface (`always_on_arch_present`/`differential_arch_matrix`, `test_arch_pole_deserialized`, FR-006) — needs re-verification when picked up.
  *Also landed in #2391:* a **docs-only trim** on the always-on pole — a docs-only PR runs only the docs-relevant arch guards (`-m docs_scoped`, seconds) instead of the full ~14.4-min suite, while preserving doc-terminology/doc-scanning coverage (the terminology guard scans `docs/`).

**Hot list:**

- **P0 (5 open in milestone):** #2346 (move-task subtask-guard regex leak — launch-blocker, queued as a post-mission op), #2160 (coord artifact authority — the class the Wave 2 trio closes), #2071 (test-QA epic), #1676 (deterministic structured authoring — verified 2026-07-04: carries **zero native dependency edges**, so it sits entirely outside the spine; it needs an explicit scheduling decision, see exit criterion 7), #1619 (the program root).
- **P1s from the 2026-07-04 sweep — pulled into 3.2.x (operator critical-path ruling, 2026-07-04):** #1239 (retrospect synthesize rejects its own create records), #1231 (stale-WP indicator: shell_pid liveness), #1734 (in_review→approved guard forces `--force` on standard review flows), #825 (restore push-time SonarCloud — CI hygiene).
- **Clusters (open-issue labels):** workflow 54 · reliability 50 · tech-debt 45 · bug 40 — consistent with a stabilization cycle: two-thirds of the open book is reliability/workflow/debt, not new surface.
- **#2392 (new, P1, child of #1619)** — "upgrade-worktree coherence" consolidation epic: one canonical fix for state/gitignore propagation across coord/lane/main, replacing what was trending toward N single-path partial fixes. Members: #2385 (`_auto_commit_upgrade_changes` main-only scope leaves sibling worktrees dirty, tripping the merge NFR-002 guard), #1873 (`_upgrade_worktrees` skips saving synthesized metadata when detected version == target), #2105 (main-checkout commit-set completeness — largely STALE per the design, since the git-status-derived commit-set is already implemented for main; residual is scope-only). #2367 is fenced as partly separate — one invariant at three seams, not one code fix: #2367-A (vcs-lock) was a deliberate stop-gap for a race (#2222/C-003; committing it would reverse that call) and #2367-B (rollback stale status) lives in the merge-snapshot path, not the upgrade helper.
- **#2400 (new, P1, sub-epic of #1799)** — "metadata & profile authority" consolidation epic: single canonical source, *structurally enforced*, across WP frontmatter, the event log, and invocation-time profile loading — same defect class as #2364 (model-discipline rule bound only as a dispatch-time prompt instruction). Members: #2399 (structurally enforce agent-profile loading across all four invocation contexts — ops/ad-hoc/dispatch/mission-WP) and #2093 (WP-metadata authority split — static design-intent stays frontmatter-canonical; dynamic runtime state, incl. `agent`/`shell_pid`/`history`/reviews, retires to event-log/invocation authority, generalizing the `lane` retirement; architect DECISION already rules it REWORK-staged). Related slices, not reparented: #1841 (WP-claim Python profile-load), #1840 (skills subagent-delegation). Mutual coupling: splitting `agent_profile` (#2093) is the precondition for #2399's enforcement; #2399's resolve→materialize→record seam is the mechanism for #2093's dynamic side — sequence together.

## Exit criteria for 3.2.x

Derived from the epics' own done-conditions; the milestone closes when all hold:

1. **#1868** — all six seams bound to a type/owner: WS1–WS3 done; **WS5 done — landed with Wave 0** (marker→job authority, fails closed, PR #2368); WS4 daemon identity and WS6 versioned-contract ADR complete via Waves 3–4.
2. **#2173** — Phase-1 canonicalizer gate ✅ (#2164 closed); **Phase-2 `MissionResolver` port** owning the single `kitty-specs/` walk lands; Clock consolidation and `InstalledVersion` routing complete. No over-injection; frozen `MissionExecutionContext` never carries adapters.
3. **#1797** — shim registry stays `shims: []`; `category_b` honest baseline (215) burned down per Wave 4; the filed unshim children (category sweeps, orphan triage) all closed.
4. **#2071** — audit children (CT1 #2072, CT2 #2073, CT3 #2074, CT4 …) remediated; test-hygiene directive + ratchet in force so the suite is scaffold again (CT8/CT9 already shipped via gate-substrate PR #2317).
5. **#1619** — one canonical `ResolvedMission`/`MissionExecutionContext` minted per invocation and consumed by claim/implement/review/finalize/status/runtime/orchestrator; the dual `target_branch` readers, mid8 fabrications, and S8 silent glob deleted; ambiguity always structured, never silent.
6. **#1746** — Mission Clarity Layer delivered (SI-01…SI-10: mission-card.json, README generation, EMI header injection) as the cycle's functional capstone.
7. **P0 book empty** — #2346 fixed; #2160's class closed by the Wave 2 trio; #1676 resolved or explicitly re-milestoned with rationale.
8. **Non-spine open book dispositioned** — the remaining milestoned issues outside the spine (the reliability/workflow clusters) get an explicit close-or-re-milestone pass; nothing rides into 3.3.x silently.

## Risks / watch items

- **#2339 — two-authority migration-id conflict.** The upgrade dry-run JSON contract rejects dotted `migration_ids` (first live offender: `3.2.0rc45_retire_standalone_skill_surface`); this reds local runs today and is exactly the two-authority failure class Decision 8 of the (now-shipped, PR #2368) suite-map mission exists to prevent. Watch for interaction with Wave 0.
- **#2342 — quarantined perf test pending verdict.** The retrospective 200-mission 5s NFR breach on CI is unadjudicated (real regression vs CI flake); the quarantine lane must not become a permanent parking lot.
- **#2345 / #1790 — dedup decision needed.** Both cover occurrence-map validation timing (bind at plan/tasks-finalize vs implement-claim-only); pick one canonical ticket before either is scheduled.
- **Milestone-drift on critical-path items** — resolved for the known set on 2026-07-04 (#1239/#1231/#1734/#825 and #2034 all pulled into 3.2.x by operator ruling), but the class remains live: a critical-path issue filed without a milestone silently escapes the burn count. The sub-issue milestone sweep (executed 2026-07-04, see next steps) is the standing counter-measure.
- **#2071 children are audit-fed.** The epic forbids pre-creating children; exit criterion 4 has open-ended scope until the audit's ticket set is complete. Watch for scope creep into #1931 territory (hygiene items belong in the campsite epic, not the blocker).
- **Wave-numbering homonyms — confirmed, not hypothetical.** Mission names and the roadmap's Wave 0–4 are distinct namespaces: PR #2308 is literally titled "Wave 2 tasks.py degod" yet delivered the roadmap's **Wave 1**, and "Unshim Wave 1/2" (PRs #2325/#2328) map to roadmap Waves 1∥/2∥ (plus the Wave-3 category_7 slice in #2325). Anchor all status claims to issue/PR numbers, never wave labels.
- **Avoid multi-path split-brain bugfix.** #2385/#1873/#2105 are the same underlying defect (upgrade-run auto-commit doesn't cover every touched checkout) surfacing at different call sites; fixing them independently risks exactly the kind of divergent-husk split-brain regression this milestone is paying down elsewhere. **#2392** is the counter-measure: one canonical `commit_touched_checkout` seam, applied symmetrically, instead of N partial patches. PR #2387 (an earlier single-path attempt) was redirected to `pr:needs-revision` for this reason — it should be re-pointed at the #2392 design rather than landed as-is. #2367's two seams (#2367-A vcs-lock stop-gap, #2367-B merge-snapshot rollback) are deliberately kept OUT of the consolidation and tracked separately.
- **Instructed-not-enforced / metadata split-brain.** #2399 and #2093 are the same "canonical authority exists in name, bound only by prompt instruction or hardcoded frontmatter copy" defect class as #2364 (dispatch-time model-discipline rule) and the sibling framing epic #1868 (different concrete domain — package layering, mission identity, guard capability, daemon identity, CI suite map, versioned contracts — not agent-profile/WP-metadata authority). **#2400** (P1) is the counter-measure, clustering #2399 + #2093 under one sub-epic instead of three unrelated parent epics (#2399 was under #1799 alone; #2093 under #1676; the WP-claim slice #1841 and doc-only companion #1840 under #1808). The pair is mutually coupled, not independently sequenceable: land #2093's intent/binding split and #2399's resolve→materialize→record mechanism together, or the half that lands first has nothing to bind against.

## Immediate next steps

1. **Wave 0 — ✅ done**: PR #2368 shipped (`ci-suite-map-bind-01KWNPMP`), closing #2034, #2333 (folded in-mission), and #2283 factor (a) — factors (b)/(c) remain under CT7 (#2077).
2. **Post-mission op**: fix P0 #2346 (queued).
3. **Then the Wave 2 degod trio** (workflow.py / implement.py / acceptance) against the now-bound suite map, closing the #2160 class.
4. **Keep milestones consistent downward** — ✅ executed 2026-07-04: the spine epics' sub-issue trees were swept (33 children assigned 3.2.x, 48 already correct, zero unexplained drift); the surviving deviations are all evidenced (#1711/#1709/#1710 at 3.3.x by operator batch; the Beads epic #1168 deferred to 3.3.0). The retired 3.2.1 milestone was closed and its last resident (#1716) folded into 3.2.x. Re-run the sweep whenever the spine gains children.
